-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: assegnazione flusso — policy eligibilita' reparto-first + competenza
--       opzionale (brief-db-assegnazione-flusso §2.2) e trigger giornale.
--       fn_prendi_in_carico_flusso (20260618-05): casi A/B/C/D + guard.
--       Trigger FLUSSO_ASSEGNAZIONE_CAMBIATA (20260618-08).
--
-- Riusa 2 operatori (risorse_umane) gia' esistenti: opA (a cui si imposta in
-- transazione il reparto RepA di test) e opO (l'"altro"). Crea solo 2 reparti
-- di test e i template. Tutto in BEGIN;...ROLLBACK; -> nessun cleanup.
--
-- Indice:
-- 1)  Setup (2 reparti, 2 operatori riusati, template, competenza, pratica)
-- 2)  Caso C (libero): opA prende flusso senza reparto/skill -> TRUE
-- 3)  Caso B (reparto): opA (RepA) prende flusso uo=RepA -> TRUE
-- 4)  Caso B ko: opA prende flusso uo=RepB (non suo) -> FLUSSI_PRESA_NON_ELIGIBILE (496)
-- 5)  Caso A (skill): opA competente prende flusso SKILL -> TRUE
-- 6)  Caso A ko: opO non competente prende flusso SKILL -> FLUSSI_COMPETENZA_MANCANTE
-- 7)  Guard: flusso gia' assegnato a opO -> opA errore FLUSSI_GIA_ASSEGNATO
-- 8)  Giornale: cambio reparto del flusso -> riga FLUSSO_ASSEGNAZIONE_CAMBIATA
-- 9)  Coda: flusso SKILL non assegnato emerge come COMPETENZA per opA
-- ------------------------------------------------------------
BEGIN;
SELECT plan(9);

-- =========================================================
-- 1) Setup
-- =========================================================
INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('BOZZA','BOZZA','Bozza',true) ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('DA_ESEGUIRE','DA_ESEGUIRE','Da eseguire',true) ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE','NORMALE','Normale',20,true) ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE _af AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno='BOZZA') AS st_bozza,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='DA_ESEGUIRE') AS sf_da_eseguire,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno='NORMALE') AS priorita_id;

-- 2 reparti di test
CREATE TEMP TABLE _af_uo AS
WITH ins AS (
  INSERT INTO config.unita_organizzative (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_AF_A','TEST_AF_A','Reparto test A',true),
         ('TEST_AF_B','TEST_AF_B','Reparto test B',true)
  RETURNING id, codice_interno
)
SELECT id AS uo_id, codice_interno FROM ins;

-- 2 operatori esistenti distinti (riuso)
CREATE TEMP TABLE _af_op AS
WITH ops AS (
  SELECT id, row_number() OVER (ORDER BY id) AS rn
    FROM anagrafiche.risorse_umane WHERE attivo=true
)
SELECT 'A'::text AS tag, id AS op_id FROM ops WHERE rn=1
UNION ALL
SELECT 'O', id FROM ops WHERE rn=2;

-- opA: reparto anagrafico = RepA (impostato in transazione, rollback)
UPDATE anagrafiche.risorse_umane
   SET unita_organizzativa_id=(SELECT uo_id FROM _af_uo WHERE codice_interno='TEST_AF_A')
 WHERE id=(SELECT op_id FROM _af_op WHERE tag='A');

-- tipo prestazione + 3 template (ripetibilita SEMPRE)
CREATE TEMP TABLE _af_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_AF','TEST_AF','Tipo test assegnazione flusso',true)
  RETURNING id
) SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE _af_tpl AS WITH t AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, attivo, direzione, ripetibilita)
  VALUES
    ((SELECT tp_id FROM _af_tp),'TF_AF_LIBERO','Libero',10,true,'INTERNA','SEMPRE'),
    ((SELECT tp_id FROM _af_tp),'TF_AF_REPARTO','Reparto',20,true,'INTERNA','SEMPRE'),
    ((SELECT tp_id FROM _af_tp),'TF_AF_SKILL','Skill',30,true,'INTERNA','SEMPRE')
  RETURNING id, codice
) SELECT id, codice FROM t;

-- competenza ATTIVA per opA sul template SKILL (skill-lock)
INSERT INTO pratiche.competenze_flussi (template_flusso_id, unita_organizzativa_id, risorsa_umana_id, attivo)
VALUES (
  (SELECT id FROM _af_tpl WHERE codice='TF_AF_SKILL'),
  (SELECT uo_id FROM _af_uo WHERE codice_interno='TEST_AF_A'),
  (SELECT op_id FROM _af_op WHERE tag='A'), true);

-- pratica assegnata a opA
CREATE TEMP TABLE _af_pratica AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, stato_id, priorita_id, risorsa_umana_id)
  VALUES ((SELECT emittente_id FROM _af),(SELECT tp_id FROM _af_tp),
          (SELECT st_bozza FROM _af),(SELECT priorita_id FROM _af),
          (SELECT op_id FROM _af_op WHERE tag='A'))
  RETURNING id
) SELECT id AS pratica_id FROM ins;

SELECT ok(
  (SELECT count(*) FROM _af_op)=2
  AND (SELECT op_id FROM _af_op WHERE tag='A') IS DISTINCT FROM (SELECT op_id FROM _af_op WHERE tag='O')
  AND (SELECT pratica_id FROM _af_pratica) IS NOT NULL,
  '1. Setup: 2 operatori riusati (distinti), 2 reparti, template, competenza, pratica'
);

-- =========================================================
-- 2) Caso C (libero): opA prende flusso senza reparto/skill -> TRUE
-- =========================================================
CREATE TEMP TABLE _af_fC AS WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM _af_pratica),(SELECT id FROM _af_tpl WHERE codice='TF_AF_LIBERO'),(SELECT sf_da_eseguire FROM _af))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

SELECT is(
  pratiche.fn_prendi_in_carico_flusso((SELECT flusso_id FROM _af_fC),(SELECT op_id FROM _af_op WHERE tag='A')),
  true, '2. Caso C: presa libera consentita (niente reparto/skill)');

-- =========================================================
-- 3) Caso B (reparto): opA in RepA prende flusso uo=RepA -> TRUE
-- =========================================================
CREATE TEMP TABLE _af_fB AS WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, unita_organizzativa_id)
  VALUES ((SELECT pratica_id FROM _af_pratica),(SELECT id FROM _af_tpl WHERE codice='TF_AF_REPARTO'),(SELECT sf_da_eseguire FROM _af),(SELECT uo_id FROM _af_uo WHERE codice_interno='TEST_AF_A'))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

SELECT is(
  pratiche.fn_prendi_in_carico_flusso((SELECT flusso_id FROM _af_fB),(SELECT op_id FROM _af_op WHERE tag='A')),
  true, '3. Caso B: operatore del reparto anagrafico prende il flusso del reparto');

-- =========================================================
-- 4) Caso B ko: opA (RepA) prende flusso uo=RepB -> errore (496)
-- =========================================================
CREATE TEMP TABLE _af_fBko AS WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, unita_organizzativa_id)
  VALUES ((SELECT pratica_id FROM _af_pratica),(SELECT id FROM _af_tpl WHERE codice='TF_AF_REPARTO'),(SELECT sf_da_eseguire FROM _af),(SELECT uo_id FROM _af_uo WHERE codice_interno='TEST_AF_B'))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

SELECT throws_ok(
  format('SELECT pratiche.fn_prendi_in_carico_flusso(%s,%s)',(SELECT flusso_id FROM _af_fBko),(SELECT op_id FROM _af_op WHERE tag='A')),
  NULL, NULL, '4. Caso B ko: operatore non del reparto del flusso (FLUSSI_PRESA_NON_ELIGIBILE)');

-- =========================================================
-- 5) Caso A (skill): opA competente prende flusso SKILL -> TRUE
-- =========================================================
CREATE TEMP TABLE _af_fA AS WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM _af_pratica),(SELECT id FROM _af_tpl WHERE codice='TF_AF_SKILL'),(SELECT sf_da_eseguire FROM _af))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

SELECT is(
  pratiche.fn_prendi_in_carico_flusso((SELECT flusso_id FROM _af_fA),(SELECT op_id FROM _af_op WHERE tag='A')),
  true, '5. Caso A: operatore competente prende il flusso skill-locked');

-- =========================================================
-- 6) Caso A ko: opO non competente prende flusso SKILL -> errore competenza
-- =========================================================
CREATE TEMP TABLE _af_fAko AS WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM _af_pratica),(SELECT id FROM _af_tpl WHERE codice='TF_AF_SKILL'),(SELECT sf_da_eseguire FROM _af))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

SELECT throws_ok(
  format('SELECT pratiche.fn_prendi_in_carico_flusso(%s,%s)',(SELECT flusso_id FROM _af_fAko),(SELECT op_id FROM _af_op WHERE tag='O')),
  NULL, NULL, '6. Caso A ko: non competente su flusso skill-locked (FLUSSI_COMPETENZA_MANCANTE)');

-- =========================================================
-- 7) Guard: flusso assegnato a opO -> opA prova e fallisce
-- =========================================================
CREATE TEMP TABLE _af_fGia AS WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, risorsa_umana_id)
  VALUES ((SELECT pratica_id FROM _af_pratica),(SELECT id FROM _af_tpl WHERE codice='TF_AF_LIBERO'),(SELECT sf_da_eseguire FROM _af),(SELECT op_id FROM _af_op WHERE tag='O'))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

SELECT throws_ok(
  format('SELECT pratiche.fn_prendi_in_carico_flusso(%s,%s)',(SELECT flusso_id FROM _af_fGia),(SELECT op_id FROM _af_op WHERE tag='A')),
  NULL, NULL, '7. Guard: flusso gia'' assegnato ad altro operatore (FLUSSI_GIA_ASSEGNATO)');

-- =========================================================
-- 8) Giornale: su un flusso FRESCO (mai preso in carico), un solo cambio
--    assegnazione -> esattamente UNA riga FLUSSO_ASSEGNAZIONE_CAMBIATA.
--    (la presa in carico, che pure cambia risorsa_umana_id, e' giornalata
--     a sua volta: per isolare il conteggio si usa un flusso dedicato)
-- =========================================================
CREATE TEMP TABLE _af_fG AS WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM _af_pratica),(SELECT id FROM _af_tpl WHERE codice='TF_AF_LIBERO'),(SELECT sf_da_eseguire FROM _af))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

UPDATE pratiche.flussi SET unita_organizzativa_id=(SELECT uo_id FROM _af_uo WHERE codice_interno='TEST_AF_A')
 WHERE id=(SELECT flusso_id FROM _af_fG);

SELECT is(
  (SELECT count(*)::int FROM pratiche.giornale
    WHERE flusso_id=(SELECT flusso_id FROM _af_fG) AND azione='FLUSSO_ASSEGNAZIONE_CAMBIATA'),
  1, '8. Giornale: una riga FLUSSO_ASSEGNAZIONE_CAMBIATA per un cambio assegnazione del flusso');

-- =========================================================
-- 9) Coda: flusso SKILL non assegnato emerge come COMPETENZA per opA
-- =========================================================
CREATE TEMP TABLE _af_fCoda AS WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM _af_pratica),(SELECT id FROM _af_tpl WHERE codice='TF_AF_SKILL'),(SELECT sf_da_eseguire FROM _af))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

SELECT is(
  (SELECT livello FROM pratiche.fn_coda_lavoro_operatore((SELECT op_id FROM _af_op WHERE tag='A'),(SELECT emittente_id FROM _af))
    WHERE flusso_id=(SELECT flusso_id FROM _af_fCoda)),
  'COMPETENZA', '9. Coda: flusso skill non assegnato emerge come COMPETENZA per il competente');

SELECT * FROM finish();
ROLLBACK;
