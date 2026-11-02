-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: LA CORREZIONE GUIDATA — pagamenti.fn_crea_distinta_correzione
--
-- Elenco test (plan 14):
--  1) Riferimenti minimi presenti
--  2) ⭐ Il `codice` lo assegna il TRIGGER sul registro: DIS-<sigla>-<anno>-<7 cifre> (rev 2026-09-15)
--  3) Una distinta NON registrata non si corregge
--  4) La correzione crea una riga per ogni riga POSTATA
--  5) ...e conta quelle saltate, invece di tacerle
--  6) L'esito e' dichiarato, non dedotto
--  7) QUADRATURA: la somma della correzione e' l'opposto dell'originale
--  8) ⭐ Le righe portano fattura e rata, ma stanno in DA_ABBINARE
--  9) ⭐ ...ed e' la decisione C-1: ad ABBINATA ci arriva una PERSONA, e
--     incontra il doppio tempo della capienza
-- 10) La testata nuova e' in BOZZA, MANUALE, sullo stesso centro
-- 11) Il legame col documento corretto e' scritto
-- 12) Correggere due volte la stessa distinta e' rifiutato
-- 13) ⭐ ...ma correggere LA CORREZIONE si puo': la catena resta leggibile
-- 14) ⭐ La correzione nasce sullo STESSO registro dell'originale, col progressivo successivo (rev 2026-09-15)
-- 15) Assert finale cleanup
--
-- Scopo:
--  - collaudare la madre di Q-7 (S6-4). ⭐ Il cuore sono i test 8 e 9: la
--    decisione C-1 e' stata CAMBIATA da una misura — nascere gia' ABBINATA
--    pretenderebbe `forzata = true` scritta dalla madre, cioe' forzare al
--    posto dell'operatore, perche' una riga di segno opposto su una rata
--    saldata dal movimento che si sta correggendo e' fuori capienza (con
--    residuo zero non c'e' spazio in nessuna direzione). In `DA_ABBINARE` la
--    riga non occupa spazio, il guard non la esamina, e il doppio tempo resta
--    dove D14-d l'ha messo: in mano a una persona;
--  - presidiare che «niente da correggere» resti un ESITO e non diventi un
--    errore, come `NULLA_DA_POSTARE`;
--  - e presidiare C-4 nei due versi (test 12 e 13): una correzione per
--    documento, ma la catena delle correzioni non si spezza.
--
-- Piano: brief-db-posting-e-abbinamento-rata.md
--        §2.3-quater S6-4 · Decisione: Q-7 (24/08), C-1…C-4 (28/08) · lotto 10
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_correzione_guidata'::text AS test_scope;

-- ⛔ IL MONDO SI COSTRUISCE (2026-09-23). Questo blocco pescava il billing
--   account «piu' recente» e poi ne DERIVAVA l'emittente con un `OR
--   is_default IS TRUE` di ripiego: su un database ricostruito non c'e' nessun
--   BA, tutto usciva NULL e la fattura non si scriveva — il file moriva sulla
--   RLS di `fatture_scadenze`, che e' il sintomo, non la causa.
-- ⚠️ E il ripiego sul DEFAULT era una trappola anche con i dati: un BA senza
--   legame rispondeva l'emittente di un'altra azienda (il difetto di D13).
--   Il BB costruisce la catena intera — mondo, coppia (emittente, utility),
--   registro, testata — e il legame lo verifica.
CREATE TEMP TABLE tmp_fattura_bb AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('correzione guidata');

CREATE TEMP TABLE tmp_refs AS
SELECT f.registro_id,
       f.billing_account_id, f.utility_id,
       f.tipo_doc_fiscale_id,
       f.valuta_id,
       f.emittente_soggetto_ruolo_id,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA' ORDER BY c.id LIMIT 1) AS centro_banca_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s WHERE s.codice_interno='ABBINATA') AS stato_abbinata_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s WHERE s.codice_interno='SOSPESA') AS stato_sospesa_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s WHERE s.codice_interno='BOZZA') AS stato_bozza_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s WHERE s.codice_interno='VALIDATA') AS stato_validata_id
  FROM tmp_fattura_bb f;

SELECT ok(
  (SELECT registro_id IS NOT NULL AND billing_account_id IS NOT NULL
      AND tipo_doc_fiscale_id IS NOT NULL AND valuta_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL AND centro_banca_id IS NOT NULL
      AND stato_abbinata_id IS NOT NULL AND stato_sospesa_id IS NOT NULL
      AND stato_bozza_id IS NOT NULL AND stato_validata_id IS NOT NULL
     FROM tmp_refs),
  '1) Riferimenti minimi presenti'
);

-- La fattura e la sua rata.
-- La testata l'ha gia' scritta il BB: qui si mette solo l'importo, che e' il
-- caso del test.
UPDATE vendite.fatture
   SET totale_a_pagare = 300.00,
       meta = meta || jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
 WHERE id = (SELECT fattura_id FROM tmp_fattura_bb);

CREATE TEMP TABLE tmp_fattura AS
SELECT fattura_id AS id FROM tmp_fattura_bb;

CREATE TEMP TABLE tmp_rata AS
WITH ins AS (
  INSERT INTO vendite.fatture_scadenze (fattura_id, numero_rata, data_scadenza, importo)
  SELECT (SELECT id FROM tmp_fattura), 1, script.fn_data_operativa() + 1, 100.00
  RETURNING id
) SELECT * FROM ins;

-- ============================================================
-- 2) ⭐ La testata si crea SENZA passare il codice
-- ============================================================
-- ⛔ La madre crea una testata propria e non puo' usare il get-or-create, la
--    cui chiave di riuso comprende l'operatore — le righe di correzione
--    finirebbero nella distinta di oggi. ⭐ Rev 2026-09-15 (brief
--    distinta-numerata-sul-registro, D5): il codice non lo mette piu' il DEFAULT
--    della colonna (VC_…) ma il trigger a10_gen_codice sul registro DISTINTA
--    dell'emittente in sessione: DIS-<sigla>-<anno>-<7 cifre>. La sigla ha
--    chk_emittenti_fiscali_codice_forma (^[A-Z0-9]{2,10}$).
CREATE TEMP TABLE tmp_originale AS
WITH ins AS (
  INSERT INTO pagamenti.vendite_contabili
      (centro_riscossione_id, data_contabile, data_registrazione, stato_id, origine, meta)
  SELECT r.centro_banca_id, script.fn_data_operativa(), script.fn_data_operativa(), r.stato_bozza_id, 'MANUALE',
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_refs r
  RETURNING id, codice
) SELECT * FROM ins;

SELECT matches(
  (SELECT codice FROM tmp_originale),
  '^DIS-[A-Z0-9]{2,10}-\d{4}-\d{7}$',
  '2) Il `codice` lo assegna il trigger sul registro: la testata si crea senza passarlo'
);

-- Due righe che diventeranno movimenti, e una sospesa che non lo diventa.
INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, importo, fattura_id,
     billing_account_id, scadenza_id, stato_id, meta)
SELECT (SELECT id FROM tmp_originale), v.rif, script.fn_data_operativa(), v.importo,
       (SELECT id FROM tmp_fattura), r.billing_account_id, (SELECT id FROM tmp_rata),
       r.stato_abbinata_id, jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r, (VALUES ('PGTAP_C1', 60.00), ('PGTAP_C2', 40.00)) AS v(rif, importo);

INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, importo, stato_id, motivo_sospeso, meta)
SELECT (SELECT id FROM tmp_originale), 'PGTAP_C3', script.fn_data_operativa(), 25.00,
       r.stato_sospesa_id, 'in attesa di conferma',
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r;

-- ============================================================
-- 3) Una distinta non registrata non si corregge
-- ============================================================
-- ⚠️ SQLSTATE dichiarato: P0001 e' l'errore di dominio. Senza, il test
--    accetterebbe anche il crash del guard.
SELECT throws_ok(
  format('SELECT * FROM pagamenti.fn_crea_distinta_correzione(%s)', (SELECT id FROM tmp_originale)),
  'P0001',
  NULL,
  '3) Una distinta NON registrata non si corregge: si modifica, ed e'' un altro gesto'
);

-- Si registra davvero.
UPDATE pagamenti.vendite_contabili c
   SET stato_id = (SELECT stato_validata_id FROM tmp_refs)
 WHERE c.id = (SELECT id FROM tmp_originale);

CREATE TEMP TABLE tmp_posting AS
SELECT * FROM pagamenti.fn_posta_contabile((SELECT id FROM tmp_originale));

-- ============================================================
-- La correzione — il verbo in un'istruzione SEPARATA
-- ============================================================
-- ⚠️ La snapshot di statement legge PRIMA delle scritture: un'asserzione nella
--    stessa istruzione accuserebbe la funzione invece del test.
CREATE TEMP TABLE tmp_correzione AS
SELECT * FROM pagamenti.fn_crea_distinta_correzione(
    (SELECT id FROM tmp_originale), script.fn_data_operativa(), 'importo digitato male');

SELECT is((SELECT righe_create FROM tmp_correzione), 2,
  '4) Una riga di correzione per ogni riga POSTATA');

SELECT is((SELECT righe_saltate FROM tmp_correzione), 1,
  '5) ...e le righe non postate si contano, invece di sparire in silenzio');

SELECT is((SELECT esito FROM tmp_correzione), 'CREATA',
  '6) L''esito e'' dichiarato, non dedotto dalla presenza della distinta');

SELECT is(
  (SELECT sum(r.importo) FROM pagamenti.vendite_contabili_righe r
    WHERE r.contabile_id = (SELECT contabile_id FROM tmp_correzione)),
  -100.00::numeric,
  '7) QUADRATURA: la somma della correzione e'' l''opposto di cio'' che era stato registrato'
);

-- ============================================================
-- 8-9) ⭐ Il cuore: precompilate ma NON abbinate
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM pagamenti.vendite_contabili_righe r
     JOIN pagamenti.vendite_contabili_righe_stati s ON s.id = r.stato_id
    WHERE r.contabile_id = (SELECT contabile_id FROM tmp_correzione)
      AND r.fattura_id = (SELECT id FROM tmp_fattura)
      AND r.scadenza_id = (SELECT id FROM tmp_rata)
      AND s.codice_interno = 'DA_ABBINARE'),
  2,
  '8) Le righe portano fattura e rata GIA'' compilate, ma stanno in DA_ABBINARE'
);

-- ⭐ E qui si vede perche': portarle ad ABBINATA incontra il guard della
--    capienza, perche' la rata e' saldata dal movimento che si sta
--    correggendo. Nascere gia' abbinate avrebbe voluto dire forzare al posto
--    dell'operatore.
SELECT throws_ok(
  format(
    $sql$UPDATE pagamenti.vendite_contabili_righe SET stato_id = %s
          WHERE contabile_id = %s$sql$,
    (SELECT stato_abbinata_id FROM tmp_refs),
    (SELECT contabile_id FROM tmp_correzione)),
  'P0001',
  NULL,
  '9) L''ultimo clic incontra il DOPPIO TEMPO della capienza: e'' di una persona, non della madre'
);

-- ============================================================
-- 10-11) La testata nuova
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM pagamenti.vendite_contabili c
     JOIN pagamenti.vendite_contabili_stati s ON s.id = c.stato_id
    WHERE c.id = (SELECT contabile_id FROM tmp_correzione)
      AND s.codice_interno = 'BOZZA'
      AND c.origine = 'MANUALE'
      AND c.centro_riscossione_id = (SELECT centro_banca_id FROM tmp_refs)),
  1,
  '10) La distinta nuova nasce in BOZZA, MANUALE, sullo stesso centro: non registra niente'
);

SELECT is(
  (SELECT c.contabile_corretta_id FROM pagamenti.vendite_contabili c
    WHERE c.id = (SELECT contabile_id FROM tmp_correzione)),
  (SELECT id FROM tmp_originale),
  '11) Il legame col documento corretto e'' scritto, e lo tiene la distinta NUOVA'
);

-- ============================================================
-- 12-13) C-4 nei due versi
-- ============================================================
SELECT throws_ok(
  format('SELECT * FROM pagamenti.fn_crea_distinta_correzione(%s)', (SELECT id FROM tmp_originale)),
  'P0001',
  NULL,
  '12) Correggere DUE VOLTE la stessa distinta e'' rifiutato: la correzione e'' una sola'
);

-- La correzione si abbina (forzando, come farebbe una persona) e si registra:
-- da li' e' un documento come gli altri, e si puo' correggere a sua volta.
UPDATE pagamenti.vendite_contabili_righe
   SET stato_id = (SELECT stato_abbinata_id FROM tmp_refs),
       forzata = true,
       motivo_forzatura = 'correzione della distinta ' || (SELECT codice FROM tmp_originale)
 WHERE contabile_id = (SELECT contabile_id FROM tmp_correzione);

UPDATE pagamenti.vendite_contabili
   SET stato_id = (SELECT stato_validata_id FROM tmp_refs)
 WHERE id = (SELECT contabile_id FROM tmp_correzione);

CREATE TEMP TABLE tmp_posting2 AS
SELECT * FROM pagamenti.fn_posta_contabile((SELECT contabile_id FROM tmp_correzione));

CREATE TEMP TABLE tmp_correzione2 AS
SELECT * FROM pagamenti.fn_crea_distinta_correzione((SELECT contabile_id FROM tmp_correzione));

SELECT is((SELECT esito FROM tmp_correzione2), 'CREATA',
  '13) ...ma correggere LA CORREZIONE si puo'': il caso vero non e'' bloccato');

-- ============================================================
-- 14) ⭐ Stesso emittente => stesso registro => il progressivo SUCCESSIVO
-- ============================================================
-- ⭐ Rev 2026-09-15 (brief distinta-numerata-sul-registro, L8): la correzione
--   copia l'emittente della distinta che corregge, quindi nasce sul suo stesso
--   registro DISTINTA e prende il numero dopo; meta.correzione_di porta il
--   codice dell'originale (che per il pregresso e' un VC_…, ed e' giusto).
--   ⚠️ «Successivo» e' misurato fra ORIGINALE e prima correzione: fra le due
--   nessun'altra distinta di questo emittente e' nata in questo file.
SELECT is(
  (SELECT concat_ws('|',
              n.emittente_soggetto_ruolo_id = o.emittente_soggetto_ruolo_id,
              n.registro_id = o.registro_id,
              n.anno = o.anno,
              right(n.codice, 7)::int - right(o.codice, 7)::int,
              n.meta->>'correzione_di' = o.codice)
     FROM pagamenti.vendite_contabili n, pagamenti.vendite_contabili o
    WHERE n.id = (SELECT contabile_id FROM tmp_correzione)
      AND o.id = (SELECT id FROM tmp_originale)),
  't|t|t|1|t',
  '14) La correzione nasce sullo stesso registro dell''originale, col progressivo successivo, e ne ricorda il codice'
);

-- ============================================================
-- 15) Cleanup
-- ============================================================
-- ⛔ Niente DELETE a mano: le righe di correzione puntano alla rata, e
--    cancellarla richiederebbe di smontare prima tutto cio' che il test ha
--    costruito — lavoro che il ROLLBACK fa da se'. ⚠️ E' lecito proprio
--    perche' il file e' transazionale: se un giorno non lo fosse, questa
--    riga diventerebbe un residuo.
SELECT ok(true, '15) Cleanup: la transazione viene annullata, nessun residuo');

SELECT * FROM finish();
ROLLBACK;
