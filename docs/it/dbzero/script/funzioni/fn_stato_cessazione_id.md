{% include-markdown "it/dbzero/script/manual/fn_stato_cessazione_id.md" %}
# ⚙️ Funzione `fn_stato_cessazione_id`

```sql
CREATE FUNCTION fn_stato_cessazione_id(p_testata regclass)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_stato_cessazione_id(p_testata regclass)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- Scopo: l'id dello stato di cessazione della testata, dal suo
    --   vocabolario (colonna cessazione = true). La logica e' del
    --   lettore comune:
    --   - testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA;
    --   - vocabolario senza la colonna cessazione: il documento
    --     non ha quello stato, NULL;
    --   - nessuno stato dichiarato: NULL.
    -- =========================================================
    RETURN script.fn_stato_per_colonna_id(p_testata, 'cessazione', 'script.fn_stato_cessazione_id');
END;
$function$

COMMENT ON FUNCTION script.fn_stato_cessazione_id(p_testata regclass)
IS 'BB del modello del documento: l''id dello stato di CESSAZIONE di una testata, letto dal suo vocabolario degli stati (colonna cessazione = true; la mappa e'' script.fn_doc_stato_modello). Unica sede da cui leggerlo: nessuno scrive ''CESSATO'' per dire «lo stato di cessazione». Al massimo uno per vocabolario, ed e'' attivo (uq_<vocabolario>_cessazione, chk_<vocabolario>_cessazione_attivo). NULL se il vocabolario non ha la colonna (i documenti che non cessano: tutti tranne il contratto) o non ne dichiara; testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA. La logica e'' di script.fn_stato_per_colonna_id, comune ai gemelli script.fn_stato_emissione_id, script.fn_stato_abortito_id, script.fn_stato_accettazione_id; il codice si legge con script.fn_doc_stato_codice. Consumatori: vendite.fn_cessa_contratto, vendite.fn_cessa_contratti_scaduti, vendite.fn_contratti_addebiti_maturati; il backend al posto di contratti_repository.STATO_CESSATO. Brief: brief-modello-documento-vendita §17 (Tid, 2026-10-31).';
```

</div>

---
{% include-markdown "signature-core.md" %}
