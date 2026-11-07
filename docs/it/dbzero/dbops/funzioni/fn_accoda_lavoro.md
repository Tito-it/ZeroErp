{% include-markdown "it/dbzero/dbops/manual/fn_accoda_lavoro.md" %}
# ⚙️ Funzione `fn_accoda_lavoro`

```sql
CREATE FUNCTION fn_accoda_lavoro(p_job_type text, p_payload jsonb, p_run_as text, p_scope jsonb, p_idempotency_key text, p_priorita smallint, p_run_after timestamp with time zone, p_max_tentativi integer, p_origine text)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_accoda_lavoro(p_job_type text, p_payload jsonb DEFAULT '{}'::jsonb, p_run_as text DEFAULT NULL::text, p_scope jsonb DEFAULT NULL::jsonb, p_idempotency_key text DEFAULT NULL::text, p_priorita smallint DEFAULT 100, p_run_after timestamp with time zone DEFAULT NULL::timestamp with time zone, p_max_tentativi integer DEFAULT NULL::integer, p_origine text DEFAULT 'API'::text)
 RETURNS bigint
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_tipo         dbops.coda_lavori_tipi%ROWTYPE;
    v_classe       dbops.processi.classe%TYPE;
    v_run_as       dbops.coda_lavori.run_as%TYPE;
    v_max_tent     dbops.coda_lavori.max_tentativi%TYPE;
    v_emittente    dbops.coda_lavori.emittente_fiscale_id%TYPE;
    v_id           dbops.coda_lavori.id%TYPE;
    v_vivo_run_as  dbops.coda_lavori.run_as%TYPE;
    v_vivo_emitt   dbops.coda_lavori.emittente_fiscale_id%TYPE;
    v_da_app       boolean;
    -- ⚠️ `integer` esplicito: django.auth_user.id, a cui il DB non si lega.
    v_chiamante    integer;
    -- ⚠️ `bigint[]` esplicito: elementi = anagrafiche.emittenti_fiscali.id.
    v_perimetro    bigint[];
BEGIN
    -- Scopo: la porta della coda. Valida il tipo, risolve i
    --   default, controlla classe e scope, scrive l'azienda del
    --   lavoro, accoda idempotente sui lavori vivi. SECURITY
    --   DEFINER: vede tutte le righe, quindi controlla da se' chi
    --   puo' accodare che cosa (vedi testata del changeSet).

    -- Guard parametro: job_type obbligatorio e non vuoto.
    IF p_job_type IS NULL OR btrim(p_job_type) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'dbops.fn_accoda_lavoro', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_job_type'),
            NULL::uuid, 'p_job_type obbligatorio');
    END IF;

    -- Guard: tipo registrato in coda_lavori_tipi.
    SELECT * INTO v_tipo
      FROM dbops.coda_lavori_tipi
     WHERE codice = p_job_type;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'dbops.fn_accoda_lavoro', 'E_JOB_TYPE_NON_TROVATO',
            jsonb_build_object('job_type', p_job_type),
            NULL::uuid, p_job_type);
    END IF;

    -- Guard: tipo attivo (l'handler dev'essere registrato lato BE).
    IF NOT v_tipo.attivo THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'dbops.fn_accoda_lavoro', 'E_JOB_TYPE_NON_ATTIVO',
            jsonb_build_object('job_type', p_job_type),
            NULL::uuid, p_job_type);
    END IF;

    -- Default per tipo, se non passati.
    v_run_as   := COALESCE(p_run_as, v_tipo.run_as_default);
    v_max_tent := COALESCE(p_max_tentativi, v_tipo.max_tentativi_default);

    -- Guard di classe: il default del tipo e' un suggerimento che
    --   p_run_as sovrascrive; un lavoro di DOMINIO resta OPERATORE.
    --   La classe si legge dal registro dei processi, non da una
    --   copia. ⚠️ Sotto-select scalare: un tipo senza processo da' NULL
    --   e il ramo non scatta (processo_codice e' NOT NULL, ma qui non
    --   si assume).
    v_classe := (SELECT pr.classe
                   FROM dbops.processi pr
                  WHERE pr.codice = v_tipo.processo_codice);

    IF v_classe = 'DOMINIO' AND v_run_as <> 'OPERATORE' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'dbops.fn_accoda_lavoro',
            'E_JOB_DOMINIO_SENZA_OPERATORE',
            jsonb_build_object('job_type', p_job_type,
                               'run_as', v_run_as,
                               'processo_codice', v_tipo.processo_codice),
            NULL::uuid, p_job_type, v_run_as);
    END IF;

    -- Guard run_as <-> scope (messaggio parlante prima del CHECK):
    --   un OPERATORE senza scope girerebbe senza identita'. Il caso
    --   simmetrico (SISTEMA con scope) lo copre il CHECK.
    IF v_run_as = 'OPERATORE' AND p_scope IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'dbops.fn_accoda_lavoro', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_scope', 'run_as', v_run_as),
            NULL::uuid, 'p_scope obbligatorio per run_as=OPERATORE');
    END IF;

    -- Un lavoro OPERATORE appartiene a un'azienda: l'emittente
    --   attivo di chi l'ha accodato, catturato nello scope.
    IF v_run_as = 'OPERATORE' THEN
        v_emittente := (p_scope ->> 'emittente_attivo_id')::bigint;
        IF v_emittente IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'dbops.fn_accoda_lavoro',
                'E_CODA_LAVORO_SENZA_EMITTENTE',
                jsonb_build_object('job_type', p_job_type,
                                   'parametro', 'p_scope'),
                NULL::uuid, p_job_type);
        END IF;
    END IF;

    -- Chi chiama. ⭐ Da una sessione dell'applicazione la porta
    --   controlla cio' che la policy controllerebbe; fuori la
    --   raggiunge solo il proprietario (l'esecuzione e' tolta a
    --   PUBLIC), cioe' le procedure di pgAgent e la migrazione.
    --   ⚠️ session_user e non current_user: qui dentro current_user
    --   e' il proprietario, sempre.
    v_da_app := CASE
                    WHEN EXISTS (SELECT 1 FROM pg_catalog.pg_roles
                                  WHERE rolname = 'zeroerp_app')
                    THEN pg_catalog.pg_has_role(session_user, 'zeroerp_app', 'MEMBER')
                    ELSE false
                END;

    IF v_da_app THEN
        v_chiamante := NULLIF(current_setting('app.current_user_id', true), '')::integer;
        v_perimetro := script.fn_get_emittenti_scope_pk_ids(v_chiamante);

        IF v_run_as = 'OPERATORE'
           AND (v_chiamante IS NULL
                OR current_setting('app.ruolo_applicativo', true) IS DISTINCT FROM 'OPERATORE'
                OR (p_scope ->> 'auth_user_id')::integer IS DISTINCT FROM v_chiamante
                OR NOT script.fn_scope_ef_perimetro(v_perimetro, v_emittente)) THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'dbops.fn_accoda_lavoro', 'E_CODA_SCOPE_ALTRUI',
                jsonb_build_object('job_type', p_job_type,
                                   'emittente_fiscale_id', v_emittente,
                                   'scope_auth_user_id', p_scope ->> 'auth_user_id',
                                   'chiamante', v_chiamante),
                NULL::uuid, p_job_type);
        END IF;
    END IF;

    -- ⛔ D9: il ciclo dell'upsert. L'unique parziale
    --   uq_coda_lavori_vivo_idem assorbe il doppione vivo (stessa
    --   job_type + idempotency_key in PENDING/IN_CORSO); se il vivo
    --   si chiude fra l'INSERT e la rilettura, si riprova l'INSERT.
    LOOP
        INSERT INTO dbops.coda_lavori (
            job_type, payload, run_as, scope, emittente_fiscale_id,
            origine, priorita, stato, max_tentativi, run_after,
            idempotency_key
        ) VALUES (
            p_job_type,
            COALESCE(p_payload, '{}'::jsonb),
            v_run_as,
            p_scope,
            v_emittente,
            p_origine,
            COALESCE(p_priorita, 100::smallint),
            'PENDING',
            v_max_tent,
            p_run_after,
            p_idempotency_key
        )
        ON CONFLICT (job_type, idempotency_key)
            WHERE idempotency_key IS NOT NULL
              AND stato IN ('PENDING', 'IN_CORSO')
            DO NOTHING
        RETURNING id INTO v_id;

        EXIT WHEN v_id IS NOT NULL;

        -- Conflitto: il lavoro vivo con la stessa chiave.
        SELECT c.id, c.run_as, c.emittente_fiscale_id
          INTO v_id, v_vivo_run_as, v_vivo_emitt
          FROM dbops.coda_lavori c
         WHERE c.job_type = p_job_type
           AND c.idempotency_key = p_idempotency_key
           AND c.stato IN ('PENDING', 'IN_CORSO')
         ORDER BY c.id
         LIMIT 1;

        IF v_id IS NOT NULL THEN
            -- ⛔ La porta vede oltre la policy: restituisce solo cio'
            --   che chi chiama potrebbe vedere. Un lavoro SISTEMA non
            --   ha azienda, e lo si accoda anche da operatore.
            IF v_da_app
               AND v_vivo_run_as = 'OPERATORE'
               AND NOT script.fn_scope_ef_perimetro(v_perimetro, v_vivo_emitt) THEN
                PERFORM script.fn_log_and_raise_error(
                    'database', 'dbops.fn_accoda_lavoro', 'E_CODA_CHIAVE_ALTRUI',
                    jsonb_build_object('job_type', p_job_type,
                                       'idempotency_key', p_idempotency_key),
                    NULL::uuid, p_job_type, p_idempotency_key);
            END IF;
            EXIT;
        END IF;
        -- Il vivo si e' chiuso nel frattempo: si riprova l'INSERT.
    END LOOP;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_accoda_lavoro(p_job_type text, p_payload jsonb, p_run_as text, p_scope jsonb, p_idempotency_key text, p_priorita smallint, p_run_after timestamp with time zone, p_max_tentativi integer, p_origine text)
IS 'La porta della coda dbops.coda_lavori, l''unica. Valida il tipo (E_JOB_TYPE_NON_TROVATO, E_JOB_TYPE_NON_ATTIVO), risolve i default del tipo, tiene di DOMINIO i soli lavori OPERATORE (E_JOB_DOMINIO_SENZA_OPERATORE, la classe da dbops.processi), pretende lo scope per un OPERATORE e un''azienda nello scope (E_CODA_LAVORO_SENZA_EMITTENTE), che scrive in emittente_fiscale_id. SECURITY DEFINER: vede tutte le righe, quindi da una sessione dell''applicazione controlla cio'' che la policy controllerebbe: un lavoro OPERATORE si accoda solo con la propria identita'' e nel proprio perimetro (E_CODA_SCOPE_ALTRUI), e un lavoro vivo con la stessa chiave si restituisce solo se chi chiama potrebbe vederlo (E_CODA_CHIAVE_ALTRUI). Fuori dall''applicazione la raggiunge solo il proprietario: l''esecuzione e'' tolta a PUBLIC. Idempotente sui lavori vivi col ciclo dell''upsert: se il vivo si chiude fra l''INSERT e la rilettura, l''INSERT si riprova, e la funzione non restituisce mai un id vuoto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
