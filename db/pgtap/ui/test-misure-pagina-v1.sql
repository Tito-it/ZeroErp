-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il CATALOGO DELLE MISURE DI PAGINA e le sue sedi — una sede sola per
--   le misure «righe per pagina» e i loro default.
--   Brief: brief-db-misure-pagina-catalogo (decisioni di Tid del 2026-09-29).
--   ChangeSet: 00_schema/ui/20260930-01, 80_data/20260930-02, 20_code/ui/
--   20260930-03 → -10, 90_end/20260930-11 → -13; loop ci_apply 20260205-41 e
--   provisioning (la porta, tre sedi).
--
-- ⭐ Il mondo si COSTRUISCE: un operatore umano, una lista con una colonna e
--   il suo preset di base (che dice la misura di default COMPATTA), i preset e
--   la preferenza dei casi. Le misure attese sono i due default del catalogo,
--   letti con ui.fn_misura_pagina_default: nessuna lista, nessun preset e
--   nessun numero del seed decide un'asserzione.
--
-- Elenco test (plan 19):
--   Il catalogo
--    1) un default per uso: COMPATTA e PAGINA, una riga ciascuno
--    2) fn_get_misure_pagina: misure strettamente crescenti, le stesse del catalogo,
--       e i due default quelli di ui.fn_misura_pagina_default
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
--   12) preferenza senza misura: risponde lo standard, la misura del preset di base
--   13) preferenza con un'altra misura del catalogo: risponde quella, non lo standard
--   14) il corpo non ha piu' un numero di default scritto a mano
--   La porta
--   15) all'app SELECT si', INSERT/UPDATE/DELETE no
--   16) come app, UPDATE del catalogo -> 42501
--   17) i BB sono INVOKER; l'app li esegue
--   18) i due trigger che giudicano la misura ci sono, in fase a10: sul preset
--       quello della misura, sulla preferenza quello di forma (che chiama
--       ui.fn_guard_misura_pagina; brief-db-revisione-ui, giro 2). Cercati per
--       funzione e tabella, non per nome (linee-guida-trigger)
--   Gli usi dall'enum (giro 7, Q58; in coda)
--   19) default_per_uso: una chiave per ogni valore di ui.uso_misura_pagina, col
--       default del BB; le due chiavi di prima uguali; il corpo legge l'enum
--
-- ⚠️ Gira come l'APPLICAZIONE (il backend scrive preset e preferenze). Il 16 e'
--   rosso da owner per costruzione.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(19);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _u AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-misure-pagina', false);
DO $f$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _u)); END $f$;

-- I due default del catalogo: righe diverse (un default per uso), quindi numeri diversi.
CREATE TEMP TABLE _m AS
SELECT ui.fn_misura_pagina_default('PAGINA') AS d_pag, ui.fn_misura_pagina_default('COMPATTA') AS d_com;

-- La lista d'appoggio, con una colonna e il suo preset di base: acceso, con la
--   colonna, e la misura di default COMPATTA (la lista e' PAGINA: lo standard
--   viene dal preset, non dall'uso).
CREATE TEMP TABLE _l AS
WITH ins AS (
  INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
  VALUES ('_pgtap.misure_pagina_' || substr(md5(clock_timestamp()::text), 1, 6),
          'Lista test pgTAP misure di pagina', 'pgtap', NULL, TRUE, 'pgtap')
  RETURNING id, codice
)
SELECT id AS lista_id, codice AS lista_codice FROM ins;

INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_dato, ordine_default, user_insert)
SELECT lista_id, 'c_1', 'c_1', 'campo_1', 'string', 10, 'pgtap' FROM _l;

WITH p AS (
  INSERT INTO ui.lista_preset (lista_id, codice, descrizione, ambito, pagina_dimensione, attivo, user_insert)
  SELECT lista_id, 'P_BASE', 'Preset di base test misure', 'sistema', (SELECT d_com FROM _m), TRUE, 'pgtap'
    FROM _l
  RETURNING id, lista_id
)
INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, visibile, fissata)
SELECT p.id, lc.id, 1, TRUE, FALSE FROM p JOIN ui.lista_colonna lc ON lc.lista_id = p.lista_id;

CREATE OR REPLACE FUNCTION pg_temp.preset(p_misura integer) RETURNS void
LANGUAGE sql AS $$
    -- user_insert esplicito: su ui.lista_preset e' NOT NULL senza default.
    INSERT INTO ui.lista_preset (lista_id, codice, descrizione, ambito, pagina_dimensione, attivo, user_insert)
    VALUES ((SELECT lista_id FROM _l),
            '_pgtap_misura_' || COALESCE(p_misura::text, 'null') || '_' || substring(md5(clock_timestamp()::text) from 1 for 6),
            'pgTAP misure di pagina', 'sistema', p_misura, false, 'pgtap');
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
-- uso_default e' l'enum ui.uso_misura_pagina (brief-db-revisione-ui, giro 3, Q44):
--   un enum non ha collation, si ordina sul testo.
SELECT is(
    (SELECT string_agg(format('%s=%s', m.uso_default, count), ',' ORDER BY m.uso_default::text COLLATE "C")
       FROM (SELECT uso_default, count(*) FROM ui.misure_pagina WHERE uso_default IS NOT NULL
              GROUP BY uso_default) m),
    'COMPATTA=1,PAGINA=1',
    '1) un default per uso: COMPATTA e PAGINA, una riga ciascuno');

-- ⭐ Le proprieta' della risposta, non la stessa query rifatta: l'ordine si
--   giudica coppia per coppia, l'insieme contro il catalogo in tutti e due i
--   versi, i default contro il BB che li sceglie.
SELECT is(
    -- ::text esplicito: format('%s') su un booleano stampa t/f.
    (SELECT format('%s|%s|%s|%s',
                   (SELECT bool_and(a.v::int < b.v::int)
                      FROM jsonb_array_elements_text(g -> 'misure') WITH ORDINALITY a(v, i)
                      JOIN jsonb_array_elements_text(g -> 'misure') WITH ORDINALITY b(v, i) ON b.i = a.i + 1)::text,
                   (NOT EXISTS (SELECT m.misura::text FROM ui.misure_pagina m
                                EXCEPT SELECT jsonb_array_elements_text(g -> 'misure'))
                    AND NOT EXISTS (SELECT jsonb_array_elements_text(g -> 'misure')
                                    EXCEPT SELECT m.misura::text FROM ui.misure_pagina m))::text,
                   ((g ->> 'default_compatta')::int = (SELECT d_com FROM _m))::text,
                   ((g ->> 'default_pagina')::int = (SELECT d_pag FROM _m))::text)
       FROM (SELECT ui.fn_get_misure_pagina() AS g) x),
    'true|true|true|true',
    '2) fn_get_misure_pagina: misure crescenti, le stesse del catalogo, i due default del BB');

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
-- Senza misura la preferenza segue lo STANDARD: la misura del preset di base
--   (COMPATTA), non il default dell'uso della lista (PAGINA). Il ripiego sul
--   default dell'uso lo prova test-ui-misure-catalogo-e-uso-v1.
SELECT is(
    (SELECT format('%s|%s|%s', r ->> 'pagina_dimensione', r ->> 'pagina_dimensione_standard',
                   r -> 'origine' ->> 'pagina_dimensione')
       FROM (SELECT ui.fn_resolve_lista_config((SELECT lista_codice FROM _l), (SELECT auth_user_id FROM _u), NULL) AS r) x),
    (SELECT format('%s|%s|sistema', d_com, d_com) FROM _m),
    '12) preferenza senza misura: risponde lo standard del preset di base, origine sistema');

-- ⭐ Una misura diversa dallo standard: il verde dice che vince la preferenza.
SELECT pg_temp.preferenza(jsonb_build_object('colonne', jsonb_build_array(),
                                             'pagina_dimensione', (SELECT d_pag FROM _m)));
SELECT is(pg_temp.risolta(), (SELECT d_pag FROM _m),
    '13) preferenza con un''altra misura del catalogo: il resolver risponde quella, non lo standard');

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
    (SELECT string_agg(format('%s:%s:%s', t.tgrelid::regclass, t.tgfoid::regproc,
                              substring(t.tgname from '_(a10)_')),
                       ',' ORDER BY t.tgrelid::regclass::text COLLATE "C")
       FROM pg_trigger t
      WHERE NOT t.tgisinternal
        AND (t.tgrelid, t.tgfoid) IN (('ui.lista_preset'::regclass,
                                       'ui.trgfn_ui_lista_preset_guard_pagina_dimensione'::regproc),
                                      ('ui.lista_preferenza_utente'::regclass,
                                       'ui.trgfn_preferenza_guard_forma'::regproc))),
    'ui.lista_preferenza_utente:ui.trgfn_preferenza_guard_forma:a10,ui.lista_preset:ui.trgfn_ui_lista_preset_guard_pagina_dimensione:a10',
    '18) i due trigger che giudicano la misura ci sono, in fase a10');

-- 19) Con l'enum di oggi un oggetto scritto a mano coi due usi darebbe le stesse
--   chiavi: per questo il caso guarda anche il corpo (enum_range sull'enum).
SELECT is(
    -- ::text esplicito: format('%s') su un booleano stampa t/f.
    (SELECT format('%s|%s|%s',
                   ((SELECT array_agg(k ORDER BY k) FROM jsonb_object_keys(g -> 'default_per_uso') k)
                     = (SELECT array_agg(u::text ORDER BY u::text)
                          FROM unnest(enum_range(NULL::ui.uso_misura_pagina)) u)
                   AND (SELECT bool_and((g -> 'default_per_uso' ->> u::text)::int = ui.fn_misura_pagina_default(u::text))
                          FROM unnest(enum_range(NULL::ui.uso_misura_pagina)) u))::text,
                   ((g ->> 'default_compatta') = (g -> 'default_per_uso' ->> 'COMPATTA')
                   AND (g ->> 'default_pagina') = (g -> 'default_per_uso' ->> 'PAGINA'))::text,
                   (pg_get_functiondef('ui.fn_get_misure_pagina()'::regprocedure)
                     ~ 'enum_range\(NULL::ui\.uso_misura_pagina\)')::text)
       FROM (SELECT ui.fn_get_misure_pagina() AS g) x),
    'true|true|true',
    '19) default_per_uso: un default per ogni uso dell''enum, quello del BB; le due chiavi di prima uguali');

SELECT * FROM finish();
ROLLBACK;
