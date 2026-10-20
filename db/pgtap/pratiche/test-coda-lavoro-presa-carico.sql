-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: fn_coda_lavoro_operatore e fn_prendi_in_carico_flusso
--
-- Indice test:
-- 0) Precondizioni
-- 1) Setup: tipo prestazione, template flusso, competenza, pratica, flusso
-- 2) Coda lavoro: flusso assegnato appare come ASSEGNATO
-- 3) Coda lavoro: flusso non assegnato con competenza appare come COMPETENZA
--    (REPARTO coperto nel file dedicato test-assegnazione-flusso-eligibilita.sql,
--     policy reparto-first 2026-06-18)
-- 4) Coda lavoro: nessun duplicato tra livelli
-- 5) Prendi in carico: flusso DA_ESEGUIRE con competenza — OK
-- 6) Prendi in carico: flusso gia' assegnato allo stesso — FALSE (noop)
-- 7) Prendi in carico: flusso gia' assegnato ad altro — ERRORE
-- 8) Prendi in carico: stato errato (IN_CORSO) — ERRORE
-- 9) Prendi in carico: senza competenza — ERRORE
-- 10) Prendi in carico: parametri NULL — ERRORE
-- 11) Coda lavoro: stato_flusso_descrizione = descrizione umana dello stato
-- 12) Cleanup
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

SELECT plan(13);

-- =========================================================
-- 0) Precondizioni
-- =========================================================
CREATE TEMP TABLE tmp_cl_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'BOZZA') AS st_bozza,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'APERTA') AS st_aperta,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE') AS sf_da_eseguire,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'IN_CORSO') AS sf_in_corso,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE') AS priorita_id;

-- Due risorse umane e un reparto COSTRUITI, non pescati dalla macchina: su un
-- database ricostruito da zero non c'e' nessuna risorsa umana da pescare, e il
-- file moriva sul NOT NULL di competenze_flussi. Il reparto e' di prova e non
-- e' il reparto anagrafico di nessuno dei due: i flussi che lo portano non
-- cadono nel livello REPARTO (coperto in test-assegnazione-flusso-eligibilita).
-- ⛔ Cio' che il builder scrive si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_cl_op1 AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('coda lavoro 1', false);
CREATE TEMP TABLE tmp_cl_op2 AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('coda lavoro 2', false);
CREATE TEMP TABLE tmp_cl_uo AS
WITH ins AS (
  INSERT INTO config.unita_organizzative (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_CL_UO', 'TEST_CL_UO', 'Reparto test coda lavoro', true)
  RETURNING id
)
SELECT id AS uo_id FROM ins;
CREATE TEMP TABLE tmp_cl_risorse AS
SELECT
  (SELECT risorsa_umana_id FROM tmp_cl_op1) AS risorsa_1_id,
  (SELECT risorsa_umana_id FROM tmp_cl_op2) AS risorsa_2_id,
  (SELECT uo_id FROM tmp_cl_uo) AS uo_id;

SELECT ok(
  (SELECT emittente_id IS NOT NULL AND st_bozza IS NOT NULL AND sf_da_eseguire IS NOT NULL
      AND priorita_id IS NOT NULL
   FROM tmp_cl_refs)
  AND (SELECT risorsa_1_id IS NOT NULL AND risorsa_2_id IS NOT NULL AND uo_id IS NOT NULL
       FROM tmp_cl_risorse),
  '0. Precondizioni soddisfatte'
);

-- =========================================================
-- 1) Setup: tipo prestazione, template flusso, competenza, pratica, flussi
-- =========================================================
-- Tipo prestazione
CREATE TEMP TABLE tmp_cl_tp AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_CL', 'TEST_CL', 'Tipo test coda lavoro', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

-- Template flusso
CREATE TEMP TABLE tmp_cl_tf AS
WITH ins AS (
  -- ripetibilita='SEMPRE': il test crea piu' istanze dello stesso template
  -- nella stessa pratica (livelli coda); il default SE_NON_POSITIVO le vieterebbe.
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, direzione, attivo, ripetibilita)
  VALUES (
    (SELECT tp_id FROM tmp_cl_tp),
    'TEST_CL_STEP', 'Step test coda lavoro', 10, false, 'INTERNA', true, 'SEMPRE'
  )
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione = EXCLUDED.descrizione, ripetibilita = EXCLUDED.ripetibilita
  RETURNING id
)
SELECT id AS tf_id FROM ins;

-- Competenza: risorsa_1 abilitata, risorsa_2 NO
INSERT INTO pratiche.competenze_flussi (template_flusso_id, unita_organizzativa_id, risorsa_umana_id, attivo)
VALUES (
  (SELECT tf_id FROM tmp_cl_tf),
  (SELECT uo_id FROM tmp_cl_risorse),
  (SELECT risorsa_1_id FROM tmp_cl_risorse),
  true
)
ON CONFLICT (template_flusso_id, unita_organizzativa_id, risorsa_umana_id) DO UPDATE SET attivo = true;

-- Pratica APERTA, interna (senza soggetto): la coda non guarda il cliente,
-- e un soggetto «il primo per id» era una pesca dalla macchina.
CREATE TEMP TABLE tmp_cl_pratica AS
WITH ins_bozza AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_cl_refs),
    (SELECT tp_id FROM tmp_cl_tp),
    (SELECT st_bozza FROM tmp_cl_refs),
    (SELECT priorita_id FROM tmp_cl_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins_bozza;

UPDATE pratiche.pratiche
   SET stato_id = (SELECT st_aperta FROM tmp_cl_refs)
 WHERE id = (SELECT pratica_id FROM tmp_cl_pratica);

-- Flusso A: assegnato a risorsa_1, DA_ESEGUIRE
CREATE TEMP TABLE tmp_cl_flusso_a AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, risorsa_umana_id, unita_organizzativa_id, sequenza)
  VALUES (
    (SELECT pratica_id FROM tmp_cl_pratica),
    (SELECT tf_id FROM tmp_cl_tf),
    (SELECT sf_da_eseguire FROM tmp_cl_refs),
    (SELECT risorsa_1_id FROM tmp_cl_risorse),
    (SELECT uo_id FROM tmp_cl_risorse),
    10
  )
  RETURNING id
)
SELECT id AS flusso_id FROM ins;

-- Flusso B: non assegnato, DA_ESEGUIRE (per test COMPETENZA)
CREATE TEMP TABLE tmp_cl_flusso_b AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, risorsa_umana_id, unita_organizzativa_id, sequenza)
  VALUES (
    (SELECT pratica_id FROM tmp_cl_pratica),
    (SELECT tf_id FROM tmp_cl_tf),
    (SELECT sf_da_eseguire FROM tmp_cl_refs),
    NULL,
    (SELECT uo_id FROM tmp_cl_risorse),
    20
  )
  RETURNING id
)
SELECT id AS flusso_id FROM ins;

-- Flusso C: assegnato a risorsa_2, DA_ESEGUIRE (usato al test 8: portato a IN_CORSO)
CREATE TEMP TABLE tmp_cl_flusso_c AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, risorsa_umana_id, unita_organizzativa_id, sequenza)
  VALUES (
    (SELECT pratica_id FROM tmp_cl_pratica),
    (SELECT tf_id FROM tmp_cl_tf),
    (SELECT sf_da_eseguire FROM tmp_cl_refs),
    (SELECT risorsa_2_id FROM tmp_cl_risorse),
    (SELECT uo_id FROM tmp_cl_risorse),
    30
  )
  RETURNING id
)
SELECT id AS flusso_id FROM ins;

SELECT pass('1. Setup completato');

-- =========================================================
-- 2) Coda: flusso A assegnato → ASSEGNATO
-- =========================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM pratiche.fn_coda_lavoro_operatore(
      (SELECT risorsa_1_id FROM tmp_cl_risorse),
      (SELECT emittente_id FROM tmp_cl_refs)
    ) WHERE livello = 'ASSEGNATO'
      AND flusso_id = (SELECT flusso_id FROM tmp_cl_flusso_a)
  ),
  '2. Flusso assegnato appare come ASSEGNATO'
);

-- =========================================================
-- 3) Coda: flusso B non assegnato con competenza → COMPETENZA
-- =========================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM pratiche.fn_coda_lavoro_operatore(
      (SELECT risorsa_1_id FROM tmp_cl_risorse),
      (SELECT emittente_id FROM tmp_cl_refs)
    ) WHERE livello = 'COMPETENZA'
      AND flusso_id = (SELECT flusso_id FROM tmp_cl_flusso_b)
  ),
  '3. Flusso non assegnato con competenza appare come COMPETENZA'
);

-- =========================================================
-- 4) Nessun duplicato tra livelli
-- =========================================================
SELECT is(
  (SELECT count(*) FROM (
    SELECT flusso_id, count(*) AS cnt
    FROM pratiche.fn_coda_lavoro_operatore(
      (SELECT risorsa_1_id FROM tmp_cl_risorse),
      (SELECT emittente_id FROM tmp_cl_refs)
    )
    GROUP BY flusso_id
    HAVING count(*) > 1
  ) dup),
  0::BIGINT,
  '4. Nessun duplicato tra livelli'
);

-- =========================================================
-- 5) Prendi in carico: flusso B (non assegnato, DA_ESEGUIRE, competenza) — OK
-- =========================================================
SELECT is(
  pratiche.fn_prendi_in_carico_flusso(
    (SELECT flusso_id FROM tmp_cl_flusso_b),
    (SELECT risorsa_1_id FROM tmp_cl_risorse)
  ),
  TRUE,
  '5. Prendi in carico flusso DA_ESEGUIRE con competenza — TRUE'
);

-- =========================================================
-- 6) Prendi in carico: stesso flusso, stesso operatore — FALSE (noop)
-- =========================================================
-- Prima riporta a DA_ESEGUIRE e riassegna per testare
-- In realta' ora e' assegnato, quindi proviamo di nuovo
SELECT is(
  pratiche.fn_prendi_in_carico_flusso(
    (SELECT flusso_id FROM tmp_cl_flusso_b),
    (SELECT risorsa_1_id FROM tmp_cl_risorse)
  ),
  FALSE,
  '6. Prendi in carico stesso operatore — FALSE (noop)'
);

-- =========================================================
-- 7) Prendi in carico: flusso gia' assegnato a risorsa_1, risorsa_2 prova — ERRORE
-- =========================================================
-- Flusso A e' assegnato a risorsa_1 e in DA_ESEGUIRE
SELECT throws_ok(
  format('SELECT pratiche.fn_prendi_in_carico_flusso(%s, %s)',
    (SELECT flusso_id FROM tmp_cl_flusso_a),
    (SELECT risorsa_2_id FROM tmp_cl_risorse)),
  NULL, NULL,
  '7. Prendi in carico flusso gia'' assegnato ad altro — ERRORE'
);

-- =========================================================
-- 8) Prendi in carico: stato errato (IN_CORSO) — ERRORE
-- =========================================================
-- Porta flusso C a IN_CORSO
UPDATE pratiche.flussi
   SET stato_id = (SELECT sf_in_corso FROM tmp_cl_refs)
 WHERE id = (SELECT flusso_id FROM tmp_cl_flusso_c);

SELECT throws_ok(
  format('SELECT pratiche.fn_prendi_in_carico_flusso(%s, %s)',
    (SELECT flusso_id FROM tmp_cl_flusso_c),
    (SELECT risorsa_1_id FROM tmp_cl_risorse)),
  NULL, NULL,
  '8. Prendi in carico stato IN_CORSO — ERRORE'
);

-- =========================================================
-- 9) Prendi in carico: senza competenza — ERRORE
-- =========================================================
-- Nuovo flusso DA_ESEGUIRE non assegnato (flusso C ora e' IN_CORSO, non riciclabile)
CREATE TEMP TABLE tmp_cl_flusso_d AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, risorsa_umana_id, unita_organizzativa_id, sequenza)
  VALUES (
    (SELECT pratica_id FROM tmp_cl_pratica),
    (SELECT tf_id FROM tmp_cl_tf),
    (SELECT sf_da_eseguire FROM tmp_cl_refs),
    NULL,
    (SELECT uo_id FROM tmp_cl_risorse),
    40
  )
  RETURNING id
)
SELECT id AS flusso_id FROM ins;

SELECT throws_ok(
  format('SELECT pratiche.fn_prendi_in_carico_flusso(%s, %s)',
    (SELECT flusso_id FROM tmp_cl_flusso_d),
    (SELECT risorsa_2_id FROM tmp_cl_risorse)),
  NULL, NULL,
  '9. Prendi in carico senza competenza — ERRORE'
);

-- =========================================================
-- 10) Prendi in carico: parametri NULL — ERRORE
-- =========================================================
SELECT throws_ok(
  'SELECT pratiche.fn_prendi_in_carico_flusso(NULL, NULL)',
  NULL, NULL,
  '10. Prendi in carico parametri NULL — ERRORE'
);

-- =========================================================
-- 11) Coda: stato_flusso_descrizione = descrizione umana dello stato
-- =========================================================
-- Flusso A e' ASSEGNATO e ancora in DA_ESEGUIRE (test 5-10 toccano solo B/C/D):
-- la sua stato_flusso_descrizione deve combaciare con la descrizione dello stato.
SELECT is(
  (SELECT stato_flusso_descrizione
     FROM pratiche.fn_coda_lavoro_operatore(
       (SELECT risorsa_1_id FROM tmp_cl_risorse),
       (SELECT emittente_id FROM tmp_cl_refs)
     )
    WHERE flusso_id = (SELECT flusso_id FROM tmp_cl_flusso_a)),
  (SELECT descrizione FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE'),
  '11. stato_flusso_descrizione = descrizione dello stato DA_ESEGUIRE'
);

-- =========================================================
-- 12) Cleanup
-- =========================================================
-- Cleanup con DO block per gestire tutte le dipendenze FK
DO $$
DECLARE
  v_tf_id INTEGER := (SELECT tf_id FROM tmp_cl_tf);
  v_tp_id INTEGER := (SELECT tp_id FROM tmp_cl_tp);
BEGIN
  -- Pulisci TUTTE le pratiche del tipo test (inclusi residui di run precedenti)
  -- 1) Calcoli tempo
  DELETE FROM pratiche.calcoli_tempo WHERE pratica_id IN (SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = v_tp_id);
  -- 2) Giornale
  DELETE FROM pratiche.giornale WHERE pratica_id IN (SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = v_tp_id);
  -- 3) Note flussi
  DELETE FROM pratiche.note_flussi WHERE flusso_id IN (SELECT f.id FROM pratiche.flussi f JOIN pratiche.pratiche p ON p.id = f.pratica_id WHERE p.tipo_prestazione_id = v_tp_id);
  -- 4) Allegati flussi
  DELETE FROM pratiche.allegati_flussi WHERE flusso_id IN (SELECT f.id FROM pratiche.flussi f JOIN pratiche.pratiche p ON p.id = f.pratica_id WHERE p.tipo_prestazione_id = v_tp_id);
  -- 5) Sospensioni
  DELETE FROM pratiche.sospensioni WHERE pratica_id IN (SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = v_tp_id);
  -- 6) Flussi
  DELETE FROM pratiche.flussi WHERE pratica_id IN (SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = v_tp_id);
  -- 7) Note pratiche
  DELETE FROM pratiche.note_pratiche WHERE pratica_id IN (SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = v_tp_id);
  -- 8) Allegati pratiche
  DELETE FROM pratiche.allegati_pratiche WHERE pratica_id IN (SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = v_tp_id);
  -- 9) Pratiche
  DELETE FROM pratiche.pratiche WHERE tipo_prestazione_id = v_tp_id;
  -- 10) Competenze
  DELETE FROM pratiche.competenze_flussi WHERE template_flusso_id = v_tf_id;
  -- 11) Template flussi
  DELETE FROM pratiche.template_flussi WHERE id = v_tf_id;
  -- 12) Tipo prestazione
  DELETE FROM pratiche.tipi_prestazione WHERE codice_interno = 'TEST_CL';
END $$;

SELECT pass('12. Cleanup completato');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
