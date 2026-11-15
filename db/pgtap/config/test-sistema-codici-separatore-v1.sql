-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: config.sistema_codici — «nessun separatore» e' la stringa vuota
-- Riferimento: brief-db-token-null-dei-seed (D1); changeSet
--   90_end/20261112-53.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - separatore e' NOT NULL con default '': script.fn_generate_codice compone
--     prefisso || separatore || numero, e un NULL renderebbe NULL il codice;
--   - la creazione che non dichiara il separatore (il pannello col campo
--     vuoto) prende la stringa vuota;
--   - nessuna riga ha il separatore NULL.
--   ⚠️ Il test non costruisce una configurazione: una riga di sistema_codici
--     crea sequenze e trigger sulla tabella che numera. Il contratto e' la
--     struttura della colonna, e la legge da li'.
--
-- Elenco test (plan 3):
--   1) separatore e' NOT NULL
--   2) separatore ha default ''
--   3) nessuna riga ha il separatore NULL
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(3);

SELECT col_not_null('config', 'sistema_codici', 'separatore',
                    '1) separatore e'' NOT NULL');

SELECT col_default_is('config', 'sistema_codici', 'separatore', ''::text,
                      '2) separatore ha default stringa vuota');

-- Il seed e' contratto (80_data): lo si legge, non si conta una popolazione.
SELECT is(
  (SELECT count(*) FROM config.sistema_codici sc WHERE sc.separatore IS NULL)::int,
  0,
  '3) nessuna riga ha il separatore NULL');

SELECT * FROM finish();
ROLLBACK;
