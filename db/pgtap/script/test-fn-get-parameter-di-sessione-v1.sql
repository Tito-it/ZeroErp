-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Un parametro letto col contesto della sessione, e lo stato proposto che lo
-- usa (2026-10-18). R-BE-13 del BE, decisioni D-13a e D-13b di Tid,
-- brief-db-processi-accensione-per-ambiente §6.12 (la richiesta) e §6.13 (la risposta). ChangeSet 20261019-05, -06.
--
-- Il difetto: script.fn_stato_proposto_id passava NULL a utente, gruppi ed
-- emittente, e i loro override di STATO_PROPOSTO_ISO2 non scattavano mai.
--
-- Elenco test (plan 15):
--  1)   la firma del BB
--  2)   STABLE e SECURITY INVOKER
--  3)   senza override: il default (IT)
--  -- utente (app.current_user_id) --
--  4)   override dell'utente a DE: il BB lo legge
--  5)   ... e fn_stato_proposto_id propone la Germania (il difetto R-BE-13)
--  6)   ... e il normalize di un indirizzo senza stato scrive la Germania:
--       il percorso che il BE ha visto
--  7)   un altro utente: il default
--  8)   una sessione senza utente: il default
--  -- gruppo (django.auth_user_groups) --
--  9)   override del gruppo dell'utente a FR
--  10)  l'utente batte il gruppo: DE
--  -- emittente (app.current_emittente_id) --
--  11)  override dell'emittente attivo a ES
--  12)  senza emittente attivo: il default
--  -- funzione (p_chi): era gia' vivo, resta --
--  13)  override per chi chiede a FR
--  14)  ... chi chiede altro: il default
--  -- per ultimo --
--  15)  un parametro non dichiarato: l'errore di fn_get_parameter_full
--
-- ⚠️ Non provato qui: il livello gruppo SPENTO quando la tabella di Django
--   non c'e' o il ruolo non la legge (zeroerp_job). L'app la legge sempre
--   (provisioning, linee-guida-sql §11.9) e non puo' cambiare ruolo: il ramo
--   e' provato prima dell'apply, da owner con SET ROLE zeroerp_job (brief
--   §6.13, «Prova»).
--
-- Scopo:
--  - provare che ogni livello del contesto arriva alla cascata COSTRUENDO gli
--    override (regola zero: il test non legge quelli di oggi, li cancella).
-- ------------------------------------------------------------

BEGIN;

-- Il mondo prima del contesto: l'emittente con il suo operatore.
CREATE TEMP TABLE _e ON COMMIT DROP AS
SELECT ceo.emittente_fiscale_id, ceo.auth_user_id
  FROM dbops.fn_pgtap_crea_emittente_operatore() ceo;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e)); END $ctx$;
-- La fixture crea il soggetto (padre) e i suoi indirizzi nello stesso
-- builder, che apre e richiude da se' la finestra dei differiti.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- Fixture
-- ============================================================
-- Nessun emittente attivo finche' il test non lo dice.
SELECT set_config('app.current_emittente_id', '', true);

CREATE TEMP TABLE _f ON COMMIT DROP AS
SELECT e.emittente_fiscale_id,
       e.auth_user_id,
       p.id AS parametro_id,
       script.fn_stato_id_da_iso2('IT') AS it_id,
       script.fn_stato_id_da_iso2('DE') AS de_id,
       dbops.fn_pgtap_crea_soggetto_pg('pgTAP stato proposto di sessione', 3, script.fn_stato_id_da_iso2('IT')) AS soggetto_id
  FROM _e e, config.parameters p
 WHERE p.code = 'STATO_PROPOSTO_ISO2';

-- La riga del soggetto (SEDELEG, obbligatoria per SC).
ALTER TABLE _f ADD COLUMN riga_id bigint, ADD COLUMN gruppo_id integer;
UPDATE _f SET riga_id = s.id
  FROM anagrafiche.indirizzi_soggetti s
 WHERE s.soggetto_id = _f.soggetto_id;

-- Un gruppo di Django per l'operatore.
WITH g AS (
    INSERT INTO django.auth_group (name)
    VALUES ('pgTAP stato proposto ' || gen_random_uuid()::text)
    RETURNING id
)
UPDATE _f SET gruppo_id = g.id FROM g;
INSERT INTO django.auth_user_groups (user_id, group_id)
SELECT auth_user_id, gruppo_id FROM _f;

-- Gli override di oggi non decidono il test: si tolgono.
DELETE FROM config.parameter_overrides
 WHERE parameter_id = (SELECT parametro_id FROM _f);

-- ============================================================
-- 1-3) Forma e default
-- ============================================================
SELECT has_function('script', 'fn_get_parameter_di_sessione',
    ARRAY['character varying', 'text'],
    '1) script.fn_get_parameter_di_sessione(code, chi)');

SELECT is(
    (SELECT p.provolatile::text || '/' || p.prosecdef::text
       FROM pg_proc p
      WHERE p.oid = 'script.fn_get_parameter_di_sessione(character varying, text)'::regprocedure),
    's/false',
    '2) STABLE e SECURITY INVOKER: legge il contesto di chi chiama');

SELECT is(script.fn_get_parameter_di_sessione('STATO_PROPOSTO_ISO2', 'pgTAP'), 'IT',
    '3) senza override: il default');

-- ============================================================
-- 4-8) Utente
-- ============================================================
INSERT INTO config.parameter_overrides (parameter_id, overridden_value, django_user_id)
SELECT parametro_id, 'DE', auth_user_id FROM _f;

SELECT is(script.fn_get_parameter_di_sessione('STATO_PROPOSTO_ISO2', 'pgTAP'), 'DE',
    '4) override dell''utente: il BB lo legge da app.current_user_id');

SELECT is(script.fn_stato_proposto_id('pgTAP'), (SELECT de_id FROM _f),
    '5) lo stato proposto all''utente e'' la Germania (R-BE-13)');

UPDATE anagrafiche.indirizzi_soggetti
   SET stato_id = NULL, comune_id = NULL, codice_postale_id = NULL,
       sublocality = NULL, locality = 'Berlino'
 WHERE id = (SELECT riga_id FROM _f);
SELECT is(
    (SELECT s.stato_id FROM anagrafiche.indirizzi_soggetti s, _f WHERE s.id = _f.riga_id),
    (SELECT de_id FROM _f),
    '6) indirizzo senza stato: il normalize scrive lo stato proposto all''utente');

SELECT set_config('app.current_user_id', (SELECT (auth_user_id + 1)::text FROM _f), true);
SELECT is(script.fn_get_parameter_di_sessione('STATO_PROPOSTO_ISO2', 'pgTAP'), 'IT',
    '7) un altro utente: il default');

SELECT set_config('app.current_user_id', '', true);
SELECT is(script.fn_get_parameter_di_sessione('STATO_PROPOSTO_ISO2', 'pgTAP'), 'IT',
    '8) una sessione senza utente: il default');

SELECT set_config('app.current_user_id', (SELECT auth_user_id::text FROM _f), true);

-- ============================================================
-- 9-10) Gruppo
-- ============================================================
DELETE FROM config.parameter_overrides
 WHERE parameter_id = (SELECT parametro_id FROM _f);
INSERT INTO config.parameter_overrides (parameter_id, overridden_value, django_group_id)
SELECT parametro_id, 'FR', gruppo_id FROM _f;

SELECT is(script.fn_get_parameter_di_sessione('STATO_PROPOSTO_ISO2', 'pgTAP'), 'FR',
    '9) override del gruppo dell''utente: letto da django.auth_user_groups');

INSERT INTO config.parameter_overrides (parameter_id, overridden_value, django_user_id)
SELECT parametro_id, 'DE', auth_user_id FROM _f;

SELECT is(script.fn_get_parameter_di_sessione('STATO_PROPOSTO_ISO2', 'pgTAP'), 'DE',
    '10) l''utente batte il gruppo');

-- ============================================================
-- 11-12) Emittente
-- ============================================================
DELETE FROM config.parameter_overrides
 WHERE parameter_id = (SELECT parametro_id FROM _f);
INSERT INTO config.parameter_overrides (parameter_id, overridden_value, emittente_fiscale_id)
SELECT parametro_id, 'ES', emittente_fiscale_id FROM _f;

SELECT set_config('app.current_emittente_id', (SELECT emittente_fiscale_id::text FROM _f), true);
SELECT is(script.fn_get_parameter_di_sessione('STATO_PROPOSTO_ISO2', 'pgTAP'), 'ES',
    '11) override dell''emittente attivo: letto da app.current_emittente_id');

SELECT set_config('app.current_emittente_id', '', true);
SELECT is(script.fn_get_parameter_di_sessione('STATO_PROPOSTO_ISO2', 'pgTAP'), 'IT',
    '12) senza emittente attivo: il default');

-- ============================================================
-- 13-14) Funzione: p_chi
-- ============================================================
DELETE FROM config.parameter_overrides
 WHERE parameter_id = (SELECT parametro_id FROM _f);
INSERT INTO config.parameter_overrides (parameter_id, overridden_value, function_name)
SELECT parametro_id, 'FR', 'pgTAP-chi' FROM _f;

SELECT is(script.fn_get_parameter_di_sessione('STATO_PROPOSTO_ISO2', 'pgTAP-chi'), 'FR',
    '13) override per chi chiede: p_chi resta il livello «function»');

SELECT is(script.fn_get_parameter_di_sessione('STATO_PROPOSTO_ISO2', 'pgTAP'), 'IT',
    '14) chi chiede altro: il default');

-- ============================================================
-- 15) Per ultimo: un parametro che non c'e'
-- ============================================================
-- ⚠️ Solo il nome del parametro: fn_get_parameter_full passa i due
--   segnaposto invertiti («Parametro: config.parameters non trovato nella
--   tabella: <codice>», brief §6.13). Un pattern sull'ordine pinnerebbe il
--   difetto.
SELECT throws_like(
    $$SELECT script.fn_get_parameter_di_sessione('PGTAP_PARAMETRO_CHE_NON_ESISTE', 'pgTAP')$$,
    '%PGTAP_PARAMETRO_CHE_NON_ESISTE%',
    '15) un parametro non dichiarato: E_ERRORE_PARAMETRI_TABELLA, da fn_get_parameter_full');

SELECT * FROM finish();
ROLLBACK;
