-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: guard "pratica terminale -> flussi congelati"
--       (pratiche.trgfn_flussi_guard_pratica_terminale,
--        trigger trg_flussi_a10_guard_pratica_terminale_ins_upd)
--
-- Modello: una pratica in stato terminale (nessuna transizione di stato
--          in uscita attiva: CHIUSA, ANNULLATA) e' conclusa; i suoi flussi
--          non sono piu' creabili ne' modificabili.
--
-- Indice test:
-- 0) Precondizioni (provisioning + verifica)
-- 1) Setup tipo_prestazione + 2 pratiche APERTA + flussi manuali
-- 2) [regressione] APERTA: INSERT flusso -> lives
-- 3) [regressione] APERTA: UPDATE stato flusso (DA_ESEGUIRE->IN_CORSO) -> lives
-- 4) [criterio 6] APERTA -> ANNULLATA con flusso attivo -> lives (terminazione permessa)
-- 5) ANNULLATA: INSERT nuovo flusso -> throws (490)
-- 6) ANNULLATA: UPDATE stato flusso (IN_CORSO->COMPLETATO) -> throws (491)
-- 7) ANNULLATA: UPDATE esito/note_esito (stato invariato) -> throws (491)
-- 8) [criterio 6] APERTA -> CHIUSA con flusso attivo -> lives (terminazione permessa)
-- 9) CHIUSA: INSERT nuovo flusso -> throws (490)
-- 10) CHIUSA: UPDATE stato flusso -> throws (491)
-- 11) Cleanup
-- ------------------------------------------------------------
SELECT plan(12);

-- =========================================================
-- 0) Precondizioni: provisioning config data (idempotente)
-- =========================================================
INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('DA_ESEGUIRE', 'DA_ESEGUIRE', 'Da eseguire', true),
       ('IN_CORSO',    'IN_CORSO',    'In corso',    true),
       ('COMPLETATO',  'COMPLETATO',  'Completato',  true)
ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_pt_refs AS
SELECT
  (SELECT id FROM anagrafiche.emittenti_fiscali WHERE attivo = true LIMIT 1) AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti LIMIT 1) AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'APERTA')    AS st_aperta,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'CHIUSA')    AS st_chiusa,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'ANNULLATA') AS st_annullata,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE') AS priorita_id,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE') AS fl_da_eseguire,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'IN_CORSO')    AS fl_in_corso,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'COMPLETATO')  AS fl_completato;

SELECT ok(
  (SELECT emittente_id IS NOT NULL AND soggetto_id IS NOT NULL
      AND st_aperta IS NOT NULL AND st_chiusa IS NOT NULL AND st_annullata IS NOT NULL
      AND priorita_id IS NOT NULL AND fl_da_eseguire IS NOT NULL
      AND fl_in_corso IS NOT NULL AND fl_completato IS NOT NULL
   FROM tmp_pt_refs),
  '0. Precondizioni soddisfatte'
);

-- =========================================================
-- 1) Setup: tipo_prestazione + 2 pratiche create direttamente in APERTA.
--    Flussi MANUALI (template_flusso_id NULL): nessun template obbligatorio
--    -> la chiusura della pratica non e' vincolata; prerequisiti/ripetibilita
--    sono bypassati (guard template-driven). Resta sotto test solo il guard
--    "pratica terminale".
-- =========================================================
CREATE TEMP TABLE tmp_pt_tp AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_PT', 'TEST_PT', 'Tipo test pratica terminale', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

-- Pratica 1 (percorso ANNULLATA)
CREATE TEMP TABLE tmp_pt_pratica1 AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_pt_refs),
    (SELECT tp_id FROM tmp_pt_tp),
    (SELECT soggetto_id FROM tmp_pt_refs),
    (SELECT st_aperta FROM tmp_pt_refs),
    (SELECT priorita_id FROM tmp_pt_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

-- Pratica 2 (percorso CHIUSA)
CREATE TEMP TABLE tmp_pt_pratica2 AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_pt_refs),
    (SELECT tp_id FROM tmp_pt_tp),
    (SELECT soggetto_id FROM tmp_pt_refs),
    (SELECT st_aperta FROM tmp_pt_refs),
    (SELECT priorita_id FROM tmp_pt_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

SELECT ok(
  (SELECT (SELECT pratica_id FROM tmp_pt_pratica1) IS NOT NULL
      AND (SELECT pratica_id FROM tmp_pt_pratica2) IS NOT NULL),
  '1. Setup completato: tipo prestazione + 2 pratiche APERTA'
);

-- =========================================================
-- 2) [regressione] APERTA: INSERT flusso manuale -> lives
-- =========================================================
SELECT lives_ok(
  format(
    'INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
     VALUES (%s, NULL, %s)',
    (SELECT pratica_id FROM tmp_pt_pratica1),
    (SELECT fl_da_eseguire FROM tmp_pt_refs)
  ),
  '2. APERTA: INSERT flusso consentito (regressione)'
);

-- Cattura il flusso appena creato sulla pratica 1
CREATE TEMP TABLE tmp_pt_flusso1 AS
SELECT id AS flusso_id
  FROM pratiche.flussi
 WHERE pratica_id = (SELECT pratica_id FROM tmp_pt_pratica1)
 ORDER BY id DESC
 LIMIT 1;

-- =========================================================
-- 3) [regressione] APERTA: UPDATE stato flusso DA_ESEGUIRE->IN_CORSO -> lives
-- =========================================================
SELECT lives_ok(
  format(
    'UPDATE pratiche.flussi SET stato_id = %s WHERE id = %s',
    (SELECT fl_in_corso FROM tmp_pt_refs),
    (SELECT flusso_id FROM tmp_pt_flusso1)
  ),
  '3. APERTA: transizione flusso consentita (regressione)'
);

-- =========================================================
-- 4) [criterio 6] APERTA -> ANNULLATA con flusso ancora attivo -> lives
--    L'atto di rendere terminale la pratica resta permesso.
-- =========================================================
SELECT lives_ok(
  format(
    'UPDATE pratiche.pratiche SET stato_id = %s WHERE id = %s',
    (SELECT st_annullata FROM tmp_pt_refs),
    (SELECT pratica_id FROM tmp_pt_pratica1)
  ),
  '4. APERTA -> ANNULLATA con flusso attivo: terminazione consentita'
);

-- =========================================================
-- 5) ANNULLATA: INSERT nuovo flusso -> throws
-- =========================================================
SELECT throws_ok(
  format(
    'INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
     VALUES (%s, NULL, %s)',
    (SELECT pratica_id FROM tmp_pt_pratica1),
    (SELECT fl_da_eseguire FROM tmp_pt_refs)
  ),
  NULL, NULL,
  '5. ANNULLATA: creazione nuovo flusso bloccata'
);

-- =========================================================
-- 6) ANNULLATA: UPDATE stato flusso (IN_CORSO->COMPLETATO + esito) -> throws
-- =========================================================
SELECT throws_ok(
  format(
    'UPDATE pratiche.flussi SET stato_id = %s, esito = ''POSITIVO'' WHERE id = %s',
    (SELECT fl_completato FROM tmp_pt_refs),
    (SELECT flusso_id FROM tmp_pt_flusso1)
  ),
  NULL, NULL,
  '6. ANNULLATA: transizione di stato del flusso bloccata'
);

-- =========================================================
-- 7) ANNULLATA: UPDATE esito/note_esito (stato invariato) -> throws
-- =========================================================
SELECT throws_ok(
  format(
    'UPDATE pratiche.flussi SET esito = ''POSITIVO'', note_esito = ''x'' WHERE id = %s',
    (SELECT flusso_id FROM tmp_pt_flusso1)
  ),
  NULL, NULL,
  '7. ANNULLATA: modifica esito/note_esito bloccata'
);

-- =========================================================
-- 8) [criterio 6] APERTA -> CHIUSA con flusso attivo -> lives
--    (nessun template obbligatorio -> guard chiusura non blocca)
-- =========================================================
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
VALUES (
  (SELECT pratica_id FROM tmp_pt_pratica2),
  NULL,
  (SELECT fl_da_eseguire FROM tmp_pt_refs)
);

CREATE TEMP TABLE tmp_pt_flusso2 AS
SELECT id AS flusso_id
  FROM pratiche.flussi
 WHERE pratica_id = (SELECT pratica_id FROM tmp_pt_pratica2)
 ORDER BY id DESC
 LIMIT 1;

SELECT lives_ok(
  format(
    'UPDATE pratiche.pratiche SET stato_id = %s WHERE id = %s',
    (SELECT st_chiusa FROM tmp_pt_refs),
    (SELECT pratica_id FROM tmp_pt_pratica2)
  ),
  '8. APERTA -> CHIUSA con flusso attivo: terminazione consentita'
);

-- =========================================================
-- 9) CHIUSA: INSERT nuovo flusso -> throws
-- =========================================================
SELECT throws_ok(
  format(
    'INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
     VALUES (%s, NULL, %s)',
    (SELECT pratica_id FROM tmp_pt_pratica2),
    (SELECT fl_da_eseguire FROM tmp_pt_refs)
  ),
  NULL, NULL,
  '9. CHIUSA: creazione nuovo flusso bloccata'
);

-- =========================================================
-- 10) CHIUSA: UPDATE stato flusso -> throws
-- =========================================================
SELECT throws_ok(
  format(
    'UPDATE pratiche.flussi SET stato_id = %s WHERE id = %s',
    (SELECT fl_in_corso FROM tmp_pt_refs),
    (SELECT flusso_id FROM tmp_pt_flusso2)
  ),
  NULL, NULL,
  '10. CHIUSA: modifica del flusso bloccata'
);

-- =========================================================
-- 11) Cleanup
-- =========================================================
DELETE FROM pratiche.giornale
 WHERE pratica_id IN (SELECT id FROM pratiche.pratiche
                       WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_pt_tp));
DELETE FROM pratiche.flussi
 WHERE pratica_id IN (SELECT id FROM pratiche.pratiche
                       WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_pt_tp));
DELETE FROM pratiche.pratiche
 WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_pt_tp);
DELETE FROM pratiche.tipi_prestazione
 WHERE codice_interno = 'TEST_PT';

SELECT pass('11. Cleanup completato');

SELECT * FROM finish();
