-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: dbops.fn_accoda_lavoro, la porta SECURITY DEFINER della coda
--       (20261107-53), e i vincoli dell'azienda di un lavoro (20261107-51).
--       Brief: brief-db-revisione-dbops, giro 5 (Q14 ③, D9).
--
-- ⭐ CHE COSA SI PROVA. La porta vede tutte le righe, quindi da una sessione
--   dell'applicazione controlla da se' cio' che la policy controllerebbe: un
--   lavoro OPERATORE si accoda solo a proprio nome e dentro il proprio
--   perimetro, e un lavoro vivo con la stessa chiave si restituisce solo se chi
--   chiama potrebbe vederlo. Un lavoro OPERATORE nasce dentro un'azienda.
--
-- ⚠️ DUE METÀ, SECONDO CHI GIRA. I rami «da sessione dell'applicazione» si
--   esercitano solo se session_user e' membro di zeroerp_app (il runner, come
--   app): da owner la porta si fida, ed e' il ramo che il test 16 prova. Ogni
--   meta' salta l'altra con skip() e il motivo.
--
-- ⛔ D9 NON SI COSTRUISCE QUI. La gara sta fra due istruzioni della stessa
--   funzione (l'INSERT che trova il vivo, la rilettura che non lo trova piu'):
--   una sessione sola non ci entra, e nemmeno un trigger, che scatta prima del
--   controllo del conflitto. Il test 6 presidia la FORMA: il ciclo dell'upsert
--   c'e'. I due esiti del conflitto (il vivo restituito, il vivo altrui
--   respinto) si provano nei test 10 e 14.
-- ------------------------------------------------------------
-- Indice test (1..16):
--   STRUTTURA
--   1)  SECURITY DEFINER
--   2)  search_path fissato
--   3)  ⛔ PUBLIC non la esegue
--   4)  zeroerp_app la esegue
--   5)  ⛔ zeroerp_job non la esegue (la raggiunge solo dalle procedure DEFINER)
--   6)  D9: il corpo ha il ciclo dell'upsert
--   L'AZIENDA DI UN LAVORO
--   7)  i due vincoli nuovi ci sono, con la loro definizione
--   8)  ⛔ colonna e scope che dicono due aziende diverse: respinto (CHECK)
--   9)  ⛔ un lavoro OPERATORE senza azienda nello scope: E_CODA_LAVORO_SENZA_EMITTENTE
--  10)  la colonna prende l'azienda dello scope; la stessa chiave restituisce lo stesso id
--   DA UNA SESSIONE DELL'APPLICAZIONE
--  11)  ⛔ scope a nome di un'altra persona: E_CODA_SCOPE_ALTRUI
--  12)  ⛔ azienda fuori dal perimetro: E_CODA_SCOPE_ALTRUI
--  13)  ⛔ senza veste OPERATORE: E_CODA_SCOPE_ALTRUI
--  14)  ⛔ un lavoro vivo con la stessa chiave in un'altra azienda: E_CODA_CHIAVE_ALTRUI
--  15)  un lavoro SISTEMA lo accoda anche un operatore
--   DA OWNER
--  16)  la porta si fida: lo scope di un'altra persona passa
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ============================================================
-- Fixture: due aziende, ognuna col suo operatore; POI il contesto
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'IO'    AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'ALTRO' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE _k AS
SELECT 'PGTAP-PORTA-' || txid_current()::text AS chiave,
       pg_catalog.pg_has_role(session_user, 'zeroerp_app', 'MEMBER') AS da_app;

CREATE FUNCTION pg_temp.come(p_lato text) RETURNS void
LANGUAGE sql AS $$
    SELECT script.fn_pgtap_set_contesto_operatore(
               (SELECT m.auth_user_id::integer FROM _mondi m WHERE m.lato = p_lato)),
           set_config('app.current_emittente_id', '', true);
$$;

-- Il codice applicativo di un rifiuto (fn_log_and_raise_error lo mette nel
-- CONSTRAINT_NAME della diagnostica).
CREATE FUNCTION pg_temp.codice_di(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

SELECT pg_temp.come('IO');

-- ============================================================
-- 1-6) Struttura
-- ============================================================
SELECT ok(
    (SELECT p.prosecdef FROM pg_proc p
      WHERE p.oid = 'dbops.fn_accoda_lavoro(text,jsonb,text,jsonb,text,smallint,timestamptz,integer,text)'::regprocedure),
    '1) la porta e'' SECURITY DEFINER: vede tutte le righe, sotto la policy');

SELECT ok(
    (SELECT 'search_path=pg_catalog, public, pg_temp' = ANY (p.proconfig) FROM pg_proc p
      WHERE p.oid = 'dbops.fn_accoda_lavoro(text,jsonb,text,jsonb,text,smallint,timestamptz,integer,text)'::regprocedure),
    '2) la porta fissa il search_path');

SELECT ok(
    NOT EXISTS (SELECT 1
                  FROM pg_proc p, aclexplode(p.proacl) a
                 WHERE p.oid = 'dbops.fn_accoda_lavoro(text,jsonb,text,jsonb,text,smallint,timestamptz,integer,text)'::regprocedure
                   AND a.grantee = 0
                   AND a.privilege_type = 'EXECUTE'),
    '3) PUBLIC non esegue la porta: fuori dall''applicazione la raggiunge solo il proprietario');

SELECT ok(
    has_function_privilege('zeroerp_app',
        'dbops.fn_accoda_lavoro(text,jsonb,text,jsonb,text,smallint,timestamptz,integer,text)', 'EXECUTE'),
    '4) zeroerp_app esegue la porta');

SELECT CASE WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zeroerp_job')
    THEN ok(NOT has_function_privilege('zeroerp_job',
                'dbops.fn_accoda_lavoro(text,jsonb,text,jsonb,text,smallint,timestamptz,integer,text)', 'EXECUTE'),
            '5) zeroerp_job non esegue la porta: i lavori di pgAgent ci arrivano dalle procedure DEFINER')
    ELSE skip('5) il ruolo zeroerp_job non c''e'' su questo database', 1)
END;

SELECT ok(
    (SELECT p.prosrc ~ 'LOOP' AND p.prosrc ~ 'EXIT WHEN v_id IS NOT NULL' FROM pg_proc p
      WHERE p.oid = 'dbops.fn_accoda_lavoro(text,jsonb,text,jsonb,text,smallint,timestamptz,integer,text)'::regprocedure),
    '6) D9: il corpo ha il ciclo dell''upsert (la gara non si costruisce in una sessione sola)');

-- ============================================================
-- 7-10) L'azienda di un lavoro
-- ============================================================
SELECT is(
    (SELECT string_agg(c.conname || ' ' || pg_get_constraintdef(c.oid), ' | ' ORDER BY c.conname)
       FROM pg_constraint c
      WHERE c.conrelid = 'dbops.coda_lavori'::regclass
        AND c.conname IN ('chk_coda_lavori_run_as_emittente', 'chk_coda_lavori_emittente_dallo_scope')),
    'chk_coda_lavori_emittente_dallo_scope CHECK ((NOT (emittente_fiscale_id IS DISTINCT FROM ((scope ->> ''emittente_attivo_id''::text))::bigint)))'
    || ' | chk_coda_lavori_run_as_emittente CHECK (((run_as = ''OPERATORE''::text) = (emittente_fiscale_id IS NOT NULL)))',
    '7) un lavoro OPERATORE ha un''azienda, uno SISTEMA no, e la colonna dice la stessa azienda dello scope');

SELECT throws_ok(
    format($$INSERT INTO dbops.coda_lavori (job_type, run_as, scope, emittente_fiscale_id, stato)
             VALUES ('CHIUSURA_SCADENZE', 'OPERATORE', %L::jsonb, %s, 'ERRORE')$$,
           dbops.fn_pgtap_scope_operatore((SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'ALTRO'))::text,
           (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'IO')),
    '23514',
    NULL,
    '8) colonna e scope che dicono due aziende diverse: il CHECK li respinge');

SELECT is(
    pg_temp.codice_di(format(
        $$SELECT dbops.fn_accoda_lavoro(p_job_type => 'CHIUSURA_SCADENZE', p_run_as => 'OPERATORE',
                                       p_scope => %L::jsonb, p_idempotency_key => %L)$$,
        (dbops.fn_pgtap_scope_operatore() - 'emittente_attivo_id')::text,
        (SELECT chiave FROM _k) || '-senza')),
    'E_CODA_LAVORO_SENZA_EMITTENTE',
    '9) un lavoro OPERATORE senza azienda nello scope non si accoda');

CREATE TEMP TABLE _primo AS
SELECT dbops.fn_accoda_lavoro(p_job_type => 'CHIUSURA_SCADENZE', p_run_as => 'OPERATORE',
                              p_scope => dbops.fn_pgtap_scope_operatore(),
                              p_idempotency_key => (SELECT chiave FROM _k)) AS id;

SELECT is(
    (SELECT c.emittente_fiscale_id::text || '/'
            || (dbops.fn_accoda_lavoro(p_job_type => 'CHIUSURA_SCADENZE', p_run_as => 'OPERATORE',
                                       p_scope => dbops.fn_pgtap_scope_operatore(),
                                       p_idempotency_key => (SELECT chiave FROM _k)) = c.id)::text
       FROM dbops.coda_lavori c WHERE c.id = (SELECT id FROM _primo)),
    (SELECT emittente_fiscale_id::text FROM _mondi WHERE lato = 'IO') || '/true',
    '10) la colonna prende l''azienda dello scope, e la stessa chiave restituisce lo stesso lavoro vivo');

-- ============================================================
-- 11-15) Da una sessione dell'applicazione
-- ============================================================
SELECT CASE WHEN (SELECT da_app FROM _k) THEN
    is(pg_temp.codice_di(format(
           $$SELECT dbops.fn_accoda_lavoro(p_job_type => 'CHIUSURA_SCADENZE', p_run_as => 'OPERATORE',
                                          p_scope => %L::jsonb)$$,
           (dbops.fn_pgtap_scope_operatore()
              || jsonb_build_object('auth_user_id', (SELECT auth_user_id FROM _mondi WHERE lato = 'ALTRO')))::text)),
       'E_CODA_SCOPE_ALTRUI',
       '11) uno scope a nome di un''altra persona non si accoda')
    ELSE skip('11) da owner la porta si fida: il ramo dell''applicazione lo prova il runner, come app', 1)
END;

SELECT CASE WHEN (SELECT da_app FROM _k) THEN
    is(pg_temp.codice_di(format(
           $$SELECT dbops.fn_accoda_lavoro(p_job_type => 'CHIUSURA_SCADENZE', p_run_as => 'OPERATORE',
                                          p_scope => %L::jsonb)$$,
           (dbops.fn_pgtap_scope_operatore()
              || jsonb_build_object('emittente_attivo_id', (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'ALTRO')))::text)),
       'E_CODA_SCOPE_ALTRUI',
       '12) un lavoro in un''azienda fuori dal perimetro non si accoda')
    ELSE skip('12) da owner la porta si fida: il ramo dell''applicazione lo prova il runner, come app', 1)
END;

CREATE TEMP TABLE _scope_io AS SELECT dbops.fn_pgtap_scope_operatore() AS s;
SELECT set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);

SELECT CASE WHEN (SELECT da_app FROM _k) THEN
    is(pg_temp.codice_di(format(
           $$SELECT dbops.fn_accoda_lavoro(p_job_type => 'CHIUSURA_SCADENZE', p_run_as => 'OPERATORE',
                                          p_scope => %L::jsonb)$$,
           (SELECT s FROM _scope_io)::text)),
       'E_CODA_SCOPE_ALTRUI',
       '13) senza la veste OPERATORE un lavoro OPERATORE non si accoda, nemmeno a proprio nome')
    ELSE skip('13) da owner la porta si fida: il ramo dell''applicazione lo prova il runner, come app', 1)
END;

-- La stessa chiave, prima nell'azienda ALTRO (dal suo operatore), poi da IO.
SELECT pg_temp.come('ALTRO');
CREATE TEMP TABLE _altrui AS
SELECT dbops.fn_accoda_lavoro(p_job_type => 'CHIUSURA_SCADENZE', p_run_as => 'OPERATORE',
                              p_scope => dbops.fn_pgtap_scope_operatore(),
                              p_idempotency_key => (SELECT chiave FROM _k) || '-altrui') AS id;
SELECT pg_temp.come('IO');

SELECT CASE WHEN (SELECT da_app FROM _k) THEN
    is(pg_temp.codice_di(format(
           $$SELECT dbops.fn_accoda_lavoro(p_job_type => 'CHIUSURA_SCADENZE', p_run_as => 'OPERATORE',
                                          p_scope => %L::jsonb, p_idempotency_key => %L)$$,
           dbops.fn_pgtap_scope_operatore()::text,
           (SELECT chiave FROM _k) || '-altrui')),
       'E_CODA_CHIAVE_ALTRUI',
       '14) un lavoro vivo con la stessa chiave in un''altra azienda: la porta non ne restituisce l''id')
    ELSE skip('14) da owner la porta si fida: il ramo dell''applicazione lo prova il runner, come app', 1)
END;

SELECT CASE WHEN (SELECT da_app FROM _k) THEN
    lives_ok($$SELECT dbops.fn_accoda_lavoro(p_job_type => 'NOTIFICA_DIGEST_MUTO', p_run_as => 'SISTEMA',
                                             p_idempotency_key => 'PGTAP-PORTA-SISTEMA-' || txid_current()::text)$$,
             '15) un lavoro SISTEMA lo accoda anche un operatore: non ha azienda')
    ELSE skip('15) da owner la porta si fida: il ramo dell''applicazione lo prova il runner, come app', 1)
END;

-- ============================================================
-- 16) Da owner
-- ============================================================
SELECT CASE WHEN NOT (SELECT da_app FROM _k) THEN
    is(pg_temp.codice_di(format(
           $$SELECT dbops.fn_accoda_lavoro(p_job_type => 'CHIUSURA_SCADENZE', p_run_as => 'OPERATORE',
                                          p_scope => %L::jsonb)$$,
           (dbops.fn_pgtap_scope_operatore()
              || jsonb_build_object('auth_user_id', (SELECT auth_user_id FROM _mondi WHERE lato = 'ALTRO')))::text)),
       NULL,
       '16) da owner la porta si fida: e'' la strada dei lavori di pgAgent, che arrivano da procedure DEFINER')
    ELSE skip('16) come app la porta non si fida: il ramo del proprietario lo prova la corsa da owner', 1)
END;

SELECT * FROM finish();
ROLLBACK;
