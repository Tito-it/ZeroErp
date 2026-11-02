-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: IL SALDO DELLA FATTURA IN TRE NUMERI — pagamenti.fn_get_saldo_fattura
--       e, dal 2026-09-18, l'ESCLUSIONE di una riga (P-6)
--
-- Elenco test (plan 18):
--  1) Riferimenti costruiti (azienda, operatore, cliente) e a catalogo (i due centri, diversi)
--  2) Una fattura senza niente sopra: residuo = totale, gli altri a zero
--  3) Una riga pronta su una distinta viva finisce in `in_lavorazione`
--  4) ...e il residuo NON si muove: dichiarare non e' registrare
--  5) `in_lavorazione` E' la risposta di fn_get_saldo_fattura_contabili
--  6) ⭐ Escludendo la riga che sta scrivendo: `in_lavorazione` 0, residuo intatto (P-6)
--  7) ⭐ ...e l'esclusione arriva alla delegata: `saldo_contabile` 0, nessuna riga postabile
--  8) Dopo il posting su BANCA il residuo cala
--  9) ...e `incassato` sale: quel denaro e' arrivato davvero
-- 10) ...e `in_lavorazione` torna a zero: la distinta e' chiusa
-- 11) ⭐ Escludendo la riga POSTATA: il suo movimento non conta — residuo 300, incassato 0, nessun movimento
-- 12) ⭐ Un movimento su un centro FONDO FATTURA fa calare il residuo
-- 13) ⭐ ...e NON tocca `incassato`: quei centri non sono cassa
-- 14) QUADRATURA: residuo = totale - somma dei movimenti attivi
-- 15) Il guard di parametro rifiuta un id non positivo
-- 16) Una fattura che non esiste e' rifiutata
-- 17) Il guard rifiuta un'esclusione non positiva (fn_get_saldo_fattura)
-- 18) ...e anche la delegata la rifiuta (fn_get_saldo_fattura_contabili)
--
-- Scopo:
--  - collaudare il passo S5-1, in cui la funzione passa da DUE numeri a TRE.
--    ⭐ Il cuore sono i test 12 e 13, ed e' l'unica coppia che distingue
--    `incassato` da `saldo`: senza un movimento su un centro interno il test
--    passerebbe anche se `incassato` fosse una copia del residuo — cioe'
--    passerebbe proprio nel caso in cui la colonna nuova non serve a niente;
--  - presidiare la DELEGA (test 5): `in_lavorazione` non e' una seconda
--    formula scritta qui, e' cio' che risponde la funzione che gia' lo sa. Se
--    un giorno qualcuno la riscrivesse, questo test diventa rosso;
--  - ⭐ collaudare P-6 (2026-09-18, brief-db-distinta-ricerca-rate §4.6):
--    `p_escludi_contabile_riga_id` risponde «quanto c'era PRIMA di me» su
--    ENTRAMBI i conti — il dichiarato (6, 7: e la delegata la riceve, non
--    e' una seconda esclusione scritta qui) e il registrato (11: il movimento
--    scritto dalla riga esclusa esce dal saldo, la stessa forma del nucleo
--    fn_get_saldi_rate). Il test 11 e' quello che distingue «solo in
--    lavorazione» (il brief) da «come la sorella» (il changeSet): senza, le
--    due sorelle potrebbero rispondere due cose diverse allo stesso nome;
--  - verificare che i due numeri VECCHI rispondano come prima (test 2, 8, 14).
--
-- Piano: brief-db-posting-e-abbinamento-rata.md
--        §2.3-ter S5-1 · lotto 8 · richiesta DB-10 del brief BE/FE (Q-10)
--        P-6: brief-db-distinta-ricerca-rate §4.6 (20260918-01, -02)
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (rev 2026-09-18). Fino a quel
--   giorno il file pescava «l'ultimo billing account per data_insert» e ne
--   deduceva l'emittente: su un database ricostruito dai changelog (zeroerp_ci,
--   la CI) le anagrafiche sono a ZERO, tmp_refs usciva vuota e il file moriva
--   nel fixture — ERRORE_FIXTURE in baseline-rossi-ci.tsv, 13 asserzioni
--   collaudate solo su dbdev. Ora: un'azienda col suo operatore
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

-- ⚠️ 3. VINCOLI DIFFERITI: senza, non verrebbero mai esercitati (si chiude in
--   ROLLBACK) e il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_saldo_fattura_tre'::text AS test_scope;

-- Il cliente fatturabile, nel contesto dell'operatore: il legame BA -> emittente
-- lo scrive il trigger z90 verso l'emittente di chi agisce.
CREATE TEMP TABLE tmp_cli AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('saldo fattura tre numeri') c;

-- ⚠️ I centri NON si fabbricano: sono seminati dal lotto 1 e i due ruoli
--   interni sono unici per vincolo. Un test che se li crea da solo non
--   verifica il seed: lo nasconde.
-- ⭐ Qui ne servono DUE, e la differenza fra loro E' l'oggetto del test:
--   BANCA e' cassa, il centro `is_fondo_fattura` no.
CREATE TEMP TABLE tmp_refs AS
SELECT script.fn_pgtap_registro_fattura(m.soggetto_ruolo_id)                       AS registro_id,
       (SELECT billing_account_id FROM tmp_cli)                                      AS billing_account_id,
       (SELECT utility_id FROM tmp_cli)                                              AS utility_id,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1)                            AS valuta_id,
       m.soggetto_ruolo_id                                                           AS emittente_soggetto_ruolo_id,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA'
         ORDER BY c.id LIMIT 1)                                                      AS centro_banca_id,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.is_fondo_fattura IS TRUE
         ORDER BY c.id LIMIT 1)                                                      AS centro_fondo_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'ABBINATA' ORDER BY s.id LIMIT 1)                  AS stato_abbinata_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'VALIDATA' ORDER BY s.id LIMIT 1)                  AS stato_validata_id
  FROM _mondo m;

SELECT ok(
  (SELECT registro_id IS NOT NULL
      AND billing_account_id IS NOT NULL
      AND tipo_doc_fiscale_id IS NOT NULL
      AND valuta_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL
      AND centro_banca_id IS NOT NULL
      AND centro_fondo_id IS NOT NULL
      AND centro_banca_id <> centro_fondo_id
      AND stato_abbinata_id IS NOT NULL
      AND stato_validata_id IS NOT NULL
     FROM tmp_refs),
  '1) Riferimenti costruiti (azienda, operatore, cliente, registro) e a catalogo: i due centri sono davvero diversi'
);

-- La fattura da incassare: 300.
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

-- ============================================================
-- 2) Il punto di partenza: nessun movimento, nessuna dichiarazione
-- ============================================================
SELECT is(
  (SELECT ARRAY[s.saldo, s.in_lavorazione, s.incassato]::text[]
     FROM pagamenti.fn_get_saldo_fattura((SELECT id FROM tmp_fattura)) s),
  ARRAY['300.00', '0', '0']::text[],
  '2) Fattura nuova: residuo = totale, in lavorazione e incassato a zero'
);

-- ============================================================
-- La distinta di cassa, con una riga pronta da 100 (la riga A)
-- ============================================================
CREATE TEMP TABLE tmp_contabile_banca AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_banca_id FROM tmp_refs),
    p_data_contabile        => script.fn_data_operativa(),
    p_data_registrazione    => script.fn_data_operativa(),
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
    p_origine               => 'MANUALE'
  ) AS contabile_id;

-- ⭐ L'id della riga si tiene: e' la riga che i test 6, 7 e 11 escludono.
CREATE TEMP TABLE tmp_riga_a AS
WITH ins AS (
  INSERT INTO pagamenti.vendite_contabili_righe
      (contabile_id, riferimento_ente, data_pagamento, data_valuta, importo,
       fattura_id, billing_account_id, stato_id, meta)
  SELECT (SELECT contabile_id FROM tmp_contabile_banca), 'PGTAP_SALDO_A',
         script.fn_data_operativa(), script.fn_data_operativa(), 100.00,
         (SELECT id FROM tmp_fattura), r.billing_account_id, r.stato_abbinata_id,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_refs r
  RETURNING id
)
SELECT id AS riga_id FROM ins;

UPDATE pagamenti.vendite_contabili c
   SET importo_dichiarato = 100.00,
       stato_id = (SELECT stato_validata_id FROM tmp_refs)
 WHERE c.id = (SELECT contabile_id FROM tmp_contabile_banca);

-- ============================================================
-- 3-4-5) Il dichiarato: c'e', si vede, e NON e' il registrato
-- ============================================================
SELECT is(
  (SELECT s.in_lavorazione
     FROM pagamenti.fn_get_saldo_fattura((SELECT id FROM tmp_fattura)) s),
  100.00::numeric,
  '3) Una riga pronta su una distinta viva finisce in `in_lavorazione`'
);

SELECT is(
  (SELECT s.saldo
     FROM pagamenti.fn_get_saldo_fattura((SELECT id FROM tmp_fattura)) s),
  300.00::numeric,
  '4) ...e il residuo non si muove: dichiarare non e'' registrare'
);

-- ⭐ La delega, non una seconda formula. Se qualcuno riscrivesse il predicato
--   qui dentro, questo confronto e' la prima cosa che se ne accorge.
SELECT is(
  (SELECT s.in_lavorazione
     FROM pagamenti.fn_get_saldo_fattura((SELECT id FROM tmp_fattura)) s),
  (SELECT c.saldo_contabile
     FROM pagamenti.fn_get_saldo_fattura_contabili((SELECT id FROM tmp_fattura)) c),
  '5) `in_lavorazione` e'' esattamente cio'' che risponde la funzione del dichiarato'
);

-- ============================================================
-- 6-7) ⭐ P-6: «quanto c'era PRIMA di me» — la riga esclusa non si conta
-- ============================================================
-- Chi sta correggendo la riga A (100 → 600) legge il pannello DOCUMENTO
-- escludendo se' stesso: il dichiarato torna a zero, il residuo resta 300.
SELECT is(
  (SELECT ARRAY[s.saldo, s.in_lavorazione]::text[]
     FROM pagamenti.fn_get_saldo_fattura((SELECT id FROM tmp_fattura),
                                         (SELECT riga_id FROM tmp_riga_a)) s),
  ARRAY['300.00', '0']::text[],
  '6) Escludendo la riga che sta scrivendo: in lavorazione 0, residuo intatto (P-6)'
);

-- ⭐ L'esclusione VIAGGIA con la delega: e' la delegata a togliere la riga,
--   non una seconda esclusione scritta nella madre. E senza la riga A non
--   resta nessuna riga postabile.
SELECT is(
  (SELECT ARRAY[c.saldo_contabile::text, c.has_righe_postabili::text]
     FROM pagamenti.fn_get_saldo_fattura_contabili((SELECT id FROM tmp_fattura),
                                                   (SELECT riga_id FROM tmp_riga_a)) c),
  ARRAY['0', 'false'],
  '7) ...e l''esclusione arriva alla delegata: saldo_contabile 0, nessuna riga postabile'
);

-- ============================================================
-- Il posting di cassa — verbo in un'istruzione SEPARATA dalle asserzioni
-- ============================================================
-- ⚠️ La snapshot di statement legge PRIMA delle scritture: un'asserzione nella
--   stessa istruzione accuserebbe la funzione invece del test.
CREATE TEMP TABLE tmp_esito_banca AS
SELECT * FROM pagamenti.fn_posta_contabile(
    (SELECT contabile_id FROM tmp_contabile_banca), 1, 100.00);

CREATE TEMP TABLE tmp_saldo_dopo_banca AS
SELECT * FROM pagamenti.fn_get_saldo_fattura((SELECT id FROM tmp_fattura));

SELECT is((SELECT saldo FROM tmp_saldo_dopo_banca), 200.00::numeric,
  '8) Dopo il posting su BANCA il residuo cala');

SELECT is((SELECT incassato FROM tmp_saldo_dopo_banca), 100.00::numeric,
  '9) ...e `incassato` sale: quel denaro e'' arrivato davvero');

SELECT is((SELECT in_lavorazione FROM tmp_saldo_dopo_banca), 0::numeric,
  '10) ...e `in_lavorazione` torna a zero: la distinta e'' chiusa');

-- ============================================================
-- 11) ⭐ P-6, il registrato: la riga POSTATA esclusa porta via il suo movimento
-- ============================================================
-- E' la stessa forma del nucleo fn_get_saldi_rate (CTE `mov`): lo stesso nome
-- di parametro risponde alla stessa domanda su rata e documento. Il movimento
-- di A e' l'UNICO sul documento: escluso, il documento e' come nuovo.
SELECT is(
  (SELECT ARRAY[s.saldo::text, s.incassato::text, s.has_movimenti::text]
     FROM pagamenti.fn_get_saldo_fattura((SELECT id FROM tmp_fattura),
                                         (SELECT riga_id FROM tmp_riga_a)) s),
  ARRAY['300.00', '0', 'false'],
  '11) Escludendo la riga POSTATA: il suo movimento non conta — residuo 300, incassato 0, nessun movimento'
);

-- ============================================================
-- ⭐ Il caso che distingue le due colonne: un centro che NON e' cassa
-- ============================================================
-- Una seconda distinta, sul centro dei fondi fattura: e' il giro interno, il
-- denaro si sposta ma in banca non entra niente.
CREATE TEMP TABLE tmp_contabile_fondo AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_fondo_id FROM tmp_refs),
    p_data_contabile        => script.fn_data_operativa(),
    p_data_registrazione    => script.fn_data_operativa(),
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
    p_origine               => 'GENERATA'
  ) AS contabile_id;

INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, data_valuta, importo,
     fattura_id, billing_account_id, stato_id, meta)
SELECT (SELECT contabile_id FROM tmp_contabile_fondo), 'PGTAP_SALDO_B',
       script.fn_data_operativa(), script.fn_data_operativa(), 50.00,
       (SELECT id FROM tmp_fattura), r.billing_account_id, r.stato_abbinata_id,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r;

UPDATE pagamenti.vendite_contabili c
   SET stato_id = (SELECT stato_validata_id FROM tmp_refs)
 WHERE c.id = (SELECT contabile_id FROM tmp_contabile_fondo);

CREATE TEMP TABLE tmp_esito_fondo AS
SELECT * FROM pagamenti.fn_posta_contabile(
    (SELECT contabile_id FROM tmp_contabile_fondo), 1, 50.00);

CREATE TEMP TABLE tmp_saldo_dopo_fondo AS
SELECT * FROM pagamenti.fn_get_saldo_fattura((SELECT id FROM tmp_fattura));

SELECT is((SELECT saldo FROM tmp_saldo_dopo_fondo), 150.00::numeric,
  '12) Un movimento su un centro FONDO FATTURA fa calare il residuo');

-- ⭐ L'asserzione che rende utile la colonna nuova: senza questa, `incassato`
--   potrebbe essere una copia del residuo e nessuno se ne accorgerebbe.
SELECT is((SELECT incassato FROM tmp_saldo_dopo_fondo), 100.00::numeric,
  '13) ...e NON tocca `incassato`: fondo fattura e compensazione non sono cassa');

-- ============================================================
-- 14) La quadratura, che non nomina il meccanismo
-- ============================================================
SELECT is(
  (SELECT s.saldo FROM pagamenti.fn_get_saldo_fattura((SELECT id FROM tmp_fattura)) s),
  (SELECT f.totale_a_pagare - COALESCE(SUM(m.importo), 0)
     FROM vendite.fatture f
     LEFT JOIN pagamenti.vendite_movimenti m
       ON m.fattura_id = f.id AND m.attivo IS TRUE
    WHERE f.id = (SELECT id FROM tmp_fattura)
    GROUP BY f.totale_a_pagare),
  '14) Quadratura: residuo = totale meno la somma dei movimenti attivi'
);

-- ============================================================
-- 15-18) I guard, con lo SQLSTATE dichiarato
-- ============================================================
-- ⚠️ Senza SQLSTATE, throws_ok accetterebbe qualunque errore, compreso il
--   crash del guard. P0001 = errore di dominio.
SELECT throws_ok(
  'SELECT * FROM pagamenti.fn_get_saldo_fattura(0)',
  'P0001',
  NULL,
  '15) Il guard di parametro rifiuta un id non positivo'
);

SELECT throws_ok(
  'SELECT * FROM pagamenti.fn_get_saldo_fattura(2147483647)',
  'P0001',
  NULL,
  '16) Una fattura che non esiste e'' rifiutata'
);

-- ⭐ Un'esclusione a zero o negativa non esce da nessuna interfaccia: e' un
--   chiamante rotto, e si ferma prima di leggere qualunque cosa.
SELECT throws_ok(
  format('SELECT * FROM pagamenti.fn_get_saldo_fattura(%s, 0)', (SELECT id FROM tmp_fattura)),
  'P0001',
  NULL,
  '17) Il guard rifiuta un''esclusione non positiva (fn_get_saldo_fattura)'
);

SELECT throws_ok(
  format('SELECT * FROM pagamenti.fn_get_saldo_fattura_contabili(%s, -1)', (SELECT id FROM tmp_fattura)),
  'P0001',
  NULL,
  '18) ...e anche la delegata la rifiuta (fn_get_saldo_fattura_contabili)'
);

SELECT * FROM finish();
ROLLBACK;
