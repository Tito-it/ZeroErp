-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_ddt_da_pushare — parametro p_ddt_id (v2)
-- ------------------------------------------------------------
-- Indice test (1..5):
-- 1) Firma funzione: 4 parametri (pronargs)
-- 2) p_ddt_id NULL: smoke — funzione eseguita senza eccezioni (regressione batch)
-- 3) p_ddt_id inesistente: 0 righe, no errore
-- 4) uom_id non NULL per righe pushable (fix bug proiezione NULL)
-- 5) anti-regressione: rename codice sorgente DDT_VENDITA -> risoluzione per codice_interno (no E_CODICE)
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

-- ============================================================
-- TEST 1) Firma funzione: 4 parametri
-- ============================================================
SELECT ok(
  (SELECT p.pronargs = 4
     FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_ddt_da_pushare'
    LIMIT 1),
  'fn_list_ddt_da_pushare ha 4 parametri (pronargs = 4)'
);

-- ============================================================
-- TEST 2) p_ddt_id NULL: smoke — regressione batch invariata
-- ============================================================
SELECT ok(
  (SELECT COUNT(*) >= 0
     FROM vendite.fn_list_ddt_da_pushare(p_ddt_id => NULL)),
  'p_ddt_id NULL: funzione eseguita senza eccezioni (smoke regressione batch)'
);

-- ============================================================
-- TEST 3) p_ddt_id inesistente: 0 righe, no errore
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_ddt_da_pushare(p_ddt_id => 999999999::bigint)
  ),
  'p_ddt_id inesistente: 0 righe, no errore'
);

-- ============================================================
-- TEST 4) uom_id non NULL per righe pushable (fix bug proiezione NULL)
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM vendite.fn_list_ddt_da_pushare(p_limit => 1) WHERE uom_id IS NULL
  ),
  'fn_list_ddt_da_pushare: uom_id valorizzato da catalogo.articoli (fix bug proiezione NULL)'
);

-- ============================================================
-- TEST 5) Anti-regressione codice_interno (analisi-hardcoded-codice §3a):
--   rinominando il `codice` (mutabile) della sorgente, la funzione DEVE
--   continuare a risolverla per `codice_interno` (immutabile): nessun E_CODICE.
-- ============================================================
UPDATE config.sorgenti
   SET codice = codice || '_RENAMED'
 WHERE codice_interno = 'DDT_VENDITA';

SELECT lives_ok(
  $$ SELECT 1 FROM vendite.fn_list_ddt_da_pushare(p_limit => 1) $$,
  '5. anti-regressione: rename codice sorgente DDT_VENDITA -> risoluzione per codice_interno (no E_CODICE)'
);

SELECT * FROM finish();
ROLLBACK;
