-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la cascata PER CHIAVE di ui.fn_resolve_lista_config e la data del
--   contenuto dei preset di lista.
--   Richiesta BE/FE «la preferenza di lista per chiave» (decisione di Tid del
--   2026-11-01). ChangeSet: 20_code/ui/20261101-20 → -23, -26.
--
-- ⭐ Il mondo si COSTRUISCE: una lista, tre colonne, un preset di sistema con
--   ordinamento, filtri e una misura diversa dal default, un utente. Nessun
--   dato esistente decide un'asserzione. Le misure si prendono dal catalogo
--   ui.misure_pagina per RUOLO (default, la piu' piccola diversa, la piu'
--   grande diversa), mai scritte a mano.
--
-- Elenco test (plan 19):
--   La cascata
--    1) preferenza di sole colonne: ordinamento, filtri e misura dal preset
--    2) ... e origine lo dice (colonne preferenza, il resto sistema)
--    3) ... e la misura standard e' quella del preset
--    4) preferenza di sola misura: le colonne vengono dal preset
--    5) ... la misura e' quella della preferenza, origine lo dice
--    6) ... e la misura standard resta quella del preset
--    7) una chiave null nella preferenza vale come assente
--    8) senza preferenza: tutto dal preset, misura = standard
--    9) preset senza misura: standard = default PAGINA, origine catalogo
--   10) lista senza preset: colonne, ordinamento, filtri e misura dal catalogo
--   La data del contenuto del preset
--   11) riscrivere la riga del preset uguale: data_update non si sposta
--   12) cambiare ordinamento_default: data_update = now()
--   13) riscrivere una colonna del preset uguale: data_update non si sposta
--   14) cambiare una colonna del preset: data_update = now()
--   15) aggiungere una colonna al preset: data_update = now()
--   16) togliere una colonna dal preset: data_update = now()
--   Il flag
--   17) snapshot allineato: preset_aggiornato = false
--   18) il preset cambia davvero: data_update spostato e flag acceso
--   I trigger
--   19) i due trigger delle liste ci sono, sulle due funzioni condivise
-- ------------------------------------------------------------
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli
--   (il COMMIT non arriva mai). Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come l'applicazione (il backend scrive
-- preset e preferenze). Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(19);

-- ============================================================
-- Fixture
-- ============================================================
-- Le misure, dal catalogo per ruolo: PAG = default PAGINA, PRESET = la piu'
-- piccola diversa da PAG, PREF = la piu' grande diversa da PAG e da PRESET.
CREATE TEMP TABLE _m AS
SELECT ui.fn_misura_pagina_default('PAGINA') AS pag,
       (SELECT min(misura) FROM ui.misure_pagina
         WHERE misura <> ui.fn_misura_pagina_default('PAGINA')) AS preset,
       (SELECT max(misura) FROM ui.misure_pagina
         WHERE misura <> ui.fn_misura_pagina_default('PAGINA')
           AND misura <> (SELECT min(misura) FROM ui.misure_pagina
                           WHERE misura <> ui.fn_misura_pagina_default('PAGINA'))) AS pref;

CREATE TEMP TABLE _l AS
WITH ins AS (
  INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
  VALUES ('_pgtap.cascata_' || substr(md5(clock_timestamp()::text), 1, 6),
          'Lista test pgTAP cascata per chiave', 'pgtap', NULL, TRUE, '_pgtap')
  RETURNING id, codice
)
SELECT id AS lista_id, codice AS lista_codice FROM ins;

-- Seconda lista, senza preset: il ripiego sul catalogo.
CREATE TEMP TABLE _l2 AS
WITH ins AS (
  INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
  VALUES ('_pgtap.cascata_nopreset_' || substr(md5(clock_timestamp()::text), 1, 6),
          'Lista test pgTAP cascata senza preset', 'pgtap', NULL, TRUE, '_pgtap')
  RETURNING id, codice
)
SELECT id AS lista_id, codice AS lista_codice FROM ins;

CREATE TEMP TABLE _c AS
WITH ins AS (
  INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente,
                                tipo_colonna, tipo_dato, ordine_default, attivo, user_insert)
  SELECT l.lista_id, v.codice, v.codice, v.codice, 'informazione', 'string', v.ordine, TRUE, '_pgtap'
    FROM (SELECT lista_id FROM _l UNION ALL SELECT lista_id FROM _l2) l,
         (VALUES ('c_uno', 10), ('c_due', 20), ('c_tre', 30)) AS v(codice, ordine)
  RETURNING id, lista_id, codice
)
SELECT id AS colonna_id, lista_id, codice FROM ins;

-- Il preset di sistema: due colonne su tre, ordinamento, filtri, misura PRESET.
CREATE TEMP TABLE _p AS
WITH ins AS (
  INSERT INTO ui.lista_preset (lista_id, codice, descrizione, ambito, is_default,
                               pagina_dimensione, ordinamento_default, filtri_default,
                               attivo, user_insert)
  SELECT l.lista_id, 'SISTEMA_CASCATA', 'Preset sistema test cascata', 'sistema', TRUE,
         (SELECT preset FROM _m),
         '[{"col": "c_uno", "dir": "desc"}]'::jsonb, '{"c_due": "x"}'::jsonb,
         TRUE, '_pgtap'
    FROM _l l
  RETURNING id
)
SELECT id AS preset_id FROM ins;

INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, visibile, fissata)
SELECT p.preset_id, c.colonna_id, v.ordine, TRUE, FALSE
  FROM _p p
  JOIN _c c ON c.lista_id = (SELECT lista_id FROM _l)
  JOIN (VALUES ('c_uno', 1), ('c_due', 2)) AS v(codice, ordine) ON v.codice = c.codice;

CREATE TEMP TABLE _u AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-cascata-per-chiave', false);

CREATE OR REPLACE FUNCTION pg_temp.preferenza(p_configurazione jsonb) RETURNS void
LANGUAGE sql AS $$
    INSERT INTO ui.lista_preferenza_utente (auth_user_id, lista_id, configurazione)
    VALUES ((SELECT auth_user_id FROM _u), (SELECT lista_id FROM _l), p_configurazione)
    ON CONFLICT (auth_user_id, lista_id) DO UPDATE SET configurazione = EXCLUDED.configurazione;
$$;

CREATE OR REPLACE FUNCTION pg_temp.risolta(p_lista_codice text DEFAULT NULL) RETURNS jsonb
LANGUAGE sql AS $$
    SELECT ui.fn_resolve_lista_config(COALESCE(p_lista_codice, (SELECT lista_codice FROM _l)),
                                      (SELECT auth_user_id FROM _u), NULL);
$$;

-- I codici delle colonne visibili, in ordine: dice da dove vengono le colonne.
CREATE OR REPLACE FUNCTION pg_temp.visibili(p_config jsonb) RETURNS text
LANGUAGE sql AS $$
    SELECT string_agg(e ->> 'codice', ',' ORDER BY (e ->> 'ordine')::integer)
      FROM jsonb_array_elements(p_config -> 'colonne') e
     WHERE (e ->> 'visibile')::boolean;
$$;

-- Le tre colonne di preferenza: solo c_tre visibile (il preset mostra c_uno, c_due).
CREATE TEMP TABLE _pref_colonne AS
SELECT '[{"codice": "c_uno", "ordine": 1, "larghezza": 100, "visibile": false, "fissata": false},
         {"codice": "c_due", "ordine": 2, "larghezza": 100, "visibile": false, "fissata": false},
         {"codice": "c_tre", "ordine": 3, "larghezza": 100, "visibile": true,  "fissata": false}]'::jsonb AS colonne;

-- ============================================================
-- 1-3 Preferenza di sole colonne
-- ============================================================
SELECT pg_temp.preferenza(jsonb_build_object('colonne', (SELECT colonne FROM _pref_colonne)));

SELECT is(
    (SELECT format('%s|%s|%s', r -> 'ordinamento', r -> 'filtri', r ->> 'pagina_dimensione')
       FROM (SELECT pg_temp.risolta() AS r) x),
    format('%s|%s|%s', '[{"col": "c_uno", "dir": "desc"}]', '{"c_due": "x"}', (SELECT preset FROM _m)),
    '1) preferenza di sole colonne: ordinamento, filtri e misura vengono dal preset');

SELECT is(
    pg_temp.risolta() -> 'origine',
    '{"colonne": "preferenza", "ordinamento": "sistema", "filtri": "sistema", "pagina_dimensione": "sistema"}'::jsonb,
    '2) ... e origine lo dice: colonne dalla preferenza, il resto dal preset di sistema');

SELECT is(
    (pg_temp.risolta() ->> 'pagina_dimensione_standard')::integer,
    (SELECT preset FROM _m),
    '3) ... e la misura standard e'' quella del preset');

-- ============================================================
-- 4-6 Preferenza di sola misura
-- ============================================================
SELECT pg_temp.preferenza(jsonb_build_object('pagina_dimensione', (SELECT pref FROM _m)));

SELECT is(
    (SELECT format('%s|%s', pg_temp.visibili(r), r -> 'origine' ->> 'colonne')
       FROM (SELECT pg_temp.risolta() AS r) x),
    'c_uno,c_due|sistema',
    '4) preferenza di sola misura: le colonne vengono dal preset');

SELECT is(
    (SELECT format('%s|%s', r ->> 'pagina_dimensione', r -> 'origine' ->> 'pagina_dimensione')
       FROM (SELECT pg_temp.risolta() AS r) x),
    format('%s|preferenza', (SELECT pref FROM _m)),
    '5) ... la misura e'' quella della preferenza, e origine lo dice');

SELECT is(
    (pg_temp.risolta() ->> 'pagina_dimensione_standard')::integer,
    (SELECT preset FROM _m),
    '6) ... e la misura standard resta quella del preset');

-- ============================================================
-- 7 Chiave null = assente
-- ============================================================
SELECT pg_temp.preferenza(jsonb_build_object('colonne', (SELECT colonne FROM _pref_colonne),
                                             'ordinamento', NULL::jsonb));
-- jsonb_build_object con NULL scrive un null JSON: e' il caso.
SELECT is(
    (SELECT format('%s|%s', r -> 'origine' ->> 'ordinamento', r -> 'ordinamento')
       FROM (SELECT pg_temp.risolta() AS r) x),
    'sistema|[{"col": "c_uno", "dir": "desc"}]',
    '7) una chiave null nella preferenza vale come assente: risponde il preset');

-- ============================================================
-- 8 Senza preferenza
-- ============================================================
DELETE FROM ui.lista_preferenza_utente WHERE auth_user_id = (SELECT auth_user_id FROM _u);

SELECT is(
    (SELECT format('%s|%s|%s', r -> 'origine', pg_temp.visibili(r),
                   -- ::text esplicito: format('%s') su un booleano stampa t/f.
                   ((r ->> 'pagina_dimensione') = (r ->> 'pagina_dimensione_standard'))::text)
       FROM (SELECT pg_temp.risolta() AS r) x),
    format('%s|c_uno,c_due|true',
           '{"colonne": "sistema", "ordinamento": "sistema", "filtri": "sistema", "pagina_dimensione": "sistema"}'::jsonb),
    '8) senza preferenza: tutto dal preset, e la misura e'' lo standard');

-- ============================================================
-- 9 Preset senza misura
-- ============================================================
UPDATE ui.lista_preset SET pagina_dimensione = NULL WHERE id = (SELECT preset_id FROM _p);

SELECT is(
    (SELECT format('%s|%s|%s', r ->> 'pagina_dimensione', r ->> 'pagina_dimensione_standard',
                   r -> 'origine' ->> 'pagina_dimensione')
       FROM (SELECT pg_temp.risolta() AS r) x),
    format('%s|%s|catalogo', (SELECT pag FROM _m), (SELECT pag FROM _m)),
    '9) preset senza misura: lo standard e'' il default PAGINA, e origine dice catalogo');

UPDATE ui.lista_preset SET pagina_dimensione = (SELECT preset FROM _m) WHERE id = (SELECT preset_id FROM _p);

-- ============================================================
-- 10 Lista senza preset
-- ============================================================
SELECT is(
    (SELECT format('%s|%s|%s|%s', r -> 'origine', pg_temp.visibili(r), r -> 'ordinamento', r ->> 'pagina_dimensione')
       FROM (SELECT pg_temp.risolta((SELECT lista_codice FROM _l2)) AS r) x),
    format('%s|c_uno,c_due,c_tre|[]|%s',
           '{"colonne": "catalogo", "ordinamento": "catalogo", "filtri": "catalogo", "pagina_dimensione": "catalogo"}'::jsonb,
           (SELECT pag FROM _m)),
    '10) lista senza preset: tutte e quattro le chiavi dal catalogo');

-- ============================================================
-- 11-16 La data del contenuto del preset
-- ============================================================
-- Data fissa nel passato: ogni spostamento la porta a now().
UPDATE ui.lista_preset SET data_update = TIMESTAMPTZ '2026-01-01 10:00:00+00'
 WHERE id = (SELECT preset_id FROM _p);

UPDATE ui.lista_preset
   SET ordinamento_default = ordinamento_default, filtri_default = filtri_default,
       pagina_dimensione = pagina_dimensione, descrizione = descrizione
 WHERE id = (SELECT preset_id FROM _p);

SELECT is(
    (SELECT data_update FROM ui.lista_preset WHERE id = (SELECT preset_id FROM _p)),
    TIMESTAMPTZ '2026-01-01 10:00:00+00',
    '11) riscrivere la riga del preset uguale (come fa il seed): data_update non si sposta');

UPDATE ui.lista_preset SET ordinamento_default = '[{"col": "c_due", "dir": "asc"}]'::jsonb
 WHERE id = (SELECT preset_id FROM _p);

SELECT is(
    (SELECT data_update FROM ui.lista_preset WHERE id = (SELECT preset_id FROM _p)),
    now(),
    '12) cambiare ordinamento_default: data_update = now()');

UPDATE ui.lista_preset SET data_update = TIMESTAMPTZ '2026-01-01 10:00:00+00'
 WHERE id = (SELECT preset_id FROM _p);

UPDATE ui.lista_preset_colonna SET ordine = ordine, visibile = visibile
 WHERE preset_id = (SELECT preset_id FROM _p);

SELECT is(
    (SELECT data_update FROM ui.lista_preset WHERE id = (SELECT preset_id FROM _p)),
    TIMESTAMPTZ '2026-01-01 10:00:00+00',
    '13) riscrivere le colonne del preset uguali: data_update non si sposta');

UPDATE ui.lista_preset_colonna SET visibile = FALSE
 WHERE preset_id = (SELECT preset_id FROM _p)
   AND colonna_id = (SELECT colonna_id FROM _c WHERE lista_id = (SELECT lista_id FROM _l) AND codice = 'c_due');

SELECT is(
    (SELECT data_update FROM ui.lista_preset WHERE id = (SELECT preset_id FROM _p)),
    now(),
    '14) cambiare una colonna del preset: data_update = now()');

UPDATE ui.lista_preset SET data_update = TIMESTAMPTZ '2026-01-01 10:00:00+00'
 WHERE id = (SELECT preset_id FROM _p);

INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, visibile, fissata)
SELECT (SELECT preset_id FROM _p), colonna_id, 3, TRUE, FALSE
  FROM _c WHERE lista_id = (SELECT lista_id FROM _l) AND codice = 'c_tre';

SELECT is(
    (SELECT data_update FROM ui.lista_preset WHERE id = (SELECT preset_id FROM _p)),
    now(),
    '15) aggiungere una colonna al preset: data_update = now()');

UPDATE ui.lista_preset SET data_update = TIMESTAMPTZ '2026-01-01 10:00:00+00'
 WHERE id = (SELECT preset_id FROM _p);

DELETE FROM ui.lista_preset_colonna
 WHERE preset_id = (SELECT preset_id FROM _p)
   AND colonna_id = (SELECT colonna_id FROM _c WHERE lista_id = (SELECT lista_id FROM _l) AND codice = 'c_tre');

SELECT is(
    (SELECT data_update FROM ui.lista_preset WHERE id = (SELECT preset_id FROM _p)),
    now(),
    '16) togliere una colonna dal preset: data_update = now()');

-- ============================================================
-- 17-18 Il flag
-- ============================================================
UPDATE ui.lista_preset SET data_update = TIMESTAMPTZ '2026-01-01 10:00:00+00'
 WHERE id = (SELECT preset_id FROM _p);

INSERT INTO ui.lista_preferenza_utente (auth_user_id, lista_id, preset_base_id, preset_base_data_update, configurazione)
VALUES ((SELECT auth_user_id FROM _u), (SELECT lista_id FROM _l), (SELECT preset_id FROM _p),
        TIMESTAMPTZ '2026-01-01 10:00:00+00', jsonb_build_object('colonne', (SELECT colonne FROM _pref_colonne)))
ON CONFLICT (auth_user_id, lista_id) DO UPDATE
   SET preset_base_id = EXCLUDED.preset_base_id,
       configurazione = EXCLUDED.configurazione;
-- Lo snapshot dopo: il trigger z90 lo azzera se preset_base_id cambia.
UPDATE ui.lista_preferenza_utente SET preset_base_data_update = TIMESTAMPTZ '2026-01-01 10:00:00+00'
 WHERE auth_user_id = (SELECT auth_user_id FROM _u) AND lista_id = (SELECT lista_id FROM _l);

SELECT is((pg_temp.risolta() ->> 'preset_aggiornato')::boolean, FALSE,
    '17) snapshot allineato al preset: preset_aggiornato = false');

UPDATE ui.lista_preset SET pagina_dimensione = (SELECT pag FROM _m) WHERE id = (SELECT preset_id FROM _p);

SELECT is(
    (SELECT format('%s|%s', (SELECT data_update = now() FROM ui.lista_preset WHERE id = (SELECT preset_id FROM _p))::text,
                   pg_temp.risolta() ->> 'preset_aggiornato')),
    'true|true',
    '18) il preset cambia davvero (la misura): data_update spostato e flag acceso');

-- ============================================================
-- 19 I trigger
-- ============================================================
-- Per funzione e argomento, non per nome (linee-guida-trigger).
SELECT is(
    -- Schema e tabella dal catalogo: regclass::text dipende dal search_path.
    (SELECT string_agg(format('%s.%s:%s', n.nspname, c.relname, p.proname), ',' ORDER BY c.relname)
       FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
       JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE NOT t.tgisinternal
        AND t.tgrelid IN ('ui.lista_preset'::regclass, 'ui.lista_preset_colonna'::regclass)
        AND p.proname IN ('trgfn_preset_data_update_contenuto', 'trgfn_preset_riga_tocca_preset')),
    'ui.lista_preset:trgfn_preset_data_update_contenuto,ui.lista_preset_colonna:trgfn_preset_riga_tocca_preset',
    '19) i due trigger delle liste ci sono, sulle due funzioni condivise');

SELECT * FROM finish();
ROLLBACK;
