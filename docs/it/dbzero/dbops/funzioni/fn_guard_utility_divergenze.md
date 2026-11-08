{% include-markdown "it/dbzero/dbops/manual/fn_guard_utility_divergenze.md" %}
# ⚙️ Funzione `fn_guard_utility_divergenze`

```sql
CREATE FUNCTION fn_guard_utility_divergenze(p_exec_mode text, p_schemas text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_guard_utility_divergenze(p_exec_mode text, p_schemas text[])
 RETURNS TABLE(schema_name text, table_name text, azione text, trigger_atteso text, utility_column text, soggetto_ruolo_column text, trigger_vivi text[])
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: il guard utility/tipo ruolo ATTESO confrontato con quello VIVO, una riga per
--   tabella dell'ambito che diverge. Criterio unico del runner
--   (dbops.fn_run_automations_guard_utility) e del presidio pgTAP.
-- Parametri: p_exec_mode come il runner (AUTO/CI/SCHEDULED); p_schemas NULL = ambito
--   risolto da dbops.fn_resolve_scope.
-- Regole:
--   - il vivo e' ogni trigger su script.trgfn_guard_utility_tipo_ruolo_by_cols, qualunque
--     nome abbia;
--   - una riga di un altro exec_mode: la tabella non si confronta (la governa l'altra corsa);
--   - riga abilitata, colonne presenti: l'atteso e' un trigger solo, BEFORE INSERT OR UPDATE
--     OF le due colonne, FOR EACH ROW, abilitato, col nome di dbops.fn_nome_oggetto_dichiarato
--     (template trg_{table}_a10_guard_utility_tipo_ruolo_ins_upd) e gli argomenti
--     (utility_column, soggetto_ruolo_column). Manca → CREA; diverso in qualcosa → RIGENERA;
--   - riga abilitata ma una colonna non c'e' → COLONNA_MANCANTE (il runner lo segnala e toglie
--     un eventuale vivo): il guard non si monta su una colonna che non esiste;
--   - riga spenta con un vivo → TOGLIE;
--   - un vivo senza nessuna riga → SCONOSCIUTO: il runner si ferma e lo nomina.
--   Nessun filtro sul nome della colonna: il guard e' generico, la colonna la dichiara il
--   registro.
DECLARE
    -- text[]: %TYPE non fa array
    v_schemas text[] := dbops.fn_resolve_scope(p_schemas);
BEGIN
    RETURN QUERY
    WITH tab AS MATERIALIZED (
        SELECT n.nspname::text AS sch, c.relname::text AS tbl, c.oid AS rel
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE c.relkind = 'r'
           AND n.nspname = ANY (v_schemas)
           AND dbops.fn_table_in_scope(n.nspname, c.relname)
    ),
    riga AS (
        SELECT t.rel, g.enabled, g.utility_column AS ucol, g.soggetto_ruolo_column AS scol,
               (upper(btrim(g.exec_mode)) = 'AUTO' OR g.exec_mode = p_exec_mode) AS del_modo,
               (    dbops.fn_col_exists(t.sch, t.tbl, g.utility_column)
                AND dbops.fn_col_exists(t.sch, t.tbl, g.soggetto_ruolo_column)) AS colonne_ok,
               dbops.fn_nome_oggetto_dichiarato(
                   g.trigger_name, 'trg_{table}_a10_guard_utility_tipo_ruolo_ins_upd',
                   g.schema_name, g.table_name) AS trg
          FROM tab t
          JOIN dbops.automazione_guard_utility_tipo_ruolo g
            ON g.schema_name = t.sch AND g.table_name = t.tbl
    ),
    vivo AS (
        SELECT tg.tgrelid AS rel,
               tg.tgname::text AS trg,
               tg.tgtype::integer AS tgtype,
               tg.tgenabled IN ('O', 'A') AS abilitato,
               dbops.fn_trigger_argomenti(tg.tgargs) AS args,
               ARRAY(SELECT a.attname::text
                       FROM unnest(tg.tgattr::smallint[]) AS k(attnum)
                       JOIN pg_attribute a ON a.attrelid = tg.tgrelid AND a.attnum = k.attnum
                      ORDER BY 1) AS cols_update_of
          FROM pg_trigger tg
          JOIN tab t ON t.rel = tg.tgrelid
         WHERE NOT tg.tgisinternal
           AND tg.tgfoid = 'script.trgfn_guard_utility_tipo_ruolo_by_cols()'::regprocedure
    ),
    vivo_tab AS (
        SELECT v.rel, array_agg(v.trg ORDER BY v.trg) AS trgs, count(*) AS n, min(v.trg) AS trg1
          FROM vivo v
         GROUP BY v.rel
    ),
    confronto AS (
        SELECT t.sch, t.tbl, r.trg, r.ucol, r.scol, vt.trgs,
               CASE
                 WHEN r.rel IS NULL AND vt.rel IS NULL THEN NULL
                 WHEN r.rel IS NULL THEN 'SCONOSCIUTO'
                 WHEN NOT r.del_modo THEN NULL
                 WHEN NOT r.enabled AND vt.rel IS NULL THEN NULL
                 WHEN NOT r.enabled THEN 'TOGLIE'
                 WHEN NOT r.colonne_ok THEN 'COLONNA_MANCANTE'
                 WHEN vt.rel IS NULL THEN 'CREA'
                 WHEN vt.n = 1
                  AND v1.trg = r.trg
                  AND v1.abilitato
                  AND v1.args = ARRAY[r.ucol::text, r.scol::text]
                  AND v1.cols_update_of = ARRAY(SELECT c FROM unnest(ARRAY[r.ucol::text, r.scol::text]) AS u(c) ORDER BY 1)
                  AND v1.tgtype = 23            -- ROW | BEFORE | INSERT | UPDATE
                 THEN NULL
                 ELSE 'RIGENERA'
               END AS azione
          FROM tab t
          LEFT JOIN riga r      ON r.rel = t.rel
          LEFT JOIN vivo_tab vt ON vt.rel = t.rel
          LEFT JOIN vivo v1     ON v1.rel = t.rel AND v1.trg = vt.trg1
    )
    SELECT cf.sch, cf.tbl, cf.azione,
           CASE WHEN cf.azione IN ('CREA', 'RIGENERA') THEN cf.trg END,
           cf.ucol, cf.scol,
           COALESCE(cf.trgs, ARRAY[]::text[])
      FROM confronto cf
     WHERE cf.azione IS NOT NULL
     ORDER BY cf.sch, cf.tbl;
END;
$function$

COMMENT ON FUNCTION dbops.fn_guard_utility_divergenze(p_exec_mode text, p_schemas text[])
IS 'Il guard utility/tipo ruolo ATTESO confrontato con quello VIVO, una riga per tabella dell''ambito che diverge (p_schemas NULL = dbops.fn_resolve_scope). Il vivo e'' ogni trigger su script.trgfn_guard_utility_tipo_ruolo_by_cols, qualunque nome abbia. Una riga di dbops.automazione_guard_utility_tipo_ruolo di un altro exec_mode lascia la tabella fuori dal confronto. Riga abilitata con le due colonne: l''atteso e'' un trigger solo, BEFORE INSERT OR UPDATE OF le due colonne, FOR EACH ROW, abilitato, col nome di dbops.fn_nome_oggetto_dichiarato (template trg_<tabella>_a10_guard_utility_tipo_ruolo_ins_upd) e gli argomenti (utility_column, soggetto_ruolo_column); manca → CREA, diverso → RIGENERA. Riga abilitata con una colonna assente → COLONNA_MANCANTE. Riga spenta con un vivo → TOGLIE. Un vivo senza nessuna riga → SCONOSCIUTO. Nessun filtro sul nome della colonna: la dichiara il registro. Criterio unico di dbops.fn_run_automations_guard_utility e del presidio dbops/test-guard-utility-convergenza-v1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
