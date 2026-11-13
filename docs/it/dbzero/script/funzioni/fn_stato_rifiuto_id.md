{% include-markdown "it/dbzero/script/manual/fn_stato_rifiuto_id.md" %}
# ⚙️ Funzione `fn_stato_rifiuto_id`

```sql
CREATE FUNCTION fn_stato_rifiuto_id(p_testata regclass)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_stato_rifiuto_id(p_testata regclass)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- Scopo: l'id dello stato di rifiuto della testata, dal suo
    --   vocabolario (colonna rifiuto = true). La logica e' del
    --   lettore comune:
    --   - testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA;
    --   - vocabolario senza la colonna rifiuto: il documento
    --     non ha quello stato, NULL;
    --   - nessuno stato dichiarato: NULL.
    -- =========================================================
    RETURN script.fn_stato_per_colonna_id(p_testata, 'rifiuto', 'script.fn_stato_rifiuto_id');
END;
$function$

COMMENT ON FUNCTION script.fn_stato_rifiuto_id(p_testata regclass)
IS 'BB del modello del documento: l''id dello stato di RIFIUTO del cliente di una testata, letto dal suo vocabolario degli stati (colonna rifiuto = true; la mappa e'' script.fn_doc_stato_modello). Unica sede da cui leggerlo: nessuno scrive ''RIFIUTATA'' / ''RIFIUTATO'' per dire «lo stato di rifiuto». Al massimo uno per vocabolario, ed e'' attivo (uq_<vocabolario>_rifiuto, chk_<vocabolario>_rifiuto_attivo). NULL se il vocabolario non ha la colonna (i documenti che il cliente non rifiuta: tutti tranne preventivo e offerta) o non ne dichiara; testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA. La logica e'' di script.fn_stato_per_colonna_id, comune ai gemelli script.fn_stato_emissione_id, script.fn_stato_abortito_id, script.fn_stato_cessazione_id, script.fn_stato_accettazione_id, script.fn_stato_scadenza_id; il codice si legge con script.fn_doc_stato_codice. Chi ha gia'' in mano la riga del vocabolario legge la colonna (vendite.trgfn_offerte_commerciali_guard_transizione); il backend la legge al posto del letterale per l''esito negativo del cliente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
