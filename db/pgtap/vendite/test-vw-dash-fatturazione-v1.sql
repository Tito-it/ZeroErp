-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: viste dashboard fatturazione (20260703-51..57):
--       5 resolver di area (vw_dash_fatturazione_{preventivi,ordini,
--       offerte,contratti,commesse}) + union (vw_dash_fatturazione_documenti)
--       + aggregata (vw_dash_fatturazione_mensile).
--       Brief: brief-design-dashboard-fatturazione.md §5.
--       Fixture: preventivo ACCETTATO misto (merce a ordine, servizio
--       EMESSO in commessa, servizio residuo); ordine da push; 4 offerte
--       (BOZZA / ACCETTATA senza figlio / con figlio vivo / con figlio
--       abortito); contratto ATTIVO con e senza canone del mese.
--
-- Indice test (0..18):
--   0)  Precondizioni (refs: BA, articoli, stati, sorgenti, listino)
--   1)  Le 7 viste esistono
--   2)  PREVENTIVI: riga documento, competenza da validita_dal, unita 3/2
--   3)  PREVENTIVI: valore totale 140, transitato 110 (imponibile)
--   4)  PREVENTIVI: fermo con motivo RIGA_RESIDUA, stato ACCETTATO
--   5)  ORDINI: DRAFT -> DOC_BOZZA, valore 50/0
--   6)  ORDINI: CONFERMATO senza push -> PUSH_NON_ESEGUITO
--   7)  ORDINI: riga EMESSA in commessa -> transitato, motivo NULL
--   8)  OFFERTE: BOZZA -> DOC_BOZZA
--   9)  OFFERTE: ACCETTATA senza figlio -> SENZA_FIGLIO
--   10) OFFERTE: ACCETTATA con contratto figlio vivo -> transitata
--   11) OFFERTE: ACCETTATA con figlio ANNULLATO -> FIGLIO_ABORTITO
--   12) CONTRATTI: ATTIVO senza canone mese corrente -> CANONE_NON_GENERATO
--   13) CONTRATTI: canone del mese EMESSO in commessa -> transitato
--   14) CONTRATTI: contratto ANNULLATO (abortito) escluso dal resolver
--   15) COMMESSE: valori 90/60, motivo ATTIVITA_NON_APPROVATA
--   16) COMMESSE: attivita APPROVATA ma non emessa -> ATTIVITA_NON_EMESSA
--   17) MENSILE: PREVENTIVI 2080-01 -> 1 doc, 1 fermo, 140/110
--   18) MENSILE: OFFERTE 2080-03 -> 4 docs, 1 transitata, 3 ferme, 0 abortite
-- ------------------------------------------------------------

BEGIN;
SELECT plan(19);

-- ============================================================
-- 0) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_df_refs AS
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
    WHERE s.codice_interno = 'ACCETTATO' AND s.attivo IS TRUE LIMIT 1) AS prev_accettato_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno = 'CONFERMATO' AND s.attivo IS TRUE LIMIT 1) AS ord_confermato_id,
  (SELECT s.id FROM config.stati_doc_offerte s
    WHERE s.codice_interno = 'BOZZA' AND s.attivo IS TRUE LIMIT 1) AS off_bozza_id,
  (SELECT s.id FROM config.stati_doc_offerte s
    WHERE s.codice_interno = 'ACCETTATA' AND s.attivo IS TRUE LIMIT 1) AS off_accettata_id,
  (SELECT s.id FROM config.stati_doc_contratti s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE LIMIT 1) AS contr_draft_id,
  (SELECT s.id FROM config.stati_doc_contratti s
    WHERE s.codice_interno = 'ATTIVO' AND s.attivo IS TRUE LIMIT 1) AS contr_attivo_id,
  (SELECT s.id FROM config.stati_doc_contratti s
    WHERE s.codice_interno = 'ANNULLATO' AND s.attivo IS TRUE LIMIT 1) AS contr_annullato_id,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1) AS sorg_preventivo_id,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'CONTRATTO' AND s.attivo IS TRUE LIMIT 1) AS sorg_contratto_id,
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
  (SELECT l.id FROM vendite.listini l WHERE l.attivo IS TRUE ORDER BY l.id LIMIT 1) AS listino_id,
  (SELECT lv.id FROM vendite.listini_versioni lv WHERE lv.stato = 'ATTIVA'
    ORDER BY lv.id LIMIT 1) AS listino_versione_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'MERCE') AS natura_merce_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'SERVIZIO_UNA_TANTUM') AS natura_serv_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND art_merce_id IS NOT NULL
      AND art_serv_id IS NOT NULL AND prev_accettato_id IS NOT NULL
      AND ord_confermato_id IS NOT NULL AND off_bozza_id IS NOT NULL
      AND off_accettata_id IS NOT NULL AND contr_attivo_id IS NOT NULL
      AND contr_annullato_id IS NOT NULL AND sorg_contratto_id IS NOT NULL
      AND listino_id IS NOT NULL AND listino_versione_id IS NOT NULL
      AND natura_merce_id IS NOT NULL AND natura_serv_id IS NOT NULL
     FROM tmp_df_refs),
  '0. Precondizioni soddisfatte'
);

-- ============================================================
-- 1) Le 7 viste esistono
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM pg_views
    WHERE schemaname = 'vendite'
      AND viewname IN ('vw_dash_fatturazione_preventivi',
                       'vw_dash_fatturazione_ordini',
                       'vw_dash_fatturazione_offerte',
                       'vw_dash_fatturazione_contratti',
                       'vw_dash_fatturazione_commesse',
                       'vw_dash_fatturazione_documenti',
                       'vw_dash_fatturazione_mensile')),
  7,
  '1. Le 7 viste dashboard fatturazione esistono'
);

-- ============================================================
-- Fixture PREVENTIVI: ACCETTATO misto, 3 righe (merce 1x50 a ordine,
-- servizio 2x30 emesso in commessa, servizio 3x10 residuo).
-- ============================================================
UPDATE catalogo.articoli SET natura_vendita_id = (SELECT natura_merce_id FROM tmp_df_refs)
 WHERE id = (SELECT art_merce_id FROM tmp_df_refs);
UPDATE catalogo.articoli SET natura_vendita_id = (SELECT natura_serv_id FROM tmp_df_refs)
 WHERE id = (SELECT art_serv_id FROM tmp_df_refs);

CREATE TEMP TABLE tmp_df_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-DF-PREV', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.prev_accettato_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_fatturazione'), r.emittente_fiscale_id
    FROM tmp_df_refs r
  RETURNING id, uid)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_df_riga_merce AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_merce_id, 1.000000, 50.000000, r.iva_id, true
    FROM tmp_df_prev p, tmp_df_refs r
  RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_df_riga_serv_emessa AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 2.000000, 30.000000, r.iva_id, true
    FROM tmp_df_prev p, tmp_df_refs r
  RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_df_riga_serv_residua AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 3.000000, 10.000000, r.iva_id, true
    FROM tmp_df_prev p, tmp_df_refs r
  RETURNING id)
SELECT * FROM ins;

-- Push reale del ramo merce: crea ordine DRAFT + riga ordine.
SELECT vendite.fn_push_preventivo_a_ordine((SELECT id FROM tmp_df_prev));

-- Ramo commessa: servizio "emesso" (commessa + attivita EMESSA, comp. 2080-01).
CREATE TEMP TABLE tmp_df_commessa AS
WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id, stato_commessa_id)
  SELECT 'PGTAP-DF-CMD-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id, r.stato_commessa_id
    FROM tmp_df_refs r
  RETURNING id)
SELECT id FROM ins;

INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key,
  articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
  competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
  pricing_mode, stato_approvazione, stato_emissione,
  sorgente_tipo_id, sorgente_uid)
SELECT
  (SELECT id FROM tmp_df_commessa),
  'PREV:' || (SELECT uid FROM tmp_df_prev)::text || ':R:' || (SELECT id FROM tmp_df_riga_serv_emessa)::text,
  r.art_serv_id, r.istanza_utility_id, DATE '2080-01-01', r.uom_id, 2,
  DATE '2080-01-01', DATE '2080-01-01', DATE '2080-12-31',
  r.tipo_doc_fiscale_id, r.valuta_id, 30.000000,
  'FIXED', 'BOZZA', 'EMESSA',
  r.sorg_preventivo_id, (SELECT uid FROM tmp_df_prev)::text
FROM tmp_df_refs r;

-- Attivita NON_EMESSA per il servizio residuo: NON conta come transito
-- (predicato canonico EMESSA) e alimenta il caso COMMESSE fermo.
INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key,
  articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
  competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
  pricing_mode, stato_approvazione, stato_emissione,
  sorgente_tipo_id, sorgente_uid)
SELECT
  (SELECT id FROM tmp_df_commessa),
  'PGTAP-DF-NE-' || substr(md5(clock_timestamp()::text), 1, 8),
  r.art_serv_id, r.istanza_utility_id, DATE '2080-01-01', r.uom_id, 3,
  DATE '2080-01-01', DATE '2080-01-01', DATE '2080-12-31',
  r.tipo_doc_fiscale_id, r.valuta_id, 10.000000,
  'FIXED', 'BOZZA', 'NON_EMESSA',
  r.sorg_preventivo_id, (SELECT uid FROM tmp_df_prev)::text
FROM tmp_df_refs r;

-- ============================================================
-- 2-4) Area PREVENTIVI
-- ============================================================
SELECT ok(
  (SELECT v.area = 'PREVENTIVI'
      AND v.competenza_mese = DATE '2080-01-01'
      AND v.unita_totali = 3
      AND v.unita_transitate = 2
     FROM vendite.vw_dash_fatturazione_preventivi v
    WHERE v.documento_id = (SELECT id FROM tmp_df_prev)),
  '2. Preventivo: competenza da validita_dal (2080-01), unita 3/2 (merce a ordine + servizio emesso)'
);

SELECT ok(
  (SELECT v.valore_totale = 140 AND v.valore_transitato = 110
     FROM vendite.vw_dash_fatturazione_preventivi v
    WHERE v.documento_id = (SELECT id FROM tmp_df_prev)),
  '3. Preventivo: valore imponibile totale 140 (50+60+30), transitato 110 (50+60)'
);

SELECT ok(
  (SELECT v.is_transitato = false
      AND v.is_abortito = false
      AND v.motivo_fermo = 'RIGA_RESIDUA'
      AND v.stato_codice_interno = 'ACCETTATO'
     FROM vendite.vw_dash_fatturazione_preventivi v
    WHERE v.documento_id = (SELECT id FROM tmp_df_prev)),
  '4. Preventivo: fermo con motivo RIGA_RESIDUA (residuo 30 sul ramo commessa)'
);

-- ============================================================
-- 5-7) Area ORDINI (ordine creato dal push, 1 riga merce 1x50)
-- ============================================================
CREATE TEMP TABLE tmp_df_ordine AS
SELECT o.id, o.uid, orr.id AS riga_id
  FROM vendite.ordini o
  JOIN vendite.ordini_righe orr ON orr.ordine_id = o.id
 WHERE orr.preventivo_riga_id = (SELECT id FROM tmp_df_riga_merce);

SELECT ok(
  (SELECT v.motivo_fermo = 'DOC_BOZZA'
      AND v.is_transitato = false
      AND v.valore_totale = 50
      AND v.valore_transitato = 0
      AND v.unita_totali = 1
     FROM vendite.vw_dash_fatturazione_ordini v
    WHERE v.documento_id = (SELECT id FROM tmp_df_ordine)),
  '5. Ordine DRAFT: motivo DOC_BOZZA, valore 50/0'
);

UPDATE vendite.ordini
   SET stato_doc_ordine_id = (SELECT ord_confermato_id FROM tmp_df_refs)
 WHERE id = (SELECT id FROM tmp_df_ordine);

SELECT is(
  (SELECT v.motivo_fermo FROM vendite.vw_dash_fatturazione_ordini v
    WHERE v.documento_id = (SELECT id FROM tmp_df_ordine)),
  'PUSH_NON_ESEGUITO',
  '6. Ordine CONFERMATO senza push: motivo PUSH_NON_ESEGUITO'
);

-- Push del ramo ordine: attivita EMESSA con segment_key ORD:<uid>:R:<riga>.
INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key,
  articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
  competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
  pricing_mode, stato_approvazione, stato_emissione,
  sorgente_tipo_id, sorgente_uid)
SELECT
  (SELECT id FROM tmp_df_commessa),
  'ORD:' || (SELECT uid FROM tmp_df_ordine)::text || ':R:' || (SELECT riga_id FROM tmp_df_ordine)::text,
  r.art_merce_id, r.istanza_utility_id, DATE '2080-02-01', r.uom_id, 1,
  DATE '2080-02-01', DATE '2080-02-01', DATE '2080-02-28',
  r.tipo_doc_fiscale_id, r.valuta_id, 50.000000,
  'FIXED', 'APPROVATA', 'EMESSA',
  r.sorg_preventivo_id, (SELECT uid FROM tmp_df_prev)::text
FROM tmp_df_refs r;

SELECT ok(
  (SELECT v.is_transitato = true
      AND v.motivo_fermo IS NULL
      AND v.valore_transitato = 50
     FROM vendite.vw_dash_fatturazione_ordini v
    WHERE v.documento_id = (SELECT id FROM tmp_df_ordine)),
  '7. Ordine con riga EMESSA in commessa: transitato, motivo NULL'
);

-- ============================================================
-- Fixture OFFERTE: 4 offerte con validita_dal 2080-03-01.
-- ============================================================
CREATE TEMP TABLE tmp_df_offerte (slot text, offerta_id bigint);

WITH ins AS (
  INSERT INTO vendite.offerte_commerciali (
    emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
    listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id)
  SELECT r.emittente_fiscale_id, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         r.listino_id, r.listino_versione_id, DATE '2080-03-01', r.off_bozza_id
    FROM tmp_df_refs r
  RETURNING id)
INSERT INTO tmp_df_offerte SELECT 'BOZZA', id FROM ins;

WITH ins AS (
  INSERT INTO vendite.offerte_commerciali (
    emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
    listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id)
  SELECT r.emittente_fiscale_id, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         r.listino_id, r.listino_versione_id, DATE '2080-03-01', r.off_accettata_id
    FROM tmp_df_refs r
  RETURNING id)
INSERT INTO tmp_df_offerte SELECT 'ACC_SENZA_FIGLIO', id FROM ins;

WITH ins AS (
  INSERT INTO vendite.offerte_commerciali (
    emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
    listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id)
  SELECT r.emittente_fiscale_id, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         r.listino_id, r.listino_versione_id, DATE '2080-03-01', r.off_accettata_id
    FROM tmp_df_refs r
  RETURNING id)
INSERT INTO tmp_df_offerte SELECT 'ACC_FIGLIO_VIVO', id FROM ins;

WITH ins AS (
  INSERT INTO vendite.offerte_commerciali (
    emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
    listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id)
  SELECT r.emittente_fiscale_id, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         r.listino_id, r.listino_versione_id, DATE '2080-03-01', r.off_accettata_id
    FROM tmp_df_refs r
  RETURNING id)
INSERT INTO tmp_df_offerte SELECT 'ACC_FIGLIO_ABORTITO', id FROM ins;

-- Figlio VIVO: contratto DRAFT da offerta (is_abortito_snapshot = false).
-- emittente_fiscale_id esplicito: in pgTAP la GUC app.current_user_id e' vuota
-- e trgfn_contratti_default_emittente solleva E_CONTRATTO_EMITTENTE_NON_RISOLTO;
-- derivato dal BA (catena specifico -> default) per soddisfare il guard emittente/BA.
INSERT INTO vendite.contratti (
  numero, billing_account_id, istanza_utility_id, utility_id,
  valido_dal, valido_al, stato_doc_contratto_id, data, offerta_id,
  emittente_fiscale_id, meta)
SELECT 'PGTAP-DF-CV-' || substr(md5(clock_timestamp()::text), 1, 8),
       r.billing_account_id, r.istanza_utility_id, r.utility_id,
       CURRENT_DATE, NULL, r.contr_draft_id, CURRENT_DATE,
       (SELECT offerta_id FROM tmp_df_offerte WHERE slot = 'ACC_FIGLIO_VIVO'),
       COALESCE(anagrafiche.fn_get_emittente_fiscale_pk(r.billing_account_id),
                r.emittente_fiscale_id),
       jsonb_build_object('test_scope','pgtap_dash_fatturazione')
  FROM tmp_df_refs r;

-- Figlio ABORTITO: contratto ANNULLATO da offerta (snapshot -> true).
CREATE TEMP TABLE tmp_df_contr_abortito AS
WITH ins AS (
  INSERT INTO vendite.contratti (
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al, stato_doc_contratto_id, data, offerta_id,
    emittente_fiscale_id, meta)
  SELECT 'PGTAP-DF-CA-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.istanza_utility_id, r.utility_id,
         CURRENT_DATE, NULL, r.contr_annullato_id, CURRENT_DATE,
         (SELECT offerta_id FROM tmp_df_offerte WHERE slot = 'ACC_FIGLIO_ABORTITO'),
         COALESCE(anagrafiche.fn_get_emittente_fiscale_pk(r.billing_account_id),
                  r.emittente_fiscale_id),
         jsonb_build_object('test_scope','pgtap_dash_fatturazione')
    FROM tmp_df_refs r
  RETURNING id)
SELECT * FROM ins;

-- ============================================================
-- 8-11) Area OFFERTE
-- ============================================================
SELECT ok(
  (SELECT v.motivo_fermo = 'DOC_BOZZA' AND v.is_transitato = false
      AND v.is_abortito = false  -- null-safe: esito NULL (senza verdetto) != abortito
      AND v.competenza_mese = DATE '2080-03-01'
     FROM vendite.vw_dash_fatturazione_offerte v
    WHERE v.documento_id = (SELECT offerta_id FROM tmp_df_offerte WHERE slot = 'BOZZA')),
  '8. Offerta BOZZA: motivo DOC_BOZZA, is_abortito false (esito NULL), competenza da validita_dal'
);

SELECT ok(
  (SELECT v.motivo_fermo = 'SENZA_FIGLIO' AND v.is_transitato = false
      AND v.unita_totali = 1 AND v.unita_transitate = 0
     FROM vendite.vw_dash_fatturazione_offerte v
    WHERE v.documento_id = (SELECT offerta_id FROM tmp_df_offerte WHERE slot = 'ACC_SENZA_FIGLIO')),
  '9. Offerta ACCETTATA senza figlio: motivo SENZA_FIGLIO'
);

SELECT ok(
  (SELECT v.is_transitato = true AND v.motivo_fermo IS NULL
      AND v.unita_transitate = 1
     FROM vendite.vw_dash_fatturazione_offerte v
    WHERE v.documento_id = (SELECT offerta_id FROM tmp_df_offerte WHERE slot = 'ACC_FIGLIO_VIVO')),
  '10. Offerta ACCETTATA con contratto figlio vivo: transitata'
);

SELECT ok(
  (SELECT v.is_transitato = false AND v.motivo_fermo = 'FIGLIO_ABORTITO'
     FROM vendite.vw_dash_fatturazione_offerte v
    WHERE v.documento_id = (SELECT offerta_id FROM tmp_df_offerte WHERE slot = 'ACC_FIGLIO_ABORTITO')),
  '11. Offerta ACCETTATA con figlio ANNULLATO: motivo FIGLIO_ABORTITO (XOR permanente)'
);

-- ============================================================
-- Fixture CONTRATTI: ATTIVO dal 1o del mese corrente, aperto.
-- ============================================================
CREATE TEMP TABLE tmp_df_contratto AS
WITH ins AS (
  INSERT INTO vendite.contratti (
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al, stato_doc_contratto_id, data,
    emittente_fiscale_id, meta)
  SELECT 'PGTAP-DF-CT-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.istanza_utility_id, r.utility_id,
         date_trunc('month', CURRENT_DATE)::date, NULL,
         r.contr_attivo_id, date_trunc('month', CURRENT_DATE)::date,
         COALESCE(anagrafiche.fn_get_emittente_fiscale_pk(r.billing_account_id),
                  r.emittente_fiscale_id),
         jsonb_build_object('test_scope','pgtap_dash_fatturazione')
    FROM tmp_df_refs r
  RETURNING id, uid)
SELECT * FROM ins;

-- ============================================================
-- 12-14) Area CONTRATTI
-- ============================================================
SELECT ok(
  (SELECT count(*) = 1
      AND bool_and(v.motivo_fermo = 'CANONE_NON_GENERATO')
      AND bool_and(v.is_transitato = false)
      AND bool_and(v.competenza_mese = date_trunc('month', CURRENT_DATE)::date)
     FROM vendite.vw_dash_fatturazione_contratti v
    WHERE v.documento_id = (SELECT id FROM tmp_df_contratto)),
  '12. Contratto ATTIVO dal mese corrente: 1 riga-mese, motivo CANONE_NON_GENERATO'
);

-- Canone del mese generato: attivita EMESSA con sorgente CONTRATTO.
INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key,
  articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
  competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
  pricing_mode, stato_approvazione, stato_emissione,
  sorgente_tipo_id, sorgente_uid)
SELECT
  (SELECT id FROM tmp_df_commessa),
  'CONTR:' || (SELECT uid FROM tmp_df_contratto)::text || ':R:0:M:'
           || to_char(date_trunc('month', CURRENT_DATE)::date, 'YYYY-MM'),
  r.art_serv_id, r.istanza_utility_id, CURRENT_DATE, r.uom_id, 1,
  date_trunc('month', CURRENT_DATE)::date,
  date_trunc('month', CURRENT_DATE)::date,
  (date_trunc('month', CURRENT_DATE) + interval '1 month - 1 day')::date,
  r.tipo_doc_fiscale_id, r.valuta_id, 25.000000,
  'FIXED', 'APPROVATA', 'EMESSA',
  r.sorg_contratto_id, (SELECT uid FROM tmp_df_contratto)::text
FROM tmp_df_refs r;

SELECT ok(
  (SELECT bool_and(v.is_transitato = true) AND bool_and(v.motivo_fermo IS NULL)
     FROM vendite.vw_dash_fatturazione_contratti v
    WHERE v.documento_id = (SELECT id FROM tmp_df_contratto)),
  '13. Contratto con canone del mese EMESSO in commessa: transitato'
);

SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_fatturazione_contratti v
    WHERE v.documento_id = (SELECT id FROM tmp_df_contr_abortito)),
  0,
  '14. Contratto ANNULLATO (esito NEGATIVO): escluso dal resolver contratti'
);

-- ============================================================
-- 15-16) Area COMMESSE (bucket 2080-01: EMESSA 60 + NON_EMESSA 30)
-- ============================================================
SELECT ok(
  (SELECT v.unita_totali = 2 AND v.unita_transitate = 1
      AND v.valore_totale = 90 AND v.valore_transitato = 60
      AND v.is_transitato = false
      AND v.motivo_fermo = 'ATTIVITA_NON_APPROVATA'
     FROM vendite.vw_dash_fatturazione_commesse v
    WHERE v.documento_id = (SELECT id FROM tmp_df_commessa)
      AND v.competenza_mese = DATE '2080-01-01'),
  '15. Commessa 2080-01: valori 90/60, motivo ATTIVITA_NON_APPROVATA (ferma in BOZZA)'
);

UPDATE vendite.commesse_attivita
   SET stato_approvazione = 'APPROVATA'
 WHERE commessa_id = (SELECT id FROM tmp_df_commessa)
   AND competenza_mese = DATE '2080-01-01'
   AND stato_emissione = 'NON_EMESSA';

SELECT is(
  (SELECT v.motivo_fermo FROM vendite.vw_dash_fatturazione_commesse v
    WHERE v.documento_id = (SELECT id FROM tmp_df_commessa)
      AND v.competenza_mese = DATE '2080-01-01'),
  'ATTIVITA_NON_EMESSA',
  '16. Commessa 2080-01 con ferma APPROVATA: motivo ATTIVITA_NON_EMESSA'
);

-- ============================================================
-- 17-18) Aggregata MENSILE
-- ============================================================
SELECT ok(
  (SELECT m.n_documenti = 1 AND m.n_fermi = 1 AND m.n_transitati = 0
      AND m.n_abortiti = 0
      AND m.valore_totale = 140 AND m.valore_transitato = 110
     FROM vendite.vw_dash_fatturazione_mensile m
    WHERE m.area = 'PREVENTIVI' AND m.competenza_mese = DATE '2080-01-01'),
  '17. Mensile PREVENTIVI 2080-01: 1 documento fermo, 140/110'
);

SELECT ok(
  (SELECT m.n_documenti = 4 AND m.n_transitati = 1 AND m.n_fermi = 3
      AND m.n_abortiti = 0
      AND m.valore_totale IS NULL AND m.valore_transitato IS NULL
     FROM vendite.vw_dash_fatturazione_mensile m
    WHERE m.area = 'OFFERTE' AND m.competenza_mese = DATE '2080-03-01'),
  '18. Mensile OFFERTE 2080-03: 4 documenti, 1 transitata, 3 ferme, valori NULL (area a conteggi)'
);

SELECT * FROM finish();
ROLLBACK;
