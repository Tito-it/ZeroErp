-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: le madri DB per lotto del fondo fattura — scope, chiavi, atomicita'
--       R-3 di brief-db-fondo-fattura-ricalcolo-e-governo.md §8.3
--       (changeSet 20260815-33 .. 20260815-35)
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): le sorgenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima
--   nascevano gia' DEFINITIVA).
-- rev 2026-10-24 (brief-modello-documento-vendita Q-4): cliente, azienda e
--   registro li costruisce dbops.fn_pgtap_crea_mondo_cliente (+
--   script.fn_pgtap_registro_fattura) invece di pescare il primo billing
--   account, che su un database ricostruito non c'e'. Il contesto si apre
--   DOPO, sull'operatore del mondo. Lotti, figlie e sorgenti restano costruiti
--   dal file: sono il caso del test.
-- rev 2026-10-24 (brief-modello-documento-vendita R-5): F1, F2, la figlia sana
--   del lotto rotto e le due sorgenti le scrive dbops.fn_pgtap_crea_fattura
--   (minimo e totale alla nascita; le sorgenti fino a DEFINITIVA coi suoi
--   snapshot). Restano a mano F3 (utility diversa dal BA) e la figlia senza
--   utility: sono il caso, e il builder la utility la scrive sempre. I lotti
--   e il ponte restano del test.
-- rev 2026-10-24 (brief-modello-documento-vendita §4-octies): la figlia senza
--   utility la scrive dbops.fn_pgtap_crea_fattura(..., p_senza_utility => true)
--   (changeSet 20261024-42), sul cliente del mondo. Resta a mano solo F3, la
--   utility DIVERSA da quella del cliente: compare in questo file soltanto
--   (regola del 2), niente builder.
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

-- Il mondo PRIMA del contesto: azienda, operatore e cliente. Poi il test
-- gira come gira l'applicazione (ruolo OPERATORE + RLS attiva), sull'operatore
-- del mondo.
CREATE TEMP TABLE tmp_mondo_ffl AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('fondi_lotto');

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_mondo_ffl)); END $ctx$;

SELECT plan(14);

-- ============================================================
-- 0) Riferimenti
-- ============================================================
CREATE TEMP TABLE tmp_cost_ffl AS
SELECT 'pgtap_fondi_lotto'::text AS test_scope;

-- I riferimenti del documento sono quelli del mondo: il registro e' quello
-- della sua azienda (lo crea se non c'e').
CREATE TEMP TABLE tmp_refs_ffl AS
SELECT script.fn_pgtap_registro_fattura(m.emittente_soggetto_ruolo_id) AS registro_id,
  m.billing_account_id,
  m.utility_id,
  -- ⚠️ Una SECONDA utility, diversa da quella del billing account: e' il
  --    perno del test 3. Se lo scope leggesse la utility dal lotto o dal BA
  --    — com'era in Python — la fattura che la usa sparirebbe dentro la
  --    chiave delle altre e nessuno se ne accorgerebbe.
  (
    SELECT u.id FROM config.utilities u
     WHERE u.id <> m.utility_id
     ORDER BY u.id LIMIT 1
  ) AS utility_altra_id,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id,
  (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DEFINITIVA' AND attivo IS TRUE ORDER BY id LIMIT 1) AS stato_definitiva_id,
  (SELECT id FROM vendite.tipi_fondi_fattura WHERE attivo IS TRUE AND codice_interno = 'F_F_ADD_ACC' ORDER BY id LIMIT 1) AS tipo_fondo_id,
  m.emittente_soggetto_ruolo_id
FROM tmp_mondo_ffl m;

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

-- Il lotto «buono»: l'INSERT non dice lo stato, e il lotto nasce nello stato
-- iniziale come le sue figlie (lo scrive il trigger della nascita, su lotto e
-- fattura). Il guard di coerenza del ponte vuole che i due lati combacino.
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
-- ⭐ F1 e F2 le scrive il builder (rev 2026-10-24, R-5): cliente del mondo
--    (terzo parametro), totale alla nascita, in bozza. Un builder per
--    istruzione: la tabella si legge dopo.
CREATE TEMP TABLE tmp_figlie_ffl AS
SELECT f.fattura_id AS id, 'F1'::text AS ruolo
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_lotto', 'DRAFT', (SELECT billing_account_id FROM tmp_refs_ffl),
         false, false, p_minimo => false, p_totale_a_pagare => 300.00) f;

INSERT INTO tmp_figlie_ffl (id, ruolo)
SELECT f.fattura_id, 'F2'
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_lotto', 'DRAFT', (SELECT billing_account_id FROM tmp_refs_ffl),
         false, false, p_minimo => false, p_totale_a_pagare => 400.00) f;

-- ⚠️ F3 resta a mano: la sua utility NON e' quella del billing account, ed e'
--    il perno del test 3; il builder scrive sempre quella del BA.
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, minimo, totale_a_pagare, meta)
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id, r.billing_account_id,
         r.tipo_doc_fiscale_id, r.valuta_id, r.utility_altra_id, FALSE, 500.00,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_ffl),
                            'ruolo', 'F3')
    FROM tmp_refs_ffl r
  RETURNING id, meta->>'ruolo' AS ruolo
)
INSERT INTO tmp_figlie_ffl (id, ruolo)
SELECT id, ruolo FROM ins;

INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, meta)
SELECT (SELECT id FROM tmp_lotto_ffl), g.id,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_ffl))
  FROM tmp_figlie_ffl g;

-- Due sorgenti «di minimo», DEFINITIVE, con la chiave di F1/F2. ⚠️ NON stanno
-- nel lotto: le sorgenti si trovano per chiave, non per appartenenza.
-- ⭐ Le scrive il builder (rev 2026-10-24, R-5): minimo e totale alla nascita,
--    e fuori bozza indirizzi, intestazione e matrice fino a DEFINITIVA.
CREATE TEMP TABLE tmp_sorgenti_ffl AS
SELECT f.fattura_id AS id, 'S1'::text AS ruolo
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_lotto', 'DEFINITIVA', (SELECT billing_account_id FROM tmp_refs_ffl),
         false, false, p_minimo => true, p_totale_a_pagare => 100.00) f;

INSERT INTO tmp_sorgenti_ffl (id, ruolo)
SELECT f.fattura_id, 'S2'
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_lotto', 'DEFINITIVA', (SELECT billing_account_id FROM tmp_refs_ffl),
         false, false, p_minimo => true, p_totale_a_pagare => 60.00) f;

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

-- ⭐ La fattura SENZA utility dal builder (rev 2026-10-24, §4-octies):
--    p_senza_utility, sul cliente del mondo, totale alla nascita, in bozza.
CREATE TEMP TABLE tmp_figlia_bad_ffl AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_lotto', 'DRAFT', (SELECT billing_account_id FROM tmp_refs_ffl),
         p_minimo => false, p_totale_a_pagare => 250.00,
         p_senza_utility => true) f;

-- La fattura SANA del lotto rotto: stessa chiave di F1/F2, quindi se il giro
-- scrivesse prima di validare, le sorgenti S1/S2 avrebbero gia' il loro fondo.
-- ⭐ Dal builder (rev 2026-10-24, R-5): e' una figlia qualunque del cliente.
CREATE TEMP TABLE tmp_figlia_sana_bad_ffl AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_lotto', 'DRAFT', (SELECT billing_account_id FROM tmp_refs_ffl),
         false, false, p_minimo => false, p_totale_a_pagare => 150.00) f;

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
