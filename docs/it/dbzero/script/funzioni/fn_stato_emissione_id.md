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
BEGIN
    -- =========================================================
    -- Scopo: l'id dello stato di emissione della testata, dal
    --   suo vocabolario (colonna emissione = true). La logica
    --   e' del lettore comune (rev 2026-10-31, 20261031-07):
    --   - testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA;
    --   - vocabolario senza la colonna emissione: il documento
    --     non si emette, NULL;
    --   - nessuno stato dichiarato: NULL.
    -- =========================================================
    RETURN script.fn_stato_per_colonna_id(p_testata, 'emissione', 'script.fn_stato_emissione_id');
END;
$function$

COMMENT ON FUNCTION script.fn_stato_emissione_id(p_testata regclass)
IS 'BB del modello del documento: l''id dello stato di EMISSIONE di una testata, letto dal suo vocabolario degli stati (colonna emissione = true; la mappa e'' script.fn_doc_stato_modello). Unica sede da cui leggerlo: nessuno scrive ''EMESSO'' per dire «lo stato a cui si arriva solo da Emetti» (M-2). NULL se il documento non si emette (vocabolario senza la colonna: reso, commessa, fattura) o se il vocabolario non ne dichiara; testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA. La logica e'' di script.fn_stato_per_colonna_id (dal 2026-10-31), comune ai lettori gemelli: script.fn_stato_abortito_id, script.fn_stato_cessazione_id, script.fn_stato_accettazione_id; il codice si legge con script.fn_doc_stato_codice. Consumatori: il backend (il cambio stato generico rifiuta l''emissione; «Emetti» ne legge il codice), script.fn_doc_azione_passaggio, vendite.fn_cambia_stato_ddt, vendite.fn_cessa_contratti_scaduti, vendite.fn_offerta_proietta_stato_revisione, vendite.trgfn_preventivi_guard_transizione (le righe all''emissione). Brief: brief-modello-documento-vendita §8, §8.11 (Tid 2026-10-25) e §17.';
```

</div>

---
{% include-markdown "signature-core.md" %}
