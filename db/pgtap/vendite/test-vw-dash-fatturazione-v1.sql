-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2d/2e): l'area della dashboard e' il codice della sorgente; le chiavi del push col prefisso lungo.
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture deve creare una commessa sull'emittente 44 (EMI-TEST), che per
--   progetto resta SENZA operatore assegnato — ed e' il soggetto del test:
--   dimostrare che la dashboard non mescola i due emittenti. Nessun operatore
--   puo' costruire quel dato, perche' la policy rls_commesse_ef_whitelist
--   glielo vieta ed e' esattamente cio' che deve fare.
--   ⚠️ Seconda categoria ammessa per il marcatore (brief §26): non DDL, ma
--   «la fixture costruisce un mondo che l'operatore non deve vedere».
-- pgTAP test per Zero ERP
--
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima le offerte
--   nascevano gia' ACCETTATA, i contratti gia' ANNULLATO e ATTIVO). Il figlio
--   ANNULLATO si annulla col verbo vendite.fn_annulla_contratto (conferma del
--   legame con l'offerta); il contratto ATTIVO prende il listino della fixture,
--   senza il quale non si attiva (trgfn_contratti_freeze_listino_versione).
--
-- Test: viste dashboard fatturazione (20260703-51..57, agg. 20260707-03/06
--       "Situazione aperta"): 5 resolver di area + union
--       (vw_dash_fatturazione_documenti). La mensile e' DISMESSA (20260707-06)
--       e il resolver contratti e' DE-ESPLOSO con giudizio sospeso (DL-12).
--       Brief: brief-design-dashboard-fatturazione.md §5 +
--       brief-db-situazione-aperta.md §2-3.
--       Fixture: preventivo ACCETTATO misto (merce a ordine, servizio
--       EMESSO in commessa, servizio residuo); ordine da push; 4 offerte
--       (BOZZA / ACCETTATA senza figlio / con figlio vivo / con figlio
--       abortito); contratto ATTIVO multi-mese (de-esplosione).
--
-- Indice test (0..18):
--   0)  Precondizioni (refs: BA, articoli, stati, sorgenti, listino)
--   1)  Le 6 viste esistono (mensile dismessa)
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
--   12) CONTRATTI: DE-ESPLOSO -> 1 riga (multi-mese), giudizio SOSPESO
--       (is_transitato/motivo NULL), competenza NULL, data_rif = valido_dal
--   13) CONTRATTI: canone EMESSO in commessa -> giudizio RESTA sospeso (DL-12)
--   14) CONTRATTI: contratto ANNULLATO (abortito) escluso dal resolver
--   15) COMMESSE: valori 90/60, motivo ATTIVITA_NON_APPROVATA
--   16) COMMESSE: attivita APPROVATA ma non emessa -> ATTIVITA_NON_EMESSA
--   17) UNION: preventivo 2080-01 -> 140/110, fase valorizzata
--   18) UNION: OFFERTE 2080-03 -> 4 docs, 1 transitata, 3 ferme non abortite
--   14b) Setup: operatore OPERATORE non-super trovato (scope commesse)
--   19) SCOPE: operatore A vede commessa A, non commessa B (emittente diverso)
--   20) COERENZA: mese di sola commessa B assente da documenti (op. A)
--   21) cliente_display non-null preventivo (path istanza->soggetti)
--   22) cliente_display non-null contratto (path BA->soggetto_ruolo->soggetti)
--   23) cliente_display non-null commessa (path BA->soggetto_ruolo->soggetti)
--   24) VOID esclusi: 2080-06 EMESSA+ANNULLATA+RIFIUTATA -> totale = solo EMESSA
--   25) mese di sole void (ANNULLATA): assente da resolver e drill-down
--   26) edge EMESSA+RIFIUTATA (gia' transitata): tenuta, non persa
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

SELECT plan(28);

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
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE) AS prev_bozza_id,
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
  -- Emittente A (= emittente_fiscale_id) e il suo soggetto_ruolo_id, per lo
  -- scope commesse (P1): la commessa fixture ha emittente A e l'operatore di
  -- test e' whitelistato su A.
  (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1) AS ef_a_sr,
  -- Emittente B: secondo emittente attivo distinto da A (per il test di
  -- coerenza card/drill-down: la commessa di B non deve comparire per l'op. A).
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE
    ORDER BY ef.id OFFSET 1 LIMIT 1) AS ef_b_id,
  (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE ORDER BY ef.id OFFSET 1 LIMIT 1) AS ef_b_sr,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT l.id FROM vendite.listini l WHERE l.attivo IS TRUE ORDER BY l.id LIMIT 1) AS listino_id,
  (SELECT lv.id FROM vendite.listini_versioni lv WHERE lv.stato = 'ATTIVA'
    ORDER BY lv.id LIMIT 1) AS listino_versione_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'MERCE') AS natura_merce_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'SERVIZIO_UNA_TANTUM') AS natura_serv_id;

-- ⭐ 2026-08-26 — IL BILLING ACCOUNT DELL'EMITTENTE B, e perche' serve.
--   La commessa B nasceva sul billing account di A con l'emittente di B: uno
--   stato che il modello non ammette piu' (vendite.trgfn_commesse_guard_emittente_ba,
--   20260826-40) e che non ammetteva nemmeno prima — semplicemente non lo
--   fermava nessuno. L'emittente della commessa si DERIVA dal cliente, quindi
--   per avere una commessa di B serve un cliente di B.
--   ⚠️ Se l'installazione non ne ha, i test 19-20 si skippano: la condizione
--   di skip si sposta da «esiste un secondo emittente» a «esiste un cliente
--   del secondo emittente», che e' la precondizione vera.
ALTER TABLE tmp_df_refs ADD COLUMN ba_b_id bigint;
ALTER TABLE tmp_df_refs ADD COLUMN ba_b_utility_id integer;

-- ⚠️ Due UPDATE e non un LATERAL: in PostgreSQL la FROM di un UPDATE non puo'
--   referenziare l'alias del target, e il predicato e' correlato a r.ef_b_sr.
-- ⚠️ Si usa script.fn_get_ba_emittente_sr_id e NON
--   anagrafiche.fn_get_emittente_fiscale_id: la seconda SOLLEVA quando non
--   risolve, e qui si sta scandendo l'intera tabella dei clienti — un
--   emittente non configurato farebbe morire la fixture invece di lasciarla
--   rispondere «nessuno».
UPDATE tmp_df_refs r
   SET ba_b_id = (
        SELECT ba.id
          FROM anagrafiche.billing_account ba
         WHERE ba.utility_id IS NOT NULL
           AND r.ef_b_sr IS NOT NULL
           AND script.fn_get_ba_emittente_sr_id(ba.id) = r.ef_b_sr
         ORDER BY ba.id
         LIMIT 1);

UPDATE tmp_df_refs r
   SET ba_b_utility_id = (
        SELECT ba.utility_id
          FROM anagrafiche.billing_account ba
         WHERE ba.id = r.ba_b_id);

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
-- 1) Le 6 viste esistono (la mensile e' dismessa, 20260707-06)
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM pg_views
    WHERE schemaname = 'vendite'
      AND viewname IN ('vw_dash_fatturazione_preventivi',
                       'vw_dash_fatturazione_ordini',
                       'vw_dash_fatturazione_offerte',
                       'vw_dash_fatturazione_contratti',
                       'vw_dash_fatturazione_commesse',
                       'vw_dash_fatturazione_documenti'))
  - (SELECT count(*)::integer FROM pg_views
      WHERE schemaname = 'vendite'
        AND viewname = 'vw_dash_fatturazione_mensile'),
  6,
  '1. Le 6 viste della famiglia esistono e la mensile e'' stata dismessa'
);

-- ============================================================
-- Fixture PREVENTIVI: ACCETTATO misto, 3 righe (merce 1x50 a ordine,
-- servizio 2x30 emesso in commessa, servizio 3x10 residuo).
-- ============================================================
UPDATE catalogo.articoli SET natura_vendita_id = (SELECT natura_merce_id FROM tmp_df_refs)
 WHERE id = (SELECT art_merce_id FROM tmp_df_refs);
UPDATE catalogo.articoli SET natura_vendita_id = (SELECT natura_serv_id FROM tmp_df_refs)
 WHERE id = (SELECT art_serv_id FROM tmp_df_refs);

-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT, prende le tre righe, poi passa ad ACCETTATO con dbops.fn_pgtap_porta_a_stato prima del push — fuori bozza le righe non si scrivono piu' (20261008-91).
CREATE TEMP TABLE tmp_df_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-DF-PREV', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.prev_bozza_id,
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
DO $porta$ BEGIN PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_df_prev), 'ACCETTATO'); END $porta$;

-- Push reale del ramo merce: crea ordine DRAFT + riga ordine.
SELECT vendite.fn_push_preventivo_a_ordine((SELECT id FROM tmp_df_prev));

-- Ramo commessa: servizio "emesso" (commessa + attivita EMESSA, comp. 2080-01).
-- emittente_soggetto_ruolo_id = emittente A: il resolver commesse (20260703-60)
-- filtra per scope emittente da GUC; l'operatore di test (impostato prima del
-- test 15) e' whitelistato su A, quindi vede questa commessa.
CREATE TEMP TABLE tmp_df_commessa AS
WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                emittente_soggetto_ruolo_id, stato_commessa_id)
  SELECT 'PGTAP-DF-CMD-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id, r.ef_a_sr, r.stato_commessa_id
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
  'PREVENTIVO:' || (SELECT uid FROM tmp_df_prev)::text || ':R:' || (SELECT id FROM tmp_df_riga_serv_emessa)::text,
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
  (SELECT v.area = 'PREVENTIVO'
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

-- Push del ramo ordine: attivita EMESSA con segment_key ORDINE_VENDITA:<uid>:R:<riga>.
INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key,
  articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
  competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
  pricing_mode, stato_approvazione, stato_emissione,
  sorgente_tipo_id, sorgente_uid)
SELECT
  (SELECT id FROM tmp_df_commessa),
  'ORDINE_VENDITA:' || (SELECT uid FROM tmp_df_ordine)::text || ':R:' || (SELECT riga_id FROM tmp_df_ordine)::text,
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

-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo). Le offerte
--   del fixture sono dell'emittente A e del primo BA dei dati: il listino si
--   COSTRUISCE con A e con la utility del BA (tipologia: la prima che la utility
--   ammette, come fn_pgtap_crea_listino), con una versione ATTIVA da oggi. Qui e'
--   scritto a mano perche' il builder prende l'emittente di chi agisce, e il
--   passaggio all'operatore di A viene dopo; il file gira da owner (marcatore in
--   testa), quindi il guard di scope dei listini non scatta.
--   ⚠️ Prima stesura dello stesso giorno: si cercava fra i dati un listino di A
--   sulla utility del BA, e su dbdev non c'era (offerta con listino NULL).
--   Listino e versione in due istruzioni: i trigger della versione rileggono il
--   listino, e nella stessa istruzione non lo vedrebbero.
CREATE TEMP TABLE tmp_df_listino AS
WITH l AS (
    INSERT INTO vendite.listini (codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP_DF_' || substr(md5(clock_timestamp()::text || random()::text), 1, 12),
           'Fixture pgTAP: dash fatturazione', r.utility_id,
           (SELECT ltu.tipologia_id FROM config.listini_tipologie_utilities ltu
              JOIN config.listini_tipologie lt ON lt.id = ltu.tipologia_id AND lt.attivo
             WHERE ltu.utility_id = r.utility_id AND ltu.attivo
             ORDER BY lt.ordinamento, lt.id LIMIT 1),
           r.ef_a_sr
      FROM tmp_df_refs r
    RETURNING id
)
SELECT l.id AS listino_id, NULL::bigint AS listino_versione_id FROM l;

WITH v AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, stato)
    SELECT listino_id, 'PGTAP_DF_V1', script.fn_data_operativa(), 'ATTIVA' FROM tmp_df_listino
    RETURNING id
)
UPDATE tmp_df_listino SET listino_versione_id = (SELECT id FROM v);

UPDATE tmp_df_refs r
   SET listino_id          = (SELECT listino_id FROM tmp_df_listino),
       listino_versione_id = (SELECT listino_versione_id FROM tmp_df_listino);

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
         r.listino_id, r.listino_versione_id, DATE '2080-03-01', r.off_bozza_id
    FROM tmp_df_refs r
  RETURNING id)
INSERT INTO tmp_df_offerte SELECT 'ACC_SENZA_FIGLIO', id FROM ins;

WITH ins AS (
  INSERT INTO vendite.offerte_commerciali (
    emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
    listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id)
  SELECT r.emittente_fiscale_id, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         r.listino_id, r.listino_versione_id, DATE '2080-03-01', r.off_bozza_id
    FROM tmp_df_refs r
  RETURNING id)
INSERT INTO tmp_df_offerte SELECT 'ACC_FIGLIO_VIVO', id FROM ins;

WITH ins AS (
  INSERT INTO vendite.offerte_commerciali (
    emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
    listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id)
  SELECT r.emittente_fiscale_id, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         r.listino_id, r.listino_versione_id, DATE '2080-03-01', r.off_bozza_id
    FROM tmp_df_refs r
  RETURNING id)
INSERT INTO tmp_df_offerte SELECT 'ACC_FIGLIO_ABORTITO', id FROM ins;

-- rev 2026-10-24: le tre ACCETTATA nascono in BOZZA e ci arrivano per la
-- matrice (BOZZA -> EMESSA -> ACCETTATA), sotto i guard veri.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', o.offerta_id, 'ACCETTATA')
  FROM tmp_df_offerte o
 WHERE o.slot IN ('ACC_SENZA_FIGLIO', 'ACC_FIGLIO_VIVO', 'ACC_FIGLIO_ABORTITO')
 ORDER BY o.slot;

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
       script.fn_data_operativa(), NULL, r.contr_draft_id, script.fn_data_operativa(),
       (SELECT offerta_id FROM tmp_df_offerte WHERE slot = 'ACC_FIGLIO_VIVO'),
       COALESCE(anagrafiche.fn_get_emittente_fiscale_pk(r.billing_account_id),
                r.emittente_fiscale_id),
       jsonb_build_object('test_scope','pgtap_dash_fatturazione')
  FROM tmp_df_refs r;

-- Figlio ABORTITO: contratto ANNULLATO da offerta (snapshot -> true).
-- rev 2026-10-24: nasce DRAFT e si annulla col verbo. ⚠️ Non con
--   fn_pgtap_porta_a_stato: annullare un contratto nato da un'offerta riapre un
--   legame (l'offerta da cui nasce), e il guard
--   trg_contratti_m10_guard_annullo_con_legami_upd vuole la conferma, che
--   vendite.fn_annulla_contratto riceve come conteggio: 1, l'offerta.
CREATE TEMP TABLE tmp_df_contr_abortito AS
WITH ins AS (
  INSERT INTO vendite.contratti (
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al, data, offerta_id,
    emittente_fiscale_id, meta)
  SELECT 'PGTAP-DF-CA-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.istanza_utility_id, r.utility_id,
         script.fn_data_operativa(), NULL, script.fn_data_operativa(),
         (SELECT offerta_id FROM tmp_df_offerte WHERE slot = 'ACC_FIGLIO_ABORTITO'),
         COALESCE(anagrafiche.fn_get_emittente_fiscale_pk(r.billing_account_id),
                  r.emittente_fiscale_id),
         jsonb_build_object('test_scope','pgtap_dash_fatturazione')
    FROM tmp_df_refs r
  RETURNING id)
SELECT * FROM ins;

SELECT vendite.fn_annulla_contratto(c.id, 1)
  FROM tmp_df_contr_abortito c;

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
-- Fixture CONTRATTI: ATTIVO da 2 mesi fa, aperto -> multi-mese: prima della
-- de-esplosione (20260707-03) avrebbe prodotto 3 righe-mese, ora 1 sola.
-- rev 2026-10-24: nasce DRAFT sul listino della fixture e si attiva per la
--   matrice.
-- ============================================================
CREATE TEMP TABLE tmp_df_contratto AS
WITH ins AS (
  INSERT INTO vendite.contratti (
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al, data, listino_id,
    emittente_fiscale_id, meta)
  SELECT 'PGTAP-DF-CT-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.istanza_utility_id, r.utility_id,
         (date_trunc('month', script.fn_data_operativa()) - interval '2 months')::date, NULL,
         (date_trunc('month', script.fn_data_operativa()) - interval '2 months')::date,
         r.listino_id,
         COALESCE(anagrafiche.fn_get_emittente_fiscale_pk(r.billing_account_id),
                  r.emittente_fiscale_id),
         jsonb_build_object('test_scope','pgtap_dash_fatturazione')
    FROM tmp_df_refs r
  RETURNING id, uid)
SELECT * FROM ins;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti', c.id, 'ATTIVO')
  FROM tmp_df_contratto c;

-- ============================================================
-- 12-14) Area CONTRATTI (de-esplosa, giudizio sospeso — DL-12)
-- ============================================================
SELECT ok(
  (SELECT count(*) = 1
      AND bool_and(v.is_transitato IS NULL)
      AND bool_and(v.unita_transitate IS NULL)
      AND bool_and(v.motivo_fermo IS NULL)
      AND bool_and(v.unita_totali = 1)
      AND bool_and(v.competenza_mese IS NULL)
      AND bool_and(v.data_riferimento = (date_trunc('month', script.fn_data_operativa()) - interval '2 months')::date)
     FROM vendite.vw_dash_fatturazione_contratti v
    WHERE v.documento_id = (SELECT id FROM tmp_df_contratto)),
  '12. Contratto ATTIVO multi-mese: 1 SOLA riga (de-esploso), giudizio sospeso (transito/motivo NULL), data_riferimento = valido_dal'
);

-- Canone del mese generato: attivita EMESSA con sorgente CONTRATTO. Con la
-- de-esplosione (DL-12) il giudizio di transito resta SOSPESO anche in
-- presenza del canone: si riaccendera' col push ricorrente.
INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key,
  articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
  competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
  pricing_mode, stato_approvazione, stato_emissione,
  sorgente_tipo_id, sorgente_uid)
SELECT
  (SELECT id FROM tmp_df_commessa),
  'CONTRATTO:' || (SELECT uid FROM tmp_df_contratto)::text || ':R:0:M:'
           || to_char(date_trunc('month', script.fn_data_operativa())::date, 'YYYY-MM'),
  r.art_serv_id, r.istanza_utility_id, script.fn_data_operativa(), r.uom_id, 1,
  date_trunc('month', script.fn_data_operativa())::date,
  date_trunc('month', script.fn_data_operativa())::date,
  (date_trunc('month', script.fn_data_operativa()) + interval '1 month - 1 day')::date,
  r.tipo_doc_fiscale_id, r.valuta_id, 25.000000,
  'FIXED', 'APPROVATA', 'EMESSA',
  r.sorg_contratto_id, (SELECT uid FROM tmp_df_contratto)::text
FROM tmp_df_refs r;

SELECT ok(
  (SELECT count(*) = 1 AND bool_and(v.is_transitato IS NULL)
      AND bool_and(v.motivo_fermo IS NULL)
     FROM vendite.vw_dash_fatturazione_contratti v
    WHERE v.documento_id = (SELECT id FROM tmp_df_contratto)),
  '13. Contratto con canone EMESSO in commessa: giudizio RESTA sospeso (DL-12), sempre 1 riga'
);

SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_fatturazione_contratti v
    WHERE v.documento_id = (SELECT id FROM tmp_df_contr_abortito)),
  0,
  '14. Contratto ANNULLATO (esito NEGATIVO): escluso dal resolver contratti'
);

-- ============================================================
-- Setup scope operatore (P1): il resolver commesse (20260703-60) filtra per
-- scope emittente da GUC ed e' FAIL-CLOSED (senza GUC operatore -> 0 righe,
-- NON aggirato da BYPASSRLS). Da qui in avanti impostiamo la sessione come un
-- operatore OPERATORE non-super whitelistato sull'emittente A: cosi' vede la
-- commessa fixture (emittente A) e NON quelle di altri emittenti.
-- ============================================================
CREATE TEMP TABLE tmp_df_op AS
SELECT id.auth_user_id AS user_id
  FROM anagrafiche.identita_digitali id
 WHERE id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND id.attivo = true
   AND NOT EXISTS (
       SELECT 1 FROM config.profili_accesso_bindings pab
       JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
       WHERE pab.identita_digitale_id = id.id
         AND pab.attivo = true
         AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso)
 ORDER BY id.id LIMIT 1;

SELECT ok(
  (SELECT user_id IS NOT NULL FROM tmp_df_op),
  '14b. Trovato un operatore OPERATORE non-super per il test scope commesse'
);

-- Whitelist emittente A per l'operatore (override delete guardato).
SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_df_op);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id, meta)
SELECT o.user_id, r.emittente_fiscale_id,
       '{"test_scope":"pgtap_dash_fatturazione"}'::jsonb
  FROM tmp_df_op o, tmp_df_refs r
 WHERE o.user_id IS NOT NULL;

-- Sessione = operatore ristretto (scope commesse attivo da qui).
SELECT set_config('app.current_user_id',
    (SELECT user_id::text FROM tmp_df_op), true);

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
-- 17-18) UNION (la mensile e' dismessa: stesse coperture dal drill-down)
-- ============================================================
SELECT ok(
  (SELECT d.valore_totale = 140 AND d.valore_transitato = 110
      AND d.is_transitato = false AND d.is_abortito = false
      AND d.fase IS NOT NULL
     FROM vendite.vw_dash_fatturazione_documenti d
    WHERE d.area = 'PREVENTIVO'
      AND d.documento_id = (SELECT id FROM tmp_df_prev)),
  '17. Union PREVENTIVI: il documento 2080-01 espone 140/110, fermo, fase valorizzata'
);

SELECT ok(
  (SELECT count(*) = 4
      AND count(*) FILTER (WHERE d.is_transitato) = 1
      AND count(*) FILTER (WHERE NOT d.is_transitato AND NOT d.is_abortito) = 3
      AND bool_and(d.valore_totale IS NULL AND d.valore_transitato IS NULL)
     FROM vendite.vw_dash_fatturazione_documenti d
    WHERE d.area = 'OFFERTA_COMMERCIALE' AND d.competenza_mese = DATE '2080-03-01'
      AND d.documento_id IN (SELECT offerta_id FROM tmp_df_offerte)),
  '18. Union OFFERTE 2080-03: 4 documenti, 1 transitata, 3 ferme, valori NULL (area a conteggi)'
);

-- ============================================================
-- 19-20) P1: coerenza scope commesse card vs drill-down (2 emittenti)
--   Commessa B (emittente B) NON deve comparire per l'operatore A, ne' nel
--   resolver/drill-down ne' nella mensile (card).
--   ⚠️ La commessa B si costruisce sul CLIENTE dell'emittente B, non su quello
--   di A: l'emittente di una commessa si deriva dal cliente, e la coppia
--   «cliente di A + emittente di B» non e' uno stato del modello. Se
--   l'installazione non ha clienti sul secondo emittente (ba_b_id NULL) i due
--   test sono skippati.
-- ============================================================
CREATE TEMP TABLE tmp_df_commessa_b AS
WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                emittente_soggetto_ruolo_id, stato_commessa_id)
  SELECT 'PGTAP-DF-CMB-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.ba_b_id, r.ba_b_utility_id, r.ef_b_sr, r.stato_commessa_id
    FROM tmp_df_refs r
   WHERE r.ba_b_id IS NOT NULL
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
  (SELECT id FROM tmp_df_commessa_b),
  'PGTAP-DF-B-' || substr(md5(clock_timestamp()::text), 1, 8),
  r.art_serv_id, r.istanza_utility_id, DATE '2080-05-01', r.uom_id, 1,
  DATE '2080-05-01', DATE '2080-05-01', DATE '2080-05-31',
  r.tipo_doc_fiscale_id, r.valuta_id, 77.000000,
  'FIXED', 'APPROVATA', 'EMESSA',
  r.sorg_preventivo_id, (SELECT uid FROM tmp_df_prev)::text
FROM tmp_df_refs r
WHERE EXISTS (SELECT 1 FROM tmp_df_commessa_b);

-- 19) Il resolver/drill-down commesse (operatore A) esclude la commessa B e
--     include la A: card e drill-down leggono la stessa vista scope-aware.
SELECT CASE WHEN (SELECT ba_b_id FROM tmp_df_refs) IS NULL
  THEN pass('19. [skip] seed con un solo emittente: coerenza scope non testabile')
  ELSE ok(
    (SELECT NOT EXISTS (
       SELECT 1 FROM vendite.vw_dash_fatturazione_commesse v
        WHERE v.documento_id = (SELECT id FROM tmp_df_commessa_b))
     AND EXISTS (
       SELECT 1 FROM vendite.vw_dash_fatturazione_commesse v
        WHERE v.documento_id = (SELECT id FROM tmp_df_commessa))),
    '19. Scope commesse: operatore A vede la commessa A, NON la commessa B (emittente diverso)'
  )
END;

-- 20) Coerenza scope sul mese di B: per l'operatore A la union non contiene
--     la commessa B (la mensile e' dismessa: resta il perimetro documenti).
SELECT CASE WHEN (SELECT ba_b_id FROM tmp_df_refs) IS NULL
  THEN pass('20. [skip] seed con un solo emittente: coerenza scope non testabile')
  ELSE ok(
    (SELECT NOT EXISTS (
              SELECT 1 FROM vendite.vw_dash_fatturazione_documenti d
               WHERE d.area = 'COMMESSA' AND d.competenza_mese = DATE '2080-05-01')),
    '20. Scope: mese 2080-05 (solo commessa B) assente da documenti per l''operatore A'
  )
END;

-- ============================================================
-- 21-23) P2: cliente_display valorizzato (path per-area delle vw_*_lista)
-- ============================================================
SELECT ok(
  (SELECT v.cliente_display IS NOT NULL
     FROM vendite.vw_dash_fatturazione_preventivi v
    WHERE v.documento_id = (SELECT id FROM tmp_df_prev)),
  '21. cliente_display valorizzato per il preventivo (path istanza->soggetti)'
);

SELECT ok(
  (SELECT v.cliente_display IS NOT NULL
     FROM vendite.vw_dash_fatturazione_contratti v
    WHERE v.documento_id = (SELECT id FROM tmp_df_contratto)
    LIMIT 1),
  '22. cliente_display valorizzato per il contratto (path BA->soggetto_ruolo->soggetti)'
);

SELECT ok(
  (SELECT v.cliente_display IS NOT NULL
     FROM vendite.vw_dash_fatturazione_commesse v
    WHERE v.documento_id = (SELECT id FROM tmp_df_commessa)
      AND v.competenza_mese = DATE '2080-01-01'),
  '23. cliente_display valorizzato per la commessa (path BA->soggetto_ruolo->soggetti)'
);

-- ============================================================
-- 24-26) Esclusione attivita' VOID dal denominatore (20260703-61)
--   Fixture su commessa A (emittente A, in scope operatore) in mesi freschi,
--   cosi' i test 2080-01 restano intatti.
-- ============================================================

-- Helper inline: inserisce un'attivita' void/edge su commessa A in un mese.
-- 2080-06: EMESSA(100) + ANNULLATA(999) + RIFIUTATA/NON_EMESSA(888)
INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
  uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
  stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
SELECT (SELECT id FROM tmp_df_commessa),
       'PGTAP-DF-V6E-' || substr(md5(clock_timestamp()::text), 1, 8),
       r.art_serv_id, r.istanza_utility_id, DATE '2080-06-01', r.uom_id, 1,
       DATE '2080-06-01', DATE '2080-06-01', DATE '2080-06-30',
       r.tipo_doc_fiscale_id, r.valuta_id, 100.000000, 'FIXED',
       'APPROVATA', 'EMESSA', r.sorg_preventivo_id, (SELECT uid FROM tmp_df_prev)::text
FROM tmp_df_refs r;

INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
  uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
  stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
SELECT (SELECT id FROM tmp_df_commessa),
       'PGTAP-DF-V6A-' || substr(md5(clock_timestamp()::text), 1, 8),
       r.art_serv_id, r.istanza_utility_id, DATE '2080-06-01', r.uom_id, 1,
       DATE '2080-06-01', DATE '2080-06-01', DATE '2080-06-30',
       r.tipo_doc_fiscale_id, r.valuta_id, 999.000000, 'FIXED',
       'APPROVATA', 'ANNULLATA', r.sorg_preventivo_id, (SELECT uid FROM tmp_df_prev)::text
FROM tmp_df_refs r;

INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
  uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
  stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
SELECT (SELECT id FROM tmp_df_commessa),
       'PGTAP-DF-V6R-' || substr(md5(clock_timestamp()::text), 1, 8),
       r.art_serv_id, r.istanza_utility_id, DATE '2080-06-01', r.uom_id, 1,
       DATE '2080-06-01', DATE '2080-06-01', DATE '2080-06-30',
       r.tipo_doc_fiscale_id, r.valuta_id, 888.000000, 'FIXED',
       'RIFIUTATA', 'NON_EMESSA', r.sorg_preventivo_id, (SELECT uid FROM tmp_df_prev)::text
FROM tmp_df_refs r;

SELECT ok(
  (SELECT v.unita_totali = 1 AND v.valore_totale = 100
      AND v.valore_transitato = 100 AND v.is_transitato = true
      AND v.motivo_fermo IS NULL
     FROM vendite.vw_dash_fatturazione_commesse v
    WHERE v.documento_id = (SELECT id FROM tmp_df_commessa)
      AND v.competenza_mese = DATE '2080-06-01'),
  '24. Void esclusi: 2080-06 EMESSA(100)+ANNULLATA(999)+RIFIUTATA(888) -> totale 100, unita 1, transitato'
);

-- 2080-07: solo 1 ANNULLATA -> mese interamente void -> assente dal resolver
INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
  uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
  stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
SELECT (SELECT id FROM tmp_df_commessa),
       'PGTAP-DF-V7A-' || substr(md5(clock_timestamp()::text), 1, 8),
       r.art_serv_id, r.istanza_utility_id, DATE '2080-07-01', r.uom_id, 1,
       DATE '2080-07-01', DATE '2080-07-01', DATE '2080-07-31',
       r.tipo_doc_fiscale_id, r.valuta_id, 555.000000, 'FIXED',
       'BOZZA', 'ANNULLATA', r.sorg_preventivo_id, (SELECT uid FROM tmp_df_prev)::text
FROM tmp_df_refs r;

SELECT ok(
  (SELECT NOT EXISTS (
     SELECT 1 FROM vendite.vw_dash_fatturazione_commesse v
      WHERE v.documento_id = (SELECT id FROM tmp_df_commessa)
        AND v.competenza_mese = DATE '2080-07-01')
   AND NOT EXISTS (
     SELECT 1 FROM vendite.vw_dash_fatturazione_documenti d
      WHERE d.area = 'COMMESSA' AND d.competenza_mese = DATE '2080-07-01')),
  '25. Mese di sole void (2080-07 ANNULLATA): assente dal resolver e dal drill-down'
);

-- 2080-08: EMESSA+RIFIUTATA (assi indipendenti) -> gia' transitata, TENUTA.
INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
  uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
  stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
SELECT (SELECT id FROM tmp_df_commessa),
       'PGTAP-DF-V8ER-' || substr(md5(clock_timestamp()::text), 1, 8),
       r.art_serv_id, r.istanza_utility_id, DATE '2080-08-01', r.uom_id, 1,
       DATE '2080-08-01', DATE '2080-08-01', DATE '2080-08-31',
       r.tipo_doc_fiscale_id, r.valuta_id, 200.000000, 'FIXED',
       'RIFIUTATA', 'EMESSA', r.sorg_preventivo_id, (SELECT uid FROM tmp_df_prev)::text
FROM tmp_df_refs r;

SELECT ok(
  (SELECT v.unita_totali = 1 AND v.valore_totale = 200
      AND v.is_transitato = true
     FROM vendite.vw_dash_fatturazione_commesse v
    WHERE v.documento_id = (SELECT id FROM tmp_df_commessa)
      AND v.competenza_mese = DATE '2080-08-01'),
  '26. Edge EMESSA+RIFIUTATA (gia'' transitata): tenuta, non persa dal totale/transitato'
);

SELECT * FROM finish();
ROLLBACK;
