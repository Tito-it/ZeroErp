-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la RLS di dbops.coda_lavori e' accesa dal 20261107-57
--   (blocco 5b di brief-db-revisione-dbops), ma il proprietario non la subisce
--   (FORCE spento per scelta, linee-guida-sql §10.5). Per esercitarla da owner
--   la transazione accende FORCE ROW LEVEL SECURITY, che solo il proprietario
--   puo' dare e che il ROLLBACK spegne. L'ENABLE no: e' del changeSet, e il
--   test 15 lo pretende.
-- pgTAP test per Zero ERP
-- Test: RLS su dbops.coda_lavori — policy rls_coda_lavori_ef_perimetro
--       (20261107-54) e la sua regola script.fn_scope_coda_lavori_perimetro
--       (20261107-52). Brief: brief-db-revisione-dbops, giro 5 (Q14 ③).
--
-- ⭐ LA REGOLA. Un lavoro OPERATORE lo vede chi ha la sua azienda nel perimetro;
--   un lavoro SISTEMA il super admin e l'identita' tecnica viva del drenatore
--   (draina_coda_lavori). Il drenatore lavora un'azienda alla volta: vede i
--   lavori OPERATORE solo col perimetro del suo utente tecnico.
--
-- ⛔ LA FIXTURE SI COSTRUISCE: tre aziende, ognuna col suo utente. IO e ALTRO
--   con dbops.fn_pgtap_crea_emittente_operatore(); DREN con
--   dbops.fn_pgtap_crea_roster_processo('draina_coda_lavori'), cioe' l'utente
--   tecnico del drenatore per la sua azienda. Un lavoro OPERATORE per ognuna e
--   un lavoro SISTEMA, tutti in ERRORE (nessuno vivo: non li prende nessun
--   drenatore e non pestano la chiave dei lavori veri).
--
-- ⚠️ Fail-closed sul RUOLO (test 9): si svuota app.ruolo_applicativo, non
--   app.current_user_id — un utente vuoto non e' «nessuno», e' un perimetro
--   che il risolutore legge a modo suo (vedi rls/test-rls-fatture-stampa-coda).
-- ⚠️ Il super admin non si costruisce qui: il suo ramo (perimetro NULL, flag
--   super admin) si prova sulla funzione pura, test 4.
-- ------------------------------------------------------------
-- Indice test (1..14):
--   STRUTTURA
--   1)  la policy esiste, PERMISSIVE e FOR ALL
--   2)  la policy chiama la regola con chi guarda in tre sottoquery
--   3)  USING e WITH CHECK dicono la stessa cosa
--   4)  la regola, sui valori: OPERATORE nel/fuori dal perimetro, perimetro
--       NULL, SISTEMA da super admin, da drenatore, da altri, run_as ignoto
--   COMPORTAMENTO (RLS armata nella transazione)
--   5)  l'operatore vede il lavoro della sua azienda
--   6)  non vede quello di un'altra azienda
--   7)  non vede il lavoro SISTEMA
--   8)  il drenatore vede il lavoro della sua azienda e il lavoro SISTEMA
--   9)  il drenatore non vede il lavoro di un'altra azienda
--  10)  senza veste dichiarata: nessuna riga
--  11)  la vista di presidio, letta da una persona, mostra il suo perimetro
--  12)  una scrittura nel perimetro passa (archiviazione)
--  13)  ⛔ WITH CHECK: spostare un lavoro nell'azienda di un altro e' respinto
--  14)  ⛔ un altro perimetro non scrive il lavoro (USING: zero righe)
--   POSTURA
--  15)  la RLS e' accesa dal changeSet, non dal test
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- Fixture: il mondo, POI il contesto
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'IO'    AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'ALTRO' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'DREN'  AS lato, emittente_fiscale_id, emittente_codice, emittente_soggetto_ruolo_id,
       auth_user_id, identita_id
  FROM dbops.fn_pgtap_crea_roster_processo('draina_coda_lavori');

-- I lavori: uno OPERATORE per azienda, uno SISTEMA. In ERRORE: nessuno e' vivo.
CREATE TEMP TABLE _lavori AS
WITH op AS (
    INSERT INTO dbops.coda_lavori
        (job_type, payload, run_as, scope, emittente_fiscale_id, origine, stato,
         tentativi, max_tentativi)
    SELECT 'CHIUSURA_SCADENZE', jsonb_build_object('pgtap', m.lato), 'OPERATORE',
           jsonb_build_object('auth_user_id', m.auth_user_id, 'username', 'pgtap',
                              'identita_id', m.identita_id,
                              'emittente_attivo_id', m.emittente_fiscale_id,
                              'emittente_ids', jsonb_build_array(m.emittente_fiscale_id)),
           m.emittente_fiscale_id, 'CRON', 'ERRORE', 1, 1
      FROM _mondi m
    RETURNING id, payload ->> 'pgtap' AS lato
), si AS (
    INSERT INTO dbops.coda_lavori
        (job_type, payload, run_as, scope, emittente_fiscale_id, origine, stato,
         tentativi, max_tentativi)
    VALUES ('NOTIFICA_DIGEST_MUTO', '{"pgtap": "SISTEMA"}'::jsonb, 'SISTEMA', NULL, NULL,
            'CRON', 'ERRORE', 1, 1)
    RETURNING id, 'SISTEMA'::text AS lato
)
SELECT * FROM op UNION ALL SELECT * FROM si;

-- Quanti lavori della fixture vede chi e' in sessione, per lato.
CREATE FUNCTION pg_temp.visti() RETURNS text
LANGUAGE sql AS $$
    SELECT coalesce(string_agg(l.lato, ',' ORDER BY l.lato), '')
      FROM dbops.coda_lavori c
      JOIN _lavori l ON l.id = c.id
$$;

-- Un UPDATE che restituisce quante righe ha scritto (una CTE di scrittura non
-- sta dentro un'asserzione).
CREATE FUNCTION pg_temp.archivia(p_id bigint, p_archiviato boolean) RETURNS bigint
LANGUAGE plpgsql AS $$
DECLARE v_n bigint;
BEGIN
    UPDATE dbops.coda_lavori SET archiviato = p_archiviato WHERE id = p_id;
    GET DIAGNOSTICS v_n = ROW_COUNT;
    RETURN v_n;
END $$;

CREATE FUNCTION pg_temp.come(p_lato text) RETURNS void
LANGUAGE sql AS $$
    SELECT script.fn_pgtap_set_contesto_operatore(
               (SELECT m.auth_user_id::integer FROM _mondi m WHERE m.lato = p_lato));
$$;

-- ============================================================
-- 1-4) Struttura e regola
-- ============================================================
SELECT is(
    (SELECT p.permissive || '/' || p.cmd
       FROM pg_policies p
      WHERE p.schemaname = 'dbops'
        AND p.tablename  = 'coda_lavori'
        AND p.policyname = 'rls_coda_lavori_ef_perimetro'),
    'PERMISSIVE/ALL',
    '1) la policy esiste, PERMISSIVE e FOR ALL: il drenatore e l''interfaccia ci scrivono');

-- ⚠️ pg_policies.qual dipende dal search_path: si legge con quello del catalogo.
SET LOCAL search_path = pg_catalog, public;
SELECT ok(
    (SELECT p.qual ~ 'fn_scope_coda_lavori_perimetro\(\( SELECT script\.fn_is_super_admin'
        AND p.qual ~ '\( SELECT script\.fn_scope_identita_processo\(.*''draina_coda_lavori''::text\)'
        AND p.qual ~ '\( SELECT script\.fn_get_emittenti_scope_pk_ids\('
       FROM pg_policies p
      WHERE p.policyname = 'rls_coda_lavori_ef_perimetro'),
    '2) la policy passa alla regola chi guarda in tre sottoquery: super admin, drenatore, perimetro');

SELECT is(
    (SELECT p.with_check FROM pg_policies p WHERE p.policyname = 'rls_coda_lavori_ef_perimetro'),
    (SELECT p.qual       FROM pg_policies p WHERE p.policyname = 'rls_coda_lavori_ef_perimetro'),
    '3) USING e WITH CHECK dicono la stessa cosa: una riga non esce dal perimetro di chi la scrive');
RESET search_path;

SELECT is_empty(
    $$SELECT caso
        FROM (VALUES
            ('OPERATORE nel perimetro',       false, false, ARRAY[1,2]::bigint[], 'OPERATORE', 2::bigint, true),
            ('OPERATORE fuori perimetro',     false, false, ARRAY[1]::bigint[],   'OPERATORE', 2::bigint, false),
            ('OPERATORE, drenatore fuori',    false, true,  ARRAY[1]::bigint[],   'OPERATORE', 2::bigint, false),
            ('OPERATORE, perimetro NULL',     true,  false, NULL::bigint[],       'OPERATORE', 2::bigint, true),
            ('OPERATORE, perimetro vuoto',    false, false, '{}'::bigint[],       'OPERATORE', 2::bigint, false),
            ('SISTEMA da super admin',        true,  false, NULL::bigint[],       'SISTEMA',   NULL::bigint, true),
            ('SISTEMA dal drenatore',         false, true,  ARRAY[1]::bigint[],   'SISTEMA',   NULL::bigint, true),
            ('SISTEMA da un operatore',       false, false, ARRAY[1]::bigint[],   'SISTEMA',   NULL::bigint, false),
            ('SISTEMA, risposte NULL',        NULL,  NULL,  ARRAY[1]::bigint[],   'SISTEMA',   NULL::bigint, false),
            ('run_as ignoto',                 true,  true,  NULL::bigint[],       'ALTRO',     2::bigint, false)
        ) AS t(caso, sa, pr, perim, run_as, ef, atteso)
       WHERE script.fn_scope_coda_lavori_perimetro(sa, pr, perim, run_as, ef) IS DISTINCT FROM atteso$$,
    '4) la regola sui valori: OPERATORE col perimetro, SISTEMA a super admin e drenatore, il resto no (mai NULL)');

-- ============================================================
-- 5-14) Chi vede e scrive cosa: la RLS e' accesa (20261107-57); FORCE, solo
--   per questa transazione, la fa subire anche al proprietario che esegue
-- ============================================================
-- ⚠️ Prima dell'apply del 20261107-57 i test 5-15 sono rossi: FORCE senza
--   ENABLE non arma niente. E' il segnale giusto, non un rosso da curare qui.
ALTER TABLE dbops.coda_lavori FORCE ROW LEVEL SECURITY;

SELECT pg_temp.come('IO');

SELECT ok(
    pg_temp.visti() ~ '(^|,)IO(,|$)',
    '5) l''operatore vede il lavoro della sua azienda');

SELECT ok(
    pg_temp.visti() !~ 'ALTRO|DREN',
    '6) l''operatore non vede i lavori delle altre aziende');

SELECT ok(
    pg_temp.visti() !~ 'SISTEMA',
    '7) l''operatore non vede il lavoro SISTEMA: non ha azienda, e lui non e'' ne'' super admin ne'' drenatore');

SELECT pg_temp.come('DREN');

SELECT ok(
    pg_temp.visti() ~ '(^|,)DREN(,|$)' AND pg_temp.visti() ~ 'SISTEMA',
    '8) il drenatore vede il lavoro della sua azienda e il lavoro SISTEMA');

SELECT ok(
    pg_temp.visti() !~ '(^|,)(IO|ALTRO)(,|$)',
    '9) il drenatore non vede i lavori di un''altra azienda: lavora un''azienda alla volta');

SELECT pg_temp.come('IO');
SELECT set_config('app.ruolo_applicativo', '', true);

SELECT is(
    pg_temp.visti(),
    '',
    '10) senza veste dichiarata nessuna riga: il gate della policy e'' fail-closed');

SELECT pg_temp.come('IO');

-- ⭐ La vista e' security_invoker (20261107-55): una persona legge col suo
--   perimetro, anche sulla vista di presidio.
SELECT is(
    (SELECT coalesce(string_agg(l.lato, ',' ORDER BY l.lato), '')
       FROM dbops.vw_coda_lavori_da_guardare v
       JOIN _lavori l ON l.id = v.id),
    'IO',
    '11) la vista di presidio, letta dall''operatore, mostra solo i lavori del suo perimetro');

SELECT is(
    pg_temp.archivia((SELECT id FROM _lavori WHERE lato = 'IO'), true),
    1::bigint,
    '12) una scrittura nel perimetro passa: l''archiviazione del proprio lavoro');

SELECT throws_ok(
    format($$UPDATE dbops.coda_lavori
                SET scope = scope || jsonb_build_object('emittente_attivo_id', %s),
                    emittente_fiscale_id = %s
              WHERE id = %s$$,
           (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'ALTRO'),
           (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'ALTRO'),
           (SELECT id FROM _lavori WHERE lato = 'IO')),
    '42501',
    NULL,
    '13) WITH CHECK: spostare il proprio lavoro nell''azienda di un altro e'' respinto');

SELECT pg_temp.come('ALTRO');

SELECT is(
    pg_temp.archivia((SELECT id FROM _lavori WHERE lato = 'IO'), false),
    0::bigint,
    '14) un operatore di un altro perimetro non scrive il lavoro: USING non glielo mostra');

-- ============================================================
-- 15) Postura: l'ENABLE e' del changeSet
-- ============================================================
-- ⭐ Il test non accende piu' la RLS: se la tabella la perdesse (un DISABLE a
--   mano, il rollback del 20261107-57) i test 5-14 sarebbero rossi, e questo
--   dice perche'. Il FORCE locale non conta: e' relforcerowsecurity, un'altra
--   colonna, e il ROLLBACK lo spegne (lo presidia test-postura-proprietario-rls-v1).
SELECT ok(
    (SELECT c.relrowsecurity FROM pg_class c WHERE c.oid = 'dbops.coda_lavori'::regclass),
    '15) la row level security di dbops.coda_lavori e'' accesa dal changeSet 20261107-57');

SELECT * FROM finish();
ROLLBACK;
