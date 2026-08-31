-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.trgfn_fatture_righe_guard_normalize — esigibilita e split_payment
--       brief-db-be-iva-risolutore-e-regime-cliente, voce `I5` (meta' DB)
-- ------------------------------------------------------------
-- A cosa serve, in una frase
--   Le due colonne esistevano da sempre, erano nel raggruppamento del riepilogo,
--   ed erano NULL su TUTTE le righe: non le scriveva nessuno. Dal changeSet
--   20260829-54 le scrive il trigger, derivandole dal soggetto CLIENTE. Questo
--   file e' cio' che impedisce a quello scrittore di sparire in silenzio.
--
-- ⭐ PERCHE' LE DUE META' NON SI PROVANO ALLO STESSO MODO
--   `split_payment` e' una derivazione pura e si riscrive SEMPRE: non esiste
--   una scelta legittima per riga. `esigibilita` no — con la scissione 'S' e'
--   IMPOSTA, ma senza restano 'I' e 'D', e la DIFFERITA e' una scelta del
--   documento che nessuna colonna sa dedurre. Percio' fuori dalla scissione il
--   trigger riempie solo il VUOTO.
--   ⚠️ E' la parte che si romperebbe per «semplificazione»: un domani qualcuno
--   uniforma i due rami «perche' fanno la stessa cosa», e una 'D' scelta da un
--   operatore sparisce senza un errore. I casi 4 e 5 sono li' per quello.
--
-- ⛔ IL CASO 7 E' QUELLO CHE SPIEGA LA SEDE
--   Il riepilogo RAGGRUPPA per (iva, natura, esigibilita, split). Se due righe
--   della stessa fattura portassero valori diversi, la stessa aliquota si
--   spezzerebbe in DUE riepiloghi e la fattura direbbe due cose sul proprio
--   regime. E' il motivo per cui questi campi si derivano nel trigger e non nel
--   chiamante.
--
-- Indice test
-- 1) La fixture e completa
-- 2) Cliente NON scisso: la riga nasce con split=false ed esigibilita='I'
-- 3) Cliente scisso: la riga nasce con split=true ed esigibilita='S'
-- 4) ⭐ Una 'D' scelta SOPRAVVIVE quando il cliente non e scisso
-- 5) ⛔ Ma NON sopravvive quando il cliente e scisso: la 'S' e imposta
-- 6) split_payment si riscrive SEMPRE: una riga che dissente viene riallineata
-- 7) ⭐ Il riepilogo porta gli stessi valori, e resta UNA riga sola
-- 8) Cleanup
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: RLS attiva, come gira l'applicazione.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- ============================================================
-- La fixture
-- ============================================================
-- ⚠️ Emittente e billing account NON si scelgono in modo indipendente:
--   fn_ricalcola_totali_fattura pretende la configurazione (emittente, utility)
--   su anagrafiche.emittenti_fiscali_utilities. Si parte DALLA configurazione.
CREATE TEMP TABLE tmp_es_refs AS
WITH cfg AS (
  SELECT efu.emittente_soggetto_ruolo_id, efu.utility_id
    FROM anagrafiche.emittenti_fiscali_utilities efu
   WHERE efu.attivo IS TRUE
     AND EXISTS (SELECT 1 FROM anagrafiche.billing_account ba
                  WHERE ba.utility_id = efu.utility_id)
   ORDER BY efu.emittente_soggetto_ruolo_id, efu.utility_id
   LIMIT 1
)
SELECT (SELECT emittente_soggetto_ruolo_id FROM cfg) AS emittente_soggetto_ruolo_id,
       (SELECT utility_id FROM cfg)                  AS utility_id,
       (SELECT ba.id FROM anagrafiche.billing_account ba
         WHERE ba.utility_id = (SELECT utility_id FROM cfg)
         ORDER BY ba.id LIMIT 1)                     AS billing_account_id,
       -- ⭐ un codice IVA con aliquota > 0: una prova fra zeri passerebbe
       --   anche con il riepilogo rotto
       (SELECT i.id FROM config.iva i
         WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
         ORDER BY i.id LIMIT 1)                      AS iva_id,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE
         ORDER BY id LIMIT 1)                        AS tipo_doc_fiscale_id,
       (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DRAFT'
         ORDER BY id LIMIT 1)                        AS stato_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id;

-- il soggetto CLIENTE della fattura: e' lui a portare la scissione (D8)
CREATE TEMP TABLE tmp_es_sogg AS
SELECT sr.soggetto_id
  FROM tmp_es_refs r
  JOIN anagrafiche.billing_account ba ON ba.id = r.billing_account_id
  JOIN anagrafiche.soggetti_ruoli sr  ON sr.id = ba.soggetto_ruolo_id;

SELECT ok(
  (SELECT emittente_soggetto_ruolo_id IS NOT NULL
      AND billing_account_id IS NOT NULL
      AND iva_id IS NOT NULL
      AND tipo_doc_fiscale_id IS NOT NULL
      AND stato_doc_fiscale_id IS NOT NULL
     FROM tmp_es_refs)
  AND EXISTS (SELECT 1 FROM tmp_es_sogg WHERE soggetto_id IS NOT NULL),
  '1) la fixture e completa: configurazione, billing account e soggetto cliente'
);

-- il registro e la fattura
CREATE TEMP TABLE tmp_es_reg AS
WITH ins AS (
  -- ⛔ emittente_soggetto_ruolo_id e' NOT NULL dal 2026-08-30 (C1-2,
  --   20260830-11), e dev'essere lo STESSO delle fatture di questo file:
  --   vendite.trgfn_fatture_guard_registro_emittente rifiuta un documento
  --   sul registro di un altro emittente (C1-3, 20260830-10).
  INSERT INTO vendite.registri_fatturazione (codice, descrizione, reset_policy, attivo,
          emittente_soggetto_ruolo_id, meta)
  VALUES ('REGESIG_PGTAP', 'Registro test esigibilita', 'ANNUALE', true,
          (SELECT emittente_soggetto_ruolo_id FROM tmp_es_refs),
          jsonb_build_object('test_scope', 'pgtap_esigibilita'))
  RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_es_fatt AS
WITH ins AS (
  INSERT INTO vendite.fatture
      (registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
       tipo_doc_fiscale_id, stato_doc_fiscale_id, valuta_id, utility_id, meta)
  SELECT (SELECT id FROM tmp_es_reg), current_date,
         r.emittente_soggetto_ruolo_id, r.billing_account_id,
         r.tipo_doc_fiscale_id, r.stato_doc_fiscale_id, r.valuta_id, r.utility_id,
         jsonb_build_object('test_scope', 'pgtap_esigibilita')
    FROM tmp_es_refs r
  RETURNING id)
SELECT * FROM ins;

-- ============================================================
-- 2) Cliente NON scisso
-- ============================================================
UPDATE anagrafiche.soggetti SET split_payment = 'N'
 WHERE id = (SELECT soggetto_id FROM tmp_es_sogg);

INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id, meta)
SELECT (SELECT id FROM tmp_es_fatt), 1, 'Riga non scissa', 1, 100, r.iva_id,
       jsonb_build_object('test_scope', 'pgtap_esigibilita')
  FROM tmp_es_refs r;

SELECT is(
  (SELECT COALESCE(esigibilita::text, 'NULL') || '/' || COALESCE(split_payment::text, 'NULL')
     FROM vendite.fatture_righe
    WHERE fattura_id = (SELECT id FROM tmp_es_fatt) AND riga_nr = 1),
  'I/false',
  '2) cliente non scisso: la riga nasce con esigibilita I e split false'
);

-- ============================================================
-- 3) Cliente scisso
-- ============================================================
UPDATE anagrafiche.soggetti SET split_payment = 'S'
 WHERE id = (SELECT soggetto_id FROM tmp_es_sogg);

INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id, meta)
SELECT (SELECT id FROM tmp_es_fatt), 2, 'Riga scissa', 1, 100, r.iva_id,
       jsonb_build_object('test_scope', 'pgtap_esigibilita')
  FROM tmp_es_refs r;

SELECT is(
  (SELECT COALESCE(esigibilita::text, 'NULL') || '/' || COALESCE(split_payment::text, 'NULL')
     FROM vendite.fatture_righe
    WHERE fattura_id = (SELECT id FROM tmp_es_fatt) AND riga_nr = 2),
  'S/true',
  '3) cliente scisso: la riga nasce con esigibilita S e split true'
);

-- ============================================================
-- 4) ⭐ La DIFFERITA sopravvive, quando il cliente non e' scisso
-- ============================================================
-- ⛔ E' la meta' che si perde per «semplificazione»: 'D' non e' deducibile da
--   nessuna colonna, e' una scelta del documento. Un trigger che sovrascrivesse
--   anche qui la cancellerebbe SENZA UN ERRORE — l'operatore vedrebbe 'I' e non
--   saprebbe mai che la sua scelta e' stata buttata.
UPDATE anagrafiche.soggetti SET split_payment = 'N'
 WHERE id = (SELECT soggetto_id FROM tmp_es_sogg);

INSERT INTO vendite.fatture_righe
    (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id, esigibilita, meta)
SELECT (SELECT id FROM tmp_es_fatt), 3, 'Riga differita', 1, 100, r.iva_id, 'D',
       jsonb_build_object('test_scope', 'pgtap_esigibilita')
  FROM tmp_es_refs r;

SELECT is(
  (SELECT esigibilita::text FROM vendite.fatture_righe
    WHERE fattura_id = (SELECT id FROM tmp_es_fatt) AND riga_nr = 3),
  'D',
  '4) su cliente non scisso una D esplicita SOPRAVVIVE: il trigger riempie il vuoto, non sovrascrive'
);

-- ============================================================
-- 5) ⛔ Ma con la scissione la 'D' NON sopravvive
-- ============================================================
-- ⚠️ Il caso 4 da solo sarebbe pericoloso: farebbe credere che l'esigibilita'
--   sia sempre negoziabile. Non lo e' — con la scissione dei pagamenti la 'S'
--   e' imposta dalla legge, e un documento che dicesse 'D' sarebbe sbagliato.
UPDATE anagrafiche.soggetti SET split_payment = 'S'
 WHERE id = (SELECT soggetto_id FROM tmp_es_sogg);

INSERT INTO vendite.fatture_righe
    (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id, esigibilita, meta)
SELECT (SELECT id FROM tmp_es_fatt), 4, 'Riga differita ma scissa', 1, 100, r.iva_id, 'D',
       jsonb_build_object('test_scope', 'pgtap_esigibilita')
  FROM tmp_es_refs r;

SELECT is(
  (SELECT esigibilita::text FROM vendite.fatture_righe
    WHERE fattura_id = (SELECT id FROM tmp_es_fatt) AND riga_nr = 4),
  'S',
  '5) con la scissione la S e IMPOSTA: una D esplicita non sopravvive'
);

-- ============================================================
-- 6) `split_payment` si riscrive SEMPRE
-- ============================================================
-- ⚠️ Qui non c'e' niente da negoziare: una riga che dissentisse dal proprio
--   cliente e' un errore, non un'eccezione. Si prova sull'UPDATE, che e' la via
--   con cui un valore sbagliato entrerebbe davvero.
UPDATE vendite.fatture_righe SET split_payment = false, descrizione = 'Riga scissa (ritoccata)'
 WHERE fattura_id = (SELECT id FROM tmp_es_fatt) AND riga_nr = 2;

SELECT is(
  (SELECT split_payment FROM vendite.fatture_righe
    WHERE fattura_id = (SELECT id FROM tmp_es_fatt) AND riga_nr = 2),
  true,
  '6) split_payment si riallinea al cliente anche se qualcuno prova a scriverlo diverso'
);

-- ============================================================
-- 7) ⭐ Il riepilogo porta gli stessi valori, e resta UNA riga
-- ============================================================
-- ⛔ E' il caso che spiega perche' la sede e' il trigger. Il riepilogo raggruppa
--   per (iva, natura, esigibilita, split): se le righe della stessa fattura
--   portassero valori diversi, la stessa aliquota uscirebbe in DUE riepiloghi e
--   la fattura direbbe due cose sul proprio regime.
-- ⚠️ Si riallineano prima tutte le righe con un UPDATE a vuoto: le prime tre
--   sono nate quando il cliente aveva un flag diverso, ed e' l'unico modo in cui
--   la divergenza puo' esistere davvero.
UPDATE vendite.fatture_righe SET descrizione = descrizione
 WHERE fattura_id = (SELECT id FROM tmp_es_fatt);

SELECT * FROM vendite.fn_ricalcola_riepilogo_iva_fattura((SELECT id FROM tmp_es_fatt));

SELECT is(
  (SELECT count(*)::text || ':' || max(COALESCE(esigibilita::text, 'NULL'))
       || '/' || max(COALESCE(split_payment::text, 'NULL'))
     FROM vendite.fatture_riepiloghi_iva
    WHERE fattura_id = (SELECT id FROM tmp_es_fatt)),
  '1:S/true',
  '7) il riepilogo e UNA riga sola e porta gli stessi valori delle righe'
);

-- ============================================================
-- 8) Smontaggio
-- ============================================================
UPDATE vendite.fatture_righe SET storicizza = false
 WHERE fattura_id = (SELECT id FROM tmp_es_fatt);
UPDATE vendite.fatture SET storicizza = false WHERE id = (SELECT id FROM tmp_es_fatt);
UPDATE vendite.registri_fatturazione SET storicizza = false WHERE id = (SELECT id FROM tmp_es_reg);

DELETE FROM vendite.fatture_riepiloghi_iva WHERE fattura_id = (SELECT id FROM tmp_es_fatt);
DELETE FROM vendite.fatture_righe WHERE fattura_id = (SELECT id FROM tmp_es_fatt);
DELETE FROM vendite.fatture WHERE id = (SELECT id FROM tmp_es_fatt);
DELETE FROM vendite.registri_fatturazione_progressivi WHERE registro_id = (SELECT id FROM tmp_es_reg);
DELETE FROM vendite.registri_fatturazione WHERE id = (SELECT id FROM tmp_es_reg);

SELECT ok(true, '8) cleanup completato');

SELECT * FROM finish();

ROLLBACK;
