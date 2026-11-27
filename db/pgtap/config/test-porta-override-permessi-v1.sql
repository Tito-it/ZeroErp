-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: gli override utente si scrivono solo dai verbi del SUPER_ADMIN, e i due
--   cataloghi dei permessi solo dal seed.
-- Riferimento: brief-db-porte-aperte-dalla-sola-guc §15 (giro 10-quater; D-AI a,
--   D-AJ a, D-AK a di Tid, 2026-11-27); changeSet 20_code/config/20261126-50 (la
--   primitiva), -51 … -53 (i tre verbi), 20_code/anagrafiche/20261126-54 (il
--   provisioning), 20_code/dbops/20261126-55 … -59 (i builder), 90_end/20261126-62
--   (le tabelle in sola lettura), -63 (la primitiva riservata).
-- rev 2026-11-27 (brief-db-motivo-override-obbligatorio §6.3): il motivo di un
--   override e' obbligatorio (20261126-80): le due voci della prima chiamata del
--   caso 12 lo scrivono. La regola la collauda config/test-override-motivo-obbligatorio-v1.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - gli override utente (aree, azioni, oggetti) e i due cataloghi
--     (config.azioni_processo, config.area_model_overrides) sono in sola lettura
--     per l'app: l'INSERT con cui un operatore si darebbe TUTTO su un'area si
--     ferma sul privilegio (42501), e cosi' l'UPDATE del livello minimo di
--     un'azione, che cambierebbe il permesso di tutti;
--   - i tre verbi sono SECURITY DEFINER col search_path fissato e chiedono il
--     SUPER_ADMIN in prima riga: un operatore, o nessun utente, riceve
--     E_PERMESSO_NEGATO, e niente si scrive;
--   - la primitiva non la esegue ne' l'app ne' PUBLIC;
--   - dal SUPER_ADMIN il verbo SOSTITUISCE l'elenco dell'utente, e rifiuta una
--     chiave estranea;
--   - i builder cambiano una voce e lasciano le altre, e il contesto torna.
--
-- ⚠️ Nessun caso «due emittenti»: le tabelle non hanno RLS, e chi passa il guard
--   e' il SUPER_ADMIN, che vede tutte le aziende.
-- Gira come l'applicazione (runner di default). Da proprietario i privilegi non si
--   vedono: 4, 5 e 6 sono rossi per costruzione, e l'8 anche, perche' l'INSERT
--   del 4 da proprietario riesce.
--
-- Elenco test (plan 18):
--   forma
--    1) i tre verbi: SECURITY DEFINER, search_path fissato
--    2) l'app esegue i tre verbi, e non la primitiva (PUBLIC nemmeno)
--   la sola lettura
--    3) sulle cinque tabelle l'app ha SELECT e nessuna scrittura
--    4) un INSERT diretto di un override d'area a TUTTO per se stesso: 42501
--    5) un UPDATE diretto del livello minimo di un'azione: 42501
--    6) un DELETE diretto dal catalogo degli oggetti: 42501
--   il permesso dei verbi
--    7) un operatore imposta gli override d'area: E_PERMESSO_NEGATO
--    8) … e l'override non c'e'
--    9) un operatore imposta gli override d'azione: E_PERMESSO_NEGATO
--   10) un operatore imposta gli override d'oggetto: E_PERMESSO_NEGATO
--   11) senza utente in sessione il verbo rifiuta (fail-closed)
--   dal SUPER_ADMIN
--   12) il verbo sostituisce l'elenco: da due voci a una, quella data
--   13) una chiave estranea: E_CAMPO_NON_AMMESSO
--   i builder
--   14) concedi_livello_area cambia la sua voce e lascia l'azione concessa prima
--   15) nega_azione scrive l'azione negata
--   16) apri_area_per_nascita apre l'area a TUTTO …
--   17) … e richiudi_area la rimette com'era (tolta, se non c'era)
--   18) dopo i builder il contesto e' di nuovo l'operatore
-- ------------------------------------------------------------

BEGIN;

-- Un'azienda col suo operatore (non SUPER_ADMIN) e una persona a cui dare gli override.
CREATE TEMP TABLE _e ON COMMIT DROP AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

CREATE TEMP TABLE _p ON COMMIT DROP AS
SELECT o.identita_id, o.auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('porta-override', false) o;

-- Due aree attive e un'azione attiva del catalogo: i nomi non contano.
CREATE TEMP TABLE _cat ON COMMIT DROP AS
SELECT (SELECT af.id FROM config.aree_funzionali af WHERE af.attivo ORDER BY af.id LIMIT 1)          AS area_1,
       (SELECT af.id FROM config.aree_funzionali af WHERE af.attivo ORDER BY af.id OFFSET 1 LIMIT 1) AS area_2,
       (SELECT af.schema_db FROM config.aree_funzionali af WHERE af.attivo ORDER BY af.id OFFSET 1 LIMIT 1) AS area_2_schema,
       (SELECT ap.permission_codename FROM config.azioni_processo ap WHERE ap.attivo ORDER BY ap.id LIMIT 1) AS azione;

-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN
  PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e));
END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

-- ============================================================
-- 1-2 La forma
-- ============================================================
SELECT is(
  (SELECT COALESCE(array_agg(p.oid::regproc::text ORDER BY 1), ARRAY[]::text[])
     FROM pg_catalog.pg_proc p
    WHERE p.oid IN ('config.fn_imposta_override_aree'::regproc, 'config.fn_imposta_override_azioni'::regproc,
                    'config.fn_imposta_override_oggetti'::regproc)
      AND NOT (p.prosecdef
               AND EXISTS (SELECT 1 FROM unnest(p.proconfig) c WHERE c LIKE 'search\_path=%'))),
  ARRAY[]::text[],
  '1) i tre verbi: SECURITY DEFINER, search_path fissato');

SELECT is(
  (SELECT bool_and(has_function_privilege('zeroerp_app', p.oid, 'EXECUTE'))
     FROM pg_catalog.pg_proc p
    WHERE p.oid IN ('config.fn_imposta_override_aree'::regproc, 'config.fn_imposta_override_azioni'::regproc,
                    'config.fn_imposta_override_oggetti'::regproc))::text
  || '|' ||
  (SELECT (has_function_privilege('zeroerp_app', p.oid, 'EXECUTE')
           OR has_function_privilege('public', p.oid, 'EXECUTE'))::text
     FROM pg_catalog.pg_proc p
    WHERE p.oid = 'config.fn_applica_imposta_override'::regproc),
  'true|false',
  '2) l''app esegue i tre verbi, e non la primitiva (PUBLIC nemmeno)');

-- ============================================================
-- 3-6 La sola lettura
-- ============================================================
SELECT is(
  (SELECT COALESCE(array_agg(t ORDER BY t), ARRAY[]::text[])
     FROM unnest(ARRAY['config.user_override_aree', 'config.user_override_azioni',
                       'config.user_override_oggetti', 'config.azioni_processo',
                       'config.area_model_overrides']) AS t
    WHERE NOT has_table_privilege('zeroerp_app', t, 'SELECT')
       OR has_table_privilege('zeroerp_app', t, 'INSERT')
       OR has_table_privilege('zeroerp_app', t, 'UPDATE')
       OR has_table_privilege('zeroerp_app', t, 'DELETE')),
  ARRAY[]::text[],
  '3) sulle cinque tabelle l''app ha SELECT e nessuna scrittura');

SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    $q$INSERT INTO config.user_override_aree (auth_user_id, area_id, livello)
       VALUES (%s, %s, 'TUTTO')$q$, (SELECT auth_user_id FROM _e), (SELECT area_1 FROM _cat))),
  '42501',
  '4) ⭐ un INSERT diretto di un override d''area a TUTTO per se stesso: 42501');

SELECT is(
  dbops.fn_pgtap_codice_errore($q$UPDATE config.azioni_processo SET livello_minimo_area = livello_minimo_area WHERE false$q$),
  '42501',
  '5) un UPDATE diretto del livello minimo di un''azione: 42501');

SELECT is(
  dbops.fn_pgtap_codice_errore($q$DELETE FROM config.area_model_overrides WHERE false$q$),
  '42501',
  '6) un DELETE diretto dal catalogo degli oggetti: 42501');

-- ============================================================
-- 7-11 Il permesso dei verbi
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    $q$SELECT config.fn_imposta_override_aree(%s, jsonb_build_array(jsonb_build_object('area_id', %s, 'livello', 'TUTTO')))$q$,
    (SELECT auth_user_id FROM _e), (SELECT area_1 FROM _cat))),
  'E_PERMESSO_NEGATO',
  '7) un operatore imposta gli override d''area: E_PERMESSO_NEGATO');

SELECT is(
  (SELECT count(*)::int FROM config.user_override_aree uoa
    WHERE uoa.auth_user_id = (SELECT auth_user_id FROM _e)),
  0,
  '8) … e l''override non c''e''');

SELECT is(
  dbops.fn_pgtap_codice_errore(format($q$SELECT config.fn_imposta_override_azioni(%s, '[]'::jsonb)$q$,
                                      (SELECT auth_user_id FROM _p))),
  'E_PERMESSO_NEGATO',
  '9) un operatore imposta gli override d''azione: E_PERMESSO_NEGATO');

SELECT is(
  dbops.fn_pgtap_codice_errore(format($q$SELECT config.fn_imposta_override_oggetti(%s, '[]'::jsonb)$q$,
                                      (SELECT auth_user_id FROM _p))),
  'E_PERMESSO_NEGATO',
  '10) un operatore imposta gli override d''oggetto: E_PERMESSO_NEGATO');

DO $vuoto$ BEGIN PERFORM set_config('app.current_user_id', '', false); END $vuoto$;

SELECT is(
  dbops.fn_pgtap_codice_errore(format($q$SELECT config.fn_imposta_override_aree(%s, '[]'::jsonb)$q$,
                                      (SELECT auth_user_id FROM _p))),
  'E_PERMESSO_NEGATO',
  '11) senza utente in sessione il verbo rifiuta (fail-closed)');

DO $ctx2$ BEGIN
  PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e));
END $ctx2$;

-- ============================================================
-- 12-13 Dal SUPER_ADMIN
-- ============================================================
-- Il verbo vero, da un SUPER_ADMIN di fixture: due voci, poi una.
CREATE TEMP TABLE _sost (n integer, err text) ON COMMIT DROP;
DO $sa$
DECLARE
  v_prima jsonb;  -- il contesto di prima: nessuna colonna
  v_n     integer;  -- un conteggio
BEGIN
  v_prima := dbops.fn_pgtap_entra_come_super_admin('porta-override');
  PERFORM config.fn_imposta_override_aree((SELECT auth_user_id FROM _p), jsonb_build_array(
      jsonb_build_object('area_id', (SELECT area_1 FROM _cat), 'livello', 'TUTTO', 'motivo', 'pgTAP'),
      jsonb_build_object('area_id', (SELECT area_2 FROM _cat), 'livello', 'LETTURA', 'motivo', 'pgTAP')));
  v_n := config.fn_imposta_override_aree((SELECT auth_user_id FROM _p), jsonb_build_array(
      jsonb_build_object('area_id', (SELECT area_2 FROM _cat), 'livello', 'TUTTO', 'motivo', 'pgTAP')));
  INSERT INTO _sost (n, err)
  VALUES (v_n, dbops.fn_pgtap_codice_errore(format(
      $q$SELECT config.fn_imposta_override_aree(%s, jsonb_build_array(jsonb_build_object('area_id', %s, 'livello', 'TUTTO', 'meta', '{}'::jsonb)))$q$,
      (SELECT auth_user_id FROM _p), (SELECT area_1 FROM _cat))));
  PERFORM dbops.fn_pgtap_rimetti_contesto(v_prima);
END
$sa$;

SELECT is(
  (SELECT n FROM _sost)::text || '|' ||
  (SELECT string_agg(uoa.area_id::text || ':' || uoa.livello::text, ',' ORDER BY uoa.area_id)
     FROM config.user_override_aree uoa WHERE uoa.auth_user_id = (SELECT auth_user_id FROM _p)),
  '1|' || (SELECT area_2 FROM _cat)::text || ':TUTTO',
  '12) il verbo sostituisce l''elenco: da due voci a una, quella data');

SELECT is((SELECT err FROM _sost), 'E_CAMPO_NON_AMMESSO',
  '13) una chiave estranea: E_CAMPO_NON_AMMESSO');

-- ============================================================
-- 14-18 I builder
-- ============================================================
-- ⚠️ La scrittura in un'istruzione e la rilettura nelle successive.
SELECT dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _p), (SELECT azione FROM _cat));
SELECT dbops.fn_pgtap_concedi_livello_area((SELECT auth_user_id FROM _p), (SELECT area_2_schema FROM _cat), 'LETTURA');

SELECT is(
  (SELECT uoa.livello::text FROM config.user_override_aree uoa
    WHERE uoa.auth_user_id = (SELECT auth_user_id FROM _p) AND uoa.area_id = (SELECT area_2 FROM _cat))
  || '|' ||
  (SELECT uoz.abilitata::text FROM config.user_override_azioni uoz
     JOIN config.azioni_processo ap ON ap.id = uoz.azione_id
    WHERE uoz.auth_user_id = (SELECT auth_user_id FROM _p) AND ap.permission_codename = (SELECT azione FROM _cat)),
  'LETTURA|true',
  '14) concedi_livello_area cambia la sua voce e lascia l''azione concessa prima');

SELECT dbops.fn_pgtap_nega_azione((SELECT auth_user_id FROM _p), (SELECT azione FROM _cat));

SELECT is(
  (SELECT uoz.abilitata FROM config.user_override_azioni uoz
     JOIN config.azioni_processo ap ON ap.id = uoz.azione_id
    WHERE uoz.auth_user_id = (SELECT auth_user_id FROM _p) AND ap.permission_codename = (SELECT azione FROM _cat)),
  false,
  '15) nega_azione scrive l''azione negata');

-- L'apertura per una nascita, per l'operatore in sessione.
CREATE TEMP TABLE _ric ON COMMIT DROP AS
SELECT dbops.fn_pgtap_apri_area_per_nascita('magazzino', 'magazzini') AS ricordo;

SELECT is(
  (SELECT uoa.livello::text FROM config.user_override_aree uoa
    WHERE uoa.auth_user_id = (SELECT auth_user_id FROM _e)
      AND uoa.area_id = ((SELECT ricordo FROM _ric) ->> 'area_id')::integer),
  'TUTTO',
  '16) apri_area_per_nascita apre l''area a TUTTO …');

SELECT dbops.fn_pgtap_richiudi_area((SELECT ricordo FROM _ric));

SELECT is(
  (SELECT uoa.livello::text FROM config.user_override_aree uoa
    WHERE uoa.auth_user_id = (SELECT auth_user_id FROM _e)
      AND uoa.area_id = ((SELECT ricordo FROM _ric) ->> 'area_id')::integer),
  (SELECT ricordo FROM _ric) -> 'prima' ->> 'livello',
  '17) … e richiudi_area la rimette com''era (tolta, se non c''era)');

SELECT is(script.fn_utente_di_sessione(), (SELECT auth_user_id FROM _e),
  '18) dopo i builder il contesto e'' di nuovo l''operatore');

SELECT * FROM finish();
ROLLBACK;
