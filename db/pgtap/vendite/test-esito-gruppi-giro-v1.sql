-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.vw_lotti_gruppi_serviti (20260815-26)
--       vendite.fn_esito_gruppi_giro   (20260815-27)
--       Il CONSUNTIVO di un giro di fatturazione, gruppo per gruppo.
--       Brief: brief-db-emittibilita-visibile-e-sbloccabile §8.2 / §9.
--
-- Perche' esiste: `fn_list_emittibili_lane.gruppi_coperti` e' una PREVISIONE.
-- Fra la discovery e l'esecuzione le righe di un gruppo possono essere prese
-- da un altro giro: la pipeline esce senza errore e senza lotto per quel
-- gruppo, e l'esito legge pieno successo. Queste asserzioni presidiano la
-- misura fatta DOPO, che e' l'unica che sa distinguere i tre casi.
--
-- Fixture costruita dentro il test (non pescata dai dati): una commessa con
-- tre gruppi sorgente distinti, due lotti, due fatture.
--   G1 -> attivita' EMESSA fatturata dal lotto L1   -> atteso SERVITO
--   G2 -> attivita' NON_EMESSA, mai fatturata       -> atteso NON_SERVITO
--   G3 -> attivita' EMESSA fatturata dal lotto L2   -> atteso FATTURATO_ALTROVE
-- Il perimetro richiesto {G1,G2,G3} e' persistito su L1 come fa
-- pipeline_repository.set_lotto_gruppi. L2 non ha perimetro: e' il giro di massa.
--
-- Indice test (0..11):
--   0)  Precondizioni (riferimenti minimi risolti)
--   1)  La vista e la funzione esistono
--   2)  vw_lotti_gruppi_serviti: L1 ha servito G1 con 1 attivita'
--   3)  G1 -> SERVITO, lotti_serventi = {L1}
--   4)  G2 -> NON_SERVITO con residuo 1 (e' il caso su cui si agisce)
--   5)  G3 -> FATTURATO_ALTROVE, lotti_altrui = {L2}, residuo 0
--   6)  Invarianza: richiesti = serviti + non serviti, tutti misurati
--   7)  Tutti e tre risultano richiesto = true (perimetro letto dal DB)
--   8)  Guard: array vuoto -> errore di dominio, non risposta vuota
--   9)  Guard: lotto inesistente -> errore di dominio
--   10) Giro di MASSA (L2, nessun perimetro): i serviti escono con richiesto=false
--   11) ⚠️ FAIL-CLOSED: lotto fuori scope -> SOLLEVA, non «non servito»
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Scattano al COMMIT, e qui il COMMIT non arriva mai (si chiude in ROLLBACK):
--   sarebbero saltati in silenzio, e il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (ruolo OPERATORE
-- + RLS attiva). Qui non e' un dettaglio: meta' della catena ha la RLS e meta'
-- no, ed e' proprio l'asimmetria che il test 11 verifica.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- ============================================================
-- 0) Riferimenti minimi
-- ============================================================
-- ⚠️ Niente LIMIT 1 senza ORDER BY: senza ordine, quale riga esca dipende dal
--   piano del planner e il test passerebbe a giorni alterni.
-- ⚠️ L'emittente non si pesca, si DERIVA dall'operatore corrente: le policy
--   ef_whitelist lo pretendono, e una fixture scritta su un emittente altrui
--   non passerebbe la RLS in scrittura.
CREATE TEMP TABLE tmp_eg_refs AS
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
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE
    ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE
    ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT sc.id FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE AND sc.codice_interno <> 'ANNULLATA'
    ORDER BY sc.id LIMIT 1) AS stato_commessa_id,
  script.fn_pgtap_emittente_sr_operatore()                          AS ef_sr,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'PREVENTIVO' AND s.attivo IS TRUE
    ORDER BY s.id LIMIT 1) AS sorgente_tipo_id,
  script.fn_pgtap_registro_fattura() AS registro_id,
  (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.attivo IS TRUE
    ORDER BY COALESCE(s.ordine, 32767), s.id LIMIT 1) AS stato_fiscale_id;

-- I tre UID sorgente si scelgono UNA volta: due sotto-select indipendenti
-- darebbero valori diversi a ogni valutazione.
CREATE TEMP TABLE tmp_eg_uid AS
SELECT 'G1'::text AS slot, uuidv7()::text AS uid
UNION ALL SELECT 'G2', uuidv7()::text
UNION ALL SELECT 'G3', uuidv7()::text;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND articolo_id IS NOT NULL
      AND uom_id IS NOT NULL AND tipo_doc_fiscale_id IS NOT NULL
      AND stato_commessa_id IS NOT NULL AND ef_sr IS NOT NULL
      AND sorgente_tipo_id IS NOT NULL AND registro_id IS NOT NULL
      AND stato_fiscale_id IS NOT NULL AND valuta_id IS NOT NULL
     FROM tmp_eg_refs),
  '0. Precondizioni soddisfatte (riferimenti minimi risolti)'
);

-- ============================================================
-- 1) Gli oggetti del cantiere esistono
-- ============================================================
SELECT ok(
  (SELECT count(*) FROM pg_views
     WHERE schemaname = 'vendite' AND viewname = 'vw_lotti_gruppi_serviti') = 1
  AND (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'vendite' AND p.proname = 'fn_esito_gruppi_giro') = 1,
  '1. vw_lotti_gruppi_serviti e fn_esito_gruppi_giro esistono'
);

-- ============================================================
-- Fixture: commessa + tre attivita' su tre gruppi sorgente distinti
-- ============================================================
CREATE TEMP TABLE tmp_eg_commessa AS
WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                emittente_soggetto_ruolo_id, stato_commessa_id)
  SELECT 'PGTAP-EG-CMD-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id, r.ef_sr, r.stato_commessa_id
    FROM tmp_eg_refs r
  RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_eg_att (slot text, attivita_id bigint);

-- G1: sara' fatturata dal lotto L1 (il giro che stiamo consuntivando).
WITH ins AS (
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
  SELECT (SELECT id FROM tmp_eg_commessa),
         'PGTAP-EG-G1-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.articolo_id, r.istanza_utility_id, DATE '2081-01-01', r.uom_id, 1,
         DATE '2081-01-01', DATE '2081-01-01', DATE '2081-01-31',
         r.tipo_doc_fiscale_id, r.valuta_id, 10.000000, 'FIXED',
         'APPROVATA', 'EMESSA', r.sorgente_tipo_id,
         (SELECT uid FROM tmp_eg_uid WHERE slot = 'G1')
    FROM tmp_eg_refs r
  RETURNING id)
INSERT INTO tmp_eg_att SELECT 'G1', id FROM ins;

-- G2: resta NON_EMESSA. E' il lavoro fermo che il consuntivo deve saper vedere.
WITH ins AS (
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
  SELECT (SELECT id FROM tmp_eg_commessa),
         'PGTAP-EG-G2-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.articolo_id, r.istanza_utility_id, DATE '2081-01-01', r.uom_id, 1,
         DATE '2081-01-01', DATE '2081-01-01', DATE '2081-01-31',
         r.tipo_doc_fiscale_id, r.valuta_id, 20.000000, 'FIXED',
         'APPROVATA', 'NON_EMESSA', r.sorgente_tipo_id,
         (SELECT uid FROM tmp_eg_uid WHERE slot = 'G2')
    FROM tmp_eg_refs r
  RETURNING id)
INSERT INTO tmp_eg_att SELECT 'G2', id FROM ins;

-- G3: fatturata da un ALTRO lotto. E' il «lavoro rubato da un altro giro».
WITH ins AS (
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
  SELECT (SELECT id FROM tmp_eg_commessa),
         'PGTAP-EG-G3-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.articolo_id, r.istanza_utility_id, DATE '2081-01-01', r.uom_id, 1,
         DATE '2081-01-01', DATE '2081-01-01', DATE '2081-01-31',
         r.tipo_doc_fiscale_id, r.valuta_id, 30.000000, 'FIXED',
         'APPROVATA', 'EMESSA', r.sorgente_tipo_id,
         (SELECT uid FROM tmp_eg_uid WHERE slot = 'G3')
    FROM tmp_eg_refs r
  RETURNING id)
INSERT INTO tmp_eg_att SELECT 'G3', id FROM ins;

-- Le chiavi di gruppo si prendono dalla SOLA fonte di verita': ricostruirle a
-- mano nel test significherebbe verificare la copia, non l'originale.
CREATE TEMP TABLE tmp_eg_key AS
SELECT a.slot,
       vendite.fn_build_gruppo_fatturabile_key(
         ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id) AS gruppo_key
  FROM tmp_eg_att a
  JOIN vendite.commesse_attivita ca ON ca.id = a.attivita_id;

-- ------------------------------------------------------------
-- Due lotti e due fatture. stato_doc_fiscale_id resta NULL sui lotti: il
-- guard di coerenza lotto/fatture esce subito quando il lotto non ha stato,
-- e qui la coerenza degli stati non e' l'oggetto del test.
-- ------------------------------------------------------------
CREATE TEMP TABLE tmp_eg_lotto (slot text, lotto_id bigint);

WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
    codice, competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id, meta)
  SELECT 'PGTAP-EG-L1-' || substr(md5(clock_timestamp()::text), 1, 8),
         DATE '2081-01-01', r.tipo_doc_fiscale_id, r.ef_sr,
         jsonb_build_object('test_scope', 'pgtap_esito_gruppi_giro')
    FROM tmp_eg_refs r
  RETURNING id)
INSERT INTO tmp_eg_lotto SELECT 'L1', id FROM ins;

WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
    codice, competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id, meta)
  SELECT 'PGTAP-EG-L2-' || substr(md5(clock_timestamp()::text), 1, 8),
         DATE '2081-01-01', r.tipo_doc_fiscale_id, r.ef_sr,
         jsonb_build_object('test_scope', 'pgtap_esito_gruppi_giro')
    FROM tmp_eg_refs r
  RETURNING id)
INSERT INTO tmp_eg_lotto SELECT 'L2', id FROM ins;

-- Il PERIMETRO del giro, scritto come lo scrive pipeline_repository:
-- l'intera tupla richiesta su OGNI lotto del giro. Qui il giro e' un lotto solo.
INSERT INTO vendite.fatturazione_lotti_gruppi (lotto_id, gruppo_key)
SELECT (SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L1'), k.gruppo_key
  FROM tmp_eg_key k;

CREATE TEMP TABLE tmp_eg_fattura (slot text, fattura_id bigint);

WITH inf AS (
  INSERT INTO vendite.fatture (
    registro_id, data, tipo_doc_fiscale_id, stato_doc_fiscale_id,
    emittente_soggetto_ruolo_id, billing_account_id, utility_id, meta)
  SELECT r.registro_id, DATE '2081-02-15', r.tipo_doc_fiscale_id, r.stato_fiscale_id,
         r.ef_sr, r.billing_account_id,
         (SELECT ba.utility_id FROM anagrafiche.billing_account ba WHERE ba.id = r.billing_account_id),
         jsonb_build_object('test_scope', 'pgtap_esito_gruppi_giro')
    FROM tmp_eg_refs r
  RETURNING id)
INSERT INTO tmp_eg_fattura SELECT 'F1', id FROM inf;

WITH inf AS (
  INSERT INTO vendite.fatture (
    registro_id, data, tipo_doc_fiscale_id, stato_doc_fiscale_id,
    emittente_soggetto_ruolo_id, billing_account_id, utility_id, meta)
  SELECT r.registro_id, DATE '2081-02-16', r.tipo_doc_fiscale_id, r.stato_fiscale_id,
         r.ef_sr, r.billing_account_id,
         (SELECT ba.utility_id FROM anagrafiche.billing_account ba WHERE ba.id = r.billing_account_id),
         jsonb_build_object('test_scope', 'pgtap_esito_gruppi_giro')
    FROM tmp_eg_refs r
  RETURNING id)
INSERT INTO tmp_eg_fattura SELECT 'F2', id FROM inf;

-- ⚠️ Padre e figlio in DUE istruzioni: le CTE che scrivono condividono la
--   stessa snapshot, e una policy che risolve il perimetro dal padre non lo
--   troverebbe.
CREATE TEMP TABLE tmp_eg_riga (slot text, riga_id bigint);

WITH ins AS (
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta,
                                     prezzo_unitario, imponibile_riga, competenza_dal, competenza_al)
  SELECT (SELECT fattura_id FROM tmp_eg_fattura WHERE slot = 'F1'), 1,
         'PGTAP esito gruppi giro G1', 1, 10.000000, 10.000000, script.fn_data_operativa(), script.fn_data_operativa()
  RETURNING id)
INSERT INTO tmp_eg_riga SELECT 'F1', id FROM ins;

WITH ins AS (
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta,
                                     prezzo_unitario, imponibile_riga, competenza_dal, competenza_al)
  SELECT (SELECT fattura_id FROM tmp_eg_fattura WHERE slot = 'F2'), 1,
         'PGTAP esito gruppi giro G3', 1, 30.000000, 30.000000, script.fn_data_operativa(), script.fn_data_operativa()
  RETURNING id)
INSERT INTO tmp_eg_riga SELECT 'F2', id FROM ins;

INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id)
SELECT (SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L1'),
       (SELECT fattura_id FROM tmp_eg_fattura WHERE slot = 'F1');

INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id)
SELECT (SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L2'),
       (SELECT fattura_id FROM tmp_eg_fattura WHERE slot = 'F2');

-- Le attivita' fatturabili che chiudono la catena: e' `fattura_riga_id`
-- valorizzato a dire «questa riga E' stata fatturata».
INSERT INTO vendite.attivita_fatturabili (
  articolo_id, istanza_utility_id, data_attivita, quantita,
  competenza_mese, competenza_dal, competenza_al,
  uom_id, valuta_id, prezzo_unitario, tipo_doc_fiscale_id,
  commessa_id, commessa_attivita_id, fattura_riga_id,
  -- ⭐ billing_account_id: NOT NULL dal changeSet 20260910-25. Si deriva
  --   dalla COMMESSA, che e' la rotta portante (commessa_id NOT NULL ->
  --   commesse.billing_account_id NOT NULL): la fixture non lo inventa.
  billing_account_id)
SELECT r.articolo_id, r.istanza_utility_id, DATE '2081-01-01', 1,
       DATE '2081-01-01', DATE '2081-01-01', DATE '2081-01-31',
       r.uom_id, r.valuta_id, 10.000000, r.tipo_doc_fiscale_id,
       (SELECT id FROM tmp_eg_commessa),
       (SELECT attivita_id FROM tmp_eg_att WHERE slot = 'G1'),
       (SELECT riga_id FROM tmp_eg_riga WHERE slot = 'F1'),
       (SELECT c.billing_account_id FROM vendite.commesse c
         WHERE c.id = (SELECT id FROM tmp_eg_commessa))
       FROM tmp_eg_refs r;

INSERT INTO vendite.attivita_fatturabili (
  articolo_id, istanza_utility_id, data_attivita, quantita,
  competenza_mese, competenza_dal, competenza_al,
  uom_id, valuta_id, prezzo_unitario, tipo_doc_fiscale_id,
  commessa_id, commessa_attivita_id, fattura_riga_id,
  -- ⭐ billing_account_id: NOT NULL dal changeSet 20260910-25. Si deriva
  --   dalla COMMESSA, che e' la rotta portante (commessa_id NOT NULL ->
  --   commesse.billing_account_id NOT NULL): la fixture non lo inventa.
  billing_account_id)
SELECT r.articolo_id, r.istanza_utility_id, DATE '2081-01-01', 1,
       DATE '2081-01-01', DATE '2081-01-01', DATE '2081-01-31',
       r.uom_id, r.valuta_id, 30.000000, r.tipo_doc_fiscale_id,
       (SELECT id FROM tmp_eg_commessa),
       (SELECT attivita_id FROM tmp_eg_att WHERE slot = 'G3'),
       (SELECT riga_id FROM tmp_eg_riga WHERE slot = 'F2'),
       (SELECT c.billing_account_id FROM vendite.commesse c
         WHERE c.id = (SELECT id FROM tmp_eg_commessa))
       FROM tmp_eg_refs r;

-- L'esito del giro L1 si calcola UNA volta e si interroga: cosi' le sei
-- asserzioni parlano della stessa fotografia, non di sei chiamate diverse.
CREATE TEMP TABLE tmp_eg_esito AS
SELECT * FROM vendite.fn_esito_gruppi_giro(
  ARRAY(SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L1'));

-- ============================================================
-- 2) La vista misura il fatto
-- ============================================================
SELECT ok(
  (SELECT s.n_attivita_fatturate = 1 AND s.n_fatture = 1
     FROM vendite.vw_lotti_gruppi_serviti s
    WHERE s.lotto_id = (SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L1')
      AND s.gruppo_key = (SELECT gruppo_key FROM tmp_eg_key WHERE slot = 'G1')),
  '2. vw_lotti_gruppi_serviti: L1 ha servito G1 con 1 attivita'' su 1 fattura'
);

-- ============================================================
-- 3-5) I tre esiti
-- ============================================================
SELECT ok(
  (SELECT e.esito = 'SERVITO'
      AND e.n_attivita_fatturate = 1
      AND e.lotti_serventi = ARRAY[(SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L1')]
      AND e.lotti_altrui IS NULL
     FROM tmp_eg_esito e
    WHERE e.gruppo_key = (SELECT gruppo_key FROM tmp_eg_key WHERE slot = 'G1')),
  '3. G1 fatturato dal lotto del giro -> SERVITO, lotti_serventi = {L1}'
);

SELECT ok(
  (SELECT e.esito = 'NON_SERVITO'
      AND e.n_attivita_fatturate = 0
      AND e.n_attivita_residue = 1
      AND e.lotti_serventi IS NULL
      AND e.lotti_altrui IS NULL
     FROM tmp_eg_esito e
    WHERE e.gruppo_key = (SELECT gruppo_key FROM tmp_eg_key WHERE slot = 'G2')),
  '4. G2 richiesto e mai fatturato, con righe ancora NON_EMESSA -> NON_SERVITO, residuo 1'
);

-- ⚠️ Il ramo che vale il test: senza il residuo a zero, G3 sarebbe
--   indistinguibile da G2, e il lavoro fermo verrebbe archiviato come gia'
--   sistemato. L'ordine dei rami del CASE E' la regola.
SELECT ok(
  (SELECT e.esito = 'FATTURATO_ALTROVE'
      AND e.n_attivita_fatturate = 0
      AND e.n_attivita_residue = 0
      AND e.lotti_serventi IS NULL
      AND e.lotti_altrui = ARRAY[(SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L2')]
     FROM tmp_eg_esito e
    WHERE e.gruppo_key = (SELECT gruppo_key FROM tmp_eg_key WHERE slot = 'G3')),
  '5. G3 fatturato da un ALTRO lotto, niente residuo -> FATTURATO_ALTROVE, lotti_altrui = {L2}'
);

-- ============================================================
-- 6-7) Invarianza e provenienza del perimetro
-- ============================================================
SELECT ok(
  (SELECT count(*) FILTER (WHERE e.richiesto)                                       = 3
      AND count(*) FILTER (WHERE e.richiesto AND e.esito = 'SERVITO')               = 1
      AND count(*) FILTER (WHERE e.richiesto AND e.esito <> 'SERVITO')              = 2
      AND count(*) FILTER (WHERE e.richiesto)
          = count(*) FILTER (WHERE e.richiesto AND e.esito = 'SERVITO')
          + count(*) FILTER (WHERE e.richiesto AND e.esito <> 'SERVITO')
     FROM tmp_eg_esito e),
  '6. Invarianza: richiesti (3) = serviti (1) + non serviti (2), entrambi misurati'
);

SELECT ok(
  (SELECT bool_and(e.richiesto) AND count(*) = 3 FROM tmp_eg_esito e),
  '7. Tutti e tre risultano richiesto=true: il perimetro e'' letto dal DB, non passato dal chiamante'
);

-- ============================================================
-- 8-9) Guard sui parametri
-- ============================================================
-- ⚠️ SQLSTATE esplicito: senza, throws_ok accetterebbe qualunque errore,
--   compreso il crash del guard che si vuole verificare.
SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_esito_gruppi_giro(ARRAY[]::bigint[]) $$,
  'P0001', NULL,
  '8. Array di lotti vuoto: errore di dominio, non una risposta vuota che sembra «nessun gruppo»'
);

SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_esito_gruppi_giro(ARRAY[-1]::bigint[]) $$,
  'P0001', NULL,
  '9. Id lotto non valido: errore di dominio (guard parametri, mai normalizzazione silenziosa)'
);

-- ============================================================
-- 10) Giro di MASSA: nessun perimetro persistito
-- ============================================================
SELECT ok(
  (SELECT e.esito = 'SERVITO' AND e.richiesto = false AND e.n_attivita_fatturate = 1
     FROM vendite.fn_esito_gruppi_giro(
            ARRAY(SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L2')) e
    WHERE e.gruppo_key = (SELECT gruppo_key FROM tmp_eg_key WHERE slot = 'G3')),
  '10. Lotto senza perimetro (giro di massa): i serviti escono con richiesto=false'
);

-- ============================================================
-- 11) ⚠️ FAIL-CLOSED. E'' il presidio del difetto piu' insidioso: la RLS su
--     questa catena e' asimmetrica (fatturazione_lotti_gruppi non ne ha,
--     fatturazione_lotti si'). Se la funzione rispondesse su un perimetro
--     dimezzato, un lotto invisibile produrrebbe «gruppi non serviti» — un
--     falso allarme con l'aria di un dato. Deve SOLLEVARE.
-- ============================================================
-- ⚠️ NON basta svuotare `app.current_user_id`: misurato, con utente NULL
--   `script.fn_scope_ef_whitelist_via_sr` risponde TRUE — «nessuna
--   restrizione», non «nessun accesso» — e i lotti resterebbero tutti
--   visibili. Il cancello vero e' il primo congiunto della policy: si cambia
--   veste, e la sessione smette di essere un operatore.
SELECT set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);

SELECT throws_ok(
  format(
    $$ SELECT * FROM vendite.fn_esito_gruppi_giro(ARRAY[%s]::bigint[]) $$,
    (SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L1')),
  'P0001', NULL,
  '11. Lotto fuori scope: SOLLEVA (fail-closed), non risponde «non servito»'
);

SELECT * FROM finish();
ROLLBACK;
