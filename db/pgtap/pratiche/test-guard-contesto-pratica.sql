-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: trigger guard contesto anagrafico su pratiche.pratiche
--       (trgfn_pratiche_guard_contesto) — MODELLO A DUE RAMI
--       (soggetto->ruolo, soggetto->istanza, indipendenti).
--
-- Indice test:
-- 0) Precondizioni (provisioning + verifica)
-- 1) INSERT pratica interna (tutti NULL) — OK
-- 2) INSERT con soggetto_id solo — OK
-- 3) INSERT con soggetto_ruolo_id senza soggetto_id — ERRORE
-- 4) INSERT con soggetto_id + istanza_utility_id, SENZA ruolo (prospect puro) — OK
-- 5) INSERT con istanza_utility_id senza soggetto_id — ERRORE (regola sostitutiva)
-- 6) INSERT con soggetto_ruolo_id non appartenente a soggetto_id — ERRORE
-- 7) INSERT con istanza_utility_id non appartenente a soggetto_id — ERRORE
-- 8) INSERT con catena coerente soggetto + ruolo — OK
-- 9) INSERT con catena coerente soggetto + ruolo + istanza — OK
-- 10) UPDATE che rompe coerenza (rimuove soggetto_id ma lascia ruolo) — ERRORE
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
-- 0) Precondizioni: recupera riferimenti
-- =========================================================
CREATE TEMP TABLE tmp_gc_refs AS
SELECT script.fn_pgtap_emittente_operatore() AS emittente_id,
  (
    SELECT id
    FROM config.stati_pratiche
    WHERE codice_interno = 'BOZZA'
  ) AS st_bozza,
  (
    SELECT id
    FROM config.priorita_pratiche
    WHERE codice_interno = 'NORMALE'
  ) AS priorita_id;
-- Tipo prestazione per i test
CREATE TEMP TABLE tmp_gc_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES (
      'TEST_GC',
      'TEST_GC',
      'Tipo test guard contesto',
      true
    ) ON CONFLICT (codice_interno) DO
  UPDATE
  SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id
FROM ins;
-- Due clienti COSTRUITI (soggetto -> ruolo CL -> istanza -> BA), non pescati
-- dalla macchina: su un database ricostruito da zero non c'e' nessun soggetto
-- da pescare, e il file moriva alle precondizioni. Il primo e' la catena
-- coerente; il secondo da' «l'altro soggetto» e «l'istanza di un altro».
-- Dopo il contesto e senza terzo parametro: il legame BA -> emittente lo
-- scrive il trigger z90 verso chi agisce.
-- ⛔ Cio' che il builder scrive si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_gc_cli1 AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('guard contesto pratica 1');
CREATE TEMP TABLE tmp_gc_cli2 AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('guard contesto pratica 2');
-- Il soggetto con un ruolo e un'istanza suoi
CREATE TEMP TABLE tmp_gc_sogg AS
SELECT soggetto_id,
  soggetto_ruolo_id AS ruolo_id,
  istanza_utility_id AS istanza_id
FROM tmp_gc_cli1;
-- Un soggetto diverso per test ruolo non coerente
CREATE TEMP TABLE tmp_gc_altro_sogg AS
SELECT soggetto_id
FROM tmp_gc_cli2;
-- Un'istanza di un soggetto diverso per test istanza non coerente
CREATE TEMP TABLE tmp_gc_altra_istanza AS
SELECT istanza_utility_id AS istanza_id
FROM tmp_gc_cli2;
SELECT ok(
    (
      SELECT emittente_id IS NOT NULL
        AND st_bozza IS NOT NULL
        AND priorita_id IS NOT NULL
      FROM tmp_gc_refs
    )
    AND (
      SELECT soggetto_id IS NOT NULL
        AND ruolo_id IS NOT NULL
        AND istanza_id IS NOT NULL
      FROM tmp_gc_sogg
    ),
    '0. Precondizioni soddisfatte'
  );
-- =========================================================
-- 1) Pratica interna: tutti NULL — OK
-- =========================================================
SELECT lives_ok(
    format(
      'INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, soggetto_ruolo_id, istanza_utility_id, stato_id, priorita_id)
          VALUES (%s, %s, NULL, NULL, NULL, %s, %s)',
      (
        SELECT emittente_id
        FROM tmp_gc_refs
      ),
      (
        SELECT tp_id
        FROM tmp_gc_tp
      ),
      (
        SELECT st_bozza
        FROM tmp_gc_refs
      ),
      (
        SELECT priorita_id
        FROM tmp_gc_refs
      )
    ),
    '1. Pratica interna (tutti NULL) — OK'
  );
-- =========================================================
-- 2) Con soggetto_id solo — OK
-- =========================================================
SELECT lives_ok(
    format(
      'INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, soggetto_ruolo_id, istanza_utility_id, stato_id, priorita_id)
          VALUES (%s, %s, %L, NULL, NULL, %s, %s)',
      (
        SELECT emittente_id
        FROM tmp_gc_refs
      ),
      (
        SELECT tp_id
        FROM tmp_gc_tp
      ),
      (
        SELECT soggetto_id
        FROM tmp_gc_sogg
      ),
      (
        SELECT st_bozza
        FROM tmp_gc_refs
      ),
      (
        SELECT priorita_id
        FROM tmp_gc_refs
      )
    ),
    '2. Con soggetto_id solo — OK'
  );
-- =========================================================
-- 3) soggetto_ruolo_id senza soggetto_id — ERRORE
-- =========================================================
SELECT throws_ok(
    format(
      'INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, soggetto_ruolo_id, istanza_utility_id, stato_id, priorita_id)
          VALUES (%s, %s, NULL, %s, NULL, %s, %s)',
      (
        SELECT emittente_id
        FROM tmp_gc_refs
      ),
      (
        SELECT tp_id
        FROM tmp_gc_tp
      ),
      (
        SELECT ruolo_id
        FROM tmp_gc_sogg
      ),
      (
        SELECT st_bozza
        FROM tmp_gc_refs
      ),
      (
        SELECT priorita_id
        FROM tmp_gc_refs
      )
    ),
    NULL,
    NULL,
    '3. Ruolo senza soggetto — ERRORE'
  );
-- =========================================================
-- 4) soggetto_id + istanza_utility_id, SENZA ruolo (prospect puro) — OK
--    Caso pre-contrattuale utilities: l'istanza pende dal soggetto, il ruolo
--    CLIENTE non e' ancora nato. Prima della 20260611-01 questo era ERRORE.
-- =========================================================
SELECT lives_ok(
    format(
      'INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, soggetto_ruolo_id, istanza_utility_id, stato_id, priorita_id)
          VALUES (%s, %s, %L, NULL, %s, %s, %s)',
      (
        SELECT emittente_id
        FROM tmp_gc_refs
      ),
      (
        SELECT tp_id
        FROM tmp_gc_tp
      ),
      (
        SELECT soggetto_id
        FROM tmp_gc_sogg
      ),
      (
        SELECT istanza_id
        FROM tmp_gc_sogg
      ),
      (
        SELECT st_bozza
        FROM tmp_gc_refs
      ),
      (
        SELECT priorita_id
        FROM tmp_gc_refs
      )
    ),
    '4. Istanza + soggetto, senza ruolo (prospect puro) — OK'
  );
-- =========================================================
-- 5) istanza_utility_id senza soggetto_id — ERRORE (regola sostitutiva)
-- =========================================================
SELECT throws_ok(
    format(
      'INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, soggetto_ruolo_id, istanza_utility_id, stato_id, priorita_id)
          VALUES (%s, %s, NULL, NULL, %s, %s, %s)',
      (
        SELECT emittente_id
        FROM tmp_gc_refs
      ),
      (
        SELECT tp_id
        FROM tmp_gc_tp
      ),
      (
        SELECT istanza_id
        FROM tmp_gc_sogg
      ),
      (
        SELECT st_bozza
        FROM tmp_gc_refs
      ),
      (
        SELECT priorita_id
        FROM tmp_gc_refs
      )
    ),
    NULL,
    NULL,
    '5. Istanza senza soggetto — ERRORE'
  );
-- =========================================================
-- 6) soggetto_ruolo_id non appartenente a soggetto_id — ERRORE
-- =========================================================
SELECT throws_ok(
    format(
      'INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, soggetto_ruolo_id, istanza_utility_id, stato_id, priorita_id)
          VALUES (%s, %s, %L, %s, NULL, %s, %s)',
      (
        SELECT emittente_id
        FROM tmp_gc_refs
      ),
      (
        SELECT tp_id
        FROM tmp_gc_tp
      ),
      (
        SELECT soggetto_id
        FROM tmp_gc_altro_sogg
      ),
      (
        SELECT ruolo_id
        FROM tmp_gc_sogg
      ),
      (
        SELECT st_bozza
        FROM tmp_gc_refs
      ),
      (
        SELECT priorita_id
        FROM tmp_gc_refs
      )
    ),
    NULL,
    NULL,
    '6. Ruolo non del soggetto — ERRORE'
  );
-- =========================================================
-- 7) istanza_utility_id non appartenente a soggetto_id — ERRORE
-- =========================================================
SELECT throws_ok(
    format(
      'INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, soggetto_ruolo_id, istanza_utility_id, stato_id, priorita_id)
          VALUES (%s, %s, %L, %s, %s, %s, %s)',
      (
        SELECT emittente_id
        FROM tmp_gc_refs
      ),
      (
        SELECT tp_id
        FROM tmp_gc_tp
      ),
      (
        SELECT soggetto_id
        FROM tmp_gc_sogg
      ),
      (
        SELECT ruolo_id
        FROM tmp_gc_sogg
      ),
      (
        SELECT istanza_id
        FROM tmp_gc_altra_istanza
      ),
      (
        SELECT st_bozza
        FROM tmp_gc_refs
      ),
      (
        SELECT priorita_id
        FROM tmp_gc_refs
      )
    ),
    NULL,
    NULL,
    '7. Istanza non del soggetto — ERRORE'
  );
-- =========================================================
-- 8) Catena coerente soggetto + ruolo — OK
-- =========================================================
SELECT lives_ok(
    format(
      'INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, soggetto_ruolo_id, istanza_utility_id, stato_id, priorita_id)
          VALUES (%s, %s, %L, %s, NULL, %s, %s)',
      (
        SELECT emittente_id
        FROM tmp_gc_refs
      ),
      (
        SELECT tp_id
        FROM tmp_gc_tp
      ),
      (
        SELECT soggetto_id
        FROM tmp_gc_sogg
      ),
      (
        SELECT ruolo_id
        FROM tmp_gc_sogg
      ),
      (
        SELECT st_bozza
        FROM tmp_gc_refs
      ),
      (
        SELECT priorita_id
        FROM tmp_gc_refs
      )
    ),
    '8. Catena soggetto + ruolo coerente — OK'
  );
-- =========================================================
-- 9) Catena coerente soggetto + ruolo + istanza — OK
-- =========================================================
SELECT lives_ok(
    format(
      'INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, soggetto_ruolo_id, istanza_utility_id, stato_id, priorita_id)
          VALUES (%s, %s, %L, %s, %s, %s, %s)',
      (
        SELECT emittente_id
        FROM tmp_gc_refs
      ),
      (
        SELECT tp_id
        FROM tmp_gc_tp
      ),
      (
        SELECT soggetto_id
        FROM tmp_gc_sogg
      ),
      (
        SELECT ruolo_id
        FROM tmp_gc_sogg
      ),
      (
        SELECT istanza_id
        FROM tmp_gc_sogg
      ),
      (
        SELECT st_bozza
        FROM tmp_gc_refs
      ),
      (
        SELECT priorita_id
        FROM tmp_gc_refs
      )
    ),
    '9. Catena soggetto + ruolo + istanza coerente — OK'
  );
-- =========================================================
-- 10) UPDATE che rompe coerenza — ERRORE
-- =========================================================
-- Prendi una pratica con soggetto + ruolo (senza istanza)
CREATE TEMP TABLE tmp_gc_pratica_upd AS
SELECT id AS pratica_id
FROM pratiche.pratiche
WHERE tipo_prestazione_id = (
    SELECT tp_id
    FROM tmp_gc_tp
  )
  AND soggetto_ruolo_id IS NOT NULL
  AND istanza_utility_id IS NULL
LIMIT 1;
SELECT throws_ok(
    format(
      'UPDATE pratiche.pratiche SET soggetto_id = NULL WHERE id = %s',
      (
        SELECT pratica_id
        FROM tmp_gc_pratica_upd
      )
    ),
    NULL,
    NULL,
    '10. UPDATE rimuove soggetto_id ma lascia ruolo — ERRORE'
  );
-- =========================================================
-- 11) Cleanup
-- =========================================================
DELETE FROM pratiche.giornale
WHERE pratica_id IN (
    SELECT id
    FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (
        SELECT tp_id
        FROM tmp_gc_tp
      )
  );
DELETE FROM pratiche.pratiche
WHERE tipo_prestazione_id = (
    SELECT tp_id
    FROM tmp_gc_tp
  );
DELETE FROM pratiche.tipi_prestazione
WHERE codice_interno = 'TEST_GC';
SELECT pass('11. Cleanup completato');
SELECT *
FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
