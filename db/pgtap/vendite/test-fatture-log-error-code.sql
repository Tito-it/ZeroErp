-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il CODICE di dominio finisce nel log — meta->>'error_code'
--       (changeSet 20260821-39/-40/-41, cantiere brief-db-liste-drawer-lotto L1)
-- ------------------------------------------------------------
-- Indice test (plan 10)
-- 1) Riferimenti minimi presenti
-- 2) Fixture: lotto + fattura DRAFT senza termine di pagamento
-- 3) ⭐ Il giro fallisce sulla fattura e ne marca UNA
-- 4) ⭐ Il log porta `meta->>'error_code'` = il codice di dominio vero
-- 5) ⛔ ...e NON e' lo sqlstate: `P0001` non compare come codice
-- 6) Lo sqlstate resta al suo posto, accanto e non al posto del codice
-- 7) `fn_log_pipeline_fase` scrive il codice quando glielo si passa
-- 8) ⚠️ ...e NON crea la chiave quando non c'e' niente da scrivere
-- 9) ⭐ L'ALTRA SPECIE: un codice DICHIARATO (W_) su una condizione propria
-- 10) I due W_ nuovi esistono a catalogo con la loro classe
--
-- Scopo:
--  - Presidia la ragione per cui i tre changeSet esistono. Prima, i log
--    registravano `RETURNED_SQLSTATE`, che per un errore di dominio vale
--    SEMPRE `P0001`: una chiave che risponde sempre lo stesso valore. Il
--    codice che DICE QUALE errore e' stato viaggia nel campo `CONSTRAINT`
--    della diagnostica, ed e' quello su cui il backend mappa status HTTP e
--    ui_action.
--  - L'asserzione 5 e' quella che misura il difetto: senza, un ritorno alla
--    forma vecchia lascerebbe il test verde (la chiave ci sarebbe comunque,
--    solo con dentro `P0001`).
--  - L'8 presidia lo `jsonb_strip_nulls`: una chiave presente e vuota, in
--    lista, e' una cella bianca indistinguibile da «non c'e'».
--
-- ⚠️ Il percorso e' quello REALE: si costruisce una fattura che fa sollevare
--    `E_SCADENZE_TERMINE_MANCANTE` alla funzione figlia, e si guarda che cosa
--    il wrapper di lotto scrive nel log. Non si simula la diagnostica.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- 0) Riferimenti
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba) e il tipo documento si legge dal
--   catalogo di seed config.tipi_doc_fiscale. Prima il BA era l'ultimo
--   inserito nel DB e il tipo veniva dalla prima mappatura
--   tipi_doc_fiscale_registri: da zero non c'erano.
CREATE TEMP TABLE tmp_cli_ec AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('fatture log error code');

CREATE TEMP TABLE tmp_refs_ec AS
WITH ba AS (
  SELECT c.billing_account_id AS id, c.utility_id
    FROM tmp_cli_ec c
)
SELECT script.fn_pgtap_registro_fattura() AS registro_id,
       ba.id                                        AS billing_account_id,
       ba.utility_id                                AS utility_id,
       (SELECT t.id
          FROM config.tipi_doc_fiscale t
         WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id,
       -- ⚠️ L'emittente non si pesca: si deriva da chi agisce, o le policy
       --    ef_whitelist negano fail-closed.
       script.fn_pgtap_emittente_sr_operatore()      AS emittente_soggetto_ruolo_id,
       (SELECT id FROM config.stati_doc_fiscale
         WHERE codice_interno = 'DRAFT' AND attivo IS TRUE ORDER BY id LIMIT 1) AS stato_draft_id,
       (SELECT id FROM vendite.fatturazione_pipeline
         WHERE attivo IS TRUE ORDER BY id LIMIT 1)   AS pipeline_id
  FROM ba;

SELECT ok(
  (SELECT registro_id IS NOT NULL
      AND billing_account_id IS NOT NULL
      AND tipo_doc_fiscale_id IS NOT NULL
      AND valuta_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL
      AND stato_draft_id IS NOT NULL
     FROM tmp_refs_ec),
  '1) riferimenti minimi presenti'
);

-- ============================================================
-- 1) Lotto + fattura SENZA termine di pagamento
--    ⚠️ Padre e figlio in due istruzioni separate: in una CTE sola
--    condividerebbero la snapshot, e una policy che risolve il perimetro dal
--    padre non lo troverebbe.
-- ============================================================
CREATE TEMP TABLE tmp_lotto_ec AS
SELECT vendite.fn_create_fatturazione_lotto(
  p_competenza_mese             => date_trunc('month', script.fn_data_operativa())::date,
  p_tipo_doc_fiscale_id         => (SELECT tipo_doc_fiscale_id FROM tmp_refs_ec),
  p_utility_id                  => (SELECT utility_id FROM tmp_refs_ec),
  p_billing_account_id          => NULL,
  p_lock_batch_id               => NULL,
  p_meta                        => jsonb_build_object('test_scope', 'pgtap_error_code'),
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_ec)
) AS lotto_id;

-- `termine_pagamento_id` volutamente NULL: e' la condizione che fa sollevare
-- E_SCADENZE_TERMINE_MANCANTE alla funzione figlia.
CREATE TEMP TABLE tmp_fattura_ec AS
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, stato_doc_fiscale_id,
      totale_a_pagare, termine_pagamento_id, meta)
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id,
         r.billing_account_id, r.tipo_doc_fiscale_id, r.valuta_id, r.utility_id,
         r.stato_draft_id, 100.00, NULL,
         jsonb_build_object('test_scope', 'pgtap_error_code')
    FROM tmp_refs_ec r
  RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, stato_doc_fiscale_id)
SELECT (SELECT lotto_id FROM tmp_lotto_ec),
       (SELECT id FROM tmp_fattura_ec),
       (SELECT stato_draft_id FROM tmp_refs_ec);

SELECT is(
  (SELECT (f.termine_pagamento_id IS NULL)::text || '|' ||
          (SELECT count(*)::int FROM vendite.fatturazione_lotti_fatture lf
            WHERE lf.lotto_id = (SELECT lotto_id FROM tmp_lotto_ec))::text
     FROM vendite.fatture f WHERE f.id = (SELECT id FROM tmp_fattura_ec)),
  'true|1',
  '2) fixture: fattura DRAFT senza termine, agganciata al lotto'
);

-- ============================================================
-- 2) Il giro: una fattura fallisce e viene marcata
--    ⚠️ Il verbo in un'istruzione SEPARATA dall'asserzione: nella stessa, la
--    snapshot di statement leggerebbe PRIMA delle scritture.
-- ============================================================
CREATE TEMP TABLE tmp_esito_ec AS
SELECT * FROM vendite.fn_genera_scadenze_lotto((SELECT lotto_id FROM tmp_lotto_ec));

SELECT is(
  (SELECT failed_rows::int FROM tmp_esito_ec),
  1,
  '3) il giro marca UNA fattura fallita, e non muore'
);

-- ============================================================
-- 3) ⭐ IL CODICE C'E', ED E' QUELLO VERO
-- ============================================================
CREATE TEMP TABLE tmp_log_ec AS
SELECT fl.meta, fl.status, fl.messaggio
  FROM vendite.fatture_log fl
 WHERE fl.fattura_id = (SELECT id FROM tmp_fattura_ec)
   AND fl.meta->>'task' = 'genera_scadenze_lotto'
 ORDER BY fl.id DESC
 LIMIT 1;

SELECT is(
  (SELECT meta->>'error_code' FROM tmp_log_ec),
  'E_SCADENZE_TERMINE_MANCANTE',
  '4) il log porta il CODICE di dominio in meta->>''error_code'''
);

-- ⛔ L'asserzione che misura davvero il difetto: prima della revisione il log
--    registrava lo sqlstate, e un ritorno a quella forma lascerebbe la 4
--    rossa ma la chiave presente. Qui si dice che il codice NON e' P0001 —
--    cioe' che non e' tornato a essere il valore che vale sempre lo stesso.
SELECT isnt(
  (SELECT meta->>'error_code' FROM tmp_log_ec),
  'P0001',
  '5) ...e non e'' lo sqlstate travestito da codice'
);

-- Lo sqlstate resta, accanto: serve a distinguere un errore di dominio da un
-- guasto di sistema, e non e' in concorrenza col codice.
SELECT is(
  (SELECT meta->>'sqlstate' FROM tmp_log_ec),
  'P0001',
  '6) lo sqlstate resta al suo posto, accanto al codice'
);

-- ============================================================
-- 4) L'imbuto del log di LOTTO (20260821-39)
-- ============================================================
SELECT vendite.fn_log_pipeline_fase(
  (SELECT lotto_id FROM tmp_lotto_ec), NULL, 'pgtap error code', 'C',
  'prova con codice', jsonb_build_object('task', 'pgtap'), 'E_PARAMETRO_INVALIDO');

SELECT is(
  (SELECT ll.meta->>'error_code' FROM vendite.fatturazione_lotti_log ll
    WHERE ll.lotto_id = (SELECT lotto_id FROM tmp_lotto_ec)
    ORDER BY ll.id DESC LIMIT 1),
  'E_PARAMETRO_INVALIDO',
  '7) fn_log_pipeline_fase scrive il codice quando glielo si passa'
);

-- ⚠️ E non lo scrive quando non c'e': una chiave presente e vuota, in lista,
--    e' una cella bianca indistinguibile da «non c'e'».
SELECT vendite.fn_log_pipeline_fase(
  (SELECT lotto_id FROM tmp_lotto_ec), NULL, 'pgtap senza codice', 'I',
  'prova senza codice', jsonb_build_object('task', 'pgtap'));

SELECT ok(
  NOT (SELECT ll.meta ? 'error_code' FROM vendite.fatturazione_lotti_log ll
        WHERE ll.lotto_id = (SELECT lotto_id FROM tmp_lotto_ec)
        ORDER BY ll.id DESC LIMIT 1),
  '8) ...e senza codice la chiave non nasce nemmeno vuota'
);

-- ============================================================
-- 5) ⭐ L'ALTRA SPECIE: il codice DICHIARATO
--    fn_genera_scadenze_fattura non cattura niente: vede da se' che il totale
--    a pagare e' negativo e lo segnala. Non c'e' nessun CONSTRAINT_NAME da
--    prendere, quindi il codice sta scritto nella funzione — ed e' un `W_`
--    perche' non si solleva: si registra e il giro prosegue.
-- ============================================================
CREATE TEMP TABLE tmp_fattura_neg AS
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, stato_doc_fiscale_id,
      totale_a_pagare, termine_pagamento_id, meta)
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id,
         r.billing_account_id, r.tipo_doc_fiscale_id, r.valuta_id, r.utility_id,
         r.stato_draft_id, -50.00,
         -- ⚠️ Un termine VALIDO serve: senza, si ferma prima con
         --    E_SCADENZE_TERMINE_MANCANTE e il ramo negativo non si raggiunge.
         (SELECT tp.id FROM config.termini_pagamento tp
           WHERE tp.ripartizione = 'UGUALI' AND tp.numero_rate IS NOT NULL
           ORDER BY tp.id LIMIT 1),
         jsonb_build_object('test_scope', 'pgtap_error_code')
    FROM tmp_refs_ec r
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_esito_neg AS
SELECT * FROM vendite.fn_genera_scadenze_fattura((SELECT id FROM tmp_fattura_neg));

SELECT is(
  (SELECT fl.meta->>'error_code'
     FROM vendite.fatture_log fl
    WHERE fl.fattura_id = (SELECT id FROM tmp_fattura_neg)
      AND fl.meta->>'source' = 'fn_genera_scadenze_fattura'
    ORDER BY fl.id DESC LIMIT 1),
  'W_SCADENZE_TOTALE_NEGATIVO',
  '9) un codice DICHIARATO (W_) su una condizione vista dalla funzione stessa'
);

-- I due codici devono esistere a catalogo con la loro classe, o la colonna
-- «codice» delle liste mostrerebbe una sigla che non risolve.
-- ℹ️ NON si asserisce che manchino da config.messaggi_errore: l'assenza e' una
--    DECISIONE (2026-08-21, opzione b) e non un invariante — inchiodarla qui
--    trasformerebbe una scelta rivedibile in un vincolo.
SELECT is(
  (SELECT string_agg(ce.classe, '|' ORDER BY ce.codice)
     FROM config.codici_errore ce
    WHERE ce.codice IN ('W_FONDO_MINIMO_NON_RIPRISTINABILE',
                        'W_SCADENZE_TOTALE_NEGATIVO')),
  'AVVISO|AVVISO',
  '10) i due W_ nuovi sono a catalogo, classe AVVISO'
);

SELECT * FROM finish();
ROLLBACK;
