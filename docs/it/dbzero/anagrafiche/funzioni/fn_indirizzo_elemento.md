{% include-markdown "it/dbzero/anagrafiche/manual/fn_indirizzo_elemento.md" %}
# ⚙️ Funzione `fn_indirizzo_elemento`

```sql
CREATE FUNCTION fn_indirizzo_elemento(p_el jsonb, p_chi text, p_contesto jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_indirizzo_elemento(p_el jsonb, p_chi text, p_contesto jsonb DEFAULT '{}'::jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_ctx      jsonb := COALESCE(p_contesto, '{}'::jsonb);
    v_tipo_id  config.tipi_indirizzi.id%TYPE;
    v_da_cod   config.tipi_indirizzi.id%TYPE;
    v_id_txt   text;   -- l'id come arriva nel jsonb, prima di verificarlo
    v_codice   text;   -- il codice come arriva: piu' lungo della colonna e' «non trovato», non un errore di lunghezza
    -- Le chiavi di un indirizzo: le colonne della riga, piu'
    -- quelle di una via da risolvere (fn_create_indirizzo).
    c_ammesse CONSTANT text[] := ARRAY[
        'tipo_indirizzo_id', 'tipo_indirizzo_codice_interno',
        'indirizzo_dettaglio_id', 'indirizzo_libero',
        'stato_id', 'comune_id', 'codice_postale_id',
        'administrative_area', 'locality', 'sublocality', 'postal_code',
        'stradario_id', 'toponomastica_id', 'descrizione_via',
        'civico', 'estensione_civico', 'palazzina', 'scala', 'piano', 'interno'];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Leggere un indirizzo in jsonb: un oggetto, solo chiavi
    --   ammesse, il tipo risolto (tipo_indirizzo_id, oppure
    --   tipo_indirizzo_codice_interno = codice interno). Ritorna
    --   l'elemento con tipo_indirizzo_id e senza il codice.
    --   p_chi: la madre che chiama (per il log); p_contesto:
    --   le chiavi che la madre aggiunge al contesto dei rifiuti.
    --
    -- Regole:
    --   - il tipo per id deve esistere; con id e codice insieme,
    --     i due devono dire lo stesso tipo (E_TIPO_INDIRIZZO_DISCORDE);
    --   - non giudica la completezza ne' la forma: e' il guard
    --     della tabella (trgfn_indirizzi_guard_forma_libera).
    -- =========================================================
    IF jsonb_typeof(p_el) IS DISTINCT FROM 'object' THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', p_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            v_ctx || jsonb_build_object('tipo_elemento', jsonb_typeof(p_el)),
            NULL::uuid,
            p_chi,
            'un indirizzo non e'' un oggetto');
    END IF;

    PERFORM script.fn_guard_campi_ammessi(p_el, c_ammesse, 'anagrafiche', p_chi, v_ctx);

    -- Il tipo (S49, 2026-11-24): l'id si verifica, non si prende
    -- com'e'; col codice insieme devono dire lo stesso tipo.
    v_id_txt := NULLIF(btrim(p_el ->> 'tipo_indirizzo_id'), '');
    v_codice := NULLIF(upper(btrim(p_el ->> 'tipo_indirizzo_codice_interno')), '');

    IF v_id_txt IS NOT NULL THEN
        -- Il cast solo dopo la forma: un AND non garantisce l'ordine.
        IF v_id_txt ~ '^[0-9]{1,10}$' THEN
            IF v_id_txt::bigint <= 2147483647 THEN
                SELECT ti.id INTO v_tipo_id
                  FROM config.tipi_indirizzi ti
                 WHERE ti.id = v_id_txt::integer;
            END IF;
        END IF;
        IF v_tipo_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'anagrafiche', p_chi, 'E_TIPO_INDIRIZZO_NON_TROVATO',
                v_ctx || jsonb_build_object(
                    'campo', 'tipo_indirizzo_id',
                    'tipo_indirizzo_id', v_id_txt),
                NULL::uuid,
                v_id_txt);
        END IF;
    END IF;

    IF v_codice IS NOT NULL THEN
        SELECT ti.id INTO v_da_cod
          FROM config.tipi_indirizzi ti
         WHERE ti.codice_interno = v_codice;
        IF v_tipo_id IS NULL THEN
            v_tipo_id := v_da_cod;
        ELSIF v_da_cod IS DISTINCT FROM v_tipo_id THEN
            PERFORM script.fn_log_and_raise_error(
                'anagrafiche', p_chi, 'E_TIPO_INDIRIZZO_DISCORDE',
                v_ctx || jsonb_build_object(
                    'campo', 'tipo_indirizzo_codice_interno',
                    'tipo_indirizzo_id', v_tipo_id,
                    'tipo_indirizzo_codice_interno', v_codice),
                NULL::uuid,
                v_tipo_id::text, v_codice);
        END IF;
    END IF;

    IF v_tipo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', p_chi, 'E_TIPO_INDIRIZZO_NON_TROVATO',
            v_ctx || jsonb_build_object(
                'campo', 'tipo_indirizzo_codice_interno',
                'tipo_indirizzo_codice_interno', p_el ->> 'tipo_indirizzo_codice_interno'),
            NULL::uuid,
            COALESCE(v_codice, '-'));
    END IF;

    RETURN (p_el - 'tipo_indirizzo_codice_interno')
           || jsonb_build_object('tipo_indirizzo_id', v_tipo_id);
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_indirizzo_elemento(p_el jsonb, p_chi text, p_contesto jsonb)
IS 'BB (2026-10-18): legge un indirizzo in jsonb per le madri degli indirizzi. Un oggetto (E_SCRIPT_CHIAMATA_NON_VALIDA), solo chiavi ammesse (E_CAMPO_NON_AMMESSO: le colonne della riga, tipo_indirizzo_codice_interno e i campi di una via da risolvere), il tipo risolto da tipo_indirizzo_id o tipo_indirizzo_codice_interno (codice interno): un id che non esiste o non e'' un numero, o un codice che non c''e'', E_TIPO_INDIRIZZO_NON_TROVATO col campo; id e codice che dicono due tipi, E_TIPO_INDIRIZZO_DISCORDE. Ritorna l''elemento con tipo_indirizzo_id e senza il codice. p_chi: la madre che chiama; p_contesto: chiavi aggiunte al contesto dei rifiuti. Non giudica completezza ne'' forma: e'' anagrafiche.trgfn_indirizzi_guard_forma_libera. Chiamanti: anagrafiche.fn_crea_indirizzi_ruolo e fn_crea_indirizzo_soggetto (una grammatica sola, D-4 di Tid, richiesta BE in brief-db-processi-accensione-per-ambiente §6.11).';
```

</div>

---
{% include-markdown "signature-core.md" %}
