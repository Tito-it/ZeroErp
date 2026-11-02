-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test STRUTTURALE per Zero ERP
--
-- Test: l'invariante su cui reggono la RLS e le SECURITY DEFINER —
--   «le tabelle sono del migratore, l'applicazione non possiede niente,
--    FORCE ROW LEVEL SECURITY resta spento».
--   Regola: linee-guida-sql §10.5. Brief: brief-db-esclusioni-implicite (Q-3).
--
-- Elenco test (plan 6):
--   0) PRECONDIZIONE: ci sono tabelle con RLS (altrimenti 1-4 sarebbero verdi
--      per sottrazione)
--   1) tutte le tabelle con RLS hanno UN SOLO proprietario (il migratore)
--   2) l'applicazione (zeroerp_app) non possiede nessuna tabella applicativa
--   3) nessuna tabella persistente ha FORCE ROW LEVEL SECURITY
--   4) ogni SECURITY DEFINER applicativa e' di un ruolo che non subisce la RLS:
--      il proprietario delle tabelle, oppure un superuser
--   5) l'applicazione non ha BYPASSRLS ne' superuser
--
-- Scopo — perche' questo invariante, e perche' nessuno lo teneva:
--  - la RLS non vale per il PROPRIETARIO della tabella, se FORCE e' spento.
--    Il progetto ci conta: le funzioni SECURITY DEFINER girano come il loro
--    proprietario, e cosi' i risolutori di scope (fn_resolve_*, i verbi DEFINER
--    che ricopiano il filtro) vedono i dati che servono per decidere;
--  - due errori lo romperebbero in silenzio, senza un solo messaggio:
--      · una tabella creata dall'applicazione (proprietario zeroerp_app):
--        l'applicazione non subirebbe piu' la RLS su quella tabella;
--      · FORCE acceso «per sicurezza»: le DEFINER smetterebbero di vedere oltre
--        la RLS, e lo scope diventerebbe vuoto, o sbagliato;
--  - fino al 2026-10-04 l'invariante era vero (172 tabelle con RLS di un solo
--    ruolo, FORCE a zero) ma non scritto: §10.5 diceva anzi di accendere FORCE
--    «se la tabella e' di zeroerp_app», cioe' rimediava a un caso che non deve
--    esistere. Q-3 della valutazione qualitativa del 2026-10-04.
--
-- ⚠️ A CRITERIO, non per elenco: il proprietario si legge dal catalogo (quello
--   delle tabelle con RLS), le estensioni (postgis, pgagent…) si escludono per
--   appartenenza (pg_depend, deptype 'e'), non per nome di schema.
--   ⚠️ Lo schema `django` e' fuori dai test 2: e' dell'applicazione per
--   costruzione (linee-guida-sql §11.9), e non ha RLS.
--   ⚠️ Le TEMP TABLE sono fuori dal test 3. E un pgTAP che accende FORCE su una
--   tabella del modello dentro la propria transazione (rls/test-rls-offerte-
--   satelliti) non disturba: il suo ROLLBACK lo spegne, e questo file guarda
--   lo stato che resta.
--
-- ⚠️ PERCHE' GIRA COME L'APPLICAZIONE (runner di default): legge solo il
--   catalogo (pg_class, pg_proc, pg_roles), che non dipende dal ruolo connesso.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il file non tocca dati, ma il preambolo e' lo stesso
-- per tutti (guardrail_pgtap_preambolo.py).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- Il perimetro: tabelle e funzioni applicative, estensioni escluse
-- ============================================================
CREATE TEMP TABLE _membri_estensione AS
SELECT d.classid, d.objid
  FROM pg_depend d
 WHERE d.deptype = 'e'
   AND d.refclassid = 'pg_extension'::regclass;

CREATE TEMP TABLE _tabelle AS
SELECT c.oid, n.nspname, c.relname, c.relowner, c.relrowsecurity, c.relforcerowsecurity
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relkind IN ('r', 'p')
   AND c.relpersistence <> 't'
   AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
   AND n.nspname !~ '^pg_'
   AND NOT EXISTS (SELECT 1 FROM _membri_estensione e
                    WHERE e.classid = 'pg_class'::regclass AND e.objid = c.oid);

-- ============================================================
-- 0) Precondizione
-- ============================================================
SELECT ok(
    (SELECT count(*) FROM _tabelle WHERE relrowsecurity) > 0
    AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zeroerp_app'),
    '0. PRECONDIZIONE: ci sono tabelle con RLS, e il ruolo zeroerp_app esiste'
);

-- ============================================================
-- 1) Un solo proprietario per le tabelle con RLS
-- ============================================================
-- In elenco i proprietari trovati: se sono piu' d'uno, il messaggio li nomina.
SELECT is(
    (SELECT array_agg(DISTINCT pg_get_userbyid(relowner)::text ORDER BY pg_get_userbyid(relowner)::text)
       FROM _tabelle WHERE relrowsecurity),
    (SELECT ARRAY[pg_get_userbyid(c.relowner)::text]
       FROM pg_class c WHERE c.oid = 'vendite.fatture'::regclass),
    '1. tutte le tabelle con RLS hanno lo stesso proprietario di vendite.fatture (il migratore)'
);

-- ============================================================
-- 2) L'applicazione non possiede tabelle
-- ============================================================
SELECT is(
    (SELECT coalesce(array_agg(nspname || '.' || relname ORDER BY nspname, relname), '{}'::text[])
       FROM _tabelle
      WHERE pg_get_userbyid(relowner) = 'zeroerp_app'
        AND nspname <> 'django'),
    '{}'::text[],
    '2. zeroerp_app non possiede nessuna tabella applicativa (django escluso): subirebbe la RLS solo per FORCE'
);

-- ============================================================
-- 3) FORCE spento
-- ============================================================
-- ⭐ Le eccezioni si DICHIARANO qui, col perche'. Oggi nessuna.
SELECT is(
    (SELECT coalesce(array_agg(nspname || '.' || relname ORDER BY nspname, relname), '{}'::text[])
       FROM _tabelle
      WHERE relforcerowsecurity
        AND (nspname || '.' || relname) <> ALL (ARRAY[]::text[])),
    '{}'::text[],
    '3. nessuna tabella persistente ha FORCE ROW LEVEL SECURITY: le DEFINER leggono oltre la RLS da proprietarie'
);

-- ============================================================
-- 4) Le DEFINER sono di chi non subisce la RLS
-- ============================================================
-- Il proprietario delle tabelle (test 1) o un superuser (le poche DEFINER di
-- postgres dichiarate nel registro dbops.sec_functions_owner: dblink, log fuori
-- transazione). Un'altra proprieta' vorrebbe dire una DEFINER che legge SOTTO
-- la RLS credendo di leggere sopra.
SELECT is(
    (SELECT coalesce(array_agg(n.nspname || '.' || p.proname || ' (' || pg_get_userbyid(p.proowner) || ')'
                               ORDER BY n.nspname, p.proname), '{}'::text[])
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
       JOIN pg_roles r ON r.oid = p.proowner
      WHERE p.prosecdef
        AND n.nspname NOT IN ('pg_catalog', 'information_schema')
        AND n.nspname !~ '^pg_'
        AND NOT EXISTS (SELECT 1 FROM _membri_estensione e
                         WHERE e.classid = 'pg_proc'::regclass AND e.objid = p.oid)
        AND NOT r.rolsuper
        AND NOT r.rolbypassrls
        AND p.proowner <> (SELECT c.relowner FROM pg_class c
                            WHERE c.oid = 'vendite.fatture'::regclass)),
    '{}'::text[],
    '4. ogni SECURITY DEFINER applicativa e'' del proprietario delle tabelle o di un superuser'
);

-- ============================================================
-- 5) L'applicazione subisce la RLS
-- ============================================================
SELECT ok(
    (SELECT NOT r.rolbypassrls AND NOT r.rolsuper
       FROM pg_roles r WHERE r.rolname = 'zeroerp_app'),
    '5. zeroerp_app non ha BYPASSRLS ne'' superuser (linee-guida-sql §10.5, punto 3)'
);

SELECT * FROM finish();
ROLLBACK;
