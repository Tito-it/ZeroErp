-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'unicita' delle vesti accese su anagrafiche.identita_digitali
-- ChangeSet: 20261127-48 (una veste accesa per credenziale, soggetto e tipo;
--            i due indici di prima ristretti a OPERATORE e API_CLIENT)
-- Brief: brief-db-accessi-area-clienti, giro 4 (D-M7, D-M8, D-G4-1)
--
-- Il modello:
--   - per i portali, una veste accesa per (credenziale, ruolo anagrafico, tipo):
--     un cliente o un fornitore ha piu' referenti (D-M7), un referente entra
--     per piu' soggetti (D-M8);
--   - per l'operatore, una veste accesa per credenziale e una per persona,
--     come prima (D-G4-1);
--   - le vesti spente non contano.
--
-- ⭐ Casi COSTRUITI (prima del 2026-11-28 il test pescava clienti liberi dalla
--   popolazione del database e saltava i casi se non ne trovava). Ogni caso
--   dice CHI lo rifiuta: dbops.fn_pgtap_codice_errore rende il nome dell'indice
--   violato, o NULL se l'istruzione passa.
--
-- Gira come l'applicazione (runner di default). Le vesti le inserisce l'app
-- spente, come il backend; le accende la fixture dbops.fn_pgtap_imposta_veste,
-- l'unica strada dell'app dopo il 20261127-09.
--
-- Elenco test (plan 9):
--    1) forma: i tre indici unici e le loro colonne
--    2) due referenti dello stesso cliente: passa (D-M7)
--    3) una persona referente di due clienti: passa (D-M8)
--    4) la porta dei fornitori, stessa regola: due fornitori per una persona,
--       due persone per un fornitore (D-M8)
--    5) la stessa persona due volte sullo stesso cliente e tipo: la rifiuta
--       uq_identita_digitali_credenziale_sr_ruolo_attivo
--    6) ...spenta invece passa: le vesti spente non contano
--    7) due tipi diversi sullo stesso cliente e la stessa persona: passa
--    8) un operatore e' uno per credenziale: la seconda veste OPERATORE accesa
--       la rifiuta uq_identita_digitali_auth_user_ruolo_attivo
--    9) un operatore e' uno per persona: una seconda credenziale sulla stessa
--       persona la rifiuta uq_identita_digitali_sr_ruolo_attivo
-- ------------------------------------------------------------
BEGIN;

-- Gli operatori prima del contesto, come le altre fixture dell'operatore.
CREATE TEMP TABLE _op AS
SELECT 'A'::text AS nome, o.auth_user_id, o.identita_id, o.soggetto_ruolo_id AS sr_id
  FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP g4 operatore A') o
UNION ALL
SELECT 'B', o.auth_user_id, o.identita_id, o.soggetto_ruolo_id
  FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP g4 operatore B') o;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- Fixture
-- ============================================================
-- Due clienti e due fornitori, ognuno col suo ruolo anagrafico.
CREATE TEMP TABLE _sr (nome text PRIMARY KEY, sr_id bigint);
INSERT INTO _sr
SELECT 'cli1', c.soggetto_ruolo_id FROM dbops.fn_pgtap_crea_cliente_ba('g4-uniq-cli1') c;
INSERT INTO _sr
SELECT 'cli2', c.soggetto_ruolo_id FROM dbops.fn_pgtap_crea_cliente_ba('g4-uniq-cli2') c;
INSERT INTO _sr
VALUES ('fo1', dbops.fn_pgtap_crea_soggetto_ruolo(dbops.fn_pgtap_crea_soggetto_pg('pgTAP g4 fornitore uno'), 'FO')),
       ('fo2', dbops.fn_pgtap_crea_soggetto_ruolo(dbops.fn_pgtap_crea_soggetto_pg('pgTAP g4 fornitore due'), 'FO'));
SET CONSTRAINTS ALL IMMEDIATE;

-- Credenziali nude, con un nome che non collide.
CREATE TEMP TABLE _c (nome text PRIMARY KEY, auth_user_id integer);  -- ⚠️ niente %TYPE su django.*
DO $$
DECLARE v_nome text;  -- un'etichetta del test, non una colonna
BEGIN
    FOREACH v_nome IN ARRAY ARRAY['mario', 'anna', 'x'] LOOP
        WITH u AS (
            INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                                          first_name, last_name, email, date_joined)
            VALUES ('_pgtap_g4_' || v_nome || '_' || substring(md5(clock_timestamp()::text) FROM 1 FOR 8),
                    '!', false, false, false, '', '', '', now())
            RETURNING id
        )
        INSERT INTO _c SELECT v_nome, u.id FROM u;
    END LOOP;
END $$;

-- Una veste: nasce spenta, come dal backend, e la fixture la accende.
CREATE OR REPLACE FUNCTION pg_temp.veste(p_auth integer, p_sr bigint, p_ruolo text, p_accesa boolean)
RETURNS void
LANGUAGE plpgsql AS $$
DECLARE
    v_id anagrafiche.identita_digitali.id%TYPE;
BEGIN
    INSERT INTO anagrafiche.identita_digitali (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    VALUES (p_sr, p_auth, p_ruolo::config.ruolo_applicativo, false)
    RETURNING id INTO v_id;
    IF p_accesa THEN
        PERFORM dbops.fn_pgtap_imposta_veste(v_id, jsonb_build_object('attivo', true));
    END IF;
END $$;

-- Chi rifiuta l'istruzione: il nome dell'indice, o «passa».
CREATE OR REPLACE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE sql AS $$ SELECT COALESCE(dbops.fn_pgtap_codice_errore(p_sql), 'passa') $$;

-- Mario e' gia' referente del cliente 1.
SELECT pg_temp.veste((SELECT auth_user_id FROM _c WHERE nome = 'mario'),
                     (SELECT sr_id FROM _sr WHERE nome = 'cli1'), 'CLIENTE_PORTALE', true);

-- ============================================================
-- 1 La forma
-- ============================================================
SELECT is(
    (SELECT string_agg(c.relname || '(' || k.colonne || ')', ' ' ORDER BY c.relname)
       FROM pg_index i
       JOIN pg_class c ON c.oid = i.indexrelid
       CROSS JOIN LATERAL (
            SELECT string_agg(a.attname::text, ',' ORDER BY x.ord) AS colonne
              FROM unnest(i.indkey) WITH ORDINALITY x(attnum, ord)
              JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = x.attnum) k
      WHERE i.indrelid = 'anagrafiche.identita_digitali'::regclass
        AND i.indisunique
        AND i.indpred IS NOT NULL),
    'uq_identita_digitali_auth_user_ruolo_attivo(auth_user_id,ruolo_applicativo) '
    || 'uq_identita_digitali_credenziale_sr_ruolo_attivo(auth_user_id,soggetto_ruolo_id,ruolo_applicativo) '
    || 'uq_identita_digitali_sr_ruolo_attivo(soggetto_ruolo_id,ruolo_applicativo)',
    '1) forma: una veste accesa per credenziale, soggetto e tipo; per credenziale e per soggetto solo l''operatore');

-- ============================================================
-- 2-4 Piu' referenti, piu' soggetti
-- ============================================================
SELECT is(
    pg_temp.esito(format($$SELECT pg_temp.veste(%s, %s, 'CLIENTE_PORTALE', true)$$,
                         (SELECT auth_user_id FROM _c WHERE nome = 'anna'),
                         (SELECT sr_id FROM _sr WHERE nome = 'cli1'))),
    'passa',
    '2) due referenti dello stesso cliente: Anna accanto a Mario');

SELECT is(
    pg_temp.esito(format($$SELECT pg_temp.veste(%s, %s, 'CLIENTE_PORTALE', true)$$,
                         (SELECT auth_user_id FROM _c WHERE nome = 'mario'),
                         (SELECT sr_id FROM _sr WHERE nome = 'cli2'))),
    'passa',
    '3) una persona referente di due clienti: Mario anche sul cliente 2');

SELECT is(
    pg_temp.esito(format($$SELECT pg_temp.veste(%1$s, %3$s, 'FORNITORE_PORTALE', true),
                                  pg_temp.veste(%1$s, %4$s, 'FORNITORE_PORTALE', true),
                                  pg_temp.veste(%2$s, %3$s, 'FORNITORE_PORTALE', true)$$,
                         (SELECT auth_user_id FROM _c WHERE nome = 'mario'),
                         (SELECT auth_user_id FROM _c WHERE nome = 'anna'),
                         (SELECT sr_id FROM _sr WHERE nome = 'fo1'),
                         (SELECT sr_id FROM _sr WHERE nome = 'fo2'))),
    'passa',
    '4) la porta dei fornitori: Mario su due fornitori, Anna accanto a lui sul primo');

-- ============================================================
-- 5-7 La chiave: persona, soggetto, tipo
-- ============================================================
SELECT is(
    pg_temp.esito(format($$SELECT pg_temp.veste(%s, %s, 'CLIENTE_PORTALE', true)$$,
                         (SELECT auth_user_id FROM _c WHERE nome = 'mario'),
                         (SELECT sr_id FROM _sr WHERE nome = 'cli1'))),
    'uq_identita_digitali_credenziale_sr_ruolo_attivo',
    '5) Mario due volte sul cliente 1 con lo stesso tipo: una veste accesa per persona, soggetto e tipo');

SELECT is(
    pg_temp.esito(format($$SELECT pg_temp.veste(%s, %s, 'CLIENTE_PORTALE', false)$$,
                         (SELECT auth_user_id FROM _c WHERE nome = 'mario'),
                         (SELECT sr_id FROM _sr WHERE nome = 'cli1'))),
    'passa',
    '6) ...una seconda veste spenta invece passa: le vesti spente non contano');

SELECT is(
    pg_temp.esito(format($$SELECT pg_temp.veste(%s, %s, 'SHOP_CUSTOMER', true)$$,
                         (SELECT auth_user_id FROM _c WHERE nome = 'mario'),
                         (SELECT sr_id FROM _sr WHERE nome = 'cli1'))),
    'passa',
    '7) due tipi diversi sullo stesso cliente e la stessa persona: passa');

-- ============================================================
-- 8-9 L'operatore, come prima
-- ============================================================
-- 8) L'operatore A prende una seconda veste OPERATORE sulla persona B, dopo che
--    la veste di B e' spenta: l'unico indice che resta da violare e' quello
--    per credenziale.
SELECT dbops.fn_pgtap_imposta_veste((SELECT identita_id FROM _op WHERE nome = 'B'),
                                    jsonb_build_object('attivo', false));

SELECT is(
    pg_temp.esito(format($$SELECT pg_temp.veste(%s, %s, 'OPERATORE', true)$$,
                         (SELECT auth_user_id FROM _op WHERE nome = 'A'),
                         (SELECT sr_id FROM _op WHERE nome = 'B'))),
    'uq_identita_digitali_auth_user_ruolo_attivo',
    '8) un operatore e'' uno per credenziale: la seconda veste OPERATORE accesa di A si ferma');

-- 9) Una credenziale nuda prende la veste OPERATORE della persona A, che ha gia'
--    la sua accesa: l'unico indice da violare e' quello per persona.
SELECT is(
    pg_temp.esito(format($$SELECT pg_temp.veste(%s, %s, 'OPERATORE', true)$$,
                         (SELECT auth_user_id FROM _c WHERE nome = 'x'),
                         (SELECT sr_id FROM _op WHERE nome = 'A'))),
    'uq_identita_digitali_sr_ruolo_attivo',
    '9) un operatore e'' uno per persona: una seconda credenziale accesa sulla persona A si ferma');

SELECT * FROM finish();
ROLLBACK;
