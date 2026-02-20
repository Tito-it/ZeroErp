{% include-markdown "it/dbzero/script/manual/trgfn_delete_block_by_guc.md" %}
# ⚙️ Funzione `trgfn_delete_block_by_guc`

```sql
CREATE FUNCTION trgfn_delete_block_by_guc()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_delete_block_by_guc()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  IF TG_NARGS < 1 THEN
    PERFORM script.fn_log_and_raise_error(
      TG_TABLE_SCHEMA,
      TG_NAME,
      'E_GENERICO',
      jsonb_build_object(
        'detail','Argomenti trigger mancanti',
        'expected','guc_key',
        'found', TG_NARGS
      ),
      NULL::uuid,
      concat('Argomenti trigger mancanti ',
        'expected ',' guc_key ',
        'found ', TG_NARGS::text)
    );
  END IF;

  IF current_setting(TG_ARGV[0], true) = 'on' THEN
    RETURN OLD;
  END IF;

  PERFORM script.fn_log_and_raise_error(
    TG_TABLE_SCHEMA,
    TG_NAME,
    'E_GENERICO',
    jsonb_build_object(
      'detail','Delete non consentita (policy ruoli)',
      'table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
      'id', OLD.id
    ),
    NULL::uuid,
    concat('Delete non consentita (policy ruoli) ',
      'table ', TG_TABLE_SCHEMA , '.' , TG_TABLE_NAME,
      ' id ', OLD.id::text)
    
  );

  RETURN OLD;
END
$function$

COMMENT ON FUNCTION script.trgfn_delete_block_by_guc()
IS 'Blocca DELETE se la GUC non e'' abilitata; usa fn_log_and_raise_error.';
```

---
{% include-markdown "signature-core.md" %}
