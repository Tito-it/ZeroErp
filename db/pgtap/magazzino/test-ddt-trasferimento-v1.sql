-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la bolla di TRASFERIMENTO fra depositi — la merce esce dal
--   magazzino di partenza all'EMESSO e entra in quello di arrivo al
--   CONSEGNATO, con lo stesso transfer_uid e al costo dell'uscita (D-L3-c,
--   D-L2-g). In mezzo e' in viaggio. Una bolla di trasferimento non genera
--   un reso. Brief: brief-db-magazzino-lotto-3-scarico-da-ddt, sezione 3.
-- rev 2026-10-25 (brief-modello-documento-vendita §7, giro 5): ATTESA CAMBIATA del test 8, per regola
--   ritirata: l'UPDATE diretto dello stato e' rifiutato dalla porta comune (E_DOC_STATO_SOLO_DAL_VERBO),
--   non piu' da E_DDT_STATO_SOLO_DA_VERBO («muove merce»).
--
-- Il mondo: due magazzini dello stesso emittente, A e B, senza ubicazioni;
--   un articolo SEMPLICE caricato in A: 10 a 5.
--
-- Elenco test (plan 13):
--    1) arrivo mancante -> fn_check_ddt_merce dice E_DDT_MAGAZZINO_OBBLIGATORIO
--    2) arrivo uguale alla partenza -> E_DDT_MAGAZZINO_INCOERENTE
--    3) arrivo su una bolla di VENDITA -> E_DDT_MAGAZZINO_INCOERENTE
--    4) emissione dal verbo: una sola uscita, TRASF_OUT -4 da A
--    5) ...con transfer_uid = uid della bolla
--    6) in viaggio: A 6, B nessuna giacenza
--    7) SPEDITO dal verbo: nessun movimento
--    8) CONSEGNATO con UPDATE diretto -> E_DOC_STATO_SOLO_DAL_VERBO
--    9) CONSEGNATO dal verbo: TRASF_IN +4 in B, al costo dell'uscita (5)
--   10) giacenze: A 6, B 4
--   11) un reso da una bolla di trasferimento -> E_RESO_DA_DDT_TRASFERIMENTO
--   12) seconda bolla: emessa e annullata da EMESSO -> uno storno, della sola uscita
--   13) ...e la giacenza di A torna a 6
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- Un'azienda NUOVA, non quella dell'operatore di sviluppo: su dbdev quella ha
-- gia' dei magazzini (e forse un predefinito), che falserebbero default e giacenze.
CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
-- Con il contesto aperto, il mondo cliente riusa l'azienda di chi agisce.
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('L3TR');
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'emetti_ddt');
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'registra_magazzino');
END $az$;

CREATE TEMP TABLE _fix (mag_a bigint, mag_b bigint, art uuid);
DO $fix$
DECLARE v_a bigint; v_b bigint; v_art uuid; v_inv bigint;
BEGIN
    v_a   := dbops.fn_pgtap_crea_magazzino('PGT-L3T-A', false);
    v_b   := dbops.fn_pgtap_crea_magazzino('PGT-L3T-B', false);
    v_art := dbops.fn_pgtap_crea_articolo('PGT-L3T-ART', true, false, false);
    INSERT INTO _fix VALUES (v_a, v_b, v_art);
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_a) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, costo_unitario) VALUES (v_inv, v_art, 10, 5);
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv;
    PERFORM magazzino.fn_posta_inventario(v_inv);
END $fix$;

-- La bolla n.1: TRASFERIMENTO da A, arrivo non ancora scelto.
CREATE TEMP TABLE _d1 (ddt bigint, uid uuid);
DO $d$
DECLARE v_ddt bigint;
BEGIN
    v_ddt := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                     'TRASFERIMENTO', (SELECT mag_a FROM _fix));
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita)
    SELECT v_ddt, 1, art, 'da spostare', 4, 4 FROM _fix;
    INSERT INTO _d1 SELECT v_ddt, d.uid FROM vendite.ddt d WHERE d.id = v_ddt;
END $d$;

-- 1) arrivo mancante: e' un motivo dell'emissione, non un rifiuto della bozza
SELECT is(
    (SELECT script.fn_check_ddt_merce(d) -> 0 ->> 'codice' FROM vendite.ddt d WHERE d.id = (SELECT ddt FROM _d1)),
    'E_DDT_MAGAZZINO_OBBLIGATORIO',
    '1) bolla di trasferimento senza arrivo: E_DDT_MAGAZZINO_OBBLIGATORIO');

-- 2) arrivo uguale alla partenza
SELECT throws_like(
    format('UPDATE vendite.ddt SET magazzino_arrivo_id = %s WHERE id = %s', (SELECT mag_a FROM _fix), (SELECT ddt FROM _d1)),
    '%coincide con quello di partenza%',
    '2) arrivo = partenza: E_DDT_MAGAZZINO_INCOERENTE (lo spostamento interno e'' un trasferimento, D-L2-g)');

-- 3) arrivo su una bolla di vendita
CREATE TEMP TABLE _dv (ddt bigint);
DO $d$ BEGIN
    INSERT INTO _dv SELECT dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                                   'VENDITA', (SELECT mag_a FROM _fix));
END $d$;
SELECT throws_like(
    format('UPDATE vendite.ddt SET magazzino_arrivo_id = %s WHERE id = %s', (SELECT mag_b FROM _fix), (SELECT ddt FROM _dv)),
    '%solo una bolla di trasferimento%',
    '3) arrivo su una bolla di vendita: E_DDT_MAGAZZINO_INCOERENTE');

-- 4-5) si sceglie l'arrivo e si emette
UPDATE vendite.ddt SET magazzino_arrivo_id = (SELECT mag_b FROM _fix) WHERE id = (SELECT ddt FROM _d1);
CREATE TEMP TABLE _em1 AS SELECT * FROM vendite.fn_cambia_stato_ddt((SELECT ddt FROM _d1), 'EMESSO');
SELECT is(
    (SELECT string_agg(c.codice_interno || ':' || trim_scale(m.qta)::text || '@' || mg.codice, ' ' ORDER BY m.id)
       FROM _em1 e JOIN magazzino.movimenti m ON m.id = e.movimento_id
       JOIN magazzino.causali c ON c.id = m.causale_id JOIN magazzino.magazzini mg ON mg.id = m.magazzino_id),
    'TRASF_OUT:-4@PGT-L3T-A',
    '4) emissione: una sola uscita, da A');
SELECT is(
    (SELECT m.transfer_uid FROM _em1 e JOIN magazzino.movimenti m ON m.id = e.movimento_id),
    (SELECT uid FROM _d1),
    '5) la coppia si tiene con l''uid della bolla');

-- 6) in viaggio
SELECT is(
    (SELECT ((SELECT trim_scale(g.qta) FROM magazzino.vw_giacenza g
               WHERE g.magazzino_id = (SELECT mag_a FROM _fix) AND g.articolo_id = (SELECT art FROM _fix)),
             (SELECT count(*) FROM magazzino.vw_giacenza g
               WHERE g.magazzino_id = (SELECT mag_b FROM _fix) AND g.articolo_id = (SELECT art FROM _fix)))::text),
    '(6,0)',
    '6) in viaggio: A 6, B nessuna giacenza (la merce non e'' su nessuno scaffale)');

-- 7) SPEDITO
CREATE TEMP TABLE _sp1 AS SELECT * FROM vendite.fn_cambia_stato_ddt((SELECT ddt FROM _d1), 'SPEDITO');
SELECT is((SELECT count(*)::int FROM _sp1), 0, '7) SPEDITO: nessun movimento');

-- 8) CONSEGNATO diretto: la porta
SELECT throws_like(
    format('UPDATE vendite.ddt SET stato_doc_ddt_id = (SELECT id FROM config.stati_doc_ddt WHERE codice_interno = %L) WHERE id = %s',
           'CONSEGNATO', (SELECT ddt FROM _d1)),
    '%si cambia solo dalle sue operazioni%',
    '8) CONSEGNATO con UPDATE diretto di una bolla di trasferimento: E_DOC_STATO_SOLO_DAL_VERBO');

-- 9) CONSEGNATO dal verbo
CREATE TEMP TABLE _co1 AS SELECT * FROM vendite.fn_cambia_stato_ddt((SELECT ddt FROM _d1), 'CONSEGNATO');
SELECT is(
    (SELECT string_agg(c.codice_interno || ':' || trim_scale(m.qta)::text || '@' || mg.codice || '/' || trim_scale(m.costo_unitario)::text,
                       ' ' ORDER BY m.id)
       FROM _co1 e JOIN magazzino.movimenti m ON m.id = e.movimento_id
       JOIN magazzino.causali c ON c.id = m.causale_id JOIN magazzino.magazzini mg ON mg.id = m.magazzino_id),
    'TRASF_IN:4@PGT-L3T-B/5',
    '9) CONSEGNATO: l''entrata in B, al costo dell''uscita');

-- 10) giacenze
SELECT is(
    (SELECT string_agg(mg.codice || '=' || trim_scale(g.qta)::text, ',' ORDER BY mg.codice)
       FROM magazzino.vw_giacenza g JOIN magazzino.magazzini mg ON mg.id = g.magazzino_id
      WHERE g.articolo_id = (SELECT art FROM _fix)),
    'PGT-L3T-A=6,PGT-L3T-B=4',
    '10) giacenze: A 6, B 4');

-- 11) niente reso da una bolla di trasferimento
-- rev 2026-11-09 (brief-db-sorgente-documento-e-riga §7.3, G-3; 20261110-20): la bolla
--   ha chiave id, quindi il reso la porta in sorgente_id e sorgente_uid resta vuota.
--   Con l'uid il guard non trovava la bolla e rispondeva «non CONSEGNATO»: il test
--   non arrivava piu' alla regola del trasferimento.
SELECT throws_like(
    format($q$INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_id,
                                        destinatario_soggetto_ruolo_id, emittente_fiscale_id)
              SELECT (SELECT id FROM config.stati_doc_reso WHERE codice_interno = 'DRAFT'),
                     (SELECT id FROM config.sorgenti WHERE codice_interno = 'DDT_VENDITA'),
                     %s, %s, %s$q$,
           (SELECT ddt FROM _d1), (SELECT cliente_soggetto_ruolo_id FROM _m), (SELECT emittente_fiscale_id FROM _m)),
    '%trasferimento fra depositi%',
    '11) un reso da una bolla di trasferimento: E_RESO_DA_DDT_TRASFERIMENTO');

-- 12-13) seconda bolla: emessa e annullata
CREATE TEMP TABLE _d2 (ddt bigint);
DO $d$
DECLARE v_ddt bigint;
BEGIN
    v_ddt := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                     'TRASFERIMENTO', (SELECT mag_a FROM _fix), (SELECT mag_b FROM _fix));
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita)
    SELECT v_ddt, 1, art, 'ci ripenso', 2, 2 FROM _fix;
    INSERT INTO _d2 VALUES (v_ddt);
    PERFORM vendite.fn_cambia_stato_ddt(v_ddt, 'EMESSO');
END $d$;
CREATE TEMP TABLE _an2 AS SELECT * FROM vendite.fn_cambia_stato_ddt((SELECT ddt FROM _d2), 'ANNULLATO');
SELECT is(
    (SELECT string_agg(c.codice_interno || ':' || trim_scale(m.qta)::text, ' ' ORDER BY m.id)
       FROM _an2 a JOIN magazzino.movimenti m ON m.id = a.movimento_id JOIN magazzino.causali c ON c.id = m.causale_id),
    'STORNO_POS:2',
    '12) annullo da EMESSO: uno storno, della sola uscita (l''entrata non c''e'' ancora)');
SELECT is(
    (SELECT trim_scale(g.qta) FROM magazzino.vw_giacenza g
      WHERE g.magazzino_id = (SELECT mag_a FROM _fix) AND g.articolo_id = (SELECT art FROM _fix)),
    6::numeric,
    '13) ...e A torna a 6');

SELECT * FROM finish();
ROLLBACK;
