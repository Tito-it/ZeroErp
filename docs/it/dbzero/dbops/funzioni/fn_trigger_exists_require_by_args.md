{% include-markdown "it/dbzero/dbops/manual/fn_trigger_exists_require_by_args.md" %}
# ⚙️ Funzione `fn_trigger_exists_require_by_args`

```sql
CREATE FUNCTION fn_trigger_exists_require_by_args(p_child_rel regclass, p_parent_schema text, p_parent_table text, p_parent_attivo_col text, p_fk_col text, p_parent_ref_col text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_trigger_exists_require_by_args(p_child_rel regclass, p_parent_schema text, p_parent_table text, p_parent_attivo_col text, p_fk_col text, p_parent_ref_col text)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
  -- Scopo: rileva l'esistenza di un trigger REQUIRE sul figlio
  -- con la signature a 5 args della trgfn. Confronta tutti gli
  -- argomenti via pattern ILIKE su pg_get_triggerdef.
  SELECT EXISTS (
    SELECT 1
    FROM pg_trigger t
    JOIN pg_proc p ON p.oid = t.tgfoid
    WHERE t.tgrelid = p_child_rel
      AND NOT t.tgisinternal
      AND p.proname = 'trgfn_child_requires_active_parent'
      AND pg_get_triggerdef(t.oid) ILIKE
          format(
            '%%EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent(''%s'',''%s'',''%s'',''%s'',''%s'')%%',
            p_parent_schema, p_parent_table, p_parent_attivo_col, p_fk_col, p_parent_ref_col
          )
  );
$function$

COMMENT ON FUNCTION dbops.fn_trigger_exists_require_by_args(p_child_rel regclass, p_parent_schema text, p_parent_table text, p_parent_attivo_col text, p_fk_col text, p_parent_ref_col text)
IS 'Verifica esistenza trigger REQUIRE (trgfn_child_requires_active_parent) su tabella figlio matchando la signature a 5 args.';
```

</div>

---
{% include-markdown "signature-core.md" %}
