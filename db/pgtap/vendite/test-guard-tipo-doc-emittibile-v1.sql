-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: guard tipo_doc emittibile + normalize/no-regressione su
--       vendite.commesse_attivita (brief-db-guard-tipo-doc-attivita)
--       Deliverable DB 20260619-03 (fn_upsert) e 20260619-05 (guard).
-- ------------------------------------------------------------
-- Indice test (1..11):
--  1) funzione trgfn_commesse_attivita_guard_tipo_doc_emittibile presente
--  2) trigger guard tipo_doc presente su commesse_attivita
--  3) codice errore E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO (497) registrato
--  4) riferimenti minimi disponibili
--  5) commessa creata + link sorgente ROOT
--  6) normalize: tipo_doc risolto da config.sorgenti quando il param e' NULL
--  7) no-regressione: re-push con default sorgente NULL non azzera il tipo_doc
--  8) riga BOZZA con tipo_doc NULL ammessa (l'invariante vincola solo emittibile)
--  9) guard: approvazione di riga con tipo_doc NULL bloccata (P0001)
-- 10) guard: approvazione di riga con tipo_doc valorizzato consentita
-- 11) guard: azzeramento tipo_doc su riga emittibile bloccato (P0001)
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(11);

-- 1) funzione guard presente
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'trgfn_commesse_attivita_guard_tipo_doc_emittibile'
  ),
  'funzione trgfn_commesse_attivita_guard_tipo_doc_emittibile presente'
);

-- 2) trigger guard presente
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite'
      AND c.relname = 'commesse_attivita'
      AND t.tgname = 'trg_commesse_attivita_a10_guard_tipo_doc_emittibile_ins_upd'
      AND NOT t.tgisinternal
  ),
  'trigger guard tipo_doc emittibile presente su commesse_attivita'
);

-- 3) codice errore registrato
SELECT ok(
  EXISTS (
    SELECT 1 FROM config.messaggi_errore
    WHERE codice = 'E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO'
      AND id = 497
  ),
  'codice errore E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO (497) registrato'
);

-- ============================================================
-- SETUP: riferimenti minimi (pattern test-attivita-guardrail-commessa-v1)
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): il cliente e l'articolo si COSTRUISCONO.
--   Prima si pescavano il primo BA con emittente e l'ultimo articolo attivo, e
--   su un database ricostruito da zero non c'erano: ora il BA viene da
--   dbops.fn_pgtap_crea_cliente_ba (legato all'azienda di chi agisce, emittente
--   derivato dal BA) e l'articolo da dbops.fn_pgtap_crea_articolo (servizio,
--   non gestito a magazzino). Restano letture di catalogo di SEED:
--   unita_misura, tipi_doc_fiscale, valute, sorgenti.
CREATE TEMP TABLE tmp_cli_tde AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('guard tipo doc emittibile');

CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_tde) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_tde) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_cli_tde) AS istanza_utility_id,
  (SELECT anagrafiche.fn_get_emittente_fiscale_id(billing_account_id) FROM tmp_cli_tde) AS emittente_soggetto_ruolo_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-TDE-ART', false) AS articolo_id,
  (SELECT id FROM catalogo.unita_misura WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS uom_id,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id,
  (SELECT id FROM config.sorgenti WHERE codice_interno = 'COMMESSA' LIMIT 1) AS src_preventivo_id;

SELECT ok(
  (
    SELECT billing_account_id IS NOT NULL
       AND utility_id IS NOT NULL
       AND istanza_utility_id IS NOT NULL
       AND emittente_soggetto_ruolo_id IS NOT NULL
       AND articolo_id IS NOT NULL
       AND uom_id IS NOT NULL
       AND tipo_doc_fiscale_id IS NOT NULL
       AND valuta_id IS NOT NULL
       AND src_preventivo_id IS NOT NULL
    FROM tmp_refs
  ),
  'riferimenti minimi disponibili'
);

-- Salva il valore originale del default tipo_doc sulla sorgente PREVENTIVO
-- (manipolato e ripristinato entro la transazione, comunque rollback finale).
CREATE TEMP TABLE tmp_src_orig AS
SELECT tipo_doc_fiscale_id AS orig_tipo_doc
FROM config.sorgenti WHERE codice_interno = 'COMMESSA';

-- Chiavi segment riusate tra i test (generate una sola volta).
CREATE TEMP TABLE tmp_seg AS
SELECT ('SEG-TDF1-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar AS seg1,
       ('SEG-TDF2-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar AS seg2;

-- Commessa di test isolata + link sorgente ROOT.
CREATE TEMP TABLE tmp_commessa AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_guard_tipo_doc'),
  p_force_new => true
) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa),
  p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_refs),
  -- ROOT: sorgente COMMESSA (key_selector='id') con uid = id della commessa
  -- stessa: esiste per costruzione -> passa formato ed esistenza del guard
  -- sorgente polimorfa. rev 2026-07-27 (bonifica).
  p_sorgente_uid => (SELECT commessa_id FROM tmp_commessa)::text,
  p_sorgente_riga => 1,
  p_meta => '{}'::jsonb
);

SELECT ok(
  (SELECT commessa_id IS NOT NULL FROM tmp_commessa),
  'commessa creata + link sorgente ROOT'
);

-- ============================================================
-- 6) NORMALIZE: default sorgente valorizzato -> risolto su param NULL
-- ============================================================
UPDATE config.sorgenti
   SET tipo_doc_fiscale_id = (SELECT tipo_doc_fiscale_id FROM tmp_refs)
 WHERE codice_interno = 'COMMESSA';

CREATE TEMP TABLE tmp_ca1 AS
SELECT r.attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa),
  p_segment_key => (SELECT seg1 FROM tmp_seg),
  p_articolo_id => (SELECT articolo_id FROM tmp_refs),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs),
  p_quantita => 1.000000,
  p_competenza_mese => DATE '2026-07-01',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_prezzo_snapshot => 10.0000000000,
  p_prezzo_base_snapshot => NULL,
  p_origine_prezzo => NULL,
  p_tipo_variazione_applicata => NULL,
  p_valore_variazione_applicata => NULL,
  p_promo_id => NULL,
  p_contratto_id => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot => NULL,
  p_qta_operativa => 1.000000,
  p_uom_operativa_id => (SELECT uom_id FROM tmp_refs),
  p_factor_to_base => 1,
  p_posticipa_al => NULL,
  p_tipo_doc_fiscale_id => NULL,        -- param NULL: deve risolvere da sorgente
  p_valuta_id => (SELECT valuta_id FROM tmp_refs),
  p_area_geografica_id => NULL,
  p_listino_versione_id => NULL,
  p_prezzo_bloccato => true,
  p_pricing_mode => 'FIXED',
  p_prezzo_da_riallineare => false,
  p_stato_approvazione => 'BOZZA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_refs),
  p_sorgente_uid => ('EXT-TDF1-' || substr(md5(clock_timestamp()::text), 1, 10))::text,
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'NORMALIZE')
) r;

SELECT is(
  (SELECT ca.tipo_doc_fiscale_id
     FROM vendite.commesse_attivita ca
     WHERE ca.id = (SELECT attivita_id FROM tmp_ca1)),
  (SELECT tipo_doc_fiscale_id FROM tmp_refs),
  'normalize: tipo_doc risolto da config.sorgenti quando il param e'' NULL'
);

-- ============================================================
-- 7) NO-REGRESSIONE: default sorgente azzerato, re-push non perde il valore
-- ============================================================
UPDATE config.sorgenti
   SET tipo_doc_fiscale_id = NULL
 WHERE codice_interno = 'COMMESSA';

-- Re-push dello stesso segment con param NULL e sorgente senza default:
-- il COALESCE su ON CONFLICT deve conservare il valore gia' risolto.
SELECT 1 FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa),
  p_segment_key => (SELECT seg1 FROM tmp_seg),
  p_articolo_id => (SELECT articolo_id FROM tmp_refs),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs),
  p_quantita => 2.000000,
  p_competenza_mese => DATE '2026-07-01',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_prezzo_snapshot => 10.0000000000,
  p_prezzo_base_snapshot => NULL,
  p_origine_prezzo => NULL,
  p_tipo_variazione_applicata => NULL,
  p_valore_variazione_applicata => NULL,
  p_promo_id => NULL,
  p_contratto_id => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot => NULL,
  p_qta_operativa => 2.000000,
  p_uom_operativa_id => (SELECT uom_id FROM tmp_refs),
  p_factor_to_base => 1,
  p_posticipa_al => NULL,
  p_tipo_doc_fiscale_id => NULL,        -- param NULL + sorgente senza default
  p_valuta_id => (SELECT valuta_id FROM tmp_refs),
  p_area_geografica_id => NULL,
  p_listino_versione_id => NULL,
  p_prezzo_bloccato => true,
  p_pricing_mode => 'FIXED',
  p_prezzo_da_riallineare => false,
  p_stato_approvazione => 'BOZZA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_refs),
  p_sorgente_uid => ('EXT-TDF1-' || substr(md5(clock_timestamp()::text), 1, 10))::text,
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'NO_REGRESSIONE')
);

SELECT is(
  (SELECT ca.tipo_doc_fiscale_id
     FROM vendite.commesse_attivita ca
     WHERE ca.id = (SELECT attivita_id FROM tmp_ca1)),
  (SELECT tipo_doc_fiscale_id FROM tmp_refs),
  'no-regressione: re-push con default sorgente NULL non azzera il tipo_doc'
);

-- ============================================================
-- 8) BOZZA + tipo_doc NULL ammessa (sorgente senza default, stato non emittibile)
-- ============================================================
CREATE TEMP TABLE tmp_ca2 AS
SELECT r.attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa),
  p_segment_key => (SELECT seg2 FROM tmp_seg),
  p_articolo_id => (SELECT articolo_id FROM tmp_refs),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs),
  p_data_attivita => DATE '2026-07-16',
  p_uom_id => (SELECT uom_id FROM tmp_refs),
  p_quantita => 1.000000,
  p_competenza_mese => DATE '2026-07-01',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_prezzo_snapshot => 10.0000000000,
  p_prezzo_base_snapshot => NULL,
  p_origine_prezzo => NULL,
  p_tipo_variazione_applicata => NULL,
  p_valore_variazione_applicata => NULL,
  p_promo_id => NULL,
  p_contratto_id => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot => NULL,
  p_qta_operativa => 1.000000,
  p_uom_operativa_id => (SELECT uom_id FROM tmp_refs),
  p_factor_to_base => 1,
  p_posticipa_al => NULL,
  p_tipo_doc_fiscale_id => NULL,
  p_valuta_id => (SELECT valuta_id FROM tmp_refs),
  p_area_geografica_id => NULL,
  p_listino_versione_id => NULL,
  p_prezzo_bloccato => true,
  p_pricing_mode => 'FIXED',
  p_prezzo_da_riallineare => false,
  p_stato_approvazione => 'BOZZA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_refs),
  p_sorgente_uid => ('EXT-TDF2-' || substr(md5(clock_timestamp()::text), 1, 10))::text,
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'BOZZA_NULL')
) r;

SELECT ok(
  EXISTS (
    SELECT 1 FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT attivita_id FROM tmp_ca2)
      AND ca.stato_approvazione = 'BOZZA'
      AND ca.tipo_doc_fiscale_id IS NULL
  ),
  'riga BOZZA con tipo_doc NULL ammessa'
);

-- ============================================================
-- 9) GUARD: approvazione di riga con tipo_doc NULL bloccata
-- ============================================================
SELECT throws_ok(
  $$
    UPDATE vendite.commesse_attivita
       SET stato_approvazione = 'APPROVATA'
     WHERE id = (SELECT attivita_id FROM tmp_ca2);
  $$,
  'P0001',
  NULL,
  'guard: approvazione di riga con tipo_doc NULL bloccata'
);

-- ============================================================
-- 10) GUARD: approvazione di riga con tipo_doc valorizzato consentita
--     (tmp_ca1 ha tipo_doc valorizzato dal normalize)
-- ============================================================
SELECT lives_ok(
  $$
    UPDATE vendite.commesse_attivita
       SET stato_approvazione = 'APPROVATA'
     WHERE id = (SELECT attivita_id FROM tmp_ca1);
  $$,
  'guard: approvazione di riga con tipo_doc valorizzato consentita'
);

-- ============================================================
-- 11) GUARD: azzeramento tipo_doc su riga emittibile bloccato
--     (tmp_ca1 ora APPROVATA + NON_EMESSA)
-- ============================================================
SELECT throws_ok(
  $$
    UPDATE vendite.commesse_attivita
       SET tipo_doc_fiscale_id = NULL
     WHERE id = (SELECT attivita_id FROM tmp_ca1);
  $$,
  'P0001',
  NULL,
  'guard: azzeramento tipo_doc su riga emittibile bloccato'
);

SELECT * FROM finish();
ROLLBACK;
