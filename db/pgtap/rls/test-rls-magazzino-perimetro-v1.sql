-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   la fixture costruisce DUE aziende e l'operatore di una non deve vedere
--   l'altra: come applicazione non potrebbe nemmeno costruirle.
-- pgTAP test per Zero ERP
--
-- Test: il perimetro RLS del dominio magazzino (M-6), esercitato — non solo
--   dichiarato — su due aziende costruite
--   (brief-db-magazzino-lotto-1-terreno-vuoto, sezioni 4.10 e 7;
--   analisi carico e scarico, sezione 7-sexies).
--
-- ⭐ Il perimetro discende da UN'ancora (magazzini.emittente_fiscale_id) piu'
--   una seconda per gli asset (assets.emittente_fiscale_id): tutto il resto
--   risale — via magazzino, via asset, via testata, via target_id per le
--   note. Questo file lo misura tabella per tabella, cosi' un adattatore
--   sbagliato su una sola non si nasconde dietro le altre.
-- ⚠️ Il PRIMO emittente creato in una fixture e' il DEFAULT: la fixture ne
--   crea DUE, e il contesto e' quello di A (stampo
--   test-rls-billing-account-returning-secondo-emittente).
-- ⚠️ La fixture scrive come owner PRIMA del FORCE: i guard di scope
--   (trgfn_guard_emittente_scope) passano perche' row_security_active e'
--   falsa per l'owner senza FORCE; il guard dei trasferimenti legge
--   magazzini senza RLS. E' cio' che permette di costruire il mondo di B.
--
-- Elenco test (plan 12):
--   La postura:
--    1) le 23 tabelle del perimetro hanno la policy ef_whitelist E la RLS accesa, nessuna forzata
--    2) dbops.vw_rls_perimetro_scoperto per magazzino: zero righe (e la riga 65 del registro non c'e' piu')
--   Il perimetro, esercitato come operatore di A:
--    3) A vede le proprie righe su tutte e 13 le tabelle base
--    4) A NON vede nessuna riga di B su nessuna delle 13
--    5) dal PADRE magazzino.note A vede le sue nove note e nessuna di B (lo smistatore)
--    6) su ciascuna delle nove partizioni: la nota di A si', quella di B no
--    7) l'invariante: nessuna riga visibile la cui testata non lo e' (righe di inventario, rettifica, trasferimento)
--    8) A non puo' scrivere sul magazzino di B (WITH CHECK): un'ubicazione su quel magazzino e' rifiutata
--    9) un trasferimento dal magazzino di A a quello di B e' rifiutato dal guard (il magazzino di B non si vede)
--   Le altre vesti:
--   10) CLIENTE_PORTALE vede zero su tutte e 13 (il magazzino e' interno)
--   11) senza veste: zero su tutte e 13 (fail-closed)
--   Lo smistatore:
--   12) i rami di fn_scope_note_magazzino_ef_perimetro (rev 2026-10-21, 20261021-25) sono esattamente i confini delle
--       partizioni del padre (rev 2026-10-25, grammatica unica lotto 3: il CHECK chk_note_target_tipo e' ritirato, 20261025-56)
-- ------------------------------------------------------------
BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- 1..2 La postura
-- ============================================================
CREATE TEMP TABLE _tabelle (t text) ON COMMIT DROP;
INSERT INTO _tabelle VALUES
    ('magazzini'), ('assets'), ('ubicazioni'), ('movimenti'), ('movimenti_attesi'),
    ('valore_giacenza'), ('inventari'), ('rettifiche'), ('trasferimenti'),
    ('eventi_assets'), ('inventari_righe'), ('rettifiche_righe'), ('trasferimenti_righe'),
    ('note'), ('note_asset'), ('note_evento_asset'), ('note_inventario'),
    ('note_inventario_riga'), ('note_movimento'), ('note_rettifica'),
    ('note_rettifica_riga'), ('note_trasferimento'), ('note_trasferimento_riga');

SELECT is(
    (SELECT count(*)::int FROM _tabelle x
       JOIN pg_class c ON c.relnamespace = 'magazzino'::regnamespace AND c.relname = x.t
       JOIN pg_policies p ON p.schemaname = 'magazzino' AND p.tablename = x.t
                         AND p.policyname = 'rls_' || x.t || '_ef_whitelist'
      WHERE c.relrowsecurity AND NOT c.relforcerowsecurity),
    23,
    '1) le 23 tabelle del perimetro: policy rls_<t>_ef_whitelist, RLS accesa, nessuna forzata');

SELECT is(
    (SELECT count(*)::int FROM dbops.vw_rls_perimetro_scoperto WHERE schema_tabella = 'magazzino')
    + (SELECT count(*)::int FROM dbops.rls_perimetro_debito WHERE schema_tabella = 'magazzino'),
    0,
    '2) vw_rls_perimetro_scoperto per magazzino e'' vuota, e il registro del debito non ha piu'' righe di magazzino');

-- ============================================================
-- Fixture: due aziende, un mondo completo per ciascuna
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'A'::text AS lato, m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;
INSERT INTO _mondi SELECT 'B'::text, m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;
SET CONSTRAINTS ALL IMMEDIATE;

CREATE TEMP TABLE _w (
    lato text, mag bigint, ubi bigint, inv bigint, inv_riga bigint, ret bigint, ret_riga bigint,
    tra bigint, tra_riga bigint, mov bigint, att bigint, asset bigint, evento bigint
);

DO $fix$
DECLARE
    m record;
    v_ind  anagrafiche.indirizzi_dettaglio.id%TYPE;
    v_art  catalogo.articoli.id%TYPE;
    v_tubi config.tipi_ubicazione.id%TYPE;
    v_sta  config.stati_assets.id%TYPE;
    v_own  config.assets_ownership.id%TYPE;
    v_tev  config.tipi_evento_assets.id%TYPE;
    v_cinv magazzino.causali.id%TYPE;
    v_cout magazzino.causali.id%TYPE;
    v_sinv config.sorgenti.id%TYPE;
    r _w%ROWTYPE;
    v_mag2 magazzino.magazzini.id%TYPE;
    v_stile config.note_stili.id%TYPE;
BEGIN
    -- L'indirizzo si FABBRICA (dato di macchina: zero righe su un DB da zero);
    -- i vocabolari sotto sono seed di catalogo, presenti per contratto.
    v_ind := dbops.fn_pgtap_crea_indirizzo_dettaglio('rls');
    SELECT a.id INTO v_art FROM catalogo.articoli a WHERE a.attivo ORDER BY a.id LIMIT 1;
    SELECT t.id INTO v_tubi FROM config.tipi_ubicazione t WHERE t.attivo ORDER BY t.id LIMIT 1;
    SELECT s.id INTO v_sta FROM config.stati_assets s WHERE s.attivo ORDER BY s.id LIMIT 1;
    SELECT o.id INTO v_own FROM config.assets_ownership o WHERE o.attivo ORDER BY o.id LIMIT 1;
    SELECT e.id INTO v_tev FROM config.tipi_evento_assets e WHERE e.attivo ORDER BY e.id LIMIT 1;
    -- Lo stile della nota e' obbligatorio e senza default (20261101-17, come nelle altre note).
    SELECT s.id INTO v_stile FROM config.note_stili s WHERE s.codice_interno = 'NORMALE';
    IF v_art IS NULL OR v_tubi IS NULL OR v_sta IS NULL OR v_own IS NULL OR v_tev IS NULL OR v_stile IS NULL THEN
        RAISE EXCEPTION 'fixture: manca un vocabolario di seed (articolo, tipo ubicazione, stato asset, ownership, tipo evento, stile nota)';
    END IF;
    SELECT id INTO v_cinv FROM magazzino.causali WHERE codice_interno = 'INV_INIZIALE';
    SELECT id INTO v_cout FROM magazzino.causali WHERE codice_interno = 'SCARICO_VEN';
    SELECT id INTO v_sinv FROM config.sorgenti WHERE codice_interno = 'INVENTARIO_RIGA';

    FOR m IN SELECT * FROM _mondi ORDER BY lato LOOP
        r.lato := m.lato;
        r.mag := magazzino.fn_crea_magazzino('PGT-RLS-' || m.lato, 'rls ' || m.lato, v_ind, '{}'::jsonb, m.emittente_fiscale_id);
        v_mag2 := magazzino.fn_crea_magazzino('PGT-RLS-' || m.lato || '2', 'rls ' || m.lato || ' 2', v_ind, '{}'::jsonb, m.emittente_fiscale_id);
        INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id) VALUES (r.mag, 'U-' || m.lato, v_tubi) RETURNING id INTO r.ubi;
        INSERT INTO magazzino.inventari (magazzino_id) VALUES (r.mag) RETURNING id INTO r.inv;
        INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata) VALUES (r.inv, v_art, 5) RETURNING id INTO r.inv_riga;
        INSERT INTO magazzino.rettifiche (magazzino_id) VALUES (r.mag) RETURNING id INTO r.ret;
        INSERT INTO magazzino.rettifiche_righe (rettifica_id, articolo_id, qta_delta) VALUES (r.ret, v_art, -1) RETURNING id INTO r.ret_riga;
        INSERT INTO magazzino.trasferimenti (magazzino_id_from, magazzino_id_to) VALUES (r.mag, v_mag2) RETURNING id INTO r.tra;
        INSERT INTO magazzino.trasferimenti_righe (trasferimento_id, articolo_id, qta) VALUES (r.tra, v_art, 1) RETURNING id INTO r.tra_riga;
        INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, causale_id, qta, sorgente_tipo_id, sorgente_riga, ubicazione_id)
        VALUES (v_art, r.mag, v_cinv, 5, v_sinv, r.inv_riga, r.ubi) RETURNING id INTO r.mov;
        INSERT INTO magazzino.movimenti_attesi (articolo_id, magazzino_id, causale_id, qta, soggetto_ruolo_id)
        VALUES (v_art, r.mag, v_cout, -1, m.soggetto_ruolo_id) RETURNING id INTO r.att;
        INSERT INTO magazzino.valore_giacenza (articolo_id, magazzino_id, valore) VALUES (v_art, r.mag, 50);
        INSERT INTO magazzino.assets (articolo_id, seriale, stato_id, ownership_id, emittente_fiscale_id)
        VALUES (v_art, 'PGT-RLS-SN-' || m.lato, v_sta, v_own, m.emittente_fiscale_id) RETURNING id INTO r.asset;
        INSERT INTO magazzino.eventi_assets (asset_id, tipo_evento_id, magazzino_id_from) VALUES (r.asset, v_tev, r.mag) RETURNING id INTO r.evento;

        -- Una nota per partizione: nelle _riga target_id e' la TESTATA.
        INSERT INTO magazzino.note (target_tipo, target_id, target_riga_id, anchor_tipo, posizione, testo, id_stile) VALUES
            ('ASSET',              r.asset,  NULL,       'DOCUMENTO', 'FOOTER', 'n ' || m.lato, v_stile),
            ('EVENTO_ASSET',       r.evento, NULL,       'DOCUMENTO', 'FOOTER', 'n ' || m.lato, v_stile),
            ('INVENTARIO',         r.inv,    NULL,       'DOCUMENTO', 'FOOTER', 'n ' || m.lato, v_stile),
            ('INVENTARIO_RIGA',    r.inv,    r.inv_riga, 'RIGA',      'AFTER',  'n ' || m.lato, v_stile),
            ('MOVIMENTO',          r.mov,    NULL,       'DOCUMENTO', 'FOOTER', 'n ' || m.lato, v_stile),
            ('RETTIFICA',          r.ret,    NULL,       'DOCUMENTO', 'FOOTER', 'n ' || m.lato, v_stile),
            ('RETTIFICA_RIGA',     r.ret,    r.ret_riga, 'RIGA',      'AFTER',  'n ' || m.lato, v_stile),
            ('TRASFERIMENTO',      r.tra,    NULL,       'DOCUMENTO', 'FOOTER', 'n ' || m.lato, v_stile),
            ('TRASFERIMENTO_RIGA', r.tra,    r.tra_riga, 'RIGA',      'AFTER',  'n ' || m.lato, v_stile);

        INSERT INTO _w SELECT r.*;
    END LOOP;
END $fix$;

-- ============================================================
-- Il perimetro, esercitato: FORCE locale alla transazione su tutte e 23
-- ============================================================
DO $force$ DECLARE t text; BEGIN
    FOR t IN SELECT x.t FROM _tabelle x LOOP
        EXECUTE format('ALTER TABLE magazzino.%I FORCE ROW LEVEL SECURITY', t);
    END LOOP;
END $force$;

CREATE TEMP TABLE _esiti (chiave text, valore text) ON COMMIT DROP;

DO $perimetro$
DECLARE
    a _w%ROWTYPE;
    b _w%ROWTYPE;
    v_user_a integer;
    v_ident_a bigint;
    v_n integer;
    v_ok integer;
    v_zero integer;
    v_tot integer;
    q text;
    -- (tabella, colonna che distingue A da B) per le 13 tabelle base
    v_tab text[][] := ARRAY[
        ['magazzini',           'id'],
        ['assets',              'id'],
        ['ubicazioni',          'id'],
        ['movimenti',           'id'],
        ['movimenti_attesi',    'id'],
        ['valore_giacenza',     'magazzino_id'],
        ['inventari',           'id'],
        ['rettifiche',          'id'],
        ['trasferimenti',       'id'],
        ['eventi_assets',       'id'],
        ['inventari_righe',     'id'],
        ['rettifiche_righe',    'id'],
        ['trasferimenti_righe', 'id']];
    v_key_a bigint[];
    v_key_b bigint[];
    i int;
BEGIN
    SELECT * INTO a FROM _w WHERE lato = 'A';
    SELECT * INTO b FROM _w WHERE lato = 'B';
    SELECT auth_user_id, identita_id INTO v_user_a, v_ident_a FROM _mondi WHERE lato = 'A';
    v_key_a := ARRAY[a.mag, a.asset, a.ubi, a.mov, a.att, a.mag, a.inv, a.ret, a.tra, a.evento, a.inv_riga, a.ret_riga, a.tra_riga];
    v_key_b := ARRAY[b.mag, b.asset, b.ubi, b.mov, b.att, b.mag, b.inv, b.ret, b.tra, b.evento, b.inv_riga, b.ret_riga, b.tra_riga];

    -- ---- l'operatore di A ----
    PERFORM script.fn_pgtap_set_contesto_operatore(v_user_a);

    v_ok := 0; v_zero := 0;
    FOR i IN 1..13 LOOP
        EXECUTE format('SELECT count(*) FROM magazzino.%I WHERE %I = $1', v_tab[i][1], v_tab[i][2]) INTO v_n USING v_key_a[i];
        IF v_n >= 1 THEN v_ok := v_ok + 1; END IF;
        EXECUTE format('SELECT count(*) FROM magazzino.%I WHERE %I = $1', v_tab[i][1], v_tab[i][2]) INTO v_n USING v_key_b[i];
        IF v_n = 0 THEN v_zero := v_zero + 1; END IF;
    END LOOP;
    INSERT INTO _esiti VALUES ('a_vede_sue', v_ok::text), ('a_non_vede_b', v_zero::text);

    -- il PADRE delle note: le nove di A, zero di B
    SELECT count(*) INTO v_n FROM magazzino.note WHERE testo = 'n A';
    INSERT INTO _esiti VALUES ('padre_a', v_n::text);
    SELECT count(*) INTO v_n FROM magazzino.note WHERE testo = 'n B';
    INSERT INTO _esiti VALUES ('padre_b', v_n::text);

    -- le partizioni: per ciascuna, A si' (1) e B no (0)
    v_ok := 0;
    FOR q IN SELECT x.t FROM _tabelle x WHERE x.t LIKE 'note\_%' LOOP
        EXECUTE format('SELECT (SELECT count(*) FROM magazzino.%I WHERE testo = ''n A'') * 10 + (SELECT count(*) FROM magazzino.%I WHERE testo = ''n B'')', q, q) INTO v_n;
        IF v_n = 10 THEN v_ok := v_ok + 1; END IF;
    END LOOP;
    INSERT INTO _esiti VALUES ('partizioni_ok', v_ok::text);

    -- l'invariante: nessuna riga visibile la cui testata non lo e'
    SELECT (SELECT count(*) FROM magazzino.inventari_righe r WHERE NOT EXISTS (SELECT 1 FROM magazzino.inventari t WHERE t.id = r.inventario_id))
         + (SELECT count(*) FROM magazzino.rettifiche_righe r WHERE NOT EXISTS (SELECT 1 FROM magazzino.rettifiche t WHERE t.id = r.rettifica_id))
         + (SELECT count(*) FROM magazzino.trasferimenti_righe r WHERE NOT EXISTS (SELECT 1 FROM magazzino.trasferimenti t WHERE t.id = r.trasferimento_id))
      INTO v_n;
    INSERT INTO _esiti VALUES ('orfane', v_n::text);

    -- scrivere sul magazzino di B: il WITH CHECK
    BEGIN
        INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id)
        VALUES (b.mag, 'INTRUSIONE', (SELECT t.id FROM config.tipi_ubicazione t WHERE t.attivo ORDER BY t.id LIMIT 1));
        INSERT INTO _esiti VALUES ('scrittura_b', 'PASSATA');
    EXCEPTION WHEN insufficient_privilege OR check_violation THEN
        INSERT INTO _esiti VALUES ('scrittura_b', 'RIFIUTATA');
    END;

    -- trasferimento da A a B: il guard (il magazzino di B non si vede -> emittente NULL)
    BEGIN
        INSERT INTO magazzino.trasferimenti (magazzino_id_from, magazzino_id_to) VALUES (a.mag, b.mag);
        INSERT INTO _esiti VALUES ('trasf_a_b', 'PASSATO');
    EXCEPTION WHEN raise_exception THEN
        INSERT INTO _esiti VALUES ('trasf_a_b', 'RIFIUTATO:' || left(SQLERRM, 40));
    WHEN insufficient_privilege OR check_violation THEN
        INSERT INTO _esiti VALUES ('trasf_a_b', 'RIFIUTATO_DALLA_POLICY');
    END;

    -- ---- CLIENTE_PORTALE ----
    PERFORM set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);
    PERFORM set_config('app.current_identita_id', v_ident_a::text, true);
    v_tot := 0;
    FOR i IN 1..13 LOOP
        EXECUTE format('SELECT count(*) FROM magazzino.%I WHERE %I IN ($1, $2)', v_tab[i][1], v_tab[i][2]) INTO v_n USING v_key_a[i], v_key_b[i];
        v_tot := v_tot + v_n;
    END LOOP;
    INSERT INTO _esiti VALUES ('cliente_portale', v_tot::text);

    -- ---- nessuna veste ----
    PERFORM set_config('app.ruolo_applicativo', '', true);
    v_tot := 0;
    FOR i IN 1..13 LOOP
        EXECUTE format('SELECT count(*) FROM magazzino.%I WHERE %I IN ($1, $2)', v_tab[i][1], v_tab[i][2]) INTO v_n USING v_key_a[i], v_key_b[i];
        v_tot := v_tot + v_n;
    END LOOP;
    INSERT INTO _esiti VALUES ('senza_veste', v_tot::text);
END $perimetro$;

DO $noforce$ DECLARE t text; BEGIN
    FOR t IN SELECT x.t FROM _tabelle x LOOP
        EXECUTE format('ALTER TABLE magazzino.%I NO FORCE ROW LEVEL SECURITY', t);
    END LOOP;
END $noforce$;

-- ============================================================
-- 3..11 Le asserzioni
-- ============================================================
SELECT is((SELECT valore FROM _esiti WHERE chiave = 'a_vede_sue'), '13',
          '3) l''operatore di A vede le proprie righe su tutte e 13 le tabelle base');
SELECT is((SELECT valore FROM _esiti WHERE chiave = 'a_non_vede_b'), '13',
          '4) e non vede NESSUNA riga di B su nessuna delle 13');
SELECT is((SELECT valore FROM _esiti WHERE chiave = 'padre_a') || '/' || (SELECT valore FROM _esiti WHERE chiave = 'padre_b'), '9/0',
          '5) dal PADRE magazzino.note: le nove note di A si'', quelle di B no (lo smistatore)');
SELECT is((SELECT valore FROM _esiti WHERE chiave = 'partizioni_ok'), '9',
          '6) su ciascuna delle nove partizioni: la nota di A si'', quella di B no');
SELECT is((SELECT valore FROM _esiti WHERE chiave = 'orfane'), '0',
          '7) nessuna riga visibile la cui testata non lo e'': le righe non sono piu'' permissive delle testate');
SELECT is((SELECT valore FROM _esiti WHERE chiave = 'scrittura_b'), 'RIFIUTATA',
          '8) A non puo'' scrivere sul magazzino di B (WITH CHECK)');
SELECT matches((SELECT valore FROM _esiti WHERE chiave = 'trasf_a_b'), '^RIFIUTATO:',
          '9) un trasferimento dal magazzino di A a quello di B e'' rifiutato dal guard: il magazzino di B non si vede');
SELECT is((SELECT valore FROM _esiti WHERE chiave = 'cliente_portale'), '0',
          '10) CLIENTE_PORTALE vede zero su tutte e 13: il magazzino e'' interno');
SELECT is((SELECT valore FROM _esiti WHERE chiave = 'senza_veste'), '0',
          '11) senza veste applicativa: zero su tutte e 13, fail-closed');

-- ============================================================
-- 12 Lo smistatore
-- ============================================================
SELECT is(
    (WITH rami AS (
        SELECT (regexp_matches(p.prosrc, 'WHEN ''([A-Z_]+)''', 'g'))[1] AS v
          FROM pg_proc p WHERE p.pronamespace = 'script'::regnamespace AND p.proname = 'fn_scope_note_magazzino_ef_perimetro'
     ), chk AS (
        -- i tipi ammessi sono le partizioni (il CHECK e' ritirato, 20261025-56)
        SELECT (regexp_match(pg_get_expr(c.relpartbound, c.oid), $r$IN \('([^']+)'\)$r$))[1] AS v
          FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid
         WHERE i.inhparent = 'magazzino.note'::regclass
     )
     SELECT (SELECT count(*) FROM ((SELECT v FROM rami) EXCEPT (SELECT v FROM chk)) x)
          + (SELECT count(*) FROM ((SELECT v FROM chk) EXCEPT (SELECT v FROM rami)) y)
          -- ⛔ zero partizioni o zero rami non e' «esattamente uguali»: e' verde per sottrazione
          + CASE WHEN NOT EXISTS (SELECT 1 FROM chk) OR NOT EXISTS (SELECT 1 FROM rami) THEN 1 ELSE 0 END),
    0::bigint,
    '12) i rami dello smistatore delle note sono esattamente i confini delle partizioni del padre: un tipo nuovo senza ramo e'' invisibile, non pubblico');

SELECT * FROM finish();
ROLLBACK;
