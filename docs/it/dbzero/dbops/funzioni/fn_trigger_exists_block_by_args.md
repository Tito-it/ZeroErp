{% include-markdown "it/dbzero/dbops/manual/fn_trigger_exists_block_by_args.md" %}
# ⚙️ Funzione `fn_trigger_exists_block_by_args`

```sql
CREATE FUNCTION fn_trigger_exists_block_by_args(p_parent_rel regclass, p_child_schema text, p_child_table text, p_fk_col text, p_parent_ref_col text, p_parent_attivo_col text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_trigger_exists_block_by_args(p_parent_rel regclass, p_child_schema text, p_child_table text, p_fk_col text, p_parent_ref_col text, p_parent_attivo_col text)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
  -- Scopo: rileva l'esistenza di un trigger BLOCK sul padre
  -- con la signature a 5 args della trgfn. Confronta tutti gli
  -- argomenti via pattern ILIKE su pg_get_triggerdef.
  SELECT EXISTS (
    SELECT 1
    FROM pg_trigger t
    JOIN pg_proc p ON p.oid = t.tgfoid
    WHERE t.tgrelid = p_parent_rel
      AND NOT t.tgisinternal
      AND p.proname = 'trgfn_prevent_deactivate_if_children'
      AND pg_get_triggerdef(t.oid) ILIKE
          format(
            '%%EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children(''%s'',''%s'',''%s'',''%s'',''%s'')%%',
            p_child_schema, p_child_table, p_fk_col, p_parent_ref_col, p_parent_attivo_col
          )
  );
$function$

COMMENT ON FUNCTION dbops.fn_trigger_exists_block_by_args(p_parent_rel regclass, p_child_schema text, p_child_table text, p_fk_col text, p_parent_ref_col text, p_parent_attivo_col text)
IS 'Verifica esistenza trigger BLOCK (trgfn_prevent_deactivate_if_children) su tabella padre matchando la signature a 5 args.';
```

</div>

---
{% include-markdown "signature-core.md" %}
