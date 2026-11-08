-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test STRUTTURALE — la copia di un'edizione di workflow è una porta riservata
--   pratiche.fn_copia_definizione · pratiche.fn_fork_definizione · pratiche.fn_nuova_versione_definizione
--
-- Brief: brief-db-sorgente-documento-e-riga §7.3 (giro finale, ⑩)
-- Sede della postura: 90_end/ci_apply/20260205-41 (voce in v_fn_riservate): il loop
--   dei grant rifà l'EXECUTE all'app a ogni passata, quindi la revoca vive lì.
--
-- ⭐ PERCHÉ È RISERVATA. fn_copia_definizione è INVOKER e scrive un'edizione intera
--   (testata, template, figli). La chiamano solo fn_fork_definizione e
--   fn_nuova_versione_definizione, SECURITY DEFINER del proprietario e con i loro
--   controlli (bozza unica, edizione d'origine pubblicata): dentro di loro gira come
--   proprietario. Eseguibile da PUBLIC, un chiamante qualunque avrebbe saltato quei
--   controlli. Né il backend né il frontend la chiamano.
--
-- ⚠️ GIRA COME L'APPLICAZIONE (runner di default): il soggetto è zeroerp_app.
--   I pgTAP che la chiamano direttamente (pratiche/test-guida-avanza-esito-proiettato)
--   girano come owner, che tiene sempre l'EXECUTE.
--
-- Elenco test (plan 4):
--   1 : l'app non esegue fn_copia_definizione
--   2 : PUBLIC non la esegue (l'=X di default è revocato)
--   3 : l'app esegue fn_fork_definizione — la strada vera resta aperta
--   4 : l'app esegue fn_nuova_versione_definizione — idem
--
-- Read-only: tutto dentro BEGIN;/ROLLBACK;. Nessuna riga scritta.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il file non attraversa tabelle in RLS, ma la riga sta
-- qui perché il preambolo è un contratto (guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(4);

SELECT is(has_function_privilege('zeroerp_app',
            'pratiche.fn_copia_definizione(integer, bigint, boolean)', 'EXECUTE'), false,
          '1. fn_copia_definizione: EXECUTE negato all''app — si copia solo da fork e nuova versione');

SELECT is(
  EXISTS (
    SELECT 1
      FROM pg_proc p, aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner))) a
     WHERE p.oid = 'pratiche.fn_copia_definizione(integer, bigint, boolean)'::regprocedure
       AND a.grantee = 0 AND a.privilege_type = 'EXECUTE'),
  false,
  '2. fn_copia_definizione: EXECUTE negato a PUBLIC');

SELECT is(has_function_privilege('zeroerp_app',
            'pratiche.fn_fork_definizione(integer, bigint)', 'EXECUTE'), true,
          '3. fn_fork_definizione: l''app la esegue, e copia come proprietario');

SELECT is(has_function_privilege('zeroerp_app',
            'pratiche.fn_nuova_versione_definizione(integer)', 'EXECUTE'), true,
          '4. fn_nuova_versione_definizione: l''app la esegue, e copia come proprietario');

SELECT * FROM finish();
ROLLBACK;
