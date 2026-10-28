{% include-markdown "it/dbzero/dbops/manual/fn_lock_columns_divergenze.md" %}
# ⚙️ Funzione `fn_lock_columns_divergenze`

```sql
CREATE FUNCTION fn_lock_columns_divergenze(p_exec_mode text, p_schemas text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_lock_columns_divergenze(p_exec_mode text, p_schemas text[])
 RETURNS TABLE(schema_name text, table_name text, azione text, trigger_atteso text, colonne_attese text[], argomenti_attesi text[], trigger_vivi text[], colonne_perse text[])
 LANGUAGE plpgsql
AS $function$
-- Scopo: il lock di colonna ATTESO confrontato con quello VIVO, una riga
--   per tabella che diverge. Criterio unico del runner
--   (dbops.fn_run_automations_lock_columns) e del presidio pgTAP.
-- Parametri: p_exec_mode come il runner (AUTO/CI/SCHEDULED);
--   p_schemas NULL = ambito risolto da dbops.fn_resolve_scope.
DECLARE
    v_schemas text[] := dbops.fn_resolve_scope(p_schemas);
BEGIN
    RETURN QUERY
    WITH tab AS (
        SELECT n.nspname::text AS sch, c.relname::text AS tbl, c.oid AS rel
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE c.relkind = 'r'
           AND n.nspname = ANY (v_schemas)
           AND dbops.fn_table_in_scope(n.nspname, c.relname)
    ),
    -- La prima regola LOCK_COLUMNS attiva che copre la tabella: ne da' il nome.
    regola AS (
        SELECT DISTINCT ON (t.rel)
               t.rel,
               dbops.fn_name_from_template(
                   COALESCE(r.name_template, 'trg_{table}_a10_lock_columns_upd'),
                   t.sch, t.tbl, NULL, NULL, NULL, NULL) AS trg
          FROM tab t
          JOIN dbops.automation_rules_tbl r
            ON r.enabled
           AND upper(btrim(r.rule_type)) = 'LOCK_COLUMNS'
           AND dbops.fn_schema_match(r.target_schema, t.sch)
           AND (upper(r.target_table) = '*ALL' OR t.tbl ILIKE r.target_table)
           AND (upper(btrim(r.exec_mode)) = 'AUTO' OR r.exec_mode = p_exec_mode)
         ORDER BY t.rel, r.priority, r.id
    ),
    -- Ogni trigger su trgfn_lock_columns, qualunque nome abbia.
    vivo AS (
        SELECT tg.tgrelid AS rel,
               tg.tgname::text AS trg,
               tg.tgtype,
               dbops.fn_trigger_argomenti(tg.tgargs) AS args,
               ARRAY(SELECT a.attname::text
                       FROM unnest(tg.tgattr::int2[]) AS k(attnum)
                       JOIN pg_attribute a
                         ON a.attrelid = tg.tgrelid AND a.attnum = k.attnum
                      ORDER BY 1) AS cols_update_of
          FROM pg_trigger tg
          JOIN tab t ON t.rel = tg.tgrelid
         WHERE NOT tg.tgisinternal
           AND tg.tgfoid = 'script.trgfn_lock_columns()'::regprocedure
    ),
    -- Le colonne che i vivi bloccano: argomenti dispari + UPDATE OF.
    vivo_col AS (
        SELECT DISTINCT v.rel, x.col
          FROM vivo v
          CROSS JOIN LATERAL (
              SELECT v.args[i] FROM generate_subscripts(v.args, 1) AS g(i) WHERE i % 2 = 1
              UNION
              SELECT unnest(v.cols_update_of)
          ) AS x(col)
    ),
    atteso_col AS (
        SELECT t.rel, 'codice_interno'::text AS col,
               'E_CODICE_NON_MODIFICABILE'::text AS codice, 0 AS ord
          FROM tab t
         WHERE dbops.fn_col_exists(t.sch, t.tbl, 'codice_interno')
        UNION ALL
        SELECT t.rel, l.column_name::text,
               COALESCE(l.error_code, 'E_CODICE_NON_MODIFICABILE')::text, 1
          FROM tab t
          JOIN dbops.automation_lock_columns l
            ON l.enabled
           AND l.target_schema = t.sch
           AND l.target_table  = t.tbl
           AND l.column_name  <> 'codice_interno'
         WHERE dbops.fn_col_exists(t.sch, t.tbl, l.column_name)
           AND (   upper(btrim(l.exec_mode)) = 'AUTO'
                OR l.exec_mode = p_exec_mode
                -- un altro modo: resta attesa se e' gia' bloccata
                OR EXISTS (SELECT 1 FROM vivo_col vc
                            WHERE vc.rel = t.rel AND vc.col = l.column_name))
    ),
    atteso AS (
        SELECT a.rel,
               array_agg(a.col ORDER BY a.ord, a.col) AS cols,
               ARRAY(SELECT w.x
                       FROM atteso_col b
                       CROSS JOIN LATERAL unnest(ARRAY[b.col, b.codice])
                            WITH ORDINALITY AS w(x, j)
                      WHERE b.rel = a.rel
                      ORDER BY b.ord, b.col, w.j) AS args
          FROM atteso_col a
         GROUP BY a.rel
    ),
    vivo_tab AS (
        SELECT v.rel,
               array_agg(v.trg ORDER BY v.trg) AS trgs,
               count(*) AS n,
               min(v.trg) AS trg1
          FROM vivo v
         GROUP BY v.rel
    ),
    confronto AS (
        SELECT t.sch, t.tbl, rg.trg, at.cols, at.args, vt.trgs,
               CASE
                 WHEN at.rel IS NULL AND vt.rel IS NULL THEN NULL
                 WHEN at.rel IS NULL THEN 'TOGLIE'
                 WHEN vt.rel IS NULL THEN 'CREA'
                 WHEN vt.n = 1
                  AND v1.trg = rg.trg
                  AND v1.args = at.args
                  AND v1.cols_update_of = ARRAY(SELECT c FROM unnest(at.cols) AS u(c) ORDER BY 1)
                  AND v1.tgtype = 19           -- BEFORE | ROW | UPDATE
                 THEN NULL
                 ELSE 'RIGENERA'
               END AS azione,
               ARRAY(SELECT vc.col
                       FROM vivo_col vc
                      WHERE vc.rel = t.rel
                        AND dbops.fn_col_exists(t.sch, t.tbl, vc.col)
                        AND NOT (vc.col = ANY (COALESCE(at.cols, ARRAY[]::text[])))
                        AND NOT EXISTS (
                              SELECT 1 FROM dbops.automation_lock_columns l
                               WHERE l.target_schema = t.sch
                                 AND l.target_table  = t.tbl
                                 AND l.column_name   = vc.col)
                      ORDER BY 1) AS perse
          FROM tab t
          JOIN regola rg        ON rg.rel = t.rel
          LEFT JOIN atteso at   ON at.rel = t.rel
          LEFT JOIN vivo_tab vt ON vt.rel = t.rel
          -- il primo (e, se allineato, unico) trigger vivo, per confrontarlo
          LEFT JOIN vivo v1     ON v1.rel = t.rel AND v1.trg = vt.trg1
    )
    SELECT cf.sch, cf.tbl, cf.azione, cf.trg, cf.cols, cf.args,
           COALESCE(cf.trgs, ARRAY[]::text[]), cf.perse
      FROM confronto cf
     WHERE cf.azione IS NOT NULL
     ORDER BY cf.sch, cf.tbl;
END;
$function$

COMMENT ON FUNCTION dbops.fn_lock_columns_divergenze(p_exec_mode text, p_schemas text[])
IS 'Il lock di colonna ATTESO (codice_interno implicito + righe attive di dbops.automation_lock_columns; una riga di un altro exec_mode resta attesa se la colonna e'' gia'' bloccata) confrontato con quello VIVO (ogni trigger su script.trgfn_lock_columns, qualunque nome abbia). Una riga per tabella che diverge: azione CREA, RIGENERA o TOGLIE; colonne_perse = colonne bloccate dal vivo che il registro non nomina affatto (una riga con enabled = false e'' invece una decisione di togliere il blocco). Criterio unico di dbops.fn_run_automations_lock_columns e del presidio pgTAP dbops/test-lock-columns-convergenza. Brief: brief-db-lock-di-colonna-fuori-registro §4 D2-D3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
