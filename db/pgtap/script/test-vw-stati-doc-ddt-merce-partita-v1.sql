-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.vw_stati_doc_ddt_merce_partita — il BB «in questo stato del DDT la
--       merce e' partita?» e le sedi che ne erano copie
-- ChangeSet: 20261012-30 … -33
-- Brief: brief-db-date-consegna-righe-in-blocco (§4.1, regola del 2, scelta (a) di Tid)
-- ------------------------------------------------------------
-- Indice test (plan 8):
--   1) ⛔ la vista esiste ed e' security_invoker
--   2) l'applicazione la legge
--   3) una riga per ogni stato del catalogo, e merce_partita mai NULL
--   4) ⭐ i casi che la regola distingue, dal seed (contratto, non popolazione):
--      DRAFT no (bozza), EMESSO si' (la soglia), RESO si' (merce tornata non e'
--      documento annullato), ANNULLATO no (abortito, anche se ordine > EMESSO)
--   5) ⭐ fail-closed: uno stato fabbricato con ordine NULL non e' «partito»
--   6) ⭐ la copia ritirata in vendite.fn_partite_merce: legge il BB, niente soglia di EMESSO
--   7) ⭐ la copia ritirata in vendite.fn_ordine_riga_spedita: legge il BB
--   8) ⭐ la copia ritirata in dbops.vw_ddt_emessi_senza_scarico: legge il BB, niente elenco
--
-- ⚠️ Il comportamento dei tre consumatori lo presidiano i loro pgTAP, che non
--   cambiano: vendite/test-data-consegna-confermata-riga-spedita-v1 (il lettore),
--   i pgTAP della partita merce (fn_partite_merce), il digest dei presidi.
--   Qui si presidia la SEDE: che la regola stia in un posto solo.
-- ------------------------------------------------------------

BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- ============================================================
-- 1-3) L'oggetto
-- ============================================================
SELECT ok(
  (SELECT c.reloptions @> ARRAY['security_invoker=true']
     FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'script' AND c.relname = 'vw_stati_doc_ddt_merce_partita' AND c.relkind = 'v'),
  '1) la vista esiste ed e'' security_invoker');

SELECT ok(
  has_table_privilege('zeroerp_app', 'script.vw_stati_doc_ddt_merce_partita', 'SELECT'),
  '2) l''applicazione la legge');

SELECT is(
  (SELECT count(*)::int FROM script.vw_stati_doc_ddt_merce_partita)
  || ' | ' || (SELECT count(*)::int FROM script.vw_stati_doc_ddt_merce_partita WHERE merce_partita IS NULL),
  (SELECT count(*)::int FROM config.stati_doc_ddt) || ' | 0',
  '3) una riga per ogni stato, e merce_partita mai NULL');

-- ============================================================
-- 4-5) La regola
-- ============================================================
SELECT results_eq(
  $$SELECT v.codice_interno::text, v.merce_partita
      FROM script.vw_stati_doc_ddt_merce_partita v
     WHERE v.codice_interno IN ('DRAFT', 'EMESSO', 'RESO', 'ANNULLATO')
     ORDER BY v.codice_interno$$,
  $$VALUES ('ANNULLATO', false), ('DRAFT', false), ('EMESSO', true), ('RESO', true)$$,
  '4) DRAFT no, EMESSO si'', RESO si'', ANNULLATO no (abortito, anche dopo EMESSO)');

-- Uno stato senza posizione nella sequenza: la regola non lo sa collocare, e
-- nel dubbio la merce NON e' partita. Fabbricato e ritirato col ROLLBACK.
-- ⚠️ id esplicito oltre il massimo: il seed del catalogo porta id espliciti.
INSERT INTO config.stati_doc_ddt (id, codice_interno, codice, descrizione, attivo, ordine,
                                  pdf_mode, pdf_allow_allegati, fase, is_abortito)
SELECT COALESCE(max(id), 0) + 1000, 'PGTAP_SENZA_ORDINE', 'PGTAP_SENZA_ORDINE', 'pgTAP', true, NULL,
       'PREVIEW', false, 'IN_CORSO', false
  FROM config.stati_doc_ddt;

SELECT is(
  (SELECT v.merce_partita FROM script.vw_stati_doc_ddt_merce_partita v
    WHERE v.codice_interno = 'PGTAP_SENZA_ORDINE'),
  false,
  '5) uno stato con ordine NULL: false, non NULL (fail-closed)');

-- ============================================================
-- 6-8) Le copie ritirate: la regola sta in un posto solo
-- ============================================================
-- ⛔ Il catalogo stampa i nomi SENZA schema quando lo schema e' nel search_path
--   della sessione (quello dell'app contiene config e script): sotto il runner
--   `script.vw_…` usciva `vw_…` (test 6 rosso dopo l'apply, 2026-10-12) e la
--   negazione su `config.stati_doc_ddt` era verde per sottrazione. Si legge
--   con un search_path neutro: i nomi escono sempre qualificati.
CREATE FUNCTION pg_temp.mp_sqlbody(p regprocedure) RETURNS text
  LANGUAGE sql STABLE SET search_path = pg_catalog
  AS $$ SELECT pg_get_function_sqlbody(p) $$;
CREATE FUNCTION pg_temp.mp_viewdef(p regclass) RETURNS text
  LANGUAGE sql STABLE SET search_path = pg_catalog
  AS $$ SELECT pg_get_viewdef(p) $$;

-- Il corpo BEGIN ATOMIC dal catalogo: niente commenti, nomi qualificati.
SELECT ok(
  (SELECT b ~ 'script\.vw_stati_doc_ddt_merce_partita'
      AND b !~ '''EMESSO'''
      AND b !~ 'config\.stati_doc_ddt\M'
     FROM (SELECT pg_temp.mp_sqlbody('vendite.fn_partite_merce(bigint[],bigint[])'::regprocedure) AS b) x),
  '6) vendite.fn_partite_merce legge il BB e non porta piu'' la soglia di EMESSO');

SELECT ok(
  (SELECT b ~ 'script\.vw_stati_doc_ddt_merce_partita'
      AND b !~ '''EMESSO'''
      AND b !~ 'config\.stati_doc_ddt\M'
     FROM (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g') AS b
             FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'vendite' AND p.proname = 'fn_ordine_riga_spedita') x),
  '7) vendite.fn_ordine_riga_spedita legge il BB');

SELECT ok(
  (SELECT b ~ 'script\.vw_stati_doc_ddt_merce_partita'
      AND b !~ 'config\.stati_doc_ddt\M'
      AND b !~ '''(EMESSO|SPEDITO|CONSEGNATO|RESO)'''
     FROM (SELECT pg_temp.mp_viewdef('dbops.vw_ddt_emessi_senza_scarico'::regclass) AS b) x),
  '8) dbops.vw_ddt_emessi_senza_scarico legge il BB, niente elenco di codici');

SELECT * FROM finish();
ROLLBACK;
