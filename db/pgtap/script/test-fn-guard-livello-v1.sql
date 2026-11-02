-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il DB APPLICA un livello su un oggetto — script.fn_area_di_oggetto
--   (20260925-31) e script.fn_guard_livello (20260925-32).
--   Brief: brief-db-pannello-config-verbo-generico, sezione 3.2.
--
-- ⭐ Il guard non contiene la regola: chiede a script.fn_resolve_livello_oggetto,
--   la stessa del backend, con l'area di fn_area_di_oggetto. Qui si prova che
--   APPLICA quella risposta, e che l'ordine ROVESCIATO dell'enum
--   (TUTTO < LETTURA < BLOCCATO) non gli fa concedere il contrario.
--
-- Elenco test (plan 12):
--   L'area di un oggetto
--    1) con un override in area_model_overrides: l'area dell'override, non app_label
--    2) senza override: app_label (area = schema)
--    3) oggetto NULL: NULL
--   Il guard (operatore costruito, livello dato con un override sull'oggetto)
--    4) utente NULL -> E_PERMESSO_NEGATO (fail-closed)
--    5) nessun livello concesso (BLOCCATO), minimo LETTURA -> negato
--    6) LETTURA, minimo TUTTO -> negato   ⛔ l'enum rovesciato, primo verso
--    7) LETTURA, minimo LETTURA -> passa   ⛔ secondo verso
--    8) TUTTO, minimo TUTTO -> passa
--    9) TUTTO ma in veste CLIENTE_PORTALE -> negato (il gate e' della regola)
--   10) minimo NULL -> negato
--   11) l'area del guard viene da fn_area_di_oggetto: TUTTO sull'area dell'override
--       basta, TUTTO su app_label no
--   La forma
--   12) tutte e due INVOKER, e l'app le esegue
--
-- ⚠️ Rev 2026-10-04 (brief-db-permessi-tetto-area, 20261004-57): l'area e' un TETTO.
--   Fino a quel giorno i test 6-8 davano il livello con il solo override sull'oggetto,
--   sotto l'area magazzino BLOCCATO: col tetto varrebbero BLOCCATO. L'override d'area
--   TUTTO su magazzino (era nel blocco 11) si scrive ora DOPO il test 5, che resta il
--   caso «nessun livello concesso»; il test 11 lo trova gia' scritto.
--
-- ⚠️ Gira come l'APPLICAZIONE: override e area si scrivono come li scrive il
--   pannello dei permessi. Operatore COSTRUITO (fn_pgtap_crea_emittente_operatore):
--   tecnico, non super admin, nessun livello — lo dà il test.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;

-- Il codice di un rifiuto (fn_log_and_raise_error lo mette in CONSTRAINT_NAME).
CREATE FUNCTION pg_temp.codice_di(p_sql text) RETURNS text AS $$
DECLARE v_cod text;
BEGIN
  EXECUTE p_sql;
  RETURN 'PASSA';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_cod = CONSTRAINT_NAME;
  RETURN COALESCE(NULLIF(v_cod, ''), 'SQLSTATE:' || SQLSTATE);
END $$ LANGUAGE plpgsql;

-- Un oggetto di fixture con un override d'area che NON coincide con app_label.
-- ⭐ E l'oggetto dei test 4-10, che riceve un override per oggetto: dal
--   2026-09-28 un override esiste solo per un oggetto a catalogo (FK composita,
--   brief-db-be-fe-catalogo-oggetti-permessi D-4), quindi entra anche lui. Area
--   magazzino: fino al test 5 l'operatore non ha livelli d'area, poi ha TUTTO su
--   magazzino (il tetto lascia passare l'override).
INSERT INTO config.area_model_overrides (app_label, model_name, area_id)
SELECT 'pgtap_app', m.model_name, af.id
  FROM config.aree_funzionali af, (VALUES ('pgtap_oggetto'), ('pgtap_modello')) m(model_name)
 WHERE af.schema_db = 'magazzino';

-- ============================================================
-- 1-3 L'area di un oggetto
-- ============================================================
SELECT is(script.fn_area_di_oggetto('pgtap_app', 'pgtap_oggetto')::text, 'magazzino',
    '1) con override: l''area dell''override (magazzino), non app_label');
SELECT is(script.fn_area_di_oggetto('pgtap_app', 'pgtap_senza_override')::text, 'pgtap_app',
    '2) senza override: app_label (area = schema)');
SELECT is(script.fn_area_di_oggetto(NULL, NULL)::text, NULL,
    '3) oggetto NULL: NULL');

-- ============================================================
-- 4-10 Il guard
-- ============================================================
SELECT is(pg_temp.codice_di($q$ SELECT script.fn_guard_livello(NULL, 'pgtap_app', 'pgtap_modello', 'LETTURA') $q$),
    'E_PERMESSO_NEGATO',
    '4) utente NULL: E_PERMESSO_NEGATO (fail-closed)');

SELECT is(pg_temp.codice_di(format($q$ SELECT script.fn_guard_livello(%s, 'pgtap_app', 'pgtap_modello', 'LETTURA') $q$,
                                   (SELECT auth_user_id FROM _mondo))),
    'E_PERMESSO_NEGATO',
    '5) nessun livello concesso: negato');

-- Il tetto: magazzino aperta a TUTTO, cosi' l'override sull'oggetto decide (restringe).
INSERT INTO config.user_override_aree (auth_user_id, area_id, livello, motivo)
SELECT m.auth_user_id, af.id, 'TUTTO', 'Fixture pgTAP'
  FROM _mondo m, config.aree_funzionali af WHERE af.schema_db = 'magazzino';

INSERT INTO config.user_override_oggetti (auth_user_id, app_label, model_name, livello, motivo)
SELECT auth_user_id, 'pgtap_app', 'pgtap_modello', 'LETTURA', 'Fixture pgTAP' FROM _mondo;

SELECT is(pg_temp.codice_di(format($q$ SELECT script.fn_guard_livello(%s, 'pgtap_app', 'pgtap_modello', 'TUTTO') $q$,
                                   (SELECT auth_user_id FROM _mondo))),
    'E_PERMESSO_NEGATO',
    '6) LETTURA con minimo TUTTO: negato (l''enum e'' TUTTO < LETTURA: un >= a occhio lo concederebbe)');

SELECT is(pg_temp.codice_di(format($q$ SELECT script.fn_guard_livello(%s, 'pgtap_app', 'pgtap_modello', 'LETTURA') $q$,
                                   (SELECT auth_user_id FROM _mondo))),
    'PASSA',
    '7) LETTURA con minimo LETTURA: passa');

UPDATE config.user_override_oggetti SET livello = 'TUTTO'
 WHERE auth_user_id = (SELECT auth_user_id FROM _mondo) AND app_label = 'pgtap_app' AND model_name = 'pgtap_modello';

SELECT is(pg_temp.codice_di(format($q$ SELECT script.fn_guard_livello(%s, 'pgtap_app', 'pgtap_modello', 'TUTTO') $q$,
                                   (SELECT auth_user_id FROM _mondo))),
    'PASSA',
    '8) TUTTO con minimo TUTTO: passa');

SELECT set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);
SELECT is(pg_temp.codice_di(format($q$ SELECT script.fn_guard_livello(%s, 'pgtap_app', 'pgtap_modello', 'TUTTO') $q$,
                                   (SELECT auth_user_id FROM _mondo))),
    'E_PERMESSO_NEGATO',
    '9) stesso operatore in veste CLIENTE_PORTALE: negato (il gate e'' della regola)');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;

SELECT is(pg_temp.codice_di(format($q$ SELECT script.fn_guard_livello(%s, 'pgtap_app', 'pgtap_modello', NULL) $q$,
                                   (SELECT auth_user_id FROM _mondo))),
    'E_PERMESSO_NEGATO',
    '10) minimo NULL: negato (fail-closed)');

-- ============================================================
-- 11 L'area la da' fn_area_di_oggetto
--   Override d'area TUTTO su magazzino (scritto prima del test 6); pgtap_app non
--   e' a catalogo: nessun livello. L'oggetto di fixture sta in magazzino per
--   override: il guard deve passare. Un oggetto dello stesso app_label senza
--   override non passa.
-- ============================================================

SELECT is(
    pg_temp.codice_di(format($q$ SELECT script.fn_guard_livello(%s, 'pgtap_app', 'pgtap_oggetto', 'TUTTO') $q$,
                             (SELECT auth_user_id FROM _mondo)))
    || ',' ||
    pg_temp.codice_di(format($q$ SELECT script.fn_guard_livello(%s, 'pgtap_app', 'pgtap_senza_override', 'TUTTO') $q$,
                             (SELECT auth_user_id FROM _mondo))),
    'PASSA,E_PERMESSO_NEGATO',
    '11) TUTTO sull''area dell''override basta; lo stesso app_label senza override no');

-- ============================================================
-- 12 La forma
-- ============================================================
SELECT is(
    (SELECT string_agg(p.proname || '=' || (p.prosecdef)::text || '/' ||
                       has_function_privilege('zeroerp_app', p.oid, 'EXECUTE')::text, ',' ORDER BY p.proname)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script' AND p.proname IN ('fn_area_di_oggetto', 'fn_guard_livello')),
    'fn_area_di_oggetto=false/true,fn_guard_livello=false/true',
    '12) tutte e due INVOKER, e l''app le esegue');

SELECT * FROM finish();
ROLLBACK;
