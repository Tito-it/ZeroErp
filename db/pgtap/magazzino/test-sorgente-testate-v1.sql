-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le testate di magazzino e l'evento nella grammatica del modello — la
--   provenienza facoltativa e' il tipo del documento, la sua chiave (sorgente_id o
--   sorgente_uid) e, se c'e', la sua riga; la verifica il guard unico.
--   Brief: brief-db-sorgente-documento-e-riga §7.2 lotto M, giro M.2 (§4, scheda
--   magazzino §1.3-1.6).
--
-- Il mondo: un magazzino A e un magazzino B; due bolle in bozza, ciascuna con una riga, e una
--   terza bolla in bozza vuota; un asset. Le testate citano le bolle (DDT_VENDITA, chiave id).
--   ⚠️ La cancellazione dell'origine (15) si prova sulla bolla VUOTA: una bolla con righe la
--   ferma prima la regola «si cancella solo la bozza vuota» (guard di stato, a10, nome minore),
--   e il test asserirebbe la regola sbagliata.
--
-- Elenco test (plan 16):
--    1) le quattro tabelle montano il guard unico, livello DOCUMENTO, azione BLOCCA
--    2) il guard tipizzato del modello A non esiste piu'
--    3) i CHECK di forma *_sorgente_forma ci sono, quelli del modello A no
--    4) gli indici unici residui non ci sono, i dodici «chi deriva da X» si'
--    5) le quattro tabelle stanno nel perimetro con la grammatica UNICO
--    6) un inventario dalla bolla intera: tipo + sorgente_id, riga NULL
--    7) una rettifica da una riga della bolla: tipo + sorgente_id + sorgente_riga
--    8) un trasferimento con la riga di un'altra bolla -> E_SORG_RIGA_NON_DEL_DOCUMENTO
--    9) un evento da una bolla che non c'e' -> E_SORG_NOT_FOUND
--   10) un inventario con l'uid per un tipo a chiave id -> E_SORG_CHIAVE_NON_CONFORME
--   11) un evento dalla riga di una bolla: passa
--   12) la forma: una riga senza tipo -> CHECK (23514)
--   13) un UPDATE della sola sorgente_id verso una bolla che non c'e' -> il guard scatta
--   14) due rettifiche dalla stessa bolla: nessuna unicita' per sorgente
--   15) la bolla vuota citata da un inventario non si cancella -> E_SORG_ORIGINE_REFERENZIATA
--   16) la riga di bolla citata non si cancella -> E_SORG_ORIGINE_REFERENZIATA
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('PGT-STES');

CREATE TEMP TABLE _fix (mag_a bigint, mag_b bigint, art uuid, ddt1 bigint, r1 bigint, ddt2 bigint, r2 bigint,
                        ddt3 bigint, asset bigint, tev bigint, t_ddt bigint);
DO $fix$
DECLARE
    v_a bigint; v_b bigint; v_art uuid; v_d1 bigint; v_d2 bigint; v_d3 bigint; v_r1 bigint; v_r2 bigint;
    v_iva integer; v_sta bigint; v_own bigint; v_tev bigint; v_asset bigint;
BEGIN
    v_a   := dbops.fn_pgtap_crea_magazzino('PGT-STES-A', false);
    v_b   := dbops.fn_pgtap_crea_magazzino('PGT-STES-B', false);
    v_art := dbops.fn_pgtap_crea_articolo('PGT-STES-ART', true, false, false);
    SELECT i.id INTO v_iva FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1;
    SELECT s.id INTO v_sta FROM config.stati_assets s WHERE s.attivo ORDER BY s.id LIMIT 1;
    SELECT o.id INTO v_own FROM config.assets_ownership o WHERE o.attivo ORDER BY o.id LIMIT 1;
    SELECT e.id INTO v_tev FROM config.tipi_evento_assets e WHERE e.attivo ORDER BY e.id LIMIT 1;
    IF v_iva IS NULL OR v_sta IS NULL OR v_own IS NULL OR v_tev IS NULL THEN
        RAISE EXCEPTION 'fixture: manca un vocabolario di seed (iva, stato asset, ownership, tipo evento)';
    END IF;

    v_d1 := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                    'VENDITA', v_a);
    v_d2 := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                    'VENDITA', v_a);
    v_d3 := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                    'VENDITA', v_a);
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    VALUES (v_d1, 1, v_art, 'riga 1', 1, 1, 10, v_iva) RETURNING id INTO v_r1;
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    VALUES (v_d2, 1, v_art, 'riga 2', 1, 1, 10, v_iva) RETURNING id INTO v_r2;

    INSERT INTO magazzino.assets (articolo_id, seriale, stato_id, ownership_id, emittente_fiscale_id)
    VALUES (v_art, 'PGT-STES-SN-1', v_sta, v_own, (SELECT emittente_fiscale_id FROM _az)) RETURNING id INTO v_asset;

    INSERT INTO _fix VALUES (v_a, v_b, v_art, v_d1, v_r1, v_d2, v_r2, v_d3, v_asset, v_tev,
                             (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'DDT_VENDITA'));
END $fix$;

-- ===== la struttura =====
SELECT is(
    (SELECT string_agg(m.nome_tabella::text || ':' || m.livello_minimo || '/' || m.azione_cancellazione, ','
                       ORDER BY m.nome_tabella)
       FROM script.fn_sorgente_guard_montaggi() m
      WHERE m.schema_tabella = 'magazzino'
        AND m.nome_tabella IN ('inventari', 'rettifiche', 'trasferimenti', 'eventi_assets')),
    'eventi_assets:DOCUMENTO/BLOCCA,inventari:DOCUMENTO/BLOCCA,rettifiche:DOCUMENTO/BLOCCA,trasferimenti:DOCUMENTO/BLOCCA',
    '1) le quattro tabelle montano il guard unico, livello DOCUMENTO, azione BLOCCA');

SELECT hasnt_function('script', 'trgfn_guard_sorgente_polimorfa_tipizzata',
    '2) il guard tipizzato del modello A non esiste piu''');

SELECT results_eq(
    $$SELECT c.conname::text COLLATE "default"
        FROM pg_catalog.pg_constraint c
        JOIN pg_catalog.pg_class t     ON t.oid = c.conrelid
        JOIN pg_catalog.pg_namespace n ON n.oid = t.relnamespace
       WHERE n.nspname = 'magazzino'
         AND t.relname IN ('inventari', 'rettifiche', 'trasferimenti', 'eventi_assets')
         AND c.contype = 'c' AND c.conname LIKE 'chk_mag_%_sorgente_%'
       ORDER BY 1$$,
    $$VALUES ('chk_mag_eventi_assets_sorgente_forma'), ('chk_mag_inventari_sorgente_forma'),
             ('chk_mag_rettifiche_sorgente_forma'), ('chk_mag_trasferimenti_sorgente_forma')$$,
    '3) i CHECK di forma *_sorgente_forma ci sono, quelli del modello A (*_sorgente_chiave) no');

SELECT ok(
    to_regclass('magazzino.uq_mag_invetario_sorgente_fk') IS NULL
    AND to_regclass('magazzino.uq_mag_rettifiche_source_fk') IS NULL
    AND to_regclass('magazzino.uq_mag_trasf_sorgente_fk') IS NULL
    AND to_regclass('magazzino.uq_mag_eventi_assets_sorgente_fk') IS NULL
    AND (SELECT count(*) FROM unnest(ARRAY['inventari', 'rettifiche', 'trasferimenti', 'eventi_assets']) t,
                              unnest(ARRAY['id', 'uid', 'riga']) k
          WHERE to_regclass(format('magazzino.ix_mag_%s_sorgente_%s', t, k)) IS NOT NULL) = 12,
    '4) gli indici unici residui (tipo, uid) non ci sono; i dodici indici «chi deriva da X» si''');

SELECT is(
    (SELECT string_agg(p.nome_tabella::text || ':' || p.grammatica, ',' ORDER BY p.nome_tabella)
       FROM dbops.fn_sorgenti_orfane_perimetro() p
      WHERE p.schema_tabella = 'magazzino'
        AND p.nome_tabella IN ('inventari', 'rettifiche', 'trasferimenti', 'eventi_assets')),
    'eventi_assets:UNICO,inventari:UNICO,rettifiche:UNICO,trasferimenti:UNICO',
    '5) le quattro tabelle stanno nel perimetro della provenienza con la grammatica UNICO');

-- ===== le provenienze buone =====
CREATE TEMP TABLE _doc (inv bigint, ret bigint);
DO $d$
DECLARE v_inv bigint; v_ret bigint;
BEGIN
    INSERT INTO magazzino.inventari (magazzino_id, sorgente_tipo_id, sorgente_id)
    SELECT mag_a, t_ddt, ddt1 FROM _fix RETURNING id INTO v_inv;
    INSERT INTO magazzino.rettifiche (magazzino_id, sorgente_tipo_id, sorgente_id, sorgente_riga)
    SELECT mag_a, t_ddt, ddt1, r1 FROM _fix RETURNING id INTO v_ret;
    INSERT INTO _doc VALUES (v_inv, v_ret);
END $d$;

SELECT is(
    (SELECT (i.sorgente_tipo_id = f.t_ddt, i.sorgente_id = f.ddt1, i.sorgente_uid IS NULL, i.sorgente_riga IS NULL)::text
       FROM magazzino.inventari i, _fix f WHERE i.id = (SELECT inv FROM _doc)),
    '(t,t,t,t)',
    '6) un inventario dalla bolla intera: il tipo, la chiave in sorgente_id, nessuna riga');

SELECT is(
    (SELECT (r.sorgente_tipo_id = f.t_ddt, r.sorgente_id = f.ddt1, r.sorgente_riga = f.r1)::text
       FROM magazzino.rettifiche r, _fix f WHERE r.id = (SELECT ret FROM _doc)),
    '(t,t,t)',
    '7) una rettifica da una riga della bolla: il tipo, la bolla, la riga');

-- ===== le provenienze sbagliate =====
SELECT throws_like(
    format($q$INSERT INTO magazzino.trasferimenti (magazzino_id_from, magazzino_id_to, sorgente_tipo_id, sorgente_id, sorgente_riga)
              VALUES (%s, %s, %s, %s, %s)$q$,
           (SELECT mag_a FROM _fix), (SELECT mag_b FROM _fix), (SELECT t_ddt FROM _fix),
           (SELECT ddt1 FROM _fix), (SELECT r2 FROM _fix)),
    '%non è una riga del documento di origine%',
    '8) un trasferimento con la riga di un''altra bolla: E_SORG_RIGA_NON_DEL_DOCUMENTO');

SELECT throws_like(
    format($q$INSERT INTO magazzino.eventi_assets (asset_id, tipo_evento_id, magazzino_id_from, sorgente_tipo_id, sorgente_id)
              VALUES (%s, %s, %s, %s, -1)$q$,
           (SELECT asset FROM _fix), (SELECT tev FROM _fix), (SELECT mag_a FROM _fix), (SELECT t_ddt FROM _fix)),
    '%Riferimento sorgente non trovato%',
    '9) un evento da una bolla che non c''e'': E_SORG_NOT_FOUND');

SELECT throws_like(
    format($q$INSERT INTO magazzino.inventari (magazzino_id, sorgente_tipo_id, sorgente_uid)
              VALUES (%s, %s, '00000000-0000-4000-8000-0000000000aa')$q$,
           (SELECT mag_a FROM _fix), (SELECT t_ddt FROM _fix)),
    '%si scrive con la sola chiave%',
    '10) un inventario con l''uid per un tipo a chiave id: E_SORG_CHIAVE_NON_CONFORME');

SELECT lives_ok(
    format($q$INSERT INTO magazzino.eventi_assets (asset_id, tipo_evento_id, magazzino_id_from, sorgente_tipo_id, sorgente_id, sorgente_riga)
              VALUES (%s, %s, %s, %s, %s, %s)$q$,
           (SELECT asset FROM _fix), (SELECT tev FROM _fix), (SELECT mag_a FROM _fix), (SELECT t_ddt FROM _fix),
           (SELECT ddt2 FROM _fix), (SELECT r2 FROM _fix)),
    '11) un evento dalla riga di una bolla: passa');

SELECT throws_ok(
    format($q$INSERT INTO magazzino.rettifiche (magazzino_id, sorgente_riga) VALUES (%s, %s)$q$,
           (SELECT mag_a FROM _fix), (SELECT r1 FROM _fix)),
    '23514', NULL,
    '12) la forma: una riga senza tipo e senza documento viola chk_mag_rettifiche_sorgente_forma');

-- ⚠️ Un UPDATE che tocca la sola chiave: il trigger la deve avere nel suo elenco OF.
SELECT throws_like(
    format('UPDATE magazzino.inventari SET sorgente_id = -1 WHERE id = %s', (SELECT inv FROM _doc)),
    '%Riferimento sorgente non trovato%',
    '13) un UPDATE della sola sorgente_id verso una bolla che non c''e'': il guard scatta');

SELECT lives_ok(
    format($q$INSERT INTO magazzino.rettifiche (magazzino_id, sorgente_tipo_id, sorgente_id) VALUES (%s, %s, %s)$q$,
           (SELECT mag_a FROM _fix), (SELECT t_ddt FROM _fix), (SELECT ddt1 FROM _fix)),
    '14) una seconda rettifica dalla stessa bolla: nessuna unicita'' per sorgente');

-- ===== S-9: l'origine citata non si cancella (bozze: la regola di stato le lascerebbe) =====
INSERT INTO magazzino.inventari (magazzino_id, sorgente_tipo_id, sorgente_id)
SELECT mag_a, t_ddt, ddt3 FROM _fix;

SELECT throws_like(
    format('DELETE FROM vendite.ddt WHERE id = %s', (SELECT ddt3 FROM _fix)),
    '%dichiarano di nascere da qui%',
    '15) la bolla vuota in bozza citata da un inventario non si cancella: E_SORG_ORIGINE_REFERENZIATA');

SELECT throws_like(
    format('DELETE FROM vendite.ddt_righe WHERE id = %s', (SELECT r2 FROM _fix)),
    '%dichiarano di nascere da qui%',
    '16) la riga di bolla citata da un evento non si cancella: E_SORG_ORIGINE_REFERENZIATA');

SELECT * FROM finish();
ROLLBACK;
