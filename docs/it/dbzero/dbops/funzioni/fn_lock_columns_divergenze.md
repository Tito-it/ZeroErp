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
-- Le tabelle dell'ambito sono di tre specie:
--   1) coperte da una regola LOCK_COLUMNS attiva del modo della corsa: il lock
--      atteso e' codice_interno + le righe del registro;
--   2) coperte SOLO da regole attive di un altro modo: nessuna azione (le
--      governa l'altra corsa, come una riga del registro di un altro modo);
--   3) senza regola attiva (spenta, cancellata o mai scritta): niente di
--      atteso, il lock vivo si toglie.
-- codice_interno e' la colonna implicita del framework: non e' mai una
--   colonna «persa», anche dove nessuna regola la chiede piu'.
DECLARE
    v_schemas text[] := dbops.fn_resolve_scope(p_schemas);
BEGIN
    RETURN QUERY
    -- ha_ci si calcola qui, una volta per tabella: valutato nei JOIN, il
    -- planner (che stima una riga per i CTE) lo ripeteva tabelle x tabelle.
    WITH tab AS MATERIALIZED (
        SELECT n.nspname::text AS sch, c.relname::text AS tbl, c.oid AS rel,
               dbops.fn_col_exists(n.nspname, c.relname, 'codice_interno') AS ha_ci
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE c.relkind = 'r'
           AND n.nspname = ANY (v_schemas)
           AND dbops.fn_table_in_scope(n.nspname, c.relname)
    ),
    -- Le regole LOCK_COLUMNS attive che coprono la tabella, di qualunque modo.
    copertura AS (
        SELECT t.rel, r.id, r.priority, r.name_template,
               (upper(btrim(r.exec_mode)) = 'AUTO' OR r.exec_mode = p_exec_mode) AS del_modo
          FROM tab t
          JOIN dbops.automation_rules_tbl r
            ON r.enabled
           AND upper(btrim(r.rule_type)) = 'LOCK_COLUMNS'
           AND dbops.fn_schema_match(r.target_schema, t.sch)
           AND (upper(r.target_table) = '*ALL' OR t.tbl ILIKE r.target_table)
    ),
    -- La prima regola del modo della corsa: ne da' il nome.
    regola AS (
        SELECT DISTINCT ON (t.rel)
               t.rel,
               dbops.fn_name_from_template(
                   cp.name_template,
                   t.sch, t.tbl, NULL, NULL, NULL, NULL) AS trg
          FROM tab t
          JOIN copertura cp ON cp.rel = t.rel AND cp.del_modo
         ORDER BY t.rel, cp.priority, cp.id
    ),
    -- Le tabelle che solo un'altra corsa governa: fuori dal confronto.
    altro_modo AS (
        SELECT cp.rel
          FROM copertura cp
         GROUP BY cp.rel
        HAVING NOT bool_or(cp.del_modo)
    ),
    -- Ogni trigger su trgfn_lock_columns, qualunque nome abbia (sede: la vista).
    vivo AS (
        SELECT v.tabella_oid AS rel,
               v.trigger_name AS trg,
               v.trigger_tipo AS tgtype,
               v.abilitato,
               v.argomenti AS args,
               v.colonne_update_of AS cols_update_of
          FROM dbops.vw_lock_columns_vivi v
          JOIN tab t ON t.rel = v.tabella_oid
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
    -- L'atteso esiste solo sulle tabelle che una regola del modo copre.
    atteso_col AS (
        SELECT t.rel, 'codice_interno'::text AS col,
               'E_CODICE_NON_MODIFICABILE'::text AS codice, 0 AS ord
          FROM tab t
          JOIN regola rg ON rg.rel = t.rel
         WHERE t.ha_ci
        UNION ALL
        SELECT t.rel, l.column_name::text, l.error_code::text, 1
          FROM tab t
          JOIN regola rg ON rg.rel = t.rel
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
                  AND v1.abilitato
                  AND v1.args = at.args
                  AND v1.cols_update_of = ARRAY(SELECT c FROM unnest(at.cols) AS u(c) ORDER BY 1)
                  AND v1.tgtype = 19           -- BEFORE | ROW | UPDATE
                 THEN NULL
                 ELSE 'RIGENERA'
               END AS azione,
               ARRAY(SELECT vc.col
                       FROM vivo_col vc
                      WHERE vc.rel = t.rel
                        AND vc.col <> 'codice_interno'
                        AND dbops.fn_col_exists(t.sch, t.tbl, vc.col)
                        AND NOT (vc.col = ANY (COALESCE(at.cols, ARRAY[]::text[])))
                        AND NOT EXISTS (
                              SELECT 1 FROM dbops.automation_lock_columns l
                               WHERE l.target_schema = t.sch
                                 AND l.target_table  = t.tbl
                                 AND l.column_name   = vc.col)
                      ORDER BY 1) AS perse
          FROM tab t
          LEFT JOIN regola rg   ON rg.rel = t.rel
          LEFT JOIN atteso at   ON at.rel = t.rel
          LEFT JOIN vivo_tab vt ON vt.rel = t.rel
          -- il primo (e, se allineato, unico) trigger vivo, per confrontarlo
          LEFT JOIN vivo v1     ON v1.rel = t.rel AND v1.trg = vt.trg1
         WHERE NOT EXISTS (SELECT 1 FROM altro_modo am WHERE am.rel = t.rel)
    )
    SELECT cf.sch, cf.tbl, cf.azione, cf.trg, cf.cols, cf.args,
           COALESCE(cf.trgs, ARRAY[]::text[]), cf.perse
      FROM confronto cf
     WHERE cf.azione IS NOT NULL
     ORDER BY cf.sch, cf.tbl;
END;
$function$

COMMENT ON FUNCTION dbops.fn_lock_columns_divergenze(p_exec_mode text, p_schemas text[])
IS 'Il lock di colonna ATTESO confrontato con quello VIVO, una riga per tabella dell''ambito che diverge: azione CREA, RIGENERA o TOGLIE. Il vivo e'' ogni trigger su script.trgfn_lock_columns, qualunque nome abbia, letto da dbops.vw_lock_columns_vivi; un trigger disabilitato non e'' allineato. L''atteso dipende dalla regola LOCK_COLUMNS di dbops.automation_rules_tbl: con una regola attiva del modo della corsa e'' codice_interno (implicito) + le righe attive di dbops.automation_lock_columns, e una riga di un altro exec_mode resta attesa se la colonna e'' gia'' bloccata; una tabella coperta solo da regole attive di un altro modo non si confronta (la governa l''altra corsa); senza regola attiva non c''e'' niente di atteso e il lock vivo si toglie. colonne_perse = colonne bloccate dal vivo che il registro non nomina affatto (una riga con enabled = false e'' invece una decisione di togliere il blocco); codice_interno, colonna implicita del framework, non e'' mai persa. Criterio unico di dbops.fn_run_automations_lock_columns, che si ferma se ci sono colonne perse, e del presidio pgTAP dbops/test-lock-columns-convergenza.';
```

</div>

---
{% include-markdown "signature-core.md" %}
