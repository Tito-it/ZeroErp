-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- La distinta e' una storia, e ogni composizione nuova si giudica.
--   - catalogo.trgfn_articoli_componenti_block_modifica_struttura: il padre di un
--     legame non cambia (prodotto_id e' un campo di struttura), e la fine di un
--     legame non cambia i giorni gia' passati: una fine gia' passata non si tocca
--     (E_BOM_LEGAME_CHIUSO), le altre vanno a vuoto o da ieri in avanti
--     (E_BOM_CHIUSURA_RETROATTIVA);
--   - catalogo.trgfn_articoli_componenti_guard_componente: la riattivazione e
--     l'allungamento della fine sono composizioni nuove, e passano dalla check
--     (padre composito, componente non ritirato);
--   - catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva, check 1: un padre
--     con una distinta solo futura resta composito;
--   - catalogo.vw_articoli_componenti_dettaglio: la prima fine proposta e' ieri.
-- Brief: brief-db-revisione-catalogo, giro 1 (D1, D9, D10, Q1, Q5).
--
-- Elenco test (plan 15):
--  1)  i due guard del padre ritirati non ci sono piu', ne' il predicato vecchio
--  2)  UPDATE prodotto_id -> E_BOM_MODIFICA_VIETATA
--  3)  legame finito: fine spostata in avanti -> E_BOM_LEGAME_CHIUSO
--  4)  legame finito: fine tolta (riapertura) -> E_BOM_LEGAME_CHIUSO
--  5)  legame in vigore: fine prima di ieri -> E_BOM_CHIUSURA_RETROATTIVA
--  6)  legame in vigore: fine prima di valido_dal -> parla la regola del periodo
--  7)  legame in vigore: fine a ieri -> ammessa (la storia non cambia)
--  8)  legame con fine futura: fine tolta -> ammessa
--  9)  componente ritirato, fine futura allungata -> E_ARTICOLO_OBSOLETO
--  10) componente ritirato, fine anticipata (chiusura) -> ammessa: si chiude sempre
--  11) legame spento, padre non piu' composito: riattivazione -> E_ARTICOLO_NON_COMPOSITO
--  12) nuovo legame su un padre non composito -> E_ARTICOLO_NON_COMPOSITO
--  13) padre con distinta solo futura: is_composito non si spegne
--  14) la vista propone come prima fine ieri (legame nato nel passato)
--  15) la vista propone come prima fine valido_dal (legame che nasce domani)
--
-- Fixture costruita (ROLLBACK finale): tutti gli articoli dal builder, i legami
-- con date relative al giorno aziendale.
-- ------------------------------------------------------------

BEGIN;

-- Vincoli differiti a fine istruzione: senza, al ROLLBACK non scatterebbero mai.
SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(15);

CREATE TEMP TABLE _t_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-DSR-KIT',      p_is_composito => true) AS kit,
       dbops.fn_pgtap_crea_articolo('PGT-DSR-KIT2',     p_is_composito => true) AS kit2,
       dbops.fn_pgtap_crea_articolo('PGT-DSR-KIT-FUT',  p_is_composito => true) AS kit_fut,
       dbops.fn_pgtap_crea_articolo('PGT-DSR-KIT-SPENTO', p_is_composito => true) AS kit_spento,
       dbops.fn_pgtap_crea_articolo('PGT-DSR-SEMPLICE')                         AS semplice,
       dbops.fn_pgtap_crea_articolo('PGT-DSR-C1')                               AS c1,
       dbops.fn_pgtap_crea_articolo('PGT-DSR-C2')                               AS c2,
       dbops.fn_pgtap_crea_articolo('PGT-DSR-C3')                               AS c3,
       dbops.fn_pgtap_crea_articolo('PGT-DSR-RITIRATO')                         AS ritirato;

-- Un legame: (padre, componente, inizio, fine, attivo)
CREATE FUNCTION pg_temp.legame(p_padre uuid, p_comp uuid, p_dal date, p_al date, p_attivo boolean DEFAULT true)
 RETURNS uuid
 LANGUAGE sql
AS $f$
    INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, obbligatorio, valido_dal, valido_al, attivo)
    VALUES (p_padre, p_comp, 1, true, p_dal, p_al, p_attivo)
    RETURNING id;
$f$;

CREATE TEMP TABLE _t_leg AS
SELECT pg_temp.legame(a.kit,  a.c1, script.fn_data_operativa() - 20, script.fn_data_operativa() - 5)  AS finito,
       pg_temp.legame(a.kit,  a.c2, script.fn_data_operativa() - 20, NULL)                            AS aperto,
       pg_temp.legame(a.kit,  a.c3, script.fn_data_operativa() - 20, script.fn_data_operativa() + 10) AS fine_futura,
       pg_temp.legame(a.kit2, a.ritirato, script.fn_data_operativa() - 20, script.fn_data_operativa() + 10) AS col_ritirato,
       pg_temp.legame(a.kit_spento, a.semplice, script.fn_data_operativa() - 20, NULL, false)         AS spento,
       pg_temp.legame(a.kit_fut, a.semplice, script.fn_data_operativa() + 1, NULL)                     AS futuro
  FROM _t_art a;

-- ============================================================
-- La struttura (1-2)
-- ============================================================
SELECT ok(
    NOT EXISTS (SELECT 1 FROM pg_trigger
                 WHERE tgrelid = 'catalogo.articoli_componenti'::regclass
                   AND tgfoid IN (SELECT p.oid FROM pg_proc p
                                    JOIN pg_namespace n ON n.oid = p.pronamespace
                                   WHERE n.nspname = 'catalogo'
                                     AND p.proname IN ('trgfn_articoli_componenti_guard_is_composito',
                                                       'trgfn_articoli_componenti_guard_solo_componente')))
    AND to_regprocedure('catalogo.trgfn_articoli_componenti_guard_is_composito()') IS NULL
    AND to_regprocedure('catalogo.trgfn_articoli_componenti_guard_solo_componente()') IS NULL
    AND to_regprocedure('catalogo.fn_articolo_padre_di_distinta_in_vigore(uuid)') IS NULL,
    '1) i due guard del padre e il predicato «in vigore» del padre sono ritirati');

SELECT throws_like(
    $$ UPDATE catalogo.articoli_componenti SET prodotto_id = (SELECT kit2 FROM _t_art)
        WHERE id = (SELECT aperto FROM _t_leg) $$,
    '%Struttura BoM immutabile%',
    '2) il padre di un legame non cambia: E_BOM_MODIFICA_VIETATA');

-- ============================================================
-- La fine non cambia i giorni gia' passati (3-8)
-- ============================================================
SELECT throws_like(
    $$ UPDATE catalogo.articoli_componenti SET valido_al = script.fn_data_operativa() + 30
        WHERE id = (SELECT finito FROM _t_leg) $$,
    '%legame _ finito il%',
    '3) legame gia'' finito: la fine non si sposta in avanti (E_BOM_LEGAME_CHIUSO)');

SELECT throws_like(
    $$ UPDATE catalogo.articoli_componenti SET valido_al = NULL
        WHERE id = (SELECT finito FROM _t_leg) $$,
    '%legame _ finito il%',
    '4) legame gia'' finito: non si riapre (E_BOM_LEGAME_CHIUSO)');

SELECT throws_like(
    $$ UPDATE catalogo.articoli_componenti SET valido_al = script.fn_data_operativa() - 3
        WHERE id = (SELECT aperto FROM _t_leg) $$,
    '%non può cambiare i giorni già passati%',
    '5) legame in vigore: una fine prima di ieri e'' rifiutata (E_BOM_CHIUSURA_RETROATTIVA)');

SELECT throws_like(
    $$ UPDATE catalogo.articoli_componenti SET valido_al = script.fn_data_operativa() - 60
        WHERE id = (SELECT aperto FROM _t_leg) $$,
    '%è inferiore alla data dal%',
    '6) una fine prima di valido_dal la giudica la regola del periodo (E_DATA_AL_MINORE_DAL)');

SELECT lives_ok(
    $$ UPDATE catalogo.articoli_componenti SET valido_al = script.fn_data_operativa() - 1
        WHERE id = (SELECT aperto FROM _t_leg) $$,
    '7) legame in vigore: chiuderlo a ieri e'' ammesso, la storia non cambia');

SELECT lives_ok(
    $$ UPDATE catalogo.articoli_componenti SET valido_al = NULL
        WHERE id = (SELECT fine_futura FROM _t_leg) $$,
    '8) legame con una fine futura: togliere la fine e'' ammesso, il passato non cambia');

-- ============================================================
-- Le composizioni nuove si giudicano (9-12)
-- ============================================================
UPDATE catalogo.articoli SET obsoleto_dal = script.fn_data_operativa()
 WHERE id = (SELECT ritirato FROM _t_art);

SELECT throws_like(
    $$ UPDATE catalogo.articoli_componenti SET valido_al = NULL
        WHERE id = (SELECT col_ritirato FROM _t_leg) $$,
    '%ritirat%',
    '9) componente ritirato: allungare la fine e'' una composizione nuova, rifiutata (E_ARTICOLO_OBSOLETO)');

SELECT lives_ok(
    $$ UPDATE catalogo.articoli_componenti SET valido_al = script.fn_data_operativa() + 1
        WHERE id = (SELECT col_ritirato FROM _t_leg) $$,
    '10) componente ritirato: anticipare la fine e'' ammesso, un legame si chiude sempre');

UPDATE catalogo.articoli SET is_composito = false
 WHERE id = (SELECT kit_spento FROM _t_art);

SELECT throws_like(
    $$ UPDATE catalogo.articoli_componenti SET attivo = true
        WHERE id = (SELECT spento FROM _t_leg) $$,
    '%indicato non _ composito%',
    '11) riattivare un legame il cui padre non e'' piu'' composito: E_ARTICOLO_NON_COMPOSITO');

SELECT throws_like(
    $$ SELECT pg_temp.legame((SELECT kit_spento FROM _t_art), (SELECT c1 FROM _t_art),
                             script.fn_data_operativa(), NULL) $$,
    '%indicato non _ composito%',
    '12) un legame nuovo su un padre non composito: E_ARTICOLO_NON_COMPOSITO');

-- ============================================================
-- Il padre con una distinta solo futura (13)
-- ============================================================
SELECT throws_like(
    $$ UPDATE catalogo.articoli SET is_composito = false
        WHERE id = (SELECT kit_fut FROM _t_art) $$,
    '%Struttura BoM immutabile%',
    '13) un padre con una distinta solo futura resta composito (check 1, da oggi in poi)');

-- ============================================================
-- La capability della vista (14-15)
-- ============================================================
SELECT is(
    (SELECT data_min_chiusura FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT fine_futura FROM _t_leg)),
    script.fn_data_operativa() - 1,
    '14) legame nato nel passato: la prima fine proposta e'' ieri');

SELECT is(
    (SELECT data_min_chiusura FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT futuro FROM _t_leg)),
    script.fn_data_operativa() + 1,
    '15) legame che nasce domani: la prima fine proposta e'' il suo inizio');

SELECT * FROM finish();
ROLLBACK;
