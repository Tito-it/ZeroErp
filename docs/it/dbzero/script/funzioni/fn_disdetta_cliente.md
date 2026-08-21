{% include-markdown "it/dbzero/script/manual/fn_disdetta_cliente.md" %}
# ⚙️ Funzione `fn_disdetta_cliente`

```sql
CREATE FUNCTION fn_disdetta_cliente(p_cliente_id bigint, p_data_cessazione date)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_disdetta_cliente(p_cliente_id bigint, p_data_cessazione date)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_stato_attivo_id   config.stati_cliente.id%TYPE;
    v_stato_chiuso_id   config.stati_cliente.id%TYPE;
    v_codice_attivo     config.stati_cliente.codice_interno%TYPE := 'AT';
    v_codice_chiuso     config.stati_cliente.codice_interno%TYPE := 'CH';
    v_data_attivazione  anagrafiche.clienti.data_attivazione%TYPE;
    v_stato_corrente_id anagrafiche.clienti.stato_cliente_id%TYPE;
BEGIN
-- ------------------------------------------------------------
-- Funzione: script.fn_disdetta_cliente
--
-- Scopo:
--   Cessazione di un cliente senza subentro (disdetta).
--   Chiude il cliente impostando data_chiusura e stato CH.
--   I trigger cascata gestiscono:
--     - trgfn_clienti_set_periodo -> aggiorna periodo
--     - trgfn_clienti_sync_stato_pdp -> PDP torna DISPONIBILE
--     - trgfn_storico_generic -> storicizzazione
--     - trgfn_audit_data_user_generic -> audit
--
-- Policy BA:
--   Il billing_account NON viene toccato dalla disdetta.
--   Resta attivo per fatture finali, conguagli e riconciliazioni.
--   La chiusura del BA e' un'operazione separata.
--
-- Parametri:
--   p_cliente_id      -> ID del cliente da cessare (NOT NULL, > 0)
--   p_data_cessazione -> Data di cessazione (NOT NULL, >= data_attivazione)
--
-- Ritorna:
--   ID del cliente cessato
-- ------------------------------------------------------------

    ----------------------------------------------------------------
    -- 1) Guard: parametri non nulli e validi
    ----------------------------------------------------------------
    IF p_cliente_id IS NULL OR p_cliente_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_disdetta_cliente',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'parametro', 'p_cliente_id',
                'valore', p_cliente_id
            ),
            NULL::uuid,
            'p_cliente_id deve essere NOT NULL e > 0'
        );
    END IF;

    IF p_data_cessazione IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_disdetta_cliente',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'parametro', 'p_data_cessazione'
            ),
            NULL::uuid,
            'p_data_cessazione deve essere NOT NULL'
        );
    END IF;

    ----------------------------------------------------------------
    -- 2) Recupero ID stati cliente AT e CH
    ----------------------------------------------------------------
    SELECT sc.id INTO v_stato_attivo_id
      FROM config.stati_cliente sc
     WHERE sc.codice_interno = v_codice_attivo;

    SELECT sc.id INTO v_stato_chiuso_id
      FROM config.stati_cliente sc
     WHERE sc.codice_interno = v_codice_chiuso;

    IF v_stato_attivo_id IS NULL OR v_stato_chiuso_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_disdetta_cliente',
            'E_CONFIG_MANCANTE',
            jsonb_build_object(
                'detail', 'Stati cliente AT e/o CH non trovati in config.stati_cliente'
            ),
            NULL::uuid,
            'AT/CH'
        );
    END IF;

    ----------------------------------------------------------------
    -- 3) Leggo il cliente con lock (evita race condition)
    ----------------------------------------------------------------
    SELECT c.stato_cliente_id, c.data_attivazione
      INTO v_stato_corrente_id, v_data_attivazione
      FROM anagrafiche.clienti c
     WHERE c.id = p_cliente_id
       FOR UPDATE;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_disdetta_cliente',
            'E_CLIENTE_NON_TROVATO',
            jsonb_build_object('p_cliente_id', p_cliente_id),
            NULL::uuid,
            p_cliente_id::text
        );
    END IF;

    ----------------------------------------------------------------
    -- 4) Guard: il cliente deve essere in stato ATTIVO (AT)
    ----------------------------------------------------------------
    IF v_stato_corrente_id <> v_stato_attivo_id THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_disdetta_cliente',
            'E_CLIENTE_NON_ATTIVO',
            jsonb_build_object(
                'p_cliente_id', p_cliente_id,
                'stato_corrente_id', v_stato_corrente_id,
                'stato_atteso', 'AT'
            ),
            NULL::uuid,
            p_cliente_id::text, v_stato_corrente_id::text
        );
    END IF;

    ----------------------------------------------------------------
    -- 5) Guard: data cessazione >= data attivazione
    ----------------------------------------------------------------
    IF v_data_attivazione IS NOT NULL
       AND p_data_cessazione < v_data_attivazione
    THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_disdetta_cliente',
            'E_DATA_CESSAZIONE_INVALIDA',
            jsonb_build_object(
                'p_cliente_id', p_cliente_id,
                'p_data_cessazione', p_data_cessazione,
                'data_attivazione', v_data_attivazione
            ),
            NULL::uuid,
            p_data_cessazione::text, v_data_attivazione::text
        );
    END IF;

    ----------------------------------------------------------------
    -- 6) Eseguo disdetta: data_chiusura + stato CH
    --    I trigger cascata sulla tabella clienti gestiscono:
    --      - trgfn_clienti_set_periodo -> [data_attivazione, data_chiusura)
    --      - trgfn_clienti_sync_stato_pdp -> PDP torna DISPONIBILE
    --      - trgfn_storico_generic -> storicizzazione
    --      - trgfn_audit_data_user_generic -> audit
    ----------------------------------------------------------------
    UPDATE anagrafiche.clienti c
       SET data_chiusura    = p_data_cessazione,
           stato_cliente_id = v_stato_chiuso_id
     WHERE c.id = p_cliente_id;

    RETURN p_cliente_id;
END;
$function$

COMMENT ON FUNCTION script.fn_disdetta_cliente(p_cliente_id bigint, p_data_cessazione date)
IS 'Cessazione cliente senza subentro (disdetta).
Chiude il cliente con data_chiusura e stato CH.
I trigger cascata aggiornano periodo, PDP (DISPONIBILE) e storico.
Il billing_account resta attivo (policy: chiusura BA separata).';
```

---
{% include-markdown "signature-core.md" %}
