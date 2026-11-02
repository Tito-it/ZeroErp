-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: regola di ripetibilita' dei flussi pratica (D3,
--       analisi-pratiche-workflow-v2). Colonna
--       template_flussi.ripetibilita (MAI/SE_NON_POSITIVO/SEMPRE),
--       guard trg_flussi_a10_guard_ripetibilita_ins,
--       fn_check_ripetibilita_flusso.
--
-- Indice test:
-- 0)  Precondizioni (provisioning + verifica)
-- 1)  Setup: tipo prestazione + 4 template (MAI, MAI2, SNP default, SEMPRE) + pratica
-- 2)  Default colonna: template creato senza ripetibilita -> SE_NON_POSITIVO
-- 3)  MAI: prima istanza ammessa
-- 4)  MAI: seconda istanza vietata (prima ancora aperta)
-- 5)  MAI: seconda istanza vietata anche dopo COMPLETATO NEGATIVO (mai = mai)
-- 6)  MAI: istanza ANNULLATO non consuma la ripetibilita' (nuova istanza ammessa)
-- 7)  SE_NON_POSITIVO: prima istanza ammessa
-- 8)  SE_NON_POSITIVO: seconda istanza vietata con prima ancora aperta
-- 9)  SE_NON_POSITIVO: seconda istanza ammessa dopo COMPLETATO NEGATIVO
-- 10) SE_NON_POSITIVO: terza istanza vietata dopo COMPLETATO POSITIVO
-- 11) SEMPRE: istanze multiple sempre ammesse
-- 12) fn_check_ripetibilita_flusso: false per template MAI gia' istanziato
-- 13) fn_check_ripetibilita_flusso: true per template SEMPRE
-- 14) Cleanup
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. Messa in testa e non in coda
--   apposta: in coda scatterebbero tutti insieme DOPO il cleanup, su righe
--   ormai cancellate, e fallirebbero per un motivo che non riguarda il test.
--   Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(14);

-- =========================================================
-- 0) Precondizioni: provisioning config data (idempotente)
-- =========================================================
INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('BOZZA', 'BOZZA', 'Bozza', true)
ON CONFLICT (codice_interno) DO NOTHING;

INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES
  ('DA_ESEGUIRE', 'DA_ESEGUIRE', 'Da eseguire', true),
  ('IN_CORSO', 'IN_CORSO', 'In corso', true),
  ('COMPLETATO', 'COMPLETATO', 'Completato', true),
  ('ANNULLATO', 'ANNULLATO', 'Annullato', true)
ON CONFLICT (codice_interno) DO NOTHING;

INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE', 'NORMALE', 'Normale', 20, true)
ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_rip_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'BOZZA') AS st_bozza,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE') AS sf_da_eseguire,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'IN_CORSO') AS sf_in_corso,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'COMPLETATO') AS sf_completato,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'ANNULLATO') AS sf_annullato,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE') AS priorita_id;

SELECT ok(
    (SELECT emittente_id IS NOT NULL
        AND st_bozza IS NOT NULL
        AND sf_da_eseguire IS NOT NULL
        AND sf_in_corso IS NOT NULL
        AND sf_completato IS NOT NULL
        AND sf_annullato IS NOT NULL
        AND priorita_id IS NOT NULL
       FROM tmp_rip_refs),
    '0. Precondizioni soddisfatte'
);

-- =========================================================
-- 1) Setup: tipo prestazione, 4 template, pratica
-- =========================================================
CREATE TEMP TABLE tmp_rip_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_RIP', 'TEST_RIP', 'Tipo test ripetibilita', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

-- Template MAI (una sola istanza, sempre)
CREATE TEMP TABLE tmp_rip_tf_mai AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, attivo, ripetibilita)
  VALUES ((SELECT tp_id FROM tmp_rip_tp), 'TF_RIP_MAI', 'Template MAI', 10, true, 'MAI')
  ON CONFLICT (definizione_id, codice) DO UPDATE SET ripetibilita = EXCLUDED.ripetibilita
  RETURNING id
)
SELECT id AS tf_id FROM ins;

-- Template MAI2 (per il caso ANNULLATO non consuma)
CREATE TEMP TABLE tmp_rip_tf_mai2 AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, attivo, ripetibilita)
  VALUES ((SELECT tp_id FROM tmp_rip_tp), 'TF_RIP_MAI2', 'Template MAI 2', 20, true, 'MAI')
  ON CONFLICT (definizione_id, codice) DO UPDATE SET ripetibilita = EXCLUDED.ripetibilita
  RETURNING id
)
SELECT id AS tf_id FROM ins;

-- Template SNP: creato SENZA ripetibilita esplicita -> verifica default
CREATE TEMP TABLE tmp_rip_tf_snp AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, attivo)
  VALUES ((SELECT tp_id FROM tmp_rip_tp), 'TF_RIP_SNP', 'Template default', 30, true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tf_id FROM ins;

-- Template SEMPRE (ripetibile liberamente)
CREATE TEMP TABLE tmp_rip_tf_sempre AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, attivo, ripetibilita)
  VALUES ((SELECT tp_id FROM tmp_rip_tp), 'TF_RIP_SEMPRE', 'Template SEMPRE', 40, true, 'SEMPRE')
  ON CONFLICT (definizione_id, codice) DO UPDATE SET ripetibilita = EXCLUDED.ripetibilita
  RETURNING id
)
SELECT id AS tf_id FROM ins;

CREATE TEMP TABLE tmp_rip_pratica AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_rip_refs),
    (SELECT tp_id FROM tmp_rip_tp),
    (SELECT st_bozza FROM tmp_rip_refs),
    (SELECT priorita_id FROM tmp_rip_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

SELECT ok(
    (SELECT pratica_id IS NOT NULL FROM tmp_rip_pratica),
    '1. Setup completato: pratica creata'
);

-- =========================================================
-- 2) Default colonna: SE_NON_POSITIVO
-- =========================================================
SELECT is(
    (SELECT ripetibilita FROM pratiche.template_flussi
      WHERE id = (SELECT tf_id FROM tmp_rip_tf_snp)),
    'SE_NON_POSITIVO',
    '2. Default ripetibilita = SE_NON_POSITIVO sul template creato senza colonna'
);

-- =========================================================
-- 3) MAI: prima istanza ammessa
-- =========================================================
SELECT lives_ok(
  format('INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id) VALUES (%s, %s, %s)',
    (SELECT pratica_id FROM tmp_rip_pratica),
    (SELECT tf_id FROM tmp_rip_tf_mai),
    (SELECT sf_da_eseguire FROM tmp_rip_refs)),
  '3. MAI: prima istanza ammessa'
);

-- =========================================================
-- 4) MAI: seconda istanza vietata (prima ancora aperta)
-- =========================================================
SELECT throws_ok(
  format('INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id) VALUES (%s, %s, %s)',
    (SELECT pratica_id FROM tmp_rip_pratica),
    (SELECT tf_id FROM tmp_rip_tf_mai),
    (SELECT sf_da_eseguire FROM tmp_rip_refs)),
  NULL, NULL,
  '4. MAI: seconda istanza vietata con prima aperta'
);

-- =========================================================
-- 5) MAI: vietata anche dopo COMPLETATO NEGATIVO
-- =========================================================
-- Percorso valido matrice transizioni: DA_ESEGUIRE -> IN_CORSO -> COMPLETATO.
UPDATE pratiche.flussi
   SET stato_id = (SELECT sf_in_corso FROM tmp_rip_refs)
 WHERE pratica_id = (SELECT pratica_id FROM tmp_rip_pratica)
   AND template_flusso_id = (SELECT tf_id FROM tmp_rip_tf_mai);
UPDATE pratiche.flussi
   SET stato_id = (SELECT sf_completato FROM tmp_rip_refs),
       esito = 'NEGATIVO'
 WHERE pratica_id = (SELECT pratica_id FROM tmp_rip_pratica)
   AND template_flusso_id = (SELECT tf_id FROM tmp_rip_tf_mai);

SELECT throws_ok(
  format('INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id) VALUES (%s, %s, %s)',
    (SELECT pratica_id FROM tmp_rip_pratica),
    (SELECT tf_id FROM tmp_rip_tf_mai),
    (SELECT sf_da_eseguire FROM tmp_rip_refs)),
  NULL, NULL,
  '5. MAI: vietata anche dopo COMPLETATO NEGATIVO (mai = mai)'
);

-- =========================================================
-- 6) MAI: istanza ANNULLATO non consuma la ripetibilita'
-- =========================================================
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
VALUES (
  (SELECT pratica_id FROM tmp_rip_pratica),
  (SELECT tf_id FROM tmp_rip_tf_mai2),
  (SELECT sf_da_eseguire FROM tmp_rip_refs)
);
-- Annulla l'istanza (transizione DA_ESEGUIRE -> ANNULLATO ammessa).
UPDATE pratiche.flussi
   SET stato_id = (SELECT sf_annullato FROM tmp_rip_refs)
 WHERE pratica_id = (SELECT pratica_id FROM tmp_rip_pratica)
   AND template_flusso_id = (SELECT tf_id FROM tmp_rip_tf_mai2);

SELECT lives_ok(
  format('INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id) VALUES (%s, %s, %s)',
    (SELECT pratica_id FROM tmp_rip_pratica),
    (SELECT tf_id FROM tmp_rip_tf_mai2),
    (SELECT sf_da_eseguire FROM tmp_rip_refs)),
  '6. MAI: nuova istanza ammessa dopo annullamento (ANNULLATO non consuma)'
);

-- =========================================================
-- 7) SE_NON_POSITIVO: prima istanza ammessa
-- =========================================================
SELECT lives_ok(
  format('INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id) VALUES (%s, %s, %s)',
    (SELECT pratica_id FROM tmp_rip_pratica),
    (SELECT tf_id FROM tmp_rip_tf_snp),
    (SELECT sf_da_eseguire FROM tmp_rip_refs)),
  '7. SE_NON_POSITIVO: prima istanza ammessa'
);

-- =========================================================
-- 8) SE_NON_POSITIVO: seconda vietata con prima ancora aperta
-- =========================================================
SELECT throws_ok(
  format('INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id) VALUES (%s, %s, %s)',
    (SELECT pratica_id FROM tmp_rip_pratica),
    (SELECT tf_id FROM tmp_rip_tf_snp),
    (SELECT sf_da_eseguire FROM tmp_rip_refs)),
  NULL, NULL,
  '8. SE_NON_POSITIVO: seconda istanza vietata con prima ancora aperta'
);

-- =========================================================
-- 9) SE_NON_POSITIVO: ammessa dopo COMPLETATO NEGATIVO
-- =========================================================
UPDATE pratiche.flussi
   SET stato_id = (SELECT sf_in_corso FROM tmp_rip_refs)
 WHERE pratica_id = (SELECT pratica_id FROM tmp_rip_pratica)
   AND template_flusso_id = (SELECT tf_id FROM tmp_rip_tf_snp);
UPDATE pratiche.flussi
   SET stato_id = (SELECT sf_completato FROM tmp_rip_refs),
       esito = 'NEGATIVO'
 WHERE pratica_id = (SELECT pratica_id FROM tmp_rip_pratica)
   AND template_flusso_id = (SELECT tf_id FROM tmp_rip_tf_snp);

SELECT lives_ok(
  format('INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id) VALUES (%s, %s, %s)',
    (SELECT pratica_id FROM tmp_rip_pratica),
    (SELECT tf_id FROM tmp_rip_tf_snp),
    (SELECT sf_da_eseguire FROM tmp_rip_refs)),
  '9. SE_NON_POSITIVO: seconda istanza ammessa dopo COMPLETATO NEGATIVO (appuntamento rifatto)'
);

-- =========================================================
-- 10) SE_NON_POSITIVO: terza vietata dopo COMPLETATO POSITIVO
-- =========================================================
-- Completa POSITIVO la seconda istanza (l'ultima per id).
UPDATE pratiche.flussi
   SET stato_id = (SELECT sf_in_corso FROM tmp_rip_refs)
 WHERE id = (SELECT max(f.id) FROM pratiche.flussi f
              WHERE f.pratica_id = (SELECT pratica_id FROM tmp_rip_pratica)
                AND f.template_flusso_id = (SELECT tf_id FROM tmp_rip_tf_snp));
UPDATE pratiche.flussi
   SET stato_id = (SELECT sf_completato FROM tmp_rip_refs),
       esito = 'POSITIVO'
 WHERE id = (SELECT max(f.id) FROM pratiche.flussi f
              WHERE f.pratica_id = (SELECT pratica_id FROM tmp_rip_pratica)
                AND f.template_flusso_id = (SELECT tf_id FROM tmp_rip_tf_snp));

SELECT throws_ok(
  format('INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id) VALUES (%s, %s, %s)',
    (SELECT pratica_id FROM tmp_rip_pratica),
    (SELECT tf_id FROM tmp_rip_tf_snp),
    (SELECT sf_da_eseguire FROM tmp_rip_refs)),
  NULL, NULL,
  '10. SE_NON_POSITIVO: terza istanza vietata dopo COMPLETATO POSITIVO'
);

-- =========================================================
-- 11) SEMPRE: istanze multiple sempre ammesse
-- =========================================================
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
VALUES (
  (SELECT pratica_id FROM tmp_rip_pratica),
  (SELECT tf_id FROM tmp_rip_tf_sempre),
  (SELECT sf_da_eseguire FROM tmp_rip_refs)
);
SELECT lives_ok(
  format('INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id) VALUES (%s, %s, %s)',
    (SELECT pratica_id FROM tmp_rip_pratica),
    (SELECT tf_id FROM tmp_rip_tf_sempre),
    (SELECT sf_da_eseguire FROM tmp_rip_refs)),
  '11. SEMPRE: seconda istanza ammessa anche con prima ancora aperta'
);

-- =========================================================
-- 12) fn_check: false per MAI gia' istanziato
-- =========================================================
SELECT is(
    pratiche.fn_check_ripetibilita_flusso(
      (SELECT pratica_id FROM tmp_rip_pratica),
      (SELECT tf_id FROM tmp_rip_tf_mai)
    ),
    false,
    '12. fn_check_ripetibilita_flusso: false per template MAI gia'' istanziato'
);

-- =========================================================
-- 13) fn_check: true per SEMPRE
-- =========================================================
SELECT is(
    pratiche.fn_check_ripetibilita_flusso(
      (SELECT pratica_id FROM tmp_rip_pratica),
      (SELECT tf_id FROM tmp_rip_tf_sempre)
    ),
    true,
    '13. fn_check_ripetibilita_flusso: true per template SEMPRE'
);

-- =========================================================
-- 14) Cleanup (resiliente: gestisce orfani da run precedenti)
-- =========================================================
DELETE FROM pratiche.giornale
WHERE pratica_id IN (
    SELECT id FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_rip_tp)
);
DELETE FROM pratiche.flussi
WHERE pratica_id IN (
    SELECT id FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_rip_tp)
);
DELETE FROM pratiche.pratiche
WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_rip_tp);
DELETE FROM pratiche.template_flussi
WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_rip_tp);
DELETE FROM pratiche.tipi_prestazione
WHERE id = (SELECT tp_id FROM tmp_rip_tp);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
