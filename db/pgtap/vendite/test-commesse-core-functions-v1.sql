-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: funzioni core commesse (changeset 20260224-10..14)
-- ------------------------------------------------------------
-- Indice test (1..21):
-- 1) fn_get_or_create_commessa presente
-- 2) fn_link_commessa_sorgente presente
-- 3) fn_upsert_commessa_attivita presente
-- 4) fn_emit_attivita_fatturabili_da_commessa presente
-- 5) fn_get_commessa_stato presente
-- 6) fn_link_commessa_sorgente valida input (commessa_id=0 -> errore)
-- 7) Riferimenti minimi disponibili
-- 8) Seed sorgente COMMESSA presente/attivo
-- 9) Commessa creata
-- 10) Link ROOT inserito
-- 11) Link ROOT idempotente (stesso id)
-- 12) Link ROOT mismatch bloccato
-- 13) Upsert commessa_attivita insert
-- 14) Upsert commessa_attivita update stesso segment_key
-- 15) Override documento su commessa_attivita (listino_versione_id + prezzo_bloccato)
-- 16) Emit dry-run con only_approved=true conta 1 candidato insert
-- 17) Emit reale inserisce 1 riga AF
-- 18) Rerun emit (stato_emissione riaperto) aggiorna riga AF esistente
-- 19) Rerun emit propaga aggiornamento prezzo_snapshot/prezzo_bloccato su AF
-- 20) Propagazione snapshot su AF (commessa/prezzo_bloccato/sorgente)
-- 21) fn_get_commessa_stato restituisce contatori coerenti
-- ------------------------------------------------------------

BEGIN;
SELECT plan(21);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_get_or_create_commessa'
  ),
  'fn_get_or_create_commessa presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_link_commessa_sorgente'
  ),
  'fn_link_commessa_sorgente presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_upsert_commessa_attivita'
  ),
  'fn_upsert_commessa_attivita presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_emit_attivita_fatturabili_da_commessa'
  ),
  'fn_emit_attivita_fatturabili_da_commessa presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_get_commessa_stato'
  ),
  'fn_get_commessa_stato presente'
);

SELECT throws_ok(
  $$ SELECT vendite.fn_link_commessa_sorgente(0, 1, 'X', NULL, '{}'::jsonb); $$,
  'P0001',
  NULL,
  'fn_link_commessa_sorgente valida input (commessa_id=0 -> errore)'
);

CREATE TEMP TABLE tmp_refs_commesse_core AS
SELECT
  (
    SELECT ba.id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS billing_account_id,
  (
    SELECT ba.utility_id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS utility_id,
  (
    SELECT ba.istanza_utility_id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS istanza_utility_id,
  (
    SELECT anagrafiche.fn_get_emittente_fiscale_id(ba.id)
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS emittente_soggetto_ruolo_id,
  (
    SELECT a.id
    FROM catalogo.articoli a
    WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST
    LIMIT 1
  ) AS articolo_id,
  (
    SELECT u.id
    FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE
    ORDER BY u.id
    LIMIT 1
  ) AS uom_id,
  (
    SELECT t.id
    FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE
    ORDER BY t.id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (
    SELECT v.id
    FROM config.valute v
    ORDER BY v.id
    LIMIT 1
  ) AS valuta_id,
  (
    SELECT s.id
    FROM config.sorgenti s
    WHERE s.codice = 'PREVENTIVO'
    LIMIT 1
  ) AS root_sorgente_tipo_id;

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
      AND root_sorgente_tipo_id IS NOT NULL
    FROM tmp_refs_commesse_core
  ),
  'Riferimenti minimi disponibili'
);

INSERT INTO config.sorgenti (
  codice_interno, codice, categoria, descrizione, attivo, target_table, key_selector, meta
)
VALUES (
  'COMMESSA', 'COMMESSA', 'DOCUMENTO', 'Commessa test pgtap', true,
  'vendite.commesse_attivita'::regclass, 'id',
  jsonb_build_object('idempotency_key','segment_key')
)
ON CONFLICT (codice)
DO UPDATE
   SET attivo = true,
       target_table = EXCLUDED.target_table,
       key_selector = EXCLUDED.key_selector,
       data_update = now(),
       user_update = current_user;

SELECT ok(
  EXISTS (
    SELECT 1
    FROM config.sorgenti s
    WHERE s.codice = 'COMMESSA'
      AND s.attivo IS TRUE
  ),
  'Seed sorgente COMMESSA presente/attivo'
);

CREATE TEMP TABLE tmp_commessa_core AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_commesse_core),
  p_utility_id => (SELECT utility_id FROM tmp_refs_commesse_core),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_commesse_core),
  p_competenza_dal => DATE '2026-06-01',
  p_competenza_al => DATE '2026-06-30',
  p_meta => jsonb_build_object('test_scope', 'pgtap_commesse_core'),
  p_force_new => true
) AS commessa_id;

SELECT ok(
  (SELECT commessa_id IS NOT NULL FROM tmp_commessa_core),
  'Commessa creata'
);

CREATE TEMP TABLE tmp_link_core AS
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
  p_sorgente_tipo_id => (SELECT root_sorgente_tipo_id FROM tmp_refs_commesse_core),
  p_sorgente_uid => ('SRC-' || substr(md5(clock_timestamp()::text), 1, 12))::text,
  p_sorgente_riga => 1,
  p_meta => jsonb_build_object('test_scope', 'pgtap_commesse_core')
) AS link_id;

SELECT ok(
  (SELECT link_id IS NOT NULL FROM tmp_link_core),
  'Link ROOT inserito'
);

CREATE TEMP TABLE tmp_link_core_reuse AS
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
  p_sorgente_tipo_id => (SELECT root_sorgente_tipo_id FROM tmp_refs_commesse_core),
  p_sorgente_uid => (
    SELECT cs.sorgente_uid
    FROM vendite.commesse_sorgenti cs
    WHERE cs.id = (SELECT link_id FROM tmp_link_core)
  ),
  p_sorgente_riga => 1,
  p_meta => jsonb_build_object('idempotent', true)
) AS link_id;

SELECT is(
  (SELECT link_id::text FROM tmp_link_core_reuse),
  (SELECT link_id::text FROM tmp_link_core),
  'Link ROOT idempotente (stesso id)'
);

SELECT throws_ok(
  $$
    SELECT vendite.fn_link_commessa_sorgente(
      p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
      p_sorgente_tipo_id => (SELECT root_sorgente_tipo_id FROM tmp_refs_commesse_core),
      p_sorgente_uid => 'SRC-MISMATCH',
      p_sorgente_riga => 1,
      p_meta => '{}'::jsonb
    );
  $$,
  'P0001',
  NULL,
  'Link ROOT mismatch bloccato'
);

CREATE TEMP TABLE tmp_upsert_core AS
SELECT vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
  p_segment_key => ('SEG-' || substr(md5(clock_timestamp()::text), 1, 18))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_commesse_core),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_commesse_core),
  p_data_attivita => DATE '2026-06-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_commesse_core),
  p_quantita => 2.000000,
  p_competenza_mese => DATE '2026-06-01',
  p_competenza_dal => DATE '2026-06-01',
  p_competenza_al => DATE '2026-06-30',
  p_prezzo_snapshot => 22.1000000000,
  p_qta_operativa => 2.000000,
  p_uom_operativa_id => (SELECT uom_id FROM tmp_refs_commesse_core),
  p_factor_to_base => 1,
  p_posticipa_al => NULL,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_commesse_core),
  p_valuta_id => (SELECT valuta_id FROM tmp_refs_commesse_core),
  p_area_geografica_id => NULL,
  p_listino_versione_id => NULL,
  p_prezzo_bloccato => true,
  p_pricing_mode => 'FIXED',
  p_prezzo_da_riallineare => false,
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (SELECT root_sorgente_tipo_id FROM tmp_refs_commesse_core),
  p_sorgente_uid => ('EXT-' || substr(md5(clock_timestamp()::text), 1, 10))::text,
  p_tipo_movimento => 'NORMALE',
  p_tipo_consumo => 'ACCONTO',
  p_meta => jsonb_build_object('case', 'UPSERT_INSERT')
) AS commessa_attivita_id;

SELECT ok(
  (SELECT commessa_attivita_id IS NOT NULL FROM tmp_upsert_core),
  'Upsert commessa_attivita insert'
);

CREATE TEMP TABLE tmp_upsert_core_update AS
WITH codice AS (
  SELECT ('LRC_CORE_' || substr(md5(clock_timestamp()::text), 1, 12))::varchar(64) AS code
),
lst AS (
  INSERT INTO vendite.listini (codice, descrizione, dominio)
  SELECT c.code, 'listino test override documento', 'COMMERCIO'
  FROM codice c
  RETURNING id
),
lst_v AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, priorita, stato)
  SELECT l.id, 'V1', DATE '2026-01-01', DATE '2026-12-31', 10, 'ATTIVA'
  FROM lst l
  RETURNING id
)
SELECT vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
  p_segment_key => (
    SELECT ca.segment_key
    FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_upsert_core)
  ),
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_commesse_core),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_commesse_core),
  p_data_attivita => DATE '2026-06-16',
  p_uom_id => (SELECT uom_id FROM tmp_refs_commesse_core),
  p_quantita => 3.000000,
  p_competenza_mese => DATE '2026-06-01',
  p_competenza_dal => DATE '2026-06-01',
  p_competenza_al => DATE '2026-06-30',
  p_prezzo_snapshot => 22.1000000000,
  p_qta_operativa => 3.000000,
  p_uom_operativa_id => (SELECT uom_id FROM tmp_refs_commesse_core),
  p_factor_to_base => 1,
  p_posticipa_al => NULL,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_commesse_core),
  p_valuta_id => (SELECT valuta_id FROM tmp_refs_commesse_core),
  p_area_geografica_id => NULL,
  p_listino_versione_id => (SELECT id FROM lst_v),
  p_prezzo_bloccato => true,
  p_pricing_mode => 'FIXED',
  p_prezzo_da_riallineare => false,
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (SELECT root_sorgente_tipo_id FROM tmp_refs_commesse_core),
  p_sorgente_uid => (
    SELECT ca.sorgente_uid
    FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_upsert_core)
  ),
  p_tipo_movimento => 'NORMALE',
  p_tipo_consumo => 'ACCONTO',
  p_meta => jsonb_build_object('case', 'UPSERT_UPDATE')
) AS commessa_attivita_id;

SELECT is(
  (SELECT commessa_attivita_id::text FROM tmp_upsert_core_update),
  (SELECT commessa_attivita_id::text FROM tmp_upsert_core),
  'Upsert commessa_attivita update stesso segment_key'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_upsert_core)
      AND ca.prezzo_bloccato IS TRUE
      AND ca.listino_versione_id IS NOT NULL
  ),
  'Override documento su commessa_attivita (listino_versione_id + prezzo_bloccato)'
);

CREATE TEMP TABLE tmp_emit_dry_core AS
SELECT *
FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
  p_lotto_attivita_id => NULL,
  p_only_approved => true,
  p_dry_run => true
);

SELECT ok(
  (
    SELECT total_candidate = 1
       AND inserted_rows = 1
       AND updated_rows = 0
    FROM tmp_emit_dry_core
  ),
  'Emit dry-run con only_approved=true conta 1 candidato insert'
);

CREATE TEMP TABLE tmp_emit_real_core AS
SELECT *
FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
  p_lotto_attivita_id => NULL,
  p_only_approved => true,
  p_dry_run => false
);

SELECT ok(
  (
    SELECT total_candidate = 1
       AND inserted_rows = 1
       AND updated_rows = 0
    FROM tmp_emit_real_core
  ),
  'Emit reale inserisce 1 riga AF'
);

UPDATE vendite.commesse_attivita
SET stato_emissione = 'NON_EMESSA'
WHERE id = (SELECT commessa_attivita_id FROM tmp_upsert_core);

SELECT vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
  p_segment_key => (
    SELECT ca.segment_key
    FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_upsert_core)
  ),
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_commesse_core),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_commesse_core),
  p_data_attivita => DATE '2026-06-16',
  p_uom_id => (SELECT uom_id FROM tmp_refs_commesse_core),
  p_quantita => 3.000000,
  p_competenza_mese => DATE '2026-06-01',
  p_competenza_dal => DATE '2026-06-01',
  p_competenza_al => DATE '2026-06-30',
  p_prezzo_snapshot => 23.1000000000,
  p_qta_operativa => 3.000000,
  p_uom_operativa_id => (SELECT uom_id FROM tmp_refs_commesse_core),
  p_factor_to_base => 1,
  p_posticipa_al => NULL,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_commesse_core),
  p_valuta_id => (SELECT valuta_id FROM tmp_refs_commesse_core),
  p_area_geografica_id => NULL,
  p_listino_versione_id => NULL,
  p_prezzo_bloccato => false,
  p_pricing_mode => 'FIXED',
  p_prezzo_da_riallineare => false,
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (SELECT root_sorgente_tipo_id FROM tmp_refs_commesse_core),
  p_sorgente_uid => (
    SELECT ca.sorgente_uid
    FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_upsert_core)
  ),
  p_tipo_movimento => 'NORMALE',
  p_tipo_consumo => 'ACCONTO',
  p_meta => jsonb_build_object('case', 'UPSERT_PRICE_UPDATE')
);

CREATE TEMP TABLE tmp_emit_rerun_core AS
SELECT *
FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
  p_lotto_attivita_id => NULL,
  p_only_approved => true,
  p_dry_run => false
);

SELECT ok(
  (
    SELECT total_candidate = 1
       AND inserted_rows = 0
       AND updated_rows = 1
    FROM tmp_emit_rerun_core
  ),
  'Rerun emit (stato_emissione riaperto) aggiorna riga AF esistente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili af
    WHERE af.commessa_id = (SELECT commessa_id FROM tmp_commessa_core)
      AND af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_upsert_core)
      AND af.prezzo_unitario = 23.1000000000
      AND af.prezzo_bloccato IS FALSE
  ),
  'Rerun emit propaga aggiornamento prezzo_snapshot/prezzo_bloccato su AF'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili af
    JOIN config.sorgenti s
      ON s.id = af.sorgente_tipo_id
    WHERE af.commessa_id = (SELECT commessa_id FROM tmp_commessa_core)
      AND af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_upsert_core)
      AND af.prezzo_bloccato IS FALSE
      AND s.codice = 'COMMESSA'
  ),
  'Propagazione snapshot su AF (commessa/prezzo_bloccato/sorgente)'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_get_commessa_stato((SELECT commessa_id FROM tmp_commessa_core)) x
    WHERE x.total_attivita >= 1
      AND x.total_approvate >= 1
      AND x.total_emesse >= 1
  ),
  'fn_get_commessa_stato restituisce contatori coerenti'
);

SELECT * FROM finish();
ROLLBACK;
