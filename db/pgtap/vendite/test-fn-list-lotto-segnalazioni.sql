-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_lotto_segnalazioni — la union, i filtri, l'ordine
--       (changeSet 20260821-44, cantiere brief-db-liste-drawer-lotto L2/P-7)
-- ------------------------------------------------------------
-- Indice test (plan 11)
-- 1)  Riferimenti minimi presenti
-- 2)  Fixture: 4 segnalazioni, 2 per origine
-- 3)  La union le restituisce tutte, con le due origini
-- 4)  ⭐ Le due meta' sono COMPLEMENTARI: documento/importo solo su FATTURA,
--     fase solo su LOTTO
-- 5)  `p_solo_attive` esclude la segnalazione ritirata
-- 6)  ⛔ `livello = I` restituisce SOLO righe LOTTO (i due alfabeti differiscono)
-- 7)  ⭐ L'ordine di default e' per GRAVITA', non per alfabeto: la C prima della I
-- 8)  ⚠️ NULLS LAST su `importo desc`: le righe senza importo restano in coda
-- 9)  Un nome fuori whitelist solleva...
-- 10) ...e `messaggio` e' fuori whitelist di proposito
-- 11) Un lotto non visibile SOLLEVA, non risponde zero righe
-- 12) ⭐ Il BERSAGLIO esce dove c'e'
-- 13) ⛔ ...e NON e' `fattura_id`: sono due entita' diverse
-- 14) Il degrado: dove non c'e', `target` e' NULL — senza filtri per livello
-- 15) 🔴 Il codice del ramo LOTTO scritto dal BACKEND (chiave `code`) si legge
--
-- Scopo:
--  - La 7 e' quella che misura il difetto piu' facile da non vedere: `C/W/I` in
--    ordine alfabetico mette la C per prima PER CASO. Con una fixture che ha
--    solo C e W il test sarebbe verde anche senza il rango — per questo la
--    fixture ha anche una I, che in alfabeto starebbe IN MEZZO.
--  - La 10 presidia una scelta, non un comportamento: `messaggio` sta fuori
--    dalla whitelist perche' il seed della lista lo offre `ordinabile = f`, e
--    una capacita' che il seed non offre e' esattamente cio' che il presidio
--    dei seed segnala come irraggiungibile.
--  - La 11 e' la forma «uno zero non e' un dato»: un lotto fuori perimetro non
--    deve leggersi come un lotto senza segnalazioni.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- 0) Riferimenti
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba, gia' legato all'azienda di chi agisce):
--   prima si pescava l'ultimo billing account del DB, e da zero non c'era.
--   Tipo documento (dal ponte tipo->registro), valuta e stato restano letture
--   di catalogo; registro ed emittente sono gia' quelli di chi agisce.
CREATE TEMP TABLE tmp_cli_sg AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('lista segnalazioni lotto');

CREATE TEMP TABLE tmp_refs_sg AS
SELECT script.fn_pgtap_registro_fattura() AS registro_id,
       ba.billing_account_id AS billing_account_id,
       ba.utility_id         AS utility_id,
       (SELECT m.tipo_doc_fiscale_id
          FROM vendite.tipi_doc_fiscale_registri m
          JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
         WHERE t.attivo IS TRUE ORDER BY m.id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id,
       script.fn_pgtap_emittente_sr_operatore() AS emittente_soggetto_ruolo_id,
       (SELECT id FROM config.stati_doc_fiscale
         WHERE codice_interno = 'DRAFT' AND attivo IS TRUE ORDER BY id LIMIT 1) AS stato_draft_id
  FROM tmp_cli_sg ba;

SELECT ok(
  (SELECT registro_id IS NOT NULL AND tipo_doc_fiscale_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL AND stato_draft_id IS NOT NULL
     FROM tmp_refs_sg),
  '1) riferimenti minimi presenti'
);

-- ============================================================
-- 1) Lotto + fattura + le quattro segnalazioni
--    ⚠️ Padre e figlio in istruzioni separate: in una CTE sola
--    condividerebbero la snapshot e una policy che risolve il perimetro dal
--    padre non lo troverebbe.
-- ============================================================
CREATE TEMP TABLE tmp_lotto_sg AS
SELECT vendite.fn_create_fatturazione_lotto(
  p_competenza_mese             => date_trunc('month', script.fn_data_operativa())::date,
  p_tipo_doc_fiscale_id         => (SELECT tipo_doc_fiscale_id FROM tmp_refs_sg),
  p_utility_id                  => (SELECT utility_id FROM tmp_refs_sg),
  p_billing_account_id          => NULL,
  p_lock_batch_id               => NULL,
  p_meta                        => jsonb_build_object('test_scope', 'pgtap_segnalazioni'),
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_sg)
) AS lotto_id;

CREATE TEMP TABLE tmp_fattura_sg AS
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, stato_doc_fiscale_id,
      totale_doc, totale_a_pagare, cliente_snapshot, meta)
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id,
         r.billing_account_id, r.tipo_doc_fiscale_id, r.valuta_id, r.utility_id,
         r.stato_draft_id, 123.45, 123.45,
         -- Lo snapshot e' la sorgente di `documento_display`: qui si mette a
         -- mano cio' che in un giro vero scrive il task DRAFT.
         jsonb_build_object('denominazione', 'PGTAP Cliente Segnalazioni'),
         jsonb_build_object('test_scope', 'pgtap_segnalazioni')
    FROM tmp_refs_sg r
  RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, stato_doc_fiscale_id)
SELECT (SELECT lotto_id FROM tmp_lotto_sg),
       (SELECT id FROM tmp_fattura_sg),
       (SELECT stato_draft_id FROM tmp_refs_sg);

-- Due segnalazioni di FATTURA: una critica viva, una warning gia' ritirata.
INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta)
VALUES
  ((SELECT id FROM tmp_fattura_sg), now(), 'pgtap critica viva', 'C', FALSE,
   jsonb_build_object('task', 'pgtap', 'error_code', 'E_SCADENZE_TERMINE_MANCANTE')),
  ((SELECT id FROM tmp_fattura_sg), now(), 'pgtap warning ritirata', 'W', TRUE,
   jsonb_build_object('task', 'pgtap'));

-- Due di LOTTO, scritte dall'imbuto vero: una info e una critica.
-- ⚠️ `I` serve alla 7: in alfabeto sta FRA C e W, quindi e' l'unico livello che
--    distingue un ordinamento per gravita' da uno per valore.
SELECT vendite.fn_log_pipeline_fase(
  (SELECT lotto_id FROM tmp_lotto_sg), NULL, 'Fase informativa', 'I',
  'pgtap info di lotto', jsonb_build_object('task', 'pgtap'));

SELECT vendite.fn_log_pipeline_fase(
  (SELECT lotto_id FROM tmp_lotto_sg), NULL, 'Fase critica', 'C',
  'pgtap critica di lotto', jsonb_build_object('task', 'pgtap'), 'E_PARAMETRO_INVALIDO');

SELECT is(
  (SELECT (SELECT count(*)::int FROM vendite.fatture_log fl
            WHERE fl.fattura_id = (SELECT id FROM tmp_fattura_sg))::text
       || '|' ||
          (SELECT count(*)::int FROM vendite.fatturazione_lotti_log ll
            WHERE ll.lotto_id = (SELECT lotto_id FROM tmp_lotto_sg))::text),
  '2|2',
  '2) fixture: 4 segnalazioni, 2 per origine'
);

-- ============================================================
-- 2) La union
--    `p_solo_attive => false` per vederle tutte e quattro.
-- ============================================================
SELECT is(
  (SELECT count(*)::int || '|' || count(DISTINCT s.origine)::int
     FROM vendite.fn_list_lotto_segnalazioni(
            (SELECT lotto_id FROM tmp_lotto_sg), NULL, NULL, FALSE) s),
  '4|2',
  '3) la union restituisce tutte e quattro, con le due origini'
);

-- ⭐ Le due meta' sono COMPLEMENTARI: dove una ha il valore, l'altra ha NULL.
--    Non e' un difetto da nascondere, e' la forma del dominio.
SELECT is(
  (SELECT string_agg(
            s.origine || ':' ||
            (s.documento_display IS NOT NULL)::text || ',' ||
            (s.importo IS NOT NULL)::text || ',' ||
            (s.fase IS NOT NULL)::text,
            ' ' ORDER BY s.origine, s.id)
     FROM vendite.fn_list_lotto_segnalazioni(
            (SELECT lotto_id FROM tmp_lotto_sg), NULL, NULL, FALSE) s),
  'FATTURA:true,true,false FATTURA:true,true,false LOTTO:false,false,true LOTTO:false,false,true',
  '4) documento e importo solo su FATTURA, fase solo su LOTTO'
);

-- ============================================================
-- 3) I filtri
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM vendite.fn_list_lotto_segnalazioni(
            (SELECT lotto_id FROM tmp_lotto_sg)) s),
  3,
  '5) il default esclude la segnalazione ritirata'
);

-- ⛔ `fatture_log.status` a CHECK ammette solo (W,C): una riga INFO e' per
--    costruzione di origine LOTTO. Il filtro lo mostra invece di dichiararlo.
SELECT is(
  (SELECT string_agg(DISTINCT s.origine, ',')
     FROM vendite.fn_list_lotto_segnalazioni(
            (SELECT lotto_id FROM tmp_lotto_sg), NULL, 'I', FALSE) s),
  'LOTTO',
  '6) livello = I restituisce solo righe LOTTO'
);

-- ============================================================
-- 4) L'ordine
-- ============================================================
-- ⭐ Per GRAVITA', non per alfabeto. Con C, W e I in campo l'alfabeto darebbe
--    C, I, W: e' proprio la I in mezzo che distingue le due regole.
SELECT is(
  (SELECT string_agg(s.livello, '' ORDER BY o)
     FROM (SELECT row_number() OVER () AS o, t.livello
             FROM vendite.fn_list_lotto_segnalazioni(
                    (SELECT lotto_id FROM tmp_lotto_sg), NULL, NULL, FALSE) t) s),
  'CCWI',
  '7) l''ordine di default e'' per gravita'': prima le C, poi la W, infine la I'
);

-- ⚠️ Su DESC PostgreSQL mette i NULL in TESTA: senza NULLS LAST esplicito
--    «per importo, dal piu' grande» comincerebbe dalle righe di lotto, che un
--    importo non ce l'hanno.
SELECT is(
  (SELECT string_agg((s.importo IS NOT NULL)::text, ',' ORDER BY o)
     FROM (SELECT row_number() OVER () AS o, t.importo
             FROM vendite.fn_list_lotto_segnalazioni(
                    (SELECT lotto_id FROM tmp_lotto_sg), NULL, NULL, FALSE,
                    FALSE, 500, 0, 'importo', 'desc') t) s),
  'true,true,false,false',
  '8) NULLS LAST su importo desc: le righe senza importo restano in coda'
);

-- ============================================================
-- 5) La whitelist e il perimetro
-- ============================================================
SELECT throws_ok(
  $$SELECT * FROM vendite.fn_list_lotto_segnalazioni(
      (SELECT lotto_id FROM tmp_lotto_sg), NULL, NULL, FALSE, FALSE, 10, 0, 'meta', 'asc')$$,
  'P0001',
  NULL,
  '9) un nome fuori whitelist solleva'
);

-- ⚠️ Presidia una SCELTA: `messaggio` e' testo libero e il seed della lista lo
--    offre `ordinabile = f`. Metterlo in whitelist creerebbe una capacita' che
--    la lista non espone — la seconda direzione del presidio dei seed.
SELECT throws_ok(
  $$SELECT * FROM vendite.fn_list_lotto_segnalazioni(
      (SELECT lotto_id FROM tmp_lotto_sg), NULL, NULL, FALSE, FALSE, 10, 0, 'messaggio', 'asc')$$,
  'P0001',
  NULL,
  '10) ...e `messaggio` e'' fuori whitelist di proposito'
);

-- ⛔ Un lotto che non si vede NON e' un lotto senza segnalazioni.
SELECT throws_ok(
  $$SELECT * FROM vendite.fn_list_lotto_segnalazioni(999999999::bigint)$$,
  'P0001',
  NULL,
  '11) un lotto non visibile solleva, non risponde zero righe'
);


-- ============================================================
-- 12-15) Il bersaglio, e il codice che il backend scrive
-- ============================================================
-- ⚠️ Le due righe di questo blocco si inseriscono QUI e non nella fixture in
--   testa, di proposito: le asserzioni 1-11 contano le segnalazioni, e due
--   righe in piu' le avrebbero rotte tutte. Un test che allarga la fixture
--   condivisa per il proprio caso costringe a riscrivere le verifiche degli
--   altri — e a quel punto non si sa piu' se il rosso e' del codice o del
--   ritocco.

-- ⭐ La riga col BERSAGLIO. `bersagli` e' la chiave che il backend scrive in
--   `meta` al momento dell'errore; la funzione la espone come `target`.
--   ⛔ L'id punta a un documento DIVERSO da quello che ha fallito: e' tutto il
--   senso del bersaglio, ed e' il test 13 a verificarlo.
INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta)
VALUES
  ((SELECT id FROM tmp_fattura_sg), now(), 'pgtap critica con bersaglio', 'C', FALSE,
   jsonb_build_object(
       'task', 'pgtap',
       'error_code', 'E_FATTURA_RETTIFICATA_SENZA_NUMERO',
       'bersagli', jsonb_build_array(
           jsonb_build_object('id', ((SELECT id FROM tmp_fattura_sg) + 1)::text,
                              'type', 'FATTURA'))));

-- 🔴 E una riga di LOTTO scritta **come la scrive il BACKEND**: chiave `code`,
--   non `error_code`. INSERT diretto di proposito — passare da
--   `fn_log_pipeline_fase` userebbe la chiave del DB e non riprodurrebbe il
--   caso. Misurato il 2026-08-24: le righe col codice sono 17, tutte scritte
--   cosi' e tutte di livello `C`.
INSERT INTO vendite.fatturazione_lotti_log
    (lotto_id, data_ora, messaggio, status, disabilitato, meta)
VALUES
  ((SELECT lotto_id FROM tmp_lotto_sg), now(), 'pgtap critica di lotto dal BE', 'C', FALSE,
   jsonb_build_object('scope', 'LOTTO',
                      'function_name', 'vendite.run_lotto_pipeline',
                      'code', 'E_LOTTO_FATTURE_NUMERATE'));
CREATE TEMP TABLE tmp_sg_bers AS
SELECT s.origine, s.livello, s.error_code, s.fattura_id, s.target, s.messaggio
  FROM vendite.fn_list_lotto_segnalazioni(
         p_lotto_id => (SELECT lotto_id FROM tmp_lotto_sg),
         p_solo_attive => false, p_limit => 100) s;

-- 12) Esce dove c'e'.
SELECT is(
  (SELECT b.target FROM tmp_sg_bers b WHERE b.messaggio = 'pgtap critica con bersaglio'),
  jsonb_build_array(jsonb_build_object('id', ((SELECT id FROM tmp_fattura_sg) + 1)::text,
                                       'type', 'FATTURA')),
  '12) il bersaglio esce, e l''array passa INTATTO (elementi id/type)'
);

-- 13) ⛔ E non e' il documento che ha fallito.
--     E' il vincolo che conta piu' di tutti nella richiesta: `fattura_id` e' cio'
--     che l'operatore sta gia' guardando, il bersaglio e' dove deve ANDARE.
SELECT isnt(
  (SELECT b.target -> 0 ->> 'id' FROM tmp_sg_bers b
    WHERE b.messaggio = 'pgtap critica con bersaglio'),
  (SELECT b.fattura_id::text FROM tmp_sg_bers b
    WHERE b.messaggio = 'pgtap critica con bersaglio'),
  '13) il bersaglio NON e'' fattura_id: ha fallito un documento, se ne apre un altro'
);

-- 14) Il degrado, e senza filtri per livello.
--     ⚠️ Si asserisce su una riga `C` e su una `W`: se il bersaglio fosse legato
--     alla criticita', la prima lo avrebbe e la seconda no per la ragione
--     sbagliata. Qui entrambe le righe senza bersaglio sono NULL, e una delle
--     due e' critica.
SELECT is(
  (SELECT count(*)::int FROM tmp_sg_bers b
    WHERE b.origine = 'FATTURA' AND b.target IS NULL),
  2,
  '14) dove il bersaglio non c''e'' la colonna e'' NULL, a prescindere dal livello'
);

-- 15) 🔴 Il codice scritto dal BACKEND si legge.
--     Prima si leggeva solo `error_code`, e questa riga sarebbe stata senza
--     codice — proprio una delle critiche, cioe' quelle dove serve.
SELECT is(
  (SELECT b.error_code FROM tmp_sg_bers b WHERE b.messaggio = 'pgtap critica di lotto dal BE'),
  'E_LOTTO_FATTURE_NUMERATE'::text,
  '15) sul ramo LOTTO si legge anche la chiave `code`, quella del backend'
);

SELECT * FROM finish();
ROLLBACK;
