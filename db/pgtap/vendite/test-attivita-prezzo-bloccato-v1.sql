-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: colonna prezzo_bloccato su vendite.attivita_fatturabili (changeset 20260224-04)
-- ------------------------------------------------------------
-- Indice test (1..5):
-- 1) Colonna prezzo_bloccato presente
-- 2) Colonna prezzo_bloccato NOT NULL
-- 3) Default prezzo_bloccato = false
-- 4) Fixture: commessa + attivita' di commessa create
-- 5) Inserimento base valorizza prezzo_bloccato=false di default
--
-- ⚠️ rev 2026-08-18 (bonifica baseline). Il test 5 inseriva una
-- attivita_fatturabile "nuda". Non e' piu' un caso possibile: commessa_id e
-- commessa_attivita_id sono NOT NULL sulla tabella, e prima ancora c'e'
-- trg_attivita_fatturabili_a10_guard_commessa. Non c'e' nulla da ritirare —
-- il soggetto del test e' il DEFAULT della colonna, che e' vivo: era morta la
-- scorciatoia con cui la fixture ci arrivava. Ora passa dalla commessa, come
-- l'applicazione. Modello: test-vw-dash-competenza-v1 (INSERT diretti, senza
-- fn_get_or_create_commessa: non serve il giro delle sorgenti per due righe).
-- ⚠️ Secondo strato trovato per strada: competenza_dal / competenza_al sono
-- diventate NOT NULL e la fixture non le passava.
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

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'attivita_fatturabili'
      AND c.column_name = 'prezzo_bloccato'
  ),
  'Colonna prezzo_bloccato presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'attivita_fatturabili'
      AND c.column_name = 'prezzo_bloccato'
      AND c.is_nullable = 'NO'
  ),
  'Colonna prezzo_bloccato NOT NULL'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'attivita_fatturabili'
      AND c.column_name = 'prezzo_bloccato'
      AND c.column_default ILIKE '%false%'
  ),
  'Default prezzo_bloccato = false'
);

CREATE TEMP TABLE tmp_refs_apb AS
-- Il billing account si sceglie UNA volta: la CTE evita che le colonne
-- correlate arrivino da righe diverse.
WITH ba AS (
  SELECT b.id, b.utility_id, b.istanza_utility_id
    FROM anagrafiche.billing_account b
   WHERE b.utility_id IS NOT NULL
     AND b.istanza_utility_id IS NOT NULL
     AND b.soggetto_ruolo_id IS NOT NULL
   ORDER BY b.id
   LIMIT 1
)
SELECT
  (SELECT id FROM ba)                 AS billing_account_id,
  (SELECT utility_id FROM ba)         AS utility_id,
  (SELECT istanza_utility_id FROM ba) AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE
    ORDER BY a.id LIMIT 1)            AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT sc.id FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE AND sc.codice_interno <> 'ANNULLATA'
    ORDER BY sc.id LIMIT 1)           AS stato_commessa_id,
  (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1) AS emittente_sr_id;

-- ============================================================
-- Fixture: la commessa e la sua attivita'. Una attivita_fatturabile non
-- esiste piu' senza questa coppia (uq_attivita_fatturabili_commessa_attivita
-- e' 1:1: una AF per attivita' di commessa).
-- ============================================================
CREATE TEMP TABLE tmp_commessa_apb AS
WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                emittente_soggetto_ruolo_id, stato_commessa_id)
  SELECT 'PGTAP-APB-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id, r.emittente_sr_id, r.stato_commessa_id
    FROM tmp_refs_apb r
  RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_ca_apb AS
WITH ins AS (
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
  SELECT (SELECT id FROM tmp_commessa_apb),
         'PGTAP-APB-SEG-' || substr(md5(clock_timestamp()::text), 1, 12),
         r.articolo_id, r.istanza_utility_id, script.fn_data_operativa(), r.uom_id, 1,
         date_trunc('month', script.fn_data_operativa())::date,
         date_trunc('month', script.fn_data_operativa())::date,
         (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
         r.tipo_doc_fiscale_id, r.valuta_id, 1.000000, 'FIXED',
         -- BOZZA di proposito: la riga non deve entrare nelle corsie di
         -- emissione degli altri test che girano nella stessa giornata.
         'BOZZA', 'NON_EMESSA', (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
         ((SELECT id FROM tmp_commessa_apb))::text
    FROM tmp_refs_apb r
  RETURNING id)
SELECT id FROM ins;

SELECT ok(
  (SELECT (SELECT id FROM tmp_commessa_apb) IS NOT NULL
      AND (SELECT id FROM tmp_ca_apb) IS NOT NULL),
  'Fixture: commessa + attivita di commessa create'
);

-- ============================================================
-- Il soggetto del test: prezzo_bloccato non passato -> default della colonna.
-- ============================================================
CREATE TEMP TABLE tmp_ins_apb AS
WITH ins AS (
  INSERT INTO vendite.attivita_fatturabili (
    articolo_id,
    istanza_utility_id,
    billing_account_id,
    data_attivita,
    quantita,
    competenza_mese,
    competenza_dal,
    competenza_al,
    tipo_doc_fiscale_id,
    valuta_id,
    commessa_id,
    commessa_attivita_id,
    meta
  )
  SELECT
    r.articolo_id,
    r.istanza_utility_id,
    r.billing_account_id,
    script.fn_data_operativa(),
    1,
    date_trunc('month', script.fn_data_operativa())::date,
    date_trunc('month', script.fn_data_operativa())::date,
    (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
    r.tipo_doc_fiscale_id,
    r.valuta_id,
    (SELECT id FROM tmp_commessa_apb),
    (SELECT id FROM tmp_ca_apb),
    jsonb_build_object('test_scope', 'pgtap_attivita_prezzo_bloccato')
  FROM tmp_refs_apb r
  RETURNING prezzo_bloccato
)
SELECT * FROM ins;

SELECT is(
  (SELECT prezzo_bloccato FROM tmp_ins_apb),
  false,
  'Inserimento base valorizza prezzo_bloccato=false di default'
);

SELECT * FROM finish();
ROLLBACK;
