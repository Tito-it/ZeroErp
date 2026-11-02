-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: vendite.fatture_righe.riga_capofila_id — la riga che si spezza
--       (changeSet 20260831-30/31/32, decisione N3 opzione a' + decisione D)
--
-- ⛔ COSA DISCRIMINA, e non e' «la INSERT riesce»: riesce comunque. Sono i tre
--   casi che il piano chiede, e il terzo esiste per smascherare un guard che
--   rifiuta SEMPRE — senza di lui i primi due passerebbero anche su un presidio
--   rotto nel verso opposto.
--
-- Elenco test (plan 10):
--  1) la fixture e' completa (due fatture sotto soglia, righe capofila)
--  2) ⭐ IL GEMELLO POSITIVO: due parti sulla stessa capofila, stessa fattura,
--     AMMESSE — senza, un presidio che rifiuta sempre passerebbe il 3 e il 4
--  3) ⛔ NIENTE CATENE: una parte che punta a una parte e' RIFIUTATA
--  4) ⛔ STESSA FATTURA: una parte che punta a una riga di un ALTRO documento
--     e' RIFIUTATA — e la respinge la FK composita, non un guard
--  5) ⭐ IL RAMO ALL'INDIETRO: una riga che HA GIA' delle parti non puo'
--     diventare a sua volta una parte. E' il ramo che si dimentica: nel caso 3
--     la riga puntata e' colpevole, qui e' innocente e la catena nasce
--     dall'altro capo
--  6) una riga non e' parte di se stessa (il CHECK)
--  7) il guard parla il SUO messaggio, non quello del congelamento
--  8) la vista espone la parte come PARTE_PLAFOND, a livello 0 e col SUO importo
--  9) ⭐ e le due parti hanno lo STESSO `ordinamento`: e' cio' che le tiene
--     attaccate quando fra loro cade un'altra riga
-- 10) il totale esposto NON cambia: la spezzatura non crea ne' perde valore
--
-- Scopo:
--  - presidiare le due invarianti che, se violate, non darebbero sintomo. Una
--    catena fa vedere meta' valore a chi somma partendo dall'attivita'; una
--    parte agganciata a un altro documento e' un totale che non torna su due
--    fatture insieme. Nessuna delle due solleva niente da se';
--  - provare che la vista NON aggrega le due parti: aggregarle produrrebbe un
--    solo DettaglioLinee, cioe' cancellerebbe la ragione della spezzatura.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, e qui il COMMIT non arriva mai.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS).
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

-- ============================================================
-- Fixture
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): le DUE fatture si COSTRUISCONO
--   (dbops.fn_pgtap_crea_fattura: azienda di chi agisce, cliente, registro
--   coerente, testata nello stato iniziale — che non congela), la seconda
--   sullo stesso billing account. Prima la coppia (emittente, utility) si
--   pescava da emittenti_fiscali_utilities, il BA col primo id, e registro e
--   testate si INSERIVANO a mano: da zero non c'era niente. Dal catalogo di
--   seed resta solo l'IVA.
CREATE TEMP TABLE tmp_cf_f1 AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('capofila 1');

CREATE TEMP TABLE tmp_cf_f2 AS
SELECT * FROM dbops.fn_pgtap_crea_fattura(
  'capofila 2', 'DRAFT', (SELECT billing_account_id FROM tmp_cf_f1));

CREATE TEMP TABLE tmp_cf_refs AS
SELECT (SELECT i.id FROM config.iva i
         WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
         ORDER BY i.id LIMIT 1)                      AS iva_id;

-- ⚠️ DUE fatture: la seconda serve al caso 4. Senza un secondo documento quel
--   caso non e' COSTRUIBILE, e la FK composita resterebbe non verificata — che
--   e' la forma classica del verde per sottrazione.
CREATE TEMP TABLE tmp_cf_fatt AS
SELECT fattura_id AS id, 1 AS n FROM tmp_cf_f1
UNION ALL
SELECT fattura_id AS id, 2 AS n FROM tmp_cf_f2;

-- Le capofila: una per fattura. Nascono senza `riga_capofila_id`, come ogni
-- riga ordinaria — la capofila E' essa stessa la prima parte.
CREATE TEMP TABLE tmp_cf_capo AS
WITH ins AS (
  INSERT INTO vendite.fatture_righe
      (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id, meta, competenza_dal, competenza_al)
  SELECT f.id, 1, 'Capofila fattura ' || f.n, 10, 100,
         (SELECT iva_id FROM tmp_cf_refs),
         jsonb_build_object('test_scope', 'pgtap_capofila', 'n', f.n), script.fn_data_operativa(), script.fn_data_operativa()
    FROM tmp_cf_fatt f
  RETURNING id, fattura_id, (meta ->> 'n')::int AS n)
SELECT * FROM ins;

SELECT ok(
  (SELECT count(*) FROM tmp_cf_fatt) = 2
  AND (SELECT count(*) FROM tmp_cf_capo) = 2
  AND (SELECT bool_and(riga_capofila_id IS NULL) FROM vendite.fatture_righe
        WHERE id IN (SELECT id FROM tmp_cf_capo)),
  '1) la fixture e completa: due fatture sotto soglia, due capofila senza padre');

-- ============================================================
-- 2) ⭐ IL GEMELLO POSITIVO — due parti sulla stessa capofila
-- ============================================================
-- ⛔ Va PRIMA dei rifiuti, ed e' voluto: senza questo caso, un presidio rotto
--   nel verso opposto — che rifiuta SEMPRE — passerebbe i casi 3, 4 e 5 e
--   sembrerebbe perfetto. E' l'unica asserzione che distingue «il guard
--   funziona» da «il guard e' un muro».
INSERT INTO vendite.fatture_righe
    (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id,
     riga_capofila_id, meta, competenza_dal, competenza_al)
SELECT c.fattura_id, 2, 'Parte 2 (plafond esaurito)', 4, 100,
       (SELECT iva_id FROM tmp_cf_refs), c.id,
       jsonb_build_object('test_scope', 'pgtap_capofila'), script.fn_data_operativa(), script.fn_data_operativa()
  FROM tmp_cf_capo c WHERE c.n = 1;

SELECT lives_ok(
  format($$INSERT INTO vendite.fatture_righe
              (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id,
               riga_capofila_id, competenza_dal, competenza_al)
           VALUES (%s, 3, 'Parte 3', 1, 100, %s, %s, script.fn_data_operativa(), script.fn_data_operativa())$$,
         (SELECT fattura_id FROM tmp_cf_capo WHERE n = 1),
         (SELECT iva_id FROM tmp_cf_refs),
         (SELECT id FROM tmp_cf_capo WHERE n = 1)),
  '2) DUE parti sulla stessa capofila, stessa fattura: ammesse');

-- ============================================================
-- 3) ⛔ NIENTE CATENE — una parte che punta a una parte
-- ============================================================
-- ⛔ Il difetto e' MUTO: se «capofila -> parti» smette di essere una lettura a
--   un salto, chi somma gli importi di un'attivita' attraversando
--   fattura_riga_id si ferma al primo livello e prende meta' valore, senza che
--   niente protesti.
SELECT throws_ok(
  format($$INSERT INTO vendite.fatture_righe
              (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id,
               riga_capofila_id, competenza_dal, competenza_al)
           VALUES (%s, 4, 'Nipote', 1, 100, %s, %s, script.fn_data_operativa(), script.fn_data_operativa())$$,
         (SELECT fattura_id FROM tmp_cf_capo WHERE n = 1),
         (SELECT iva_id FROM tmp_cf_refs),
         (SELECT r.id FROM vendite.fatture_righe r
           WHERE r.fattura_id = (SELECT fattura_id FROM tmp_cf_capo WHERE n = 1)
             AND r.riga_capofila_id IS NOT NULL
           ORDER BY r.riga_nr LIMIT 1)),
  'P0001',
  NULL::text,
  '3) una parte che punta a una PARTE e rifiutata: niente catene');

-- ============================================================
-- 4) ⛔ STESSA FATTURA — e la respinge un VINCOLO, non un guard
-- ============================================================
-- ⭐ Lo SQLSTATE atteso e' 23503 e non P0001, ed e' la prova che a parlare e'
--   la FK composita: se un giorno qualcuno sostituisse il vincolo con un
--   controllo in PL/pgSQL questo caso diventerebbe rosso, e sarebbe giusto —
--   la garanzia strutturale sarebbe sparita.
SELECT throws_ok(
  format($$INSERT INTO vendite.fatture_righe
              (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id,
               riga_capofila_id, competenza_dal, competenza_al)
           VALUES (%s, 9, 'Parte con capofila altrui', 1, 100, %s, %s, script.fn_data_operativa(), script.fn_data_operativa())$$,
         (SELECT fattura_id FROM tmp_cf_capo WHERE n = 2),
         (SELECT iva_id FROM tmp_cf_refs),
         (SELECT id FROM tmp_cf_capo WHERE n = 1)),
  '23503',
  NULL::text,
  '4) una parte che punta a una riga di un ALTRA fattura e rifiutata dalla FK composita');

-- ============================================================
-- 5) ⭐ IL RAMO ALL'INDIETRO — quello che si dimentica
-- ============================================================
-- ⚠️ Qui la riga PUNTATA e' innocente: e' una capofila legittima, senza padre.
--   La catena nascerebbe dall'altro capo, perche' e' la riga che si sta
--   spostando ad avere gia' delle parti proprie. Un guard che controlla solo
--   «in avanti» passa questo caso e lascia costruire la catena lo stesso.
-- ⛔ Serve una TERZA capofila: quella della fattura 2 non va bene, perche' il
--   vincolo di fattura la respingerebbe prima per un altro motivo — e il test
--   direbbe verde per il presidio sbagliato.
INSERT INTO vendite.fatture_righe
    (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id, meta, competenza_dal, competenza_al)
SELECT (SELECT fattura_id FROM tmp_cf_capo WHERE n = 1), 5,
       'Terza capofila, stessa fattura', 1, 100,
       (SELECT iva_id FROM tmp_cf_refs),
       jsonb_build_object('test_scope', 'pgtap_capofila'), script.fn_data_operativa(), script.fn_data_operativa();

SELECT throws_ok(
  format($$UPDATE vendite.fatture_righe SET riga_capofila_id = %s WHERE id = %s$$,
         (SELECT r.id FROM vendite.fatture_righe r
           WHERE r.fattura_id = (SELECT fattura_id FROM tmp_cf_capo WHERE n = 1)
             AND r.riga_nr = 5),
         (SELECT id FROM tmp_cf_capo WHERE n = 1)),
  'P0001',
  NULL::text,
  '5) una riga che HA GIA delle parti non puo diventare a sua volta una parte');

-- ============================================================
-- 6) Una riga non e' parte di se stessa
-- ============================================================
-- ⚠️ Lo ferma il CHECK, non il guard: il cappio a un nodo e' il caso degenere,
--   e toglierlo dal trigger lo tiene piu' semplice.
SELECT throws_ok(
  format($$UPDATE vendite.fatture_righe SET riga_capofila_id = id WHERE id = %s$$,
         (SELECT id FROM tmp_cf_capo WHERE n = 2)),
  '23514',
  NULL::text,
  '6) una riga non e parte di se stessa (CHECK, non guard)');

-- ============================================================
-- 7) Il guard parla il SUO messaggio
-- ============================================================
-- ⛔ Un throws_ok sul solo SQLSTATE sarebbe verde anche se questo guard si
--   prendesse il codice del congelamento: sollevano entrambi P0001. Il
--   discriminante e' la frase, che e' legata al CODICE e non alla funzione.
-- ⚠️ Il pattern non attraversa un segnaposto: si cerca il pezzo stabile.
SELECT throws_like(
  format($$INSERT INTO vendite.fatture_righe
              (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id,
               riga_capofila_id, competenza_dal, competenza_al)
           VALUES (%s, 6, 'Nipote bis', 1, 100, %s, %s, script.fn_data_operativa(), script.fn_data_operativa())$$,
         (SELECT fattura_id FROM tmp_cf_capo WHERE n = 1),
         (SELECT iva_id FROM tmp_cf_refs),
         (SELECT r.id FROM vendite.fatture_righe r
           WHERE r.fattura_id = (SELECT fattura_id FROM tmp_cf_capo WHERE n = 1)
             AND r.riga_capofila_id IS NOT NULL
           ORDER BY r.riga_nr LIMIT 1)),
  '%legame con la riga capofila%',
  '7) il guard solleva il SUO messaggio, non quello del congelamento');

-- ============================================================
-- 8) La vista espone la parte come PARTE_PLAFOND, col SUO importo
-- ============================================================
-- ⛔ E' il caso che smaschera la forma sbagliata. Se le due parti fossero
--   trattate come un kit sarebbero AGGREGATE in una riga sola — un solo
--   DettaglioLinee — oppure la parte scenderebbe a livello 1 con imponibile
--   NULL, e chi salta il livello 1 perderebbe il suo valore in silenzio.
SELECT is(
  (SELECT e.tipo_riga || '/' || e.livello || '/' || (e.imponibile > 0)::text
     FROM vendite.vw_fattura_righe_esposte e
    WHERE e.fattura_id = (SELECT fattura_id FROM tmp_cf_capo WHERE n = 1)
      AND e.riga_capofila_id IS NOT NULL
    ORDER BY e.riga_nr
    LIMIT 1),
  'PARTE_PLAFOND/0/true',
  '8) la parte esce come PARTE_PLAFOND, a livello 0 e con un imponibile suo');

-- ============================================================
-- 9) ⭐ Le due parti hanno lo STESSO `ordinamento`
-- ============================================================
-- ⚠️ E' cio' che le tiene ATTACCATE quando fra loro cade un'altra riga: senza,
--   l'operatore leggerebbe due righe con quantita' strane in punti diversi del
--   documento, senza niente che dica che vengono dalla stessa origine.
SELECT is(
  (SELECT count(DISTINCT e.ordinamento)::int
     FROM vendite.vw_fattura_righe_esposte e
    WHERE e.fattura_id = (SELECT fattura_id FROM tmp_cf_capo WHERE n = 1)
      AND (e.fatture_righe_id = (SELECT id FROM tmp_cf_capo WHERE n = 1)
           OR e.riga_capofila_id = (SELECT id FROM tmp_cf_capo WHERE n = 1))),
  1,
  '9) capofila e parti condividono lo stesso ordinamento: restano attaccate');

-- ============================================================
-- 10) Il totale esposto non cambia
-- ============================================================
-- ⛔ E' il controllo che la spezzatura non crei ne' perda valore: la somma
--   della vista deve coincidere con la somma delle righe. Se le parti fossero
--   aggregate come un kit il totale tornerebbe LO STESSO (il padre porta la
--   somma), quindi questo caso da solo non basta — ma senza di lui una vista
--   che espone le parti DUE volte passerebbe l'8 e il 9.
SELECT is(
  (SELECT COALESCE(sum(e.imponibile), 0) FROM vendite.vw_fattura_righe_esposte e
    WHERE e.fattura_id = (SELECT fattura_id FROM tmp_cf_capo WHERE n = 1)),
  (SELECT COALESCE(sum(r.imponibile_riga), 0) FROM vendite.fatture_righe r
    WHERE r.fattura_id = (SELECT fattura_id FROM tmp_cf_capo WHERE n = 1)),
  '10) il totale esposto coincide con la somma delle righe: niente valore creato o perso');

SELECT * FROM finish();

ROLLBACK;
