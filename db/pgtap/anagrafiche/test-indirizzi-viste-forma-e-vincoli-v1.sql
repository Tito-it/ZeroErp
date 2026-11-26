-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Gli indirizzi, giro 4 della revisione di anagrafiche (T7a): le viste, la
-- forma di un elemento, la posizione, il tipo, le FK geografiche e la via
-- ritrovata. Decisioni D-T7a-2 … D-T7a-7 (Tid, 2026-11-24).
-- Brief: brief-db-revisione-anagrafiche §21.
--
-- Elenco test (plan 25):
--   la forma degli oggetti
--    1) fn_search_indirizzi_dettaglio e' ritirata (D-T7a-6)
--    2) trgfn_indirizzi_sync_geoloc e' ritirata (D-T7a-3)
--    3) tipi_ruolo_tipi_indirizzo.tipo_ruolo_id e' integer, come
--       config.tipi_ruoli.id (D-T7a-7)
--    4) ... e ha una FK sola
--    5) fn_tipo_indirizzo_ammesso_per_ruolo(integer, integer, date)
--    6) le FK di indirizzi verso comuni, CAP e stati non hanno azione,
--       come quelle di indirizzi_soggetti (S19)
--   S3, la vista resolved
--    7) l'indirizzo libero della forma del catalogo esce una volta sola
--    8) ... col CAP scelto, non con quello di una via del comune
--   S50, la via non risolta (D-T7a-2) e la premessa di S16
--    9) l'INSERT diretto di un civico su una via del comune senza provincia:
--       E_INDIRIZZO_VIA_NON_RISOLTA, non il 23502
--   10) il «trova o crea» sulla stessa via: lo stesso codice (gia' verde)
--   11) la provincia di un comune che lo stradario usa non si toglie
--       (gia' verde: e' la premessa per cui S16 non si produce)
--   S50, la forma di un elemento (D-T7a-5)
--   12) indirizzo_libero vuoto: E_INDIRIZZO_LIBERO_INCOMPLETO
--   13) un elemento col solo tipo: E_INDIRIZZO_LIBERO_INCOMPLETO
--   14) una via nuova senza toponomastica: E_INDIRIZZO_VIA_NUOVA_INCOMPLETA
--   S50, la posizione (D-T7a-3)
--   15) un indirizzo col dettaglio nasce senza una posizione sua
--   16) la vista legge la posizione del civico, anche cambiata dopo
--       (gia' verde)
--   S49, il tipo dell'elemento
--   17) un id che non esiste: E_TIPO_INDIRIZZO_NON_TROVATO, non la FK
--   18) un id non numerico: E_TIPO_INDIRIZZO_NON_TROVATO, non il 22P02
--   19) id e codice che dicono due tipi: E_TIPO_INDIRIZZO_DISCORDE
--   20) il solo codice: passa (controllo)
--   S19, le FK
--   21) cancellare uno stato sotto un indirizzo di ruolo: lo ferma la FK
--   22) cancellare un CAP sotto un indirizzo di ruolo: lo ferma la FK
--   S-T7a-a, la via ritrovata
--   23) la seconda chiamata di fn_create_indirizzo con la stessa via nuova
--       passa
--   24) ... non riscrive la via (il ctid di config.stradario non cambia)
--   25) ... e non lascia versioni di storico della via
--
-- Scopo:
--  - ogni caso si costruisce: comune, CAP, vie, stato e tipi d'indirizzo
--    nascono nel test (le tabelle di config hanno id identity e l'app le
--    scrive), le matrici ammettono i tipi del test sulla natura del
--    soggetto e sul tipo di ruolo. Dal database si leggono solo provincia
--    e toponomastica di seed, la natura del soggetto dal builder;
--  - gira come app.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- I builder del soggetto e del ruolo aprono e richiudono da se' la finestra
-- dei differiti; le scritture del test sono complete istruzione per istruzione.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(25);

-- ============================================================
-- 1-6) La forma degli oggetti
-- ============================================================
SELECT hasnt_function('anagrafiche', 'fn_search_indirizzi_dettaglio',
    '1) fn_search_indirizzi_dettaglio e'' ritirata: la ricerca dei civici e'' del BE');

SELECT hasnt_function('anagrafiche', 'trgfn_indirizzi_sync_geoloc',
    '2) trgfn_indirizzi_sync_geoloc e'' ritirata: la posizione la dice il civico');

SELECT col_type_is('config', 'tipi_ruolo_tipi_indirizzo', 'tipo_ruolo_id', 'integer',
    '3) tipi_ruolo_tipi_indirizzo.tipo_ruolo_id e'' integer, come config.tipi_ruoli.id');

SELECT is(
    (SELECT count(*)::int
       FROM pg_constraint c
       JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
      WHERE c.conrelid = 'config.tipi_ruolo_tipi_indirizzo'::regclass
        AND c.contype = 'f'
        AND a.attname = 'tipo_ruolo_id'),
    1,
    '4) tipo_ruolo_id ha una FK sola verso config.tipi_ruoli');

SELECT has_function('anagrafiche', 'fn_tipo_indirizzo_ammesso_per_ruolo',
    ARRAY['integer', 'integer', 'date'],
    '5) fn_tipo_indirizzo_ammesso_per_ruolo prende il tipo di ruolo integer');

SELECT is(
    (SELECT string_agg(c.conname || '=' || c.confdeltype::text, ',' ORDER BY c.conname)
       FROM pg_constraint c
      WHERE c.conrelid = 'anagrafiche.indirizzi'::regclass
        AND c.contype = 'f'
        AND c.confrelid IN ('config.comuni'::regclass,
                            'config.codici_postali'::regclass,
                            'config.stati'::regclass)),
    'fk_codici_postali_config=a,fk_comuni_config=a,fk_stati_config=a',
    '6) le FK di indirizzi verso comune, CAP e stato non hanno azione, come la gemella');

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _f (k text PRIMARY KEY, v bigint) ON COMMIT DROP;
CREATE TEMP TABLE _s (k text PRIMARY KEY, v uuid)   ON COMMIT DROP;
CREATE TEMP TABLE _t (k text PRIMARY KEY, v text)   ON COMMIT DROP;

DO $fx$
DECLARE
    v_sfx      text := upper(substr(md5(random()::text || clock_timestamp()::text), 1, 8));
    v_prov     config.province.id%TYPE;
    v_topo     config.toponomastica.id%TYPE;
    v_com      config.comuni.id%TYPE;
    v_com0     config.comuni.id%TYPE;
    v_cp1      config.codici_postali.id%TYPE;
    v_cp2      config.codici_postali.id%TYPE;
    v_cpx      config.codici_postali.id%TYPE;
    v_cp0      config.codici_postali.id%TYPE;
    v_g        config.stradario_generale.id%TYPE;
    v_via1     config.stradario.id%TYPE;
    v_via2     config.stradario.id%TYPE;
    v_via0     config.stradario.id%TYPE;
    v_stato_e  config.stati.id%TYPE;
    v_sog      anagrafiche.soggetti.id%TYPE;
    v_natura   anagrafiche.soggetti.tipo_soggetto_dettaglio_id%TYPE;
    v_ruolo    anagrafiche.soggetti_ruoli.id%TYPE;
    v_tipo_r   anagrafiche.soggetti_ruoli.tipo_ruolo_id%TYPE;
    v_tipo     config.tipi_indirizzi.id%TYPE;
    v_i        integer;
BEGIN
    INSERT INTO _t VALUES ('sfx', v_sfx);

    -- Dal seed: una provincia dello stato 1 (quello del builder) e una
    -- toponomastica. Il resto si costruisce.
    SELECT p.id INTO v_prov
      FROM config.province p
      JOIN config.regioni r ON r.id = p.regione_id
     WHERE r.stato_id = 1
     ORDER BY p.id LIMIT 1;
    SELECT t.id INTO v_topo FROM config.toponomastica t ORDER BY t.id LIMIT 1;
    INSERT INTO _f VALUES ('topo', v_topo);

    -- Il comune del test, con tre CAP: due per le due vie, uno che nessuna
    -- via usa (S19).
    INSERT INTO config.comuni (descrizione, provincia_id)
    VALUES ('PGTAP T7A ' || v_sfx, v_prov) RETURNING id INTO v_com;
    INSERT INTO config.codici_postali (codice, comune_id) VALUES ('T7A1' || v_sfx, v_com) RETURNING id INTO v_cp1;
    INSERT INTO config.codici_postali (codice, comune_id) VALUES ('T7A2' || v_sfx, v_com) RETURNING id INTO v_cp2;
    INSERT INTO config.codici_postali (codice, comune_id) VALUES ('T7AX' || v_sfx, v_com) RETURNING id INTO v_cpx;

    -- Due vie del comune, ognuna col suo CAP (S3).
    INSERT INTO config.stradario_generale (toponomastica_id, descrizione, descrizione_breve)
    VALUES (v_topo, 'PGTAP UNO ' || v_sfx, 'PGTAP UNO ' || v_sfx) RETURNING id INTO v_g;
    INSERT INTO config.stradario (stradario_generale_id, comune_id, codice_postale_id)
    VALUES (v_g, v_com, v_cp1) RETURNING id INTO v_via1;
    INSERT INTO config.stradario_generale (toponomastica_id, descrizione, descrizione_breve)
    VALUES (v_topo, 'PGTAP DUE ' || v_sfx, 'PGTAP DUE ' || v_sfx) RETURNING id INTO v_g;
    INSERT INTO config.stradario (stradario_generale_id, comune_id, codice_postale_id)
    VALUES (v_g, v_com, v_cp2) RETURNING id INTO v_via2;

    -- Un comune senza provincia (il modello lo ammette), con una via (S50).
    INSERT INTO config.comuni (descrizione, provincia_id)
    VALUES ('PGTAP T7A SENZA PROV ' || v_sfx, NULL) RETURNING id INTO v_com0;
    INSERT INTO config.codici_postali (codice, comune_id) VALUES ('T7A0' || v_sfx, v_com0) RETURNING id INTO v_cp0;
    INSERT INTO config.stradario_generale (toponomastica_id, descrizione, descrizione_breve)
    VALUES (v_topo, 'PGTAP ZERO ' || v_sfx, 'PGTAP ZERO ' || v_sfx) RETURNING id INTO v_g;
    INSERT INTO config.stradario (stradario_generale_id, comune_id, codice_postale_id)
    VALUES (v_g, v_com0, v_cp0) RETURNING id INTO v_via0;

    -- Uno stato senza il catalogo dei comuni: gli indirizzi esteri (S19).
    INSERT INTO config.stati (descrizione, catalogo_comuni_completo)
    VALUES ('PGTAP T7A ' || v_sfx, false) RETURNING id INTO v_stato_e;

    INSERT INTO _f VALUES ('com', v_com), ('com0', v_com0), ('cp1', v_cp1), ('cp2', v_cp2),
                          ('cpx', v_cpx), ('cp0', v_cp0), ('via1', v_via1), ('via2', v_via2),
                          ('via0', v_via0), ('stato_e', v_stato_e);

    -- Il soggetto (privato dello stato 1) e il suo ruolo cliente, completi
    -- dei loro obbligatori: li scrivono i builder.
    v_sog := dbops.fn_pgtap_crea_soggetto_pf('PgtapT7a' || v_sfx);
    v_ruolo := dbops.fn_pgtap_crea_soggetto_ruolo(v_sog, 'CL');
    SELECT s.tipo_soggetto_dettaglio_id INTO v_natura FROM anagrafiche.soggetti s WHERE s.id = v_sog;
    SELECT sr.tipo_ruolo_id INTO v_tipo_r FROM anagrafiche.soggetti_ruoli sr WHERE sr.id = v_ruolo;
    INSERT INTO _s VALUES ('sog', v_sog);
    INSERT INTO _f VALUES ('ruolo', v_ruolo);

    -- Sei tipi d'indirizzo del test, ammessi dalla natura e dal tipo di
    -- ruolo, nessuno obbligatorio: 1 S3, 2 la posizione, 3 il codice, 4 i
    -- rifiuti, 5 l'estero del ruolo, 6 il CAP del ruolo.
    FOR v_i IN 1..6 LOOP
        INSERT INTO config.tipi_indirizzi (codice_interno, codice, descrizione)
        VALUES ('T' || v_i || substr(v_sfx, 1, 8), 'T7A' || v_i || v_sfx, 'pgTAP T7a tipo ' || v_i)
        RETURNING id INTO v_tipo;
        INSERT INTO config.tipi_soggetto_dettaglio_tipi_indirizzo
               (tipo_soggetto_dettaglio_id, tipo_indirizzo_id, obbligatorio, attivo)
        VALUES (v_natura, v_tipo, false, true);
        INSERT INTO config.tipi_ruolo_tipi_indirizzo
               (tipo_ruolo_id, tipo_indirizzo_id, obbligatorio, attivo)
        VALUES (v_tipo_r, v_tipo, false, true);
        INSERT INTO _f VALUES ('t' || v_i, v_tipo);
    END LOOP;

    -- S3: l'indirizzo libero della forma del catalogo, sul comune del test
    -- col secondo CAP.
    PERFORM anagrafiche.fn_crea_indirizzo_soggetto(v_sog, jsonb_build_object(
        'tipo_indirizzo_id', (SELECT v FROM _f WHERE k = 't1'),
        'indirizzo_libero',  'Via pgTAP S3 1',
        'stato_id',          1,
        'comune_id',         v_com,
        'codice_postale_id', v_cp2));

    -- S19: sul ruolo, un indirizzo estero nello stato del test e uno del
    -- catalogo sul CAP che nessuna via usa.
    PERFORM anagrafiche.fn_crea_indirizzo_ruolo(v_ruolo, jsonb_build_object(
        'tipo_indirizzo_id', (SELECT v FROM _f WHERE k = 't5'),
        'indirizzo_libero',  'Via pgTAP estera 1',
        'stato_id',          v_stato_e,
        'locality',          'Localita pgTAP'));
    PERFORM anagrafiche.fn_crea_indirizzo_ruolo(v_ruolo, jsonb_build_object(
        'tipo_indirizzo_id', (SELECT v FROM _f WHERE k = 't6'),
        'indirizzo_libero',  'Via pgTAP CAP 1',
        'stato_id',          1,
        'comune_id',         v_com,
        'codice_postale_id', v_cpx));
END
$fx$;

-- ============================================================
-- 7-8) S3, la vista resolved
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM anagrafiche.vw_indirizzi_resolved_base r
      WHERE r.scope = 'SOGGETTO'
        AND r.soggetto_id = (SELECT v FROM _s WHERE k = 'sog')
        AND r.tipo_indirizzo_id = (SELECT v FROM _f WHERE k = 't1')),
    1,
    '7) l''indirizzo libero di un comune con due vie esce una volta sola');

SELECT is(
    (SELECT string_agg(DISTINCT r.cap::text, ',')
       FROM anagrafiche.vw_indirizzi_resolved_base r
      WHERE r.scope = 'SOGGETTO'
        AND r.soggetto_id = (SELECT v FROM _s WHERE k = 'sog')
        AND r.tipo_indirizzo_id = (SELECT v FROM _f WHERE k = 't1')),
    (SELECT cp.codice::text FROM config.codici_postali cp WHERE cp.id = (SELECT v FROM _f WHERE k = 'cp2')),
    '8) ... col CAP scelto, non con quello di una via del comune');

-- ============================================================
-- 9-11) S50, la via non risolta; la premessa di S16
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$INSERT INTO anagrafiche.indirizzi_dettaglio (stradario_id, civico) VALUES (%s, 1)$$,
        (SELECT v FROM _f WHERE k = 'via0'))),
    'E_INDIRIZZO_VIA_NON_RISOLTA',
    '9) un civico scritto a mano su una via del comune senza provincia: E_INDIRIZZO_VIA_NON_RISOLTA');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(%s, 1)$$,
        (SELECT v FROM _f WHERE k = 'via0'))),
    'E_INDIRIZZO_VIA_NON_RISOLTA',
    '10) il «trova o crea» sulla stessa via: lo stesso codice');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$UPDATE config.comuni SET provincia_id = NULL WHERE id = %s$$,
        (SELECT v FROM _f WHERE k = 'com'))),
    'E_COLONNA_NON_MODIFICABILE',
    '11) la provincia di un comune che lo stradario usa non si toglie: una via non la perde dopo');

-- ============================================================
-- 12-14) S50, la forma di un elemento
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)$$,
        (SELECT v FROM _s WHERE k = 'sog'),
        jsonb_build_object('tipo_indirizzo_id', (SELECT v FROM _f WHERE k = 't4'),
                           'indirizzo_libero',  ''))),
    'E_INDIRIZZO_LIBERO_INCOMPLETO',
    '12) l''indirizzo libero vuoto: E_INDIRIZZO_LIBERO_INCOMPLETO, dal guard della forma');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)$$,
        (SELECT v FROM _s WHERE k = 'sog'),
        jsonb_build_object('tipo_indirizzo_id', (SELECT v FROM _f WHERE k = 't4')))),
    'E_INDIRIZZO_LIBERO_INCOMPLETO',
    '13) un elemento col solo tipo: E_INDIRIZZO_LIBERO_INCOMPLETO');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)$$,
        (SELECT v FROM _s WHERE k = 'sog'),
        jsonb_build_object('tipo_indirizzo_id', (SELECT v FROM _f WHERE k = 't4'),
                           'descrizione_via',   'PGTAP SENZA TOPONIMO ' || (SELECT v FROM _t WHERE k = 'sfx'),
                           'comune_id',         (SELECT v FROM _f WHERE k = 'com'),
                           'codice_postale_id', (SELECT v FROM _f WHERE k = 'cp1'),
                           'civico',            1))),
    'E_INDIRIZZO_VIA_NUOVA_INCOMPLETA',
    '14) una via nuova senza toponomastica: E_INDIRIZZO_VIA_NUOVA_INCOMPLETA');

-- ============================================================
-- 15-16) S50, la posizione
-- ============================================================
DO $pos$
DECLARE
    v_det anagrafiche.indirizzi_dettaglio.id%TYPE;
BEGIN
    v_det := anagrafiche.fn_get_or_create_indirizzo_dettaglio((SELECT v FROM _f WHERE k = 'via1')::integer, 7);
    UPDATE anagrafiche.indirizzi_dettaglio
       SET civic_geoloc = ST_SetSRID(ST_MakePoint(13.10, 43.10), 4326)
     WHERE id = v_det;
    PERFORM anagrafiche.fn_crea_indirizzo_soggetto((SELECT v FROM _s WHERE k = 'sog'), jsonb_build_object(
        'tipo_indirizzo_id',      (SELECT v FROM _f WHERE k = 't2'),
        'indirizzo_dettaglio_id', v_det));
    INSERT INTO _f VALUES ('det_pos', v_det);
END
$pos$;

SELECT is(
    (SELECT i.geoloc IS NULL
       FROM anagrafiche.indirizzi_soggetti i
      WHERE i.soggetto_id = (SELECT v FROM _s WHERE k = 'sog')
        AND i.tipo_indirizzo_id = (SELECT v FROM _f WHERE k = 't2')),
    true,
    '15) un indirizzo col dettaglio nasce senza una posizione sua: la dice il civico');

UPDATE anagrafiche.indirizzi_dettaglio
   SET civic_geoloc = ST_SetSRID(ST_MakePoint(13.20, 43.20), 4326)
 WHERE id = (SELECT v FROM _f WHERE k = 'det_pos');

SELECT is(
    (SELECT ST_Equals(r.geoloc, ST_SetSRID(ST_MakePoint(13.20, 43.20), 4326))
       FROM anagrafiche.vw_indirizzi_resolved_base r
      WHERE r.scope = 'SOGGETTO'
        AND r.soggetto_id = (SELECT v FROM _s WHERE k = 'sog')
        AND r.tipo_indirizzo_id = (SELECT v FROM _f WHERE k = 't2')),
    true,
    '16) la vista legge la posizione del civico, anche quando cambia dopo');

-- ============================================================
-- 17-20) S49, il tipo dell'elemento
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)$$,
        (SELECT v FROM _s WHERE k = 'sog'),
        jsonb_build_object('tipo_indirizzo_id', 2147483647,
                           'indirizzo_libero',  'Via pgTAP S49 1',
                           'stato_id',          1,
                           'comune_id',         (SELECT v FROM _f WHERE k = 'com'),
                           'codice_postale_id', (SELECT v FROM _f WHERE k = 'cp1')))),
    'E_TIPO_INDIRIZZO_NON_TROVATO',
    '17) un tipo per id che non esiste: E_TIPO_INDIRIZZO_NON_TROVATO, non la FK');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)$$,
        (SELECT v FROM _s WHERE k = 'sog'),
        jsonb_build_object('tipo_indirizzo_id', 'abc',
                           'indirizzo_libero',  'Via pgTAP S49 2',
                           'stato_id',          1,
                           'comune_id',         (SELECT v FROM _f WHERE k = 'com'),
                           'codice_postale_id', (SELECT v FROM _f WHERE k = 'cp1')))),
    'E_TIPO_INDIRIZZO_NON_TROVATO',
    '18) un tipo per id non numerico: E_TIPO_INDIRIZZO_NON_TROVATO, non il 22P02');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)$$,
        (SELECT v FROM _s WHERE k = 'sog'),
        jsonb_build_object('tipo_indirizzo_id',             (SELECT v FROM _f WHERE k = 't4'),
                           'tipo_indirizzo_codice_interno', (SELECT ti.codice_interno FROM config.tipi_indirizzi ti
                                                              WHERE ti.id = (SELECT v FROM _f WHERE k = 't3')),
                           'indirizzo_libero',  'Via pgTAP S49 3',
                           'stato_id',          1,
                           'comune_id',         (SELECT v FROM _f WHERE k = 'com'),
                           'codice_postale_id', (SELECT v FROM _f WHERE k = 'cp1')))),
    'E_TIPO_INDIRIZZO_DISCORDE',
    '19) id e codice che dicono due tipi diversi: E_TIPO_INDIRIZZO_DISCORDE');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)$$,
        (SELECT v FROM _s WHERE k = 'sog'),
        jsonb_build_object('tipo_indirizzo_codice_interno', (SELECT ti.codice_interno FROM config.tipi_indirizzi ti
                                                              WHERE ti.id = (SELECT v FROM _f WHERE k = 't3')),
                           'indirizzo_libero',  'Via pgTAP S49 4',
                           'stato_id',          1,
                           'comune_id',         (SELECT v FROM _f WHERE k = 'com'),
                           'codice_postale_id', (SELECT v FROM _f WHERE k = 'cp1')))),
    NULL,
    '20) il solo codice: passa');

-- ============================================================
-- 21-22) S19, le FK
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$DELETE FROM config.stati WHERE id = %s$$, (SELECT v FROM _f WHERE k = 'stato_e'))),
    'fk_stati_config',
    '21) uno stato sotto un indirizzo di ruolo non si cancella: lo ferma la FK, non riscrive l''indirizzo');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$DELETE FROM config.codici_postali WHERE id = %s$$, (SELECT v FROM _f WHERE k = 'cpx'))),
    'fk_codici_postali_config',
    '22) un CAP sotto un indirizzo di ruolo non si cancella: lo ferma la FK');

-- ============================================================
-- 23-25) S-T7a-a, la via ritrovata
-- ============================================================
-- La prima chiamata crea la via e il civico; si fotografano la riga della
-- via e le sue versioni di storico.
DO $via$
DECLARE
    v_det  anagrafiche.indirizzi_dettaglio.id%TYPE;
    v_via  config.stradario.id%TYPE;
BEGIN
    v_det := anagrafiche.fn_create_indirizzo(
        p_toponomastica_id  := (SELECT v FROM _f WHERE k = 'topo')::integer,
        p_descrizione_via   := 'PGTAP RITROVATA ' || (SELECT v FROM _t WHERE k = 'sfx'),
        p_comune_id         := (SELECT v FROM _f WHERE k = 'com')::integer,
        p_codice_postale_id := (SELECT v FROM _f WHERE k = 'cp1')::integer,
        p_civico            := 3);
    SELECT d.stradario_id INTO v_via FROM anagrafiche.indirizzi_dettaglio d WHERE d.id = v_det;
    INSERT INTO _f VALUES ('via_r', v_via),
                          ('via_r_storico', (SELECT count(*) FROM storico.stradario h WHERE h.stradario_id = v_via));
    INSERT INTO _t VALUES ('via_r_ctid', (SELECT s.ctid::text FROM config.stradario s WHERE s.id = v_via));
END
$via$;

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$SELECT anagrafiche.fn_create_indirizzo(
              p_toponomastica_id  := %s,
              p_descrizione_via   := %L,
              p_comune_id         := %s,
              p_codice_postale_id := %s,
              p_civico            := 3)$$,
        (SELECT v FROM _f WHERE k = 'topo'),
        'PGTAP RITROVATA ' || (SELECT v FROM _t WHERE k = 'sfx'),
        (SELECT v FROM _f WHERE k = 'com'),
        (SELECT v FROM _f WHERE k = 'cp1'))),
    NULL,
    '23) la stessa via nuova, una seconda volta: passa');

SELECT is(
    (SELECT s.ctid::text FROM config.stradario s WHERE s.id = (SELECT v FROM _f WHERE k = 'via_r')),
    (SELECT v FROM _t WHERE k = 'via_r_ctid'),
    '24) ... e la via ritrovata non si riscrive');

SELECT is(
    (SELECT count(*) FROM storico.stradario h WHERE h.stradario_id = (SELECT v FROM _f WHERE k = 'via_r')),
    (SELECT v FROM _f WHERE k = 'via_r_storico'),
    '25) ... e non lascia una versione di storico');

SELECT * FROM finish();
ROLLBACK;
