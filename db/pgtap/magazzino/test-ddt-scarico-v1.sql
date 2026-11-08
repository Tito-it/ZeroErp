-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la merce esce con la bolla — il verbo vendite.fn_cambia_stato_ddt
--   porta una bolla di VENDITA a EMESSO e scrive uno scarico per PRELIEVO
--   (D-L3-b, D-L3-d), crea da se' il prelievo della merce semplice, si ferma
--   sulla giacenza e sul blocco di un altro, e all'annullo storna.
--   Brief: brief-db-magazzino-lotto-3-scarico-da-ddt, sezioni 3 e 5.
-- rev 2026-10-25 (brief-modello-documento-vendita §7, giro 5): ATTESE CAMBIATE dei test 4 e 16, per
--   regola ritirata: la porta sullo stato (E_DOC_STATO_SOLO_DAL_VERBO) vale per OGNI bolla, quindi il 4
--   aspetta la frase nuova (non piu' E_DDT_STATO_SOLO_DA_VERBO, «muove merce») e il 16 aspetta il rifiuto
--   anche per la bolla senza merce (prima passava dall'UPDATE diretto).
--
-- Il mondo: un magazzino senza ubicazioni, tre articoli costruiti —
--   SEMPLICE (gestito), A_LOTTI (gestito, requires_lotto), NON_GESTITO —
--   caricati con un inventario: SEMPLICE 10, A_LOTTI 6 nel lotto A e 6 nel B.
--
-- Elenco test (plan 16):
--    1) prelievi incompleti (A_LOTTI: 5 su 8) -> fn_check_ddt_merce dice E_DDT_PRELIEVI_INCOMPLETI
--    2) ...e la capability di emissione lo porta (fn_check_ddt_emittibile)
--    3) prelievi completi -> fn_check_ddt_merce e' vuota (la SEMPLICE non ha prelievi: e' automatica)
--    4) UPDATE diretto a EMESSO di una bolla che muove merce -> E_DOC_STATO_SOLO_DAL_VERBO
--    5) il verbo emette: tre scarichi SCARICO_VEN (uno automatico, due per lotto)
--    6) il prelievo automatico della SEMPLICE esiste, per l'intera quantita'
--    7) ogni scarico ha per provenienza la bolla, la riga e il suo prelievo (DDT_VENDITA; rev 2026-11-09, lotto M)
--    8) giacenze dopo l'emissione: SEMPLICE 6, A_LOTTI 4
--    9) la NON_GESTITO non ha movimenti
--   10) prelievi congelati fuori bozza -> E_RIGA_DOC_NON_BOZZA
--   11) bolla oltre la giacenza -> rifiuto (E_MAG_GIACENZA_INSUFFICIENTE), niente emesso
--   12) un blocco altrui ferma l'emissione (E_MAG_MERCE_BLOCCATA)
--   13) liberato il blocco, la stessa bolla si emette
--   14) annullo della bolla emessa: tre storni, al costo dell'originale
--   15) giacenze dopo l'annullo: SEMPLICE 7, A_LOTTI 12
--   16) anche una bolla che NON muove merce (solo NON_GESTITO): l'UPDATE diretto e' rifiutato
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- Il mondo: azienda, operatore, contesto e un cliente fatturabile legato.
-- Un'azienda NUOVA, non quella dell'operatore di sviluppo: su dbdev quella ha
-- gia' dei magazzini (e forse un predefinito), che falserebbero default e giacenze.
CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
-- Con il contesto aperto, il mondo cliente riusa l'azienda di chi agisce.
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('L3SC');
-- Il verbo applica emetti_ddt, l'inventario registra_magazzino, il blocco
-- blocca_merce: l'operatore di fixture non ha azioni, si costruiscono qui.
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'emetti_ddt');
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'registra_magazzino');
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'blocca_merce');
END $az$;

CREATE TEMP TABLE _fix (mag bigint, art_s uuid, art_l uuid, art_n uuid, lotto_a bigint, lotto_b bigint);
DO $fix$
DECLARE
    v_mag bigint; v_s uuid; v_l uuid; v_n uuid; v_la bigint; v_lb bigint; v_inv bigint;
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-L3S-MAG', false);
    v_s   := dbops.fn_pgtap_crea_articolo('PGT-L3S-SEMPLICE', true,  false, false);
    v_l   := dbops.fn_pgtap_crea_articolo('PGT-L3S-A-LOTTI',  true,  true,  false);
    v_n   := dbops.fn_pgtap_crea_articolo('PGT-L3S-NON-GEST', false, false, false);
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo) VALUES (v_l, 'PGT-L3S-A', script.fn_data_operativa() - 10) RETURNING id INTO v_la;
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo) VALUES (v_l, 'PGT-L3S-B', script.fn_data_operativa() - 5)  RETURNING id INTO v_lb;
    INSERT INTO _fix VALUES (v_mag, v_s, v_l, v_n, v_la, v_lb);

    -- Il carico: SEMPLICE 10 a 5, A_LOTTI 6+6 a 3.
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, costo_unitario) VALUES (v_inv, v_s, 10, 5);
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, lotto_id, qta_contata, costo_unitario) VALUES (v_inv, v_l, v_la, 6, 3);
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, lotto_id, qta_contata, costo_unitario) VALUES (v_inv, v_l, v_lb, 6, 3);
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv;
    PERFORM magazzino.fn_posta_inventario(v_inv);
END $fix$;

-- La bolla n.1 (VENDITA): SEMPLICE 4 (nessun prelievo: automatico),
-- A_LOTTI 8 (prelievi a mano), NON_GESTITO 2 (non muove).
CREATE TEMP TABLE _d1 (ddt bigint, r_s bigint, r_l bigint, r_n bigint);
DO $d$
DECLARE v_ddt bigint; v_rs bigint; v_rl bigint; v_rn bigint; v_iva integer;
BEGIN
    SELECT i.id INTO v_iva FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1;
    v_ddt := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                     'VENDITA', (SELECT mag FROM _fix));
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_ddt, 1, art_s, 'semplice', 4, 4, 10, v_iva FROM _fix RETURNING id INTO v_rs;
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_ddt, 2, art_l, 'a lotti', 8, 8, 10, v_iva FROM _fix RETURNING id INTO v_rl;
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_ddt, 3, art_n, 'non gestito', 2, 2, 10, v_iva FROM _fix RETURNING id INTO v_rn;
    INSERT INTO vendite.ddt_righe_prelievi (ddt_riga_id, qta, lotto_id) SELECT v_rl, 5, lotto_a FROM _fix;
    INSERT INTO _d1 VALUES (v_ddt, v_rs, v_rl, v_rn);
END $d$;

-- 1-2) i prelievi della riga a lotti coprono 5 pezzi su 8
SELECT is(
    (SELECT script.fn_check_ddt_merce(d) -> 0 ->> 'codice' FROM vendite.ddt d WHERE d.id = (SELECT ddt FROM _d1)),
    'E_DDT_PRELIEVI_INCOMPLETI',
    '1) prelievi incompleti: la check della merce lo dice');
SELECT ok(
    (SELECT script.fn_check_ddt_emittibile(d) @> '[{"codice": "E_DDT_PRELIEVI_INCOMPLETI"}]'::jsonb
       FROM vendite.ddt d WHERE d.id = (SELECT ddt FROM _d1)),
    '2) ...e la check dell''emissione lo porta (capability e guard: una sede)');

-- 3) completati: la SEMPLICE non ha prelievi ed e' automatica
INSERT INTO vendite.ddt_righe_prelievi (ddt_riga_id, qta, lotto_id) SELECT (SELECT r_l FROM _d1), 3, lotto_b FROM _fix;
SELECT is(
    (SELECT script.fn_check_ddt_merce(d) FROM vendite.ddt d WHERE d.id = (SELECT ddt FROM _d1)),
    '[]'::jsonb,
    '3) prelievi completi: nessun motivo fisico (la merce semplice si preleva da se'')');

-- 4) la porta: l'UPDATE diretto di una bolla che muove merce e' rifiutato
SELECT throws_like(
    format('UPDATE vendite.ddt SET stato_doc_ddt_id = (SELECT id FROM config.stati_doc_ddt WHERE codice_interno = %L) WHERE id = %s',
           'EMESSO', (SELECT ddt FROM _d1)),
    '%si cambia solo dalle sue operazioni%',
    '4) UPDATE diretto a EMESSO di una bolla che muove merce: E_DOC_STATO_SOLO_DAL_VERBO');

-- 5) il verbo emette
CREATE TEMP TABLE _em1 AS SELECT * FROM vendite.fn_cambia_stato_ddt((SELECT ddt FROM _d1), 'EMESSO');
SELECT is(
    (SELECT string_agg(c.codice_interno || ':' || trim_scale(m.qta)::text, ' ' ORDER BY m.id)
       FROM _em1 e JOIN magazzino.movimenti m ON m.id = e.movimento_id JOIN magazzino.causali c ON c.id = m.causale_id),
    'SCARICO_VEN:-4 SCARICO_VEN:-5 SCARICO_VEN:-3',
    '5) tre scarichi: la SEMPLICE (automatica), poi i due lotti della riga a lotti');

-- 6) il prelievo automatico
SELECT is(
    (SELECT string_agg(trim_scale(p.qta)::text, ',') FROM vendite.ddt_righe_prelievi p WHERE p.ddt_riga_id = (SELECT r_s FROM _d1)),
    '4',
    '6) la SEMPLICE ha il suo prelievo, creato dal verbo, per l''intera quantita''');

-- 7) la provenienza di ogni movimento: la bolla, la riga, il prelievo (rev 2026-11-09, lotto M)
SELECT ok(
    (SELECT bool_and(s.codice_interno = 'DDT_VENDITA' AND m.sorgente_id = (SELECT ddt FROM _d1)
                     AND p.id IS NOT NULL AND p.ddt_riga_id = m.sorgente_riga)
       FROM _em1 e
       JOIN magazzino.movimenti m ON m.id = e.movimento_id
       JOIN config.sorgenti s ON s.id = m.sorgente_tipo_id
       LEFT JOIN vendite.ddt_righe_prelievi p ON p.id = m.sorgente_dettaglio
                                              AND p.ddt_riga_id IN (SELECT r_s FROM _d1 UNION ALL SELECT r_l FROM _d1)),
    '7) ogni scarico nomina la bolla, la riga e il proprio prelievo (D-L3-d; il modello, lotto M)');

-- 8-9) le giacenze
SELECT is(
    (SELECT string_agg(trim_scale(g.qta)::text, ',' ORDER BY a.codice)
       FROM magazzino.vw_giacenza g JOIN catalogo.articoli a ON a.id = g.articolo_id
      WHERE g.magazzino_id = (SELECT mag FROM _fix) AND a.id IN (SELECT art_s FROM _fix UNION ALL SELECT art_l FROM _fix)),
    '4,6',
    '8) giacenze dopo l''emissione: A_LOTTI 4, SEMPLICE 6');
SELECT is(
    (SELECT count(*)::int FROM magazzino.movimenti m WHERE m.articolo_id = (SELECT art_n FROM _fix)),
    0,
    '9) l''articolo non gestito non muove niente');

-- 10) fuori bozza i prelievi sono congelati
SELECT throws_like(
    format('INSERT INTO vendite.ddt_righe_prelievi (ddt_riga_id, qta, lotto_id) VALUES (%s, 1, %s)',
           (SELECT r_l FROM _d1), (SELECT lotto_a FROM _fix)),
    '%non e'' piu'' in bozza%',
    '10) un prelievo su una bolla emessa: E_RIGA_DOC_NON_BOZZA');

-- 11) la bolla n.2: SEMPLICE 100 su una giacenza di 6
CREATE TEMP TABLE _d2 (ddt bigint);
DO $d$
DECLARE v_ddt bigint; v_iva integer;
BEGIN
    SELECT i.id INTO v_iva FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1;
    v_ddt := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                     'VENDITA', (SELECT mag FROM _fix));
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_ddt, 1, art_s, 'troppa', 100, 100, 10, v_iva FROM _fix;
    INSERT INTO _d2 VALUES (v_ddt);
END $d$;
SELECT throws_like(
    format('SELECT * FROM vendite.fn_cambia_stato_ddt(%s, %L)', (SELECT ddt FROM _d2), 'EMESSO'),
    '%disponibili 6, richiesti 100.%',
    '11) oltre la giacenza: il verbo rifiuta prima di emettere');

-- 12-13) la bolla n.3: SEMPLICE 3, sotto un blocco di 5 per un altro cliente
CREATE TEMP TABLE _d3 (ddt bigint, blocco bigint);
DO $d$
DECLARE v_ddt bigint; v_iva integer; v_blocco bigint;
BEGIN
    SELECT i.id INTO v_iva FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1;
    v_blocco := magazzino.fn_apri_blocco((SELECT mag FROM _fix), (SELECT art_s FROM _fix), 5,
                                         (SELECT cliente_soggetto_ruolo_id FROM _m), 'riservata a un altro ordine');
    v_ddt := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                     'VENDITA', (SELECT mag FROM _fix));
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_ddt, 1, art_s, 'sotto blocco', 3, 3, 10, v_iva FROM _fix;
    INSERT INTO _d3 VALUES (v_ddt, v_blocco);
END $d$;
SELECT throws_like(
    format('SELECT * FROM vendite.fn_cambia_stato_ddt(%s, %L)', (SELECT ddt FROM _d3), 'EMESSO'),
    '%bloccati per altri%',
    '12) il blocco di un altro ferma l''emissione (M-3: il blocco e'' un vincolo)');
DO $l$ BEGIN PERFORM magazzino.fn_libera_blocco((SELECT blocco FROM _d3), 'ordine annullato'); END $l$;
SELECT lives_ok(
    format('SELECT * FROM vendite.fn_cambia_stato_ddt(%s, %L)', (SELECT ddt FROM _d3), 'EMESSO'),
    '13) liberato il blocco, la bolla si emette');

-- 14-15) annullo della bolla n.1
CREATE TEMP TABLE _an1 AS SELECT * FROM vendite.fn_cambia_stato_ddt((SELECT ddt FROM _d1), 'ANNULLATO');
SELECT is(
    (SELECT string_agg(c.codice_interno || ':' || trim_scale(m.qta)::text || '@' || trim_scale(m.costo_unitario)::text,
                       ' ' ORDER BY m.qta)
       FROM _an1 a JOIN magazzino.movimenti m ON m.id = a.movimento_id JOIN magazzino.causali c ON c.id = m.causale_id
      WHERE m.storno_di_movimento_id IS NOT NULL),
    'STORNO_POS:3@3 STORNO_POS:4@5 STORNO_POS:5@3',
    '14) annullo: tre storni, al costo dell''originale (M-8)');
SELECT is(
    (SELECT string_agg(trim_scale(g.qta)::text, ',' ORDER BY a.codice)
       FROM magazzino.vw_giacenza g JOIN catalogo.articoli a ON a.id = g.articolo_id
      WHERE g.magazzino_id = (SELECT mag FROM _fix) AND a.id IN (SELECT art_s FROM _fix UNION ALL SELECT art_l FROM _fix)),
    '12,7',
    '15) giacenze dopo l''annullo: A_LOTTI 12, SEMPLICE 7 (6 - 3 della bolla n.3 + 4 stornati)');

-- 16) una bolla che non muove merce: l'UPDATE diretto e' rifiutato anch'esso.
--   ⚠️ Attesa cambiata 2026-10-25 (§7, giro 5): fino al giro 5 passava (porta del registro, D-L3-e);
--   ora la porta sullo stato vale per ogni bolla.
CREATE TEMP TABLE _d4 (ddt bigint);
DO $d$
DECLARE v_ddt bigint; v_iva integer;
BEGIN
    SELECT i.id INTO v_iva FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1;
    v_ddt := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                     'VENDITA', NULL);
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_ddt, 1, art_n, 'solo non gestiti', 1, 1, 10, v_iva FROM _fix;
    INSERT INTO _d4 VALUES (v_ddt);
END $d$;
SELECT throws_like(
    format('UPDATE vendite.ddt SET stato_doc_ddt_id = (SELECT id FROM config.stati_doc_ddt WHERE codice_interno = %L) WHERE id = %s',
           'EMESSO', (SELECT ddt FROM _d4)),
    '%si cambia solo dalle sue operazioni%',
    '16) anche una bolla senza merce da muovere: l''UPDATE diretto e'' rifiutato (E_DOC_STATO_SOLO_DAL_VERBO)');

SELECT * FROM finish();
ROLLBACK;
