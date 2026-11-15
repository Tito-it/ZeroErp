-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: config.messaggi_errore — causa e soluzione assenti sono NULL, mai ''
-- Riferimento: brief-db-token-null-dei-seed (D3); changeSet
--   90_end/20261112-55 (i due CHECK) e il mirror 80_data/20260614-08 (le
--   celle NULL del CSV).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la causa o la soluzione stringa vuota sono rifiutate dal loro vincolo;
--     una stringa di soli spazi vale come vuota;
--   - NULL passa: e' la forma dell'assenza; un testo vero passa;
--   - il seed non scrive la stringa vuota.
--   La riga di prova e' E_GENERICO in italiano, che esiste dal bootstrap:
--   l'UPDATE si annulla col ROLLBACK finale.
--   ⚠️ Il test 8 prova il RISULTATO, non chi lo produce: anche la conversione
--     di 20261112-55 porta a NULL le stringhe vuote. Che le scriva il loader si
--     prova col render offline del mirror (brief, §4).
--
-- Elenco test (plan 8):
--   1) i due vincoli esistono
--   2) causa '' rifiutata da chk_messaggi_errore_causa_non_vuota
--   3) causa di soli spazi: vale come vuota
--   4) soluzione '' rifiutata da chk_messaggi_errore_soluzione_non_vuota
--   5) soluzione di soli spazi: vale come vuota
--   6) causa e soluzione NULL: la riga passa
--   7) causa e soluzione vere: la riga passa
--   8) il seed: nessuna causa o soluzione stringa vuota
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- L'UPDATE della riga di prova con la causa e la soluzione indicate.
CREATE OR REPLACE FUNCTION pg_temp.scrivi(p_causa text, p_soluzione text)
RETURNS text LANGUAGE sql AS $f$
  SELECT format(
    'UPDATE config.messaggi_errore SET causa = %1$L, soluzione = %2$L '
    'WHERE codice = %3$L AND lingua = %4$L',
    p_causa, p_soluzione, 'E_GENERICO', 'it');
$f$;

SELECT is(
  (SELECT count(*)::int FROM pg_catalog.pg_constraint
    WHERE conrelid = 'config.messaggi_errore'::regclass
      AND contype = 'c'
      AND conname IN ('chk_messaggi_errore_causa_non_vuota',
                      'chk_messaggi_errore_soluzione_non_vuota')),
  2,
  '1) i due vincoli esistono');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.scrivi('', NULL)),
          'chk_messaggi_errore_causa_non_vuota',
          '2) causa vuota: rifiutata dal suo vincolo');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.scrivi('   ', NULL)),
          'chk_messaggi_errore_causa_non_vuota',
          '3) una causa di soli spazi vale come vuota');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.scrivi(NULL, '')),
          'chk_messaggi_errore_soluzione_non_vuota',
          '4) soluzione vuota: rifiutata dal suo vincolo');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.scrivi(NULL, '   ')),
          'chk_messaggi_errore_soluzione_non_vuota',
          '5) una soluzione di soli spazi vale come vuota');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.scrivi(NULL, NULL)),
          NULL,
          '6) causa e soluzione NULL: la riga passa');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.scrivi('Una causa', 'Una soluzione')),
          NULL,
          '7) causa e soluzione vere: la riga passa');

-- Il seed e' contratto (80_data): lo si legge, non si conta una popolazione.
-- ⚠️ Dopo il test 7 la riga E_GENERICO ha testi veri: non pesa sul conteggio.
SELECT is(
  (SELECT count(*) FROM config.messaggi_errore me
    WHERE btrim(me.causa) = '' OR btrim(me.soluzione) = '')::int,
  0,
  '8) il seed: nessuna causa o soluzione stringa vuota');

SELECT * FROM finish();
ROLLBACK;
