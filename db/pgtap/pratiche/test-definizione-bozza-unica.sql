-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: invariante «≤1 BOZZA per scope» + nuova-versione dalla PUBBLICATA.
--       (brief-db-nuova-versione-bozza-unica)
--
--   Scope = (tipo_prestazione, emittente). Guard fail-fast in fn_fork_definizione
--   e fn_nuova_versione_definizione (+ indice uq_workflow_definizioni_bozza):
--     - fork/nuova-versione su scope con BOZZA aperta -> DEFINIZIONE_BOZZA_ESISTENTE (515);
--     - nuova-versione da sorgente non-PUBBLICATA -> DEFINIZIONE_NO_PUBBLICATA (516).
--   Il flusso pulito fork->pubblica->nuova-versione->pubblica resta verde.
--
-- Indice test:
-- 0)  Precondizioni (emittente)
-- 1)  Setup: preset {A} + fork(X) BOZZA -> pubblica (flusso pulito, no doppia bozza)
-- 2)  nuova-versione(X pubblicata) -> BOZZA v2 (ammesso) -> pubblica
-- 3)  dopo il flusso pulito: scope X ha 0 BOZZA e 1 PUBBLICATA
-- 4)  nuova-versione(X pubblicata) -> BOZZA v3 (ammesso: scope senza bozza)
-- 5)  nuova-versione(X pubblicata) di nuovo -> 515 (scope ha gia' una BOZZA)
-- 6)  nuova-versione(BOZZA v3) -> 516 (sorgente non PUBBLICATA)
-- 7)  nuova-versione(v1 RITIRATA) -> 516 (sorgente non PUBBLICATA)
-- 8)  fork(preset, X) con BOZZA v3 aperta nello scope X -> 515
-- 9)  Cleanup
-- ------------------------------------------------------------
SELECT plan(10);

-- =========================================================
-- PRE-CLEANUP (pg_prove COMMITTA): ritira i fork PUBBLICATI residui, poi cancella.
-- =========================================================
UPDATE pratiche.workflow_definizioni SET stato='RITIRATA'
 WHERE tipo_prestazione_id IN (SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno='TEST_BZU')
   AND emittente_fiscale_id IS NOT NULL AND stato='PUBBLICATA';
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
  SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno='TEST_BZU');
DELETE FROM pratiche.tipi_prestazione WHERE codice_interno='TEST_BZU';

-- =========================================================
-- 0) Precondizioni
-- =========================================================
CREATE TEMP TABLE tmp_bzu_refs AS
SELECT script.fn_pgtap_emittente_operatore() AS emittente_id;
SELECT ok((SELECT emittente_id IS NOT NULL FROM tmp_bzu_refs), '0. Precondizioni (emittente)');

-- =========================================================
-- 1) Setup: preset {A} + fork(X) -> pubblica
-- =========================================================
CREATE TEMP TABLE tmp_bzu_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_BZU','TEST_BZU','Bozza unica per scope',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_bzu_preset AS
SELECT id AS preset_id FROM pratiche.workflow_definizioni
 WHERE tipo_prestazione_id=(SELECT tp_id FROM tmp_bzu_tp)
   AND emittente_fiscale_id IS NULL AND stato='PUBBLICATA';

-- Un template attivo nel preset (necessario per pubblicare i fork/versioni).
INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo, definizione_id)
VALUES ((SELECT tp_id FROM tmp_bzu_tp),'BZU_A','Step A',10,true,true,(SELECT preset_id FROM tmp_bzu_preset));

-- fork(preset, X) -> BOZZA (flusso pulito: scope X senza bozza) -> pubblica.
CREATE TEMP TABLE tmp_bzu_fork AS
SELECT pratiche.fn_fork_definizione(
         (SELECT preset_id FROM tmp_bzu_preset),
         (SELECT emittente_id FROM tmp_bzu_refs)) AS fork_id;
SELECT pratiche.fn_pubblica_definizione((SELECT fork_id FROM tmp_bzu_fork));

SELECT ok(
  (SELECT stato='PUBBLICATA' FROM pratiche.workflow_definizioni WHERE id=(SELECT fork_id FROM tmp_bzu_fork)),
  '1. fork(X) su scope pulito -> BOZZA -> pubblicata'
);

-- =========================================================
-- 2) nuova-versione(X pubblicata) -> BOZZA v2 -> pubblica
-- =========================================================
CREATE TEMP TABLE tmp_bzu_v2 AS
SELECT pratiche.fn_nuova_versione_definizione((SELECT fork_id FROM tmp_bzu_fork)) AS v2_id;
SELECT pratiche.fn_pubblica_definizione((SELECT v2_id FROM tmp_bzu_v2));

SELECT ok(
  (SELECT stato FROM pratiche.workflow_definizioni WHERE id=(SELECT fork_id FROM tmp_bzu_fork))='RITIRATA'
  AND (SELECT stato FROM pratiche.workflow_definizioni WHERE id=(SELECT v2_id FROM tmp_bzu_v2))='PUBBLICATA',
  '2. nuova-versione(pubblicata) -> BOZZA v2 -> pubblica (v1 RITIRATA, v2 PUBBLICATA)'
);

-- =========================================================
-- 3) Flusso pulito: scope X ha 0 BOZZA e 1 PUBBLICATA
-- =========================================================
SELECT is(
  (SELECT count(*) FILTER (WHERE stato='BOZZA') || '/' || count(*) FILTER (WHERE stato='PUBBLICATA')
     FROM pratiche.workflow_definizioni
    WHERE tipo_prestazione_id=(SELECT tp_id FROM tmp_bzu_tp)
      AND emittente_fiscale_id=(SELECT emittente_id FROM tmp_bzu_refs)),
  '0/1',
  '3. dopo il flusso pulito: scope X con 0 BOZZA e 1 PUBBLICATA'
);

-- =========================================================
-- 4) nuova-versione(v2 pubblicata) -> BOZZA v3 (ammesso: scope senza bozza)
-- =========================================================
CREATE TEMP TABLE tmp_bzu_v3 AS
SELECT pratiche.fn_nuova_versione_definizione((SELECT v2_id FROM tmp_bzu_v2)) AS v3_id;
SELECT is(
  (SELECT stato FROM pratiche.workflow_definizioni WHERE id=(SELECT v3_id FROM tmp_bzu_v3)),
  'BOZZA'::varchar,
  '4. nuova-versione(pubblicata) su scope senza bozza -> BOZZA v3 ammessa'
);

-- =========================================================
-- 5) nuova-versione(v2 pubblicata) di nuovo -> 515 (scope ha gia' la BOZZA v3)
-- =========================================================
SELECT throws_like(
  format('SELECT pratiche.fn_nuova_versione_definizione(%s)', (SELECT v2_id FROM tmp_bzu_v2)),
  '%bozza di edizione workflow per lo scope%',
  '5. seconda nuova-versione con BOZZA gia'' aperta nello scope -> 515'
);

-- =========================================================
-- 6) nuova-versione(BOZZA v3) -> 516 (sorgente non PUBBLICATA)
-- =========================================================
SELECT throws_like(
  format('SELECT pratiche.fn_nuova_versione_definizione(%s)', (SELECT v3_id FROM tmp_bzu_v3)),
  '%non e'' in stato PUBBLICATA%',
  '6. nuova-versione da sorgente BOZZA -> 516'
);

-- =========================================================
-- 7) nuova-versione(v1 RITIRATA) -> 516 (sorgente non PUBBLICATA)
-- =========================================================
SELECT throws_like(
  format('SELECT pratiche.fn_nuova_versione_definizione(%s)', (SELECT fork_id FROM tmp_bzu_fork)),
  '%non e'' in stato PUBBLICATA%',
  '7. nuova-versione da sorgente RITIRATA -> 516'
);

-- =========================================================
-- 8) fork(preset, X) con BOZZA v3 gia' aperta nello scope X -> 515
-- =========================================================
SELECT throws_like(
  format('SELECT pratiche.fn_fork_definizione(%s, %s)',
         (SELECT preset_id FROM tmp_bzu_preset),
         (SELECT emittente_id FROM tmp_bzu_refs)),
  '%bozza di edizione workflow per lo scope%',
  '8. fork su scope X con BOZZA gia'' aperta -> 515'
);

-- =========================================================
-- 9) Cleanup (ritira i fork PUBBLICATI, poi cancella)
-- =========================================================
UPDATE pratiche.workflow_definizioni SET stato='RITIRATA'
 WHERE tipo_prestazione_id=(SELECT tp_id FROM tmp_bzu_tp)
   AND emittente_fiscale_id IS NOT NULL AND stato='PUBBLICATA';
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id=(SELECT tp_id FROM tmp_bzu_tp);
DELETE FROM pratiche.tipi_prestazione WHERE codice_interno='TEST_BZU';

SELECT pass('9. Cleanup completato');

SELECT * FROM finish();
