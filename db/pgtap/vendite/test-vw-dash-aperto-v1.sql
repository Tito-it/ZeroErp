-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: viste "Situazione aperta" (Fase 3 due lenti, 20260707-03..06):
--       vw_dash_aperto_documenti (stock 4 aree documento, no COMMESSE,
--       no abortiti, tutte le fasi — DL-13) e vw_dash_aperto_riepilogo
--       (card area x fase). Brief: brief-db-situazione-aperta.md §2-3.
--       Fixture: preventivo ACCETTATO con riga residua (aperto), preventivo
--       ABORTITO (esito NEGATIVO, fuori), preventivo emittente B (scope),
--       contratto ATTIVO multi-mese (de-esploso, giudizio sospeso),
--       commessa con attivita' (esclusa dallo stock).
--
-- Indice test (0..9):
--   0)  Precondizioni (refs: BA, articoli, stati incl. esito NEGATIVO)
--   1)  Le 2 viste vw_dash_aperto_* esistono
--   2)  Setup: operatore OPERATORE non-super trovato + GUC scope
--   3)  COMMESSE fuori dallo stock (presenti in union, assenti da aperto)
--   4)  Abortito (esito NEGATIVO) fuori dallo stock (D-6 applicata in vista)
--   5)  Preventivo ACCETTATO con residuo: nello stock, is_aperto, valore > 0
--   6)  Contratto ATTIVO multi-mese: 1 riga, giudizio sospeso -> is_aperto
--   7)  Riepilogo: cella PREVENTIVI con valori, cella CONTRATTI valori NULL
--       (DL-11) e coerente col dettaglio
--   8)  fase mai NULL nello stock (criterio 6)
--   9)  SCOPE RLS (FORCE in-transazione): preventivo emittente B invisibile
--       all'operatore A [skip se il seed ha un solo emittente]
-- ------------------------------------------------------------

BEGIN;
SELECT plan(10);

-- ============================================================
-- 0) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_ap_refs AS
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
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1) AS articolo_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'ACCETTATO' AND s.attivo IS TRUE LIMIT 1) AS prev_accettato_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.esito = 'NEGATIVO' AND s.attivo IS TRUE
    ORDER BY s.id LIMIT 1) AS prev_negativo_id,
  (SELECT s.id FROM config.stati_doc_contratti s
    WHERE s.codice_interno = 'ATTIVO' AND s.attivo IS TRUE LIMIT 1) AS contr_attivo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE
    ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE
    ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT sc.id FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE AND sc.codice_interno <> 'ANNULLATA'
    ORDER BY sc.id LIMIT 1) AS stato_commessa_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
  (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1) AS ef_a_sr,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE
    ORDER BY ef.id OFFSET 1 LIMIT 1) AS ef_b_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND articolo_id IS NOT NULL
      AND prev_accettato_id IS NOT NULL AND prev_negativo_id IS NOT NULL
      AND contr_attivo_id IS NOT NULL AND stato_commessa_id IS NOT NULL
      AND emittente_fiscale_id IS NOT NULL
     FROM tmp_ap_refs),
  '0. Precondizioni soddisfatte'
);

-- ============================================================
-- 1) Le 2 viste esistono
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM pg_views
    WHERE schemaname = 'vendite'
      AND viewname IN ('vw_dash_aperto_documenti', 'vw_dash_aperto_riepilogo')),
  2,
  '1. Le 2 viste vw_dash_aperto_* esistono'
);

-- ============================================================
-- Fixture (con GUC ancora vuota: guard emittente in modalita' batch).
-- ============================================================

-- Preventivo ACCETTATO con 1 riga residua (emittente A) -> stock aperto.
CREATE TEMP TABLE tmp_ap_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-AP-PREV', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.prev_accettato_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_aperto'), r.emittente_fiscale_id
    FROM tmp_ap_refs r
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
SELECT p.id, r.articolo_id, 2.000000, 25.000000, r.iva_id, true
  FROM tmp_ap_prev p, tmp_ap_refs r;

-- Preventivo ABORTITO (stato con esito NEGATIVO, emittente A) -> fuori stock.
CREATE TEMP TABLE tmp_ap_prev_neg AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-AP-PRNEG', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.prev_negativo_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_aperto'), r.emittente_fiscale_id
    FROM tmp_ap_refs r
  RETURNING id)
SELECT * FROM ins;

-- Preventivo emittente B (per il test scope 9; solo se esiste un secondo EF).
CREATE TEMP TABLE tmp_ap_prev_b AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-AP-PREVB', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.prev_accettato_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_aperto'), r.ef_b_id
    FROM tmp_ap_refs r
   WHERE r.ef_b_id IS NOT NULL
  RETURNING id)
SELECT * FROM ins;

-- Contratto ATTIVO multi-mese (de-esploso: 1 riga nello stock).
CREATE TEMP TABLE tmp_ap_contratto AS
WITH ins AS (
  INSERT INTO vendite.contratti (
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al, stato_doc_contratto_id, data,
    emittente_fiscale_id, meta)
  SELECT 'PGTAP-AP-CT-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.istanza_utility_id, r.utility_id,
         (date_trunc('month', CURRENT_DATE) - interval '2 months')::date, NULL,
         r.contr_attivo_id, (date_trunc('month', CURRENT_DATE) - interval '2 months')::date,
         COALESCE(anagrafiche.fn_get_emittente_fiscale_pk(r.billing_account_id),
                  r.emittente_fiscale_id),
         jsonb_build_object('test_scope','pgtap_dash_aperto')
    FROM tmp_ap_refs r
  RETURNING id)
SELECT * FROM ins;

-- Commessa (emittente A) con 1 attivita': visibile in union, MAI nello stock.
CREATE TEMP TABLE tmp_ap_commessa AS
WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                emittente_soggetto_ruolo_id, stato_commessa_id)
  SELECT 'PGTAP-AP-CMD-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id, r.ef_a_sr, r.stato_commessa_id
    FROM tmp_ap_refs r
  RETURNING id)
SELECT id FROM ins;

INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
  uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
  stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
SELECT (SELECT id FROM tmp_ap_commessa),
       'PGTAP-AP-A1-' || substr(md5(clock_timestamp()::text), 1, 8),
       r.articolo_id, r.istanza_utility_id, DATE '2080-02-01', r.uom_id, 1,
       DATE '2080-02-01', DATE '2080-02-01', DATE '2080-02-28',
       r.tipo_doc_fiscale_id, r.valuta_id, 33.000000, 'FIXED',
       'BOZZA', 'NON_EMESSA', NULL, NULL
FROM tmp_ap_refs r;

-- ============================================================
-- 2) Setup scope: operatore OPERATORE non-super whitelistato su A.
-- ============================================================
CREATE TEMP TABLE tmp_ap_op AS
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
  (SELECT user_id IS NOT NULL FROM tmp_ap_op),
  '2. Trovato un operatore OPERATORE non-super per lo scope'
);

SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_ap_op);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id, meta)
SELECT o.user_id, r.emittente_fiscale_id,
       '{"test_scope":"pgtap_dash_aperto"}'::jsonb
  FROM tmp_ap_op o, tmp_ap_refs r
 WHERE o.user_id IS NOT NULL;

SELECT set_config('app.current_user_id',
    (SELECT user_id::text FROM tmp_ap_op), true);

-- ============================================================
-- 3) COMMESSE fuori dallo stock
-- ============================================================
SELECT ok(
  (SELECT EXISTS (
     SELECT 1 FROM vendite.vw_dash_fatturazione_documenti d
      WHERE d.area = 'COMMESSE'
        AND d.documento_id = (SELECT id FROM tmp_ap_commessa)))
  AND NOT EXISTS (
     SELECT 1 FROM vendite.vw_dash_aperto_documenti a
      WHERE a.area = 'COMMESSE'),
  '3. La commessa e'' nella union ma le COMMESSE non entrano nello stock (Lente 1 le copre)'
);

-- ============================================================
-- 4) Abortito fuori dallo stock (D-6 applicata dalla vista aperto)
-- ============================================================
SELECT ok(
  (SELECT EXISTS (
     SELECT 1 FROM vendite.vw_dash_fatturazione_documenti d
      WHERE d.documento_id = (SELECT id FROM tmp_ap_prev_neg)
        AND d.area = 'PREVENTIVI' AND d.is_abortito))
  AND NOT EXISTS (
     SELECT 1 FROM vendite.vw_dash_aperto_documenti a
      WHERE a.area = 'PREVENTIVI'
        AND a.documento_id = (SELECT id FROM tmp_ap_prev_neg)),
  '4. Preventivo con esito NEGATIVO: marcato abortito in union, ASSENTE dallo stock'
);

-- ============================================================
-- 5) Preventivo aperto nello stock
-- ============================================================
SELECT ok(
  (SELECT a.is_aperto = true AND a.fase IS NOT NULL
      AND a.valore_totale = 50 AND a.valore_transitato = 0
      AND a.motivo_fermo = 'RIGA_RESIDUA'
     FROM vendite.vw_dash_aperto_documenti a
    WHERE a.area = 'PREVENTIVI'
      AND a.documento_id = (SELECT id FROM tmp_ap_prev)),
  '5. Preventivo ACCETTATO con residuo: nello stock, aperto, 50/0, fase valorizzata'
);

-- ============================================================
-- 6) Contratto de-esploso, giudizio sospeso -> aperto
-- ============================================================
SELECT ok(
  (SELECT count(*) = 1
      AND bool_and(a.is_transitato IS NULL)
      AND bool_and(a.is_aperto = true)
      AND bool_and(a.fase IS NOT NULL)
      AND bool_and(a.valore_totale IS NULL)
     FROM vendite.vw_dash_aperto_documenti a
    WHERE a.area = 'CONTRATTI'
      AND a.documento_id = (SELECT id FROM tmp_ap_contratto)),
  '6. Contratto ATTIVO multi-mese: 1 sola riga nello stock, giudizio sospeso = aperto, valori NULL'
);

-- ============================================================
-- 7) Riepilogo coerente col dettaglio + DL-11
-- ============================================================
SELECT ok(
  -- cella PREVENTIVI della fase del fixture: conta e somma
  (SELECT r.n_documenti >= 1 AND r.n_aperti >= 1 AND r.valore_totale IS NOT NULL
     FROM vendite.vw_dash_aperto_riepilogo r
    WHERE r.area = 'PREVENTIVI'
      AND r.fase = (SELECT a.fase FROM vendite.vw_dash_aperto_documenti a
                     WHERE a.documento_id = (SELECT id FROM tmp_ap_prev)
                       AND a.area = 'PREVENTIVI'))
  AND
  -- cella CONTRATTI: area a conteggi -> valori NULL (DL-11)
  (SELECT bool_and(r.valore_totale IS NULL AND r.valore_transitato IS NULL)
     FROM vendite.vw_dash_aperto_riepilogo r
    WHERE r.area = 'CONTRATTI')
  AND
  -- coerenza globale: somma n_documenti del riepilogo = righe del dettaglio
  (SELECT (SELECT COALESCE(SUM(n_documenti), 0) FROM vendite.vw_dash_aperto_riepilogo)
        = (SELECT count(*) FROM vendite.vw_dash_aperto_documenti)),
  '7. Riepilogo: cella PREVENTIVI con valori, CONTRATTI a NULL (DL-11), somme = dettaglio'
);

-- ============================================================
-- 8) fase mai NULL nello stock (criterio 6)
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_aperto_documenti a
    WHERE a.fase IS NULL),
  0,
  '8. Nessuna riga dello stock ha fase NULL'
);

-- ============================================================
-- 9) SCOPE RLS: FORCE in-transazione (pattern
--    test-rls-fatture-ef-whitelist-functional) assoggetta anche l'owner
--    titodb; GUC operatore A gia' impostata -> il preventivo di emittente B
--    deve sparire dallo stock (invoker -> RLS preventivi). Rollback finale
--    ripristina tutto. ULTIMO test: il FORCE resta attivo fino al rollback.
-- ============================================================
-- Le fixture inserite in-transazione lasciano constraint trigger deferiti in
-- coda su preventivi: vanno flushati ORA, altrimenti l'ALTER e' rifiutato
-- ("ha eventi trigger in sospeso").
SET CONSTRAINTS ALL IMMEDIATE;
ALTER TABLE vendite.preventivi FORCE ROW LEVEL SECURITY;
SELECT set_config('app.ruolo_applicativo', 'OPERATORE', true);

SELECT CASE WHEN (SELECT ef_b_id FROM tmp_ap_refs) IS NULL
  THEN pass('9. [skip] seed con un solo emittente: scope RLS non testabile')
  ELSE ok(
    (SELECT NOT EXISTS (
       SELECT 1 FROM vendite.vw_dash_aperto_documenti a
        WHERE a.documento_id = (SELECT id FROM tmp_ap_prev_b)
          AND a.area = 'PREVENTIVI')
     AND EXISTS (
       SELECT 1 FROM vendite.vw_dash_aperto_documenti a
        WHERE a.documento_id = (SELECT id FROM tmp_ap_prev)
          AND a.area = 'PREVENTIVI')),
    '9. Scope RLS (FORCE): l''operatore A vede il preventivo A, NON quello di emittente B'
  )
END;

SELECT * FROM finish();
ROLLBACK;
