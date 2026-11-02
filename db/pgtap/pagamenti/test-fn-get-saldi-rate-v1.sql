-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: pagamenti.fn_get_saldi_rate — il NUCLEO dei saldi delle rate, le sue
--       tre porte, e l'IMPUTAZIONE derivata dei movimenti senza rata
--       (changeSet 20260917-07 · -08 · -09 · -10)
--
-- Elenco test (plan 17):
--  1) Riferimenti costruiti (azienda, operatore, cliente) e a catalogo
--  2) Le tre porte danno gli stessi numeri su una rata con movimenti DIRETTI
--  3) Una rata mai toccata torna lo stesso dal nucleo, con has_movimenti false
--  4) p_scadenza_ids NULL = zero righe (semantica SQL, non «tutte»)
--  5) Un id inesistente: zero righe dal nucleo
--  6) ...ed E_RATA_NON_TROVATA dalla porta 1
--  7) ⭐ Fattura a rata unica pagata SENZA rata: la rata dice zero (il punto cieco)
--  8) ...e has_movimenti e' vero, e l'incassato e' arrivato alla rata
--  9) ⭐ Tre rate e un acconto senza rata: FIFO per scadenza fino a capienza
-- 10) ...e Σ saldi delle rate = saldo del documento, per costruzione
-- 11) ⭐ Una riga senza rata IN LAVORAZIONE occupa lo spazio della rata
-- 12) ...e il guard di capienza LO VEDE: una riga sulla rata piena e' respinta
-- 13) Verso contrario senza rata: va sulla prima rata e resta visibile
-- 14) p_escludi_contabile_riga_id vale anche su una riga senza rata
-- 15) Una riga diretta gia' piena non riceve imputazione: l'acconto salta alla successiva
-- 16) L'eccedenza oltre l'ultima rata resta sull'ultima (sovra-incasso, Σ tiene)
-- 17) La vista vw_saldi_rate e' security_invoker e coincide col nucleo
--
-- Scopo:
--  - provare che il CONTENITORE e' fedele (2-6): stessa formula di ieri per i
--    movimenti diretti, in tre porte che non possono divergere perche' sono una;
--  - provare la regola NUOVA (7-16) su casi COSTRUITI, non letti: il punto
--    cieco della rata (brief-db-distinta-ricerca-rate §4-bis.6, Q-A/γ) —
--    prima di questa rev una fattura a rata unica pagata «senza rata» aveva
--    saldo_fattura 0 e saldo_rata 100, e il fondo fattura scrive SEMPRE cosi';
--  - il test 12 e' il presidio che conta: il guard di capienza legge il
--    nucleo, quindi vede lo spazio che il documento sa anche prima del posting.
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (rev 2026-09-17 sera). La prima
--   stesura ricopiava la fixture di test-abbinamento-rata — «l'ultimo billing
--   account per data_insert» e l'emittente dedotto da li' — che in
--   baseline-rossi-ci.tsv e' gia' ERRORE_FIXTURE per lo stesso motivo: su un
--   database ricostruito dai changelog (zeroerp_ci, la CI) le anagrafiche sono
--   a ZERO, tmp_refs usciva vuota e fn_get_or_create_vendite_contabile moriva
--   su «il centro di riscossione» NULL — nessuna delle 17 asserzioni eseguita.
--   Ora: un'azienda col suo operatore (dbops.fn_pgtap_crea_emittente_operatore)
--   PRIMA del contesto, un cliente fatturabile (dbops.fn_pgtap_crea_cliente_ba)
--   NEL contesto — guida pgtap-come-si-scrive-un-test §«Il mondo si
--   costruisce, non si cerca». Con un emittente nuovo la chiave di riuso di
--   fn_get_or_create_vendite_contabile (che dal 2026-09-15 comprende
--   l'emittente) non puo' agganciare una distinta preesistente della macchina.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore.
CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_fn_get_saldi_rate'::text AS test_scope;

-- Il cliente fatturabile, nel contesto dell'operatore: il legame BA -> emittente
-- lo scrive il trigger z90 verso l'emittente di chi agisce.
CREATE TEMP TABLE tmp_cli AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('saldi rate') c;

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
         WHERE s.codice_interno = 'ABBINATA' ORDER BY s.id LIMIT 1)                  AS stato_abbinata_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'VALIDATA' ORDER BY s.id LIMIT 1)                  AS stato_validata_id
  FROM _mondo m;

SELECT ok(
  (SELECT registro_id IS NOT NULL AND billing_account_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL AND centro_banca_id IS NOT NULL
      AND stato_abbinata_id IS NOT NULL AND stato_validata_id IS NOT NULL
     FROM tmp_refs),
  '1) Riferimenti costruiti: azienda, operatore, cliente, registro, centro BANCA e stati a catalogo'
);

-- Sette fatture, una per caso: A rata unica pagata senza rata · B tre rate con
-- acconto senza rata · C rata unica con riga senza rata in lavorazione ·
-- D verso contrario · E rata unica con movimento DIRETTO (le tre porte) ·
-- F rata diretta piena piu' acconto senza rata · G eccedenza oltre l'ultima.
CREATE TEMP TABLE tmp_fatture AS
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, totale_a_pagare, meta)
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id, r.billing_account_id,
         r.tipo_doc_fiscale_id, r.valuta_id, r.utility_id, v.totale,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti), 'ruolo', v.ruolo)
    FROM tmp_refs r,
         (VALUES ('A', 100.00), ('B', 100.00), ('C', 100.00), ('D', 100.00),
                 ('E', 100.00), ('F', 100.00), ('G', 100.00)) AS v(ruolo, totale)
  RETURNING id, meta ->> 'ruolo' AS ruolo
)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_rate AS
WITH ins AS (
  INSERT INTO vendite.fatture_scadenze (fattura_id, numero_rata, data_scadenza, importo, meta)
  SELECT f.id, v.n, script.fn_data_operativa() + v.n, v.importo,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti), 'rata', v.et)
    FROM (VALUES ('A', 1, 100.00, 'A1'),
                 ('B', 1,  30.00, 'B1'), ('B', 2, 30.00, 'B2'), ('B', 3, 40.00, 'B3'),
                 ('C', 1, 100.00, 'C1'),
                 ('D', 1, 100.00, 'D1'),
                 ('E', 1, 100.00, 'E1'),
                 ('F', 1,  30.00, 'F1'), ('F', 2, 70.00, 'F2'),
                 ('G', 1,  30.00, 'G1'), ('G', 2, 70.00, 'G2')) AS v(ruolo, n, importo, et)
    JOIN tmp_fatture f ON f.ruolo = v.ruolo
  RETURNING id, meta ->> 'rata' AS etichetta, fattura_id
)
SELECT * FROM ins;

-- Una distinta da REGISTRARE (bozza → validata → posting) e una che resta in
-- lavorazione: cosi' i due stadi dell'imputazione si provano separati.
CREATE TEMP TABLE tmp_contabile AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_banca_id FROM tmp_refs),
    p_data_contabile        => script.fn_data_operativa(),
    p_data_registrazione    => script.fn_data_operativa(),
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
    p_origine               => 'MANUALE'
  ) AS contabile_id;

CREATE TEMP TABLE tmp_contabile_bozza AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_banca_id FROM tmp_refs),
    p_data_contabile        => script.fn_data_operativa() - 1,
    p_data_registrazione    => script.fn_data_operativa(),
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
    p_origine               => 'MANUALE'
  ) AS contabile_id;

-- Le righe da registrare. ⚠️ Quelle SENZA rata non incontrano il guard di
-- capienza (esce su scadenza_id IS NULL): e' esattamente il buco per cui
-- esiste l'imputazione.
INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, importo, fattura_id,
     billing_account_id, scadenza_id, stato_id, meta)
SELECT (SELECT contabile_id FROM tmp_contabile), v.rif, script.fn_data_operativa(), v.importo,
       f.id, r.billing_account_id,
       (SELECT id FROM tmp_rate WHERE etichetta = v.rata), r.stato_abbinata_id,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r,
       (VALUES ('A', NULL, 'PGTAP_A_SENZA_RATA', 100.00),   -- rata unica pagata senza rata
               ('B', NULL, 'PGTAP_B_ACCONTO',     50.00),   -- acconto su tre rate
               ('D', NULL, 'PGTAP_D_CONTRARIA',  -20.00),   -- verso contrario senza rata
               ('E', 'E1', 'PGTAP_E_DIRETTA',     60.00),   -- movimento DIRETTO sulla rata
               ('G', NULL, 'PGTAP_G_ECCEDENZA',  130.00)    -- oltre il totale del documento
       ) AS v(ruolo, rata, rif, importo)
  JOIN tmp_fatture f ON f.ruolo = v.ruolo;

-- ⚠️ F in DUE istruzioni, nell'ordine dei fatti: prima la riga DIRETTA sulla
--   rata 1 (30, la riempie), poi l'acconto senza rata (20). L'imputazione
--   segue i fatti nell'ordine in cui arrivano: in un INSERT multi-riga il
--   JOIN puo' riordinare, l'acconto entrerebbe prima, verrebbe imputato alla
--   rata 1 (FIFO) e la riga diretta da 30 troverebbe 10 — cioe' esattamente
--   lo spazio che il picker mostrerebbe in quel momento, e il guard, che
--   legge lo stesso nucleo, la respingerebbe. Non e' un difetto: e' «cio' che
--   vedi e' cio' che vale» (changeSet 20260917-10, «l'ordine dei fatti»).
INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, importo, fattura_id,
     billing_account_id, scadenza_id, stato_id, meta)
SELECT (SELECT contabile_id FROM tmp_contabile), 'PGTAP_F1_PIENA', script.fn_data_operativa(), 30.00,
       (SELECT id FROM tmp_fatture WHERE ruolo = 'F'), r.billing_account_id,
       (SELECT id FROM tmp_rate WHERE etichetta = 'F1'), r.stato_abbinata_id,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r;

INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, importo, fattura_id,
     billing_account_id, scadenza_id, stato_id, meta)
SELECT (SELECT contabile_id FROM tmp_contabile), 'PGTAP_F_ACCONTO', script.fn_data_operativa(), 20.00,
       (SELECT id FROM tmp_fatture WHERE ruolo = 'F'), r.billing_account_id,
       NULL, r.stato_abbinata_id,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r;

UPDATE pagamenti.vendite_contabili c
   SET stato_id = (SELECT stato_validata_id FROM tmp_refs)
 WHERE c.id = (SELECT contabile_id FROM tmp_contabile);

CREATE TEMP TABLE tmp_esito AS
SELECT * FROM pagamenti.fn_posta_contabile((SELECT contabile_id FROM tmp_contabile));

-- La riga che RESTA in lavorazione, senza rata, su C.
INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, importo, fattura_id,
     billing_account_id, scadenza_id, stato_id, meta)
SELECT (SELECT contabile_id FROM tmp_contabile_bozza), 'PGTAP_C_IN_LAVORAZIONE', script.fn_data_operativa(), 100.00,
       (SELECT id FROM tmp_fatture WHERE ruolo = 'C'), r.billing_account_id,
       NULL, r.stato_abbinata_id,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r;

-- Un aiuto di lettura: il nucleo per etichetta.
CREATE OR REPLACE FUNCTION pg_temp.nucleo(p_et text)
RETURNS TABLE(saldo numeric, in_lavorazione numeric, incassato numeric, has_movimenti boolean)
LANGUAGE sql AS $$
  SELECT k.saldo, k.in_lavorazione, k.incassato, k.has_movimenti
    FROM pagamenti.fn_get_saldi_rate(ARRAY[(SELECT id FROM tmp_rate WHERE etichetta = p_et)]) k
$$;

-- ============================================================
-- 2-6) Il contenitore e' fedele: tre porte, una formula
-- ============================================================
SELECT ok(
  (SELECT p1.saldo = 40.00 AND p1.incassato = 60.00 AND p1.has_movimenti
      AND p1.saldo = k.saldo AND p1.in_lavorazione = k.in_lavorazione
      AND p1.incassato = k.incassato AND p1.has_movimenti = k.has_movimenti
      AND p1.saldo = v.saldo AND p1.in_lavorazione = v.in_lavorazione
      AND p1.incassato = v.incassato AND p1.has_movimenti = v.has_movimenti
     FROM pagamenti.fn_get_saldo_rata((SELECT id FROM tmp_rate WHERE etichetta = 'E1')) p1,
          pg_temp.nucleo('E1') k,
          pagamenti.vw_saldi_rate v
    WHERE v.scadenza_id = (SELECT id FROM tmp_rate WHERE etichetta = 'E1')),
  '2) Le tre porte danno gli stessi numeri su una rata con movimenti DIRETTI (100 - 60 = 40)'
);

SELECT ok(
  (SELECT k.saldo = 40.00 AND k.in_lavorazione = 0 AND k.incassato = 0 AND k.has_movimenti IS FALSE
     FROM pg_temp.nucleo('B3') k),
  '3) Una rata mai toccata torna lo stesso dal nucleo, con has_movimenti false'
);

SELECT is(
  (SELECT count(*)::int FROM pagamenti.fn_get_saldi_rate(NULL)),
  0,
  '4) p_scadenza_ids NULL = zero righe (semantica SQL, non «tutte»)'
);

SELECT is(
  (SELECT count(*)::int FROM pagamenti.fn_get_saldi_rate(ARRAY[999999999::bigint])),
  0,
  '5) Un id inesistente: zero righe dal nucleo'
);
SELECT throws_like(
  'SELECT * FROM pagamenti.fn_get_saldo_rata(999999999)',
  '%non esiste%',
  '6) ...ed E_RATA_NON_TROVATA dalla porta 1'
);

-- ============================================================
-- 7-8) ⭐ Il punto cieco: rata unica pagata SENZA rata
-- ============================================================
SELECT is(
  (SELECT k.saldo FROM pg_temp.nucleo('A1') k),
  0.00::numeric,
  '7) Fattura a rata unica pagata senza rata: la rata dice ZERO (prima diceva 100)'
);

SELECT ok(
  (SELECT k.has_movimenti IS TRUE AND k.incassato = 100.00
     FROM pg_temp.nucleo('A1') k),
  '8) ...e has_movimenti e'' vero, e l''incassato e'' arrivato alla rata'
);

-- ============================================================
-- 9-10) ⭐ FIFO per data di scadenza, e Σ rate = documento
-- ============================================================
SELECT is(
  (SELECT string_agg(round(k.saldo, 2)::text, ' | ' ORDER BY r.etichetta)
     FROM tmp_rate r
     JOIN LATERAL pagamenti.fn_get_saldi_rate(ARRAY[r.id]) k ON true
    WHERE r.etichetta IN ('B1', 'B2', 'B3')),
  '0.00 | 10.00 | 40.00',
  '9) Tre rate (30/30/40) e un acconto di 50 senza rata: 0 | 10 | 40 — FIFO per scadenza'
);

SELECT is(
  (SELECT sum(k.saldo)
     FROM pagamenti.fn_get_saldi_rate(ARRAY(SELECT id FROM tmp_rate WHERE etichetta LIKE 'B%')) k),
  (SELECT sf.saldo FROM pagamenti.fn_get_saldo_fattura((SELECT id FROM tmp_fatture WHERE ruolo = 'B')) sf),
  '10) Σ saldi delle rate = saldo del documento, per costruzione'
);

-- ============================================================
-- 11-12) ⭐ Il secondo stadio: la riga senza rata in lavorazione
-- ============================================================
SELECT ok(
  (SELECT k.saldo = 100.00 AND k.in_lavorazione = 100.00 AND k.has_movimenti IS FALSE
     FROM pg_temp.nucleo('C1') k),
  '11) Una riga senza rata IN LAVORAZIONE occupa lo spazio della rata (saldo 100, in lavorazione 100)'
);

-- ⭐ Il presidio che conta: il guard legge il nucleo, quindi vede lo spazio
--   che il documento sa. Senza imputazione questa riga sarebbe entrata.
SELECT throws_like(
  format($q$INSERT INTO pagamenti.vendite_contabili_righe
             (contabile_id, importo, fattura_id, billing_account_id, scadenza_id, stato_id)
           VALUES (%s, 10.00, %s, %s, %s, %s)$q$,
         (SELECT contabile_id FROM tmp_contabile_bozza),
         (SELECT id FROM tmp_fatture WHERE ruolo = 'C'),
         (SELECT billing_account_id FROM tmp_refs),
         (SELECT id FROM tmp_rate WHERE etichetta = 'C1'),
         (SELECT stato_abbinata_id FROM tmp_refs)),
  '%non ci rientra%',
  '12) ...e il guard di capienza LO VEDE: una riga sulla rata gia'' occupata e'' respinta'
);

-- ============================================================
-- 13) Verso contrario senza rata: sulla prima, e visibile
-- ============================================================
SELECT ok(
  (SELECT k.saldo = 120.00 AND k.has_movimenti IS TRUE
     FROM pg_temp.nucleo('D1') k),
  '13) Un rimborso di 20 senza rata su una fattura positiva: la rata dice 120, l''anomalia resta visibile'
);

-- ============================================================
-- 14) L'esclusione vale anche sulla riga senza rata
-- ============================================================
SELECT is(
  (SELECT k.saldo
     FROM pagamenti.fn_get_saldi_rate(
            ARRAY[(SELECT id FROM tmp_rate WHERE etichetta = 'A1')],
            (SELECT cr.id FROM pagamenti.vendite_contabili_righe cr WHERE cr.riferimento_ente = 'PGTAP_A_SENZA_RATA')) k),
  100.00::numeric,
  '14) Escludendo la riga senza rata, la rata torna a 100: p_escludi vale anche sul non-imputato'
);

-- ============================================================
-- 15-16) La capienza per rata, e l'ultima che assorbe
-- ============================================================
SELECT is(
  (SELECT string_agg(round(k.saldo, 2)::text, ' | ' ORDER BY r.etichetta)
     FROM tmp_rate r
     JOIN LATERAL pagamenti.fn_get_saldi_rate(ARRAY[r.id]) k ON true
    WHERE r.etichetta IN ('F1', 'F2')),
  '0.00 | 50.00',
  '15) Rata 1 piena in diretta (30) e acconto di 20 senza rata: salta alla seconda — 0 | 50'
);

SELECT is(
  (SELECT string_agg(round(k.saldo, 2)::text, ' | ' ORDER BY r.etichetta)
     FROM tmp_rate r
     JOIN LATERAL pagamenti.fn_get_saldi_rate(ARRAY[r.id]) k ON true
    WHERE r.etichetta IN ('G1', 'G2')),
  '0.00 | -30.00',
  '16) Incassati 130 senza rata su 30 + 70: l''eccedenza resta sull''ultima (0 | -30), e Σ tiene'
);

-- ============================================================
-- 17) La vista: security_invoker e coincide col nucleo
-- ============================================================
SELECT ok(
  (SELECT 'security_invoker=on' = ANY (c.reloptions)
     FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'pagamenti' AND c.relname = 'vw_saldi_rate')
  AND NOT EXISTS (
    SELECT 1
      FROM tmp_rate r
      JOIN pagamenti.vw_saldi_rate v ON v.scadenza_id = r.id
      JOIN LATERAL pagamenti.fn_get_saldi_rate(ARRAY[r.id]) k ON true
     WHERE v.saldo <> k.saldo OR v.in_lavorazione <> k.in_lavorazione
        OR v.incassato <> k.incassato OR v.has_movimenti <> k.has_movimenti),
  '17) vw_saldi_rate e'' security_invoker e coincide col nucleo su tutte le rate costruite'
);

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
