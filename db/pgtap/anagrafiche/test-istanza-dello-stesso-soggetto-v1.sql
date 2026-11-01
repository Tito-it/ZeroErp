-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- L'istanza e il ruolo di una riga sono del suo soggetto (2026-10-19).
-- R-BE-15 del BE, decisioni D-17a … D-17d di Tid,
-- brief-db-processi-accensione-per-ambiente §6.17 (la richiesta) e §6.17.1
-- (la risposta). ChangeSet 20261019-80 … -85, il lock in
-- dbops.automation_lock_columns (anagrafiche.soggetti_ruoli.soggetto_id).
--
-- Elenco test (plan 17):
--  -- i due BB --
--  1)   fn_istanza_di_altro_soggetto: stesso soggetto, altro, istanza NULL, soggetto NULL
--  2)   fn_ruolo_di_altro_soggetto: gli stessi quattro casi
--  3)   i guard montati su indirizzi, conti del ruolo e contatti
--  -- indirizzi (la R-BE-15) --
--  4)   la madre con l'istanza di un altro soggetto: E_ISTANZA_ALTRO_SOGGETTO, campo istanza_utility_id
--  5)   la madre con l'istanza dello stesso soggetto: passa
--  6)   la madre senza istanza: passa
--  7)   UPDATE dell'istanza verso quella di un altro soggetto: rifiutato
--  8)   UPDATE del ruolo verso quello di un altro soggetto: rifiutato
--  9)   UPDATE che non tocca ruolo e istanza: passa
--  -- conti del ruolo (D-17a) --
--  10)  INSERT con l'istanza di un altro soggetto: rifiutato
--  11)  INSERT con l'istanza dello stesso soggetto: passa
--  12)  UPDATE dell'istanza verso quella di un altro soggetto: rifiutato
--  -- contatti (D-17a) --
--  13)  il ruolo di un altro soggetto: E_RUOLO_ALTRO_SOGGETTO, campo soggetto_ruolo_id
--  14)  l'istanza di un altro soggetto: E_ISTANZA_ALTRO_SOGGETTO
--  15)  ruolo e istanza del soggetto, e il contatto del solo soggetto: passano
--  16)  UPDATE del soggetto del contatto (il ruolo resta dell'altro): rifiutato
--  -- la porta del ruolo (D-17d) --
--  17)  UPDATE del soggetto di un ruolo: E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE
--       (il trigger lo monta il runner dei lock: 90_end/20261019-86, poi il
--       ci_apply e il job serale lo tengono a convergenza)
--
-- Scopo:
--  - provare la regola COSTRUENDO due clienti (soggetto, ruolo, istanza, BA)
--    coi builder: regola zero, il test non legge le righe di oggi.
--  - asserire il CODICE (canale CONSTRAINT) e il CAMPO (canale COLUMN), non
--    un P0001 qualsiasi: un altro guard che rifiutasse prima farebbe passare
--    il test per la ragione sbagliata.
--  - la regressione del BA e delle pratiche, che passano dai BB, sta nei loro
--    test (anagrafiche/test-trgfn-billing-account-guard-soggetto-coerenza-istanza-v1,
--    pratiche/test-guard-contesto-pratica).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- I builder creano il soggetto (padre) e i suoi indirizzi nella stessa
-- chiamata, e aprono e richiudono da se' la finestra dei differiti.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

-- L'esito di un'istruzione: 'ok', oppure il codice di dominio e il campo
-- (canali CONSTRAINT e COLUMN di script.fn_log_and_raise_error), oppure lo
-- SQLSTATE e il messaggio per un errore che non e' di dominio.
CREATE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE
    v_codice text;
    v_campo  text;
    v_stato  text;
    v_msg    text;
BEGIN
    EXECUTE p_sql;
    RETURN 'ok';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME, v_campo = COLUMN_NAME,
                            v_stato = RETURNED_SQLSTATE, v_msg = MESSAGE_TEXT;
    IF v_stato = 'P0001' AND v_codice <> '' THEN
        RETURN v_codice || '/' || COALESCE(NULLIF(v_campo, ''), '-');
    END IF;
    RETURN v_stato || ': ' || v_msg;
END;
$f$;

-- ============================================================
-- Fixture: due clienti, A e B, ognuno con la sua istanza
-- ============================================================
CREATE TEMP TABLE _a ON COMMIT DROP AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgTAP istanza stesso soggetto A');

CREATE TEMP TABLE _b ON COMMIT DROP AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgTAP istanza stesso soggetto B');

CREATE TEMP TABLE _f ON COMMIT DROP AS
SELECT a.soggetto_id AS sogg_a, a.soggetto_ruolo_id AS sr_a, a.istanza_utility_id AS ist_a,
       b.soggetto_id AS sogg_b, b.soggetto_ruolo_id AS sr_b, b.istanza_utility_id AS ist_b,
       (SELECT tc.id FROM config.tipi_contatti tc ORDER BY tc.id LIMIT 1) AS tipo_contatto_id,
       -- un tipo che il soggetto A non ha ancora (il builder gli crea dei
       -- contatti): il contatto del solo soggetto non urta uq_contatti_soggetto_tipo
       (SELECT tc.id FROM config.tipi_contatti tc
         WHERE NOT EXISTS (SELECT 1 FROM anagrafiche.contatti c
                            WHERE c.soggetto_id = a.soggetto_id
                              AND c.soggetto_ruolo_id IS NULL
                              AND c.istanza_utility_id IS NULL
                              AND c.tipo_contatto_id = tc.id)
         ORDER BY tc.id LIMIT 1) AS tipo_contatto_libero
  FROM _a a, _b b;

-- Un indirizzo libero valido per l'Italia, nella forma che il guard pretende;
-- il tipo e l'istanza si aggiungono caso per caso. Per il cliente sono
-- ammessi POSTA, SPED, RES.
CREATE TEMP TABLE _el ON COMMIT DROP AS
SELECT jsonb_strip_nulls(
           jsonb_build_object('indirizzo_libero', 'Via pgTAP istanza 1',
                              'stato_id', script.fn_stato_id_da_iso2('IT'))
           || to_jsonb(fm)) AS base
  FROM dbops.fn_pgtap_indirizzo_libero_forma(script.fn_stato_id_da_iso2('IT')) fm;

-- ============================================================
-- 1-3) I due BB e i guard montati
-- ============================================================
SELECT is(
    (SELECT ROW(anagrafiche.fn_istanza_di_altro_soggetto(f.ist_a, f.sogg_a),
                anagrafiche.fn_istanza_di_altro_soggetto(f.ist_a, f.sogg_b),
                anagrafiche.fn_istanza_di_altro_soggetto(NULL, f.sogg_a),
                anagrafiche.fn_istanza_di_altro_soggetto(f.ist_a, NULL))::text
       FROM _f f),
    (SELECT ROW(NULL::uuid, f.sogg_a, NULL::uuid, NULL::uuid)::text FROM _f f),
    '1) fn_istanza_di_altro_soggetto: NULL se e'' lo stesso, il soggetto dell''istanza se e'' un altro, NULL senza istanza o senza soggetto');

SELECT is(
    (SELECT ROW(anagrafiche.fn_ruolo_di_altro_soggetto(f.sr_a, f.sogg_a),
                anagrafiche.fn_ruolo_di_altro_soggetto(f.sr_a, f.sogg_b),
                anagrafiche.fn_ruolo_di_altro_soggetto(NULL, f.sogg_a),
                anagrafiche.fn_ruolo_di_altro_soggetto(f.sr_a, NULL))::text
       FROM _f f),
    (SELECT ROW(NULL::uuid, f.sogg_a, NULL::uuid, NULL::uuid)::text FROM _f f),
    '2) fn_ruolo_di_altro_soggetto: gli stessi quattro casi');

SELECT is(
    (SELECT string_agg(c.relname || ':' || t.tgname, ' ' ORDER BY c.relname)
       FROM pg_trigger t
       JOIN pg_class c ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'anagrafiche'
        AND NOT t.tgisinternal
        AND t.tgfoid IN ('anagrafiche.trgfn_guard_istanza_del_ruolo()'::regprocedure,
                         'anagrafiche.trgfn_contatti_guard_contesto_soggetto()'::regprocedure)),
    'contatti:trg_contatti_a10_guard_contesto_soggetto_ins_upd '
    'indirizzi:trg_indirizzi_a10_guard_istanza_ins_upd '
    'soggetti_ruoli_conti_bancari:trg_soggetti_ruoli_conti_bancari_a10_guard_istanza_ins_upd',
    '3) i guard montati su contatti, indirizzi e conti del ruolo');

-- ============================================================
-- 4-9) Indirizzi
-- ============================================================
SELECT is(
    (SELECT pg_temp.esito(format(
         'SELECT anagrafiche.fn_crea_indirizzo_ruolo(%s, %L::jsonb)',
         f.sr_a, e.base || jsonb_build_object('tipo_indirizzo_codice_interno', 'SPED',
                                              'istanza_utility_id', f.ist_b)))
       FROM _f f, _el e),
    'E_ISTANZA_ALTRO_SOGGETTO/istanza_utility_id',
    '4) indirizzo del ruolo di A con l''istanza di B: E_ISTANZA_ALTRO_SOGGETTO sul campo istanza_utility_id');

CREATE TEMP TABLE _ind ON COMMIT DROP AS
SELECT anagrafiche.fn_crea_indirizzo_ruolo(
           f.sr_a, e.base || jsonb_build_object('tipo_indirizzo_codice_interno', 'SPED',
                                                'istanza_utility_id', f.ist_a)) AS id
  FROM _f f, _el e;

SELECT is(
    (SELECT i.istanza_utility_id FROM anagrafiche.indirizzi i, _ind WHERE i.id = _ind.id),
    (SELECT ist_a FROM _f),
    '5) indirizzo del ruolo di A con l''istanza di A: passa');

SELECT is(
    (SELECT pg_temp.esito(format(
         'SELECT anagrafiche.fn_crea_indirizzo_ruolo(%s, %L::jsonb)',
         f.sr_a, e.base || jsonb_build_object('tipo_indirizzo_codice_interno', 'POSTA')))
       FROM _f f, _el e),
    'ok',
    '6) indirizzo del ruolo di A senza istanza: passa');

SELECT is(
    (SELECT pg_temp.esito(format(
         'UPDATE anagrafiche.indirizzi SET istanza_utility_id = %s WHERE id = %s', f.ist_b, _ind.id))
       FROM _f f, _ind),
    'E_ISTANZA_ALTRO_SOGGETTO/istanza_utility_id',
    '7) UPDATE: l''indirizzo di A passa all''istanza di B: rifiutato');

SELECT is(
    (SELECT pg_temp.esito(format(
         'UPDATE anagrafiche.indirizzi SET soggetto_ruolo_id = %s WHERE id = %s', f.sr_b, _ind.id))
       FROM _f f, _ind),
    'E_ISTANZA_ALTRO_SOGGETTO/istanza_utility_id',
    '8) UPDATE: l''indirizzo dell''istanza di A passa al ruolo di B: rifiutato');

SELECT is(
    (SELECT pg_temp.esito(format(
         'UPDATE anagrafiche.indirizzi SET storicizza = storicizza WHERE id = %s', _ind.id))
       FROM _ind),
    'ok',
    '9) UPDATE che non tocca ruolo e istanza: passa');

-- ============================================================
-- 10-12) Conti del ruolo
-- ============================================================
CREATE TEMP TABLE _bb ON COMMIT DROP AS
SELECT bank_branch_id AS id
  FROM dbops.fn_pgtap_crea_filiale_bancaria('pgTAP istanza stesso soggetto');

CREATE TEMP TABLE _cb ON COMMIT DROP AS
WITH ins AS (
    INSERT INTO anagrafiche.conti_bancari (iban, bic_swift, intestatario_predefinito, paese,
                                           attivo, verificato, meta, bank_branch_id)
    SELECT 'IT77Z0000000000000000000077', 'BGFNOIT2XXX', 'pgTAP istanza stesso soggetto', 'IT',
           TRUE, FALSE, '{}'::jsonb, _bb.id
      FROM _bb
    RETURNING id
) SELECT id FROM ins;

SELECT is(
    (SELECT pg_temp.esito(format(
         'INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, istanza_utility_id, valido_dal, verificato, bloccato, meta) '
         'VALUES (%s, %s, ''GENERICO'', FALSE, %s, script.fn_data_operativa(), FALSE, FALSE, ''{}''::jsonb)',
         f.sr_a, _cb.id, f.ist_b))
       FROM _f f, _cb),
    'E_ISTANZA_ALTRO_SOGGETTO/istanza_utility_id',
    '10) conto del ruolo di A con l''istanza di B: rifiutato');

CREATE TEMP TABLE _srcb ON COMMIT DROP AS
WITH ins AS (
    INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari (soggetto_ruolo_id, conto_bancario_id, uso,
                                                          predefinito, istanza_utility_id, valido_dal,
                                                          verificato, bloccato, meta)
    SELECT f.sr_a, _cb.id, 'GENERICO', FALSE, f.ist_a, script.fn_data_operativa(), FALSE, FALSE, '{}'::jsonb
      FROM _f f, _cb
    RETURNING id
) SELECT id FROM ins;

SELECT is(
    (SELECT count(*)::int FROM _srcb),
    1,
    '11) conto del ruolo di A con l''istanza di A: passa');

SELECT is(
    (SELECT pg_temp.esito(format(
         'UPDATE anagrafiche.soggetti_ruoli_conti_bancari SET istanza_utility_id = %s WHERE id = %s',
         f.ist_b, _srcb.id))
       FROM _f f, _srcb),
    'E_ISTANZA_ALTRO_SOGGETTO/istanza_utility_id',
    '12) UPDATE: il conto di A passa all''istanza di B: rifiutato');

-- ============================================================
-- 13-16) Contatti
-- ============================================================
SELECT is(
    (SELECT pg_temp.esito(format(
         'SELECT anagrafiche.fn_crea_contatto(%L::uuid, %s, %L::jsonb)',
         f.sogg_a, f.sr_b,
         jsonb_build_object('tipo_contatto_id', f.tipo_contatto_id, 'nominativo', 'pgTAP 13')))
       FROM _f f),
    'E_RUOLO_ALTRO_SOGGETTO/soggetto_ruolo_id',
    '13) contatto di A sul ruolo di B: E_RUOLO_ALTRO_SOGGETTO sul campo soggetto_ruolo_id');

SELECT is(
    (SELECT pg_temp.esito(format(
         'SELECT anagrafiche.fn_crea_contatto(%L::uuid, %s, %L::jsonb)',
         f.sogg_a, f.sr_a,
         jsonb_build_object('tipo_contatto_id', f.tipo_contatto_id, 'nominativo', 'pgTAP 14',
                            'istanza_utility_id', f.ist_b)))
       FROM _f f),
    'E_ISTANZA_ALTRO_SOGGETTO/istanza_utility_id',
    '14) contatto di A con l''istanza di B: E_ISTANZA_ALTRO_SOGGETTO');

CREATE TEMP TABLE _ct ON COMMIT DROP AS
SELECT (anagrafiche.fn_crea_contatto(
            f.sogg_a, f.sr_a,
            jsonb_build_object('tipo_contatto_id', f.tipo_contatto_id, 'nominativo', 'pgTAP 15',
                               'istanza_utility_id', f.ist_a)) ->> 'id')::bigint AS id
  FROM _f f;

SELECT is(
    (SELECT (SELECT count(*)::int FROM _ct WHERE id IS NOT NULL)::text || '|' ||
            pg_temp.esito(format(
                'SELECT anagrafiche.fn_crea_contatto(%L::uuid, NULL, %L::jsonb)',
                f.sogg_a,
                jsonb_build_object('tipo_contatto_id', f.tipo_contatto_libero, 'nominativo', 'pgTAP 15 bis')))
       FROM _f f),
    '1|ok',
    '15) contatto di A sul ruolo e sull''istanza di A, e contatto del solo soggetto A: passano');

SELECT is(
    (SELECT pg_temp.esito(format(
         'UPDATE anagrafiche.contatti SET soggetto_id = %L::uuid WHERE id = %s', f.sogg_b, _ct.id))
       FROM _f f, _ct),
    'E_RUOLO_ALTRO_SOGGETTO/soggetto_ruolo_id',
    '16) UPDATE: il contatto passa al soggetto B e resta sul ruolo di A: rifiutato');

-- ============================================================
-- 17) La porta del ruolo: il suo soggetto non cambia
-- ============================================================
SELECT is(
    (SELECT split_part(pg_temp.esito(format(
         'UPDATE anagrafiche.soggetti_ruoli SET soggetto_id = %L::uuid WHERE id = %s', f.sogg_b, f.sr_a)),
         '/', 1)
       FROM _f f),
    'E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE',
    '17) UPDATE del soggetto di un ruolo: E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE (lock di colonna)');

SELECT * FROM finish();
ROLLBACK;
