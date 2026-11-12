-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: config.note_stili — l'assenza di una nota e' NULL, mai ''
-- Riferimento: brief-db-token-null-dei-seed (D3); changeSet 90_end/20261112-58
--   (il CHECK) e il mirror 80_data/20260519-02 (le celle NULL del CSV).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la nota stringa vuota e' rifiutata dal suo vincolo; una stringa di soli
--     spazi vale come vuota;
--   - NULL passa: e' la forma dell'assenza; una nota vera passa;
--   - il seed non scrive la stringa vuota.
--   La riga di prova e' lo stile DEFAULT del seed: l'UPDATE si annulla col
--   ROLLBACK finale. Che il pannello porti '' a NULL lo prova
--   config/test-fn-pannello-scrivi-stringa-vuota-v1.
--
-- Elenco test (plan 6):
--   1) il vincolo esiste
--   2) nota '' rifiutata da chk_note_stili_note_non_vuota
--   3) una stringa di soli spazi vale come vuota
--   4) nota NULL: la riga passa
--   5) una nota vera: la riga passa
--   6) il seed: nessuna nota stringa vuota
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- L'UPDATE della riga di prova con la nota indicata.
CREATE OR REPLACE FUNCTION pg_temp.scrivi(p_note text)
RETURNS text LANGUAGE sql AS $f$
  SELECT format('UPDATE config.note_stili SET note = %1$L WHERE codice_interno = %2$L',
                p_note, 'DEFAULT');
$f$;

SELECT is(
  (SELECT count(*)::int FROM pg_catalog.pg_constraint
    WHERE conrelid = 'config.note_stili'::regclass
      AND contype = 'c'
      AND conname = 'chk_note_stili_note_non_vuota'),
  1,
  '1) il vincolo esiste');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.scrivi('')),
          'chk_note_stili_note_non_vuota',
          '2) nota vuota: rifiutata dal suo vincolo');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.scrivi('   ')),
          'chk_note_stili_note_non_vuota',
          '3) una stringa di soli spazi vale come vuota');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.scrivi(NULL)),
          NULL,
          '4) nota NULL: la riga passa');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.scrivi('Una nota')),
          NULL,
          '5) una nota vera: la riga passa');

-- Il seed e' contratto (80_data): lo si legge, non si conta una popolazione.
SELECT is(
  (SELECT count(*) FROM config.note_stili ns WHERE btrim(ns.note) = '')::int,
  0,
  '6) il seed: nessuna nota stringa vuota');

SELECT * FROM finish();
ROLLBACK;
