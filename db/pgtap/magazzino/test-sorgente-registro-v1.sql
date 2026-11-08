-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- pgtap-runner: owner
-- pgtap-runner-motivo: una parte del soggetto e' la primitiva del registro
--   (magazzino.fn_scrivi_movimento) e lo storno, RISERVATI: l'app non li esegue, ci
--   arriva solo dai verbi. Le provenienze sbagliate e le attese con documento (che oggi
--   nessun verbo scrive, e l'app non ha INSERT sugli attesi) si scrivono da proprietario.
--   E' la forma 3 del criterio del runner. Il contesto operatore e' comunque impostato.
--
-- Test: il registro di magazzino nella grammatica del modello — il tipo e' il documento,
--   la chiave e' la sua, sotto la riga e il dettaglio (S-3).
--   Brief: brief-db-sorgente-documento-e-riga §7.2 lotto M, giro M.1 (scheda magazzino
--   §2, §1.2, §6).
--
-- Il mondo: un magazzino, SEMPLICE (10 a 5) e A_LOTTI (lotti A e B, 6+6 a 3), caricati
--   con un inventario. Bolla 1: A_LOTTI 8 (prelievi A 5, B 3), SEMPLICE 2; emessa,
--   spedita, consegnata. Reso 1: SEMPLICE 1, confermato. Bolla 2: SEMPLICE 1, emessa e
--   poi annullata.
--
-- Elenco test (plan 17):
--    1) l'inventario scrive INVENTARIO + l'inventario + la riga, senza dettaglio
--    2) la bolla scrive DDT_VENDITA + la bolla + la riga + il prelievo, per ogni uscita
--    3) il reso scrive RESO_VENDITA + il reso + la riga + il rientro, al costo dell'uscita (5)
--    4) il guard: una riga di un altro documento -> E_SORG_RIGA_NON_DEL_DOCUMENTO
--    5) il guard: la bolla senza il dettaglio (livello minimo DETTAGLIO) -> E_SORG_LIVELLO_MANCANTE
--    6) il guard: un dettaglio di un'altra riga -> E_SORG_DETTAGLIO_NON_DELLA_RIGA
--    7) l'identita': lo stesso prelievo, la stessa causale e tranche -> E_MAG_MOVIMENTO_GIA_REGISTRATO
--    8) la primitiva: due chiavi del documento -> E_MAG_CHIAMATA_NON_VALIDA
--    9) l'annullo della bolla 2 storna per documento: uno storno per uscita, provenienza copiata
--   10) lo storno senza la chiave del documento -> E_MAG_CHIAMATA_NON_VALIDA (non uno storno sbagliato)
--   11) la disponibilita': un'attesa del documento intero e' PROPRIA di ogni sua riga (non blocca)
--   12) ...un'attesa di un'altra riga dello stesso documento e' altrui (blocca)
--   13) ...un'attesa di un altro documento e' altrui (blocca)
--   14) S-9: un reso confermato coi suoi carichi, spenta la sola regola di stato -> E_SORG_ORIGINE_REFERENZIATA
--   15) S-9: ...e una riga di bolla movimentata, spente le sole regole di stato
--   16) i cinque tipi di foglia non sono piu' sorgenti (giro M.3, 20261109-20)
--   17) ...e restano entita' di config.tipi_entita, con is_sorgente false
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('SREG');
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'emetti_ddt');
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'registra_magazzino');
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'conferma_reso');
END $az$;

CREATE TEMP TABLE _fix (mag bigint, art_s uuid, art_l uuid, lotto_a bigint, lotto_b bigint, iva integer,
                        inv bigint, t_ddt bigint, t_reso bigint, t_inv bigint);
DO $fix$
DECLARE v_mag bigint; v_s uuid; v_l uuid; v_la bigint; v_lb bigint; v_inv bigint; v_iva integer;
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-SREG-MAG', false);
    v_s   := dbops.fn_pgtap_crea_articolo('PGT-SREG-SEMPLICE', true, false, false);
    v_l   := dbops.fn_pgtap_crea_articolo('PGT-SREG-A-LOTTI',  true, true,  false);
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo) VALUES (v_l, 'PGT-SREG-LA', script.fn_data_operativa() - 10) RETURNING id INTO v_la;
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo) VALUES (v_l, 'PGT-SREG-LB', script.fn_data_operativa() - 5)  RETURNING id INTO v_lb;
    SELECT i.id INTO v_iva FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1;
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, costo_unitario) VALUES (v_inv, v_s, 10, 5);
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, lotto_id, qta_contata, costo_unitario) VALUES (v_inv, v_l, v_la, 6, 3);
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, lotto_id, qta_contata, costo_unitario) VALUES (v_inv, v_l, v_lb, 6, 3);
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv;
    PERFORM magazzino.fn_posta_inventario(v_inv);
    INSERT INTO _fix
    SELECT v_mag, v_s, v_l, v_la, v_lb, v_iva, v_inv,
           (SELECT id FROM config.sorgenti WHERE codice_interno = 'DDT_VENDITA'),
           (SELECT id FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA'),
           (SELECT id FROM config.sorgenti WHERE codice_interno = 'INVENTARIO');
END $fix$;

CREATE TEMP TABLE _d (ddt bigint, r_l bigint, r_s bigint, p_la bigint, p_lb bigint, reso bigint, rr bigint, ddt2 bigint);
DO $d$
DECLARE v_ddt bigint; v_rl bigint; v_rs bigint; v_pla bigint; v_plb bigint; v_reso bigint; v_rr bigint; v_d2 bigint;
BEGIN
    v_ddt := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                     'VENDITA', (SELECT mag FROM _fix));
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_ddt, 1, art_l, 'a lotti', 8, 8, 10, iva FROM _fix RETURNING id INTO v_rl;
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_ddt, 2, art_s, 'semplice', 2, 2, 10, iva FROM _fix RETURNING id INTO v_rs;
    INSERT INTO vendite.ddt_righe_prelievi (ddt_riga_id, qta, lotto_id) SELECT v_rl, 5, lotto_a FROM _fix RETURNING id INTO v_pla;
    INSERT INTO vendite.ddt_righe_prelievi (ddt_riga_id, qta, lotto_id) SELECT v_rl, 3, lotto_b FROM _fix RETURNING id INTO v_plb;
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_ddt, 'EMESSO');
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_ddt, 'SPEDITO');
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_ddt, 'CONSEGNATO');
    SELECT b.reso_id, b.resi_riga_id INTO v_reso, v_rr
      FROM dbops.fn_pgtap_crea_reso('SREG', v_ddt, 1, p_stato_codice_interno => 'DRAFT', p_ddt_riga_id => v_rs) b;
    PERFORM vendite.fn_conferma_reso(v_reso);

    v_d2 := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                    'VENDITA', (SELECT mag FROM _fix));
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_d2, 1, art_s, 'semplice', 1, 1, 10, iva FROM _fix;
    INSERT INTO _d VALUES (v_ddt, v_rl, v_rs, v_pla, v_plb, v_reso, v_rr, v_d2);
END $d$;

-- 1) l'inventario
SELECT is(
    (SELECT bool_and(m.sorgente_tipo_id = f.t_inv AND m.sorgente_id = f.inv AND r.inventario_id = f.inv
                     AND m.sorgente_dettaglio IS NULL AND m.sorgente_uid IS NULL)::text || ':' || count(*)
       FROM magazzino.movimenti m CROSS JOIN _fix f
       JOIN magazzino.inventari_righe r ON r.id = m.sorgente_riga
      WHERE m.sorgente_id = f.inv AND m.sorgente_tipo_id = f.t_inv),
    'true:3',
    '1) l''inventario: tipo INVENTARIO, la chiave dell''inventario, la riga; niente dettaglio');

-- 2) la bolla
SELECT is(
    (SELECT bool_and(p.ddt_riga_id = m.sorgente_riga AND dr.ddt_id = m.sorgente_id AND m.sorgente_uid IS NULL)::text
            || ':' || count(*)
       FROM magazzino.movimenti m CROSS JOIN _fix f CROSS JOIN _d d
       JOIN vendite.ddt_righe_prelievi p ON p.id = m.sorgente_dettaglio
       JOIN vendite.ddt_righe dr ON dr.id = p.ddt_riga_id
      WHERE m.sorgente_tipo_id = f.t_ddt AND m.sorgente_id = d.ddt AND m.qta < 0),
    'true:3',
    '2) la bolla: tipo DDT_VENDITA, la bolla, la riga, il prelievo come dettaglio (tre uscite)');

-- 3) il reso
SELECT is(
    (SELECT bool_and(x.resi_riga_id = m.sorgente_riga AND m.sorgente_id = d.reso)::text
            || ':' || trim_scale(min(m.costo_unitario))::text
       FROM magazzino.movimenti m CROSS JOIN _fix f CROSS JOIN _d d
       JOIN vendite.resi_righe_rientri x ON x.id = m.sorgente_dettaglio
      WHERE m.sorgente_tipo_id = f.t_reso AND m.sorgente_id = d.reso),
    'true:5',
    '3) il reso: tipo RESO_VENDITA, il reso, la riga, il rientro; al costo dell''uscita della bolla (5)');

-- 4-6) il guard unico del registro
SELECT throws_like(
    format($q$SELECT magazzino.fn_scrivi_movimento(p_magazzino_id => %s, p_articolo_id => %L::uuid,
              p_causale => 'RETT_POS', p_qta => 1, p_sorgente_tipo_id => %s, p_sorgente_id => %s,
              p_sorgente_riga => %s, p_sorgente_dettaglio => %s)$q$,
           (SELECT mag FROM _fix), (SELECT art_s FROM _fix), (SELECT t_ddt FROM _fix), (SELECT ddt2 FROM _d),
           (SELECT r_s FROM _d), (SELECT p.id FROM vendite.ddt_righe_prelievi p WHERE p.ddt_riga_id = (SELECT r_s FROM _d))),
    '%non è una riga del documento di origine%',
    '4) una riga della bolla 1 dichiarata della bolla 2: E_SORG_RIGA_NON_DEL_DOCUMENTO');
SELECT throws_like(
    format($q$SELECT magazzino.fn_scrivi_movimento(p_magazzino_id => %s, p_articolo_id => %L::uuid,
              p_causale => 'RETT_POS', p_qta => 1, p_sorgente_tipo_id => %s, p_sorgente_id => %s,
              p_sorgente_riga => %s)$q$,
           (SELECT mag FROM _fix), (SELECT art_s FROM _fix), (SELECT t_ddt FROM _fix), (SELECT ddt FROM _d),
           (SELECT r_s FROM _d)),
    '%deve arrivare fino al livello%',
    '5) la bolla senza il dettaglio: E_SORG_LIVELLO_MANCANTE (il registro vuole la foglia)');
SELECT throws_like(
    format($q$SELECT magazzino.fn_scrivi_movimento(p_magazzino_id => %s, p_articolo_id => %L::uuid,
              p_causale => 'RETT_POS', p_qta => 1, p_sorgente_tipo_id => %s, p_sorgente_id => %s,
              p_sorgente_riga => %s, p_sorgente_dettaglio => %s)$q$,
           (SELECT mag FROM _fix), (SELECT art_s FROM _fix), (SELECT t_ddt FROM _fix), (SELECT ddt FROM _d),
           (SELECT r_s FROM _d), (SELECT p_la FROM _d)),
    '%non appartiene alla riga%',
    '6) un prelievo di un''altra riga: E_SORG_DETTAGLIO_NON_DELLA_RIGA');

-- 7) l'identita', sulle nove colonne
SELECT throws_like(
    format($q$SELECT magazzino.fn_scrivi_movimento(p_magazzino_id => %s, p_articolo_id => %L::uuid,
              p_causale => 'SCARICO_VEN', p_qta => -1, p_sorgente_tipo_id => %s, p_sorgente_id => %s,
              p_sorgente_riga => %s, p_sorgente_dettaglio => %s, p_lotto_id => %s)$q$,
           (SELECT mag FROM _fix), (SELECT art_l FROM _fix), (SELECT t_ddt FROM _fix), (SELECT ddt FROM _d),
           (SELECT r_l FROM _d), (SELECT p_la FROM _d), (SELECT lotto_a FROM _fix)),
    '%ha già registrato il movimento%',
    '7) lo stesso prelievo con la stessa causale e tranche: E_MAG_MOVIMENTO_GIA_REGISTRATO');

-- 8) due chiavi del documento
SELECT throws_like(
    format($q$SELECT magazzino.fn_scrivi_movimento(p_magazzino_id => %s, p_articolo_id => %L::uuid,
              p_causale => 'RETT_POS', p_qta => 1, p_sorgente_tipo_id => %s, p_sorgente_id => %s,
              p_sorgente_uid => gen_random_uuid(), p_sorgente_riga => %s)$q$,
           (SELECT mag FROM _fix), (SELECT art_s FROM _fix), (SELECT t_inv FROM _fix), (SELECT inv FROM _fix),
           (SELECT min(r.id) FROM magazzino.inventari_righe r WHERE r.inventario_id = (SELECT inv FROM _fix))),
    '%Chiamata non valida a magazzino.fn_%',
    '8) due chiavi del documento: E_MAG_CHIAMATA_NON_VALIDA');

-- 9) l'annullo della bolla 2 storna per documento
DO $a$ BEGIN
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt((SELECT ddt2 FROM _d), 'EMESSO');
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt((SELECT ddt2 FROM _d), 'ANNULLATO');
END $a$;
SELECT is(
    (SELECT count(*) FILTER (WHERE s.id IS NOT NULL)::text || '/' || count(*)::text || ':'
            || COALESCE(bool_and(s.sorgente_tipo_id = o.sorgente_tipo_id AND s.sorgente_id = o.sorgente_id
                                 AND s.sorgente_riga = o.sorgente_riga
                                 AND s.sorgente_dettaglio = o.sorgente_dettaglio), false)::text
       FROM magazzino.movimenti o
       LEFT JOIN magazzino.movimenti s ON s.storno_di_movimento_id = o.id
      WHERE o.sorgente_tipo_id = (SELECT t_ddt FROM _fix) AND o.sorgente_id = (SELECT ddt2 FROM _d)
        AND o.storno_di_movimento_id IS NULL),
    '1/1:true',
    '9) l''annullo storna per documento: ogni uscita ha il suo storno, con la provenienza copiata');

-- 10) lo storno con la firma di prima (tipo + foglie, senza documento)
SELECT throws_like(
    format('SELECT * FROM magazzino.fn_storna_movimenti_sorgente(%s, ARRAY[%s]::bigint[])',
           (SELECT t_ddt FROM _fix), (SELECT p_la FROM _d)),
    '%Chiamata non valida a magazzino.fn_%',
    '10) lo storno senza la chiave del documento: E_MAG_CHIAMATA_NON_VALIDA, non uno storno sbagliato');

-- 11-13) la disponibilita': le attese proprie per prefisso. SEMPLICE in giacenza: 10 - 2 + 1 = 9.
INSERT INTO magazzino.movimenti_attesi (articolo_id, magazzino_id, qta, causale_id, sorgente_tipo_id, sorgente_id)
SELECT art_s, mag, -9, (SELECT id FROM magazzino.causali WHERE codice_interno = 'SCARICO_VEN'), t_ddt, (SELECT ddt FROM _d)
  FROM _fix;
SELECT is(
    (SELECT script.fn_check_disponibilita_uscita(f.mag, f.art_s, 1, f.t_ddt, d.r_s, NULL, NULL, NULL, false,
                                                 d.ddt, (SELECT p.id FROM vendite.ddt_righe_prelievi p WHERE p.ddt_riga_id = d.r_s))
       FROM _fix f, _d d),
    '[]'::jsonb,
    '11) un''attesa della bolla intera e'' propria del prelievo di una sua riga: non blocca');
UPDATE magazzino.movimenti_attesi SET sorgente_riga = (SELECT r_l FROM _d)
 WHERE sorgente_id = (SELECT ddt FROM _d) AND sorgente_tipo_id = (SELECT t_ddt FROM _fix);
SELECT is(
    (SELECT script.fn_check_disponibilita_uscita(f.mag, f.art_s, 1, f.t_ddt, d.r_s, NULL, NULL, NULL, false,
                                                 d.ddt) -> 0 ->> 'codice'
       FROM _fix f, _d d),
    'E_MAG_MERCE_BLOCCATA',
    '12) un''attesa di un''altra riga della stessa bolla e'' altrui: blocca');
SELECT is(
    (SELECT script.fn_check_disponibilita_uscita(f.mag, f.art_s, 1, f.t_ddt, NULL, NULL, NULL, NULL, false,
                                                 d.ddt2) -> 0 ->> 'codice'
       FROM _fix f, _d d),
    'E_MAG_MERCE_BLOCCATA',
    '13) un''attesa di un''altra bolla e'' altrui: blocca');
DELETE FROM magazzino.movimenti_attesi WHERE sorgente_id = (SELECT ddt FROM _d) AND sorgente_tipo_id = (SELECT t_ddt FROM _fix);

-- 14-15) S-9: il registro protegge da se' i documenti, le righe e i dettagli movimentati.
--   Le regole di stato (il reso si cancella solo da bozza vuota, la riga di bolla solo in
--   bozza) parlano per prime e restano: per vedere la rete del registro si spengono SOLO
--   loro, per nome, nella transazione; il lato «in uscita» resta acceso.
ALTER TABLE vendite.resi DISABLE TRIGGER trg_resi_a10_guard_delete_solo_bozza_dlt;
SELECT throws_like(
    format('DELETE FROM vendite.resi WHERE id = %s', (SELECT reso FROM _d)),
    '%dichiarano di nascere da qui%',
    '14) un reso confermato coi suoi carichi non si cancella neppure senza la regola di stato: E_SORG_ORIGINE_REFERENZIATA');
ALTER TABLE vendite.resi ENABLE TRIGGER trg_resi_a10_guard_delete_solo_bozza_dlt;

ALTER TABLE vendite.ddt_righe DISABLE TRIGGER trg_ddt_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt;
ALTER TABLE vendite.ddt_righe DISABLE TRIGGER trg_ddt_righe_a10_block_ddt_dlt;
ALTER TABLE vendite.ddt_righe_prelievi DISABLE TRIGGER USER;
ALTER TABLE vendite.ddt_righe_prelievi ENABLE TRIGGER trg_vendite_ddt_righe_prelievi_a10_sorgente_in_uscita_dlt;
SELECT throws_like(
    format('DELETE FROM vendite.ddt_righe WHERE id = %s', (SELECT r_l FROM _d)),
    '%dichiarano di nascere da qui%',
    '15) una riga di bolla movimentata non si cancella neppure senza le regole di stato: E_SORG_ORIGINE_REFERENZIATA');
ALTER TABLE vendite.ddt_righe ENABLE TRIGGER USER;
ALTER TABLE vendite.ddt_righe_prelievi ENABLE TRIGGER USER;

-- 16-17) il ritiro dei tipi di foglia (giro M.3): il registro scrive il tipo del documento,
--   e le foglie restano entita' (note di magazzino, errori), non sorgenti.
SELECT is_empty(
    $$SELECT s.codice_interno FROM config.sorgenti s
       WHERE s.codice_interno IN ('INVENTARIO_RIGA', 'RETTIFICA_RIGA', 'TRASFERIMENTO_RIGA',
                                  'DDT_VENDITA_PRELIEVO', 'RESO_VENDITA_RIENTRO')$$,
    '16) INVENTARIO_RIGA, RETTIFICA_RIGA, TRASFERIMENTO_RIGA, DDT_VENDITA_PRELIEVO, RESO_VENDITA_RIENTRO non sono piu'' sorgenti');
SELECT is(
    (SELECT string_agg(e.codice || ':' || e.is_sorgente || ':' || coalesce(e.sorgente_codice_interno, '-'), ',' ORDER BY e.codice)
       FROM config.tipi_entita e
      WHERE e.codice IN ('INVENTARIO_RIGA', 'RETTIFICA_RIGA', 'TRASFERIMENTO_RIGA',
                         'DDT_VENDITA_PRELIEVO', 'RESO_VENDITA_RIENTRO')),
    'DDT_VENDITA_PRELIEVO:false:-,INVENTARIO_RIGA:false:-,RESO_VENDITA_RIENTRO:false:-,RETTIFICA_RIGA:false:-,TRASFERIMENTO_RIGA:false:-',
    '17) le cinque restano entita'' (note, errori), con is_sorgente false e nessuna sorgente legata');

SELECT * FROM finish();
ROLLBACK;
