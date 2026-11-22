-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- pgtap-runner: owner
-- pgtap-runner-motivo: magazzino.eventi_assets e' chiusa all'applicazione e nessun verbo la scrive (Lotto 1, D-M7): il guard della sorgente su un evento lo fa scattare solo uno scrittore privilegiato (forma 3).
--
-- Test: l'evento del seriale nella grammatica della provenienza — il guard
--   unico della sorgente su magazzino.eventi_assets.
--   Brief: brief-db-sorgente-documento-e-riga §7.2 lotto M (i casi erano 9 e 11
--   di magazzino/test-sorgente-testate-v1); brief-db-magazzino-tutte-le-scritture-dal-verbo,
--   D-M7 (Tid 2026-11-22: l'evento si chiude all'app, il test passa a owner).
--
-- ⭐ Il mondo si COSTRUISCE come in test-sorgente-testate-v1: un emittente col suo
--   operatore in sessione, un magazzino, due bolle in bozza con una riga, un
--   seriale dal suo builder. Da owner la RLS non filtra: l'operatore in sessione
--   serve ai builder (i verbi di nascita) e ai guard che lo leggono.
-- ⛔ Quando l'evento avra' il suo verbo (il primo scrittore, brief §8), questi casi
--   tornano come app, attraverso il verbo, e il marcatore si toglie.
--
-- Elenco test (plan 3):
--   1) un evento da una bolla che non c'e' -> E_SORG_NOT_FOUND
--   2) un evento dalla riga di una bolla: passa
--   3) la riga di bolla citata da un evento non si cancella -> E_SORG_ORIGINE_REFERENZIATA
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(3);

CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('PGT-SEVA');

CREATE TEMP TABLE _fix (mag bigint, ddt bigint, r bigint, asset bigint, tev bigint, t_ddt bigint);
DO $fix$
DECLARE
    v_mag magazzino.magazzini.id%TYPE;
    v_art catalogo.articoli.id%TYPE;
    v_ddt vendite.ddt.id%TYPE;
    v_r   vendite.ddt_righe.id%TYPE;
    v_iva config.iva.id%TYPE;
    v_tev config.tipi_evento_assets.id%TYPE;
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-SEVA-A', false);
    v_art := dbops.fn_pgtap_crea_articolo('PGT-SEVA-ART', true, false, false);
    SELECT i.id INTO v_iva FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1;
    SELECT e.id INTO v_tev FROM config.tipi_evento_assets e WHERE e.attivo ORDER BY e.id LIMIT 1;
    IF v_iva IS NULL OR v_tev IS NULL THEN
        RAISE EXCEPTION 'fixture: manca un vocabolario di seed (iva, tipo evento)';
    END IF;

    v_ddt := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                     'VENDITA', v_mag);
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    VALUES (v_ddt, 1, v_art, 'riga 1', 1, 1, 10, v_iva) RETURNING id INTO v_r;

    INSERT INTO _fix VALUES (v_mag, v_ddt, v_r, dbops.fn_pgtap_crea_asset(v_art, 'PGT-SEVA-SN-1'), v_tev,
                             (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'DDT_VENDITA'));
END $fix$;

-- 1
SELECT throws_like(
    format($q$INSERT INTO magazzino.eventi_assets (asset_id, tipo_evento_id, magazzino_id_from, sorgente_tipo_id, sorgente_id)
              VALUES (%s, %s, %s, %s, -1)$q$,
           (SELECT asset FROM _fix), (SELECT tev FROM _fix), (SELECT mag FROM _fix), (SELECT t_ddt FROM _fix)),
    '%Riferimento sorgente non trovato%',
    '1) un evento da una bolla che non c''e'': E_SORG_NOT_FOUND');

-- 2
SELECT lives_ok(
    format($q$INSERT INTO magazzino.eventi_assets (asset_id, tipo_evento_id, magazzino_id_from, sorgente_tipo_id, sorgente_id, sorgente_riga)
              VALUES (%s, %s, %s, %s, %s, %s)$q$,
           (SELECT asset FROM _fix), (SELECT tev FROM _fix), (SELECT mag FROM _fix), (SELECT t_ddt FROM _fix),
           (SELECT ddt FROM _fix), (SELECT r FROM _fix)),
    '2) un evento dalla riga di una bolla: passa');

-- 3
SELECT throws_like(
    format('DELETE FROM vendite.ddt_righe WHERE id = %s', (SELECT r FROM _fix)),
    '%dichiarano di nascere da qui%',
    '3) la riga di bolla citata da un evento non si cancella: E_SORG_ORIGINE_REFERENZIATA');

SELECT * FROM finish();
ROLLBACK;
