-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test STRUTTURALE: sulle viste l'applicazione ha solo SELECT
--
-- ChangeSet: 90_end/20261123-47 · il ramo per tipo del loop 90_end/ci_apply/20260205-41
--            · il blocco «POSTURA DICHIARATA: le viste» di scripts/sql/provision_zeroerp.sql
-- Brief: brief-db-porte-aperte-dalla-sola-guc §5 (D-V), giro 3
--
-- ⭐ PERCHE'. Una vista aggiornabile senza security_invoker controlla i permessi
--   sulla tabella sotto come il suo proprietario: con INSERT, UPDATE o DELETE
--   sulla vista l'app scriverebbe anche una tabella che ha in sola lettura. Il
--   test guarda la regola, non le viste di oggi: una vista nuova che nascesse
--   col DML all'app (i privilegi di default non distinguono le viste dalle
--   tabelle) lo fa diventare rosso dopo la passata ci_apply, cioe' in CI.
--
-- ⚠️ GIRA COME L'APPLICAZIONE (runner di default). Il caso costruito (una vista
--   nuova in uno schema applicativo) chiede DDL che l'app non puo' fare: il
--   presidio e' il criterio sul catalogo, che vale per ogni vista presente, e il
--   test 3 impedisce che passi a vuoto. Il test 4 e' il comportamento: il
--   privilegio si controlla prima di guardare le righe.
--
-- Il perimetro: tutte le viste e le materializzate fuori dal catalogo di
--   sistema. `django` resta fuori: i suoi oggetti sono dell'applicazione
--   (linee-guida-sql §11.9). Le viste di `public` delle estensioni (pgTAP,
--   PostGIS) sono dentro: le chiude il provisioning, fase post.
--
-- Elenco test (plan 5):
--   1 : nessuna vista da' all'app INSERT, UPDATE o DELETE
--   2 : la lettura resta: ogni vista fuori da maintenance l'app la legge
--   3 : il perimetro non e' vuoto: ci sono viste aggiornabili da guardare
--   4 : come app, UPDATE … WHERE false su una vista aggiornabile del proprietario
--       senza security_invoker: 42501
--   5 : idem con DELETE
--
-- Read-only: tutto dentro BEGIN;/ROLLBACK;. Nessuna riga scritta.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il file non attraversa tabelle in RLS, ma la riga sta
-- qui perche' il preambolo e' un contratto (guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- La vista del caso di comportamento: la prima aggiornabile del proprietario
-- senza security_invoker, con una sua colonna (il parser risolve i nomi prima
-- del controllo dei permessi: con una colonna assente risponderebbe 42703).
CREATE TEMP TABLE tmp_vista AS
SELECT c.oid::regclass::text AS vista,
       (SELECT a.attname::text
          FROM pg_attribute a
         WHERE a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
         ORDER BY a.attnum
         LIMIT 1) AS colonna
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relkind = 'v'
   AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'django', 'public', 'maintenance')
   AND pg_get_userbyid(c.relowner) = 'zeroerp_owner'
   AND pg_relation_is_updatable(c.oid::regclass, false) & 4 = 4      -- UPDATE
   AND pg_relation_is_updatable(c.oid::regclass, false) & 16 = 16    -- DELETE
   AND NOT COALESCE(c.reloptions @> ARRAY['security_invoker=true'], false)
 ORDER BY 1
 LIMIT 1;

SELECT is_empty(
    $$SELECT c.oid::regclass::text
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE c.relkind IN ('v', 'm')
         AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'django')
         AND (   has_table_privilege('zeroerp_app', c.oid, 'INSERT')
              OR has_table_privilege('zeroerp_app', c.oid, 'UPDATE')
              OR has_table_privilege('zeroerp_app', c.oid, 'DELETE'))$$,
    '1. nessuna vista da'' all''app INSERT, UPDATE o DELETE');

SELECT is_empty(
    $$SELECT c.oid::regclass::text
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE c.relkind IN ('v', 'm')
         AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'django', 'maintenance')
         AND NOT has_table_privilege('zeroerp_app', c.oid, 'SELECT')$$,
    '2. la lettura resta: ogni vista fuori da maintenance l''app la legge');

SELECT cmp_ok(
    (SELECT count(*)::int
       FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE c.relkind = 'v'
        AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'django', 'public')
        AND pg_relation_is_updatable(c.oid::regclass, false) <> 0),
    '>', 0,
    '3. il perimetro non e'' vuoto: ci sono viste aggiornabili da guardare');

SELECT throws_ok(
    format('UPDATE %s SET %I = %I WHERE false',
           (SELECT vista FROM tmp_vista), (SELECT colonna FROM tmp_vista), (SELECT colonna FROM tmp_vista)),
    '42501', NULL,
    '4. come app, UPDATE su una vista aggiornabile del proprietario senza security_invoker: 42501');

SELECT throws_ok(
    format('DELETE FROM %s WHERE false', (SELECT vista FROM tmp_vista)),
    '42501', NULL,
    '5. come app, DELETE dalla stessa vista: 42501');

SELECT * FROM finish();
ROLLBACK;
