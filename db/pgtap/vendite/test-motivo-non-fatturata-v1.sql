-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la DIMENSIONE `motivo_non_fatturata` e la CHIAVE del verbo
--       (brief-db-residui-competenza-dimensione-e-chiave, D-1 · D-2 · D-3)
-- ------------------------------------------------------------
-- A cosa serve, in una frase
--   `vendite.vw_dash_competenza_attivita.motivo_non_fatturata` e
--   `script.fn_check_attivita_riportabile_da_emettere` rispondono alla STESSA
--   domanda — «questa riga la si puo' riportare da emettere?» — da due
--   superfici diverse. Questo file le tiene attaccate.
--
-- ⛔ PERCHE' UN PRESIDIO, E NON «basta scriverle bene»
--   Se le due divergono, la divergenza e' SILENZIOSA: nessun errore, nessun
--   contatore fuori posto. La lista proporrebbe il verbo su una riga che la
--   mutazione rifiuta (l'operatore clicca e il salvataggio dice di no), oppure
--   lo nasconderebbe su una che avrebbe accettato — e quel lavoro resterebbe
--   invisibile, che e' il male da cui nasce l'intero cantiere.
--
-- ⚠️ FIXTURE COSTRUITE, NON SCELTE
--   Un test che itera su cio' che c'e' passa a vuoto su un database
--   ricostruito da zero, cioe' in CI. Qui commessa, sei righe di commessa,
--   lotto, fattura, riga e cinque attivita' fatturabili sono INSERITE dal file.
--   Solo i riferimenti anagrafici/di catalogo si scelgono dall'esistente, come
--   in tutta questa famiglia.
--
-- ⛔ IL RAMO CHE NESSUN DATO PRODUCE OGGI (test 7 e 9)
--   `stato_esecuzione` e' NULLABLE e il CHECK ammette anche `ERRORE`: il
--   discriminante DEVE essere `IS DISTINCT FROM 'COMPLETED'`, come nella
--   fn_check. Con un `<>` un lucchetto a NULL darebbe NULL, il CASE cadrebbe
--   sul ramo dopo e la vista direbbe RESIDUO dove la funzione rifiuta. Nessuna
--   riga viva produce oggi quel caso: si COSTRUISCE, perche' zero occorrenze
--   non significa che il caso non esiste.
--   Stessa ragione per `SENZA_ATTIVITA_FATTURABILE` (test 8): il JOIN e' LEFT
--   e il modello ammette una riga di commessa a EMESSA senza attivita'
--   fatturabile.
--
-- ⚠️ IL CONFRONTO NON E' SUL NOME MA SULL'ESITO
--   La vista dice un valore di vocabolario, la funzione un codice di errore:
--   la tabella di corrispondenza sta scritta qui sotto UNA volta sola, e ogni
--   caso la attraversa. Confrontare due stringhe uguali non avrebbe provato
--   niente — sono due linguaggi diversi apposta.
--
-- 🔴 REV 2026-09-12 — QUESTO PRESIDIO HA FATTO IL SUO MESTIERE
--   Il 20260912-35 ha cambiato il motivo 3 del check: un'attivita' LIBERA con
--   la riga di commessa EMESSA non e' «gia' disponibile» (nessun giro la
--   riprende) — e' in transito se il suo marchio e' di un lotto IN GIOCO
--   (motivo 5, E_ATTIVITA_IN_LAVORAZIONE), riportabile se il lotto e' morto o
--   il marchio non c'e'. La vista diceva ancora IN_ATTESA_LOTTO: i test 5 e 11
--   sono diventati rossi la sera stessa, e il 20260912-36 ha allineato la
--   vista. IN_ATTESA_LOTTO e' RITIRATO: dentro EMESSA_NON_FATTURATA la riga
--   e' EMESSA per costruzione, quindi nessun caso lo produce piu'. La mappa
--   qui sotto non lo nomina, e il test 11-bis prova che la vista non lo
--   emette — senza quel test il JOIN sulla mappa lascerebbe uscire in
--   SILENZIO qualunque valore fuori vocabolario (contare i cattivi e' muto se
--   il rotto esce dal join).
--
-- Indice test (1..20, con un 5-bis, un 5-ter, un 11-bis e un 13-bis)
--  1) Riferimenti minimi presenti
--  2) La vista espone le OTTO colonne nuove
--  3) Fixture: otto righe di commessa EMESSA, sette attivita, due lotti (uno vivo, uno morto)
--  4) ⭐ LA CHIAVE: attivita_fatturabile_id e' l id vero, riga per riga
--  5) ⭐ RESIDUO          <-> nessun motivo: libera, riga EMESSA, SENZA marchio (divergenza)
--  5-bis) ⭐ GIRO_IN_CORSO <-> E_ATTIVITA_IN_LAVORAZIONE: libera col marchio di un lotto IN GIOCO
--  5-ter) ⭐ RESIDUO       <-> nessun motivo: libera col marchio di un lotto MORTO
--  6) GIRO_IN_CORSO    <-> E_ATTIVITA_IN_LAVORAZIONE   (lucchettata, stato PENDING)
--  7) ⛔ GIRO_IN_CORSO <-> E_ATTIVITA_IN_LAVORAZIONE   (lucchettata, stato NULL)
--  8) ⛔ SENZA_ATTIVITA_FATTURABILE: nominata, e senza chiave
--  9) RESIDUO          <-> nessun motivo: lucchettata e COMPLETED
-- 10) ⛔ NULL fuori da EMESSA_NON_FATTURATA, e li la fn rifiuta comunque
-- 11) ⭐ IL GIRO GENERALE: nessuna riga visibile contraddice la fn_check
-- 11-bis) ⛔ Nessuna riga porta un motivo fuori vocabolario (IN_ATTESA_LOTTO compreso)
-- 12) ⭐ Il lotto di PROVENIENZA c e, e non e lotto_id — anche per il divergente, dal marchio
-- 13) ⛔ I join di provenienza e decode non moltiplicano le righe
-- 13-bis) ⭐ L articolo esce decodificato, non come UUID
-- 14) La mensile ha una riga per (mese, stadio, stato, movimento, motivo)
-- 15) security_invoker=on su ENTRAMBE le viste
-- 16) Fail-closed: senza GUC operatore la dimensione non esce
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Scattano al COMMIT, e qui il COMMIT non arriva mai (si chiude in ROLLBACK):
--   sarebbero saltati in silenzio e il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (ruolo OPERATORE
-- + RLS attiva), non come owner. ⛔ Qui non e' un dettaglio: le due viste sono
-- `security_invoker` e fail-closed, e il perimetro del verbo E' la RLS su
-- vendite.commesse_attivita.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(20);

-- ============================================================
-- 0) Riferimenti e costanti
-- ============================================================
CREATE TEMP TABLE tmp_cost_mnf AS
SELECT 'pgtap_motivo_non_fatturata'::text        AS test_scope,
       uuidv7()                                  AS lock_batch_id,
       -- ⭐ Il marchio di un SECONDO lotto, morto: serve al caso «libera col
       --   marchio di un lotto che non e' piu' in gioco» (5-ter).
       uuidv7()                                  AS lock_batch_morto,
       script.fn_pgtap_emittente_sr_operatore()  AS emittente_sr_id,
       -- ⚠️ Un mese di competenza LONTANO da quelli veri: le asserzioni di
       --   grana (test 14) e di perimetro restano leggibili anche su un
       --   database con dati, e il test 16 non conta righe altrui.
       DATE '2081-05-01'                         AS competenza_mese;

-- rev 2026-10-27 (lotto 4 di D7): la commessa si COSTRUISCE
--   (dbops.fn_pgtap_crea_commessa: cliente, BA dell'azienda di chi agisce e
--   commessa aperta dalla madre, nello stato iniziale), e i riferimenti del
--   cliente si leggono da li'. Prima il BA si pescava con LIMIT 1 e la commessa
--   si INSERIVA a mano: da zero il BA non c'era. Righe di commessa, lotti,
--   fattura e attivita' restano scritte a mano: sono il caso del test.
CREATE TEMP TABLE tmp_cmm_mnf AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('motivo non fatturata');

CREATE TEMP TABLE tmp_refs_mnf AS
SELECT
  (SELECT id FROM config.stati_doc_fiscale
    WHERE upper(btrim(codice_interno)) = 'DRAFT' ORDER BY id LIMIT 1) AS stato_draft_id,
  -- Lo stato che spegne un lotto: congela_fiscale, quindi vw_lotti_fase.in_gioco = false.
  (SELECT id FROM config.stati_doc_fiscale
    WHERE upper(btrim(codice_interno)) = 'ANNULLATA' ORDER BY id LIMIT 1) AS stato_annullata_id,
  (SELECT billing_account_id FROM tmp_cmm_mnf) AS billing_account_id,
  (SELECT utility_id FROM tmp_cmm_mnf)         AS utility_id,
  (SELECT istanza_utility_id FROM tmp_cmm_mnf) AS istanza_utility_id,
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
  script.fn_pgtap_registro_fattura((SELECT emittente_sr_id FROM tmp_cost_mnf))            AS registro_id;

SELECT ok(
  (SELECT r.stato_draft_id IS NOT NULL
      AND r.stato_annullata_id IS NOT NULL
      AND r.billing_account_id IS NOT NULL
      AND r.articolo_id IS NOT NULL
      AND r.uom_id IS NOT NULL
      AND r.tipo_doc_fiscale_id IS NOT NULL
      AND r.valuta_id IS NOT NULL
      AND r.stato_commessa_id IS NOT NULL
      AND r.registro_id IS NOT NULL
      AND (SELECT emittente_sr_id FROM tmp_cost_mnf) IS NOT NULL
     FROM tmp_refs_mnf r),
  '1) riferimenti minimi presenti (anagrafiche, catalogo, registro, emittente)'
);

-- ============================================================
-- 2) Le otto colonne nuove esistono
-- ============================================================
-- ⚠️ La presenza non basta a provare il comportamento, ma la sua ASSENZA
--   renderebbe illeggibili tutti i rossi che seguono.
SELECT is(
  (SELECT count(*)::integer
     FROM pg_attribute a
    WHERE a.attrelid = 'vendite.vw_dash_competenza_attivita'::regclass
      AND a.attnum > 0 AND NOT a.attisdropped
      AND a.attname IN ('attivita_fatturabile_id', 'lock_in_fatturazione',
                        'stato_esecuzione', 'motivo_non_fatturata',
                        'lotto_provenienza_id', 'lotto_provenienza_codice',
                        'articolo_codice', 'articolo_descrizione')),
  8,
  '2) la vista di dettaglio espone le otto colonne nuove'
);

-- ============================================================
-- LA TABELLA DI CORRISPONDENZA, scritta UNA volta sola.
-- ⭐ E' il contratto fra le due superfici: la vista dice un valore di
--   vocabolario, la funzione un codice di errore. `codice_atteso` NULL
--   significa «la funzione non ha motivi», cioe' il verbo si puo' fare.
-- ============================================================
CREATE TEMP TABLE tmp_mappa_mnf (motivo text PRIMARY KEY, codice_atteso text);
INSERT INTO tmp_mappa_mnf (motivo, codice_atteso) VALUES
  ('GIRO_IN_CORSO',   'E_ATTIVITA_IN_LAVORAZIONE'),
  ('RESIDUO',         NULL);
-- ⛔ SENZA_ATTIVITA_FATTURABILE non entra nella mappa, e non e' una svista:
--   li' non c'e' nessun `attivita_fatturabili.id` da passare alla funzione.
--   E' proprio cio' che il test 8 asserisce.
-- ⛔ IN_ATTESA_LOTTO non c'e' piu' (rev 2026-09-12): la vista non lo produce, e
--   il test 11-bis lo pretende. Rimetterlo qui senza un caso che lo produca
--   sarebbe un ramo morto nella mappa.

-- ============================================================
-- Fixture: una commessa, SEI righe di commessa gia' EMESSA
-- ============================================================
CREATE TEMP TABLE tmp_commessa_mnf AS
SELECT commessa_id AS id FROM tmp_cmm_mnf;

CREATE TEMP TABLE tmp_ca_mnf (slot text PRIMARY KEY, attivita_id bigint);

-- ⚠️ Tutte EMESSA: e' lo stato che la pipeline lascia dopo l'emissione, ed e'
--   la condizione che porta la riga nello stadio EMESSA_NON_FATTURATA quando
--   la riga di fattura manca. Senza, il motivo uscirebbe NULL per un'altra
--   ragione e il test verificherebbe un caso diverso da quello che dichiara.
DO $fx$
DECLARE
  s text;
BEGIN
  FOREACH s IN ARRAY ARRAY['ORFANA', 'IN_FATTURA', 'LIBERA', 'LIBERA_VIVA',
                           'LIBERA_MORTA', 'VIVA', 'VIVA_NULL', 'SENZA_AF'] LOOP
    -- ⚠️ Un INSERT che restituisce righe sta in una CTE, non in un FROM.
    WITH ins AS (
      INSERT INTO vendite.commesse_attivita (
        commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
        uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
        tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
        stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_id)
      SELECT (SELECT id FROM tmp_commessa_mnf),
             ((SELECT x.segment_key FROM dbops.fn_pgtap_consumo_della_commessa((SELECT id FROM tmp_commessa_mnf)) x) || ':' || 'PGTAP-MNF-' || s || '-' || substr(md5(clock_timestamp()::text), 1, 12)),
             r.articolo_id, r.istanza_utility_id,
             (SELECT competenza_mese FROM tmp_cost_mnf),
             r.uom_id, 1,
             (SELECT competenza_mese FROM tmp_cost_mnf),
             (SELECT competenza_mese FROM tmp_cost_mnf),
             ((SELECT competenza_mese FROM tmp_cost_mnf) + INTERVAL '1 month - 1 day')::date,
             r.tipo_doc_fiscale_id, r.valuta_id, 10.000000, 'FIXED',
             'APPROVATA', 'EMESSA', (SELECT x.sorgente_tipo_id FROM dbops.fn_pgtap_consumo_della_commessa((SELECT id FROM tmp_commessa_mnf)) x),
         (SELECT x.consumo_id FROM dbops.fn_pgtap_consumo_della_commessa((SELECT id FROM tmp_commessa_mnf)) x)
        FROM tmp_refs_mnf r
      RETURNING id)
    INSERT INTO tmp_ca_mnf(slot, attivita_id) SELECT s, ins.id FROM ins;
  END LOOP;
END
$fx$;

-- Il LOTTO di provenienza. ⭐ Si aggancia per `lock_batch_id`, che su
-- vendite.fatturazione_lotti ha un UNIQUE: e' l'unico legame fra un'attivita'
-- lucchettata e il giro che l'ha lucchettata.
-- ⚠️ L'emittente e' quello dell'operatore: fatturazione_lotti ha la RLS, e un
--   lotto di un altro emittente sarebbe invisibile — il test 12 misurerebbe
--   allora la policy invece del join.
CREATE TEMP TABLE tmp_lotto_mnf AS
WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
    codice, competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id,
    lock_batch_id, meta)
  SELECT 'PGTAP-MNF-LT-' || substr(md5(clock_timestamp()::text), 1, 8),
         (SELECT competenza_mese FROM tmp_cost_mnf),
         r.tipo_doc_fiscale_id,
         (SELECT emittente_sr_id FROM tmp_cost_mnf),
         (SELECT lock_batch_id FROM tmp_cost_mnf),
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_mnf))
    FROM tmp_refs_mnf r
  RETURNING id, codice)
SELECT id AS lotto_id, codice AS lotto_codice FROM ins;

-- ⭐ Il lotto MORTO (rev 2026-09-12): nasce direttamente ANNULLATA — l'INSERT
--   non passa dalla matrice delle transizioni, per progetto (§7c.6) — e il suo
--   lock_batch_id e' il marchio che la LIBERA_MORTA porta in emit_batch_id.
--   Su vw_lotti_fase.in_gioco vale false: e' cio' che separa 5-bis da 5-ter.
CREATE TEMP TABLE tmp_lotto_morto_mnf AS
WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
    codice, competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id,
    lock_batch_id, stato_doc_fiscale_id, meta)
  SELECT 'PGTAP-MNF-LM-' || substr(md5(clock_timestamp()::text), 1, 8),
         (SELECT competenza_mese FROM tmp_cost_mnf),
         r.tipo_doc_fiscale_id,
         (SELECT emittente_sr_id FROM tmp_cost_mnf),
         (SELECT lock_batch_morto FROM tmp_cost_mnf),
         r.stato_annullata_id,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_mnf))
    FROM tmp_refs_mnf r
  RETURNING id, codice)
SELECT id AS lotto_id, codice AS lotto_codice FROM ins;

-- Una fattura DRAFT con una riga, per il caso IN_FATTURA
CREATE TEMP TABLE tmp_fattura_mnf AS
WITH ins AS (
  INSERT INTO vendite.fatture (registro_id, emittente_soggetto_ruolo_id,
                               billing_account_id, utility_id, tipo_doc_fiscale_id,
                               valuta_id, stato_doc_fiscale_id, data)
  SELECT r.registro_id, (SELECT emittente_sr_id FROM tmp_cost_mnf),
         r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
         r.valuta_id, r.stato_draft_id,
         (SELECT competenza_mese FROM tmp_cost_mnf)
    FROM tmp_refs_mnf r
  RETURNING id)
SELECT id AS fattura_id FROM ins;

CREATE TEMP TABLE tmp_riga_mnf AS
WITH ins AS (
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione,
                                     qta, prezzo_unitario, imponibile_riga, competenza_dal, competenza_al)
  SELECT f.fattura_id, 1, 'Riga PGTAP MNF', 1, 10, 10, script.fn_data_operativa(), script.fn_data_operativa()
    FROM tmp_fattura_mnf f
  RETURNING id)
SELECT id AS riga_id FROM ins;

-- ============================================================
-- Le SETTE attivita' fatturabili — e l'ottava riga che non ne ha nessuna
-- ============================================================
--   ORFANA       -> lucchettata, COMPLETED, senza fattura         => RESIDUO
--   IN_FATTURA   -> agganciata a una riga viva                    => stadio FATTURATA
--   LIBERA       -> nessun lucchetto, nessun marchio (divergenza) => RESIDUO
--   LIBERA_VIVA  -> nessun lucchetto, marchio del lotto IN GIOCO  => GIRO_IN_CORSO
--   LIBERA_MORTA -> nessun lucchetto, marchio del lotto MORTO     => RESIDUO
--   VIVA         -> lucchettata, PENDING                          => GIRO_IN_CORSO
--   VIVA_NULL    -> lucchettata, stato NULL                       => GIRO_IN_CORSO
--   SENZA_AF     -> nessuna attivita' fatturabile      => SENZA_ATTIVITA_FATTURABILE
-- ⭐ Le tre LIBERA hanno tutte la riga di commessa EMESSA (e' la fixture, e
--   dentro EMESSA_NON_FATTURATA e' cosi' per costruzione): cio' che le
--   distingue e' SOLO il marchio, cioe' i due livelli del 20260912-35.
CREATE TEMP TABLE tmp_af_mnf (slot text PRIMARY KEY, attivita_id bigint);

DO $fx$
DECLARE
  s       text;
  v_riga  bigint;
  v_lock  boolean;
  v_batch uuid;
  v_emit  uuid;
  v_stato text;
BEGIN
  FOREACH s IN ARRAY ARRAY['ORFANA', 'IN_FATTURA', 'LIBERA', 'LIBERA_VIVA',
                           'LIBERA_MORTA', 'VIVA', 'VIVA_NULL'] LOOP
    v_riga  := CASE WHEN s = 'IN_FATTURA' THEN (SELECT riga_id FROM tmp_riga_mnf) END;
    v_lock  := (s NOT LIKE 'LIBERA%');
    v_batch := CASE WHEN s NOT LIKE 'LIBERA%' THEN (SELECT lock_batch_id FROM tmp_cost_mnf) END;
    -- ⭐ Il MARCHIO del giro (emit_batch_id): per le lucchettate e' lo stesso
    --   del lucchetto (il pull marchia, la select lucchetta, stesso giro); per
    --   le libere e' la variabile del test.
    v_emit  := CASE WHEN s = 'LIBERA'       THEN NULL
                    WHEN s = 'LIBERA_VIVA'  THEN (SELECT lock_batch_id    FROM tmp_cost_mnf)
                    WHEN s = 'LIBERA_MORTA' THEN (SELECT lock_batch_morto FROM tmp_cost_mnf)
                    ELSE (SELECT lock_batch_id FROM tmp_cost_mnf) END;
    -- ⛔ VIVA_NULL resta a NULL DI PROPOSITO: e' il caso che distingue
    --   `IS DISTINCT FROM` da `<>`, e nessun dato vivo lo produce oggi.
    v_stato := CASE WHEN s = 'VIVA'      THEN 'PENDING'
                    WHEN s = 'VIVA_NULL' THEN NULL
                    WHEN s LIKE 'LIBERA%' THEN NULL
                    ELSE 'COMPLETED' END;

    WITH ins AS (
      INSERT INTO vendite.attivita_fatturabili (
            articolo_id, istanza_utility_id, billing_account_id, data_attivita,
            competenza_mese, competenza_dal, competenza_al, quantita, approvato,
            sospesa, tipo_doc_fiscale_id, valuta_id, commessa_id,
            commessa_attivita_id, uom_id, prezzo_unitario, lock_in_fatturazione,
            lock_batch_id, emit_batch_id, fattura_riga_id, stato_esecuzione, meta)
        SELECT r.articolo_id, r.istanza_utility_id, r.billing_account_id,
               (SELECT competenza_mese FROM tmp_cost_mnf),
               (SELECT competenza_mese FROM tmp_cost_mnf),
               (SELECT competenza_mese FROM tmp_cost_mnf),
               ((SELECT competenza_mese FROM tmp_cost_mnf) + INTERVAL '1 month - 1 day')::date,
               1, true,
               -- ⚠️ `fatturato` NON si scrive: dal 20260826-33 e' GENERATA su
               --    `fattura_riga_id`. Lo stato si ottiene dal PUNTATORE.
               false,
               r.tipo_doc_fiscale_id, r.valuta_id,
               (SELECT id FROM tmp_commessa_mnf),
               (SELECT attivita_id FROM tmp_ca_mnf WHERE slot = s),
               r.uom_id, 10,
               v_lock, v_batch, v_emit, v_riga, v_stato,
               jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_mnf))
          FROM tmp_refs_mnf r
      RETURNING id)
    INSERT INTO tmp_af_mnf(slot, attivita_id) SELECT s, ins.id FROM ins;
  END LOOP;
END
$fx$;

SELECT ok(
  (SELECT count(*) = 7 FROM tmp_af_mnf)
  AND (SELECT count(*) = 8 FROM vendite.commesse_attivita ca
        JOIN tmp_ca_mnf t ON t.attivita_id = ca.id
       WHERE ca.stato_emissione = 'EMESSA')
  -- ⛔ La sesta riga NON deve avere un'attivita' fatturabile: e' il soggetto
  --   del test 8, e se qualcuno gliene creasse una il test verificherebbe
  --   un'altra cosa restando verde.
  AND NOT EXISTS (SELECT 1 FROM vendite.attivita_fatturabili af
                   WHERE af.commessa_attivita_id
                       = (SELECT attivita_id FROM tmp_ca_mnf WHERE slot = 'SENZA_AF'))
  AND (SELECT a.stato_esecuzione IS NULL AND a.lock_in_fatturazione IS TRUE
         FROM vendite.attivita_fatturabili a
        WHERE a.id = (SELECT attivita_id FROM tmp_af_mnf WHERE slot = 'VIVA_NULL'))
  AND (SELECT l.lotto_id IS NOT NULL FROM tmp_lotto_mnf l)
  -- ⭐ I due lotti stanno ai due lati di `in_gioco`: senza questo, 5-bis e
  --   5-ter proverebbero la stessa cosa due volte.
  AND (SELECT f.in_gioco FROM vendite.vw_lotti_fase f
        WHERE f.lotto_id = (SELECT lotto_id FROM tmp_lotto_mnf))
  AND NOT (SELECT f.in_gioco FROM vendite.vw_lotti_fase f
            WHERE f.lotto_id = (SELECT lotto_id FROM tmp_lotto_morto_mnf)),
  '3) fixture: otto righe di commessa EMESSA, sette attivita, un lotto in gioco e uno morto; l ottava senza attivita fatturabile'
);

-- ============================================================
-- 4) ⭐ LA CHIAVE DEL VERBO
-- ============================================================
-- ⛔ E' il fatto del §1 del brief: senza questa colonna il frontend non puo'
--   chiamare vendite.fn_riporta_attivita_da_emettere, e tradurre
--   commessa_attivita_id -> af.id lato backend sarebbe una seconda
--   implementazione di un legame che il database conosce gia'.
SELECT is(
  (SELECT count(*)::integer
     FROM vendite.vw_dash_competenza_attivita v
     JOIN tmp_ca_mnf c ON c.attivita_id = v.commessa_attivita_id
     JOIN tmp_af_mnf a ON a.slot = c.slot
    WHERE v.attivita_fatturabile_id = a.attivita_id),
  7,
  '4) la vista espone la CHIAVE del verbo: attivita_fatturabile_id e l id vero, su tutte e sette'
);

-- ============================================================
-- 5..9) Caso per caso: la vista e la fn_check dicono la stessa cosa
-- ============================================================
-- ⚠️ Il verbo si chiama in un'espressione SEPARATA dal confronto sul motivo:
--   sono due letture indipendenti, ed e' proprio la loro indipendenza che
--   rende il confronto una prova.
CREATE TEMP TABLE tmp_esito_mnf AS
SELECT c.slot,
       v.motivo_non_fatturata::text AS motivo_vista,
       v.stadio::text               AS stadio,
       (script.fn_check_attivita_riportabile_da_emettere(
            ARRAY[a.attivita_id]) -> 0 ->> 'codice') AS codice_fn
  FROM tmp_ca_mnf c
  JOIN tmp_af_mnf a ON a.slot = c.slot
  JOIN vendite.vw_dash_competenza_attivita v
    ON v.commessa_attivita_id = c.attivita_id;

-- ⭐ rev 2026-09-12: la DIVERGENZA. Libera, riga EMESSA, nessun marchio —
--   nessun giro la riprende, e il verbo e' l'unica via. Fino al 20260912-35
--   entrambe le superfici la chiamavano «in attesa del lotto», ed era falso.
SELECT ok(
  (SELECT e.motivo_vista = 'RESIDUO'
      AND e.codice_fn IS NOT DISTINCT FROM (SELECT codice_atteso FROM tmp_mappa_mnf
                                             WHERE motivo = 'RESIDUO')
     FROM tmp_esito_mnf e WHERE e.slot = 'LIBERA'),
  '5) libera con la riga EMESSA e senza marchio (divergenza): la vista dice RESIDUO e la fn NON ha motivi'
);

-- ⭐ Il transito fra pull e select: libera, ma il marchio e' di un lotto IN
--   GIOCO. Liberarla da qui la farebbe prendere da due giri: motivo 5.
SELECT ok(
  (SELECT e.motivo_vista = 'GIRO_IN_CORSO'
      AND e.codice_fn    = (SELECT codice_atteso FROM tmp_mappa_mnf
                             WHERE motivo = 'GIRO_IN_CORSO')
     FROM tmp_esito_mnf e WHERE e.slot = 'LIBERA_VIVA'),
  '5-bis) libera col marchio di un lotto IN GIOCO: la vista dice GIRO_IN_CORSO e la fn rifiuta con E_ATTIVITA_IN_LAVORAZIONE'
);

-- ⭐ Lo stesso marchio, ma di un lotto MORTO: e' il 13338 del brief — orfana,
--   e il verbo la riallinea.
SELECT ok(
  (SELECT e.motivo_vista = 'RESIDUO'
      AND e.codice_fn IS NOT DISTINCT FROM (SELECT codice_atteso FROM tmp_mappa_mnf
                                             WHERE motivo = 'RESIDUO')
     FROM tmp_esito_mnf e WHERE e.slot = 'LIBERA_MORTA'),
  '5-ter) libera col marchio di un lotto MORTO: la vista dice RESIDUO e la fn NON ha motivi'
);

SELECT ok(
  (SELECT e.motivo_vista = 'GIRO_IN_CORSO'
      AND e.codice_fn    = (SELECT codice_atteso FROM tmp_mappa_mnf
                             WHERE motivo = 'GIRO_IN_CORSO')
     FROM tmp_esito_mnf e WHERE e.slot = 'VIVA'),
  '6) lucchettata e PENDING: la vista dice GIRO_IN_CORSO e la fn rifiuta con E_ATTIVITA_IN_LAVORAZIONE'
);

-- ⛔ IL TEST CHE DISTINGUE `IS DISTINCT FROM` DA `<>`. Con un `<>` il confronto
--   su NULL darebbe NULL, il CASE cadrebbe sul ramo successivo e questa riga
--   uscirebbe RESIDUO — cioe' la lista offrirebbe il verbo su un'attivita' che
--   la mutazione rifiuta. Nessun dato vivo produce questo caso: e' costruito.
SELECT ok(
  (SELECT e.motivo_vista = 'GIRO_IN_CORSO'
      AND e.codice_fn    = (SELECT codice_atteso FROM tmp_mappa_mnf
                             WHERE motivo = 'GIRO_IN_CORSO')
     FROM tmp_esito_mnf e WHERE e.slot = 'VIVA_NULL'),
  '7) lucchettata con stato_esecuzione NULL: ANCORA GIRO_IN_CORSO su entrambe le superfici (IS DISTINCT FROM, non <>)'
);

-- ⛔ La riga di commessa EMESSA senza attivita' fatturabile. Il modello la
--   ammette (JOIN LEFT), nessun percorso scritto la produce, e senza un ramo
--   suo il COALESCE la farebbe cadere sul ramo delle LIBERE — cioe' RESIDUO,
--   «riportabile», con una chiave che non esiste: il verbo non avrebbe niente
--   da riallineare (fino al 2026-09-12 cadeva su IN_ATTESA_LOTTO, «il prossimo
--   giro la prende», falso per la stessa ragione: la pull filtra su
--   stato_emissione).
--   ⚠️ Qui non c'e' nessun id da passare alla fn_check, ed e' esattamente il
--   motivo per cui questo valore NON sta nella mappa: la chiave dev'essere
--   NULL, cosi' il frontend non puo' proporre un verbo che non ha bersaglio.
SELECT ok(
  (SELECT v.motivo_non_fatturata = 'SENZA_ATTIVITA_FATTURABILE'
      AND v.stadio               = 'EMESSA_NON_FATTURATA'
      AND v.attivita_fatturabile_id IS NULL
     FROM vendite.vw_dash_competenza_attivita v
    WHERE v.commessa_attivita_id = (SELECT attivita_id FROM tmp_ca_mnf WHERE slot = 'SENZA_AF')),
  '8) riga EMESSA senza attivita fatturabile: la vista la NOMINA e lascia la chiave a NULL'
);

-- ⭐ Il residuo: l'unico caso su cui il verbo ha effetto. `codice_fn` NULL vuol
--   dire che la funzione non ha trovato motivi, cioe' «si puo' fare».
SELECT ok(
  (SELECT e.motivo_vista = 'RESIDUO'
      AND e.codice_fn IS NOT DISTINCT FROM (SELECT codice_atteso FROM tmp_mappa_mnf
                                             WHERE motivo = 'RESIDUO')
     FROM tmp_esito_mnf e WHERE e.slot = 'ORFANA'),
  '9) lucchettata e COMPLETED senza fattura: la vista dice RESIDUO e la fn NON ha motivi'
);

-- ============================================================
-- 10) ⛔ Il confine: NULL fuori dallo stadio
-- ============================================================
-- La riga in fattura e' allo stadio FATTURATA, quindi la dimensione non si
-- applica e vale NULL. ⚠️ La fn_check rifiuta comunque, e con un codice
-- DIVERSO: e' la prova che «motivo NULL» non vuol dire «il verbo si puo' fare».
SELECT ok(
  (SELECT e.stadio = 'FATTURATA'
      AND e.motivo_vista IS NULL
      AND e.codice_fn = 'E_ATTIVITA_ANCORA_IN_FATTURA'
     FROM tmp_esito_mnf e WHERE e.slot = 'IN_FATTURA'),
  '10) fuori da EMESSA_NON_FATTURATA il motivo e NULL, e li la fn rifiuta con E_ATTIVITA_ANCORA_IN_FATTURA'
);

-- ============================================================
-- 11) ⭐ IL GIRO GENERALE — nessuna riga contraddice la fn_check
-- ============================================================
-- ⚠️ Non sostituisce i casi costruiti sopra, li COMPLETA: quelli provano che
--   ogni ramo esiste ed e' raggiungibile (su un DB vuoto questo giro sarebbe
--   0 = 0 e non proverebbe niente), questo prova che nessun'altra riga —
--   comprese quelle vere del database di sviluppo — sfugge alla mappa.
SELECT is(
  (SELECT count(*)::integer
     FROM vendite.vw_dash_competenza_attivita v
     JOIN tmp_mappa_mnf m ON m.motivo = v.motivo_non_fatturata::text
    WHERE v.attivita_fatturabile_id IS NOT NULL
      AND (script.fn_check_attivita_riportabile_da_emettere(
               ARRAY[v.attivita_fatturabile_id]) -> 0 ->> 'codice')
          IS DISTINCT FROM m.codice_atteso),
  0,
  '11) nessuna riga visibile della vista contraddice fn_check_attivita_riportabile_da_emettere'
);

-- ⛔ Il test 11 e' MUTO su un valore fuori mappa: il JOIN lo lascia fuori, e
--   un IN_ATTESA_LOTTO risorto (o un quinto valore inventato) passerebbe in
--   silenzio. Il vocabolario si asserisce per intero, qui.
SELECT is(
  (SELECT count(*)::integer
     FROM vendite.vw_dash_competenza_attivita v
    WHERE v.motivo_non_fatturata IS NOT NULL
      AND v.motivo_non_fatturata::text NOT IN (SELECT motivo FROM tmp_mappa_mnf)
      AND v.motivo_non_fatturata::text <> 'SENZA_ATTIVITA_FATTURABILE'),
  0,
  '11-bis) nessuna riga visibile porta un motivo fuori vocabolario: IN_ATTESA_LOTTO e ritirato, e la mappa e completa'
);

-- ============================================================
-- 12) ⭐ Il lotto di PROVENIENZA, e perche non e lotto_id
-- ============================================================
-- ⛔ `lotto_id` nasce dalla catena della FATTURA: su un residuo la fattura non
--   c'e', quindi e' NULL — ed e' proprio la riga in cui serve sapere da dove
--   viene. L'asserzione tiene le due colonne insieme apposta: se un giorno
--   qualcuno «semplificasse» riusando lotto_id, questo test cade.
SELECT ok(
  (SELECT v.lotto_provenienza_id      = (SELECT lotto_id FROM tmp_lotto_mnf)
      AND v.lotto_provenienza_codice  = (SELECT lotto_codice FROM tmp_lotto_mnf)
      AND v.lotto_id IS NULL
     FROM vendite.vw_dash_competenza_attivita v
    WHERE v.commessa_attivita_id = (SELECT attivita_id FROM tmp_ca_mnf WHERE slot = 'ORFANA'))
  -- E su una riga mai marchiata non c'e' nessuna provenienza da inventare.
  AND (SELECT v.lotto_provenienza_id IS NULL
         FROM vendite.vw_dash_competenza_attivita v
        WHERE v.commessa_attivita_id = (SELECT attivita_id FROM tmp_ca_mnf WHERE slot = 'LIBERA'))
  -- ⭐ rev 2026-09-12: il residuo DIVERGENTE il lucchetto non ce l'ha, e la
  --   sua provenienza e' il MARCHIO — il lotto morto che l'aveva presa in
  --   carico. Senza, la lista dei residui direbbe «da nessuna parte» proprio
  --   sulla riga in cui serve sapere da dove viene.
  AND (SELECT v.lotto_provenienza_id     = (SELECT lotto_id     FROM tmp_lotto_morto_mnf)
          AND v.lotto_provenienza_codice = (SELECT lotto_codice FROM tmp_lotto_morto_mnf)
         FROM vendite.vw_dash_competenza_attivita v
        WHERE v.commessa_attivita_id = (SELECT attivita_id FROM tmp_ca_mnf WHERE slot = 'LIBERA_MORTA')),
  '12) il residuo nomina il lotto di PROVENIENZA (lotto_id resta NULL: nasce dalla fattura); la riga senza marchio non ne ha; il divergente la prende dal marchio'
);

-- ============================================================
-- 13) ⛔ Il join sul lotto non moltiplica le righe
-- ============================================================
-- E' l'invariante che rende lecito un LEFT JOIN su una vista che ne alimenta
-- altre quattro: `fatturazione_lotti.lock_batch_id` e' UNIQUE. Se qualcuno
-- togliesse quel UNIQUE, la vista comincerebbe a contare doppio in silenzio.
SELECT is(
  (SELECT count(*)::integer
     FROM vendite.vw_dash_competenza_attivita v
     JOIN tmp_ca_mnf c ON c.attivita_id = v.commessa_attivita_id),
  8,
  '13) una riga di vista per riga di commessa: i join di provenienza e decode non moltiplicano'
);

-- ============================================================
-- 13-bis) ⭐ Il decode dell articolo — CHE LAVORO E
-- ============================================================
-- ⛔ Senza, la lista dei residui mostrerebbe un UUID: una lista su cui si deve
--   AGIRE, e che non dice quale lavoro sta chiedendo un'azione, non e'
--   azionabile. Il decode e' quello di fn_list_commessa_attivita, un livello
--   sopra sulla stessa colonna.
SELECT ok(
  (SELECT v.articolo_codice      = (SELECT a.codice      FROM catalogo.articoli a
                                     WHERE a.id = r.articolo_id)
      AND v.articolo_descrizione = (SELECT a.descrizione FROM catalogo.articoli a
                                     WHERE a.id = r.articolo_id)
     FROM vendite.vw_dash_competenza_attivita v, tmp_refs_mnf r
    WHERE v.commessa_attivita_id = (SELECT attivita_id FROM tmp_ca_mnf WHERE slot = 'ORFANA')),
  '13-bis) l articolo esce decodificato (codice e descrizione), non come UUID'
);

-- ============================================================
-- 14) La GRANA dell aggregata
-- ============================================================
-- ⭐ Non la sola presenza della colonna: la mensile deve avere esattamente una
--   riga per ogni (mese, stadio, stato, tipo_movimento, motivo) del dettaglio.
--   Diventa rossa se qualcuno ri-aggregasse a valle «per non rompere il
--   frontend», che e' la scorciatoia da cui questa dimensione nasce.
SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_competenza_mensile),
  (SELECT count(*)::integer FROM (
      SELECT 1 FROM vendite.vw_dash_competenza_attivita
       GROUP BY competenza_mese, stadio, stato_fattura_codice_interno,
                tipo_movimento, motivo_non_fatturata
   ) x),
  '14) la mensile ha una riga per (mese, stadio, stato, tipo_movimento, motivo_non_fatturata)'
);

-- ============================================================
-- 15) security_invoker su ENTRAMBE le viste
-- ============================================================
-- ⚠️ La reloption non e' visibile in pg_get_viewdef: un REPLACE che la omette
--   la azzera in SILENZIO, e lo scope emittente smette di valere. Entrambe le
--   viste sono state riscritte in questo giro, quindi si guardano entrambe.
SELECT is(
  (SELECT count(*)::integer
     FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite'
      AND c.relname IN ('vw_dash_competenza_attivita', 'vw_dash_competenza_mensile')
      AND c.reloptions @> ARRAY['security_invoker=on']),
  2,
  '15) security_invoker=on su entrambe le viste della Lente 1 toccate in questo giro'
);

-- ============================================================
-- 16) Fail-closed
-- ============================================================
-- ⚠️ Uno ZERO qui non e' un dato, e' un cancello: senza la GUC operatore le
--   viste non devono esporre NIENTE — nemmeno la dimensione nuova.
SELECT set_config('app.current_user_id', '', true);

SELECT ok(
  (SELECT count(*) = 0 FROM vendite.vw_dash_competenza_attivita v
    WHERE v.commessa_id = (SELECT id FROM tmp_commessa_mnf))
  AND
  (SELECT count(*) = 0 FROM vendite.vw_dash_competenza_mensile m
    WHERE m.competenza_mese = (SELECT competenza_mese FROM tmp_cost_mnf)),
  '16) fail-closed: senza GUC operatore ne il dettaglio ne l aggregata espongono la dimensione'
);

SELECT * FROM finish();
ROLLBACK;
