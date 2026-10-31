{% include-markdown "it/dbzero/script/manual/fn_stato_scadenza_id.md" %}
# ⚙️ Funzione `fn_stato_scadenza_id`

```sql
CREATE FUNCTION fn_stato_scadenza_id(p_testata regclass)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_stato_scadenza_id(p_testata regclass)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- Scopo: l'id dello stato di scadenza della testata, dal suo
    --   vocabolario (colonna scadenza = true). La logica e' del
    --   lettore comune:
    --   - testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA;
    --   - vocabolario senza la colonna scadenza: il documento
    --     non ha quello stato, NULL;
    --   - nessuno stato dichiarato: NULL.
    -- =========================================================
    RETURN script.fn_stato_per_colonna_id(p_testata, 'scadenza', 'script.fn_stato_scadenza_id');
END;
$function$

COMMENT ON FUNCTION script.fn_stato_scadenza_id(p_testata regclass)
IS 'BB del modello del documento: l''id dello stato di SCADENZA di una testata, letto dal suo vocabolario degli stati (colonna scadenza = true; la mappa e'' script.fn_doc_stato_modello): lo stato in cui il documento arriva quando la sua validita'' e'' finita senza risposta del cliente. Unica sede da cui leggerlo: nessuno scrive ''SCADUTO'' per dire «lo stato di scadenza». Al massimo uno per vocabolario, ed e'' attivo (uq_<vocabolario>_scadenza, chk_<vocabolario>_scadenza_attivo). NULL se il vocabolario non ha la colonna (tutti i documenti tranne il preventivo) o non ne dichiara; testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA. La logica e'' di script.fn_stato_per_colonna_id, comune ai gemelli script.fn_stato_emissione_id, script.fn_stato_abortito_id, script.fn_stato_accettazione_id, script.fn_stato_cessazione_id; il codice si legge con script.fn_doc_stato_codice. Consumatori: vendite.fn_chiudi_preventivi_scaduti; vendite.fn_crea_revisione_preventivo e script.fn_available_actions_preventivo leggono la colonna scadenza dalla riga del vocabolario che hanno gia''. Brief: brief-db-scadenza-preventivi §8.1 (D-1, Tid 2026-10-31).';
```

</div>

---
{% include-markdown "signature-core.md" %}
