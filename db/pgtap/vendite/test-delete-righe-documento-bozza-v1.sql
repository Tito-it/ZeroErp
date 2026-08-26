-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le righe di DDT e ordine si tolgono FINCHE' il documento e' in
--   bozza — e il documento stesso si elimina alle stesse condizioni.
--   changeSet 20260826-20 / -21 / -22.
-- ------------------------------------------------------------
-- COSA PRESIDIA, e perche' non esisteva
--   Fino al 2026-08-26 vendite.trgfn_dlt_block_ordrig_ddtrig era un
--   DIVIETO SENZA USCITA: tutti i suoi rami sollevavano e il `RETURN OLD`
--   in fondo era irraggiungibile. Nessun DELETE poteva riuscire, su
--   nessuna delle due tabelle — e nemmeno la cancellazione dell'INTERO
--   documento, che ci passa per ON DELETE CASCADE.
--
-- 🔴 E' sopravvissuto per una ragione sola: NESSUN TEST ESEGUIVA UN
--   DELETE VERO su queste tabelle. Misurato il 2026-08-26: zero file in
--   db/pgtap/ contenevano «DELETE FROM vendite.ddt_righe» o
--   «... ordini_righe», e zero nominavano il guard o i suoi codici. Il
--   ramo cieco non era coperto male: non era coperto affatto.
--
--   ⚠️ Il corollario e' che questo file va letto al contrario: i test che
--   contano non sono quelli che verificano un RIFIUTO — quelli passavano
--   anche prima, per il motivo sbagliato — ma il 3, il 4 e il 7, che
--   verificano che qualcosa RIESCA.
--
-- ⚠️ LE FIXTURE SI COSTRUISCONO, NON SI SCELGONO. Un documento in bozza
--   con una riga si fabbrica in poche istruzioni, quindi non c'e' nessuna
--   ragione per andarlo a cercare fra i dati esistenti: un file che
--   sceglie passa a vuoto su un DB ricostruito da zero, cioe' in CI.
--
-- ⭐ IL DOCUMENTO FUORI BOZZA NASCE FUORI BOZZA, e non ci arriva per
--   transizione. Tutti i gate di emissione (causale, indirizzi,
--   approvazione, transizione) sono BEFORE **UPDATE**: nascere in EMESSO
--   li salta tutti, senza disabilitare niente. Ed e' corretto per questo
--   file — il soggetto e' il guard di CANCELLAZIONE, non il gate di
--   emissione. Provato il 2026-08-26: passando per la transizione la
--   fixture moriva su tre precondizioni diverse in fila (causale, prezzo
--   risolvibile, indirizzo CON), e ogni volta il test dichiarava «il
--   guard non ha bloccato» mentre il documento era rimasto in bozza.
--
-- ⭐ IL PERIMETRO E' NELLE CHIAVI ESTERNE, non in questo trigger: il
--   test 9 lo presidia. Se un domani qualcuno degradasse
--   fk_ordini_r_ful_v_ddt_riga da RESTRICT a SET NULL o CASCADE, il
--   guard continuerebbe a dire la sua frase e la protezione vera
--   sparirebbe in silenzio.
--
-- Indice test (1..10)
--   1) Le due trigger function esistono
--   2) I quattro codici nuovi sono a catalogo con la loro classe
--   3) 🔴 DDT in bozza: la riga SI TOGLIE            <-- il ramo che mancava
--   4) 🔴 DDT in bozza: la testata si elimina (cascade sulle righe)
--   5) DDT fuori bozza: la riga NON si toglie, e il motivo lo dice
--   6) DDT fuori bozza: la testata NON si elimina
--   7) 🔴 Ordine in bozza: la riga SI TOGLIE
--   8) Ordine fuori bozza: la riga NON si toglie
--   9) La protezione del fulfillment e ancora nella FK (RESTRICT)
--  10) I due guard di testata sono montati su ddt e su ordini
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. ⚠️ E qui NON e' una formalita':
-- vendite.ddt e vendite.ordini hanno RLS e le loro righe no — e' esattamente
-- l'asimmetria per cui script.fn_get_stato_testata_documento e' SECURITY
-- DEFINER. Senza contesto, il file non eserciterebbe quel pezzo.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

-- ============================================================
-- 1-2) Strutturali (girano sempre)
-- ============================================================

SELECT is(
  (SELECT count(*)::int
     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE (n.nspname, p.proname) IN (
            ('vendite','trgfn_dlt_block_ordrig_ddtrig'),
            ('vendite','trgfn_doc_guard_delete_solo_bozza'),
            ('script','fn_get_stato_testata_documento'))),
  3,
  '1) Le tre funzioni della coppia di guard esistono');

-- Un codice sollevato ma non a catalogo produce «MESSAGGIO NON DEFINITO»
-- all'operatore: il presidio sta qui perche' e' un silenzio, non un errore.
SELECT is(
  (SELECT count(*)::int FROM config.codici_errore c
    WHERE c.codice IN ('E_DELETE_RIGA_DOC_NON_BOZZA','E_DELETE_DOC_NON_BOZZA',
                       'E_DELETE_RIGA_DOC_REFERENZIATA','E_DOC_TIPO_NON_GESTITO')
      AND c.classe = CASE WHEN c.codice = 'E_DOC_TIPO_NON_GESTITO'
                          THEN 'TECNICO' ELSE 'CONFLITTO_STATO' END),
  4,
  '2) I quattro codici nuovi sono a catalogo, ognuno con la classe giusta');

-- ============================================================
-- Fixture — COSTRUITE
-- ============================================================
CREATE TEMP TABLE tmp_fix(chiave text PRIMARY KEY, id bigint);
CREATE TEMP TABLE tmp_esito(caso text PRIMARY KEY, sqlstate text, messaggio text, righe int);

DO $fix$
DECLARE
  v_ef      anagrafiche.emittenti_fiscali.id%TYPE;
  v_ba      anagrafiche.billing_account.id%TYPE;
  v_ut      anagrafiche.billing_account.utility_id%TYPE;
  v_sr      anagrafiche.soggetti_ruoli.id%TYPE;
  v_val     config.valute.id%TYPE;
  v_art     catalogo.articoli.id%TYPE;
  v_ddraft  config.stati_doc_ddt.id%TYPE;
  v_demesso config.stati_doc_ddt.id%TYPE;
  v_odraft  config.stati_doc_ordini.id%TYPE;
  v_oconf   config.stati_doc_ordini.id%TYPE;
  v_id      bigint;
BEGIN
  -- ⚠️ L'EMITTENTE LO DETTA L'OPERATORE, non il billing account:
  --   script.trgfn_guard_emittente_scope rifiuta un documento il cui emittente
  --   non sia nella whitelist di chi scrive.
  v_ef := script.fn_pgtap_emittente_operatore();

  SELECT ba.id, ba.utility_id INTO v_ba, v_ut
    FROM anagrafiche.billing_account ba
   WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
   ORDER BY ba.id LIMIT 1;

  SELECT id INTO v_sr  FROM anagrafiche.soggetti_ruoli ORDER BY id LIMIT 1;
  SELECT id INTO v_val FROM config.valute ORDER BY id LIMIT 1;

  -- ⚠️ Articolo NON composito: un kit farebbe nascere righe componenti, cioe'
  --   figlie in CASCADE, e il caso in esame e' la riga NUDA.
  SELECT a.id INTO v_art FROM catalogo.articoli a
   WHERE a.attivo IS TRUE AND COALESCE(a.is_composito, false) IS FALSE
   ORDER BY a.id LIMIT 1;

  SELECT id INTO v_ddraft  FROM config.stati_doc_ddt    WHERE codice_interno='DRAFT'      AND attivo LIMIT 1;
  SELECT id INTO v_demesso FROM config.stati_doc_ddt    WHERE codice_interno='EMESSO'     AND attivo LIMIT 1;
  SELECT id INTO v_odraft  FROM config.stati_doc_ordini WHERE codice_interno='DRAFT'      AND attivo LIMIT 1;
  SELECT id INTO v_oconf   FROM config.stati_doc_ordini WHERE codice_interno='CONFERMATO' AND attivo LIMIT 1;

  IF v_ef IS NULL OR v_ba IS NULL OR v_art IS NULL THEN
    -- ⚠️ Il motivo si DICE: uno skip inspiegato somiglia troppo a un verde.
    RAISE WARNING 'fixture delete-righe non costruibile: emittente/BA/articolo mancanti';
    RETURN;
  END IF;

  -- ── DDT in bozza (test 3 e 4) ───────────────────────────────────
  INSERT INTO vendite.ddt (data, stato_doc_ddt_id, destinatario_soggetto_ruolo_id,
                           billing_account_id, utility_id, valuta_id,
                           emittente_fiscale_id, storicizza, meta)
  VALUES (CURRENT_DATE, v_ddraft, v_sr, v_ba, v_ut, v_val, v_ef, false,
          jsonb_build_object('test_scope','pgtap_delete_righe_bozza'))
  RETURNING id INTO v_id;
  INSERT INTO tmp_fix VALUES ('ddt_bozza', v_id);

  INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
                                 qta_operativa, quantita, storicizza, meta)
  VALUES (v_id, 1, v_art, 'riga togliibile', 1.000000, 1.000000, false,
          jsonb_build_object('test_scope','pgtap_delete_righe_bozza'))
  RETURNING id INTO v_id;
  INSERT INTO tmp_fix VALUES ('ddt_bozza_riga', v_id);

  -- Secondo DDT in bozza, per provare il cascade sulla testata senza
  -- consumare quello dei test 3.
  INSERT INTO vendite.ddt (data, stato_doc_ddt_id, destinatario_soggetto_ruolo_id,
                           billing_account_id, utility_id, valuta_id,
                           emittente_fiscale_id, storicizza, meta)
  VALUES (CURRENT_DATE, v_ddraft, v_sr, v_ba, v_ut, v_val, v_ef, false,
          jsonb_build_object('test_scope','pgtap_delete_righe_bozza'))
  RETURNING id INTO v_id;
  INSERT INTO tmp_fix VALUES ('ddt_bozza2', v_id);
  INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
                                 qta_operativa, quantita, storicizza, meta)
  VALUES (v_id, 1, v_art, 'riga che muore col padre', 1.000000, 1.000000, false,
          jsonb_build_object('test_scope','pgtap_delete_righe_bozza'));

  -- ── DDT che NASCE fuori bozza (test 5 e 6) ──────────────────────
  INSERT INTO vendite.ddt (data, stato_doc_ddt_id, destinatario_soggetto_ruolo_id,
                           billing_account_id, utility_id, valuta_id,
                           emittente_fiscale_id, storicizza, meta)
  VALUES (CURRENT_DATE, v_demesso, v_sr, v_ba, v_ut, v_val, v_ef, false,
          jsonb_build_object('test_scope','pgtap_delete_righe_bozza'))
  RETURNING id INTO v_id;
  INSERT INTO tmp_fix VALUES ('ddt_emesso', v_id);
  INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
                                 qta_operativa, quantita, storicizza, meta)
  VALUES (v_id, 1, v_art, 'riga intoccabile', 1.000000, 1.000000, false,
          jsonb_build_object('test_scope','pgtap_delete_righe_bozza'))
  RETURNING id INTO v_id;
  INSERT INTO tmp_fix VALUES ('ddt_emesso_riga', v_id);

  -- ── Ordine in bozza e ordine confermato (test 7 e 8) ────────────
  INSERT INTO vendite.ordini (data, stato_doc_ordine_id, soggetto_ruolo_id,
                              billing_account_id, utility_id, valuta_id,
                              emittente_fiscale_id, storicizza, meta)
  VALUES (CURRENT_DATE, v_odraft, v_sr, v_ba, v_ut, v_val, v_ef, false,
          jsonb_build_object('test_scope','pgtap_delete_righe_bozza'))
  RETURNING id INTO v_id;
  INSERT INTO tmp_fix VALUES ('ord_bozza', v_id);
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
                                    qta_operativa, quantita, prezzo_unitario, storicizza, meta)
  VALUES (v_id, 1, v_art, 'riga ordine togliibile', 1.000000, 1.000000, 10.000000, false,
          jsonb_build_object('test_scope','pgtap_delete_righe_bozza'))
  RETURNING id INTO v_id;
  INSERT INTO tmp_fix VALUES ('ord_bozza_riga', v_id);

  INSERT INTO vendite.ordini (data, stato_doc_ordine_id, soggetto_ruolo_id,
                              billing_account_id, utility_id, valuta_id,
                              emittente_fiscale_id, storicizza, meta)
  VALUES (CURRENT_DATE, v_oconf, v_sr, v_ba, v_ut, v_val, v_ef, false,
          jsonb_build_object('test_scope','pgtap_delete_righe_bozza'))
  RETURNING id INTO v_id;
  INSERT INTO tmp_fix VALUES ('ord_conf', v_id);
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
                                    qta_operativa, quantita, prezzo_unitario, storicizza, meta)
  VALUES (v_id, 1, v_art, 'riga ordine intoccabile', 1.000000, 1.000000, 10.000000, false,
          jsonb_build_object('test_scope','pgtap_delete_righe_bozza'))
  RETURNING id INTO v_id;
  INSERT INTO tmp_fix VALUES ('ord_conf_riga', v_id);
END $fix$;

-- ============================================================
-- Esecuzione dei sei DELETE, con l'esito catturato
-- ============================================================
-- ⚠️ Catturato e non `throws_ok`: cosi' si asserisce il CODICE che e' uscito e
--   non «un errore qualunque». Un throws_ok con solo P0001 passerebbe anche se
--   a sollevare fosse un guard diverso — o il crash del guard stesso.
DO $run$
DECLARE
  r record; v_n int;
BEGIN
  FOR r IN SELECT * FROM (VALUES
      ('3_ddt_bozza_riga',   'vendite.ddt_righe',    'ddt_bozza_riga'),
      ('4_ddt_bozza_testata','vendite.ddt',          'ddt_bozza2'),
      ('5_ddt_emesso_riga',  'vendite.ddt_righe',    'ddt_emesso_riga'),
      ('6_ddt_emesso_testata','vendite.ddt',         'ddt_emesso'),
      ('7_ord_bozza_riga',   'vendite.ordini_righe', 'ord_bozza_riga'),
      ('8_ord_conf_riga',    'vendite.ordini_righe', 'ord_conf_riga')
    ) AS t(caso, tabella, chiave)
  LOOP
    IF NOT EXISTS (SELECT 1 FROM tmp_fix WHERE chiave = r.chiave) THEN
      CONTINUE;   -- fixture non costruita: il test si skippa piu' sotto
    END IF;
    BEGIN
      EXECUTE format('DELETE FROM %s WHERE id = %s',
                     r.tabella, (SELECT id FROM tmp_fix WHERE chiave = r.chiave));
      GET DIAGNOSTICS v_n = ROW_COUNT;
      INSERT INTO tmp_esito VALUES (r.caso, NULL, NULL, v_n);
    EXCEPTION WHEN OTHERS THEN
      INSERT INTO tmp_esito VALUES (r.caso, SQLSTATE, SQLERRM, NULL);
    END;
  END LOOP;
END $run$;

-- ============================================================
-- 3-4) 🔴 I DUE TEST CHE VALGONO: qualcosa deve RIUSCIRE
-- ============================================================

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso='3_ddt_bozza_riga')
    THEN skip('fixture DDT in bozza non costruita', 1)
  ELSE is(
    (SELECT COALESCE(righe, -1) || COALESCE(' / ' || sqlstate || ' ' || messaggio, '')
       FROM tmp_esito WHERE caso='3_ddt_bozza_riga'),
    '1',
    '3) DDT in bozza: la riga si toglie (il ramo che fino al 2026-08-26 non esisteva)')
END;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso='4_ddt_bozza_testata')
    THEN skip('fixture DDT in bozza (2) non costruita', 1)
  ELSE is(
    (SELECT COALESCE(righe, -1) || COALESCE(' / ' || sqlstate || ' ' || messaggio, '')
       FROM tmp_esito WHERE caso='4_ddt_bozza_testata'),
    '1',
    '4) DDT in bozza: la testata si elimina, e le righe la seguono per cascade')
END;

-- ============================================================
-- 5-6) Il rifiuto fuori bozza, e il motivo che lo dice
-- ============================================================
-- ⚠️ Si asserisce SQLSTATE **e** la frase: con il solo P0001 passerebbe anche
--   un guard diverso, e con la sola frase passerebbe un errore tecnico che
--   contiene per caso le stesse parole.

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso='5_ddt_emesso_riga')
    THEN skip('fixture DDT emesso non costruita', 1)
  ELSE ok(
    (SELECT sqlstate = 'P0001' AND messaggio LIKE '%non e'' piu'' in bozza%'
                              AND messaggio LIKE '%le sue righe%'
       FROM tmp_esito WHERE caso='5_ddt_emesso_riga'),
    '5) DDT fuori bozza: la riga NON si toglie, ed e E_DELETE_RIGA_DOC_NON_BOZZA a dirlo')
END;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso='6_ddt_emesso_testata')
    THEN skip('fixture DDT emesso non costruita', 1)
  ELSE ok(
    (SELECT sqlstate = 'P0001' AND messaggio LIKE '%non e'' piu'' in bozza%'
                              AND messaggio LIKE '%si puo'' eliminare%'
       FROM tmp_esito WHERE caso='6_ddt_emesso_testata'),
    '6) DDT fuori bozza: la testata NON si elimina (e il cascade non e una porta di servizio)')
END;

-- ============================================================
-- 7-8) L'altra tabella: stessa funzione, stesso verdetto
-- ============================================================
-- ⚠️ Non e' un doppione del 3 e del 5: la funzione dispaccia su
--   TG_TABLE_NAME e i due rami leggono testate diverse. Provarne uno solo
--   lascerebbe l'altro scoperto, ed e' esattamente com'e' andata finora.

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso='7_ord_bozza_riga')
    THEN skip('fixture ordine in bozza non costruita', 1)
  ELSE is(
    (SELECT COALESCE(righe, -1) || COALESCE(' / ' || sqlstate || ' ' || messaggio, '')
       FROM tmp_esito WHERE caso='7_ord_bozza_riga'),
    '1',
    '7) Ordine in bozza: la riga si toglie')
END;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso='8_ord_conf_riga')
    THEN skip('fixture ordine confermato non costruita', 1)
  ELSE ok(
    (SELECT sqlstate = 'P0001' AND messaggio LIKE '%non e'' piu'' in bozza%'
       FROM tmp_esito WHERE caso='8_ord_conf_riga'),
    '8) Ordine fuori bozza: la riga NON si toglie')
END;

-- ============================================================
-- 9) ⭐ La protezione vera sta nelle FK, e va sorvegliata li'
-- ============================================================
-- Questo trigger TRADUCE il rifiuto in una frase; a rifiutare e' la chiave
-- esterna. Se qualcuno la degradasse a SET NULL o CASCADE, il guard
-- continuerebbe a dire la sua frase nei casi che vede e la protezione
-- sparirebbe per tutti gli altri percorsi, in silenzio.
SELECT is(
  (SELECT count(*)::int FROM pg_constraint c
    WHERE c.conname IN ('fk_ordini_r_ful_v_ddt_riga','fk_ordini_r_ful_v_ordine_riga')
      AND c.confdeltype = 'r'),
  2,
  '9) Le due FK del fulfillment sono ancora in ON DELETE RESTRICT');

-- ============================================================
-- 10) La coppia di guard e montata su ENTRAMBE le testate
-- ============================================================
-- ⚠️ Il guard di riga da solo e' aggirabile dal cascade: se uno dei due
--   trigger di testata sparisse, il file 5/6 resterebbe verde e il buco
--   tornerebbe. Qui si presidia il MONTAGGIO, non il comportamento.
SELECT is(
  (SELECT count(*)::int
     FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
    WHERE NOT t.tgisinternal
      AND p.proname = 'trgfn_doc_guard_delete_solo_bozza'
      AND t.tgrelid IN ('vendite.ddt'::regclass, 'vendite.ordini'::regclass)),
  2,
  '10) Il guard di testata e montato sia su vendite.ddt sia su vendite.ordini');

SELECT * FROM finish();

ROLLBACK;
