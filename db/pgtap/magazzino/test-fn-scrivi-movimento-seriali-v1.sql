-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- pgtap-runner: owner
-- pgtap-runner-motivo: il soggetto sono i CONTROLLI della primitiva
--   magazzino.fn_scrivi_movimento, che dal 2026-09-24 l'app non esegue piu': la
--   raggiunge solo dai verbi fn_posta_inventario / fn_posta_rettifica
--   (brief-db-magazzino-verbi-con-permesso, P-4). Chiamarla coi parametri che il
--   test sceglie e' cosa che solo uno scrittore privilegiato puo' fare: forma 3
--   del criterio del runner, come i test del ledger del Lotto 2. Il contesto
--   operatore resta impostato: il guard di scope e i controlli lo leggono.
--
-- Test: la posizione di un seriale si DERIVA dal registro e la primitiva la
--   difende (D-L2-e, passo 9-bis di sezione 4.2). Brief:
--   brief-db-magazzino-lotto-2-motore, sezione 7.
--
-- ⚠️ Fixture COSTRUITA: due magazzini dello stesso emittente, un articolo per
--   seriale, un asset dell'emittente, le sorgenti (inventari DRAFT, una riga
--   per scrittura: l'identita' del ledger e' per riga + causale + asset).
--
-- Elenco test (plan 5):
--   1) entrata del seriale in A: passa (non era dentro da nessuna parte)
--   2) seconda entrata dello stesso seriale in B -> E_MAG_ASSET_POSIZIONE_INCOERENTE, «gia' presente nel magazzino A»
--   3) uscita da B, dove non e' -> E_MAG_ASSET_POSIZIONE_INCOERENTE, «assente dal magazzino B»
--   4) uscita da A, poi entrata in B: passa (il pezzo si sposta)
--   5) |qta| <> 1 con un asset -> 23514 chk_mag_movimenti_asset_qta_unitaria (la rete del Lotto 1, oltre la madre)
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;

CREATE TEMP TABLE _fix (mag_a bigint, mag_b bigint, art uuid, asset bigint, src bigint,
                        r1 bigint, r2 bigint, r3 bigint, r4 bigint, r5 bigint, r6 bigint);
DO $fix$
DECLARE
    v_a bigint; v_b bigint; v_art uuid; v_asset bigint; v_inv bigint; v_tmp bigint;
    v_r bigint[] := '{}'; i int;
BEGIN
    v_a := dbops.fn_pgtap_crea_magazzino('PGT-L2S-A', false);
    v_b := dbops.fn_pgtap_crea_magazzino('PGT-L2S-B', false);
    v_art := dbops.fn_pgtap_crea_articolo('PGT-L2S-SER', true, false, true);
    INSERT INTO magazzino.assets (articolo_id, seriale, stato_id, ownership_id, emittente_fiscale_id)
    VALUES (v_art, 'PGT-L2S-SN',
            (SELECT s.id FROM config.stati_assets s WHERE s.attivo ORDER BY s.id LIMIT 1),
            (SELECT o.id FROM config.assets_ownership o WHERE o.attivo ORDER BY o.id LIMIT 1),
            (SELECT emittente_fiscale_id FROM _mondo)) RETURNING id INTO v_asset;
    FOR i IN 1..6 LOOP
        INSERT INTO magazzino.inventari (magazzino_id) VALUES (CASE WHEN i % 2 = 1 THEN v_a ELSE v_b END) RETURNING id INTO v_inv;
        INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, asset_id) VALUES (v_inv, v_art, 1, v_asset) RETURNING id INTO v_tmp;
        v_r := v_r || v_tmp;
    END LOOP;
    INSERT INTO _fix VALUES (v_a, v_b, v_art, v_asset,
                             (SELECT id FROM config.sorgenti WHERE codice_interno = 'INVENTARIO_RIGA'),
                             v_r[1], v_r[2], v_r[3], v_r[4], v_r[5], v_r[6]);
END $fix$;

SELECT lives_ok(
    $$ SELECT magazzino.fn_scrivi_movimento(mag_a, art, 'INV_INIZIALE', 1, src, r1, NULL, 100, NULL, asset) FROM _fix $$,
    '1) entrata del seriale in A: non era dentro da nessuna parte, passa');

SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag_b, art, 'INV_INIZIALE', 1, src, r2, NULL, 100, NULL, asset) FROM _fix $$,
    '%Il seriale PGT-L2S-SN non può fare questo movimento: a registro risulta gia'' presente nel magazzino PGT-L2S-A.%',
    '2) seconda entrata dello stesso seriale altrove: E_MAG_ASSET_POSIZIONE_INCOERENTE');

SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag_b, art, 'RETT_NEG', -1, src, r4, NULL, NULL, NULL, asset) FROM _fix $$,
    '%a registro risulta assente dal magazzino PGT-L2S-B.%',
    '3) uscita da dove non e'': E_MAG_ASSET_POSIZIONE_INCOERENTE');

SELECT lives_ok(
    $$ SELECT magazzino.fn_scrivi_movimento(mag_a, art, 'RETT_NEG', -1, src, r3, NULL, NULL, NULL, asset) FROM _fix;
       SELECT magazzino.fn_scrivi_movimento(mag_b, art, 'RETT_POS', 1, src, r6, NULL, NULL, NULL, asset) FROM _fix $$,
    '4) uscita da A e poi entrata in B: il pezzo si sposta');

SELECT throws_ok(
    $$ SELECT magazzino.fn_scrivi_movimento(mag_b, art, 'RETT_NEG', -2, src, r5, NULL, NULL, NULL, asset) FROM _fix $$,
    'P0001', NULL,
    '5) |qta| = 2 con un asset: rifiutata (la posizione derivata non ammette due pezzi: la madre, prima del CHECK)');

SELECT * FROM finish();
ROLLBACK;
