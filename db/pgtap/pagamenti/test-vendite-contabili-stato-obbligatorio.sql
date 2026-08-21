-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: lo stato della testata contabile e' obbligatorio, e il saldo contabile
--       si ferma al confine della distinta finale
--
-- Presidia i passi P-4 e P-5 del lotto 1 del cantiere incassi
--   (docs/it/dev/work-in-progress/brief-db-posting-e-abbinamento-rata.md §2.0).
--
-- Elenco test (plan 7):
-- 1) In pagamenti.vendite_contabili_stati l'id 1 e' BOZZA
-- 2) Una testata inserita senza stato_id nasce in BOZZA
-- 3) Una testata con stato_id esplicitamente NULL e' rifiutata
-- 4) Il guard di parametro di fn_get_saldo_fattura_contabili e' un errore di dominio
-- 5) Una riga postabile sotto una distinta NON finale entra nel saldo contabile
-- 6) La stessa riga, quando la distinta passa a uno stato finale, esce dal saldo
-- 7) has_righe_postabili segue lo stesso confine
--
-- Scopo:
--  - il test 1 presidia un CONTRATTO, non un dettaglio: il DEFAULT della colonna
--    e' l'id numerico 1, scritto a mano, perche' un DEFAULT di colonna in
--    PostgreSQL non ammette sottoquery e non si puo' scrivere «l'id di BOZZA».
--    L'id e' un contratto del CSV di seed (loader 20260213-04, primaryKey id):
--    un'assunzione non presidiata e' la prossima trappola.
--    ⚠️ NON vale per la tabella gemella vendite_contabili_righe_stati, il cui CSV
--    non porta la colonna id: li' gli stati si risolvono sempre per codice_interno;
--  - i test 2 e 3 presidiano il NOT NULL. Da quando lo stato e' il cancello fra
--    brogliaccio e registro — prima della conferma la contabile si annulla, dopo
--    no — una testata SENZA stato non e' ne' l'uno ne' l'altro, e passava i
--    filtri di entrambi;
--  - i test 5 e 6 presidiano il confine che fn_get_saldo_fattura_contabili
--    applica. ⚠️ NON sono il presidio contro la riga appesa a una distinta gia'
--    chiusa (difetto C-5 del piano): quello lo chiudono i guard della slice 1.
--    Qui si verifica che un documento chiuso smetta di contare, che e' un'altra
--    cosa.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Contesto applicativo: il test gira come gira l'applicazione (ruolo
--   OPERATORE + RLS attiva), non come owner. Serve anche per VEDERE la fattura
--   della fixture: vendite.fatture ha la RLS.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, che qui non arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- 1) Il contratto su cui poggia il DEFAULT della colonna
-- ============================================================
SELECT is(
  (SELECT codice_interno FROM pagamenti.vendite_contabili_stati WHERE id = 1),
  'BOZZA',
  'L''id 1 di vendite_contabili_stati e'' BOZZA: e'' il contratto del DEFAULT della colonna'
);

-- ============================================================
-- Fixture
--   ⚠️ Niente LIMIT 1 senza ORDER BY, e la condizione che rende il caso
--   significativo e' scelta UNA volta: la fattura dev'essere VISIBILE (la RLS
--   filtra da se') e avere il billing account, perche' e' quello che finisce
--   sulla riga contabile.
-- ============================================================
CREATE TEMP TABLE tmp_vcso_ref AS
SELECT
  (SELECT f.id
     FROM vendite.fatture f
    WHERE f.billing_account_id IS NOT NULL
    ORDER BY f.id
    LIMIT 1)                                              AS fattura_id,
  (SELECT f.billing_account_id
     FROM vendite.fatture f
    WHERE f.billing_account_id IS NOT NULL
    ORDER BY f.id
    LIMIT 1)                                              AS billing_account_id,
  (SELECT c.id FROM pagamenti.centri_riscossione c
    WHERE c.codice_interno = 'BANCA')                     AS centro_id,
  (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
    WHERE s.codice_interno = 'ABBINATA')                  AS stato_riga_abbinata_id,
  (SELECT s.id FROM pagamenti.vendite_contabili_stati s
    WHERE s.codice_interno = 'ANNULLATA')                 AS stato_testata_finale_id;

-- ⚠️ I due valori della fattura arrivano da due sotto-select con lo STESSO
--   ORDER BY sulla stessa colonna unica: la riga scelta e' la medesima.

-- ============================================================
-- 2) Una testata senza stato_id nasce in BOZZA
--   E' il DEFAULT che dice cio' che fn_get_or_create_vendite_contabile gia' fa.
-- ============================================================
-- ⚠️ `CREATE TABLE AS INSERT ... RETURNING` non esiste in PostgreSQL: la
--   scrittura va incapsulata in una CTE e la temp table si popola dal suo
--   RETURNING.
CREATE TEMP TABLE tmp_vcso_contabile AS
WITH ins AS (
  INSERT INTO pagamenti.vendite_contabili
    (codice, centro_riscossione_id, data_contabile, data_registrazione, meta)
  SELECT
    'VCSO_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    r.centro_id,
    current_date,
    current_date,
    jsonb_build_object('test_scope', 'pgtap_vendite_contabili_stato_obbligatorio')
  FROM tmp_vcso_ref r
  RETURNING id, stato_id
)
SELECT id, stato_id FROM ins;

SELECT is(
  (SELECT s.codice_interno
     FROM tmp_vcso_contabile c
     JOIN pagamenti.vendite_contabili_stati s ON s.id = c.stato_id),
  'BOZZA',
  'Una testata contabile inserita senza stato nasce in BOZZA'
);

-- ============================================================
-- 3) Una testata con stato NULL esplicito e' rifiutata
-- ============================================================
SELECT throws_ok(
  $$
  INSERT INTO pagamenti.vendite_contabili
    (codice, centro_riscossione_id, data_contabile, data_registrazione, stato_id, meta)
  SELECT
    'VCSO_NULL_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    r.centro_id, current_date, current_date, NULL, '{}'::jsonb
  FROM tmp_vcso_ref r;
  $$,
  '23502',
  NULL,
  'Una testata contabile senza stato non si scrive'
);

-- ============================================================
-- 4) Il guard di parametro e' un errore di DOMINIO
--   ⚠️ P0001 dice «errore di dominio», non QUALE: qui basta, perche' la funzione
--   ha un solo guard di parametro. Se un giorno ne avesse due, il discriminante
--   diventerebbe la frase.
-- ============================================================
SELECT throws_ok(
  $$ SELECT * FROM pagamenti.fn_get_saldo_fattura_contabili(0) $$,
  'P0001',
  NULL,
  'fn_get_saldo_fattura_contabili rifiuta un id non valido con un errore di dominio'
);

-- ============================================================
-- Fixture: il saldo PRIMA, poi la riga
--   ⚠️ Si asserisce la QUADRATURA (il delta), non il valore assoluto: sulla
--   fattura scelta potrebbero esistere altre righe, e un'asserzione sul totale
--   verificherebbe i dati dell'ambiente invece della regola.
-- ============================================================
CREATE TEMP TABLE tmp_vcso_saldo_prima AS
SELECT s.saldo_contabile, s.has_righe_postabili
FROM tmp_vcso_ref r
CROSS JOIN LATERAL pagamenti.fn_get_saldo_fattura_contabili(r.fattura_id) s;

INSERT INTO pagamenti.vendite_contabili_righe
  (contabile_id, importo, fattura_id, billing_account_id, stato_id, meta)
SELECT
  c.id,
  100.00,
  r.fattura_id,
  r.billing_account_id,
  r.stato_riga_abbinata_id,
  jsonb_build_object('test_scope', 'pgtap_vendite_contabili_stato_obbligatorio')
FROM tmp_vcso_contabile c
CROSS JOIN tmp_vcso_ref r;

-- ⚠️ La lettura sta in un'istruzione SEPARATA dalla scrittura: la snapshot di
--   statement legge PRIMA delle scritture, e un'unica istruzione accuserebbe la
--   funzione di un difetto del test.
CREATE TEMP TABLE tmp_vcso_saldo_bozza AS
SELECT s.saldo_contabile, s.has_righe_postabili
FROM tmp_vcso_ref r
CROSS JOIN LATERAL pagamenti.fn_get_saldo_fattura_contabili(r.fattura_id) s;

-- ============================================================
-- 5) La riga postabile sotto una distinta non finale entra nel saldo
-- ============================================================
SELECT is(
  (SELECT d.saldo_contabile - p.saldo_contabile
     FROM tmp_vcso_saldo_bozza d, tmp_vcso_saldo_prima p),
  100.00::numeric,
  'Una riga postabile sotto una distinta in BOZZA aumenta il saldo contabile del proprio importo'
);

-- ============================================================
-- La distinta passa a uno stato finale
--
-- ⚠️ ANNULLATA e non CHIUSA, e la ragione e' arrivata col lotto 2: dal
--   2026-08-21 pagamenti.trgfn_vendite_contabili_guard_chiusura rifiuta la
--   CHIUSURA di una distinta che ha ancora righe pronte da registrare (difetto
--   C-5, porta d'uscita) - ed e' esattamente il caso di questa fixture, che una
--   riga ABBINATA ce l'ha per costruzione.
--
-- ⭐ E il test ci guadagna in precisione: quello che verifica e' il filtro su
--   is_final, e ANNULLATA e' il caso in cui quel filtro ha davvero un mestiere.
--   Su CHIUSA non protegge niente - le righe registrate sarebbero escluse
--   comunque, perche' non piu' postabili.
-- ============================================================
UPDATE pagamenti.vendite_contabili vc
   SET stato_id = (SELECT stato_testata_finale_id FROM tmp_vcso_ref)
 WHERE vc.id = (SELECT id FROM tmp_vcso_contabile);

CREATE TEMP TABLE tmp_vcso_saldo_finale AS
SELECT s.saldo_contabile, s.has_righe_postabili
FROM tmp_vcso_ref r
CROSS JOIN LATERAL pagamenti.fn_get_saldo_fattura_contabili(r.fattura_id) s;

-- ============================================================
-- 6) Con la distinta finale la riga esce dal saldo
-- ============================================================
SELECT is(
  (SELECT c.saldo_contabile FROM tmp_vcso_saldo_finale c),
  (SELECT p.saldo_contabile FROM tmp_vcso_saldo_prima p),
  'Quando la distinta passa a uno stato finale la sua riga esce dal saldo contabile'
);

-- ============================================================
-- 7) has_righe_postabili segue lo stesso confine
-- ============================================================
SELECT is(
  (SELECT c.has_righe_postabili FROM tmp_vcso_saldo_finale c),
  (SELECT p.has_righe_postabili FROM tmp_vcso_saldo_prima p),
  'has_righe_postabili torna com''era: una distinta finale non ha piu'' righe da registrare'
);

SELECT * FROM finish();
ROLLBACK;
