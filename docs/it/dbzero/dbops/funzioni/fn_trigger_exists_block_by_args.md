{% include-markdown "it/dbzero/dbops/manual/fn_trigger_exists_block_by_args.md" %}
# ⚙️ Funzione `fn_trigger_exists_block_by_args`

```sql
CREATE FUNCTION fn_trigger_exists_block_by_args(p_parent_rel regclass, p_child_schema name, p_child_table name, p_fk_col name, p_parent_ref_col name, p_parent_attivo_col name)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_trigger_exists_block_by_args(p_parent_rel regclass, p_child_schema name, p_child_table name, p_fk_col name, p_parent_ref_col name, p_parent_attivo_col name)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
  -- Scopo: c'e' sul padre un block montato con questi argomenti?
  --   La funzione per OID, gli argomenti per nome dalla grammatica.
  SELECT EXISTS (
      SELECT 1
        FROM pg_catalog.pg_trigger t
       CROSS JOIN LATERAL dbops.fn_trigger_attivo_argomenti(
               'trgfn_prevent_deactivate_if_children',
               dbops.fn_trigger_argomenti(t.tgargs)) g
       WHERE t.tgrelid = p_parent_rel
         AND NOT t.tgisinternal
         AND t.tgfoid = 'dbops.trgfn_prevent_deactivate_if_children()'::pg_catalog.regprocedure
         AND g.valido
         AND g.figlia_schema  = p_child_schema
         AND g.figlia_tabella = p_child_table
         AND g.fk_col         = p_fk_col
         AND g.ref_col        = p_parent_ref_col
         AND g.stato_col      = p_parent_attivo_col
  );
$function$

COMMENT ON FUNCTION dbops.fn_trigger_exists_block_by_args(p_parent_rel regclass, p_child_schema name, p_child_table name, p_fk_col name, p_parent_ref_col name, p_parent_attivo_col name)
IS 'Dice se sulla tabella padre c''e'' un block ATTIVO (dbops.trgfn_prevent_deactivate_if_children) montato con questi argomenti: figlia (schema e tabella), colonna FK della figlia, colonna referenziata del padre, colonna attivo del padre. Riconosce la funzione del trigger per OID, quindi con qualunque search_path, e legge gli argomenti per nome con la grammatica dei trigger ATTIVO (dbops.fn_trigger_attivo_argomenti su dbops.fn_trigger_argomenti): un montaggio fuori grammatica non e'' riconosciuto. Confronto esatto degli identificatori. La chiama dbops.fn_run_automations_attivo per le strategie di esistenza BY_FUNCTION e BOTH.';
```

</div>

---
{% include-markdown "signature-core.md" %}
