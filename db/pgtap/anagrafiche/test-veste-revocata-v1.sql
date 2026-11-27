-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la veste revocata dall'amministratore (R-4) — il segno, il guard della
--       tabella, i due verbi col loro permesso, lo stato REVOCATA
-- ChangeSet: 20261125-51 (colonne e CHECK), -52 (guard), -53 (permesso),
--            -54 (fn_revoca_veste), -55 (fn_togli_revoca_veste),
--            -57 (fn_stato_veste); 90_end/20261127-09 (l'app non aggiorna e non
--            cancella le vesti: 4, 13, 16)
-- Brief: brief-db-accessi-area-clienti, giro 1
--
-- Gira come l'applicazione (runner di default): ogni caso passa dalle porte
-- che l'app ha davvero. Le vesti cliente le scrive l'app, come le scrive oggi
-- il backend; gli operatori nascono dal percorso di produzione.
--
-- Elenco test (plan 24):
--   La forma
--    1) le due colonne e il CHECK esistono
--    2) i verbi sono SECURITY DEFINER col search_path fissato; il guard e'
--       montato su INSERT, UPDATE e DELETE
--    3) i tre codici nuovi sono a catalogo con la classe giusta
--   Il segno si scrive solo dai verbi
--    4) l'app che scrive revocata_at da se' -> permesso negato (42501): dal
--       90_end/20261127-09 l'app non aggiorna le vesti; il guard resta la rete
--       per il proprietario
--    5) l'app che inserisce una veste col segno -> idem
--   Il permesso
--    6) un operatore senza permessi non revoca una veste cliente
--    7) senza utente nella sessione non si revoca (fail-closed)
--    8) un operatore col livello TUTTO su anagrafiche revoca una veste cliente
--    9) ma non una veste OPERATORE: quella chiede SUPER_ADMIN
--   La revoca
--   10) il super admin revoca una veste accesa: ritorna true, spenta, segno
--       con chi
--   11) fn_stato_veste dice REVOCATA
--   12) la riaccensione col verbo dell'invito e' rifiutata (E_VESTE_REVOCATA)
--   13) e anche con un UPDATE diretto: permesso negato (42501); il guard sulla
--       stessa accensione lo prova anagrafiche/test-veste-accensione-invito-fixture-v1 (19)
--   14) una riga nuova accesa sulla stessa coppia e' rifiutata
--   15) una riga nuova spenta nasce, ma non si accende
--   16) la veste revocata non si cancella dall'app: permesso negato (42501)
--   17) revocare di nuovo: ritorna false e tiene il segno di prima
--   18) una veste con l'invito pendente, mai accesa, si revoca: ritorna false,
--       e lo stato e' REVOCATA anche col token in volo
--   Il nuovo invito
--   19) un operatore senza permessi non toglie il segno, nemmeno dove non c'e'
--   20) il super admin toglie il segno: true, dalla coppia intera
--   21) dopo, il link dell'invito accende
--   22) togliere di nuovo: false
--   Gli argomenti
--   23) veste assente -> E_VESTE_NON_TROVATA, dai due verbi
--   24) id NULL -> E_SCRIPT_CHIAMATA_NON_VALIDA
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(24);

-- ============================================================
-- Fixture
-- ============================================================
-- Chi agisce: il super admin, un operatore senza permessi, un operatore col
-- livello TUTTO sull'area anagrafiche, e un operatore da revocare.
CREATE TEMP TABLE _sa  AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-revoca', true);
CREATE TEMP TABLE _op  AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-OP-revoca', false);
CREATE TEMP TABLE _ana AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-ANA-revoca', false);
CREATE TEMP TABLE _bersaglio AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-OP2-revoca', false);
SELECT dbops.fn_pgtap_concedi_livello_area((SELECT auth_user_id FROM _ana), 'anagrafiche', 'TUTTO');

-- Un ruolo cliente su cui appoggiare le vesti.
CREATE TEMP TABLE _cli AS
SELECT c.soggetto_ruolo_id AS sr_id FROM dbops.fn_pgtap_crea_cliente_ba('revoca') c;
SET CONSTRAINTS ALL IMMEDIATE;

-- Una credenziale nuda, con un nome che non collide.
CREATE OR REPLACE FUNCTION pg_temp.credenziale(p_nome text) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE v_id integer;  -- ⚠️ niente %TYPE su django.*
BEGIN
    INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                                  first_name, last_name, email, date_joined)
    VALUES ('_pgtap_rev_' || p_nome || '_' || substring(md5(clock_timestamp()::text) FROM 1 FOR 8),
            '!', false, false, false, '', '', '', now())
    RETURNING id INTO v_id;
    RETURN v_id;
END $$;

-- Le credenziali: c1 cliente portale accesa (la revoca del super admin),
-- c2 cliente portale spenta con l'invito pendente, c3 shop accesa (la revoca
-- col livello d'area).
CREATE TEMP TABLE _c (nome text PRIMARY KEY, auth_user_id integer, identita_id bigint);
INSERT INTO _c (nome, auth_user_id)
SELECT n, pg_temp.credenziale(n) FROM unnest(ARRAY['c1','c2','c3']) n;

CREATE OR REPLACE FUNCTION pg_temp.veste(p_nome text, p_ruolo text, p_attivo boolean) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE v_id anagrafiche.identita_digitali.id%TYPE;
BEGIN
    INSERT INTO anagrafiche.identita_digitali (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    VALUES ((SELECT sr_id FROM _cli), (SELECT auth_user_id FROM _c WHERE nome = p_nome),
            p_ruolo::config.ruolo_applicativo, p_attivo)
    RETURNING id INTO v_id;
    UPDATE _c SET identita_id = v_id WHERE nome = p_nome;
END $$;

SELECT pg_temp.veste('c1', 'CLIENTE_PORTALE', true);
SELECT pg_temp.veste('c2', 'CLIENTE_PORTALE', false);
SELECT pg_temp.veste('c3', 'SHOP_CUSTOMER',   true);

-- L'invito pendente di c2: identita_id nel meta, come lo scrive l'emissione.
INSERT INTO config.token_monouso (token_hash, tipo, auth_user_id, scadenza, utilizzato, meta)
VALUES (md5(random()::text || clock_timestamp()::text), 'INVITO_PORTALE',
        (SELECT auth_user_id FROM _c WHERE nome = 'c2'), now() + interval '1 day', false,
        jsonb_build_object('identita_id', (SELECT identita_id FROM _c WHERE nome = 'c2')));

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

CREATE OR REPLACE FUNCTION pg_temp.id(p_nome text) RETURNS bigint
LANGUAGE sql AS $$ SELECT identita_id FROM _c WHERE nome = p_nome $$;

-- ============================================================
-- 1-3 La forma
-- ============================================================
SELECT is(
    (SELECT format('%s|%s|%s',
                   EXISTS (SELECT 1 FROM pg_attribute
                            WHERE attrelid = 'anagrafiche.identita_digitali'::regclass
                              AND attname = 'revocata_at' AND NOT attisdropped),
                   EXISTS (SELECT 1 FROM pg_attribute
                            WHERE attrelid = 'anagrafiche.identita_digitali'::regclass
                              AND attname = 'revocata_da_user_id' AND NOT attisdropped),
                   EXISTS (SELECT 1 FROM pg_constraint
                            WHERE conrelid = 'anagrafiche.identita_digitali'::regclass
                              AND conname = 'chk_identita_digitali_revoca_coerente'
                              AND contype = 'c'))),
    't|t|t',
    '1) revocata_at, revocata_da_user_id e chk_identita_digitali_revoca_coerente esistono');

SELECT is(
    (SELECT format('%s|%s|%s',
                   (SELECT bool_and(p.prosecdef AND p.proconfig::text LIKE '%search_path=pg_catalog%')
                      FROM pg_proc p
                     WHERE p.oid IN ('anagrafiche.fn_revoca_veste'::regproc,
                                     'anagrafiche.fn_togli_revoca_veste'::regproc)),
                   (SELECT t.tgtype & (4 | 8 | 16) = (4 | 8 | 16)
                      FROM pg_trigger t
                     WHERE t.tgrelid = 'anagrafiche.identita_digitali'::regclass
                       AND t.tgfoid  = 'anagrafiche.trgfn_identita_digitali_guard_revoca'::regproc
                       AND NOT t.tgisinternal),
                   (SELECT t.tgtype & 2 = 2
                      FROM pg_trigger t
                     WHERE t.tgrelid = 'anagrafiche.identita_digitali'::regclass
                       AND t.tgfoid  = 'anagrafiche.trgfn_identita_digitali_guard_revoca'::regproc
                       AND NOT t.tgisinternal))),
    't|t|t',
    '2) i verbi sono DEFINER con search_path fissato; il guard e'' BEFORE su INSERT, UPDATE e DELETE');

SELECT is(
    (SELECT string_agg(codice || '=' || classe, ' | ' ORDER BY codice COLLATE "C")
       FROM config.codici_errore
      WHERE codice IN ('E_VESTE_NON_TROVATA', 'E_VESTE_REVOCATA', 'E_VESTE_REVOCA_SOLO_DAL_VERBO')),
    -- ordine in COLLATE "C" nella string_agg: in it_IT il trattino basso non conta
    'E_VESTE_NON_TROVATA=NON_TROVATO | E_VESTE_REVOCATA=CONFLITTO_STATO | '
    'E_VESTE_REVOCA_SOLO_DAL_VERBO=TECNICO',
    '3) i tre codici sono a catalogo con la classe giusta');

-- ============================================================
-- 4-5 Il segno si scrive solo dai verbi
-- ============================================================
SELECT is(
    pg_temp.codice(format(
        $$UPDATE anagrafiche.identita_digitali
             SET attivo = false, revocata_at = now(), revocata_da_user_id = %s
           WHERE id = %s$$,
        (SELECT auth_user_id FROM _sa), pg_temp.id('c3'))),
    '42501',
    '4) l''app che scrive il segno da se'' e'' rifiutata: non aggiorna le vesti (permesso negato)');

SELECT is(
    pg_temp.codice(format(
        $$INSERT INTO anagrafiche.identita_digitali
              (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo, revocata_at, revocata_da_user_id)
          VALUES (%s, %s, 'SHOP_CUSTOMER', false, now(), %s)$$,
        (SELECT sr_id FROM _cli), (SELECT auth_user_id FROM _c WHERE nome = 'c3'),
        (SELECT auth_user_id FROM _sa))),
    'E_VESTE_REVOCA_SOLO_DAL_VERBO',
    '5) l''app che inserisce una veste col segno e'' rifiutata');

-- ============================================================
-- 6-9 Il permesso
-- ============================================================
SELECT pg_temp.agisci((SELECT auth_user_id FROM _op));
SELECT is(
    pg_temp.codice(format('SELECT anagrafiche.fn_revoca_veste(%s)', pg_temp.id('c1'))),
    'E_PERMESSO_NEGATO',
    '6) un operatore senza permessi non revoca una veste cliente');

SELECT set_config('app.current_user_id', '', true);
SELECT is(
    pg_temp.codice(format('SELECT anagrafiche.fn_revoca_veste(%s)', pg_temp.id('c1'))),
    'E_PERMESSO_NEGATO',
    '7) senza utente nella sessione non si revoca');

SELECT pg_temp.agisci((SELECT auth_user_id FROM _ana));
SELECT is(
    anagrafiche.fn_revoca_veste(pg_temp.id('c3')),
    true,
    '8) col livello TUTTO su anagrafiche si revoca una veste shop');

SELECT is(
    pg_temp.codice(format('SELECT anagrafiche.fn_revoca_veste(%s)', (SELECT identita_id FROM _bersaglio))),
    'E_PERMESSO_NEGATO',
    '9) lo stesso operatore non revoca una veste OPERATORE: chiede SUPER_ADMIN');

-- ============================================================
-- 10-18 La revoca
-- ============================================================
SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));

CREATE TEMP TABLE _r1 AS SELECT anagrafiche.fn_revoca_veste(pg_temp.id('c1')) AS era_accesa;
SELECT is(
    (SELECT format('%s|%s|%s|%s', r.era_accesa, idg.attivo, idg.revocata_at IS NOT NULL,
                   idg.revocata_da_user_id = (SELECT auth_user_id FROM _sa))
       FROM _r1 r, anagrafiche.identita_digitali idg
      WHERE idg.id = pg_temp.id('c1')),
    't|f|t|t',
    '10) il super admin revoca: era accesa, ora spenta, col segno e il suo nome');

SELECT is(
    (SELECT s.stato FROM script.fn_stato_veste(pg_temp.id('c1')) s),
    'REVOCATA',
    '11) fn_stato_veste dice REVOCATA');

SELECT is(
    pg_temp.codice(format('SELECT anagrafiche.fn_accendi_veste(%s, %s)',
                          pg_temp.id('c1'), (SELECT auth_user_id FROM _c WHERE nome = 'c1'))),
    'E_VESTE_REVOCATA',
    '12) il link di un invito non riaccende una veste revocata');

SELECT is(
    pg_temp.codice(format('UPDATE anagrafiche.identita_digitali SET attivo = true WHERE id = %s',
                          pg_temp.id('c1'))),
    '42501',
    '13) nemmeno un UPDATE diretto: l''app non aggiorna le vesti (permesso negato)');

SELECT is(
    pg_temp.codice(format(
        $$INSERT INTO anagrafiche.identita_digitali (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
          VALUES (%s, %s, 'CLIENTE_PORTALE', true)$$,
        (SELECT sr_id FROM _cli), (SELECT auth_user_id FROM _c WHERE nome = 'c1'))),
    'E_VESTE_REVOCATA',
    '14) una riga nuova accesa sulla stessa coppia e'' rifiutata');

INSERT INTO anagrafiche.identita_digitali (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
VALUES ((SELECT sr_id FROM _cli), (SELECT auth_user_id FROM _c WHERE nome = 'c1'), 'CLIENTE_PORTALE', false);
CREATE TEMP TABLE _nuova AS
SELECT max(id) AS id FROM anagrafiche.identita_digitali
 WHERE auth_user_id = (SELECT auth_user_id FROM _c WHERE nome = 'c1');
SELECT is(
    pg_temp.codice(format('SELECT anagrafiche.fn_accendi_veste(%s, %s)',
                          (SELECT id FROM _nuova), (SELECT auth_user_id FROM _c WHERE nome = 'c1'))),
    'E_VESTE_REVOCATA',
    '15) una riga nuova spenta sulla coppia nasce, ma non si accende');

SELECT is(
    pg_temp.codice(format('DELETE FROM anagrafiche.identita_digitali WHERE id = %s', pg_temp.id('c1'))),
    '42501',
    '16) la veste revocata non si cancella dall''app: non cancella vesti (permesso negato)');

CREATE TEMP TABLE _prima AS
SELECT revocata_at, revocata_da_user_id FROM anagrafiche.identita_digitali WHERE id = pg_temp.id('c1');
SELECT pg_temp.agisci((SELECT auth_user_id FROM _ana));
CREATE TEMP TABLE _r2 AS SELECT anagrafiche.fn_revoca_veste(pg_temp.id('c1')) AS era_accesa;
SELECT is(
    (SELECT format('%s|%s', r.era_accesa,
                   (idg.revocata_at, idg.revocata_da_user_id) = (p.revocata_at, p.revocata_da_user_id))
       FROM _r2 r, _prima p, anagrafiche.identita_digitali idg
      WHERE idg.id = pg_temp.id('c1')),
    'f|t',
    '17) revocare di nuovo: era spenta, e il segno resta quello della prima revoca');

SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));
CREATE TEMP TABLE _r3 AS SELECT anagrafiche.fn_revoca_veste(pg_temp.id('c2')) AS era_accesa;
SELECT is(
    (SELECT format('%s|%s|%s', r.era_accesa, s.stato, s.token_scade_at IS NOT NULL)
       FROM _r3 r, script.fn_stato_veste(pg_temp.id('c2')) s),
    'f|REVOCATA|t',
    '18) la veste con l''invito pendente si revoca, e resta REVOCATA col token in volo');

-- ============================================================
-- 19-22 Il nuovo invito
-- ============================================================
SELECT pg_temp.agisci((SELECT auth_user_id FROM _op));
SELECT is(
    format('%s|%s',
           pg_temp.codice(format('SELECT anagrafiche.fn_togli_revoca_veste(%s)', pg_temp.id('c1'))),
           pg_temp.codice(format('SELECT anagrafiche.fn_togli_revoca_veste(%s)',
                                 (SELECT identita_id FROM _bersaglio)))),
    'E_PERMESSO_NEGATO|E_PERMESSO_NEGATO',
    '19) senza permesso il segno non si toglie, nemmeno su una veste che non lo porta');

-- Il segno anche sulla riga nuova della coppia: lo mette il verbo, che la
-- revoca come una veste spenta qualunque.
SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));
SELECT anagrafiche.fn_revoca_veste((SELECT id FROM _nuova));
CREATE TEMP TABLE _t1 AS SELECT anagrafiche.fn_togli_revoca_veste(pg_temp.id('c1')) AS tolto;
SELECT is(
    (SELECT format('%s|%s', t.tolto,
                   (SELECT count(*) FROM anagrafiche.identita_digitali
                     WHERE auth_user_id = (SELECT auth_user_id FROM _c WHERE nome = 'c1')
                       AND revocata_at IS NOT NULL))
       FROM _t1 t),
    't|0',
    '20) il super admin toglie il segno, da tutte le righe della coppia');

-- ⚠️ L'accensione e la lettura in due istruzioni: nella stessa, la lettura
--   vedrebbe la snapshot di prima.
CREATE TEMP TABLE _a1 AS
SELECT anagrafiche.fn_accendi_veste(pg_temp.id('c1'), (SELECT auth_user_id FROM _c WHERE nome = 'c1')) AS accesa;
SELECT is(
    (SELECT format('%s|%s', a.accesa,
                   (SELECT attivo FROM anagrafiche.identita_digitali WHERE id = pg_temp.id('c1')))
       FROM _a1 a),
    't|t',
    '21) dopo il nuovo invito il link accende');

SELECT is(
    anagrafiche.fn_togli_revoca_veste(pg_temp.id('c1')),
    false,
    '22) togliere di nuovo: non c''e'' piu'' niente da togliere');

-- ============================================================
-- 23-24 Gli argomenti
-- ============================================================
SELECT is(
    format('%s|%s',
           pg_temp.codice('SELECT anagrafiche.fn_revoca_veste(999999999999)'),
           pg_temp.codice('SELECT anagrafiche.fn_togli_revoca_veste(999999999999)')),
    'E_VESTE_NON_TROVATA|E_VESTE_NON_TROVATA',
    '23) una veste assente: E_VESTE_NON_TROVATA, dai due verbi');

SELECT is(
    format('%s|%s',
           pg_temp.codice('SELECT anagrafiche.fn_revoca_veste(NULL)'),
           pg_temp.codice('SELECT anagrafiche.fn_togli_revoca_veste(NULL)')),
    'E_SCRIPT_CHIAMATA_NON_VALIDA|E_SCRIPT_CHIAMATA_NON_VALIDA',
    '24) id NULL: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT * FROM finish();
ROLLBACK;
