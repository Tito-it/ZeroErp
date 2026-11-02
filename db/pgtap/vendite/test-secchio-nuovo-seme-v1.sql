-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il SEME del secchio appena nato
--       vendite.fn_get_next_progressivo (20260908-10)
--       Piano: brief-db-registri-numerazione-chiave-del-contatore, sezione 11.7
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2c/2d): le famiglie col codice della sorgente.
-- ------------------------------------------------------------
-- Elenco test (plan 5):
-- 1) ANNUALE -> NESSUNA su un registro che ha gia' numerato: NON riparte da 1
-- 2) ...e da li' in poi il contatore attraversa l'anno
-- 3) NESSUNA -> ANNUALE: nemmeno il verso opposto riparte da 1
-- 4) ⭐⭐ IL GEMELLO NEGATIVO: senza cambi di politica l'azzeramento ANNUALE REGGE
-- 5) Il seme non inventa niente: su un registro senza storia il primo numero e' 1
--
-- Scopo:
--   ⭐ UN SECCHIO NASCE QUANDO CAMBIA LA CHIAVE, e la chiave cambia in due
--   momenti: a capodanno (ANNUALE) e quando qualcuno cambia `reset_policy` su
--   un registro che ha gia' numerato. Nel secondo caso un secchio che nasce a
--   ZERO consegna un numero che, nell'anno solare del documento, e' gia' stato
--   emesso: il vincolo di unicita' del documento lo respinge, il rollback
--   riporta indietro anche l'incremento, e al tentativo dopo si sbatte di
--   nuovo. Cioe' un numeratore PIANTATO.
--   ⇒ Il secchio nuovo parte dal massimo dei secchi con cui puo' COLLIDERE.
--
--   ⛔⛔ IL TEST 4 E' QUELLO CHE TIENE IN PIEDI GLI ALTRI TRE. Il criterio
--   sbagliato — «parti sempre dal massimo di sempre» — supererebbe i test 1, 2
--   e 3 esattamente come quello giusto, e spegnerebbe l'azzeramento annuale su
--   TUTTI i registri senza che niente diventi rosso. E' il difetto piu' grave
--   che questa modifica puo' introdurre, ed e' invisibile fino al 1° gennaio.
--
--   ⚠️ I VERBI STANNO IN ISTRUZIONI SEPARATE dalle asserzioni: la funzione
--   scrive, e dentro la stessa istruzione dell'asserzione l'ordine di
--   valutazione non e' garantito.
--
-- ⚠️ COSA QUESTO FILE NON PROVA: che la collisione a valle avvenga davvero.
--   Costruirla vorrebbe dire scrivere due documenti veri col loro corredo; qui
--   si prova il NUMERO consegnato, che e' la causa. Il vincolo che respinge e'
--   gia' presidiato da test-chiave-contatore-assi-dichiarati-v1.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

-- ============================================================
-- Fixture: due registri di prova sullo stesso emittente.
-- ⚠️ La utility va valorizzata: lo slot (famiglia, emittente, «per tutte le
--    utility») e' gia' preso dal provisioning, e quell'indice non filtra su
--    `attivo`.
-- ============================================================
CREATE TEMP TABLE tmp_seme_reg AS
WITH base AS (
  SELECT r.emittente_soggetto_ruolo_id AS sr,
         (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1) AS ut
    FROM vendite.registri_fatturazione r
   WHERE r.emittente_soggetto_ruolo_id IS NOT NULL
   ORDER BY r.id
   LIMIT 1),
a AS (
  INSERT INTO vendite.registri_fatturazione
      (codice, descrizione, emittente_soggetto_ruolo_id, famiglia_documento,
       prefisso, lunghezza_numero, reset_policy, utility_id)
  SELECT 'PGTAP-SEME-A', 'pgTAP seme: passaggio di politica', base.sr, 'ORDINE_VENDITA',
         'QSA', 7, 'ANNUALE', base.ut FROM base
  RETURNING id),
b AS (
  INSERT INTO vendite.registri_fatturazione
      (codice, descrizione, emittente_soggetto_ruolo_id, famiglia_documento,
       prefisso, lunghezza_numero, reset_policy, utility_id)
  SELECT 'PGTAP-SEME-B', 'pgTAP seme: nessun cambio di politica', base.sr, 'DDT_VENDITA',
         'QSB', 7, 'ANNUALE', base.ut FROM base
  RETURNING id)
SELECT (SELECT id FROM a) AS reg_a, (SELECT id FROM b) AS reg_b;

-- ============================================================
-- 1/2) Il passaggio ANNUALE -> NESSUNA
-- ============================================================
-- Due numeri con la politica di partenza: il secchio 2026 arriva a 2.
CREATE TEMP TABLE tmp_seme_a1 AS
SELECT vendite.fn_get_next_progressivo((SELECT reg_a FROM tmp_seme_reg),
           DATE '2126-03-01', NULL, '', NULL, 'ORDINE_VENDITA') AS n1;
CREATE TEMP TABLE tmp_seme_a2 AS
SELECT vendite.fn_get_next_progressivo((SELECT reg_a FROM tmp_seme_reg),
           DATE '2126-04-01', NULL, '', NULL, 'ORDINE_VENDITA') AS n2;

UPDATE vendite.registri_fatturazione
   SET reset_policy = 'NESSUNA'
 WHERE id = (SELECT reg_a FROM tmp_seme_reg);

CREATE TEMP TABLE tmp_seme_a3 AS
SELECT vendite.fn_get_next_progressivo((SELECT reg_a FROM tmp_seme_reg),
           DATE '2126-05-01', NULL, '', NULL, 'ORDINE_VENDITA') AS n3;

SELECT is(
    (SELECT n3 FROM tmp_seme_a3),
    3::bigint,
    '1) Cambiando politica su un registro che ha gia'' numerato il secchio nuovo NON riparte da 1');

CREATE TEMP TABLE tmp_seme_a4 AS
SELECT vendite.fn_get_next_progressivo((SELECT reg_a FROM tmp_seme_reg),
           DATE '2127-02-01', NULL, '', NULL, 'ORDINE_VENDITA') AS n4;

SELECT is(
    (SELECT n4 FROM tmp_seme_a4),
    4::bigint,
    '2) ...e da li'' in poi la numerazione attraversa l''anno, come NESSUNA promette');

-- ============================================================
-- 3) Il verso opposto, NESSUNA -> ANNUALE
-- ============================================================
UPDATE vendite.registri_fatturazione
   SET reset_policy = 'ANNUALE'
 WHERE id = (SELECT reg_a FROM tmp_seme_reg);

CREATE TEMP TABLE tmp_seme_a5 AS
SELECT vendite.fn_get_next_progressivo((SELECT reg_a FROM tmp_seme_reg),
           DATE '2127-03-01', NULL, '', NULL, 'ORDINE_VENDITA') AS n5;

SELECT is(
    (SELECT n5 FROM tmp_seme_a5),
    5::bigint,
    '3) Il verso opposto ha lo stesso difetto e la stessa cura: il secchio d''anno nasce dal continuo');

-- ============================================================
-- 4) ⭐⭐ Il gemello negativo: l'azzeramento annuale deve REGGERE
-- ============================================================
CREATE TEMP TABLE tmp_seme_b1 AS
SELECT vendite.fn_get_next_progressivo((SELECT reg_b FROM tmp_seme_reg),
           DATE '2126-06-01', NULL, '', NULL, 'DDT_VENDITA') AS n1;
CREATE TEMP TABLE tmp_seme_b2 AS
SELECT vendite.fn_get_next_progressivo((SELECT reg_b FROM tmp_seme_reg),
           DATE '2126-07-01', NULL, '', NULL, 'DDT_VENDITA') AS n2;
CREATE TEMP TABLE tmp_seme_b3 AS
SELECT vendite.fn_get_next_progressivo((SELECT reg_b FROM tmp_seme_reg),
           DATE '2127-01-02', NULL, '', NULL, 'DDT_VENDITA') AS n3;

SELECT is(
    (SELECT n3 FROM tmp_seme_b3),
    1::bigint,
    '4) Senza cambi di politica il primo documento dell''anno riparte da 1: l''azzeramento ANNUALE regge');

-- ============================================================
-- 5) Il seme non inventa: senza storia si parte da 1
-- ============================================================
CREATE TEMP TABLE tmp_seme_c AS
WITH base AS (
  SELECT r.emittente_soggetto_ruolo_id AS sr,
         (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1) AS ut
    FROM vendite.registri_fatturazione r
   WHERE r.emittente_soggetto_ruolo_id IS NOT NULL
   ORDER BY r.id
   LIMIT 1),
c AS (
  INSERT INTO vendite.registri_fatturazione
      (codice, descrizione, emittente_soggetto_ruolo_id, famiglia_documento,
       prefisso, lunghezza_numero, reset_policy, utility_id)
  SELECT 'PGTAP-SEME-C', 'pgTAP seme: registro senza storia', base.sr, 'RESO_VENDITA',
         'QSC', 7, 'NESSUNA', base.ut FROM base
  RETURNING id)
SELECT id AS reg_c FROM c;

CREATE TEMP TABLE tmp_seme_c1 AS
SELECT vendite.fn_get_next_progressivo((SELECT reg_c FROM tmp_seme_c),
           DATE '2126-08-01', NULL, '', NULL, 'RESO_VENDITA') AS n1;

SELECT is(
    (SELECT n1 FROM tmp_seme_c1),
    1::bigint,
    '5) Su un registro senza nessun secchio il massimo e'' su zero righe: si parte da 1');

SELECT * FROM finish();

ROLLBACK;
