{% include-markdown "it/dbzero/dbops/manual/fn_drop_triggers_by_function_args.md" %}
# ⚙️ Funzione `fn_drop_triggers_by_function_args`

```sql
CREATE FUNCTION fn_drop_triggers_by_function_args(p_rel regclass, p_func_schema text, p_func_name text, VARIADIC p_args text[])
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_drop_triggers_by_function_args(p_rel regclass, p_func_schema text, p_func_name text, VARIADIC p_args text[])
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
      DECLARE
        r    record;
        n    int := 0;
        pat  text;
      BEGIN
        pat := format(
                'EXECUTE FUNCTION %I.%I(%s)',
                p_func_schema, p_func_name,
                array_to_string(ARRAY(SELECT quote_literal(a) FROM unnest(p_args) a), ', ')
              );

        FOR r IN
          SELECT t.tgname
          FROM pg_trigger t
          WHERE t.tgrelid = p_rel
            AND NOT t.tgisinternal
            AND pg_get_triggerdef(t.oid) ILIKE ('%'||pat||'%')
        LOOP
          EXECUTE format('DROP TRIGGER IF EXISTS %I ON %s', r.tgname, p_rel::text);
          n := n + 1;
        END LOOP;

        RETURN n;
      END;
      $function$
```

---
{% include-markdown "signature-core.md" %}
