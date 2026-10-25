-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il magazzino sulla TESTATA della bolla (D-L3-a) e le regole dei
--   prelievi che non dipendono dal registro: il predefinito come default
--   (D-L3-h), l'immutabilita' fuori bozza, la coerenza del prelievo con la
--   regola del kit (D-L3-f), e le due colonne testuali ritirate (D-L3-k).
--   Brief: brief-db-magazzino-lotto-3-scarico-da-ddt, sezione 3.
--
-- Elenco test (plan 9):
--   1) due magazzini predefiniti per lo stesso emittente -> 23505
--   2) una bolla nata senza magazzino prende il predefinito del suo emittente
--   3) una bolla nata CON un magazzino tiene il suo
--   4) in bozza il magazzino si cambia
--   5) fuori bozza no -> E_DDT_MAGAZZINO_IMMUTABILE
--   6) prelievo su una riga il cui articolo non e' gestito -> E_DDT_PRELIEVO_INCOERENTE
--   7) prelievo con seriale e quantita' diversa da 1 -> 23514
--   8) vendite.ddt_righe non ha piu' la colonna lotto
--   9) vendite.ddt_righe non ha piu' la colonna seriale
--
-- rev 2026-10-25 (brief-modello-documento-vendita §7, giro 5): l'emissione
--   della bolla «senza» passa da dbops.fn_pgtap_porta_a_stato (il verbo): lo
--   stato della bolla non si cambia piu' con un UPDATE diretto, per nessuna
--   bolla (E_DOC_STATO_SOLO_DAL_VERBO).
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- Un'azienda NUOVA, non quella dell'operatore di sviluppo: su dbdev quella ha
-- gia' dei magazzini (e forse un predefinito), che falserebbero default e giacenze.
CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
-- Con il contesto aperto, il mondo cliente riusa l'azienda di chi agisce.
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('L3TE');

CREATE TEMP TABLE _fix (mag_p bigint, mag_x bigint, art_g uuid, art_n uuid);
DO $fix$
DECLARE v_p bigint; v_x bigint;
BEGIN
    v_p := dbops.fn_pgtap_crea_magazzino('PGT-L3E-PRED', false);
    v_x := dbops.fn_pgtap_crea_magazzino('PGT-L3E-ALTRO', false);
    -- Il predefinito si sceglie con un UPDATE: la fixture nasce non predefinita.
    UPDATE magazzino.magazzini SET predefinito = true WHERE id = v_p;
    INSERT INTO _fix VALUES (v_p, v_x,
                             dbops.fn_pgtap_crea_articolo('PGT-L3E-GEST', true, false, false),
                             dbops.fn_pgtap_crea_articolo('PGT-L3E-NONG', false, false, false));
END $fix$;

-- 1) un solo predefinito per emittente
SELECT throws_ok(
    format('UPDATE magazzino.magazzini SET predefinito = true WHERE id = %s', (SELECT mag_x FROM _fix)),
    '23505', NULL,
    '1) il secondo magazzino predefinito dello stesso emittente e'' rifiutato (D-L3-h)');

-- 2-3) il default
CREATE TEMP TABLE _d (senza bigint, con bigint);
DO $d$ BEGIN
    INSERT INTO _d VALUES (
        dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m), 'VENDITA', NULL),
        dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m), 'VENDITA',
                                (SELECT mag_x FROM _fix)));
END $d$;
SELECT is(
    (SELECT d.magazzino_id FROM vendite.ddt d WHERE d.id = (SELECT senza FROM _d)),
    (SELECT mag_p FROM _fix),
    '2) nata senza magazzino: prende il predefinito del suo emittente');
SELECT is(
    (SELECT d.magazzino_id FROM vendite.ddt d WHERE d.id = (SELECT con FROM _d)),
    (SELECT mag_x FROM _fix),
    '3) nata con un magazzino: tiene il suo (il default non sovrascrive)');

-- 4-5) immutabile fuori bozza. La bolla «senza» si emette con una riga di un
--      articolo NON gestito, col verbo (lo stato si cambia solo da li').
SELECT lives_ok(
    format('UPDATE vendite.ddt SET magazzino_id = %s WHERE id = %s', (SELECT mag_x FROM _fix), (SELECT senza FROM _d)),
    '4) in bozza il magazzino si cambia');
DO $e$
DECLARE v_iva integer;
BEGIN
    SELECT i.id INTO v_iva FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1;
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT (SELECT senza FROM _d), 1, art_n, 'non gestito', 1, 1, 10, v_iva FROM _fix;
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ddt', (SELECT senza FROM _d), 'EMESSO');
END $e$;
SELECT throws_like(
    format('UPDATE vendite.ddt SET magazzino_id = %s WHERE id = %s', (SELECT mag_p FROM _fix), (SELECT senza FROM _d)),
    '%si sceglie solo in bozza%',
    '5) fuori bozza il magazzino non si cambia: E_DDT_MAGAZZINO_IMMUTABILE');

-- 6-7) i prelievi della bolla «con», ancora in bozza
CREATE TEMP TABLE _r (r_n bigint, r_g bigint);
DO $r$
DECLARE v_iva integer; v_rn bigint; v_rg bigint;
BEGIN
    SELECT i.id INTO v_iva FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1;
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT (SELECT con FROM _d), 1, art_n, 'non gestito', 1, 1, 10, v_iva FROM _fix RETURNING id INTO v_rn;
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT (SELECT con FROM _d), 2, art_g, 'gestito', 3, 3, 10, v_iva FROM _fix RETURNING id INTO v_rg;
    INSERT INTO _r VALUES (v_rn, v_rg);
END $r$;
SELECT throws_like(
    format('INSERT INTO vendite.ddt_righe_prelievi (ddt_riga_id, qta) VALUES (%s, 1)', (SELECT r_n FROM _r)),
    '%non e'' gestito a magazzino%',
    '6) un prelievo su una riga non gestita: E_DDT_PRELIEVO_INCOERENTE (non muove merce, D-L3-f)');

-- Un seriale del magazzino «con», per il CHECK |qta| = 1.
CREATE TEMP TABLE _as (id bigint);
DO $a$
DECLARE v_id bigint;
BEGIN
    INSERT INTO magazzino.assets (articolo_id, seriale, stato_id, ownership_id, emittente_fiscale_id)
    SELECT art_g, 'PGT-L3E-SER-1',
           (SELECT s.id FROM config.stati_assets s WHERE s.attivo ORDER BY s.id LIMIT 1),
           (SELECT o.id FROM config.assets_ownership o WHERE o.attivo ORDER BY o.id LIMIT 1),
           (SELECT emittente_fiscale_id FROM _m)
      FROM _fix RETURNING id INTO v_id;
    INSERT INTO _as VALUES (v_id);
END $a$;
SELECT throws_ok(
    format('INSERT INTO vendite.ddt_righe_prelievi (ddt_riga_id, qta, asset_id) VALUES (%s, 2, %s)',
           (SELECT r_g FROM _r), (SELECT id FROM _as)),
    '23514', NULL,
    '7) un seriale e'' un pezzo: prelievo con asset e quantita'' 2 rifiutato dal CHECK');

-- 8-9) le colonne testuali ritirate (D-L3-k)
SELECT hasnt_column('vendite', 'ddt_righe', 'lotto',   '8) ddt_righe.lotto non esiste piu'': il lotto sta sul prelievo');
SELECT hasnt_column('vendite', 'ddt_righe', 'seriale', '9) ddt_righe.seriale non esiste piu'': il seriale sta sul prelievo');

SELECT * FROM finish();
ROLLBACK;
