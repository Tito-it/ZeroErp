-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: aggancio documento->flusso su pratiche.pratiche_sorgenti
--       (brief-db-aggancio-documento-flusso, 2026-06-16)
--
-- Copre:
--   - presenza colonna flusso_id (nullable) + FK -> pratiche.flussi
--   - indice UNIQUE parziale uq_pratiche_sorgenti_flusso_root
--   - enforcement "max 1 ROOT per flusso"
--   - COLLEGATO con flusso_id NULL non vincolato (anche piu' d'uno)
--   - guard coerenza pratica<->flusso (trg_..._a10_guard_coerenza_flusso_ins_upd)
--
-- Indice test:
-- 0) Precondizioni (refs config + provisioning stati flusso)
-- 1) Setup tipo_prestazione + template + 2 pratiche (A, B) + 3 flussi
-- 2) Struttura: colonna flusso_id presente
-- 3) Struttura: flusso_id nullable
-- 4) Struttura: FK fk_pratiche_sorgenti_flusso -> pratiche.flussi
-- 5) Struttura: indice uq_pratiche_sorgenti_flusso_root presente
-- 6) INSERT ROOT preventivo con flusso_id (flusso A1) -> lives
-- 7) Secondo ROOT (uid diverso) sullo STESSO flusso -> throws (max 1 ROOT/flusso)
-- 8) ROOT su flusso DIVERSO della stessa pratica (A2) -> lives
-- 9) COLLEGATO con flusso_id NULL -> lives (non vincolato)
-- 10) Secondo COLLEGATO con flusso_id NULL -> lives (NULL fuori dall'indice parziale)
-- 11) [coerenza] ROOT su pratica A con flusso di pratica B -> throws (493)
-- 12) Cleanup
-- ------------------------------------------------------------
SELECT plan(13);

-- =========================================================
-- 0) Precondizioni: provisioning stati flusso (idempotente) + refs
-- =========================================================
INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('DA_ESEGUIRE', 'DA_ESEGUIRE', 'Da eseguire', true),
       ('IN_CORSO',    'IN_CORSO',    'In corso',    true),
       ('COMPLETATO',  'COMPLETATO',  'Completato',  true)
ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_ps_refs AS
SELECT
  (SELECT id FROM anagrafiche.emittenti_fiscali WHERE attivo = true LIMIT 1) AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti LIMIT 1)                              AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'APERTA')     AS st_aperta,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE') AS priorita_id,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE') AS fl_da_eseguire,
  (SELECT id FROM config.sorgenti WHERE codice_interno = 'PREVENTIVO')       AS src_preventivo,
  (SELECT id FROM config.sorgenti WHERE codice_interno = 'COMMESSA')         AS src_commessa;

SELECT ok(
  (SELECT emittente_id IS NOT NULL AND soggetto_id IS NOT NULL
      AND st_aperta IS NOT NULL AND priorita_id IS NOT NULL
      AND fl_da_eseguire IS NOT NULL
      AND src_preventivo IS NOT NULL AND src_commessa IS NOT NULL
   FROM tmp_ps_refs),
  '0. Precondizioni soddisfatte'
);

-- =========================================================
-- 1) Setup: tipo_prestazione + template (non obbligatorio, ripetibile) +
--    2 pratiche APERTA (A, B) + 3 flussi (A1, A2 su A; B1 su B).
-- =========================================================
CREATE TEMP TABLE tmp_ps_tp AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_PS', 'TEST_PS', 'Tipo test sorgenti-flusso', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_ps_tf AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo, ripetibilita)
  VALUES ((SELECT tp_id FROM tmp_ps_tp), 'TEST_PS_STEP', 'Step test', 10, false, true, 'SEMPRE')
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione = EXCLUDED.descrizione, ripetibilita = EXCLUDED.ripetibilita
  RETURNING id
)
SELECT id AS tf_id FROM ins;

CREATE TEMP TABLE tmp_ps_pa AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_ps_refs), (SELECT tp_id FROM tmp_ps_tp),
          (SELECT soggetto_id FROM tmp_ps_refs), (SELECT st_aperta FROM tmp_ps_refs),
          (SELECT priorita_id FROM tmp_ps_refs))
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

CREATE TEMP TABLE tmp_ps_pb AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_ps_refs), (SELECT tp_id FROM tmp_ps_tp),
          (SELECT soggetto_id FROM tmp_ps_refs), (SELECT st_aperta FROM tmp_ps_refs),
          (SELECT priorita_id FROM tmp_ps_refs))
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

-- Flusso A1 (pratica A)
CREATE TEMP TABLE tmp_ps_fa1 AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM tmp_ps_pa), (SELECT tf_id FROM tmp_ps_tf), (SELECT fl_da_eseguire FROM tmp_ps_refs))
  RETURNING id
)
SELECT id AS flusso_id FROM ins;

-- Flusso A2 (pratica A)
CREATE TEMP TABLE tmp_ps_fa2 AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM tmp_ps_pa), (SELECT tf_id FROM tmp_ps_tf), (SELECT fl_da_eseguire FROM tmp_ps_refs))
  RETURNING id
)
SELECT id AS flusso_id FROM ins;

-- Flusso B1 (pratica B)
CREATE TEMP TABLE tmp_ps_fb1 AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM tmp_ps_pb), (SELECT tf_id FROM tmp_ps_tf), (SELECT fl_da_eseguire FROM tmp_ps_refs))
  RETURNING id
)
SELECT id AS flusso_id FROM ins;

SELECT ok(
  (SELECT (SELECT flusso_id FROM tmp_ps_fa1) IS NOT NULL
      AND (SELECT flusso_id FROM tmp_ps_fa2) IS NOT NULL
      AND (SELECT flusso_id FROM tmp_ps_fb1) IS NOT NULL),
  '1. Setup completato: 2 pratiche + 3 flussi'
);

-- =========================================================
-- 2..5) Struttura
-- =========================================================
SELECT has_column('pratiche', 'pratiche_sorgenti', 'flusso_id',
  '2. pratiche_sorgenti.flusso_id presente');

SELECT col_is_null('pratiche', 'pratiche_sorgenti', 'flusso_id',
  '3. flusso_id nullable');

SELECT fk_ok('pratiche', 'pratiche_sorgenti', 'flusso_id',
             'pratiche', 'flussi', 'id',
  '4. FK flusso_id -> pratiche.flussi(id)');

SELECT has_index('pratiche', 'pratiche_sorgenti', 'uq_pratiche_sorgenti_flusso_root',
  '5. indice uq_pratiche_sorgenti_flusso_root presente');

-- =========================================================
-- 6) INSERT ROOT preventivo con flusso_id (flusso A1) -> lives
-- =========================================================
SELECT lives_ok(
  format(
    'INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link, flusso_id)
     VALUES (%s, %s, %L, ''ROOT'', %s)',
    (SELECT pratica_id FROM tmp_ps_pa),
    (SELECT src_preventivo FROM tmp_ps_refs),
    'prev-A1-001',
    (SELECT flusso_id FROM tmp_ps_fa1)
  ),
  '6. ROOT preventivo agganciato al flusso A1'
);

-- =========================================================
-- 7) Secondo ROOT (uid diverso) sullo STESSO flusso -> throws
-- =========================================================
SELECT throws_ok(
  format(
    'INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link, flusso_id)
     VALUES (%s, %s, %L, ''ROOT'', %s)',
    (SELECT pratica_id FROM tmp_ps_pa),
    (SELECT src_preventivo FROM tmp_ps_refs),
    'prev-A1-002',
    (SELECT flusso_id FROM tmp_ps_fa1)
  ),
  NULL, NULL,
  '7. Secondo ROOT sullo stesso flusso bloccato (max 1 ROOT/flusso)'
);

-- =========================================================
-- 8) ROOT su flusso DIVERSO della stessa pratica (A2) -> lives
-- =========================================================
SELECT lives_ok(
  format(
    'INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link, flusso_id)
     VALUES (%s, %s, %L, ''ROOT'', %s)',
    (SELECT pratica_id FROM tmp_ps_pa),
    (SELECT src_preventivo FROM tmp_ps_refs),
    'prev-A2-001',
    (SELECT flusso_id FROM tmp_ps_fa2)
  ),
  '8. ROOT su flusso diverso della stessa pratica consentito'
);

-- =========================================================
-- 9) COLLEGATO con flusso_id NULL -> lives (non vincolato)
-- =========================================================
SELECT lives_ok(
  format(
    'INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link, flusso_id)
     VALUES (%s, %s, %L, ''COLLEGATO'', NULL)',
    (SELECT pratica_id FROM tmp_ps_pa),
    (SELECT src_commessa FROM tmp_ps_refs),
    'comm-A-001'
  ),
  '9. COLLEGATO con flusso_id NULL consentito'
);

-- =========================================================
-- 10) Secondo COLLEGATO con flusso_id NULL -> lives (NULL fuori indice parziale)
-- =========================================================
SELECT lives_ok(
  format(
    'INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link, flusso_id)
     VALUES (%s, %s, %L, ''COLLEGATO'', NULL)',
    (SELECT pratica_id FROM tmp_ps_pa),
    (SELECT src_commessa FROM tmp_ps_refs),
    'comm-A-002'
  ),
  '10. Secondo COLLEGATO con flusso_id NULL consentito'
);

-- =========================================================
-- 11) [coerenza] ROOT su pratica A con flusso di pratica B -> throws (493)
-- =========================================================
SELECT throws_ok(
  format(
    'INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link, flusso_id)
     VALUES (%s, %s, %L, ''ROOT'', %s)',
    (SELECT pratica_id FROM tmp_ps_pa),
    (SELECT src_preventivo FROM tmp_ps_refs),
    'prev-cross-001',
    (SELECT flusso_id FROM tmp_ps_fb1)
  ),
  NULL, NULL,
  '11. ROOT con flusso di un''altra pratica bloccato (guard coerenza)'
);

-- =========================================================
-- 12) Cleanup
-- =========================================================
DELETE FROM pratiche.pratiche_sorgenti
 WHERE pratica_id IN (SELECT id FROM pratiche.pratiche
                       WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ps_tp));
DELETE FROM pratiche.giornale
 WHERE pratica_id IN (SELECT id FROM pratiche.pratiche
                       WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ps_tp));
DELETE FROM pratiche.flussi
 WHERE pratica_id IN (SELECT id FROM pratiche.pratiche
                       WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ps_tp));
DELETE FROM pratiche.pratiche
 WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ps_tp);
DELETE FROM pratiche.template_flussi
 WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ps_tp);
DELETE FROM pratiche.tipi_prestazione
 WHERE codice_interno = 'TEST_PS';

SELECT pass('12. Cleanup completato');

SELECT * FROM finish();
