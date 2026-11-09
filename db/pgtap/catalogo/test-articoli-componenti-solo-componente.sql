-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Regola: un articolo «solo componente» non e' il padre di una distinta.
--
-- La regola ha due sedi, che qui si provano insieme:
--   - il CHECK chk_articoli_composito_non_solo_componente di catalogo.articoli:
--     un articolo non e' insieme composito e solo componente;
--   - il lato documento della check della distinta (script.fn_articolo_riga_contesto,
--     chiamata dal guard del legame): il padre deve essere composito
--     (E_ARTICOLO_NON_COMPOSITO). Un solo componente, che composito non e', e'
--     quindi rifiutato come padre.
-- Il componente «solo componente» e' invece il caso normale.
-- Brief: brief-db-revisione-catalogo, giro 1 (Q2, Q5). Fino al 2026-11-09 la regola
--   la diceva catalogo.trgfn_articoli_componenti_guard_solo_componente, ritirato.
--
-- Elenco test (plan 5):
--  1) il CHECK esiste
--  2) un kit non diventa solo componente: CHECK (23514)
--  3) un solo componente come padre: E_ARTICOLO_NON_COMPOSITO
--  4) kit con un componente semplice: ammesso
--  5) kit con un componente solo componente: ammesso
-- ------------------------------------------------------------

BEGIN;

-- Vincoli differiti a fine istruzione: senza, al ROLLBACK non scatterebbero mai.
SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

CREATE TEMP TABLE _t_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-SOLOC-KIT', p_is_composito => true)          AS kit,
       dbops.fn_pgtap_crea_articolo('PGT-SOLOC-SEMPLICE')                             AS semplice,
       dbops.fn_pgtap_crea_articolo('PGT-SOLOC-SOLO', p_is_solo_componente => true)   AS solo;

SELECT ok(
    EXISTS (SELECT 1 FROM pg_constraint
             WHERE conrelid = 'catalogo.articoli'::regclass
               AND conname  = 'chk_articoli_composito_non_solo_componente'
               AND contype  = 'c'),
    '1) catalogo.articoli ha il CHECK composito / solo componente');

SELECT throws_ok(
    $$ UPDATE catalogo.articoli SET is_solo_componente = true
        WHERE id = (SELECT kit FROM _t_art) $$,
    '23514', NULL,
    '2) un kit non diventa solo componente: lo rifiuta il CHECK');

SELECT throws_like(
    $$ INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, obbligatorio, valido_dal, attivo)
       VALUES ((SELECT solo FROM _t_art), (SELECT semplice FROM _t_art), 1, true, script.fn_data_operativa(), true) $$,
    '%indicato non _ composito%',
    '3) un solo componente come padre: E_ARTICOLO_NON_COMPOSITO (non ha una distinta)');

SELECT lives_ok(
    $$ INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, obbligatorio, valido_dal, attivo)
       VALUES ((SELECT kit FROM _t_art), (SELECT semplice FROM _t_art), 1, true, script.fn_data_operativa(), true) $$,
    '4) kit con un componente semplice: ammesso');

SELECT lives_ok(
    $$ INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, obbligatorio, valido_dal, attivo)
       VALUES ((SELECT kit FROM _t_art), (SELECT solo FROM _t_art), 1, true, script.fn_data_operativa(), true) $$,
    '5) kit con un componente solo componente: ammesso, e'' il caso normale');

SELECT * FROM finish();
ROLLBACK;
