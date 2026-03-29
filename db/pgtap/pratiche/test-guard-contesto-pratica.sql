-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: trigger guard contesto anagrafico su pratiche.pratiche
--       (trgfn_pratiche_guard_contesto)
--
-- Indice test:
-- 0) Precondizioni (provisioning + verifica)
-- 1) INSERT pratica interna (tutti NULL) — OK
-- 2) INSERT con soggetto_id solo — OK
-- 3) INSERT con soggetto_ruolo_id senza soggetto_id — ERRORE
-- 4) INSERT con istanza_utility_id senza soggetto_ruolo_id — ERRORE
-- 5) INSERT con soggetto_ruolo_id non appartenente a soggetto_id — ERRORE
-- 6) INSERT con istanza_utility_id non appartenente a soggetto_id — ERRORE
-- 7) INSERT con catena coerente soggetto + ruolo — OK
-- 8) INSERT con catena coerente soggetto + ruolo + istanza — OK
-- 9) UPDATE che rompe coerenza (rimuove soggetto_id ma lascia ruolo) — ERRORE
-- 10) Cleanup
-- ------------------------------------------------------------
SELECT plan(11);
-- =========================================================
-- 0) Precondizioni: recupera riferimenti
-- =========================================================
CREATE TEMP TABLE tmp_gc_refs AS
SELECT (
    SELECT id
    FROM anagrafiche.emittenti_fiscali
    WHERE attivo = true
    LIMIT 1
  ) AS emittente_id,
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
-- Recupera un soggetto con almeno un ruolo e un'istanza
CREATE TEMP TABLE tmp_gc_sogg AS
SELECT s.id AS soggetto_id,
  sr.id AS ruolo_id,
  iu.id AS istanza_id
FROM anagrafiche.soggetti s
  JOIN anagrafiche.soggetti_ruoli sr ON sr.soggetto_id = s.id
  JOIN anagrafiche.istanze_utilities iu ON iu.soggetto_id = s.id
LIMIT 1;
-- Un soggetto diverso per test ruolo non coerente
CREATE TEMP TABLE tmp_gc_altro_sogg AS
SELECT s.id AS soggetto_id
FROM anagrafiche.soggetti s
WHERE s.id <> (
    SELECT soggetto_id
    FROM tmp_gc_sogg
  )
LIMIT 1;
-- Un'istanza di un soggetto diverso per test istanza non coerente
CREATE TEMP TABLE tmp_gc_altra_istanza AS
SELECT iu.id AS istanza_id
FROM anagrafiche.istanze_utilities iu
WHERE iu.soggetto_id <> (
    SELECT soggetto_id
    FROM tmp_gc_sogg
  )
LIMIT 1;
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
-- 4) istanza_utility_id senza soggetto_ruolo_id — ERRORE
-- =========================================================
SELECT throws_ok(
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
    NULL,
    NULL,
    '4. Istanza senza ruolo — ERRORE'
  );
-- =========================================================
-- 5) soggetto_ruolo_id non appartenente a soggetto_id — ERRORE
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
    '5. Ruolo non del soggetto — ERRORE'
  );
-- =========================================================
-- 6) istanza_utility_id non appartenente a soggetto_id — ERRORE
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
    '6. Istanza non del soggetto — ERRORE'
  );
-- =========================================================
-- 7) Catena coerente soggetto + ruolo — OK
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
    '7. Catena soggetto + ruolo coerente — OK'
  );
-- =========================================================
-- 8) Catena coerente soggetto + ruolo + istanza — OK
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
    '8. Catena soggetto + ruolo + istanza coerente — OK'
  );
-- =========================================================
-- 9) UPDATE che rompe coerenza — ERRORE
-- =========================================================
-- Prendi la pratica del test 7 (soggetto + ruolo)
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
    '9. UPDATE rimuove soggetto_id ma lascia ruolo — ERRORE'
  );
-- =========================================================
-- 10) Cleanup
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
SELECT pass('10. Cleanup completato');
SELECT *
FROM finish();