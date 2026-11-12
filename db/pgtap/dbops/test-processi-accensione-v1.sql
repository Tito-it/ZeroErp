-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Quali processi sono accesi: la regola, il catalogo, la scelta a mano, la
-- sveglia e il panorama.
--   Brief: brief-db-processi-accensione-per-ambiente (A-2, A-5, P-2, P-3, R-1)
--   changeSet 20261016-20 (colonne e CHECK), -21 (scelta a mano), -22/-23
--   (guard), -24 (la regola sui valori), -25 (la lettura), -26 (la sveglia),
--   -27 (il verbo), -28 (panorama: SPENTO), 90_end/20261016-31 (convalida);
--   80_data processi.csv (i default), codici_errore/messaggi_errore (1341-1343).
--   Rev 2026-10-17 (S-1, R-BE-1): 20261017-02 (acceso nullable, storicizza,
--   tx_id), -03 (il verbo non cancella e non scrive l'audit), -04 (registro
--   dello storico); automation_scope.csv e storico_scope_policy.csv.
--   ⚠️ I test 33-34 leggono l'audit e lo storico GENERATI da ci_apply: su un
--   database di sviluppo sono verdi dopo il giro dei job automations_* (brief
--   §6.3), non subito dopo il migrate.
--   Rev 2026-10-18 (R-BE-5, §6.6): 20261018-10 (accendibile_in_produzione e
--   CHECK riscritto), -11 (il predicato del divieto), -12 (la regola ignora la
--   scelta che il divieto non ammette), -13 (il guard), 90_end/20261018-14;
--   processi.csv, codici_errore/messaggi_errore (1355). Il ramo PRODUZIONE
--   del guard e della lettura, costruito, sta in
--   dbops/test-processi-accensione-produzione-v1 (runner owner).
--
-- Elenco test (plan 47):
--   forma
--    1) la regola e' STABLE, LANGUAGE sql, senza STRICT (i NULL sono casi normali;
--       STABLE dal giro 9 di brief-db-revisione-dbops: il ritiro si legge con script.fn_e_obsoleto)
--    2) la sveglia e' SECURITY DEFINER con search_path pinnato
--    3) zeroerp_job puo' chiedere alla sveglia (il passo pgAgent gira come lui)
--    4) il verbo e' INVOKER: il permesso e' del backend
--   ⭐ la regola, sui VALORI — l'ambiente e' immutabile e la CI e' SVILUPPO:
--     il ramo PRODUZIONE si prova passando il valore
--    5) CODA -> NULL
--    6) ritirato -> NULL
--    7) non spegnibile, spento a mano, PRODUZIONE -> true
--    8) non spegnibile, ambiente non dichiarato -> true (R-1: non legge l'ambiente)
--    9) spegnibile, spento a mano, default acceso -> false
--   10) spegnibile, acceso a mano, default spento -> true
--   11) SVILUPPO -> il default di sviluppo
--   12) PRODUZIONE -> il default di produzione
--   13) ambiente non dichiarato, nessuna scelta -> NULL (non decidibile)
--   il catalogo (A-2, A-5)
--   14) chk_processi_accensione c'e' ed e' convalidato
--   15) i non spegnibili sono esattamente i sette decisi da Tid (A-5)
--   16) smoke_notturno: acceso in sviluppo, spento in produzione
--   17) run_fatturazione_batch: spento in tutti e due gli ambienti
--   la sveglia
--   18) un non spegnibile: true, qualunque cosa dica l'ambiente
--   19) codice inesistente -> E_PROCESSO_NON_TROVATO
--   20) processo CODA -> E_PROCESSO_SENZA_SVEGLIA
--   il verbo, e cio' che ne segue
--   21) spegne smoke_notturno: torna false
--   22) ... e la sveglia dice false
--   23) ... e il panorama dice SPENTO, non da guardare, acceso false
--   24) lo riaccende: torna true
--   25) lo rimette al default: lo stato e' il default dell'ambiente
--   25-bis) ... e la riga resta, con acceso NULL e il motivo (S-1)
--   26) spegnere listen_permessi -> E_PROCESSO_NON_SPEGNIBILE
--   27) confermare acceso un non spegnibile e' ammesso
--   28) motivo vuoto -> E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO
--   29) un processo CODA -> E_PROCESSO_SENZA_SVEGLIA
--   30) codice inesistente -> E_PROCESSO_NON_TROVATO
--   la storia (S-1, R-BE-1)
--   31) acceso e' nullable: NULL = tornato al default
--   32) tornare al default senza motivo -> E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO
--   33) chi ha fatto i gesti e' l'utente del backend (app.jwt_user), non il ruolo
--   34) ogni gesto lascia una versione in storico.processi_accensione
--   ⭐ il divieto di accensione in PRODUZIONE (R-BE-5), sui VALORI
--   35) il predicato e' IMMUTABLE, LANGUAGE sql, senza STRICT
--   36) spegnere e tornare al default sono sempre ammessi, anche in PRODUZIONE
--   37) un processo accendibile, o senza sveglia, si accende in PRODUZIONE
--   38) un non accendibile: SVILUPPO si', PRODUZIONE no, non dichiarato NULL
--   39) la regola: non accendibile acceso a mano in PRODUZIONE -> la riga si
--       ignora, vale il default di produzione (spento)
--   40) la regola: non accendibile acceso a mano in SVILUPPO -> acceso
--   41) la regola: non accendibile acceso a mano, ambiente non dichiarato -> NULL
--   42) la regola: non accendibile spento a mano in PRODUZIONE -> spento
--   il catalogo
--   43) i non accendibili in produzione sono esattamente smoke_notturno
--   44) un non accendibile acceso di default in produzione -> chk_processi_accensione
--   45) un processo con sveglia senza accendibile_in_produzione -> chk_processi_accensione
--   46) un CODA con accendibile_in_produzione valorizzato -> chk_processi_accensione
--   ⚠️ In SVILUPPO il guard ammette l'accensione di smoke_notturno: e' il test 24.
--
--   ⚠️ Il cablaggio dei passi pgAgent (85_pgagent/20261016-30) e il caso
--   «ambiente non dichiarato» costruito stanno in
--   dbops/test-installazione-ambiente-v1 (runner owner).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(47);


-- ============================================================
-- Forma
-- ============================================================
SELECT is(
    (SELECT format('%s|%s|%s', p.provolatile, l.lanname, p.proisstrict)
       FROM pg_proc p
       JOIN pg_language l ON l.oid = p.prolang
      WHERE p.oid = 'dbops.fn_processo_acceso_su_valori(text, date, boolean, boolean, boolean, boolean, text, boolean)'::regprocedure),
    's|sql|f',
    '1. la regola e'' STABLE (il ritiro dipende dalla data di oggi), LANGUAGE sql, senza STRICT');

SELECT is(
    (SELECT format('%s|%s', p.prosecdef, array_to_string(p.proconfig, ';'))
       FROM pg_proc p
      WHERE p.oid = 'maintenance.fn_sveglia_accesa(text)'::regprocedure),
    't|search_path=pg_catalog, public, pg_temp',
    '2. la sveglia e'' SECURITY DEFINER con search_path pinnato');

SELECT ok(
    NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zeroerp_job')
    OR has_function_privilege('zeroerp_job', 'maintenance.fn_sveglia_accesa(text)', 'EXECUTE'),
    '3. zeroerp_job puo'' chiedere alla sveglia (il passo pgAgent gira come lui)');

SELECT is(
    (SELECT p.prosecdef
       FROM pg_proc p
      WHERE p.oid = 'dbops.fn_imposta_accensione_processo(text, boolean, text)'::regprocedure),
    false,
    '4. il verbo e'' INVOKER: il permesso e'' del backend');

-- ============================================================
-- ⭐ La regola, sui VALORI
--   (canale, obsoleto_dal, spegnibile, acceso_svil, acceso_prod, a_mano, ambiente,
--    accendibile_in_produzione)
-- ============================================================
SELECT is(dbops.fn_processo_acceso_su_valori('CODA', NULL, NULL, NULL, NULL, NULL, 'SVILUPPO', NULL),
          NULL::boolean, '5. CODA: senza sveglia, NULL');

SELECT is(dbops.fn_processo_acceso_su_valori('COMMAND', DATE '2026-01-01', NULL, NULL, NULL, NULL, 'SVILUPPO', NULL),
          NULL::boolean, '6. ritiro raggiunto: senza sveglia, NULL');

SELECT is(dbops.fn_processo_acceso_su_valori('PGAGENT', NULL, false, true, true, false, 'PRODUZIONE', true),
          true, '7. non spegnibile, spento a mano, PRODUZIONE: acceso comunque');

SELECT is(dbops.fn_processo_acceso_su_valori('COMMAND', NULL, false, true, true, NULL, NULL, true),
          true, '8. non spegnibile con l''ambiente non dichiarato: acceso (R-1, non legge l''ambiente)');

SELECT is(dbops.fn_processo_acceso_su_valori('COMMAND', NULL, true, true, true, false, 'SVILUPPO', true),
          false, '9. spegnibile, spento a mano, default acceso: spento');

SELECT is(dbops.fn_processo_acceso_su_valori('COMMAND', NULL, true, false, false, true, 'PRODUZIONE', true),
          true, '10. spegnibile, acceso a mano, default spento: acceso');

SELECT is(dbops.fn_processo_acceso_su_valori('COMMAND', NULL, true, true, false, NULL, 'SVILUPPO', true),
          true, '11. SVILUPPO senza scelta: il default di sviluppo');

SELECT is(dbops.fn_processo_acceso_su_valori('COMMAND', NULL, true, true, false, NULL, 'PRODUZIONE', true),
          false, '12. PRODUZIONE senza scelta: il default di produzione (la forma dello smoke)');

SELECT is(dbops.fn_processo_acceso_su_valori('PGAGENT', NULL, true, true, true, NULL, NULL, true),
          NULL::boolean, '13. ambiente non dichiarato e nessuna scelta: non decidibile, NULL');

-- ============================================================
-- Il catalogo (A-2, A-5)
-- ============================================================
SELECT is(
    (SELECT c.convalidated
       FROM pg_constraint c
      WHERE c.conrelid = 'dbops.processi'::regclass
        AND c.conname = 'chk_processi_accensione'),
    true,
    '14. chk_processi_accensione c''e'' ed e'' convalidato (90_end/20261016-31)');

SELECT is(
    (SELECT string_agg(p.codice, ',' ORDER BY p.codice)
       FROM dbops.processi p
      WHERE p.spegnibile IS FALSE),
    'chiusura_scadenze_daily,digest_presidi,draina_coda_lavori,guardiano_digest,listen_permessi,send_pending_emails,sync_auth_user_expired_daily',
    '15. i non spegnibili sono esattamente i sette decisi da Tid (A-5)');

SELECT is(
    (SELECT format('%s|%s|%s', p.acceso_in_sviluppo, p.acceso_in_produzione, p.spegnibile)
       FROM dbops.processi p WHERE p.codice = 'smoke_notturno'),
    't|f|t',
    '16. smoke_notturno: acceso in sviluppo, spento in produzione, spegnibile');

SELECT is(
    (SELECT format('%s|%s', p.acceso_in_sviluppo, p.acceso_in_produzione)
       FROM dbops.processi p WHERE p.codice = 'run_fatturazione_batch'),
    'f|f',
    '17. run_fatturazione_batch: spento ovunque, si accende a mano quando e'' pronto');

-- ============================================================
-- La sveglia
-- ============================================================
SELECT is(maintenance.fn_sveglia_accesa('listen_permessi'), true,
          '18. un non spegnibile: la sveglia e'' accesa');

SELECT is(dbops.fn_pgtap_codice_errore($$SELECT maintenance.fn_sveglia_accesa('PGTAP-PROCESSO-CHE-NON-ESISTE')$$),
          'E_PROCESSO_NON_TROVATO', '19. codice inesistente: E_PROCESSO_NON_TROVATO');

SELECT is(dbops.fn_pgtap_codice_errore($$SELECT maintenance.fn_sveglia_accesa('avvio_manuale')$$),
          'E_PROCESSO_SENZA_SVEGLIA', '20. processo CODA: E_PROCESSO_SENZA_SVEGLIA');

-- ============================================================
-- Il verbo, e cio' che ne segue
-- ============================================================
-- ⚠️ Una scelta a mano gia' presente su questa macchina non deve falsare i
--   test: si parte senza (tutto si annulla col ROLLBACK).
DELETE FROM dbops.processi_accensione a
 USING dbops.processi p
 WHERE p.id = a.processo_id AND p.codice IN ('smoke_notturno', 'listen_permessi');

-- L'utente del backend: lo imposta il middleware a ogni richiesta, e l'audit
--   generato lo legge (test 33). Locale alla transazione.
SELECT set_config('app.jwt_user', 'pgtap.accensione', true);

SELECT is(dbops.fn_imposta_accensione_processo('smoke_notturno', false, 'pgTAP: prova dello spegnimento'),
          false, '21. il verbo spegne smoke_notturno e torna lo stato effettivo: false');

SELECT is(maintenance.fn_sveglia_accesa('smoke_notturno'), false,
          '22. la sveglia di smoke_notturno ora e'' spenta');

SELECT is(
    (SELECT format('%s|%s|%s', v.stato, v.da_guardare, v.acceso)
       FROM dbops.vw_processi_programmazione v
      WHERE v.processo_codice = 'smoke_notturno'),
    'SPENTO|f|f',
    '23. il panorama dice SPENTO, non da guardare: spento non e'' morto');

SELECT is(dbops.fn_imposta_accensione_processo('smoke_notturno', true, 'pgTAP: prova della riaccensione'),
          true, '24. il verbo lo riaccende: true');

-- ⚠️ Il verbo e la lettura della riga in DUE istruzioni: nella stessa SELECT
--   la lettura vedrebbe la fotografia di inizio istruzione.
SELECT is(
    dbops.fn_imposta_accensione_processo('smoke_notturno', NULL, 'pgTAP: prova del ritorno al default')
        IS NOT DISTINCT FROM
    (SELECT CASE script.fn_ambiente_dichiarato()
                 WHEN 'SVILUPPO'   THEN p.acceso_in_sviluppo
                 WHEN 'PRODUZIONE' THEN p.acceso_in_produzione END
       FROM dbops.processi p WHERE p.codice = 'smoke_notturno'),
    true,
    '25. rimesso al default: lo stato e'' quello del suo ambiente');

SELECT is(
    (SELECT format('%s|%s', a.acceso IS NULL, a.motivo)
       FROM dbops.processi_accensione a
       JOIN dbops.processi p ON p.id = a.processo_id
      WHERE p.codice = 'smoke_notturno'),
    't|pgTAP: prova del ritorno al default',
    '25-bis. ... e la riga resta, con acceso NULL e il motivo: chi e perche'' non si perdono (S-1)');

SELECT is(dbops.fn_pgtap_codice_errore($$SELECT dbops.fn_imposta_accensione_processo('listen_permessi', false, 'pgTAP: prova')$$),
          'E_PROCESSO_NON_SPEGNIBILE', '26. spegnere listen_permessi: E_PROCESSO_NON_SPEGNIBILE');

SELECT is(dbops.fn_imposta_accensione_processo('listen_permessi', true, 'pgTAP: conferma'),
          true, '27. confermare acceso un non spegnibile e'' ammesso');

SELECT is(dbops.fn_pgtap_codice_errore($$SELECT dbops.fn_imposta_accensione_processo('smoke_notturno', false, '   ')$$),
          'E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO', '28. motivo vuoto: E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO');

SELECT is(dbops.fn_pgtap_codice_errore($$SELECT dbops.fn_imposta_accensione_processo('avvio_manuale', false, 'pgTAP: prova')$$),
          'E_PROCESSO_SENZA_SVEGLIA', '29. un processo CODA non ha sveglia: E_PROCESSO_SENZA_SVEGLIA');

SELECT is(dbops.fn_pgtap_codice_errore($$SELECT dbops.fn_imposta_accensione_processo('PGTAP-PROCESSO-CHE-NON-ESISTE', false, 'pgTAP')$$),
          'E_PROCESSO_NON_TROVATO', '30. codice inesistente: E_PROCESSO_NON_TROVATO');

-- ============================================================
-- La storia (S-1, R-BE-1)
-- ============================================================
SELECT is(
    (SELECT a.attnotnull
       FROM pg_attribute a
      WHERE a.attrelid = 'dbops.processi_accensione'::regclass
        AND a.attname = 'acceso'),
    false,
    '31. acceso e'' nullable: NULL = tornato al default (20261017-02)');

SELECT is(dbops.fn_pgtap_codice_errore($$SELECT dbops.fn_imposta_accensione_processo('smoke_notturno', NULL, NULL)$$),
          'E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO',
          '32. anche tornare al default vuole il motivo');

-- ⚠️ Audit e storico sono GENERATI da ci_apply: senza i trigger questi due
--   test sono rossi, ed e' cio' che devono dire (brief §6.3).
SELECT is(
    (SELECT format('%s|%s', a.user_insert, a.user_update)
       FROM dbops.processi_accensione a
       JOIN dbops.processi p ON p.id = a.processo_id
      WHERE p.codice = 'smoke_notturno'),
    'pgtap.accensione|pgtap.accensione',
    '33. chi ha fatto i gesti e'' l''utente del backend (app.jwt_user), non zeroerp_app (R-BE-1)');

-- I tre gesti su smoke_notturno (21 spegne: INSERT; 24 riaccende e 25 torna
--   al default: due UPDATE) lasciano tre versioni: la fotografia di partenza
--   del primo UPDATE (tipo 1) e una per UPDATE; quella aperta e' l'ultima.
--   ⚠️ La gemella si legge via EXECUTE: se non c'e' ancora (automazioni non
--   girate) il test e' rosso con la causa, non interrompe il file.
CREATE OR REPLACE FUNCTION pg_temp.versioni_smoke() RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_r text;
BEGIN
    IF to_regclass('storico.processi_accensione') IS NULL THEN
        RETURN 'gemella storico.processi_accensione assente';
    END IF;
    EXECUTE $q$
        SELECT format('%s|%s|%s',
                      count(*),
                      count(*) FILTER (WHERE s.valid_to IS NULL
                                         AND s.snapshot ->> 'acceso' IS NULL
                                         AND s.snapshot ->> 'motivo' = 'pgTAP: prova del ritorno al default'),
                      count(*) FILTER (WHERE s.snapshot ->> 'acceso' = 'false'))
          FROM storico.processi_accensione s
          JOIN dbops.processi_accensione a ON a.id = s.processi_accensione_id
          JOIN dbops.processi p ON p.id = a.processo_id
         WHERE p.codice = 'smoke_notturno'
    $q$ INTO v_r;
    RETURN v_r;
END $$;

SELECT is(
    pg_temp.versioni_smoke(),
    '3|1|1',
    '34. ogni gesto lascia una versione nello storico; l''ultima, aperta, e'' il ritorno al default');

-- ============================================================
-- ⭐ Il divieto di accensione in PRODUZIONE (R-BE-5), sui VALORI
--   (acceso_a_mano, accendibile_in_produzione, ambiente)
-- ============================================================
SELECT is(
    (SELECT format('%s|%s|%s', p.provolatile, l.lanname, p.proisstrict)
       FROM pg_proc p
       JOIN pg_language l ON l.oid = p.prolang
      WHERE p.oid = 'dbops.fn_accensione_a_mano_ammessa_su_valori(boolean, boolean, text)'::regprocedure),
    'i|sql|f',
    '35. il predicato e'' IMMUTABLE, LANGUAGE sql, senza STRICT');

SELECT is(
    format('%s|%s',
           dbops.fn_accensione_a_mano_ammessa_su_valori(false, false, 'PRODUZIONE'),
           dbops.fn_accensione_a_mano_ammessa_su_valori(NULL,  false, 'PRODUZIONE')),
    't|t',
    '36. spegnere e tornare al default sono ammessi anche su un non accendibile in PRODUZIONE');

SELECT is(
    format('%s|%s',
           dbops.fn_accensione_a_mano_ammessa_su_valori(true, true, 'PRODUZIONE'),
           dbops.fn_accensione_a_mano_ammessa_su_valori(true, NULL, 'PRODUZIONE')),
    't|t',
    '37. un processo accendibile (o senza sveglia: lo rifiuta un''altra regola) si accende in PRODUZIONE');

SELECT is(
    format('%s|%s|%s',
           dbops.fn_accensione_a_mano_ammessa_su_valori(true, false, 'SVILUPPO'),
           dbops.fn_accensione_a_mano_ammessa_su_valori(true, false, 'PRODUZIONE'),
           coalesce(dbops.fn_accensione_a_mano_ammessa_su_valori(true, false, NULL)::text, 'NULL')),
    't|f|NULL',
    '38. un non accendibile si accende a mano in SVILUPPO, non in PRODUZIONE; ambiente non dichiarato: non decidibile');

SELECT is(dbops.fn_processo_acceso_su_valori('COMMAND', NULL, true, true, false, true, 'PRODUZIONE', false),
          false, '39. la regola: non accendibile acceso a mano in PRODUZIONE, la riga si ignora e vale il default (spento)');

SELECT is(dbops.fn_processo_acceso_su_valori('COMMAND', NULL, true, true, false, true, 'SVILUPPO', false),
          true, '40. la regola: non accendibile acceso a mano in SVILUPPO, acceso');

SELECT is(dbops.fn_processo_acceso_su_valori('COMMAND', NULL, true, true, false, true, NULL, false),
          NULL::boolean, '41. la regola: non accendibile acceso a mano, ambiente non dichiarato: non decidibile');

SELECT is(dbops.fn_processo_acceso_su_valori('COMMAND', NULL, true, true, false, false, 'PRODUZIONE', false),
          false, '42. la regola: non accendibile spento a mano in PRODUZIONE, spento');

-- ============================================================
-- Il catalogo (R-BE-5)
-- ============================================================
SELECT is(
    (SELECT string_agg(p.codice, ',' ORDER BY p.codice)
       FROM dbops.processi p
      WHERE p.accendibile_in_produzione IS FALSE),
    'smoke_notturno',
    '43. i non accendibili in produzione sono esattamente smoke_notturno (R-BE-5)');

SELECT throws_like(
    $$INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                  acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
      VALUES (9851, 'PGTAP-NON-ACCENDIBILE-ACCESO', 'prova', 'MANUTENZIONE', 'COMMAND', true, true, true, 'PROGRAMMA', false)$$,
    '%chk_processi_accensione%',
    '44. un non accendibile acceso di default in produzione: il divieto non vieterebbe niente, chk_processi_accensione');

SELECT throws_like(
    $$INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                  acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento)
      VALUES (9852, 'PGTAP-SENZA-ACCENDIBILE', 'prova', 'MANUTENZIONE', 'COMMAND', true, true, true, 'PROGRAMMA')$$,
    '%chk_processi_accensione%',
    '45. un processo con sveglia dichiara accendibile_in_produzione: chk_processi_accensione');

SELECT throws_like(
    $$INSERT INTO dbops.processi (id, codice, descrizione, classe, canale, causa_fallimento, accendibile_in_produzione)
      VALUES (9853, 'PGTAP-CODA-ACCENDIBILE', 'prova', 'DOMINIO', 'CODA', 'PROGRAMMA', true)$$,
    '%chk_processi_accensione%',
    '46. un CODA non ha sveglia: accendibile_in_produzione NULL, chk_processi_accensione');

SELECT * FROM finish();

ROLLBACK;
