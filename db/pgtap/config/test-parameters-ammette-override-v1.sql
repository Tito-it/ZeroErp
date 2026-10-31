-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la famiglia di un parametro (config.parameters.ammette_override) e i
--       due guard che la fanno rispettare; la lista che la espone; i default
--       dei dati societari letti con la cascata della sessione.
--       Brief: brief-db-parametri-senza-override (D-1, D-2-bis, D-4).
--       Migrations:
--         20261025-83 (colonna, DEFAULT temporaneo) · 90_end/20261025-88 (via il DEFAULT)
--         20261025-84 (guard sugli override, a05) · 20261025-85 (guard inverso)
--         20261025-86 (fn_list_parameters_for_user) · 20261025-87 (fn_scrivi_dati_societari)
--
-- ⭐ I parametri sono COSTRUITI dal test, non presi dal catalogo: quali parametri
--   reali valgano per tutti lo dice il CSV, e un elenco qui sarebbe una seconda
--   copia della famiglia (§3 del brief, l'alternativa scartata).
--
-- Elenco test (plan 21):
--  1) colonna ammette_override presente
--  2) NOT NULL
--  3) senza DEFAULT (lo toglie 90_end)
--  4) INSERT di un parametro senza la colonna -> 23502
--  5) override su un parametro senza override -> E_PARAMETER_OVERRIDE_NON_AMMESSO
--  6) idem con l'override spento (attivo = false)
--  7) override su un parametro con override -> ammesso
--  8) UPDATE del solo parametro dell'override verso uno senza override -> rifiutato
--  9) UPDATE del valore di un override ammesso -> passa (il guard guarda il parametro)
-- 10) ordine: su un parametro del registro FK-surrogata senza override e con un
--     valore che il registro rifiuta, parla il guard della famiglia (a05)
-- 11) trigger del guard sugli override prima del dispatcher (nome)
-- 12) con -> senza override, con un override acceso -> E_PARAMETER_OVERRIDE_PRESENTI
-- 13) idem con l'override solo spento
-- 14) con -> senza override, senza override -> passa
-- 15) senza -> con override -> passa
-- 16) la lista espone ammette_override (false sul parametro senza override)
-- 17) la lista espone ammette_override (true sul parametro con override)
-- 18) la lista: resolved_value del parametro senza override = default
-- 19) setup: il soggetto PG del builder ha i dati societari
-- 20) fn_scrivi_dati_societari, socio_unico NULL, emittente in sessione con
--     override -> il valore dell'override di quell'emittente
-- 21) idem senza emittente in sessione -> il default del parametro
--
-- Scopo:
--  - il difetto che chiude: un override su un parametro che vale per tutti era
--    accettato e ignorato; ora si rifiuta, e la lista lo dice.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(21);

-- ============================================================
-- Fixture: due parametri di prova, uno per famiglia, e un parametro del
-- registro FK-surrogata (pattern DEFAULT_TIPO_SOGGETTO_DETTAGLIO_%) che vale per
-- tutti. Ogni override ha esattamente un ambito: qui la funzione.
-- ============================================================
INSERT INTO config.parameters (id, code, default_value, description, ammette_override, tipo_valore)
VALUES (99950, '_TEST_SENZA_OVR_', 'DEF_SENZA', 'pgTAP ammette_override: vale per tutti', false, 'TESTO'),
       (99951, '_TEST_CON_OVR_',   'DEF_CON',   'pgTAP ammette_override: con override',   true,  'TESTO');

INSERT INTO config.parameters (id, code, default_value, description, ammette_override, tipo_valore)
SELECT 99952, 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_PGTAP_SENZA', t.codice_interno,
       'pgTAP ammette_override: registro FK-surrogata, vale per tutti', false, 'TESTO'
  FROM (SELECT codice_interno FROM config.tipi_soggetto_dettaglio ORDER BY id LIMIT 1) t;

-- ============================================================
-- 1-4) La colonna
-- ============================================================
SELECT has_column('config', 'parameters', 'ammette_override',
    '1) colonna config.parameters.ammette_override presente');

SELECT col_not_null('config', 'parameters', 'ammette_override',
    '2) ammette_override NOT NULL');

SELECT col_hasnt_default('config', 'parameters', 'ammette_override',
    '3) ammette_override senza DEFAULT: un parametro nuovo dichiara la sua famiglia');

SELECT throws_ok(
    $$INSERT INTO config.parameters (id, code, default_value, description, tipo_valore)
      VALUES (99953, '_TEST_SENZA_FAMIGLIA_', 'X', 'pgTAP senza famiglia', 'TESTO')$$,
    '23502', NULL,
    '4) INSERT di un parametro senza ammette_override -> 23502');

-- ============================================================
-- 5-9) Il guard sugli override
-- ============================================================
SELECT throws_like(
    $$INSERT INTO config.parameter_overrides (parameter_id, overridden_value, function_name)
      VALUES (99950, 'X', 'pgtap_ammette_override_5')$$,
    '%vale per tutti e non si personalizza%',
    '5) override su un parametro senza override -> E_PARAMETER_OVERRIDE_NON_AMMESSO');

SELECT throws_like(
    $$INSERT INTO config.parameter_overrides (parameter_id, overridden_value, function_name, attivo)
      VALUES (99950, 'X', 'pgtap_ammette_override_6', false)$$,
    '%vale per tutti e non si personalizza%',
    '6) override SPENTO su un parametro senza override -> rifiutato (si riaccenderebbe senza guard)');

SELECT lives_ok(
    $$INSERT INTO config.parameter_overrides (id, parameter_id, overridden_value, function_name)
      VALUES (99960, 99951, 'X', 'pgtap_ammette_override_7')$$,
    '7) override su un parametro con override -> ammesso');

SELECT throws_like(
    $$UPDATE config.parameter_overrides SET parameter_id = 99950 WHERE id = 99960$$,
    '%vale per tutti e non si personalizza%',
    '8) UPDATE del solo parameter_id verso un parametro senza override -> rifiutato');

SELECT lives_ok(
    $$UPDATE config.parameter_overrides SET overridden_value = 'Y' WHERE id = 99960$$,
    '9) UPDATE del valore di un override ammesso -> passa');

SELECT throws_like(
    $$INSERT INTO config.parameter_overrides (parameter_id, overridden_value, function_name)
      VALUES (99952, 'CODICE_INESISTENTE_XYZ', 'pgtap_ammette_override_10')$$,
    '%vale per tutti e non si personalizza%',
    '10) registro FK-surrogata + valore rifiutato + senza override: parla il guard della famiglia');

SELECT ok(
    (SELECT g.tgname < d.tgname
       FROM pg_catalog.pg_trigger g, pg_catalog.pg_trigger d
      WHERE g.tgfoid = 'config.trgfn_parameter_overrides_guard_ammette_override'::regproc
        AND d.tgfoid = 'config.trgfn_parameter_overrides_fk_surrogate_dispatch'::regproc
        AND g.tgrelid = d.tgrelid),
    '11) il guard della famiglia ordina prima del dispatcher FK-surrogata');

-- ============================================================
-- 12-15) Il guard inverso (99960 e' un override ACCESO su 99951)
-- ============================================================
SELECT throws_like(
    $$UPDATE config.parameters SET ammette_override = false WHERE id = 99951$$,
    '%ha ancora personalizzazioni (1)%',
    '12) con -> senza override, con un override acceso -> E_PARAMETER_OVERRIDE_PRESENTI');

UPDATE config.parameter_overrides SET attivo = false WHERE id = 99960;

SELECT throws_like(
    $$UPDATE config.parameters SET ammette_override = false WHERE id = 99951$$,
    '%ha ancora personalizzazioni (1)%',
    '13) con -> senza override, con un override solo spento -> rifiutato');

DELETE FROM config.parameter_overrides WHERE id = 99960;

SELECT lives_ok(
    $$UPDATE config.parameters SET ammette_override = false WHERE id = 99951$$,
    '14) con -> senza override, senza override -> passa');

SELECT lives_ok(
    $$UPDATE config.parameters SET ammette_override = true WHERE id = 99951$$,
    '15) senza -> con override -> passa');

-- ============================================================
-- 16-18) La lista
-- ============================================================
SELECT is(
    (SELECT l.ammette_override FROM script.fn_list_parameters_for_user(NULL::integer) l
      WHERE l.code = '_TEST_SENZA_OVR_'),
    false,
    '16) la lista espone ammette_override = false sul parametro senza override');

SELECT is(
    (SELECT l.ammette_override FROM script.fn_list_parameters_for_user(NULL::integer) l
      WHERE l.code = '_TEST_CON_OVR_'),
    true,
    '17) la lista espone ammette_override = true sul parametro con override');

SELECT is(
    (SELECT l.resolved_value FROM script.fn_list_parameters_for_user(NULL::integer) l
      WHERE l.code = '_TEST_SENZA_OVR_'),
    'DEF_SENZA',
    '18) la lista: il valore risolto del parametro senza override e'' il default');

-- ============================================================
-- 19-21) fn_scrivi_dati_societari: il default PROPOSTO con la cascata della
-- sessione (D-2-bis, D-4). Si tolgono gli override esistenti sui due parametri
-- (il ROLLBACK li rimette): un override personale dell'operatore su dbdev
-- vincerebbe sull'emittente e falserebbe la prova.
-- ============================================================
DELETE FROM config.parameter_overrides o
 USING config.parameters p
 WHERE p.id = o.parameter_id
   AND p.code IN ('dati_societari_default_socio_unico', 'dati_societari_default_liquidazione');

CREATE TEMP TABLE _ds AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Parametri senza override pgTAP') AS soggetto_id,
       (SELECT default_value FROM config.parameters
         WHERE code = 'dati_societari_default_socio_unico') AS socio_default;

-- L'altro valore dell'enum: l'override deve essere diverso dal default.
ALTER TABLE _ds ADD COLUMN socio_override text;
UPDATE _ds SET socio_override = CASE WHEN socio_default = 'SU' THEN 'SM' ELSE 'SU' END;

INSERT INTO config.parameter_overrides (parameter_id, overridden_value, emittente_fiscale_id)
SELECT p.id, d.socio_override, script.fn_pgtap_emittente_operatore()
  FROM config.parameters p, _ds d
 WHERE p.code = 'dati_societari_default_socio_unico';

SELECT ok(
    EXISTS (SELECT 1 FROM anagrafiche.dati_societari ds JOIN _ds d ON d.soggetto_id = ds.soggetto_id),
    '19) setup: il soggetto PG del builder ha i dati societari');

-- Lo stato intero: si riscrivono i valori della riga, socio e liquidazione NULL.
CREATE TEMP TABLE _scrivi AS
SELECT ds.soggetto_id, ds.forma_giuridica_id, ds.id_prov_iscri_rea, ds.iscrizione_rea,
       ds.capitale_sociale, ds.destinatario_fe, ds.pec_fatturazione, ds.codice_sdi,
       ds.data_costituzione
  FROM anagrafiche.dati_societari ds JOIN _ds d ON d.soggetto_id = ds.soggetto_id;

SELECT set_config('app.current_emittente_id', script.fn_pgtap_emittente_operatore()::text, true);

SELECT anagrafiche.fn_scrivi_dati_societari(
           s.soggetto_id, s.forma_giuridica_id, s.id_prov_iscri_rea, s.iscrizione_rea,
           s.capitale_sociale, NULL, NULL, s.destinatario_fe, s.pec_fatturazione,
           s.codice_sdi, s.data_costituzione)
  FROM _scrivi s;

SELECT is(
    (SELECT ds.socio_unico::text FROM anagrafiche.dati_societari ds JOIN _ds d ON d.soggetto_id = ds.soggetto_id),
    (SELECT socio_override FROM _ds),
    '20) socio_unico NULL con l''emittente in sessione: vale l''override di quell''emittente');

SELECT set_config('app.current_emittente_id', '', true);

SELECT anagrafiche.fn_scrivi_dati_societari(
           s.soggetto_id, s.forma_giuridica_id, s.id_prov_iscri_rea, s.iscrizione_rea,
           s.capitale_sociale, NULL, NULL, s.destinatario_fe, s.pec_fatturazione,
           s.codice_sdi, s.data_costituzione)
  FROM _scrivi s;

SELECT is(
    (SELECT ds.socio_unico::text FROM anagrafiche.dati_societari ds JOIN _ds d ON d.soggetto_id = ds.soggetto_id),
    (SELECT socio_default FROM _ds),
    '21) socio_unico NULL senza emittente in sessione: vale il default del parametro');

SELECT * FROM finish();
ROLLBACK;
