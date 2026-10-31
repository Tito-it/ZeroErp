{% include-markdown "it/dbzero/script/manual/fn_stato_accettazione_id.md" %}
# ⚙️ Funzione `fn_stato_accettazione_id`

```sql
CREATE FUNCTION fn_stato_accettazione_id(p_testata regclass)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_stato_accettazione_id(p_testata regclass)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- Scopo: l'id dello stato di accettazione della testata, dal suo
    --   vocabolario (colonna accettazione = true). La logica e' del
    --   lettore comune:
    --   - testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA;
    --   - vocabolario senza la colonna accettazione: il documento
    --     non ha quello stato, NULL;
    --   - nessuno stato dichiarato: NULL.
    -- =========================================================
    RETURN script.fn_stato_per_colonna_id(p_testata, 'accettazione', 'script.fn_stato_accettazione_id');
END;
$function$

COMMENT ON FUNCTION script.fn_stato_accettazione_id(p_testata regclass)
IS 'BB del modello del documento: l''id dello stato di ACCETTAZIONE di una testata, letto dal suo vocabolario degli stati (colonna accettazione = true; la mappa e'' script.fn_doc_stato_modello). Unica sede da cui leggerlo: nessuno scrive ''ACCETTATO'' / ''ACCETTATA'' per dire «lo stato di accettazione». Al massimo uno per vocabolario, ed e'' attivo (uq_<vocabolario>_accettazione, chk_<vocabolario>_accettazione_attivo). NULL se il vocabolario non ha la colonna (i documenti che il cliente non accetta: tutti tranne preventivo e offerta) o non ne dichiara; testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA. La logica e'' di script.fn_stato_per_colonna_id, comune ai gemelli script.fn_stato_emissione_id, script.fn_stato_abortito_id, script.fn_stato_cessazione_id; il codice si legge con script.fn_doc_stato_codice. Consumatori: vendite.fn_list_preventivi_da_pushare, vendite.fn_push_preventivo_a_ordine; chi ha gia'' in mano la riga del vocabolario legge la colonna (le capability di preventivo e offerta, vendite.fn_push_offerta_a_contratto, vendite.fn_genera_ordine_da_offerta); il backend al posto dei letterali di preventivi_service e StatoOfferta. Brief: brief-modello-documento-vendita §17 (Tid, 2026-10-31).';
```

</div>

---
{% include-markdown "signature-core.md" %}
