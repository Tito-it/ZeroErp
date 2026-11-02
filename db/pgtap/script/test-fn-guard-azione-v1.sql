-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il DB APPLICA un'azione di processo — script.fn_guard_azione — e il
--   gate di contesto di script.fn_resolve_livello_oggetto (passo 0, 20260924-40).
--   Brief: brief-db-magazzino-verbi-con-permesso, sezioni 2.1, 2.4 e 3.1.
--
-- ⭐ Il guard non contiene la regola: chiede a script.fn_check_azione_processo,
--   la stessa funzione del backend. Qui si prova che APPLICA quella risposta
--   (e che distingue il chiamante rotto dal permesso mancante), non la regola.
--
-- Elenco test (plan 9):
--   Il guard
--    1) azione inesistente -> E_CONFIG_MANCANTE (chiamante rotto, non rifiuto)
--    2) utente NULL -> E_PERMESSO_NEGATO (fail-closed)
--    3) operatore senza l'azione -> E_PERMESSO_NEGATO
--    4) operatore con l'azione (override costruito) -> passa
--    5) ...stesso operatore in veste CLIENTE_PORTALE -> E_PERMESSO_NEGATO (gate della regola)
--    6) il guard e' INVOKER e raggiungibile dall'app
--   Il gate di fn_resolve_livello_oggetto
--    7) override per oggetto LETTURA, veste OPERATORE -> LETTURA
--    8) ...stesso override in veste CLIENTE_PORTALE -> BLOCCATO (il difetto chiuso)
--    9) ...senza override, veste OPERATORE -> il livello d'area dell'OGGETTO (il quarto
--       parametro non conta piu', R4 del tetto d'area)
--
-- ⚠️ Rev 2026-10-04 (brief-db-permessi-tetto-area, 20261004-55/-57/-59): l'area e' un
--   tetto. Il test 4 regge perche' dbops.fn_pgtap_concedi_azione apre anche l'area
--   dell'azione al suo minimo; i test 7-9 aprono vendite a TUTTO, altrimenti l'override
--   LETTURA sotto un'area BLOCCATO varrebbe BLOCCATO e il test 7 proverebbe il tetto,
--   non il gate.
--
-- ⚠️ Gira come l'APPLICAZIONE: il guard deve funzionare con i privilegi dell'app,
--   e l'override per oggetto si scrive come lo scrive il pannello. Operatore
--   COSTRUITO (fn_pgtap_crea_emittente_operatore): tecnico, non super admin,
--   senza azioni — il permesso lo dà il test.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;

-- ============================================================
-- 1-6 Il guard
-- ============================================================
SELECT throws_like(
    $$ SELECT script.fn_guard_azione((SELECT auth_user_id FROM _mondo), 'pgtap_azione_che_non_esiste') $$,
    '%Configurazione mancante: azione di processo pgtap_azione_che_non_esiste%',
    '1) azione inesistente: E_CONFIG_MANCANTE — e'' il verbo a sbagliare, non un permesso mancante');

SELECT throws_like(
    $$ SELECT script.fn_guard_azione(NULL, 'registra_magazzino') $$,
    '%Non hai i permessi per questa operazione%',
    '2) utente NULL: E_PERMESSO_NEGATO (fail-closed, chi non dichiara chi e'' non scrive)');

SELECT throws_like(
    $$ SELECT script.fn_guard_azione((SELECT auth_user_id FROM _mondo), 'registra_magazzino') $$,
    '%Non hai i permessi per questa operazione%',
    '3) operatore senza l''azione: E_PERMESSO_NEGATO');

DO $az$ BEGIN PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _mondo), 'registra_magazzino'); END $az$;
SELECT lives_ok(
    $$ SELECT script.fn_guard_azione((SELECT auth_user_id FROM _mondo), 'registra_magazzino') $$,
    '4) operatore con l''azione: il guard passa');

SELECT set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);
SELECT throws_like(
    $$ SELECT script.fn_guard_azione((SELECT auth_user_id FROM _mondo), 'registra_magazzino') $$,
    '%Non hai i permessi per questa operazione%',
    '5) stesso operatore in veste CLIENTE_PORTALE: negata (il gate e'' della regola, il guard lo eredita)');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;

SELECT is(
    (SELECT (p.prosecdef, has_function_privilege('zeroerp_app', p.oid, 'EXECUTE'))::text
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script' AND p.proname = 'fn_guard_azione'),
    '(f,t)',
    '6) fn_guard_azione e'' INVOKER e l''app la esegue');

-- ============================================================
-- 7-9 Il gate di contesto di fn_resolve_livello_oggetto
-- ============================================================
-- L'oggetto di fixture entra a catalogo: dal 2026-09-28 un override per oggetto
-- esiste solo per un oggetto a catalogo (FK composita,
-- brief-db-be-fe-catalogo-oggetti-permessi D-4).
INSERT INTO config.area_model_overrides (app_label, model_name, area_id)
SELECT 'pgtap_app', 'pgtap_modello', af.id FROM config.aree_funzionali af WHERE af.schema_db = 'vendite';

-- Il tetto: vendite aperta, cosi' l'override LETTURA si legge per quello che e'.
INSERT INTO config.user_override_aree (auth_user_id, area_id, livello, motivo)
SELECT m.auth_user_id, af.id, 'TUTTO', 'Fixture pgTAP'
  FROM _mondo m, config.aree_funzionali af WHERE af.schema_db = 'vendite';

-- Un secondo oggetto a catalogo in vendite, senza override, per il test 9.
INSERT INTO config.area_model_overrides (app_label, model_name, area_id)
SELECT 'pgtap_app', 'pgtap_senza_override', af.id FROM config.aree_funzionali af WHERE af.schema_db = 'vendite';

INSERT INTO config.user_override_oggetti (auth_user_id, app_label, model_name, livello, motivo)
SELECT auth_user_id, 'pgtap_app', 'pgtap_modello', 'LETTURA', 'Fixture pgTAP' FROM _mondo;

SELECT is(
    script.fn_resolve_livello_oggetto((SELECT auth_user_id FROM _mondo), 'pgtap_app', 'pgtap_modello', 'vendite')::text,
    'LETTURA',
    '7) override per oggetto LETTURA, veste OPERATORE: LETTURA');

SELECT set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);
SELECT is(
    script.fn_resolve_livello_oggetto((SELECT auth_user_id FROM _mondo), 'pgtap_app', 'pgtap_modello', 'vendite')::text,
    'BLOCCATO',
    '8) stesso override in veste CLIENTE_PORTALE: BLOCCATO (prima del 20260924-40 rispondeva LETTURA)');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;

-- ⚠️ Fino al 2026-10-04 l'oggetto era fuori catalogo ('pgtap_altra_app') con l'area
--   'vendite' passata dal chiamante: BLOCCATO = BLOCCATO, verde per coincidenza. Col
--   tetto l'area la ricava la funzione dall'oggetto: si chiede un oggetto di vendite
--   con un'area SBAGLIATA nel quarto parametro, e deve tornare TUTTO.
SELECT is(
    script.fn_resolve_livello_oggetto((SELECT auth_user_id FROM _mondo), 'pgtap_app', 'pgtap_senza_override', 'magazzino')::text
    || ' ' || script.fn_resolve_livello_area((SELECT auth_user_id FROM _mondo), 'vendite')::text,
    'TUTTO TUTTO',
    '9) senza override, veste OPERATORE: il livello dell''area DELL''OGGETTO (il quarto parametro non conta)');

SELECT * FROM finish();
ROLLBACK;
