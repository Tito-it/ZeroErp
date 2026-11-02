-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- Guardrail naming codice_interno / codice (linee-guida-sql §6c,
-- brief-naming-stato-codice-interno.md).
--
-- Scansiona le definizioni LIVE (pg_views + pg_matviews + pg_proc), NON i
-- changelog storici, e FALLISCE (RAISE) se trova:
--   A) `codice_interno AS <x>_codice`        (immutabile col nome del mutabile)
--   B) `<x>codice AS <y>_codice_interno`     (mutabile col nome dell'immutabile)
--   C) chiave jsonb `'<x>_codice'` valorizzata con `<rel>.codice_interno`
--
-- Regola: codice_interno -> *_codice_interno (logica) ; codice -> *_codice (display).
--
-- Esclusi by-design (alias-free / gia' fedeli, non producono il pattern):
--   - dbops.fn_get_lookup_codici          (RETURNS TABLE codice + codice_interno;
--                                           mapping dinamico via %I, mai 'codice_interno AS codice')
--   - script.fn_get_entita_ruolo_detail   (to_jsonb(e.*), nessun alias)
--
-- Uso (read-only):
--   psql "$DB_URL" -v ON_ERROR_STOP=1 -f scripts/sql/check_naming_stato_codice.sql
-- Esce con errore (RAISE EXCEPTION) se trova mislabel; NOTICE 'OK' altrimenti.
-- ------------------------------------------------------------

DO $$
DECLARE
    v_hits text;
BEGIN
    WITH defs AS (
        SELECT format('VIEW %I.%I', schemaname, viewname) AS obj,
               pg_get_viewdef(format('%I.%I', schemaname, viewname)::regclass) AS src
          FROM pg_views
         WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        UNION ALL
        SELECT format('MATVIEW %I.%I', schemaname, matviewname) AS obj,
               pg_get_viewdef(format('%I.%I', schemaname, matviewname)::regclass) AS src
          FROM pg_matviews
         WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        UNION ALL
        SELECT format('FUNCTION %I.%I', n.nspname, p.proname) AS obj,
               pg_get_functiondef(p.oid) AS src
          FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
           AND p.prokind IN ('f', 'p')
    )
    SELECT string_agg(obj, E'\n' ORDER BY obj)
      INTO v_hits
      FROM (
          SELECT DISTINCT obj
            FROM defs
           WHERE -- A) codice_interno AS <x>_codice  (ma NON _codice_interno)
                 src ~ 'codice_interno[ \t]+AS[ \t]+[a-z_]*codice([^_a-z]|$)'
              -- B) codice (non _interno) AS <x>_codice_interno
              OR src ~ '[^_a-z]codice[ \t]+AS[ \t]+[a-z_]*codice_interno'
              -- C) jsonb '<x>_codice' => <rel>.codice_interno
              OR src ~ '''[a-z_]*codice''[ \t]*,[^,)]*\.codice_interno'
      ) h;

    IF v_hits IS NOT NULL THEN
        RAISE EXCEPTION E'[naming codice_interno/codice] mislabel rilevati nelle definizioni live:\n%\n\nRegola (linee-guida-sql §6c): codice_interno -> *_codice_interno (logica); codice -> *_codice (display). Vedi brief-naming-stato-codice-interno.md.', v_hits;
    END IF;

    RAISE NOTICE '[naming codice_interno/codice] OK — nessun mislabel nelle definizioni live.';
END $$;
