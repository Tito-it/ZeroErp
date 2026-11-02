-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- pgtap-runner: owner
-- pgtap-runner-motivo: il soggetto e' un orfano CREATO cancellando il
--   bersaglio di un movimento — la riga di un inventario POSTED — che
--   l'applicazione non puo' cancellare (righe congelate, D-L2-h) e che qui si
--   toglie disabilitando i trigger utente: forma 3 del criterio del runner.
--   Il contesto operatore e' impostato comunque (la primitiva e le fixture).
--
-- Test: la spia degli orfani di sorgente (D-9): dbops.fn_sorgenti_orfane,
--   il suo perimetro visibile e la vista. Brief:
--   brief-db-magazzino-lotto-2-motore, sezione 4.7, sezione 7.
--
-- Elenco test (plan 6):
--   1) il PERIMETRO contiene le sei tabelle di magazzino (gemello «esiste»: un presidio che esamina zero tabelle e' verde e muto)
--   2) ...e solo tabelle col guard tipizzato montato (C16: le tabelle di vendite con FK e colonne ma un'altra semantica restano fuori)
--   3) zero orfani sul mondo costruito (per il perimetro di magazzino)
--   4) cancellato il bersaglio di un movimento -> UNA riga: tabella, id, sorgente
--   5) fn_conta_presidio('dbops.vw_sorgenti_orfane') la conta
--   6) la riga in dbops.presidi c'e', con natura ZERO, perimetro DEFINER, cadenza SETTIMANALE
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;
-- Rev 2026-09-24 (brief-db-magazzino-verbi-con-permesso §3.2): fn_posta_inventario e
--   fn_posta_rettifica sono VERBI e applicano registra_magazzino (script.fn_guard_azione);
--   l'operatore di fixture e' tecnico e non ha azioni: il permesso si costruisce qui.
DO $az$ BEGIN PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _mondo), 'registra_magazzino'); END $az$;

CREATE TEMP TABLE _fix (mag bigint, art uuid, inv bigint, riga bigint, mov bigint);
DO $fix$
DECLARE v_mag bigint; v_art uuid; v_inv bigint; v_riga bigint; v_mov bigint;
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-L2X-A', false);
    v_art := dbops.fn_pgtap_crea_articolo('PGT-L2X-ART', true, false, false);
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata) VALUES (v_inv, v_art, 4) RETURNING id INTO v_riga;
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv;
    SELECT movimento_id INTO v_mov FROM magazzino.fn_posta_inventario(v_inv);
    INSERT INTO _fix VALUES (v_mag, v_art, v_inv, v_riga, v_mov);
END $fix$;

SELECT is(
    (SELECT string_agg(tabella::text, ',' ORDER BY tabella::text) FROM dbops.fn_sorgenti_orfane_perimetro() WHERE tabella::text LIKE 'magazzino.%'),
    'magazzino.eventi_assets,magazzino.inventari,magazzino.movimenti,magazzino.movimenti_attesi,magazzino.rettifiche,magazzino.trasferimenti',
    '1) il perimetro contiene le sei tabelle di magazzino');
SELECT is(
    (SELECT count(*) FROM dbops.fn_sorgenti_orfane_perimetro() p
      WHERE NOT EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_proc f ON f.oid = t.tgfoid
                         WHERE t.tgrelid = p.tabella AND f.proname = 'trgfn_guard_sorgente_polimorfa_tipizzata')),
    0::bigint,
    '2) ogni tabella del perimetro porta il guard tipizzato: e'' il guard il contratto del modello A (C16)');
SELECT is(
    (SELECT count(*) FROM dbops.vw_sorgenti_orfane o WHERE o.tabella::text LIKE 'magazzino.%'),
    0::bigint,
    '3) zero orfani di magazzino sul mondo costruito');

-- Il bersaglio sparisce: come owner, coi trigger utente spenti (le righe di una POSTED sono congelate).
ALTER TABLE magazzino.inventari_righe DISABLE TRIGGER USER;
DELETE FROM magazzino.inventari_righe WHERE id = (SELECT riga FROM _fix);
ALTER TABLE magazzino.inventari_righe ENABLE TRIGGER USER;

SELECT is(
    (SELECT (o.tabella::text, o.riga_id, o.sorgente_codice_interno, o.sorgente_riga, o.target_table::text)::text
       FROM dbops.vw_sorgenti_orfane o WHERE o.riga_id = (SELECT mov FROM _fix) AND o.tabella = 'magazzino.movimenti'::regclass),
    (SELECT ('magazzino.movimenti', mov, 'INVENTARIO_RIGA', riga, 'magazzino.inventari_righe')::text FROM _fix),
    '4) cancellato il bersaglio: UNA riga con tabella, id del movimento, sorgente e bersaglio');
SELECT is(
    dbops.fn_conta_presidio('dbops.vw_sorgenti_orfane'),
    1::bigint,
    '5) fn_conta_presidio la conta (perimetro DEFINER: la funzione attraversa la RLS)');
SELECT is(
    (SELECT (natura, perimetro, cadenza, attivo)::text FROM dbops.presidi WHERE vista = 'dbops.vw_sorgenti_orfane'),
    '(ZERO,DEFINER,SETTIMANALE,t)',
    '6) la riga di catalogo: ZERO, DEFINER, SETTIMANALE, attiva');

SELECT * FROM finish();
ROLLBACK;
