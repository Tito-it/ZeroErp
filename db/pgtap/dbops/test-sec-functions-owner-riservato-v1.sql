-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test STRUTTURALE — il registro degli owner e la sync riservati al migratore
--   dbops.sec_functions_owner · dbops.fn_sync_functions_owner()
--
-- Brief: brief-db-registro-owner-e-sync-riservati-al-migratore.md §3
-- ChangeSet: 20_code/dbops/20260926-11 (la guardia nel corpo della sync)
--            20_code/dbops/20260929-08/-09 (la domanda passa nel BB
--            dbops.fn_sessione_del_migratore, brief-db-secondo-fattore-totp)
--            90_end/20260926-12 (il registro in sola lettura, forward su dev)
--            90_end/ci_apply/20260205-41 (voce in v_tabelle_sola_lettura_app)
--            scripts/sql/provision_zeroerp.sql (fase post) (la stessa voce: e' l'ULTIMA
--            parola in CI, gira dopo ci_apply)
--
-- ⭐ CHI SCRIVE IL REGISTRO ED ESEGUE LA SYNC SCEGLIE CHI POSSIEDE LE DEFINER
--   DI POSTGRES. Fino al 2026-09-26 `zeroerp_app` aveva entrambe le porte:
--   `UPDATE … SET required_owner = 'zeroerp_app'` + `SELECT
--   dbops.fn_sync_functions_owner()` e le sei funzioni indurite passavano
--   all'app. Il registro diventa sola lettura (ACL, tre sedi); la sync si
--   difende NEL CORPO, perche' l'ACL di una funzione di postgres il loop dei
--   grant la riscrive e il cambio di proprietario la rimappa.
--
-- ⚠️ PERCHÉ GIRA COME L'APPLICAZIONE (runner di default). Il SOGGETTO è
--   `zeroerp_app`: le asserzioni di comportamento (42501) hanno senso solo come
--   app, da owner passerebbero tutte. La guardia legge `session_user`, quindi
--   un `SET ROLE zeroerp_app` dentro una sessione di owner NON la esercita: la
--   prova negativa esiste solo con una connessione vera come app, cioè qui.
--   Il verso positivo («il migratore passa ancora») è il gemello
--   test-sec-functions-owner-migratore-passa-v1.sql, che gira come owner.
--
-- ⚠️ LIMITE DICHIARATO DELLA GUARDIA, non nascosto: `session_user` è il ruolo
--   di LOGIN. Una sessione aperta come migratore che fa `SET ROLE zeroerp_app`
--   passerebbe. Non è il caso dell'applicazione (Django si connette COME
--   zeroerp_app) né di questo runner. PostgreSQL non espone l'invocante di una
--   DEFINER: un'alternativa senza il limite non esiste.
--
-- Elenco test (plan 13):
--   POSTURA — il registro (has_table_privilege)
--    1-3 : INSERT, UPDATE, DELETE negati
--    4   : SELECT concesso — dichiarato (D-2): configurazione, non un segreto
--   COMPORTAMENTO — il registro
--    5-7 : INSERT / UPDATE / DELETE → 42501, anche a zero righe
--   LA SYNC
--    8   : ⭐ EXECUTE concesso — DICHIARATO (D-3): la difesa non è nell'ACL.
--          Chi si aspetta un `false` come per fn_audit_begin legga qui. Se un
--          giorno la sync entrerà in v_fn_riservate, questo test va girato
--    9   : SELECT dbops.fn_sync_functions_owner() come app → 42501
--   10   : ... e il rifiuto è la GUARDIA, non l'ACL (il messaggio è il suo)
--   11   : gemello «esiste»: il registro ha righe — il rifiuto del 9 non è un
--          rifiuto su un registro vuoto
--   STRUTTURA
--   12   : la guardia legge session_user e NON pg_has_role(current_user…)
--          (commenti tolti) — pinna la trappola 1 del brief. Dal 2026-09-29
--          la domanda sta in dbops.fn_sessione_del_migratore (20260929-08/-09):
--          la sync la chiama, il BB legge session_user
--   13   : la copia di servizio del giro non è rimasta (hasnt_function)
--
-- Read-only: tutto dentro BEGIN;/ROLLBACK;. Nessuna riga scritta.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il file non attraversa tabelle in RLS, ma la riga sta
-- qui perché il preambolo è un contratto (guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- 1-4. Postura sul registro
-- ============================================================
SELECT is(has_table_privilege('zeroerp_app', 'dbops.sec_functions_owner', 'INSERT'), false,
          '1. sec_functions_owner: INSERT negato — il registro lo scrive solo il migratore');
SELECT is(has_table_privilege('zeroerp_app', 'dbops.sec_functions_owner', 'UPDATE'), false,
          '2. sec_functions_owner: UPDATE negato — chi riscrive required_owner sceglie il proprietario');
SELECT is(has_table_privilege('zeroerp_app', 'dbops.sec_functions_owner', 'DELETE'), false,
          '3. sec_functions_owner: DELETE negato — togliere una riga toglie la funzione dall''hardening');
SELECT is(has_table_privilege('zeroerp_app', 'dbops.sec_functions_owner', 'SELECT'), true,
          '4. sec_functions_owner: SELECT concesso — dichiarato (D-2): leggere senza scrivere non è una leva');

-- ============================================================
-- 5-7. Comportamento: il permesso si controlla all'avvio dell'esecuzione,
--      prima di guardare le righe — `WHERE false` basta e non tocca niente.
--      ⚠️ `SET id = id`: una colonna che ESISTE, o il parser risponderebbe
--      42703 prima del controllo dei permessi.
-- ============================================================
SELECT throws_ok(
    $$ INSERT INTO dbops.sec_functions_owner
           SELECT * FROM dbops.sec_functions_owner WHERE false $$,
    '42501', NULL,
    '5. INSERT sul registro → permesso negato (42501)');
SELECT throws_ok(
    $$ UPDATE dbops.sec_functions_owner SET id = id WHERE false $$,
    '42501', NULL,
    '6. UPDATE sul registro → permesso negato (42501)');
SELECT throws_ok(
    $$ DELETE FROM dbops.sec_functions_owner WHERE false $$,
    '42501', NULL,
    '7. DELETE sul registro → permesso negato (42501)');

-- ============================================================
-- 8-11. La sync: EXECUTE c'è, e la guardia rifiuta lo stesso
-- ============================================================
SELECT is(has_function_privilege('zeroerp_app', 'dbops.fn_sync_functions_owner()', 'EXECUTE'), true,
          '8. fn_sync_functions_owner: EXECUTE concesso — DICHIARATO (D-3): la difesa è nel corpo, non nell''ACL');

SELECT throws_ok(
    $$ SELECT dbops.fn_sync_functions_owner() $$,
    '42501', NULL,
    '9. fn_sync_functions_owner come app → 42501');

-- Il messaggio distingue la guardia da un «permesso negato per la funzione»
-- dell'ACL: stesso codice, frase diversa. Senza questo test un REVOKE futuro
-- farebbe restare verde il 9 anche con la guardia tolta.
SELECT throws_like(
    $$ SELECT dbops.fn_sync_functions_owner() $$,
    '%riservata a chi possiede lo schema dbops%',
    '10. il rifiuto è la GUARDIA nel corpo, non l''ACL');

SELECT cmp_ok((SELECT count(*) FROM dbops.sec_functions_owner), '>', 0::bigint,
          '11. gemello «esiste»: il registro ha righe — il 9 non rifiuta un registro vuoto');

-- ============================================================
-- 12-13. Struttura
-- ============================================================
-- ⛔ Dentro una DEFINER current_user è il PROPRIETARIO (postgres): una guardia
--    su current_user sarebbe sempre aperta. Commenti `--` tolti prima di
--    cercare: il corpo SPIEGA la trappola, e un presidio sul testo non deve
--    accendersi sulla prosa.
-- ⭐ Dal 2026-09-29 (20260929-08/-09, regola del 2) la domanda sta nel BB
--    dbops.fn_sessione_del_migratore, che la sync chiama: il presidio segue la
--    domanda dove e' andata — la sync chiede al BB, e il BB legge session_user.
SELECT ok(
    (SELECT regexp_replace(s.prosrc, '--[^\n]*', '', 'g') ~ 'dbops\.fn_sessione_del_migratore\(\s*\)'
        AND regexp_replace(s.prosrc, '--[^\n]*', '', 'g') !~ 'pg_has_role\(\s*current_user'
        AND regexp_replace(b.prosrc, '--[^\n]*', '', 'g') ~ 'pg_has_role\(\s*session_user'
        AND regexp_replace(b.prosrc, '--[^\n]*', '', 'g') !~ 'pg_has_role\(\s*current_user'
       FROM pg_catalog.pg_proc s, pg_catalog.pg_proc b
      WHERE s.oid = 'dbops.fn_sync_functions_owner()'::regprocedure
        AND b.oid = 'dbops.fn_sessione_del_migratore()'::regprocedure),
    '12. la guardia chiede a fn_sessione_del_migratore, che legge session_user e non current_user — trappola 1');

SELECT hasnt_function('dbops', 'fn_sync_functions_owner_boot',
    '13. la copia di servizio del giro 20260926-11 non è rimasta');

SELECT * FROM finish();
ROLLBACK;
