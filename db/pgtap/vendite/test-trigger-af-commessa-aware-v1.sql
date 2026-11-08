-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: trigger attivita_fatturabili commessa-aware
-- (changeset 20260227-01, 20260227-02)
-- ------------------------------------------------------------
-- Indice test (1..8):
--  1) trgfn_attivita_fatturabili_normalize presente
--  2) trgfn_attivita_fatturabili_guard_ba_coerenza presente
--  3) Commessa di test creata
--  4) Attivita` inserita nella commessa
--  5) fn_emit produce righe AF con commessa_attivita_id NOT NULL
--  6) Normalize: competenza_mese AF corretta (non sovrascritta)
--  7) Normalize: tipo_doc_fiscale_id risolto anche su riga da commessa
--  8) Normalize: valuta_id risolta anche su riga da commessa
-- rev 2026-10-26 (brief-modello-documento-vendita §14, giro 10): la porta sulla
--   commessa rifiuta l'UPDATE diretto dello stato; la commessa va a
--   PRONTA_FATTURAZIONE con dbops.fn_pgtap_porta_a_stato (il verbo, l'azione la
--   concede la fixture). Attese invariate.
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

SELECT plan(8);

-- ============================================================
-- TRIGGER PRESENTI
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'trgfn_attivita_fatturabili_normalize'
  ),
  'trgfn_attivita_fatturabili_normalize presente'
);

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'trgfn_attivita_fatturabili_guard_ba_coerenza'
  ),
  'trgfn_attivita_fatturabili_guard_ba_coerenza presente'
);

-- ============================================================
-- SETUP DATI TEST
-- ============================================================

-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba, BA legato all'azienda di chi agisce):
--   prima il BA si pescava con LIMIT 1, e da zero non c'era. La commessa resta
--   aperta dalla madre, il preventivo resta scritto qui.
CREATE TEMP TABLE tmp_cli_tca AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('trigger af commessa aware');

CREATE TEMP TABLE tmp_refs_tca AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_tca) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_tca) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_cli_tca) AS istanza_utility_id,
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
  ) AS uom_id;

-- Crea commessa di test
CREATE TEMP TABLE tmp_commessa_tca AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_tca),
  p_utility_id => (SELECT utility_id FROM tmp_refs_tca),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-09-01',
  p_competenza_al => DATE '2026-09-30',
  p_meta => jsonb_build_object('test_scope', 'pgtap_trigger_commessa_aware'),
  p_force_new => true
) AS commessa_id;

SELECT ok(
  (SELECT commessa_id IS NOT NULL FROM tmp_commessa_tca),
  'Commessa di test creata'
);

-- Preventivo VERO come sorgente della riga (rev 2026-10-13): basta la testata
--   in bozza sullo stesso billing account. Prima la riga portava un token
--   inventato ('PGTAP-TCA-SRC-...'), che commesse_attivita accettava; dal
--   20261012-46 la madre aggancia il documento alla commessa con
--   fn_link_commessa_sorgente, che ne pretende formato (uuid, key_selector
--   'uid') ed esistenza. L'emittente e' quello del billing account: lo
--   pretendono il guard emittente/BA e l'omogeneita' del link.
CREATE TEMP TABLE tmp_prev_tca AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id,
    emittente_fiscale_id, meta)
  SELECT r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2026-09-01', DATE '2026-09-30',
         (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1),
         (SELECT s.id FROM config.stati_doc_preventivi s
           WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE LIMIT 1),
         (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
           WHERE ef.soggetto_ruolo_id = anagrafiche.fn_get_emittente_fiscale_id(r.billing_account_id)),
         jsonb_build_object('test_scope', 'pgtap_trigger_commessa_aware')
  FROM tmp_refs_tca r
  RETURNING id, uid)
SELECT * FROM ins;

-- Inserisci attivita` con competenza_mese specifica (senza tipo_doc e valuta su CA)
CREATE TEMP TABLE tmp_att_tca AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_tca),
  p_segment_key => ((SELECT script.fn_segment_key(s.codice_interno, d.documento_uid::text) FROM config.sorgenti s, script.fn_sorgente_documento_da_chiave(s.id, ((SELECT uid::text FROM tmp_prev_tca))::text) d WHERE s.id = (
    SELECT s.id FROM config.sorgenti s
    WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE
    LIMIT 1
  )) || ':' || ('SEG-TCA-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar)::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_tca),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_tca),
  p_data_attivita => DATE '2026-09-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_tca),
  p_quantita => 1.000000,
  p_competenza_mese => DATE '2026-09-01',
  p_competenza_dal => DATE '2026-09-01',
  p_competenza_al => DATE '2026-09-30',
  p_prezzo_snapshot => 50.0000000000,
  p_prezzo_base_snapshot => NULL,
  p_origine_prezzo => NULL,
  p_tipo_variazione_applicata => NULL,
  p_valore_variazione_applicata => NULL,
  p_promo_id => NULL,
  p_contratto_id => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot => NULL,
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (
    SELECT s.id FROM config.sorgenti s
    WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE
    LIMIT 1
  ),
  p_sorgente_chiave => (SELECT uid::text FROM tmp_prev_tca),
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'TCA_TRIGGER_TEST')
) r;

SELECT ok(
  (SELECT commessa_attivita_id IS NOT NULL FROM tmp_att_tca),
  'Attivita` inserita nella commessa'
);

-- Collega ROOT source (richiesto da fn_emit)
-- rev 2026-07-27 (bonifica): ROOT su sorgente COMMESSA (key_selector='id') con
-- uid = id della commessa stessa. Prima: sorgente PREVENTIVO (che vuole un
-- uuid) e chiave con prefisso 'PGTAP-TCA-' davanti all'id — illegale dal guard
-- del 2026-07-18 su entrambi i fronti (formato e tabella target).
-- Nota: la lookup era anche per `codice` (etichetta modificabile) invece che
-- per `codice_interno` (immutabile) — linee-guida-sql §6c/§6d.
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_tca),
  p_sorgente_tipo_id => (
    SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'COMMESSA' AND s.attivo IS TRUE
    LIMIT 1
  ),
  p_sorgente_chiave => (SELECT commessa_id FROM tmp_commessa_tca)::text
);

-- Porta commessa in stato PRONTA_FATTURAZIONE (emittibile=true)
SELECT dbops.fn_pgtap_porta_a_stato('vendite.commesse', (SELECT commessa_id FROM tmp_commessa_tca),
                                     'PRONTA_FATTURAZIONE');

-- Esegui emit: crea righe AF con commessa_attivita_id NOT NULL
CREATE TEMP TABLE tmp_emit_tca AS
SELECT *
FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_tca),
  p_only_approved => true,
  p_dry_run => false
);

-- ============================================================
-- TEST: emit ha prodotto righe AF
-- ============================================================

SELECT ok(
  (SELECT inserted_rows >= 1 FROM tmp_emit_tca),
  'fn_emit produce righe AF con commessa_attivita_id NOT NULL'
);

-- ============================================================
-- TEST: normalize non ha sovrascritto competenza_mese
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili af
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_att_tca)
      AND af.competenza_mese = DATE '2026-09-01'
  ),
  'Normalize: competenza_mese AF corretta (non sovrascritta)'
);

-- ============================================================
-- TEST: tipo_doc_fiscale_id risolto (CA non lo aveva)
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili af
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_att_tca)
      AND af.tipo_doc_fiscale_id IS NOT NULL
  ),
  'Normalize: tipo_doc_fiscale_id risolto anche su riga da commessa'
);

-- ============================================================
-- TEST: valuta_id risolta (CA non la aveva)
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili af
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_att_tca)
      AND af.valuta_id IS NOT NULL
  ),
  'Normalize: valuta_id risolta anche su riga da commessa'
);

SELECT * FROM finish();
ROLLBACK;
