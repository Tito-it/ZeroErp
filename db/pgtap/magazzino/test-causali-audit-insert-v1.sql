-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: magazzino.causali — user_insert nella forma di linee-guida-sql §7
-- Riferimento: brief-db-nullvalue-vuoto-cinque-mirror; changeSet
--   90_end/20261112-39 e il mirror 80_data/20251001-51 (senza le colonne di
--   audit).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - user_insert e' NOT NULL con default CURRENT_USER: chi inserisce senza
--     dichiararla (il pannello, il seed) scrive il ruolo che inserisce;
--   - il seed non lascia colonne di audit vuote: nessuna user_insert NULL o
--     vuota, nessuna user_update vuota.
--   ⚠️ Il test non costruisce una causale: l'applicazione non ha INSERT sulla
--     tabella (la scrive il pannello, SECURITY DEFINER). Il contratto e' la
--     struttura della colonna, e la legge da li'.
--
-- Elenco test (plan 3):
--   1) user_insert e' NOT NULL
--   2) user_insert ha default CURRENT_USER
--   3) il seed: nessuna colonna di audit vuota
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(3);

SELECT col_not_null('magazzino', 'causali', 'user_insert',
                    '1) user_insert e'' NOT NULL');

SELECT col_default_is('magazzino', 'causali', 'user_insert', 'CURRENT_USER',
                      '2) user_insert ha default CURRENT_USER');

-- Il seed e' contratto (80_data): lo si legge, non si conta una popolazione.
SELECT is(
  (SELECT count(*) FROM magazzino.causali c
    WHERE NULLIF(btrim(c.user_insert), '') IS NULL
       OR btrim(c.user_update) = '')::int,
  0,
  '3) il seed: nessuna colonna di audit vuota');

SELECT * FROM finish();
ROLLBACK;
