-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU GPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: vendite.fatture_atti — il satellite dei riferimenti dell'atto
--       (changeSet 20260831-25/26/27/28,
--        brief-db-fatture-atti-riferimenti-contratto)
--
-- ⛔ COSA NON VERIFICA QUESTO FILE, e va detto subito: il POPOLAMENTO.
--   `fatture_atti` la riempie il backend (`I4` del cantiere IVA), non il
--   database: non esiste nessuna funzione DB da collaudare. Qui si verifica che
--   la SEDE regga le regole per cui e' stata costruita — cioe' che il
--   difetto muto non si possa scrivere. E' l'unica cosa che il DB puo' promettere.
--
-- Elenco test (plan 11):
--  1) la fixture e' completa (registro, fattura sotto soglia, DUE contratti)
--  2) una fattura con DUE atti tiene due blocchi, e ogni riga punta al suo
--  3) ⭐ il gemello negativo: un SECONDO blocco per lo STESSO atto e' rifiutato
--     (uq_fatture_atti_fattura_contratto) — senza, «una fattura con righe di un
--     solo contratto produce una riga sola» sarebbe una speranza
--  4) contratto_id NOT NULL: senza, la UNIQUE del caso 3 si sfonda da sola
--  5) ⛔ la FK COMPOSITA: una riga che punta all'atto di un'ALTRA fattura e'
--     rifiutata
--  6) ⭐ e il gemello positivo: la riga che punta all'atto della PROPRIA fattura
--     e' ammessa — senza, un vincolo che rifiuta sempre passerebbe il caso 5
--  7) lo snapshot E' uno snapshot: cambiare il contratto non tocca il blocco
--  8) ⭐ il congelamento morde: oltre la soglia la scrittura sul satellite e'
--     rifiutata, e con il messaggio DEI SATELLITI
--  9) e sotto la soglia si scrive: il caso 8 verifica una soglia, non un muro
-- 10) la DELETE della fattura con righe E atti passa (ordine delle ON DELETE)
-- 11) l'assetto delle quattro tabelle «che si rifanno» e' allineato
--
-- Scopo:
--  - presidiare le due invarianti che, se violate, NON darebbero sintomo: due
--    blocchi per lo stesso atto sulla stessa fattura, e una riga agganciata
--    all'atto di un altro documento. Nessuna delle due solleva niente da se':
--    la prima raddoppia un blocco `DatiContratto`, la seconda fa uscire un
--    `RiferimentoNumeroLinea` vuoto e il CIG sparisce dal documento;
--  - provare che l'ordine delle cascate regge una DELETE di fattura, invece di
--    dedurlo dal fatto che «la NO ACTION si verifica a fine istruzione».
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): fatture e contratti
--   nascono dai builder, sullo STESSO cliente. Prima emittente, utility e billing
--   account si pescavano da anagrafiche.emittenti_fiscali_utilities («la prima
--   coppia con un BA»), il registro e le due testate si scrivevano a mano e i
--   contratti stavano su un cliente costruito a parte: su un database ricostruito
--   da zero la coppia non c'e' e il file moriva sul registro senza emittente.
--   Ora dbops.fn_pgtap_crea_fattura (mondo, registro dell'azienda, testata nello
--   stato sotto soglia) e dbops.fn_pgtap_crea_contratto (dalla madre
--   vendite.fn_create_contratto) sul billing account della prima fattura.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Scattano al COMMIT, e qui il COMMIT non arriva mai (si chiude in ROLLBACK).
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_fattura (rev
--   2026-10-24), sull'operatore dell'azienda che costruisce
--   (fn_pgtap_crea_mondo_cliente, ramo «nessun contesto»).

-- ⚠️ Lo stato si sceglie SOTTO la soglia leggendo `congela_fiscale`, non per
--   nome: la soglia e' un DATO dal 2026-08-30 (D33), e scrivere 'DRAFT' qui
--   rimetterebbe una copia della lista che quel cantiere ha tolto da otto posti.
CREATE TEMP TABLE tmp_at_stato AS
SELECT s.id, s.codice_interno
  FROM config.stati_doc_fiscale s
 WHERE s.congela_fiscale IS FALSE
 ORDER BY s.ordine, s.id
 LIMIT 1;

-- ⚠️ DUE fatture: la seconda serve al caso 5, dove una riga prova a puntare
--   all'atto dell'altra. Senza un secondo documento quel caso non e'
--   costruibile, e la FK composita resterebbe non verificata. La seconda e'
--   dello STESSO cliente: il registro e l'emittente li sceglie il builder.
CREATE TEMP TABLE tmp_at_fatt AS
SELECT 1 AS n, f.fattura_id AS id, f.billing_account_id, f.emittente_soggetto_ruolo_id
  FROM dbops.fn_pgtap_crea_fattura('fatture atti 1', (SELECT codice_interno FROM tmp_at_stato)) f;

INSERT INTO tmp_at_fatt
SELECT 2, f.fattura_id, f.billing_account_id, f.emittente_soggetto_ruolo_id
  FROM dbops.fn_pgtap_crea_fattura('fatture atti 2', (SELECT codice_interno FROM tmp_at_stato),
                                   (SELECT billing_account_id FROM tmp_at_fatt WHERE n = 1)) f;

SELECT plan(11);

-- ============================================================
-- Fixture
-- ============================================================
-- L'aliquota: una qualsiasi con imposta, dal catalogo di sistema (le righe del
--   test non dipendono da quale).
CREATE TEMP TABLE tmp_at_refs AS
SELECT (SELECT i.id FROM config.iva i
         WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
         ORDER BY i.id LIMIT 1)                      AS iva_id,
       (SELECT id FROM tmp_at_stato)                 AS stato_doc_fiscale_id;

-- I DUE contratti, creati e non pescati: un test che cerca due contratti
-- esistenti passa a vuoto su un database ricostruito da zero, che e' la CI.
-- ⚠️ Il builder passa dalla funzione madre (vendite.fn_create_contratto), che e'
--   il percorso vero: un INSERT diretto dovrebbe replicare a mano numero, stato e
--   i default di ventiquattro trigger. Il cliente e' quello delle fatture (rev
--   2026-10-24): BA nuovo, sulla sua utility, SENZA dati precontrattuali, e la
--   coppia (istanza, utility) del contratto e' quella del suo BA
--   (fk_contratti_ba_coppia, 20261008-54). ⛔ Il builder scrive; si legge in
--   un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_at_contr AS
SELECT 1 AS n, c.contratto_id, c.numero
  FROM dbops.fn_pgtap_crea_contratto('fatture atti contratto 1', 'DRAFT',
                                     (SELECT billing_account_id FROM tmp_at_fatt WHERE n = 1)) c;

INSERT INTO tmp_at_contr(n, contratto_id, numero)
SELECT 2, c.contratto_id, c.numero
  FROM dbops.fn_pgtap_crea_contratto('fatture atti contratto 2', 'DRAFT',
                                     (SELECT billing_account_id FROM tmp_at_fatt WHERE n = 1)) c;

-- Il CIG del secondo contratto arriva per UPDATE e non dal payload della
-- create, e la scelta e' voluta: passarlo in creazione lega questo file al
-- changeSet 20260831-24 (la whitelist dei tre codici dell'atto), e un test che
-- ne collauda un altro diventa rosso per un motivo che non e' il suo. La
-- strada dell'UPDATE e' quella che il backend usa gia' in PATCH.
UPDATE vendite.contratti
   SET codice_cig = 'PGTAPCIG02'
 WHERE id = (SELECT contratto_id FROM tmp_at_contr WHERE n = 2);

SELECT ok(
  (SELECT count(*) FROM tmp_at_fatt) = 2
  AND (SELECT count(*) FROM tmp_at_contr) = 2
  AND (SELECT count(DISTINCT contratto_id) FROM tmp_at_contr) = 2
  AND (SELECT stato_doc_fiscale_id IS NOT NULL FROM tmp_at_refs)
  AND (SELECT count(*) FROM vendite.fatture f
        WHERE f.id IN (SELECT id FROM tmp_at_fatt)
          AND f.stato_doc_fiscale_id = (SELECT stato_doc_fiscale_id FROM tmp_at_refs)) = 2,
  '1) la fixture e completa: due fatture sotto soglia e DUE contratti distinti');

-- ============================================================
-- 2) Due atti sulla stessa fattura, e ogni riga punta al suo
-- ============================================================
-- E' il caso che il brief chiama «una fattura con righe di due contratti
-- produce due righe in fatture_atti». Non e' un dato che il DB produce: e' una
-- forma che il DB deve AMMETTERE, e questo la costruisce.
INSERT INTO vendite.fatture_atti
    (fattura_id, contratto_id, id_documento, data_documento, codice_cig)
SELECT (SELECT id FROM tmp_at_fatt WHERE n = 1), k.contratto_id, c.numero, c.data,
       c.codice_cig
  FROM tmp_at_contr k
  JOIN vendite.contratti c ON c.id = k.contratto_id;

INSERT INTO vendite.fatture_righe
    (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id,
     fattura_atto_id, meta, competenza_dal, competenza_al)
SELECT (SELECT id FROM tmp_at_fatt WHERE n = 1), k.n,
       'Riga atto ' || k.n, 1, 100, (SELECT iva_id FROM tmp_at_refs),
       a.id, jsonb_build_object('test_scope', 'pgtap_fatture_atti'), script.fn_data_operativa(), script.fn_data_operativa()
  FROM tmp_at_contr k
  JOIN vendite.fatture_atti a
         ON a.fattura_id   = (SELECT id FROM tmp_at_fatt WHERE n = 1)
        AND a.contratto_id = k.contratto_id;

SELECT is(
  (SELECT count(DISTINCT r.fattura_atto_id)::int
     FROM vendite.fatture_righe r
    WHERE r.fattura_id = (SELECT id FROM tmp_at_fatt WHERE n = 1)),
  2,
  '2) fattura con DUE atti: due blocchi, e le righe puntano a due atti distinti');

-- ============================================================
-- 3) ⭐ IL GEMELLO NEGATIVO — un solo blocco per atto, per fattura
-- ============================================================
-- ⛔ Senza questo, «una fattura con righe di UN contratto produce UNA riga
--   sola» resterebbe una promessa: un'implementazione che scrive un atto PER
--   RIGA passerebbe il caso 2 e sarebbe sbagliata. Qui a impedirlo e' la
--   UNIQUE, cioe' una garanzia e non una convenzione.
SELECT throws_ok(
  format($$INSERT INTO vendite.fatture_atti
              (fattura_id, contratto_id, id_documento, data_documento)
           VALUES (%s, %s, 'DOPPIONE', script.fn_data_operativa())$$,
         (SELECT id FROM tmp_at_fatt WHERE n = 1),
         (SELECT contratto_id FROM tmp_at_contr WHERE n = 1)),
  '23505',
  NULL::text,
  '3) un SECONDO blocco per lo stesso atto sulla stessa fattura e rifiutato');

-- ============================================================
-- 4) contratto_id NOT NULL — ed e' cio' che tiene in piedi il caso 3
-- ============================================================
-- ⚠️ Non e' pignoleria sul NOT NULL: i NULL non collidono, quindi con la
--   colonna nullable due righe a contratto NULL sulla stessa fattura sarebbero
--   entrambe ammesse e la UNIQUE del caso 3 sarebbe aggirabile scrivendo NULL.
SELECT throws_ok(
  format($$INSERT INTO vendite.fatture_atti
              (fattura_id, contratto_id, id_documento, data_documento)
           VALUES (%s, NULL, 'SENZA-ATTO', script.fn_data_operativa())$$,
         (SELECT id FROM tmp_at_fatt WHERE n = 1)),
  '23502',
  NULL::text,
  '4) contratto_id NOT NULL: la UNIQUE del caso 3 non si aggira scrivendo NULL');

-- ============================================================
-- 5) ⛔ LA FK COMPOSITA — l'atto di un'ALTRA fattura e rifiutato
-- ============================================================
-- ⛔ E' il difetto MUTO che questa forma esiste per chiudere. Con una FK
--   semplice verso fatture_atti(id) questa INSERT passerebbe, e non
--   solleverebbe niente MAI: il generatore XML raccoglie i blocchi della
--   fattura che sta stampando, non trova nessuna riga che punti a quel blocco,
--   e il RiferimentoNumeroLinea esce vuoto — il CIG sparisce dal documento.
SELECT throws_ok(
  format($$INSERT INTO vendite.fatture_righe
              (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id,
               fattura_atto_id, competenza_dal, competenza_al)
           VALUES (%s, 90, 'Riga con atto altrui', 1, 10, %s, %s, script.fn_data_operativa(), script.fn_data_operativa())$$,
         (SELECT id FROM tmp_at_fatt WHERE n = 2),
         (SELECT iva_id FROM tmp_at_refs),
         (SELECT a.id FROM vendite.fatture_atti a
           WHERE a.fattura_id = (SELECT id FROM tmp_at_fatt WHERE n = 1)
           ORDER BY a.id LIMIT 1)),
  '23503',
  NULL::text,
  '5) riga che punta all atto di un ALTRA fattura: rifiutata dalla FK composita');

-- ============================================================
-- 6) ⭐ IL GEMELLO POSITIVO — senza, un vincolo che rifiuta sempre passerebbe il 5
-- ============================================================
INSERT INTO vendite.fatture_atti
    (fattura_id, contratto_id, id_documento, data_documento)
SELECT (SELECT id FROM tmp_at_fatt WHERE n = 2),
       (SELECT contratto_id FROM tmp_at_contr WHERE n = 1),
       'ATTO-F2', script.fn_data_operativa();

SELECT lives_ok(
  format($$INSERT INTO vendite.fatture_righe
              (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id,
               fattura_atto_id, competenza_dal, competenza_al)
           VALUES (%s, 91, 'Riga con atto proprio', 1, 10, %s, %s, script.fn_data_operativa(), script.fn_data_operativa())$$,
         (SELECT id FROM tmp_at_fatt WHERE n = 2),
         (SELECT iva_id FROM tmp_at_refs),
         (SELECT a.id FROM vendite.fatture_atti a
           WHERE a.fattura_id = (SELECT id FROM tmp_at_fatt WHERE n = 2)
           ORDER BY a.id LIMIT 1)),
  '6) riga che punta all atto della PROPRIA fattura: ammessa');

-- ============================================================
-- 7) ⭐ LO SNAPSHOT E UNO SNAPSHOT
-- ============================================================
-- ⛔ E' l'unica ragione per cui quelle colonne esistono invece di un JOIN al
--   contratto: un CIG corretto domani in anagrafica NON deve cambiare su una
--   fattura gia' emessa. Se il blocco seguisse il contratto, questa modifica lo
--   riscriverebbe.
UPDATE vendite.contratti
   SET codice_cig = 'CIG-CAMBIATO'
 WHERE id = (SELECT contratto_id FROM tmp_at_contr WHERE n = 2);

SELECT is(
  (SELECT a.codice_cig FROM vendite.fatture_atti a
    WHERE a.fattura_id   = (SELECT id FROM tmp_at_fatt WHERE n = 1)
      AND a.contratto_id = (SELECT contratto_id FROM tmp_at_contr WHERE n = 2)),
  'PGTAPCIG02',
  '7) il CIG cambiato sul contratto NON tocca il blocco gia scritto');

-- ============================================================
-- 8) ⭐ IL CONGELAMENTO MORDE, e con il messaggio DEI SATELLITI
-- ============================================================
-- ⚠️ Si congela spostando la COLONNA, non lo stato della fattura: vendite.fatture
--   ha un guard di transizione, e forzarlo proverebbe quello. Stessa tecnica di
--   test-guard-congelamento-fusione-v1.
-- ⛔ E si guarda il MESSAGGIO e non il solo SQLSTATE: tutti i codici di dominio
--   sollevano P0001, quindi un throws_ok generico sarebbe verde anche se questo
--   satellite si prendesse il codice DELLE RIGHE.
UPDATE config.stati_doc_fiscale SET congela_fiscale = true
 WHERE id = (SELECT stato_doc_fiscale_id FROM tmp_at_refs);

SELECT throws_like(
  format($$INSERT INTO vendite.fatture_atti
              (fattura_id, contratto_id, id_documento, data_documento)
           VALUES (%s, %s, 'OLTRE-SOGLIA', script.fn_data_operativa())$$,
         (SELECT id FROM tmp_at_fatt WHERE n = 2),
         (SELECT contratto_id FROM tmp_at_contr WHERE n = 2)),
  '%non e'' piu'' modificabile%',
  '8) oltre la soglia la scrittura sul satellite e rifiutata, col messaggio dei satelliti');

-- ============================================================
-- 9) E sotto la soglia si scrive: il caso 8 verifica una SOGLIA, non un muro
-- ============================================================
-- ⚠️ Una guardia che rifiutasse sempre passerebbe il caso 8 senza dire niente.
-- ⛔ E si tocca una riga GIA' ESISTENTE invece di inserirne una sulla stessa
--   coppia del caso 8: quella coppia il caso 8 non la scrive solo perche' il
--   guard lo impedisce, quindi riusarla legherebbe questo caso al FALLIMENTO
--   del precedente. Trovato con la prova di mutazione: togliendo il trigger,
--   il caso 8 scriveva davvero la riga e il 9 moriva sulla UNIQUE — due rossi
--   per un difetto solo, e il secondo indicava il posto sbagliato.
UPDATE config.stati_doc_fiscale SET congela_fiscale = false
 WHERE id = (SELECT stato_doc_fiscale_id FROM tmp_at_refs);

SELECT lives_ok(
  format($$UPDATE vendite.fatture_atti SET id_documento = id_documento
            WHERE id = %s$$,
         (SELECT a.id FROM vendite.fatture_atti a
           WHERE a.fattura_id = (SELECT id FROM tmp_at_fatt WHERE n = 2)
           ORDER BY a.id LIMIT 1)),
  '9) sotto la soglia il satellite si scrive: era una soglia, non un muro');

-- ============================================================
-- 10) ⭐ L'ORDINE DELLE CASCATE — provato, non dedotto
-- ============================================================
-- ⛔ E' il punto in cui una DELETE di fattura puo' esplodere con una violazione
--   grezza a runtime. Il ragionamento dice che non succede — la NO ACTION di
--   fk_fatture_righe_fattura_atto si verifica a FINE ISTRUZIONE, quando le
--   cascate su righe e atti sono gia' passate — ma un ragionamento non e' una
--   prova, e questa e' la sola cosa che lo distingue da un'ipotesi.
-- ⚠️ La fattura scelta e' la n.2, che a questo punto ha ENTRAMBE le figlie:
--   atti (casi 6 e 9) e righe con fattura_atto_id valorizzato (caso 6).
SELECT lives_ok(
  format('DELETE FROM vendite.fatture WHERE id = %s',
         (SELECT id FROM tmp_at_fatt WHERE n = 2)),
  '10) DELETE di una fattura con righe E atti: le cascate reggono, nessun 23503');

-- ============================================================
-- 11) L'assetto delle quattro tabelle «che si rifanno»
-- ============================================================
-- ⭐ Righe, indirizzi, riepiloghi IVA e atti sono la stessa specie: si
--   rigenerano col lotto e si congelano con la fattura. Devono avere lo stesso
--   assetto — tx_id presente, storicizza presente e SPENTO — o la prossima
--   tabella nascera' di nuovo a caso, che e' esattamente com'e' andata finora
--   (cinque parenti, quattro comportamenti diversi).
-- ⚠️ Si legge dal CATALOGO e non dai dati: e' struttura, non popolazione.
SELECT is(
  (SELECT count(*)::int
     FROM (VALUES ('fatture_righe'), ('fatture_indirizzi'),
                  ('fatture_riepiloghi_iva'), ('fatture_atti')) AS t(tab)
    WHERE NOT (
      EXISTS (SELECT 1 FROM information_schema.columns c
               WHERE c.table_schema = 'vendite' AND c.table_name = t.tab
                 AND c.column_name = 'tx_id')
      AND EXISTS (SELECT 1 FROM information_schema.columns c
                   WHERE c.table_schema = 'vendite' AND c.table_name = t.tab
                     AND c.column_name = 'storicizza'
                     AND c.is_nullable = 'NO'
                     AND c.column_default = 'false'))),
  0,
  '11) le quattro tabelle «che si rifanno» hanno tx_id e storicizza NOT NULL DEFAULT false');

SELECT * FROM finish();

ROLLBACK;
