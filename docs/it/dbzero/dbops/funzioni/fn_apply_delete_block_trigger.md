{% include-markdown "it/dbzero/dbops/manual/fn_apply_delete_block_trigger.md" %}
# ⚙️ Funzione `fn_apply_delete_block_trigger`

```sql
CREATE FUNCTION fn_apply_delete_block_trigger(p_schema text, p_table text, p_guc_key text, p_trigger_name text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_apply_delete_block_trigger(p_schema text, p_table text, p_guc_key text, p_trigger_name text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_trigger_name text;
  v_exists boolean;
BEGIN
  IF p_schema IS NULL OR p_table IS NULL OR p_guc_key IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops',
      'fn_apply_delete_block_trigger',
      'E_GENERICO',
      jsonb_build_object(
        'detail','Parametri obbligatori mancanti',
        'schema', p_schema,
        'table', p_table,
        'guc_key', p_guc_key
      ),
      NULL::uuid,
      'Parametri obbligatori mancanti (schema, table, guc_key).'
    );
  END IF;

  v_trigger_name := COALESCE(
    NULLIF(p_trigger_name, ''),
    format('trg_%s_a10_delete_block_dlt', p_table)
  );

  SELECT EXISTS (
    SELECT 1
      FROM pg_trigger t
      JOIN pg_class c ON c.oid = t.tgrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = p_schema
       AND c.relname = p_table
       AND t.tgname = v_trigger_name
  )
  INTO v_exists;

  IF v_exists THEN
    RETURN;
  END IF;

  EXECUTE format(
    'CREATE TRIGGER %I AFTER DELETE ON %I.%I FOR EACH ROW EXECUTE FUNCTION script.trgfn_delete_block_by_guc(%L);',
    v_trigger_name,
    p_schema,
    p_table,
    p_guc_key
  );
END
$function$

COMMENT ON FUNCTION dbops.fn_apply_delete_block_trigger(p_schema text, p_table text, p_guc_key text, p_trigger_name text)
IS 'Crea trigger delete-block con template trg_<tabella>_a10_delete_block_dlt e GUC di bypass.';
```

</div>

---
{% include-markdown "signature-core.md" %}
