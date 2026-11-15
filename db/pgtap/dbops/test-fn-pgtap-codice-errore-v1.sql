-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_codice_errore — che cosa ha rifiutato un'istruzione
-- Riferimento: changeSet 20261112-28 (il building block, che ritira le copie
--   locali in pg_temp dei pgTAP).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - un'istruzione che passa rende NULL, e le sue scritture restano;
--   - un rifiuto di dominio (fn_log_and_raise_error) rende il CODICE, non la frase;
--   - un vincolo violato rende il NOME del vincolo, per CHECK e per UNIQUE;
--   - un RAISE senza codice rende P0001, ogni altro errore il suo SQLSTATE: un
--     errore inatteso non interrompe il file;
--   - le scritture di un'istruzione rifiutata si annullano;
--   ⚠️ Che nessun pgTAP ricopi la lettura non si prova da qui: i file dei test non
--     stanno nel database. Si verifica sui file: in db/pgtap nessuna funzione
--     pg_temp col nome codice_errore.
--   I casi si costruiscono qui, su una tabella temporanea: nessuno pesca dal
--   catalogo un vincolo o un verbo che domani potrebbe cambiare forma, tranne il
--   rifiuto di dominio, preso da un verbo con un codice stabile.
--
-- Elenco test (plan 8):
--   1) la funzione esiste, con un argomento text
--   2) un'istruzione che passa: NULL
--   3) ... e la sua scrittura resta
--   4) un rifiuto di dominio: il codice
--   5) un CHECK violato: il nome del vincolo
--   6) una UNIQUE violata: il nome del vincolo
--   7) un RAISE senza codice: P0001
--   8) un errore che non e' un rifiuto (divisione per zero): il suo SQLSTATE,
--      e nessuna riga scritta
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

CREATE TEMP TABLE t_prova (
    id     integer PRIMARY KEY,
    valore integer NOT NULL,
    CONSTRAINT chk_t_prova_valore_positivo CHECK (valore > 0),
    CONSTRAINT uq_t_prova_valore UNIQUE (valore)
);

SELECT has_function('dbops', 'fn_pgtap_codice_errore', ARRAY['text'],
    '1) dbops.fn_pgtap_codice_errore esiste, con un argomento text');

SELECT is(dbops.fn_pgtap_codice_errore($$INSERT INTO t_prova VALUES (1, 10)$$),
          NULL,
          '2) un''istruzione che passa: NULL');

SELECT is((SELECT count(*) FROM t_prova WHERE id = 1), 1::bigint,
          '3) ... e la sua scrittura resta nella transazione del test');

SELECT is(dbops.fn_pgtap_codice_errore($$SELECT script.fn_scrivi_riga_da_jsonb(NULL, '{}'::jsonb)$$),
          'E_SCRIPT_CHIAMATA_NON_VALIDA',
          '4) un rifiuto di dominio: il codice, non la frase');

SELECT is(dbops.fn_pgtap_codice_errore($$INSERT INTO t_prova VALUES (2, -1)$$),
          'chk_t_prova_valore_positivo',
          '5) un CHECK violato: il nome del vincolo');

SELECT is(dbops.fn_pgtap_codice_errore($$INSERT INTO t_prova VALUES (3, 10)$$),
          'uq_t_prova_valore',
          '6) una UNIQUE violata: il nome del vincolo');

SELECT is(dbops.fn_pgtap_codice_errore($q$DO $x$ BEGIN RAISE EXCEPTION 'nessun codice'; END $x$$q$),
          'P0001',
          '7) un RAISE senza codice: P0001');

SELECT is(dbops.fn_pgtap_codice_errore($$INSERT INTO t_prova VALUES (4, 1 / 0)$$)
          || '|' || (SELECT count(*) FROM t_prova)::text,
          '22012|1',
          '8) un errore che non e'' un rifiuto: il suo SQLSTATE, e nessuna riga scritta');

SELECT * FROM finish();
ROLLBACK;
