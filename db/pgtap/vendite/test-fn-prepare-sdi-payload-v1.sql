-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_prepare_sdi_payload — payload SDI del lotto
-- ------------------------------------------------------------
-- Brief: docs/it/dev/work-done/brief-db-bonifica-riferimenti-morti.md
--        (F2, changeSet 20260804-39)
--
-- Indice test (1..10):
--  1) p_lotto_id NULL                      -> solleva
--  2) p_lotto_id <= 0                      -> solleva
--  3) p_stato_sdi_codice_interno vuoto     -> solleva
--  4) lotto inesistente                    -> solleva
--  5) codice stato SDI inesistente         -> solleva
--  6) il CHECK tentativo_num > 0 esiste ancora (e' cio' che rende vero il 7)
--  7) 🔴 primo giro, force=false -> tentativo_num = 1 (era 0: CHECK violato)
--  8) 🔴 la riga e' scritta davvero in vendite.fatture_sdi, con lo stato chiesto
--  9) force=true -> tentativo successivo (2), e la riga precedente resta
-- 10) totale_a_pagare arriva dalla TESTATA, non ricostruito a valle
--
-- ── PERCHE' ESISTE ──────────────────────────────────────────────────────
--   Questa funzione non aveva **nessun** test, ed e' il task
--   `prepare_sdi_payload_lotto` (registry id 9) montato su due pipeline
--   attive: MASSIVO (id 5) e GIORNALIERO (id 7), entrambe con
--   `"force_new_tentativo": false`. Fino al 2026-08-04 non poteva girare,
--   e la copertura di quel passo valeva zero.
--
--   ⚠️ I difetti erano DUE, in serie, e il secondo si vedeva solo dopo
--   aver riparato il primo:
--     1. la funzione nominava la colonna `tentativo`, che si chiama
--        `tentativo_num` — errore di compilazione, lo prende
--        `plpgsql_check` e ora lo presidia
--        `db/pgtap/dbops/test-riferimenti-morti-v1.sql`;
--     2. il numero di tentativo era
--          COALESCE(MAX, 0) + CASE WHEN force THEN 1 ELSE 0 END
--        che con `force = false` — la configurazione **in seed** — dava
--        **0** al primo inserimento, contro
--        `chk_fatture_sdi_tentativo_num CHECK (tentativo_num > 0)`.
--
--   Il secondo difetto NON e' un errore di compilazione: nessun controllo
--   statico lo avrebbe visto, si manifesta solo eseguendo. E' la ragione
--   per cui questo file esiste accanto al presidio, e non al posto suo:
--   il presidio verifica che il codice si risolva, il test che faccia la
--   cosa giusta. Il test 7 e' quello che tiene chiuso il difetto 2.
--
-- ── FIXTURE ─────────────────────────────────────────────────────────────
--   Un lotto con almeno una fattura collegata, scelto dai dati esistenti
--   (stesso criterio di test-elimina-fattura-da-lotto-v1). Le eventuali
--   righe `fatture_sdi` di quelle fatture vengono cancellate DENTRO la
--   transazione: cosi' il punto che conta — «il PRIMO tentativo vale 1» —
--   e' deterministico invece di dipendere dal fatto che nessuno abbia mai
--   preparato il payload di quel lotto.
--
--   ⚠️ LIMITE DA CONOSCERE. La fixture e' data-dependent: su un database
--   appena migrato — che ha i seed ma nessun dato transazionale — non
--   esiste nessun lotto con fatture, e i test 7-10 fanno **skip**. Cioe'
--   proprio i quattro che presidiano il difetto. I test 1-6 girano sempre.
--   E' una copertura condizionata, e va detto invece di lasciarla
--   scoprire: se un domani la suite pgTAP venisse portata in CI, questo
--   file li' misurerebbe meno di quanto misura qui, e per chiudere il buco
--   servirebbe costruire lotto e fatture da zero — che significa passare
--   per i guard di emissione, numerazione e satelliti, cioe' un lavoro a
--   se'. Finche' gira sul server di sviluppo, sui dati veri, misura.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

-- ============================================================
-- 1-5) Guard di parametro e di esistenza — non dipendono dai dati
-- ============================================================
SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_prepare_sdi_payload(NULL) $$,
  'P0001', NULL,
  '1) p_lotto_id NULL: rifiutato'
);

SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_prepare_sdi_payload(0) $$,
  'P0001', NULL,
  '2) p_lotto_id <= 0: rifiutato'
);

SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_prepare_sdi_payload(1, '') $$,
  'P0001', NULL,
  '3) p_stato_sdi_codice_interno vuoto: rifiutato'
);

-- Un id sicuramente inesistente ma > 0, per non finire nel guard 2.
SELECT throws_ok(
  format(
    $$ SELECT * FROM vendite.fn_prepare_sdi_payload(%s) $$,
    (SELECT COALESCE(MAX(id), 0) + 1000 FROM vendite.fatturazione_lotti)
  ),
  'P0001', NULL,
  '4) lotto inesistente: rifiutato'
);

SELECT throws_ok(
  format(
    $$ SELECT * FROM vendite.fn_prepare_sdi_payload(%s, 'NON_ESISTE_QUESTO_STATO') $$,
    (SELECT COALESCE(MAX(id), 1) FROM vendite.fatturazione_lotti)
  ),
  'P0001', NULL,
  '5) codice stato SDI inesistente: rifiutato'
);

-- ============================================================
-- 6) Il CHECK che rende significativo il test 7
--
-- ⚠️ Senza questo vincolo, `tentativo_num = 0` sarebbe solo brutto invece
--    che impossibile, e il difetto originale non avrebbe fatto rumore.
--    Se qualcuno lo togliesse, il test 7 continuerebbe a passare ma
--    smetterebbe di presidiare qualcosa: meglio accorgersene qui.
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conrelid = 'vendite.fatture_sdi'::regclass
       AND conname  = 'chk_fatture_sdi_tentativo_num'
       AND contype  = 'c'
  ),
  '6) chk_fatture_sdi_tentativo_num presente (tentativo_num > 0)'
);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_sdi_lotto AS
SELECT lf.lotto_id,
       count(*) AS n_fatture
  FROM vendite.fatturazione_lotti_fatture lf
  JOIN vendite.fatture f ON f.id = lf.fattura_id
 GROUP BY lf.lotto_id
 ORDER BY count(*) DESC, lf.lotto_id DESC
 LIMIT 1;

-- Slate pulito: il primo tentativo deve essere davvero il primo.
DELETE FROM vendite.fatture_sdi
 WHERE fattura_id IN (
   SELECT lf.fattura_id
     FROM vendite.fatturazione_lotti_fatture lf
    WHERE lf.lotto_id = (SELECT lotto_id FROM tmp_sdi_lotto)
 );

-- ⚠️ Ogni giro si MATERIALIZZA in una temp table prima di essere
--    asserito, e non si chiama la funzione dentro l'espressione di un
--    `is()`. Due motivi, entrambi pagati scrivendo questo file:
--      · la funzione SCRIVE, e le sue scritture non sono visibili ad
--        altre parti della **stessa** istruzione — un'asserzione che
--        chiama la funzione e rilegge `fatture_sdi` in un colpo solo
--        legge la tabella com'era prima;
--      · chiamarla due volte per due asserzioni diverse aprirebbe due
--        tentativi invece di uno, falsando il conteggio a valle.
CREATE TEMP TABLE tmp_sdi_giro1 AS
SELECT p.*
  FROM tmp_sdi_lotto l,
       vendite.fn_prepare_sdi_payload(l.lotto_id) p;

-- ============================================================
-- 7) 🔴 Primo giro con force=false -> tentativo_num = 1
--
--    E' il test del difetto 2. Prima della riparazione il calcolo dava 0
--    e la INSERT moriva sul CHECK: qui non si asserisce «non solleva» ma
--    il VALORE, perche' «non solleva» sarebbe passato anche con un 5.
--    Si asserisce l'insieme dei tentativi su TUTTE le fatture del lotto,
--    non su una: un `LIMIT 1` avrebbe coperto una fattura sola.
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_sdi_lotto)
  THEN skip('7) skip: nessun lotto con fatture collegate nei dati', 1)
  ELSE is(
    (SELECT array_agg(DISTINCT tentativo_num) FROM tmp_sdi_giro1),
    ARRAY[1]::smallint[],
    '7) primo giro (force=false): tentativo_num = 1 su tutte le fatture del lotto'
  )
END;

-- ============================================================
-- 8) La riga e' scritta davvero, con lo stato richiesto
--
--    Il test 7 legge cio' che la funzione RITORNA. Questo legge cio' che
--    ha SCRITTO: sono due cose diverse, e il ritorno passa da una CTE
--    `RETURNING` che potrebbe divergere dalla tabella.
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_sdi_lotto)
  THEN skip('8) skip: nessun lotto con fatture collegate nei dati', 1)
  ELSE is(
    (SELECT count(*)
       FROM vendite.fatture_sdi fs
       JOIN vendite.fatturazione_lotti_fatture lf ON lf.fattura_id = fs.fattura_id
      WHERE lf.lotto_id = (SELECT lotto_id FROM tmp_sdi_lotto)
        AND fs.tentativo_num = 1
        AND fs.stato_sdi_id = (SELECT s.id FROM config.stati_sdi s
                                WHERE s.codice_interno = 'DA_INVIARE' AND s.attivo IS TRUE
                                ORDER BY s.ordine NULLS LAST, s.id LIMIT 1)),
    (SELECT n_fatture FROM tmp_sdi_lotto),
    '8) una riga fatture_sdi per fattura, tentativo 1, stato DA_INVIARE'
  )
END;

-- ============================================================
-- 9) force=true -> tentativo successivo, senza cancellare il precedente
--
--    ⚠️ Il tentativo e' una STORIA, non un contatore da sovrascrivere:
--    la riga 1 deve restare, altrimenti si perde traccia dell'invio
--    fallito che ha reso necessario il secondo.
-- ============================================================
CREATE TEMP TABLE tmp_sdi_giro2 AS
SELECT p.*
  FROM tmp_sdi_lotto l,
       vendite.fn_prepare_sdi_payload(l.lotto_id, 'DA_INVIARE', true) p;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_sdi_lotto)
  THEN skip('9) skip: nessun lotto con fatture collegate nei dati', 1)
  ELSE is(
    (SELECT array_agg(DISTINCT tentativo_num) FROM tmp_sdi_giro2)
    || (SELECT array_agg(DISTINCT fs.tentativo_num ORDER BY fs.tentativo_num)
          FROM vendite.fatture_sdi fs
          JOIN vendite.fatturazione_lotti_fatture lf ON lf.fattura_id = fs.fattura_id
         WHERE lf.lotto_id = (SELECT lotto_id FROM tmp_sdi_lotto)),
    ARRAY[2]::smallint[] || ARRAY[1, 2]::smallint[],
    '9) force=true: tentativo 2 restituito, e in tabella restano 1 e 2'
  )
END;

-- ============================================================
-- 10) totale_a_pagare arriva dalla TESTATA
--
--     rev 2026-07-28: prima era una SUM su vendite.fatture_riepiloghi_iva
--     con una colonna inesistente — un altro riferimento morto, in un
--     ramo che nessuno eseguiva. Il totale dovuto e' quello che
--     fn_ricalcola_totali_fattura ha gia' calcolato, fondi e
--     arrotondamento inclusi: qui si verifica che non venga ricostruito.
-- ============================================================
-- Si rilegge il PRIMO giro, gia' materializzato: chiamare di nuovo la
-- funzione qui aprirebbe un terzo tentativo solo per fare un confronto.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_sdi_giro1)
  THEN skip('10) skip: nessun lotto con fatture collegate nei dati', 1)
  ELSE ok(
    (SELECT bool_and(g.totale_a_pagare = COALESCE(f.totale_a_pagare, 0))
       FROM tmp_sdi_giro1 g
       JOIN vendite.fatture f ON f.id = g.fattura_id),
    '10) totale_a_pagare = vendite.fatture.totale_a_pagare (non ricostruito)'
  )
END;

SELECT * FROM finish();

ROLLBACK;
