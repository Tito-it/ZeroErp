-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): i DDT in bozza da dbops.fn_pgtap_crea_ddt_senza_ordine (DRAFT), gli ordini in bozza e confermato da dbops.fn_pgtap_crea_ordine_con_righe; restano a mano i sei DELETE (sono il caso).
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine (test 5 e 6); restano scritti a mano i DDT in bozza senza ordine e gli ordini in bozza/confermato (sono il caso: righe che si tolgono o no), e i DELETE.
-- pgTAP test per Zero ERP
--
-- Test: le righe di DDT e ordine si tolgono FINCHE' il documento e' in
--   bozza — e il documento stesso si elimina alle stesse condizioni.
--   changeSet 20260826-20 / -21 / -22; dal 2026-09-22 la regola di stato sulle
--   righe vive nel BB vendite.trgfn_doc_righe_lock_fuori_bozza (20260922-02…-05).
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
-- ⭐ IL DOCUMENTO FUORI BOZZA SI FABBRICA NEL VERSO VERO (rev 2026-09-22).
--   Fino al 21-09 il DDT «fuori bozza» NASCEVA emesso e riceveva la riga
--   dopo: tutti i gate di emissione sono BEFORE UPDATE e nascere in EMESSO
--   li saltava. Dal 20260922-03 quella scorciatoia e' esattamente cio' che
--   il building block vendite.trgfn_doc_righe_lock_fuori_bozza chiude: una
--   riga non entra in un documento fuori bozza. Il DDT emesso si costruisce
--   quindi da un ordine, col builder dbops.fn_pgtap_crea_ddt_da_ordine (rev
--   2026-10-25). ⚠️ E il DELETE della sua riga (test
--   5) e' rifiutato dal BB in fascia _a05_, PRIMA che il traduttore dei
--   legami veda il fulfillment: e' il verdetto giusto («il documento e'
--   chiuso» va detto per primo), ed e' per questo che il ramo 1 e' uscito da
--   trgfn_dlt_block_ordrig_ddtrig (20260922-05).
--
-- ⚠️ LE FIXTURE SI COSTRUISCONO COI BUILDER (rev 2026-09-22): fino a quel
--   giorno il file pescava billing account, soggetto e articolo dai dati
--   esistenti — su un database da zero anagrafiche.* e' vuoto, e il file
--   era in baseline-rossi-ci come ERRORE_FIXTURE. Cliente e articolo li
--   fabbricano dbops.fn_pgtap_crea_cliente_ba / fn_pgtap_crea_articolo; i
--   documenti dbops.fn_pgtap_crea_ddt_senza_ordine, fn_pgtap_crea_ddt_da_ordine
--   e fn_pgtap_crea_ordine_con_righe (rev 2026-10-25, giro D-4).
--
-- ⭐ IL PERIMETRO E' NELLE CHIAVI ESTERNE, non in questo trigger: il
--   test 9 lo presidia. Se un domani qualcuno degradasse
--   fk_ordini_r_ful_v_ddt_riga da RESTRICT a SET NULL o CASCADE, il
--   guard continuerebbe a dire la sua frase e la protezione vera
--   sparirebbe in silenzio.
--
-- Indice test (1..10)
--   1) Le quattro funzioni (coppia di guard, BB delle righe, lettore) esistono
--   2) I quattro codici sono a catalogo con la loro classe (E_RIGA_DOC_NON_BOZZA dal 22-09)
--   3) 🔴 DDT in bozza: la riga SI TOGLIE            <-- il ramo che mancava
--   4) 🔴 DDT in bozza: la testata si elimina (cascade sulle righe)
--   5) DDT fuori bozza: la riga NON si toglie, e il motivo lo dice (E_RIGA_DOC_NON_BOZZA, dal BB)
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
-- testate e righe hanno RLS (dal 22-09 anche le righe, letto dal catalogo), ed
-- e' il motivo per cui script.fn_get_stato_testata_documento e' SECURITY
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
            ('vendite','trgfn_doc_righe_lock_fuori_bozza'),
            ('script','fn_get_stato_testata_documento'))),
  4,
  '1) Le quattro funzioni (coppia di guard, BB delle righe, lettore) esistono');

-- Un codice sollevato ma non a catalogo produce «MESSAGGIO NON DEFINITO»
-- all'operatore: il presidio sta qui perche' e' un silenzio, non un errore.
SELECT is(
  (SELECT count(*)::int FROM config.codici_errore c
    WHERE c.codice IN ('E_RIGA_DOC_NON_BOZZA','E_DELETE_DOC_NON_BOZZA',
                       'E_DELETE_RIGA_DOC_REFERENZIATA','E_DOC_TIPO_NON_GESTITO')
      AND c.obsoleto_dal IS NULL
      AND c.classe = CASE WHEN c.codice = 'E_DOC_TIPO_NON_GESTITO'
                          THEN 'TECNICO' ELSE 'CONFLITTO_STATO' END),
  4,
  '2) I quattro codici sono a catalogo e vivi, ognuno con la classe giusta');

-- ============================================================
-- Fixture — COSTRUITE
-- ============================================================
CREATE TEMP TABLE tmp_fix(chiave text PRIMARY KEY, id bigint);
CREATE TEMP TABLE tmp_esito(caso text PRIMARY KEY, sqlstate text, messaggio text, righe int);

-- Il mondo si COSTRUISCE: cliente e articolo dai builder, il catalogo per
-- codice_interno. ⚠️ Ordine obbligato: prima il contesto (in testa), poi il
-- cliente — il legame BA -> emittente lo scrive il trigger z90 verso
-- l'emittente di chi agisce.
CREATE TEMP TABLE tmp_cli_dr AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgtap_delete_righe_bozza');

CREATE TEMP TABLE tmp_refs_dr AS
SELECT
  c.billing_account_id,
  -- ⚠️ NON composito (un kit farebbe nascere figlie in CASCADE) e NON gestito a magazzino.
  dbops.fn_pgtap_crea_articolo('PGT-DR-ART', false)                                                  AS articolo_id
FROM tmp_cli_dr c;

DO $fix$
DECLARE
  r       RECORD;
  v_id    bigint;
  v_riga  bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_dr;

  -- ── DDT senza ordine in bozza, con una riga (test 3 e 4), dal builder ──
  SELECT b.ddt_id, b.ddt_riga_id INTO v_id, v_riga
    FROM dbops.fn_pgtap_crea_ddt_senza_ordine('pgtap_delete_righe_bozza', 'DRAFT', r.billing_account_id,
           p_quantita => 1, p_articolo_id => r.articolo_id) b;
  INSERT INTO tmp_fix VALUES ('ddt_bozza', v_id), ('ddt_bozza_riga', v_riga);

  -- Secondo DDT in bozza, per provare il cascade sulla testata senza
  -- consumare quello del test 3.
  SELECT b.ddt_id INTO v_id
    FROM dbops.fn_pgtap_crea_ddt_senza_ordine('pgtap_delete_righe_bozza', 'DRAFT', r.billing_account_id,
           p_quantita => 1, p_articolo_id => r.articolo_id) b;
  INSERT INTO tmp_fix VALUES ('ddt_bozza2', v_id);

  -- ── DDT EMESSO nel verso vero (test 5 e 6): dal builder, ordine del
  --    cliente del file con una riga di 2 a 10, bolla emessa per la matrice ─
  SELECT b.ddt_id, b.ddt_riga_id INTO v_id, v_riga
    FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgtap_delete_righe_bozza', 'EMESSO',
           p_billing_account_id => r.billing_account_id,
           p_articolo_id        => r.articolo_id,
           p_quantita           => 2,
           p_prezzo             => 10) b;
  INSERT INTO tmp_fix VALUES ('ddt_emesso', v_id), ('ddt_emesso_riga', v_riga);

  -- ── Ordine in bozza e ordine confermato, una riga di 1 a 10 (test 7 e 8),
  --    dal builder: la conferma passa per dbops.fn_pgtap_porta_a_stato ──
  SELECT o.ordine_id, o.ordine_riga_id INTO v_id, v_riga
    FROM dbops.fn_pgtap_crea_ordine_con_righe('pgtap_delete_righe_bozza', 'DRAFT', r.billing_account_id,
           p_quantita => 1, p_prezzo => 10, p_articolo_id => r.articolo_id) o;
  INSERT INTO tmp_fix VALUES ('ord_bozza', v_id), ('ord_bozza_riga', v_riga);

  SELECT o.ordine_id, o.ordine_riga_id INTO v_id, v_riga
    FROM dbops.fn_pgtap_crea_ordine_con_righe('pgtap_delete_righe_bozza', 'CONFERMATO', r.billing_account_id,
           p_quantita => 1, p_prezzo => 10, p_articolo_id => r.articolo_id) o;
  INSERT INTO tmp_fix VALUES ('ord_conf', v_id), ('ord_conf_riga', v_riga);
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
    '5) DDT fuori bozza: la riga NON si toglie, ed e E_RIGA_DOC_NON_BOZZA (il BB, fascia _a05_) a dirlo')
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
