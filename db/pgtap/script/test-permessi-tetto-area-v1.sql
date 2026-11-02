-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il livello dell'area e' un TETTO per i suoi permessi (20261004-50 → -59).
--   Brief: brief-db-permessi-tetto-area, sezioni 1, 3 (D-1…D-4) e 4 (R1…R8).
--
-- ⭐ Ogni caso si COSTRUISCE (regola zero, corollario sui test): due azioni di
--   fixture con un minimo d'area noto, due oggetti di fixture a catalogo, operatori
--   umani costruiti, livelli d'area dati con override o con un profilo AD_HOC.
--   Niente dipende da cosa c'e' oggi nel catalogo.
--
-- Ogni lettura di un'azione e' «resolver/mappa/limitata» e di un oggetto
--   «resolver/mappa/limitato»: la mappa = resolver puntuale (R8 i) e la provenienza
--   del pannello (R8 j) si provano in OGNI caso, non in uno a parte.
--
-- Elenco test (plan 26):
--   La forma
--    1) azioni_processo.livello_minimo_area: livello_accesso NOT NULL DEFAULT TUTTO
--    2) un minimo BLOCCATO e' rifiutato dal CHECK (23514)
--    3) fn_area_consente_azione, tutti e due i versi dell'enum rovesciato
--    4) fn_livello_con_tetto_area: lo specifico restringe, non allarga
--    5) ⭐ sede unica: resolver e mappe LEGGONO i building block, che chiamano le
--       due regole e non riscrivono il confronto
--    6) i quattro nuovi sono INVOKER e l'app li esegue
--   Le azioni (operatore A, override)
--    7) (a) area BLOCCATO + override che abilita (minimo TUTTO) -> negata, limitata
--    8) (b) area LETTURA + minimo TUTTO -> negata, limitata
--    9) (b) area LETTURA + minimo LETTURA -> abilitata
--   10) area TUTTO -> abilitate tutte e due, nessuna limitata
--   11) il guard dei verbi eredita il tetto: area BLOCCATO -> E_PERMESSO_NEGATO
--   Gli oggetti (operatore A, override)
--   12) (d) area BLOCCATO + override TUTTO -> BLOCCATO, limitato
--   13) (e) area LETTURA + override TUTTO -> LETTURA, limitato
--   14) (f) area TUTTO + override BLOCCATO -> BLOCCATO, NON limitato (il tetto non allarga)
--   15) senza override: il livello d'area, non limitato
--   16) R4: l'area e' quella dell'OGGETTO — il quarto parametro non conta
--   17) R5: la mappa ha la chiave di ogni oggetto del catalogo, anche senza override
--   18) il guard livello eredita il tetto: (d) con minimo LETTURA -> E_PERMESSO_NEGATO
--   Il profilo (operatore B, D-2) e la scadenza (D-3)
--   19) (c) area BLOCCATO + azione abilitata dal PROFILO -> negata, limitata
--   20) (c) e l'oggetto: override TUTTO sotto l'area BLOCCATO -> BLOCCATO, limitato
--   21) (g) l'override d'area scade: l'area torna al profilo (TUTTO), e azione e
--       override sull'oggetto tornano validi — erano dormienti, non cancellati
--   Il super admin (operatore S)
--   22) (h) super admin con l'area BLOCCATO: bypass, prima del tetto, mai limitato
--   La fixture dei pgTAP
--   23) fn_pgtap_concedi_azione apre l'area AL MINIMO dell'azione (LETTURA, non TUTTO)
--   24) ...e non scavalca un override d'area che il test ha scritto: RAISE
--   Il contesto (in coda: cambia la veste di sessione)
--   25) veste CLIENTE_PORTALE: azioni negate e oggetti BLOCCATO, nei resolver e nelle mappe
--   26) ...e la provenienza non segna limitato cio' che e' negato dal gate
--
-- ⚠️ Gira come l'APPLICAZIONE: override, profili e catalogo si scrivono come li
--   scrive il pannello dei permessi. ROLLBACK in coda.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(26);

-- ============================================================
-- Fixture — catalogo: due azioni e due oggetti, con area e minimo noti
-- ============================================================
INSERT INTO config.azioni_processo (area_id, permission_codename, descrizione, livello_minimo_area)
SELECT af.id, v.codename, 'Fixture pgTAP tetto d''area', v.minimo::config.livello_accesso
  FROM config.aree_funzionali af,
       (VALUES ('pgtap_tetto_scrive', 'TUTTO'), ('pgtap_tetto_legge', 'LETTURA')) v(codename, minimo)
 WHERE af.schema_db = 'vendite';

INSERT INTO config.area_model_overrides (app_label, model_name, area_id)
SELECT 'pgtap_app', v.model_name, af.id
  FROM (VALUES ('pgtap_tetto', 'vendite'), ('pgtap_tetto_mag', 'magazzino')) v(model_name, area)
  JOIN config.aree_funzionali af ON af.schema_db = v.area;

-- I livelli li danno solo il test: un profilo legato alla veste OPERATORE (il
-- modello lo ammette, uq_profili_accesso_bindings_ruolo) si spegne qui, il
-- ROLLBACK lo riaccende.
UPDATE config.profili_accesso_bindings
   SET attivo = false
 WHERE ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND attivo;

-- Operatori: A (override), B (profilo), S (super admin). Umani, senza profili.
CREATE TEMP TABLE _t_op (sigla text, auth_user_id integer, identita_id bigint);
INSERT INTO _t_op SELECT 'A', o.auth_user_id, o.identita_id FROM dbops.fn_pgtap_crea_operatore_umano('tetto area A') o;
INSERT INTO _t_op SELECT 'B', o.auth_user_id, o.identita_id FROM dbops.fn_pgtap_crea_operatore_umano('tetto area B') o;
INSERT INTO _t_op SELECT 'S', o.auth_user_id, o.identita_id FROM dbops.fn_pgtap_crea_operatore_umano('tetto area S', p_super_admin := true) o;

CREATE FUNCTION pg_temp.op(p_sigla text) RETURNS integer LANGUAGE sql STABLE
AS $$ SELECT auth_user_id FROM _t_op WHERE sigla = p_sigla $$;

-- Il livello d'area di un utente, con un override valido da oggi (upsert).
CREATE FUNCTION pg_temp.area(p_user integer, p_schema text, p_livello text) RETURNS void LANGUAGE sql
AS $$
    INSERT INTO config.user_override_aree (auth_user_id, area_id, livello, motivo, valido_dal, valido_al)
    SELECT p_user, af.id, p_livello::config.livello_accesso, 'Fixture pgTAP', script.fn_data_operativa(), NULL
      FROM config.aree_funzionali af WHERE af.schema_db = p_schema
    ON CONFLICT ON CONSTRAINT uq_user_override_aree_user_area
    DO UPDATE SET livello = EXCLUDED.livello, valido_dal = script.fn_data_operativa(), valido_al = NULL
$$;

-- Un override sull'oggetto di fixture (upsert).
CREATE FUNCTION pg_temp.oggetto(p_user integer, p_model text, p_livello text) RETURNS void LANGUAGE sql
AS $$
    INSERT INTO config.user_override_oggetti (auth_user_id, app_label, model_name, livello, motivo)
    VALUES (p_user, 'pgtap_app', p_model, p_livello::config.livello_accesso, 'Fixture pgTAP')
    ON CONFLICT ON CONSTRAINT uq_user_override_oggetti_user_app_model
    DO UPDATE SET livello = EXCLUDED.livello
$$;

-- Un'azione letta da tre parti: resolver puntuale / mappa / provenienza.
CREATE FUNCTION pg_temp.az(p_user integer, p_codename text) RETURNS text LANGUAGE sql STABLE
AS $$
    SELECT script.fn_check_azione_processo(p_user, p_codename)::text
        || '/' || COALESCE(script.fn_get_user_actions_map(p_user) ->> p_codename, 'assente')
        || '/' || COALESCE((SELECT e.limitata_da_area::text
                              FROM script.fn_get_permessi_effettivi_azioni(p_user) e
                             WHERE e.permission_codename = p_codename), 'assente')
$$;

-- Un oggetto letto da tre parti: resolver puntuale / mappa / provenienza.
CREATE FUNCTION pg_temp.ogg(p_user integer, p_model text) RETURNS text LANGUAGE sql STABLE
AS $$
    SELECT script.fn_resolve_livello_oggetto(p_user, 'pgtap_app', p_model, NULL)::text
        || '/' || COALESCE(script.fn_get_user_object_permissions_map(p_user) ->> ('pgtap_app.' || p_model), 'assente')
        || '/' || COALESCE((SELECT e.limitato_da_area::text
                              FROM script.fn_get_permessi_effettivi_oggetti(p_user) e
                             WHERE e.app_label = 'pgtap_app' AND e.model_name = p_model), 'assente')
$$;

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
-- 1-6 La forma
-- ============================================================
-- ⚠️ Il tipo si confronta per OID, non come testo: format_type e pg_get_expr
--   omettono lo schema quando config e' nel search_path (il runner ce l'ha, una
--   sessione da owner no), e lo stesso test dava due esiti. Il default si legge
--   col prefisso di schema facoltativo, per la stessa ragione.
SELECT is(
    (SELECT (a.atttypid = 'config.livello_accesso'::regtype)::text || '/'
            || a.attnotnull::text || '/'
            || (pg_get_expr(d.adbin, d.adrelid) ~ '^''TUTTO''::(config\.)?livello_accesso$')::text
       FROM pg_attribute a
       LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
      WHERE a.attrelid = 'config.azioni_processo'::regclass
        AND a.attname = 'livello_minimo_area' AND NOT a.attisdropped),
    'true/true/true',
    '1) azioni_processo.livello_minimo_area: livello_accesso NOT NULL DEFAULT TUTTO');

SELECT throws_ok(
    $$ INSERT INTO config.azioni_processo (area_id, permission_codename, descrizione, livello_minimo_area)
       SELECT af.id, 'pgtap_tetto_bloccato', 'x', 'BLOCCATO' FROM config.aree_funzionali af
        WHERE af.schema_db = 'vendite' $$,
    '23514', NULL,
    '2) un minimo d''area BLOCCATO e'' rifiutato (non vieterebbe niente)');

SELECT is(
    concat_ws(' ',
        script.fn_area_consente_azione('LETTURA', 'TUTTO'),
        script.fn_area_consente_azione('LETTURA', 'LETTURA'),
        script.fn_area_consente_azione('TUTTO', 'LETTURA'),
        script.fn_area_consente_azione('BLOCCATO', 'LETTURA'),
        script.fn_area_consente_azione(NULL, 'TUTTO'),
        script.fn_area_consente_azione('TUTTO', NULL)),
    'f t t f f f',   -- concat_ws su boolean stampa t/f
    '3) fn_area_consente_azione: LETTURA non basta a TUTTO, basta a LETTURA; NULL vale no (enum TUTTO < LETTURA < BLOCCATO)');

SELECT is(
    concat_ws(' ',
        script.fn_livello_con_tetto_area('TUTTO', 'BLOCCATO'),
        script.fn_livello_con_tetto_area('TUTTO', 'LETTURA'),
        script.fn_livello_con_tetto_area('BLOCCATO', 'TUTTO'),
        script.fn_livello_con_tetto_area('LETTURA', 'TUTTO'),
        script.fn_livello_con_tetto_area(NULL, 'LETTURA'),
        script.fn_livello_con_tetto_area('TUTTO', NULL)),
    'BLOCCATO LETTURA BLOCCATO LETTURA LETTURA BLOCCATO',
    '4) fn_livello_con_tetto_area: il piu'' restrittivo; senza specifico vale l''area; area NULL = BLOCCATO');

-- ⭐ Il presidio che conta (linee-guida-sql §12.5.2): non «gli esiti coincidono
--   oggi», ma «la catena e il confronto stanno scritti in un posto». Commenti tolti,
--   nome seguito da parentesi.
SELECT is(
    (SELECT string_agg(x.proname, ',' ORDER BY x.proname) FILTER (WHERE NOT x.ok)
       FROM (SELECT p.proname,
                    CASE p.proname
                        WHEN 'fn_check_azione_processo' THEN
                             s ~ 'script\.fn_get_permessi_effettivi_azioni\s*\(' AND s !~ 'user_override_azioni\s'
                        WHEN 'fn_get_user_actions_map' THEN
                             s ~ 'script\.fn_get_permessi_effettivi_azioni\s*\(' AND s !~ 'user_override_azioni\s'
                        WHEN 'fn_resolve_livello_oggetto' THEN
                             s ~ 'script\.fn_get_permessi_effettivi_oggetti\s*\(' AND s !~ 'user_override_oggetti\s'
                        WHEN 'fn_get_user_object_permissions_map' THEN
                             s ~ 'script\.fn_get_permessi_effettivi_oggetti\s*\(' AND s !~ 'user_override_oggetti\s'
                        WHEN 'fn_get_permessi_effettivi_azioni' THEN
                             s ~ 'script\.fn_area_consente_azione\s*\(' AND s !~ '<='
                        WHEN 'fn_get_permessi_effettivi_oggetti' THEN
                             s ~ 'script\.fn_livello_con_tetto_area\s*\(' AND s !~* 'greatest'
                    END AS ok
               FROM pg_proc p
               CROSS JOIN LATERAL (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g') AS s) t
              WHERE p.pronamespace = 'script'::regnamespace
                AND p.proname IN ('fn_check_azione_processo', 'fn_get_user_actions_map',
                                  'fn_resolve_livello_oggetto', 'fn_get_user_object_permissions_map',
                                  'fn_get_permessi_effettivi_azioni', 'fn_get_permessi_effettivi_oggetti')) x),
    NULL,
    '5) sede unica: resolver e mappe leggono i building block, che chiamano le due regole senza riscriverle');

SELECT is(
    (SELECT string_agg(p.proname || '=' || p.prosecdef::text || '/'
                       || has_function_privilege('zeroerp_app', p.oid, 'EXECUTE')::text, ',' ORDER BY p.proname)
       FROM pg_proc p
      WHERE p.pronamespace = 'script'::regnamespace
        AND p.proname IN ('fn_area_consente_azione', 'fn_livello_con_tetto_area',
                          'fn_get_permessi_effettivi_azioni', 'fn_get_permessi_effettivi_oggetti')),
    'fn_area_consente_azione=false/true,fn_get_permessi_effettivi_azioni=false/true,'
    || 'fn_get_permessi_effettivi_oggetti=false/true,fn_livello_con_tetto_area=false/true',
    '6) i quattro nuovi sono INVOKER e l''app li esegue');

-- ============================================================
-- 7-11 Le azioni: operatore A, abilitate da override
-- ============================================================
INSERT INTO config.user_override_azioni (auth_user_id, azione_id, abilitata, motivo)
SELECT pg_temp.op('A'), ap.id, true, 'Fixture pgTAP'
  FROM config.azioni_processo ap
 WHERE ap.permission_codename IN ('pgtap_tetto_scrive', 'pgtap_tetto_legge');

SELECT pg_temp.area(pg_temp.op('A'), 'vendite', 'BLOCCATO');

SELECT is(pg_temp.az(pg_temp.op('A'), 'pgtap_tetto_scrive'), 'false/false/true',
    '7) (a) area BLOCCATO + override che abilita: negata, e limitata dall''area');

SELECT pg_temp.area(pg_temp.op('A'), 'vendite', 'LETTURA');

SELECT is(pg_temp.az(pg_temp.op('A'), 'pgtap_tetto_scrive'), 'false/false/true',
    '8) (b) area LETTURA, minimo TUTTO: negata, limitata');

SELECT is(pg_temp.az(pg_temp.op('A'), 'pgtap_tetto_legge'), 'true/true/false',
    '9) (b) area LETTURA, minimo LETTURA: abilitata');

SELECT pg_temp.area(pg_temp.op('A'), 'vendite', 'TUTTO');

SELECT is(pg_temp.az(pg_temp.op('A'), 'pgtap_tetto_scrive') || ' ' || pg_temp.az(pg_temp.op('A'), 'pgtap_tetto_legge'),
    'true/true/false true/true/false',
    '10) area TUTTO: abilitate tutte e due, nessuna limitata');

SELECT pg_temp.area(pg_temp.op('A'), 'vendite', 'BLOCCATO');

SELECT is(pg_temp.codice_di(format($q$ SELECT script.fn_guard_azione(%s, 'pgtap_tetto_scrive') $q$, pg_temp.op('A'))),
    'E_PERMESSO_NEGATO',
    '11) il guard dei verbi eredita il tetto: area BLOCCATO -> E_PERMESSO_NEGATO');

-- ============================================================
-- 12-18 Gli oggetti: operatore A
-- ============================================================
SELECT pg_temp.oggetto(pg_temp.op('A'), 'pgtap_tetto', 'TUTTO');

SELECT is(pg_temp.ogg(pg_temp.op('A'), 'pgtap_tetto'), 'BLOCCATO/BLOCCATO/true',
    '12) (d) area BLOCCATO + override TUTTO: BLOCCATO, limitato');

SELECT pg_temp.area(pg_temp.op('A'), 'vendite', 'LETTURA');

SELECT is(pg_temp.ogg(pg_temp.op('A'), 'pgtap_tetto'), 'LETTURA/LETTURA/true',
    '13) (e) area LETTURA + override TUTTO: LETTURA, limitato');

SELECT pg_temp.area(pg_temp.op('A'), 'vendite', 'TUTTO');
SELECT pg_temp.oggetto(pg_temp.op('A'), 'pgtap_tetto', 'BLOCCATO');

SELECT is(pg_temp.ogg(pg_temp.op('A'), 'pgtap_tetto'), 'BLOCCATO/BLOCCATO/false',
    '14) (f) area TUTTO + override BLOCCATO: BLOCCATO, NON limitato (il tetto non allarga)');

DELETE FROM config.user_override_oggetti
 WHERE auth_user_id = pg_temp.op('A') AND app_label = 'pgtap_app' AND model_name = 'pgtap_tetto';

SELECT is(pg_temp.ogg(pg_temp.op('A'), 'pgtap_tetto'), 'TUTTO/TUTTO/false',
    '15) senza override: il livello d''area, non limitato');

-- Area magazzino BLOCCATO, vendite TUTTO: l'oggetto di magazzino segue la SUA area,
-- qualunque area dica il chiamante.
SELECT pg_temp.area(pg_temp.op('A'), 'magazzino', 'BLOCCATO');

SELECT is(
    script.fn_resolve_livello_oggetto(pg_temp.op('A'), 'pgtap_app', 'pgtap_tetto_mag', 'vendite')::text
    || ' ' || script.fn_resolve_livello_oggetto(pg_temp.op('A'), 'pgtap_app', 'pgtap_tetto', 'magazzino')::text,
    'BLOCCATO TUTTO',
    '16) R4: l''area e'' quella dell''oggetto (area_model_overrides), il quarto parametro non conta');

SELECT is(
    (SELECT count(*)
       FROM config.area_model_overrides amo
      WHERE NOT (script.fn_get_user_object_permissions_map(pg_temp.op('A')) ? (amo.app_label || '.' || amo.model_name)))::text
    || ' ' || (script.fn_get_user_object_permissions_map(pg_temp.op('A')) ->> 'pgtap_app.pgtap_tetto_mag'),
    '0 BLOCCATO',
    '17) R5: la mappa ha una chiave per ogni oggetto del catalogo, anche senza override, col livello effettivo');

SELECT pg_temp.area(pg_temp.op('A'), 'vendite', 'BLOCCATO');
SELECT pg_temp.oggetto(pg_temp.op('A'), 'pgtap_tetto', 'TUTTO');

SELECT is(pg_temp.codice_di(format($q$ SELECT script.fn_guard_livello(%s, 'pgtap_app', 'pgtap_tetto', 'LETTURA') $q$, pg_temp.op('A'))),
    'E_PERMESSO_NEGATO',
    '18) il guard livello eredita il tetto: (d) con minimo LETTURA -> E_PERMESSO_NEGATO');

-- ============================================================
-- 19-21 Il profilo (D-2) e la scadenza dell'override d'area (D-3): operatore B
--   Profilo AD_HOC sull'identita' di B: vendite TUTTO, pgtap_tetto_scrive abilitata.
--   Sopra, un override d'area BLOCCATO che poi scade.
-- ============================================================
CREATE TEMP TABLE _t_prof AS
WITH ins AS (
    INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo)
    VALUES ('AD_HOC'::config.tipo_profilo_accesso,
            '_PGTAP_TETTO_' || upper(substr(md5(clock_timestamp()::text), 1, 16)),
            'pgTAP tetto d''area B', true)
    RETURNING id
)
SELECT id AS profilo_id FROM ins;

INSERT INTO config.profili_accesso_aree (profilo_accesso_id, area_id, livello)
SELECT p.profilo_id, af.id, 'TUTTO'::config.livello_accesso
  FROM _t_prof p, config.aree_funzionali af WHERE af.schema_db = 'vendite';

INSERT INTO config.profili_accesso_azioni (profilo_accesso_id, azione_id, abilitata)
SELECT p.profilo_id, ap.id, true
  FROM _t_prof p, config.azioni_processo ap WHERE ap.permission_codename = 'pgtap_tetto_scrive';

DO $lega$
BEGIN
    PERFORM config.fn_lega_profilo_identita(p.profilo_id, o.identita_id) FROM _t_prof p, _t_op o WHERE o.sigla = 'B';
END
$lega$;

SELECT pg_temp.area(pg_temp.op('B'), 'vendite', 'BLOCCATO');
SELECT pg_temp.oggetto(pg_temp.op('B'), 'pgtap_tetto', 'TUTTO');

SELECT is(pg_temp.az(pg_temp.op('B'), 'pgtap_tetto_scrive'), 'false/false/true',
    '19) (c) area BLOCCATO + azione abilitata dal PROFILO: negata, limitata (il tetto vale su ogni fonte)');

SELECT is(pg_temp.ogg(pg_temp.op('B'), 'pgtap_tetto'), 'BLOCCATO/BLOCCATO/true',
    '20) (c) override sull''oggetto TUTTO sotto l''area BLOCCATO: BLOCCATO, limitato');

UPDATE config.user_override_aree uoa
   SET valido_dal = script.fn_data_operativa() - 30, valido_al = script.fn_data_operativa() - 1
  FROM config.aree_funzionali af
 WHERE af.id = uoa.area_id AND af.schema_db = 'vendite'
   AND uoa.auth_user_id = pg_temp.op('B');

SELECT is(pg_temp.az(pg_temp.op('B'), 'pgtap_tetto_scrive') || ' ' || pg_temp.ogg(pg_temp.op('B'), 'pgtap_tetto'),
    'true/true/false TUTTO/TUTTO/false',
    '21) (g) l''override d''area scade: l''area torna al profilo, azione e override tornano validi (dormienti, non cancellati)');

-- ============================================================
-- 22 Il super admin
-- ============================================================
SELECT pg_temp.area(pg_temp.op('S'), 'vendite', 'BLOCCATO');
SELECT pg_temp.oggetto(pg_temp.op('S'), 'pgtap_tetto', 'BLOCCATO');

SELECT is(pg_temp.az(pg_temp.op('S'), 'pgtap_tetto_scrive') || ' ' || pg_temp.ogg(pg_temp.op('S'), 'pgtap_tetto'),
    'true/true/false TUTTO/TUTTO/false',
    '22) (h) super admin con l''area BLOCCATO: bypass totale, prima del tetto, mai limitato');

-- ============================================================
-- 23-24 La fixture dei pgTAP: concedere un'azione vuol dire che vale
-- ============================================================
CREATE TEMP TABLE _t_fix AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('tetto area fixture');

DO $az$ BEGIN PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _t_fix), 'pgtap_tetto_legge'); END $az$;

SELECT is(
    pg_temp.az((SELECT auth_user_id FROM _t_fix), 'pgtap_tetto_legge')
    || ' ' || script.fn_resolve_livello_area((SELECT auth_user_id FROM _t_fix), 'vendite')::text,
    'true/true/false LETTURA',
    '23) fn_pgtap_concedi_azione: l''azione vale, e l''area si apre AL MINIMO dell''azione (LETTURA, non TUTTO)');

SELECT pg_temp.area((SELECT auth_user_id FROM _t_fix), 'vendite', 'BLOCCATO');

SELECT throws_like(
    $$ SELECT dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _t_fix), 'pgtap_tetto_scrive') $$,
    '%chiusa da un override d''area del test%',
    '24) ...e non scavalca un override d''area scritto dal test: RAISE');

-- ============================================================
-- 25-26 Il contesto (in coda: cambia la veste di sessione)
-- ============================================================
SELECT pg_temp.area(pg_temp.op('A'), 'vendite', 'TUTTO');
SELECT set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);

SELECT is(pg_temp.az(pg_temp.op('A'), 'pgtap_tetto_legge') || ' ' || pg_temp.ogg(pg_temp.op('A'), 'pgtap_tetto'),
    'false/false/false BLOCCATO/BLOCCATO/false',
    '25) veste CLIENTE_PORTALE: azione negata e oggetto BLOCCATO, nei resolver e nelle mappe');

SELECT is(
    (SELECT count(*) FROM script.fn_get_permessi_effettivi_azioni(pg_temp.op('A')) e WHERE e.limitata_da_area OR e.abilitata)
  + (SELECT count(*) FROM script.fn_get_permessi_effettivi_oggetti(pg_temp.op('A')) e WHERE e.limitato_da_area OR e.livello <> 'BLOCCATO'),
    0::bigint,
    '26) ...su tutto il catalogo: niente abilitato, niente aperto, e niente «limitato dall''area» (e'' il gate a negare)');

SELECT * FROM finish();
ROLLBACK;
