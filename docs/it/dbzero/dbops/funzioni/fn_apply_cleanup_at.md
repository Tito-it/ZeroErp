{% include-markdown "it/dbzero/dbops/manual/fn_apply_cleanup_at.md" %}
# ⚙️ Funzione `fn_apply_cleanup_at`

```sql
CREATE FUNCTION fn_apply_cleanup_at(p_schema text, p_table text, p_cleanup_column text, p_base_ts_column text, p_ttl_days integer, p_apply_on_update boolean, p_dry_run boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_apply_cleanup_at(p_schema text, p_table text, p_cleanup_column text, p_base_ts_column text, p_ttl_days integer, p_apply_on_update boolean DEFAULT false, p_dry_run boolean DEFAULT false)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_base_col text := NULLIF(btrim(p_base_ts_column), '');
  v_sql text;
  v_count integer := 0;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Scrive cleanup_at = <colonna base> + ttl_days sulle righe
  --   di una tabella (il pregresso del cleanup).
  --
  -- Regole:
  --   - p_ttl_days obbligatorio (>= 0)
  --   - p_base_ts_column obbligatoria: la sceglie chi chiama, con
  --     dbops.fn_cleanup_at_regola (il runner); qui non si indovina
  --   - la colonna e' cleanup_at, nome fisso del framework:
  --     p_cleanup_column puo' solo confermarlo (NULL o 'cleanup_at')
  --   - se p_dry_run=true ritorna il conteggio righe potenziali
  --   - se apply_on_update=false aggiorna solo righe senza cleanup_at
  --   - righe con la base NULL: non si toccano (non scadono)
  -- =========================================================

  IF p_schema IS NULL OR p_table IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops', 'fn_apply_cleanup_at', 'E_GENERICO',
      jsonb_build_object('detail','schema/table obbligatori'),
      NULL::uuid,
      'p_schema e p_table obbligatori'
    );
  END IF;

  IF NULLIF(btrim(p_cleanup_column), '') IS DISTINCT FROM NULL
     AND btrim(p_cleanup_column) <> 'cleanup_at' THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'dbops.fn_apply_cleanup_at', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro', 'p_cleanup_column', 'valore', p_cleanup_column),
      NULL::uuid, 'la colonna della scadenza e'' cleanup_at');
  END IF;

  IF v_base_col IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'dbops.fn_apply_cleanup_at', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro', 'p_base_ts_column'),
      NULL::uuid, 'p_base_ts_column obbligatoria');
  END IF;

  IF p_ttl_days IS NULL OR p_ttl_days < 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops', 'fn_apply_cleanup_at', 'E_GENERICO',
      jsonb_build_object('detail','ttl_days non valido'),
      NULL::uuid,
      'p_ttl_days deve essere >= 0'
    );
  END IF;

  IF NOT dbops.fn_col_exists(p_schema, p_table, 'cleanup_at') THEN
    RETURN 0;
  END IF;

  IF NOT dbops.fn_col_exists(p_schema, p_table, v_base_col) THEN
    RETURN 0;
  END IF;

  IF p_apply_on_update THEN
    v_sql := format(
      'SELECT count(*) FROM %I.%I WHERE %I IS NOT NULL AND (cleanup_at IS NULL OR cleanup_at <> (%I + make_interval(days => %s)))',
      p_schema, p_table, v_base_col, v_base_col, p_ttl_days
    );
  ELSE
    v_sql := format(
      'SELECT count(*) FROM %I.%I WHERE cleanup_at IS NULL AND %I IS NOT NULL',
      p_schema, p_table, v_base_col
    );
  END IF;

  IF p_dry_run THEN
    EXECUTE v_sql INTO v_count;
    RETURN v_count;
  END IF;

  IF p_apply_on_update THEN
    v_sql := format(
      'UPDATE %I.%I SET cleanup_at = %I + make_interval(days => %s) WHERE %I IS NOT NULL AND (cleanup_at IS NULL OR cleanup_at <> (%I + make_interval(days => %s)))',
      p_schema, p_table, v_base_col, p_ttl_days,
      v_base_col, v_base_col, p_ttl_days
    );
  ELSE
    v_sql := format(
      'UPDATE %I.%I SET cleanup_at = %I + make_interval(days => %s) WHERE cleanup_at IS NULL AND %I IS NOT NULL',
      p_schema, p_table, v_base_col, p_ttl_days, v_base_col
    );
  END IF;

  EXECUTE v_sql;
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count;
END;
$function$

COMMENT ON FUNCTION dbops.fn_apply_cleanup_at(p_schema text, p_table text, p_cleanup_column text, p_base_ts_column text, p_ttl_days integer, p_apply_on_update boolean, p_dry_run boolean)
IS 'Scrive cleanup_at = colonna base + p_ttl_days sulle righe di p_schema.p_table: il pregresso del cleanup, chiamato da dbops.fn_run_automations_cleanup con la regola di dbops.fn_cleanup_at_regola. p_base_ts_column obbligatoria (la sceglie il chiamante, qui non si indovina); p_cleanup_column puo'' solo confermare cleanup_at, nome fisso del framework (NULL o ''cleanup_at'', altro → E_PARAMETRO_INVALIDO). p_apply_on_update false: solo le righe con cleanup_at NULL; true: anche quelle con una scadenza diversa. Le righe con la base NULL non si toccano. p_dry_run: conta senza scrivere. Tabella senza cleanup_at o senza la colonna base: 0. Ritorna le righe scritte (o contate).';
```

</div>

---
{% include-markdown "signature-core.md" %}
