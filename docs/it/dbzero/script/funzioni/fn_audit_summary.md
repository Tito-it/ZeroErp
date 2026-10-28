{% include-markdown "it/dbzero/script/manual/fn_audit_summary.md" %}
# ⚙️ Funzione `fn_audit_summary`

```sql
CREATE FUNCTION fn_audit_summary(p_audit_source_code text, p_storico_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_audit_summary(p_audit_source_code text, p_storico_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_storico_table   dbops.audit_sources.storico_table%TYPE;
    v_storico_pk_col  dbops.audit_sources.storico_pk_col%TYPE;
    v_storico_schema  text;
    v_storico_name    text;
    v_snapshot        jsonb;
    v_prev            jsonb;
    v_diff            jsonb;
    v_summary         text;
    -- Colonne audit standard da escludere dal diff: rumore.
    v_audit_cols      text[] := ARRAY[
        'data_insert','user_insert',
        'data_update','user_update',
        'tx_id'
    ];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Diff lazy on-read fra lo snapshot p_storico_id e lo
    --   snapshot precedente (stessa riga originale, ordinato
    --   per valid_from). Nessun pre-calcolo trigger-time.
    --
    -- Algoritmo:
    --   1. Guard parametri.
    --   2. Lookup dbops.audit_sources per dispatch dinamico.
    --   3. EXECUTE format(): trova snapshot + LAG(prev) sulla
    --      partizione storico_pk_col.
    --   4. jsonb_object_keys + filtro audit cols + filtro
    --      "valore cambiato" (IS DISTINCT FROM = NULL-safe).
    --   5. Compose summary "<N> modifiche".
    -- =========================================================

    -- Guard parametri (errori applicativi -> log + raise via
    -- script.fn_log_and_raise_error per coerenza con il resto
    -- del progetto: codici stabili, audit log, fallback i18n).
    IF p_audit_source_code IS NULL
       OR length(trim(p_audit_source_code)) = 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_audit_summary',
            'E_AUDIT_SUMMARY_PARAM_NON_VALIDO',
            jsonb_build_object(
                'param', 'p_audit_source_code',
                'value', p_audit_source_code
            ),
            NULL::uuid,
            'p_audit_source_code',
            coalesce(p_audit_source_code, 'NULL')
        );
    END IF;
    IF p_storico_id IS NULL OR p_storico_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_audit_summary',
            'E_AUDIT_SUMMARY_PARAM_NON_VALIDO',
            jsonb_build_object(
                'param', 'p_storico_id',
                'value', p_storico_id
            ),
            NULL::uuid,
            'p_storico_id',
            coalesce(p_storico_id::text, 'NULL')
        );
    END IF;

    -- Lookup metadata storico target.
    SELECT storico_table, storico_pk_col
      INTO v_storico_table, v_storico_pk_col
      FROM dbops.audit_sources
     WHERE code = p_audit_source_code
       AND attivo = true;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_audit_summary',
            'E_AUDIT_SOURCE_NON_TROVATO',
            jsonb_build_object(
                'audit_source_code', p_audit_source_code
            ),
            NULL::uuid,
            p_audit_source_code
        );
    END IF;

    -- Split "schema.table". Le storico tables sono controllate
    -- (seedate da CSV), nessun punto nel nome -> split_part
    -- e' sufficiente. Per maggiore robustezza in futuro si
    -- puo' passare a regclass + lookup pg_class.
    v_storico_schema := split_part(v_storico_table, '.', 1);
    v_storico_name   := split_part(v_storico_table, '.', 2);

    -- Dispatch dinamico: trova snapshot + prev tramite LAG.
    -- format(%I) sanifica gli identificatori (no SQL injection
    -- anche se i valori arrivassero da fonte non controllata).
    EXECUTE format(
        $sql$
        WITH target AS (
            SELECT %1$I AS row_id
              FROM %2$I.%3$I
             WHERE id = $1
        ),
        ranked AS (
            SELECT s.id,
                   s.snapshot,
                   LAG(s.snapshot)
                       OVER (ORDER BY s.valid_from, s.id) AS prev
              FROM %2$I.%3$I s
              JOIN target t ON s.%1$I = t.row_id
        )
        SELECT snapshot, prev FROM ranked WHERE id = $1
        $sql$,
        v_storico_pk_col,
        v_storico_schema,
        v_storico_name
    )
    INTO v_snapshot, v_prev
    USING p_storico_id;

    IF v_snapshot IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_audit_summary',
            'E_AUDIT_SNAPSHOT_NON_TROVATO',
            jsonb_build_object(
                'audit_source_code', p_audit_source_code,
                'storico_id',        p_storico_id
            ),
            NULL::uuid,
            p_audit_source_code,
            p_storico_id::text
        );
    END IF;

    -- Calcolo diff. NULL-safe via IS DISTINCT FROM.
    -- Itera sull'UNION dei keys di v_snapshot e v_prev: cosi'
    -- copre sia i campi aggiunti (chiave solo in snapshot,
    -- old=null new=val) sia i campi rimossi (chiave solo in
    -- prev, old=val new=null) sia gli update (chiave in
    -- entrambi, valore diverso). Se v_prev IS NULL (primo
    -- snapshot, tipo_operazione=1 INIZIALE), il primo SELECT
    -- domina e la WHERE include tutti i field non-audit.
    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'field', field_name,
                'old',   v_prev->field_name,
                'new',   v_snapshot->field_name
            )
            ORDER BY field_name
        ),
        '[]'::jsonb
    )
      INTO v_diff
      FROM (
          SELECT jsonb_object_keys(v_snapshot) AS field_name
          UNION
          SELECT jsonb_object_keys(COALESCE(v_prev, '{}'::jsonb))
      ) keys
     WHERE NOT (field_name = ANY(v_audit_cols))
       AND (
              v_prev IS NULL
           OR (v_prev->field_name) IS DISTINCT FROM (v_snapshot->field_name)
       );

    v_summary := format(
        '%s modifiche',
        jsonb_array_length(v_diff)
    );

    RETURN jsonb_build_object(
        'summary', v_summary,
        'diff',    v_diff
    );
END;
$function$

COMMENT ON FUNCTION script.fn_audit_summary(p_audit_source_code text, p_storico_id bigint)
IS 'Diff lazy on-read fra uno snapshot storico e il suo precedente sulla stessa riga originale (Fase 5 P1 2026-04-29). Dispatch dinamico via dbops.audit_sources (storico_table + storico_pk_col). Ritorna jsonb {summary: "<N> modifiche", diff: [{field,old,new},...]}. Esclude le 5 colonne audit standard. NULL-safe via IS DISTINCT FROM. LANGUAGE plpgsql STABLE - nessuna scrittura, nessun trigger, nessuna colonna aggiuntiva sulle storico.*';
```

</div>

---
{% include-markdown "signature-core.md" %}
