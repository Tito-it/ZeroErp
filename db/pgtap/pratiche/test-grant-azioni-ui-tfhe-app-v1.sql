-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: GRANT SELECT a zeroerp_app su pratiche.azioni_ui e
--       pratiche.template_flussi_handler_eventi (changeset 20260615-12)
-- ------------------------------------------------------------
-- Indice test (1..2):
--  1) zeroerp_app ha SELECT su pratiche.azioni_ui
--  2) zeroerp_app ha SELECT su pratiche.template_flussi_handler_eventi
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(2);

SELECT ok(
  has_table_privilege('zeroerp_app', 'pratiche.azioni_ui', 'SELECT'),
  'zeroerp_app ha SELECT su pratiche.azioni_ui'
);

SELECT ok(
  has_table_privilege('zeroerp_app', 'pratiche.template_flussi_handler_eventi', 'SELECT'),
  'zeroerp_app ha SELECT su pratiche.template_flussi_handler_eventi'
);

SELECT * FROM finish();

ROLLBACK;
