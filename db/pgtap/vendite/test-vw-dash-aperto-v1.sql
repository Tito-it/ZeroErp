-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2d): l'area della dashboard e' il codice della sorgente.
-- pgtap-contesto: escluso — la ragione e' scritta per esteso piu' sotto in
--   questo stesso file. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato», che una nota in prosa non fa.
--   ⚠️ Da riguardare: le esclusioni `rls/` furono fatte IN BLOCCO, e almeno
--   una non ne aveva diritto (brief pgtap-runner-rls-baseline §30.2).
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE vendite.preventivi FORCE ROW LEVEL SECURITY: il test verifica che
--   la vista di dashboard resti coerente con la RLS armata.
-- pgTAP test per Zero ERP
--
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima il
--   contratto nasceva gia' ATTIVO, i preventivi NEGATIVO e di B gia' RIFIUTATO e
--   ACCETTATO). Il contratto si costruisce dopo il passaggio all'operatore di A
--   (setup 4): per attivarsi vuole un listino con una versione in vigore, e
--   dbops.fn_pgtap_crea_listino gli da' l'emittente di chi agisce.
--
-- Test: viste "Situazione aperta" v2 — SERBATOIO PRE-COMMESSA
--       (brief-db-situazione-aperta-v2, 20260708-03..04; design §6-ter
--       DL-14..18). Perimetro ristretto agli APERTI-NON-CONCLUSI:
--         area<>COMMESSE AND NOT is_abortito
--         AND is_transitato IS DISTINCT FROM true   (solo aperti)
--         AND fase <> 'CHIUSO'                       (solo non-conclusi)
--       e viste SNELLITE (via colonne transitato/is_aperto/n_aperti).
--
--       I due predicati sono entrambi necessari (nessuno basta da solo):
--         (a) TRANSITATO-non-chiuso  -> lo toglie SOLO is_transitato<>true
--             (es. preventivo ACCETTATO gia' completamente smistato, IN_CORSO);
--         (b) CHIUSO-non-transitato  -> lo toglie SOLO fase<>CHIUSO
--             (es. preventivo EVASO con riga residua: esito POSITIVO ->
--             NOT is_abortito NON lo prende, is_transitato=false -> is_aperto
--             NON lo prende).  NB: l'esempio "offerta SUPERATA" del brief NON
--             vale (SUPERATA ha esito=NEGATIVO -> is_abortito, gia' escluso).
--
--       Caso (a): coperto da INVARIANTE data-level (fallback, test 10) invece
--       che da fixture "transito completo" (costosa: is_transitato e' derivata
--       da tutte-le-righe-transitate).
--
-- Fixture: preventivo ACCETTATO con riga residua (aperto, resta), preventivo
-- EVASO con riga residua (chiuso-non-transitato, ESCE — caso b), preventivo
-- ABORTITO (NEGATIVO, fuori), preventivo emittente B (scope), contratto ATTIVO
-- multi-mese (aperto, resta), commessa (esclusa dallo stock).
--
-- Indice test (0..13):
--   0)  Precondizioni (refs: BA, articoli, stati incl. NEGATIVO ed EVASO)
--   1)  Le 2 viste vw_dash_aperto_* esistono
--   2)  Colonne transitato RIMOSSE dalla dettaglio
--       (is_transitato/is_aperto/valore_transitato/unita_transitate)
--   3)  Colonne RIMOSSE dal riepilogo (n_aperti/valore_transitato)
--   4)  Setup: operatore OPERATORE non-super trovato + GUC scope
--   5)  COMMESSE fuori dallo stock
--   6)  Abortito (esito NEGATIVO) fuori dallo stock
--   7)  Preventivo ACCETTATO con residuo: nello stock, valore>0, fase, motivo
--   8)  Contratto ATTIVO multi-mese: 1 riga nello stock, valori NULL
--   9)  Caso (b): preventivo EVASO con residuo -> in union (fase=CHIUSO,
--       NON abortito, NON transitato) ma ASSENTE dallo stock (fase<>CHIUSO)
--  10)  INVARIANTE perimetro: nessuna riga dello stock e' transitata o CHIUSA
--       sulla union (fallback caso a + b, seed-agnostico)
--  11)  Riepilogo coerente col dettaglio + DL-11 (CONTRATTI valore NULL)
--  12)  fase mai NULL nello stock
--  13)  SCOPE RLS (FORCE in-transazione): preventivo emittente B invisibile
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ QUESTO FILE NON USA script.fn_pgtap_set_contesto_operatore(), a differenza
-- degli altri di vendite, e non e' una dimenticanza.
-- Il test si costruisce il contesto DA SOLO (set_config piu' sotto, e
-- perfino ALTER TABLE ... FORCE ROW LEVEL SECURITY in transazione) perche'
-- cio' che verifica E' lo scope RLS: l'asserzione 13 pretende che il
-- preventivo dell'emittente B risulti invisibile.
-- Imporre un operatore in testa lo romperebbe prima di cominciare: la
-- fixture crea documenti su un emittente derivato dal billing account, che
-- non e' detto stia nella whitelist di quell'operatore — e il guard
-- trgfn_guard_emittente_scope li rifiuterebbe, giustamente.
-- Misurato: con la riga passa da 14 asserzioni a 4.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.

SELECT plan(14);

-- ============================================================
-- 0) Riferimenti minimi
-- ============================================================
-- ⭐ Il mondo si FABBRICA (rev 2026-10-18): emittente A col suo operatore,
--   emittente B, e un cliente per ciascuno, legato al suo emittente. Prima si
--   pescavano «il primo BA con un emittente derivabile» e «un BA di un altro
--   emittente»: su un database ricostruito da zero non ce n'e' nessuno, la
--   fixture moriva su «Nessun emittente fiscale attivo» e il 13 andava in skip.
--   ⚠️ Nessun contesto operatore aperto qui: i builder lavorano da owner, come
--   il resto della fixture (guard emittente in modalita' batch).
CREATE TEMP TABLE tmp_ap_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE tmp_ap_cli_a AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'pgTAP dash aperto A', NULL, (SELECT soggetto_ruolo_id FROM tmp_ap_mondo));

CREATE TEMP TABLE tmp_ap_ef_b AS
SELECT * FROM dbops.fn_pgtap_crea_emittente();

CREATE TEMP TABLE tmp_ap_cli_b AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'pgTAP dash aperto B', NULL, (SELECT soggetto_ruolo_id FROM tmp_ap_ef_b));

CREATE TEMP TABLE tmp_ap_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_ap_cli_a) AS billing_account_id,
  (SELECT utility_id FROM tmp_ap_cli_a) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_ap_cli_a) AS istanza_utility_id,
  dbops.fn_pgtap_crea_articolo('PGT-DASH-AP') AS articolo_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'ACCETTATO' AND s.attivo IS TRUE LIMIT 1) AS prev_accettato_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE) AS prev_bozza_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'EVASO' AND s.attivo IS TRUE LIMIT 1) AS prev_evaso_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.esito = 'NEGATIVO' AND s.attivo IS TRUE
    ORDER BY s.id LIMIT 1) AS prev_negativo_id,
  -- lo stesso stato, per codice: ci si arriva per la matrice (rev 2026-10-24)
  (SELECT s.codice_interno FROM config.stati_doc_preventivi s
    WHERE s.esito = 'NEGATIVO' AND s.attivo IS TRUE
    ORDER BY s.id LIMIT 1) AS prev_negativo_cod,
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
  -- Emittente A = quello DERIVABILE dal BA principale (fn_get_emittente_fiscale_pk
  -- e' la funzione con cui i guard emittente<->BA confrontano).
  (SELECT anagrafiche.fn_get_emittente_fiscale_pk(billing_account_id) FROM tmp_ap_cli_a) AS emittente_fiscale_id,
  (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.id = (SELECT anagrafiche.fn_get_emittente_fiscale_pk(billing_account_id)
                     FROM tmp_ap_cli_a)) AS ef_a_sr;

-- Emittente B: il SECONDO BA, fabbricato sull'emittente B (il guard vieta un
-- emittente non coerente col BA: serve un BA suo, non «il secondo EF»).
CREATE TEMP TABLE tmp_ap_refs_b AS
SELECT c.billing_account_id                                       AS ba_b_id,
       c.utility_id                                               AS ba_b_utility_id,
       c.istanza_utility_id                                       AS ba_b_istanza_id,
       anagrafiche.fn_get_emittente_fiscale_pk(c.billing_account_id) AS ef_b_id
  FROM tmp_ap_cli_b c;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND articolo_id IS NOT NULL
      AND prev_accettato_id IS NOT NULL AND prev_evaso_id IS NOT NULL
      AND prev_negativo_id IS NOT NULL
      AND contr_attivo_id IS NOT NULL AND stato_commessa_id IS NOT NULL
      AND emittente_fiscale_id IS NOT NULL
     FROM tmp_ap_refs),
  '0. Precondizioni soddisfatte (incl. stato EVASO per il caso b)'
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
-- 2) Colonne transitato RIMOSSE dalla dettaglio (DL-14)
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM information_schema.columns
    WHERE table_schema = 'vendite' AND table_name = 'vw_dash_aperto_documenti'
      AND column_name IN ('is_transitato','is_aperto','valore_transitato','unita_transitate')),
  0,
  '2. Colonne transitato/is_aperto rimosse da vw_dash_aperto_documenti (DL-14)'
);

-- ============================================================
-- 3) Colonne RIMOSSE dal riepilogo (n_aperti/valore_transitato)
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM information_schema.columns
    WHERE table_schema = 'vendite' AND table_name = 'vw_dash_aperto_riepilogo'
      AND column_name IN ('n_aperti','valore_transitato')),
  0,
  '3. Colonne n_aperti/valore_transitato rimosse da vw_dash_aperto_riepilogo (DL-14)'
);

-- ============================================================
-- Fixture (con GUC ancora vuota: guard emittente in modalita' batch).
-- ============================================================

-- Preventivo ACCETTATO con 1 riga residua (emittente A) -> stock aperto.
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT, prende la riga, poi passa ad ACCETTATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le righe non si scrivono piu' (20261008-91).
CREATE TEMP TABLE tmp_ap_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-AP-PREV', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.prev_bozza_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_aperto'), r.emittente_fiscale_id
    FROM tmp_ap_refs r
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
SELECT p.id, r.articolo_id, 2.000000, 25.000000, r.iva_id, true
  FROM tmp_ap_prev p, tmp_ap_refs r;
DO $porta$ BEGIN PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_ap_prev), 'ACCETTATO'); END $porta$;

-- Caso (b): preventivo EVASO (fase CHIUSO, esito POSITIVO -> NON abortito) con
-- riga residua (transitata=false di default -> is_transitato=false). Deve
-- essere presente in union ma FUORI dallo stock, tolto SOLO da fase<>CHIUSO.
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT, prende la riga, poi cammina fino a EVASO (DRAFT->EMESSO->ACCETTATO->EVASO) con dbops.fn_pgtap_porta_a_stato — fuori bozza le righe non si scrivono piu' (20261008-91).
CREATE TEMP TABLE tmp_ap_prev_evaso AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-AP-PREVASO', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.prev_bozza_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_aperto'), r.emittente_fiscale_id
    FROM tmp_ap_refs r
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
SELECT p.id, r.articolo_id, 1.000000, 10.000000, r.iva_id, true
  FROM tmp_ap_prev_evaso p, tmp_ap_refs r;
DO $porta$ BEGIN PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_ap_prev_evaso), 'EVASO'); END $porta$;

-- Preventivo ABORTITO (stato con esito NEGATIVO, emittente A) -> fuori stock.
-- rev 2026-10-24: nasce DRAFT e arriva allo stato NEGATIVO per la matrice.
CREATE TEMP TABLE tmp_ap_prev_neg AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-AP-PRNEG', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.prev_bozza_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_aperto'), r.emittente_fiscale_id
    FROM tmp_ap_refs r
  RETURNING id)
SELECT * FROM ins;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.preventivi', p.id, r.prev_negativo_cod)
  FROM tmp_ap_prev_neg p, tmp_ap_refs r;

-- Preventivo emittente B (per il test scope 13; solo se esiste un secondo BA
-- con emittente derivabile DIVERSO — il guard emittente<->BA del 2026-07-13
-- vieta di appoggiare l'emittente B sul BA di A).
-- rev 2026-10-24: nasce DRAFT e arriva ad ACCETTATO per la matrice.
CREATE TEMP TABLE tmp_ap_prev_b AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-AP-PREVB', 0, b.ba_b_id, b.ba_b_istanza_id, b.ba_b_utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.prev_bozza_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_aperto'), b.ef_b_id
    FROM tmp_ap_refs r, tmp_ap_refs_b b
  RETURNING id)
SELECT * FROM ins;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.preventivi', p.id, 'ACCETTATO')
  FROM tmp_ap_prev_b p;

-- Il contratto ATTIVO si costruisce dopo il setup 4 (rev 2026-10-24).

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
       'BOZZA', 'NON_EMESSA', (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
         ((SELECT id FROM tmp_ap_commessa))::text
FROM tmp_ap_refs r;

-- ============================================================
-- 4) Setup scope: operatore OPERATORE non-super whitelistato su A.
-- ============================================================
-- L'operatore e' quello fabbricato con l'emittente A (rev 2026-10-18): un
-- operatore OPERATORE non super, che prima si pescava fra quelli esistenti.
CREATE TEMP TABLE tmp_ap_op AS
SELECT id.auth_user_id AS user_id
  FROM anagrafiche.identita_digitali id
 WHERE id.auth_user_id = (SELECT auth_user_id FROM tmp_ap_mondo)
   AND id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND id.attivo = true
   AND NOT EXISTS (
       SELECT 1 FROM config.profili_accesso_bindings pab
       JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
       WHERE pab.identita_digitale_id = id.id
         AND pab.attivo = true
         AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso);

SELECT ok(
  (SELECT user_id IS NOT NULL FROM tmp_ap_op),
  '4. Trovato un operatore OPERATORE non-super per lo scope'
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

-- Contratto ATTIVO multi-mese (de-esploso: 1 riga nello stock).
-- ⛔ rev 2026-10-24 (brief-modello-documento-vendita N-1): nasceva gia' ATTIVO,
--   senza listino. Ora nasce in DRAFT e si attiva per la matrice, e
--   l'attivazione vuole un listino con una versione in vigore
--   (trgfn_contratti_freeze_listino_versione): lo costruisce il builder, che
--   gli da' l'emittente di chi agisce — per questo il contratto nasce QUI,
--   con l'operatore di A in sessione, e non nella fixture di sopra.
CREATE TEMP TABLE tmp_ap_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_ap_refs), 'dash aperto');

CREATE TEMP TABLE tmp_ap_contratto AS
WITH ins AS (
  INSERT INTO vendite.contratti (
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al, data, listino_id,
    emittente_fiscale_id, meta)
  SELECT 'PGTAP-AP-CT-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.istanza_utility_id, r.utility_id,
         (date_trunc('month', script.fn_data_operativa()) - interval '2 months')::date, NULL,
         (date_trunc('month', script.fn_data_operativa()) - interval '2 months')::date,
         (SELECT listino_id FROM tmp_ap_listino),
         COALESCE(anagrafiche.fn_get_emittente_fiscale_pk(r.billing_account_id),
                  r.emittente_fiscale_id),
         jsonb_build_object('test_scope','pgtap_dash_aperto')
    FROM tmp_ap_refs r
  RETURNING id)
SELECT * FROM ins;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti', c.id, 'ATTIVO')
  FROM tmp_ap_contratto c;

-- ============================================================
-- 5) COMMESSE fuori dallo stock
-- ============================================================
SELECT ok(
  (SELECT EXISTS (
     SELECT 1 FROM vendite.vw_dash_fatturazione_documenti d
      WHERE d.area = 'COMMESSA'
        AND d.documento_id = (SELECT id FROM tmp_ap_commessa)))
  AND NOT EXISTS (
     SELECT 1 FROM vendite.vw_dash_aperto_documenti a
      WHERE a.area = 'COMMESSA'),
  '5. La commessa e'' nella union ma le COMMESSE non entrano nello stock (Lente 1 le copre)'
);

-- ============================================================
-- 6) Abortito fuori dallo stock (D-6 applicata dalla vista aperto)
-- ============================================================
SELECT ok(
  (SELECT EXISTS (
     SELECT 1 FROM vendite.vw_dash_fatturazione_documenti d
      WHERE d.documento_id = (SELECT id FROM tmp_ap_prev_neg)
        AND d.area = 'PREVENTIVO' AND d.is_abortito))
  AND NOT EXISTS (
     SELECT 1 FROM vendite.vw_dash_aperto_documenti a
      WHERE a.area = 'PREVENTIVO'
        AND a.documento_id = (SELECT id FROM tmp_ap_prev_neg)),
  '6. Preventivo con esito NEGATIVO: marcato abortito in union, ASSENTE dallo stock'
);

-- ============================================================
-- 7) Preventivo aperto nello stock (colonne v2: no is_aperto/valore_transitato)
-- ============================================================
SELECT ok(
  (SELECT a.fase IS NOT NULL
      AND a.valore_totale = 50
      AND a.motivo_fermo = 'RIGA_RESIDUA'
     FROM vendite.vw_dash_aperto_documenti a
    WHERE a.area = 'PREVENTIVO'
      AND a.documento_id = (SELECT id FROM tmp_ap_prev)),
  '7. Preventivo ACCETTATO con residuo: nello stock, valore 50, fase valorizzata, motivo_fermo tenuto'
);

-- ============================================================
-- 8) Contratto de-esploso -> 1 riga, valori NULL
-- ============================================================
SELECT ok(
  (SELECT count(*) = 1
      AND bool_and(a.fase IS NOT NULL)
      AND bool_and(a.valore_totale IS NULL)
     FROM vendite.vw_dash_aperto_documenti a
    WHERE a.area = 'CONTRATTO'
      AND a.documento_id = (SELECT id FROM tmp_ap_contratto)),
  '8. Contratto ATTIVO multi-mese: 1 sola riga nello stock (giudizio sospeso = aperto), valori NULL'
);

-- ============================================================
-- 9) CASO (b): EVASO con residuo — in union (CHIUSO, non-abortito,
--    non-transitato) ma FUORI dallo stock (tolto SOLO da fase<>CHIUSO).
-- ============================================================
SELECT ok(
  (SELECT EXISTS (
     SELECT 1 FROM vendite.vw_dash_fatturazione_documenti d
      WHERE d.documento_id = (SELECT id FROM tmp_ap_prev_evaso)
        AND d.area = 'PREVENTIVO'
        AND d.fase = 'CHIUSO'
        AND NOT d.is_abortito
        AND d.is_transitato IS DISTINCT FROM true))
  AND NOT EXISTS (
     SELECT 1 FROM vendite.vw_dash_aperto_documenti a
      WHERE a.area = 'PREVENTIVO'
        AND a.documento_id = (SELECT id FROM tmp_ap_prev_evaso)),
  '9. Caso (b): preventivo EVASO non-abortito/non-transitato in union (fase CHIUSO), ASSENTE dallo stock via fase<>CHIUSO'
);

-- ============================================================
-- 10) INVARIANTE perimetro: nessuna riga dello stock e' transitata o CHIUSA
--     sulla union (fallback caso a + b, seed-agnostico — evita la fixture
--     "transito completo" costosa).
-- ============================================================
SELECT is(
  (SELECT count(*)::integer
     FROM vendite.vw_dash_aperto_documenti a
     JOIN vendite.vw_dash_fatturazione_documenti u
       ON u.area = a.area AND u.documento_id = a.documento_id
    WHERE u.is_transitato IS TRUE
       OR u.fase = 'CHIUSO'),
  0,
  '10. Invariante: nessun documento dello stock e'' transitato o in fase CHIUSO sulla union'
);

-- ============================================================
-- 11) Riepilogo coerente col dettaglio + DL-11
-- ============================================================
SELECT ok(
  -- cella PREVENTIVI della fase del fixture: conta e somma
  (SELECT r.n_documenti >= 1 AND r.valore_totale IS NOT NULL
     FROM vendite.vw_dash_aperto_riepilogo r
    WHERE r.area = 'PREVENTIVO'
      AND r.fase = (SELECT a.fase FROM vendite.vw_dash_aperto_documenti a
                     WHERE a.documento_id = (SELECT id FROM tmp_ap_prev)
                       AND a.area = 'PREVENTIVO'))
  AND
  -- cella CONTRATTI: area a conteggi -> valore_totale NULL (DL-11)
  (SELECT bool_and(r.valore_totale IS NULL)
     FROM vendite.vw_dash_aperto_riepilogo r
    WHERE r.area = 'CONTRATTO')
  AND
  -- coerenza globale: somma n_documenti del riepilogo = righe del dettaglio
  (SELECT (SELECT COALESCE(SUM(n_documenti), 0) FROM vendite.vw_dash_aperto_riepilogo)
        = (SELECT count(*) FROM vendite.vw_dash_aperto_documenti)),
  '11. Riepilogo: cella PREVENTIVI con valore, CONTRATTI a NULL (DL-11), somme = dettaglio'
);

-- ============================================================
-- 12) fase mai NULL nello stock
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_aperto_documenti a
    WHERE a.fase IS NULL),
  0,
  '12. Nessuna riga dello stock ha fase NULL'
);

-- ============================================================
-- 13) SCOPE RLS: FORCE in-transazione (pattern
--    test-rls-fatture-ef-whitelist-functional) assoggetta anche l'owner
--    titodb; GUC operatore A gia' impostata -> il preventivo di emittente B
--    deve sparire dallo stock (invoker -> RLS preventivi). Rollback finale
--    ripristina tutto. ULTIMO test: il FORCE resta attivo fino al rollback.
-- ============================================================
SET CONSTRAINTS ALL IMMEDIATE;
ALTER TABLE vendite.preventivi FORCE ROW LEVEL SECURITY;
SELECT set_config('app.ruolo_applicativo', 'OPERATORE', true);

SELECT CASE WHEN (SELECT ef_b_id FROM tmp_ap_refs_b) IS NULL
  THEN pass('13. [skip] nessun BA con secondo emittente derivabile: scope RLS non testabile')
  ELSE ok(
    (SELECT NOT EXISTS (
       SELECT 1 FROM vendite.vw_dash_aperto_documenti a
        WHERE a.documento_id = (SELECT id FROM tmp_ap_prev_b)
          AND a.area = 'PREVENTIVO')
     AND EXISTS (
       SELECT 1 FROM vendite.vw_dash_aperto_documenti a
        WHERE a.documento_id = (SELECT id FROM tmp_ap_prev)
          AND a.area = 'PREVENTIVO')),
    '13. Scope RLS (FORCE): l''operatore A vede il preventivo A, NON quello di emittente B'
  )
END;

SELECT * FROM finish();
ROLLBACK;
