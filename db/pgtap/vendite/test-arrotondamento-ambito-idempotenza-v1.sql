-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: ambito di compensazione degli arrotondamenti — idempotenza del
--       ricalcolo, separazione degli ambiti, storno alla cancellazione
--       (piano-db-satelliti-fattura.md, decisione D-N e rilievi C-20/C-22/C-23,
--        fase 3b.5)
-- ------------------------------------------------------------
-- Perche' questo file esiste
--   Il saldo d'arrotondamento e' condiviso da tutte le fatture dello stesso
--   ambito, e tre difetti diversi lo facevano mentire in silenzio:
--     · il ricalcolo rileggeva un saldo che conteneva GIA' il proprio
--       contributo, quindi la riesecuzione inseguiva il primo calcolo invece
--       di ripeterlo (D-N pezzo 2);
--     · l'ambito non conteneva le condizioni di pagamento, quindi due fatture
--       che la chiave aveva separato si passavano il saldo (C-20);
--     · la cancellazione non stornava niente, quindi il saldo diventava la
--       somma di cio' che era stato emesso E di cio' che era stato buttato
--       (C-23).
--   Nessuno dei tre produce un errore: producono numeri. Per questo la
--   copertura sta in un file suo.
--
--   ⚠️ La misura che conta non e' il totale, e' la SCOMPOSIZIONE. Il totale
--   resta simile anche quando il meccanismo e' rotto, perche' l'arrotondamento
--   e' piccolo; a diventare falsa e' la coppia
--   (arrotondamento_precedente, arrotondamento_attuale) in testata — e uno dei
--   due va in stampa.
-- ------------------------------------------------------------
-- Indice test
-- 1) Fixture: fattura con riepilogo IVA e arrotondamento non nullo
-- 2) Il ricalcolo produce un arrotondamento diverso da zero (fixture utile)
-- 3) Idempotenza: due ricalcoli, stesso totale
-- 4) Idempotenza: due ricalcoli, stessa SCOMPOSIZIONE precedente/attuale
-- 5) Idempotenza: il saldo d ambito non raddoppia
-- 6) Separazione: termini diversi -> due righe d ambito distinte (C-20)
-- 7) Separazione: il rerun della prima non sposta i totali della seconda
-- 8) Storno (C-23): cancellare la fattura riporta il saldo d ambito
-- 9) Storno: nessuna riga d ambito viene CREATA dal cleanup (UPDATE, non upsert)
-- 10) C-22: il ramo lock_batch_id libera tutte le attivita del batch
-- 11) C-22: senza lock_batch_id le attivita degli altri restano intatte
-- 12) C-22: il reset per-fattura passa NULL alla primitiva
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

SELECT plan(12);

-- ============================================================
-- 0) Fixture
-- ============================================================
-- Si parte da un'attivita' con commessa (serve al test 6 per far divergere il
-- termine per la via reale) e da un lotto esistente. Gli importi hanno tre
-- decimali apposta: con due, il totale cade gia' tondo e l'arrotondamento
-- sarebbe zero — cioe' la fixture non eserciterebbe nulla. Il test 2 lo
-- verifica invece di darlo per scontato.
CREATE TEMP TABLE tmp_refs_arr AS
SELECT (SELECT a.id FROM vendite.attivita_fatturabili a
         WHERE a.commessa_id IS NOT NULL ORDER BY a.id LIMIT 1)  AS attivita_id,
       (SELECT a.commessa_id FROM vendite.attivita_fatturabili a
         WHERE a.commessa_id IS NOT NULL ORDER BY a.id LIMIT 1)  AS commessa_id,
       (SELECT fl.id FROM vendite.fatturazione_lotti fl
         ORDER BY fl.id DESC LIMIT 1)                            AS lotto_id;

CREATE TEMP TABLE tmp_f1_arr AS
SELECT vendite.fn_get_or_create_fattura_header(
         (SELECT lotto_id FROM tmp_refs_arr),
         (SELECT attivita_id FROM tmp_refs_arr)) AS id;

INSERT INTO vendite.fatture_riepiloghi_iva (fattura_id, imponibile, imposta, arrotondamento)
SELECT (SELECT id FROM tmp_f1_arr), 10.503, 0.712, 0;

SELECT ok((SELECT id FROM tmp_f1_arr) IS NOT NULL,
  '1) Fixture: fattura di test creata con il suo riepilogo IVA');

SELECT vendite.fn_ricalcola_totali_fattura((SELECT id FROM tmp_f1_arr));

CREATE TEMP TABLE tmp_giro1_arr AS
SELECT f.totale_a_pagare, f.arrotondamento_precedente, f.arrotondamento_attuale,
       f.billing_account_id, f.utility_id, f.tipo_doc_fiscale_id,
       f.emittente_soggetto_ruolo_id, f.valuta_id,
       f.termine_pagamento_id, f.modalita_pagamento_id
  FROM vendite.fatture f WHERE f.id = (SELECT id FROM tmp_f1_arr);

SELECT isnt(
  (SELECT arrotondamento_attuale FROM tmp_giro1_arr), 0::numeric,
  '2) La fixture produce un arrotondamento non nullo (altrimenti non prova nulla)');

-- ============================================================
-- 1) Idempotenza del ricalcolo (D-N pezzo 2)
-- ============================================================
SELECT vendite.fn_ricalcola_totali_fattura((SELECT id FROM tmp_f1_arr));

SELECT is(
  (SELECT f.totale_a_pagare FROM vendite.fatture f WHERE f.id = (SELECT id FROM tmp_f1_arr)),
  (SELECT totale_a_pagare FROM tmp_giro1_arr),
  '3) Idempotenza: il secondo ricalcolo non sposta il totale');

SELECT ok(
  (SELECT f.arrotondamento_precedente IS NOT DISTINCT FROM g.arrotondamento_precedente
      AND f.arrotondamento_attuale    IS NOT DISTINCT FROM g.arrotondamento_attuale
     FROM vendite.fatture f, tmp_giro1_arr g
    WHERE f.id = (SELECT id FROM tmp_f1_arr)),
  '4) Idempotenza: la scomposizione precedente/attuale resta identica');

SELECT is(
  (SELECT vendite.fn_get_arrotondamento_scope(
            g.billing_account_id, g.utility_id, g.tipo_doc_fiscale_id,
            g.emittente_soggetto_ruolo_id, g.valuta_id,
            g.termine_pagamento_id, g.modalita_pagamento_id)
     FROM tmp_giro1_arr g),
  (SELECT arrotondamento_attuale FROM tmp_giro1_arr),
  '5) Idempotenza: il saldo d ambito non raddoppia dopo due ricalcoli');

-- ============================================================
-- 2) Separazione degli ambiti (C-20)
-- ============================================================
-- Il termine diverge per la via reale: si mette sulla commessa e la catena lo
-- raccoglie. Il bypass GUC e' per il guard di immutabilita' 3b.0-c, che in
-- esercizio deve continuare a impedirlo.
SELECT set_config('zeroerp.maintenance_reset_lotto_draft', 'on', true);
UPDATE vendite.commesse
   SET termine_pagamento_id = (SELECT tp.id FROM config.termini_pagamento tp
                                WHERE tp.attivo IS TRUE
                                  AND tp.id IS DISTINCT FROM (SELECT termine_pagamento_id FROM tmp_giro1_arr)
                                ORDER BY tp.id LIMIT 1)
 WHERE id = (SELECT commessa_id FROM tmp_refs_arr);
SELECT set_config('zeroerp.maintenance_reset_lotto_draft', 'off', true);

CREATE TEMP TABLE tmp_f2_arr AS
SELECT vendite.fn_get_or_create_fattura_header(
         (SELECT lotto_id FROM tmp_refs_arr),
         (SELECT attivita_id FROM tmp_refs_arr)) AS id;

INSERT INTO vendite.fatture_riepiloghi_iva (fattura_id, imponibile, imposta, arrotondamento)
SELECT (SELECT id FROM tmp_f2_arr), 20.507, 1.214, 0;

SELECT vendite.fn_ricalcola_totali_fattura((SELECT id FROM tmp_f2_arr));

SELECT ok(
  (SELECT f2.termine_pagamento_id IS DISTINCT FROM g.termine_pagamento_id
     FROM vendite.fatture f2, tmp_giro1_arr g
    WHERE f2.id = (SELECT id FROM tmp_f2_arr))
  AND (SELECT vendite.fn_get_arrotondamento_scope(
                g.billing_account_id, g.utility_id, g.tipo_doc_fiscale_id,
                g.emittente_soggetto_ruolo_id, g.valuta_id,
                g.termine_pagamento_id, g.modalita_pagamento_id)
         FROM tmp_giro1_arr g) = (SELECT arrotondamento_attuale FROM tmp_giro1_arr),
  '6) Separazione: la seconda fattura ha un altro termine e NON tocca il saldo della prima');

-- Il rerun della prima non deve muovere la seconda: sono ambiti diversi, e se
-- si passassero il saldo il totale della seconda cambierebbe da solo.
CREATE TEMP TABLE tmp_f2_prima_arr AS
SELECT totale_a_pagare, arrotondamento_precedente, arrotondamento_attuale
  FROM vendite.fatture WHERE id = (SELECT id FROM tmp_f2_arr);

SELECT vendite.fn_ricalcola_totali_fattura((SELECT id FROM tmp_f1_arr));

SELECT ok(
  (SELECT f.totale_a_pagare = p.totale_a_pagare
      AND f.arrotondamento_precedente IS NOT DISTINCT FROM p.arrotondamento_precedente
      AND f.arrotondamento_attuale    IS NOT DISTINCT FROM p.arrotondamento_attuale
     FROM vendite.fatture f, tmp_f2_prima_arr p
    WHERE f.id = (SELECT id FROM tmp_f2_arr)),
  '7) Separazione: rieseguire la prima non sposta totale ne scomposizione della seconda');

-- ============================================================
-- 3) Storno alla cancellazione (C-23 / D-N pezzo 3)
-- ============================================================
CREATE TEMP TABLE tmp_saldo_pre_arr AS
SELECT vendite.fn_get_arrotondamento_scope(
         g.billing_account_id, g.utility_id, g.tipo_doc_fiscale_id,
         g.emittente_soggetto_ruolo_id, g.valuta_id,
         g.termine_pagamento_id, g.modalita_pagamento_id) AS saldo,
       (SELECT f.arrotondamento_attuale FROM vendite.fatture f
         WHERE f.id = (SELECT id FROM tmp_f1_arr))        AS quota
  FROM tmp_giro1_arr g;

SELECT vendite.fn_cleanup_fatture_by_ids(ARRAY[(SELECT id FROM tmp_f1_arr)], NULL::uuid);

SELECT is(
  (SELECT vendite.fn_get_arrotondamento_scope(
            g.billing_account_id, g.utility_id, g.tipo_doc_fiscale_id,
            g.emittente_soggetto_ruolo_id, g.valuta_id,
            g.termine_pagamento_id, g.modalita_pagamento_id)
     FROM tmp_giro1_arr g),
  (SELECT saldo - quota FROM tmp_saldo_pre_arr),
  '8) Storno: cancellare la fattura restituisce all ambito il suo arrotondamento');

-- Una fattura che non e' mai passata dal ricalcolo non ha lasciato niente in
-- nessun ambito: il cleanup non deve INVENTARE una riga con saldo negativo.
-- E' la ragione per cui lo storno e' un UPDATE e non un upsert.
CREATE TEMP TABLE tmp_f3_arr AS
SELECT vendite.fn_get_or_create_fattura_header(
         (SELECT lotto_id FROM tmp_refs_arr),
         (SELECT attivita_id FROM tmp_refs_arr)) AS id;

UPDATE vendite.fatture SET arrotondamento_attuale = 0.01,
                           tipo_doc_fiscale_id = tipo_doc_fiscale_id
 WHERE id = (SELECT id FROM tmp_f3_arr);

CREATE TEMP TABLE tmp_righe_scope_arr AS
SELECT count(*)::int AS n FROM vendite.fatture_arrotondamenti_scope;

SELECT vendite.fn_cleanup_fatture_by_ids(ARRAY[(SELECT id FROM tmp_f3_arr)], NULL::uuid);

SELECT is(
  (SELECT count(*)::int FROM vendite.fatture_arrotondamenti_scope),
  (SELECT n FROM tmp_righe_scope_arr),
  '9) Storno: il cleanup non crea righe d ambito che non esistevano');

-- ============================================================
-- 4) L over-free del lock_batch_id (C-22)
-- ============================================================
-- Il primo ramo del ripristino attivita' prende tutto il batch. E' corretto
-- nel reset GLOBALE — libera anche le attivita' agganciate al lotto che non
-- sono mai diventate riga — ed e' esattamente il motivo per cui il reset
-- PER-FATTURA non deve passare quel parametro.
CREATE TEMP TABLE tmp_batch_arr AS
SELECT a.lock_batch_id AS batch, count(*)::int AS attivita
  FROM vendite.attivita_fatturabili a
 WHERE a.lock_batch_id IS NOT NULL
 GROUP BY a.lock_batch_id ORDER BY count(*) DESC LIMIT 1;

SELECT CASE
  WHEN (SELECT count(*) FROM tmp_batch_arr) = 0
    THEN skip('nessun batch di attivita su cui misurare', 2)
  ELSE is(
    (SELECT c.updated_attivita
       FROM vendite.fn_cleanup_fatture_by_ids(
              ARRAY[(SELECT id FROM tmp_f2_arr)], (SELECT batch FROM tmp_batch_arr)) c),
    (SELECT attivita FROM tmp_batch_arr),
    '10) C-22: con il lock_batch_id il cleanup libera TUTTE le attivita del batch')
END;

-- Stessa cancellazione, senza il batch: tocca solo cio' che appartiene alla
-- fattura. La fattura del test e' senza righe, quindi zero — ed e' il punto:
-- prima, resettarne una ne liberava quindici.
CREATE TEMP TABLE tmp_f4_arr AS
SELECT vendite.fn_get_or_create_fattura_header(
         (SELECT lotto_id FROM tmp_refs_arr),
         (SELECT attivita_id FROM tmp_refs_arr)) AS id;

SELECT CASE
  WHEN (SELECT count(*) FROM tmp_batch_arr) = 0
    THEN skip('nessun batch di attivita su cui misurare', 1)
  ELSE is(
    (SELECT c.updated_attivita
       FROM vendite.fn_cleanup_fatture_by_ids(ARRAY[(SELECT id FROM tmp_f4_arr)], NULL::uuid) c),
    0,
    '11) C-22: senza lock_batch_id le attivita delle altre fatture restano intatte')
END;

-- Presidio della regressione vera e propria: che il chiamante per-fattura
-- passi NULL. Il giro completo non e' esercitabile qui, quindi si verifica il
-- punto esatto in cui il difetto viveva.
-- ⚠️ Questa asserzione cerca la funzione PER NOME: se il nome cambia, la
-- sottoquery non trova niente e il test diventa rosso per il motivo sbagliato
-- («la funzione non esiste») invece che per quello giusto («il corpo non passa
-- piu' NULL»). E' gia' successo: rinominata in fn_elimina_fattura_da_lotto il
-- 2026-08-04 (RD-7), quando il perimetro del LOTTO e' passato da DRAFT a
-- pre-fiscale e il vecchio nome ha smesso di dire la verita'.
SELECT ok(
  (SELECT pg_get_functiondef(p.oid) LIKE '%fn_cleanup_fatture_by_ids(ARRAY[p_fattura_id], NULL%'
     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite' AND p.proname = 'fn_elimina_fattura_da_lotto'),
  '12) C-22: il reset per-fattura passa NULL come lock_batch_id');

SELECT * FROM finish();

ROLLBACK;
