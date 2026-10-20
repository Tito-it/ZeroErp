{% include-markdown "it/dbzero/script/manual/fn_subentro_cliente.md" %}
# ⚙️ Funzione `fn_subentro_cliente`

```sql
CREATE FUNCTION fn_subentro_cliente(p_pdp_id bigint, p_data_attivazione date)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_subentro_cliente(p_pdp_id bigint, p_data_attivazione date)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    --v_cliente_precedente_id bigint;
    --v_stato_chiuso_id       integer;
    --v_codice_chiuso         text := 'CH';
    v_cliente_precedente_id anagrafiche.clienti.id%TYPE;
    v_stato_chiuso_id       config.stati_cliente.id%TYPE;
    v_codice_chiuso         config.stati_cliente.codice_interno%TYPE := 'CH';  

BEGIN
-- ------------------------------------------------------------
-- Funzione: script.fn_subentro_cliente
--
-- Scopo:
--   - Dato un PDP e una data di attivazione del nuovo cliente,
--     chiude (se esiste) il cliente precedente su quel PDP
--     per evitare overlap del periodo commerciale.
--
--   - Logica:
--       * Cerca il cliente più recente su p_pdp_id con:
--           - stato_cliente.codice_interno <> 'AN'
--           - data_attivazione NOT NULL
--           - data_attivazione < p_data_attivazione
--           - data_chiusura IS NULL oppure >= p_data_attivazione
--       * Se trovato:
--           - imposta data_chiusura = p_data_attivazione - 1 giorno
--           - imposta stato_cliente a 'CH'
--         (il trigger trg_clienti_set_periodo normalizzerà periodo)
--
--   - Ritorna:
--       * id del cliente chiuso
--       * NULL se nessun cliente da chiudere (primo cliente sul PDP)
--
-- NOTE:
--   - Non crea la nuova istanza né il nuovo cliente: questo
--     viene fatto dal frontend / servizio applicativo subito dopo.
--   - Va tipicamente chiamata in transazione:
--       1) SELECT script.fn_subentro_cliente(...)
--       2) INSERT nuovo cliente sullo stesso PDP
--     in modo da rispettare il vincolo ex_clienti_no_overlap_stesso_pdp.
-- ------------------------------------------------------------



    ----------------------------------------------------------------
    -- Validazioni minime parametri
    ----------------------------------------------------------------
    IF p_pdp_id IS NULL THEN

         PERFORM script.fn_log_and_raise_error(
                          'database',
                          'script.fn_subentro_cliente',
                          'E_ERRORE_PARAMETRI',
                          jsonb_build_object(
                              'p_pdp_id non può essere NULL', 
                              'indicare un valore valido'  
                          ),
                          NULL,
                          'Non è stato fornito un valore per pdp_id'
                      );
    END IF;

    IF p_data_attivazione IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
                          'database',
                          'script.fn_subentro_cliente',
                          'E_ERRORE_PARAMETRI',
                          jsonb_build_object(
                              'fn_subentro_cliente: p_data_attivazione non può essere NULL', 
                              'indicare un valore valido'  
                          ),
                          NULL,
                          'Non è stato fornito un valore per data_attivazione'
                      );
    END IF;

    ----------------------------------------------------------------
    -- Recupero ID stato_cliente "CH" (Chiuso)
    ----------------------------------------------------------------
    SELECT sc.id
      INTO v_stato_chiuso_id
    FROM config.stati_cliente sc
    WHERE sc.codice_interno = v_codice_chiuso
    LIMIT 1;

    IF v_stato_chiuso_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
                          'database',
                          'script.fn_subentro_cliente',
                          'E_CONFIG_MANCANTE',
                          jsonb_build_object(
                                  'codice id_cliente',
                                  v_codice_chiuso
                          ),
                          NULL,
                          'stato_cliente con id_cliente' || v_codice_chiuso::text || ' non trovato'
                      );               
    END IF;

    ----------------------------------------------------------------
    -- Seleziono il cliente precedente da chiudere:
    --   - stesso PDP
    --   - non ANNULLATO
    --   - con data_attivazione < nuova data attivazione
    --   - con periodo ancora “aperto” rispetto alla nuova data
    --   - prendo il più recente (data_attivazione DESC, id DESC)
    ----------------------------------------------------------------
    SELECT c.id
      INTO v_cliente_precedente_id
    FROM anagrafiche.clienti c
    JOIN config.stati_cliente sc
         ON sc.id = c.stato_cliente_id
    WHERE c.pdp_id = p_pdp_id
      AND sc.codice_interno <> 'AN'
      AND c.data_attivazione IS NOT NULL
      AND c.data_attivazione < p_data_attivazione
      AND (c.data_chiusura IS NULL OR c.data_chiusura >= p_data_attivazione)
    ORDER BY c.data_attivazione DESC,
             c.id DESC
    FOR UPDATE
    LIMIT 1;

    ----------------------------------------------------------------
    -- Se non c'è nessun cliente da chiudere → primo cliente sul PDP
    ----------------------------------------------------------------
    IF v_cliente_precedente_id IS NULL THEN
        RETURN NULL;
    END IF;

    ----------------------------------------------------------------
    -- Chiusura del cliente precedente:
    --   - data_chiusura = p_data_attivazione - 1 giorno
    --   - stato_cliente  = CH
    --
    -- I trigger sulla tabella clienti si occupano di:
    --   - normalizzare periodo (trg_clienti_set_periodo)
    --   - aggiornare storico, stato PDP, ecc.
    ----------------------------------------------------------------
    UPDATE anagrafiche.clienti c
       SET data_chiusura   = p_data_attivazione - INTERVAL '1 day',
           stato_cliente_id = v_stato_chiuso_id
     WHERE c.id = v_cliente_precedente_id;

    RETURN v_cliente_precedente_id;
END;
$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
