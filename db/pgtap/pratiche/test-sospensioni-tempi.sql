-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: sospensioni, propagazione, riattivazione, calcoli_tempo da/a
--       Guard coerenza flusso, guard immutabili calcoli_tempo,
--       fn_calcola_tempo_netto_da_a, fn_valuta_tempo_esecuzione_da_a,
--       giornale sospensioni.
--
-- Indice test:
-- 0)  Precondizioni (provisioning + verifica)
-- 1)  Setup tipo_prestazione, template_flussi, formule_tempo
-- 2)  Formule tempo: CHECK giorni_warning > giorni_critico (vietata)
-- 3)  Formule tempo: CHECK giorni_warning < giorni_esecuzione (vietata)
-- 4)  Formule tempo: CHECK template_da <> template_a (vietata)
-- 5)  Formule tempo: CHECK giorni_esecuzione > 0 (vietata)
-- 6)  Setup pratica APERTA con 2 flussi (DA_ESEGUIRE)
-- 7)  Sospensione pratica: INSERT sospensioni (flusso_id NULL)
-- 8)  Propagazione: flussi passano a SOSPESO
-- 9)  Giornale: SOSPENSIONE_REGISTRATA presente
-- 10) Riattivazione: chiusura sospensione (data_fine)
-- 11) Riattivazione: flussi tornano allo stato precedente
-- 12) Giornale: SOSPENSIONE_CHIUSA presente
-- 13) Guard coerenza: INSERT con flusso di altra pratica (vietata)
-- 14) Guard coerenza: INSERT con flusso coerente (ammessa)
-- 15) Calcolo tempo da/a: flusso_da COMPLETATO (avvio)
-- 16) Calcolo tempo da/a: riga calcoli_tempo creata
-- 17) Calcolo tempo da/a: flusso_a COMPLETATO (chiusura)
-- 18) Calcolo tempo da/a: riga calcoli_tempo completata
-- 19) fn_valuta_tempo_esecuzione_da_a: stato OK
-- 20) Guard immutabili: UPDATE pratica_id su calcoli_tempo (vietata)
-- 21) Sospensione singolo flusso (non propaga)
-- 22) Cleanup
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

SELECT plan(22);

-- =========================================================
-- Cleanup preventivo (idempotente, per riesecuzione sicura)
-- =========================================================
DO $$
DECLARE
  v_tp_id INTEGER;
BEGIN
  SELECT id INTO v_tp_id FROM pratiche.tipi_prestazione WHERE codice_interno = 'TEST_SOSP';
  IF v_tp_id IS NOT NULL THEN
    DELETE FROM pratiche.sospensioni WHERE pratica_id IN (SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = v_tp_id);
    DELETE FROM pratiche.calcoli_tempo WHERE pratica_id IN (SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = v_tp_id);
    DELETE FROM pratiche.giornale WHERE pratica_id IN (SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = v_tp_id);
    DELETE FROM pratiche.flussi WHERE pratica_id IN (SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = v_tp_id);
    DELETE FROM pratiche.pratiche WHERE tipo_prestazione_id = v_tp_id;
    DELETE FROM pratiche.formule_tempo WHERE tipo_prestazione_id = v_tp_id;
    DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id = v_tp_id;
    DELETE FROM pratiche.tipi_prestazione WHERE id = v_tp_id;
  END IF;
END $$;

-- =========================================================
-- 0) Precondizioni
-- =========================================================
CREATE TEMP TABLE tmp_st_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti ORDER BY id LIMIT 1) AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'BOZZA') AS st_bozza,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'APERTA') AS st_aperta,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'SOSPESA') AS st_sospesa,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE') AS sf_da_eseguire,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'IN_CORSO') AS sf_in_corso,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'COMPLETATO') AS sf_completato,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'SOSPESO') AS sf_sospeso,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE') AS priorita_id;

SELECT ok(
  (SELECT emittente_id IS NOT NULL AND soggetto_id IS NOT NULL
      AND st_bozza IS NOT NULL AND st_aperta IS NOT NULL
      AND sf_da_eseguire IS NOT NULL AND sf_completato IS NOT NULL
      AND sf_sospeso IS NOT NULL AND priorita_id IS NOT NULL
   FROM tmp_st_refs),
  '0. Precondizioni soddisfatte'
);

-- =========================================================
-- 1) Setup tipo_prestazione + template_flussi + formula_tempo
-- =========================================================
CREATE TEMP TABLE tmp_st_tp AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_SOSP', 'TEST_SOSP', 'Tipo test sospensioni/tempi', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

-- Due template flussi: flusso_da e flusso_a
CREATE TEMP TABLE tmp_st_tpl AS
WITH tpl_da AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, attivo)
  VALUES ((SELECT tp_id FROM tmp_st_tp), 'STEP_DA', 'Step da (partenza)', 1, true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
),
tpl_a AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, attivo)
  VALUES ((SELECT tp_id FROM tmp_st_tp), 'STEP_A', 'Step a (arrivo)', 2, true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT
  (SELECT id FROM tpl_da) AS tpl_da_id,
  (SELECT id FROM tpl_a) AS tpl_a_id;

-- Formula tempo: 30 giorni esecuzione, warning a 10 rimanenti, critico a 3
CREATE TEMP TABLE tmp_st_formula AS
WITH ins AS (
  INSERT INTO pratiche.formule_tempo (
    tipo_prestazione_id, template_flusso_da_id, template_flusso_a_id,
    giorni_esecuzione, giorni_warning, giorni_critico, attivo
  )
  VALUES (
    (SELECT tp_id FROM tmp_st_tp),
    (SELECT tpl_da_id FROM tmp_st_tpl),
    (SELECT tpl_a_id FROM tmp_st_tpl),
    30, 10, 3, true
  )
  RETURNING id
)
SELECT id AS formula_id FROM ins;

SELECT ok(
  (SELECT formula_id IS NOT NULL FROM tmp_st_formula),
  '1. Setup: tipo_prestazione, template_flussi, formula_tempo creati'
);

-- =========================================================
-- 2) Formule tempo: CHECK giorni_warning > giorni_critico (vietata)
-- =========================================================
SELECT throws_ok(
  format(
    $$INSERT INTO pratiche.formule_tempo
      (tipo_prestazione_id, template_flusso_da_id, template_flusso_a_id,
       giorni_esecuzione, giorni_warning, giorni_critico, attivo)
      VALUES (%s, %s, %s, 30, 2, 5, true)$$,
    (SELECT tp_id FROM tmp_st_tp),
    (SELECT tpl_a_id FROM tmp_st_tpl),
    (SELECT tpl_da_id FROM tmp_st_tpl)),
  NULL, NULL,
  '2. Formule tempo: giorni_warning (2) < giorni_critico (5) vietato'
);

-- =========================================================
-- 3) Formule tempo: CHECK giorni_warning < giorni_esecuzione (vietata)
-- =========================================================
SELECT throws_ok(
  format(
    $$INSERT INTO pratiche.formule_tempo
      (tipo_prestazione_id, template_flusso_da_id, template_flusso_a_id,
       giorni_esecuzione, giorni_warning, giorni_critico, attivo)
      VALUES (%s, %s, %s, 10, 15, 3, true)$$,
    (SELECT tp_id FROM tmp_st_tp),
    (SELECT tpl_a_id FROM tmp_st_tpl),
    (SELECT tpl_da_id FROM tmp_st_tpl)),
  NULL, NULL,
  '3. Formule tempo: giorni_warning (15) > giorni_esecuzione (10) vietato'
);

-- =========================================================
-- 4) Formule tempo: CHECK template_da <> template_a (vietata)
-- =========================================================
SELECT throws_ok(
  format(
    $$INSERT INTO pratiche.formule_tempo
      (tipo_prestazione_id, template_flusso_da_id, template_flusso_a_id,
       giorni_esecuzione, giorni_warning, giorni_critico, attivo)
      VALUES (%s, %s, %s, 30, 10, 3, true)$$,
    (SELECT tp_id FROM tmp_st_tp),
    (SELECT tpl_da_id FROM tmp_st_tpl),
    (SELECT tpl_da_id FROM tmp_st_tpl)),
  NULL, NULL,
  '4. Formule tempo: template_da = template_a vietato'
);

-- =========================================================
-- 5) Formule tempo: CHECK giorni_esecuzione > 0 (vietata)
-- =========================================================
SELECT throws_ok(
  format(
    $$INSERT INTO pratiche.formule_tempo
      (tipo_prestazione_id, template_flusso_da_id, template_flusso_a_id,
       giorni_esecuzione, giorni_warning, giorni_critico, attivo)
      VALUES (%s, %s, %s, 0, 10, 3, true)$$,
    (SELECT tp_id FROM tmp_st_tp),
    (SELECT tpl_a_id FROM tmp_st_tpl),
    (SELECT tpl_da_id FROM tmp_st_tpl)),
  NULL, NULL,
  '5. Formule tempo: giorni_esecuzione = 0 vietato'
);

-- =========================================================
-- 6) Setup pratica APERTA con 2 flussi DA_ESEGUIRE
-- =========================================================
CREATE TEMP TABLE tmp_st_pratica AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_st_refs),
    (SELECT tp_id FROM tmp_st_tp),
    (SELECT soggetto_id FROM tmp_st_refs),
    (SELECT st_bozza FROM tmp_st_refs),
    (SELECT priorita_id FROM tmp_st_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

-- BOZZA -> APERTA
UPDATE pratiche.pratiche
SET stato_id = (SELECT st_aperta FROM tmp_st_refs)
WHERE id = (SELECT pratica_id FROM tmp_st_pratica);

-- Flusso 1 (flusso_da) con template
CREATE TEMP TABLE tmp_st_flusso_da AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
  VALUES (
    (SELECT pratica_id FROM tmp_st_pratica),
    (SELECT tpl_da_id FROM tmp_st_tpl),
    (SELECT sf_da_eseguire FROM tmp_st_refs),
    1
  )
  RETURNING id
)
SELECT id AS flusso_id FROM ins;

-- Flusso 2 (flusso_a) con template
CREATE TEMP TABLE tmp_st_flusso_a AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
  VALUES (
    (SELECT pratica_id FROM tmp_st_pratica),
    (SELECT tpl_a_id FROM tmp_st_tpl),
    (SELECT sf_da_eseguire FROM tmp_st_refs),
    2
  )
  RETURNING id
)
SELECT id AS flusso_id FROM ins;

SELECT ok(
  (SELECT flusso_id IS NOT NULL FROM tmp_st_flusso_a),
  '6. Setup: pratica APERTA con 2 flussi DA_ESEGUIRE'
);

-- =========================================================
-- 7) Sospensione pratica (flusso_id NULL)
-- =========================================================
CREATE TEMP TABLE tmp_st_sosp AS
WITH ins AS (
  INSERT INTO pratiche.sospensioni (pratica_id, flusso_id, motivo)
  VALUES (
    (SELECT pratica_id FROM tmp_st_pratica),
    NULL,
    'Test sospensione pratica'
  )
  RETURNING id
)
SELECT id AS sosp_id FROM ins;

SELECT ok(
  (SELECT sosp_id IS NOT NULL FROM tmp_st_sosp),
  '7. Sospensione pratica: INSERT riuscita'
);

-- =========================================================
-- 8) Propagazione: entrambi i flussi devono essere SOSPESO
-- =========================================================
SELECT ok(
  (SELECT COUNT(*) = 2
   FROM pratiche.flussi
   WHERE pratica_id = (SELECT pratica_id FROM tmp_st_pratica)
     AND stato_id = (SELECT sf_sospeso FROM tmp_st_refs)),
  '8. Propagazione: entrambi i flussi passati a SOSPESO'
);

-- =========================================================
-- 9) Giornale: SOSPENSIONE_REGISTRATA presente
-- =========================================================
SELECT ok(
  (SELECT EXISTS (
    SELECT 1 FROM pratiche.giornale
    WHERE pratica_id = (SELECT pratica_id FROM tmp_st_pratica)
      AND azione = 'SOSPENSIONE_REGISTRATA'
      AND dettaglio->>'livello' = 'PRATICA'
  )),
  '9. Giornale: SOSPENSIONE_REGISTRATA presente con livello PRATICA'
);

-- =========================================================
-- 10) Riattivazione: chiusura sospensione
-- =========================================================
-- ⚠️ clock_timestamp() e non now(), ed e' una differenza di sostanza.
--   `chk_sospensioni_data_fine` pretende data_fine > data_inizio, STRETTO.
--   Dentro una transazione now() e' congelato all'apertura: la sospensione e'
--   stata aperta poche righe fa nella STESSA transazione, quindi data_fine
--   verrebbe identica a data_inizio e il CHECK respingerebbe.
--   In esercizio non succede mai — si apre in una richiesta e si chiude in
--   un'altra — quindi comprimere i due momenti e' un artificio del test, non
--   una condizione reale. clock_timestamp() legge l'orologio adesso e dice
--   «un istante dopo»: e' l'unico modo di riprodurre nel piccolo cio' che
--   nella realta' e' separato da minuti o giorni. Il vincolo resta esercitato.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
SELECT lives_ok(
  format('UPDATE pratiche.sospensioni SET data_fine = clock_timestamp() WHERE id = %s',
    (SELECT sosp_id FROM tmp_st_sosp)),
  '10. Riattivazione: chiusura sospensione riuscita'
);

-- =========================================================
-- 11) Flussi tornano allo stato precedente (DA_ESEGUIRE)
-- =========================================================
SELECT ok(
  (SELECT COUNT(*) = 2
   FROM pratiche.flussi
   WHERE pratica_id = (SELECT pratica_id FROM tmp_st_pratica)
     AND stato_id = (SELECT sf_da_eseguire FROM tmp_st_refs)),
  '11. Riattivazione: flussi tornati a DA_ESEGUIRE'
);

-- =========================================================
-- 12) Giornale: SOSPENSIONE_CHIUSA presente
-- =========================================================
SELECT ok(
  (SELECT EXISTS (
    SELECT 1 FROM pratiche.giornale
    WHERE pratica_id = (SELECT pratica_id FROM tmp_st_pratica)
      AND azione = 'SOSPENSIONE_CHIUSA'
      AND dettaglio->>'livello' = 'PRATICA'
  )),
  '12. Giornale: SOSPENSIONE_CHIUSA presente con livello PRATICA'
);

-- =========================================================
-- 13) Guard coerenza: flusso di altra pratica (vietata)
-- =========================================================
-- Crea una seconda pratica con un flusso
CREATE TEMP TABLE tmp_st_pratica2 AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_st_refs),
    (SELECT tp_id FROM tmp_st_tp),
    (SELECT soggetto_id FROM tmp_st_refs),
    (SELECT st_bozza FROM tmp_st_refs),
    (SELECT priorita_id FROM tmp_st_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

UPDATE pratiche.pratiche
SET stato_id = (SELECT st_aperta FROM tmp_st_refs)
WHERE id = (SELECT pratica_id FROM tmp_st_pratica2);

CREATE TEMP TABLE tmp_st_flusso_altro AS
WITH ins AS (
  -- template_flusso_id e' NOT NULL dal 20260614-09: riusa STEP_DA della pratica2
  -- (stesso tipo/definizione -> guard flusso<->definizione 508 soddisfatto).
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
  VALUES (
    (SELECT pratica_id FROM tmp_st_pratica2),
    (SELECT tpl_da_id FROM tmp_st_tpl),
    (SELECT sf_da_eseguire FROM tmp_st_refs),
    1
  )
  RETURNING id
)
SELECT id AS flusso_id FROM ins;

-- Tenta sospensione pratica1 con flusso di pratica2 (deve fallire)
SELECT throws_ok(
  format(
    $$INSERT INTO pratiche.sospensioni (pratica_id, flusso_id, motivo)
      VALUES (%s, %s, 'Test coerenza')$$,
    (SELECT pratica_id FROM tmp_st_pratica),
    (SELECT flusso_id FROM tmp_st_flusso_altro)),
  NULL, NULL,
  '13. Guard coerenza: flusso di altra pratica rifiutato'
);

-- =========================================================
-- 14) Guard coerenza: flusso coerente (ammessa)
-- =========================================================
SELECT lives_ok(
  format(
    $$INSERT INTO pratiche.sospensioni (pratica_id, flusso_id, motivo)
      VALUES (%s, %s, 'Test sospensione singolo flusso')$$,
    (SELECT pratica_id FROM tmp_st_pratica),
    (SELECT flusso_id FROM tmp_st_flusso_da)),
  '14. Guard coerenza: flusso della stessa pratica ammesso'
);

-- Chiudi la sospensione flusso per non bloccare i test successivi.
-- clock_timestamp() per la stessa ragione dell'asserzione 10: il CHECK vuole
-- data_fine > data_inizio e in transazione now() non avanza.
UPDATE pratiche.sospensioni
SET data_fine = clock_timestamp()
WHERE pratica_id = (SELECT pratica_id FROM tmp_st_pratica)
  AND flusso_id = (SELECT flusso_id FROM tmp_st_flusso_da)
  AND data_fine IS NULL;

-- =========================================================
-- 15) Calcolo tempo da/a: flusso_da -> IN_CORSO -> COMPLETATO
-- =========================================================
-- Porta flusso_da: DA_ESEGUIRE -> IN_CORSO -> COMPLETATO
UPDATE pratiche.flussi
SET stato_id = (SELECT sf_in_corso FROM tmp_st_refs)
WHERE id = (SELECT flusso_id FROM tmp_st_flusso_da);

SELECT lives_ok(
  format(
    -- clock_timestamp(): la chiusura del flusso alimenta calcoli_tempo via
    -- trigger, e chk_calcoli_tempo_data_fine vuole data_fine > data_inizio.
    -- Con now() congelato in transazione i due istanti coinciderebbero.
    'UPDATE pratiche.flussi SET stato_id = %s, esito = ''POSITIVO'', data_fine = clock_timestamp() WHERE id = %s',
    (SELECT sf_completato FROM tmp_st_refs),
    (SELECT flusso_id FROM tmp_st_flusso_da)),
  '15. Calcolo tempo: flusso_da COMPLETATO'
);

-- =========================================================
-- 16) Calcolo tempo: riga calcoli_tempo creata (in corso)
-- =========================================================
SELECT ok(
  (SELECT EXISTS (
    SELECT 1 FROM pratiche.calcoli_tempo
    WHERE pratica_id = (SELECT pratica_id FROM tmp_st_pratica)
      AND flusso_da_id = (SELECT flusso_id FROM tmp_st_flusso_da)
      AND flusso_a_id = (SELECT flusso_id FROM tmp_st_flusso_a)
      AND data_inizio_calcolo IS NOT NULL
      AND data_fine_calcolo IS NULL
  )),
  '16. Calcolo tempo: riga creata con data_fine_calcolo NULL (in corso)'
);

-- =========================================================
-- 17) Calcolo tempo: flusso_a -> IN_CORSO -> COMPLETATO
-- =========================================================
UPDATE pratiche.flussi
SET stato_id = (SELECT sf_in_corso FROM tmp_st_refs)
WHERE id = (SELECT flusso_id FROM tmp_st_flusso_a);

SELECT lives_ok(
  format(
    -- clock_timestamp(): la chiusura del flusso alimenta calcoli_tempo via
    -- trigger, e chk_calcoli_tempo_data_fine vuole data_fine > data_inizio.
    -- Con now() congelato in transazione i due istanti coinciderebbero.
    'UPDATE pratiche.flussi SET stato_id = %s, esito = ''POSITIVO'', data_fine = clock_timestamp() WHERE id = %s',
    (SELECT sf_completato FROM tmp_st_refs),
    (SELECT flusso_id FROM tmp_st_flusso_a)),
  '17. Calcolo tempo: flusso_a COMPLETATO'
);

-- =========================================================
-- 18) Calcolo tempo: riga calcoli_tempo completata
-- =========================================================
SELECT ok(
  (SELECT EXISTS (
    SELECT 1 FROM pratiche.calcoli_tempo
    WHERE pratica_id = (SELECT pratica_id FROM tmp_st_pratica)
      AND flusso_da_id = (SELECT flusso_id FROM tmp_st_flusso_da)
      AND flusso_a_id = (SELECT flusso_id FROM tmp_st_flusso_a)
      AND data_fine_calcolo IS NOT NULL
      AND giorni_lordi IS NOT NULL
      AND giorni_netti IS NOT NULL
      AND sforato IS NOT NULL
  )),
  '18. Calcolo tempo: riga completata con giorni e sforato'
);

-- =========================================================
-- 19) fn_valuta_tempo_esecuzione_da_a: stato OK (< 30 giorni)
-- =========================================================
SELECT ok(
  (SELECT stato_tempo = 'OK'
   FROM pratiche.fn_valuta_tempo_esecuzione_da_a(
     (SELECT pratica_id FROM tmp_st_pratica),
     (SELECT flusso_id FROM tmp_st_flusso_da),
     (SELECT flusso_id FROM tmp_st_flusso_a)
   )),
  '19. fn_valuta_tempo_esecuzione_da_a: stato OK (tempo < soglia)'
);

-- =========================================================
-- 20) Guard immutabili: UPDATE pratica_id su calcoli_tempo (vietata)
-- =========================================================
SELECT throws_ok(
  format(
    'UPDATE pratiche.calcoli_tempo SET pratica_id = 999999 WHERE pratica_id = %s',
    (SELECT pratica_id FROM tmp_st_pratica)),
  NULL, NULL,
  '20. Guard immutabili: UPDATE pratica_id su calcoli_tempo vietato'
);

-- =========================================================
-- 21) Sospensione singolo flusso: non propaga ad altri flussi
-- =========================================================
-- Usa pratica2 con flusso_altro in DA_ESEGUIRE
INSERT INTO pratiche.sospensioni (pratica_id, flusso_id, motivo)
VALUES (
  (SELECT pratica_id FROM tmp_st_pratica2),
  (SELECT flusso_id FROM tmp_st_flusso_altro),
  'Sospensione singolo flusso'
);

-- La pratica2 ha un solo flusso, e la sospensione e' a livello flusso,
-- quindi il flusso NON deve essere passato a SOSPESO dalla propagazione
-- (la propagazione agisce solo se flusso_id IS NULL).
-- Il flusso rimane DA_ESEGUIRE perche' il trigger propaga non interviene.
SELECT ok(
  (SELECT stato_id = (SELECT sf_da_eseguire FROM tmp_st_refs)
   FROM pratiche.flussi
   WHERE id = (SELECT flusso_id FROM tmp_st_flusso_altro)),
  '21. Sospensione singolo flusso: propagazione NON avvenuta (flusso resta DA_ESEGUIRE)'
);

-- =========================================================
-- 22) Cleanup
-- =========================================================
-- Sospensioni
DELETE FROM pratiche.sospensioni
WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche
  WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_st_tp)
);
-- Calcoli tempo
DELETE FROM pratiche.calcoli_tempo
WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche
  WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_st_tp)
);
-- Giornale
DELETE FROM pratiche.giornale
WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche
  WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_st_tp)
);
-- Flussi
DELETE FROM pratiche.flussi
WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche
  WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_st_tp)
);
-- Pratiche
DELETE FROM pratiche.pratiche
WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_st_tp);
-- Formule tempo
DELETE FROM pratiche.formule_tempo
WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_st_tp);
-- Template flussi
DELETE FROM pratiche.template_flussi
WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_st_tp);
-- Tipo prestazione
DELETE FROM pratiche.tipi_prestazione
WHERE id = (SELECT tp_id FROM tmp_st_tp);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
