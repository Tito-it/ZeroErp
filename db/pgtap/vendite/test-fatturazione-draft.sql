-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: selezione attivita_fatturabili per pipeline DRAFT
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Inserimento attivita_fatturabili di test
-- 3) Selezione + lock ritorna 1 riga
-- 4) Lock attivato sulla riga
-- 5) Lock_batch_id valorizzato
-- 6) Cleanup completato
--
-- ⚠️ rev 2026-08-18 (bonifica baseline). La fixture inseriva una
-- attivita_fatturabile senza commessa: non e' piu' un caso possibile
-- (commessa_id / commessa_attivita_id NOT NULL + guard a10). Il soggetto del
-- test — selezione e lock in DRAFT — e' intatto: passa dalla commessa come
-- l'applicazione. Modello: test-vw-dash-competenza-v1.
-- ⚠️ E i riferimenti sceglievano articolo, istanza utility e billing account
-- da TRE query indipendenti: nulla garantiva che l'istanza appartenesse a
-- quel BA, e fn_select_attivita_fatturabili filtra su entrambi. Ora il
-- billing account si sceglie UNA volta e le colonne correlate vengono da li'.
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
-- 0) Riferimenti e costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_fd AS
SELECT
  'pgtap_fatturazione_draft'::text AS test_scope,
  uuidv7() AS lock_batch_id,
  uuidv7() AS sorgente_uid;

CREATE TEMP TABLE tmp_refs_fd AS
-- Il billing account si sceglie UNA volta: utility e istanza vengono dalla
-- stessa riga, non da tre LIMIT 1 scorrelati.
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
  (SELECT s2.id FROM config.sorgenti s2
    WHERE s2.attivo IS TRUE ORDER BY s2.id LIMIT 1) AS sorgente_tipo_id,
  (SELECT u.id FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)   AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)   AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT sc.id FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE AND sc.codice_interno <> 'ANNULLATA'
    ORDER BY sc.id LIMIT 1)           AS stato_commessa_id,
  (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1) AS emittente_sr_id;

SELECT ok(
  (SELECT articolo_id IS NOT NULL
     AND istanza_utility_id IS NOT NULL
     AND billing_account_id IS NOT NULL
     AND utility_id IS NOT NULL
     AND sorgente_tipo_id IS NOT NULL
     AND tipo_doc_fiscale_id IS NOT NULL
     AND valuta_id IS NOT NULL
     AND stato_commessa_id IS NOT NULL
     AND emittente_sr_id IS NOT NULL
   FROM tmp_refs_fd),
  'Riferimenti minimi presenti'
);

-- ============================================================
-- Fixture commessa: una attivita_fatturabile non esiste senza la coppia
-- commessa_id / commessa_attivita_id (NOT NULL + guard a10).
-- ============================================================
CREATE TEMP TABLE tmp_commessa_fd AS
WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                emittente_soggetto_ruolo_id, stato_commessa_id)
  SELECT 'PGTAP-FD-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id, r.emittente_sr_id, r.stato_commessa_id
    FROM tmp_refs_fd r
  RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_ca_fd AS
WITH ins AS (
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
  SELECT (SELECT id FROM tmp_commessa_fd),
         'PGTAP-FD-SEG-' || substr(md5(clock_timestamp()::text), 1, 12),
         r.articolo_id, r.istanza_utility_id, script.fn_data_operativa(), r.uom_id, 1,
         date_trunc('month', script.fn_data_operativa())::date,
         date_trunc('month', script.fn_data_operativa())::date,
         (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
         r.tipo_doc_fiscale_id, r.valuta_id, 1.000000, 'FIXED',
         'BOZZA', 'NON_EMESSA', (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
         ((SELECT id FROM tmp_commessa_fd))::text
    FROM tmp_refs_fd r
  RETURNING id)
SELECT id FROM ins;

-- ============================================================
-- 1) Inserimento attivita_fatturabili di test
-- ============================================================
CREATE TEMP TABLE tmp_attivita_fd AS
WITH ins AS (
  INSERT INTO vendite.attivita_fatturabili (
    articolo_id,
    istanza_utility_id,
    billing_account_id,
    data_attivita,
    competenza_mese,
    competenza_dal,
    competenza_al,
    quantita,
    approvato,
    sospesa,
    tipo_doc_fiscale_id,
    valuta_id,
    sorgente_tipo_id,
    sorgente_uid,
    sorgente_riga,
    commessa_id,
    commessa_attivita_id,
    emit_batch_id,
    meta
  )
  SELECT
    r.articolo_id,
    r.istanza_utility_id,
    r.billing_account_id,
    script.fn_data_operativa(),
    date_trunc('month', script.fn_data_operativa())::date,
    date_trunc('month', script.fn_data_operativa())::date,
    (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
    1,
    true,
    false,
    r.tipo_doc_fiscale_id,
    r.valuta_id,
    NULL,
    NULL,
    NULL,
    (SELECT id FROM tmp_commessa_fd),
    (SELECT id FROM tmp_ca_fd),
    -- ⛔ 2026-09-04 (changeSet 20260904-50). Da qui in poi
    --   `vendite.fn_select_attivita_fatturabili` prende SOLO le righe marchiate
    --   col proprio giro: `a.emit_batch_id = p_lock_batch_id`. Una riga senza
    --   marchio non e' piu' eleggibile, e la select tornava zero — che e'
    --   esattamente l'effetto voluto dal cantiere «esito parziale», non un
    --   difetto da aggirare.
    --   ⇒ La fixture si marchia col PROPRIO giro, che e' cio' che fara' il
    --     backend quando il pull passera' il lock_batch_id del lotto. Deve
    --     essere lo STESSO uuid che il test 2 passa come p_lock_batch_id, o il
    --     filtro escluderebbe la riga appena creata.
    (SELECT lock_batch_id FROM tmp_costanti_fd),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_fd))
  FROM tmp_refs_fd r
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT count(*) = 1 FROM tmp_attivita_fd),
  'Inserimento attivita_fatturabili di test'
);

-- ============================================================
-- 2) Selezione + lock
-- ============================================================
SELECT is(
  (
    SELECT count(*)::int
    FROM vendite.fn_select_attivita_fatturabili(
      p_competenza_mese => date_trunc('month', script.fn_data_operativa())::date,
      p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_fd),
      p_lock_batch_id => (SELECT lock_batch_id FROM tmp_costanti_fd),
      p_lock => true,
      p_data_fatturazione => script.fn_data_operativa(),
      p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_fd),
      p_utility_id => (SELECT utility_id FROM tmp_refs_fd),
      p_valuta_id => (SELECT valuta_id FROM tmp_refs_fd),
      p_emittente_soggetto_ruolo_id => NULL,
      p_area_geografica_id => NULL,
      p_limit => 10
    )
  ),
  1,
  'Selezione + lock ritorna 1 riga'
);

SELECT is(
  (
    SELECT lock_in_fatturazione
    FROM vendite.attivita_fatturabili
    WHERE id = (SELECT id FROM tmp_attivita_fd)
  ),
  true,
  'Lock attivato sulla riga'
);

SELECT is(
  (
    SELECT lock_batch_id
    FROM vendite.attivita_fatturabili
    WHERE id = (SELECT id FROM tmp_attivita_fd)
  ),
  (SELECT lock_batch_id FROM tmp_costanti_fd),
  'Lock_batch_id valorizzato'
);

-- ============================================================
-- Cleanup
-- ============================================================
DELETE FROM vendite.attivita_fatturabili
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_fd);

SELECT ok(true, 'Cleanup completato');

SELECT * FROM finish();

ROLLBACK;
