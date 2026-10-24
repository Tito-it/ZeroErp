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
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): il mondo si COSTRUISCE.
--   Prima billing account, articolo, unita' di misura, tipo documento, stato
--   commessa ed emittente si pescavano «il primo per id», e commessa, righe di
--   commessa, lotti e attivita' fatturabili si scrivevano a mano: su un database
--   ricostruito da zero il primo billing account non c'e' e il file moriva sulla
--   commessa. Ora due commesse emittibili dello stesso cliente
--   (dbops.fn_pgtap_crea_commessa, una per slot: l'attivita' fatturabile e' 1:1
--   con la riga di commessa), i lotti DRAFT dalla loro madre
--   (vendite.fn_create_fatturazione_lotto) e le attivita' fatturabili dal PULL
--   vero col marchio di ciascun lotto — che porta anche la riga di commessa a
--   EMESSA, cio' che prima si scriveva a mano per lo slot RL2. Resta scritto a
--   mano il passo della SELECT del lotto (riga di fattura + lucchetto
--   sull'attivita'): e' il caso del test.
-- rev 2026-10-24 (brief-modello-documento-vendita R-3/R-4): la sorgente ROOT
--   delle due commesse la scrive il builder (p_con_sorgente_root), non piu' un
--   INSERT del test; i due lotti DRAFT nascono da dbops.fn_pgtap_crea_lotto, del
--   cliente (p_del_cliente) e col tipo documento delle righe di commessa, come
--   prima li faceva la madre chiamata col billing account. Il lock_batch_id lo
--   decide la madre e si rilegge dal builder. Asserzioni invariate.
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
-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_commessa (rev
--   2026-10-24), sull'operatore dell'azienda che costruisce
--   (fn_pgtap_crea_mondo_cliente, ramo «nessun contesto»).
CREATE TEMP TABLE tmp_comm_rl AS
SELECT 'RL1'::text AS slot, c.*
  FROM dbops.fn_pgtap_crea_commessa('reset lotto draft RL1', 'PRONTA_FATTURAZIONE',
                                    p_con_sorgente_root => true) c;

INSERT INTO tmp_comm_rl
SELECT 'RL2', c.*
  FROM dbops.fn_pgtap_crea_commessa('reset lotto draft RL2', 'PRONTA_FATTURAZIONE',
                                    (SELECT billing_account_id FROM tmp_comm_rl WHERE slot = 'RL1'),
                                    p_con_sorgente_root => true) c;

SELECT plan(16);
-- ============================================================
-- 0) Riferimenti e costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_rl AS
SELECT 'pgtap_reset_lotto_draft'::text AS test_scope;
-- I riferimenti vengono dal mondo costruito: emittente e cliente dal builder,
--   tipo documento dalla riga di commessa che il builder ha scritto. Gli stati
--   del lotto si leggono per codice_interno.
CREATE TEMP TABLE tmp_refs_rl AS
SELECT
  (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DRAFT')     AS stato_draft_id,
  (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'ANNULLATA') AS stato_annullata_id,
  c.billing_account_id,
  ca.tipo_doc_fiscale_id,
  c.emittente_soggetto_ruolo_id AS emittente_sr_id,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'COMMESSA' AND s.attivo IS TRUE)               AS sorgente_id,
  -- le due commesse sono emittibili e hanno la loro riga APPROVATA
  (SELECT bool_and(sc.emittibile) AND count(*) = 2
     FROM tmp_comm_rl k
     JOIN vendite.stati_commessa sc ON sc.id = k.stato_commessa_id
     JOIN vendite.commesse_attivita a ON a.id = k.attivita_id)              AS commesse_ok
  FROM tmp_comm_rl c
  JOIN vendite.commesse_attivita ca ON ca.id = c.attivita_id
 WHERE c.slot = 'RL1';
SELECT ok(
    (
      SELECT stato_draft_id IS NOT NULL
        AND stato_annullata_id IS NOT NULL
        AND billing_account_id IS NOT NULL
        AND tipo_doc_fiscale_id IS NOT NULL
        AND emittente_sr_id IS NOT NULL
        AND sorgente_id IS NOT NULL
        AND commesse_ok IS TRUE
      FROM tmp_refs_rl
    ),
    'Riferimenti minimi presenti'
  );

-- ============================================================
-- Fixture commessa: DUE commesse, una riga di commessa ciascuna, una per
-- ciascuna delle due attivita_fatturabili del file (la UNIQUE su
-- commessa_attivita_id e' 1:1, non si possono condividere).
-- ============================================================
-- ⚠️ Il pull PRETENDE una sorgente ROOT: la scrive il builder
--   (p_con_sorgente_root, sorgente COMMESSA, chiave = id della commessa).

CREATE TEMP TABLE tmp_ca_rl AS
SELECT c.slot, c.attivita_id, c.commessa_id
  FROM tmp_comm_rl c;
-- ============================================================
-- 1) Inserimento lotto DRAFT
-- ============================================================
-- 🔴 EMITTENTE (2026-08-18, vale per entrambi i lotti di questo file). La policy
--   `rls_fatturazione_lotti_ef_whitelist` ammette, per OPERATORE, solo gli
--   emittenti nella whitelist dell'utente, e la stessa espressione sta nel
--   `WITH CHECK`. ⭐ rev 2026-10-24: il lotto nasce dalla sua madre con
--   l'emittente del mondo costruito, che e' quello dell'operatore del contesto.
-- ⭐ rev R-4: il lotto lo da' dbops.fn_pgtap_crea_lotto (madre sotto), del
--   cliente e col tipo documento della riga di commessa, che il pull confronta.
-- ⛔ Il builder scrive in un'istruzione, il lotto si rilegge in un'altra: nella
--   stessa, la snapshot non vedrebbe la riga appena scritta.
CREATE TEMP TABLE tmp_lotto_rl AS
SELECT l.lotto_id AS id, l.lock_batch_id
  FROM tmp_refs_rl r,
       dbops.fn_pgtap_crea_lotto('reset lotto draft RL1', 'DRAFT', r.billing_account_id,
                                 r.tipo_doc_fiscale_id, p_del_cliente => true) l;
SELECT ok(
    (
      SELECT count(*) = 1
      FROM tmp_lotto_rl t
      JOIN vendite.fatturazione_lotti fl ON fl.id = t.id
     WHERE fl.stato_doc_fiscale_id = (SELECT stato_draft_id FROM tmp_refs_rl)
       AND fl.billing_account_id = (SELECT billing_account_id FROM tmp_refs_rl)
       AND t.lock_batch_id IS NOT NULL
    ),
    'Inserimento lotto DRAFT'
  );
-- ============================================================
-- 2) Inserimento attivita_fatturabili di test
-- ============================================================
-- ⭐ L'attivita' fatturabile nasce dal PULL vero, col marchio del lotto: prima
--   era un INSERT diretto in vendite.attivita_fatturabili.
CREATE TEMP TABLE tmp_pull_rl AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
         p_commessa_id   => (SELECT commessa_id FROM tmp_ca_rl WHERE slot = 'RL1'),
         p_emit_batch_id => (SELECT lock_batch_id FROM tmp_lotto_rl));

CREATE TEMP TABLE tmp_attivita_rl AS
SELECT af.id
  FROM vendite.attivita_fatturabili af
 WHERE af.commessa_attivita_id = (SELECT attivita_id FROM tmp_ca_rl WHERE slot = 'RL1')
   AND af.emit_batch_id = (SELECT lock_batch_id FROM tmp_lotto_rl);
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
      meta, competenza_dal, competenza_al
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
      ), script.fn_data_operativa(), script.fn_data_operativa()
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
        -- ⛔ `stato_lotto` NON si asserisce piu' qui (rev 2026-09-07,
        --   changeSet 20260907-08): l'annullo non lo scrive piu'. Scriveva
        --   'COMPLETATO', e su un lotto interrotto o fallito era una bugia —
        --   la macchina a stati vieta ERRORE -> COMPLETATO, e quell'UPDATE
        --   diretto le passava dietro.
        -- ⭐ Che l'annullo lasci quella colonna com'era lo presidia, sui due
        --   versi, db/pgtap/vendite/test-annulla-lotto-non-riscrive-stato-v1.sql:
        --   qui sarebbe un terzo posto in cui la stessa regola e' scritta.
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
CREATE TEMP TABLE tmp_lotto_rl2 AS
SELECT l.lotto_id AS id, l.lock_batch_id
  FROM tmp_refs_rl r,
       dbops.fn_pgtap_crea_lotto('reset lotto draft RL2', 'DRAFT', r.billing_account_id,
                                 r.tipo_doc_fiscale_id, p_del_cliente => true) l;

-- L'attivita' dello slot RL2 nasce dal PULL della seconda commessa, col marchio
--   del secondo lotto.
CREATE TEMP TABLE tmp_pull_rl2 AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
         p_commessa_id   => (SELECT commessa_id FROM tmp_ca_rl WHERE slot = 'RL2'),
         p_emit_batch_id => (SELECT lock_batch_id FROM tmp_lotto_rl2));

CREATE TEMP TABLE tmp_attivita_rl2 AS
SELECT af.id
  FROM vendite.attivita_fatturabili af
 WHERE af.commessa_attivita_id = (SELECT attivita_id FROM tmp_ca_rl WHERE slot = 'RL2')
   AND af.emit_batch_id = (SELECT lock_batch_id FROM tmp_lotto_rl2);
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
      meta, competenza_dal, competenza_al
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
      ), script.fn_data_operativa(), script.fn_data_operativa()
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
-- ⚠️ La commessa_attivita dello slot RL2 deve essere EMESSA prima della
--   chiamata: e' cio' che rende SIGNIFICATIVA l'asserzione su
--   `riemesse_attivita` (lasciata NON_EMESSA, quel contatore varrebbe 0 sia con
--   la correzione sia senza). ⭐ rev 2026-10-24: ce la porta il PULL qui sopra,
--   per la via vera; prima la riga nasceva NON_EMESSA e la si portava a EMESSA a
--   mano. Il 14 la vuole di nuovo NON_EMESSA dopo la mutazione.
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
