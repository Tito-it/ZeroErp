{% include-markdown "it/dbzero/anagrafiche/manual/fn_indirizzo_elemento.md" %}
# ⚙️ Funzione `fn_indirizzo_elemento`

```sql
CREATE FUNCTION fn_indirizzo_elemento(p_el jsonb, p_chi text, p_contesto jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_indirizzo_elemento(p_el jsonb, p_chi text, p_contesto jsonb DEFAULT '{}'::jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_ctx      jsonb := COALESCE(p_contesto, '{}'::jsonb);
    v_estranea text;
    v_tipo_id  config.tipi_indirizzi.id%TYPE;
    -- Le chiavi di un indirizzo: le colonne della riga, piu'
    -- quelle di una via da risolvere (fn_create_indirizzo).
    c_ammesse CONSTANT text[] := ARRAY[
        'tipo_indirizzo_id', 'tipo_indirizzo_codice',
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
    --   tipo_indirizzo_codice = codice interno). Ritorna
    --   l'elemento con tipo_indirizzo_id e senza il codice.
    --   p_chi: la madre che chiama (per il log); p_contesto:
    --   le chiavi che la madre aggiunge al contesto dei rifiuti.
    --
    -- Regole:
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

    v_estranea := script.fn_prima_chiave_estranea(p_el, c_ammesse);
    IF v_estranea IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', p_chi, 'E_CAMPO_NON_AMMESSO',
            v_ctx || jsonb_build_object('campo', v_estranea),
            NULL::uuid,
            v_estranea);
    END IF;

    v_tipo_id := (p_el ->> 'tipo_indirizzo_id')::integer;
    IF v_tipo_id IS NULL AND NULLIF(btrim(p_el ->> 'tipo_indirizzo_codice'), '') IS NOT NULL THEN
        SELECT ti.id
          INTO v_tipo_id
          FROM config.tipi_indirizzi ti
         WHERE ti.codice_interno = upper(btrim(p_el ->> 'tipo_indirizzo_codice'));
    END IF;

    IF v_tipo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', p_chi, 'E_TIPO_INDIRIZZO_NON_TROVATO',
            v_ctx || jsonb_build_object(
                'campo', 'tipo_indirizzo_codice',
                'tipo_indirizzo_codice', p_el ->> 'tipo_indirizzo_codice'),
            NULL::uuid,
            COALESCE(NULLIF(btrim(p_el ->> 'tipo_indirizzo_codice'), ''), '-'));
    END IF;

    RETURN (p_el - 'tipo_indirizzo_codice')
           || jsonb_build_object('tipo_indirizzo_id', v_tipo_id);
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_indirizzo_elemento(p_el jsonb, p_chi text, p_contesto jsonb)
IS 'BB (2026-10-18): legge un indirizzo in jsonb per le madri degli indirizzi. Un oggetto (E_SCRIPT_CHIAMATA_NON_VALIDA), solo chiavi ammesse (E_CAMPO_NON_AMMESSO: le colonne della riga, tipo_indirizzo_codice e i campi di una via da risolvere), il tipo risolto da tipo_indirizzo_id o tipo_indirizzo_codice (codice interno; E_TIPO_INDIRIZZO_NON_TROVATO). Ritorna l''elemento con tipo_indirizzo_id e senza il codice. p_chi: la madre che chiama; p_contesto: chiavi aggiunte al contesto dei rifiuti. Non giudica completezza ne'' forma: e'' anagrafiche.trgfn_indirizzi_guard_forma_libera. Chiamanti: anagrafiche.fn_crea_indirizzi_ruolo e fn_crea_indirizzo_soggetto (una grammatica sola, D-4 di Tid, richiesta BE in brief-db-processi-accensione-per-ambiente §6.11).';
```

---
{% include-markdown "signature-core.md" %}
