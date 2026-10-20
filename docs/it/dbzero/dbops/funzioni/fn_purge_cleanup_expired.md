{% include-markdown "it/dbzero/dbops/manual/fn_purge_cleanup_expired.md" %}
# ⚙️ Funzione `fn_purge_cleanup_expired`

```sql
CREATE FUNCTION fn_purge_cleanup_expired(p_schema text, p_table text, p_cleanup_column text, p_batch_limit integer, p_dry_run boolean)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_purge_cleanup_expired(p_schema text, p_table text, p_cleanup_column text DEFAULT 'cleanup_at'::text, p_batch_limit integer DEFAULT 5000, p_dry_run boolean DEFAULT false)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_cleanup_col text := COALESCE(NULLIF(btrim(p_cleanup_column), ''), 'cleanup_at');
  v_limit integer := COALESCE(NULLIF(p_batch_limit, 0), 5000);
  v_sql text;
  v_deleted integer := 0;
  v_total integer := 0;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Elimina record con cleanup_at scaduto, a batch.
  --
  -- Regole:
  --   - cleanup_at deve esistere
  --   - p_batch_limit default 5000
  --   - se p_dry_run=true ritorna il numero record eleggibili
  -- =========================================================

  IF p_schema IS NULL OR p_table IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops', 'fn_purge_cleanup_expired', 'E_GENERICO',
      jsonb_build_object('detail','schema/table obbligatori'),
      NULL::uuid,
      'p_schema e p_table obbligatori'
    );
  END IF;

  IF v_limit < 1 THEN
    v_limit := 5000;
  END IF;

  IF NOT dbops.fn_col_exists(p_schema, p_table, v_cleanup_col) THEN
    RETURN 0;
  END IF;

  IF p_dry_run THEN
    v_sql := format(
      'SELECT count(*) FROM %I.%I WHERE %I IS NOT NULL AND %I <= now()',
      p_schema, p_table, v_cleanup_col, v_cleanup_col
    );
    EXECUTE v_sql INTO v_total;
    RETURN v_total;
  END IF;

  LOOP
    v_sql := format($f$
      WITH del AS (
        DELETE FROM %I.%I
        WHERE ctid IN (
          SELECT ctid
          FROM %I.%I
          WHERE %I IS NOT NULL AND %I <= now()
          ORDER BY %I
          LIMIT %s
        )
        RETURNING 1
      )
      SELECT count(*) FROM del
    $f$, p_schema, p_table, p_schema, p_table, v_cleanup_col, v_cleanup_col, v_cleanup_col, v_limit);

    EXECUTE v_sql INTO v_deleted;
    v_total := v_total + COALESCE(v_deleted, 0);

    EXIT WHEN v_deleted IS NULL OR v_deleted = 0;
  END LOOP;

  RETURN v_total;
END;
$function$

COMMENT ON FUNCTION dbops.fn_purge_cleanup_expired(p_schema text, p_table text, p_cleanup_column text, p_batch_limit integer, p_dry_run boolean)
IS '
Helper per cancellare record scaduti in base a cleanup_at.

Parametri:
- p_schema, p_table: tabella target.
- p_cleanup_column: colonna di cleanup (default cleanup_at).
- p_batch_limit: limite batch di cancellazione (default 5000).
- p_dry_run: se true non elimina e ritorna il numero eleggibile.
';
```

</div>

---
{% include-markdown "signature-core.md" %}
