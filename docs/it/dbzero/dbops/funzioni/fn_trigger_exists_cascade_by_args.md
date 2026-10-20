{% include-markdown "it/dbzero/dbops/manual/fn_trigger_exists_cascade_by_args.md" %}
# ⚙️ Funzione `fn_trigger_exists_cascade_by_args`

```sql
CREATE FUNCTION fn_trigger_exists_cascade_by_args(p_parent_rel regclass, p_child_schema text, p_child_table text, p_fk_col text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_trigger_exists_cascade_by_args(p_parent_rel regclass, p_child_schema text, p_child_table text, p_fk_col text)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
  SELECT EXISTS (
    SELECT 1
    FROM pg_trigger t
    JOIN pg_proc p ON p.oid = t.tgfoid
    WHERE t.tgrelid = p_parent_rel
      AND NOT t.tgisinternal
      AND p.proname = 'trgfn_soft_delete_cascade'
      AND pg_get_triggerdef(t.oid) ILIKE
          format('%%EXECUTE FUNCTION dbops.trgfn_soft_delete_cascade(''%s'',''%s'',''%s'')%%',
                p_child_schema, p_child_table, p_fk_col)
  );
$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
