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
-- Test: i controlli della primitiva magazzino.fn_scrivi_movimento, uno per
--   test, ciascuno col caso COSTRUITO (brief-db-magazzino-lotto-2-motore,
--   sezione 4.2 e sezione 7). La disponibilita' (passo 11), i seriali (9-bis)
--   e il valore (12-14) hanno il loro file.
--
-- ⚠️ Fixture COSTRUITA: azienda e operatore dall'helper, due magazzini (uno a
--   ubicazioni, D-L2-m), TRE articoli con i flag scelti dal test (gestito;
--   per lotti; per seriale), un lotto, un asset, e un inventario DRAFT con
--   righe come sorgenti (INVENTARIO_RIGA:{riga}). Una SECONDA azienda per
--   l'asset di altro emittente (contesto cambiato per costruirlo, e rimesso).
-- ⚠️ Fino al 2026-09-24 girava come l'applicazione; da P-4 gira come owner
--   (marcatore in testa). Il guard di scope legge comunque le GUC dell'operatore;
--   le letture del test NON sono piu' filtrate dalla RLS — provato il 24-09 che
--   le 25 asserzioni non ne dipendono (fixture costruita, id propri).
--
-- Elenco test (plan 25 — il 5 e il 16 sono in due asserzioni):
--    1) parametro: qta = 0 -> E_MAG_CHIAMATA_NON_VALIDA (la frase nomina la funzione)
--    2) causale sconosciuta -> E_CONFIG_MANCANTE con il codice nella frase
--    3) verso incoerente -> la frase della MADRE (E_MAG_MOVIMENTO_VERSO_INCOERENTE)
--    4) magazzino inesistente -> E_MAG_MAGAZZINO_NON_VALIDO
--    5) articolo non gestito -> E_MAG_ARTICOLO_NON_GESTITO, e la check porta campo = articolo_id
--    6) lotto obbligatorio    7) lotto non ammesso    8) lotto di altro articolo
--    9) seriale obbligatorio 10) seriale non ammesso 11) asset di altro articolo
--   12) asset di altro emittente
--   13) ubicazione obbligatoria (magazzino a ubicazioni)
--   14) ubicazione non ammessa (magazzino senza)  15) ubicazione di altro magazzino
--   16) usa_ubicazioni NON si cambia su un magazzino con un movimento (E_MAG_MAGAZZINO_CON_GIACENZA)
--   17) ...e si cambia su uno vuoto
--   18) identita' gia' registrata: la frase nomina l'id esistente
--   19) costo passato su un'uscita -> E_MAG_COSTO_NON_AMMESSO
--   20) entrata gemella senza OUT -> E_MAG_GEMELLA_NON_TROVATA
--   21) storno incoerente (quantita' non opposta) -> E_MAG_STORNO_INCOERENTE
--   22) il caso buono ritorna un id
--   23) ...e la riga e' come attesa (qta firmata, costo, sorgente, causale)
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(25);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
CREATE TEMP TABLE _mondo_b AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore('L2B');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;

CREATE TEMP TABLE _fix (
    mag bigint, mag_ubi bigint, mag_b bigint,
    art uuid, art_lotto uuid, art_serial uuid, art_no uuid,
    lotto bigint, lotto_altro bigint, asset bigint, asset_altro_art bigint, asset_b bigint,
    ubi bigint, ubi_b bigint,
    inv bigint, r1 bigint, r2 bigint, r3 bigint, r4 bigint, r5 bigint, r6 bigint,
    src bigint
);

DO $fix$
DECLARE
    v_mag bigint; v_mag_ubi bigint; v_mag_b bigint;
    v_art uuid; v_art_lotto uuid; v_art_serial uuid; v_art_no uuid;
    v_lotto bigint; v_lotto_altro bigint; v_asset bigint; v_asset_altro bigint; v_asset_b bigint;
    v_ubi bigint; v_ubi_b bigint; v_inv bigint;
    v_r bigint[] := '{}';
    v_tmp bigint; i int;
BEGIN
    v_mag     := dbops.fn_pgtap_crea_magazzino('PGT-L2C-A', false);
    v_mag_ubi := dbops.fn_pgtap_crea_magazzino('PGT-L2C-U', true);
    v_art        := dbops.fn_pgtap_crea_articolo('PGT-L2C-ART', true, false, false);
    v_art_lotto  := dbops.fn_pgtap_crea_articolo('PGT-L2C-LOT', true, true,  false);
    v_art_serial := dbops.fn_pgtap_crea_articolo('PGT-L2C-SER', true, false, true);
    v_art_no     := dbops.fn_pgtap_crea_articolo('PGT-L2C-NO',  false, false, false);
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo) VALUES (v_art_lotto, 'PGT-L2C-L1', script.fn_data_operativa()) RETURNING id INTO v_lotto;
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo) VALUES (v_art, 'PGT-L2C-L2', script.fn_data_operativa()) RETURNING id INTO v_lotto_altro;
    INSERT INTO magazzino.assets (articolo_id, seriale, stato_id, ownership_id, emittente_fiscale_id)
    VALUES (v_art_serial, 'PGT-L2C-SN1',
            (SELECT s.id FROM config.stati_assets s WHERE s.attivo ORDER BY s.id LIMIT 1),
            (SELECT o.id FROM config.assets_ownership o WHERE o.attivo ORDER BY o.id LIMIT 1),
            (SELECT emittente_fiscale_id FROM _mondo)) RETURNING id INTO v_asset;
    INSERT INTO magazzino.assets (articolo_id, seriale, stato_id, ownership_id, emittente_fiscale_id)
    VALUES (v_art, 'PGT-L2C-SN2',
            (SELECT s.id FROM config.stati_assets s WHERE s.attivo ORDER BY s.id LIMIT 1),
            (SELECT o.id FROM config.assets_ownership o WHERE o.attivo ORDER BY o.id LIMIT 1),
            (SELECT emittente_fiscale_id FROM _mondo)) RETURNING id INTO v_asset_altro;
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id)
    VALUES (v_mag_ubi, 'PGT-L2C-U1', (SELECT t.id FROM config.tipi_ubicazione t ORDER BY t.id LIMIT 1)) RETURNING id INTO v_ubi;

    -- La seconda azienda: il suo magazzino e il suo asset, nel SUO contesto.
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo_b));
    v_mag_b := dbops.fn_pgtap_crea_magazzino('PGT-L2C-B', false);
    INSERT INTO magazzino.assets (articolo_id, seriale, stato_id, ownership_id, emittente_fiscale_id)
    VALUES (v_art_serial, 'PGT-L2C-SNB',
            (SELECT s.id FROM config.stati_assets s WHERE s.attivo ORDER BY s.id LIMIT 1),
            (SELECT o.id FROM config.assets_ownership o WHERE o.attivo ORDER BY o.id LIMIT 1),
            (SELECT emittente_fiscale_id FROM _mondo_b)) RETURNING id INTO v_asset_b;
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id)
    VALUES (v_mag_b, 'PGT-L2C-UB', (SELECT t.id FROM config.tipi_ubicazione t ORDER BY t.id LIMIT 1)) RETURNING id INTO v_ubi_b;
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo));

    -- Le sorgenti: sei inventari DRAFT con una riga ciascuno (una per test che
    -- scrive). ⚠️ Sei righe dello STESSO inventario sulla stessa posizione
    -- violerebbero uq_mag_inventari_righe_posizione (C14): un conteggio a posizione.
    FOR i IN 1..6 LOOP
        INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
        INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata)
        VALUES (v_inv, v_art, i) RETURNING id INTO v_tmp;
        v_r := v_r || v_tmp;
    END LOOP;

    INSERT INTO _fix VALUES (v_mag, v_mag_ubi, v_mag_b, v_art, v_art_lotto, v_art_serial, v_art_no,
                             v_lotto, v_lotto_altro, v_asset, v_asset_altro, v_asset_b, v_ubi, v_ubi_b,
                             v_inv, v_r[1], v_r[2], v_r[3], v_r[4], v_r[5], v_r[6],
                             (SELECT id FROM config.sorgenti WHERE codice_interno = 'INVENTARIO'));
END $fix$;

-- ============================================================
-- 1-4 Parametri, causale, verso, magazzino
-- ============================================================
SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'INV_INIZIALE', 0, src, r1, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r1)) FROM _fix $$,
    '%Chiamata non valida a magazzino.fn_scrivi_movimento%',
    '1) qta = 0: E_MAG_CHIAMATA_NON_VALIDA, la frase nomina la funzione');

SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'BOH', 1, src, r1, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r1)) FROM _fix $$,
    '%Configurazione mancante: causale di magazzino BOH%',
    '2) causale sconosciuta: E_CONFIG_MANCANTE col codice nella frase');

SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'SCARICO_VEN', 1, src, r1, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r1)) FROM _fix $$,
    '%Verso incoerente: la causale SCARICO_VEN ha segno -1, ma la quantità vale 1.%',
    '3) verso incoerente: la frase della madre, non del trigger');

SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(999999999, art, 'INV_INIZIALE', 1, src, r1, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r1)) FROM _fix $$,
    '%Magazzino 999999999 inesistente o non attivo.%',
    '4) magazzino inesistente: E_MAG_MAGAZZINO_NON_VALIDO');

-- ============================================================
-- 5-15 La riga (fn_check_riga_magazzino, letta dalla primitiva)
-- ============================================================
SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art_no, 'INV_INIZIALE', 1, src, r1, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r1)) FROM _fix $$,
    '%non è gestito a magazzino%',
    '5a) articolo non gestito: E_MAG_ARTICOLO_NON_GESTITO');
SELECT is(
    (SELECT script.fn_check_riga_magazzino(mag, art_no) -> 0 -> 'dettaglio' ->> 'campo' FROM _fix),
    'articolo_id',
    '5b) ...e la check porta campo = articolo_id nel dettaglio');

SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art_lotto, 'INV_INIZIALE', 1, src, r1, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r1)) FROM _fix $$,
    '%si movimenta per lotti: indica il lotto.%',
    '6) requires_lotto senza lotto: E_MAG_LOTTO_OBBLIGATORIO');
SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'INV_INIZIALE', 1, src, r1, NULL, NULL, lotto_altro, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r1)) FROM _fix $$,
    '%non si movimenta per lotti: il lotto PGT-L2C-L2 non va indicato.%',
    '7) articolo senza lotti con un lotto: E_MAG_LOTTO_NON_AMMESSO');
SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art_lotto, 'INV_INIZIALE', 1, src, r1, NULL, NULL, lotto_altro, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r1)) FROM _fix $$,
    '%Il lotto PGT-L2C-L2 non è dell''articolo PGT-L2C-LOT%',
    '8) lotto di un altro articolo: E_MAG_LOTTO_DI_ALTRO_ARTICOLO');

SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art_serial, 'INV_INIZIALE', 1, src, r1, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r1)) FROM _fix $$,
    '%si movimenta per seriale: indica il seriale.%',
    '9) requires_serial senza asset: E_MAG_SERIALE_OBBLIGATORIO');
SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'INV_INIZIALE', 1, src, r1, NULL, NULL, NULL, asset_altro_art, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r1)) FROM _fix $$,
    '%non si movimenta per seriale: il seriale PGT-L2C-SN2 non va indicato.%',
    '10) articolo senza seriale con un asset: E_MAG_SERIALE_NON_AMMESSO');
SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art_serial, 'INV_INIZIALE', 1, src, r1, NULL, NULL, NULL, asset_altro_art, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r1)) FROM _fix $$,
    '%Il seriale PGT-L2C-SN2 non è dell''articolo PGT-L2C-SER%',
    '11) asset di un altro articolo: E_MAG_ASSET_DI_ALTRO_ARTICOLO');
SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art_serial, 'INV_INIZIALE', 1, src, r1, NULL, NULL, NULL, asset_b, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r1)) FROM _fix $$,
    '%non appartiene all''emittente del magazzino PGT-L2C-A.%',
    '12) asset di un altro emittente: E_MAG_ASSET_DI_ALTRO_EMITTENTE (la DEFINER lo vede, la regola lo ferma)');

SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag_ubi, art, 'INV_INIZIALE', 1, src, r1, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r1)) FROM _fix $$,
    '%Il magazzino PGT-L2C-U usa le ubicazioni: indica in quale ubicazione.%',
    '13) magazzino a ubicazioni senza ubicazione: E_MAG_UBICAZIONE_OBBLIGATORIA (D-L2-m)');
SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'INV_INIZIALE', 1, src, r1, NULL, NULL, NULL, NULL, ubi, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r1)) FROM _fix $$,
    '%Il magazzino PGT-L2C-A non usa le ubicazioni: l''ubicazione PGT-L2C-U1 non va indicata.%',
    '14) magazzino senza ubicazioni con un''ubicazione: E_MAG_UBICAZIONE_NON_AMMESSA (D-L2-m)');
SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag_ubi, art, 'INV_INIZIALE', 1, src, r1, NULL, NULL, NULL, NULL, ubi_b, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r1)) FROM _fix $$,
    '%non è del magazzino PGT-L2C-U%',
    '15) ubicazione di un altro magazzino: E_MAG_UBICAZIONE_DI_ALTRO_MAGAZZINO');

-- ============================================================
-- 16-17 usa_ubicazioni si cambia solo a registro vuoto (D-L2-m)
-- ============================================================
-- Un movimento buono nel magazzino A (lo stesso del 22, riga r6: qui r5).
SELECT lives_ok(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'INV_INIZIALE', 5, src, r5, NULL, 10, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r5)) FROM _fix $$,
    '16a) un movimento nel magazzino A (per il 16b)');
SELECT throws_like(
    $$ UPDATE magazzino.magazzini SET usa_ubicazioni = true WHERE id = (SELECT mag FROM _fix) $$,
    '%ha già movimenti a registro: le ubicazioni si decidono prima del primo carico.%',
    '16b) usa_ubicazioni su un magazzino con un movimento: E_MAG_MAGAZZINO_CON_GIACENZA');
SELECT lives_ok(
    $$ UPDATE magazzino.magazzini SET usa_ubicazioni = false WHERE id = (SELECT mag_ubi FROM _fix) $$,
    '17) ...e su un magazzino vuoto il flag si cambia');

-- ============================================================
-- 18-21 Identita', costo, gemella, storno
-- ============================================================
SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'INV_INIZIALE', 5, src, r5, NULL, 10, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r5)) FROM _fix $$,
    '%Questa operazione ha già registrato il movimento ' ||
        (SELECT m.id::text FROM magazzino.movimenti m JOIN _fix f ON m.sorgente_riga = f.r5) || '.%',
    '18) stessa identita'': E_MAG_MOVIMENTO_GIA_REGISTRATO, la frase nomina l''id esistente');

SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'RETT_NEG', -1, src, r2, NULL, 9, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r2)) FROM _fix $$,
    '%Costo unitario non ammesso su questo movimento (uscita)%',
    '19) costo passato su un''uscita: E_MAG_COSTO_NON_AMMESSO');

SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'TRASF_IN', 1, src, r3, NULL, NULL, NULL, NULL, NULL, now(), '11111111-1111-1111-1111-111111111111', p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r3)) FROM _fix $$,
    '%Nessuna uscita con transfer_uid 11111111-1111-1111-1111-111111111111%',
    '20) entrata gemella senza la OUT: E_MAG_GEMELLA_NON_TROVATA');

SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'STORNO_NEG', -4, src, r5, NULL, NULL, NULL, NULL, NULL, now(), NULL,
              (SELECT m.id FROM magazzino.movimenti m JOIN _fix f ON m.sorgente_riga = f.r5), p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r5)) FROM _fix $$,
    '%Storno incoerente del movimento%',
    '21) storno con quantita'' non opposta: E_MAG_STORNO_INCOERENTE');

-- ============================================================
-- 22-23 Il caso buono
-- ============================================================
SELECT ok(
    (SELECT magazzino.fn_scrivi_movimento(mag, art, 'RETT_POS', 3, src, r6, NULL, 12.5, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r6)) FROM _fix) > 0,
    '22) il caso buono ritorna un id');
SELECT is(
    (SELECT (m.qta, m.costo_unitario, m.causale_id, m.sorgente_tipo_id, m.sorgente_riga, m.lotto_id)::text
       FROM magazzino.movimenti m JOIN _fix f ON m.sorgente_riga = f.r6),
    (SELECT (3::numeric(18,6), 12.5::numeric(18,6), (SELECT id FROM magazzino.causali WHERE codice_interno = 'RETT_POS'),
             src, r6, NULL::bigint)::text FROM _fix),
    '23) ...e la riga e'' come attesa: qta firmata, costo, causale, sorgente, lotto');

SELECT * FROM finish();
ROLLBACK;
