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
  v_exists      boolean;
  v_sql         text;

  -- nome tabella storico = stesso nome della base, schema 'storico'
  v_tbl_sto     text := format('%I', p_table_base);
  v_full_base   text := format('%I.%I', p_schema_base, p_table_base);
  v_full_sto    text := format('storico.%I', v_tbl_sto);

  -- PK padre (monocolonna) e tipo per allineare la FK
  v_parent_reg  regclass := (quote_ident(p_schema_base)||'.'||quote_ident(p_table_base))::regclass;
  v_parent_pk   text;
  v_parent_pk_n int;
  v_fk_type     text;

  -- nomi vincoli/indici
  v_pk_name     text := format('pk_%s_%s', 'storico', p_table_base);
  v_fk_name     text := format('fk_%s', p_table_base);
  v_ix_fk_name  text := format('ix_%s_%s_fk', p_table_base, p_fk_col);
  v_ix_gin_name text := format('ix_%s_snapshot_gin', p_table_base);
BEGIN
  -- esiste già la tabella storico?<— esci
  SELECT EXISTS (
    SELECT 1
    FROM pg_class c
    JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='storico' AND c.relname=p_table_base AND c.relkind='r'
  ) INTO v_exists;
  IF v_exists THEN
    RETURN;
  END IF;

  -- PK e tipo dal padre (assume PK monocampo; fallback su 'id')
  SELECT a.attname, array_length(i.indkey,1)
    INTO v_parent_pk, v_parent_pk_n
  FROM pg_index i
  JOIN pg_attribute a
    ON a.attrelid=i.indrelid AND a.attnum = i.indkey[0]
  WHERE i.indrelid = v_parent_reg
    AND i.indisprimary
    AND array_length(i.indkey,1)=1
  LIMIT 1;

  IF v_parent_pk IS NOT NULL THEN
    SELECT format_type(att.atttypid, att.atttypmod)
      INTO v_fk_type
    FROM pg_attribute att
    WHERE att.attrelid = v_parent_reg
      AND att.attname  = v_parent_pk
      AND NOT att.attisdropped;
  END IF;

  IF v_fk_type IS NULL THEN
    v_parent_pk := 'id';
    SELECT format_type(att.atttypid, att.atttypmod)
      INTO v_fk_type
    FROM pg_attribute att
    WHERE att.attrelid = v_parent_reg
      AND att.attname  = 'id'
      AND NOT att.attisdropped;

    IF v_fk_type IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'dbops',
        'fn_run_automations_storico_provision',
        'E_STORICO_PARENT_PK_NOT_FOUND',
        jsonb_build_object('schema',p_schema_base,'table',p_table_base),
        NULL::uuid,
        ARRAY['Impossibile determinare PK o tipo per tabella padre']
      );
      RETURN;
    END IF;
  END IF;

  -- DDL: tabella, commenti, FK, indici (no indice su ts; non esiste più)
  v_sql := format($ddl$
    CREATE SCHEMA IF NOT EXISTS storico;
    CREATE TABLE IF NOT EXISTS %s (
      id              BIGSERIAL,
      %I              %s NOT NULL,
      change_type     char(1) DEFAULT 'A',
      tipo_operazione smallint,
      snapshot        jsonb,
      user_insert     text DEFAULT CURRENT_USER,
      data_insert     timestamptz DEFAULT now(),
      tx_id           uuid,
      valid_from      timestamptz DEFAULT now(),
      valid_to        timestamptz,
      CONSTRAINT %I PRIMARY KEY (id)
    );
    COMMENT ON COLUMN %s.change_type
      IS 'Tipo di cambiamento: A=Active, S=Suppressed, F=Fused, D=Divided';
    COMMENT ON COLUMN %s.tipo_operazione
      IS 'Tipo operazione (1=insert, 2=update, 3=delete)';

    ALTER TABLE %s
      ADD CONSTRAINT %I FOREIGN KEY (%I) REFERENCES %s(%I);

    CREATE INDEX IF NOT EXISTS %I ON %s (%I);
  $ddl$,
    v_full_sto,
    p_fk_col, v_fk_type,
    v_pk_name,
    v_full_sto,
    v_full_sto,
    v_full_sto,
    v_fk_name, p_fk_col, v_full_base, v_parent_pk,
    v_ix_fk_name, v_full_sto, p_fk_col
  );

  IF p_create_gin_index THEN
    v_sql := v_sql || format(E'\nCREATE INDEX IF NOT EXISTS %I ON %s USING GIN (snapshot);\n',
                             v_ix_gin_name, v_full_sto);
  END IF;

  IF p_dry_run THEN
    PERFORM dbops.fn_audit_log_once(
      p_function_name => 'fn_run_automations_storico_provision',
      p_status        => 'DRYRUN',
      p_rule_type     => 'STORICO_PROVISION',
      p_dry_run       => true,
      p_params        => jsonb_build_object('table', v_full_sto, 'action','CREATE_STORICO_TABLE'),
      p_message       => 'Storico table would be created'
    );
    RETURN;
  END IF;

  BEGIN
    EXECUTE v_sql;
    PERFORM dbops.fn_audit_log_once(
      p_function_name => 'fn_run_automations_storico_provision',
      p_status        => 'OK',
      p_rule_type     => 'STORICO_PROVISION',
      p_params        => jsonb_build_object('table', v_full_sto, 'action','CREATE_STORICO_TABLE'),
      p_message       => 'Storico table created'
    );
  EXCEPTION WHEN OTHERS THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops',
      'fn_run_automations_storico_provision',
      'E_STORICO_PROVISION',
      jsonb_build_object(
        'action','CREATE_STORICO_TABLE',
        'schema', p_schema_base,
        'table',  p_table_base,
        'target', v_full_sto,
        'fk',     p_fk_col
      ),
      NULL::uuid,
      ARRAY[SQLERRM]
    );
  END;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
