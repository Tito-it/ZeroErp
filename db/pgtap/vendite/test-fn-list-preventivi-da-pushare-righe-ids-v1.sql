-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2e): le chiavi del push col codice della sorgente (PREVENTIVO:, DDT_VENDITA:, ORDINE_VENDITA:, CONTRATTO:, ATTIVITA_CONSUMI:), stessa forma di script.fn_segment_key carattere per carattere.
-- rev 2026-10-24 (brief-modello-documento-vendita R-6/Q-4): il mondo si
--   costruisce. Cliente ed emittente da dbops.fn_pgtap_crea_mondo_cliente,
--   i due articoli da dbops.fn_pgtap_crea_articolo con la natura del caso
--   (MERCE, SERVIZIO_UNA_TANTUM), la commessa del test 5 da
--   dbops.fn_pgtap_crea_commessa sul cliente del mondo. Prima si pescavano il
--   primo billing account, il primo emittente, «i primi due articoli per id»
--   (riscrivendone la natura: il primo e' un articolo-onere e il file moriva
--   li'), la prima unita' di misura e il primo stato commessa. Numero e stato
--   della testata non si scrivono piu': li assegnano il dominio e il trigger
--   della nascita.
-- rev 2026-10-24 (brief-modello-documento-vendita §4-octies): l'attivita' EMESSA della riga B (test 5) la scrive dbops.fn_pgtap_crea_commessa_attivita con la sorgente, invece dell'INSERT con la chiave composta a mano; uom e tipo documento non si pescano piu' (li derivano articolo e madre).
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_list_preventivi_da_pushare con p_righe_ids
--       (20260612-06): push commessa per sottoinsieme righe,
--       simmetrico al ramo ordine. Brief:
--       brief-db-smistamento-preventivi.md, Richiesta C.
--
-- Indice test (0..5):
--   0) Precondizioni (refs + nature)
--   1) p_righe_ids=[A] -> solo la riga A
--   2) p_righe_ids=[A, merce] -> solo A (skip silenzioso riga non eleggibile)
--   3) p_righe_ids senza p_preventivo_id -> throws (E_PUSH_RIGHE_IDS_SENZA_PREVENTIVO)
--   4) p_righe_ids NULL -> comportamento invariato (tutte le eleggibili: A+B)
--   5) p_righe_ids=[B] con B gia' EMESSA -> lista vuota (skip silenzioso)
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

SELECT plan(6);

-- ============================================================
-- 0) Riferimenti minimi + classificazione nature
-- ============================================================
-- ⭐ rev 2026-10-24 (Q-4): il cliente e l'emittente da
--   dbops.fn_pgtap_crea_mondo_cliente (col contesto aperto riusa l'azienda di
--   chi agisce: emittente e BA d'accordo per costruzione); gli articoli
--   nascono con la natura del caso: art_merce -> MERCE (ORDINE), art_serv ->
--   SERVIZIO_UNA_TANTUM (COMMESSA). ⛔ Cio' che il builder scrive si legge in
--   un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_ri_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('list prev righe ids');

CREATE TEMP TABLE tmp_ri_art AS
SELECT
  dbops.fn_pgtap_crea_articolo('PGT-LPPR-MERCE',
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                               WHERE codice_interno = 'MERCE')) AS art_merce_id,
  dbops.fn_pgtap_crea_articolo('PGT-LPPR-SERV', false,
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                               WHERE codice_interno = 'SERVIZIO_UNA_TANTUM')) AS art_serv_id;

CREATE TEMP TABLE tmp_ri_refs AS
SELECT
  m.billing_account_id,
  m.utility_id,
  m.istanza_utility_id,
  x.art_merce_id,
  x.art_serv_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'ACCETTATO' AND s.attivo IS TRUE) AS stato_accettato_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  m.emittente_fiscale_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'MERCE') AS natura_merce_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'SERVIZIO_UNA_TANTUM') AS natura_serv_id
FROM tmp_ri_mondo m, tmp_ri_art x;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND art_merce_id IS NOT NULL
      AND art_serv_id IS NOT NULL AND stato_accettato_id IS NOT NULL
      AND natura_merce_id IS NOT NULL AND natura_serv_id IS NOT NULL
     FROM tmp_ri_refs),
  '0. Precondizioni soddisfatte'
);

-- Preventivo ACCETTATO: servizio A + servizio B + merce.
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT, prende le tre righe, poi passa ad ACCETTATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le righe non si scrivono piu' (20261008-91).
CREATE TEMP TABLE tmp_ri_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_list_righe_ids'), r.emittente_fiscale_id
    FROM tmp_ri_refs r
  RETURNING id, uid)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ri_riga_a AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 1.000000, 10.000000, r.iva_id, true
    FROM tmp_ri_prev p, tmp_ri_refs r
  RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ri_riga_b AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 2.000000, 20.000000, r.iva_id, true
    FROM tmp_ri_prev p, tmp_ri_refs r
  RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ri_riga_merce AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_merce_id, 1.000000, 50.000000, r.iva_id, true
    FROM tmp_ri_prev p, tmp_ri_refs r
  RETURNING id)
SELECT * FROM ins;

DO $porta$ BEGIN PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_ri_prev), 'ACCETTATO'); END $porta$;

-- ============================================================
-- 1) p_righe_ids=[A] -> solo la riga A
-- ============================================================
SELECT ok(
  (SELECT count(*) = 1 AND bool_and(f.riga_id = (SELECT id FROM tmp_ri_riga_a))
     FROM vendite.fn_list_preventivi_da_pushare(
            NULL, NULL, NULL,
            (SELECT id FROM tmp_ri_prev),
            ARRAY[(SELECT id FROM tmp_ri_riga_a)]) f),
  '1. Sottoinsieme [A]: ritorna solo la riga A'
);

-- ============================================================
-- 2) p_righe_ids=[A, merce] -> solo A (skip silenzioso non eleggibile)
-- ============================================================
SELECT ok(
  (SELECT count(*) = 1 AND bool_and(f.riga_id = (SELECT id FROM tmp_ri_riga_a))
     FROM vendite.fn_list_preventivi_da_pushare(
            NULL, NULL, NULL,
            (SELECT id FROM tmp_ri_prev),
            ARRAY[(SELECT id FROM tmp_ri_riga_a), (SELECT id FROM tmp_ri_riga_merce)]) f),
  '2. Sottoinsieme [A, merce]: la merce e'' skippata in silenzio (D5), torna solo A'
);

-- ============================================================
-- 3) p_righe_ids senza p_preventivo_id -> throws
-- ============================================================
SELECT throws_ok(
  format('SELECT * FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, NULL, NULL, ARRAY[%s]::bigint[])',
         (SELECT id FROM tmp_ri_riga_a)),
  NULL, NULL,
  '3. p_righe_ids senza p_preventivo_id rifiutato (E_PUSH_RIGHE_IDS_SENZA_PREVENTIVO)'
);

-- ============================================================
-- 4) p_righe_ids NULL -> invariato (tutte le eleggibili: A+B)
-- ============================================================
SELECT is(
  (SELECT count(*)::integer
     FROM vendite.fn_list_preventivi_da_pushare(
            NULL, NULL, NULL, (SELECT id FROM tmp_ri_prev)) f),
  2,
  '4. p_righe_ids NULL: comportamento invariato (A+B eleggibili, merce esclusa)'
);

-- ============================================================
-- 5) p_righe_ids=[B] con B gia' EMESSA -> lista vuota
-- ============================================================
-- ⭐ rev 2026-10-24 (Q-4): la commessa nasce dalla madre del dominio
--   (dbops.fn_pgtap_crea_commessa), sul cliente del mondo, nello stato
--   iniziale. Prima era un INSERT diretto col primo stato commessa per id.
--   L'attivita' EMESSA della riga B resta scritta qui: e' il caso del test.
CREATE TEMP TABLE tmp_ri_commessa AS
SELECT c.commessa_id AS id
  FROM dbops.fn_pgtap_crea_commessa('list prev righe ids', NULL,
         (SELECT billing_account_id FROM tmp_ri_refs)) c;

-- rev 2026-10-24 (§4-octies): l'attivita' della riga B la scrive il builder
--   con la sorgente; la chiave la compone il dominio (script.fn_segment_key).
--   Tipo documento fiscale e valuta non si passano: li deriva la madre.
CREATE TEMP TABLE tmp_ri_att AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_ri_commessa),
    p_prezzo_snapshot    => 20.000000,
    p_articolo_id        => (SELECT art_serv_id FROM tmp_ri_refs),
    p_sorgente_codice    => 'PREVENTIVO',
    p_sorgente_chiave    => (SELECT uid::text FROM tmp_ri_prev),
    p_sorgente_riga_id   => (SELECT id FROM tmp_ri_riga_b),
    p_quantita           => 2,
    p_stato_approvazione => 'BOZZA',
    p_stato_emissione    => 'EMESSA',
    p_competenza_dal     => DATE '2080-01-01',
    p_competenza_al      => DATE '2080-12-31');

-- La riga scritta davvero, sulla chiave della riga B (controllo, non test).
DO $chk$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM vendite.commesse_attivita ca
                   JOIN tmp_ri_att t ON t.attivita_id = ca.id
                  WHERE ca.stato_emissione = 'EMESSA'
                    AND ca.segment_key = script.fn_segment_key('PREVENTIVO',
                                           (SELECT uid FROM tmp_ri_prev)::text,
                                           (SELECT id FROM tmp_ri_riga_b))) THEN
    RAISE EXCEPTION 'fixture: manca l''attivita'' EMESSA della riga B';
  END IF;
END $chk$;

SELECT is(
  (SELECT count(*)::integer
     FROM vendite.fn_list_preventivi_da_pushare(
            NULL, NULL, NULL,
            (SELECT id FROM tmp_ri_prev),
            ARRAY[(SELECT id FROM tmp_ri_riga_b)]) f),
  0,
  '5. Sottoinsieme [B] con B gia'' EMESSA: lista vuota (skip silenzioso, idempotenza a monte)'
);

SELECT * FROM finish();
ROLLBACK;
