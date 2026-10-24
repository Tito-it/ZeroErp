-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: le madri DB per lotto del fondo fattura — scope, chiavi, atomicita'
--       R-3 di brief-db-fondo-fattura-ricalcolo-e-governo.md §8.3
--       (changeSet 20260815-33 .. 20260815-35)
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): le sorgenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima
--   nascevano gia' DEFINITIVA).
-- ------------------------------------------------------------
-- Indice test
--  1) Riferimenti minimi presenti
--  2) Lo scope torna una riga per fattura del lotto
--  3) ⭐ La utility e' quella DELLA FATTURA, non del lotto/billing account
--  4) Lotto inesistente rifiutato (non confuso con «lotto vuoto»)
--  5) Parametro invalido rifiutato
--  6) Scope incompleto: il giro si ferma invece di non fare niente
--  7) ⭐ La validazione PRECEDE la scrittura: niente fondi per le altre
--  8) Codice interno del tipo fondo inesistente rifiutato
--  9) Lotto vuoto: zero, e nessun errore
-- 10) ⭐ La generazione gira una volta per CHIAVE, non per FATTURA
-- 11) La generazione crea i fondi delle sorgenti del lotto
-- 12) Seconda corsa: nessun fondo in piu' (atto unico)
-- 13) L'applicazione assegna i fondi alle figlie del lotto
-- 14) Cleanup completato
-- ------------------------------------------------------------
BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Qui conta doppio — il ponte lotto/fattura ha un guard DEFERRED sulla
--   coerenza degli stati, e senza SET CONSTRAINTS non scatterebbe mai.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(14);

-- ============================================================
-- 0) Riferimenti
-- ============================================================
CREATE TEMP TABLE tmp_cost_ffl AS
SELECT 'pgtap_fondi_lotto'::text AS test_scope;

CREATE TEMP TABLE tmp_refs_ffl AS WITH ba AS (
  SELECT b.id, b.utility_id
  FROM anagrafiche.billing_account b
  ORDER BY b.data_insert DESC NULLS LAST, b.id DESC
  LIMIT 1
)
SELECT script.fn_pgtap_registro_fattura(anagrafiche.fn_get_emittente_fiscale_id(ba.id)) AS registro_id,
  ba.id AS billing_account_id,
  ba.utility_id AS utility_id,
  -- ⚠️ Una SECONDA utility, diversa da quella del billing account: e' il
  --    perno del test 3. Se lo scope leggesse la utility dal lotto o dal BA
  --    — com'era in Python — la fattura che la usa sparirebbe dentro la
  --    chiave delle altre e nessuno se ne accorgerebbe.
  (
    SELECT u.id FROM config.utilities u
     WHERE u.id <> ba.utility_id
     ORDER BY u.id LIMIT 1
  ) AS utility_altra_id,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id,
  (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DEFINITIVA' AND attivo IS TRUE ORDER BY id LIMIT 1) AS stato_definitiva_id,
  (SELECT id FROM vendite.tipi_fondi_fattura WHERE attivo IS TRUE AND codice_interno = 'F_F_ADD_ACC' ORDER BY id LIMIT 1) AS tipo_fondo_id,
  (
    SELECT m.emittente_soggetto_ruolo_id
    FROM anagrafiche.emittenti_fiscali_billing_account m
    WHERE (m.billing_account_id = ba.id OR m.is_default IS TRUE)
    ORDER BY CASE WHEN m.billing_account_id = ba.id THEN 0 ELSE 1 END, m.id
    LIMIT 1
  ) AS emittente_soggetto_ruolo_id
FROM ba;

SELECT ok(
    (SELECT registro_id IS NOT NULL
        AND billing_account_id IS NOT NULL
        AND utility_id IS NOT NULL
        AND utility_altra_id IS NOT NULL
        AND tipo_doc_fiscale_id IS NOT NULL
        AND valuta_id IS NOT NULL
        AND stato_definitiva_id IS NOT NULL
        AND tipo_fondo_id IS NOT NULL
        AND emittente_soggetto_ruolo_id IS NOT NULL
     FROM tmp_refs_ffl),
    'Riferimenti minimi presenti (due utility distinte comprese)'
  );

-- ============================================================
-- Fixture: un lotto con tre figlie, due sorgenti, e un lotto rotto
-- ============================================================

-- Il lotto «buono». Nessuno stato fiscale: le figlie nascono senza stato, e
-- il guard di coerenza del ponte vuole che i due lati combacino.
-- ⚠️ rev 2026-10-24: le figlie non nascono piu' «senza stato» ma in DRAFT
--    (lo stato iniziale, che il trigger della nascita scrive). Provato sullo
--    scratch con un mondo costruito: il ponte verso il lotto senza stato
--    resta accettato dal guard di coerenza.
CREATE TEMP TABLE tmp_lotto_ffl AS WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
      competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id, meta)
  SELECT date_trunc('month', script.fn_data_operativa())::date,
         r.tipo_doc_fiscale_id, r.emittente_soggetto_ruolo_id,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_ffl))
    FROM tmp_refs_ffl r
  RETURNING id
) SELECT * FROM ins;

-- F1 e F2: STESSA chiave. F3: stessa chiave tranne la utility.
CREATE TEMP TABLE tmp_figlie_ffl AS WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, minimo, totale_a_pagare, meta)
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id, r.billing_account_id,
         r.tipo_doc_fiscale_id, r.valuta_id, v.utility_id, FALSE, v.totale,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_ffl),
                            'ruolo', v.ruolo)
    FROM tmp_refs_ffl r
    CROSS JOIN LATERAL (VALUES
        (r.utility_id,       300.00::NUMERIC, 'F1'),
        (r.utility_id,       400.00::NUMERIC, 'F2'),
        (r.utility_altra_id, 500.00::NUMERIC, 'F3')
    ) AS v(utility_id, totale, ruolo)
  RETURNING id, meta->>'ruolo' AS ruolo
) SELECT * FROM ins;

INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, meta)
SELECT (SELECT id FROM tmp_lotto_ffl), g.id,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_ffl))
  FROM tmp_figlie_ffl g;

-- Due sorgenti «di minimo», DEFINITIVE, con la chiave di F1/F2. ⚠️ NON stanno
-- nel lotto: le sorgenti si trovano per chiave, non per appartenenza.
CREATE TEMP TABLE tmp_sorgenti_ffl AS WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id,
      minimo, totale_a_pagare, meta)
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id, r.billing_account_id,
         r.tipo_doc_fiscale_id, r.valuta_id, r.utility_id,
         TRUE, v.totale,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_ffl),
                            'ruolo', v.ruolo)
    FROM tmp_refs_ffl r
    CROSS JOIN LATERAL (VALUES
        (100.00::NUMERIC, 'S1'),
        ( 60.00::NUMERIC, 'S2')
    ) AS v(totale, ruolo)
  RETURNING id, meta->>'ruolo' AS ruolo
) SELECT * FROM ins;

-- ⛔ Nate in bozza come ogni documento (rev 2026-10-24): si portano in
--    DEFINITIVA per la matrice, con indirizzi e intestazione scritti dai
--    building block della pipeline, come prima di emettere.
SELECT i.inserted_rows, t.scritta
  FROM (SELECT id FROM tmp_sorgenti_ffl) s
 CROSS JOIN LATERAL vendite.fn_snapshot_indirizzi_fattura(s.id) i
 CROSS JOIN LATERAL vendite.fn_snapshot_intestazione_fattura(s.id) t;
SELECT dbops.fn_pgtap_porta_a_stato('vendite.fatture', s.id, 'DEFINITIVA')
  FROM (SELECT id FROM tmp_sorgenti_ffl) s;

-- Un lotto VUOTO: esiste, non ha fatture. Non e' un errore — e' un giro che
-- non ha niente da fare, e va distinto dal lotto inesistente.
CREATE TEMP TABLE tmp_lotto_vuoto_ffl AS WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
      competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id, meta)
  SELECT date_trunc('month', script.fn_data_operativa())::date,
         r.tipo_doc_fiscale_id, r.emittente_soggetto_ruolo_id,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_ffl))
    FROM tmp_refs_ffl r
  RETURNING id
) SELECT * FROM ins;

-- Il lotto «rotto»: una fattura senza utility. Deve fermare il giro.
-- ⚠️ Insieme a lei ce n'e' una SANA, ed e' il perno del test 7: se la
--    validazione arrivasse dopo la scrittura, la fattura sana avrebbe gia'
--    prodotto i suoi fondi quando l'altra fa saltare tutto.
CREATE TEMP TABLE tmp_lotto_bad_ffl AS WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
      competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id, meta)
  SELECT date_trunc('month', script.fn_data_operativa())::date,
         r.tipo_doc_fiscale_id, r.emittente_soggetto_ruolo_id,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_ffl))
    FROM tmp_refs_ffl r
  RETURNING id
) SELECT * FROM ins;

CREATE TEMP TABLE tmp_figlia_bad_ffl AS WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, minimo, totale_a_pagare, meta)
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id, r.billing_account_id,
         r.tipo_doc_fiscale_id, r.valuta_id, FALSE, 250.00,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_ffl))
    FROM tmp_refs_ffl r
  RETURNING id
) SELECT * FROM ins;

-- La fattura SANA del lotto rotto: stessa chiave di F1/F2, quindi se il giro
-- scrivesse prima di validare, le sorgenti S1/S2 avrebbero gia' il loro fondo.
CREATE TEMP TABLE tmp_figlia_sana_bad_ffl AS WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, minimo, totale_a_pagare, meta)
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id, r.billing_account_id,
         r.tipo_doc_fiscale_id, r.valuta_id, r.utility_id, FALSE, 150.00,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_ffl))
    FROM tmp_refs_ffl r
  RETURNING id
) SELECT * FROM ins;

INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, meta)
SELECT (SELECT id FROM tmp_lotto_bad_ffl), v.fattura_id,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_ffl))
  FROM (VALUES
          ((SELECT id FROM tmp_figlia_bad_ffl)),
          ((SELECT id FROM tmp_figlia_sana_bad_ffl))
       ) AS v(fattura_id);

-- ============================================================
-- 1) e 2) Lo scope
-- ============================================================
SELECT is(
    (SELECT count(*)::INTEGER
       FROM vendite.fn_get_scope_fatture_lotto((SELECT id FROM tmp_lotto_ffl))),
    3,
    'Lo scope torna una riga per fattura del lotto'
  );

-- ⚠️ L'asserzione e' RELATIVA: due utility distinte fra le tre righe. Con la
--    utility presa dal lotto o dal billing account sarebbe UNA sola, e il
--    test lo vedrebbe. Contare le righe non basterebbe.
SELECT is(
    (SELECT count(DISTINCT s.utility_id)::INTEGER
       FROM vendite.fn_get_scope_fatture_lotto((SELECT id FROM tmp_lotto_ffl)) s),
    2,
    'La utility dello scope e'' quella della FATTURA, non del lotto o del billing account'
  );

-- ============================================================
-- 3) e 4) I due guard di parametro
-- ============================================================
-- ⚠️ P0001: errore di dominio da script.fn_log_and_raise_error. «Lotto
--    inesistente» non deve poter passare per «lotto vuoto»: darebbero
--    entrambi zero righe, e una delle due e' un errore del chiamante.
SELECT throws_ok(
    $$ SELECT * FROM vendite.fn_get_scope_fatture_lotto(999999999); $$,
    'P0001',
    NULL,
    'Lotto inesistente rifiutato, non confuso con «lotto vuoto»'
  );

SELECT throws_ok(
    format($$ SELECT * FROM vendite.fn_genera_fondi_fattura_lotto(%s, '   '); $$,
           (SELECT id FROM tmp_lotto_ffl)),
    'P0001',
    NULL,
    'Codice del tipo fondo vuoto rifiutato dalla madre'
  );

-- ============================================================
-- 5) Scope incompleto: si ferma
-- ============================================================
-- ⚠️ Prima questa fattura non fermava niente: la utility veniva rimpiazzata
--    con quella del billing account e il giro proseguiva SENZA FARE NULLA.
--    Una fattura emessa senza il fondo che le spettava non se ne accorge
--    nessuno; un task rosso si'.
SELECT throws_ok(
    format($$ SELECT * FROM vendite.fn_genera_fondi_fattura_lotto(%s, 'F_F_ADD_ACC'); $$,
           (SELECT id FROM tmp_lotto_bad_ffl)),
    'P0001',
    NULL,
    'Scope incompleto: il giro si ferma invece di non fare niente in silenzio'
  );

-- ⭐ E si ferma PRIMA di scrivere. La fattura sana del lotto rotto ha la chiave
--    di S1/S2: se la validazione arrivasse dopo, quelle due sorgenti avrebbero
--    gia' il loro fondo e il rollback dello statement sarebbe l'unica rete.
--    ⚠️ Vale perche' questo test gira PRIMA della generazione sul lotto buono.
SELECT is(
    (SELECT count(*)::INTEGER
       FROM vendite.fatture_fondi_fattura_source s
      WHERE s.fattura_sorgente_id IN (SELECT id FROM tmp_sorgenti_ffl)),
    0,
    'La validazione precede la scrittura: nessun fondo creato per le fatture sane del lotto rotto'
  );

-- ============================================================
-- 8) Il tipo di fondo si risolve dal CODICE INTERNO
-- ============================================================
-- ⚠️ E' la ragione per cui la firma prende una stringa e non un id: il
--    parametro arriva cosi' dalla configurazione del task, e un id
--    costringerebbe il chiamante a una query di lookup in piu' — cioe' a
--    perdere il «una SELECT per task» che e' il senso di questo passo.
SELECT throws_ok(
    format($$ SELECT * FROM vendite.fn_genera_fondi_fattura_lotto(%s, 'F_F_NON_ESISTE'); $$,
           (SELECT id FROM tmp_lotto_ffl)),
    'P0001',
    NULL,
    'Codice interno del tipo fondo inesistente rifiutato'
  );

-- ============================================================
-- 9) Lotto vuoto: zero, non un errore
-- ============================================================
-- ⚠️ «Vuoto» e «inesistente» danno entrambi zero righe di scope, ma sono due
--    risposte diverse: la prima e' legittima, la seconda e' un errore del
--    chiamante (test 4).
SELECT is(
    (SELECT g.fatture_count || '|' || g.chiavi_count || '|' || g.fondi_creati
       FROM vendite.fn_genera_fondi_fattura_lotto(
              (SELECT id FROM tmp_lotto_vuoto_ffl), 'F_F_ADD_ACC') g),
    '0|0|0',
    'Lotto vuoto: zero fatture, zero chiavi, zero fondi — e nessun errore'
  );

-- ============================================================
-- 10) e 11) La generazione per lotto
-- ============================================================
-- ⭐ Il cuore di R-3: tre fatture, DUE chiavi. La versione Python chiamava la
--    generazione una volta per FATTURA (il DISTINCT aveva l'id in
--    proiezione), quindi qui avrebbe fatto tre giri per due chiavi — e su un
--    lotto vero, centinaia per una.
SELECT is(
    (SELECT g.fatture_count || '|' || g.chiavi_count
       FROM vendite.fn_genera_fondi_fattura_lotto(
              (SELECT id FROM tmp_lotto_ffl),
              'F_F_ADD_ACC') g),
    '3|2',
    'La generazione gira una volta per CHIAVE (2) e non per FATTURA (3)'
  );

-- ⚠️ Si osservano le DUE SORGENTI e non il contatore globale: quante fatture
--    di minimo esistano nel database non dipende da questo test.
SELECT is(
    (SELECT count(*)::INTEGER
       FROM vendite.fatture_fondi_fattura_source s
      WHERE s.fattura_sorgente_id IN (SELECT id FROM tmp_sorgenti_ffl)
        AND s.stato = 'DISPONIBILE'),
    2,
    'La generazione crea il fondo di entrambe le sorgenti del lotto'
  );

-- ============================================================
-- 12) Atto unico anche dalla madre
-- ============================================================
SELECT vendite.fn_genera_fondi_fattura_lotto(
         (SELECT id FROM tmp_lotto_ffl),
         'F_F_ADD_ACC');

SELECT is(
    (SELECT count(*)::INTEGER
       FROM vendite.fatture_fondi_fattura_source s
      WHERE s.fattura_sorgente_id IN (SELECT id FROM tmp_sorgenti_ffl)),
    2,
    'Seconda corsa: nessun fondo in piu'' (l''atto e'' unico anche per lotto)'
  );

-- ============================================================
-- 13) L'applicazione per lotto
-- ============================================================
-- ⚠️ Si guardano gli stati delle due sorgenti e la figlia che le ha prese:
--    il contatore `fondi_applicati` dipenderebbe da quanti fondi DISPONIBILE
--    con questa chiave esistono nel database.
SELECT vendite.fn_applica_fondi_lotto(
         (SELECT id FROM tmp_lotto_ffl),
         'F_F_ADD_ACC');

SELECT is(
    (SELECT count(*)::INTEGER
       FROM vendite.fatture_fondi_fattura_source s
      WHERE s.fattura_sorgente_id IN (SELECT id FROM tmp_sorgenti_ffl)
        AND s.stato = 'ASSEGNATO'
        AND s.fattura_figlia_id IN (SELECT id FROM tmp_figlie_ffl)),
    2,
    'L''applicazione per lotto assegna i fondi alle figlie del lotto'
  );

-- ============================================================
-- Cleanup
-- ============================================================
DELETE FROM vendite.fatture_fondi_fattura
 WHERE fattura_id IN (SELECT id FROM tmp_figlie_ffl);

DELETE FROM vendite.fatture_fondi_fattura_source
 WHERE fattura_sorgente_id IN (SELECT id FROM tmp_sorgenti_ffl);

DELETE FROM vendite.fatturazione_lotti_fatture
 WHERE lotto_id IN (
   SELECT id FROM tmp_lotto_ffl
   UNION ALL SELECT id FROM tmp_lotto_bad_ffl
   UNION ALL SELECT id FROM tmp_lotto_vuoto_ffl);

DELETE FROM vendite.fatture
 WHERE id IN (
   SELECT id FROM tmp_figlie_ffl
   UNION ALL SELECT id FROM tmp_sorgenti_ffl
   UNION ALL SELECT id FROM tmp_figlia_bad_ffl
   UNION ALL SELECT id FROM tmp_figlia_sana_bad_ffl);

DELETE FROM vendite.fatturazione_lotti
 WHERE id IN (
   SELECT id FROM tmp_lotto_ffl
   UNION ALL SELECT id FROM tmp_lotto_bad_ffl
   UNION ALL SELECT id FROM tmp_lotto_vuoto_ffl);

SELECT is(
    (SELECT count(*)::INTEGER
       FROM vendite.fatture_fondi_fattura_source s
      WHERE s.fattura_sorgente_id IN (SELECT id FROM tmp_sorgenti_ffl))
    + (SELECT count(*)::INTEGER
         FROM vendite.fatturazione_lotti l
        WHERE l.id IN (SELECT id FROM tmp_lotto_ffl
                       UNION ALL SELECT id FROM tmp_lotto_bad_ffl
                       UNION ALL SELECT id FROM tmp_lotto_vuoto_ffl)),
    0,
    'Cleanup completato'
  );

SELECT * FROM finish();
ROLLBACK;
