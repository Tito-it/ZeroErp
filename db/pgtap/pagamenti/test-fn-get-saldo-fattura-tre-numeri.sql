-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: IL SALDO DELLA FATTURA IN TRE NUMERI — pagamenti.fn_get_saldo_fattura
--
-- Elenco test (plan 13):
--  1) Riferimenti minimi presenti (i due centri che servono, e sono diversi)
--  2) Una fattura senza niente sopra: residuo = totale, gli altri a zero
--  3) Una riga pronta su una distinta viva finisce in `in_lavorazione`
--  4) ...e il residuo NON si muove: dichiarare non e' registrare
--  5) `in_lavorazione` E' la risposta di fn_get_saldo_fattura_contabili
--  6) Dopo il posting su BANCA il residuo cala
--  7) ...e `incassato` sale: quel denaro e' arrivato davvero
--  8) ...e `in_lavorazione` torna a zero: la distinta e' chiusa
--  9) ⭐ Un movimento su un centro FONDO FATTURA fa calare il residuo
-- 10) ⭐ ...e NON tocca `incassato`: quei centri non sono cassa
-- 11) QUADRATURA: residuo = totale - somma dei movimenti attivi
-- 12) Il guard di parametro rifiuta un id non positivo
-- 13) Una fattura che non esiste e' rifiutata
--
-- Scopo:
--  - collaudare il passo S5-1, in cui la funzione passa da DUE numeri a TRE.
--    ⭐ Il cuore sono i test 9 e 10, ed e' l'unica coppia che distingue
--    `incassato` da `saldo`: senza un movimento su un centro interno il test
--    passerebbe anche se `incassato` fosse una copia del residuo — cioe'
--    passerebbe proprio nel caso in cui la colonna nuova non serve a niente;
--  - presidiare la DELEGA (test 5): `in_lavorazione` non e' una seconda
--    formula scritta qui, e' cio' che risponde la funzione che gia' lo sa. Se
--    un giorno qualcuno la riscrivesse, questo test diventa rosso;
--  - verificare che i due numeri VECCHI rispondano come prima (test 2, 6, 11).
--
-- Piano: brief-db-posting-e-abbinamento-rata.md
--        §2.3-ter S5-1 · lotto 8 · richiesta DB-10 del brief BE/FE (Q-10)
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione (OPERATORE +
--   RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI: senza, non verrebbero mai esercitati (si chiude in
--   ROLLBACK) e il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_saldo_fattura_tre'::text AS test_scope;

-- ⚠️ I centri NON si fabbricano: sono seminati dal lotto 1 e i due ruoli
--   interni sono unici per vincolo. Un test che se li crea da solo non
--   verifica il seed: lo nasconde.
-- ⭐ Qui ne servono DUE, e la differenza fra loro E' l'oggetto del test:
--   BANCA e' cassa, il centro `is_fondo_fattura` no.
CREATE TEMP TABLE tmp_refs AS
WITH ba AS (
  SELECT b.id, b.utility_id
    FROM anagrafiche.billing_account b
   ORDER BY b.data_insert DESC NULLS LAST, b.id DESC
   LIMIT 1
)
SELECT script.fn_pgtap_registro_fattura(anagrafiche.fn_get_emittente_fiscale_id(ba.id)) AS registro_id,
       ba.id                                                                         AS billing_account_id,
       ba.utility_id                                                                 AS utility_id,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1)                            AS valuta_id,
       (SELECT m.emittente_soggetto_ruolo_id
          FROM anagrafiche.emittenti_fiscali_billing_account m
         WHERE (m.billing_account_id = ba.id OR m.is_default IS TRUE)
         ORDER BY CASE WHEN m.billing_account_id = ba.id THEN 0 ELSE 1 END, m.id
         LIMIT 1)                                                                    AS emittente_soggetto_ruolo_id,
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
  FROM ba;

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
  '1) Riferimenti minimi presenti, e i due centri sono davvero diversi'
);

-- La fattura da incassare: 300.
CREATE TEMP TABLE tmp_fattura AS
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, totale_a_pagare, meta)
  SELECT r.registro_id, current_date, r.emittente_soggetto_ruolo_id, r.billing_account_id,
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
-- La distinta di cassa, con una riga pronta da 100
-- ============================================================
CREATE TEMP TABLE tmp_contabile_banca AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_banca_id FROM tmp_refs),
    p_data_contabile        => current_date,
    p_data_registrazione    => current_date,
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
    p_origine               => 'MANUALE'
  ) AS contabile_id;

INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, data_valuta, importo,
     fattura_id, billing_account_id, stato_id, meta)
SELECT (SELECT contabile_id FROM tmp_contabile_banca), 'PGTAP_SALDO_A',
       current_date, current_date, 100.00,
       (SELECT id FROM tmp_fattura), r.billing_account_id, r.stato_abbinata_id,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r;

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
  '6) Dopo il posting su BANCA il residuo cala');

SELECT is((SELECT incassato FROM tmp_saldo_dopo_banca), 100.00::numeric,
  '7) ...e `incassato` sale: quel denaro e'' arrivato davvero');

SELECT is((SELECT in_lavorazione FROM tmp_saldo_dopo_banca), 0::numeric,
  '8) ...e `in_lavorazione` torna a zero: la distinta e'' chiusa');

-- ============================================================
-- ⭐ Il caso che distingue le due colonne: un centro che NON e' cassa
-- ============================================================
-- Una seconda distinta, sul centro dei fondi fattura: e' il giro interno, il
-- denaro si sposta ma in banca non entra niente.
CREATE TEMP TABLE tmp_contabile_fondo AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_fondo_id FROM tmp_refs),
    p_data_contabile        => current_date,
    p_data_registrazione    => current_date,
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
    p_origine               => 'GENERATA'
  ) AS contabile_id;

INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, data_valuta, importo,
     fattura_id, billing_account_id, stato_id, meta)
SELECT (SELECT contabile_id FROM tmp_contabile_fondo), 'PGTAP_SALDO_B',
       current_date, current_date, 50.00,
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
  '9) Un movimento su un centro FONDO FATTURA fa calare il residuo');

-- ⭐ L'asserzione che rende utile la colonna nuova: senza questa, `incassato`
--   potrebbe essere una copia del residuo e nessuno se ne accorgerebbe.
SELECT is((SELECT incassato FROM tmp_saldo_dopo_fondo), 100.00::numeric,
  '10) ...e NON tocca `incassato`: fondo fattura e compensazione non sono cassa');

-- ============================================================
-- 11) La quadratura, che non nomina il meccanismo
-- ============================================================
SELECT is(
  (SELECT s.saldo FROM pagamenti.fn_get_saldo_fattura((SELECT id FROM tmp_fattura)) s),
  (SELECT f.totale_a_pagare - COALESCE(SUM(m.importo), 0)
     FROM vendite.fatture f
     LEFT JOIN pagamenti.vendite_movimenti m
       ON m.fattura_id = f.id AND m.attivo IS TRUE
    WHERE f.id = (SELECT id FROM tmp_fattura)
    GROUP BY f.totale_a_pagare),
  '11) Quadratura: residuo = totale meno la somma dei movimenti attivi'
);

-- ============================================================
-- 12-13) I due guard, con lo SQLSTATE dichiarato
-- ============================================================
-- ⚠️ Senza SQLSTATE, throws_ok accetterebbe qualunque errore, compreso il
--   crash del guard. P0001 = errore di dominio.
SELECT throws_ok(
  'SELECT * FROM pagamenti.fn_get_saldo_fattura(0)',
  'P0001',
  NULL,
  '12) Il guard di parametro rifiuta un id non positivo'
);

SELECT throws_ok(
  'SELECT * FROM pagamenti.fn_get_saldo_fattura(2147483647)',
  'P0001',
  NULL,
  '13) Una fattura che non esiste e'' rifiutata'
);

SELECT * FROM finish();
ROLLBACK;
