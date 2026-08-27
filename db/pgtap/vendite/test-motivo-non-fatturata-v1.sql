-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
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
-- Indice test (1..17, con un 13-bis)
--  1) Riferimenti minimi presenti
--  2) La vista espone le OTTO colonne nuove
--  3) Fixture: sei righe di commessa EMESSA, cinque attivita, un lotto
--  4) ⭐ LA CHIAVE: attivita_fatturabile_id e' l id vero, riga per riga
--  5) IN_ATTESA_LOTTO  <-> E_ATTIVITA_GIA_DA_EMETTERE
--  6) GIRO_IN_CORSO    <-> E_ATTIVITA_IN_LAVORAZIONE   (stato PENDING)
--  7) ⛔ GIRO_IN_CORSO <-> E_ATTIVITA_IN_LAVORAZIONE   (stato NULL)
--  8) ⛔ SENZA_ATTIVITA_FATTURABILE: nominata, e senza chiave
--  9) RESIDUO          <-> nessun motivo: il verbo accetta
-- 10) ⛔ NULL fuori da EMESSA_NON_FATTURATA, e li la fn rifiuta comunque
-- 11) ⭐ IL GIRO GENERALE: nessuna riga visibile contraddice la fn_check
-- 12) ⭐ Il lotto di PROVENIENZA c e, e non e lotto_id
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

SELECT plan(17);

-- ============================================================
-- 0) Riferimenti e costanti
-- ============================================================
CREATE TEMP TABLE tmp_cost_mnf AS
SELECT 'pgtap_motivo_non_fatturata'::text        AS test_scope,
       uuidv7()                                  AS lock_batch_id,
       script.fn_pgtap_emittente_sr_operatore()  AS emittente_sr_id,
       -- ⚠️ Un mese di competenza LONTANO da quelli veri: le asserzioni di
       --   grana (test 14) e di perimetro restano leggibili anche su un
       --   database con dati, e il test 16 non conta righe altrui.
       DATE '2081-05-01'                         AS competenza_mese;

CREATE TEMP TABLE tmp_refs_mnf AS
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
    WHERE upper(btrim(codice_interno)) = 'DRAFT' ORDER BY id LIMIT 1) AS stato_draft_id,
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
  (SELECT r.id FROM vendite.registri_fatturazione r
    WHERE r.attivo IS TRUE
      AND (r.emittente_soggetto_ruolo_id IS NULL
           OR r.emittente_soggetto_ruolo_id = (SELECT emittente_sr_id FROM tmp_cost_mnf))
    ORDER BY r.id LIMIT 1)            AS registro_id;

SELECT ok(
  (SELECT r.stato_draft_id IS NOT NULL
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
  ('IN_ATTESA_LOTTO', 'E_ATTIVITA_GIA_DA_EMETTERE'),
  ('GIRO_IN_CORSO',   'E_ATTIVITA_IN_LAVORAZIONE'),
  ('RESIDUO',         NULL);
-- ⛔ SENZA_ATTIVITA_FATTURABILE non entra nella mappa, e non e' una svista:
--   li' non c'e' nessun `attivita_fatturabili.id` da passare alla funzione.
--   E' proprio cio' che il test 8 asserisce.

-- ============================================================
-- Fixture: una commessa, SEI righe di commessa gia' EMESSA
-- ============================================================
CREATE TEMP TABLE tmp_commessa_mnf AS
WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                emittente_soggetto_ruolo_id, stato_commessa_id)
  SELECT 'PGTAP-MNF-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id,
         (SELECT emittente_sr_id FROM tmp_cost_mnf), r.stato_commessa_id
    FROM tmp_refs_mnf r
  RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_ca_mnf (slot text PRIMARY KEY, attivita_id bigint);

-- ⚠️ Tutte EMESSA: e' lo stato che la pipeline lascia dopo l'emissione, ed e'
--   la condizione che porta la riga nello stadio EMESSA_NON_FATTURATA quando
--   la riga di fattura manca. Senza, il motivo uscirebbe NULL per un'altra
--   ragione e il test verificherebbe un caso diverso da quello che dichiara.
DO $fx$
DECLARE
  s text;
BEGIN
  FOREACH s IN ARRAY ARRAY['ORFANA', 'IN_FATTURA', 'LIBERA', 'VIVA',
                           'VIVA_NULL', 'SENZA_AF'] LOOP
    -- ⚠️ Un INSERT che restituisce righe sta in una CTE, non in un FROM.
    WITH ins AS (
      INSERT INTO vendite.commesse_attivita (
        commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
        uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
        tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
        stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
      SELECT (SELECT id FROM tmp_commessa_mnf),
             'PGTAP-MNF-' || s || '-' || substr(md5(clock_timestamp()::text), 1, 12),
             r.articolo_id, r.istanza_utility_id,
             (SELECT competenza_mese FROM tmp_cost_mnf),
             r.uom_id, 1,
             (SELECT competenza_mese FROM tmp_cost_mnf),
             (SELECT competenza_mese FROM tmp_cost_mnf),
             ((SELECT competenza_mese FROM tmp_cost_mnf) + INTERVAL '1 month - 1 day')::date,
             r.tipo_doc_fiscale_id, r.valuta_id, 10.000000, 'FIXED',
             'APPROVATA', 'EMESSA', NULL, NULL
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
                                     qta, prezzo_unitario, imponibile_riga)
  SELECT f.fattura_id, 1, 'Riga PGTAP MNF', 1, 10, 10
    FROM tmp_fattura_mnf f
  RETURNING id)
SELECT id AS riga_id FROM ins;

-- ============================================================
-- Le CINQUE attivita' fatturabili — e la sesta riga che non ne ha nessuna
-- ============================================================
--   ORFANA     -> lucchettata, COMPLETED, senza fattura   => RESIDUO
--   IN_FATTURA -> agganciata a una riga viva              => stadio FATTURATA
--   LIBERA     -> nessun lucchetto                        => IN_ATTESA_LOTTO
--   VIVA       -> lucchettata, PENDING                    => GIRO_IN_CORSO
--   VIVA_NULL  -> lucchettata, stato NULL                 => GIRO_IN_CORSO
--   SENZA_AF   -> nessuna attivita' fatturabile      => SENZA_ATTIVITA_FATTURABILE
CREATE TEMP TABLE tmp_af_mnf (slot text PRIMARY KEY, attivita_id bigint);

DO $fx$
DECLARE
  s       text;
  v_riga  bigint;
  v_lock  boolean;
  v_batch uuid;
  v_stato text;
BEGIN
  FOREACH s IN ARRAY ARRAY['ORFANA', 'IN_FATTURA', 'LIBERA', 'VIVA', 'VIVA_NULL'] LOOP
    v_riga  := CASE WHEN s = 'IN_FATTURA' THEN (SELECT riga_id FROM tmp_riga_mnf) END;
    v_lock  := (s <> 'LIBERA');
    v_batch := CASE WHEN s <> 'LIBERA' THEN (SELECT lock_batch_id FROM tmp_cost_mnf) END;
    -- ⛔ VIVA_NULL resta a NULL DI PROPOSITO: e' il caso che distingue
    --   `IS DISTINCT FROM` da `<>`, e nessun dato vivo lo produce oggi.
    v_stato := CASE WHEN s = 'VIVA'      THEN 'PENDING'
                    WHEN s = 'VIVA_NULL' THEN NULL
                    WHEN s = 'LIBERA'    THEN NULL
                    ELSE 'COMPLETED' END;

    WITH ins AS (
      INSERT INTO vendite.attivita_fatturabili (
            articolo_id, istanza_utility_id, billing_account_id, data_attivita,
            competenza_mese, competenza_dal, competenza_al, quantita, approvato,
            sospesa, tipo_doc_fiscale_id, valuta_id, commessa_id,
            commessa_attivita_id, uom_id, prezzo_unitario, lock_in_fatturazione,
            lock_batch_id, fattura_riga_id, stato_esecuzione, meta)
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
               v_lock, v_batch, v_riga, v_stato,
               jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_mnf))
          FROM tmp_refs_mnf r
      RETURNING id)
    INSERT INTO tmp_af_mnf(slot, attivita_id) SELECT s, ins.id FROM ins;
  END LOOP;
END
$fx$;

SELECT ok(
  (SELECT count(*) = 5 FROM tmp_af_mnf)
  AND (SELECT count(*) = 6 FROM vendite.commesse_attivita ca
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
  AND (SELECT l.lotto_id IS NOT NULL FROM tmp_lotto_mnf l),
  '3) fixture: sei righe di commessa EMESSA, cinque attivita, un lotto; la sesta senza attivita fatturabile'
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
  5,
  '4) la vista espone la CHIAVE del verbo: attivita_fatturabile_id e l id vero, su tutte e cinque'
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

SELECT ok(
  (SELECT e.motivo_vista = 'IN_ATTESA_LOTTO'
      AND e.codice_fn    = (SELECT codice_atteso FROM tmp_mappa_mnf
                             WHERE motivo = 'IN_ATTESA_LOTTO')
     FROM tmp_esito_mnf e WHERE e.slot = 'LIBERA'),
  '5) non lucchettata: la vista dice IN_ATTESA_LOTTO e la fn rifiuta con E_ATTIVITA_GIA_DA_EMETTERE'
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
--   suo il COALESCE la farebbe cadere su IN_ATTESA_LOTTO — «il prossimo giro
--   la prende», che e' falso: la pull filtra su stato_emissione.
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
  -- E su una riga mai lucchettata non c'e' nessuna provenienza da inventare.
  AND (SELECT v.lotto_provenienza_id IS NULL
         FROM vendite.vw_dash_competenza_attivita v
        WHERE v.commessa_attivita_id = (SELECT attivita_id FROM tmp_ca_mnf WHERE slot = 'LIBERA')),
  '12) il residuo nomina il lotto di PROVENIENZA (lotto_id resta NULL: nasce dalla fattura); la riga libera non ne ha'
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
  6,
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
