-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le colonne che il pannello scrive, in una sede —
--   config.fn_pannello_colonne_scrivibili (20260927-21), e il verbo che la usa
--   (config.fn_pannello_scrivi, 20260927-22).
--   Brief: brief-db-pannello-config-verbo-generico, sezione 6.
--
-- Elenco test (plan 7):
--   La regola
--    1) config.tipi_nota: codice e descrizione ci sono, nessuna colonna di sistema
--       (id, audit, tx_id, storicizza, uid)
--    2) l'ordine e' quello della tabella (attnum)
--    3) su OGNI riga del pannello: risponde, e non da' colonne di sistema, generate
--       o identity ALWAYS
--   Fuori dal pannello: NULL, non un errore (a sollevare e' il verbo)
--    4) magazzino.magazzini (RLS), config.profili_accesso (casa propria), una
--       tabella che non esiste, NULL
--   Il verbo
--    5) ⭐ la riga che il verbo ritorna ha esattamente id + le colonne scrivibili
--       (i campi del form)
--    6) il verbo non ha piu' una copia sua dell'elenco: chiama la funzione, e la
--       costante c_escluse non c'e' piu' (presidio sul testo, dichiarato)
--   La forma
--    7) STABLE, INVOKER, l'app la esegue, PUBLIC no
--
-- ⚠️ Gira come l'APPLICAZIONE. Il ramo «colonna generata / identity ALWAYS» non si
--   COSTRUISCE qui: l'app non crea tabelle e non scrive la lista. Il 3 lo
--   controlla sulle tabelle del pannello, e la prova pre-apply da owner lo ha
--   costruito (tabella con una colonna generata e una identity ALWAYS, in lista,
--   in transazione annullata). Il 3 legge la lista che semina il seed di CATALOGO:
--   su un database da zero non e' vuota, e il test lo pretende.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

CREATE TEMP TABLE _di_sistema (nome text);
INSERT INTO _di_sistema VALUES ('id'), ('data_insert'), ('user_insert'), ('data_update'),
                               ('user_update'), ('tx_id'), ('storicizza'), ('uid');

-- ============================================================
-- 1-3 La regola
-- ============================================================
SELECT is(
    (SELECT format('%s|%s',
                   (config.fn_pannello_colonne_scrivibili('config.tipi_nota') @> ARRAY['codice', 'descrizione'])::text,
                   (config.fn_pannello_colonne_scrivibili('config.tipi_nota') && (SELECT array_agg(nome) FROM _di_sistema))::text)),
    'true|false',
    '1) config.tipi_nota: codice e descrizione si scrivono, nessuna colonna di sistema');

SELECT is(
    config.fn_pannello_colonne_scrivibili('config.tipi_nota'),
    (SELECT array_agg(a.attname::text ORDER BY a.attnum)
       FROM pg_attribute a
      WHERE a.attrelid = 'config.tipi_nota'::regclass
        AND a.attname::text = ANY (config.fn_pannello_colonne_scrivibili('config.tipi_nota'))),
    '2) nell''ordine delle colonne della tabella');

SELECT is(
    (SELECT format('%s|%s', (count(*) > 0)::text,
                   COALESCE(string_agg(tg.codice_interno, ',' ORDER BY tg.codice_interno)
                                FILTER (WHERE config.fn_pannello_colonne_scrivibili(tg.codice_interno) IS NULL
                                           OR EXISTS (
                                              SELECT 1
                                                FROM unnest(config.fn_pannello_colonne_scrivibili(tg.codice_interno)) AS k
                                                JOIN pg_namespace n ON n.nspname = tg.schema_tabella
                                                JOIN pg_class c ON c.relnamespace = n.oid AND c.relname = tg.nome_tabella
                                                JOIN pg_attribute a ON a.attrelid = c.oid AND a.attname = k
                                               WHERE k IN (SELECT nome FROM _di_sistema)
                                                  OR a.attgenerated <> ''
                                                  OR a.attidentity = 'a')), ''))
       FROM config.tabelle_gestibili tg
      WHERE tg.pannello),
    'true|',
    '3) ogni tabella del pannello risponde, senza colonne di sistema, generate o identity ALWAYS');

-- ============================================================
-- 4 Fuori dal pannello
-- ============================================================
SELECT is(
    format('%s|%s|%s|%s',
           (config.fn_pannello_colonne_scrivibili('magazzino.magazzini') IS NULL)::text,
           (config.fn_pannello_colonne_scrivibili('config.profili_accesso') IS NULL)::text,
           (config.fn_pannello_colonne_scrivibili('config.non_esiste_pgtap') IS NULL)::text,
           (config.fn_pannello_colonne_scrivibili(NULL) IS NULL)::text),
    'true|true|true|true',
    '4) fuori dal pannello, o inesistente, o NULL: NULL');

-- ============================================================
-- 5-6 Il verbo
--   TUTTO sull'area config all'operatore costruito, per scrivere tipi_nota.
-- ============================================================
CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;

INSERT INTO config.user_override_aree (auth_user_id, area_id, livello, motivo)
SELECT m.auth_user_id, af.id, 'TUTTO', 'Fixture pgTAP'
  FROM _mondo m, config.aree_funzionali af WHERE af.schema_db = 'config';

SELECT is(
    (SELECT array_agg(k ORDER BY k)
       FROM jsonb_object_keys(config.fn_pannello_scrivi(
                'config.tipi_nota', NULL,
                jsonb_build_object('codice', 'PGTAP_COLONNE', 'codice_interno', 'PGTAP_COLONNE',
                                   'descrizione', 'Fixture pgTAP colonne scrivibili'))) AS k),
    (SELECT array_agg(k ORDER BY k)
       FROM unnest(array_append(config.fn_pannello_colonne_scrivibili('config.tipi_nota'), 'id')) AS k),
    '5) ⭐ il verbo ritorna id + le colonne scrivibili, cioe'' i campi del form');

SELECT is(
    (SELECT format('%s|%s',
                   (p.prosrc LIKE '%config.fn_pannello_colonne_scrivibili(%')::text,
                   (p.prosrc LIKE '%c_escluse%')::text)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'config' AND p.proname = 'fn_pannello_scrivi'),
    'true|false',
    '6) il verbo chiama la sede unica e non ha piu'' una copia sua (c_escluse)');

-- ============================================================
-- 7 La forma
-- ============================================================
SELECT is(
    (SELECT format('%s|%s|%s|%s', p.provolatile::text, p.prosecdef::text,
                   has_function_privilege('zeroerp_app', p.oid, 'EXECUTE')::text,
                   (EXISTS (SELECT 1 FROM aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner))) x
                             WHERE x.grantee = 0 AND x.privilege_type = 'EXECUTE'))::text)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'config' AND p.proname = 'fn_pannello_colonne_scrivibili'),
    's|false|true|false',
    '7) STABLE, INVOKER, l''app la esegue, PUBLIC no');

SELECT * FROM finish();
ROLLBACK;
