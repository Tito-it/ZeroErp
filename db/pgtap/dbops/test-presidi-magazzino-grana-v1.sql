-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- pgtap-runner: owner
-- pgtap-runner-motivo: il soggetto sono quattro presidi che vedono una porta del
--   registro che non ha tenuto (un movimento che manca, uno stato scritto fuori
--   dal verbo, uno stato nuovo nel vocabolario). Quello stato rotto i verbi non
--   lo producono: il test lo FABBRICA fuori dalla porta (DELETE di un movimento,
--   trigger spenti nella transazione, una riga di catalogo), cose che solo il
--   proprietario puo' fare. E' la forma 3 del criterio del runner. Il contesto
--   operatore e' comunque impostato: verbi e fixture lo vogliono.
--
-- Test: i presidi di magazzino alla grana del posting.
--   Brief: brief-db-sorgente-documento-e-riga §7.2 lotto M, «Riverifica fatta»
--   (pgTAP confermati da Tid, 2026-11-08); D58, D29, Q14 ⑧ di brief-db-revisione-dbops;
--   decisione C (il presidio dell'arrivo del trasferimento).
--
-- Il mondo: due magazzini A e B; SEMPLICE (10 a 5), A_LOTTI (lotti A e B, 6+6 a 3),
--   SENZA_COSTO (3 pezzi caricati senza costo, articolo nuovo: nessuna media).
--   Bolla 1 di vendita da A: A_LOTTI 8 (prelievi A 5, B 3), SEMPLICE 2; emessa,
--   spedita, consegnata. Reso 1 sulla bolla 1: A_LOTTI 4 (rientri A 3, B 1),
--   confermato. Bolla 3 di trasferimento A -> B: SEMPLICE 1, emessa, spedita, consegnata.
--   Per ⑧: una rettifica e un trasferimento interno in bozza, con movimenti scritti dalla
--   primitiva a giacenza zero (vedi la nota prima del test 10).
--
-- ⚠️ Il filtro sulle righe attive dei due presidi segue il contratto del posting (un
--   movimento per prelievo delle righe ATTIVE). Un prelievo di una riga spenta il modello
--   non lo ammette (la riga con prelievi non si spegne, il prelievo vuole la riga attiva):
--   non c'e' un caso da costruire, e il test non lo finge.
--
-- Elenco test (plan 15):
--    1) D58 — la bolla 1, tutta scaricata, non e' nel presidio
--    2) D58 — tolta l'uscita del prelievo B (uno su due): la bolla e' nel presidio, 1 prelievo senza scarico
--    3) D58 — il reso 1, tutto caricato, non e' nel presidio dei resi
--    4) D58 — tolto il carico del rientro B (uno su due): il reso e' nel presidio, 1 rientro senza carico
--    5) D29 — il BB: DRAFT no, CONFERMATO si', ANNULLATO no
--    6) D29 — uno stato nuovo dopo la conferma (ordine 25, non abortito): il BB dice si'
--    7) D29 — il reso 1 portato nello stato nuovo resta nel presidio: lo stato viene dal BB
--    8) D29 — ...e vendite.vw_resi_righe_effettive vede le sue righe anche li'
--    9) D29 — nessuna delle tre viste del reso nomina piu' 'CONFERMATO'; tutte leggono il BB
--   10) ⑧ — il carico senza costo di SENZA_COSTO e' nella spia
--   11) ⑧ — un'uscita senza costo (giacenza zero, causale a stock negativo) stornata: lo storno non c'e'
--   12) ⑧ — l'entrata gemella TRASF_IN senza costo nel magazzino B c'e' (diluisce la media li')
--   13) C — la bolla 3 consegnata, con l'arrivo, non e' nel presidio dell'arrivo
--   14) C — tolto l'arrivo: la bolla 3 e' nel presidio, 1 prelievo senza arrivo
--   15) C — la bolla 1 (vendita, non trasferimento) non c'e' mai
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- Il mondo: un'azienda NUOVA (su dbdev quella dell'operatore ha gia' magazzini).
CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('PMGR');
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'emetti_ddt');
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'registra_magazzino');
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'conferma_reso');
END $az$;

CREATE TEMP TABLE _fix (mag_a bigint, mag_b bigint, art_s uuid, art_l uuid, art_z uuid,
                        lotto_a bigint, lotto_b bigint, iva integer);
DO $fix$
DECLARE
    v_a bigint; v_b bigint; v_s uuid; v_l uuid; v_z uuid; v_la bigint; v_lb bigint; v_inv bigint; v_iva integer;
BEGIN
    v_a := dbops.fn_pgtap_crea_magazzino('PGT-PMG-A', false);
    v_b := dbops.fn_pgtap_crea_magazzino('PGT-PMG-B', false);
    v_s := dbops.fn_pgtap_crea_articolo('PGT-PMG-SEMPLICE',    true, false, false);
    v_l := dbops.fn_pgtap_crea_articolo('PGT-PMG-A-LOTTI',     true, true,  false);
    v_z := dbops.fn_pgtap_crea_articolo('PGT-PMG-SENZA-COSTO', true, false, false);
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo) VALUES (v_l, 'PGT-PMG-LA', script.fn_data_operativa() - 10) RETURNING id INTO v_la;
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo) VALUES (v_l, 'PGT-PMG-LB', script.fn_data_operativa() - 5)  RETURNING id INTO v_lb;
    SELECT i.id INTO v_iva FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1;
    INSERT INTO _fix VALUES (v_a, v_b, v_s, v_l, v_z, v_la, v_lb, v_iva);

    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_a) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, costo_unitario) VALUES (v_inv, v_s, 10, 5);
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, lotto_id, qta_contata, costo_unitario) VALUES (v_inv, v_l, v_la, 6, 3);
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, lotto_id, qta_contata, costo_unitario) VALUES (v_inv, v_l, v_lb, 6, 3);
    -- Il carico senza valore: nessun costo sulla riga e nessuna media (articolo nuovo).
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata) VALUES (v_inv, v_z, 3);
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv;
    PERFORM magazzino.fn_posta_inventario(v_inv);
END $fix$;

-- La bolla 1 e il reso 1.
CREATE TEMP TABLE _d1 (ddt bigint, r_l bigint, r_s bigint, p_la bigint, p_lb bigint,
                       reso bigint, rr_l bigint, x_a bigint, x_b bigint);
DO $d$
DECLARE v_ddt bigint; v_rl bigint; v_rs bigint; v_pla bigint; v_plb bigint; v_reso bigint; v_rrl bigint;
        v_xa bigint; v_xb bigint;
BEGIN
    v_ddt := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                     'VENDITA', (SELECT mag_a FROM _fix));
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_ddt, 1, art_l, 'a lotti', 8, 8, 10, iva FROM _fix RETURNING id INTO v_rl;
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_ddt, 2, art_s, 'semplice', 2, 2, 10, iva FROM _fix RETURNING id INTO v_rs;
    INSERT INTO vendite.ddt_righe_prelievi (ddt_riga_id, qta, lotto_id) SELECT v_rl, 5, lotto_a FROM _fix RETURNING id INTO v_pla;
    INSERT INTO vendite.ddt_righe_prelievi (ddt_riga_id, qta, lotto_id) SELECT v_rl, 3, lotto_b FROM _fix RETURNING id INTO v_plb;
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_ddt, 'EMESSO');
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_ddt, 'SPEDITO');
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_ddt, 'CONSEGNATO');

    SELECT b.reso_id, b.resi_riga_id INTO v_reso, v_rrl
      FROM dbops.fn_pgtap_crea_reso('PMGR', v_ddt, 4, p_stato_codice_interno => 'DRAFT', p_ddt_riga_id => v_rl) b;
    INSERT INTO vendite.resi_righe_rientri (resi_riga_id, ddt_riga_prelievo_id, qta) VALUES (v_rrl, v_pla, 3) RETURNING id INTO v_xa;
    INSERT INTO vendite.resi_righe_rientri (resi_riga_id, ddt_riga_prelievo_id, qta) VALUES (v_rrl, v_plb, 1) RETURNING id INTO v_xb;
    PERFORM vendite.fn_conferma_reso(v_reso);
    INSERT INTO _d1 VALUES (v_ddt, v_rl, v_rs, v_pla, v_plb, v_reso, v_rrl, v_xa, v_xb);
END $d$;

-- 1) la bolla 1, tutta scaricata
SELECT ok(
    NOT EXISTS (SELECT 1 FROM dbops.vw_ddt_emessi_senza_scarico v WHERE v.ddt_id = (SELECT ddt FROM _d1)),
    '1) D58: la bolla con tutti i prelievi scaricati non e'' nel presidio');

-- 2) fuori porta: l'uscita del prelievo B se ne va (uno dei due prelievi della stessa riga)
DELETE FROM magazzino.movimenti m
 WHERE m.sorgente_dettaglio = (SELECT p_lb FROM _d1)
   AND m.sorgente_id = (SELECT ddt FROM _d1)
   AND m.qta < 0 AND m.storno_di_movimento_id IS NULL;
SELECT is(
    (SELECT v.prelievi_senza_scarico FROM dbops.vw_ddt_emessi_senza_scarico v WHERE v.ddt_id = (SELECT ddt FROM _d1)),
    1::bigint,
    '2) D58: un prelievo su due senza uscita: la bolla e'' nel presidio, con 1 prelievo senza scarico');

-- 3-4) il reso 1
SELECT ok(
    NOT EXISTS (SELECT 1 FROM dbops.vw_resi_confermati_senza_carico v WHERE v.reso_id = (SELECT reso FROM _d1)),
    '3) D58: il reso con tutti i rientri caricati non e'' nel presidio');
DELETE FROM magazzino.movimenti m
 WHERE m.sorgente_dettaglio = (SELECT x_b FROM _d1)
   AND m.sorgente_id = (SELECT reso FROM _d1)
   AND m.qta > 0 AND m.storno_di_movimento_id IS NULL;
SELECT is(
    (SELECT v.rientri_senza_carico FROM dbops.vw_resi_confermati_senza_carico v WHERE v.reso_id = (SELECT reso FROM _d1)),
    1::bigint,
    '4) D58: un rientro su due senza carico: il reso e'' nel presidio, con 1 rientro senza carico');

-- 5-9) D29
SELECT results_eq(
    $$SELECT v.codice_interno::text, v.merce_rientrata FROM script.vw_stati_doc_reso_merce_rientrata v
       WHERE v.codice_interno IN ('DRAFT', 'CONFERMATO', 'ANNULLATO') ORDER BY v.codice_interno$$,
    $$VALUES ('ANNULLATO', false), ('CONFERMATO', true), ('DRAFT', false)$$,
    '5) D29: il BB, DRAFT no, CONFERMATO si'', ANNULLATO no (abortito)');

-- Uno stato nuovo dopo la conferma, fabbricato e ritirato col ROLLBACK.
-- ⚠️ id esplicito oltre il massimo: il seed del catalogo porta id espliciti.
INSERT INTO config.stati_doc_reso (id, codice_interno, codice, descrizione, attivo, ordine, fase, is_abortito, iniziale)
SELECT COALESCE(max(id), 0) + 1000, 'PGTAP_DOPO_CONFERMA', 'PGTAP_DOPO_CONFERMA', 'pgTAP', true, 25, 'CHIUSO', false, false
  FROM config.stati_doc_reso;
SELECT is(
    (SELECT v.merce_rientrata FROM script.vw_stati_doc_reso_merce_rientrata v WHERE v.codice_interno = 'PGTAP_DOPO_CONFERMA'),
    true,
    '6) D29: uno stato nuovo dopo la conferma, non abortito: la merce e'' rientrata');

-- Fuori porta: lo stato del reso si scrive solo dal verbo, che questo stato non lo conosce.
ALTER TABLE vendite.resi DISABLE TRIGGER USER;
UPDATE vendite.resi SET stato_doc_reso_id = (SELECT id FROM config.stati_doc_reso WHERE codice_interno = 'PGTAP_DOPO_CONFERMA')
 WHERE id = (SELECT reso FROM _d1);
ALTER TABLE vendite.resi ENABLE TRIGGER USER;
SELECT is(
    (SELECT v.stato_codice_interno::text || ':' || v.rientri_senza_carico FROM dbops.vw_resi_confermati_senza_carico v
      WHERE v.reso_id = (SELECT reso FROM _d1)),
    'PGTAP_DOPO_CONFERMA:1',
    '7) D29: nello stato nuovo il reso senza carico resta nel presidio (lo stato dal BB, non dal letterale)');
SELECT is(
    (SELECT count(*) FROM vendite.vw_resi_righe_effettive v WHERE v.reso_id = (SELECT reso FROM _d1)),
    1::bigint,
    '8) D29: ...e la riga del reso resta effettiva per vendite.vw_resi_righe_effettive');

-- Il catalogo stampa i nomi senza schema quando lo schema e' nel search_path:
-- si legge con un search_path neutro.
CREATE FUNCTION pg_temp.pmg_viewdef(p regclass) RETURNS text
  LANGUAGE sql STABLE SET search_path = pg_catalog
  AS $$ SELECT pg_get_viewdef(p) $$;
SELECT is(
    (SELECT string_agg(v::text || ':' || (pg_temp.pmg_viewdef(v) LIKE '%CONFERMATO%')::text
                       || ':' || (pg_temp.pmg_viewdef(v) LIKE '%script.vw_stati_doc_reso_merce_rientrata%')::text,
                       ' ' ORDER BY v::text)
       FROM unnest(ARRAY['dbops.vw_resi_confermati_senza_carico'::regclass,
                         'vendite.vw_resi_righe_effettive'::regclass,
                         'vendite.vw_resi_da_riconsegnare'::regclass]) v),
    'dbops.vw_resi_confermati_senza_carico:false:true vendite.vw_resi_da_riconsegnare:false:true vendite.vw_resi_righe_effettive:false:true',
    '9) D29: le tre viste non nominano CONFERMATO e leggono il BB');

-- 10-12) ⑧
-- La bolla 3 di trasferimento A -> B (serve a C, sotto).
CREATE TEMP TABLE _d2 (ddt3 bigint, rett bigint, tras bigint, art_w uuid);
DO $d$
DECLARE v_d3 bigint;
BEGIN
    v_d3 := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                    'TRASFERIMENTO', (SELECT mag_a FROM _fix));
    UPDATE vendite.ddt SET magazzino_arrivo_id = (SELECT mag_b FROM _fix) WHERE id = v_d3;
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_d3, 1, art_s, 'semplice', 1, 1, 10, iva FROM _fix;
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_d3, 'EMESSO');
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_d3, 'SPEDITO');
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_d3, 'CONSEGNATO');
    INSERT INTO _d2 (ddt3) VALUES (v_d3);
END $d$;

-- ⚠️ Un carico senza valore porta la media a ZERO, non a NULL (magazzino.vw_costo_medio:
--   valore / qta): le uscite dopo di lui hanno costo 0. Un'uscita SENZA costo nasce solo
--   quando la giacenza e' a zero o sotto, cioe' da una causale che ammette lo stock
--   negativo (magazzino.causali.consente_stock_negativo: la colonna c'e', il seed oggi non
--   ne accende nessuna). Il caso si costruisce cosi', con la primitiva e due causali di
--   prova, sui documenti interni in bozza; tutto ritirato col ROLLBACK.
INSERT INTO magazzino.causali (codice_interno, codice, descrizione, segno, consente_stock_negativo)
VALUES ('PGT_PMG_USCITA_NEG', 'PGT_PMG_USCITA_NEG', 'pgTAP: uscita a stock negativo', -1, true);
UPDATE magazzino.causali SET consente_stock_negativo = true WHERE codice_interno = 'TRASF_OUT';
DO $d$
DECLARE v_w uuid; v_rett bigint; v_rr bigint; v_tras bigint; v_tr bigint; v_uid uuid;
        v_t_rett bigint; v_t_tras bigint;
BEGIN
    v_w := dbops.fn_pgtap_crea_articolo('PGT-PMG-VUOTO', true, false, false);
    SELECT id INTO v_t_rett FROM config.sorgenti WHERE codice_interno = 'RETTIFICA';
    SELECT id INTO v_t_tras FROM config.sorgenti WHERE codice_interno = 'TRASFERIMENTO';
    INSERT INTO magazzino.rettifiche (magazzino_id) VALUES ((SELECT mag_a FROM _fix)) RETURNING id INTO v_rett;
    INSERT INTO magazzino.rettifiche_righe (rettifica_id, articolo_id, qta_delta) VALUES (v_rett, v_w, -1) RETURNING id INTO v_rr;
    -- L'uscita a giacenza zero: nessuna media, costo NULL.
    PERFORM magazzino.fn_scrivi_movimento(
        p_magazzino_id => (SELECT mag_a FROM _fix), p_articolo_id => v_w, p_causale => 'PGT_PMG_USCITA_NEG',
        p_qta => -1, p_sorgente_tipo_id => v_t_rett, p_sorgente_id => v_rett, p_sorgente_riga => v_rr);
    -- Lo storno, per documento: un'entrata al costo dell'originale, cioe' senza costo.
    PERFORM 1 FROM magazzino.fn_storna_movimenti_sorgente(v_t_rett, NULL, p_sorgente_id => v_rett);

    -- La coppia del trasferimento a giacenza zero: l'uscita senza costo, la gemella anche.
    INSERT INTO magazzino.trasferimenti (magazzino_id_from, magazzino_id_to)
    VALUES ((SELECT mag_a FROM _fix), (SELECT mag_b FROM _fix)) RETURNING id, uid INTO v_tras, v_uid;
    INSERT INTO magazzino.trasferimenti_righe (trasferimento_id, articolo_id, qta) VALUES (v_tras, v_w, 1) RETURNING id INTO v_tr;
    PERFORM magazzino.fn_scrivi_movimento(
        p_magazzino_id => (SELECT mag_a FROM _fix), p_articolo_id => v_w, p_causale => 'TRASF_OUT',
        p_qta => -1, p_sorgente_tipo_id => v_t_tras, p_sorgente_id => v_tras, p_sorgente_riga => v_tr,
        p_transfer_uid => v_uid);
    PERFORM magazzino.fn_scrivi_movimento(
        p_magazzino_id => (SELECT mag_b FROM _fix), p_articolo_id => v_w, p_causale => 'TRASF_IN',
        p_qta => 1, p_sorgente_tipo_id => v_t_tras, p_sorgente_id => v_tras, p_sorgente_riga => v_tr,
        p_transfer_uid => v_uid);
    UPDATE _d2 SET rett = v_rett, tras = v_tras, art_w = v_w;
END $d$;

SELECT is(
    (SELECT count(*) FROM dbops.vw_magazzino_movimenti_senza_costo v
       JOIN config.sorgenti s ON s.id = v.sorgente_tipo_id
      WHERE v.articolo_id = (SELECT art_z FROM _fix) AND s.codice_interno = 'INVENTARIO'),
    1::bigint,
    '10) ⑧: il carico senza costo e'' nella spia');
SELECT is(
    (SELECT string_agg(trim_scale(m.qta)::text || ':' || (m.costo_unitario IS NULL)::text || ':'
                       || (m.storno_di_movimento_id IS NOT NULL)::text || ':'
                       || EXISTS (SELECT 1 FROM dbops.vw_magazzino_movimenti_senza_costo v WHERE v.id = m.id)::text,
                       ' ' ORDER BY m.id)
       FROM magazzino.movimenti m WHERE m.sorgente_id = (SELECT rett FROM _d2)
        AND m.sorgente_tipo_id = (SELECT id FROM config.sorgenti WHERE codice_interno = 'RETTIFICA')),
    '-1:true:false:false 1:true:true:false',
    '11) ⑧: l''uscita senza costo e il suo storno (un''entrata senza costo): lo storno non e'' nella spia');
SELECT is(
    (SELECT string_agg(c.codice_interno || '@' || (v.magazzino_id = (SELECT mag_b FROM _fix))::text, ',')
       FROM dbops.vw_magazzino_movimenti_senza_costo v
       JOIN magazzino.causali c ON c.id = v.causale_id
      WHERE v.sorgente_id = (SELECT tras FROM _d2)
        AND v.sorgente_tipo_id = (SELECT id FROM config.sorgenti WHERE codice_interno = 'TRASFERIMENTO')),
    'TRASF_IN@true',
    '12) ⑧: l''entrata gemella senza costo nel magazzino d''arrivo resta nella spia');

-- 13-15) C
SELECT ok(
    NOT EXISTS (SELECT 1 FROM dbops.vw_ddt_trasferimenti_consegnati_senza_arrivo v WHERE v.ddt_id = (SELECT ddt3 FROM _d2)),
    '13) C: la bolla di trasferimento consegnata con il suo arrivo non e'' nel presidio');
DELETE FROM magazzino.movimenti m
 WHERE m.sorgente_id = (SELECT ddt3 FROM _d2)
   AND m.qta > 0 AND m.storno_di_movimento_id IS NULL;
SELECT is(
    (SELECT v.prelievi_senza_arrivo FROM dbops.vw_ddt_trasferimenti_consegnati_senza_arrivo v
      WHERE v.ddt_id = (SELECT ddt3 FROM _d2)),
    1::bigint,
    '14) C: tolto l''arrivo, la bolla di trasferimento e'' nel presidio con 1 prelievo senza arrivo');
SELECT ok(
    NOT EXISTS (SELECT 1 FROM dbops.vw_ddt_trasferimenti_consegnati_senza_arrivo v WHERE v.ddt_id = (SELECT ddt FROM _d1)),
    '15) C: una bolla di vendita non e'' mai nel presidio dell''arrivo');

SELECT * FROM finish();
ROLLBACK;
