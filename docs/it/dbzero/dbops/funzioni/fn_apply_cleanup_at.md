{% include-markdown "it/dbzero/dbops/manual/fn_apply_cleanup_at.md" %}
# ⚙️ Funzione `fn_apply_cleanup_at`

```sql
CREATE FUNCTION fn_apply_cleanup_at(p_schema text, p_table text, p_cleanup_column text, p_base_ts_column text, p_ttl_days integer, p_apply_on_update boolean, p_dry_run boolean)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_apply_cleanup_at(p_schema text, p_table text, p_cleanup_column text, p_base_ts_column text, p_ttl_days integer, p_apply_on_update boolean DEFAULT false, p_dry_run boolean DEFAULT false)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_cleanup_col text := COALESCE(NULLIF(btrim(p_cleanup_column), ''), 'cleanup_at');
  v_base_col text := NULLIF(btrim(p_base_ts_column), '');
  v_sql text;
  v_count integer := 0;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Calcola cleanup_at con TTL fisso a partire da una colonna
  --   timestamp di base (es. data_insert, executed_at, ecc.).
  --
  -- Regole:
  --   - p_ttl_days obbligatorio (>= 0)
  --   - se p_dry_run=true ritorna il conteggio righe potenziali
  --   - se apply_on_update=false aggiorna solo righe senza cleanup_at
  -- =========================================================

  IF p_schema IS NULL OR p_table IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops', 'fn_apply_cleanup_at', 'E_GENERICO',
      jsonb_build_object('detail','schema/table obbligatori'),
      NULL::uuid,
      'p_schema e p_table obbligatori'
    );
  END IF;

  IF p_ttl_days IS NULL OR p_ttl_days < 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops', 'fn_apply_cleanup_at', 'E_GENERICO',
      jsonb_build_object('detail','ttl_days non valido'),
      NULL::uuid,
      'p_ttl_days deve essere >= 0'
    );
  END IF;

  IF v_base_col IS NULL THEN
    v_base_col := 'data_insert';
  END IF;

  IF NOT dbops.fn_col_exists(p_schema, p_table, v_cleanup_col) THEN
    RETURN 0;
  END IF;

  IF NOT dbops.fn_col_exists(p_schema, p_table, v_base_col) THEN
    RETURN 0;
  END IF;

  IF p_apply_on_update THEN
    v_sql := format(
      'SELECT count(*) FROM %I.%I WHERE %I IS NOT NULL AND (%I IS NULL OR %I <> (%I + make_interval(days => %s)))',
      p_schema, p_table, v_base_col, v_cleanup_col, v_cleanup_col, v_base_col, p_ttl_days
    );
  ELSE
    v_sql := format(
      'SELECT count(*) FROM %I.%I WHERE %I IS NULL AND %I IS NOT NULL',
      p_schema, p_table, v_cleanup_col, v_base_col
    );
  END IF;

  IF p_dry_run THEN
    EXECUTE v_sql INTO v_count;
    RETURN v_count;
  END IF;

  IF p_apply_on_update THEN
    v_sql := format(
      'UPDATE %I.%I SET %I = %I + make_interval(days => %s) WHERE %I IS NOT NULL AND (%I IS NULL OR %I <> (%I + make_interval(days => %s)))',
      p_schema, p_table, v_cleanup_col, v_base_col, p_ttl_days,
      v_base_col, v_cleanup_col, v_cleanup_col, v_base_col, p_ttl_days
    );
  ELSE
    v_sql := format(
      'UPDATE %I.%I SET %I = %I + make_interval(days => %s) WHERE %I IS NULL AND %I IS NOT NULL',
      p_schema, p_table, v_cleanup_col, v_base_col, p_ttl_days, v_cleanup_col, v_base_col
    );
  END IF;

  EXECUTE v_sql;
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count;
END;
$function$

COMMENT ON FUNCTION dbops.fn_apply_cleanup_at(p_schema text, p_table text, p_cleanup_column text, p_base_ts_column text, p_ttl_days integer, p_apply_on_update boolean, p_dry_run boolean)
IS '
Helper per calcolare cleanup_at con TTL fisso.

Parametri:
- p_schema, p_table: tabella target.
- p_cleanup_column: colonna di cleanup (default cleanup_at).
- p_base_ts_column: colonna timestamp di base (es. data_insert).
- p_ttl_days: giorni di retention.
- p_apply_on_update: se true ricalcola anche su righe già valorizzate.
- p_dry_run: se true non aggiorna e ritorna il numero righe potenziali.
';
```

</div>

---
{% include-markdown "signature-core.md" %}
