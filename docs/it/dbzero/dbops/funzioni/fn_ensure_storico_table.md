# ⚙️ Funzione `fn_ensure_storico_table`

```sql
CREATE FUNCTION fn_ensure_storico_table(p_schema_base text, p_table_base text, p_fk_col text, p_create_gin_index boolean, p_dry_run boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_ensure_storico_table(p_schema_base text, p_table_base text, p_fk_col text, p_create_gin_index boolean, p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_exists   boolean;
  v_sql      text;
  v_tbl_sto  text := format('%I_storico', p_table_base);
  v_full_base text := format('%I.%I', p_schema_base, p_table_base);
  v_full_sto  text := format('storico.%I', v_tbl_sto);
BEGIN 
  -- Helper: crea (se manca) storico.<table>_storico con struttura standard
  -- esiste già?
  SELECT EXISTS (
    SELECT 1
    FROM pg_class c
    JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='storico' AND c.relname=v_tbl_sto AND c.relkind='r'
  ) INTO v_exists;

  IF v_exists THEN
    RETURN;
  END IF;

  -- build DDL
  v_sql := format($ddl$
    CREATE SCHEMA IF NOT EXISTS storico;
    CREATE TABLE IF NOT EXISTS %s (
      id              BIGSERIAL PRIMARY KEY,
      %I              bigint NOT NULL,
      op              text NOT NULL,                      -- 'UPD' | 'DLT' | altro
      ts              timestamptz NOT NULL DEFAULT now(), -- timestamp evento
      snapshot        jsonb,                              -- contenuto riga (NEW/OLD)
      user_update     text,
      data_update     timestamptz,
      tx_id           uuid,
      valid_from      timestamptz DEFAULT now(),
      valid_to        timestamptz
    );
    -- FK opzionale sulla base (commentata se non desideri vincolo)
    ALTER TABLE %s
      ADD CONSTRAINT fk_%I FOREIGN KEY (%I) REFERENCES %s(id);
    CREATE INDEX IF NOT EXISTS ix_%s_%I_ts      ON %s (ts);
    CREATE INDEX IF NOT EXISTS ix_%s_%I_fk      ON %s (%I);
  $ddl$,
    v_full_sto,
    p_fk_col,
    -- FK (commentata)
    v_full_sto, p_table_base, p_fk_col, v_full_base,
    p_table_base, p_fk_col, v_full_sto,
    p_table_base, p_fk_col, v_full_sto, p_fk_col
  );

  IF p_create_gin_index THEN
    v_sql := v_sql || format(E'\nCREATE INDEX IF NOT EXISTS ix_%s_snapshot_gin ON %s USING GIN (snapshot);\n',
                            p_table_base, v_full_sto);
  END IF;

  IF p_dry_run THEN
    PERFORM dbops.fn_audit_log_once(
      p_function_name => 'fn_run_automations_storico',
      p_status        => 'DRYRUN',
      p_rule_type     => 'STORICO',
      p_dry_run       => true,
      p_params        => jsonb_build_object('table', v_full_sto, 'action','CREATE_STORICO_TABLE'),
      p_message       => 'Storico table would be created'
    );
    RETURN;
  END IF;

  BEGIN
    EXECUTE v_sql;
    PERFORM dbops.fn_audit_log_once(
      p_function_name => 'fn_run_automations_storico',
      p_status        => 'OK',
      p_rule_type     => 'STORICO',
      p_params        => jsonb_build_object('table', v_full_sto, 'action','CREATE_STORICO_TABLE'),
      p_message       => 'Storico table created'
    );

  EXCEPTION WHEN OTHERS THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops',
      'fn_run_automations_storico',          -- function_name / contesto
      'E_STORICO_PROVISION',              -- codice breve dell’errore
      jsonb_build_object(
        'action','CREATE_STORICO_TABLE',
        'schema', p_schema_base,
        'table',  p_table_base,
        'target', format('storico.%s_storico', p_table_base),
        'fk',     p_fk_col
      ),
      NULL::uuid,
      SQLERRM
    );

  END;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
