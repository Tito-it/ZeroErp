-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- ⚠️ rev 2026-11-18 (brief-db-seed-primo-impianto-non-si-riscrive, Q21): il
--   caso della riga a natura NULL (pregresso) e' uscito in
--   test-righe-natura-vendita-legacy-v1, che gira come owner. La riga si
--   costruisce solo dalla porta del lock, e dal 20261117-07 la porta si apre
--   solo alla sessione del migratore: come app non si puo' piu' costruire.
-- rev 2026-10-24 (brief-modello-documento-vendita R-6/Q-4): cliente ed
--   emittente dal mondo costruito (dbops.fn_pgtap_crea_mondo_cliente), i due
--   articoli da dbops.fn_pgtap_crea_articolo con la natura del caso (MERCE,
--   SERVIZIO_UNA_TANTUM). Prima si pescavano il primo billing account, il
--   primo emittente e «i primi due articoli per id», e gli si riscriveva la
--   natura: il primo per id e' un articolo-onere (ONERE_SENZA_CONTRATTO) e il
--   file moriva li'. Numero e stato delle testate non si scrivono piu': li
--   assegnano il dominio e il trigger della nascita.
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_list_preventivi_da_pushare natura-aware (20260609-09).
--       Il push su commessa deve includere SOLO le righe con natura
--       destinazione_tipo='COMMESSA' (natura NULL = pregresso, inclusa: in
--       test-righe-natura-vendita-legacy-v1) ed
--       ESCLUDERE la merce (destinazione ORDINE), che va su
--       fn_push_preventivo_a_ordine. Niente doppio routing.
--
-- Indice test (1..3):
--   1) preventivo misto -> la riga SERVIZIO_UNA_TANTUM e' inclusa
--   2) preventivo misto -> la riga MERCE e' esclusa
--   3) preventivo di sole righe merce -> lista vuota
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

SELECT plan(3);

-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): le testate nascono DRAFT, prendono le righe, poi passano ad ACCETTATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le righe non si scrivono piu' (20261008-91).
-- ⭐ rev 2026-10-24 (Q-4): il mondo si COSTRUISCE. Il cliente e l'emittente
--   da dbops.fn_pgtap_crea_mondo_cliente (col contesto aperto riusa l'azienda
--   di chi agisce: emittente e BA d'accordo per costruzione); gli articoli
--   nascono con la natura del caso, che e' la condizione del test:
--   art_merce -> MERCE (ORDINE), art_serv -> SERVIZIO_UNA_TANTUM (COMMESSA).
--   ⛔ Cio' che il builder scrive si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('list prev natura aware');

CREATE TEMP TABLE tmp_refs AS
SELECT
  m.billing_account_id,
  m.utility_id,
  m.istanza_utility_id,
  dbops.fn_pgtap_crea_articolo('PGT-LPPN-MERCE',
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                               WHERE codice_interno = 'MERCE')) AS art_merce_id,
  dbops.fn_pgtap_crea_articolo('PGT-LPPN-SERV', false,
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                               WHERE codice_interno = 'SERVIZIO_UNA_TANTUM')) AS art_serv_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  m.emittente_fiscale_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id
FROM tmp_mondo m;

-- Preventivo MISTO ACCETTATO: riga servizio + riga merce.
CREATE TEMP TABLE tmp_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_list_natura_aware'), r.emittente_fiscale_id
    FROM tmp_refs r
  RETURNING id)
SELECT * FROM ins;

-- riga servizio (natura COMMESSA)
CREATE TEMP TABLE tmp_riga_serv AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 2.000000, 30.000000, r.iva_id, true
    FROM tmp_prev p, tmp_refs r
  RETURNING id)
SELECT * FROM ins;

-- riga merce (natura ORDINE)
CREATE TEMP TABLE tmp_riga_merce AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_merce_id, 2.000000, 30.000000, r.iva_id, true
    FROM tmp_prev p, tmp_refs r
  RETURNING id)
SELECT * FROM ins;

DO $porta$ BEGIN PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_prev), 'ACCETTATO'); END $porta$;

-- Preventivo di SOLE merci (per test 3).
CREATE TEMP TABLE tmp_prev_merce AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_list_natura_aware_merce'), r.emittente_fiscale_id
    FROM tmp_refs r
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
SELECT p.id, r.art_merce_id, 2.000000, 30.000000, r.iva_id, true
  FROM tmp_prev_merce p, tmp_refs r;
DO $porta$ BEGIN PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_prev_merce), 'ACCETTATO'); END $porta$;

-- ============================================================
-- 1) riga SERVIZIO_UNA_TANTUM inclusa
-- ============================================================
SELECT ok(
  EXISTS(SELECT 1 FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, NULL, (SELECT id FROM tmp_prev)) f
          WHERE f.riga_id = (SELECT id FROM tmp_riga_serv)),
  '1) preventivo misto -> riga SERVIZIO_UNA_TANTUM inclusa'
);

-- ============================================================
-- 2) riga MERCE esclusa
-- ============================================================
SELECT ok(
  NOT EXISTS(SELECT 1 FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, NULL, (SELECT id FROM tmp_prev)) f
              WHERE f.riga_id = (SELECT id FROM tmp_riga_merce)),
  '2) preventivo misto -> riga MERCE esclusa (va su ordine)'
);

-- ============================================================
-- 3) preventivo di sole merci -> lista vuota
-- ============================================================
SELECT is(
  (SELECT count(*) FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, NULL, (SELECT id FROM tmp_prev_merce))),
  0::bigint,
  '3) preventivo di sole merci -> lista push commessa vuota'
);

SELECT * FROM finish();
ROLLBACK;
