-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
--   4)  NESSUNA colonna sorgente_uid: era il doppione testuale di sorgente_id
--        (ritirata da 20261108-18, brief-db-sorgente-documento-e-riga lotto D)
--   5)  colonna tentativi
--   6)  colonna ultimo_errore
--   7)  colonna documento_id
--   8)  stato e' text
--   9)  CHECK chk_fatture_stampa_coda_stato presente
--  10)  vincolo di ESCLUSIONE parziale anti-doppione (ex_fatture_stampa_coda_vivo,
--        al posto di uq_fatture_stampa_coda_vivo dal 2026-10-20: 20261020-29/-31)
--  11)  indice di polling PARZIALE (ix_fatture_stampa_coda_da_lavorare)
--  12)  FK sorgente_id -> vendite.fatture
--  13)  esiste vendite.fn_accoda_stampe_lotto(bigint, bigint) (il tipo da stampare, 20261020-30)
--  14)  fn ritorna integer
--  15)  seed: 2 azioni_processo attive (approva_attivita_commessa, numera_fatture_lotti)
--  16)  seed: numera_fatture_lotti e' pericolosa
--  17)  seed: registry+impl stampa_documenti_lotto attivi e default
--  18)  seed: 2 task_policy stampa su pipeline 4 e 6 (annullabile, RESUME_TASK)
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

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
SELECT hasnt_column('vendite', 'fatture_stampa_coda', 'sorgente_uid',
    'coda: nessuna colonna sorgente_uid, la fattura sta in sorgente_id');
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

-- Vincolo di esclusione PARZIALE = anti doppio-accodamento sui work-item vivi,
-- per (fattura, tipo); il tipo NULL copre tutti (brief-db-modelli-documento-standard
-- §9.2 Q-2). Si guarda la clausola, non solo il nome: senza il WHERE la ristampa
-- dopo FATTO sarebbe impossibile, senza l'intervallo sul tipo il NULL non
-- escluderebbe niente. I casi li prova test-stampa-coda-tipo-documento-v1.
SELECT is(
    (SELECT pg_get_constraintdef(c.oid)
       FROM pg_constraint c
      WHERE c.conrelid = 'vendite.fatture_stampa_coda'::regclass
        AND c.conname = 'ex_fatture_stampa_coda_vivo'
        AND c.contype = 'x'),
    'EXCLUDE USING gist (sorgente_tipo_id WITH =, sorgente_id WITH =, '
    || 'int8range(tipo_documento_output_id, tipo_documento_output_id, ''[]''::text) WITH &&) '
    || 'WHERE ((stato = ANY (ARRAY[''PENDING''::text, ''IN_CORSO''::text])))',
    'coda: ex_fatture_stampa_coda_vivo e'' un''esclusione parziale per (fattura, tipo)');

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
SELECT has_function('vendite', 'fn_accoda_stampe_lotto', ARRAY['bigint', 'bigint'],
    'esiste vendite.fn_accoda_stampe_lotto(bigint, bigint)');
SELECT function_returns('vendite', 'fn_accoda_stampe_lotto', ARRAY['bigint', 'bigint'], 'integer',
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
