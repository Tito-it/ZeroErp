-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-24 (brief-modello-documento-vendita R-6/Q-4): cliente ed
--   emittente dal mondo costruito (dbops.fn_pgtap_crea_mondo_cliente); prima
--   erano il primo billing account e il primo emittente attivo del database,
--   che non vanno d'accordo (il file moriva col «valore nullo» di
--   billing_account_id) e su un database ricostruito non ci sono. Le testate
--   restano scritte qui, perche' validita', competenza e data SONO il caso;
--   numero e stato non si scrivono piu': li assegnano il dominio e il
--   trigger della nascita.
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_list_preventivi_da_pushare competenza (20260610-06).
--       Fix brief competenza 10-06-2026:
--         - competenza_dal/al NOT NULL-safe (commesse_attivita NOT NULL):
--           fallback validita -> competenza_mese -> data; GREATEST dal<=al.
--         - competenza_mese policy-aware: COALESCE(p.competenza_mese, derivato).
--
-- Indice test (1..5):
--   1) preventivo senza validita -> competenza_dal = p.data (no NULL crash)
--   2) preventivo senza validita -> competenza_al  = p.data (push NOT NULL-safe)
--   3) preventivo DIFFERITA (competenza_mese policy) -> mese proiettato = policy
--   4) pregresso (competenza_mese NULL) -> mese derivato da validita_dal
--   5) edge validita_dal NULL + validita_al SET -> competenza_dal <= competenza_al
--      (GREATEST; skip se chk_preventivi_validita vieta lo stato)
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

SELECT plan(5);

-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): le testate nascono DRAFT, prendono la riga, poi passano ad ACCETTATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le righe non si scrivono piu' (20261008-91).
-- ⭐ rev 2026-10-24 (Q-4): il cliente e l'emittente si COSTRUISCONO.
--   dbops.fn_pgtap_crea_mondo_cliente, col contesto gia' aperto, riusa
--   l'azienda di chi agisce e le lega un cliente nuovo: emittente e BA vanno
--   d'accordo per costruzione. ⛔ Cio' che il builder scrive si legge in
--   un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('list prev competenza');

CREATE TEMP TABLE tmp_refs AS
SELECT
  m.billing_account_id,
  m.utility_id,
  m.istanza_utility_id,
  -- ⛔ rev 2026-10-13: l'articolo si COSTRUISCE. Prima era il primo del catalogo
  --   per id, e gli si cambiava la natura qui sotto: su dbdev e' ART_TEST_BASE,
  --   gia' usato, e dal 20261013-48 un articolo usato non cambia natura (A-10 di
  --   brief-db-articoli-ammessi-per-documento).
  -- Nasce SERVIZIO_UNA_TANTUM: natura destinazione COMMESSA, per essere incluso.
  dbops.fn_pgtap_crea_articolo('PGT-LPPC-SERV', false,
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                               WHERE codice_interno = 'SERVIZIO_UNA_TANTUM')) AS art_serv_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  m.emittente_fiscale_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id
FROM tmp_mondo m;

-- ============================================================
-- Preventivo 1: SENZA validita (validita_dal/al NULL, competenza_mese NULL).
-- data = 2080-06-10. Atteso: competenza_dal = competenza_al = 2080-06-10.
-- ============================================================
CREATE TEMP TABLE tmp_noval AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, competenza_mese, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT r.billing_account_id, r.istanza_utility_id, r.utility_id,
         NULL, NULL, NULL, r.valuta_id, DATE '2080-06-10',
         false, false, jsonb_build_object('test_scope','pgtap_competenza'), r.emittente_fiscale_id
    FROM tmp_refs r
  RETURNING id)
SELECT * FROM ins;
INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
SELECT p.id, r.art_serv_id, 1.000000, 10.000000, r.iva_id, true FROM tmp_noval p, tmp_refs r;
DO $porta$ BEGIN PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_noval), 'ACCETTATO'); END $porta$;

-- ============================================================
-- Preventivo 2: DIFFERITA. competenza_mese policy = 2080-09-01 (primo del mese),
-- validita_dal = 2080-06-15 (derivato sarebbe 2080-06-01). Atteso: mese = 2080-09-01.
-- ============================================================
CREATE TEMP TABLE tmp_diff AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, competenza_mese, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-06-15', DATE '2080-06-20', DATE '2080-09-01', r.valuta_id, DATE '2080-06-10',
         false, false, jsonb_build_object('test_scope','pgtap_competenza'), r.emittente_fiscale_id
    FROM tmp_refs r
  RETURNING id)
SELECT * FROM ins;
INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
SELECT p.id, r.art_serv_id, 1.000000, 10.000000, r.iva_id, true FROM tmp_diff p, tmp_refs r;
DO $porta$ BEGIN PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_diff), 'ACCETTATO'); END $porta$;

-- ============================================================
-- Preventivo 3: PREGRESSO. competenza_mese NULL, validita_dal = 2080-06-15.
-- Atteso: mese derivato = date_trunc('month', 2080-06-15) = 2080-06-01.
-- ============================================================
CREATE TEMP TABLE tmp_preg AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, competenza_mese, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-06-15', DATE '2080-06-20', NULL, r.valuta_id, DATE '2080-06-10',
         false, false, jsonb_build_object('test_scope','pgtap_competenza'), r.emittente_fiscale_id
    FROM tmp_refs r
  RETURNING id)
SELECT * FROM ins;
INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
SELECT p.id, r.art_serv_id, 1.000000, 10.000000, r.iva_id, true FROM tmp_preg p, tmp_refs r;
DO $porta$ BEGIN PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_preg), 'ACCETTATO'); END $porta$;

-- ============================================================
-- Preventivo 5 (edge): validita_dal NULL + validita_al SET. Insert protetto da
-- savepoint: se chk_preventivi_validita lo vieta, lo stato e' impossibile -> skip.
-- ============================================================
CREATE TEMP TABLE tmp_edge(prev_id bigint, insertable boolean);
DO $edge$
DECLARE v_prev bigint;
BEGIN
  INSERT INTO vendite.preventivi (
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, competenza_mese, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT r.billing_account_id, r.istanza_utility_id, r.utility_id,
         NULL, DATE '2080-07-15', DATE '2080-09-01', r.valuta_id, DATE '2080-06-10',
         false, false, jsonb_build_object('test_scope','pgtap_competenza'), r.emittente_fiscale_id
    FROM tmp_refs r
  RETURNING id INTO v_prev;

  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT v_prev, r.art_serv_id, 1.000000, 10.000000, r.iva_id, true FROM tmp_refs r;
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', v_prev, 'ACCETTATO');

  INSERT INTO tmp_edge VALUES (v_prev, true);
EXCEPTION WHEN check_violation THEN
  INSERT INTO tmp_edge VALUES (NULL, false);
END
$edge$;

-- ============================================================
-- 1) senza validita -> competenza_dal = data
-- ============================================================
SELECT is(
  (SELECT competenza_dal FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, NULL, (SELECT id FROM tmp_noval))),
  DATE '2080-06-10',
  '1) preventivo senza validita -> competenza_dal = p.data (no NULL crash)'
);

-- ============================================================
-- 2) senza validita -> competenza_al = data (push NOT NULL-safe)
-- ============================================================
SELECT is(
  (SELECT competenza_al FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, NULL, (SELECT id FROM tmp_noval))),
  DATE '2080-06-10',
  '2) preventivo senza validita -> competenza_al = p.data (push NOT NULL-safe)'
);

-- ============================================================
-- 3) DIFFERITA -> competenza_mese proiettato = policy (settembre)
-- ============================================================
SELECT is(
  (SELECT competenza_mese FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, NULL, (SELECT id FROM tmp_diff))),
  DATE '2080-09-01',
  '3) DIFFERITA -> competenza_mese = policy p.competenza_mese (vince sul derivato)'
);

-- ============================================================
-- 4) pregresso -> competenza_mese derivato da validita_dal
-- ============================================================
SELECT is(
  (SELECT competenza_mese FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, NULL, (SELECT id FROM tmp_preg))),
  DATE '2080-06-01',
  '4) pregresso (competenza_mese NULL) -> derivato da validita_dal (2080-06-01)'
);

-- ============================================================
-- 5) edge validita_dal NULL + validita_al SET -> competenza_dal <= competenza_al
-- ============================================================
SELECT CASE
  WHEN (SELECT insertable FROM tmp_edge) THEN
    ok(
      (SELECT competenza_dal <= competenza_al
         FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, NULL, (SELECT prev_id FROM tmp_edge))),
      '5) edge validita_dal NULL + validita_al SET -> competenza_dal <= competenza_al (GREATEST)'
    )
  ELSE
    skip('chk_preventivi_validita vieta validita_dal NULL + validita_al SET: edge impossibile per costruzione', 1)
  END;

SELECT * FROM finish();
ROLLBACK;
