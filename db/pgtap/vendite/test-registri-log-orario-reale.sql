-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: R-1 — l'orario dei registri e' quello della SCRITTURA
--       (changeSet 20260824-16 + 20260824-17)
--
-- ⭐ COSA PRESIDIA, in una riga: che la storia di un lotto sia ORDINABILE.
--   `now()` e' l'istante di inizio transazione, quindi tutte le righe scritte
--   insieme uscivano con lo stesso timestamp al microsecondo. Su un registro
--   solo non morde — dentro l'istante ordina il contatore di quel registro —
--   ma la storia di un lotto ne legge TRE, e i loro contatori non sono
--   confrontabili fra loro.
--   Richiesta: brief-db-event-log-scope-e-riga-parlante.md §13 (R-1).
--
-- Elenco test (plan 8):
-- 1) i quattro DEFAULT sono `clock_timestamp()`
-- 2) ⭐ IL PRESIDIO: nessuna funzione scrive piu' `now()` in quelle colonne
-- 3) tre registri in UNA transazione: tre orari DISTINTI
-- 4) …e nell'ordine in cui sono stati scritti
-- 5) il trigger impone l'orario su `fatture_log` anche a chi passa `now()`
-- 6) `task_runs`: aperto e chiuso nella stessa transazione, la fine sta DOPO
--    l'inizio — cioe' il CHECK regge
-- 7) ⭐ L'ANCORAGGIO DEL «GIRO CORRENTE» CAMBIA, ed e' deciso: una riga
--    scritta nella stessa transazione ma PRIMA del `PIPELINE_STARTED` cade
--    FUORI dal giro corrente
-- 8) ⭐ …ma un orario SCELTO dal chiamante viene RISPETTATO — il rovescio del
--    test 5, aggiunto col changeSet 20260824-18
--
-- ⚠️ SUL TEST 2, e vale la pena leggerlo: il presidio deve TOGLIERE I COMMENTI
--   prima di cercare. Scrivendo questo lotto la prima versione era rossa, e il
--   colpevole era un commento del changeSet stesso che spiega il difetto
--   citandolo — «con `ended_at = now()` un tentativo…». Un presidio che legge
--   `prosrc` grezzo accusa chi documenta il difetto invece di chi lo commette.
--   E' la stessa lezione dello scanner dell'arita' in
--   test-catalogo-messaggi-errore-completo.sql, che i commenti li toglie.
--
-- ⚠️ COSA QUESTO FILE **NON** MISURA: che due righe non possano MAI collidere.
--   `clock_timestamp()` ha risoluzione al microsecondo, quindi due scritture
--   dentro la stessa istruzione possono ancora cadere nello stesso istante —
--   ma sono righe dello STESSO registro, dove il tiebreak per id esiste ed e'
--   valido. Il caso che serviva risolvere e' quello FRA registri, e quello sta
--   in statement diversi.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

SET LOCAL app.ruolo_applicativo = 'OPERATORE';

-- ============================================================
-- 1) I quattro DEFAULT
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM pg_attrdef d
     JOIN pg_class c ON c.oid = d.adrelid
     JOIN pg_namespace n ON n.oid = c.relnamespace
     JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = d.adnum
    WHERE n.nspname = 'vendite'
      AND (c.relname, a.attname) IN
          (('event_log','event_time'), ('fatture_log','data_ora'),
           ('fatturazione_lotti_log','data_ora'),
           ('fatturazione_lotti_task_runs','started_at'))
      AND pg_get_expr(d.adbin, d.adrelid) ILIKE '%clock_timestamp%'),
  4,
  '1) i quattro registri hanno il DEFAULT all''orario della scrittura'
);

-- ============================================================
-- 2) ⭐ IL PRESIDIO — vale per il futuro, non per oggi.
--    Il difetto vero non e' il codice di adesso: e' il nono scrittore, che fra
--    sei mesi scrivera' `now()` per abitudine e non lo dira' a nessuno. Qui
--    non c'e' niente da leggere a video, quindi un difetto del genere non si
--    manifesta: si accumula.
--    ⚠️ Si tolgono i commenti prima di cercare — vedi la testata.
-- ============================================================
SELECT is(
  (SELECT coalesce(string_agg(DISTINCT n.nspname || '.' || p.proname, ', '), '')
     FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
     JOIN pg_language l ON l.oid = p.prolang
    WHERE l.lanname = 'plpgsql'
      AND regexp_replace(p.prosrc, '--[^' || chr(10) || ']*', '', 'g')
          ~ '(event_time|started_at|ended_at)[[:space:]]*=[[:space:]]*now\(\)'),
  '',
  '2) nessuna funzione scrive piu'' now() nelle colonne di orario dei registri'
);

-- ============================================================
-- FIXTURE — un lotto con almeno una fattura, visibile all'operatore.
-- rev 2026-10-27 (lotto 4 di D7): lotto e fattura si COSTRUISCONO
--   (dbops.fn_pgtap_crea_fattura, poi dbops.fn_pgtap_crea_lotto sullo stesso
--   cliente) e si legano col ponte. Prima si pescava l'ultimo lotto del DB
--   con una fattura: da zero non ce n'era, e il primo fn_log_event moriva
--   su un lotto NULL. Il test scrive comunque le PROPRIE righe di registro:
--   ogni lotto con una fattura e' un soggetto valido.
-- ============================================================
CREATE TEMP TABLE tmp_fattura_r1 AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('registri orario reale');

CREATE TEMP TABLE tmp_lotto_r1 AS
SELECT * FROM dbops.fn_pgtap_crea_lotto(
         'registri orario reale', 'DRAFT',
         (SELECT billing_account_id FROM tmp_fattura_r1));

INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, stato_doc_fiscale_id)
SELECT l.lotto_id, f.fattura_id, f.stato_doc_fiscale_id
  FROM tmp_lotto_r1 l, tmp_fattura_r1 f;

CREATE TEMP TABLE tmp_refs_r1 AS
SELECT l.lotto_id, f.fattura_id
  FROM tmp_lotto_r1 l, tmp_fattura_r1 f;

-- ⚠️ Le tre scritture in ISTRUZIONI SEPARATE, ed e' il soggetto del test: e'
--    proprio fra statement diversi che `now()` dava lo stesso valore e
--    `clock_timestamp()` no.
--    ⭐ E la prima passa `now()` A MANO: e' il caso reale dei cinque
--    scrittori di `fatture_log` e del backend, ed e' quello che il trigger
--    deve scavalcare (test 5).
INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta)
SELECT fattura_id, now(), 'pgTAP R-1 prima', 'W', FALSE,
       jsonb_build_object('test_scope', 'pgtap_r1', 'quando', 'prima')
  FROM tmp_refs_r1;

SELECT vendite.fn_log_event('LOTTO', (SELECT lotto_id FROM tmp_refs_r1),
                            'PIPELINE_STARTED', 'INFO');

SELECT vendite.fn_log_pipeline_fase((SELECT lotto_id FROM tmp_refs_r1), NULL,
                                    'pgtap_r1', 'I', 'pgTAP R-1 fase');

INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta)
SELECT fattura_id, now(), 'pgTAP R-1 dopo', 'W', FALSE,
       jsonb_build_object('test_scope', 'pgtap_r1', 'quando', 'dopo')
  FROM tmp_refs_r1;

CREATE TEMP TABLE tmp_orari_r1 AS
SELECT (SELECT data_ora FROM vendite.fatture_log
         WHERE meta->>'test_scope' = 'pgtap_r1' AND meta->>'quando' = 'prima') AS t_prima,
       (SELECT max(event_time) FROM vendite.event_log
         WHERE entity_type = 'LOTTO' AND entity_id = (SELECT lotto_id FROM tmp_refs_r1)
           AND event_code = 'PIPELINE_STARTED')                                 AS t_evento,
       (SELECT data_ora FROM vendite.fatturazione_lotti_log
         WHERE lotto_id = (SELECT lotto_id FROM tmp_refs_r1) AND fase = 'pgtap_r1') AS t_fase,
       (SELECT data_ora FROM vendite.fatture_log
         WHERE meta->>'test_scope' = 'pgtap_r1' AND meta->>'quando' = 'dopo')  AS t_dopo;

-- ============================================================
-- 3) Tre registri, una transazione, TRE orari distinti.
--    Con `now()` sarebbero stati uno solo, ed e' tutto il difetto.
-- ============================================================
SELECT is(
  (SELECT count(DISTINCT x)::int FROM tmp_orari_r1 o,
          LATERAL (VALUES (o.t_prima), (o.t_evento), (o.t_fase)) AS v(x)),
  3,
  '3) tre registri scritti nella stessa transazione hanno tre orari distinti'
);

-- ============================================================
-- 4) …e l'ordine e' quello della scrittura. E' la proprieta' che la storia
--    del lotto consuma: senza, la timeline mostrerebbe una sequenza mai
--    avvenuta — e nessuno se ne accorgerebbe guardandola.
-- ============================================================
SELECT is(
  (SELECT (t_prima < t_evento AND t_evento < t_fase AND t_fase < t_dopo)::text
     FROM tmp_orari_r1),
  'true',
  '4) gli orari crescono nell''ordine in cui le righe sono state scritte'
);

-- ============================================================
-- 5) IL TRIGGER SCAVALCA IL CHIAMANTE.
--    Le due righe di `fatture_log` qui sopra hanno passato `now()` a mano —
--    come fanno i cinque scrittori veri e il backend — e devono essere uscite
--    con un orario DIVERSO da `data_insert`, che `now()` ce l'ha davvero.
--    ⚠️ Si confronta con `data_insert` e non con `now()` scritto qui: dentro
--    la stessa transazione `now()` e' una costante, quindi il confronto e'
--    esattamente «il trigger ha scavalcato l'inizio transazione».
-- ============================================================
SELECT is(
  (SELECT (count(*) = 2)::text
     FROM vendite.fatture_log
    WHERE meta->>'test_scope' = 'pgtap_r1'
      AND data_ora > data_insert),
  'true',
  '5) su fatture_log l''orario lo mette il trigger, non il chiamante'
);

-- ============================================================
-- 6) task_runs: aperto e chiuso nella STESSA transazione.
--    ⛔ E' il caso che avrebbe rotto la pipeline se `ended_at` fosse rimasto a
--    `now()`: la fine sarebbe caduta PRIMA dell'inizio e
--    chk_fatt_lotti_task_runs_timestamps avrebbe rifiutato l'UPDATE. Misurato
--    il 2026-08-24: 165 corse su 319 sono esattamente questo caso.
-- ============================================================
CREATE TEMP TABLE tmp_run_r1 AS
SELECT (vendite.fn_start_lotto_task_run(
           (SELECT lotto_id FROM tmp_refs_r1),
           (SELECT p.id FROM vendite.fatturazione_pipeline p ORDER BY p.id LIMIT 1),
           NULL, 'PGTAP_R1')).task_run_id AS id;

SELECT vendite.fn_set_runtime_task_run_esito((SELECT id FROM tmp_run_r1), 'COMPLETATO');

SELECT is(
  (SELECT (ended_at > started_at)::text
     FROM vendite.fatturazione_lotti_task_runs
    WHERE id = (SELECT id FROM tmp_run_r1)),
  'true',
  '6) un tentativo aperto e chiuso nella stessa transazione finisce DOPO essere iniziato'
);

-- ============================================================
-- 7) ⭐ L'ANCORAGGIO DEL «GIRO CORRENTE» — il cambio di perimetro, deciso.
--
--    `fn_list_lotto_segnalazioni` (e la gemella `fn_list_lotto_task_runs`)
--    ancorano il giro corrente a `max(event_time)` dei `PIPELINE_STARTED` e
--    tengono dentro cio' che viene da li' in avanti.
--
--    ⚠️ CON `now()` QUEL PREDICATO NON DISTINGUEVA NIENTE: tutte le righe
--    della stessa transazione avevano l'orario del marcatore, quindi anche
--    quelle scritte PRIMA finivano dentro il giro corrente. Con l'orario vero
--    cadono fuori.
--
--    ⭐ E' la lettura giusta — appartengono al giro precedente — ed e' una
--    DECISIONE (Tid, 2026-08-24) su una funzione in servizio: sta qui, in un
--    test, e non in una frase di un brief.
-- ============================================================
SELECT is(
  (SELECT string_agg(s.messaggio || '=' || s.job_corrente::text, ' ' ORDER BY s.data_ora)
     FROM vendite.fn_list_lotto_segnalazioni(
            (SELECT lotto_id FROM tmp_refs_r1), NULL, NULL, TRUE, FALSE, 500, 0) s
    WHERE s.messaggio IN ('pgTAP R-1 prima', 'pgTAP R-1 dopo')),
  'pgTAP R-1 prima=false pgTAP R-1 dopo=true',
  '7) cio'' che precede il PIPELINE_STARTED resta FUORI dal giro corrente, anche nella stessa transazione'
);

-- ============================================================
-- 8) ⭐ IL ROVESCIO DEL TEST 5, e vale un rosso pagato.
--
--    La prima versione del trigger (20260824-17) scriveva SEMPRE, senza
--    guardare cosa avesse passato il chiamante — e ha cancellato le linee del
--    tempo che le fixture pgTAP fabbricano a mano (`now() - interval '40 min'`),
--    che sono l'unico modo di collaudare una finestra temporale dentro una
--    transazione, dove `now()` e' costante. Tre asserzioni di
--    `test-fn-list-lotto-segnalazioni-job` sono diventate rosse, e la testata
--    di quel file la ragione la scriveva gia'.
--
--    ⭐ La regola corretta (20260824-18): chi passa l'istante di INIZIO
--    TRANSAZIONE non ha SCELTO un orario, ha usato l'unico che aveva — e
--    quello si sostituisce (test 5). Qualunque ALTRO valore e' una scelta, e
--    si rispetta — che e' questo test.
--
--    ⚠️ Senza questa asserzione la correzione sarebbe una riga di codice senza
--    nessuno che la difenda: chi in futuro «semplificasse» il trigger
--    togliendo la condizione rifarebbe lo stesso danno, e se ne accorgerebbe
--    solo dal rosso di un test che parla d'altro.
-- ============================================================
INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta)
SELECT fattura_id, now() - interval '40 min', 'pgTAP R-1 scelto', 'W', FALSE,
       jsonb_build_object('test_scope', 'pgtap_r1', 'quando', 'scelto')
  FROM tmp_refs_r1;

SELECT is(
  (SELECT (data_ora = now() - interval '40 min')::text
     FROM vendite.fatture_log
    WHERE meta->>'test_scope' = 'pgtap_r1' AND meta->>'quando' = 'scelto'),
  'true',
  '8) un orario scelto dal chiamante NON viene sovrascritto dal trigger'
);

SELECT * FROM finish();
ROLLBACK;
