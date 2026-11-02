-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: generazione cross-pratica (rev 2026-06-11, D-fix
--       analisi-pratiche-workflow-v2 §7.B).
--       Completamento flusso con regola auto=true -> pratica figlia
--       con genealogia completa (pratica_padre_id + flusso_origine_id),
--       contesto propagato, flusso iniziale da template_flusso_dest_id,
--       generazione IDEMPOTENTE (trigger su transizione + dedup fn +
--       indice uq_pratiche_flusso_origine_tipo).
--
-- Indice test:
-- 0)  Precondizioni (provisioning + verifica)
-- 1)  Setup: tipi prestazione, template (src SEMPRE + dest iniziale), pratica, regola auto
-- 2)  UPDATE flusso -> COMPLETATO: una pratica figlia generata
-- 3)  Figlia: flusso_origine_id corretto
-- 4)  Figlia: pratica_padre_id = pratica sorgente (fix-2)
-- 5)  Figlia: emittente, soggetto, priorita ereditati
-- 5b) Figlia: nasce APERTA con data_apertura valorizzata (20260614-03)
-- 6)  Figlia: contesto soggetto_ruolo_id propagato (fix-4; skip se sorgente senza ruolo)
-- 7)  Figlia: flusso iniziale creato da template_flusso_dest_id in DA_ESEGUIRE (fix-3)
-- 8)  Idempotenza trigger: UPDATE su flusso gia' COMPLETATO non genera doppioni
-- 9)  Idempotenza fn: chiamata diretta ritorna la figlia esistente, nessun doppione
-- 10) Regola auto=false: nessuna generazione automatica
-- 11) Cleanup
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

SELECT plan(12);
-- =========================================================
-- 0) Precondizioni: provisioning config data (idempotente)
-- =========================================================
INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('BOZZA', 'BOZZA', 'Bozza', true),
       ('APERTA', 'APERTA', 'Aperta', true) ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES
  ('DA_ESEGUIRE', 'DA_ESEGUIRE', 'Da eseguire', true),
  ('IN_CORSO', 'IN_CORSO', 'In corso', true),
  ('COMPLETATO', 'COMPLETATO', 'Completato', true)
ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE', 'NORMALE', 'Normale', 20, true) ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_gen_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'BOZZA' AND attivo = true LIMIT 1) AS stato_bozza_id,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE' AND attivo = true LIMIT 1) AS stato_da_eseguire_id,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'IN_CORSO' AND attivo = true LIMIT 1) AS stato_in_corso_id,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'COMPLETATO' AND attivo = true LIMIT 1) AS stato_completato_id,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE' AND attivo = true LIMIT 1) AS priorita_normale_id;

-- Contesto sorgente: preferisce un soggetto con ruolo (per il test fix-4);
-- fallback su un soggetto qualunque (ruolo NULL -> test 6 in skip).
-- Unica riga coerente: ruolo e soggetto della STESSA riga di soggetti_ruoli
-- (il guard contesto verifica l'appartenenza ruolo->soggetto).
CREATE TEMP TABLE tmp_gen_sogg AS
WITH ruolo AS (
  SELECT sr.id AS ruolo_id, sr.soggetto_id
    FROM anagrafiche.soggetti_ruoli sr
   ORDER BY sr.id
   LIMIT 1
)
SELECT
  COALESCE(
    (SELECT soggetto_id FROM ruolo),
    (SELECT s.id FROM anagrafiche.soggetti s ORDER BY s.id LIMIT 1)
  ) AS soggetto_id,
  (SELECT ruolo_id FROM ruolo) AS ruolo_id;

SELECT ok(
    (SELECT emittente_id IS NOT NULL
        AND stato_bozza_id IS NOT NULL
        AND stato_da_eseguire_id IS NOT NULL
        AND stato_completato_id IS NOT NULL
        AND priorita_normale_id IS NOT NULL
       FROM tmp_gen_refs)
    AND (SELECT soggetto_id IS NOT NULL FROM tmp_gen_sogg),
    '0. Precondizioni soddisfatte'
);
-- =========================================================
-- 1) Setup: tipi, template, pratica sorgente, regola auto
-- =========================================================
CREATE TEMP TABLE tmp_gen_tp_src AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_GEN_SRC', 'TEST_GEN_SRC', 'Tipo sorgente test generazione', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_gen_tp_dest AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_GEN_DEST', 'TEST_GEN_DEST', 'Tipo destinazione test generazione', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

-- Template sorgente: ripetibilita='SEMPRE' (il test crea due istanze
-- dello stesso template; il default SE_NON_POSITIVO le vieterebbe).
CREATE TEMP TABLE tmp_gen_tf AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, attivo, ripetibilita)
  VALUES ((SELECT tp_id FROM tmp_gen_tp_src), 'TF_GEN_SRC', 'Template sorgente generazione', true, 'SEMPRE')
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione = EXCLUDED.descrizione, ripetibilita = EXCLUDED.ripetibilita
  RETURNING id
)
SELECT id AS tf_id FROM ins;

-- Template iniziale della figlia (fix-3): senza prerequisiti.
CREATE TEMP TABLE tmp_gen_tf_dest AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, attivo)
  VALUES ((SELECT tp_id FROM tmp_gen_tp_dest), 'TF_GEN_DEST_INIT', 'Step iniziale pratica generata', 10, true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tf_id FROM ins;

CREATE TEMP TABLE tmp_gen_pratica AS WITH ins AS (
  INSERT INTO pratiche.pratiche (
      emittente_fiscale_id, tipo_prestazione_id, soggetto_id, soggetto_ruolo_id,
      stato_id, priorita_id
  )
  VALUES (
      (SELECT emittente_id FROM tmp_gen_refs),
      (SELECT tp_id FROM tmp_gen_tp_src),
      (SELECT soggetto_id FROM tmp_gen_sogg),
      (SELECT ruolo_id FROM tmp_gen_sogg),
      (SELECT stato_bozza_id FROM tmp_gen_refs),
      (SELECT priorita_normale_id FROM tmp_gen_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

-- Regola auto=true con flusso iniziale dichiarato (fix-3).
CREATE TEMP TABLE tmp_gen_regola AS WITH ins AS (
  INSERT INTO pratiche.regole_generazione (
      template_flusso_origine_id, tipo_prestazione_dest_id,
      template_flusso_dest_id, auto, attivo, descrizione
  )
  VALUES (
      (SELECT tf_id FROM tmp_gen_tf),
      (SELECT tp_id FROM tmp_gen_tp_dest),
      (SELECT tf_id FROM tmp_gen_tf_dest),
      true, true, 'Regola test generazione auto'
  )
  RETURNING id
)
SELECT id AS regola_id FROM ins;

SELECT ok(
    (SELECT pratica_id IS NOT NULL FROM tmp_gen_pratica)
    AND (SELECT regola_id IS NOT NULL FROM tmp_gen_regola),
    '1. Setup completato: pratica sorgente e regola create'
);
-- =========================================================
-- 2) UPDATE flusso -> COMPLETATO: una figlia generata
-- =========================================================
CREATE TEMP TABLE tmp_gen_flusso AS WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES (
      (SELECT pratica_id FROM tmp_gen_pratica),
      (SELECT tf_id FROM tmp_gen_tf),
      (SELECT stato_da_eseguire_id FROM tmp_gen_refs)
  )
  RETURNING id
)
SELECT id AS flusso_id FROM ins;

CREATE TEMP TABLE tmp_gen_count_before AS
SELECT count(*) AS cnt
FROM pratiche.pratiche
WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_gen_tp_dest);

-- Percorso valido per la matrice transizioni: DA_ESEGUIRE -> IN_CORSO -> COMPLETATO.
UPDATE pratiche.flussi
SET stato_id = (SELECT stato_in_corso_id FROM tmp_gen_refs)
WHERE id = (SELECT flusso_id FROM tmp_gen_flusso);
-- esito obbligatorio per COMPLETATO (guard trg_flussi_a10_guard_esito_completato).
-- La regola auto=true ha esito_richiesto NULL: 'POSITIVO' genera comunque.
UPDATE pratiche.flussi
SET stato_id = (SELECT stato_completato_id FROM tmp_gen_refs),
    esito = 'POSITIVO'
WHERE id = (SELECT flusso_id FROM tmp_gen_flusso);

SELECT is(
    (SELECT (count(*) - (SELECT cnt FROM tmp_gen_count_before))::integer
       FROM pratiche.pratiche
      WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_gen_tp_dest)),
    1,
    '2. Pratica figlia generata dopo completamento flusso'
);
-- =========================================================
-- 3) Figlia: flusso_origine_id corretto
-- =========================================================
CREATE TEMP TABLE tmp_gen_pratica_target AS
SELECT id AS pratica_id,
  pratica_padre_id,
  flusso_origine_id,
  emittente_fiscale_id,
  soggetto_id,
  soggetto_ruolo_id,
  istanza_utility_id,
  priorita_id
FROM pratiche.pratiche
WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_gen_tp_dest)
  AND flusso_origine_id = (SELECT flusso_id FROM tmp_gen_flusso)
LIMIT 1;

SELECT is(
    (SELECT flusso_origine_id FROM tmp_gen_pratica_target),
    (SELECT flusso_id FROM tmp_gen_flusso),
    '3. Figlia: flusso_origine_id corretto'
);
-- =========================================================
-- 4) Figlia: pratica_padre_id = pratica sorgente (fix-2)
-- =========================================================
SELECT is(
    (SELECT pratica_padre_id FROM tmp_gen_pratica_target),
    (SELECT pratica_id FROM tmp_gen_pratica),
    '4. Figlia: pratica_padre_id valorizzato con la pratica sorgente'
);
-- =========================================================
-- 5) Figlia: emittente, soggetto, priorita ereditati
-- =========================================================
SELECT ok(
    (SELECT t.emittente_fiscale_id = (SELECT emittente_id FROM tmp_gen_refs)
        AND t.soggetto_id = (SELECT soggetto_id FROM tmp_gen_sogg)
        AND t.priorita_id = (SELECT priorita_normale_id FROM tmp_gen_refs)
       FROM tmp_gen_pratica_target t),
    '5. Figlia: eredita emittente, soggetto, priorita dalla sorgente'
);
-- =========================================================
-- 5b) Figlia: nasce APERTA con data_apertura valorizzata (20260614-03)
--     La figlia auto-generata e' un lavoro avviato: nasce operativa,
--     non in BOZZA. data_apertura impostata dal trigger INSERT.
-- =========================================================
SELECT ok(
    (SELECT sp.codice_interno = 'APERTA' AND p.data_apertura = script.fn_data_operativa()
       FROM pratiche.pratiche p
       JOIN config.stati_pratiche sp ON sp.id = p.stato_id
      WHERE p.id = (SELECT pratica_id FROM tmp_gen_pratica_target)),
    '5b. Figlia: nasce APERTA con data_apertura = script.fn_data_operativa()'
);
-- =========================================================
-- 6) Figlia: contesto soggetto_ruolo_id propagato (fix-4)
--    (skip se nel DB di test non esiste un soggetto con ruolo)
-- =========================================================
SELECT CASE
  WHEN (SELECT ruolo_id FROM tmp_gen_sogg) IS NULL THEN
    skip('6. Nessun soggetto con ruolo nel DB di test: propagazione contesto non verificabile', 1)
  ELSE
    is(
      (SELECT soggetto_ruolo_id FROM tmp_gen_pratica_target),
      (SELECT ruolo_id FROM tmp_gen_sogg),
      '6. Figlia: soggetto_ruolo_id propagato dalla sorgente (lente D1 coerente)'
    )
END;
-- =========================================================
-- 7) Figlia: flusso iniziale da template_flusso_dest_id (fix-3)
-- =========================================================
SELECT ok(
    (SELECT EXISTS (
       SELECT 1
         FROM pratiche.flussi f
         JOIN config.stati_flussi_pratiche sfp ON sfp.id = f.stato_id
        WHERE f.pratica_id = (SELECT pratica_id FROM tmp_gen_pratica_target)
          AND f.template_flusso_id = (SELECT tf_id FROM tmp_gen_tf_dest)
          AND sfp.codice_interno = 'DA_ESEGUIRE'
    )),
    '7. Figlia: flusso iniziale creato da template_flusso_dest_id in DA_ESEGUIRE'
);
-- =========================================================
-- 8) Idempotenza trigger: UPDATE su flusso gia' COMPLETATO
--    non genera doppioni (stesso stato + ritocco note_esito)
-- =========================================================
UPDATE pratiche.flussi
SET stato_id = (SELECT stato_completato_id FROM tmp_gen_refs),
    note_esito = 'ritocco post-completamento'
WHERE id = (SELECT flusso_id FROM tmp_gen_flusso);

SELECT is(
    (SELECT count(*)::integer
       FROM pratiche.pratiche
      WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_gen_tp_dest)
        AND flusso_origine_id = (SELECT flusso_id FROM tmp_gen_flusso)),
    1,
    '8. Idempotenza trigger: UPDATE su flusso completato non rigenera la figlia'
);
-- =========================================================
-- 9) Idempotenza fn: chiamata diretta ritorna la figlia esistente
-- =========================================================
SELECT is(
    pratiche.fn_genera_pratica_da_flusso(
      (SELECT flusso_id FROM tmp_gen_flusso),
      (SELECT regola_id FROM tmp_gen_regola)
    ),
    (SELECT pratica_id FROM tmp_gen_pratica_target),
    '9. Idempotenza fn: chiamata diretta ritorna la figlia esistente (nessun doppione)'
);
-- =========================================================
-- 10) Regola auto=false: nessuna generazione automatica
-- =========================================================
-- Regola non-auto con esito specifico su un SECONDO tipo destinazione
-- dedicato, per isolare il conteggio dalla regola auto gia' attiva.
CREATE TEMP TABLE tmp_gen_tp_dest2 AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_GEN_DEST2', 'TEST_GEN_DEST2', 'Tipo destinazione 2 test generazione', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

INSERT INTO pratiche.regole_generazione (
    template_flusso_origine_id, tipo_prestazione_dest_id, auto, attivo, descrizione, esito_richiesto
)
VALUES (
    (SELECT tf_id FROM tmp_gen_tf),
    (SELECT tp_id FROM tmp_gen_tp_dest2),
    false, true, 'Regola test generazione NON auto', 'POSITIVO'
);

CREATE TEMP TABLE tmp_gen_flusso2 AS WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES (
      (SELECT pratica_id FROM tmp_gen_pratica),
      (SELECT tf_id FROM tmp_gen_tf),
      (SELECT stato_da_eseguire_id FROM tmp_gen_refs)
  )
  RETURNING id
)
SELECT id AS flusso_id FROM ins;

-- Percorso valido per la matrice transizioni: DA_ESEGUIRE -> IN_CORSO -> COMPLETATO.
UPDATE pratiche.flussi
SET stato_id = (SELECT stato_in_corso_id FROM tmp_gen_refs)
WHERE id = (SELECT flusso_id FROM tmp_gen_flusso2);
UPDATE pratiche.flussi
SET stato_id = (SELECT stato_completato_id FROM tmp_gen_refs),
    esito = 'POSITIVO'
WHERE id = (SELECT flusso_id FROM tmp_gen_flusso2);

SELECT is(
    (SELECT count(*)::integer
       FROM pratiche.pratiche
      WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_gen_tp_dest2)),
    0,
    '10. Regola auto=false non genera pratica (solo auto=true genera)'
);
-- =========================================================
-- 11) Cleanup (resiliente: gestisce orfani da run precedenti)
-- =========================================================
-- 1) Pratiche generate (tipi dest): giornale, flussi, pratiche
DELETE FROM pratiche.giornale
WHERE pratica_id IN (
    SELECT id FROM pratiche.pratiche
    WHERE tipo_prestazione_id IN (
        (SELECT tp_id FROM tmp_gen_tp_dest), (SELECT tp_id FROM tmp_gen_tp_dest2))
);
DELETE FROM pratiche.flussi
WHERE pratica_id IN (
    SELECT id FROM pratiche.pratiche
    WHERE tipo_prestazione_id IN (
        (SELECT tp_id FROM tmp_gen_tp_dest), (SELECT tp_id FROM tmp_gen_tp_dest2))
);
DELETE FROM pratiche.pratiche
WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_gen_tp_dest), (SELECT tp_id FROM tmp_gen_tp_dest2));
-- 2) Flussi, giornale e pratiche sorgente
DELETE FROM pratiche.giornale
WHERE pratica_id IN (
    SELECT id FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_gen_tp_src)
);
DELETE FROM pratiche.flussi
WHERE pratica_id IN (
    SELECT id FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_gen_tp_src)
);
DELETE FROM pratiche.pratiche
WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_gen_tp_src);
-- 3) Regole generazione
DELETE FROM pratiche.regole_generazione
WHERE template_flusso_origine_id IN (
    SELECT id FROM pratiche.template_flussi
    WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_gen_tp_src)
);
-- 4) Template e tipi prestazione
DELETE FROM pratiche.template_flussi
WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_gen_tp_src),
    (SELECT tp_id FROM tmp_gen_tp_dest),
    (SELECT tp_id FROM tmp_gen_tp_dest2));
DELETE FROM pratiche.tipi_prestazione
WHERE id IN (
    (SELECT tp_id FROM tmp_gen_tp_src),
    (SELECT tp_id FROM tmp_gen_tp_dest),
    (SELECT tp_id FROM tmp_gen_tp_dest2));

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
