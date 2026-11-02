-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il riepilogo permessi per area e la sede unica del conteggio degli override
--   (20261006-01 script.vw_override_operatore_area, 20261006-02
--   script.fn_get_permessi_riepilogo_aree).
--   Brief: brief-db-riepilogo-permessi-lista-operatori, §3.1, §3.2 e §4.
--
-- ⭐ Ogni caso si COSTRUISCE (regola zero, corollario sui test): un'azione e due
--   oggetti di fixture con area nota, quattro operatori umani fabbricati, livelli
--   d'area dati con override. Niente dipende da cosa c'e' oggi nel catalogo: le voci
--   reali del catalogo, per questi operatori senza profili, non sono mai limitate e
--   non hanno override.
--
-- ⚠️ Il §4 del brief chiedeva di contare un override su un'azione NON attiva e uno
--   su un oggetto RISERVATO. Sul modello non si possono costruire: i test 5-7 provano
--   che il database li rifiuta, ed e' questa la ragione per cui la vista non filtra.
--
-- Elenco test (plan 16):
--   La forma
--    1) la vista e' security_invoker e l'app la legge
--    2) la funzione e' INVOKER, STABLE, e l'app la esegue
--    3) ⭐ sede unica: la funzione legge le quattro sedi e non riscrive niente
--   §3.1 La vista
--    4) una riga per override scritto, con l'area giusta per tipo
--    5) D-2: un override scaduto si conta lo stesso
--    6) il modello rifiuta di spegnere un'azione che ha un override
--    7) ...e di rendere riservato un oggetto che ha un override
--    8) ...e un override nuovo su un oggetto riservato
--   §3.2 La funzione
--    9) una riga per (operatore, area attiva), duplicati e NULL ignorati
--   10) livello = fn_resolve_livello_area per ogni (operatore, area)
--   11) override_count = le righe della vista per (operatore, area), zeri compresi
--   12) operatore A: vendite e magazzino, livello, override e voci limitate
--   13) voci_limitate = il conteggio fatto direttamente sulle due funzioni del tetto
--   14) super admin: TUTTO ovunque, override contati, niente limitato
--   15) veste OPERATORE spenta: BLOCCATO ovunque, override contati, niente limitato
--   16) array vuoto e NULL: zero righe
--
-- ⚠️ Gira come l'APPLICAZIONE: override e catalogo si scrivono come li scrive il
--   pannello dei permessi. ROLLBACK in coda.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ============================================================
-- Fixture — catalogo: un'azione in vendite, due oggetti in magazzino (uno riservato)
-- ============================================================
INSERT INTO config.azioni_processo (area_id, permission_codename, descrizione, livello_minimo_area)
SELECT af.id, 'pgtap_riep_scrive', 'Fixture pgTAP riepilogo permessi', 'TUTTO'::config.livello_accesso
  FROM config.aree_funzionali af
 WHERE af.schema_db = 'vendite';

INSERT INTO config.area_model_overrides (app_label, model_name, area_id, riservato)
SELECT 'pgtap_app', v.model_name, af.id, v.riservato
  FROM (VALUES ('pgtap_riep', false), ('pgtap_riep_riservato', true)) v(model_name, riservato)
  JOIN config.aree_funzionali af ON af.schema_db = 'magazzino';

-- I livelli li danno solo il test: i profili legati alla veste OPERATORE si
-- spengono qui, il ROLLBACK li riaccende.
UPDATE config.profili_accesso_bindings
   SET attivo = false
 WHERE ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND attivo;

-- Operatori: A (override), B (nessun override), S (super admin), V (veste spenta).
CREATE TEMP TABLE _t_op (sigla text, auth_user_id integer, identita_id bigint);
INSERT INTO _t_op SELECT 'A', o.auth_user_id, o.identita_id FROM dbops.fn_pgtap_crea_operatore_umano('riepilogo A') o;
INSERT INTO _t_op SELECT 'B', o.auth_user_id, o.identita_id FROM dbops.fn_pgtap_crea_operatore_umano('riepilogo B') o;
INSERT INTO _t_op SELECT 'S', o.auth_user_id, o.identita_id FROM dbops.fn_pgtap_crea_operatore_umano('riepilogo S', p_super_admin := true) o;
INSERT INTO _t_op SELECT 'V', o.auth_user_id, o.identita_id FROM dbops.fn_pgtap_crea_operatore_umano('riepilogo V') o;

CREATE FUNCTION pg_temp.op(p_sigla text) RETURNS integer LANGUAGE sql STABLE
AS $$ SELECT auth_user_id FROM _t_op WHERE sigla = p_sigla $$;

-- Un override d'area, con la sua finestra.
CREATE FUNCTION pg_temp.area(p_user integer, p_schema text, p_livello text,
                             p_dal date DEFAULT script.fn_data_operativa(), p_al date DEFAULT NULL)
RETURNS void LANGUAGE sql
AS $$
    INSERT INTO config.user_override_aree (auth_user_id, area_id, livello, motivo, valido_dal, valido_al)
    SELECT p_user, af.id, p_livello::config.livello_accesso, 'Fixture pgTAP', p_dal, p_al
      FROM config.aree_funzionali af WHERE af.schema_db = p_schema
$$;

-- L'override che abilita l'azione di fixture.
CREATE FUNCTION pg_temp.azione(p_user integer) RETURNS void LANGUAGE sql
AS $$
    INSERT INTO config.user_override_azioni (auth_user_id, azione_id, abilitata, motivo)
    SELECT p_user, ap.id, true, 'Fixture pgTAP'
      FROM config.azioni_processo ap WHERE ap.permission_codename = 'pgtap_riep_scrive'
$$;

-- Il riepilogo di un operatore, area per area: «schema=livello/override/limitate».
CREATE FUNCTION pg_temp.riep(p_user integer, p_schemi text[]) RETURNS text LANGUAGE sql STABLE
AS $$
    SELECT string_agg(af.schema_db || '=' || r.livello::text || '/' || r.override_count
                      || '/' || r.voci_limitate, ' ' ORDER BY af.schema_db)
      FROM script.fn_get_permessi_riepilogo_aree(ARRAY[p_user]) r
      JOIN config.aree_funzionali af ON af.id = r.area_id
     WHERE af.schema_db = ANY (p_schemi)
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

-- A: area vendite BLOCCATO + azione abilitata (minimo TUTTO) => 1 voce limitata in
--    vendite; area magazzino LETTURA SCADUTA (l'area torna BLOCCATO) + oggetto TUTTO
--    => 1 voce limitata in magazzino. Quattro override scritti.
SELECT pg_temp.area(pg_temp.op('A'), 'vendite', 'BLOCCATO');
SELECT pg_temp.area(pg_temp.op('A'), 'magazzino', 'LETTURA', script.fn_data_operativa() - 10, script.fn_data_operativa() - 5);
SELECT pg_temp.azione(pg_temp.op('A'));
INSERT INTO config.user_override_oggetti (auth_user_id, app_label, model_name, livello, motivo)
VALUES (pg_temp.op('A'), 'pgtap_app', 'pgtap_riep', 'TUTTO', 'Fixture pgTAP');

-- S e V: gli stessi due override in vendite che per A fermano l'azione.
SELECT pg_temp.area(pg_temp.op(s), 'vendite', 'BLOCCATO') FROM unnest(ARRAY['S', 'V']) s;
SELECT pg_temp.azione(pg_temp.op(s)) FROM unnest(ARRAY['S', 'V']) s;

-- ============================================================
-- 1-3 La forma
-- ============================================================
SELECT is(
    (SELECT (c.reloptions @> ARRAY['security_invoker=true'])::text || '/'
            || has_table_privilege('zeroerp_app', c.oid, 'SELECT')::text
       FROM pg_class c
      WHERE c.oid = 'script.vw_override_operatore_area'::regclass),
    'true/true',
    '1) script.vw_override_operatore_area: security_invoker, e l''app la legge');

SELECT is(
    (SELECT p.prosecdef::text || '/' || p.provolatile::text || '/'
            || has_function_privilege('zeroerp_app', p.oid, 'EXECUTE')::text
       FROM pg_proc p
      WHERE p.oid = 'script.fn_get_permessi_riepilogo_aree(integer[])'::regprocedure),
    'false/s/true',
    '2) fn_get_permessi_riepilogo_aree: INVOKER, STABLE, e l''app la esegue');

-- ⭐ Il presidio che conta (linee-guida-sql §12.5.2): non «gli esiti coincidono
--   oggi», ma «il riepilogo non riscrive niente». Commenti tolti, nome seguito da
--   parentesi.
SELECT is(
    (SELECT concat_ws(' ',
                s ~ 'script\.fn_resolve_livello_area\s*\(',
                s ~ 'script\.vw_override_operatore_area\M',
                s ~ 'script\.fn_get_permessi_effettivi_azioni\s*\(',
                s ~ 'script\.fn_get_permessi_effettivi_oggetti\s*\(',
                s ~ 'user_override_',
                s ~ 'fn_area_consente_azione|fn_livello_con_tetto_area',
                s ~* 'greatest')
       FROM pg_proc p
      CROSS JOIN LATERAL (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g') AS s) t
      WHERE p.oid = 'script.fn_get_permessi_riepilogo_aree(integer[])'::regprocedure),
    't t t t f f f',   -- concat_ws su boolean stampa t/f
    '3) sede unica: legge catena d''area, vista e le due funzioni del tetto, non le tabelle ne'' le regole');

-- ============================================================
-- 4-8 §3.1 La vista
-- ============================================================
SELECT is(
    (SELECT string_agg(v.tipo || ':' || af.schema_db, ' ' ORDER BY v.tipo, af.schema_db)
       FROM script.vw_override_operatore_area v
       JOIN config.aree_funzionali af ON af.id = v.area_id
      WHERE v.auth_user_id = pg_temp.op('A')),
    'AREA:magazzino AREA:vendite AZIONE:vendite OGGETTO:magazzino',
    '4) una riga per override scritto: l''area dell''override, dell''azione, dell''oggetto');

SELECT is(
    (SELECT count(*)::integer
       FROM script.vw_override_operatore_area v
       JOIN config.user_override_aree uoa ON uoa.id = v.override_id
      WHERE v.tipo = 'AREA'
        AND v.auth_user_id = pg_temp.op('A')
        AND NOT uoa.validita @> script.fn_data_operativa()),
    1,
    '5) D-2: l''override d''area scaduto resta contato (scritto, non in vigore)');

SELECT is(
    pg_temp.codice_di($q$ UPDATE config.azioni_processo SET attivo = false
                           WHERE permission_codename = 'pgtap_riep_scrive' $q$),
    'E_ATTIVO_BLOCK_CHILDREN_EXIST',
    '6) un''azione con un override non si spegne: «override su azione non attiva» non esiste');

SELECT is(
    pg_temp.codice_di($q$ UPDATE config.area_model_overrides SET riservato = true
                           WHERE app_label = 'pgtap_app' AND model_name = 'pgtap_riep' $q$),
    'fk_user_override_oggetti_catalogo',
    '7) un oggetto con un override non diventa riservato (FK composita)');

SELECT is(
    pg_temp.codice_di(format(
        $q$ INSERT INTO config.user_override_oggetti (auth_user_id, app_label, model_name, livello, motivo)
            VALUES (%s, 'pgtap_app', 'pgtap_riep_riservato', 'TUTTO', 'Fixture pgTAP') $q$,
        pg_temp.op('B'))),
    'fk_user_override_oggetti_catalogo',
    '8) ...e un override nuovo su un oggetto riservato e'' rifiutato: «riservato con override» non esiste');

-- ============================================================
-- 9-16 §3.2 La funzione
-- ============================================================
SELECT is(
    (SELECT count(*)::integer || '/' || count(DISTINCT r.auth_user_id)::integer
       FROM script.fn_get_permessi_riepilogo_aree(
                ARRAY[pg_temp.op('A'), pg_temp.op('B'), pg_temp.op('A'), NULL]) r),
    (SELECT (2 * count(*))::integer || '/2' FROM config.aree_funzionali WHERE attivo),
    '9) una riga per (operatore, area attiva): duplicati e NULL dell''array ignorati');

SELECT is(
    (SELECT count(*)::integer
       FROM script.fn_get_permessi_riepilogo_aree(
                ARRAY(SELECT auth_user_id FROM _t_op)) r
       JOIN config.aree_funzionali af ON af.id = r.area_id
      WHERE r.livello IS DISTINCT FROM script.fn_resolve_livello_area(r.auth_user_id, af.schema_db)),
    0,
    '10) livello = fn_resolve_livello_area, per ogni operatore e ogni area');

SELECT is(
    (SELECT count(*)::integer
       FROM script.fn_get_permessi_riepilogo_aree(
                ARRAY(SELECT auth_user_id FROM _t_op)) r
      WHERE r.override_count <> (SELECT count(*)
                                   FROM script.vw_override_operatore_area v
                                  WHERE v.auth_user_id = r.auth_user_id
                                    AND v.area_id = r.area_id)),
    0,
    '11) override_count = le righe della vista per (operatore, area), zeri compresi');

SELECT is(
    pg_temp.riep(pg_temp.op('A'), ARRAY['magazzino', 'vendite']),
    'magazzino=BLOCCATO/2/1 vendite=BLOCCATO/2/1',
    '12) A: vendite BLOCCATO, 2 override, l''azione fermata; magazzino BLOCCATO (override scaduto), 2 override, l''oggetto fermato');

SELECT is(
    (SELECT count(*)::integer
       FROM script.fn_get_permessi_riepilogo_aree(
                ARRAY(SELECT auth_user_id FROM _t_op)) r
       JOIN config.aree_funzionali af ON af.id = r.area_id
      WHERE r.voci_limitate <>
            (SELECT count(*) FROM script.fn_get_permessi_effettivi_azioni(r.auth_user_id) e
              WHERE e.area_id = r.area_id AND e.limitata_da_area)
          + (SELECT count(*) FROM script.fn_get_permessi_effettivi_oggetti(r.auth_user_id) e
              WHERE e.area_schema_db = af.schema_db AND e.limitato_da_area)),
    0,
    '13) voci_limitate = il conteggio fatto direttamente sulle due funzioni del tetto');

SELECT is(
    (SELECT string_agg(DISTINCT r.livello::text || '/' || r.voci_limitate, ',')
            || ' ' || sum(r.override_count)
       FROM script.fn_get_permessi_riepilogo_aree(ARRAY[pg_temp.op('S')]) r),
    'TUTTO/0 2',
    '14) super admin: TUTTO su ogni area, nessuna voce limitata, i due override contati');

UPDATE anagrafiche.identita_digitali SET attivo = false
 WHERE id = (SELECT identita_id FROM _t_op WHERE sigla = 'V');

SELECT is(
    (SELECT string_agg(DISTINCT r.livello::text || '/' || r.voci_limitate, ',')
            || ' ' || sum(r.override_count)
       FROM script.fn_get_permessi_riepilogo_aree(ARRAY[pg_temp.op('V')]) r),
    'BLOCCATO/0 2',
    '15) veste OPERATORE spenta: BLOCCATO su ogni area, nessuna voce limitata, gli override scritti contati');

SELECT is(
    (SELECT count(*)::integer FROM script.fn_get_permessi_riepilogo_aree(ARRAY[]::integer[]))
    || '/' ||
    (SELECT count(*)::integer FROM script.fn_get_permessi_riepilogo_aree(NULL)),
    '0/0',
    '16) array vuoto e NULL: zero righe');

SELECT * FROM finish();
ROLLBACK;
