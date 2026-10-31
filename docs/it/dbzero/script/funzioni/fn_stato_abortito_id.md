{% include-markdown "it/dbzero/script/manual/fn_stato_abortito_id.md" %}
# ⚙️ Funzione `fn_stato_abortito_id`

```sql
CREATE FUNCTION fn_stato_abortito_id(p_testata regclass)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_stato_abortito_id(p_testata regclass)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- Scopo: l'id dello stato d'annullo della testata, dal suo
    --   vocabolario (is_abortito = true). La logica e' del
    --   lettore comune (rev 2026-10-31, 20261031-08):
    --   - testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA;
    --   - nessuno stato dichiarato: NULL.
    -- =========================================================
    RETURN script.fn_stato_per_colonna_id(p_testata, 'is_abortito', 'script.fn_stato_abortito_id');
END;
$function$

COMMENT ON FUNCTION script.fn_stato_abortito_id(p_testata regclass)
IS 'BB del modello del documento: l''id dello stato d''ANNULLO di una testata, letto dal suo vocabolario degli stati (is_abortito = true; la mappa e'' script.fn_doc_stato_modello). Unica sede da cui leggerlo: nessuno scrive ''ANNULLATO'' per dire «lo stato d''annullo» (guida del modello §8). Al massimo uno per vocabolario, ed e'' attivo (uq_<vocabolario>_abortito, chk_<vocabolario>_abortito_attivo). NULL se il vocabolario non ne dichiara; testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA. La logica e'' di script.fn_stato_per_colonna_id (dal 2026-10-31), comune ai lettori gemelli: script.fn_stato_emissione_id, script.fn_stato_cessazione_id, script.fn_stato_accettazione_id; il codice per i verbi che lo prendono si legge con script.fn_doc_stato_codice. Consumatori: il backend (l''annullo chiesto dal cambio di stato va al verbo d''annullo), vendite.fn_annulla_commessa, vendite.fn_annulla_contratto, vendite.fn_annulla_lotto_da_draft, vendite.fn_annulla_offerta, vendite.fn_annulla_ordine, vendite.fn_annulla_preventivo, vendite.fn_cambia_stato_ddt (l''annullo della bolla emessa). Brief: brief-modello-documento-vendita §9 (Z-3 di Tid, 2026-10-25) e §17.';
```

</div>

---
{% include-markdown "signature-core.md" %}
