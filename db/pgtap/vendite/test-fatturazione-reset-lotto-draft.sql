-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: rollback tecnico lotto MASSIVO in DRAFT
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti (stati, anagrafiche, catalogo)
-- 2) Inserimento lotto DRAFT
-- 3) Inserimento attivita_fatturabili di test
-- 4) Creazione fattura bozza + link lotto
-- 5) Inserimento riga fattura
-- 6) Reset lotto DRAFT
-- 7) Lotto annullato e chiuso
-- 8) Documenti e righe eliminati
-- 9) Attivita_fatturabili ripristinate
-- 10) Cleanup completato (note + righe + fatture)
-- 11) Reset singola fattura DRAFT (nuova funzione)
-- 12) Chiusura test e rollback
-- 13) 🔴 L'attivita' della fattura tolta e' tornata LIBERA
-- 14) 🔴 La sua commessa_attivita e' tornata NON_EMESSA
-- 15) Il contatore updated_attivita dice 1 (non 0)
-- 16) Il contatore riemesse_attivita dice 1 (non 0)
--
-- ⛔ rev 2026-08-26 — PERCHE' I QUATTRO IN FONDO SONO STATI AGGIUNTI
--   Fino a oggi l'ultimo test costruiva ESATTAMENTE il caso giusto — lotto
--   DRAFT, commessa_attivita, attivita' portata a mano ad agganciata +
--   fatturata + lucchettata — e poi asseriva su `deleted_fatture`, che e' una
--   colonna A SINISTRA di quella che si era rotta. Fra il 2026-07-28 e il
--   2026-08-26 `updated_attivita` valeva 0 e questo file era VERDE.
--   Il difetto non era «mancava un test»: il test c'era, la fixture era
--   corretta, e l'asserzione guardava la colonna sbagliata.
--   Brief: brief-db-lavoro-che-non-torna-indietro §8.4.
--
-- ⚠️ E la commessa_attivita dello slot RL2 viene portata a EMESSA PRIMA della
--   chiamata. Senza quel passo nasce NON_EMESSA, quindi `riemesse_attivita`
--   varrebbe 0 sia con la correzione sia senza: sarebbe verde per sottrazione.
--
-- ⚠️ La mutazione e' chiamata in un'ISTRUZIONE SEPARATA dalle asserzioni e il
--   risultato e' materializzato in una temp: dentro la stessa istruzione la
--   snapshot leggerebbe lo stato PRIMA delle scritture, e il rosso accuserebbe
--   la funzione invece del test.
--
-- ⚠️ rev 2026-08-18 (bonifica baseline). I due inserimenti di
-- attivita_fatturabili erano "nudi": non e' piu' un caso possibile
-- (commessa_id / commessa_attivita_id NOT NULL + guard a10). Il soggetto —
-- il rollback tecnico del lotto in DRAFT — e' intatto. Modello:
-- test-vw-dash-competenza-v1.
-- ⚠️ Le due attivita' hanno commesse_attivita DISTINTE:
-- uq_attivita_fatturabili_commessa_attivita e' 1:1, riusare la stessa avrebbe
-- fatto scattare quella UNIQUE al posto di cio' che il test verifica.
-- ⚠️ E i riferimenti sceglievano articolo, istanza utility e billing account
-- da tre LIMIT 1 scorrelati: ora il billing account si sceglie una volta sola.
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

SELECT plan(16);
-- ============================================================
-- 0) Riferimenti e costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_rl AS
SELECT 'pgtap_reset_lotto_draft'::text AS test_scope,
  uuidv7() AS lock_batch_id;
CREATE TEMP TABLE tmp_refs_rl AS
-- Il billing account si sceglie UNA volta: utility e istanza vengono da li'.
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
  (SELECT id FROM config.stati_doc_fiscale
    WHERE upper(btrim(codice)) = 'DRAFT' ORDER BY id LIMIT 1)     AS stato_draft_id,
  (SELECT id FROM config.stati_doc_fiscale
    WHERE upper(btrim(codice)) = 'ANNULLATA' ORDER BY id LIMIT 1) AS stato_annullata_id,
  (SELECT id FROM ba)                 AS billing_account_id,
  (SELECT utility_id FROM ba)         AS utility_id,
  (SELECT istanza_utility_id FROM ba) AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE
    ORDER BY a.id LIMIT 1)            AS articolo_id,
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
    (
      SELECT stato_draft_id IS NOT NULL
        AND stato_annullata_id IS NOT NULL
        AND articolo_id IS NOT NULL
        AND istanza_utility_id IS NOT NULL
        AND billing_account_id IS NOT NULL
        AND utility_id IS NOT NULL
        AND tipo_doc_fiscale_id IS NOT NULL
        AND valuta_id IS NOT NULL
        AND stato_commessa_id IS NOT NULL
        AND emittente_sr_id IS NOT NULL
      FROM tmp_refs_rl
    ),
    'Riferimenti minimi presenti'
  );

-- ============================================================
-- Fixture commessa: una commessa e DUE attivita' di commessa, una per
-- ciascuna delle due attivita_fatturabili del file (la UNIQUE su
-- commessa_attivita_id e' 1:1, non si possono condividere).
-- ============================================================
CREATE TEMP TABLE tmp_commessa_rl AS
WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                emittente_soggetto_ruolo_id, stato_commessa_id)
  SELECT 'PGTAP-RL-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id, r.emittente_sr_id, r.stato_commessa_id
    FROM tmp_refs_rl r
  RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_ca_rl (slot text, attivita_id bigint);

WITH ins AS (
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
  SELECT (SELECT id FROM tmp_commessa_rl),
         'PGTAP-RL-SEG-1-' || substr(md5(clock_timestamp()::text), 1, 12),
         r.articolo_id, r.istanza_utility_id, current_date, r.uom_id, 1,
         date_trunc('month', current_date)::date,
         date_trunc('month', current_date)::date,
         (date_trunc('month', current_date) + INTERVAL '1 month - 1 day')::date,
         r.tipo_doc_fiscale_id, r.valuta_id, 10.000000, 'FIXED',
         'BOZZA', 'NON_EMESSA', NULL, NULL
    FROM tmp_refs_rl r
  RETURNING id)
INSERT INTO tmp_ca_rl SELECT 'RL1', id FROM ins;

WITH ins AS (
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
  SELECT (SELECT id FROM tmp_commessa_rl),
         'PGTAP-RL-SEG-2-' || substr(md5(clock_timestamp()::text), 1, 12),
         r.articolo_id, r.istanza_utility_id, current_date, r.uom_id, 1,
         date_trunc('month', current_date)::date,
         date_trunc('month', current_date)::date,
         (date_trunc('month', current_date) + INTERVAL '1 month - 1 day')::date,
         r.tipo_doc_fiscale_id, r.valuta_id, 10.000000, 'FIXED',
         'BOZZA', 'NON_EMESSA', NULL, NULL
    FROM tmp_refs_rl r
  RETURNING id)
INSERT INTO tmp_ca_rl SELECT 'RL2', id FROM ins;
-- ============================================================
-- 1) Inserimento lotto DRAFT
-- ============================================================
-- 🔴 EMITTENTE, aggiunto il 2026-08-18 (vale per entrambi gli inserimenti di
--   lotto di questo file). La policy `rls_fatturazione_lotti_ef_whitelist`
--   ammette, per OPERATORE, solo gli emittenti nella whitelist dell'utente, e
--   la stessa espressione sta nel `WITH CHECK`: senza
--   `emittente_soggetto_ruolo_id` l'INSERT moriva con «la nuova riga viola la
--   regola di sicurezza per riga». `script.fn_pgtap_emittente_sr_operatore()`
--   e' la compagna esatta di `fn_scope_ef_whitelist_via_sr`, che la policy
--   interroga. Brief: brief-db-pgtap-runner-rls-baseline §26.
CREATE TEMP TABLE tmp_lotto_rl AS WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
      lock_batch_id,
      competenza_mese,
      tipo_doc_fiscale_id,
      utility_id,
      billing_account_id,
      stato_doc_fiscale_id,
      emittente_soggetto_ruolo_id
    )
  SELECT (
      SELECT lock_batch_id
      FROM tmp_costanti_rl
    ),
    date_trunc('month', current_date)::date,
    r.tipo_doc_fiscale_id,
    r.utility_id,
    r.billing_account_id,
    r.stato_draft_id,
    script.fn_pgtap_emittente_sr_operatore()
  FROM tmp_refs_rl r
  RETURNING id,
    lock_batch_id
)
SELECT *
FROM ins;
SELECT ok(
    (
      SELECT count(*) = 1
      FROM tmp_lotto_rl
    ),
    'Inserimento lotto DRAFT'
  );
-- ============================================================
-- 2) Inserimento attivita_fatturabili di test
-- ============================================================
CREATE TEMP TABLE tmp_attivita_rl AS WITH ins AS (
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
      commessa_id,
      commessa_attivita_id,
      meta
    )
  SELECT r.articolo_id,
    r.istanza_utility_id,
    r.billing_account_id,
    current_date,
    date_trunc('month', current_date)::date,
    date_trunc('month', current_date)::date,
    (date_trunc('month', current_date) + INTERVAL '1 month - 1 day')::date,
    1,
    true,
    false,
    r.tipo_doc_fiscale_id,
    r.valuta_id,
    (SELECT id FROM tmp_commessa_rl),
    (SELECT attivita_id FROM tmp_ca_rl WHERE slot = 'RL1'),
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_rl
      )
    )
  FROM tmp_refs_rl r
  RETURNING id
)
SELECT *
FROM ins;
SELECT ok(
    (
      SELECT count(*) = 1
      FROM tmp_attivita_rl
    ),
    'Inserimento attivita_fatturabili di test'
  );
-- ============================================================
-- 3) Creazione fattura bozza + link lotto
-- ============================================================
CREATE TEMP TABLE tmp_fattura_rl AS
SELECT vendite.fn_get_or_create_fattura_header(
    p_lotto_id => (
      SELECT id
      FROM tmp_lotto_rl
    ),
    p_attivita_id => (
      SELECT id
      FROM tmp_attivita_rl
    )
  ) AS fattura_id;
SELECT ok(
    (
      SELECT fattura_id IS NOT NULL
      FROM tmp_fattura_rl
    ),
    'Creazione fattura bozza + link lotto'
  );
-- ============================================================
-- 4) Inserimento riga fattura
-- ============================================================
CREATE TEMP TABLE tmp_fattura_riga_rl AS WITH ins AS (
  INSERT INTO vendite.fatture_righe (
      fattura_id,
      riga_nr,
      descrizione,
      qta,
      prezzo_unitario,
      meta
    )
  VALUES (
      (
        SELECT fattura_id
        FROM tmp_fattura_rl
      ),
      1,
      'Riga test rollback',
      1,
      10,
      jsonb_build_object(
        'test_scope',
        (
          SELECT test_scope
          FROM tmp_costanti_rl
        )
      )
    )
  RETURNING id
)
SELECT *
FROM ins;
UPDATE vendite.attivita_fatturabili
SET lock_in_fatturazione = true,
  lock_batch_id = (
    SELECT lock_batch_id
    FROM tmp_lotto_rl
  ),
  fattura_riga_id = (
    SELECT id
    FROM tmp_fattura_riga_rl
  )
WHERE id = (
    SELECT id
    FROM tmp_attivita_rl
  );
SELECT ok(
    (
      SELECT count(*) = 1
      FROM tmp_fattura_riga_rl
    ),
    'Inserimento riga fattura'
  );
-- ============================================================
-- 5) Reset lotto DRAFT
-- ============================================================
SELECT ok(
    (
      SELECT updated_lotti = 1
      FROM vendite.fn_annulla_lotto_da_draft(
          (
            SELECT id
            FROM tmp_lotto_rl
          )
        )
    ),
    'Reset lotto DRAFT'
  );
-- ============================================================
-- 6) Lotto annullato e chiuso
-- ============================================================
SELECT ok(
    (
      SELECT fl.stato_doc_fiscale_id = (
          SELECT stato_annullata_id
          FROM tmp_refs_rl
        )
        AND fl.stato_operativo = 'CHIUSO'
        AND fl.stato_lotto = 'COMPLETATO'
      FROM vendite.fatturazione_lotti fl
      WHERE fl.id = (
          SELECT id
          FROM tmp_lotto_rl
        )
    ),
    'Lotto annullato e chiuso'
  );
-- ============================================================
-- 7) Documenti e righe eliminati
-- ============================================================
SELECT ok(
    (
      SELECT count(*) = 0
      FROM vendite.fatture f
      WHERE f.id = (
          SELECT fattura_id
          FROM tmp_fattura_rl
        )
    ),
    'Fatture eliminate'
  );
SELECT ok(
    (
      SELECT count(*) = 0
      FROM vendite.fatture_righe r
      WHERE r.id = (
          SELECT id
          FROM tmp_fattura_riga_rl
        )
    ),
    'Righe fattura eliminate'
  );
-- ============================================================
-- 8) Attivita_fatturabili ripristinate
-- ============================================================
SELECT ok(
    (
      SELECT lock_in_fatturazione IS FALSE
        AND lock_batch_id IS NULL
        AND fatturato IS FALSE
        AND fattura_riga_id IS NULL
      FROM vendite.attivita_fatturabili
      WHERE id = (
          SELECT id
          FROM tmp_attivita_rl
        )
    ),
    'Attivita_fatturabili ripristinate'
  );
SELECT ok(
    (
      SELECT count(*) = 0
      FROM vendite.note
      WHERE meta->>'test_scope' = (
          SELECT test_scope
          FROM tmp_costanti_rl
        )
    ),
    'Cleanup completato'
  );
-- ============================================================
-- 9) Reset singola fattura DRAFT
-- ============================================================
CREATE TEMP TABLE tmp_lotto_rl2 AS WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
      lock_batch_id,
      competenza_mese,
      tipo_doc_fiscale_id,
      utility_id,
      billing_account_id,
      stato_doc_fiscale_id,
      emittente_soggetto_ruolo_id
    )
  SELECT uuidv7(),
    date_trunc('month', current_date)::date,
    r.tipo_doc_fiscale_id,
    r.utility_id,
    r.billing_account_id,
    r.stato_draft_id,
    script.fn_pgtap_emittente_sr_operatore()
  FROM tmp_refs_rl r
  RETURNING id,
    lock_batch_id
)
SELECT *
FROM ins;
CREATE TEMP TABLE tmp_attivita_rl2 AS WITH ins AS (
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
      commessa_id,
      commessa_attivita_id,
      meta
    )
  SELECT r.articolo_id,
    r.istanza_utility_id,
    r.billing_account_id,
    current_date,
    date_trunc('month', current_date)::date,
    date_trunc('month', current_date)::date,
    (date_trunc('month', current_date) + INTERVAL '1 month - 1 day')::date,
    1,
    true,
    false,
    r.tipo_doc_fiscale_id,
    r.valuta_id,
    (SELECT id FROM tmp_commessa_rl),
    (SELECT attivita_id FROM tmp_ca_rl WHERE slot = 'RL2'),
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_rl
      )
    )
  FROM tmp_refs_rl r
  RETURNING id
)
SELECT *
FROM ins;
CREATE TEMP TABLE tmp_fattura_rl2 AS
SELECT vendite.fn_get_or_create_fattura_header(
    p_lotto_id => (
      SELECT id
      FROM tmp_lotto_rl2
    ),
    p_attivita_id => (
      SELECT id
      FROM tmp_attivita_rl2
    )
  ) AS fattura_id;
CREATE TEMP TABLE tmp_fattura_riga_rl2 AS WITH ins AS (
  INSERT INTO vendite.fatture_righe (
      fattura_id,
      riga_nr,
      descrizione,
      qta,
      prezzo_unitario,
      meta
    )
  VALUES (
      (
        SELECT fattura_id
        FROM tmp_fattura_rl2
      ),
      1,
      'Riga test reset singolo',
      1,
      10,
      jsonb_build_object(
        'test_scope',
        (
          SELECT test_scope
          FROM tmp_costanti_rl
        )
      )
    )
  RETURNING id
)
SELECT *
FROM ins;
UPDATE vendite.attivita_fatturabili
SET lock_in_fatturazione = true,
  lock_batch_id = (
    SELECT lock_batch_id
    FROM tmp_lotto_rl2
  ),
  fattura_riga_id = (
    SELECT id
    FROM tmp_fattura_riga_rl2
  )
WHERE id = (
    SELECT id
    FROM tmp_attivita_rl2
  );
-- ⚠️ La commessa_attivita dello slot RL2 nasce NON_EMESSA. Portarla a EMESSA
--   e' cio' che rende SIGNIFICATIVA l'asserzione su `riemesse_attivita`:
--   lasciandola dov'era, quel contatore varrebbe 0 sia con la correzione sia
--   senza, e il test sarebbe verde per sottrazione.
UPDATE vendite.commesse_attivita
SET stato_emissione = 'EMESSA'
WHERE id = (
    SELECT attivita_id
    FROM tmp_ca_rl
    WHERE slot = 'RL2'
  );
-- ⚠️ La mutazione gira in un'ISTRUZIONE SEPARATA e il suo esito si
--   materializza: chiamandola dentro l'asserzione, la snapshot di statement
--   leggerebbe lo stato PRIMA delle scritture.
CREATE TEMP TABLE tmp_esito_rl2 AS
SELECT *
FROM vendite.fn_elimina_fattura_da_lotto(
    p_lotto_id => (
      SELECT id
      FROM tmp_lotto_rl2
    ),
    p_fattura_id => (
      SELECT fattura_id
      FROM tmp_fattura_rl2
    )
  );
SELECT ok(
    (
      SELECT deleted_fatture = 1
      FROM tmp_esito_rl2
    ),
    'Reset singola fattura DRAFT'
  );
-- ============================================================
-- 13) 🔴 L'attivita' e tornata LIBERA — l asserzione che mancava
-- ============================================================
-- ⛔ E' la colonna che si era rotta. Con il ripristino a valle del DELETE
--   (fino al 2026-08-26) qui restava fatturato = true e il lucchetto messo:
--   l attivita usciva dal giro e fn_select_attivita_fatturabili non la
--   sceglieva mai piu.
SELECT ok(
    (
      SELECT a.fatturato IS FALSE
        AND a.fattura_riga_id IS NULL
        AND COALESCE(a.lock_in_fatturazione, false) IS FALSE
        AND a.lock_batch_id IS NULL
        AND a.stato_esecuzione IS NULL
      FROM vendite.attivita_fatturabili a
      WHERE a.id = (
          SELECT id
          FROM tmp_attivita_rl2
        )
    ),
    '13) l attivita della fattura tolta e tornata libera (timbro, legame, lucchetto, stato)'
  );
-- ============================================================
-- 14) 🔴 La commessa_attivita e tornata NON_EMESSA
-- ============================================================
-- ⛔ Il secondo livello, e il piu costoso: senza,
--   fn_emit_attivita_fatturabili_da_commessa filtra su EMESSA e non la
--   ri-emette mai piu. Due porte chiuse invece di una.
SELECT is(
    (
      SELECT ca.stato_emissione
      FROM vendite.commesse_attivita ca
      WHERE ca.id = (
          SELECT attivita_id
          FROM tmp_ca_rl
          WHERE slot = 'RL2'
        )
    ),
    'NON_EMESSA'::character varying,
    '14) la commessa_attivita della fattura tolta e tornata NON_EMESSA'
  );
-- ============================================================
-- 15-16) I due contatori dicono quello che e successo
-- ============================================================
-- ⚠️ Sono le colonne che la funzione restituisce e che nessuno leggeva: un
--   ripristino che non ripristina si vede QUI prima che altrove.
SELECT is(
    (
      SELECT updated_attivita
      FROM tmp_esito_rl2
    ),
    1,
    '15) updated_attivita = 1 (era 0 con il ripristino a valle del DELETE)'
  );
SELECT is(
    (
      SELECT riemesse_attivita
      FROM tmp_esito_rl2
    ),
    1,
    '16) riemesse_attivita = 1 (la commessa_attivita era EMESSA per costruzione)'
  );
SELECT *
FROM finish();
ROLLBACK;
