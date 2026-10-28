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
-- ⭐ rev 2026-10-01 (D-7 di brief-db-esigibilita-iva-per-cassa-emittente):
--   ENTRAMBE le colonne sono una derivazione pura e si riscrivono SEMPRE.
--   Fino al 2026-09-30 fuori dalla scissione il trigger riempiva solo il
--   VUOTO, perche' una 'D' poteva venire solo da una persona, e il caso 4
--   pretendeva che una 'D' scritta a mano sopravvivesse. Con l'IVA per cassa
--   anche la 'D' e' DEDOTTA (dal regime dell'emittente), e una colonna non sa
--   dire chi l'ha scritta: il «solo il vuoto» lasciava valori stantii. Il caso
--   4 ora pretende il contrario, ed e' il cambio deciso. I casi del regime per
--   cassa stanno in vendite/test-esigibilita-iva-per-cassa-v1.sql.
--   ⚠️ La fixture fissa l'emittente a RF01: prende un emittente dai DATI, e
--   il suo regime decide l'esigibilita' — un emittente per cassa sporcherebbe
--   i casi 2 e 4 senza che il test lo dica.
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
-- 4) ⭐ D-7: una 'D' scritta a mano NON sopravvive su un emittente ordinario
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
-- ⭐ Rev 2026-10-10 (brief-db-dati-fiscali-e-societari-del-soggetto, A-3): il
--   cliente deve poter essere scisso. Da trgfn_soggetti_guard_regime_pa
--   (20261010-86) split_payment = 'S' su una natura che non lo ammette (un
--   privato, una ditta individuale) o senza natura e' rifiutato, e il caso 3
--   morirebbe sul guard invece di misurare il trigger. Si scelgono quindi solo
--   i billing account il cui cliente ha una natura con split_payment_ammesso:
--   e' un filtro sulla CONFIGURAZIONE, non sui dati. Il primo account per id,
--   su dbdev al 2026-10-10, era di un privato.
CREATE TEMP VIEW ba_scindibili AS
SELECT ba.id, ba.utility_id
  FROM anagrafiche.billing_account ba
  JOIN anagrafiche.soggetti_ruoli sr          ON sr.id  = ba.soggetto_ruolo_id
  JOIN anagrafiche.soggetti s                 ON s.id   = sr.soggetto_id
  JOIN config.tipi_soggetto_dettaglio tsd     ON tsd.id = s.tipo_soggetto_dettaglio_id
 WHERE tsd.split_payment_ammesso;

-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba, BA dell'azienda di chi agisce) e
--   l'emittente e' quello dell'operatore di contesto. Prima la coppia
--   (emittente, utility) si pescava da emittenti_fiscali_utilities e il BA era
--   il primo scindibile del DB: da zero non c'era niente. Il filtro
--   ba_scindibili resta, sul BA costruito: e' la premessa del caso 3, e se il
--   builder cambiasse natura al cliente il test 1 lo direbbe. Registro e
--   fattura restano scritti a mano, coi valori da qui.
CREATE TEMP TABLE tmp_es_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('esigibilita split');

CREATE TEMP TABLE tmp_es_refs AS
SELECT script.fn_pgtap_emittente_sr_operatore()      AS emittente_soggetto_ruolo_id,
       (SELECT utility_id FROM tmp_es_cli)           AS utility_id,
       (SELECT b.id FROM pg_temp.ba_scindibili b
         WHERE b.id = (SELECT billing_account_id FROM tmp_es_cli)) AS billing_account_id,
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

-- ⭐ L'emittente della fixture viene dai dati: si fissa il suo regime a RF01,
--   o un emittente per cassa cambierebbe l'esigibilita' attesa (rev 2026-10-01).
UPDATE anagrafiche.emittenti_fiscali SET regime_fiscale_rf = 'RF01'
 WHERE soggetto_ruolo_id = (SELECT emittente_soggetto_ruolo_id FROM tmp_es_refs);

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
  SELECT (SELECT id FROM tmp_es_reg), script.fn_data_operativa(),
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

INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id, meta, competenza_dal, competenza_al)
SELECT (SELECT id FROM tmp_es_fatt), 1, 'Riga non scissa', 1, 100, r.iva_id,
       jsonb_build_object('test_scope', 'pgtap_esigibilita'), script.fn_data_operativa(), script.fn_data_operativa()
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

INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id, meta, competenza_dal, competenza_al)
SELECT (SELECT id FROM tmp_es_fatt), 2, 'Riga scissa', 1, 100, r.iva_id,
       jsonb_build_object('test_scope', 'pgtap_esigibilita'), script.fn_data_operativa(), script.fn_data_operativa()
  FROM tmp_es_refs r;

SELECT is(
  (SELECT COALESCE(esigibilita::text, 'NULL') || '/' || COALESCE(split_payment::text, 'NULL')
     FROM vendite.fatture_righe
    WHERE fattura_id = (SELECT id FROM tmp_es_fatt) AND riga_nr = 2),
  'S/true',
  '3) cliente scisso: la riga nasce con esigibilita S e split true'
);

-- ============================================================
-- 4) ⭐ D-7: la DIFFERITA non si sceglie piu' a mano
-- ============================================================
-- ⛔ Rev 2026-10-01. Fino al 2026-09-30 qui si pretendeva che una 'D' scritta
--   a mano sopravvivesse. Con l'IVA per cassa la 'D' la deduce il regime
--   dell'emittente, e una colonna che ospita insieme valori dedotti e scelti
--   non sa dire quale dei due ha davanti: l'esigibilita' e' una derivazione
--   pura (D-7). Su un emittente ordinario la 'D' a mano diventa 'I'. Una
--   differita scelta, se mai servira', avra' una colonna sua.
UPDATE anagrafiche.soggetti SET split_payment = 'N'
 WHERE id = (SELECT soggetto_id FROM tmp_es_sogg);

INSERT INTO vendite.fatture_righe
    (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id, esigibilita, meta, competenza_dal, competenza_al)
SELECT (SELECT id FROM tmp_es_fatt), 3, 'Riga differita', 1, 100, r.iva_id, 'D',
       jsonb_build_object('test_scope', 'pgtap_esigibilita'), script.fn_data_operativa(), script.fn_data_operativa()
  FROM tmp_es_refs r;

SELECT is(
  (SELECT esigibilita::text FROM vendite.fatture_righe
    WHERE fattura_id = (SELECT id FROM tmp_es_fatt) AND riga_nr = 3),
  'I',
  '4) D-7: su un emittente ordinario una D esplicita NON sopravvive, la riga dice I'
);

-- ============================================================
-- 5) ⛔ Ma con la scissione la 'D' NON sopravvive
-- ============================================================
-- ⚠️ Con la scissione dei pagamenti la 'S' e' imposta dalla legge, e un
--   documento che dicesse 'D' sarebbe sbagliato.
UPDATE anagrafiche.soggetti SET split_payment = 'S'
 WHERE id = (SELECT soggetto_id FROM tmp_es_sogg);

INSERT INTO vendite.fatture_righe
    (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id, esigibilita, meta, competenza_dal, competenza_al)
SELECT (SELECT id FROM tmp_es_fatt), 4, 'Riga differita ma scissa', 1, 100, r.iva_id, 'D',
       jsonb_build_object('test_scope', 'pgtap_esigibilita'), script.fn_data_operativa(), script.fn_data_operativa()
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
