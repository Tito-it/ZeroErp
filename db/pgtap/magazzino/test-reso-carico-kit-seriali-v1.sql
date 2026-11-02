-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la merce rientra col reso — i tre casi che magazzino/test-reso-carico-v1
--   non fabbrica: il KIT uscito per componenti (D-3b-g), il SERIALE, e
--   l'UBICAZIONE di rientro in un magazzino che le usa (D-L2-m).
--   Brief: brief-db-magazzino-lotto-3-bis-carico-da-reso, sezioni 3 e 5.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): pg_temp.crea_reso fa le righe col builder dbops.fn_pgtap_crea_reso, in bozza; il magazzino scelto (reso n.3) si scrive in bozza dopo la nascita, il builder non lo sceglie; restano scritti a mano i rientri e le conferme dal verbo, che sono il caso.
--
-- Il mondo, costruito: MAG senza ubicazioni, MAGU con l'ubicazione U1; un KIT
--   non gestito (is_composito) con due componenti gestiti — C_SEMPLICE (2 per
--   kit) e C_LOTTI (3 per kit, requires_lotto) —, un articolo a SERIALE e una
--   merce SEMPLICE. Caricati con un inventario in MAG. Una bolla OMAGGIO
--   (muove merce, non e' fatturabile: i componenti non chiedono prezzi) da
--   MAG, emessa e consegnata: KIT 2 (escono i componenti: 4 e 6), SERIALE 1,
--   SEMPLICE 4.
--
-- ⚠️ Non fabbricato qui: la proporzione CON RESTO (tre pezzi per kit, un kit
--   su due). Le quantita' dei componenti sono calcolate dal trigger del kit
--   (coefficiente × quantita' della riga) e con coefficienti interi la
--   proporzione e' sempre esatta. La regola sta in
--   vendite.fn_reso_merce_da_rientrare (colonna esatta): e' un ramo DICHIARATO
--   non provato, non un ramo verificato.
--
-- Elenco test (plan 14):
--    1) le voci del reso del kit sono i due COMPONENTI, entrambi automatici (D-L3-f ereditata)
--    2) la proporzione: 1 kit su 2 -> C_SEMPLICE 2, C_LOTTI 3
--    3) il seriale e' una voce automatica (un solo prelievo: il seriale e' gia' deciso)
--    4) il verbo conferma: tre carichi — C_SEMPLICE 2, C_LOTTI 3, SERIALE 1
--    5) il componente a lotti rientra nel SUO lotto
--    6) il seriale rientra con il suo asset, al suo costo
--    7) il KIT (non gestito) non ha movimenti
--    8) secondo reso del kit: un componente oltre la sua proporzione -> E_RESO_RIENTRI_INCOMPLETI
--    9) kit reso INCOMPLETO (solo C_SEMPLICE): nessun motivo
--   10) ...e il verbo carica il solo componente tornato
--   11) reso in MAGU senza rientri: la voce SEMPLICE non e' automatica -> E_RESO_RIENTRI_INCOMPLETI
--   12) rientro senza ubicazione in MAGU -> il motivo della check di riga (merce non ricollocabile)
--   13) con l'ubicazione U1 la check tace
--   14) il carico va in MAGU, sull'ubicazione U1
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- Il mondo: un'azienda NUOVA (su dbdev quella dell'operatore ha gia' magazzini).
CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('L3BK');
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'emetti_ddt');
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'registra_magazzino');
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'conferma_reso');
END $az$;

CREATE TEMP TABLE _fix (mag bigint, magu bigint, u1 bigint, kit uuid, c_s uuid, c_l uuid, ser uuid, sem uuid,
                        lotto_a bigint, sn1 bigint);
DO $fix$
DECLARE
    v_mag bigint; v_magu bigint; v_u1 bigint; v_k uuid; v_cs uuid; v_cl uuid; v_ser uuid; v_sem uuid;
    v_la bigint; v_sn bigint; v_inv bigint;
BEGIN
    v_mag  := dbops.fn_pgtap_crea_magazzino('PGT-L3BK-MAG', false);
    v_magu := dbops.fn_pgtap_crea_magazzino('PGT-L3BK-MAGU', true);
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id)
    VALUES (v_magu, 'PGT-L3BK-U1', (SELECT t.id FROM config.tipi_ubicazione t ORDER BY t.id LIMIT 1))
    RETURNING id INTO v_u1;

    v_k   := dbops.fn_pgtap_crea_articolo('PGT-L3BK-KIT',       false, false, false,
                                          p_is_composito => true);
    v_cs  := dbops.fn_pgtap_crea_articolo('PGT-L3BK-C-SEMPLICE', true, false, false);
    v_cl  := dbops.fn_pgtap_crea_articolo('PGT-L3BK-C-LOTTI',    true, true,  false);
    v_ser := dbops.fn_pgtap_crea_articolo('PGT-L3BK-SERIALE',    true, false, true);
    v_sem := dbops.fn_pgtap_crea_articolo('PGT-L3BK-SEMPLICE',   true, false, false);
    INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)
    VALUES (v_k, v_cs, 2, script.fn_data_operativa() - 30), (v_k, v_cl, 3, script.fn_data_operativa() - 30);

    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo) VALUES (v_cl, 'PGT-L3BK-A', script.fn_data_operativa() - 10) RETURNING id INTO v_la;
    INSERT INTO magazzino.assets (articolo_id, seriale, stato_id, ownership_id, emittente_fiscale_id)
    VALUES (v_ser, 'PGT-L3BK-SN1',
            (SELECT s.id FROM config.stati_assets s WHERE s.attivo ORDER BY s.id LIMIT 1),
            (SELECT o.id FROM config.assets_ownership o WHERE o.attivo ORDER BY o.id LIMIT 1),
            (SELECT emittente_fiscale_id FROM _m))
    RETURNING id INTO v_sn;

    INSERT INTO _fix
    SELECT v_mag, v_magu, v_u1, v_k, v_cs, v_cl, v_ser, v_sem, v_la, v_sn;

    -- Il carico: C_SEMPLICE 10 a 2, C_LOTTI 10 nel lotto A a 4, il seriale a 100, SEMPLICE 10 a 5.
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, costo_unitario) VALUES (v_inv, v_cs, 10, 2);
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, lotto_id, qta_contata, costo_unitario) VALUES (v_inv, v_cl, v_la, 10, 4);
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, asset_id, qta_contata, costo_unitario) VALUES (v_inv, v_ser, v_sn, 1, 100);
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, costo_unitario) VALUES (v_inv, v_sem, 10, 5);
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv;
    PERFORM magazzino.fn_posta_inventario(v_inv);
END $fix$;

-- La bolla OMAGGIO: KIT 2, SERIALE 1, SEMPLICE 4 — emessa e consegnata.
CREATE TEMP TABLE _d (ddt bigint, r_k bigint, r_ser bigint, r_sem bigint);
DO $d$
DECLARE v_ddt bigint; v_rk bigint; v_rser bigint; v_rsem bigint; v_comp_l bigint;
BEGIN
    v_ddt := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                     'OMAGGIO', (SELECT mag FROM _fix));
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita)
    SELECT v_ddt, 1, kit, 'kit', 2, 2 FROM _fix RETURNING id INTO v_rk;
    PERFORM vendite.fn_ddt_riga_componenti_init(v_rk, (SELECT emittente_soggetto_ruolo_id FROM _m), script.fn_data_operativa());
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita)
    SELECT v_ddt, 2, ser, 'seriale', 1, 1 FROM _fix RETURNING id INTO v_rser;
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita)
    SELECT v_ddt, 3, sem, 'semplice', 4, 4 FROM _fix RETURNING id INTO v_rsem;
    -- I prelievi da scegliere: il componente a lotti, il seriale.
    SELECT drc.id INTO v_comp_l FROM vendite.ddt_righe_componenti drc
     WHERE drc.riga_ddt_id = v_rk AND drc.componente_id = (SELECT c_l FROM _fix);
    INSERT INTO vendite.ddt_righe_prelievi (ddt_riga_id, ddt_riga_componente_id, qta, lotto_id)
    SELECT v_rk, v_comp_l, 6, lotto_a FROM _fix;
    INSERT INTO vendite.ddt_righe_prelievi (ddt_riga_id, qta, asset_id) SELECT v_rser, 1, sn1 FROM _fix;
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_ddt, 'EMESSO');
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_ddt, 'SPEDITO');
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_ddt, 'CONSEGNATO');
    INSERT INTO _d VALUES (v_ddt, v_rk, v_rser, v_rsem);
END $d$;

-- Un reso a credito in bozza: una riga per (riga di bolla, quantita'), dal
-- builder; su un magazzino scelto o di default.
-- ⚠️ Il builder non sceglie il magazzino: il reso nasce con quello della bolla
--   e, se il test ne vuole un altro, lo cambia in bozza (dove si sceglie,
--   D-3b-a), prima di ogni rientro.
CREATE FUNCTION pg_temp.crea_reso(p_righe jsonb, p_magazzino bigint DEFAULT NULL)
RETURNS bigint LANGUAGE plpgsql AS $f$
DECLARE v_reso bigint; v_r jsonb;
BEGIN
    FOR v_r IN SELECT * FROM jsonb_array_elements(p_righe) LOOP
        SELECT b.reso_id INTO v_reso
          FROM dbops.fn_pgtap_crea_reso('L3BK', CASE WHEN v_reso IS NULL THEN (SELECT ddt FROM _d) END,
                                        (v_r ->> 'qta')::numeric, p_stato_codice_interno => 'DRAFT',
                                        p_ddt_riga_id => (v_r ->> 'riga')::bigint, p_reso_id => v_reso) b;
    END LOOP;
    IF p_magazzino IS NOT NULL THEN
        UPDATE vendite.resi SET magazzino_id = p_magazzino WHERE id = v_reso;
    END IF;
    RETURN v_reso;
END $f$;

-- Il reso n.1: 1 kit su 2, e il seriale.
CREATE TEMP TABLE _r1 AS
SELECT pg_temp.crea_reso(jsonb_build_array(jsonb_build_object('riga', r_k, 'qta', 1),
                                           jsonb_build_object('riga', r_ser, 'qta', 1))) AS reso
  FROM _d;

-- 1-3) le voci
SELECT is(
    (SELECT string_agg(a.codice || ':' || m.automatico, ' ' ORDER BY a.codice)
       FROM vendite.resi r, vendite.fn_reso_merce_da_rientrare(r) m
       JOIN catalogo.articoli a ON a.id = m.articolo_id
      WHERE r.id = (SELECT reso FROM _r1) AND m.ddt_riga_componente_id IS NOT NULL),
    'PGT-L3BK-C-LOTTI:true PGT-L3BK-C-SEMPLICE:true',
    '1) il reso del kit fa rientrare i due COMPONENTI (sono loro a essere usciti), entrambi automatici');
SELECT is(
    (SELECT string_agg(a.codice || '=' || trim_scale(m.qta)::text, ' ' ORDER BY a.codice)
       FROM vendite.resi r, vendite.fn_reso_merce_da_rientrare(r) m
       JOIN catalogo.articoli a ON a.id = m.articolo_id
      WHERE r.id = (SELECT reso FROM _r1) AND m.ddt_riga_componente_id IS NOT NULL),
    'PGT-L3BK-C-LOTTI=3 PGT-L3BK-C-SEMPLICE=2',
    '2) la proporzione (D-3b-g): 1 kit su 2 -> 2 del primo componente, 3 del secondo');
SELECT ok(
    (SELECT m.automatico FROM vendite.resi r, vendite.fn_reso_merce_da_rientrare(r) m
      WHERE r.id = (SELECT reso FROM _r1) AND m.articolo_id = (SELECT ser FROM _fix)),
    '3) il seriale e'' automatico: il suo prelievo e'' uno, e il seriale e'' gia'' deciso');

-- 4-7) la conferma
SELECT vendite.fn_conferma_reso((SELECT reso FROM _r1));
CREATE TEMP TABLE _car AS
SELECT m.*
  FROM magazzino.movimenti m
  JOIN config.sorgenti so ON so.id = m.sorgente_tipo_id AND so.codice_interno = 'RESO_VENDITA_RIENTRO'
  JOIN vendite.resi_righe_rientri x ON x.id = m.sorgente_riga
  JOIN vendite.resi_righe rr ON rr.id = x.resi_riga_id
 WHERE rr.reso_id = (SELECT reso FROM _r1);
SELECT is(
    (SELECT string_agg(a.codice || ':' || trim_scale(k.qta)::text, ' ' ORDER BY a.codice)
       FROM _car k JOIN catalogo.articoli a ON a.id = k.articolo_id),
    'PGT-L3BK-C-LOTTI:3 PGT-L3BK-C-SEMPLICE:2 PGT-L3BK-SERIALE:1',
    '4) tre carichi: i due componenti in proporzione e il seriale');
SELECT is(
    (SELECT k.lotto_id FROM _car k WHERE k.articolo_id = (SELECT c_l FROM _fix)),
    (SELECT lotto_a FROM _fix),
    '5) il componente a lotti rientra nel SUO lotto (dal prelievo d''origine)');
SELECT is(
    (SELECT k.asset_id::text || '@' || trim_scale(k.costo_unitario)::text FROM _car k WHERE k.articolo_id = (SELECT ser FROM _fix)),
    (SELECT sn1::text || '@100' FROM _fix),
    '6) il seriale rientra con il suo asset, al costo della sua uscita');
SELECT is(
    (SELECT count(*)::int FROM magazzino.movimenti m WHERE m.articolo_id = (SELECT kit FROM _fix)),
    0,
    '7) il kit, non gestito, non muove niente: ne'' all''uscita ne'' al rientro');

-- 8-10) il reso n.2: l'altro kit, reso INCOMPLETO
CREATE TEMP TABLE _r2 AS
SELECT pg_temp.crea_reso(jsonb_build_array(jsonb_build_object('riga', r_k, 'qta', 1))) AS reso FROM _d;
CREATE TEMP TABLE _r2x AS
SELECT rr.id AS rr_k,
       (SELECT p.id FROM vendite.ddt_righe_prelievi p
          JOIN vendite.ddt_righe_componenti drc ON drc.id = p.ddt_riga_componente_id
         WHERE p.ddt_riga_id = (SELECT r_k FROM _d) AND drc.componente_id = (SELECT c_s FROM _fix)) AS p_cs
  FROM vendite.resi_righe rr WHERE rr.reso_id = (SELECT reso FROM _r2);
INSERT INTO vendite.resi_righe_rientri (resi_riga_id, ddt_riga_prelievo_id, qta) SELECT rr_k, p_cs, 3 FROM _r2x;
SELECT is(
    (SELECT script.fn_check_reso_merce(r) -> 0 ->> 'codice' FROM vendite.resi r WHERE r.id = (SELECT reso FROM _r2)),
    'E_RESO_RIENTRI_INCOMPLETI',
    '8) un componente oltre la sua proporzione (3 su 2): E_RESO_RIENTRI_INCOMPLETI');
UPDATE vendite.resi_righe_rientri SET qta = 2 WHERE resi_riga_id = (SELECT rr_k FROM _r2x);
SELECT is(
    (SELECT script.fn_check_reso_merce(r) FROM vendite.resi r WHERE r.id = (SELECT reso FROM _r2)),
    '[]'::jsonb,
    '9) il kit torna senza il componente a lotti: chi scrive un rientro si prende la riga, nessun motivo');
SELECT vendite.fn_conferma_reso((SELECT reso FROM _r2));
SELECT is(
    (SELECT string_agg(a.codice || ':' || trim_scale(m.qta)::text, ' ')
       FROM magazzino.movimenti m
       JOIN config.sorgenti so ON so.id = m.sorgente_tipo_id AND so.codice_interno = 'RESO_VENDITA_RIENTRO'
       JOIN vendite.resi_righe_rientri x ON x.id = m.sorgente_riga
       JOIN vendite.resi_righe rr ON rr.id = x.resi_riga_id
       JOIN catalogo.articoli a ON a.id = m.articolo_id
      WHERE rr.reso_id = (SELECT reso FROM _r2)),
    'PGT-L3BK-C-SEMPLICE:2',
    '10) ...e il verbo carica il solo componente tornato (il registro dice il vero)');

-- 11-14) il reso n.3: SEMPLICE 2, nel magazzino con le ubicazioni
CREATE TEMP TABLE _r3 AS
SELECT pg_temp.crea_reso(jsonb_build_array(jsonb_build_object('riga', r_sem, 'qta', 2)),
                         (SELECT magu FROM _fix)) AS reso FROM _d;
SELECT is(
    (SELECT script.fn_check_reso_merce(r) -> 0 ->> 'codice' FROM vendite.resi r WHERE r.id = (SELECT reso FROM _r3)),
    'E_RESO_RIENTRI_INCOMPLETI',
    '11) in un magazzino con le ubicazioni il rientro non e'' automatico: c''e'' da dire dove');
INSERT INTO vendite.resi_righe_rientri (resi_riga_id, ddt_riga_prelievo_id, qta)
SELECT rr.id, (SELECT p.id FROM vendite.ddt_righe_prelievi p WHERE p.ddt_riga_id = (SELECT r_sem FROM _d)), 2
  FROM vendite.resi_righe rr WHERE rr.reso_id = (SELECT reso FROM _r3);
SELECT is(
    (SELECT script.fn_check_reso_merce(r) -> 0 ->> 'reason' FROM vendite.resi r WHERE r.id = (SELECT reso FROM _r3)),
    'MERCE_NON_RICOLLOCABILE',
    '12) un rientro senza ubicazione in MAGU: il motivo della check di riga (la stessa della primitiva)');
UPDATE vendite.resi_righe_rientri x SET ubicazione_id = (SELECT u1 FROM _fix)
  FROM vendite.resi_righe rr WHERE rr.id = x.resi_riga_id AND rr.reso_id = (SELECT reso FROM _r3);
SELECT is(
    (SELECT script.fn_check_reso_merce(r) FROM vendite.resi r WHERE r.id = (SELECT reso FROM _r3)),
    '[]'::jsonb,
    '13) con l''ubicazione U1 la check tace');
SELECT vendite.fn_conferma_reso((SELECT reso FROM _r3));
SELECT is(
    (SELECT string_agg(trim_scale(m.qta)::text || '@' || u.codice, ',')
       FROM magazzino.movimenti m JOIN magazzino.ubicazioni u ON u.id = m.ubicazione_id
      WHERE m.magazzino_id = (SELECT magu FROM _fix)),
    '2@PGT-L3BK-U1',
    '14) il carico va in MAGU, sull''ubicazione del rientro');

SELECT * FROM finish();
ROLLBACK;
