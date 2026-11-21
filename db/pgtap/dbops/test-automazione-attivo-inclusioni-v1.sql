-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- pgtap-runner: owner
-- pgtap-runner-motivo: spegnere un regime fiscale lo puo' solo il migratore (config.regimi_fiscali e' un catalogo scritto dal seed): il block che il test collauda nessun entry point dell'applicazione lo puo' far scattare (forma 3 di scripts/testpgtap.sh)
--
-- Test: le INCLUSIONI dell'automazione ATTIVO, e le prime: un regime fiscale
--   spento non si assegna, e uno in uso non si spegne (Tid, 2026-11-21).
--   ChangeSet: 20261121-10 (registro), -11 (dbops.fn_attivo_fk_esclusa),
--   -12 (runner), -13 (ritiro), -14 (seed), -15 (provision).
--
-- ⛔ I trigger si cercano per FUNZIONE e ARGOMENTI, non per nome: i nomi
--   generati sono hashati oltre i 63 caratteri.
-- ⚠️ In CI i trigger ATTIVO li genera la passata ci_apply, che gira PRIMA dei
--   pgTAP: i test 3-5 sono veri anche li'.
-- ⭐ I due regimi del test (RF97, RF98) li COSTRUISCE il test, con id
--   espliciti e liberi (regola zero): spegnere un regime del catalogo
--   dipenderebbe da chi lo usa oggi.
--
-- Elenco test (plan 12):
--   Il registro e il framework
--    1) le due righe del registro, col motivo
--    2) ogni riga nomina una FK monocolonna viva della figlia, senza _id, e
--       non e' anche un'eccezione
--    3) il require su emittenti_fiscali per regime_fiscale_rf, verso
--       config.regimi_fiscali(codice_interno)
--    4) il require su fornitori, idem
--    5) i due block su config.regimi_fiscali, uno per figlia
--    6) dbops.fn_attivo_fk_esclusa: eccezione, FK senza _id fuori registro,
--       FK inclusa, FK con _id
--   Il comportamento
--    7) un regime che nessuno usa si spegne
--    8) a un fornitore acceso non si assegna un regime spento: E_ATTIVO_PADRE_NON_ATTIVO
--    9) a un emittente acceso nemmeno: E_ATTIVO_PADRE_NON_ATTIVO
--   10) un regime usato da un fornitore acceso non si spegne: E_ATTIVO_BLOCK_CHILDREN_ACTIVE
--   11) spento il fornitore, il regime si spegne, e il fornitore lo tiene
--   12) riaccendere il fornitore che tiene il regime spento: E_ATTIVO_PADRE_NON_ATTIVO
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- I trigger ATTIVO, con gli argomenti letti dalla grammatica condivisa.
-- ⛔ Il nome della tabella si compone dal catalogo, NON con tgrelid::regclass::text,
--   che dipende dal search_path.
CREATE TEMP TABLE _trg AS
SELECT cn.nspname || '.' || c.relname AS rel,
       p.proname::text AS proname,
       g.*
  FROM pg_trigger t
  JOIN pg_class c      ON c.oid = t.tgrelid
  JOIN pg_namespace cn ON cn.oid = c.relnamespace
  JOIN pg_proc p       ON p.oid = t.tgfoid
  JOIN pg_namespace pn ON pn.oid = p.pronamespace AND pn.nspname = 'dbops'
  CROSS JOIN LATERAL dbops.fn_trigger_attivo_argomenti(
      p.proname, dbops.fn_trigger_argomenti(t.tgargs)) AS g
 WHERE NOT t.tgisinternal
   AND p.proname IN ('trgfn_child_requires_active_parent',
                     'trgfn_prevent_deactivate_if_children');

-- ============================================================
-- 1-2) Il registro
-- ============================================================
SELECT is(
    (SELECT array_agg(i.tabella_figlia || '.' || i.colonna_fk ORDER BY i.tabella_figlia COLLATE "C")
       FROM dbops.automazione_attivo_inclusioni i
      WHERE i.schema_figlia = 'anagrafiche'
        AND i.colonna_fk = 'regime_fiscale_rf'
        AND btrim(i.motivo) <> ''),
    ARRAY['emittenti_fiscali.regime_fiscale_rf', 'fornitori.regime_fiscale_rf'],
    '1) le due righe del registro, col motivo');

SELECT is(
    (SELECT COALESCE(array_agg(i.schema_figlia || '.' || i.tabella_figlia || '.' || i.colonna_fk
                               ORDER BY 1), '{}'::text[])
       FROM dbops.automazione_attivo_inclusioni i
      WHERE NOT EXISTS (
                SELECT 1
                  FROM pg_constraint k
                  JOIN pg_attribute a ON a.attrelid = k.conrelid AND a.attnum = k.conkey[1]
                 WHERE k.contype = 'f'
                   AND cardinality(k.conkey) = 1
                   AND k.conrelid = to_regclass(format('%I.%I', i.schema_figlia, i.tabella_figlia))
                   AND a.attname = i.colonna_fk)
         OR EXISTS (
                SELECT 1 FROM dbops.automazione_attivo_eccezioni e
                 WHERE (e.schema_figlia, e.tabella_figlia, e.colonna_fk)
                     = (i.schema_figlia, i.tabella_figlia, i.colonna_fk))),
    '{}'::text[],
    '2) ogni riga nomina una FK monocolonna viva e non e'' anche un''eccezione');

-- ============================================================
-- 3-5) I trigger generati
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM _trg
      WHERE proname = 'trgfn_child_requires_active_parent'
        AND rel = 'anagrafiche.emittenti_fiscali'
        AND padre_schema = 'config' AND padre_tabella = 'regimi_fiscali'
        AND fk_col = 'regime_fiscale_rf' AND ref_col = 'codice_interno'),
    1,
    '3) il require su emittenti_fiscali.regime_fiscale_rf verso config.regimi_fiscali(codice_interno)');

SELECT is(
    (SELECT count(*)::int FROM _trg
      WHERE proname = 'trgfn_child_requires_active_parent'
        AND rel = 'anagrafiche.fornitori'
        AND padre_schema = 'config' AND padre_tabella = 'regimi_fiscali'
        AND fk_col = 'regime_fiscale_rf' AND ref_col = 'codice_interno'),
    1,
    '4) il require su fornitori.regime_fiscale_rf verso config.regimi_fiscali(codice_interno)');

SELECT is(
    (SELECT COALESCE(array_agg(figlia_tabella::text ORDER BY figlia_tabella COLLATE "C"), '{}'::text[])
       FROM _trg
      WHERE proname = 'trgfn_prevent_deactivate_if_children'
        AND rel = 'config.regimi_fiscali'
        AND figlia_schema = 'anagrafiche'
        AND fk_col = 'regime_fiscale_rf' AND ref_col = 'codice_interno'),
    ARRAY['emittenti_fiscali', 'fornitori'],
    '5) i due block su config.regimi_fiscali, uno per figlia');

-- ============================================================
-- 6) La risposta del building block
-- ============================================================
SELECT is(
    ARRAY[
      COALESCE(dbops.fn_attivo_fk_esclusa('config', 'profili_accesso_bindings', 'identita_digitale_id'), '<si lega>'),
      COALESCE(dbops.fn_attivo_fk_esclusa('vendite', 'note', 'target_tipo'), '<si lega>'),
      COALESCE(dbops.fn_attivo_fk_esclusa('anagrafiche', 'fornitori', 'regime_fiscale_rf'), '<si lega>'),
      COALESCE(dbops.fn_attivo_fk_esclusa('anagrafiche', 'fornitori', 'valuta_id'), '<si lega>')],
    ARRAY['ECCEZIONE_DICHIARATA', 'FK_NO_ID_SUFFIX', '<si lega>', '<si lega>'],
    '6) fn_attivo_fk_esclusa: eccezione, FK senza _id fuori registro, FK inclusa, FK con _id');

-- ============================================================
-- Fixture: due regimi del test, un fornitore con RF97, un emittente
-- ============================================================
INSERT INTO config.regimi_fiscali (id, codice_interno, codice, descrizione)
VALUES (999997, 'RF97', 'PGTAP-RF97', 'Regime pgTAP 97'),
       (999998, 'RF98', 'PGTAP-RF98', 'Regime pgTAP 98');

CREATE TEMP TABLE _s AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Fornitore regime spento pgTAP') AS s;
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(s, 'FO') FROM _s;
SET CONSTRAINTS ALL DEFERRED;
CREATE TEMP TABLE _f AS
SELECT f.fornitore_id
  FROM _s, anagrafiche.fn_crea_fornitore(_s.s, '{"regime_fiscale_rf": "RF97"}'::jsonb) f;
CREATE TEMP TABLE _e AS SELECT * FROM dbops.fn_pgtap_crea_emittente();
SET CONSTRAINTS ALL IMMEDIATE;

-- ============================================================
-- 7-12) Il comportamento
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(
        $$UPDATE config.regimi_fiscali SET attivo = false WHERE codice_interno = 'RF98'$$),
    NULL,
    '7) un regime che nessuno usa si spegne');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$UPDATE anagrafiche.fornitori SET regime_fiscale_rf = 'RF98' WHERE id = %s$$,
        (SELECT fornitore_id FROM _f))),
    'E_ATTIVO_PADRE_NON_ATTIVO',
    '8) a un fornitore acceso non si assegna un regime spento: E_ATTIVO_PADRE_NON_ATTIVO');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$UPDATE anagrafiche.emittenti_fiscali SET regime_fiscale_rf = 'RF98' WHERE id = %s$$,
        (SELECT emittente_fiscale_id FROM _e))),
    'E_ATTIVO_PADRE_NON_ATTIVO',
    '9) a un emittente acceso non si assegna un regime spento: E_ATTIVO_PADRE_NON_ATTIVO');

SELECT is(
    dbops.fn_pgtap_codice_errore(
        $$UPDATE config.regimi_fiscali SET attivo = false WHERE codice_interno = 'RF97'$$),
    'E_ATTIVO_BLOCK_CHILDREN_ACTIVE',
    '10) un regime usato da un fornitore acceso non si spegne: E_ATTIVO_BLOCK_CHILDREN_ACTIVE');

SELECT is(
    ARRAY[
      COALESCE(dbops.fn_pgtap_codice_errore(format(
          $$UPDATE anagrafiche.fornitori SET attivo = false WHERE id = %s$$,
          (SELECT fornitore_id FROM _f))), 'ok'),
      COALESCE(dbops.fn_pgtap_codice_errore(
          $$UPDATE config.regimi_fiscali SET attivo = false WHERE codice_interno = 'RF97'$$), 'ok'),
      COALESCE((SELECT fo.regime_fiscale_rf::text FROM anagrafiche.fornitori fo
                 WHERE fo.id = (SELECT fornitore_id FROM _f)), '<senza regime>')],
    ARRAY['ok', 'ok', 'RF97'],
    '11) spento il fornitore, il regime si spegne, e il fornitore lo tiene');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$UPDATE anagrafiche.fornitori SET attivo = true WHERE id = %s$$,
        (SELECT fornitore_id FROM _f))),
    'E_ATTIVO_PADRE_NON_ATTIVO',
    '12) riaccendere il fornitore che tiene un regime spento: E_ATTIVO_PADRE_NON_ATTIVO');

SELECT * FROM finish();
ROLLBACK;
