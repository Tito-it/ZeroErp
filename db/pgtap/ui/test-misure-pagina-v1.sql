-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il CATALOGO DELLE MISURE DI PAGINA e le sue sedi — una sede sola per
--   le misure «righe per pagina» e i loro default.
--   Brief: brief-db-misure-pagina-catalogo (decisioni di Tid del 2026-09-29).
--   ChangeSet: 00_schema/ui/20260930-01, 80_data/20260930-02, 20_code/ui/
--   20260930-03 → -10, 90_end/20260930-11 → -13; loop ci_apply 20260205-41 e
--   provisioning (la porta, tre sedi).
--
-- ⭐ Preset e preferenza si COSTRUISCONO (un operatore umano, un preset e una
--   preferenza sulla prima lista del catalogo delle liste). Nessuna misura
--   letta dai preset esistenti.
--
-- Elenco test (plan 18):
--   Il catalogo
--    1) un default per uso: COMPATTA e PAGINA, una riga ciascuno
--    2) fn_get_misure_pagina: misure in ordine crescente, i due default fra loro
--    3) un uso fuori vocabolario -> E_UI_MISURA_PAGINA_DEFAULT_MANCANTE
--   Il preset
--    4) una misura fuori catalogo -> E_UI_MISURA_PAGINA_NON_AMMESSA (non 23503)
--    5) una misura del catalogo passa
--    6) NULL passa (e' il default)
--    7) cambiarla in una fuori catalogo -> E_UI_MISURA_PAGINA_NON_AMMESSA
--    8) la FK c'e', verso la chiave naturale del catalogo
--   La preferenza utente (jsonb)
--    9) una misura fuori catalogo -> E_UI_MISURA_PAGINA_NON_AMMESSA
--   10) un valore che numero non e' ("25") -> E_UI_MISURA_PAGINA_NON_AMMESSA
--   11) senza misura passa (e' il default)
--   Il resolver
--   12) preferenza senza misura: risponde lo standard (cascata per chiave, 2026-11-01)
--   13) preferenza con una misura del catalogo: risponde quella
--   14) il corpo non ha piu' un numero di default scritto a mano
--   La porta
--   15) all'app SELECT si', INSERT/UPDATE/DELETE no
--   16) come app, UPDATE del catalogo -> 42501
--   17) i BB sono INVOKER; l'app li esegue
--   18) i due trigger ci sono, in fase a10
--
-- ⚠️ Gira come l'APPLICAZIONE (il backend scrive preset e preferenze). Il 16 e'
--   rosso da owner per costruzione.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _u AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-misure-pagina', false);
DO $f$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _u)); END $f$;

-- Una lista qualunque del catalogo delle liste: serve solo come appoggio.
CREATE TEMP TABLE _l AS
SELECT ld.id AS lista_id, ld.codice AS lista_codice
  FROM ui.lista_definizione ld WHERE ld.attivo ORDER BY ld.id LIMIT 1;

CREATE OR REPLACE FUNCTION pg_temp.preset(p_misura integer) RETURNS void
LANGUAGE sql AS $$
    -- user_insert esplicito: su ui.lista_preset e' NOT NULL senza default.
    INSERT INTO ui.lista_preset (lista_id, codice, descrizione, ambito, is_default, pagina_dimensione, attivo, user_insert)
    VALUES ((SELECT lista_id FROM _l),
            '_pgtap_misura_' || COALESCE(p_misura::text, 'null') || '_' || substring(md5(clock_timestamp()::text) from 1 for 6),
            'pgTAP misure di pagina', 'sistema', false, p_misura, true, 'pgtap');
$$;

CREATE OR REPLACE FUNCTION pg_temp.preferenza(p_configurazione jsonb) RETURNS void
LANGUAGE sql AS $$
    INSERT INTO ui.lista_preferenza_utente (auth_user_id, lista_id, configurazione)
    VALUES ((SELECT auth_user_id FROM _u), (SELECT lista_id FROM _l), p_configurazione)
    ON CONFLICT (auth_user_id, lista_id) DO UPDATE SET configurazione = EXCLUDED.configurazione;
$$;

CREATE OR REPLACE FUNCTION pg_temp.risolta() RETURNS integer
LANGUAGE sql AS $$
    SELECT (ui.fn_resolve_lista_config((SELECT lista_codice FROM _l), (SELECT auth_user_id FROM _u), NULL)
            ->> 'pagina_dimensione')::integer;
$$;

-- ============================================================
-- 1-3 Il catalogo
-- ============================================================
SELECT is(
    (SELECT string_agg(format('%s=%s', m.uso_default, count), ',' ORDER BY m.uso_default COLLATE "C")
       FROM (SELECT uso_default, count(*) FROM ui.misure_pagina WHERE uso_default IS NOT NULL
              GROUP BY uso_default) m),
    'COMPATTA=1,PAGINA=1',
    '1) un default per uso: COMPATTA e PAGINA, una riga ciascuno');

SELECT is(
    -- ::text esplicito: format('%s') su un booleano stampa t/f.
    (SELECT format('%s|%s|%s',
                   (g -> 'misure' = (SELECT jsonb_agg(m.misura ORDER BY m.misura) FROM ui.misure_pagina m))::text,
                   ((g -> 'misure') @> jsonb_build_array(g -> 'default_compatta'))::text,
                   ((g -> 'misure') @> jsonb_build_array(g -> 'default_pagina'))::text)
       FROM (SELECT ui.fn_get_misure_pagina() AS g) x),
    'true|true|true',
    '2) fn_get_misure_pagina: le misure in ordine, e i due default fra loro');

SELECT throws_like(
    $$ SELECT ui.fn_misura_pagina_default('ALTRO') $$,
    '%Manca la misura di default delle righe per pagina per l''uso ALTRO%',
    '3) un uso fuori vocabolario: E_UI_MISURA_PAGINA_DEFAULT_MANCANTE, mai NULL');

-- ============================================================
-- 4-8 Il preset
-- ============================================================
SELECT throws_like(
    $$ SELECT pg_temp.preset(15) $$,
    '%La misura di 15 righe per pagina non e'' ammessa%',
    '4) preset con una misura fuori catalogo: il codice di catalogo, non il 23503 della FK');

SELECT lives_ok($$ SELECT pg_temp.preset(ui.fn_misura_pagina_default('COMPATTA')) $$,
    '5) preset con una misura del catalogo: passa');

SELECT lives_ok($$ SELECT pg_temp.preset(NULL) $$,
    '6) preset senza misura: passa (e'' il default)');

SELECT throws_like(
    $$ UPDATE ui.lista_preset SET pagina_dimensione = 7
        WHERE codice LIKE '\_pgtap\_misura\_%' $$,
    '%La misura di 7 righe per pagina non e'' ammessa%',
    '7) cambiare la misura di un preset in una fuori catalogo: rifiutato');

SELECT is(
    (SELECT format('%s|%s', c.confrelid::regclass::text,
                   (SELECT a.attname FROM pg_attribute a WHERE a.attrelid = c.confrelid AND a.attnum = c.confkey[1]))
       FROM pg_constraint c
      WHERE c.conrelid = 'ui.lista_preset'::regclass AND c.conname = 'fk_lista_preset_misure_pagina'),
    'ui.misure_pagina|misura',
    '8) la FK dei preset c''e'', verso la chiave naturale del catalogo');

-- ============================================================
-- 9-11 La preferenza utente
-- ============================================================
SELECT throws_like(
    $$ SELECT pg_temp.preferenza('{"colonne": [], "pagina_dimensione": 15}'::jsonb) $$,
    '%La misura di 15 righe per pagina non e'' ammessa%',
    '9) preferenza con una misura fuori catalogo: rifiutata');

SELECT throws_like(
    $$ SELECT pg_temp.preferenza('{"colonne": [], "pagina_dimensione": "25"}'::jsonb) $$,
    '%La misura di 25 righe per pagina non e'' ammessa%',
    '10) preferenza con un valore che numero non e'': rifiutata col codice di catalogo');

SELECT lives_ok($$ SELECT pg_temp.preferenza('{"colonne": []}'::jsonb) $$,
    '11) preferenza senza misura: passa (e'' il default)');

-- ============================================================
-- 12-14 Il resolver
-- ============================================================
-- ⚠️ 2026-11-01 (cascata per chiave, 20_code/ui/20261101-26): senza misura la
--   preferenza segue lo STANDARD, cioe' la misura del preset di base della lista
--   d'appoggio, o il default PAGINA se il preset non ne ha. Fino al 2026-10-31 qui
--   si asseriva il default PAGINA: dopo il cambio sarebbe stato verde solo quando
--   il preset della prima lista ha proprio quella misura. Il ripiego sul default lo
--   prova, con un mondo costruito, test-fn-resolve-lista-config-cascata-per-chiave-v1 (9).
SELECT is(
    -- ::text esplicito: format('%s') su un booleano stampa t/f.
    (SELECT format('%s|%s', ((r ->> 'pagina_dimensione') = (r ->> 'pagina_dimensione_standard'))::text,
                   (r -> 'origine' ->> 'pagina_dimensione' <> 'preferenza')::text)
       FROM (SELECT ui.fn_resolve_lista_config((SELECT lista_codice FROM _l), (SELECT auth_user_id FROM _u), NULL) AS r) x),
    'true|true',
    '12) preferenza senza misura: il resolver risponde lo standard, e non la dice una scelta');

SELECT pg_temp.preferenza(jsonb_build_object('colonne', jsonb_build_array(),
                                             'pagina_dimensione', (SELECT max(misura) FROM ui.misure_pagina)));
SELECT is(pg_temp.risolta(), (SELECT max(misura) FROM ui.misure_pagina),
    '13) preferenza con una misura del catalogo: il resolver risponde quella');

-- Commenti tolti: il corpo SPIEGA il 25 che non c'e' piu'.
SELECT ok(
    (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g') !~ 'pagina_dimensione[^;]*\m(10|25|50|100)\M'
        AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') !~ ':=\s*25\M'
       FROM pg_proc p WHERE p.oid = 'ui.fn_resolve_lista_config(character varying,integer,bigint)'::regprocedure),
    '14) il resolver non ha piu'' una misura di default scritta a mano');

-- ============================================================
-- 15-18 La porta e la forma
-- ============================================================
SELECT is(
    (SELECT format('%s|%s', has_table_privilege('zeroerp_app', 'ui.misure_pagina', 'SELECT')::text,
                   has_table_privilege('zeroerp_app', 'ui.misure_pagina', 'INSERT, UPDATE, DELETE')::text)),
    'true|false',
    '15) ui.misure_pagina: all''app SELECT si'', nessuna scrittura');

SELECT throws_ok(
    $$ UPDATE ui.misure_pagina SET misura = misura WHERE false $$,
    '42501', NULL,
    '16) come app, UPDATE del catalogo: permesso negato (rosso da owner per costruzione)');

SELECT is(
    (SELECT string_agg(format('%s=%s%s', p.proname, CASE WHEN p.prosecdef THEN 'D' ELSE 'I' END,
                              CASE WHEN has_function_privilege('zeroerp_app', p.oid, 'EXECUTE') THEN '' ELSE '!' END),
                       ',' ORDER BY p.proname COLLATE "C")
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'ui'
        AND p.proname IN ('fn_misura_pagina_ammessa', 'fn_misura_pagina_default',
                          'fn_get_misure_pagina', 'fn_guard_misura_pagina')),
    'fn_get_misure_pagina=I,fn_guard_misura_pagina=I,fn_misura_pagina_ammessa=I,fn_misura_pagina_default=I',
    '17) i quattro BB sono INVOKER, e l''app li esegue');

SELECT is(
    (SELECT string_agg(t.tgname, ',' ORDER BY t.tgname COLLATE "C")
       FROM pg_trigger t
      WHERE t.tgname IN ('trg_ui_lista_preset_a10_guard_pagina_ins_upd',
                         'trg_ui_lista_preferenza_utente_a10_guard_pagina_ins_upd')),
    'trg_ui_lista_preferenza_utente_a10_guard_pagina_ins_upd,trg_ui_lista_preset_a10_guard_pagina_ins_upd',
    '18) i due trigger dei guard ci sono, in fase a10');

SELECT * FROM finish();
ROLLBACK;
