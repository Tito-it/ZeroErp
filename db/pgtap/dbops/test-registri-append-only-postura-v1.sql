-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test STRUTTURALE — postura di `zeroerp_app` sui registri append-only
--   dbops.audit_log · dbops.error_log
--
-- Brief: brief-db-rls-storico-scope-congelato.md §8.4
-- ChangeSet: 90_end/20260911-09-revoke-app-update-delete-registri-audit
--            90_end/ci_apply/20260205-41 (eccezione dichiarata nel loop dei grant)
--            scripts/sql/provision_zeroerp.sql (fase post) (la stessa eccezione: e' l'ULTIMA
--            parola in CI, gira dopo ci_apply — senza, questo file e' rosso su
--            un database ricostruito da zero e verde su dev. Successo 2026-09-11)
--
-- ⭐ UN REGISTRO DI AUDIT MODIFICABILE DA CHI E' AUDITATO NON E' UN REGISTRO.
--   L'applicazione legge e aggiunge (SELECT, INSERT); non riscrive, non
--   cancella, non svuota. L'app scrive con la sola fn_audit_log_once. La
--   modalità sessione dell'audit (fn_audit_begin → fn_audit_end), che era un
--   UPDATE del registro riservato a chi possiede la tabella, è ritirata
--   (90_end/20261104-18): i test 14-15 provano che non torni.
--
-- ⚠️ PERCHÉ GIRA COME L'APPLICAZIONE (runner di default). Il SOGGETTO è proprio
--   `zeroerp_app`: i privilegi che ha e ciò che riesce a fare. Le asserzioni di
--   postura usano `has_*_privilege(ruolo, …)`, che legge il catalogo e non
--   dipende dal ruolo connesso — MAI `information_schema.role_table_grants`,
--   che mostra solo i grant del ruolo connesso ed è verde per sottrazione
--   quando interroga un altro ruolo. Le asserzioni di comportamento (42501)
--   hanno senso SOLO come app: da owner passerebbero tutte.
--
-- ⚠️ PERCHÉ È UN PRESIDIO E NON SOLO UN TEST. Il loop `20260205-41` rifà i
--   GRANT a ogni passata `ci_apply`, e `provision_zeroerp.sql` (fase post) li rifà DOPO
--   di lui: se una delle due sedi perdesse l'eccezione dichiarata, o un
--   DROP+CREATE riportasse `=X` (PUBLIC) sulle due funzioni, la postura si
--   riaprirebbe in silenzio. Questo file è il rosso che lo dice — e l'ha
--   detto il giorno stesso in cui è nato, sul provisioning.
--
-- Elenco test (plan 22):
--   POSTURA — tabelle (has_table_privilege)
--    1-2 : audit_log — SELECT, INSERT concessi
--    3-5 : audit_log — UPDATE, DELETE, TRUNCATE negati
--    6-7 : error_log — SELECT, INSERT concessi
--    8-10: error_log — UPDATE, DELETE, TRUNCATE negati
--   POSTURA — sequenze (l'INSERT ha bisogno di USAGE)
--   11-12: USAGE su audit_log_id_seq e error_log_id_seq
--   POSTURA — funzioni (has_function_privilege: comprende PUBLIC)
--   13   : fn_audit_log_once — EXECUTE concesso (la porta dell'app)
--   14-15: fn_audit_begin, fn_audit_end — non esistono (modalità sessione ritirata)
--   COMPORTAMENTO — quello che l'app riesce a fare davvero
--   16-17: UPDATE / DELETE su audit_log → 42501, anche a zero righe
--   18-19: UPDATE / DELETE su error_log → 42501, anche a zero righe
--   20   : fn_audit_log_once scrive (id > 0) — l'INSERT non è stato toccato
--   21   : gemello «esiste»: la riga scritta al 20 è nel registro, in locale
--   22   : la riga del 20 è FIRMATA dal ruolo che l'ha scritta (executed_by =
--          current_user) — pinna 00_schema/20260911-20: il default era la
--          STRINGA 'CURRENT_USER', e il registro non diceva chi eseguiva
--
-- Read-only: tutto dentro BEGIN;/ROLLBACK;, la riga del test 20 muore col
-- ROLLBACK (canale dblink spento con SET LOCAL, vedi fixture).
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il file non attraversa tabelle in RLS, ma la riga sta
-- qui perché il preambolo è un contratto (guardrail_pgtap_preambolo) e perché
-- fn_audit_log_once passa dal trigger tx_id, che legge la sessione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(22);

-- ============================================================
-- Fixture
-- ============================================================
-- ⚠️ Il canale fuori transazione va SPENTO per la durata del test: con
--   `myapp.log_with_dblink = on` fn_audit_log_once scriverebbe su una
--   connessione separata e la riga di prova sopravvivrebbe al ROLLBACK, una per
--   corsa. Su dev il GUC non è impostato (2026-09-11), ma il test non deve
--   dipendere da com'è configurata la macchina.
SET LOCAL myapp.log_with_dblink = 'off';

-- ============================================================
-- 1-10. Postura sulle tabelle
-- ============================================================
SELECT is(has_table_privilege('zeroerp_app', 'dbops.audit_log', 'SELECT'), true,
          '1. audit_log: SELECT concesso — il registro si legge');
SELECT is(has_table_privilege('zeroerp_app', 'dbops.audit_log', 'INSERT'), true,
          '2. audit_log: INSERT concesso — il registro si aggiunge');
SELECT is(has_table_privilege('zeroerp_app', 'dbops.audit_log', 'UPDATE'), false,
          '3. audit_log: UPDATE negato — il registro non si riscrive');
SELECT is(has_table_privilege('zeroerp_app', 'dbops.audit_log', 'DELETE'), false,
          '4. audit_log: DELETE negato — il registro non si cancella');
SELECT is(has_table_privilege('zeroerp_app', 'dbops.audit_log', 'TRUNCATE'), false,
          '5. audit_log: TRUNCATE negato — mai concesso, e deve restare così');

SELECT is(has_table_privilege('zeroerp_app', 'dbops.error_log', 'SELECT'), true,
          '6. error_log: SELECT concesso');
SELECT is(has_table_privilege('zeroerp_app', 'dbops.error_log', 'INSERT'), true,
          '7. error_log: INSERT concesso — fn_log_error_only scrive in locale a canale spento');
SELECT is(has_table_privilege('zeroerp_app', 'dbops.error_log', 'UPDATE'), false,
          '8. error_log: UPDATE negato');
SELECT is(has_table_privilege('zeroerp_app', 'dbops.error_log', 'DELETE'), false,
          '9. error_log: DELETE negato');
SELECT is(has_table_privilege('zeroerp_app', 'dbops.error_log', 'TRUNCATE'), false,
          '10. error_log: TRUNCATE negato');

-- ============================================================
-- 11-12. Sequenze: senza USAGE l'INSERT concesso sarebbe una promessa vuota
-- ============================================================
SELECT is(has_sequence_privilege('zeroerp_app', 'dbops.audit_log_id_seq', 'USAGE'), true,
          '11. audit_log_id_seq: USAGE — l''INSERT può prendere il prossimo id');
SELECT is(has_sequence_privilege('zeroerp_app', 'dbops.error_log_id_seq', 'USAGE'), true,
          '12. error_log_id_seq: USAGE');

-- ============================================================
-- 13-15. Funzioni: has_function_privilege tiene conto anche di PUBLIC, quindi
--        un `=X` rimasto sull'ACL farebbe rosso qui — è la trappola del
--        DROP+CREATE, che riporta i default.
-- ============================================================
SELECT is(has_function_privilege('zeroerp_app',
            'dbops.fn_audit_log_once(text,text,jsonb,text,text,text[],text,boolean,text,text,integer,jsonb,text,text)',
            'EXECUTE'), true,
          '13. fn_audit_log_once: EXECUTE concesso — è la porta di scrittura dell''app');
-- ⭐ 14-15: la modalità sessione è ritirata (90_end/20261104-18). Un ritorno
--   delle due funzioni riaprirebbe una porta di UPDATE sul registro: il rosso
--   deve dirlo qui, prima che qualcuno ne riscriva i grant.
SELECT hasnt_function('dbops', 'fn_audit_begin',
          '14. fn_audit_begin non esiste: la modalità sessione dell''audit è ritirata');
SELECT hasnt_function('dbops', 'fn_audit_end',
          '15. fn_audit_end non esiste: la chiusura era un UPDATE del registro');

-- ============================================================
-- 16-19. Comportamento: il permesso si controlla all'avvio dell'esecuzione,
--        prima di guardare le righe — `WHERE false` basta e non tocca niente.
--        ⚠️ `SET id = id` e non una colonna «parlante»: il parser risolve le
--        colonne PRIMA del controllo dei permessi, e su una colonna assente
--        risponderebbe 42703 — rosso per il motivo sbagliato. `id` c'è su
--        entrambe e non ha nome da cambiare.
-- ============================================================
SELECT throws_ok(
    $$ UPDATE dbops.audit_log SET id = id WHERE false $$,
    '42501', NULL,
    '16. UPDATE su audit_log → permesso negato (42501)');
SELECT throws_ok(
    $$ DELETE FROM dbops.audit_log WHERE false $$,
    '42501', NULL,
    '17. DELETE su audit_log → permesso negato (42501)');
SELECT throws_ok(
    $$ UPDATE dbops.error_log SET id = id WHERE false $$,
    '42501', NULL,
    '18. UPDATE su error_log → permesso negato (42501)');
SELECT throws_ok(
    $$ DELETE FROM dbops.error_log WHERE false $$,
    '42501', NULL,
    '19. DELETE su error_log → permesso negato (42501)');

-- ============================================================
-- 20-21. La porta dell'app resta aperta: la revoca non ha stretto di più.
-- ============================================================
CREATE TEMP TABLE _audit_prova ON COMMIT DROP AS
SELECT dbops.fn_audit_log_once(
           'pgtap.test-registri-append-only-postura',
           'OK',
           '{"pgtap": true}'::jsonb,
           'riga di prova: muore col ROLLBACK') AS id;

SELECT ok((SELECT id FROM _audit_prova) > 0,
          '20. fn_audit_log_once come app: scrive e torna un id');

SELECT is((SELECT count(*) FROM dbops.audit_log a
            WHERE a.id = (SELECT id FROM _audit_prova)
              AND a.function_name = 'pgtap.test-registri-append-only-postura'),
          1::bigint,
          '21. gemello «esiste»: la riga è nel registro, scritta in locale (canale dblink spento)');

-- ============================================================
-- 22. Chi è l'auditato: la riga porta il RUOLO che l'ha scritta.
--     ⛔ Fino al 2026-09-11 il default di executed_by era la STRINGA
--     'CURRENT_USER' — tremila righe con la parola al posto del ruolo — e un
--     registro che non sa dire chi esegue non è un registro più di uno che si
--     lascia riscrivere. È la stessa domanda del §8.4 vista dall'altro lato.
--     Pinna 00_schema/dbops/20260911-20.
-- ============================================================
SELECT is((SELECT a.executed_by FROM dbops.audit_log a
            WHERE a.id = (SELECT id FROM _audit_prova)),
          current_user::text,
          '22. executed_by = current_user: la riga è firmata dal ruolo, non dalla parola CURRENT_USER');

SELECT * FROM finish();
ROLLBACK;
