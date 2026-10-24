-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce un'AZIENDA e un CLIENTE
--   (dbops.fn_pgtap_crea_emittente_operatore + fn_pgtap_crea_cliente_ba), e un
--   operatore dentro un perimetro non puo' crearli: l'INSERT su
--   anagrafiche.billing_account e' un `... RETURNING id`, e la RLS non lascia
--   RILEGGERE una riga il cui legame all'emittente non esiste ancora — lo
--   scrive il trigger z90, cioe' DOPO. E' la stessa ragione per cui girano da
--   owner tutti e sei i call-site di quel building block (rls/*-satelliti).
-- pgTAP test per Zero ERP
--
-- Test: P-5 — vendite.fn_emit_attivita_fatturabili_da_commessa non prende una
--       riga trattenuta da un ALTRO lotto in gioco, e riprende le PROPRIE.
--       Dal 2026-09-12 anche P-5-bis (la DISCOVERY fa lo stesso) e P-5-ter
--       (il PERCORSO INTERO discovery → emit), piu' la premessa dell'helper e
--       il decimo numero del riepilogo (D2).
--
-- Elenco test (plan 13) — numerati come li stampa il TAP:
--  0) riferimenti minimi risolti
--  1) 🔴 il pull NON emette una riga trattenuta da un ALTRO lotto in gioco
--  2) ⭐ e il verso opposto: la riga LIBERA della stessa commessa passa
--  3) ⭐⭐ RERUN: la riga trattenuta dal PROPRIO lotto viene ripresa
--  4) ⚠️ senza identita' del giro (p_emit_batch_id NULL) la trattenuta resta
--        fuori — la risposta prudente
--  5) P-5-bis 🔴 la DISCOVERY non visita la commessa trattenuta da un ALTRO lotto
--  6) P-5-bis ⚠️ ne' la visita senza identita' del giro
--  7) P-5-bis ⭐⭐ RERUN: la DISCOVERY visita la commessa trattenuta dal PROPRIO
--        lotto — e' il test che il 12-09 mancava, ed e' ROSSO sul -61
--  8) P-5-ter ⭐⭐ PERCORSO INTERO: la commessa data dalla discovery, passata
--        all'emit con la stessa identita', ha la riga presa (total_candidate 1)
--  9) P-5-ter ... e la riga esce EMESSA
-- 10) la PREMESSA dell'helper: una riga NON approvata trattenuta da un lotto e'
--        NON_APPROVATA, non TRATTENUTA (ordine del CASE della vista)
-- 11) D2: il riepilogo del lotto «mio» conta 1 esito ERRORE, «altrui» 0
-- 12) D2: un esito portato a ESCLUSO non conta piu'
--
-- ────────────────────────────────────────────────────────────────
-- 🔴 PERCHE' I TEST 5-9 ESISTONO — il collaudo del 2026-09-12 (prova 5).
--   Il test 3 era verde e il rilancio NON riprendeva niente: il pull ha DUE
--   cancelli in serie, fn_list_commesse_emittibili (quali COMMESSE visitare)
--   e l'emit (quali RIGHE emettere), e il test 3 chiamava DIRETTAMENTE l'emit.
--   La discovery aveva la whitelist secca, senza identita': al rerun scartava
--   la commessa coi PROPRI documenti trattenuti, e l'emit — che li avrebbe
--   ripresi — non veniva mai chiamato. «La whitelist si verifica dal percorso
--   che la attraversa, non dal nome»: il test 8 e' quel percorso.
--   ChangeSet: 20260912-12 (helper classe per giro), -13 (lotto da batch),
--   -14 (emit dall'helper), -15 (discovery con p_emit_batch_id), -16 (D2).
--   Brief: brief-db-rilancio-step-non-rivede-le-proprie-commesse.md
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in bozza e si
--   portano avanti con dbops.fn_pgtap_porta_a_stato (prima le commesse nascevano gia'
--   nello stato emittibile, PRONTA_FATTURAZIONE).
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

SET CONSTRAINTS ALL IMMEDIATE;

-- ⭐ L'AZIENDA, L'OPERATORE E IL CLIENTE SI COSTRUISCONO (rev 2026-09-09).
--   Prima l'emittente si CERCAVA (`fn_pgtap_emittente_sr_operatore`) e il
--   billing account pure (`ORDER BY b.id LIMIT 1`). Su un database ricostruito
--   dai changelog — cioe' in CI — `anagrafiche` e' vuoto: sono seed di
--   `dati_macchina`. ⇒ Il file sollevava «Nessun emittente fiscale attivo» e
--   non eseguiva NEMMENO UNA asserzione, mentre la sua intestazione dichiara
--   «I CASI SI COSTRUISCONO»: le due commesse si', il mondo sotto no.
-- ⛔ Il mondo si costruisce PRIMA di aprire il contesto: dopo, il legame
--   BA→emittente lo scriverebbe anche `trg_billing_account_z90_link_ef_ins` e
--   i due si scontrerebbero su `uq_emittenti_fiscali_ba`.
CREATE TEMP TABLE tmp_pt_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE tmp_pt_cliente AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'pull trattenuti', NULL, (SELECT soggetto_ruolo_id FROM tmp_pt_mondo));

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM tmp_pt_mondo));
END $ctx$;

SELECT plan(13);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_pt_rif AS
SELECT
  (SELECT m.soggetto_ruolo_id FROM tmp_pt_mondo m)         AS emittente_sr,
  (SELECT c.billing_account_id FROM tmp_pt_cliente c)      AS billing_account_id,
  (SELECT c.utility_id FROM tmp_pt_cliente c)              AS utility_id,
  (SELECT c.istanza_utility_id FROM tmp_pt_cliente c)      AS istanza_utility_id,
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
  date_trunc('month', script.fn_data_operativa())::date                  AS mese;

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
        -- rev 2026-10-24: la commessa nasce BOZZA (trigger della nascita) e passa
        --   allo stato emittibile DOPO la sua riga APPROVATA, che il passaggio a
        --   PRONTA_FATTURAZIONE pretende (fn_check_commessa_pronta_fatturazione).
        INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                      emittente_soggetto_ruolo_id)
        VALUES ('PGTAP-PT-' || upper(r.caso) || '-'
                            || substr(md5(clock_timestamp()::text), 1, 6),
                v_rif.billing_account_id, v_rif.utility_id, v_rif.emittente_sr)
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
                'APPROVATA', 'NON_EMESSA', -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
                (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'), v_comm::text)
        RETURNING id INTO v_ca;

        PERFORM dbops.fn_pgtap_porta_a_stato('vendite.commesse', v_comm,
            (SELECT sc.codice_interno FROM vendite.stati_commessa sc WHERE sc.id = v_rif.stato_ok));

        INSERT INTO tmp_pt VALUES (r.caso, v_comm, v_ca,
            vendite.fn_build_gruppo_fatturabile_key(
                (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'), v_comm::text, v_comm));
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

-- ============================================================
-- P-5-bis — la DISCOVERY (rev 2026-09-12)
-- ============================================================
-- Stato qui: `bloccata` trattenuta dal lotto ALTRUI, riga NON_EMESSA.
-- ⭐ La chiamata e' quella del pull: competenza, emittente, i gruppi richiesti
--   e l'identita' del giro — gli stessi argomenti che il backend binda.

-- 5) 🔴 Trattenuta da un ALTRO lotto: la commessa NON si visita (niente pull
--    a vuoto registrato come lavorato — e' l'effetto che il -61 voleva).
SELECT is(
    (SELECT count(*)::int
       FROM tmp_pt_rif r,
            LATERAL vendite.fn_list_commesse_emittibili(
                p_competenza_mese             => r.mese,
                p_emittente_soggetto_ruolo_id => r.emittente_sr,
                p_gruppi                      => ARRAY[(SELECT gruppo_key FROM tmp_pt WHERE caso = 'bloccata')],
                p_emit_batch_id               => (SELECT lock_batch_id FROM tmp_pt_lotti WHERE caso = 'mio')) d),
    0,
    '5. P-5-bis: la discovery NON visita la commessa trattenuta da un ALTRO lotto in gioco'
);

-- 6) ⚠️ Senza identita' del giro: nemmeno (la risposta prudente, come l'emit).
SELECT is(
    (SELECT count(*)::int
       FROM tmp_pt_rif r,
            LATERAL vendite.fn_list_commesse_emittibili(
                p_competenza_mese             => r.mese,
                p_emittente_soggetto_ruolo_id => r.emittente_sr,
                p_gruppi                      => ARRAY[(SELECT gruppo_key FROM tmp_pt WHERE caso = 'bloccata')],
                p_emit_batch_id               => NULL) d),
    0,
    '6. P-5-bis: senza identita'' del giro la discovery non visita la commessa trattenuta'
);

-- 7) ⭐⭐ RERUN: l'esito passa al lotto MIO — e' lo stato in cui un rilancio
--    trova le cose. La commessa DEVE essere visitata, con la sua riga contata.
-- ⛔ Sul changeSet -61 (whitelist secca, nessuna identita') questo test e'
--    ROSSO: e' il difetto di LTF-0010972, «totale 0» su un lotto COMPLETATO.
UPDATE vendite.fatturazione_lotti_esiti
   SET lotto_id = (SELECT lotto_id FROM tmp_pt_lotti WHERE caso = 'mio')
 WHERE gruppo_key = (SELECT gruppo_key FROM tmp_pt WHERE caso = 'bloccata');

SELECT is(
    (SELECT coalesce(sum(d.total_non_emesse), 0)::int
       FROM tmp_pt_rif r,
            LATERAL vendite.fn_list_commesse_emittibili(
                p_competenza_mese             => r.mese,
                p_emittente_soggetto_ruolo_id => r.emittente_sr,
                p_gruppi                      => ARRAY[(SELECT gruppo_key FROM tmp_pt WHERE caso = 'bloccata')],
                p_emit_batch_id               => (SELECT lock_batch_id FROM tmp_pt_lotti WHERE caso = 'mio')) d
      WHERE d.commessa_id = (SELECT commessa_id FROM tmp_pt WHERE caso = 'bloccata')),
    1,
    '7. P-5-bis RERUN: la discovery VISITA la commessa trattenuta dal PROPRIO lotto, con la riga contata'
);

-- ============================================================
-- P-5-ter — il PERCORSO INTERO: discovery → emit, stessa identita'
-- ============================================================
-- ⭐ E' il test che mancava: i due cancelli provati INSIEME, come li
--   attraversa il pull. La commessa la da' la discovery, l'emit la riceve.
-- ⚠️ `total_candidate` e non `inserted_rows`: il test 3 ha gia' creato la riga
--   di attivita_fatturabili (il test 4 ha rimesso la commessa a NON_EMESSA, non
--   ha tolto quella riga), quindi qui l'emit passa dal ramo UPDATE.
SELECT is(
    (SELECT (vendite.fn_emit_attivita_fatturabili_da_commessa(
                 p_commessa_id   => d.commessa_id,
                 p_emit_batch_id => (SELECT lock_batch_id FROM tmp_pt_lotti WHERE caso = 'mio')
             )).total_candidate
       FROM tmp_pt_rif r,
            LATERAL vendite.fn_list_commesse_emittibili(
                p_competenza_mese             => r.mese,
                p_emittente_soggetto_ruolo_id => r.emittente_sr,
                p_gruppi                      => ARRAY[(SELECT gruppo_key FROM tmp_pt WHERE caso = 'bloccata')],
                p_emit_batch_id               => (SELECT lock_batch_id FROM tmp_pt_lotti WHERE caso = 'mio')) d
      WHERE d.commessa_id = (SELECT commessa_id FROM tmp_pt WHERE caso = 'bloccata')),
    1,
    '8. P-5-ter PERCORSO INTERO: la commessa data dalla discovery, passata all''emit con la stessa identita'', ha la riga presa'
);

-- 9) ... e la riga e' uscita EMESSA: il rilancio ha prodotto qualcosa.
SELECT is(
    (SELECT ca.stato_emissione::text FROM vendite.commesse_attivita ca
      WHERE ca.id = (SELECT ca_id FROM tmp_pt WHERE caso = 'bloccata')),
    'EMESSA',
    '9. P-5-ter: e la riga esce EMESSA'
);

-- ============================================================
-- 10) La PREMESSA dell'helper: TRATTENUTA implica approvata
-- ============================================================
-- ⭐ fn_classe_emittibilita_per_giro promuove «TRATTENUTA solo da me» a PRONTA.
--   Regge perche' nel CASE della vista RIFIUTATA e NON_APPROVATA vengono PRIMA
--   di TRATTENUTA: una riga non approvata non e' MAI trattenuta, anche se un
--   lotto tiene il suo documento. Se la vista cambiasse ordine, l'helper
--   promuoverebbe una riga non approvata — e questo test lo direbbe.
-- ⛔ Il caso si COSTRUISCE: una seconda riga della commessa bloccata, in
--   BOZZA, mentre il lotto «mio» ne tiene il documento (stesso gruppo_key).
INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
SELECT t.commessa_id,
       'PGTAP-PT-bozza-' || substr(md5(clock_timestamp()::text), 1, 12),
       r.articolo_id, r.istanza_utility_id, r.mese,
       r.uom_id, 1, r.mese, r.mese, (r.mese + INTERVAL '1 month - 1 day')::date,
       r.tipo_doc_fiscale_id, r.valuta_id, 10.000000, 'FIXED',
       'BOZZA', 'NON_EMESSA', (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
         (t.commessa_id)::text
  FROM tmp_pt_rif r, tmp_pt t WHERE t.caso = 'bloccata';

SELECT is(
    (SELECT e.classe_emittibilita::text || ' / tenuta=' || (e.trattenuta_da_lotti IS NOT NULL)::text
       FROM vendite.vw_commesse_attivita_emittibilita e
       JOIN vendite.commesse_attivita ca ON ca.id = e.commessa_attivita_id
      WHERE ca.segment_key LIKE 'PGTAP-PT-bozza-%'),
    'NON_APPROVATA / tenuta=true',
    '10. una riga NON approvata tenuta da un lotto e'' NON_APPROVATA, non TRATTENUTA (la premessa dell''helper)'
);

-- ============================================================
-- D2 — il decimo numero del riepilogo (rev 2026-09-12)
-- ============================================================
-- Stato qui: l'esito ERRORE della commessa bloccata e' sul lotto MIO.
SELECT is(
    (SELECT (SELECT s.esiti_stato_esecuzione_errore_count
               FROM vendite.fn_get_lotto_segnalazioni_summary((SELECT lotto_id FROM tmp_pt_lotti WHERE caso = 'mio')) s)::text
         || '/' ||
            (SELECT s.esiti_stato_esecuzione_errore_count
               FROM vendite.fn_get_lotto_segnalazioni_summary((SELECT lotto_id FROM tmp_pt_lotti WHERE caso = 'altrui')) s)::text),
    '1/0',
    '11. D2: il riepilogo conta l''esito ERRORE sul lotto che lo porta (mio=1, altrui=0)'
);

-- 12) ESCLUSO non conta: e' la dichiarazione dell'operatore che il documento
--     non fa piu' parte del giro — la via d'uscita, non un errore.
UPDATE vendite.fatturazione_lotti_esiti
   SET stato_esecuzione = 'ESCLUSO',
       uscita_motivo    = 'pgTAP: il documento esce dal giro',
       uscita_quando    = now(),
       uscita_da        = 'pgtap'
 WHERE gruppo_key = (SELECT gruppo_key FROM tmp_pt WHERE caso = 'bloccata')
   AND lotto_id   = (SELECT lotto_id FROM tmp_pt_lotti WHERE caso = 'mio');

SELECT is(
    (SELECT s.esiti_stato_esecuzione_errore_count
       FROM vendite.fn_get_lotto_segnalazioni_summary((SELECT lotto_id FROM tmp_pt_lotti WHERE caso = 'mio')) s),
    0::bigint,
    '12. D2: un esito portato a ESCLUSO non conta piu'' come ERRORE'
);

SELECT * FROM finish();

ROLLBACK;
