-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_preventivo_ha_residuo_commessa (20260612-03) +
--       capability can_push_commessa simmetrica con reason
--       (script.fn_available_actions_preventivo, 20260612-04).
--       Brief: brief-db-smistamento-preventivi.md, Richiesta A.
--
-- Indice test (0..9):
--   0) Precondizioni (refs + nature)
--   1) Preventivo MISTO (servizio+merce, BA ok) -> residuo = true
--   2) Preventivo SOLO MERCE -> residuo = false
--   3) Preventivo con riga servizio ma SENZA billing account -> residuo = false (testata)
--   4) Guard: id invalido -> throws
--   5) available_actions MISTO: can_push_commessa = true, reason NULL
--   6) available_actions SOLO MERCE: can_push=false, reason PREVENTIVO_NESSUNA_RIGA_COMMESSA
--   7) available_actions SENZA BA: can_push=false, reason PREVENTIVO_SENZA_BILLING_ACCOUNT
--   8) Post-push (riga servizio EMESSA in commessa): residuo MISTO = false
--      (la merce residua non conta sul ramo commessa)
--   9) available_actions DRAFT: reason PREVENTIVO_NON_ACCETTATO
--  10) Post-push NON_EMESSA -> residuo = false (fix gate EVASO: la riga e'
--      esclusa appena instradata, non solo dopo fatturazione)
--  11) Post-push componente BoM (segment_key #CMP, NON_EMESSA) -> residuo = false
--      (match a prefisso §4: una riga composita viene esclusa)
--  12) Attivita ANNULLATA -> residuo = false (decisione: riga instradata, non
--      ri-pushabile; non riapre il preventivo)
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

SELECT plan(13);

-- ============================================================
-- 0) Riferimenti minimi + classificazione nature
-- ============================================================
CREATE TEMP TABLE tmp_rc_refs AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS billing_account_id,
  (SELECT ba.utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS utility_id,
  (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1 OFFSET 0) AS art_merce_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1 OFFSET 1) AS art_serv_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'ACCETTATO' AND s.attivo IS TRUE LIMIT 1) AS stato_accettato_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'DRAFT' AND s.attivo IS TRUE LIMIT 1) AS stato_draft_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE
    ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE
    ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT sc.id FROM vendite.stati_commessa sc WHERE sc.attivo IS TRUE
    ORDER BY sc.id LIMIT 1) AS stato_commessa_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'MERCE') AS natura_merce_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'SERVIZIO_UNA_TANTUM') AS natura_serv_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND art_merce_id IS NOT NULL
      AND art_serv_id IS NOT NULL AND stato_accettato_id IS NOT NULL
      AND natura_merce_id IS NOT NULL AND natura_serv_id IS NOT NULL
     FROM tmp_rc_refs),
  '0. Precondizioni soddisfatte'
);

-- Classifica gli articoli di test: merce -> ORDINE, servizio -> COMMESSA.
UPDATE catalogo.articoli SET natura_vendita_id = (SELECT natura_merce_id FROM tmp_rc_refs)
 WHERE id = (SELECT art_merce_id FROM tmp_rc_refs);
UPDATE catalogo.articoli SET natura_vendita_id = (SELECT natura_serv_id FROM tmp_rc_refs)
 WHERE id = (SELECT art_serv_id FROM tmp_rc_refs);

-- Preventivo MISTO ACCETTATO (BA ok): 1 riga servizio + 1 riga merce.
CREATE TEMP TABLE tmp_rc_misto AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-RC-MISTO', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.stato_accettato_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_residuo_commessa'), r.emittente_fiscale_id
    FROM tmp_rc_refs r
  RETURNING id, uid)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_rc_riga_serv AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 2.000000, 30.000000, r.iva_id, true
    FROM tmp_rc_misto p, tmp_rc_refs r
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
SELECT p.id, r.art_merce_id, 1.000000, 50.000000, r.iva_id, true
  FROM tmp_rc_misto p, tmp_rc_refs r;

-- Preventivo SOLO MERCE ACCETTATO (BA ok).
CREATE TEMP TABLE tmp_rc_merce AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-RC-MERCE', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.stato_accettato_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_residuo_commessa_merce'), r.emittente_fiscale_id
    FROM tmp_rc_refs r
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
SELECT p.id, r.art_merce_id, 1.000000, 50.000000, r.iva_id, true
  FROM tmp_rc_merce p, tmp_rc_refs r;

-- Preventivo ACCETTATO con riga servizio ma SENZA billing account.
CREATE TEMP TABLE tmp_rc_noba AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-RC-NOBA', 0, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.stato_accettato_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_residuo_commessa_noba'), r.emittente_fiscale_id
    FROM tmp_rc_refs r
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
SELECT p.id, r.art_serv_id, 1.000000, 20.000000, r.iva_id, true
  FROM tmp_rc_noba p, tmp_rc_refs r;

-- Preventivo DRAFT con riga servizio (per reason non_accettato).
CREATE TEMP TABLE tmp_rc_draft AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-RC-DRAFT', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.stato_draft_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_residuo_commessa_draft'), r.emittente_fiscale_id
    FROM tmp_rc_refs r
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
SELECT p.id, r.art_serv_id, 1.000000, 20.000000, r.iva_id, true
  FROM tmp_rc_draft p, tmp_rc_refs r;

-- ============================================================
-- 1) MISTO -> residuo = true
-- ============================================================
SELECT is(
  vendite.fn_preventivo_ha_residuo_commessa((SELECT id FROM tmp_rc_misto)),
  true,
  '1. Preventivo misto: residuo commessa = true'
);

-- ============================================================
-- 2) SOLO MERCE -> residuo = false
-- ============================================================
SELECT is(
  vendite.fn_preventivo_ha_residuo_commessa((SELECT id FROM tmp_rc_merce)),
  false,
  '2. Preventivo solo merce: residuo commessa = false'
);

-- ============================================================
-- 3) Riga servizio ma SENZA billing account -> false (testata)
-- ============================================================
SELECT is(
  vendite.fn_preventivo_ha_residuo_commessa((SELECT id FROM tmp_rc_noba)),
  false,
  '3. Testata incompleta (BA NULL): residuo commessa = false (il push non listerebbe nulla)'
);

-- ============================================================
-- 4) Guard: id invalido -> throws
-- ============================================================
SELECT throws_ok(
  'SELECT vendite.fn_preventivo_ha_residuo_commessa(-1)',
  NULL, NULL,
  '4. Guard: p_preventivo_id invalido rifiutato'
);

-- ============================================================
-- 5) available_actions MISTO: can_push = true, reason NULL
-- ============================================================
SELECT ok(
  (SELECT (j->>'can_push_commessa')::boolean IS TRUE
      AND (j->>'can_push_commessa_reason') IS NULL
     FROM (SELECT script.fn_available_actions_preventivo((SELECT id FROM tmp_rc_misto)) AS j) s),
  '5. Misto ACCETTATO: can_push_commessa=true, reason NULL'
);

-- ============================================================
-- 6) available_actions SOLO MERCE: reason NESSUNA_RIGA_COMMESSA
-- ============================================================
SELECT ok(
  (SELECT (j->>'can_push_commessa')::boolean IS FALSE
      AND (j->>'can_push_commessa_reason') = 'PREVENTIVO_NESSUNA_RIGA_COMMESSA'
      AND (j->>'can_push_commessa_reason_key') = 'preventivi.push_commessa_reason.nessuna_riga'
     FROM (SELECT script.fn_available_actions_preventivo((SELECT id FROM tmp_rc_merce)) AS j) s),
  '6. Solo merce ACCETTATO: can_push=false, reason PREVENTIVO_NESSUNA_RIGA_COMMESSA'
);

-- ============================================================
-- 7) available_actions SENZA BA: reason SENZA_BILLING_ACCOUNT
-- ============================================================
SELECT ok(
  (SELECT (j->>'can_push_commessa')::boolean IS FALSE
      AND (j->>'can_push_commessa_reason') = 'PREVENTIVO_SENZA_BILLING_ACCOUNT'
      AND (j->>'can_push_commessa_reason_key') = 'preventivi.push_commessa_reason.senza_billing_account'
     FROM (SELECT script.fn_available_actions_preventivo((SELECT id FROM tmp_rc_noba)) AS j) s),
  '7. ACCETTATO senza BA: can_push=false, reason PREVENTIVO_SENZA_BILLING_ACCOUNT'
);

-- ============================================================
-- 8) Post-push: riga servizio EMESSA in commessa -> residuo false
--    (la merce residua non conta sul ramo commessa)
-- ============================================================
CREATE TEMP TABLE tmp_rc_commessa AS
WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id, stato_commessa_id)
  SELECT 'PGTAP-RC-CMD-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id, r.stato_commessa_id
    FROM tmp_rc_refs r
  RETURNING id)
SELECT id FROM ins;

INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key,
  articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
  competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
  pricing_mode, stato_approvazione, stato_emissione,
  sorgente_tipo_id, sorgente_uid
)
SELECT
  (SELECT id FROM tmp_rc_commessa),
  'PREV:' || (SELECT uid FROM tmp_rc_misto)::text || ':R:' || (SELECT id FROM tmp_rc_riga_serv)::text,
  r.art_serv_id, r.istanza_utility_id, DATE '2080-01-01', r.uom_id, 2,
  DATE '2080-01-01', DATE '2080-01-01', DATE '2080-12-31',
  r.tipo_doc_fiscale_id, r.valuta_id, 30.000000,
  'FIXED', 'BOZZA', 'EMESSA',
  (SELECT s.id FROM config.sorgenti s WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1),
  (SELECT uid FROM tmp_rc_misto)::text
FROM tmp_rc_refs r;

SELECT is(
  vendite.fn_preventivo_ha_residuo_commessa((SELECT id FROM tmp_rc_misto)),
  false,
  '8. Post-push (servizio EMESSO): residuo commessa = false anche con merce residua'
);

-- ============================================================
-- 9) available_actions DRAFT: reason PREVENTIVO_NON_ACCETTATO
-- ============================================================
SELECT ok(
  (SELECT (j->>'can_push_commessa')::boolean IS FALSE
      AND (j->>'can_push_commessa_reason') = 'PREVENTIVO_NON_ACCETTATO'
     FROM (SELECT script.fn_available_actions_preventivo((SELECT id FROM tmp_rc_draft)) AS j) s),
  '9. DRAFT: can_push=false, reason PREVENTIVO_NON_ACCETTATO'
);

-- ============================================================
-- Setup casi 10-12: tre preventivi servizio (BA ok), riusano la
-- commessa del caso 8 (tmp_rc_commessa) con segment_key distinti.
-- Helper inline: crea preventivo+riga servizio, ritorna id/uid/riga_id.
-- ============================================================
CREATE TEMP TABLE tmp_rc_nonemessa AS
WITH p AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-RC-NONEMESSA', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.stato_accettato_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_residuo_nonemessa'), r.emittente_fiscale_id
    FROM tmp_rc_refs r RETURNING id, uid),
rg AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 1.000000, 25.000000, r.iva_id, true FROM p, tmp_rc_refs r
  RETURNING id)
SELECT (SELECT id FROM p) AS prev_id, (SELECT uid FROM p) AS prev_uid, (SELECT id FROM rg) AS riga_id;

CREATE TEMP TABLE tmp_rc_bom AS
WITH p AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-RC-BOM', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.stato_accettato_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_residuo_bom'), r.emittente_fiscale_id
    FROM tmp_rc_refs r RETURNING id, uid),
rg AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 1.000000, 25.000000, r.iva_id, true FROM p, tmp_rc_refs r
  RETURNING id)
SELECT (SELECT id FROM p) AS prev_id, (SELECT uid FROM p) AS prev_uid, (SELECT id FROM rg) AS riga_id;

CREATE TEMP TABLE tmp_rc_annull AS
WITH p AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-RC-ANNULL', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.stato_accettato_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_residuo_annull'), r.emittente_fiscale_id
    FROM tmp_rc_refs r RETURNING id, uid),
rg AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 1.000000, 25.000000, r.iva_id, true FROM p, tmp_rc_refs r
  RETURNING id)
SELECT (SELECT id FROM p) AS prev_id, (SELECT uid FROM p) AS prev_uid, (SELECT id FROM rg) AS riga_id;

-- Attivita NON_EMESSA con segment_key esatto (caso 10)
INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
  competenza_mese, competenza_dal, competenza_al, tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
  pricing_mode, stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
SELECT (SELECT id FROM tmp_rc_commessa),
  'PREV:' || (SELECT prev_uid FROM tmp_rc_nonemessa)::text || ':R:' || (SELECT riga_id FROM tmp_rc_nonemessa)::text,
  r.art_serv_id, r.istanza_utility_id, DATE '2080-01-01', r.uom_id, 1,
  DATE '2080-01-01', DATE '2080-01-01', DATE '2080-12-31', r.tipo_doc_fiscale_id, r.valuta_id, 25.000000,
  'FIXED', 'BOZZA', 'NON_EMESSA',
  (SELECT s.id FROM config.sorgenti s WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1),
  (SELECT prev_uid FROM tmp_rc_nonemessa)::text
FROM tmp_rc_refs r;

-- Attivita NON_EMESSA con segment_key componente BoM '#CMP:<id>' (caso 11)
INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
  competenza_mese, competenza_dal, competenza_al, tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
  pricing_mode, stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
SELECT (SELECT id FROM tmp_rc_commessa),
  'PREV:' || (SELECT prev_uid FROM tmp_rc_bom)::text || ':R:' || (SELECT riga_id FROM tmp_rc_bom)::text || '#CMP:999',
  r.art_serv_id, r.istanza_utility_id, DATE '2080-01-01', r.uom_id, 1,
  DATE '2080-01-01', DATE '2080-01-01', DATE '2080-12-31', r.tipo_doc_fiscale_id, r.valuta_id, 25.000000,
  'FIXED', 'BOZZA', 'NON_EMESSA',
  (SELECT s.id FROM config.sorgenti s WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1),
  (SELECT prev_uid FROM tmp_rc_bom)::text
FROM tmp_rc_refs r;

-- Attivita ANNULLATA con segment_key esatto (caso 12)
INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
  competenza_mese, competenza_dal, competenza_al, tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
  pricing_mode, stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
SELECT (SELECT id FROM tmp_rc_commessa),
  'PREV:' || (SELECT prev_uid FROM tmp_rc_annull)::text || ':R:' || (SELECT riga_id FROM tmp_rc_annull)::text,
  r.art_serv_id, r.istanza_utility_id, DATE '2080-01-01', r.uom_id, 1,
  DATE '2080-01-01', DATE '2080-01-01', DATE '2080-12-31', r.tipo_doc_fiscale_id, r.valuta_id, 25.000000,
  'FIXED', 'BOZZA', 'ANNULLATA',
  (SELECT s.id FROM config.sorgenti s WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1),
  (SELECT prev_uid FROM tmp_rc_annull)::text
FROM tmp_rc_refs r;

-- ============================================================
-- 10) NON_EMESSA -> residuo = false (IL FIX: esclusa appena instradata)
-- ============================================================
SELECT is(
  vendite.fn_preventivo_ha_residuo_commessa((SELECT prev_id FROM tmp_rc_nonemessa)),
  false,
  '10. Post-push NON_EMESSA: residuo commessa = false (fix gate EVASO)'
);

-- ============================================================
-- 11) Componente BoM (#CMP) NON_EMESSA -> residuo = false (match a prefisso)
-- ============================================================
SELECT is(
  vendite.fn_preventivo_ha_residuo_commessa((SELECT prev_id FROM tmp_rc_bom)),
  false,
  '11. Post-push componente BoM (#CMP): residuo commessa = false (match prefisso §4)'
);

-- ============================================================
-- 12) Attivita ANNULLATA -> residuo = false (riga instradata, non ri-pushabile)
-- ============================================================
SELECT is(
  vendite.fn_preventivo_ha_residuo_commessa((SELECT prev_id FROM tmp_rc_annull)),
  false,
  '12. Attivita ANNULLATA: residuo commessa = false (decisione: non riapre il preventivo)'
);

SELECT * FROM finish();
ROLLBACK;
