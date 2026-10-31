-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce soggetti, ruoli e un cliente di
--   un'azienda nuova; il soggetto del test sono i campi su cui la ricerca
--   cerca, non il perimetro (lo prova script/test-search-scope-interno-v1
--   con FORCE ROW LEVEL SECURITY).
-- pgTAP test per Zero ERP
--
-- La ricerca universale cerca solo sui campi che il chiamante le passa
-- (p_campi_ricerca, in coda): i campo_sorgente accesi nel catalogo della lista
-- anagrafiche.ricerca_soggetti. Brief: brief-db-liste-datatable-grezze-
-- secondo-giro §4.5.1 (D-4 di Tid del 2026-10-31), changeSet 20261031-58.
--
-- Elenco test (plan 11):
--   1) una funzione sola con quel nome: la firma a sei argomenti e' ritirata
--   2) p_campi_ricerca NULL: si cerca su tutti e tre (il CF trova)
--   3) solo ragione sociale: il CF non trova
--   4) solo CF: il CF trova
--   5) solo CF: la ragione sociale non trova
--   6) solo codice: il codice del soggetto trova
--   7) solo codice: il codice dell'entita' (billing account del cliente) trova
--   8) solo CF: il codice dell'entita' non trova (segue soggetto_codice)
--   9) elenco vuoto: nessuna riga
--  10) * un campo fuori whitelist (utility_list) -> E_SCRIPT_CHIAMATA_NON_VALIDA
--  11) * un elemento NULL -> E_SCRIPT_CHIAMATA_NON_VALIDA
--
-- Scopo:
--  - il difetto che chiude: la funzione cercava sempre su codice, ragione
--    sociale e CF, e l'interruttore ricercabile_full del catalogo non contava.
--    Chi aveva la colonna CF a livello BLOCCATO poteva sondarla cercandola.
--  - ⭐ I test 3, 5 e 8 sono quelli che distinguono il corpo nuovo dal vecchio:
--    col vecchio ogni campo era sempre acceso.
--
-- ⛔ LA FIXTURE SI COSTRUISCE: un soggetto RE (nessuna entita_esistenza: si
--   vede se esiste) e un cliente, ciascuno col suo termine. Codice e CF si
--   leggono dalla riga costruita: i test chiedono se QUEL soggetto-ruolo c'e',
--   non quante righe tornano (altri soggetti possono avere codici simili).
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- Contesto applicativo: un'azienda col suo operatore, costruita, e il contesto
-- aperto su di lui. Il cliente costruito dopo si lega a quest'azienda.
CREATE TEMP TABLE _op ON COMMIT DROP AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _op));
END $ctx$;

CREATE TEMP TABLE _ruoli ON COMMIT DROP AS
SELECT tr.codice_interno, tr.id FROM config.tipi_ruoli tr;

-- ============================================================
-- Fixture: un soggetto RE e un cliente
-- ============================================================
-- ⚠️ Costruire e leggere in due istruzioni: una JOIN nella stessa SELECT del
--   builder non vede la riga che il builder crea.
CREATE TEMP TABLE _re_sr ON COMMIT DROP AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(
           dbops.fn_pgtap_crea_soggetto_pg('ZQCAMPIRE pgTAP campi ricerca'),
           'RE'::character varying) AS sr_id;

CREATE TEMP TABLE _re ON COMMIT DROP AS
SELECT x.sr_id, s.codice, s.id_fiscale_univoco_cf_piva AS cf
  FROM _re_sr x
  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = x.sr_id
  JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id;

CREATE TEMP TABLE _cl_c ON COMMIT DROP AS
SELECT * FROM dbops.fn_pgtap_crea_cliente(
           'ZQCAMPICL',
           (SELECT u.id FROM config.utilities u WHERE u.codice_interno = 'BASE'));

CREATE TEMP TABLE _cl ON COMMIT DROP AS
SELECT c.soggetto_ruolo_id AS sr_id, ba.codice AS ba_codice
  FROM _cl_c c
  JOIN anagrafiche.billing_account ba ON ba.id = c.billing_account_id;

-- Se il soggetto-ruolo della fixture e' fra i risultati.
CREATE OR REPLACE FUNCTION pg_temp.trova(p_term text, p_ruolo text, p_sr bigint, p_campi text[])
RETURNS boolean LANGUAGE sql AS $$
    SELECT EXISTS (
        SELECT 1
          FROM script.fn_search_soggetti_universale(
                   p_term, (SELECT id FROM _ruoli WHERE codice_interno = p_ruolo),
                   200, 0, NULL, 'ASC', p_campi) r
         WHERE r.soggetto_ruolo_id = p_sr)
$$;

-- ============================================================
-- 1) La firma
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_catalog.pg_proc p
       JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script' AND p.proname = 'fn_search_soggetti_universale'),
    1,
    '1. una funzione sola: nessun overload con la firma a sei argomenti');

-- ============================================================
-- 2-8) I campi
-- ============================================================
SELECT ok(pg_temp.trova((SELECT cf FROM _re), 'RE', (SELECT sr_id FROM _re), NULL),
    '2. p_campi_ricerca NULL: tutti e tre i campi, il CF trova (il comportamento di prima)');

SELECT ok(NOT pg_temp.trova((SELECT cf FROM _re), 'RE', (SELECT sr_id FROM _re),
                            ARRAY['ragione_sociale_completa']),
    '3. solo ragione sociale: il CF non trova');

SELECT ok(pg_temp.trova((SELECT cf FROM _re), 'RE', (SELECT sr_id FROM _re),
                        ARRAY['id_fiscale_univoco']),
    '4. solo CF: il CF trova');

SELECT ok(NOT pg_temp.trova('ZQCAMPIRE', 'RE', (SELECT sr_id FROM _re),
                            ARRAY['id_fiscale_univoco']),
    '5. solo CF: la ragione sociale non trova');

SELECT ok(pg_temp.trova((SELECT codice FROM _re), 'RE', (SELECT sr_id FROM _re),
                        ARRAY['soggetto_codice']),
    '6. solo codice: il codice del soggetto trova');

SELECT ok(pg_temp.trova((SELECT ba_codice FROM _cl), 'CL', (SELECT sr_id FROM _cl),
                        ARRAY['soggetto_codice']),
    '7. solo codice: il codice dell''entita'' (billing account del cliente) trova');

-- ⚠️ Solo CF e non solo ragione sociale: fn_pgtap_crea_cliente scrive il codice
--   del billing account DENTRO la ragione sociale («Cliente <etichetta> <BA>»).
SELECT ok(NOT pg_temp.trova((SELECT ba_codice FROM _cl), 'CL', (SELECT sr_id FROM _cl),
                            ARRAY['id_fiscale_univoco']),
    '8. solo CF: il codice dell''entita'' non trova (segue soggetto_codice)');

-- ============================================================
-- 9-11) Elenco vuoto e campi non ammessi
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM script.fn_search_soggetti_universale(
                'ZQCAMPIRE', (SELECT id FROM _ruoli WHERE codice_interno = 'RE'),
                50, 0, NULL, 'ASC', ARRAY[]::text[])),
    0,
    '9. elenco vuoto: nessuna colonna accesa, nessuna riga');

SELECT throws_like(
    format($q$SELECT * FROM script.fn_search_soggetti_universale('ZQCAMPIRE', %s, 50, 0, NULL, 'ASC', ARRAY['utility_list'])$q$,
           (SELECT id FROM _ruoli WHERE codice_interno = 'RE')),
    '%campo di ricerca non ammesso: utility_list%',
    '10. un campo fuori whitelist -> E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT throws_like(
    format($q$SELECT * FROM script.fn_search_soggetti_universale('ZQCAMPIRE', %s, 50, 0, NULL, 'ASC', ARRAY[NULL, 'soggetto_codice'])$q$,
           (SELECT id FROM _ruoli WHERE codice_interno = 'RE')),
    '%campo di ricerca non ammesso: NULL%',
    '11. un elemento NULL -> E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT * FROM finish();
ROLLBACK;
