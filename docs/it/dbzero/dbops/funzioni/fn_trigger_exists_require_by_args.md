{% include-markdown "it/dbzero/dbops/manual/fn_trigger_exists_require_by_args.md" %}
# ⚙️ Funzione `fn_trigger_exists_require_by_args`

```sql
CREATE FUNCTION fn_trigger_exists_require_by_args(p_child_rel regclass, p_parent_schema name, p_parent_table name, p_parent_attivo_col name, p_fk_col name, p_parent_ref_col name)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_trigger_exists_require_by_args(p_child_rel regclass, p_parent_schema name, p_parent_table name, p_parent_attivo_col name, p_fk_col name, p_parent_ref_col name)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
  -- Scopo: c'e' sulla figlia un require montato con questi argomenti?
  --   La funzione per OID, gli argomenti per nome dalla grammatica.
  SELECT EXISTS (
      SELECT 1
        FROM pg_catalog.pg_trigger t
       CROSS JOIN LATERAL dbops.fn_trigger_attivo_argomenti(
               'trgfn_child_requires_active_parent',
               dbops.fn_trigger_argomenti(t.tgargs)) g
       WHERE t.tgrelid = p_child_rel
         AND NOT t.tgisinternal
         AND t.tgfoid = 'dbops.trgfn_child_requires_active_parent()'::pg_catalog.regprocedure
         AND g.valido
         AND g.padre_schema  = p_parent_schema
         AND g.padre_tabella = p_parent_table
         AND g.stato_col     = p_parent_attivo_col
         AND g.fk_col        = p_fk_col
         AND g.ref_col       = p_parent_ref_col
  );
$function$

COMMENT ON FUNCTION dbops.fn_trigger_exists_require_by_args(p_child_rel regclass, p_parent_schema name, p_parent_table name, p_parent_attivo_col name, p_fk_col name, p_parent_ref_col name)
IS 'Dice se sulla tabella figlia c''e'' un require ATTIVO (dbops.trgfn_child_requires_active_parent) montato con questi argomenti: padre (schema e tabella), colonna attivo del padre, colonna FK della figlia, colonna referenziata del padre. Riconosce la funzione del trigger per OID, quindi con qualunque search_path, e legge gli argomenti per nome con la grammatica dei trigger ATTIVO (dbops.fn_trigger_attivo_argomenti su dbops.fn_trigger_argomenti): un montaggio fuori grammatica non e'' riconosciuto. Confronto esatto degli identificatori. La chiama dbops.fn_run_automations_attivo per le strategie di esistenza BY_FUNCTION e BOTH.';
```

</div>

---
{% include-markdown "signature-core.md" %}
