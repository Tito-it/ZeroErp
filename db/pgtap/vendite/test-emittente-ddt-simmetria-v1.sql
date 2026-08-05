-- ============================================================
-- test-emittente-ddt-simmetria-v1.sql
-- Copertura: brief-db emittente DDT legato allo user + etichetta soggetto
-- ------------------------------------------------------------
-- ⚠️ Rinominato il 2026-08-03: l'alias era `emittente_fiscale_descrizione`,
--    nome che rimandava a `emittenti_fiscali.descrizione` — colonna droppata
--    il 2026-08-02. Il contenuto non e' mai cambiato in questa passata: e'
--    la ragione sociale del soggetto emittente da quando il COALESCE e'
--    caduto. Changeset `20260803-01` (ALTER VIEW ... RENAME COLUMN).
-- Indice test (1..12):
--  1-5) le 5 viste lista espongono emittente_ragione_sociale
--  6) trigger trg_ddt_a10_default_emittente_ins presente su vendite.ddt
--  7) trigger trg_ddt_z10_guard_emittente_ba_ins_upd presente su vendite.ddt
--  8) trigger guard_emittente_ba presente su vendite.preventivi
--  9) trigger guard_emittente_ba presente su vendite.offerte_commerciali
-- 10) firing order: default_emittente PRIMA di normalize (nome ordina prima)
-- 11) firing order: guard_emittente_ba DOPO normalize (nome ordina dopo)
-- 12) seed: le 5 colonne "Emittente" bindano campo_sorgente=emittente_ragione_sociale
-- ============================================================
BEGIN;
-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- 1-5) colonna emittente_ragione_sociale nelle 5 viste lista.
SELECT has_column('vendite', 'vw_ddt_lista',                 'emittente_ragione_sociale', '1) vw_ddt_lista.emittente_ragione_sociale');
SELECT has_column('vendite', 'vw_ordini_lista',              'emittente_ragione_sociale', '2) vw_ordini_lista.emittente_ragione_sociale');
SELECT has_column('vendite', 'vw_preventivi_lista',          'emittente_ragione_sociale', '3) vw_preventivi_lista.emittente_ragione_sociale');
SELECT has_column('vendite', 'vw_offerte_commerciali_lista', 'emittente_ragione_sociale', '4) vw_offerte_commerciali_lista.emittente_ragione_sociale');
SELECT has_column('vendite', 'vw_contratti_lista',           'emittente_ragione_sociale', '5) vw_contratti_lista.emittente_ragione_sociale');

-- 6-9) trigger presenti.
SELECT has_trigger('vendite', 'ddt',                 'trg_ddt_a10_default_emittente_ins',                     '6) trg_ddt_a10_default_emittente_ins');
SELECT has_trigger('vendite', 'ddt',                 'trg_ddt_z10_guard_emittente_ba_ins_upd',                '7) trg_ddt_z10_guard_emittente_ba_ins_upd');
SELECT has_trigger('vendite', 'preventivi',          'trg_preventivi_a10_guard_emittente_ba_ins_upd',         '8) trg_preventivi_a10_guard_emittente_ba_ins_upd');
SELECT has_trigger('vendite', 'offerte_commerciali', 'trg_offerte_commerciali_a10_guard_emittente_ba_ins_upd', '9) trg_offerte_commerciali_a10_guard_emittente_ba_ins_upd');

-- 10) Firing order: PostgreSQL esegue i trigger stesso timing/evento in
--     ordine alfabetico di nome. default_emittente deve firare PRIMA di
--     normalize (per non sovrascrivere l'ereditarieta'/fallback del normalize).
SELECT ok(
  'trg_ddt_a10_default_emittente_ins' < 'trg_ddt_normalize_ins_upd',
  '10) default_emittente ordina prima di normalize'
);

-- 11) guard_emittente_ba deve firare DOPO normalize (controlla i valori
--     finali di BA/emittente risolti dal normalize).
SELECT ok(
  'trg_ddt_z10_guard_emittente_ba_ins_upd' > 'trg_ddt_normalize_ins_upd',
  '11) guard_emittente_ba ordina dopo normalize'
);

-- 12) Seed: le 5 colonne "Emittente" (una per lista documento) ora bindano
--     la descrizione, non il codice tecnico.
--     ⚠️ 2026-08-01: due chiavi aggiornate. `contratti.col_emittente` e
--     `preventivi.col_emittente` sono diventate `vendite.contratti.*` e
--     `vendite.preventivi.*` con la normalizzazione delle chiavi i18n del
--     cantiere liste/PrimeVue (commit 0c32ea34c, piano-migrazione-primevue-5
--     §9 «80 su 80»). Il test contava 3 su 5 e falliva su una rinomina, non
--     su una regressione del binding.
SELECT is(
  (SELECT count(*)::int
     FROM ui.lista_colonna
    WHERE etichetta_i18n_key IN (
            'vendite.contratti.col_emittente','vendite.preventivi.col_emittente',
            'vendite.offerte.col_emittente','vendite.ordini.col_emittente',
            'vendite.ddt.col_emittente')
      AND campo_sorgente = 'emittente_ragione_sociale'),
  5, '12) le 5 colonne Emittente bindano emittente_ragione_sociale'
);

SELECT * FROM finish();
ROLLBACK;
