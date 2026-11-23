-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test STRUTTURALE: in maintenance, le SECURITY DEFINER che l'app esegue sono
--   un elenco dichiarato
--
-- Brief: brief-db-porte-aperte-dalla-sola-guc §6.5 (D-H a)
-- Sede della postura: i changeSet che creano le routine (REVOKE … FROM PUBLIC,
--   lo stampo di 20_code/maintenance/20261014-55); `maintenance` e' fuori dal
--   loop dei grant e dal provisioning delle funzioni.
--
-- ⭐ PERCHE' LE DEFINER E SOLO LORO. Le funzioni di maintenance che non hanno un
--   REVOKE tengono l'=X di default di PUBLIC, e il privilegio di default per
--   schema non lo toglie. Una INVOKER gira coi permessi dell'app: eseguirla non
--   da' all'app niente che non possa fare da se'. Una DEFINER gira come
--   proprietario: e' l'unico caso in cui una routine di maintenance darebbe
--   all'app piu' dei suoi permessi. Il test guarda quella classe, a criterio:
--   una DEFINER nuova nata aperta lo fa diventare rosso.
--
-- L'ELENCO DICHIARATO (2026-11-24):
--   * fn_sveglia_accesa — legge se un processo e' acceso; la chiamano il BE
--     (`e_dovuto`, `maintenance_repository`, connessione zeroerp_app) e i passi
--     dei job pgAgent (zeroerp_job). Scrive niente;
--   * fn_job_run_log_failure — scrive una corsa fallita nel giornale, timbrando
--     ruolo_sessione e agent_host della sessione: cio' che l'app fa gia' col
--     verbo script.fn_job_run_start / fn_job_run_end. La chiama fn_run_and_log.
--   Una voce nuova si aggiunge qui con il suo perche'; una DEFINER che l'app non
--   deve eseguire riceve il suo REVOKE … FROM PUBLIC nel changeSet che la crea.
--
-- ⚠️ GIRA COME L'APPLICAZIONE (runner di default). Il caso costruito (una DEFINER
--   nuova in maintenance) chiede DDL nello schema, che l'app non puo' fare: il
--   presidio e' il criterio sul catalogo, che vale per ogni routine presente.
--
-- Elenco test (plan 2):
--   1 : le DEFINER di maintenance eseguibili dall'app sono esattamente l'elenco
--   2 : l'elenco non e' vuoto per sottrazione: le due voci esistono e sono DEFINER
--
-- Read-only: tutto dentro BEGIN;/ROLLBACK;. Nessuna riga scritta.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il file non attraversa tabelle in RLS, ma la riga sta
-- qui perche' il preambolo e' un contratto (guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(2);

SELECT set_eq(
    $$SELECT p.proname::text
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
       WHERE n.nspname = 'maintenance'
         AND p.prosecdef
         AND has_function_privilege('zeroerp_app', p.oid, 'EXECUTE')$$,
    ARRAY['fn_sveglia_accesa', 'fn_job_run_log_failure'],
    '1. in maintenance l''app esegue solo le SECURITY DEFINER dichiarate');

SELECT is(
    (SELECT count(*)::int
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'maintenance'
        AND p.prosecdef
        AND p.proname IN ('fn_sveglia_accesa', 'fn_job_run_log_failure')),
    2,
    '2. le due voci dell''elenco esistono e sono SECURITY DEFINER');

SELECT * FROM finish();
ROLLBACK;
