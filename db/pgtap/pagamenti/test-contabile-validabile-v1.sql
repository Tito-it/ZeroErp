-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: che cosa deve essere vero per VALIDARE — script.fn_check_contabile_validabile
--       e il guard che la chiama (D20-a), piu' la coppia spenta di D20-e
--
-- Elenco test (plan 16):
--  1) Riferimenti costruiti (azienda, operatore, cliente) e a catalogo
--  2) La check e' STABLE e INVOKER, e `lavorata` e' a catalogo come deciso
--  3) Una distinta che non esiste: E_CONTABILE_NON_TROVATA, non []
--  4) Un id nullo e' una chiamata rotta: TECNICO
--  5) MOTIVO 1 — una riga DA_ABBINARE: RIGHE_NON_LAVORATE, codice, dettaglio (quante, id)
--  6) ...e i valori della frase: codice della distinta e quante
--  7) Il guard rifiuta l'ingresso in VALIDATA con la frase del motivo 1
--  8) Con un dichiarato sbagliato i motivi sono DUE, nell'ordine: prima il lavoro, poi i conti
--  9) La sospesa E' stata guardata: sospesa la riga, la check risponde []
-- 10) MOTIVO 2 — dichiarato che non quadra: TOTALE_NON_QUADRA, campo, stessi valori di prima
-- 11) ⭐ Il guard giudica il dichiarato che ENTRA, non quello di ieri (stesso UPDATE)
-- 12) Dichiarato giusto — SCARTATA compresa nella somma — la distinta si valida
-- 13) La riapertura resta com'era: la MANUALE torna in BOZZA
-- 14) D20-e: ABBINATA -> DA_ABBINARE e' spenta — rifiutata con la frase della matrice
-- 15) D20-e: ABBINATA -> SOSPESA resta ammessa
-- 16) Cleanup
--
-- Scopo:
--  - presidiare D20-a: VALIDATA = «ogni riga e' stata guardata». Quali stati
--    siano «non lavorati» lo dice il catalogo (`lavorata`), non un elenco nel
--    guard; la sospesa E' stata guardata e passa (test 5, 7, 9);
--  - presidiare la sede unica: il guard CHIAMA la check e solleva il primo
--    motivo (test 7 e 11 confrontano la frase del guard con il codice della
--    check) — tooltip e rifiuto non possono divergere;
--  - ⭐ presidiare la scelta di firma (test 11): il dichiarato e' un PARAMETRO
--    perche' il guard gira BEFORE ROW. `UPDATE ... SET importo_dichiarato = X,
--    stato_id = VALIDATA` in un'istruzione sola deve essere giudicato su X,
--    non sul valore di ieri. Se qualcuno riscrive la check per rileggere il
--    dichiarato per id, questo test diventa verde-per-sottrazione: lo dice qui;
--  - presidiare la quadratura spostata (test 10, 12): stesso codice, stessi
--    valori, e la SCARTATA conta ancora;
--  - presidiare D20-e (test 14, 15): la coppia spenta si rifiuta e la
--    sospensione di una abbinata resta. Il pin sul SEED sta in
--    test-transizioni-stati-contabili; qui c'e' il comportamento.
--
-- Brief: brief-db-validata-e-registrazione-tardiva §2.1, §2.5, §4 P-3/P-4/P-6/P-8
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca: un'azienda col suo operatore
--   (dbops.fn_pgtap_crea_emittente_operatore) PRIMA del contesto, un cliente
--   fatturabile (dbops.fn_pgtap_crea_cliente_ba) NEL contesto — guida
--   pgtap-come-si-scrive-un-test §«Il mondo si costruisce, non si cerca».
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore.
CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione (OPERATORE +
--   RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_contabile_validabile'::text AS test_scope;

CREATE TEMP TABLE tmp_cli AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('contabile validabile') c;

CREATE TEMP TABLE tmp_refs AS
SELECT script.fn_pgtap_registro_fattura(m.soggetto_ruolo_id)                       AS registro_id,
       (SELECT billing_account_id FROM tmp_cli)                                      AS billing_account_id,
       (SELECT utility_id FROM tmp_cli)                                              AS utility_id,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1)                           AS valuta_id,
       m.soggetto_ruolo_id                                                          AS emittente_soggetto_ruolo_id,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA' ORDER BY c.id LIMIT 1) AS centro_banca_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'ABBINATA'    ORDER BY s.id LIMIT 1)               AS st_abbinata,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'SOSPESA'     ORDER BY s.id LIMIT 1)               AS st_sospesa,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'SCARTATA'    ORDER BY s.id LIMIT 1)               AS st_scartata,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'DA_ABBINARE' ORDER BY s.id LIMIT 1)               AS st_da_abbinare,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'VALIDATA'    ORDER BY s.id LIMIT 1)               AS d_validata,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'BOZZA'       ORDER BY s.id LIMIT 1)               AS d_bozza
  FROM _mondo m;

SELECT ok(
  (SELECT registro_id IS NOT NULL AND billing_account_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL AND centro_banca_id IS NOT NULL
      AND st_abbinata IS NOT NULL AND st_sospesa IS NOT NULL AND st_scartata IS NOT NULL
      AND st_da_abbinare IS NOT NULL AND d_validata IS NOT NULL AND d_bozza IS NOT NULL
     FROM tmp_refs),
  '1) Riferimenti costruiti (azienda, operatore, cliente, registro) e a catalogo (centro BANCA, stati)'
);

-- ============================================================
-- 2) La forma della check, e il catalogo come deciso
-- ============================================================
SELECT ok(
  (SELECT p.provolatile = 's' AND p.prosecdef IS FALSE
     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'script' AND p.proname = 'fn_check_contabile_validabile')
  AND (SELECT array_agg(codice_interno ORDER BY codice_interno)
         FROM pagamenti.vendite_contabili_righe_stati
        WHERE lavorata IS NOT TRUE) = ARRAY['DA_ABBINARE', 'IMPORTATA']::text[],
  '2) La check e'' STABLE e INVOKER; non lavorati SOLO DA_ABBINARE e IMPORTATA (D20-a)'
);

-- ============================================================
-- 3-4) I due guard di chiamata
-- ============================================================
-- ⚠️ Rispondere [] su una distinta che non si vede sarebbe un fail-open.
SELECT throws_like(
  'SELECT script.fn_check_contabile_validabile(999999999, NULL)',
  '%non esiste%',
  '3) Una distinta che non esiste solleva E_CONTABILE_NON_TROVATA, non risponde []'
);

SELECT throws_ok(
  'SELECT script.fn_check_contabile_validabile(NULL, NULL)',
  'P0001',
  NULL,
  '4) Un id nullo e'' una chiamata rotta: rifiutata (TECNICO)'
);

-- ============================================================
-- La distinta: manuale, in BOZZA, senza dichiarato. Quattro righe:
--   A ABBINATA 100 · B SOSPESA 30 · C SCARTATA 20 · D DA_ABBINARE 50
-- ============================================================
CREATE TEMP TABLE tmp_fattura AS
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, totale_a_pagare, meta)
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id, r.billing_account_id,
         r.tipo_doc_fiscale_id, r.valuta_id, r.utility_id, 300.00,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_refs r
  RETURNING id
)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_contabile AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_banca_id FROM tmp_refs),
    p_data_contabile        => script.fn_data_operativa(),
    p_data_registrazione    => script.fn_data_operativa(),
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
    p_origine               => 'MANUALE'
  ) AS contabile_id;

CREATE TEMP TABLE tmp_righe AS
WITH ins AS (
  INSERT INTO pagamenti.vendite_contabili_righe
      (contabile_id, riferimento_ente, data_pagamento, importo,
       fattura_id, billing_account_id, stato_id, motivo_sospeso, meta)
  SELECT (SELECT contabile_id FROM tmp_contabile), 'PGTAP_CV_' || v.et, script.fn_data_operativa(), v.importo,
         CASE WHEN v.et IN ('A', 'B') THEN (SELECT id FROM tmp_fattura) END,
         CASE WHEN v.et IN ('A', 'B') THEN r.billing_account_id END,
         CASE v.et WHEN 'A' THEN r.st_abbinata
                   WHEN 'B' THEN r.st_sospesa
                   WHEN 'C' THEN r.st_scartata
                   ELSE          r.st_da_abbinare END,
         CASE WHEN v.et = 'B' THEN 'in attesa di conferma' END,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti), 'et', v.et)
    FROM tmp_refs r
    CROSS JOIN (VALUES ('A', 100.00::numeric), ('B', 30.00::numeric),
                       ('C',  20.00::numeric), ('D', 50.00::numeric)) AS v(et, importo)
  RETURNING id, meta ->> 'et' AS et
)
SELECT * FROM ins;

-- ============================================================
-- 5-6) MOTIVO 1 — la riga D nessuno l'ha guardata
-- ============================================================
CREATE TEMP TABLE tmp_m1 AS
SELECT script.fn_check_contabile_validabile((SELECT contabile_id FROM tmp_contabile), NULL) AS m;

SELECT ok(
  (SELECT jsonb_array_length(m) = 1
      AND m -> 0 ->> 'reason'     = 'RIGHE_NON_LAVORATE'
      AND m -> 0 ->> 'codice'     = 'E_CONTABILE_VALIDAZIONE_RIGHE_NON_LAVORATE'
      AND m -> 0 ->> 'reason_key' = 'pagamenti.distinte.validazione_reason.righe_non_lavorate'
      AND (m -> 0 -> 'dettaglio' ->> 'quante')::int = 1
      AND m -> 0 -> 'dettaglio' -> 'contabile_righe_ids' @> to_jsonb(ARRAY[(SELECT id FROM tmp_righe WHERE et = 'D')])
     FROM tmp_m1),
  '5) Una riga DA_ABBINARE: un solo motivo, RIGHE_NON_LAVORATE, con quante e gli id nel dettaglio'
);

SELECT is(
  (SELECT m -> 0 -> 'valori' FROM tmp_m1),
  jsonb_build_array((SELECT codice FROM pagamenti.vendite_contabili WHERE id = (SELECT contabile_id FROM tmp_contabile)), '1'),
  '6) I valori della frase: codice della distinta e quante'
);

-- ============================================================
-- 7) Il guard solleva il primo motivo, con la sua frase
-- ============================================================
-- ⚠️ throws_like e non throws_ok: qui la posta e' PROPRIO quale frase esce —
--   e' la prova che il guard chiama la check e non fa i conti da se'.
SELECT throws_like(
  format($q$UPDATE pagamenti.vendite_contabili SET stato_id = %s WHERE id = %s$q$,
         (SELECT d_validata FROM tmp_refs), (SELECT contabile_id FROM tmp_contabile)),
  '%nessuno ha ancora lavorato%',
  '7) Il guard rifiuta VALIDATA con la frase del motivo 1: la check e'' la sede unica'
);

-- ============================================================
-- 8) Due motivi, nell'ordine: prima il lavoro non finito, poi i conti
-- ============================================================
SELECT is(
  (SELECT array_agg(x ->> 'reason' ORDER BY ord)
     FROM jsonb_array_elements(
            script.fn_check_contabile_validabile((SELECT contabile_id FROM tmp_contabile), 199.00))
          WITH ORDINALITY AS t(x, ord)),
  ARRAY['RIGHE_NON_LAVORATE', 'TOTALE_NON_QUADRA']::text[],
  '8) Con un dichiarato sbagliato i motivi sono due, in quest''ordine: RIGHE_NON_LAVORATE, TOTALE_NON_QUADRA'
);

-- ============================================================
-- 9) La sospesa E' stata guardata
-- ============================================================
UPDATE pagamenti.vendite_contabili_righe
   SET stato_id = (SELECT st_sospesa FROM tmp_refs),
       motivo_sospeso = 'da capire di chi e'''
 WHERE id = (SELECT id FROM tmp_righe WHERE et = 'D');

SELECT is(
  script.fn_check_contabile_validabile((SELECT contabile_id FROM tmp_contabile), NULL),
  '[]'::jsonb,
  '9) Sospesa la riga da abbinare, senza dichiarato la check risponde []: la sospesa e'' stata guardata'
);

-- ============================================================
-- 10) MOTIVO 2 — la quadratura, con gli stessi valori di prima
-- ============================================================
-- Σ righe attive = 100 + 30 + 20 + 50 = 200, SCARTATA compresa.
CREATE TEMP TABLE tmp_m2 AS
SELECT script.fn_check_contabile_validabile((SELECT contabile_id FROM tmp_contabile), 199.00) AS m;

SELECT ok(
  (SELECT jsonb_array_length(m) = 1
      AND m -> 0 ->> 'reason' = 'TOTALE_NON_QUADRA'
      AND m -> 0 ->> 'codice' = 'E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA'
      AND m -> 0 -> 'dettaglio' ->> 'campo' = 'importo_dichiarato'
      AND m -> 0 -> 'valori' = jsonb_build_array(
            (SELECT codice FROM pagamenti.vendite_contabili WHERE id = (SELECT contabile_id FROM tmp_contabile)),
            '199.00', '200.00')
     FROM tmp_m2),
  '10) Dichiarato 199 su 200 di righe: TOTALE_NON_QUADRA, campo importo_dichiarato, i tre valori di sempre'
);

-- ============================================================
-- 11) ⭐ Il guard giudica il dichiarato che ENTRA
-- ============================================================
-- La testata ha importo_dichiarato NULL. Se la check rileggesse il dichiarato
-- per id, vedrebbe NULL, non applicherebbe la quadratura e questo UPDATE
-- passerebbe scrivendo 199 su 200 righe senza nessun errore.
SELECT throws_like(
  format($q$UPDATE pagamenti.vendite_contabili
             SET importo_dichiarato = 199.00, stato_id = %s WHERE id = %s$q$,
         (SELECT d_validata FROM tmp_refs), (SELECT contabile_id FROM tmp_contabile)),
  '%dichiara 199.00 ma le sue righe sommano 200.00%',
  '11) Dichiarato e VALIDATA nello stesso UPDATE: il guard giudica il valore che entra, non quello di ieri'
);

-- ============================================================
-- 12) Dichiarato giusto: si valida, e la SCARTATA e' nella somma
-- ============================================================
SELECT lives_ok(
  format($q$UPDATE pagamenti.vendite_contabili
             SET importo_dichiarato = 200.00, stato_id = %s WHERE id = %s$q$,
         (SELECT d_validata FROM tmp_refs), (SELECT contabile_id FROM tmp_contabile)),
  '12) Dichiarato 200 = 100 + 30 + 20 (scartati) + 50: la distinta si valida'
);

-- ============================================================
-- 13) La riapertura resta com'era (blocco 2 del guard)
-- ============================================================
SELECT lives_ok(
  format($q$UPDATE pagamenti.vendite_contabili SET stato_id = %s WHERE id = %s$q$,
         (SELECT d_bozza FROM tmp_refs), (SELECT contabile_id FROM tmp_contabile)),
  '13) La MANUALE torna in BOZZA: la riapertura non e'' cambiata'
);

-- ============================================================
-- 14-15) D20-e — sulla abbinata non si «sgancia», si sospende
-- ============================================================
-- ⚠️ La frase della matrice, con i codici interni: e' il guard delle
--   transizioni a parlare, non un altro.
SELECT throws_like(
  format($q$UPDATE pagamenti.vendite_contabili_righe SET stato_id = %s WHERE id = %s$q$,
         (SELECT st_da_abbinare FROM tmp_refs), (SELECT id FROM tmp_righe WHERE et = 'A')),
  '%non puo'' passare da ABBINATA a DA_ABBINARE%',
  '14) D20-e: ABBINATA -> DA_ABBINARE e'' spenta — su una abbinata si ri-abbina, non si sgancia'
);

SELECT lives_ok(
  format($q$UPDATE pagamenti.vendite_contabili_righe
             SET stato_id = %s, motivo_sospeso = 'un dubbio prima di registrare' WHERE id = %s$q$,
         (SELECT st_sospesa FROM tmp_refs), (SELECT id FROM tmp_righe WHERE et = 'A')),
  '15) D20-e: ABBINATA -> SOSPESA resta — una abbinata con un dubbio si parcheggia con un motivo'
);

-- ============================================================
-- Cleanup
-- ============================================================
SELECT set_config('zeroerp.maintenance_allow_delete_logs', 'on', true);
SELECT set_config('zeroerp.allow_contabile_riga_delete_override', 'on', true);

DELETE FROM pagamenti.vendite_contabili_righe
 WHERE contabile_id = (SELECT contabile_id FROM tmp_contabile);

DELETE FROM pagamenti.vendite_contabili
 WHERE id = (SELECT contabile_id FROM tmp_contabile);

DELETE FROM vendite.fatture_log
 WHERE fattura_id = (SELECT id FROM tmp_fattura);

UPDATE vendite.fatture
   SET storicizza = false
 WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti);

DELETE FROM vendite.fatture
 WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti);

SELECT ok(true, '16) Cleanup completato');

SELECT * FROM finish();

ROLLBACK;
