-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il building block script.fn_is_proprietario_tabella (20260925-37) e i
--   suoi tre consumatori. Brief: brief-db-magazzino-verbi-con-permesso, D-V1 / P-7.
--
-- ⭐ La domanda del BB e' «chi esegue e' il proprietario della tabella?». E' il
--   modo in cui un guard riconosce di essere attraversato da un verbo DEFINER, e
--   non da una scrittura diretta dell'app.
--
-- Elenco test (plan 7):
--   La forma
--    1) la funzione esiste con firma (regclass)
--    2) ⛔ e' SECURITY INVOKER e STABLE: una DEFINER vedrebbe il proprio
--       proprietario come current_user e direbbe si' a chiunque
--   Le risposte
--    3) tabella NULL -> false (fail-closed)
--    4) tabella inesistente (oid 0) -> false
--    5) l'app su magazzino.inventari -> false
--   I consumatori (regola del 2: la copia si ritira nello stesso giro)
--    6) ui.trgfn_lista_definizione_guard_multi_emittente: l'app che accende o spegne
--       multi_emittente riceve ancora E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE
--    7) i tre guard chiamano il BB con TG_RELID, e quello di ui non legge piu'
--       il proprietario da se' (relowner)
--
-- ⚠️ Gira come l'APPLICAZIONE (runner di default): il test 5 e' vero solo li'.
--   La risposta «si'» non si prova qui, perche' l'app non sa essere proprietaria:
--   la prova e' il verbo che attraversa le due porte, test 7b di
--   magazzino/test-documenti-interni-guard-v1.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- Il codice di un rifiuto (fn_log_and_raise_error lo mette in CONSTRAINT_NAME).
CREATE FUNCTION pg_temp.codice_di(p_sql text) RETURNS text AS $$
DECLARE v_cod text;
BEGIN
  EXECUTE p_sql;
  RETURN 'NESSUN ERRORE';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_cod = CONSTRAINT_NAME;
  RETURN COALESCE(NULLIF(v_cod, ''), 'SQLSTATE:' || SQLSTATE);
END $$ LANGUAGE plpgsql;

-- ============================================================
-- 1-2 La forma
-- ============================================================
SELECT has_function('script', 'fn_is_proprietario_tabella', ARRAY['regclass'],
    '1) script.fn_is_proprietario_tabella(regclass) esiste');

SELECT is(
    (SELECT (p.prosecdef, p.provolatile)::text
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script' AND p.proname = 'fn_is_proprietario_tabella'),
    '(f,s)',
    '2) INVOKER e STABLE: una DEFINER risponderebbe si'' a chiunque');

-- ============================================================
-- 3-5 Le risposte
-- ============================================================
SELECT is(script.fn_is_proprietario_tabella(NULL), false,
    '3) tabella NULL -> false (fail-closed)');

SELECT is(script.fn_is_proprietario_tabella(0::oid::regclass), false,
    '4) tabella inesistente -> false');

SELECT is(script.fn_is_proprietario_tabella('magazzino.inventari'::regclass), false,
    '5) l''app non e'' il proprietario di magazzino.inventari');

-- ============================================================
-- 6-7 I consumatori
-- ============================================================
SELECT is(
    pg_temp.codice_di($q$ UPDATE ui.lista_definizione SET multi_emittente = NOT multi_emittente
                          WHERE id = (SELECT min(id) FROM ui.lista_definizione) $q$),
    'E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE',
    '6) il guard di ui, passato dal BB, rifiuta ancora l''app');

SELECT is(
    (SELECT string_agg(n.nspname || '.' || p.proname || '='
                       || (p.prosrc LIKE '%script.fn_is_proprietario_tabella(TG_RELID)%')::text
                       -- relowner e non pg_class: il segno della copia e' la lettura del
                       -- proprietario, e «pg_class» compare anche nei commenti che la spiegano.
                       || CASE WHEN p.prosrc LIKE '%relowner%' THEN ',legge_relowner' ELSE '' END,
                       ' ' ORDER BY n.nspname, p.proname)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE (n.nspname, p.proname) IN (('magazzino', 'trgfn_documento_interno_guard_transizione'),
                                       ('magazzino', 'trgfn_documento_interno_righe_guard_testata'),
                                       ('ui', 'trgfn_lista_definizione_guard_multi_emittente'))),
    'magazzino.trgfn_documento_interno_guard_transizione=true '
    'magazzino.trgfn_documento_interno_righe_guard_testata=true '
    'ui.trgfn_lista_definizione_guard_multi_emittente=true',
    '7) i tre guard chiamano il BB con TG_RELID, nessuno legge il proprietario da se''');

SELECT * FROM finish();
ROLLBACK;
