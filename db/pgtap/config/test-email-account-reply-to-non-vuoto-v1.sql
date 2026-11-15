-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: config.email_account — senza Reply-To email_reply_to e' NULL, mai ''
-- Riferimento: brief-db-nullvalue-vuoto-cinque-mirror §7; changeSet
--   90_end/20261112-43 (il CHECK) e il mirror 80_data/20260329-60
--   (nullValue "NULL").
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - il Reply-To stringa vuota e' rifiutato dal suo vincolo, in INSERT e in
--     UPDATE (la modifica dal pannello e' un UPDATE); una stringa di soli spazi
--     vale come vuota;
--   - NULL passa: e' la forma dell'assenza; un indirizzo vero passa;
--   - svuotare un Reply-To esistente a NULL passa: e' cio' che scrive la PATCH;
--   - il seed non scrive la stringa vuota.
--   Le righe di prova si costruiscono qui, con codici fuori scala.
--   ⚠️ Il test 8 prova il RISULTATO, non chi lo produce: anche la conversione di
--     20261112-43 porta a NULL le stringhe vuote. Che le scriva il loader col
--     nullValue nuovo si prova col render offline del mirror (brief, §4).
--
-- Elenco test (plan 8):
--   1) il vincolo esiste
--   2) INSERT con Reply-To '' rifiutato da chk_email_account_email_reply_to_non_vuoto
--   3) una stringa di soli spazi vale come vuota
--   4) INSERT con Reply-To NULL: la riga entra
--   5) INSERT con un indirizzo vero: la riga entra
--   6) UPDATE di un Reply-To esistente a '': rifiutato dal suo vincolo
--   7) UPDATE di un Reply-To esistente a NULL: passa
--   8) il seed: nessun account ha il Reply-To stringa vuota
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- Un account di prova col Reply-To indicato (account di sistema: nessun reparto).
CREATE OR REPLACE FUNCTION pg_temp.riga(p_codice text, p_reply_to text)
RETURNS text LANGUAGE sql AS $f$
  SELECT format(
    'INSERT INTO config.email_account '
    '(codice, codice_interno, descrizione, smtp_host, smtp_username, '
    ' smtp_password_encrypted, email_from, email_reply_to) '
    'VALUES (%1$L, %1$L, %2$L, %3$L, %4$L, %5$L, %4$L, %6$L)',
    p_codice, 'Prova Reply-To vuoto', 'smtp.test.local', 'zzr@test.local',
    'encrypted_pwd_test', p_reply_to);
$f$;

SELECT is(
  (SELECT count(*)::int FROM pg_catalog.pg_constraint
    WHERE conrelid = 'config.email_account'::regclass
      AND contype = 'c'
      AND conname = 'chk_email_account_email_reply_to_non_vuoto'),
  1,
  '1) il vincolo esiste');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riga('ZZR_VUOTO', '')),
          'chk_email_account_email_reply_to_non_vuoto',
          '2) INSERT con Reply-To vuoto: rifiutato dal suo vincolo');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riga('ZZR_SPAZI', '   ')),
          'chk_email_account_email_reply_to_non_vuoto',
          '3) una stringa di soli spazi vale come vuota');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riga('ZZR_NULL', NULL)),
          NULL,
          '4) INSERT con Reply-To NULL: la riga entra');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riga('ZZR_VERO', 'risposte@test.local')),
          NULL,
          '5) INSERT con un indirizzo vero: la riga entra');

-- La modifica dal pannello e' un UPDATE: la si prova sulla riga del test 5.
SELECT is(dbops.fn_pgtap_codice_errore(
            $q$UPDATE config.email_account SET email_reply_to = ''
                WHERE codice_interno = 'ZZR_VERO'$q$),
          'chk_email_account_email_reply_to_non_vuoto',
          '6) UPDATE a Reply-To vuoto: rifiutato dal suo vincolo');

SELECT is(dbops.fn_pgtap_codice_errore(
            $q$UPDATE config.email_account SET email_reply_to = NULL
                WHERE codice_interno = 'ZZR_VERO'$q$),
          NULL,
          '7) UPDATE a Reply-To NULL: passa');

-- Il seed e' contratto (80_data): lo si legge, non si conta una popolazione.
SELECT is(
  (SELECT count(*) FROM config.email_account ea WHERE ea.email_reply_to = '')::int,
  0,
  '8) il seed: nessun Reply-To stringa vuota');

SELECT * FROM finish();
ROLLBACK;
