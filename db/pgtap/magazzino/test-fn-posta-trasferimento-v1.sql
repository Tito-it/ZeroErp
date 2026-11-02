-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il trasferimento INTERNO — magazzino.fn_posta_trasferimento (D-L2-g):
--   fra due ubicazioni dello stesso magazzino, o fra due magazzini dello
--   stesso emittente, senza trasporto. Per riga una coppia TRASF_OUT /
--   TRASF_IN con il transfer_uid del trasferimento, nello stesso momento
--   (non c'e' merce in viaggio), l'entrata al costo dell'uscita. Il
--   trasferimento entra nella famiglia dei documenti interni: stessa
--   matrice, stessa porta POSTED, righe congelate fuori bozza.
--   Brief: brief-db-magazzino-lotto-3-scarico-da-ddt, sezioni 3 e 4 (P-4, P-10).
--
-- Il mondo: magazzino A con ubicazioni (U1, U2), magazzino B senza, un
--   articolo SEMPLICE caricato in A/U1: 10 a 5.
--
-- Elenco test (plan 10):
--    1) A/U1 -> A/U2, 4 pezzi: TRASF_OUT -4 su U1 e TRASF_IN +4 su U2
--    2) ...con il transfer_uid del trasferimento, e l'entrata al costo dell'uscita
--    3) la testata va a POSTED
--    4) giacenza per ubicazione: U1 6, U2 4; la giacenza di A non cambia (10)
--    5) una riga da U1 a U1 -> 23514 (chk_mag_trasferimenti_righe_ubicazioni_distinte)
--    6) stesso magazzino, riga senza ubicazioni -> E_MAG_TRASFERIMENTO_STESSA_POSIZIONE
--    7) A/U2 -> B, 2 pezzi: uscita da A/U2, entrata in B senza ubicazione
--    8) giacenze: A 8, B 2
--    9) POSTED con UPDATE diretto -> E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE
--   10) una riga su un trasferimento POSTED -> E_MAG_DOCUMENTO_RIGHE_CONGELATE
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
DO $az$ BEGIN PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _az), 'registra_magazzino'); END $az$;

CREATE TEMP TABLE _fix (mag_a bigint, mag_b bigint, u1 bigint, u2 bigint, art uuid);
DO $fix$
DECLARE v_a bigint; v_b bigint; v_u1 bigint; v_u2 bigint; v_art uuid; v_tipo bigint; v_inv bigint;
BEGIN
    SELECT t.id INTO v_tipo FROM config.tipi_ubicazione t WHERE t.attivo ORDER BY t.id LIMIT 1;
    IF v_tipo IS NULL THEN
        RAISE EXCEPTION 'fixture: serve un tipo di ubicazione attivo (seed di catalogo)';
    END IF;
    v_a := dbops.fn_pgtap_crea_magazzino('PGT-L3I-A', true);
    v_b := dbops.fn_pgtap_crea_magazzino('PGT-L3I-B', false);
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id) VALUES (v_a, 'PGT-L3I-U1', v_tipo) RETURNING id INTO v_u1;
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id) VALUES (v_a, 'PGT-L3I-U2', v_tipo) RETURNING id INTO v_u2;
    v_art := dbops.fn_pgtap_crea_articolo('PGT-L3I-ART', true, false, false);
    INSERT INTO _fix VALUES (v_a, v_b, v_u1, v_u2, v_art);
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_a) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, ubicazione_id, qta_contata, costo_unitario)
    VALUES (v_inv, v_art, v_u1, 10, 5);
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv;
    PERFORM magazzino.fn_posta_inventario(v_inv);
END $fix$;

-- 1-4) dentro A, da U1 a U2
CREATE TEMP TABLE _t1 (id bigint, uid uuid);
DO $t$
DECLARE v_id bigint; v_uid uuid;
BEGIN
    INSERT INTO magazzino.trasferimenti (magazzino_id_from, magazzino_id_to)
    SELECT mag_a, mag_a FROM _fix RETURNING id, uid INTO v_id, v_uid;
    INSERT INTO magazzino.trasferimenti_righe (trasferimento_id, articolo_id, qta, ubicazione_id_da, ubicazione_id_a)
    SELECT v_id, art, 4, u1, u2 FROM _fix;
    UPDATE magazzino.trasferimenti SET stato_trasferimento = 'CONFIRM' WHERE id = v_id;
    INSERT INTO _t1 VALUES (v_id, v_uid);
END $t$;
CREATE TEMP TABLE _p1 AS SELECT * FROM magazzino.fn_posta_trasferimento((SELECT id FROM _t1));
SELECT is(
    (SELECT string_agg(c.codice_interno || ':' || trim_scale(m.qta)::text || '@' || u.codice, ' ' ORDER BY m.id)
       FROM _p1 p JOIN magazzino.movimenti m ON m.id = p.movimento_id
       JOIN magazzino.causali c ON c.id = m.causale_id JOIN magazzino.ubicazioni u ON u.id = m.ubicazione_id),
    'TRASF_OUT:-4@PGT-L3I-U1 TRASF_IN:4@PGT-L3I-U2',
    '1) una coppia per riga: uscita da U1, entrata in U2');
SELECT ok(
    (SELECT bool_and(m.transfer_uid = (SELECT uid FROM _t1) AND m.costo_unitario = 5)
       FROM _p1 p JOIN magazzino.movimenti m ON m.id = p.movimento_id),
    '2) la coppia si tiene col transfer_uid del trasferimento, l''entrata al costo dell''uscita');
SELECT is(
    (SELECT stato_trasferimento FROM magazzino.trasferimenti WHERE id = (SELECT id FROM _t1))::text,
    'POSTED',
    '3) la testata e'' POSTED');
SELECT is(
    (SELECT string_agg(u.codice || '=' || trim_scale(g.qta)::text, ',' ORDER BY u.codice)
       FROM magazzino.vw_giacenza_ubicazione g JOIN magazzino.ubicazioni u ON u.id = g.ubicazione_id
      WHERE g.articolo_id = (SELECT art FROM _fix))
    || ' A=' || (SELECT trim_scale(g.qta)::text FROM magazzino.vw_giacenza g
                  WHERE g.magazzino_id = (SELECT mag_a FROM _fix) AND g.articolo_id = (SELECT art FROM _fix)),
    'PGT-L3I-U1=6,PGT-L3I-U2=4 A=10',
    '4) per ubicazione U1 6 e U2 4; il magazzino resta a 10');

-- 5-6) stesso magazzino, stessa posizione
CREATE TEMP TABLE _t2 (id bigint);
DO $t$
DECLARE v_id bigint;
BEGIN
    INSERT INTO magazzino.trasferimenti (magazzino_id_from, magazzino_id_to)
    SELECT mag_a, mag_a FROM _fix RETURNING id INTO v_id;
    INSERT INTO _t2 VALUES (v_id);
END $t$;
SELECT throws_ok(
    format('INSERT INTO magazzino.trasferimenti_righe (trasferimento_id, articolo_id, qta, ubicazione_id_da, ubicazione_id_a) VALUES (%s, %L, 1, %s, %s)',
           (SELECT id FROM _t2), (SELECT art FROM _fix), (SELECT u1 FROM _fix), (SELECT u1 FROM _fix)),
    '23514', NULL,
    '5) una riga da U1 a U1: il CHECK la rifiuta');
DO $t$ BEGIN
    INSERT INTO magazzino.trasferimenti_righe (trasferimento_id, articolo_id, qta)
    SELECT (SELECT id FROM _t2), art, 1 FROM _fix;
    UPDATE magazzino.trasferimenti SET stato_trasferimento = 'CONFIRM' WHERE id = (SELECT id FROM _t2);
END $t$;
SELECT throws_like(
    format('SELECT * FROM magazzino.fn_posta_trasferimento(%s)', (SELECT id FROM _t2)),
    '%partenza e arrivo coincidono%',
    '6) stesso magazzino senza due ubicazioni: E_MAG_TRASFERIMENTO_STESSA_POSIZIONE');

-- 7-8) da A/U2 a B
CREATE TEMP TABLE _t3 (id bigint);
DO $t$
DECLARE v_id bigint;
BEGIN
    INSERT INTO magazzino.trasferimenti (magazzino_id_from, magazzino_id_to)
    SELECT mag_a, mag_b FROM _fix RETURNING id INTO v_id;
    INSERT INTO magazzino.trasferimenti_righe (trasferimento_id, articolo_id, qta, ubicazione_id_da)
    SELECT v_id, art, 2, u2 FROM _fix;
    UPDATE magazzino.trasferimenti SET stato_trasferimento = 'CONFIRM' WHERE id = v_id;
    INSERT INTO _t3 VALUES (v_id);
END $t$;
CREATE TEMP TABLE _p3 AS SELECT * FROM magazzino.fn_posta_trasferimento((SELECT id FROM _t3));
SELECT is(
    (SELECT string_agg(c.codice_interno || ':' || mg.codice || '/' || COALESCE(u.codice, '-'), ' ' ORDER BY m.id)
       FROM _p3 p JOIN magazzino.movimenti m ON m.id = p.movimento_id
       JOIN magazzino.causali c ON c.id = m.causale_id JOIN magazzino.magazzini mg ON mg.id = m.magazzino_id
       LEFT JOIN magazzino.ubicazioni u ON u.id = m.ubicazione_id),
    'TRASF_OUT:PGT-L3I-A/PGT-L3I-U2 TRASF_IN:PGT-L3I-B/-',
    '7) fra due magazzini: uscita da A/U2, entrata in B (che non usa ubicazioni)');
SELECT is(
    (SELECT string_agg(mg.codice || '=' || trim_scale(g.qta)::text, ',' ORDER BY mg.codice)
       FROM magazzino.vw_giacenza g JOIN magazzino.magazzini mg ON mg.id = g.magazzino_id
      WHERE g.articolo_id = (SELECT art FROM _fix)),
    'PGT-L3I-A=8,PGT-L3I-B=2',
    '8) giacenze: A 8, B 2');

-- 9-10) la famiglia dei documenti interni
CREATE TEMP TABLE _t4 (id bigint);
DO $t$
DECLARE v_id bigint;
BEGIN
    INSERT INTO magazzino.trasferimenti (magazzino_id_from, magazzino_id_to)
    SELECT mag_a, mag_b FROM _fix RETURNING id INTO v_id;
    INSERT INTO magazzino.trasferimenti_righe (trasferimento_id, articolo_id, qta, ubicazione_id_da)
    SELECT v_id, art, 1, u2 FROM _fix;
    UPDATE magazzino.trasferimenti SET stato_trasferimento = 'CONFIRM' WHERE id = v_id;
    INSERT INTO _t4 VALUES (v_id);
END $t$;
SELECT throws_like(
    format('UPDATE magazzino.trasferimenti SET stato_trasferimento = %L WHERE id = %s', 'POSTED', (SELECT id FROM _t4)),
    '%passa dall''operazione di registrazione%',
    '9) POSTED con UPDATE diretto: E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE');
SELECT throws_like(
    format('INSERT INTO magazzino.trasferimenti_righe (trasferimento_id, articolo_id, qta, ubicazione_id_da) VALUES (%s, %L, 1, %s)',
           (SELECT id FROM _t3), (SELECT art FROM _fix), (SELECT u2 FROM _fix)),
    '%POSTED%',
    '10) una riga su un trasferimento POSTED: E_MAG_DOCUMENTO_RIGHE_CONGELATE');

SELECT * FROM finish();
ROLLBACK;
