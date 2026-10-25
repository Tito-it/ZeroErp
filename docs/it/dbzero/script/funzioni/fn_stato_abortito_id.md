{% include-markdown "it/dbzero/script/manual/fn_stato_abortito_id.md" %}
# ⚙️ Funzione `fn_stato_abortito_id`

```sql
CREATE FUNCTION fn_stato_abortito_id(p_testata regclass)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_stato_abortito_id(p_testata regclass)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- Il vocabolario e l'id di uno stato di una qualunque testata
    -- della mappa: bigint in tutti, nessuna colonna comune a cui
    -- ancorarli.
    v_vocabolario regclass;
    v_id          bigint;
BEGIN
    -- =========================================================
    -- Scopo: l'id dello stato d'annullo della testata, dal suo
    --   vocabolario (is_abortito = true).
    -- Regole:
    --   - testata fuori mappa: il chiamante e' rotto,
    --     E_SCRIPT_CHIAMATA_NON_VALIDA;
    --   - nessuno stato dichiarato: NULL (al massimo uno lo
    --     garantisce l'indice unico parziale, ed e' attivo).
    -- =========================================================
    SELECT m.vocabolario
      INTO v_vocabolario
      FROM script.fn_doc_stato_modello(p_testata) m;

    IF v_vocabolario IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_stato_abortito_id', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('testata', p_testata::text),
            NULL::uuid,
            'script.fn_stato_abortito_id',
            'p_testata: una testata della mappa del modello (script.fn_doc_stato_modello)');
    END IF;

    EXECUTE format('SELECT s.id FROM %s s WHERE s.is_abortito', v_vocabolario)
       INTO v_id;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION script.fn_stato_abortito_id(p_testata regclass)
IS 'BB del modello del documento: l''id dello stato d''ANNULLO di una testata, letto dal suo vocabolario degli stati (is_abortito = true; la mappa e'' script.fn_doc_stato_modello). Unica sede da cui leggerlo: nessuno scrive ''ANNULLATO'' per dire «lo stato d''annullo» (guida del modello §8). Al massimo uno per vocabolario, ed e'' attivo (uq_<vocabolario>_abortito, chk_<vocabolario>_abortito_attivo). NULL se il vocabolario non ne dichiara; testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA. Gemello di script.fn_stato_emissione_id; il codice per i verbi che lo prendono si legge con script.fn_doc_stato_codice. Consumatori: vendite.fn_annulla_ordine, vendite.fn_annulla_preventivo, vendite.fn_cambia_stato_ddt (l''annullo della bolla emessa). Brief: brief-modello-documento-vendita §9 (Z-3 di Tid, 2026-10-25).';
```

</div>

---
{% include-markdown "signature-core.md" %}
