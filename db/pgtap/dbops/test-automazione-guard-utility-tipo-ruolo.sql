-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: automazione guard utility->tipo_ruolo
--
-- Elenco test:
-- 1) Seed rileva e configura anagrafiche.emittenti_fiscali_utilities
-- 2) Configurazione seed con colonne attese (utility_id, emittente_soggetto_ruolo_id)
-- 3) Apply crea trigger con funzione script.trgfn_guard_utility_tipo_ruolo_by_cols
-- 4) Trigger creato risulta BEFORE INSERT/UPDATE sulla tabella target
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. In testa e non in coda apposta:
--   in coda scatterebbero tutti insieme DOPO il cleanup, su righe ormai
--   cancellate. Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(4);

SELECT dbops.fn_seed_automazione_guard_utility_tipo_ruolo(ARRAY['anagrafiche']);

SELECT ok(
  EXISTS (
    SELECT 1
      FROM dbops.automazione_guard_utility_tipo_ruolo a
     WHERE a.schema_name = 'anagrafiche'
       AND a.table_name = 'emittenti_fiscali_utilities'
       AND a.enabled = true
  ),
  'Seed rileva e configura anagrafiche.emittenti_fiscali_utilities'
);

SELECT ok(
  EXISTS (
    SELECT 1
      FROM dbops.automazione_guard_utility_tipo_ruolo a
     WHERE a.schema_name = 'anagrafiche'
       AND a.table_name = 'emittenti_fiscali_utilities'
       AND a.utility_column = 'utility_id'
       AND a.soggetto_ruolo_column = 'emittente_soggetto_ruolo_id'
  ),
  'Configurazione seed con colonne attese (utility_id, emittente_soggetto_ruolo_id)'
);

SELECT dbops.fn_apply_automazione_guard_utility_tipo_ruolo('AUTO', false);

SELECT ok(
  EXISTS (
    SELECT 1
      FROM pg_trigger t
      JOIN pg_class c ON c.oid = t.tgrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
      JOIN pg_proc p ON p.oid = t.tgfoid
      JOIN pg_namespace pn ON pn.oid = p.pronamespace
     WHERE n.nspname = 'anagrafiche'
       AND c.relname = 'emittenti_fiscali_utilities'
       AND NOT t.tgisinternal
       AND pn.nspname = 'script'
       AND p.proname = 'trgfn_guard_utility_tipo_ruolo_by_cols'
  ),
  'Apply crea trigger con funzione script.trgfn_guard_utility_tipo_ruolo_by_cols'
);

SELECT ok(
  EXISTS (
    SELECT 1
      FROM pg_trigger t
      JOIN pg_class c ON c.oid = t.tgrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'anagrafiche'
       AND c.relname = 'emittenti_fiscali_utilities'
       AND NOT t.tgisinternal
       AND (t.tgtype & 2) = 2
       AND (t.tgtype & 4) = 4
       AND (t.tgtype & 16) = 16
  ),
  'Trigger creato risulta BEFORE INSERT/UPDATE sulla tabella target'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
