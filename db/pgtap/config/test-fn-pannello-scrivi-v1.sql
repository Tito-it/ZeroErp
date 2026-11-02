-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il verbo del pannello di configurazione — config.fn_pannello_scrivi
--   (20260925-33). Brief: brief-db-pannello-config-verbo-generico, sezione 3.3.
--
-- ⭐ Il soggetto e' la D-3: il livello si chiede sull'OGGETTO della riga, non
--   sull'area del pannello. Chi ha TUTTO su Configurazione scrive le tabelle di
--   config, ma non le causali di magazzino (test 10).
--
-- Elenco test (plan 14):
--   Il passo 0: la tabella
--    1) fuori dalla lista -> E_PANNELLO_TABELLA_NON_AMMESSA
--    2) in lista ma fuori dal pannello (magazzino.magazzini, RLS: D-P2) -> idem
--   Il passo 1: il permesso
--    3) operatore senza livello su config -> E_PERMESSO_NEGATO
--   Con TUTTO sull'area config (override d'area)
--    4) INSERT su config.tipi_nota: passa, ritorna la riga con id e senza audit
--    5) UPDATE della stessa riga: passa, il valore cambia
--   Il passo 2: il payload (D-P3)
--    6) una chiave che non e' una colonna -> E_PANNELLO_CAMPO_NON_AMMESSO
--    7) una colonna esclusa (data_insert) -> idem
--    8) payload vuoto -> E_PANNELLO_DATI_VUOTI
--   Il passo 3
--    9) UPDATE di un id che non c'e' -> E_PANNELLO_RIGA_NON_TROVATA
--   ⭐ Il livello e' sull'area della riga (la chiave della tabella la da', D-2)
--   10) TUTTO su config NON basta per magazzino.causali -> E_PERMESSO_NEGATO
--   11) ⛔ ('magazzino', 'causali') non e' a catalogo: nessun override per oggetto
--       (FK composita, D-4 del brief catalogo-oggetti) -> 23503
--   12) ...con TUTTO sull'AREA della riga (magazzino) si scrive: una chiave non a
--       catalogo vale come la sua area (D-2 dello stesso brief)
--   13) ⛔ config.profili_accesso, con TUTTO su config -> E_PANNELLO_TABELLA_NON_AMMESSA
--       (D-P6: il pannello non e' una seconda strada per i profili di permesso;
--       fino al 2026-09-27 qui c'era ui.lista_definizione, uscita anch'essa)
--   La forma
--   14) SECURITY DEFINER del proprietario, search_path bloccato
--   15) l'app la esegue, PUBLIC no
--
-- ⚠️ Gira come l'APPLICAZIONE (runner di default). Operatore COSTRUITO
--   (fn_pgtap_crea_emittente_operatore): tecnico, non super admin; i livelli li
--   concede il test con gli override, come il pannello dei permessi.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

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

-- ============================================================
-- 1-3 La tabella e il permesso
-- ============================================================
SELECT is(pg_temp.codice_di($q$ SELECT config.fn_pannello_scrivi('config.pgtap_non_esiste', NULL, '{"codice":"X"}') $q$),
    'E_PANNELLO_TABELLA_NON_AMMESSA',
    '1) tabella fuori dalla lista: E_PANNELLO_TABELLA_NON_AMMESSA');

SELECT is(pg_temp.codice_di($q$ SELECT config.fn_pannello_scrivi('magazzino.magazzini', NULL, '{"codice":"X"}') $q$),
    'E_PANNELLO_TABELLA_NON_AMMESSA',
    '2) magazzino.magazzini: nelle tendine ma non nel pannello (RLS, D-P2)');

SELECT is(pg_temp.codice_di($q$ SELECT config.fn_pannello_scrivi('config.tipi_nota', NULL,
                                   '{"codice":"PGT_NOTA","codice_interno":"PGT_NOTA","descrizione":"pgTAP"}') $q$),
    'E_PERMESSO_NEGATO',
    '3) operatore senza livello su config: E_PERMESSO_NEGATO');

-- TUTTO sull'area Configurazione, come lo concede il pannello dei permessi.
INSERT INTO config.user_override_aree (auth_user_id, area_id, livello, motivo)
SELECT m.auth_user_id, af.id, 'TUTTO', 'Fixture pgTAP'
  FROM _mondo m, config.aree_funzionali af WHERE af.schema_db = 'config';

-- ============================================================
-- 4-5 Inserimento e modifica
-- ============================================================
CREATE TEMP TABLE _nota AS
SELECT config.fn_pannello_scrivi('config.tipi_nota', NULL,
           '{"codice":"PGT_NOTA","codice_interno":"PGT_NOTA","descrizione":"pgTAP"}') AS riga;

SELECT is(
    (SELECT format('%s|%s|%s', (riga ? 'id')::text, riga ->> 'descrizione', (riga ? 'data_insert')::text) FROM _nota),
    'true|pgTAP|false',
    '4) INSERT su config.tipi_nota: ritorna la riga con id e senza le colonne di audit');

SELECT is(
    (SELECT config.fn_pannello_scrivi('config.tipi_nota', (riga ->> 'id')::bigint,
                                      '{"descrizione":"pgTAP modificata"}') ->> 'descrizione' FROM _nota),
    'pgTAP modificata',
    '5) UPDATE della stessa riga: il valore cambia');

-- ============================================================
-- 6-9 Il payload e la riga
-- ============================================================
SELECT is(pg_temp.codice_di(format($q$ SELECT config.fn_pannello_scrivi('config.tipi_nota', %s, '{"descrizione":"x","non_esiste":1}') $q$,
                                   (SELECT riga ->> 'id' FROM _nota))),
    'E_PANNELLO_CAMPO_NON_AMMESSO',
    '6) chiave che non e'' una colonna: rifiutata, non scartata (D-P3)');

SELECT is(pg_temp.codice_di(format($q$ SELECT config.fn_pannello_scrivi('config.tipi_nota', %s, '{"data_insert":"2026-01-01"}') $q$,
                                   (SELECT riga ->> 'id' FROM _nota))),
    'E_PANNELLO_CAMPO_NON_AMMESSO',
    '7) colonna esclusa (data_insert): rifiutata');

SELECT is(pg_temp.codice_di(format($q$ SELECT config.fn_pannello_scrivi('config.tipi_nota', %s, '{}') $q$,
                                   (SELECT riga ->> 'id' FROM _nota))),
    'E_PANNELLO_DATI_VUOTI',
    '8) payload vuoto: E_PANNELLO_DATI_VUOTI');

SELECT is(pg_temp.codice_di($q$ SELECT config.fn_pannello_scrivi('config.tipi_nota', 2147483000, '{"descrizione":"x"}') $q$),
    'E_PANNELLO_RIGA_NON_TROVATA',
    '9) UPDATE di un id che non c''e'': E_PANNELLO_RIGA_NON_TROVATA');

-- ============================================================
-- 10-13 Il livello e' sull'area della riga (D-3; D-2 del brief catalogo-oggetti)
-- ============================================================
SELECT is(pg_temp.codice_di($q$ SELECT config.fn_pannello_scrivi('magazzino.causali',
                                   (SELECT id FROM magazzino.causali WHERE codice_interno = 'CARICO_ACQ'),
                                   jsonb_build_object('descrizione',
                                       (SELECT descrizione FROM magazzino.causali WHERE codice_interno = 'CARICO_ACQ'))) $q$),
    'E_PERMESSO_NEGATO',
    '10) ⭐ TUTTO su Configurazione NON basta per le causali di magazzino: si chiede l''area della riga');

-- ⭐ Fino al 2026-09-28 il test 11 concedeva TUTTO con un override sull'oggetto
--   ('magazzino', 'causali'). La D-2 del brief catalogo-oggetti ha deciso che le
--   chiavi del pannello NON sono oggetti personalizzabili: valgono come la loro
--   area. La D-4 lo rende un vincolo, e questi due test lo dichiarano.
SELECT throws_ok(
    format($$INSERT INTO config.user_override_oggetti (auth_user_id, app_label, model_name, livello, motivo)
             VALUES (%s, 'magazzino', 'causali', 'TUTTO', 'Fixture pgTAP')$$,
           (SELECT auth_user_id FROM _mondo)),
    '23503', NULL,
    '11) ⛔ (''magazzino'', ''causali'') non e'' a catalogo: nessun override per oggetto (D-4)');

INSERT INTO config.user_override_aree (auth_user_id, area_id, livello, motivo)
SELECT m.auth_user_id, af.id, 'TUTTO', 'Fixture pgTAP'
  FROM _mondo m, config.aree_funzionali af WHERE af.schema_db = 'magazzino';

SELECT is(pg_temp.codice_di($q$ SELECT config.fn_pannello_scrivi('magazzino.causali',
                                   (SELECT id FROM magazzino.causali WHERE codice_interno = 'CARICO_ACQ'),
                                   jsonb_build_object('descrizione',
                                       (SELECT descrizione FROM magazzino.causali WHERE codice_interno = 'CARICO_ACQ'))) $q$),
    'PASSA',
    '12) ...con TUTTO sull''area della riga (magazzino) si scrive: la chiave vale come la sua area (D-2)');

SELECT is(pg_temp.codice_di($q$ SELECT config.fn_pannello_scrivi('config.profili_accesso',
                                   (SELECT min(id) FROM config.profili_accesso), '{"descrizione":"x"}') $q$),
    'E_PANNELLO_TABELLA_NON_AMMESSA',
    '13) ⛔ config.profili_accesso: TUTTO su Configurazione non apre il pannello sui profili di permesso (D-P6)');

-- ============================================================
-- 14-15 La forma
-- ============================================================
SELECT is(
    (SELECT format('%s|%s|%s', p.prosecdef::text,
                   (pg_get_userbyid(p.proowner) = (SELECT pg_get_userbyid(relowner) FROM pg_class
                                                    WHERE oid = 'config.tabelle_gestibili'::regclass))::text,
                   array_to_string(p.proconfig, ';'))
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'config' AND p.proname = 'fn_pannello_scrivi'),
    'true|true|search_path=pg_catalog, public, pg_temp',
    '14) SECURITY DEFINER del proprietario delle tabelle, search_path bloccato');

SELECT is(
    (SELECT format('%s|%s', has_function_privilege('zeroerp_app', p.oid, 'EXECUTE')::text,
                   (EXISTS (SELECT 1 FROM aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner))) x
                             WHERE x.grantee = 0 AND x.privilege_type = 'EXECUTE'))::text)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'config' AND p.proname = 'fn_pannello_scrivi'),
    'true|false',
    '15) l''app la esegue, PUBLIC no');

SELECT * FROM finish();
ROLLBACK;
