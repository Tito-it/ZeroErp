-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: config.iva_assoggettamenti — l'assenza di una nota e' NULL, mai ''
-- Riferimento: brief-db-nullvalue-vuoto-cinque-mirror; changeSet
--   90_end/20261112-36 (il CHECK) e il mirror 80_data/20250814-04
--   (nullValue "NULL").
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la nota stringa vuota e' rifiutata dal suo vincolo; una stringa di soli
--     spazi vale come vuota;
--   - NULL passa: e' la forma dell'assenza; una nota vera passa;
--   - il seed non scrive la stringa vuota.
--   Le righe di prova si costruiscono qui, con id e codici fuori scala.
--   ⚠️ Il test 6 prova il RISULTATO, non chi lo produce: anche la conversione di
--     20261112-36 porta a NULL le stringhe vuote. Che le scriva il loader col
--     nullValue nuovo si prova col render offline del mirror (brief, §4).
--
-- Elenco test (plan 6):
--   1) il vincolo esiste
--   2) note '' rifiutata da chk_iva_assoggettamenti_note_non_vuota
--   3) una stringa di soli spazi vale come vuota
--   4) note NULL: la riga entra
--   5) una nota vera: la riga entra
--   6) il seed: nessuna riga ha la nota stringa vuota
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- Una riga di prova con la nota indicata.
CREATE OR REPLACE FUNCTION pg_temp.riga(p_id integer, p_note text)
RETURNS text LANGUAGE sql AS $f$
  SELECT format(
    'INSERT INTO config.iva_assoggettamenti (id, codice, descrizione, note) '
    'VALUES (%1$s, %2$L, %3$L, %4$L)',
    p_id, 'ZZN' || p_id, 'Prova note vuote', p_note);
$f$;

SELECT is(
  (SELECT count(*)::int FROM pg_catalog.pg_constraint
    WHERE conrelid = 'config.iva_assoggettamenti'::regclass
      AND contype = 'c'
      AND conname = 'chk_iva_assoggettamenti_note_non_vuota'),
  1,
  '1) il vincolo esiste');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riga(990001, '')),
          'chk_iva_assoggettamenti_note_non_vuota',
          '2) nota vuota: rifiutata dal suo vincolo');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riga(990002, '   ')),
          'chk_iva_assoggettamenti_note_non_vuota',
          '3) una stringa di soli spazi vale come vuota');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riga(990003, NULL)),
          NULL,
          '4) nota NULL: la riga entra');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riga(990004, 'Una nota')),
          NULL,
          '5) una nota vera: la riga entra');

-- Il seed e' contratto (80_data): lo si legge, non si conta una popolazione.
SELECT is(
  (SELECT count(*) FROM config.iva_assoggettamenti ia WHERE ia.note = '')::int,
  0,
  '6) il seed: nessuna nota stringa vuota');

SELECT * FROM finish();
ROLLBACK;
