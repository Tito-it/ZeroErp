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
