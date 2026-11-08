{% include-markdown "it/dbzero/dbops/manual/fn_apply_delete_block_trigger.md" %}
# ⚙️ Funzione `fn_apply_delete_block_trigger`

```sql
CREATE FUNCTION fn_apply_delete_block_trigger(p_schema text, p_table text, p_guc_key text, p_trigger_name text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_apply_delete_block_trigger(p_schema text, p_table text, p_guc_key text, p_trigger_name text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_trigger_name text;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Montare il blocco di DELETE di una tabella: un trigger BEFORE DELETE FOR EACH
  --   ROW su script.trgfn_delete_block_by_guc(p_guc_key), col nome di
  --   dbops.fn_nome_oggetto_dichiarato (template trg_{table}_a10_delete_block_dlt).
  --
  -- Regole:
  --   - BEFORE e non AFTER: il rifiuto arriva prima delle cascate delle FK e dei
  --     guard dei figli, che altrimenti cancellano o parlano al posto suo;
  --   - un trigger con lo stesso nome si toglie e si ricrea: la forma e' sempre quella
  --     di oggi. Gli altri trigger della funzione sulla tabella li governa il runner
  --     (dbops.fn_run_automations_delete_block, con dbops.fn_delete_block_divergenze).
  -- =========================================================
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

  v_trigger_name := dbops.fn_nome_oggetto_dichiarato(p_trigger_name, 'trg_{table}_a10_delete_block_dlt', p_schema, p_table);

  EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I.%I', v_trigger_name, p_schema, p_table);

  EXECUTE format(
    'CREATE TRIGGER %I BEFORE DELETE ON %I.%I FOR EACH ROW EXECUTE FUNCTION script.trgfn_delete_block_by_guc(%L);',
    v_trigger_name,
    p_schema,
    p_table,
    p_guc_key
  );
END
$function$

COMMENT ON FUNCTION dbops.fn_apply_delete_block_trigger(p_schema text, p_table text, p_guc_key text, p_trigger_name text)
IS 'Monta il blocco di DELETE di p_schema.p_table: un trigger BEFORE DELETE FOR EACH ROW su script.trgfn_delete_block_by_guc(p_guc_key), col nome di dbops.fn_nome_oggetto_dichiarato (p_trigger_name, o il template trg_<tabella>_a10_delete_block_dlt). BEFORE perche'' il rifiuto (E_DELETE_NOT_ALLOWED) arrivi prima delle cascate delle FK e dei guard dei figli. Un trigger con lo stesso nome si toglie e si ricrea; gli altri trigger della funzione sulla tabella li porta all''atteso dbops.fn_run_automations_delete_block. Schema, tabella o guc_key mancanti: E_GENERICO.';
```

</div>

---
{% include-markdown "signature-core.md" %}
