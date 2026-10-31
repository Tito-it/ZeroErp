-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-31 (brief-db-contratto-righe-periodiche-in-commessa §6.13, 20261031-04): il giudizio dei contratti e' riacceso dal push. Il contratto della fixture non ha niente da mandare (il listino ha solo la riga d'appoggio, che non matura canoni): e' transitato (1, motivo NULL); il canone EMESSO scritto a mano non cambia il giudizio, che e' del push. Sempre 1 riga.
-- rev 2026-10-25 (brief-modello-documento-vendita §9): la conferma dell'ordine passa da
--   dbops.fn_pgtap_porta_a_stato (il verbo dell'ordine), non da un UPDATE dello stato: la porta lo
--   ferma. Nessuna attesa cambiata.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2d/2e): l'area della dashboard e' il codice della sorgente; le chiavi del push col prefisso lungo.
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture deve creare una commessa dell'emittente B con l'operatore di A
--   in sessione — ed e' il soggetto del test: dimostrare che la dashboard non
--   mescola i due emittenti. L'operatore di A non puo' costruire quel dato,
--   perche' la policy rls_commesse_ef_whitelist glielo vieta ed e' esattamente
--   cio' che deve fare. (rev 2026-10-24: B si costruisce, prima era
--   l'emittente 44 EMI-TEST dei dati, senza operatore.)
--   ⚠️ rev 2026-10-24 (R-9): la commessa di B ora nasce dal builder sotto il
--   contesto dell'operatore di B, non piu' scritta dall'owner con A in
--   sessione: se il marcatore serva ancora va riprovato col runner app.
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
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): il mondo si
--   COSTRUISCE: le aziende A e B coi loro operatori (prima «il primo e il
--   secondo emittente per id»), un cliente per ciascuna (quello di B sotto il
--   contesto di B), articoli merce e servizio con la natura nel builder (prima i
--   primi due per id, corretti con un UPDATE), il listino di A dal builder. I
--   due figli dell'offerta nascono dalla PUSH (dbops.fn_pgtap_crea_contratto col
--   quarto parametro), il contratto ATTIVO dal builder: DRAFT, date multi-mese
--   e listino in bozza, poi ATTIVO per la matrice.
-- rev 2026-10-24 (brief-modello-documento-vendita R-2/R-9): l'azienda A e il
--   suo cliente nascono da dbops.fn_pgtap_crea_mondo_cliente (contesto e
--   whitelist su A dal builder: tolta la riscrittura a mano di
--   config.user_emittenti_fiscali e il set_config); il contratto ATTIVO nasce
--   dal builder col periodo multi-mese, la data e il listino della fixture; le
--   commesse di A e di B nascono da dbops.fn_pgtap_crea_commessa in BOZZA
--   (quella di B sotto il contesto di B). Le attivita' restano del test.
-- rev 2026-10-24 (brief-modello-documento-vendita §4-octies): le attivita'
--   le scrive dbops.fn_pgtap_crea_commessa_attivita (nove INSERT a mano in
--   meno). Con la sorgente quelle del servizio (PREVENTIVO) e dell'ordine
--   (ORDINE_VENDITA, prima con la sorgente sbagliata), chiave dal dominio;
--   senza (sorgente COMMESSA) le righe che avevano una chiave inventata. Il
--   canone del contratto resta a mano (chiave col mese), con la chiave da
--   script.fn_segment_key. Tipo documento e valuta li deriva la madre.
--
-- Test: viste dashboard fatturazione (20260703-51..57, agg. 20260707-03/06
--       "Situazione aperta"): 5 resolver di area + union
--       (vw_dash_fatturazione_documenti). La mensile e' DISMESSA (20260707-06)
--       e il resolver contratti e' DE-ESPLOSO (DL-12), giudizio dal push (20261031-04).
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
--   12) CONTRATTI: DE-ESPLOSO -> 1 riga (multi-mese), niente da mandare ->
--       transitato (motivo NULL), competenza NULL, data_rif = valido_dal
--   13) CONTRATTI: canone EMESSO in commessa -> sempre 1 riga, giudizio invariato
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
-- ⭐ rev 2026-10-24 (Q-4): le due aziende e i loro operatori si costruiscono,
--   non si cercano. Il cliente di B nasce col contesto su B (il trigger z90
--   lega il BA all'azienda di chi agisce), poi il contesto torna ad A, che e'
--   chi agisce nel resto del file.
-- rev 2026-10-24 (R-9): A e' il mondo del builder: azienda, operatore,
--   contesto aperto su di lui e il cliente di A in una chiamata.
CREATE TEMP TABLE tmp_df_mondo_a AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('dash fatturazione A');

CREATE TEMP TABLE tmp_df_cli_a AS
SELECT billing_account_id, istanza_utility_id, utility_id FROM tmp_df_mondo_a;

CREATE TEMP TABLE tmp_df_mondo_b AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_df_mondo_b)); END $ctx$;

CREATE TEMP TABLE tmp_df_cli_b AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgTAP dash fatturazione B');

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_df_mondo_a)); END $ctx$;

SELECT plan(28);

-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo). Con
--   l'operatore di A in sessione il builder gli da' l'emittente A, sulla
--   utility del cliente (rev 2026-10-24: prima era scritto a mano, perche' il
--   passaggio all'operatore di A veniva dopo).
CREATE TEMP TABLE tmp_df_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_df_cli_a), 'dash fatturazione');

-- ============================================================
-- 0) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_df_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_df_cli_a) AS billing_account_id,
  (SELECT utility_id FROM tmp_df_cli_a) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_df_cli_a) AS istanza_utility_id,
  dbops.fn_pgtap_crea_articolo('PGT-DF-MERCE', true,
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita WHERE codice_interno = 'MERCE')) AS art_merce_id,
  dbops.fn_pgtap_crea_articolo('PGT-DF-SERV', false,
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita WHERE codice_interno = 'SERVIZIO_UNA_TANTUM')) AS art_serv_id,
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
    WHERE s.codice_interno = 'CONTRATTO' AND s.attivo IS TRUE LIMIT 1) AS sorg_contratto_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  -- uom, tipo documento e valuta servono solo al canone del contratto, che
  --   resta scritto a mano (rev 2026-10-24 §4-octies: vedi sotto).
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE
    ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE
    ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  -- Emittente A: la commessa fixture ha emittente A e l'operatore di test e'
  -- whitelistato su A (scope commesse, P1).
  (SELECT emittente_fiscale_id FROM tmp_df_mondo_a) AS emittente_fiscale_id,
  -- Emittente B: la seconda azienda costruita (per il test di coerenza
  -- card/drill-down: la commessa di B non deve comparire per l'op. A).
  (SELECT emittente_fiscale_id FROM tmp_df_mondo_b) AS ef_b_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT listino_id FROM tmp_df_listino) AS listino_id,
  (SELECT listino_versione_id FROM tmp_df_listino) AS listino_versione_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'MERCE') AS natura_merce_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'SERVIZIO_UNA_TANTUM') AS natura_serv_id;

-- ⭐ 2026-08-26 — IL BILLING ACCOUNT DELL'EMITTENTE B, e perche' serve.
--   La commessa B nasceva sul billing account di A con l'emittente di B: uno
--   stato che il modello non ammette (vendite.trgfn_commesse_guard_emittente_ba,
--   20260826-40). L'emittente della commessa si DERIVA dal cliente, quindi per
--   avere una commessa di B serve un cliente di B: dal 2026-10-24 si costruisce
--   (prima si cercava fra i dati, e senza i test 19-20 andavano in skip).
ALTER TABLE tmp_df_refs ADD COLUMN ba_b_id bigint;

UPDATE tmp_df_refs r
   SET ba_b_id = c.billing_account_id
  FROM tmp_df_cli_b c;

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
-- Emittente A: il resolver commesse (20260703-60) filtra per scope emittente
-- da GUC; l'operatore di test e' whitelistato su A, quindi vede questa commessa.
-- rev 2026-10-24: nasce dalla madre via dbops.fn_pgtap_crea_commessa, in
--   BOZZA (prima: INSERT a mano nel «primo stato per id»).
-- rev 2026-10-24 (§4-octies): le attivita' le scrive
--   dbops.fn_pgtap_crea_commessa_attivita. Quella della riga di servizio
--   porta la sorgente (chiave dal dominio); tipo documento fiscale e valuta li
--   deriva la madre, l'unita' di misura l'articolo.
CREATE TEMP TABLE tmp_df_cmd AS
SELECT * FROM dbops.fn_pgtap_crea_commessa(
                 'dash fatturazione A', 'BOZZA', (SELECT billing_account_id FROM tmp_df_refs));

CREATE TEMP TABLE tmp_df_commessa AS
SELECT commessa_id AS id FROM tmp_df_cmd;

CREATE TEMP TABLE tmp_df_att_serv AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_df_commessa),
    p_prezzo_snapshot    => 30.000000,
    p_articolo_id        => (SELECT art_serv_id FROM tmp_df_refs),
    p_sorgente_codice    => 'PREVENTIVO',
    p_sorgente_uid       => (SELECT uid::text FROM tmp_df_prev),
    p_sorgente_riga_id   => (SELECT id FROM tmp_df_riga_serv_emessa),
    p_quantita           => 2,
    p_stato_approvazione => 'BOZZA',
    p_stato_emissione    => 'EMESSA',
    p_competenza_dal     => DATE '2080-01-01',
    p_competenza_al      => DATE '2080-12-31');

-- Attivita NON_EMESSA per il servizio residuo: NON conta come transito
-- (predicato canonico EMESSA) e alimenta il caso COMMESSE fermo.
-- ⚠️ rev 2026-10-24 (§4-octies): era una riga PREVENTIVO con una chiave
--   inventata, che nessuna riga del preventivo produce; ora e' una riga della
--   commessa (sorgente COMMESSA, chiave del builder). Il residuo del
--   preventivo (30) resta, perche' la riga residua non ha attivita'.
CREATE TEMP TABLE tmp_df_att_ferma AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_df_commessa),
    p_prezzo_snapshot    => 10.000000,
    p_articolo_id        => (SELECT art_serv_id FROM tmp_df_refs),
    p_quantita           => 3,
    p_stato_approvazione => 'BOZZA',
    p_stato_emissione    => 'NON_EMESSA',
    p_competenza_dal     => DATE '2080-01-01',
    p_competenza_al      => DATE '2080-12-31');

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

-- rev 2026-10-25 (brief-modello-documento-vendita §9): lo stato dell'ordine
-- si cambia solo dal suo verbo (la porta ferma l'UPDATE diretto): la
-- conferma passa da porta_a_stato, sotto il guard di transizione.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ordini'::regclass, (SELECT id FROM tmp_df_ordine), 'CONFERMATO');

SELECT is(
  (SELECT v.motivo_fermo FROM vendite.vw_dash_fatturazione_ordini v
    WHERE v.documento_id = (SELECT id FROM tmp_df_ordine)),
  'PUSH_NON_ESEGUITO',
  '6. Ordine CONFERMATO senza push: motivo PUSH_NON_ESEGUITO'
);

-- Push del ramo ordine: attivita EMESSA con segment_key ORDINE_VENDITA:<uid>:R:<riga>.
-- ⚠️ rev 2026-10-24 (§4-octies): dal builder, con la sorgente ORDINE_VENDITA
--   (uid dell'ordine, come il push). Prima la chiave era dell'ordine e la
--   sorgente il PREVENTIVO: una riga che nessun push scrive.
CREATE TEMP TABLE tmp_df_att_ordine AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_df_commessa),
    p_prezzo_snapshot    => 50.000000,
    p_articolo_id        => (SELECT art_merce_id FROM tmp_df_refs),
    p_sorgente_codice    => 'ORDINE_VENDITA',
    p_sorgente_uid       => (SELECT uid::text FROM tmp_df_ordine),
    p_sorgente_riga_id   => (SELECT riga_id FROM tmp_df_ordine),
    p_quantita           => 1,
    p_stato_approvazione => 'APPROVATA',
    p_stato_emissione    => 'EMESSA',
    p_competenza_dal     => DATE '2080-02-01',
    p_competenza_al      => DATE '2080-02-28');

-- Le tre attivita' di A scritte davvero, con la chiave del dominio dove c'e'
-- la sorgente (controllo, non test).
DO $chk$ BEGIN
  IF (SELECT count(*) FROM vendite.commesse_attivita ca
       WHERE ca.commessa_id = (SELECT id FROM tmp_df_commessa)
         AND ((ca.id = (SELECT attivita_id FROM tmp_df_att_serv)
               AND ca.segment_key = script.fn_segment_key('PREVENTIVO', (SELECT uid::text FROM tmp_df_prev),
                                                          (SELECT id FROM tmp_df_riga_serv_emessa)))
           OR (ca.id = (SELECT attivita_id FROM tmp_df_att_ferma) AND ca.stato_emissione = 'NON_EMESSA')
           OR (ca.id = (SELECT attivita_id FROM tmp_df_att_ordine)
               AND ca.segment_key = script.fn_segment_key('ORDINE_VENDITA', (SELECT uid::text FROM tmp_df_ordine),
                                                          (SELECT riga_id FROM tmp_df_ordine))))) <> 3 THEN
    RAISE EXCEPTION 'fixture: attese 3 attivita'' dal builder sulla commessa A';
  END IF;
END $chk$;

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
-- rev 2026-10-24 (Q-2): nasce dalla PUSH dell'offerta, come in produzione
--   (dbops.fn_pgtap_crea_contratto col quarto parametro).
CREATE TEMP TABLE tmp_df_contr_vivo AS
SELECT * FROM dbops.fn_pgtap_crea_contratto(
                 'dash fatturazione figlio vivo', 'DRAFT', NULL,
                 (SELECT offerta_id FROM tmp_df_offerte WHERE slot = 'ACC_FIGLIO_VIVO'));

-- Figlio ABORTITO: contratto ANNULLATO da offerta (snapshot -> true).
-- rev 2026-10-24 (Q-2): nasce dalla PUSH e il builder lo annulla col verbo
--   vendite.fn_annulla_contratto, dichiarando il legame con l'offerta.
CREATE TEMP TABLE tmp_df_k_abortito AS
SELECT * FROM dbops.fn_pgtap_crea_contratto(
                 'dash fatturazione figlio abortito', 'ANNULLATO', NULL,
                 (SELECT offerta_id FROM tmp_df_offerte WHERE slot = 'ACC_FIGLIO_ABORTITO'));

CREATE TEMP TABLE tmp_df_contr_abortito AS
SELECT contratto_id AS id FROM tmp_df_k_abortito;

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
-- rev 2026-10-24 (Q-2): dal builder, dalla madre di produzione, sul cliente
--   di A.
-- rev 2026-10-24 (R-2): nasce ATTIVO col periodo multi-mese (da due mesi fa,
--   aperto), la data e il listino della fixture, dal builder.
CREATE TEMP TABLE tmp_df_k AS
SELECT * FROM dbops.fn_pgtap_crea_contratto(
                 'dash fatturazione', 'ATTIVO', (SELECT billing_account_id FROM tmp_df_refs), NULL,
                 (date_trunc('month', script.fn_data_operativa()) - interval '2 months')::date,
                 NULL,
                 (date_trunc('month', script.fn_data_operativa()) - interval '2 months')::date,
                 (SELECT listino_id FROM tmp_df_refs));

CREATE TEMP TABLE tmp_df_contratto AS
SELECT k.id, k.uid FROM vendite.contratti k WHERE k.id = (SELECT contratto_id FROM tmp_df_k);

-- ============================================================
-- 12-14) Area CONTRATTI (de-esplosa — DL-12; giudizio dal push, 20261031-04)
-- ============================================================
SELECT ok(
  (SELECT count(*) = 1
      AND bool_and(v.is_transitato)
      AND bool_and(v.unita_transitate = 1)
      AND bool_and(v.motivo_fermo IS NULL)
      AND bool_and(v.unita_totali = 1)
      AND bool_and(v.competenza_mese IS NULL)
      AND bool_and(v.data_riferimento = (date_trunc('month', script.fn_data_operativa()) - interval '2 months')::date)
     FROM vendite.vw_dash_fatturazione_contratti v
    WHERE v.documento_id = (SELECT id FROM tmp_df_contratto)),
  '12. Contratto ATTIVO multi-mese senza niente da mandare: 1 SOLA riga (de-esploso), transitato, motivo NULL, data_riferimento = valido_dal'
);

-- Canone del mese generato: attivita EMESSA con sorgente CONTRATTO. Con la
-- de-esplosione (DL-12) resta 1 riga; il giudizio e' del push (20261031-04,
-- rev 2026-10-31): l'attivita' scritta a mano non lo cambia.
-- ⚠️ rev 2026-10-24 (§4-octies): resta scritta a mano, perche' la chiave del
--   canone porta il mese (:M:<AAAA-MM>) e il builder non lo passa al
--   costruttore; la chiave pero' la compone script.fn_segment_key.
INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key,
  articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
  competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
  pricing_mode, stato_approvazione, stato_emissione,
  sorgente_tipo_id, sorgente_uid)
SELECT
  (SELECT id FROM tmp_df_commessa),
  script.fn_segment_key('CONTRATTO', (SELECT uid FROM tmp_df_contratto)::text, 0,
                        date_trunc('month', script.fn_data_operativa())::date),
  r.art_serv_id, r.istanza_utility_id, script.fn_data_operativa(), r.uom_id, 1,
  date_trunc('month', script.fn_data_operativa())::date,
  date_trunc('month', script.fn_data_operativa())::date,
  (date_trunc('month', script.fn_data_operativa()) + interval '1 month - 1 day')::date,
  r.tipo_doc_fiscale_id, r.valuta_id, 25.000000,
  'FIXED', 'APPROVATA', 'EMESSA',
  r.sorg_contratto_id, (SELECT uid FROM tmp_df_contratto)::text
FROM tmp_df_refs r;

SELECT ok(
  (SELECT count(*) = 1 AND bool_and(v.is_transitato)
      AND bool_and(v.motivo_fermo IS NULL)
     FROM vendite.vw_dash_fatturazione_contratti v
    WHERE v.documento_id = (SELECT id FROM tmp_df_contratto)),
  '13. Contratto con canone EMESSO in commessa: sempre 1 riga (DL-12), giudizio del push invariato (transitato)'
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
-- L'operatore e' quello costruito con l'azienda A (rev 2026-10-24): prima si
-- pescava il primo OPERATORE non super per id.
-- rev 2026-10-24 (R-9): la whitelist su A e il contesto li da' il mondo dal
-- primo blocco; la riscrittura a mano e il set_config sono usciti.
-- ============================================================
CREATE TEMP TABLE tmp_df_op AS
SELECT id.auth_user_id AS user_id
  FROM anagrafiche.identita_digitali id
 WHERE id.auth_user_id = (SELECT auth_user_id FROM tmp_df_mondo_a)
   AND id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND id.attivo = true
   AND NOT EXISTS (
       SELECT 1 FROM config.profili_accesso_bindings pab
       JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
       WHERE pab.identita_digitale_id = id.id
         AND pab.attivo = true
         AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso);

SELECT ok(
  (SELECT user_id IS NOT NULL FROM tmp_df_op),
  '14b. Trovato un operatore OPERATORE non-super per il test scope commesse'
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
-- rev 2026-10-24 (R-9): la commessa di B nasce dal builder, in BOZZA, sotto
--   il contesto dell'operatore di B (il builder verifica che il cliente sia
--   dell'azienda di chi agisce); la sua attivita' pure. Poi si torna ad A.
-- rev 2026-10-24 (§4-octies): l'attivita' di B dal builder, sorgente COMMESSA
--   (prima: chiave inventata e sorgente il preventivo di A, su una commessa
--   di B, una riga che il dominio non scrive).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_df_mondo_b)); END $ctx$;

CREATE TEMP TABLE tmp_df_cmd_b AS
SELECT * FROM dbops.fn_pgtap_crea_commessa(
                 'dash fatturazione B', 'BOZZA', (SELECT ba_b_id FROM tmp_df_refs));

CREATE TEMP TABLE tmp_df_commessa_b AS
SELECT commessa_id AS id FROM tmp_df_cmd_b;

CREATE TEMP TABLE tmp_df_att_b AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_df_commessa_b),
    p_prezzo_snapshot    => 77.000000,
    p_articolo_id        => (SELECT art_serv_id FROM tmp_df_refs),
    p_quantita           => 1,
    p_stato_approvazione => 'APPROVATA',
    p_stato_emissione    => 'EMESSA',
    p_competenza_dal     => DATE '2080-05-01',
    p_competenza_al      => DATE '2080-05-31');

-- L'attivita' di B scritta davvero: senza, il 20 sarebbe verde per sottrazione.
DO $chk$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM vendite.commesse_attivita ca
                   JOIN tmp_df_att_b t ON t.attivita_id = ca.id
                  WHERE ca.commessa_id = (SELECT id FROM tmp_df_commessa_b)
                    AND ca.competenza_mese = DATE '2080-05-01' AND ca.stato_emissione = 'EMESSA') THEN
    RAISE EXCEPTION 'fixture: manca l''attivita'' della commessa B';
  END IF;
END $chk$;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_df_mondo_a)); END $ctx$;

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

-- Le attivita' void/edge su commessa A, un mese ciascuna, dal builder (rev
-- 2026-10-24 §4-octies: prima INSERT a mano con chiavi inventate e sorgente
-- il preventivo; ora sorgente COMMESSA e chiave del builder). Gli stati sono
-- il caso: li dichiara il test.
-- 2080-06: EMESSA(100) + ANNULLATA(999) + RIFIUTATA/NON_EMESSA(888)
CREATE TEMP TABLE tmp_df_att_v6e AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_df_commessa),
    p_prezzo_snapshot    => 100.000000,
    p_articolo_id        => (SELECT art_serv_id FROM tmp_df_refs),
    p_quantita           => 1,
    p_stato_approvazione => 'APPROVATA',
    p_stato_emissione    => 'EMESSA',
    p_competenza_dal     => DATE '2080-06-01',
    p_competenza_al      => DATE '2080-06-30');

CREATE TEMP TABLE tmp_df_att_v6a AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_df_commessa),
    p_prezzo_snapshot    => 999.000000,
    p_articolo_id        => (SELECT art_serv_id FROM tmp_df_refs),
    p_quantita           => 1,
    p_stato_approvazione => 'APPROVATA',
    p_stato_emissione    => 'ANNULLATA',
    p_competenza_dal     => DATE '2080-06-01',
    p_competenza_al      => DATE '2080-06-30');

CREATE TEMP TABLE tmp_df_att_v6r AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_df_commessa),
    p_prezzo_snapshot    => 888.000000,
    p_articolo_id        => (SELECT art_serv_id FROM tmp_df_refs),
    p_quantita           => 1,
    p_stato_approvazione => 'RIFIUTATA',
    p_stato_emissione    => 'NON_EMESSA',
    p_competenza_dal     => DATE '2080-06-01',
    p_competenza_al      => DATE '2080-06-30');

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
CREATE TEMP TABLE tmp_df_att_v7a AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_df_commessa),
    p_prezzo_snapshot    => 555.000000,
    p_articolo_id        => (SELECT art_serv_id FROM tmp_df_refs),
    p_quantita           => 1,
    p_stato_approvazione => 'BOZZA',
    p_stato_emissione    => 'ANNULLATA',
    p_competenza_dal     => DATE '2080-07-01',
    p_competenza_al      => DATE '2080-07-31');

-- La ANNULLATA del 2080-07 scritta davvero: senza, il 25 sarebbe verde per
-- sottrazione (controllo, non test).
DO $chk$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM vendite.commesse_attivita ca
                   JOIN tmp_df_att_v7a t ON t.attivita_id = ca.id
                  WHERE ca.competenza_mese = DATE '2080-07-01' AND ca.stato_emissione = 'ANNULLATA') THEN
    RAISE EXCEPTION 'fixture: manca l''attivita'' ANNULLATA del 2080-07';
  END IF;
END $chk$;

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
CREATE TEMP TABLE tmp_df_att_v8er AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_df_commessa),
    p_prezzo_snapshot    => 200.000000,
    p_articolo_id        => (SELECT art_serv_id FROM tmp_df_refs),
    p_quantita           => 1,
    p_stato_approvazione => 'RIFIUTATA',
    p_stato_emissione    => 'EMESSA',
    p_competenza_dal     => DATE '2080-08-01',
    p_competenza_al      => DATE '2080-08-31');

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
