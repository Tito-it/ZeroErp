# ⚙️ Funzione `fn_idempotency_prenota`

```sql
CREATE FUNCTION fn_idempotency_prenota(p_idempotency_key text, p_auth_user_id integer, p_endpoint text, p_request_id uuid)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_idempotency_prenota(p_idempotency_key text, p_auth_user_id integer, p_endpoint text, p_request_id uuid DEFAULT NULL::uuid)
 RETURNS TABLE(esito text, response_payload jsonb)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_riga           dbops.idempotency_keys%ROWTYPE;
    -- il valore grezzo del parametro, prima della validazione
    v_soglia_testo   config.parameters.default_value%TYPE;
    -- secondi: un intero validato, non una colonna
    v_soglia_secondi integer;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Prenotare una Idempotency-Key per una richiesta, e dire al
    --   backend che cosa fare:
    --     ESEGUI   — la key e' sua: esegua l'operazione;
    --     REPLAY   — l'operazione e' gia' stata fatta: rimandi
    --                response_payload;
    --     IN_CORSO — la sta eseguendo un'altra richiesta: 409
    --                E_IDEMPOTENCY_IN_PROGRESS (lo solleva il backend).
    --
    -- Regole:
    --   - key nuova                         → ESEGUI
    --   - key di un altro utente o endpoint → E_IDEMPOTENCY_KEY_RIUSATA
    --   - completed                         → REPLAY
    --   - failed                            → ripresa, ESEGUI
    --   - in_progress entro la soglia       → IN_CORSO
    --   - in_progress oltre la soglia       → ripresa, ESEGUI (D6)
    --
    -- ⛔ La ripresa di una in_progress e' sicura solo se il backend
    --   scrive completed nella stessa transazione dell'operazione:
    --   vedi l'intestazione del changeSet 20261023-04.
    -- =========================================================

    -- Guard di parametro: forme che nessuna richiesta produce.
    IF NULLIF(btrim(p_idempotency_key), '') IS NULL
       OR NULLIF(btrim(p_endpoint), '') IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'dbops.fn_idempotency_prenota', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'key ed endpoint obbligatori',
                               'p_endpoint', p_endpoint),
            NULL::uuid,
            'dbops.fn_idempotency_prenota',
            'la key e l''endpoint della richiesta sono obbligatori');
    END IF;

    -- 1. Key nuova: la prenotazione e' di chi la scrive.
    INSERT INTO dbops.idempotency_keys (
        idempotency_key, request_id, status, auth_user_id, endpoint)
    VALUES (p_idempotency_key, p_request_id, 'in_progress', p_auth_user_id, p_endpoint)
    ON CONFLICT (idempotency_key) DO NOTHING
    RETURNING * INTO v_riga;

    IF FOUND THEN
        RETURN QUERY SELECT 'ESEGUI'::text, NULL::jsonb;
        RETURN;
    END IF;

    -- 2. La key c'e'. FOR UPDATE: due riprese concorrenti non
    --    eseguono entrambe, e un'operazione che sta scrivendo
    --    completed si aspetta per l'istante del suo commit.
    SELECT * INTO v_riga
      FROM dbops.idempotency_keys k
     WHERE k.idempotency_key = p_idempotency_key
       FOR UPDATE;

    IF NOT FOUND THEN
        -- Purgata fra i due passi (la regola 24 la fa scadere dopo
        -- un giorno): e' di nuovo una key nuova. Se un'altra
        -- richiesta l'ha appena riscritta, e' sua e sta lavorando.
        INSERT INTO dbops.idempotency_keys (
            idempotency_key, request_id, status, auth_user_id, endpoint)
        VALUES (p_idempotency_key, p_request_id, 'in_progress', p_auth_user_id, p_endpoint)
        ON CONFLICT (idempotency_key) DO NOTHING;
        RETURN QUERY SELECT (CASE WHEN FOUND THEN 'ESEGUI' ELSE 'IN_CORSO' END)::text,
                            NULL::jsonb;
        RETURN;
    END IF;

    -- 3. D7: la key e' di chi l'ha prenotata, su quell'endpoint.
    --    ⚠️ endpoint NULL = riga nata prima del 2026-10-23: nessun
    --    legame da confrontare.
    --    ⛔ Nel contesto non entrano utente ed endpoint dell'ALTRO:
    --    sono proprio cio' che non va rivelato a chi rimanda la key.
    IF v_riga.endpoint IS NOT NULL
       AND (v_riga.endpoint     IS DISTINCT FROM p_endpoint
         OR v_riga.auth_user_id IS DISTINCT FROM p_auth_user_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'dbops.fn_idempotency_prenota', 'E_IDEMPOTENCY_KEY_RIUSATA',
            jsonb_build_object('detail', 'key prenotata da un altro utente o su un altro endpoint',
                               'endpoint', p_endpoint),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 4. Fatta: si rimanda la risposta salvata.
    --    ⭐ Si decide dalla RISPOSTA e non dall'esito: per
    --    chk_idempotency_keys_risposta_solo_completed (20261023-03)
    --    c'e' se e solo se la key e' completed. Cosi' la funzione non
    --    nomina gli esiti che scrive il backend: il presidio C1
    --    (dbops.vw_stati_check_scrittori) e' testuale, e conterebbe
    --    questa funzione fra i loro scrittori.
    IF v_riga.response_payload IS NOT NULL THEN
        RETURN QUERY SELECT 'REPLAY'::text, v_riga.response_payload;
        RETURN;
    END IF;

    -- 5. In corso: entro la soglia lavora qualcun altro; oltre, chi
    --    lavorava e' morto senza commit (D6) e si riprende.
    --    prenotata_at e' l'ora della prenotazione o della ripresa
    --    (20261023-03); non data_update, che il trigger di audit
    --    riscrive a ogni UPDATE.
    IF v_riga.status = 'in_progress' THEN
        SELECT p.default_value INTO v_soglia_testo
          FROM config.parameters p
         WHERE p.code = 'SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI';

        -- Fail-loud: assente, vuoto o non intero positivo e'
        -- un'installazione rotta, mai un valore di ripiego.
        IF COALESCE(v_soglia_testo, '') !~ '^[1-9][0-9]{0,5}$' THEN
            PERFORM script.fn_log_and_raise_error(
                'dbops', 'dbops.fn_idempotency_prenota', 'E_CONFIG_MANCANTE',
                jsonb_build_object('config',    'config.parameters',
                                   'parametro', 'SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI',
                                   'valore',    v_soglia_testo),
                NULL::uuid,
                VARIADIC ARRAY['parametro SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI (intero positivo)']);
        END IF;
        v_soglia_secondi := v_soglia_testo::integer;

        IF v_riga.prenotata_at > now() - make_interval(secs => v_soglia_secondi) THEN
            RETURN QUERY SELECT 'IN_CORSO'::text, NULL::jsonb;
            RETURN;
        END IF;
    END IF;

    -- 6. Ripresa: failed, o in_progress abbandonata. La riga si
    --    lega a chi la riprende (le righe senza legame lo prendono qui).
    UPDATE dbops.idempotency_keys k
       SET status           = 'in_progress',
           request_id       = p_request_id,
           tx_id            = NULL,
           response_payload = NULL,
           auth_user_id     = p_auth_user_id,
           endpoint         = p_endpoint,
           prenotata_at     = now(),
           data_update      = now(),
           user_update      = CURRENT_USER
     WHERE k.idempotency_key = p_idempotency_key;

    RETURN QUERY SELECT 'ESEGUI'::text, NULL::jsonb;
END;
$function$

COMMENT ON FUNCTION dbops.fn_idempotency_prenota(p_idempotency_key text, p_auth_user_id integer, p_endpoint text, p_request_id uuid)
IS 'Prenota una Idempotency-Key per una richiesta e risponde al backend: ESEGUI (la key e'' sua), REPLAY (operazione gia'' fatta: response_payload), IN_CORSO (la sta eseguendo un''altra richiesta: il backend solleva E_IDEMPOTENCY_IN_PROGRESS). Una key failed, o in_progress da oltre SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI (config.parameters, sopra il timeout di gunicorn), si riprende (D6). Una key prenotata da un altro utente o su un altro endpoint solleva E_IDEMPOTENCY_KEY_RIUSATA (D7); le righe nate prima del 2026-10-23 (endpoint NULL) non hanno legame e lo prendono alla ripresa. ⛔ La ripresa di una in_progress e'' sicura solo se il backend scrive completed nella STESSA transazione dell''operazione: allora una in_progress orfana vuol dire «nessun commit». La prenotazione committa da sola: le altre richieste la vedono subito e non aspettano. SECURITY INVOKER. Brief: brief-be-verifica-documentazione-api D6, D7.';
```

</div>

---
{% include-markdown "signature-core.md" %}
