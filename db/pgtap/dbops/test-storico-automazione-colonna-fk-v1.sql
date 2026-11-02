-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test — l'automazione STORICO non monta un trigger che non potra' chiudere
--   dbops.fn_run_automations_storico (rubinetto E_STORICO_FK_COL_ASSENTE)
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test fa DDL — crea una madre in config e la sua gemella in storico, e rinomina una colonna della gemella; e' il percorso delle migrazioni e di ci_apply, non dell'applicazione
--
-- Brief: brief-db-storico-colonna-fk-dei-trigger.md §5.2
-- ChangeSet: 20_code/dbops/20260925-27
--
-- ⭐ IL CASO SI COSTRUISCE. Una madre `config.pgtap_sto_fk` e una gemella con
--   la colonna FK chiamata in un altro modo (`pgtap_sto_fk_rif` invece di
--   `pgtap_sto_fk_id`, il nome che l'automazione passerebbe): e' la forma delle
--   cinque gemelle del 2025. Poi la si rinomina al nome giusto e si verifica
--   che il trigger nasca e funzioni. Il ROLLBACK pulisce tutto.
--
-- ⚠️ La gemella e' una copia della FORMA di storico.parameters (LIKE, dopo
--   20260925-26 la sua FK si chiama parameters_id): cosi' ha le colonne che il
--   trigger scrive, senza ripetere qui la DDL di fn_ensure_storico_table.
--   La forma di `id` diverge fra le macchine (vedi la fixture): la copia la
--   porta con se' in entrambe le forme.
--
-- ⚠️ L'automazione scorre tutto lo schema config: le altre madri hanno gia' il
--   trigger e vengono saltate. Se una di loro fosse rotta, i test 1-3
--   nominerebbero lei e non pgtap_sto_fk — il messaggio lo dice.
--
-- Elenco test (plan 7):
--   1 : colonna FK assente nella gemella → P0001
--   2 : …con la frase del catalogo, che nomina colonna, gemella e madre
--   3 : anche in dry run solleva (un «verrebbe creato» su un trigger rotto e'
--       una risposta sbagliata)
--   4 : rinominata la colonna al nome dell'automazione → l'automazione vive
--   5 : il trigger e' nato, con l'argomento pgtap_sto_fk_id
--   6 : UPDATE di una riga storicizzata della madre: vive
--   7 : lo snapshot e' nella gemella
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TABLE config.pgtap_sto_fk (
    id         bigint PRIMARY KEY,
    nota       text,
    storicizza boolean DEFAULT true
);

-- ⚠️ INCLUDING IDENTITY non e' ridondante: storico.parameters.id e' un default
--   nextval(...) su dbdev (gemella ricreata dal provisioning) e una colonna
--   IDENTITY su un DB da zero. INCLUDING DEFAULTS copia solo il primo: senza
--   IDENTITY, sulla CI la copia nasceva con `id` senza generatore e lo snapshot
--   moriva su NOT NULL (test 6-7 rossi su zeroerp_ci, verdi su dbdev, 2026-09-25).
CREATE TABLE storico.pgtap_sto_fk (LIKE storico.parameters INCLUDING DEFAULTS INCLUDING IDENTITY INCLUDING CONSTRAINTS);
ALTER TABLE storico.pgtap_sto_fk RENAME COLUMN parameters_id TO pgtap_sto_fk_rif;

INSERT INTO config.pgtap_sto_fk (id, nota, storicizza) VALUES (1, 'prima', true);

-- ============================================================
-- Il rubinetto
-- ============================================================
-- 1
SELECT throws_ok(
  $$ SELECT dbops.fn_run_automations_storico('SCHEDULED', ARRAY['config'], false) $$,
  'P0001',
  NULL,
  'Colonna FK assente nella gemella: l''automazione solleva invece di montare il trigger'
);

-- 2
SELECT throws_like(
  $$ SELECT dbops.fn_run_automations_storico('SCHEDULED', ARRAY['config'], false) $$,
  '%colonna pgtap_sto_fk_id non esiste in storico.pgtap_sto_fk%config.pgtap_sto_fk%',
  'La frase nomina la colonna cercata, la gemella e la madre'
);

-- 3
SELECT throws_like(
  $$ SELECT dbops.fn_run_automations_storico('SCHEDULED', ARRAY['config'], true) $$,
  '%colonna pgtap_sto_fk_id non esiste in storico.pgtap_sto_fk%',
  'Anche in dry run: non promette un trigger che non potrebbe chiudere'
);

-- ============================================================
-- Il nome giusto
-- ============================================================
ALTER TABLE storico.pgtap_sto_fk RENAME COLUMN pgtap_sto_fk_rif TO pgtap_sto_fk_id;

-- 4
SELECT lives_ok(
  $$ SELECT dbops.fn_run_automations_storico('SCHEDULED', ARRAY['config'], false) $$,
  'Con la colonna al nome dell''automazione il trigger si monta'
);

-- 5
SELECT is(
  (SELECT split_part(encode(t.tgargs, 'escape'), E'\\000', 1)
     FROM pg_trigger t
     JOIN pg_proc p ON p.oid = t.tgfoid
    WHERE t.tgrelid = 'config.pgtap_sto_fk'::regclass
      AND NOT t.tgisinternal
      AND p.proname = 'trgfn_storico_generic'),
  'pgtap_sto_fk_id',
  'Il trigger di storico e'' nato, con l''argomento pgtap_sto_fk_id'
);

-- 6
SELECT lives_ok(
  $$ UPDATE config.pgtap_sto_fk SET nota = 'dopo' WHERE id = 1 $$,
  'UPDATE di una riga storicizzata della madre: vive'
);

-- 7
SELECT ok(
  EXISTS (SELECT 1 FROM storico.pgtap_sto_fk WHERE pgtap_sto_fk_id = 1),
  'Lo snapshot e'' nella gemella, legato per pgtap_sto_fk_id'
);

SELECT * FROM finish();

ROLLBACK;
