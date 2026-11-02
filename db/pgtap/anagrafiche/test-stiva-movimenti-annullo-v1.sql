-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: annullo di una forzatura nel registro plafond IVA, e registro append-only
-- Brief: brief-db-titoli-iva-movimenti-annullo, §6.7 (Fase F-1)
-- ------------------------------------------------------------
-- Indice test (plan 12):
--  0) oggetti presenti (colonna, indice, check, madre, check di dominio, vista)
--  1) annullata una forzatura: DUE righe nel registro e imponibile_utilizzato
--     tornato al valore precedente
--  2) doppio annullo rifiutato (dall'indice unique parziale)
--  3) annullo di un movimento FATTURA rifiutato
--  4) ⭐ importo diverso dall'opposto rifiutato — e' cio' che rende vero il
--     n. 1 invece di lasciarlo alla fixture
--  5) ⭐ collegamento a un movimento di un ALTRO titolo rifiutato
--  6) auto-annullo rifiutato (dal CHECK)
--  7) ⭐ annullo di un annullo rifiutato (decisione B-2)
--  8) ⭐ DELETE sul registro rifiutato (decisione B-1)
--  9) ⭐ UPDATE sul registro rifiutato (decisione B-1)
-- 10) ⭐ la vista espone il motivo di blocco, e coincide con cio' che la madre
--     rifiuta — il pulsante spento e il rifiuto leggono la stessa regola
-- 11) ⭐⭐ la check VEDE la riga anche da un perimetro che NON la vede: e' la
--     prova che il SECURITY DEFINER serve davvero
--
-- Scopo:
--  - il n. 4 e il n. 5 sono i due che il brief del BE non chiedeva, e sono i
--    piu' importanti: senza il 4, il presidio del n. 1 lo rende vero la
--    FIXTURE (che scrive il numero giusto) e non la regola; senza il 5, un
--    annullo collegato a un altro titolo decurta il plafond sbagliato SENZA
--    sollevare niente, perche' l'accumulatore somma per titolo;
--  - il n. 10 e' il presidio della decisione B-3: un motivo che non arriva
--    sulla superficie e' un pulsante grigio e muto.
--
-- ⭐ Il n. 11 e' la prova del SECURITY DEFINER, e non serviva un secondo
--    emittente come si era creduto: basta cambiare CHI GUARDA. La riga si
--    costruisce dal perimetro che la puo' scrivere, poi si sposta il contesto
--    su uno che non la vede — e si verifica che la check la veda lo stesso.
--    ⛔ Senza quel test, togliere `SECURITY DEFINER` domani lascerebbe tutti
--    gli altri 11 verdi.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga non verrebbero mai esercitati (qui il
--   COMMIT non arriva mai, si chiude in ROLLBACK) e il file sarebbe verde per
--   sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS
-- attiva), non come owner. La policy del registro pretende
-- app.ruolo_applicativo = 'OPERATORE' e la whitelist emittente.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- ⛔ 2026-09-23: qui c'erano `SET LOCAL app.ruolo_applicativo = 'OPERATORE'` e
--   `SET LOCAL app.current_user_id = '1'`, che SOVRASCRIVEVANO il contesto
--   appena aperto dalla riga sopra. L'utente 1 su dbdev e' il super admin —
--   il perimetro che vede tutto, cioe' il contrario di cio' che un test RLS
--   vuole — e su un database ricostruito dai changelog non esiste: la fixture
--   moriva su «la nuova riga viola la regola di sicurezza». Veste e utente li
--   mette gia' la riga di contesto.

-- ============================================================
-- 0) Oggetti presenti
-- ============================================================
SELECT ok(
  (SELECT count(*) = 3 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE (n.nspname = 'anagrafiche' AND p.proname IN
             ('fn_annulla_movimento_titolo_iva','trgfn_stiva_movimenti_append_only'))
       OR (n.nspname = 'script' AND p.proname = 'fn_check_annullo_movimento_titolo_iva'))
  AND EXISTS (SELECT 1 FROM pg_attribute
               WHERE attrelid = 'anagrafiche.soggetti_titoli_iva_movimenti'::regclass
                 AND attname = 'annulla_movimento_id' AND NOT attisdropped)
  AND to_regclass('anagrafiche.uq_stiva_movimenti_annulla') IS NOT NULL
  AND to_regclass('anagrafiche.vw_stiva_movimenti_dettaglio') IS NOT NULL
  AND EXISTS (SELECT 1 FROM pg_constraint
               WHERE conrelid = 'anagrafiche.soggetti_titoli_iva_movimenti'::regclass
                 AND conname = 'chk_stiva_movimenti_auto_annullo'),
  '0) oggetti presenti (colonna, indice, check, madre, check di dominio, vista)');

-- ============================================================
-- Fixture: due titoli IVA dello STESSO emittente di chi opera.
--   ⚠️ L'emittente NON si pesca, si DERIVA: le policy `ef_whitelist` lo
--   pretendono, e un titolo di un altro emittente sarebbe invisibile alla
--   fixture stessa.
--   ⭐ Due titoli e non uno: il n. 5 verifica proprio il collegamento
--   incrociato, e con un titolo solo non sarebbe costruibile.
-- ============================================================
-- I due clienti titolari, in due istruzioni: il BA del secondo serve anche
-- alla fattura del n. 3.
CREATE TEMP TABLE tmp_cli AS
SELECT 1 AS n, c.* FROM dbops.fn_pgtap_crea_cliente_ba('annullo titolo 1') c;

INSERT INTO tmp_cli
SELECT 2, c.* FROM dbops.fn_pgtap_crea_cliente_ba('annullo titolo 2') c;

CREATE TEMP TABLE tmp_ref AS
SELECT
  script.fn_pgtap_emittente_operatore()                                      AS emittente_fiscale_id,
  -- ⭐ DUE soggetti, e non due titoli dello stesso: il vincolo
  --   ex_soggetti_titoli_iva_no_overlap vieta due titoli dello stesso tipo,
  --   emittente e soggetto con validita' sovrapposte — giustamente. E il caso
  --   peggiore del n. 5 e' proprio questo: un annullo che decurta il plafond
  --   di UN ALTRO CLIENTE.
  --   ⛔ 2026-09-23: erano «i primi due soggetti» del database, che su uno
  --   ricostruito sono l'azienda del contesto e poco altro. Si costruiscono:
  --   due clienti dell'azienda di chi agisce (tmp_cli, sopra).
  (SELECT c.soggetto_id FROM tmp_cli c WHERE c.n = 1)                       AS soggetto_1_id,
  (SELECT c.soggetto_id FROM tmp_cli c WHERE c.n = 2)                       AS soggetto_2_id,
  (SELECT tt.id FROM config.tipi_titolo_iva tt WHERE tt.attivo IS TRUE ORDER BY tt.id LIMIT 1) AS tipo_titolo_iva_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id;

CREATE TEMP TABLE tmp_titoli AS
WITH ins AS (
  INSERT INTO anagrafiche.soggetti_titoli_iva (
      soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
      ambito, valido_dal, plafond, storicizza, meta)
  SELECT CASE g WHEN 1 THEN r.soggetto_1_id ELSE r.soggetto_2_id END,
         r.emittente_fiscale_id, r.tipo_titolo_iva_id, r.iva_id,
         'TUTTO', script.fn_data_operativa() - 30, 100000, false,
         jsonb_build_object('test_scope','pgtap_stiva_annullo', 'n', g)
    FROM tmp_ref r, generate_series(1,2) g
  RETURNING id, meta)
SELECT id, (meta->>'n')::int AS n FROM ins;

-- La forzatura da annullare: +250 sul titolo 1.
CREATE TEMP TABLE tmp_forz AS
WITH ins AS (
  INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti (
      titolo_iva_id, tipo_movimento, imponibile, data_movimento, motivo, meta)
  SELECT (SELECT id FROM tmp_titoli WHERE n = 1),
         'FORZATURA', 250, script.fn_data_operativa() - 5, 'forzatura di prova',
         jsonb_build_object('test_scope','pgtap_stiva_annullo')
  RETURNING id, titolo_iva_id, imponibile)
SELECT * FROM ins;

-- Il valore dell'accumulatore PRIMA dell'annullo, letto e non supposto.
CREATE TEMP TABLE tmp_prima AS
SELECT t.imponibile_utilizzato AS usato
  FROM anagrafiche.soggetti_titoli_iva t
 WHERE t.id = (SELECT titolo_iva_id FROM tmp_forz);

-- ============================================================
-- 1) L'annullo: due righe, e il totale torna dov'era.
--    ⚠️ Il valore "precedente" e' quello di PRIMA della forzatura, cioe'
--    l'usato meno 250: annullare significa tornare li'.
-- ============================================================
CREATE TEMP TABLE tmp_annullo AS
SELECT anagrafiche.fn_annulla_movimento_titolo_iva(
         (SELECT id FROM tmp_forz), 'forzatura sbagliata') AS id;

SELECT ok(
  (SELECT count(*) = 2 FROM anagrafiche.soggetti_titoli_iva_movimenti m
    WHERE m.titolo_iva_id = (SELECT titolo_iva_id FROM tmp_forz))
  AND (SELECT t.imponibile_utilizzato = (SELECT usato FROM tmp_prima) - 250
         FROM anagrafiche.soggetti_titoli_iva t
        WHERE t.id = (SELECT titolo_iva_id FROM tmp_forz)),
  '1) annullo: DUE righe nel registro e imponibile_utilizzato tornato indietro');

-- ============================================================
-- 2) Doppio annullo: lo ferma l'indice unique parziale.
--    ⚠️ Esce P0001 e NON 23505, ed e' voluto: il guard BEFORE INSERT chiama
--    la check, che risponde GIA_ANNULLATO, e solleva PRIMA che l'indice venga
--    valutato. L'indice resta la difesa finale per chi scrivesse col guard
--    spento — ma non e' lui a parlare all'operatore.
-- ============================================================
SELECT throws_ok(
  format($q$INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti
             (titolo_iva_id, tipo_movimento, imponibile, data_movimento, motivo,
              annulla_movimento_id)
             SELECT %s, 'FORZATURA', -250, script.fn_data_operativa(), 'secondo annullo', %s$q$,
         (SELECT titolo_iva_id FROM tmp_forz), (SELECT id FROM tmp_forz)),
  'P0001', NULL,
  '2) doppio annullo rifiutato');

-- ============================================================
-- 3) Un movimento FATTURA non si annulla: si corregge dal documento.
--    ⚠️ Costruito, non cercato: serve una riga con fattura_id valorizzato, che
--    il CHECK pretende su ogni tipo diverso da FORZATURA.
-- ============================================================
-- ⛔ 2026-09-23: «costruito, non cercato» valeva per il movimento ma non per
--   la fattura, che era «la prima» del database: da zero non ce n'e' nessuna.
--   Si costruisce, sul BA del cliente del titolo 2 — la fattura e' sua.
CREATE TEMP TABLE tmp_fatt AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
           'annullo titolo', 'DRAFT',
           (SELECT c.billing_account_id FROM tmp_cli c WHERE c.n = 2)) f;

CREATE TEMP TABLE tmp_mov_fatt AS
WITH ins AS (
  INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti (
      titolo_iva_id, tipo_movimento, imponibile, data_movimento, fattura_id, meta)
  SELECT (SELECT id FROM tmp_titoli WHERE n = 2), 'FATTURA', 100,
         script.fn_data_operativa() - 3, (SELECT id FROM tmp_fatt),
         jsonb_build_object('test_scope','pgtap_stiva_annullo')
  RETURNING id)
SELECT * FROM ins;

SELECT throws_ok(
  format($q$SELECT anagrafiche.fn_annulla_movimento_titolo_iva(%s, 'tentativo')$q$,
         (SELECT id FROM tmp_mov_fatt)),
  'P0001', NULL,
  '3) annullo di un movimento FATTURA rifiutato');

-- ============================================================
-- 4) ⭐ Importo diverso dall'opposto: rifiutato.
--    E' il test che rende vero il n. 1. Senza, il n. 1 passa perche' la
--    FIXTURE scrive il numero giusto — non perche' la regola lo imponga.
--    Serve una forzatura NON ancora annullata: si usa il titolo 2.
-- ============================================================
CREATE TEMP TABLE tmp_forz2 AS
WITH ins AS (
  INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti (
      titolo_iva_id, tipo_movimento, imponibile, data_movimento, motivo, meta)
  SELECT (SELECT id FROM tmp_titoli WHERE n = 2), 'FORZATURA', 400,
         script.fn_data_operativa() - 4, 'seconda forzatura',
         jsonb_build_object('test_scope','pgtap_stiva_annullo')
  RETURNING id, titolo_iva_id)
SELECT * FROM ins;

SELECT throws_ok(
  format($q$INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti
             (titolo_iva_id, tipo_movimento, imponibile, data_movimento, motivo,
              annulla_movimento_id)
             SELECT %s, 'FORZATURA', -100, script.fn_data_operativa(), 'importo sbagliato', %s$q$,
         (SELECT titolo_iva_id FROM tmp_forz2), (SELECT id FROM tmp_forz2)),
  'P0001', NULL,
  '4) importo diverso dall''opposto rifiutato');

-- ============================================================
-- 5) ⭐ Collegamento a un movimento di un ALTRO titolo: rifiutato.
--    E' il difetto peggiore, perche' non solleverebbe niente da solo:
--    l'accumulatore somma PER TITOLO e del collegamento non sa nulla, quindi
--    troverebbe entrambi i totali «coerenti».
-- ============================================================
SELECT throws_ok(
  format($q$INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti
             (titolo_iva_id, tipo_movimento, imponibile, data_movimento, motivo,
              annulla_movimento_id)
             SELECT %s, 'FORZATURA', -400, script.fn_data_operativa(), 'titolo sbagliato', %s$q$,
         (SELECT id FROM tmp_titoli WHERE n = 1), (SELECT id FROM tmp_forz2)),
  'P0001', NULL,
  '5) collegamento a un movimento di un altro titolo rifiutato');

-- ============================================================
-- 6) Auto-annullo: lo ferma il CHECK, che qui e' la sede giusta perche'
--    confronta due colonne della stessa riga.
--    ⚠️ Non si puo' costruire con una INSERT (l'id non esiste ancora): si
--    verifica che il vincolo ci sia e che sia quello.
-- ============================================================
SELECT ok(
  (SELECT pg_get_constraintdef(oid) LIKE '%annulla_movimento_id <> id%'
     FROM pg_constraint
    WHERE conrelid = 'anagrafiche.soggetti_titoli_iva_movimenti'::regclass
      AND conname = 'chk_stiva_movimenti_auto_annullo'),
  '6) il CHECK anti auto-annullo esiste e confronta annulla_movimento_id con id');

-- ============================================================
-- 7) ⭐ Annullo di un annullo: rifiutato (decisione B-2).
--    La riga creata al n. 1 E' un annullo: annullarla vorrebbe dire
--    ripristinare, e Tid ha deciso che non si fa — se la forzatura serve
--    ancora se ne scrive una nuova, col suo motivo.
-- ============================================================
SELECT throws_ok(
  format($q$SELECT anagrafiche.fn_annulla_movimento_titolo_iva(%s, 'ripristino')$q$,
         (SELECT id FROM tmp_annullo)),
  'P0001', NULL,
  '7) annullo di un annullo rifiutato');

-- ============================================================
-- 8) e 9) ⭐ Il registro e' «solo aggiunte» (decisione B-1).
--    ⛔ Il 9) e' il piu' importante dei due: un UPDATE riscriverebbe la storia
--    in silenzio, perche' l'accumulatore ricalcola e il totale resterebbe
--    «giusto». Un DELETE almeno lascia un buco.
-- ============================================================
SELECT throws_ok(
  format($q$DELETE FROM anagrafiche.soggetti_titoli_iva_movimenti WHERE id = %s$q$,
         (SELECT id FROM tmp_forz2)),
  'P0001', NULL,
  '8) DELETE sul registro rifiutato');

SELECT throws_ok(
  format($q$UPDATE anagrafiche.soggetti_titoli_iva_movimenti
              SET imponibile = 1 WHERE id = %s$q$,
         (SELECT id FROM tmp_forz2)),
  'P0001', NULL,
  '9) UPDATE sul registro rifiutato');

-- ============================================================
-- 10) ⭐ Il motivo arriva sulla superficie, e coincide con il rifiuto.
--     E' il presidio della decisione B-3: la vista spegne il pulsante col
--     motivo, la madre rifiuta — e leggono la STESSA regola.
--     · sulla forzatura gia' annullata (n. 1): il motivo c'e';
--     · su quella ancora viva (tmp_forz2): il motivo e' NULL, cioe' ammesso.
-- ============================================================
SELECT ok(
  (SELECT v.annullo_blocco_codice = 'GIA_ANNULLATO'
      AND v.annullo_blocco_reason_key IS NOT NULL
      AND v.is_annullato IS TRUE
     FROM anagrafiche.vw_stiva_movimenti_dettaglio v
    WHERE v.id = (SELECT id FROM tmp_forz))
  AND (SELECT v.annullo_blocco_codice IS NULL AND v.is_annullato IS FALSE
         FROM anagrafiche.vw_stiva_movimenti_dettaglio v
        WHERE v.id = (SELECT id FROM tmp_forz2)),
  '10) la vista espone il motivo di blocco e coincide con cio'' che la madre rifiuta');

-- ============================================================
-- 11) ⭐⭐ LA PROVA DEL `SECURITY DEFINER`.
--     script.fn_check_annullo_movimento_titolo_iva deve poter leggere la riga
--     annullata ANCHE quando chi opera non la vede: la FK, che la RLS la
--     scavalca sempre, accetterebbe comunque il riferimento — e una check
--     `INVOKER` lo tratterebbe come «non esiste». I due divergerebbero in
--     silenzio.
--
-- ⭐ NON servono due emittenti: basta cambiare CHI GUARDA. La riga si e'
--    costruita sopra, dal perimetro che la puo' scrivere; qui si sposta solo il
--    contesto.
--
-- ⛔ E NON si svuota `app.current_user_id`: fino al 2026-10-04
--    script.fn_check_user_emittente_scope(NULL, ...) rispondeva **TRUE**, cioe'
--    fail-OPEN — svuotare il GUC rendeva visibile tutto e il test passava per
--    il motivo sbagliato. Dal 2026-10-04 risponde FALSE (Q-1 di
--    brief-db-esclusioni-implicite), ma il caso che conta resta «un utente
--    VERO senza whitelist»: e' quello che il test costruisce. Serve un id CONCRETO senza whitelist, che risponde
--    FALSE. Si calcola invece di scriverlo a mano, cosi' non collide quando gli
--    utenti crescono.
--
-- ⚠️ La prima meta' («chi opera non la vede») non e' un'asserzione ma la
--    PRECONDIZIONE: senza di essa la seconda non proverebbe niente, perche' la
--    riga potrebbe essere visibile a tutti. Se non regge, si SALTA dichiarando
--    il motivo — non si asserisce lo stesso.
-- ⚠️ Ultimo test del file di proposito: da qui in poi il contesto e' cieco.
-- ============================================================
SELECT set_config('app.current_user_id',
                  (SELECT (COALESCE(max(auth_user_id), 0) + 1000)::text
                     FROM config.user_emittenti_fiscali),
                  true);

-- ⛔ LA PRECONDIZIONE SI MISURA, NON SI SUPPONE. Se la riga si vede lo stesso,
--    la RLS a questo ruolo NON si applica — owner (relforcerowsecurity = false)
--    o BYPASSRLS — e il SOGGETTO di questo test non esiste: asserire sarebbe
--    verde per costruzione, e sarebbe la forma peggiore di verde.
--    ⚠️ Nel giro vero (scripts/testpgtap.sh, ruolo zeroerp_app) questo ramo NON
--    scatta: li' la RLS c'e', e l'asserzione si esegue davvero.
SELECT CASE
  WHEN (SELECT count(*) FROM anagrafiche.soggetti_titoli_iva_movimenti m
         WHERE m.id = (SELECT id FROM tmp_forz)) > 0
  THEN skip('RLS non applicata a questo ruolo (owner o BYPASSRLS): il perimetro '
            'cieco non e'' costruibile, e il SECURITY DEFINER non e'' esercitato. '
            'Va rilanciato da scripts/testpgtap.sh come zeroerp_app.', 1)
  ELSE ok(
    -- La riga NON si vede (lo ha appena stabilito il CASE) e la check la vede
    -- lo stesso, e dice la verita' su di essa. Con INVOKER direbbe
    -- 'MOVIMENTO_NON_TROVATO'.
    (script.fn_check_annullo_movimento_titolo_iva((SELECT id FROM tmp_forz))
       -> 0 ->> 'reason') = 'GIA_ANNULLATO',
    '11) la check vede la riga anche da un perimetro cieco (SECURITY DEFINER)')
END;

SELECT * FROM finish();
ROLLBACK;
