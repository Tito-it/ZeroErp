-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: il motivo di un override utente e' obbligatorio, sulle tre tabelle e
--   anche per la voce che toglie un permesso; si scrive ripulito; togliere una
--   voce non lo chiede.
-- Riferimento: brief-db-motivo-override-obbligatorio §6 (D-1 a, D-2 b, D-4 no di
--   Tid, 2026-11-27); changeSet 20_code/config/20261126-80 (la primitiva
--   config.fn_applica_imposta_override), codice E_OVERRIDE_MOTIVO_OBBLIGATORIO.
--
-- ⭐ Il caso si COSTRUISCE: un operatore umano dal builder, due aree, un'azione
--   e un oggetto non riservato dai cataloghi; gli override li scrive il verbo
--   vero, da un SUPER_ADMIN di fixture.
--
-- Elenco test (plan 16):
--   il motivo che manca, sulle aree
--    1) motivo assente: E_OVERRIDE_MOTIVO_OBBLIGATORIO
--    2) motivo null
--    3) motivo vuoto
--    4) motivo di soli spazi
--    5) motivo non di testo (un numero)
--   le altre due tabelle, e la voce che toglie
--    6) azioni, motivo assente
--    7) azioni, la voce che toglie (abilitata false) senza motivo
--    8) oggetti, la voce che toglie (BLOCCATO) senza motivo
--    9) il campo motivo esce sul canale COLUMN
--   l'elenco si giudica tutto prima di scrivere
--   10) prima voce sull'area inesistente (la FK), seconda senza motivo: vince il motivo
--   11) … e l'elenco di prima resta, col suo motivo
--   12) chiave estranea e motivo assente insieme: E_CAMPO_NON_AMMESSO, giudicata prima
--   la scrittura
--   13) il motivo si scrive ripulito dagli spazi
--   14) togliere una voce (lasciarla fuori dall'elenco) non chiede motivo
--   15) l'elenco vuoto toglie tutto, senza motivo
--   16) un override che toglie, col motivo, si scrive
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(16);

CREATE TEMP TABLE _u AS
SELECT (SELECT o.auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('Motivo override pgTAP', false) o) AS au;

CREATE TEMP TABLE _cat AS
SELECT (SELECT af.id FROM config.aree_funzionali af ORDER BY af.id LIMIT 1)          AS area_1,
       (SELECT af.id FROM config.aree_funzionali af ORDER BY af.id OFFSET 1 LIMIT 1) AS area_2,
       (SELECT ap.id FROM config.azioni_processo ap ORDER BY ap.id LIMIT 1)          AS azione,
       (SELECT jsonb_build_object('app_label', a.app_label, 'model_name', a.model_name)
          FROM config.area_model_overrides a WHERE NOT a.riservato
         ORDER BY a.app_label, a.model_name LIMIT 1)                                 AS oggetto,
       (SELECT max(af.id) + 1000 FROM config.aree_funzionali af)                     AS area_assente;

-- Gli override li scrive il verbo del SUPER_ADMIN.
CREATE TEMP TABLE _sa AS SELECT dbops.fn_pgtap_entra_come_super_admin('motivo-override') AS prima;

-- Il verbo delle aree su un elenco: il codice del rifiuto, o NULL.
CREATE OR REPLACE FUNCTION pg_temp.aree(p_elenco jsonb) RETURNS text
LANGUAGE sql AS $$
    SELECT dbops.fn_pgtap_codice_errore(format(
        'SELECT config.fn_imposta_override_aree(%s, %L::jsonb)', (SELECT au FROM _u), p_elenco));
$$;

-- Una voce d'area sulla prima area, coi campi dati.
CREATE OR REPLACE FUNCTION pg_temp.voce(p_campi jsonb) RETURNS jsonb
LANGUAGE sql AS $$
    SELECT jsonb_build_object('area_id', (SELECT area_1 FROM _cat), 'livello', 'LETTURA') || p_campi;
$$;

-- Codice e campo del rifiuto (i canali CONSTRAINT e COLUMN), come li legge il backend.
CREATE OR REPLACE FUNCTION pg_temp.codice_e_campo(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_codice text; v_campo text;  -- valori della diagnostica, nessuna colonna
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME, v_campo = COLUMN_NAME;
    RETURN v_codice || ' / ' || v_campo;
END $$;

-- ============================================================
-- 1-5 Il motivo che manca, sulle aree
-- ============================================================
SELECT is(pg_temp.aree(jsonb_build_array(pg_temp.voce('{}'))),
          'E_OVERRIDE_MOTIVO_OBBLIGATORIO', '1) motivo assente: E_OVERRIDE_MOTIVO_OBBLIGATORIO');

SELECT is(pg_temp.aree(jsonb_build_array(pg_temp.voce('{"motivo": null}'))),
          'E_OVERRIDE_MOTIVO_OBBLIGATORIO', '2) motivo null: E_OVERRIDE_MOTIVO_OBBLIGATORIO');

SELECT is(pg_temp.aree(jsonb_build_array(pg_temp.voce('{"motivo": ""}'))),
          'E_OVERRIDE_MOTIVO_OBBLIGATORIO', '3) motivo vuoto: E_OVERRIDE_MOTIVO_OBBLIGATORIO');

SELECT is(pg_temp.aree(jsonb_build_array(pg_temp.voce('{"motivo": "   "}'))),
          'E_OVERRIDE_MOTIVO_OBBLIGATORIO', '4) motivo di soli spazi: E_OVERRIDE_MOTIVO_OBBLIGATORIO');

SELECT is(pg_temp.aree(jsonb_build_array(pg_temp.voce('{"motivo": 123}'))),
          'E_OVERRIDE_MOTIVO_OBBLIGATORIO', '5) motivo non di testo: E_OVERRIDE_MOTIVO_OBBLIGATORIO');

-- ============================================================
-- 6-9 Le altre due tabelle, la voce che toglie, il canale
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT config.fn_imposta_override_azioni(%s, %L::jsonb)', (SELECT au FROM _u),
        jsonb_build_array(jsonb_build_object('azione_id', (SELECT azione FROM _cat), 'abilitata', true)))),
    'E_OVERRIDE_MOTIVO_OBBLIGATORIO',
    '6) azioni, motivo assente: E_OVERRIDE_MOTIVO_OBBLIGATORIO');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT config.fn_imposta_override_azioni(%s, %L::jsonb)', (SELECT au FROM _u),
        jsonb_build_array(jsonb_build_object('azione_id', (SELECT azione FROM _cat), 'abilitata', false)))),
    'E_OVERRIDE_MOTIVO_OBBLIGATORIO',
    '7) azioni, la voce che toglie (abilitata false) senza motivo: rifiutata');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT config.fn_imposta_override_oggetti(%s, %L::jsonb)', (SELECT au FROM _u),
        jsonb_build_array((SELECT oggetto FROM _cat) || '{"livello": "BLOCCATO"}'::jsonb))),
    'E_OVERRIDE_MOTIVO_OBBLIGATORIO',
    '8) oggetti, la voce che toglie (BLOCCATO) senza motivo: rifiutata');

SELECT is(
    pg_temp.codice_e_campo(format(
        'SELECT config.fn_imposta_override_aree(%s, %L::jsonb)', (SELECT au FROM _u),
        jsonb_build_array(pg_temp.voce('{}')))),
    'E_OVERRIDE_MOTIVO_OBBLIGATORIO / motivo',
    '9) il campo motivo esce sul canale COLUMN');

-- ============================================================
-- 10-12 L'elenco si giudica tutto prima di scrivere
-- ============================================================
-- Lo stato di partenza: una voce col suo motivo. Ogni scrittura in
-- un'istruzione sua: la lettura nella stessa non la vedrebbe.
SELECT config.fn_imposta_override_aree(
           (SELECT au FROM _u), jsonb_build_array(pg_temp.voce('{"motivo": "Prima"}')));

SELECT is(
    pg_temp.aree(jsonb_build_array(
        jsonb_build_object('area_id', (SELECT area_assente FROM _cat), 'livello', 'LETTURA', 'motivo', 'pgTAP'),
        jsonb_build_object('area_id', (SELECT area_2 FROM _cat), 'livello', 'TUTTO'))),
    'E_OVERRIDE_MOTIVO_OBBLIGATORIO',
    '10) prima voce sull''area inesistente, seconda senza motivo: il motivo si giudica prima di scrivere');

SELECT is(
    (SELECT string_agg(uoa.area_id::text || ':' || uoa.motivo, ',' ORDER BY uoa.area_id)
       FROM config.user_override_aree uoa WHERE uoa.auth_user_id = (SELECT au FROM _u)),
    (SELECT area_1 FROM _cat)::text || ':Prima',
    '11) … e l''elenco di prima resta, col suo motivo');

SELECT is(pg_temp.aree(jsonb_build_array(pg_temp.voce('{"meta": {}}'))),
          'E_CAMPO_NON_AMMESSO',
          '12) chiave estranea e motivo assente: E_CAMPO_NON_AMMESSO, giudicata prima del motivo');

-- ============================================================
-- 13-16 La scrittura
-- ============================================================
SELECT config.fn_imposta_override_aree(
           (SELECT au FROM _u), jsonb_build_array(
               pg_temp.voce('{"motivo": "  Delega temporanea  "}'),
               jsonb_build_object('area_id', (SELECT area_2 FROM _cat), 'livello', 'TUTTO', 'motivo', 'Seconda')));

SELECT is(
    (SELECT uoa.motivo FROM config.user_override_aree uoa
      WHERE uoa.auth_user_id = (SELECT au FROM _u) AND uoa.area_id = (SELECT area_1 FROM _cat)),
    'Delega temporanea',
    '13) il motivo si scrive ripulito dagli spazi');

-- Si toglie la seconda voce: l'elenco porta solo la prima, col suo motivo.
SELECT config.fn_imposta_override_aree(
           (SELECT au FROM _u), jsonb_build_array(pg_temp.voce('{"motivo": "Delega temporanea"}')));

SELECT is(
    (SELECT string_agg(uoa.area_id::text, ',' ORDER BY uoa.area_id)
       FROM config.user_override_aree uoa WHERE uoa.auth_user_id = (SELECT au FROM _u)),
    (SELECT area_1 FROM _cat)::text,
    '14) togliere una voce (lasciarla fuori dall''elenco) non chiede motivo');

SELECT config.fn_imposta_override_aree((SELECT au FROM _u), '[]'::jsonb);

SELECT is(
    (SELECT count(*)::int FROM config.user_override_aree uoa WHERE uoa.auth_user_id = (SELECT au FROM _u)),
    0,
    '15) l''elenco vuoto toglie tutto, senza motivo');

SELECT config.fn_imposta_override_oggetti(
           (SELECT au FROM _u),
           jsonb_build_array((SELECT oggetto FROM _cat) || '{"livello": "BLOCCATO", "motivo": "Oggetto riservato al responsabile"}'::jsonb));

SELECT is(
    (SELECT uoo.livello::text || ':' || uoo.motivo FROM config.user_override_oggetti uoo
      WHERE uoo.auth_user_id = (SELECT au FROM _u)),
    'BLOCCATO:Oggetto riservato al responsabile',
    '16) un override che toglie, col motivo, si scrive');

SELECT dbops.fn_pgtap_rimetti_contesto((SELECT prima FROM _sa));

SELECT * FROM finish();

ROLLBACK;
