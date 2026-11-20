{% include-markdown "it/dbzero/dbops/manual/fn_seed_primo_impianto_divergenze.md" %}
# ⚙️ Funzione `fn_seed_primo_impianto_divergenze`

```sql
CREATE FUNCTION fn_seed_primo_impianto_divergenze(p_schemas text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_seed_primo_impianto_divergenze(p_schemas text[])
 RETURNS TABLE(schema_name text, table_name text, azione text, trigger_atteso text, argomenti_attesi text[], trigger_vivi text[], colonne_non_classificate text[], colonne_assenti text[])
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: il trigger del seed di primo impianto ATTESO confrontato con
--   quello VIVO, una riga per tabella dell'ambito che diverge.
-- Parametri: p_schemas NULL = ambito risolto da dbops.fn_resolve_scope.
-- Regole:
--   - il vivo e' ogni trigger su script.trgfn_seed_primo_impianto,
--     qualunque nome abbia;
--   - riga accesa: l'atteso e' un trigger solo, BEFORE INSERT OR
--     UPDATE OR DELETE FOR EACH ROW, abilitato, col nome di
--     dbops.fn_nome_oggetto_dichiarato (template
--     trg_{table}_a00_seed_primo_impianto_ins_upd_dlt) e gli argomenti
--     della forma. Manca → CREA; diverso → RIGENERA;
--   - forma COLONNA con colonne non classificate o assenti →
--     NON_CLASSIFICATA, al posto di CREA o RIGENERA (il trigger di
--     prima resta); tabella senza colonna id → SENZA_ID, salvo la forma
--     FIGLIA, che la colonna id non la chiede;
--   - forma FIGLIA: la colonna del padre assente → NON_CLASSIFICATA;
--     il padre non iscritto, spento, figlia a sua volta o senza id →
--     PADRE_NON_ISCRITTO (il trigger di prima resta);
--   - riga spenta e un vivo → TOGLIE;
--   - un vivo senza riga → SCONOSCIUTO: il runner si ferma e lo nomina.
DECLARE
    -- text[]: %TYPE non fa array
    v_schemas text[] := dbops.fn_resolve_scope(p_schemas);
    -- text[]: le colonne libere, dalla grammatica
    v_libere  text[] := (SELECT g.colonne_libere
                           FROM dbops.fn_seed_primo_impianto_argomenti(ARRAY['RIGA']) AS g);
BEGIN
    RETURN QUERY
    WITH tab AS MATERIALIZED (
        SELECT n.nspname::text AS sch, c.relname::text AS tbl, c.oid AS rel
          FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
         WHERE c.relkind = 'r'
           AND n.nspname = ANY (v_schemas)
           AND dbops.fn_table_in_scope(n.nspname, c.relname)
    ),
    colonne AS (
        SELECT t.rel,
               array_agg(a.attname::text ORDER BY a.attnum) AS tutte
          FROM tab t
          JOIN pg_catalog.pg_attribute a
            ON a.attrelid = t.rel AND a.attnum > 0 AND NOT a.attisdropped
         GROUP BY t.rel
    ),
    riga AS (
        SELECT t.rel, d.enabled,
               dbops.fn_nome_oggetto_dichiarato(
                   d.trigger_name, 'trg_{table}_a00_seed_primo_impianto_ins_upd_dlt',
                   d.schema_name, d.table_name) AS trg,
               CASE
                 WHEN d.tabella_padre IS NOT NULL THEN ARRAY['FIGLIA', d.colonna_padre, d.tabella_padre]
                 WHEN d.solo_inserimento        THEN ARRAY['SOLO_INSERIMENTO']
                 WHEN d.colonne_software IS NULL THEN ARRAY['RIGA']
                 ELSE ARRAY['COLONNA',
                            array_to_string(d.colonne_software, ','),
                            array_to_string(d.colonne_installazione, ',')]
               END AS args,
               d.colonne_software IS NOT NULL AS per_colonna,
               d.tabella_padre IS NOT NULL AS figlia,
               -- il padre: iscritto, acceso, non figlia a sua volta, con la colonna id
               (d.tabella_padre IS NULL
                OR EXISTS (SELECT 1
                             FROM dbops.automazione_seed_primo_impianto p
                            WHERE p.schema_name || '.' || p.table_name = d.tabella_padre
                              AND p.enabled
                              AND p.tabella_padre IS NULL
                              AND EXISTS (SELECT 1 FROM pg_catalog.pg_attribute pa
                                           WHERE pa.attrelid = to_regclass(d.tabella_padre)
                                             AND pa.attname = 'id' AND pa.attnum > 0
                                             AND NOT pa.attisdropped))) AS padre_ok,
               COALESCE(d.colonne_software, ARRAY[]::text[])
                 || COALESCE(d.colonne_installazione, ARRAY[]::text[])
                 || CASE WHEN d.colonna_padre IS NULL THEN ARRAY[]::text[]
                         ELSE ARRAY[d.colonna_padre] END AS elencate
          FROM tab t
          JOIN dbops.automazione_seed_primo_impianto d
            ON d.schema_name = t.sch AND d.table_name = t.tbl
    ),
    classifica AS (
        SELECT r.rel,
               'id' = ANY (c.tutte) AS ha_id,
               CASE WHEN r.per_colonna THEN
                 ARRAY(SELECT x FROM unnest(c.tutte) AS x
                        WHERE NOT (x = ANY (v_libere)) AND NOT (x = ANY (r.elencate))
                        ORDER BY x)
               ELSE ARRAY[]::text[] END AS non_class,
               ARRAY(SELECT x FROM unnest(r.elencate) AS x
                      WHERE NOT (x = ANY (c.tutte))
                      ORDER BY x) AS assenti
          FROM riga r
          JOIN colonne c ON c.rel = r.rel
    ),
    vivo AS (
        SELECT tg.tgrelid AS rel,
               tg.tgname::text AS trg,
               tg.tgtype::integer AS tgtype,
               tg.tgenabled IN ('O', 'A') AS abilitato,
               dbops.fn_trigger_argomenti(tg.tgargs) AS args
          FROM pg_catalog.pg_trigger tg
          JOIN tab t ON t.rel = tg.tgrelid
         WHERE NOT tg.tgisinternal
           AND tg.tgfoid = 'script.trgfn_seed_primo_impianto()'::regprocedure
    ),
    vivo_tab AS (
        SELECT v.rel, array_agg(v.trg ORDER BY v.trg) AS trgs, count(*) AS n, min(v.trg) AS trg1
          FROM vivo v
         GROUP BY v.rel
    ),
    confronto AS (
        SELECT t.sch, t.tbl, r.trg, r.args, vt.trgs, k.non_class, k.assenti,
               CASE
                 WHEN r.rel IS NULL AND vt.rel IS NULL THEN NULL
                 WHEN r.rel IS NULL THEN 'SCONOSCIUTO'
                 WHEN NOT r.enabled AND vt.rel IS NULL THEN NULL
                 WHEN NOT r.enabled THEN 'TOGLIE'
                 WHEN NOT k.ha_id AND NOT r.figlia THEN 'SENZA_ID'
                 WHEN NOT r.padre_ok THEN 'PADRE_NON_ISCRITTO'
                 WHEN cardinality(k.non_class) > 0 OR cardinality(k.assenti) > 0
                   THEN 'NON_CLASSIFICATA'
                 WHEN vt.rel IS NULL THEN 'CREA'
                 WHEN vt.n = 1
                  AND v1.trg = r.trg
                  AND v1.abilitato
                  AND v1.args = r.args
                  AND v1.tgtype = 31            -- ROW | BEFORE | INSERT | DELETE | UPDATE
                 THEN NULL
                 ELSE 'RIGENERA'
               END AS azione
          FROM tab t
          LEFT JOIN riga r       ON r.rel = t.rel
          LEFT JOIN classifica k ON k.rel = t.rel
          LEFT JOIN vivo_tab vt  ON vt.rel = t.rel
          LEFT JOIN vivo v1      ON v1.rel = t.rel AND v1.trg = vt.trg1
    )
    SELECT cf.sch, cf.tbl, cf.azione,
           CASE WHEN cf.azione IN ('CREA', 'RIGENERA') THEN cf.trg END,
           CASE WHEN cf.azione IN ('CREA', 'RIGENERA') THEN cf.args END,
           COALESCE(cf.trgs, ARRAY[]::text[]),
           COALESCE(cf.non_class, ARRAY[]::text[]),
           COALESCE(cf.assenti, ARRAY[]::text[])
      FROM confronto cf
     WHERE cf.azione IS NOT NULL
     ORDER BY cf.sch, cf.tbl;
END;
$function$

COMMENT ON FUNCTION dbops.fn_seed_primo_impianto_divergenze(p_schemas text[])
IS 'Il trigger del seed di primo impianto ATTESO (dbops.automazione_seed_primo_impianto) contro quello VIVO, una riga per tabella dell''ambito che diverge. Il vivo e'' ogni trigger su script.trgfn_seed_primo_impianto, qualunque nome abbia. Azioni: CREA (riga accesa, nessun trigger), RIGENERA (nome, momento, argomenti o abilitazione diversi, o piu'' di uno), TOGLIE (riga spenta, trigger vivo), SCONOSCIUTO (trigger vivo senza riga: il runner si ferma), NON_CLASSIFICATA (forma COLONNA con una colonna non libera in nessuno dei due elenchi, o con una colonna elencata che la tabella non ha: il runner non monta e non rigenera, il trigger di prima resta), SENZA_ID (la tabella non ha la colonna id, salvo la forma FIGLIA), PADRE_NON_ISCRITTO (forma FIGLIA con un padre non iscritto, spento, figlia a sua volta o senza colonna id: il runner non monta e non rigenera). Nella forma FIGLIA la colonna del padre conta come elencata: assente, NON_CLASSIFICATA. p_schemas NULL = l''ambito di dbops.fn_resolve_scope; le tabelle fuori dall''ambito non si confrontano. La leggono il runner dbops.fn_run_automations_seed_primo_impianto, la rete di convergenza e il presidio. STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
