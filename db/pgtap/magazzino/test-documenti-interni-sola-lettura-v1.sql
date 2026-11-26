-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- Test: i documenti interni di magazzino sono in SOLA LETTURA per
--   l'applicazione (Lotto 2, P-5c, brief-db-magazzino-tutte-le-scritture-dal-verbo):
--   inventari, rettifiche, trasferimenti e le loro righe li scrivono i verbi
--   DEFINER (nascita per famiglia, verbi comuni, registrazione fn_posta_*).
--   ChangeSet: 90_end/20261123-12.
--
-- Elenco test (plan 9):
--    1) all'applicazione SELECT si', INSERT, UPDATE e DELETE no, sulle sei tabelle
--    2) come applicazione, UPDATE degli inventari: 42501
--    3) come applicazione, UPDATE delle righe d'inventario: 42501
--    4) come applicazione, UPDATE delle rettifiche: 42501
--    5) come applicazione, UPDATE delle righe di rettifica: 42501
--    6) come applicazione, UPDATE dei trasferimenti: 42501
--    7) come applicazione, UPDATE delle righe di trasferimento: 42501
--    8) come applicazione, INSERT negli inventari: 42501
--    9) come applicazione, DELETE delle righe d'inventario: 42501
--
-- Scopo:
--  - 1 e' la terza sede della postura (linee-guida-sql §11.8): il forward
--    90_end/20261123-12, il loop 90_end/ci_apply/20260205-41 e il blocco
--    «POSTURA DICHIARATA» di scripts/sql/provision_zeroerp.sql devono dire la
--    stessa cosa, e su un database ricostruito da zero lo dice solo questo test.
--  - ⚠️ Gira come l'APPLICAZIONE (runner di default): 2-9 sono veri solo li'.
--  - ⚠️ 2-9 nominano colonne che esistono: su una colonna assente il parser
--    risponderebbe 42703, rosso per il motivo sbagliato.
--  - La strada che resta aperta (i verbi e i builder dbops.fn_pgtap_crea_<documento>
--    che li chiamano) la provano come applicazione i pgTAP dei documenti
--    interni: test-verbi-documenti-interni-v1, test-documenti-interni-guard-v1 e
--    i diciassette portati sui builder (brief, §5.6). Qui non si ricopia.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- 1
SELECT is(
  (SELECT string_agg(t || ':' || p, ', ' ORDER BY t, p)
     FROM unnest(ARRAY[
              'magazzino.inventari', 'magazzino.inventari_righe',
              'magazzino.rettifiche', 'magazzino.rettifiche_righe',
              'magazzino.trasferimenti', 'magazzino.trasferimenti_righe']) t,
          unnest(ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE']) p
    WHERE has_table_privilege('zeroerp_app', t, p) IS DISTINCT FROM (p = 'SELECT')),
  NULL,
  '1) documenti interni di magazzino e righe: all''applicazione solo SELECT');

-- 2-9
SELECT throws_ok($$UPDATE magazzino.inventari SET id = id WHERE false$$,
  '42501', NULL, '2) come applicazione, un UPDATE degli inventari risponde 42501');
SELECT throws_ok($$UPDATE magazzino.inventari_righe SET id = id WHERE false$$,
  '42501', NULL, '3) come applicazione, un UPDATE delle righe d''inventario risponde 42501');
SELECT throws_ok($$UPDATE magazzino.rettifiche SET id = id WHERE false$$,
  '42501', NULL, '4) come applicazione, un UPDATE delle rettifiche risponde 42501');
SELECT throws_ok($$UPDATE magazzino.rettifiche_righe SET id = id WHERE false$$,
  '42501', NULL, '5) come applicazione, un UPDATE delle righe di rettifica risponde 42501');
SELECT throws_ok($$UPDATE magazzino.trasferimenti SET id = id WHERE false$$,
  '42501', NULL, '6) come applicazione, un UPDATE dei trasferimenti risponde 42501');
SELECT throws_ok($$UPDATE magazzino.trasferimenti_righe SET id = id WHERE false$$,
  '42501', NULL, '7) come applicazione, un UPDATE delle righe di trasferimento risponde 42501');
SELECT throws_ok($$INSERT INTO magazzino.inventari (magazzino_id) SELECT 1 WHERE false$$,
  '42501', NULL, '8) come applicazione, un INSERT negli inventari risponde 42501');
SELECT throws_ok($$DELETE FROM magazzino.inventari_righe WHERE false$$,
  '42501', NULL, '9) come applicazione, un DELETE delle righe d''inventario risponde 42501');

SELECT * FROM finish();
ROLLBACK;
