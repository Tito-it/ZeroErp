{% include-markdown "it/dbzero/script/manual/fn_disdetta_cliente.md" %}
# ⚙️ Funzione `fn_disdetta_cliente`

```sql
CREATE FUNCTION fn_disdetta_cliente(p_cliente_id bigint, p_data_cessazione date)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_disdetta_cliente(p_cliente_id bigint, p_data_cessazione date)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_stato_chiuso_id   config.stati_cliente.id%TYPE;
    v_codice_chiuso     config.stati_cliente.codice_interno%TYPE := 'CH';
    v_data_attivazione  anagrafiche.clienti.data_attivazione%TYPE;
BEGIN
-- ------------------------------------------------------------
-- Funzione: script.fn_disdetta_cliente
--
-- Scopo:
--   Cessazione di un cliente senza subentro (disdetta).
--   Chiude il cliente impostando data_chiusura e stato CH.
--   Da quale stato si puo' chiudere lo decide il grafo
--   config.transizioni_stati_cliente, applicato dal guard
--   anagrafiche.trgfn_clienti_guard_stato_date (rev 2026-10-14,
--   brief-db-cliente-manuale-uno-per-soggetto-e-utility, C-6):
--   AT, SF, SC si chiudono; un chiuso, un annullato o un
--   pre-contrattuale no.
--   I trigger cascata gestiscono:
--     - trgfn_clienti_set_periodo -> aggiorna periodo
--     - trgfn_clienti_sync_stato_pdp -> PDP libero se nessuno lo occupa
--     - trgfn_storico_generic -> storicizzazione
--     - trgfn_audit_data_user_generic -> audit
--
-- Policy BA:
--   Il billing_account NON viene toccato dalla disdetta.
--   Resta per fatture finali e conguagli; non si riattiva
--   (C-5: chi torna apre una catena nuova).
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
    -- 2) Stato CH
    ----------------------------------------------------------------
    SELECT sc.id INTO v_stato_chiuso_id
      FROM config.stati_cliente sc
     WHERE sc.codice_interno = v_codice_chiuso;

    IF v_stato_chiuso_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_disdetta_cliente',
            'E_CONFIG_MANCANTE',
            jsonb_build_object(
                'detail', 'Stato cliente CH non trovato in config.stati_cliente'
            ),
            NULL::uuid,
            'CH'
        );
    END IF;

    ----------------------------------------------------------------
    -- 3) Leggo il cliente con lock (evita race condition)
    ----------------------------------------------------------------
    SELECT c.data_attivazione
      INTO v_data_attivazione
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
    -- 4) Guard: data cessazione >= data attivazione
    ----------------------------------------------------------------
    IF v_data_attivazione IS NOT NULL
       AND p_data_cessazione < v_data_attivazione
    THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_disdetta_cliente',
            'E_DATA_CESSAZIONE_INVALIDA',
            jsonb_build_object(
                'campo', 'data_cessazione',
                'p_cliente_id', p_cliente_id,
                'p_data_cessazione', p_data_cessazione,
                'data_attivazione', v_data_attivazione
            ),
            NULL::uuid,
            p_data_cessazione::text, v_data_attivazione::text
        );
    END IF;

    ----------------------------------------------------------------
    -- 5) Eseguo disdetta: data_chiusura + stato CH. Il grafo
    --    (da quale stato) lo applica il guard sulla tabella.
    ----------------------------------------------------------------
    UPDATE anagrafiche.clienti c
       SET data_chiusura    = p_data_cessazione,
           stato_cliente_id = v_stato_chiuso_id
     WHERE c.id = p_cliente_id;

    RETURN p_cliente_id;
END;
$function$

COMMENT ON FUNCTION script.fn_disdetta_cliente(p_cliente_id bigint, p_data_cessazione date)
IS 'Cessazione cliente senza subentro (disdetta): data_chiusura e stato CH. Da quale stato si chiude lo decide il grafo config.transizioni_stati_cliente (guard anagrafiche.trgfn_clienti_guard_stato_date: AT, SF, SC; rev 2026-10-14, prima solo AT). I trigger aggiornano periodo, PDP e storico. Il billing account resta per fatture finali e conguagli e non si riattiva: chi torna apre una catena nuova (C-5). Brief: brief-db-cliente-manuale-uno-per-soggetto-e-utility.';
```

</div>

---
{% include-markdown "signature-core.md" %}
