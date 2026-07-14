-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: read-side DDT (brief §13)
--   vendite.vw_ddt_lista + script.fn_available_actions_ddt + seed lista ui
-- ------------------------------------------------------------
-- Indice test (1..15):
--  1) vista vendite.vw_ddt_lista presente
--  2) funzione script.fn_available_actions_ddt presente
--  3) ui.lista_definizione 'vendite.ddt' -> vw_ddt_lista
--  4) ui.lista_colonna: colonne DDT seedate (>= 15)
--  5) riferimenti minimi disponibili
--  6) vw_ddt_lista: DDT presente in stato DRAFT
--  7) vw_ddt_lista: destinatario_denominazione valorizzato
--  8) vw_ddt_lista: sorgente ORDINE_VENDITA + ordine_origine_numero corretto
--  9) fn_available_actions_ddt DRAFT: azioni emetti + annulla presenti
-- 10) fn_available_actions_ddt DRAFT: can_edit_testata=true, stato_codice=DRAFT
-- 11) emissione DRAFT->EMESSO consentita
-- 12) fn_available_actions_ddt EMESSO: spedisci presente, emetti assente
-- 13) fn_available_actions_ddt EMESSO: can_edit_testata=false
-- 14) vw_ddt_lista: numero valorizzato dopo EMESSO
-- 15) fn_available_actions_ddt su DDT inesistente -> NULL
-- ------------------------------------------------------------

BEGIN;
SELECT plan(15);

-- ============================================================
-- 1-2) Oggetti presenti
-- ============================================================
SELECT ok(
  EXISTS (SELECT 1 FROM pg_views WHERE schemaname='vendite' AND viewname='vw_ddt_lista'),
  '1) vista vendite.vw_ddt_lista presente'
);
SELECT ok(
  EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
           WHERE n.nspname='script' AND p.proname='fn_available_actions_ddt'),
  '2) funzione script.fn_available_actions_ddt presente'
);

-- ============================================================
-- 3-4) Seed lista ui
-- ============================================================
SELECT is(
  (SELECT vista_sql FROM ui.lista_definizione WHERE codice='vendite.ddt'),
  'vw_ddt_lista', '3) ui.lista_definizione vendite.ddt -> vw_ddt_lista'
);
SELECT cmp_ok(
  (SELECT count(*)::int FROM ui.lista_colonna
    WHERE lista_id = (SELECT id FROM ui.lista_definizione WHERE codice='vendite.ddt')),
  '>=', 15, '4) ui.lista_colonna: colonne DDT seedate (>=15)'
);

-- ============================================================
-- Riferimenti + fixture ordine (per generare un DDT reale)
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1)                       AS billing_account_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id LIMIT 1) AS soggetto_ruolo_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND COALESCE(a.is_composito,FALSE) IS FALSE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1) AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno='CONFERMATO' AND s.attivo IS TRUE LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ddt s
    WHERE s.codice_interno='EMESSO' AND s.attivo IS TRUE LIMIT 1) AS stato_ddt_emesso_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND soggetto_ruolo_id IS NOT NULL
      AND articolo_id IS NOT NULL AND iva_id IS NOT NULL
      AND emittente_fiscale_id IS NOT NULL AND stato_ord_conf_id IS NOT NULL
   FROM tmp_refs),
  '5) riferimenti minimi disponibili'
);

CREATE TEMP TABLE tmp_ord AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id,
         r.valuta_id, DATE '2026-07-01', 'SPEDITO', r.emittente_fiscale_id, false,
         jsonb_build_object('test_scope','pgtap_ddt_readside')
  FROM tmp_refs r
  RETURNING id, uid, numero)
SELECT * FROM ins;

INSERT INTO vendite.ordini_righe (
  ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'Riga read-side',
       10.000000, 10.000000, 25.000000, r.iva_id, true, false,
       jsonb_build_object('test_scope','pgtap_ddt_readside')
FROM tmp_ord o, tmp_refs r;

CREATE TEMP TABLE tmp_ddt AS
SELECT vendite.fn_genera_ddt_da_ordine((SELECT id FROM tmp_ord)) AS ddt_id;

-- ============================================================
-- 6-8) vw_ddt_lista
-- ============================================================
SELECT is(
  (SELECT stato_codice_interno FROM vendite.vw_ddt_lista WHERE id=(SELECT ddt_id FROM tmp_ddt)),
  'DRAFT', '6) vw_ddt_lista: DDT in stato DRAFT'
);
SELECT ok(
  (SELECT destinatario_denominazione IS NOT NULL
     FROM vendite.vw_ddt_lista WHERE id=(SELECT ddt_id FROM tmp_ddt)),
  '7) vw_ddt_lista: destinatario_denominazione valorizzato'
);
SELECT ok(
  (SELECT sorgente_codice_interno = 'ORDINE_VENDITA'
      AND ordine_origine_numero = (SELECT numero FROM tmp_ord)
     FROM vendite.vw_ddt_lista WHERE id=(SELECT ddt_id FROM tmp_ddt)),
  '8) vw_ddt_lista: sorgente ORDINE_VENDITA + ordine_origine_numero corretto'
);

-- ============================================================
-- 9-10) fn_available_actions_ddt in DRAFT
-- ============================================================
CREATE TEMP TABLE tmp_act_draft AS
SELECT script.fn_available_actions_ddt((SELECT ddt_id FROM tmp_ddt)) AS a;

SELECT ok(
  (SELECT (a->'available_actions') @> '[{"key":"emetti"}]'::jsonb
      AND (a->'available_actions') @> '[{"key":"annulla"}]'::jsonb
     FROM tmp_act_draft),
  '9) fn_available_actions_ddt DRAFT: azioni emetti + annulla presenti'
);
SELECT ok(
  (SELECT (a->>'can_edit_testata')::boolean IS TRUE
      AND a->>'stato_codice' = 'DRAFT'
     FROM tmp_act_draft),
  '10) fn_available_actions_ddt DRAFT: can_edit_testata=true, stato_codice=DRAFT'
);

-- ============================================================
-- 11) Emissione DRAFT->EMESSO
-- ============================================================
-- Setup guard indirizzi obbligatori (DDT): il CON e' obbligatorio
-- all'emissione (trg_ddt_a10_guard_indirizzi_obbligatori_upd).
INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
SELECT (SELECT ddt_id FROM tmp_ddt),
       (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'CON'),
       '{"display":"CON test"}'::jsonb
ON CONFLICT DO NOTHING;

SELECT lives_ok(
  format($q$UPDATE vendite.ddt SET stato_doc_ddt_id=
             (SELECT stato_ddt_emesso_id FROM tmp_refs) WHERE id=%s$q$,
         (SELECT ddt_id FROM tmp_ddt)),
  '11) emissione DRAFT->EMESSO consentita'
);

-- ============================================================
-- 12-14) Dopo EMESSO
-- ============================================================
CREATE TEMP TABLE tmp_act_emesso AS
SELECT script.fn_available_actions_ddt((SELECT ddt_id FROM tmp_ddt)) AS a;

SELECT ok(
  (SELECT (a->'available_actions') @> '[{"key":"spedisci"}]'::jsonb
      AND NOT ((a->'available_actions') @> '[{"key":"emetti"}]'::jsonb)
     FROM tmp_act_emesso),
  '12) fn_available_actions_ddt EMESSO: spedisci presente, emetti assente'
);
SELECT ok(
  (SELECT (a->>'can_edit_testata')::boolean IS FALSE FROM tmp_act_emesso),
  '13) fn_available_actions_ddt EMESSO: can_edit_testata=false'
);
SELECT ok(
  (SELECT numero IS NOT NULL AND btrim(numero) <> ''
     FROM vendite.vw_ddt_lista WHERE id=(SELECT ddt_id FROM tmp_ddt)),
  '14) vw_ddt_lista: numero valorizzato dopo EMESSO'
);

-- ============================================================
-- 15) DDT inesistente -> NULL
-- ============================================================
SELECT ok(
  script.fn_available_actions_ddt(999999999) IS NULL,
  '15) fn_available_actions_ddt su DDT inesistente -> NULL'
);

SELECT * FROM finish();
ROLLBACK;
