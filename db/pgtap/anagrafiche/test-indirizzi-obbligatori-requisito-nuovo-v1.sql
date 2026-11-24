-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Gli indirizzi obbligatori, giro 4 della revisione di anagrafiche (T7a).
--   D-T7a-1 (Tid, 2026-11-24): una matrice che cambia vale per le scritture
--   che toccano il requisito, come per i tipi ammessi. Il titolare si giudica
--   alla nascita e al cambio di natura; dal lato degli indirizzi si giudica
--   la riga che esce, non tutto il titolare.
--   D-T7a-4 (Tid, 2026-11-24): «obbligatorio per la natura» ha una sede sola,
--   il ripiego del soggetto conta solo se la natura lo ammette, e la copia
--   degli obbligatori non copia un tipo il cui ripiego c'e' gia'.
-- Brief: brief-db-revisione-anagrafiche §21.
--
-- Elenco test (plan 11):
--   la sede
--    1) anagrafiche.fn_tipo_indirizzo_obbligatorio_per_natura esiste
--    2) e' l'unica funzione che legge «obbligatorio» dalla matrice della
--       natura (presidio sul testo dei corpi)
--   D-T7a-1, il soggetto (una riga obbligatoria nuova, che non ha)
--    3) una scrittura su un'altra colonna passa
--    4) cancellare un indirizzo che nessuna riga chiede passa
--    5) cancellare l'unico indirizzo di una riga obbligatoria: rifiutato
--       (controllo, gia' verde)
--   D-T7a-1, il ruolo (una riga obbligatoria nuova, che non ha)
--    6) una scrittura su un'altra colonna passa
--    7) cancellare un indirizzo che nessuna riga chiede passa
--   D-T7a-4, il ripiego
--    8) un ripiego che la natura vieta non si propone: il mancante ha il
--       ripiego vuoto
--    9) la copia degli obbligatori non copia il tipo quando nell'elenco
--       c'e' il suo ripiego
--   10) ... il ripiego si scrive (controllo)
--   11) ... e il tipo senza ripiego si copia (controllo)
--
-- Scopo:
--  - i tipi d'indirizzo e le righe di matrice sono del test (id identity,
--    l'app scrive le matrici): il requisito nuovo nasce DOPO il titolare,
--    che e' il controesempio di partenza della S48;
--  - gira come app.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- I builder del soggetto e del ruolo aprono e richiudono da se' la finestra
-- dei differiti; con IMMEDIATE i constraint trigger differiti scattano a fine
-- istruzione, ed e' li' che le asserzioni li leggono.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- 1-2) La sede
-- ============================================================
SELECT has_function('anagrafiche', 'fn_tipo_indirizzo_obbligatorio_per_natura',
    ARRAY['bigint', 'integer', 'date'],
    '1) fn_tipo_indirizzo_obbligatorio_per_natura(natura, tipo, giorno) esiste');

SELECT is(
    (SELECT string_agg(DISTINCT n.nspname || '.' || p.proname, ', '
                       ORDER BY n.nspname || '.' || p.proname)
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname IN ('anagrafiche', 'script', 'dbops', 'config')
        AND p.prokind = 'f'
        AND pg_get_functiondef(p.oid) ~ 'tipi_soggetto_dettaglio_tipi_indirizzo'
        AND pg_get_functiondef(p.oid) ~ '\.obbligatorio\M'),
    'anagrafiche.fn_tipo_indirizzo_obbligatorio_per_natura',
    '2) solo la sede legge «obbligatorio» dalla matrice della natura');

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _f (k text PRIMARY KEY, v bigint) ON COMMIT DROP;
CREATE TEMP TABLE _s (k text PRIMARY KEY, v uuid)   ON COMMIT DROP;

DO $fx$
DECLARE
    v_sfx     text := upper(substr(md5(random()::text || clock_timestamp()::text), 1, 8));
    v_natura  config.tipi_soggetto_dettaglio.id%TYPE;
    v_tipo_r  config.tipi_ruoli.id%TYPE;
    v_sog     anagrafiche.soggetti.id%TYPE;
    v_ruolo   anagrafiche.soggetti_ruoli.id%TYPE;
    v_tipo    config.tipi_indirizzi.id%TYPE;
    v_k       text;
    v_n       bigint;   -- l'ordinale del tipo nell'elenco: niente da ancorare
    v_forma   jsonb;
BEGIN
    -- La natura e il tipo di ruolo sono quelli dei builder: il privato dello
    -- stato 1 e il cliente.
    SELECT d.id INTO v_natura FROM config.tipi_soggetto_dettaglio d
     WHERE d.codice_interno = 'PR' AND d.stato_id = 1;
    SELECT t.id INTO v_tipo_r FROM config.tipi_ruoli t WHERE t.codice_interno = 'CL';

    -- Sette tipi del test:
    --   td  obbligatorio per la natura da PRIMA del soggetto (il controllo 5)
    --   tb  ammesso, non chiesto (4)       tbr ammesso sul ruolo, non chiesto (7)
    --   ta  chiesto DOPO, col ripiego tf, che la natura vieta (3, 8)
    --   tf  nessuna riga per la natura: vietato
    --   tc  chiesto DOPO, col ripiego tr, ammesso (9-11)
    --   tar chiesto DOPO dal ruolo (6)
    FOR v_k, v_n IN
        SELECT u.k, u.n FROM unnest(ARRAY['td', 'tb', 'tbr', 'ta', 'tf', 'tc', 'tr', 'tar'])
                             WITH ORDINALITY AS u(k, n)
    LOOP
        -- codice_interno: 10 caratteri, «O» + il numero + il suffisso
        INSERT INTO config.tipi_indirizzi (codice_interno, codice, descrizione)
        VALUES ('O' || v_n || v_sfx, 'T7AO' || v_n || v_sfx, 'pgTAP T7a ' || v_k)
        RETURNING id INTO v_tipo;
        INSERT INTO _f VALUES (v_k, v_tipo);
    END LOOP;

    -- Prima del soggetto: td obbligatorio, e le righe «ammesso» della natura
    -- per tb, tbr, tr, tar.
    INSERT INTO config.tipi_soggetto_dettaglio_tipi_indirizzo
           (tipo_soggetto_dettaglio_id, tipo_indirizzo_id, obbligatorio, attivo)
    SELECT v_natura, f.v, f.k = 'td', true
      FROM _f f WHERE f.k IN ('td', 'tb', 'tbr', 'tr', 'tar');
    INSERT INTO config.tipi_ruolo_tipi_indirizzo
           (tipo_ruolo_id, tipo_indirizzo_id, obbligatorio, attivo)
    SELECT v_tipo_r, f.v, false, true
      FROM _f f WHERE f.k IN ('tbr', 'tar');

    -- Il soggetto e il ruolo, completi dei loro obbligatori di oggi: td lo
    -- copia la madre.
    v_sog   := dbops.fn_pgtap_crea_soggetto_pf('PgtapT7aObb' || v_sfx);
    v_ruolo := dbops.fn_pgtap_crea_soggetto_ruolo(v_sog, 'CL');
    INSERT INTO _s VALUES ('sog', v_sog);
    INSERT INTO _f VALUES ('ruolo', v_ruolo), ('natura', v_natura);

    -- Un indirizzo che nessuno chiede, sul soggetto e sul ruolo.
    SELECT jsonb_strip_nulls(to_jsonb(f)) INTO v_forma FROM dbops.fn_pgtap_indirizzo_libero_forma(1) f;
    PERFORM anagrafiche.fn_crea_indirizzo_soggetto(v_sog,
        v_forma || jsonb_build_object('tipo_indirizzo_id', (SELECT v FROM _f WHERE k = 'tb'),
                                      'indirizzo_libero', 'Via pgTAP non chiesto 1',
                                      'stato_id', 1));
    PERFORM anagrafiche.fn_crea_indirizzo_ruolo(v_ruolo,
        v_forma || jsonb_build_object('tipo_indirizzo_id', (SELECT v FROM _f WHERE k = 'tbr'),
                                      'indirizzo_libero', 'Via pgTAP non chiesto 2',
                                      'stato_id', 1));

    -- ⭐ Il controesempio: i requisiti nuovi nascono DOPO i titolari.
    INSERT INTO config.tipi_soggetto_dettaglio_tipi_indirizzo
           (tipo_soggetto_dettaglio_id, tipo_indirizzo_id, obbligatorio, attivo, fallback_tipo_indirizzo_id)
    VALUES (v_natura, (SELECT v FROM _f WHERE k = 'ta'), true, true, (SELECT v FROM _f WHERE k = 'tf')),
           (v_natura, (SELECT v FROM _f WHERE k = 'tc'), true, true, (SELECT v FROM _f WHERE k = 'tr'));
    UPDATE config.tipi_ruolo_tipi_indirizzo
       SET obbligatorio = true
     WHERE tipo_ruolo_id = v_tipo_r
       AND tipo_indirizzo_id = (SELECT v FROM _f WHERE k = 'tar');
END
$fx$;

-- ============================================================
-- 3-5) D-T7a-1, il soggetto
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$UPDATE anagrafiche.soggetti SET titolo_cortesia_id = titolo_cortesia_id WHERE id = %L::uuid$$,
        (SELECT v FROM _s WHERE k = 'sog'))),
    NULL,
    '3) un soggetto a cui una riga nuova chiede un indirizzo si scrive ancora, su un''altra colonna');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$DELETE FROM anagrafiche.indirizzi_soggetti WHERE soggetto_id = %L::uuid AND tipo_indirizzo_id = %s$$,
        (SELECT v FROM _s WHERE k = 'sog'), (SELECT v FROM _f WHERE k = 'tb'))),
    NULL,
    '4) ... e perde un indirizzo che nessuna riga chiede');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$DELETE FROM anagrafiche.indirizzi_soggetti WHERE soggetto_id = %L::uuid AND tipo_indirizzo_id = %s$$,
        (SELECT v FROM _s WHERE k = 'sog'), (SELECT v FROM _f WHERE k = 'td'))),
    'E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO',
    '5) l''unico indirizzo di una riga obbligatoria non si cancella');

-- ============================================================
-- 6-7) D-T7a-1, il ruolo
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$UPDATE anagrafiche.soggetti_ruoli SET meta = meta WHERE id = %s$$,
        (SELECT v FROM _f WHERE k = 'ruolo'))),
    NULL,
    '6) un ruolo a cui una riga nuova chiede un indirizzo si scrive ancora');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$DELETE FROM anagrafiche.indirizzi WHERE soggetto_ruolo_id = %s AND tipo_indirizzo_id = %s$$,
        (SELECT v FROM _f WHERE k = 'ruolo'), (SELECT v FROM _f WHERE k = 'tbr'))),
    NULL,
    '7) ... e perde un indirizzo che nessuna riga chiede');

-- ============================================================
-- 8-11) D-T7a-4, il ripiego
-- ============================================================
SELECT is(
    (SELECT m.ripiego_tipo_indirizzo_id
       FROM anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto(
                (SELECT v FROM _s WHERE k = 'sog'),
                (SELECT v FROM _f WHERE k = 'natura'),
                script.fn_data_operativa()) m
      WHERE m.tipo_indirizzo_id = (SELECT v FROM _f WHERE k = 'ta')),
    NULL::integer,
    '8) un ripiego che la natura vieta non si propone');

SELECT anagrafiche.fn_crea_indirizzi_soggetto(
    (SELECT v FROM _s WHERE k = 'sog'),
    jsonb_build_array(
        (SELECT jsonb_strip_nulls(to_jsonb(f)) FROM dbops.fn_pgtap_indirizzo_libero_forma(1) f)
        || jsonb_build_object('tipo_indirizzo_id', (SELECT v FROM _f WHERE k = 'tr'),
                              'indirizzo_libero',  'Via pgTAP ripiego 1',
                              'stato_id',          1)),
    true);

SELECT is(
    (SELECT count(*)::int FROM anagrafiche.indirizzi_soggetti i
      WHERE i.soggetto_id = (SELECT v FROM _s WHERE k = 'sog')
        AND i.tipo_indirizzo_id = (SELECT v FROM _f WHERE k = 'tc')),
    0,
    '9) la copia degli obbligatori non copia il tipo quando c''e'' il suo ripiego');

SELECT is(
    (SELECT count(*)::int FROM anagrafiche.indirizzi_soggetti i
      WHERE i.soggetto_id = (SELECT v FROM _s WHERE k = 'sog')
        AND i.tipo_indirizzo_id = (SELECT v FROM _f WHERE k = 'tr')),
    1,
    '10) ... il ripiego si scrive');

SELECT is(
    (SELECT count(*)::int FROM anagrafiche.indirizzi_soggetti i
      WHERE i.soggetto_id = (SELECT v FROM _s WHERE k = 'sog')
        AND i.tipo_indirizzo_id = (SELECT v FROM _f WHERE k = 'ta')),
    1,
    '11) ... e il tipo il cui ripiego e'' vietato si copia');

SELECT * FROM finish();
ROLLBACK;
