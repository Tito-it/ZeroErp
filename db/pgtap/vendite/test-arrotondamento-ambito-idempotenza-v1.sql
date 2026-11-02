-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): attivita', lotto e
--   batch si COSTRUISCONO. Prima si pescavano «la prima attivita' con commessa»,
--   «l'ultimo lotto DRAFT» e «il batch di attivita' piu' grosso»: su un database
--   ricostruito da zero non ci sono, il file moriva nella fixture e il 10-11 si
--   sarebbero saltati da soli. Ora due commesse emittibili dello stesso cliente
--   (dbops.fn_pgtap_crea_commessa), un lotto DRAFT dalla sua madre e il PULL vero
--   col marchio del lotto: il batch del 10 e' quel marchio, con DUE attivita'.
-- rev 2026-10-24 (brief-modello-documento-vendita R-3/R-4): la sorgente ROOT
--   delle due commesse la scrive il builder (p_con_sorgente_root), non piu' un
--   INSERT del test; il lotto DRAFT nasce da dbops.fn_pgtap_crea_lotto, del
--   cliente (p_del_cliente) e col tipo documento della riga di commessa, come
--   prima lo faceva la madre chiamata col billing account. Asserzioni invariate.
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
-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_commessa (rev
--   2026-10-24), sull'operatore dell'azienda
--   che costruisce (fn_pgtap_crea_mondo_cliente, ramo «nessun contesto»). La
--   seconda commessa e' dello STESSO cliente: entra nello stesso lotto e nello
--   stesso batch.
CREATE TEMP TABLE tmp_comm_arr AS
SELECT 1 AS n, c.* FROM dbops.fn_pgtap_crea_commessa('arrotondamento ambito', 'PRONTA_FATTURAZIONE',
                                                      p_con_sorgente_root => true) c;

INSERT INTO tmp_comm_arr
SELECT 2, c.* FROM dbops.fn_pgtap_crea_commessa('arrotondamento ambito 2', 'PRONTA_FATTURAZIONE',
                                                (SELECT billing_account_id FROM tmp_comm_arr WHERE n = 1),
                                                p_con_sorgente_root => true) c;

SELECT plan(12);

-- ============================================================
-- 0) Fixture
-- ============================================================
-- Si parte da un'attivita' con commessa (serve al test 6 per far divergere il
-- termine per la via reale) e da un lotto DRAFT. Gli importi hanno tre
-- decimali apposta: con due, il totale cade gia' tondo e l'arrotondamento
-- sarebbe zero — cioe' la fixture non eserciterebbe nulla. Il test 2 lo
-- verifica invece di darlo per scontato.
-- ⚠️ Il pull PRETENDE una sorgente ROOT: la scrive il builder
--   (p_con_sorgente_root, sorgente COMMESSA, chiave = id della commessa).

-- ⚠️ Solo un lotto in DRAFT: `fn_get_or_create_fattura_header` crea la
--    fattura in DRAFT e il guard di coerenza vuole lo stesso stato sul lotto
--    (il 2026-08-16 un lotto EMESSA pescato fece fallire la fixture). Il lotto
--    lo da' dbops.fn_pgtap_crea_lotto (madre sotto), nello stato iniziale, del
--    cliente e col tipo documento della riga di commessa, che il pull confronta.
CREATE TEMP TABLE tmp_lotto_arr AS
SELECT l.lotto_id
  FROM (SELECT c.billing_account_id, ca.tipo_doc_fiscale_id
          FROM tmp_comm_arr c
          JOIN vendite.commesse_attivita ca ON ca.id = c.attivita_id
         WHERE c.n = 1) r,
       dbops.fn_pgtap_crea_lotto('arrotondamento ambito', 'DRAFT', r.billing_account_id,
                                 r.tipo_doc_fiscale_id, p_del_cliente => true) l;

-- Le attivita' fatturabili nascono dal PULL vero, col marchio del lotto: e' il
--   batch su cui il 10 misura.
CREATE TEMP TABLE tmp_pull_arr AS
SELECT p.*
  FROM tmp_comm_arr c,
       vendite.fn_emit_attivita_fatturabili_da_commessa(
         p_commessa_id   => c.commessa_id,
         p_emit_batch_id => (SELECT fl.lock_batch_id FROM vendite.fatturazione_lotti fl
                              WHERE fl.id = (SELECT lotto_id FROM tmp_lotto_arr))) p;

CREATE TEMP TABLE tmp_refs_arr AS
SELECT af.id AS attivita_id, af.commessa_id, l.lotto_id
  FROM vendite.attivita_fatturabili af, tmp_lotto_arr l
 WHERE af.commessa_attivita_id = (SELECT attivita_id FROM tmp_comm_arr WHERE n = 1);

CREATE TEMP TABLE tmp_f1_arr AS
SELECT vendite.fn_get_or_create_fattura_header(
         (SELECT lotto_id FROM tmp_refs_arr),
         (SELECT attivita_id FROM tmp_refs_arr)) AS id;

INSERT INTO vendite.fatture_riepiloghi_iva (fattura_id, imponibile, imposta, arrotondamento)
SELECT (SELECT id FROM tmp_f1_arr), 10.503, 0.712, 0;

SELECT ok((SELECT id FROM tmp_f1_arr) IS NOT NULL
          AND (SELECT count(*) FROM tmp_refs_arr) = 1
          AND (SELECT sum(inserted_rows) FROM tmp_pull_arr) = 2,
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
-- ⭐ rev 2026-10-24: il batch e' il marchio del lotto del test, e le sue attivita'
--   sono le DUE del pull (una per commessa), nessuna ancora diventata riga. Prima
--   era «il batch piu' grosso del database», e su un database vuoto il 10 e l'11
--   si saltavano: ora non c'e' piu' un ramo di salto, la fixture lo garantisce.
CREATE TEMP TABLE tmp_batch_arr AS
SELECT fl.lock_batch_id AS batch,
       (SELECT count(*)::int FROM vendite.attivita_fatturabili a
         WHERE a.emit_batch_id = fl.lock_batch_id) AS attivita
  FROM vendite.fatturazione_lotti fl
 WHERE fl.id = (SELECT lotto_id FROM tmp_refs_arr);

SELECT is(
    (SELECT c.updated_attivita
       FROM vendite.fn_cleanup_fatture_by_ids(
              ARRAY[(SELECT id FROM tmp_f2_arr)], (SELECT batch FROM tmp_batch_arr)) c),
    (SELECT attivita FROM tmp_batch_arr),
    '10) C-22: con il lock_batch_id il cleanup libera TUTTE le attivita del batch');

-- Stessa cancellazione, senza il batch: tocca solo cio' che appartiene alla
-- fattura. La fattura del test e' senza righe, quindi zero — ed e' il punto:
-- prima, resettarne una ne liberava quindici.
CREATE TEMP TABLE tmp_f4_arr AS
SELECT vendite.fn_get_or_create_fattura_header(
         (SELECT lotto_id FROM tmp_refs_arr),
         (SELECT attivita_id FROM tmp_refs_arr)) AS id;

SELECT is(
    (SELECT c.updated_attivita
       FROM vendite.fn_cleanup_fatture_by_ids(ARRAY[(SELECT id FROM tmp_f4_arr)], NULL::uuid) c),
    0,
    '11) C-22: senza lock_batch_id le attivita delle altre fatture restano intatte');

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
