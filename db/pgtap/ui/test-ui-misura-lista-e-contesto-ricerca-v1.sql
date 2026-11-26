-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la MISURA RISOLTA di una lista e il CONTESTO della ricerca libera.
--   ui.fn_misura_pagina_risolta, la cascata della misura in una sede sola;
--   ui.fn_misura_lista, la misura senza la risoluzione intera; il resolver che
--   legge la stessa cascata; ui.fn_lista_colonne_ricerca_full davanti a un id
--   utente illeggibile (dal BB script.fn_utente_di_sessione, giro 8 di
--   brief-db-revisione-ui); l'area con cui i guard di ui scrivono il giornale.
--
-- ⭐ Gira come APPLICAZIONE (il runner di default): liste, colonne, preset e
--   preferenze l'applicazione li scrive; il catalogo delle misure si legge
--   soltanto, con ui.fn_misura_pagina_default.
-- ⭐ Il mondo si COSTRUISCE: due liste (una PAGINA col preset a una misura del
--   catalogo, una COMPATTA col preset senza misura), una colonna ricercabile, un
--   operatore umano. Le misure attese sono i due default del catalogo e un numero
--   fuori catalogo calcolato dal massimo: nessun numero del seed decide
--   un'asserzione.
-- ⚠️ I casi 12-15 cambiano app.current_user_id: stanno in coda.
--
-- Elenco test (plan 16):
--   La struttura
--    1) ui.fn_misura_pagina_risolta esiste, con la firma (integer, integer, uso)
--    2) ui.fn_misura_lista esiste, con la firma di ui.fn_ordinamento_lista
--   Il BB, sui quattro rami
--    3) la preferenza nel catalogo risponde; lo standard e' il preset
--    4) la preferenza fuori catalogo non vale: risponde il preset
--    5) senza preferenza e preset: il default dell'uso COMPATTA
--    6) il preset fuori catalogo non vale: il default dell'uso PAGINA
--   La misura della lista, uguale a quella del resolver
--    7) ⭐ lista PAGINA col preset: fn_misura_lista = resolver = la misura del preset
--    8) ... e il resolver dice l'origine con l'ambito del preset (sistema)
--    9) ⭐ lista COMPATTA senza misura: il default COMPATTA, origine catalogo, nei due
--   10) ⭐ con la preferenza: la sua misura nei due, origine preferenza, standard il preset
--   11) lista inesistente: E_UI_LISTA_NON_TROVATA
--   U38: l'id utente della ricerca
--   12) ⭐ app.current_user_id non numerico: E_SCRIPT_CHIAMATA_NON_VALIDA (dal BB), non il 22P02
--   13) ... e cosi' un numero fuori dall'intero
--   14) con l'utente valido la colonna ricercabile c'e'
--   15) senza utente (GUC vuota) nessun errore, e la colonna non sensibile c'e'
--   L'area del giornale
--   16) nessuna funzione di ui passa 'ui' come area a script.fn_log_and_raise_error
-- ------------------------------------------------------------
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ============================================================
-- Fixture
-- ============================================================
-- Le misure: i due default del catalogo (righe diverse per l'UNIQUE parziale
--   sull'uso, quindi numeri diversi) e un numero che il catalogo non ha.
CREATE TEMP TABLE _m AS
SELECT ui.fn_misura_pagina_default('PAGINA')   AS d_pag,
       ui.fn_misura_pagina_default('COMPATTA') AS d_com,
       (SELECT max(misura) + 7 FROM ui.misure_pagina) AS fuori;

CREATE TEMP TABLE _l AS
WITH ins AS (
  INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert, uso_misura)
  SELECT '_pgtap.misura_lista_' || v.n || '_' || substr(md5(clock_timestamp()::text), 1, 6),
         'Lista test pgTAP misura risolta ' || v.n, 'pgtap', NULL, TRUE, '_pgtap', v.uso::ui.uso_misura_pagina
    FROM (VALUES (1, 'PAGINA'), (2, 'COMPATTA')) AS v(n, uso)
  RETURNING id, codice
)
SELECT id AS lista_id, codice AS lista_codice, row_number() OVER (ORDER BY id) AS n FROM ins;

CREATE TEMP TABLE _c AS
WITH ins AS (
  INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_dato, ordine_default,
                                ricercabile_full, user_insert)
  SELECT l.lista_id, 'c_' || l.n, 'c_' || l.n, 'campo_' || l.n, 'string', 10, TRUE, '_pgtap' FROM _l l
  RETURNING id, lista_id
)
SELECT ins.id AS colonna_id, ins.lista_id, l.n FROM ins JOIN _l l USING (lista_id);

-- Il preset della lista 1 dice la misura COMPATTA (nel catalogo, diversa dal
--   default PAGINA della lista); quello della lista 2 non la dice.
CREATE TEMP TABLE _p AS
WITH ins AS (
  INSERT INTO ui.lista_preset (lista_id, codice, descrizione, ambito, pagina_dimensione, attivo, user_insert)
  SELECT l.lista_id, 'P_MISURA', 'Preset test misura risolta', 'sistema',
         CASE l.n WHEN 1 THEN (SELECT d_com FROM _m) END, TRUE, '_pgtap'
    FROM _l l
  RETURNING id, lista_id
)
SELECT ins.id AS preset_id, ins.lista_id, l.n FROM ins JOIN _l l USING (lista_id);

INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, visibile, fissata)
SELECT p.preset_id, c.colonna_id, 1, TRUE, FALSE FROM _p p JOIN _c c ON c.n = p.n;

CREATE TEMP TABLE _u AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-misura-lista', false);

-- La misura risolta nei due lettori, e l'origine e lo standard del resolver.
-- integer: il numero della lista nella fixture (_l.n), non una colonna di tabella
CREATE FUNCTION pg_temp.misura(p_n integer)
  -- text: le quattro letture unite per il confronto, non il riflesso di una colonna
  RETURNS text LANGUAGE sql AS $f$
  SELECT concat_ws('|',
           ui.fn_misura_lista(l.lista_codice, (SELECT auth_user_id FROM _u), NULL),
           r.cfg ->> 'pagina_dimensione',
           r.cfg -> 'origine' ->> 'pagina_dimensione',
           r.cfg ->> 'pagina_dimensione_standard')
    FROM _l l
    CROSS JOIN LATERAL (SELECT ui.fn_resolve_lista_config(l.lista_codice,
                                 (SELECT auth_user_id FROM _u), NULL) AS cfg) r
   WHERE l.n = p_n
$f$;

CREATE FUNCTION pg_temp.bb(p_pref   ui.misure_pagina.misura%TYPE,
                           p_preset ui.lista_preset.pagina_dimensione%TYPE,
                           p_uso    ui.lista_definizione.uso_misura%TYPE)
  -- text: le tre uscite del BB unite per il confronto, non il riflesso di una colonna
  RETURNS text LANGUAGE sql AS $f$
  SELECT concat_ws('|', r.misura, r.standard, r.origine)
    FROM ui.fn_misura_pagina_risolta(p_pref, p_preset, p_uso) r
$f$;

-- ============================================================
-- 1-2) La struttura
-- ============================================================
SELECT has_function('ui', 'fn_misura_pagina_risolta', ARRAY['integer', 'integer', 'ui.uso_misura_pagina'],
    '1) ui.fn_misura_pagina_risolta(integer, integer, ui.uso_misura_pagina)');
SELECT has_function('ui', 'fn_misura_lista', ARRAY['character varying', 'integer', 'bigint'],
    '2) ui.fn_misura_lista(character varying, integer, bigint), la firma di ui.fn_ordinamento_lista');

-- ============================================================
-- 3-6) Il BB
-- ============================================================
SELECT is(pg_temp.bb((SELECT d_pag FROM _m), (SELECT d_com FROM _m), 'PAGINA'::ui.uso_misura_pagina),
    concat_ws('|', (SELECT d_pag FROM _m), (SELECT d_com FROM _m), 'preferenza'),
    '3) la preferenza nel catalogo risponde; lo standard e'' il preset');
SELECT is(pg_temp.bb((SELECT fuori FROM _m), (SELECT d_com FROM _m), 'PAGINA'::ui.uso_misura_pagina),
    concat_ws('|', (SELECT d_com FROM _m), (SELECT d_com FROM _m), 'preset'),
    '4) la preferenza fuori catalogo non vale: risponde il preset');
SELECT is(pg_temp.bb(NULL, NULL, 'COMPATTA'::ui.uso_misura_pagina),
    concat_ws('|', (SELECT d_com FROM _m), (SELECT d_com FROM _m), 'catalogo'),
    '5) senza preferenza e preset: il default dell''uso COMPATTA');
SELECT is(pg_temp.bb(NULL, (SELECT fuori FROM _m), 'PAGINA'::ui.uso_misura_pagina),
    concat_ws('|', (SELECT d_pag FROM _m), (SELECT d_pag FROM _m), 'catalogo'),
    '6) il preset fuori catalogo non vale: il default dell''uso PAGINA');

-- ============================================================
-- 7-11) La misura della lista
-- ============================================================
SELECT is(split_part(pg_temp.misura(1), '|', 1) || '|' || split_part(pg_temp.misura(1), '|', 2),
    (SELECT d_com || '|' || d_com FROM _m),
    '7) ⭐ lista PAGINA col preset: fn_misura_lista e il resolver rispondono la misura del preset');
SELECT is(split_part(pg_temp.misura(1), '|', 3), 'sistema',
    '8) ... e il resolver dice l''origine con l''ambito del preset');
SELECT is(pg_temp.misura(2),
    (SELECT concat_ws('|', d_com, d_com, 'catalogo', d_com) FROM _m),
    '9) ⭐ lista COMPATTA senza misura: il default COMPATTA nei due, origine catalogo');

INSERT INTO ui.lista_preferenza_utente (auth_user_id, lista_id, configurazione)
SELECT (SELECT auth_user_id FROM _u), l.lista_id,
       jsonb_build_object('pagina_dimensione', (SELECT d_pag FROM _m))
  FROM _l l WHERE l.n = 1;

SELECT is(pg_temp.misura(1),
    (SELECT concat_ws('|', d_pag, d_pag, 'preferenza', d_com) FROM _m),
    '10) ⭐ con la preferenza: la sua misura nei due, origine preferenza, standard il preset');

SELECT is(dbops.fn_pgtap_codice_errore(
    $$ SELECT ui.fn_misura_lista('_pgtap.lista_che_non_esiste', 0, NULL) $$),
    'E_UI_LISTA_NON_TROVATA',
    '11) lista inesistente: E_UI_LISTA_NON_TROVATA');

-- ============================================================
-- 12-15) U38: l'id utente della ricerca (cambiano il contesto: in coda)
-- ============================================================
SELECT set_config('app.current_user_id', 'non-un-id', true);
SELECT is(dbops.fn_pgtap_codice_errore(format(
    $$ SELECT * FROM ui.fn_lista_colonne_ricerca_full(%L) $$, (SELECT lista_codice FROM _l WHERE n = 1))),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '12) ⭐ app.current_user_id non numerico: E_SCRIPT_CHIAMATA_NON_VALIDA (dal BB), non il 22P02');

SELECT set_config('app.current_user_id', '2147483648', true);
SELECT is(dbops.fn_pgtap_codice_errore(format(
    $$ SELECT * FROM ui.fn_lista_colonne_ricerca_full(%L) $$, (SELECT lista_codice FROM _l WHERE n = 1))),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '13) ... e cosi'' un numero fuori dall''intero');

SELECT set_config('app.current_user_id', (SELECT auth_user_id FROM _u)::text, true);
SELECT is((SELECT string_agg(r.codice || '=' || r.campo_sorgente, ',')
             FROM ui.fn_lista_colonne_ricerca_full((SELECT lista_codice FROM _l WHERE n = 1)) r),
    'c_1=campo_1',
    '14) con l''utente valido la colonna ricercabile c''e''');

SELECT set_config('app.current_user_id', '', true);
SELECT is((SELECT string_agg(r.codice, ',')
             FROM ui.fn_lista_colonne_ricerca_full((SELECT lista_codice FROM _l WHERE n = 1)) r),
    'c_1',
    '15) senza utente nessun errore, e la colonna non sensibile c''e''');

-- ============================================================
-- 16) L'area del giornale
-- ============================================================
SELECT is((SELECT string_agg(p.proname::text, ', ' ORDER BY p.proname)
             FROM pg_catalog.pg_proc p
            WHERE p.pronamespace = 'ui'::regnamespace
              AND pg_get_functiondef(p.oid) ~ 'fn_log_and_raise_error\(\s*''ui'''),
    NULL,
    '16) nessuna funzione di ui passa ''ui'' come area a script.fn_log_and_raise_error');

SELECT * FROM finish();
ROLLBACK;
