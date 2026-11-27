-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le scritture della veste che restano all'app passano dai verbi —
--       l'accensione DEFINER, l'invito spedito, la fixture dei test, la veste
--       che nasce spenta, lo stato REVOCATA nell'aggregato di vw_accessi_altri
-- ChangeSet (90_end -09 e 20_code -10 per 21-24): 20261127-01 (fn_accendi_veste DEFINER), -02 (fn_riattiva_utente_tecnico
--            DEFINER), -03 (fn_segna_invito_inviato), -04 (vw_accessi_altri),
--            -05 (dbops.fn_pgtap_imposta_veste), 90_end -06 (ritiro di
--            fn_crea_operatore_v2), -07 (la veste tecnica nasce accesa), 90_end -08
--            (attivo DEFAULT false)
-- Brief: brief-db-accessi-area-clienti, passo 3c-1
--
-- Gira come l'applicazione (runner di default): ogni caso passa dalle porte
-- che l'app ha davvero. Le vesti cliente le inserisce l'app, come le inserisce
-- oggi il backend (l'INSERT resta all'app fino al giro della veste cliente).
--
-- ⚠️ Il caso «PRODUZIONE» della fixture non si costruisce: l'ambiente sta in
--   dbops.installazione, in sola lettura per l'app. Si prova che la fixture
--   chieda la regola dei dati di sviluppo prima di scrivere (20), come per le
--   fixture del giro 10-bis (config/test-porta-tabelle-accesso-v1).
-- ⚠️ La riattivazione dell'utente tecnico la prova script/test-fn-riattiva-utente-tecnico
--   (runner owner); qui solo la forma (1).
--
-- Elenco test (plan 24):
--   La forma
--    1) i quattro verbi sono SECURITY DEFINER col search_path fissato
--    2) attivo nasce false per default
--    3) fn_crea_operatore_v2 non c'e' piu'
--    4) ogni stato di script.fn_stato_veste e' nominato nell'aggregato della vista
--   La nascita
--    5) un INSERT dell'app che non nomina attivo fa nascere la veste spenta
--    6) l'utente tecnico nasce con la veste accesa
--   L'accensione
--    7) senza utente in sessione (il link anonimo) accende: true, e accesa
--    8) la veste di un'altra credenziale: false, e resta spenta
--   Lo stato aggregato
--    9) tutte le vesti revocate: REVOCATA
--   10) una revocata e una spenta senza segno: DISATTIVO
--   L'invito spedito
--   11) un operatore senza permessi non lo segna
--   12) senza utente in sessione non si segna (fail-closed)
--   13) col livello TUTTO su anagrafiche si segna una veste cliente: ritorna il
--       momento scritto, attivo non cambia
--   14) una veste OPERATORE chiede SUPER_ADMIN
--   15) veste assente: E_VESTE_NON_TROVATA; id NULL: E_SCRIPT_CHIAMATA_NON_VALIDA
--   La fixture
--   16) cambia solo le colonne nominate; una chiave a null porta a NULL
--   17) una colonna fuori elenco, o nessuna: E_SCRIPT_CHIAMATA_NON_VALIDA
--   18) veste assente: E_VESTE_NON_TROVATA
--   19) una veste revocata non si accende nemmeno da qui
--   20) il cancello dei dati di sviluppo viene prima della scrittura
--   21) una veste revocata non cambia tipo ne' ruolo anagrafico dalla fixture
--   22) la fixture che cancella toglie una veste non revocata
--   23) ma non una revocata: E_VESTE_REVOCA_SOLO_DAL_VERBO
--   24) anche la fixture che cancella chiede la regola dei dati di sviluppo prima
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(24);

-- ============================================================
-- Fixture
-- ============================================================
-- Chi agisce: il super admin, un operatore senza permessi, un operatore col
-- livello TUTTO sull'area anagrafiche; un operatore come veste OPERATORE.
CREATE TEMP TABLE _sa  AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-3c1', true);
CREATE TEMP TABLE _op  AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-OP-3c1', false);
CREATE TEMP TABLE _ana AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-ANA-3c1', false);
CREATE TEMP TABLE _bersaglio AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-OP2-3c1', false);
SELECT dbops.fn_pgtap_concedi_livello_area((SELECT auth_user_id FROM _ana), 'anagrafiche', 'TUTTO');

-- Un ruolo cliente su cui appoggiare le vesti.
CREATE TEMP TABLE _cli AS
SELECT c.soggetto_ruolo_id AS sr_id FROM dbops.fn_pgtap_crea_cliente_ba('3c1') c;
-- Un secondo cliente, per la veste che la fixture accende (16): una veste
-- accesa per ruolo e tipo (uq_identita_digitali_sr_ruolo_attivo).
CREATE TEMP TABLE _cli2 AS
SELECT c.soggetto_ruolo_id AS sr_id FROM dbops.fn_pgtap_crea_cliente_ba('3c1-bis') c;
SET CONSTRAINTS ALL IMMEDIATE;

-- Una credenziale nuda, con un nome che non collide.
CREATE OR REPLACE FUNCTION pg_temp.credenziale(p_nome text) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE v_id integer;  -- ⚠️ niente %TYPE su django.*
BEGIN
    INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                                  first_name, last_name, email, date_joined)
    VALUES ('_pgtap_3c1_' || p_nome || '_' || substring(md5(clock_timestamp()::text) FROM 1 FOR 8),
            '!', false, false, false, '', '', '', now())
    RETURNING id INTO v_id;
    RETURN v_id;
END $$;

-- Le vesti, per nome: (credenziale, veste).
CREATE TEMP TABLE _c (nome text PRIMARY KEY, auth_user_id integer);
CREATE TEMP TABLE _v (nome text PRIMARY KEY, identita_id bigint);
INSERT INTO _c (nome, auth_user_id)
SELECT n, pg_temp.credenziale(n) FROM unnest(ARRAY['c1','c2','c3','c4','c5']) n;

CREATE OR REPLACE FUNCTION pg_temp.veste(p_veste text, p_cred text, p_ruolo text, p_attivo boolean,
                                          p_secondo_cliente boolean DEFAULT false)
RETURNS void
LANGUAGE plpgsql AS $$
DECLARE v_id anagrafiche.identita_digitali.id%TYPE;
BEGIN
    INSERT INTO anagrafiche.identita_digitali (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    VALUES (CASE WHEN p_secondo_cliente THEN (SELECT sr_id FROM _cli2) ELSE (SELECT sr_id FROM _cli) END,
            (SELECT auth_user_id FROM _c WHERE nome = p_cred),
            p_ruolo::config.ruolo_applicativo, p_attivo)
    RETURNING id INTO v_id;
    INSERT INTO _v VALUES (p_veste, v_id);
END $$;

CREATE OR REPLACE FUNCTION pg_temp.id(p_nome text) RETURNS bigint
LANGUAGE sql AS $$ SELECT identita_id FROM _v WHERE nome = p_nome $$;

-- c1: una veste spenta per l'accensione dal link.
SELECT pg_temp.veste('c1', 'c1', 'CLIENTE_PORTALE', false);
-- c3: due vesti, tutte e due da revocare.
SELECT pg_temp.veste('c3a', 'c3', 'CLIENTE_PORTALE', false);
SELECT pg_temp.veste('c3b', 'c3', 'SHOP_CUSTOMER',   false);
-- c4: una da revocare e una spenta senza segno.
SELECT pg_temp.veste('c4a', 'c4', 'CLIENTE_PORTALE', false);
SELECT pg_temp.veste('c4b', 'c4', 'SHOP_CUSTOMER',   false);
-- c5: la veste dell'invito spedito e della fixture.
SELECT pg_temp.veste('c5', 'c5', 'CLIENTE_PORTALE', false, true);

-- Chi agisce: il contesto operatore su un utente dato.
CREATE OR REPLACE FUNCTION pg_temp.agisci(p_auth_user_id integer) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(p_auth_user_id);
END $$;

-- Esegue un'istruzione e ne restituisce il codice di dominio (campo
-- CONSTRAINT di un P0001), lo SQLSTATE per un altro errore, 'ok' se passa.
CREATE OR REPLACE FUNCTION pg_temp.codice(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_codice text;  -- un nome d'errore, nessuna colonna
BEGIN
    EXECUTE p_sql;
    RETURN 'ok';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME;
    RETURN COALESCE(NULLIF(v_codice, ''), SQLSTATE);
END $$;

-- ============================================================
-- 1-4 La forma
-- ============================================================
SELECT is(
    (SELECT COALESCE(array_agg(p.pronamespace::regnamespace::text || '.' || p.proname
                                 ORDER BY p.pronamespace::regnamespace::text || '.' || p.proname), ARRAY[]::text[])
       FROM pg_catalog.pg_proc p
      WHERE p.oid IN ('anagrafiche.fn_accendi_veste'::regproc,
                      'script.fn_riattiva_utente_tecnico'::regproc,
                      'anagrafiche.fn_segna_invito_inviato'::regproc,
                      'dbops.fn_pgtap_imposta_veste'::regproc)
        AND p.prosecdef
        AND 'search_path=pg_catalog, public, pg_temp' = ANY (p.proconfig)),
    ARRAY['anagrafiche.fn_accendi_veste', 'anagrafiche.fn_segna_invito_inviato',
          'dbops.fn_pgtap_imposta_veste', 'script.fn_riattiva_utente_tecnico'],
    '1) i quattro verbi: SECURITY DEFINER, search_path fissato');

SELECT is(
    (SELECT pg_get_expr(d.adbin, d.adrelid)
       FROM pg_attrdef d
       JOIN pg_attribute a ON a.attrelid = d.adrelid AND a.attnum = d.adnum
      WHERE d.adrelid = 'anagrafiche.identita_digitali'::regclass
        AND a.attname = 'attivo'),
    'false',
    '2) attivo: DEFAULT false');

SELECT is(to_regproc('anagrafiche.fn_crea_operatore_v2'), NULL,
    '3) fn_crea_operatore_v2 non c''e'' piu''');

SELECT is(
    (SELECT COALESCE(string_agg(s.stato, ', ' ORDER BY s.stato), '')
       FROM (SELECT DISTINCT m[1] AS stato
               FROM regexp_matches(pg_get_functiondef('script.fn_stato_veste'::regproc),
                                   'THEN ''([A-Z_]+)''::text', 'g') m) s
      WHERE position(format('THEN %L::text', s.stato)
                     IN pg_get_viewdef('anagrafiche.vw_accessi_altri'::regclass)) = 0),
    '',
    '4) ogni stato di script.fn_stato_veste e'' nominato nell''aggregato di vw_accessi_altri');

-- ============================================================
-- 5-6 La nascita
-- ============================================================
INSERT INTO anagrafiche.identita_digitali (soggetto_ruolo_id, auth_user_id, ruolo_applicativo)
VALUES ((SELECT sr_id FROM _cli), (SELECT auth_user_id FROM _c WHERE nome = 'c2'),
        'CLIENTE_PORTALE'::config.ruolo_applicativo);
SELECT is(
    (SELECT idg.attivo FROM anagrafiche.identita_digitali idg
      WHERE idg.auth_user_id = (SELECT auth_user_id FROM _c WHERE nome = 'c2')),
    false,
    '5) un INSERT dell''app che non nomina attivo fa nascere la veste spenta');

CREATE TEMP TABLE _tec AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
SELECT is(
    (SELECT idg.attivo::text || '|' || idg.tecnica::text
       FROM anagrafiche.identita_digitali idg WHERE idg.id = (SELECT identita_id FROM _tec)),
    'true|true',
    '6) l''utente tecnico nasce con la veste accesa');

-- ============================================================
-- 7-8 L'accensione
-- ============================================================
-- Il ritorno si legge in un'istruzione, lo stato nella successiva: una
-- sottoquery della stessa istruzione non vede la scrittura della funzione.
SELECT set_config('app.current_user_id', '', true);
CREATE TEMP TABLE _acceso AS
SELECT anagrafiche.fn_accendi_veste(pg_temp.id('c1'), (SELECT auth_user_id FROM _c WHERE nome = 'c1')) AS esito;
SELECT is(
    format('%s|%s', (SELECT esito FROM _acceso),
           (SELECT idg.attivo FROM anagrafiche.identita_digitali idg WHERE idg.id = pg_temp.id('c1'))),
    't|t',
    '7) senza utente in sessione, come dal link dell''invito, la veste si accende');

CREATE TEMP TABLE _altrui AS
SELECT anagrafiche.fn_accendi_veste(pg_temp.id('c5'), (SELECT auth_user_id FROM _c WHERE nome = 'c1')) AS esito;
SELECT is(
    format('%s|%s', (SELECT esito FROM _altrui),
           (SELECT idg.attivo FROM anagrafiche.identita_digitali idg WHERE idg.id = pg_temp.id('c5'))),
    'f|f',
    '8) la veste di un''altra credenziale: false, e resta spenta');

-- ============================================================
-- 9-10 Lo stato aggregato
-- ============================================================
SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));
SELECT anagrafiche.fn_revoca_veste(pg_temp.id('c3a'));
SELECT anagrafiche.fn_revoca_veste(pg_temp.id('c3b'));
SELECT anagrafiche.fn_revoca_veste(pg_temp.id('c4a'));

SELECT is(
    (SELECT va.stato_accesso FROM anagrafiche.vw_accessi_altri va
      WHERE va.auth_user_id = (SELECT auth_user_id FROM _c WHERE nome = 'c3')),
    'REVOCATA',
    '9) tutte le vesti revocate: REVOCATA');

SELECT is(
    (SELECT va.stato_accesso FROM anagrafiche.vw_accessi_altri va
      WHERE va.auth_user_id = (SELECT auth_user_id FROM _c WHERE nome = 'c4')),
    'DISATTIVO',
    '10) una revocata e una spenta senza segno: DISATTIVO, il migliore dei due');

-- ============================================================
-- 11-15 L'invito spedito
-- ============================================================
SELECT pg_temp.agisci((SELECT auth_user_id FROM _op));
SELECT is(
    pg_temp.codice(format('SELECT anagrafiche.fn_segna_invito_inviato(%s)', pg_temp.id('c5'))),
    'E_PERMESSO_NEGATO',
    '11) un operatore senza permessi non segna l''invito');

SELECT set_config('app.current_user_id', '', true);
SELECT is(
    pg_temp.codice(format('SELECT anagrafiche.fn_segna_invito_inviato(%s)', pg_temp.id('c5'))),
    'E_PERMESSO_NEGATO',
    '12) senza utente in sessione non si segna');

SELECT pg_temp.agisci((SELECT auth_user_id FROM _ana));
CREATE TEMP TABLE _segnato AS
SELECT anagrafiche.fn_segna_invito_inviato(pg_temp.id('c5')) AS momento;
SELECT is(
    (SELECT format('%s|%s', idg.invito_inviato_at = (SELECT momento FROM _segnato), idg.attivo)
       FROM anagrafiche.identita_digitali idg WHERE idg.id = pg_temp.id('c5')),
    't|f',
    '13) col livello TUTTO su anagrafiche si segna: ritorna il momento scritto, attivo non cambia');

CREATE TEMP TABLE _op_da_ana AS
SELECT pg_temp.codice(format('SELECT anagrafiche.fn_segna_invito_inviato(%s)',
                             (SELECT identita_id FROM _bersaglio))) AS esito;
SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));
SELECT is(
    (SELECT esito FROM _op_da_ana) || '|' ||
    pg_temp.codice(format('SELECT anagrafiche.fn_segna_invito_inviato(%s)', (SELECT identita_id FROM _bersaglio))),
    'E_PERMESSO_NEGATO|ok',
    '14) una veste OPERATORE: col solo livello d''area no, dal super admin si');

SELECT is(
    format('%s|%s',
           pg_temp.codice(format('SELECT anagrafiche.fn_segna_invito_inviato(%s)', (SELECT max(id) + 1000 FROM anagrafiche.identita_digitali))),
           pg_temp.codice('SELECT anagrafiche.fn_segna_invito_inviato(NULL)')),
    'E_VESTE_NON_TROVATA|E_SCRIPT_CHIAMATA_NON_VALIDA',
    '15) veste assente: E_VESTE_NON_TROVATA; id NULL: E_SCRIPT_CHIAMATA_NON_VALIDA');

-- ============================================================
-- 16-20 La fixture
-- ============================================================
SELECT set_config('app.current_user_id', '', true);
SELECT dbops.fn_pgtap_imposta_veste(pg_temp.id('c5'),
    '{"attivo": true, "valido_al": "2099-12-31", "invito_inviato_at": null}'::jsonb);
SELECT is(
    (SELECT format('%s|%s|%s|%s', idg.attivo, idg.valido_al, idg.invito_inviato_at IS NULL,
                   idg.ruolo_applicativo)
       FROM anagrafiche.identita_digitali idg WHERE idg.id = pg_temp.id('c5')),
    't|2099-12-31|t|CLIENTE_PORTALE',
    '16) la fixture cambia solo le colonne nominate, e una chiave a null porta a NULL');

SELECT is(
    format('%s|%s',
           pg_temp.codice(format('SELECT dbops.fn_pgtap_imposta_veste(%s, %L::jsonb)',
                                 pg_temp.id('c5'), '{"revocata_at": null}')),
           pg_temp.codice(format('SELECT dbops.fn_pgtap_imposta_veste(%s, %L::jsonb)',
                                 pg_temp.id('c5'), '{}'))),
    'E_SCRIPT_CHIAMATA_NON_VALIDA|E_SCRIPT_CHIAMATA_NON_VALIDA',
    '17) una colonna fuori elenco, o nessuna: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT is(
    pg_temp.codice(format('SELECT dbops.fn_pgtap_imposta_veste(%s, %L::jsonb)',
                          (SELECT max(id) + 1000 FROM anagrafiche.identita_digitali), '{"attivo": false}')),
    'E_VESTE_NON_TROVATA',
    '18) veste assente: E_VESTE_NON_TROVATA');

SELECT is(
    pg_temp.codice(format('SELECT dbops.fn_pgtap_imposta_veste(%s, %L::jsonb)',
                          pg_temp.id('c3a'), '{"attivo": true}')),
    'E_VESTE_REVOCATA',
    '19) una veste revocata non si accende nemmeno dalla fixture');

SELECT ok(
    (SELECT position('fn_dati_di_sviluppo_ammessi_su_valori' IN p.prosrc) BETWEEN 1
                AND position('fn_scrivi_riga_da_jsonb' IN p.prosrc) - 1
       FROM pg_proc p WHERE p.oid = 'dbops.fn_pgtap_imposta_veste'::regproc),
    '20) la fixture chiede la regola dei dati di sviluppo prima di scrivere');

SELECT is(
    pg_temp.codice(format('SELECT dbops.fn_pgtap_imposta_veste(%s, %L::jsonb)',
                          pg_temp.id('c3a'), '{"ruolo_applicativo": "SHOP_CUSTOMER"}')),
    'E_VESTE_REVOCA_SOLO_DAL_VERBO',
    '21) una veste revocata non cambia tipo nemmeno dalla fixture');

SELECT dbops.fn_pgtap_cancella_veste(pg_temp.id('c4b'));
SELECT is(
    (SELECT count(*) FROM anagrafiche.identita_digitali WHERE id = pg_temp.id('c4b'))::int,
    0,
    '22) la fixture che cancella toglie una veste non revocata');

SELECT is(
    pg_temp.codice(format('SELECT dbops.fn_pgtap_cancella_veste(%s)', pg_temp.id('c4a'))),
    'E_VESTE_REVOCA_SOLO_DAL_VERBO',
    '23) ma non una revocata');

SELECT ok(
    (SELECT position('fn_dati_di_sviluppo_ammessi_su_valori' IN p.prosrc) BETWEEN 1
                AND position('DELETE FROM' IN p.prosrc) - 1
       FROM pg_proc p WHERE p.oid = 'dbops.fn_pgtap_cancella_veste'::regproc),
    '24) la fixture che cancella chiede la regola dei dati di sviluppo prima di scrivere');

SELECT * FROM finish();
ROLLBACK;
