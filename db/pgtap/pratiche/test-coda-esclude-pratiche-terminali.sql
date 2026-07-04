-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: fn_coda_lavoro_operatore esclude i flussi di pratiche TERMINALI
--       (fix 20260614-02). Un flusso attivo (DA_ESEGUIRE) assegnato a un
--       operatore compare in coda finche' la pratica e' operativa; quando
--       la pratica diventa terminale (ANNULLATA) sparisce dalla coda.
--
-- Indice test:
-- 0) Precondizioni (provisioning + verifica; richiede una risorsa umana)
-- 1) Setup: pratica APERTA + flusso DA_ESEGUIRE assegnato all'operatore
-- 2) Pratica APERTA: il flusso compare in coda (regressione) [skip se no risorsa]
-- 3) Pratica ANNULLATA: il flusso sparisce dalla coda (fix) [skip se no risorsa]
-- 4) Cleanup
-- ------------------------------------------------------------
SELECT plan(5);

-- =========================================================
-- 0) Precondizioni: provisioning config data (idempotente)
-- =========================================================
INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('APERTA', 'APERTA', 'Aperta', true),
       ('ANNULLATA', 'ANNULLATA', 'Annullata', true) ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('DA_ESEGUIRE', 'DA_ESEGUIRE', 'Da eseguire', true) ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE', 'NORMALE', 'Normale', 20, true) ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_ct_refs AS
SELECT
  (SELECT id FROM anagrafiche.emittenti_fiscali WHERE attivo = true LIMIT 1) AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti LIMIT 1) AS soggetto_id,
  (SELECT id FROM anagrafiche.risorse_umane ORDER BY id LIMIT 1) AS risorsa_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'APERTA') AS st_aperta,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'ANNULLATA') AS st_annullata,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE') AS fl_da_eseguire,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE') AS priorita_id;

SELECT ok(
  (SELECT emittente_id IS NOT NULL AND st_aperta IS NOT NULL
      AND st_annullata IS NOT NULL AND fl_da_eseguire IS NOT NULL
      AND priorita_id IS NOT NULL
   FROM tmp_ct_refs),
  '0. Precondizioni soddisfatte (config presente)'
);

-- =========================================================
-- 1) Setup: pratica APERTA + flusso DA_ESEGUIRE assegnato all'operatore
--    (livello ASSEGNATO: basta flussi.risorsa_umana_id = operatore)
-- =========================================================
CREATE TEMP TABLE tmp_ct_tp AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_CODA_TERM', 'TEST_CODA_TERM', 'Tipo test coda terminale', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

-- Template non obbligatorio (il flusso e' template-driven; non obbligatorio
-- per non innescare l'auto-chiusura al completamento).
CREATE TEMP TABLE tmp_ct_tf AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo)
  VALUES ((SELECT tp_id FROM tmp_ct_tp), 'TEST_CT_STEP', 'Step coda', 10, false, true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tf_id FROM ins;

CREATE TEMP TABLE tmp_ct_pratica AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_ct_refs),
    (SELECT tp_id FROM tmp_ct_tp),
    (SELECT soggetto_id FROM tmp_ct_refs),
    (SELECT st_aperta FROM tmp_ct_refs),
    (SELECT priorita_id FROM tmp_ct_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

-- Flusso (template-driven) assegnato all'operatore, se esiste una risorsa.
CREATE TEMP TABLE tmp_ct_flusso AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, risorsa_umana_id)
  SELECT (SELECT pratica_id FROM tmp_ct_pratica),
         (SELECT tf_id FROM tmp_ct_tf),
         (SELECT fl_da_eseguire FROM tmp_ct_refs),
         (SELECT risorsa_id FROM tmp_ct_refs)
  WHERE (SELECT risorsa_id FROM tmp_ct_refs) IS NOT NULL
  RETURNING id
)
SELECT id AS flusso_id FROM ins;

SELECT ok(
  (SELECT pratica_id IS NOT NULL FROM tmp_ct_pratica),
  '1. Setup completato: pratica APERTA creata'
);

-- =========================================================
-- 2) Pratica APERTA: il flusso compare in coda (regressione)
-- =========================================================
SELECT CASE
  WHEN (SELECT risorsa_id FROM tmp_ct_refs) IS NULL THEN
    skip('2. Nessuna risorsa umana nel DB di test: coda non verificabile', 1)
  ELSE
    ok(
      EXISTS (
        SELECT 1 FROM pratiche.fn_coda_lavoro_operatore(
                        (SELECT risorsa_id FROM tmp_ct_refs),
                        (SELECT emittente_id FROM tmp_ct_refs))
         WHERE flusso_id = (SELECT flusso_id FROM tmp_ct_flusso)
      ),
      '2. Pratica APERTA: il flusso assegnato compare in coda'
    )
END;

-- =========================================================
-- 3) Pratica ANNULLATA: il flusso sparisce dalla coda (fix)
-- =========================================================
UPDATE pratiche.pratiche
   SET stato_id = (SELECT st_annullata FROM tmp_ct_refs)
 WHERE id = (SELECT pratica_id FROM tmp_ct_pratica);

SELECT CASE
  WHEN (SELECT risorsa_id FROM tmp_ct_refs) IS NULL THEN
    skip('3. Nessuna risorsa umana nel DB di test: coda non verificabile', 1)
  ELSE
    ok(
      NOT EXISTS (
        SELECT 1 FROM pratiche.fn_coda_lavoro_operatore(
                        (SELECT risorsa_id FROM tmp_ct_refs),
                        (SELECT emittente_id FROM tmp_ct_refs))
         WHERE flusso_id = (SELECT flusso_id FROM tmp_ct_flusso)
      ),
      '3. Pratica ANNULLATA: il flusso non compare piu'' in coda'
    )
END;

-- =========================================================
-- 4) Cleanup
-- =========================================================
DELETE FROM pratiche.giornale
 WHERE pratica_id IN (SELECT id FROM pratiche.pratiche
                       WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ct_tp));
DELETE FROM pratiche.flussi
 WHERE pratica_id IN (SELECT id FROM pratiche.pratiche
                       WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ct_tp));
DELETE FROM pratiche.pratiche
 WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ct_tp);
DELETE FROM pratiche.template_flussi
 WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ct_tp);
DELETE FROM pratiche.tipi_prestazione
 WHERE codice_interno = 'TEST_CODA_TERM';

SELECT pass('4. Cleanup completato');

SELECT * FROM finish();
