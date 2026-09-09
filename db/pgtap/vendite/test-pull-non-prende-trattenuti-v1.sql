-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: P-5 — vendite.fn_emit_attivita_fatturabili_da_commessa non prende una
--       riga trattenuta da un ALTRO lotto in gioco, e riprende le PROPRIE.
--
-- Elenco test (plan 5) — numerati come li stampa il TAP:
--  0) riferimenti minimi risolti
--  1) 🔴 il pull NON emette una riga trattenuta da un ALTRO lotto in gioco
--  2) ⭐ e il verso opposto: la riga LIBERA della stessa commessa passa
--  3) ⭐⭐ RERUN: la riga trattenuta dal PROPRIO lotto viene ripresa
--  4) ⚠️ senza identita' del giro (p_emit_batch_id NULL) la trattenuta resta
--        fuori — la risposta prudente
--
-- ────────────────────────────────────────────────────────────────
-- 🔴 PERCHE' QUESTO TEST ESISTE — il collaudo del 2026-09-09.
--   La card diceva 4, l'elenco ne mostrava 3 e sbarrava ORD0036005, gia'
--   trattenuto da LTF-0010331. Premuto «Fattura», ORD0036005 e' finito in un
--   lotto NUOVO.
--   ⛔ Il changeSet 20260909-25 aveva insegnato a `fn_list_emittibili_lane` a
--   non offrirlo. Ma LA LANE NON DECIDE COSA IL GIRO PRENDE: decide quanti
--   giri partono. Se la terna ha altro lavoro il lotto nasce comunque, e IL
--   PULL rastrella tutto. La porta e' questa funzione.
--
-- ⭐⭐ IL TEST 3 E' QUELLO CHE VALE, e non e' il caso principale.
--   Un RERUN dello stesso lotto («avanza step», resume di un giro fermo) trova
--   i PROPRI documenti gia' marcati in fatturazione_lotti_esiti: il giro
--   precedente ha fallito la commessa, il savepoint del fan-out ha rimesso le
--   righe a NON_EMESSA, ma l'esito e' scritto FUORI dal savepoint.
--   ⇒ Senza l'auto-esclusione il rilancio salterebbe esattamente le righe che
--   deve riprovare. In silenzio: nessun errore, un lotto che riparte e non
--   produce niente, indistinguibile da un mese senza lavoro.
--   ⛔ Con il solo test 1 questo file passerebbe anche su una correzione che
--   blocca TUTTO cio' che ha un esito — cioe' che rompe il rilancio.
--
-- ⛔ I CASI SI COSTRUISCONO: due commesse, due lotti, e gli esiti attaccati a
--   mano. Su un database ricostruito da zero non c'e' niente da «trovare».
--
-- ChangeSet: 20260909-62-update-fn-emit-attivita-non-prende-trattenuti
-- Brief: brief-db-il-trattenuto-passa-lo-stesso.md (L3, §5.3, §5.4)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_pt_rif AS
WITH ba AS (
  SELECT b.id, b.utility_id, b.istanza_utility_id
    FROM anagrafiche.billing_account b
   WHERE b.utility_id IS NOT NULL AND b.istanza_utility_id IS NOT NULL
     AND b.soggetto_ruolo_id IS NOT NULL
   ORDER BY b.id LIMIT 1
)
SELECT
  script.fn_pgtap_emittente_sr_operatore()                 AS emittente_sr,
  (SELECT id FROM ba)                                      AS billing_account_id,
  (SELECT utility_id FROM ba)                              AS utility_id,
  (SELECT istanza_utility_id FROM ba)                      AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1) AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)          AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)          AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT sc.id FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE AND sc.emittibile IS TRUE ORDER BY sc.id LIMIT 1) AS stato_ok,
  -- ⚠️ La sorgente si sceglie per `codice_interno`, non «la prima attiva»: un
  --   guard confronta `sorgente_uid` con il `key_selector` del tipo E verifica
  --   che la riga ESISTA nella target_table. COMMESSA punta a vendite.commesse
  --   con key_selector `id`, quindi l'id della commessa stessa lo soddisfa
  --   sempre — anche su un database ricostruito da zero, dove non c'e' nessun
  --   ordine o DDT da citare.
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'COMMESSA' AND s.attivo IS TRUE) AS sorgente_id,
  date_trunc('month', CURRENT_DATE)::date                  AS mese;

SELECT ok(
  (SELECT r.emittente_sr IS NOT NULL AND r.billing_account_id IS NOT NULL
      AND r.articolo_id IS NOT NULL AND r.tipo_doc_fiscale_id IS NOT NULL
      AND r.stato_ok IS NOT NULL AND r.sorgente_id IS NOT NULL
     FROM tmp_pt_rif r),
  '0. riferimenti minimi risolti'
);

-- Due commesse: `bloccata` (trattenuta da un altro lotto) e `libera`.
CREATE TEMP TABLE tmp_pt (caso text, commessa_id bigint, ca_id bigint, gruppo_key text);
CREATE TEMP TABLE tmp_pt_lotti (caso text, lotto_id bigint, lock_batch_id uuid);

DO $fixture$
DECLARE
    v_rif   record;
    r       record;
    v_comm  vendite.commesse.id%TYPE;
    v_ca    vendite.commesse_attivita.id%TYPE;
    v_lot   vendite.fatturazione_lotti.id%TYPE;
    v_lock  vendite.fatturazione_lotti.lock_batch_id%TYPE;
BEGIN
    SELECT * INTO v_rif FROM tmp_pt_rif;

    FOR r IN SELECT * FROM (VALUES ('bloccata'), ('libera')) AS v(caso)
    LOOP
        INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                      emittente_soggetto_ruolo_id, stato_commessa_id)
        VALUES ('PGTAP-PT-' || upper(r.caso) || '-'
                            || substr(md5(clock_timestamp()::text), 1, 6),
                v_rif.billing_account_id, v_rif.utility_id, v_rif.emittente_sr,
                v_rif.stato_ok)
        RETURNING id INTO v_comm;

        -- ⚠️ Il pull PRETENDE una sorgente ROOT: senza, solleva
        --   E_VALORE_MANCANTE prima ancora di guardare le righe.
        -- ⚠️ E `sorgente_uid` non e' testo libero: un guard lo confronta col
        --   `key_selector` del tipo a catalogo E pretende che la riga esista
        --   nella target_table. Con la sorgente COMMESSA la target e'
        --   vendite.commesse: l'id appena creato la soddisfa per costruzione.
        INSERT INTO vendite.commesse_sorgenti
            (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
        VALUES (v_comm, v_rif.sorgente_id, v_comm::text, 'ROOT');

        INSERT INTO vendite.commesse_attivita (
            commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
            uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
            tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
            stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
        VALUES (v_comm,
                'PGTAP-PT-' || r.caso || '-' || substr(md5(clock_timestamp()::text), 1, 12),
                v_rif.articolo_id, v_rif.istanza_utility_id, v_rif.mese,
                v_rif.uom_id, 1, v_rif.mese, v_rif.mese,
                (v_rif.mese + INTERVAL '1 month - 1 day')::date,
                v_rif.tipo_doc_fiscale_id, v_rif.valuta_id, 10.000000, 'FIXED',
                'APPROVATA', 'NON_EMESSA', NULL, NULL)
        RETURNING id INTO v_ca;

        INSERT INTO tmp_pt VALUES (r.caso, v_comm, v_ca,
            vendite.fn_build_gruppo_fatturabile_key(NULL, NULL, v_comm));
    END LOOP;

    -- Due lotti IN GIOCO: «altrui» tiene la commessa bloccata, «mio» e' quello
    -- che eseguira' il pull nei test 3.
    FOR r IN SELECT * FROM (VALUES ('altrui'), ('mio')) AS v(caso)
    LOOP
        INSERT INTO vendite.fatturazione_lotti
            (codice, competenza_mese, tipo_doc_fiscale_id,
             emittente_soggetto_ruolo_id, stato_doc_fiscale_id)
        VALUES ('PGTAP-PT-LOTTO-' || upper(r.caso), v_rif.mese,
                v_rif.tipo_doc_fiscale_id, v_rif.emittente_sr,
                (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DRAFT'))
        RETURNING id, lock_batch_id INTO v_lot, v_lock;
        INSERT INTO tmp_pt_lotti VALUES (r.caso, v_lot, v_lock);
    END LOOP;

    -- L'esito che TRATTIENE: il lotto ALTRUI tiene la commessa bloccata.
    INSERT INTO vendite.fatturazione_lotti_esiti
        (lotto_id, gruppo_key, stato_esecuzione, errore_codice, errore_messaggio)
    SELECT (SELECT lotto_id FROM tmp_pt_lotti WHERE caso = 'altrui'),
           t.gruppo_key, 'ERRORE', 'E_PULL_COMMESSA', 'rotto per la prova'
      FROM tmp_pt t WHERE t.caso = 'bloccata';
END;
$fixture$;

-- ============================================================
-- 1) 🔴 Il pull NON prende una riga trattenuta da un ALTRO lotto
-- ============================================================
-- ⛔ E' il difetto del collaudo: la lane non l'aveva offerta, e il pull la
--   prendeva lo stesso perche' guardava solo `stato_emissione`.
SELECT is(
    (SELECT (vendite.fn_emit_attivita_fatturabili_da_commessa(
                 p_commessa_id   => t.commessa_id,
                 p_emit_batch_id => (SELECT lock_batch_id FROM tmp_pt_lotti WHERE caso = 'mio')
             )).total_candidate
       FROM tmp_pt t WHERE t.caso = 'bloccata'),
    0,
    '1. il pull NON prende una riga trattenuta da un ALTRO lotto in gioco'
);

-- ============================================================
-- 2) ⭐ E il verso opposto: la riga libera passa
-- ============================================================
-- ⛔ Senza questo, il test 1 passerebbe anche su una correzione che blocca
--   TUTTO — cioe' che spegne la fatturazione.
SELECT is(
    (SELECT (vendite.fn_emit_attivita_fatturabili_da_commessa(
                 p_commessa_id   => t.commessa_id,
                 p_emit_batch_id => (SELECT lock_batch_id FROM tmp_pt_lotti WHERE caso = 'mio')
             )).inserted_rows
       FROM tmp_pt t WHERE t.caso = 'libera'),
    1,
    '2. e una riga LIBERA della stessa competenza passa: il filtro non blocca troppo'
);

-- ============================================================
-- 3) ⭐⭐ RERUN: il giro riprende i PROPRI documenti
-- ============================================================
-- ⭐ Si sposta l'esito dal lotto «altrui» al lotto «mio»: e' esattamente lo
--   stato in cui un rilancio trova le cose — il giro precedente ha fallito la
--   commessa, il savepoint ha rimesso la riga a NON_EMESSA, l'esito e' rimasto.
-- ⛔ Senza l'auto-esclusione (`trattenuta_da_lotti <@ ARRAY[mio]`) il rilancio
--   salterebbe la riga che deve riprovare, e il lotto ripartirebbe a vuoto.
UPDATE vendite.fatturazione_lotti_esiti
   SET lotto_id = (SELECT lotto_id FROM tmp_pt_lotti WHERE caso = 'mio')
 WHERE gruppo_key = (SELECT gruppo_key FROM tmp_pt WHERE caso = 'bloccata');

SELECT is(
    (SELECT (vendite.fn_emit_attivita_fatturabili_da_commessa(
                 p_commessa_id   => t.commessa_id,
                 p_emit_batch_id => (SELECT lock_batch_id FROM tmp_pt_lotti WHERE caso = 'mio')
             )).inserted_rows
       FROM tmp_pt t WHERE t.caso = 'bloccata'),
    1,
    '3. RERUN: il giro riprende il documento che trattiene DA SE'''
);

-- ============================================================
-- 4) ⚠️ Senza identita' del giro, la trattenuta resta fuori
-- ============================================================
-- ⭐ Un chiamante fuori pipeline (backfill, riconciliazione) non ha un lotto:
--   li' non c'e' nessuna auto-esclusione da fare, e la risposta prudente e'
--   lasciare fuori tutto cio' che un giro sta tenendo.
-- ⚠️ Si rimette la riga a NON_EMESSA: il test 3 l'ha appena emessa.
UPDATE vendite.commesse_attivita
   SET stato_emissione = 'NON_EMESSA'
 WHERE id = (SELECT ca_id FROM tmp_pt WHERE caso = 'bloccata');

UPDATE vendite.fatturazione_lotti_esiti
   SET lotto_id = (SELECT lotto_id FROM tmp_pt_lotti WHERE caso = 'altrui')
 WHERE gruppo_key = (SELECT gruppo_key FROM tmp_pt WHERE caso = 'bloccata');

SELECT is(
    (SELECT (vendite.fn_emit_attivita_fatturabili_da_commessa(
                 p_commessa_id   => t.commessa_id,
                 p_emit_batch_id => NULL
             )).total_candidate
       FROM tmp_pt t WHERE t.caso = 'bloccata'),
    0,
    '4. senza identita'' del giro la riga trattenuta resta fuori (risposta prudente)'
);

SELECT * FROM finish();

ROLLBACK;
