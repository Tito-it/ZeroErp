-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- pgtap-runner: owner
-- pgtap-runner-motivo: i soggetti sono ORFANI, e un orfano l'applicazione non lo
--   sa produrre: si costruiscono cancellando un bersaglio congelato (la riga di un
--   inventario POSTED) o scrivendo una provenienza a guard spenti, cioe'
--   disabilitando i trigger utente (forma 3 del criterio del runner). Il contesto
--   operatore e' impostato comunque (la primitiva e le fixture).
--
-- Test: la spia degli orfani di sorgente: dbops.fn_sorgenti_orfane, il perimetro
--   della provenienza (dbops.fn_sorgenti_orfane_perimetro) e la vista.
--   Brief: brief-db-magazzino-lotto-2-motore §4.7 (la nascita);
--   brief-db-sorgente-documento-e-riga §7.2 lotto 0, giro 0.2 (il perimetro e i tre
--   livelli, 20261106-20); lotto T, giro T.2 (bolla e reso col guard unico: il caso
--   TESTUALE passa su una tabella del test).
--
-- Elenco test (plan 12):
--   1) il PERIMETRO contiene le sei tabelle di magazzino, con grammatica MODELLO_A
--   2) le testate di vendita sono nel perimetro, tutte col guard unico (UNICO): bolla e reso
--      dal giro T.2, ordine, contratto e fattura dal giro T.3 di brief-db-sorgente-documento-e-riga
--   3) le esenzioni dichiarate sono tre, ognuna col suo motivo
--   4) zero orfani di magazzino sul mondo costruito
--   5) MODELLO_A: cancellato il bersaglio di un movimento -> UNA riga, livello DOCUMENTO
--   6) TESTUALE: una tabella senza guard che nomina un ordine che non c'e' -> UNA riga
--   7) UNICO: una tabella col guard unico entra nel perimetro con la sua grammatica
--   8) UNICO, livello DOCUMENTO: la bolla che non c'e'
--   9) UNICO, livello RIGA: la riga di un'altra bolla
--  10) UNICO, livello DETTAGLIO: il prelievo di un'altra riga
--  11) fn_conta_presidio conta quanto la vista (perimetro DEFINER)
--  12) la riga in dbops.presidi c'e', con natura ZERO, perimetro DEFINER, cadenza SETTIMANALE
-- ⚠️ La convergenza del lato «in uscita» e' idempotente: lo prova
--   script/test-sorgente-in-uscita-v1 (1) dal risultato; qui non si rilancia.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;
-- fn_posta_inventario e fn_posta_rettifica sono VERBI e applicano registra_magazzino
-- (script.fn_guard_azione); l'operatore di fixture e' tecnico e non ha azioni.
DO $az$ BEGIN PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _mondo), 'registra_magazzino'); END $az$;
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('PGT-ORF');

CREATE TEMP TABLE _fix (mag bigint, art uuid, inv bigint, riga bigint, mov bigint, art_l uuid, lotto bigint);
DO $fix$
DECLARE v_mag bigint; v_art uuid; v_inv bigint; v_riga bigint; v_mov bigint; v_art_l uuid; v_lotto bigint;
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-L2X-A', false);
    v_art := dbops.fn_pgtap_crea_articolo('PGT-L2X-ART', true, false, false);
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata) VALUES (v_inv, v_art, 4) RETURNING id INTO v_riga;
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv;
    SELECT movimento_id INTO v_mov FROM magazzino.fn_posta_inventario(v_inv);
    v_art_l := dbops.fn_pgtap_crea_articolo('PGT-ORF-LOTTI', true, true, false);
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo)
    VALUES (v_art_l, 'PGT-ORF-L1', script.fn_data_operativa() - 1) RETURNING id INTO v_lotto;
    INSERT INTO _fix VALUES (v_mag, v_art, v_inv, v_riga, v_mov, v_art_l, v_lotto);
END $fix$;

-- Due bolle in bozza: la prima con due righe e un prelievo sulla riga 1.
CREATE TEMP TABLE _b (ddt1 bigint, r1 bigint, r2 bigint, prel1 bigint, ddt2 bigint, r3 bigint);
DO $b$
DECLARE v_d1 bigint; v_d2 bigint; v_r1 bigint; v_r2 bigint; v_r3 bigint; v_p bigint; v_iva integer;
BEGIN
    SELECT i.id INTO v_iva FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1;
    v_d1 := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                    'VENDITA', (SELECT mag FROM _fix));
    v_d2 := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                    'VENDITA', (SELECT mag FROM _fix));
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_d1, 1, art_l, 'riga 1', 2, 2, 10, v_iva FROM _fix RETURNING id INTO v_r1;
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_d1, 2, art_l, 'riga 2', 1, 1, 10, v_iva FROM _fix RETURNING id INTO v_r2;
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_d2, 1, art_l, 'riga 3', 1, 1, 10, v_iva FROM _fix RETURNING id INTO v_r3;
    INSERT INTO vendite.ddt_righe_prelievi (ddt_riga_id, qta, lotto_id)
    SELECT v_r1, 2, lotto FROM _fix RETURNING id INTO v_p;
    INSERT INTO _b VALUES (v_d1, v_r1, v_r2, v_p, v_d2, v_r3);
END $b$;

CREATE TEMP TABLE _t AS
SELECT (SELECT id FROM config.sorgenti WHERE codice_interno = 'DDT_VENDITA')    AS ddt,
       (SELECT id FROM config.sorgenti WHERE codice_interno = 'ORDINE_VENDITA') AS ord;

-- ===== il perimetro =====
SELECT is(
    (SELECT string_agg(tabella::text || ':' || grammatica, ',' ORDER BY tabella::text)
       FROM dbops.fn_sorgenti_orfane_perimetro() WHERE schema_tabella = 'magazzino'),
    'magazzino.eventi_assets:MODELLO_A,magazzino.inventari:MODELLO_A,magazzino.movimenti:MODELLO_A,'
    'magazzino.movimenti_attesi:MODELLO_A,magazzino.rettifiche:MODELLO_A,magazzino.trasferimenti:MODELLO_A',
    '1) il perimetro contiene le sei tabelle di magazzino, col guard tipizzato (MODELLO_A)');

SELECT is(
    (SELECT string_agg(nome_tabella::text || ':' || grammatica, ',' ORDER BY nome_tabella)
       FROM dbops.fn_sorgenti_orfane_perimetro()
      WHERE schema_tabella = 'vendite' AND nome_tabella IN ('ordini', 'ddt', 'resi', 'contratti', 'fatture')),
    'contratti:UNICO,ddt:UNICO,fatture:UNICO,ordini:UNICO,resi:UNICO',
    '2) le testate di vendita sono nel perimetro, tutte col guard unico (UNICO)');

SELECT results_eq(
    $$SELECT tabella::text COLLATE "default", orfani_esclusi_perche IS NOT NULL, guard_esente_perche IS NOT NULL
        FROM dbops.fn_sorgenti_orfane_perimetro()
       WHERE orfani_esclusi_perche IS NOT NULL OR guard_esente_perche IS NOT NULL
       ORDER BY 1$$,
    $$VALUES ('pratiche.reconcile_errori', true, true),
             ('vendite.attivita_fatturabili', true, false),
             ('vendite.fatture_righe', true, false)$$,
    '3) le esenzioni dichiarate sono tre, ognuna col suo motivo');

SELECT is(
    (SELECT count(*) FROM dbops.vw_sorgenti_orfane o WHERE o.tabella::text LIKE 'magazzino.%'),
    0::bigint,
    '4) zero orfani di magazzino sul mondo costruito');

-- ===== MODELLO_A: il bersaglio sparisce =====
-- Come owner, coi trigger utente spenti: le righe di una POSTED sono congelate, e
-- il lato «in uscita» e' fra i trigger spenti (e' proprio cio' che lascia l'orfano).
ALTER TABLE magazzino.inventari_righe DISABLE TRIGGER USER;
DELETE FROM magazzino.inventari_righe WHERE id = (SELECT riga FROM _fix);
ALTER TABLE magazzino.inventari_righe ENABLE TRIGGER USER;

SELECT is(
    (SELECT (o.tabella::text, o.riga_id, o.grammatica, o.livello, o.sorgente_codice_interno,
             o.sorgente_riga, o.target_table::text)::text
       FROM dbops.vw_sorgenti_orfane o WHERE o.riga_id = (SELECT mov FROM _fix) AND o.tabella = 'magazzino.movimenti'::regclass),
    (SELECT ('magazzino.movimenti', mov, 'MODELLO_A', 'DOCUMENTO', 'INVENTARIO_RIGA', riga,
             'magazzino.inventari_righe')::text FROM _fix),
    '5) MODELLO_A: cancellato il bersaglio, UNA riga con tabella, id, sorgente e bersaglio');

-- ===== TESTUALE: una tabella senza guard nomina un ordine che non c'e' =====
-- Il caso si costruisce su una tabella del test: le testate vere passano al
-- guard unico lotto dopo lotto (la bolla col giro T.2), e il ramo TESTUALE
-- deve restare provato finche' esiste.
CREATE TEMP TABLE _prov_testo (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sorgente_tipo_id bigint, sorgente_uid uuid);
INSERT INTO pg_temp._prov_testo (sorgente_tipo_id, sorgente_uid)
SELECT ord, '00000000-0000-4000-8000-0000000000aa' FROM _t;

SELECT is(
    (SELECT (o.grammatica, o.livello, o.sorgente_codice_interno, o.sorgente_uid, o.target_table::text)::text
       FROM dbops.vw_sorgenti_orfane o WHERE o.tabella = 'pg_temp._prov_testo'::regclass),
    '(TESTUALE,DOCUMENTO,ORDINE_VENDITA,00000000-0000-4000-8000-0000000000aa,vendite.ordini)',
    '6) TESTUALE: la riga senza guard che nomina un ordine inesistente e'' UNA riga orfana');

-- ===== UNICO: una tabella col guard unico, con le provenienze scritte a guard spento =====
CREATE TEMP TABLE _prov (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sorgente_tipo_id bigint, sorgente_id bigint, sorgente_uid uuid,
    sorgente_riga bigint, sorgente_dettaglio bigint, caso text);
CREATE TRIGGER trg_prov_a10_guard_sorgente_ins_upd BEFORE INSERT OR UPDATE ON pg_temp._prov
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA');
ALTER TABLE pg_temp._prov DISABLE TRIGGER USER;
INSERT INTO pg_temp._prov (sorgente_tipo_id, sorgente_id, sorgente_riga, sorgente_dettaglio, caso)
SELECT (SELECT ddt FROM _t), ddt1, r1, prel1, 'buona' FROM _b
UNION ALL SELECT (SELECT ddt FROM _t), -1, NULL, NULL, 'documento' FROM _b
UNION ALL SELECT (SELECT ddt FROM _t), ddt1, r3, NULL, 'riga' FROM _b
UNION ALL SELECT (SELECT ddt FROM _t), ddt1, r2, prel1, 'dettaglio' FROM _b;
ALTER TABLE pg_temp._prov ENABLE TRIGGER USER;

SELECT is(
    (SELECT p.grammatica FROM dbops.fn_sorgenti_orfane_perimetro() p WHERE p.tabella = 'pg_temp._prov'::regclass),
    'UNICO',
    '7) una tabella col guard unico entra nel perimetro con la grammatica UNICO');

SELECT results_eq(
    $$SELECT p.caso, o.livello, o.target_table::text COLLATE "default"
        FROM dbops.vw_sorgenti_orfane o
        JOIN pg_temp._prov p ON p.id = o.riga_id
       WHERE o.tabella = 'pg_temp._prov'::regclass AND p.caso = 'documento'$$,
    $$VALUES ('documento', 'DOCUMENTO', 'vendite.ddt')$$,
    '8) UNICO, livello DOCUMENTO: la bolla che non c''e''');

SELECT results_eq(
    $$SELECT p.caso, o.livello, o.target_table::text COLLATE "default"
        FROM dbops.vw_sorgenti_orfane o
        JOIN pg_temp._prov p ON p.id = o.riga_id
       WHERE o.tabella = 'pg_temp._prov'::regclass AND p.caso = 'riga'$$,
    $$VALUES ('riga', 'RIGA', 'vendite.ddt_righe')$$,
    '9) UNICO, livello RIGA: la riga di un''altra bolla');

SELECT results_eq(
    $$SELECT p.caso, o.livello, o.target_table::text COLLATE "default"
        FROM dbops.vw_sorgenti_orfane o
        JOIN pg_temp._prov p ON p.id = o.riga_id
       WHERE o.tabella = 'pg_temp._prov'::regclass AND p.caso IN ('dettaglio', 'buona')$$,
    $$VALUES ('dettaglio', 'DETTAGLIO', 'vendite.ddt_righe_prelievi')$$,
    '10) UNICO, livello DETTAGLIO: il prelievo di un''altra riga; la provenienza buona non compare');

SELECT ok(
    dbops.fn_conta_presidio('dbops.vw_sorgenti_orfane') = (SELECT count(*) FROM dbops.vw_sorgenti_orfane)
    AND dbops.fn_conta_presidio('dbops.vw_sorgenti_orfane') >= 5,
    '11) fn_conta_presidio conta quanto la vista, e vede gli orfani costruiti (perimetro DEFINER)');
SELECT is(
    (SELECT (natura, perimetro, cadenza, attivo)::text FROM dbops.presidi WHERE vista = 'dbops.vw_sorgenti_orfane'),
    '(ZERO,DEFINER,SETTIMANALE,t)',
    '12) la riga di catalogo: ZERO, DEFINER, SETTIMANALE, attiva');

SELECT * FROM finish();
ROLLBACK;
