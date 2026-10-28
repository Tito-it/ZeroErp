{% include-markdown "it/dbzero/dbops/manual/fn_accoda_lavoro.md" %}
# ⚙️ Funzione `fn_accoda_lavoro`

```sql
CREATE FUNCTION fn_accoda_lavoro(p_job_type text, p_payload jsonb, p_run_as text, p_scope jsonb, p_idempotency_key text, p_priorita smallint, p_run_after timestamp with time zone, p_max_tentativi integer, p_origine text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_accoda_lavoro(p_job_type text, p_payload jsonb DEFAULT '{}'::jsonb, p_run_as text DEFAULT NULL::text, p_scope jsonb DEFAULT NULL::jsonb, p_idempotency_key text DEFAULT NULL::text, p_priorita smallint DEFAULT 100, p_run_after timestamp with time zone DEFAULT NULL::timestamp with time zone, p_max_tentativi integer DEFAULT NULL::integer, p_origine text DEFAULT 'API'::text)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tipo     dbops.coda_lavori_tipi%ROWTYPE;
    v_classe   dbops.processi.classe%TYPE;
    v_run_as   dbops.coda_lavori.run_as%TYPE;
    v_max_tent dbops.coda_lavori.max_tentativi%TYPE;
    v_id       dbops.coda_lavori.id%TYPE;
BEGIN
    -- Scopo: enqueue atomico idempotente. Valida il tipo, risolve i
    --   default, INSERT idempotente sui job vivi. Una sola INSERT ->
    --   atomica per costruzione (autocommit). Callable da trigger.

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

    -- Risoluzione default per-tipo se non passati.
    v_run_as   := COALESCE(p_run_as, v_tipo.run_as_default);
    v_max_tent := COALESCE(p_max_tentativi, v_tipo.max_tentativi_default);

    -- =====================================================
    -- ⭐ Guard di CLASSE (2026-09-04). Il default per-tipo qui
    --   sopra e' un suggerimento che `p_run_as` sovrascrive:
    --   senza questo controllo un lavoro di DOMINIO poteva
    --   essere accodato come SISTEMA e girare senza operatore.
    --   La classe si LEGGE dal registro, non da una copia sulla
    --   riga del tipo: fonte unica, e se un processo cambia
    --   classe la coda lo sa il giorno stesso.
    --   ⚠️ Sotto-select scalare, non SELECT INTO: senza righe
    --   ritorna NULL e il ramo non scatta — un tipo non ancora
    --   agganciato a un processo non viene bloccato (la colonna
    --   e' NOT NULL dal changeSet -42, ma qui non si assume).
    -- =====================================================
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

    -- Guard coerenza run_as<->scope (messaggio parlante prima del
    -- CHECK di tabella): OPERATORE senza scope girerebbe senza filtro
    -- RLS. Il caso simmetrico (SISTEMA con scope) lo copre il CHECK.
    IF v_run_as = 'OPERATORE' AND p_scope IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'dbops.fn_accoda_lavoro', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_scope', 'run_as', v_run_as),
            NULL::uuid, 'p_scope obbligatorio per run_as=OPERATORE');
    END IF;

    -- Enqueue idempotente sui job vivi: l'unique parziale
    -- uq_coda_lavori_vivo_idem assorbe il doppione vivo (stessa
    -- job_type+idempotency_key in PENDING/IN_CORSO).
    INSERT INTO dbops.coda_lavori (
        job_type, payload, run_as, scope, origine, priorita,
        stato, max_tentativi, run_after, idempotency_key
    ) VALUES (
        p_job_type,
        COALESCE(p_payload, '{}'::jsonb),
        v_run_as,
        p_scope,
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

    -- Conflitto idempotente (nessuna riga inserita): ritorna l'id
    -- del job vivo esistente, senza creare doppioni.
    IF v_id IS NULL THEN
        SELECT id INTO v_id
          FROM dbops.coda_lavori
         WHERE job_type = p_job_type
           AND idempotency_key = p_idempotency_key
           AND stato IN ('PENDING', 'IN_CORSO')
         ORDER BY id
         LIMIT 1;
    END IF;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_accoda_lavoro(p_job_type text, p_payload jsonb, p_run_as text, p_scope jsonb, p_idempotency_key text, p_priorita smallint, p_run_after timestamp with time zone, p_max_tentativi integer, p_origine text)
IS 'Enqueue atomico idempotente nella coda lavori generica dbops.coda_lavori. Valida il job_type contro dbops.coda_lavori_tipi (E_JOB_TYPE_NON_TROVATO/NON_ATTIVO), risolve i default per-tipo, verifica la coerenza OPERATORE<->scope, INSERT ON CONFLICT DO NOTHING sull''unique parziale vivo. ⭐ Rev 2026-09-04: guard di CLASSE — un job il cui processo e'' di classe DOMINIO non puo'' essere accodato con run_as diverso da OPERATORE (E_JOB_DOMINIO_SENZA_OPERATORE). Serve perche'' il run_as_default del tipo e'' un suggerimento che p_run_as sovrascrive, e il CHECK di tabella guarda la coerenza run_as/scope, non la natura del lavoro. La classe si legge da dbops.processi via coda_lavori_tipi.processo_codice: fonte unica, mai duplicata. Brief: brief-db-processi-automatici-identita-e-perimetro §5.3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
