{% include-markdown "it/dbzero/script/manual/fn_stato_emissione_id.md" %}
# ⚙️ Funzione `fn_stato_emissione_id`

```sql
CREATE FUNCTION fn_stato_emissione_id(p_testata regclass)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_stato_emissione_id(p_testata regclass)
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
    -- Scopo: l'id dello stato di emissione della testata, dal
    --   suo vocabolario (colonna emissione = true).
    -- Regole:
    --   - testata fuori mappa: il chiamante e' rotto,
    --     E_SCRIPT_CHIAMATA_NON_VALIDA;
    --   - vocabolario senza la colonna emissione: il documento
    --     non si emette, NULL;
    --   - nessuno stato dichiarato: NULL (al massimo uno lo
    --     garantisce l'indice unico parziale).
    -- =========================================================
    SELECT m.vocabolario
      INTO v_vocabolario
      FROM script.fn_doc_stato_modello(p_testata) m;

    IF v_vocabolario IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_stato_emissione_id', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('testata', p_testata::text),
            NULL::uuid,
            'script.fn_stato_emissione_id',
            'p_testata: una testata della mappa del modello (script.fn_doc_stato_modello)');
    END IF;

    IF NOT EXISTS (SELECT 1
                     FROM pg_catalog.pg_attribute a
                    WHERE a.attrelid = v_vocabolario
                      AND a.attname  = 'emissione'
                      AND a.attnum   > 0
                      AND NOT a.attisdropped) THEN
        RETURN NULL;
    END IF;

    EXECUTE format('SELECT s.id FROM %s s WHERE s.emissione', v_vocabolario)
       INTO v_id;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION script.fn_stato_emissione_id(p_testata regclass)
IS 'BB del modello del documento: l''id dello stato di EMISSIONE di una testata, letto dal suo vocabolario degli stati (colonna emissione = true; la mappa e'' script.fn_doc_stato_modello). Unica sede da cui leggerlo: nessuno scrive ''EMESSO'' per dire «lo stato a cui si arriva solo da Emetti» (M-2). NULL se il documento non si emette (vocabolario senza la colonna: reso, commessa, fattura) o se il vocabolario non ne dichiara; testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA. Gemello di script.fn_stato_iniziale_id, ma riceve la testata. Consumatori: il backend (il cambio stato generico rifiuta l''emissione; «Emetti» ne legge il codice con script.fn_doc_stato_codice), script.fn_doc_azione_passaggio, vendite.fn_cambia_stato_ddt, vendite.trgfn_preventivi_guard_transizione (le righe all''emissione). Brief: brief-modello-documento-vendita §8 e §8.11 (Tid 2026-10-25).';
```

</div>

---
{% include-markdown "signature-core.md" %}
