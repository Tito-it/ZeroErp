-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le liste del push a commessa non aprono il filtro di stato quando lo
--       stato non si trova nel catalogo.
-- Oggetti: vendite.fn_list_*_da_pushare (20261010-52 preventivi,
--   20261010-55 contratti).
-- Riferimento: brief-db-istanza-nasce-col-ba-residui (D-2, decisione di Tid
--   del 2026-10-10).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - lo stato di partenza (ACCETTATO, ATTIVO) si cerca nel catalogo per
--     codice_interno; se non c'e' (riga assente o spenta) la lista SOLLEVA
--     E_CODICE, come per la sorgente: non lista documenti in uno stato
--     qualunque;
--   - nessuna lista del push filtra lo stato nella forma
--     `v_stato_..._id IS NULL OR ...`, che con lo stato assente fa cadere il
--     filtro.
--
-- Elenco test (plan 3):
--   1) nessuna fn_list_*_da_pushare di vendite ha la forma `v_stato_..._id IS NULL OR`
--   2) preventivi: lo stato ACCETTATO assente solleva E_CODICE su config.stati_doc_preventivi
--   3) contratti: lo stato ATTIVO assente solleva E_CODICE su config.stati_doc_contratti
--
-- ⚠️ PRESIDIO SULLA FORMA, dichiarato. Il caso vero (lo stato spento nel
--   catalogo) e' raggiungibile sul modello — basta che nessun documento sia
--   in quello stato — ma un test non lo costruisce in modo deterministico:
--   dbops.trgfn_prevent_deactivate_if_children impedisce di spegnere uno
--   stato che un documento usa, e i documenti in quello stato dipendono dai
--   dati della macchina. Le due strade che lo forzerebbero (disattivare il
--   trigger, la GUC di bypass) non si usano in un pgTAP. Quindi si legge il
--   corpo: il test 1 fallisce se la forma che apre torna, in qualunque lista,
--   e i test 2-3 se il rifiuto sparisce.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — legge solo il catalogo delle funzioni.

SELECT plan(3);

-- ============================================================
-- 1) Nessuna lista del push apre il filtro di stato
-- ============================================================
SELECT is(
    (SELECT string_agg(p.proname, ', ' ORDER BY p.proname)
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite'
        AND p.proname ~ '^fn_list_.*_da_pushare$'
        AND p.prosrc ~* 'v_stato_\w+_id\s+IS\s+NULL\s+OR'),
    NULL,
    '1. Nessuna fn_list_*_da_pushare filtra lo stato con «IS NULL OR» (che con lo stato assente lista tutto)'
);

-- ============================================================
-- 2-3) Lo stato assente solleva E_CODICE col suo catalogo
-- ============================================================
SELECT ok(
    (SELECT p.prosrc ~ 'IF\s+v_stato_accettato_id\s+IS\s+NULL\s+THEN\s+PERFORM\s+script\.fn_log_and_raise_error\('
        AND p.prosrc ~ '''E_CODICE''[^;]*''ACCETTATO'',\s*''config\.stati_doc_preventivi'''
       FROM pg_proc p
      WHERE p.oid = 'vendite.fn_list_preventivi_da_pushare(date,bigint,integer,bigint,bigint[])'::regprocedure),
    '2. fn_list_preventivi_da_pushare: ACCETTATO assente dal catalogo -> E_CODICE (config.stati_doc_preventivi)'
);

SELECT ok(
    (SELECT p.prosrc ~ 'IF\s+v_stato_attivo_id\s+IS\s+NULL\s+THEN\s+PERFORM\s+script\.fn_log_and_raise_error\('
        AND p.prosrc ~ '''E_CODICE''[^;]*''ATTIVO'',\s*''config\.stati_doc_contratti'''
       FROM pg_proc p
      WHERE p.oid = 'vendite.fn_list_contratti_da_pushare(date,bigint,integer,bigint)'::regprocedure),
    '3. fn_list_contratti_da_pushare: ATTIVO assente dal catalogo -> E_CODICE (config.stati_doc_contratti)'
);

SELECT * FROM finish();
ROLLBACK;
