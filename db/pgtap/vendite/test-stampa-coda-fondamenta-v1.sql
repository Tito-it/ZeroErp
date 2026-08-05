-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: fondamenta (G1) del cockpit stampa fatture
--       (brief-db-processi-fatturazione-cockpit §3/§4/§5;
--        migrations 20260720-01..02 + seed azioni/registry/impl/task_policy).
--       Verifica struttura coda outbox + funzione accodatore + seed inerti,
--       PRIMA che il task stampa sia armato in pipeline (G2, alla release BE).
-- ------------------------------------------------------------
-- Indice test (1..18):
--   1)  esiste tabella vendite.fatture_stampa_coda
--   2)  colonna stato
--   3)  colonna sorgente_id
--   4)  colonna sorgente_uid
--   5)  colonna tentativi
--   6)  colonna ultimo_errore
--   7)  colonna documento_id
--   8)  stato e' text
--   9)  CHECK chk_fatture_stampa_coda_stato presente
--  10)  indice unico PARZIALE anti-doppione (uq_fatture_stampa_coda_vivo)
--  11)  indice di polling PARZIALE (ix_fatture_stampa_coda_da_lavorare)
--  12)  FK sorgente_id -> vendite.fatture
--  13)  esiste vendite.fn_accoda_stampe_lotto(bigint)
--  14)  fn ritorna integer
--  15)  seed: 2 azioni_processo attive (approva_attivita_commessa, numera_fatture_lotti)
--  16)  seed: numera_fatture_lotti e' pericolosa
--  17)  seed: registry+impl stampa_documenti_lotto attivi e default
--  18)  seed: 2 task_policy stampa su pipeline 4 e 6 (annullabile, RESUME_TASK)
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(18);

-- ============================================================
-- Struttura tabella coda
-- ============================================================
SELECT has_table('vendite', 'fatture_stampa_coda',
    'esiste la coda outbox vendite.fatture_stampa_coda');
SELECT has_column('vendite', 'fatture_stampa_coda', 'stato',
    'coda: colonna stato');
SELECT has_column('vendite', 'fatture_stampa_coda', 'sorgente_id',
    'coda: colonna sorgente_id');
SELECT has_column('vendite', 'fatture_stampa_coda', 'sorgente_uid',
    'coda: colonna sorgente_uid');
SELECT has_column('vendite', 'fatture_stampa_coda', 'tentativi',
    'coda: colonna tentativi');
SELECT has_column('vendite', 'fatture_stampa_coda', 'ultimo_errore',
    'coda: colonna ultimo_errore');
SELECT has_column('vendite', 'fatture_stampa_coda', 'documento_id',
    'coda: colonna documento_id');
SELECT col_type_is('vendite', 'fatture_stampa_coda', 'stato', 'text',
    'coda: stato e'' text');

SELECT ok(
    (SELECT count(*) = 1
       FROM pg_constraint
      WHERE conname = 'chk_fatture_stampa_coda_stato'
        AND conrelid = 'vendite.fatture_stampa_coda'::regclass),
    'coda: CHECK chk_fatture_stampa_coda_stato presente');

-- Indice unico PARZIALE = anti doppio-accodamento sui work-item vivi.
SELECT ok(
    (SELECT indisunique AND indpred IS NOT NULL
       FROM pg_index
      WHERE indexrelid = 'vendite.uq_fatture_stampa_coda_vivo'::regclass),
    'coda: uq_fatture_stampa_coda_vivo e'' unico e parziale');

SELECT ok(
    (SELECT indpred IS NOT NULL
       FROM pg_index
      WHERE indexrelid = 'vendite.ix_fatture_stampa_coda_da_lavorare'::regclass),
    'coda: ix_fatture_stampa_coda_da_lavorare e'' parziale');

SELECT ok(
    (SELECT count(*) = 1
       FROM pg_constraint
      WHERE conname = 'fk_fatture_stampa_coda_fattura'
        AND conrelid = 'vendite.fatture_stampa_coda'::regclass
        AND confrelid = 'vendite.fatture'::regclass),
    'coda: FK sorgente_id -> vendite.fatture');

-- ============================================================
-- Funzione accodatore
-- ============================================================
SELECT has_function('vendite', 'fn_accoda_stampe_lotto', ARRAY['bigint'],
    'esiste vendite.fn_accoda_stampe_lotto(bigint)');
SELECT function_returns('vendite', 'fn_accoda_stampe_lotto', ARRAY['bigint'], 'integer',
    'fn_accoda_stampe_lotto ritorna integer');

-- ============================================================
-- Seed (inerti finche' G2 non arma il task in pipeline)
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM config.azioni_processo
      WHERE permission_codename IN ('approva_attivita_commessa', 'numera_fatture_lotti')
        AND attivo),
    2, 'seed: 2 azioni_processo attive');

SELECT ok(
    (SELECT pericolosa FROM config.azioni_processo
      WHERE permission_codename = 'numera_fatture_lotti'),
    'seed: numera_fatture_lotti e'' pericolosa');

SELECT is(
    (SELECT count(*)::int
       FROM dbops.pipeline_task_registry r
       JOIN dbops.pipeline_task_registry_impl i ON i.task_registry_id = r.id
      WHERE r.task_code = 'stampa_documenti_lotto'
        AND r.attivo AND i.attivo AND i.is_default
        AND i.handler_code = 'stampa_documenti_lotto_default'),
    1, 'seed: registry+impl stampa_documenti_lotto attivi e default');

SELECT is(
    (SELECT count(*)::int FROM vendite.fatturazione_pipeline_task_policy
      WHERE task_code = 'stampa_documenti_lotto'
        AND pipeline_id IN (4, 6)
        AND annullabile
        AND resume_mode = 'RESUME_TASK'
        AND attivo),
    2, 'seed: 2 task_policy stampa su pipeline DEFINITIVA 4 e 6');

SELECT * FROM finish();
ROLLBACK;
