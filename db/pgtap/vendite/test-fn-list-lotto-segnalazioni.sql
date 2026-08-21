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

SELECT plan(11);

-- ============================================================
-- 0) Riferimenti
-- ============================================================
CREATE TEMP TABLE tmp_refs_sg AS
WITH ba AS (
  SELECT b.id, b.utility_id
    FROM anagrafiche.billing_account b
   ORDER BY b.data_insert DESC NULLS LAST, b.id DESC
   LIMIT 1
)
SELECT (SELECT id FROM vendite.registri_fatturazione
         WHERE attivo IS TRUE ORDER BY data_insert DESC NULLS LAST, id DESC LIMIT 1) AS registro_id,
       ba.id        AS billing_account_id,
       ba.utility_id AS utility_id,
       (SELECT m.tipo_doc_fiscale_id
          FROM vendite.tipi_doc_fiscale_registri m
          JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
         WHERE t.attivo IS TRUE ORDER BY m.id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id,
       script.fn_pgtap_emittente_sr_operatore() AS emittente_soggetto_ruolo_id,
       (SELECT id FROM config.stati_doc_fiscale
         WHERE codice_interno = 'DRAFT' AND attivo IS TRUE ORDER BY id LIMIT 1) AS stato_draft_id
  FROM ba;

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
  p_competenza_mese             => date_trunc('month', current_date)::date,
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
  SELECT r.registro_id, current_date, r.emittente_soggetto_ruolo_id,
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

SELECT * FROM finish();
ROLLBACK;
