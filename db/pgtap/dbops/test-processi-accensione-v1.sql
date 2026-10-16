-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Quali processi sono accesi: la regola, il catalogo, la scelta a mano, la
-- sveglia e il panorama.
--   Brief: brief-db-processi-accensione-per-ambiente (A-2, A-5, P-2, P-3, R-1)
--   changeSet 20261016-20 (colonne e CHECK), -21 (scelta a mano), -22/-23
--   (guard), -24 (la regola sui valori), -25 (la lettura), -26 (la sveglia),
--   -27 (il verbo), -28 (panorama: SPENTO), 90_end/20261016-31 (convalida);
--   80_data processi.csv (i default), codici_errore/messaggi_errore (1341-1343).
--
-- Elenco test (plan 31):
--   forma
--    1) la regola e' IMMUTABLE, LANGUAGE sql, senza STRICT (i NULL sono casi normali)
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
--   25-bis) ... e la riga della scelta a mano non c'e' piu'
--   26) spegnere listen_permessi -> E_PROCESSO_NON_SPEGNIBILE
--   27) confermare acceso un non spegnibile e' ammesso
--   28) motivo vuoto -> E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO
--   29) un processo CODA -> E_PROCESSO_SENZA_SVEGLIA
--   30) codice inesistente -> E_PROCESSO_NON_TROVATO
--
--   ⚠️ Il cablaggio dei passi pgAgent (85_pgagent/20261016-30) e il caso
--   «ambiente non dichiarato» costruito stanno in
--   dbops/test-installazione-ambiente-v1 (runner owner).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(31);

-- Il CODICE dell'errore viaggia nel canale CONSTRAINT_NAME dell'eccezione
-- P0001 (fn_log_and_raise_error): si pinna il codice, non la frase.
CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

-- ============================================================
-- Forma
-- ============================================================
SELECT is(
    (SELECT format('%s|%s|%s', p.provolatile, l.lanname, p.proisstrict)
       FROM pg_proc p
       JOIN pg_language l ON l.oid = p.prolang
      WHERE p.oid = 'dbops.fn_processo_acceso_su_valori(text, date, boolean, boolean, boolean, boolean, text)'::regprocedure),
    'i|sql|f',
    '1. la regola e'' IMMUTABLE, LANGUAGE sql, senza STRICT');

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
--   (canale, obsoleto_dal, spegnibile, acceso_svil, acceso_prod, a_mano, ambiente)
-- ============================================================
SELECT is(dbops.fn_processo_acceso_su_valori('CODA', NULL, NULL, NULL, NULL, NULL, 'SVILUPPO'),
          NULL::boolean, '5. CODA: senza sveglia, NULL');

SELECT is(dbops.fn_processo_acceso_su_valori('COMMAND', DATE '2026-01-01', NULL, NULL, NULL, NULL, 'SVILUPPO'),
          NULL::boolean, '6. ritirato: senza sveglia, NULL');

SELECT is(dbops.fn_processo_acceso_su_valori('PGAGENT', NULL, false, true, true, false, 'PRODUZIONE'),
          true, '7. non spegnibile, spento a mano, PRODUZIONE: acceso comunque');

SELECT is(dbops.fn_processo_acceso_su_valori('COMMAND', NULL, false, true, true, NULL, NULL),
          true, '8. non spegnibile con l''ambiente non dichiarato: acceso (R-1, non legge l''ambiente)');

SELECT is(dbops.fn_processo_acceso_su_valori('COMMAND', NULL, true, true, true, false, 'SVILUPPO'),
          false, '9. spegnibile, spento a mano, default acceso: spento');

SELECT is(dbops.fn_processo_acceso_su_valori('COMMAND', NULL, true, false, false, true, 'PRODUZIONE'),
          true, '10. spegnibile, acceso a mano, default spento: acceso');

SELECT is(dbops.fn_processo_acceso_su_valori('COMMAND', NULL, true, true, false, NULL, 'SVILUPPO'),
          true, '11. SVILUPPO senza scelta: il default di sviluppo');

SELECT is(dbops.fn_processo_acceso_su_valori('COMMAND', NULL, true, true, false, NULL, 'PRODUZIONE'),
          false, '12. PRODUZIONE senza scelta: il default di produzione (la forma dello smoke)');

SELECT is(dbops.fn_processo_acceso_su_valori('PGAGENT', NULL, true, true, true, NULL, NULL),
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

SELECT is(pg_temp.codice_errore($$SELECT maintenance.fn_sveglia_accesa('PGTAP-PROCESSO-CHE-NON-ESISTE')$$),
          'E_PROCESSO_NON_TROVATO', '19. codice inesistente: E_PROCESSO_NON_TROVATO');

SELECT is(pg_temp.codice_errore($$SELECT maintenance.fn_sveglia_accesa('avvio_manuale')$$),
          'E_PROCESSO_SENZA_SVEGLIA', '20. processo CODA: E_PROCESSO_SENZA_SVEGLIA');

-- ============================================================
-- Il verbo, e cio' che ne segue
-- ============================================================
-- ⚠️ Una scelta a mano gia' presente su questa macchina non deve falsare i
--   test: si parte senza (tutto si annulla col ROLLBACK).
DELETE FROM dbops.processi_accensione a
 USING dbops.processi p
 WHERE p.id = a.processo_id AND p.codice IN ('smoke_notturno', 'listen_permessi');

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

-- ⚠️ Il verbo e il conteggio in DUE istruzioni: nella stessa SELECT il
--   conteggio vedrebbe la fotografia di inizio istruzione, cioe' la riga
--   appena cancellata.
SELECT is(
    dbops.fn_imposta_accensione_processo('smoke_notturno', NULL, NULL)
        IS NOT DISTINCT FROM
    (SELECT CASE script.fn_ambiente_dichiarato()
                 WHEN 'SVILUPPO'   THEN p.acceso_in_sviluppo
                 WHEN 'PRODUZIONE' THEN p.acceso_in_produzione END
       FROM dbops.processi p WHERE p.codice = 'smoke_notturno'),
    true,
    '25. rimesso al default: lo stato e'' quello del suo ambiente');

SELECT is(
    (SELECT count(*)::int
       FROM dbops.processi_accensione a
       JOIN dbops.processi p ON p.id = a.processo_id
      WHERE p.codice = 'smoke_notturno'),
    0,
    '25-bis. ... e la scelta a mano non c''e'' piu''');

SELECT is(pg_temp.codice_errore($$SELECT dbops.fn_imposta_accensione_processo('listen_permessi', false, 'pgTAP: prova')$$),
          'E_PROCESSO_NON_SPEGNIBILE', '26. spegnere listen_permessi: E_PROCESSO_NON_SPEGNIBILE');

SELECT is(dbops.fn_imposta_accensione_processo('listen_permessi', true, 'pgTAP: conferma'),
          true, '27. confermare acceso un non spegnibile e'' ammesso');

SELECT is(pg_temp.codice_errore($$SELECT dbops.fn_imposta_accensione_processo('smoke_notturno', false, '   ')$$),
          'E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO', '28. motivo vuoto: E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO');

SELECT is(pg_temp.codice_errore($$SELECT dbops.fn_imposta_accensione_processo('avvio_manuale', false, 'pgTAP: prova')$$),
          'E_PROCESSO_SENZA_SVEGLIA', '29. un processo CODA non ha sveglia: E_PROCESSO_SENZA_SVEGLIA');

SELECT is(pg_temp.codice_errore($$SELECT dbops.fn_imposta_accensione_processo('PGTAP-PROCESSO-CHE-NON-ESISTE', false, 'pgTAP')$$),
          'E_PROCESSO_NON_TROVATO', '30. codice inesistente: E_PROCESSO_NON_TROVATO');

SELECT * FROM finish();

ROLLBACK;
