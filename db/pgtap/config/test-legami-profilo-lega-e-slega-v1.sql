-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Legare un profilo a un reparto, e slegare un profilo da un reparto o da
-- un'identita' (2026-10-19). R-BE-7 del BE, decisioni D-16b e D-16c di Tid,
-- brief-db-processi-accensione-per-ambiente §6.10 (la richiesta) e §6.16 (la
-- risposta). ChangeSet 20261019-33, -34, -35.
--
-- Elenco test (plan 11):
--  -- il reparto (fn_lega_profilo_reparto, fn_slega_profilo_reparto) --
--  1)   legare: il binding nasce, sul reparto e su quel profilo
--  2)   legare di nuovo lo stesso profilo: lo stesso binding (idempotente)
--  3)   un altro profilo su un reparto gia' legato: lo rifiuta il vincolo
--  4)   slegare un profilo che il reparto non ha: 0, il binding resta
--  5)   slegare il suo profilo: 1, il binding non c'e' piu'
--  6)   slegare di nuovo: 0, non e' un errore
--  -- l'identita' (fn_slega_profilo_identita) --
--  7)   slegare un profilo che l'identita' non ha: 0, il binding resta
--  8)   slegare il suo profilo: 1
--  9)   slegare di nuovo: 0
--  -- gli argomenti --
--  10)  slegare senza profilo: E_SCRIPT_CHIAMATA_NON_VALIDA
--  11)  legare un reparto senza reparto: E_SCRIPT_CHIAMATA_NON_VALIDA
--
-- ⚠️ Non provato qui: l'ultimo super admin. Lo protegge il trigger della
--   tabella (trgfn_profili_accesso_bindings_guard_ultimo_super_admin), che
--   scatta anche sul DELETE della madre come su ogni altro scrittore: ha i suoi
--   test, e costruire «l'unico super admin attivo» qui vorrebbe dire spegnere
--   quelli che il database ha.
--
-- Scopo:
--  - provare le tre madri COSTRUENDO reparto, profili e identita'.
-- ------------------------------------------------------------

BEGIN;

-- Il mondo prima del contesto: un operatore senza super admin.
CREATE TEMP TABLE _op ON COMMIT DROP AS
SELECT o.identita_id
  FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP legami di profilo', false) o;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- Fixture: un reparto, due profili REPARTO, due profili AD_HOC
-- ============================================================
CREATE TEMP TABLE _uo (uo_id integer) ON COMMIT DROP;
WITH u AS (
    INSERT INTO config.unita_organizzative (codice, codice_interno, descrizione)
    SELECT 'PGTLEG' || k, 'PGTAP_LEGAMI_' || k, 'Reparto pgTAP legami di profilo'
      FROM (SELECT upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 12)) AS k) x
    RETURNING id
)
INSERT INTO _uo SELECT u.id FROM u;

CREATE TEMP TABLE _f ON COMMIT DROP AS
SELECT (SELECT uo_id FROM _uo) AS uo_id,
       (SELECT identita_id FROM _op) AS identita_id,
       config.fn_scrivi_profilo_accesso('REPARTO'::config.tipo_profilo_accesso,
           'PGTAP_REP_A_' || k, 'Profilo pgTAP reparto A', '[]'::jsonb, '[]'::jsonb, '{}'::jsonb) AS rep_a,
       config.fn_scrivi_profilo_accesso('REPARTO'::config.tipo_profilo_accesso,
           'PGTAP_REP_B_' || k, 'Profilo pgTAP reparto B', '[]'::jsonb, '[]'::jsonb, '{}'::jsonb) AS rep_b,
       config.fn_scrivi_profilo_accesso('AD_HOC'::config.tipo_profilo_accesso,
           'PGTAP_ADH_X_' || k, 'Profilo pgTAP ad hoc X', '[]'::jsonb, '[]'::jsonb, '{}'::jsonb) AS adh_x,
       config.fn_scrivi_profilo_accesso('AD_HOC'::config.tipo_profilo_accesso,
           'PGTAP_ADH_Y_' || k, 'Profilo pgTAP ad hoc Y', '[]'::jsonb, '[]'::jsonb, '{}'::jsonb) AS adh_y
  FROM (SELECT replace(gen_random_uuid()::text, '-', '') AS k) x;

-- ============================================================
-- 1-6) Il reparto
-- ============================================================
CREATE TEMP TABLE _l1 ON COMMIT DROP AS
SELECT config.fn_lega_profilo_reparto(rep_a, uo_id) AS binding_id FROM _f;

SELECT is(
    (SELECT pab.unita_organizzativa_id::text || '/' || (pab.profilo_accesso_id = _f.rep_a)::text
       FROM config.profili_accesso_bindings pab, _l1, _f
      WHERE pab.id = _l1.binding_id),
    (SELECT uo_id::text || '/true' FROM _f),
    '1) legare: il binding nasce, sul reparto e su quel profilo');

SELECT is(
    (SELECT config.fn_lega_profilo_reparto(rep_a, uo_id) FROM _f),
    (SELECT binding_id FROM _l1),
    '2) legare di nuovo lo stesso profilo: lo stesso binding');

SELECT throws_ok(
    (SELECT format('SELECT config.fn_lega_profilo_reparto(%s, %s)', rep_b, uo_id) FROM _f),
    '23505', NULL,
    '3) un altro profilo su un reparto gia'' legato: lo rifiuta uq_profili_accesso_bindings_uo');

-- ⚠️ La madre in un'istruzione sua: un conteggio nella stessa istruzione
--   vedrebbe la fotografia di prima del DELETE.
CREATE TEMP TABLE _s4 ON COMMIT DROP AS
SELECT config.fn_slega_profilo_reparto(rep_b, uo_id) AS tolti FROM _f;
SELECT is(
    (SELECT tolti::text FROM _s4) || '/'
        || (SELECT count(*) FROM config.profili_accesso_bindings pab, _l1 WHERE pab.id = _l1.binding_id)::text,
    '0/1',
    '4) slegare un profilo che il reparto non ha: 0, il binding resta');

CREATE TEMP TABLE _s5 ON COMMIT DROP AS
SELECT config.fn_slega_profilo_reparto(rep_a, uo_id) AS tolti FROM _f;
SELECT is(
    (SELECT tolti::text FROM _s5) || '/'
        || (SELECT count(*) FROM config.profili_accesso_bindings pab, _f WHERE pab.unita_organizzativa_id = _f.uo_id)::text,
    '1/0',
    '5) slegare il suo profilo: 1, il binding non c''e'' piu''');

SELECT is(
    (SELECT config.fn_slega_profilo_reparto(rep_a, uo_id) FROM _f),
    0,
    '6) slegare di nuovo: 0, non e'' un errore');

-- ============================================================
-- 7-9) L'identita'
-- ============================================================
CREATE TEMP TABLE _l2 ON COMMIT DROP AS
SELECT config.fn_lega_profilo_identita(adh_x, identita_id) AS binding_id FROM _f;

CREATE TEMP TABLE _s7 ON COMMIT DROP AS
SELECT config.fn_slega_profilo_identita(adh_y, identita_id) AS tolti FROM _f;
SELECT is(
    (SELECT tolti::text FROM _s7) || '/'
        || (SELECT count(*) FROM config.profili_accesso_bindings pab, _l2 WHERE pab.id = _l2.binding_id)::text,
    '0/1',
    '7) slegare un profilo che l''identita'' non ha: 0, il binding resta');

SELECT is(
    (SELECT config.fn_slega_profilo_identita(adh_x, identita_id) FROM _f),
    1,
    '8) slegare il suo profilo: 1');

SELECT is(
    (SELECT config.fn_slega_profilo_identita(adh_x, identita_id) FROM _f),
    0,
    '9) slegare di nuovo: 0');

-- ============================================================
-- 10-11) Gli argomenti
-- ============================================================
SELECT throws_like(
    (SELECT format('SELECT config.fn_slega_profilo_identita(NULL, %s)', identita_id) FROM _f),
    '%mancanti%',
    '10) slegare senza profilo: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT throws_like(
    (SELECT format('SELECT config.fn_lega_profilo_reparto(%s, NULL)', rep_a) FROM _f),
    '%mancanti%',
    '11) legare un reparto senza reparto: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT * FROM finish();
ROLLBACK;
