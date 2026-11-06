-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la merce rientra col reso — il verbo vendite.fn_conferma_reso fa
--   rientrare cio' che era USCITO con la bolla: un carico per RIENTRO, che
--   punta al prelievo d'origine (D-3b-b, D-3b-d), al costo dell'uscita
--   (D-3b-e), nel magazzino del reso (D-3b-a); il rientro della merce semplice
--   lo crea da se'; il tetto per prelievo somma i resi della bolla; l'annullo
--   di un reso confermato storna; la porta del registro chiude l'UPDATE
--   diretto; il permesso e' conferma_reso (D-3b-f).
--   Brief: brief-db-magazzino-lotto-3-bis-carico-da-reso, sezioni 3 e 5.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): i resi in bozza dal builder dbops.fn_pgtap_crea_reso (piu' righe con p_reso_id); restano scritti a mano il reso senza righe (6b, il caso), i rientri, le conferme e l'annullo dal verbo, che sono il caso del file.
-- rev 2026-10-25 (brief-modello-documento-vendita §7, giro 5): ATTESA CAMBIATA del test 7 (n.11), per regola
--   ritirata: l'UPDATE diretto dello stato e' rifiutato dalla porta comune (E_DOC_STATO_SOLO_DAL_VERBO),
--   non piu' da E_RESO_STATO_SOLO_DA_VERBO («fa rientrare merce»).
--
-- Il mondo: due magazzini senza ubicazioni (MAG, e QUA per i «resi da
--   verificare»), tre articoli costruiti — SEMPLICE (gestito), A_LOTTI
--   (gestito, requires_lotto), NON_GESTITO — caricati con un inventario:
--   SEMPLICE 10 a 5, A_LOTTI 6 nel lotto A e 6 nel B a 3. Una bolla di
--   VENDITA da MAG, emessa e consegnata: SEMPLICE 4 (prelievo automatico),
--   A_LOTTI 8 (A 5, B 3), NON_GESTITO 2.
--
-- Elenco test (plan 29):
--    1) il reso nasce col magazzino della bolla d'origine (default, D-3b-a)
--    2) le voci: SEMPLICE automatica, A_LOTTI no (due prelievi), NON_GESTITO nessuna
--    3) senza rientri sulla riga a lotti -> fn_check_reso_merce: E_RESO_RIENTRI_INCOMPLETI
--    4) ...e la capability spegne «Conferma» con lo stesso motivo
--   4a) ...e porta `reasons`: l'array della check, intero (una sede)
--   4b) ...coi `valori` della frase: riga 2, 0 indicati su 4
--       (brief-db-reso-motivi-conferma-con-valori)
--    5) un rientro che nomina il prelievo di un'altra riga -> E_RESO_RIENTRO_INCOERENTE
--    6) rientri completi (A 3, B 1) -> nessun motivo
--   6a) ...e la «Conferma» e' accesa, con `reasons` null
--   6b) PRESIDIO: un reso senza righe -> DOCUMENTO_SENZA_RIGHE e `reasons` null.
--       Oggi verde anche senza la precedenza scritta (la check della merce con
--       zero righe non parla): diventa rosso il giorno che l'incastro si rompe
--    7) UPDATE diretto a CONFERMATO di un reso che muove merce -> E_DOC_STATO_SOLO_DAL_VERBO
--    8) senza l'azione conferma_reso il verbo rifiuta -> E_PERMESSO_NEGATO
--    9) il verbo conferma: tre carichi CARICO_RESO_VEN (SEMPLICE 2, lotto A 3, lotto B 1)
--   10) il rientro automatico della SEMPLICE esiste, per la quantita' resa
--   11) ogni carico ha per sorgente il suo rientro (RESO_VENDITA_RIENTRO)
--   12) ogni carico ha il costo della sua uscita (5 e 3), non la media di oggi
--   13) giacenze in MAG dopo la conferma: A_LOTTI 8, SEMPLICE 8
--   14) la NON_GESTITO non rientra
--   15) rientri congelati dopo la conferma -> E_RIGA_DOC_NON_BOZZA
--   16) magazzino congelato dopo la conferma -> E_RESO_MAGAZZINO_IMMUTABILE
--   17) il presidio dbops.vw_resi_confermati_senza_carico non vede il reso
--   18) un secondo reso sul lotto A oltre l'uscito -> E_RESO_RIENTRO_OLTRE_USCITO
--   19) ...e il verbo rifiuta, senza confermare
--   20) corretto e spostato in QUA in bozza: il carico va in QUA (A 2, B 2)
--   21) annullo del primo reso: tre storni, al costo del carico
--   22) giacenze in MAG dopo l'annullo: A_LOTTI 4, SEMPLICE 6
--   23) un reso da una bolla che non ha mosso merce non muove merce
--   24) l'app non esegue il posting del reso (riservato)
--   25) una riga di un reso confermato non si tocca piu' -> E_RIGA_DOC_NON_BOZZA (D-3b-h)
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(29);

-- Il mondo: un'azienda NUOVA (su dbdev quella dell'operatore ha gia' magazzini).
CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('L3BR');
-- Emettere la bolla chiede emetti_ddt, l'inventario registra_magazzino, il
-- reso conferma_reso: l'operatore di fixture non ha azioni.
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'emetti_ddt');
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'registra_magazzino');
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'conferma_reso');
END $az$;

CREATE TEMP TABLE _fix (mag bigint, qua bigint, art_s uuid, art_l uuid, art_n uuid, lotto_a bigint, lotto_b bigint,
                        sorgente_ddt bigint);
DO $fix$
DECLARE
    v_mag bigint; v_qua bigint; v_s uuid; v_l uuid; v_n uuid; v_la bigint; v_lb bigint; v_inv bigint;
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-L3B-MAG', false);
    v_qua := dbops.fn_pgtap_crea_magazzino('PGT-L3B-QUA', false);
    v_s   := dbops.fn_pgtap_crea_articolo('PGT-L3B-SEMPLICE', true,  false, false);
    v_l   := dbops.fn_pgtap_crea_articolo('PGT-L3B-A-LOTTI',  true,  true,  false);
    v_n   := dbops.fn_pgtap_crea_articolo('PGT-L3B-NON-GEST', false, false, false);
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo) VALUES (v_l, 'PGT-L3B-A', script.fn_data_operativa() - 10) RETURNING id INTO v_la;
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo) VALUES (v_l, 'PGT-L3B-B', script.fn_data_operativa() - 5)  RETURNING id INTO v_lb;
    INSERT INTO _fix
    SELECT v_mag, v_qua, v_s, v_l, v_n, v_la, v_lb,
           (SELECT so.id FROM config.sorgenti so WHERE so.codice_interno = 'DDT_VENDITA');

    -- Il carico: SEMPLICE 10 a 5, A_LOTTI 6+6 a 3.
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, costo_unitario) VALUES (v_inv, v_s, 10, 5);
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, lotto_id, qta_contata, costo_unitario) VALUES (v_inv, v_l, v_la, 6, 3);
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, lotto_id, qta_contata, costo_unitario) VALUES (v_inv, v_l, v_lb, 6, 3);
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv;
    PERFORM magazzino.fn_posta_inventario(v_inv);
END $fix$;

-- La bolla: SEMPLICE 4, A_LOTTI 8 (A 5, B 3), NON_GESTITO 2 — emessa e consegnata.
CREATE TEMP TABLE _d (ddt bigint, r_s bigint, r_l bigint, r_n bigint, p_s bigint, p_la bigint, p_lb bigint);
DO $d$
DECLARE v_ddt bigint; v_rs bigint; v_rl bigint; v_rn bigint; v_iva integer; v_pla bigint; v_plb bigint;
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
    INSERT INTO vendite.ddt_righe_prelievi (ddt_riga_id, qta, lotto_id) SELECT v_rl, 5, lotto_a FROM _fix RETURNING id INTO v_pla;
    INSERT INTO vendite.ddt_righe_prelievi (ddt_riga_id, qta, lotto_id) SELECT v_rl, 3, lotto_b FROM _fix RETURNING id INTO v_plb;
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_ddt, 'EMESSO');
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_ddt, 'SPEDITO');
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_ddt, 'CONSEGNATO');
    INSERT INTO _d
    SELECT v_ddt, v_rs, v_rl, v_rn,
           (SELECT p.id FROM vendite.ddt_righe_prelievi p WHERE p.ddt_riga_id = v_rs), v_pla, v_plb;
END $d$;

-- Il reso n.1, a credito, in bozza dal builder: SEMPLICE 2, A_LOTTI 4,
-- NON_GESTITO 1 (righe 1, 2, 3). La conferma e' il passo del test (9).
CREATE TEMP TABLE _r1 (reso bigint, rr_s bigint, rr_l bigint, rr_n bigint);
DO $r$
DECLARE v_reso bigint; v_s bigint; v_l bigint; v_n bigint;
BEGIN
    SELECT b.reso_id, b.resi_riga_id INTO v_reso, v_s
      FROM dbops.fn_pgtap_crea_reso('L3BR', (SELECT ddt FROM _d), 2, p_stato_codice_interno => 'DRAFT',
                                    p_ddt_riga_id => (SELECT r_s FROM _d)) b;
    SELECT b.resi_riga_id INTO v_l
      FROM dbops.fn_pgtap_crea_reso('L3BR', NULL, 4, p_stato_codice_interno => 'DRAFT',
                                    p_ddt_riga_id => (SELECT r_l FROM _d), p_reso_id => v_reso) b;
    SELECT b.resi_riga_id INTO v_n
      FROM dbops.fn_pgtap_crea_reso('L3BR', NULL, 1, p_stato_codice_interno => 'DRAFT',
                                    p_ddt_riga_id => (SELECT r_n FROM _d), p_reso_id => v_reso) b;
    INSERT INTO _r1 VALUES (v_reso, v_s, v_l, v_n);
END $r$;

-- 1) il default
SELECT is(
    (SELECT r.magazzino_id FROM vendite.resi r WHERE r.id = (SELECT reso FROM _r1)),
    (SELECT mag FROM _fix),
    '1) il reso nasce col magazzino da cui era partita la bolla (D-3b-a)');

-- 2) le voci
SELECT is(
    (SELECT string_agg(m.riga_nr || ':' || m.n_prelievi || ':' || m.automatico, ' ' ORDER BY m.riga_nr)
       FROM vendite.resi r, vendite.fn_reso_merce_da_rientrare(r) m
      WHERE r.id = (SELECT reso FROM _r1)),
    '1:1:true 2:2:false',
    '2) voci: SEMPLICE automatica, A_LOTTI con due prelievi da scegliere, NON_GESTITO non rientra');

-- 3-4) la riga a lotti chiede la scelta
SELECT is(
    (SELECT script.fn_check_reso_merce(r) -> 0 ->> 'codice' FROM vendite.resi r WHERE r.id = (SELECT reso FROM _r1)),
    'E_RESO_RIENTRI_INCOMPLETI',
    '3) senza rientri sulla riga a lotti: la check della merce lo dice');
SELECT is(
    (SELECT a ->> 'reason'
       FROM jsonb_array_elements(script.fn_available_actions_reso((SELECT reso FROM _r1)) -> 'available_actions') a
      WHERE a ->> 'target_state' = 'CONFERMATO'),
    'RIENTRI_INCOMPLETI',
    '4) ...e la capability spegne «Conferma» con lo stesso motivo (una sede)');
SELECT is(
    (SELECT a -> 'reasons'
       FROM jsonb_array_elements(script.fn_available_actions_reso((SELECT reso FROM _r1)) -> 'available_actions') a
      WHERE a ->> 'target_state' = 'CONFERMATO'),
    (SELECT script.fn_check_reso_merce(r) FROM vendite.resi r WHERE r.id = (SELECT reso FROM _r1)),
    '4a) ...e porta `reasons`: l''array della check, intero (la forma della bolla)');
SELECT is(
    (SELECT a -> 'reasons' -> 0 -> 'valori'
       FROM jsonb_array_elements(script.fn_available_actions_reso((SELECT reso FROM _r1)) -> 'available_actions') a
      WHERE a ->> 'target_state' = 'CONFERMATO'),
    '["2", "0", "4"]'::jsonb,
    '4b) ...coi valori della frase «Riga {0} del reso: indicati {1} pezzi su {2}»: riga 2, 0 su 4');

-- 5) il prelievo di un'altra riga
SELECT throws_like(
    format('INSERT INTO vendite.resi_righe_rientri (resi_riga_id, ddt_riga_prelievo_id, qta) VALUES (%s, %s, 1)',
           (SELECT rr_l FROM _r1), (SELECT p_s FROM _d)),
    '%Rientro non valido sulla riga 2%',
    '5) un rientro che nomina il prelievo di un''altra riga: E_RESO_RIENTRO_INCOERENTE');

-- 6) completati
INSERT INTO vendite.resi_righe_rientri (resi_riga_id, ddt_riga_prelievo_id, qta)
SELECT rr_l, p_la, 3 FROM _r1, _d UNION ALL SELECT rr_l, p_lb, 1 FROM _r1, _d;
SELECT is(
    (SELECT script.fn_check_reso_merce(r) FROM vendite.resi r WHERE r.id = (SELECT reso FROM _r1)),
    '[]'::jsonb,
    '6) rientri completi: nessun motivo (la SEMPLICE rientra da se'')');
SELECT is(
    (SELECT (a ->> 'enabled') || ':' || jsonb_typeof(a -> 'reasons')
       FROM jsonb_array_elements(script.fn_available_actions_reso((SELECT reso FROM _r1)) -> 'available_actions') a
      WHERE a ->> 'target_state' = 'CONFERMATO'),
    'true:null',
    '6a) ...e la «Conferma» e'' accesa, con `reasons` presente e null');

-- 6b) PRESIDIO della precedenza: un reso senza righe sulla stessa bolla.
--   Scritto a mano: il builder nasce sempre con una riga, e qui la riga che
--   manca e' il caso.
CREATE TEMP TABLE _r0 (reso bigint);
DO $r0$
DECLARE v_reso bigint;
BEGIN
    INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_id, storicizza)
    SELECT (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno = 'DRAFT'),
           f.sorgente_ddt, (SELECT ddt FROM _d), false
      FROM _fix f RETURNING id INTO v_reso;
    INSERT INTO _r0 VALUES (v_reso);
END $r0$;
SELECT is(
    (SELECT (a ->> 'reason') || ':' || jsonb_typeof(a -> 'reasons')
       FROM jsonb_array_elements(script.fn_available_actions_reso((SELECT reso FROM _r0)) -> 'available_actions') a
      WHERE a ->> 'target_state' = 'CONFERMATO'),
    'DOCUMENTO_SENZA_RIGHE:null',
    '6b) PRESIDIO: reso senza righe -> DOCUMENTO_SENZA_RIGHE, e `reasons` null (la merce non parla prima delle righe)');

-- 7) la porta
SELECT throws_like(
    format('UPDATE vendite.resi SET stato_doc_reso_id = (SELECT id FROM config.stati_doc_reso WHERE codice_interno = %L) WHERE id = %s',
           'CONFERMATO', (SELECT reso FROM _r1)),
    '%si cambia solo dalle sue operazioni%',
    '7) UPDATE diretto a CONFERMATO di un reso che muove merce: E_DOC_STATO_SOLO_DAL_VERBO');

-- 8) il permesso: tolto l'override, il verbo rifiuta
UPDATE config.user_override_azioni SET abilitata = false
 WHERE auth_user_id = (SELECT auth_user_id FROM _m)
   AND azione_id = (SELECT ap.id FROM config.azioni_processo ap WHERE ap.permission_codename = 'conferma_reso');
SELECT throws_like(
    format('SELECT vendite.fn_conferma_reso(%s)', (SELECT reso FROM _r1)),
    '%Non hai i permessi%',
    '8) senza l''azione conferma_reso il verbo rifiuta (E_PERMESSO_NEGATO)');
UPDATE config.user_override_azioni SET abilitata = true
 WHERE auth_user_id = (SELECT auth_user_id FROM _m)
   AND azione_id = (SELECT ap.id FROM config.azioni_processo ap WHERE ap.permission_codename = 'conferma_reso');

-- 9) il verbo conferma
SELECT vendite.fn_conferma_reso((SELECT reso FROM _r1));
CREATE TEMP TABLE _car1 AS
SELECT m.*
  FROM magazzino.movimenti m
  JOIN config.sorgenti so ON so.id = m.sorgente_tipo_id AND so.codice_interno = 'RESO_VENDITA_RIENTRO'
  JOIN vendite.resi_righe_rientri x ON x.id = m.sorgente_riga
  JOIN vendite.resi_righe rr ON rr.id = x.resi_riga_id
 WHERE rr.reso_id = (SELECT reso FROM _r1);
SELECT is(
    (SELECT string_agg(c.codice_interno || ':' || trim_scale(k.qta)::text, ' ' ORDER BY k.qta DESC, k.id)
       FROM _car1 k JOIN magazzino.causali c ON c.id = k.causale_id),
    'CARICO_RESO_VEN:3 CARICO_RESO_VEN:2 CARICO_RESO_VEN:1',
    '9) tre carichi: lotto A 3, SEMPLICE 2 (automatica), lotto B 1');

-- 10) il rientro automatico
SELECT is(
    (SELECT string_agg(trim_scale(x.qta)::text, ',') FROM vendite.resi_righe_rientri x WHERE x.resi_riga_id = (SELECT rr_s FROM _r1)),
    '2',
    '10) la SEMPLICE ha il suo rientro, creato dal verbo, per la quantita'' resa');

-- 11) sorgente = rientro
SELECT is(
    (SELECT count(*)::int FROM _car1),
    (SELECT count(*)::int FROM vendite.resi_righe_rientri x JOIN vendite.resi_righe rr ON rr.id = x.resi_riga_id
      WHERE rr.reso_id = (SELECT reso FROM _r1)),
    '11) un carico per rientro, e ogni carico nomina il suo (D-3b-d)');

-- 12) il costo dell'uscita
SELECT is(
    (SELECT string_agg(a.codice || '=' || trim_scale(k.costo_unitario)::text, ' ' ORDER BY a.codice, k.id)
       FROM _car1 k JOIN catalogo.articoli a ON a.id = k.articolo_id),
    'PGT-L3B-A-LOTTI=3 PGT-L3B-A-LOTTI=3 PGT-L3B-SEMPLICE=5',
    '12) ogni carico al costo della sua uscita d''origine (D-3b-e)');

-- 13-14) le giacenze
SELECT is(
    (SELECT string_agg(trim_scale(g.qta)::text, ',' ORDER BY a.codice)
       FROM magazzino.vw_giacenza g JOIN catalogo.articoli a ON a.id = g.articolo_id
      WHERE g.magazzino_id = (SELECT mag FROM _fix) AND a.id IN (SELECT art_s FROM _fix UNION ALL SELECT art_l FROM _fix)),
    '8,8',
    '13) giacenze dopo la conferma: A_LOTTI 4+4, SEMPLICE 6+2');
SELECT is(
    (SELECT count(*)::int FROM magazzino.movimenti m WHERE m.articolo_id = (SELECT art_n FROM _fix)),
    0,
    '14) l''articolo non gestito non rientra');

-- 15-16) dopo la conferma
SELECT throws_like(
    format('INSERT INTO vendite.resi_righe_rientri (resi_riga_id, ddt_riga_prelievo_id, qta) VALUES (%s, %s, 1)',
           (SELECT rr_l FROM _r1), (SELECT p_la FROM _d)),
    '%non e'' piu'' in bozza%',
    '15) un rientro su un reso confermato: E_RIGA_DOC_NON_BOZZA');
SELECT throws_like(
    format('UPDATE vendite.resi SET magazzino_id = %s WHERE id = %s', (SELECT qua FROM _fix), (SELECT reso FROM _r1)),
    '%si sceglie solo in bozza%',
    '16) il magazzino di un reso confermato non cambia: E_RESO_MAGAZZINO_IMMUTABILE');

-- 17) il presidio
SELECT ok(
    NOT EXISTS (SELECT 1 FROM dbops.vw_resi_confermati_senza_carico v WHERE v.reso_id = (SELECT reso FROM _r1)),
    '17) il presidio non vede il reso: ha il suo carico');

-- 18-19) il reso n.2 sulla stessa bolla: A_LOTTI 4, di cui 3 dal lotto A (2 soli rimasti)
CREATE TEMP TABLE _r2 (reso bigint, rr_l bigint);
DO $r$
DECLARE v_reso bigint; v_l bigint;
BEGIN
    SELECT b.reso_id, b.resi_riga_id INTO v_reso, v_l
      FROM dbops.fn_pgtap_crea_reso('L3BR', (SELECT ddt FROM _d), 4, p_stato_codice_interno => 'DRAFT',
                                    p_ddt_riga_id => (SELECT r_l FROM _d)) b;
    INSERT INTO vendite.resi_righe_rientri (resi_riga_id, ddt_riga_prelievo_id, qta)
    SELECT v_l, p_la, 3 FROM _d UNION ALL SELECT v_l, p_lb, 1 FROM _d;
    INSERT INTO _r2 VALUES (v_reso, v_l);
END $r$;
SELECT is(
    (SELECT script.fn_check_reso_merce(r) -> 0 ->> 'codice' FROM vendite.resi r WHERE r.id = (SELECT reso FROM _r2)),
    'E_RESO_RIENTRO_OLTRE_USCITO',
    '18) dal lotto A rientrerebbero 6 pezzi su 5 usciti: E_RESO_RIENTRO_OLTRE_USCITO');
SELECT throws_like(
    format('SELECT vendite.fn_conferma_reso(%s)', (SELECT reso FROM _r2)),
    '%ne erano usciti 5%',
    '19) ...e il verbo rifiuta prima di confermare');

-- 20) corretto (A 2, B 2) e spostato in bozza nel magazzino dei resi da verificare
UPDATE vendite.resi_righe_rientri SET qta = 2 WHERE resi_riga_id = (SELECT rr_l FROM _r2);
UPDATE vendite.resi SET magazzino_id = (SELECT qua FROM _fix) WHERE id = (SELECT reso FROM _r2);
SELECT vendite.fn_conferma_reso((SELECT reso FROM _r2));
SELECT is(
    (SELECT string_agg(l.codice || ':' || trim_scale(g.qta)::text, ',' ORDER BY l.codice)
       FROM magazzino.movimenti g JOIN magazzino.lotti l ON l.id = g.lotto_id
      WHERE g.magazzino_id = (SELECT qua FROM _fix)),
    'PGT-L3B-A:2,PGT-L3B-B:2',
    '20) il magazzino scelto in bozza vince: la merce rientra in QUA, lotto per lotto');

-- 21-22) l'annullo del reso n.1 storna
SELECT vendite.fn_annulla_reso((SELECT reso FROM _r1));
SELECT is(
    (SELECT string_agg(c.codice_interno || ':' || trim_scale(s.qta)::text || '@' || trim_scale(s.costo_unitario)::text,
                       ' ' ORDER BY s.qta, s.id)
       FROM magazzino.movimenti s
       JOIN magazzino.causali c ON c.id = s.causale_id
      WHERE s.storno_di_movimento_id IN (SELECT id FROM _car1)),
    'STORNO_NEG:-3@3 STORNO_NEG:-2@5 STORNO_NEG:-1@3',
    '21) annullo del reso confermato: tre storni, al costo del carico (M-8)');
SELECT is(
    (SELECT string_agg(trim_scale(g.qta)::text, ',' ORDER BY a.codice)
       FROM magazzino.vw_giacenza g JOIN catalogo.articoli a ON a.id = g.articolo_id
      WHERE g.magazzino_id = (SELECT mag FROM _fix) AND a.id IN (SELECT art_s FROM _fix UNION ALL SELECT art_l FROM _fix)),
    '4,6',
    '22) giacenze in MAG dopo l''annullo: A_LOTTI 4, SEMPLICE 6 (come dopo la bolla)');

-- 23) un reso da una bolla che non ha mosso merce
CREATE TEMP TABLE _d9 (ddt bigint, reso bigint);
DO $d$
DECLARE v_ddt bigint; v_rn bigint; v_iva integer; v_reso bigint;
BEGIN
    SELECT i.id INTO v_iva FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1;
    v_ddt := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                     'VENDITA', (SELECT mag FROM _fix));
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_ddt, 1, art_n, 'solo servizio', 2, 2, 10, v_iva FROM _fix RETURNING id INTO v_rn;
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_ddt, 'EMESSO');
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_ddt, 'SPEDITO');
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt(v_ddt, 'CONSEGNATO');
    SELECT b.reso_id INTO v_reso
      FROM dbops.fn_pgtap_crea_reso('L3BR', v_ddt, 1, p_stato_codice_interno => 'DRAFT', p_ddt_riga_id => v_rn) b;
    INSERT INTO _d9 VALUES (v_ddt, v_reso);
END $d$;
SELECT ok(
    (SELECT NOT vendite.fn_reso_muove_merce(r) FROM vendite.resi r WHERE r.id = (SELECT reso FROM _d9)),
    '23) un reso da una bolla che non ha mosso merce non ne fa rientrare');

-- 24) la postura
SELECT ok(
    NOT has_function_privilege('zeroerp_app', 'vendite.fn_posta_reso(bigint)', 'EXECUTE'),
    '24) l''app non esegue il posting del reso: ci arriva solo dal verbo');

-- 25) le righe del reso confermato sono congelate (D-3b-h): il carico e' scritto
SELECT throws_like(
    format('UPDATE vendite.resi_righe SET qta_operativa = 3 WHERE id = %s', (SELECT rr_l FROM _r2)),
    '%non e'' piu'' in bozza%',
    '25) una riga di un reso confermato non cambia: E_RIGA_DOC_NON_BOZZA');

SELECT * FROM finish();
ROLLBACK;
