-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: un billing account, un listino e i documenti con l'azienda diretta
--   stanno su un'utility che l'azienda gestisce; la riga dell'azienda non si
--   cancella finche' qualcuno la usa.
--   Brief: brief-db-utility-gestite-dall-emittente §6 (D-U-2, D-U-4, D-U-9, D-U-12), §9 (V4, V5).
--   ChangeSet: 20261127-36 (collegamento del BA, listino per categoria),
--   -37 (l'utility del collegamento), -38 (documenti di vendita), -39 (fixture).
-- ------------------------------------------------------------
-- Elenco test (plan 10):
--  La forma
--   1) le sette FK verso emittenti_fiscali_utilities, composte e differite
--   2) la riga predefinita del collegamento non ha utility
--  L'azienda di prova gestisce le utility ammesse (fixture)
--   3) nasce un BA su un'utility gestita
--   4) il collegamento porta l'utility del BA
--  La cancellazione della riga dell'azienda (D-U-9)
--   5) con un BA che la usa: rifiutata (23503)
--   6) senza BA ne' documenti: passa
--  Un'utility che l'azienda non gestisce (D-U-2, D-U-4)
--   7) un BA su quell'utility: rifiutato (23503)
--   8) un listino su quell'utility: rifiutato (23503)
--   9) il cambio d'azienda del BA verso un'azienda che non la gestisce: rifiutato (23503)
--  10) l'utility del collegamento non si cambia (lucchetto di colonna)
--
-- Scopo:
--  - i casi si COSTRUISCONO: un'azienda nuova (dbops.fn_pgtap_crea_emittente_
--    operatore) che gestisce ogni utility ammessa per EF; le si toglie il
--    telefono (TEL) per avere un'utility non gestita. Una seconda azienda, a cui
--    si toglie l'energia (ENE), per il cambio d'azienda;
--  - con SET CONSTRAINTS ALL IMMEDIATE le FK differite si giudicano a fine
--    istruzione: e' il comportamento al COMMIT di una transazione di una
--    istruzione sola.
-- ------------------------------------------------------------

BEGIN;

CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

CREATE TEMP TABLE _u AS
SELECT (SELECT u.id FROM config.utilities u WHERE u.codice = 'ENE') AS ene,
       (SELECT u.id FROM config.utilities u WHERE u.codice = 'TEL') AS tel;

-- ============================================================
-- La forma
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM pg_constraint c
    WHERE c.contype = 'f'
      AND c.confrelid = 'anagrafiche.emittenti_fiscali_utilities'::regclass
      AND c.conname IN ('fk_emittenti_fiscali_ba_utility_gestita',
                        'fk_categorie_clienti_listini_utility_gestita',
                        'fk_listini_utility_gestita', 'fk_commesse_utility_gestita',
                        'fk_fatture_utility_gestita', 'fk_registri_fatturazione_utility_gestita',
                        'fk_fatturazione_lotti_utility_gestita')
      AND array_length(c.conkey, 1) = 2
      AND c.condeferrable AND c.condeferred),
  7,
  '1) sette FK composte e differite verso la riga dell''azienda');

SELECT is(
  (SELECT count(*)::int FROM anagrafiche.emittenti_fiscali_billing_account l
    WHERE l.is_default AND l.utility_id IS NOT NULL),
  0,
  '2) la riga predefinita del collegamento non ha utility');

-- ============================================================
-- L'azienda di prova gestisce le utility ammesse
-- ============================================================
SELECT lives_ok(
  format($$CREATE TEMP TABLE _ba AS
           SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('utility gestita', %s, %s)$$,
         (SELECT ene FROM _u), (SELECT soggetto_ruolo_id FROM _mondo)),
  '3) nasce un billing account su un''utility che l''azienda gestisce');

SELECT is(
  (SELECT l.utility_id FROM anagrafiche.emittenti_fiscali_billing_account l
    WHERE l.billing_account_id = (SELECT billing_account_id FROM _ba)),
  (SELECT ene FROM _u),
  '4) il collegamento porta l''utility del billing account');

-- ============================================================
-- La cancellazione della riga dell'azienda
-- ============================================================
SELECT throws_ok(
  format($$DELETE FROM anagrafiche.emittenti_fiscali_utilities
            WHERE emittente_soggetto_ruolo_id = %s AND utility_id = %s$$,
         (SELECT soggetto_ruolo_id FROM _mondo), (SELECT ene FROM _u)),
  '23503',
  NULL,
  '5) la riga dell''azienda con un billing account non si cancella');

SELECT lives_ok(
  format($$DELETE FROM anagrafiche.emittenti_fiscali_utilities
            WHERE emittente_soggetto_ruolo_id = %s AND utility_id = %s$$,
         (SELECT soggetto_ruolo_id FROM _mondo), (SELECT tel FROM _u)),
  '6) senza billing account ne'' documenti la riga si cancella');

-- ============================================================
-- Un'utility che l'azienda non gestisce
-- ============================================================
SELECT throws_ok(
  format($$SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('utility non gestita', %s, %s)$$,
         (SELECT tel FROM _u), (SELECT soggetto_ruolo_id FROM _mondo)),
  '23503',
  NULL,
  '7) un billing account su un''utility che l''azienda non gestisce: rifiutato');

-- Il listino nasce per l'azienda di chi agisce (la fixture lo dice).
SELECT throws_ok(
  format($$SELECT * FROM dbops.fn_pgtap_crea_listino(%s, 'utility non gestita')$$,
         (SELECT tel FROM _u)),
  '23503',
  NULL,
  '8) un listino su un''utility che l''azienda non gestisce: rifiutato');

-- Una seconda azienda che non gestisce l'energia.
CREATE TEMP TABLE _altra AS
SELECT e.* FROM dbops.fn_pgtap_crea_emittente() e;
DELETE FROM anagrafiche.emittenti_fiscali_utilities r
 USING _altra a, _u
 WHERE r.emittente_soggetto_ruolo_id = a.soggetto_ruolo_id AND r.utility_id = _u.ene;

SELECT throws_ok(
  format($$UPDATE anagrafiche.emittenti_fiscali_billing_account
              SET emittente_soggetto_ruolo_id = %s
            WHERE billing_account_id = %s$$,
         (SELECT soggetto_ruolo_id FROM _altra), (SELECT billing_account_id FROM _ba)),
  '23503',
  NULL,
  '9) il billing account non passa a un''azienda che non gestisce la sua utility');

SELECT throws_ok(
  format($$UPDATE anagrafiche.emittenti_fiscali_billing_account SET utility_id = %s
            WHERE billing_account_id = %s$$,
         (SELECT tel FROM _u), (SELECT billing_account_id FROM _ba)),
  'P0001',
  NULL,
  '10) l''utility del collegamento non si cambia');

SELECT * FROM finish();

ROLLBACK;
