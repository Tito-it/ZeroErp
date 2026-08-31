-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la proprieta' sotto esame e' la SEPARAZIONE fra due
--   emittenti, e nessun operatore ne vede due: config.user_emittenti_fiscali ha
--   UNIQUE su auth_user_id — «un operatore, un emittente». La fixture deve
--   COSTRUIRE un secondo emittente e il suo registro, e da dentro un perimetro
--   non potrebbe nemmeno crearlo. E' lo stesso marcatore, con la stessa
--   ragione, di db/pgtap/anagrafiche/test-soggetti-titoli-iva-due-emittenti.sql.
--   ⚠️ La RLS di vendite.fatture NON e' il soggetto di questo file: il guard e'
--   un BEFORE trigger e scatta prima e a prescindere.
-- pgtap-contesto: escluso — discende dal marcatore qui sopra: un contesto
--   operatore restringerebbe la vista a UN emittente e la fixture non potrebbe
--   costruire il caso.
-- pgTAP test per Zero ERP
-- Test: C1-3 — una fattura sta sul registro del PROPRIO emittente
--       vendite.trgfn_fatture_guard_registro_emittente
--       Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, C1-3
-- ------------------------------------------------------------
-- Elenco test (plan 6):
-- 0) Fixture: due emittenti distinti, un registro per ciascuno
-- 1) ⭐ Fattura sul registro del PROPRIO emittente: PASSA
-- 2) ⛔ Fattura sul registro dell'ALTRO emittente: respinta, SQLSTATE P0001
-- 3) La frase nomina il CODICE del registro, non il suo id
-- 4) ⛔ E non si aggira con un UPDATE: spostare la fattura sul registro
--       dell'altro e' respinto allo stesso modo
-- 5) ⛔ Un registro SENZA emittente non si crea piu' (C1-2, 23502)
--
-- Scopo:
--   Fino al 2026-08-30 niente legava vendite.fatture.registro_id a
--   vendite.fatture.emittente_soggetto_ruolo_id. Il difetto che ne discendeva
--   e' MUTO: un registro condiviso fra due emittenti non produce numeri
--   duplicati — il contatore e' uno solo, quindi uq_fatture_numero non ha
--   niente da respingere — ma spezza l'ATTRIBUZIONE, e nessuna delle due
--   partite IVA ha piu' una propria numerazione progressiva.
--
--   ⭐ IL TEST 1 SERVE QUANTO IL TEST 2, e non e' una formalita': senza il
--   gemello positivo, un guard che respingesse OGNI fattura passerebbe il
--   test 2 esattamente come quello giusto. E' la differenza fra «respinge il
--   caso sbagliato» e «respinge tutto».
--
--   ⭐ IL TEST 5 GUARDA L'ALTRA META' DELLA COPPIA. Il guard e il NOT NULL si
--   reggono a vicenda: finche' un registro poteva non avere emittente, il
--   guard aveva un ramo che TACEVA (per non fermare la fatturazione prima
--   della bonifica). Con il NOT NULL quel ramo diventa irraggiungibile — e
--   questo test e' cio' che lo dimostra invece di darlo per fatto.
--
-- ⚠️ COSA QUESTO FILE **NON** PUO' PROVARE, ed e' scritto qui invece di essere
--   scoperto da chi verra' dopo:
--   * che il trigger sia montato `UPDATE OF` sulle due sole colonne. Provarlo
--     richiederebbe una fattura GIA' incoerente su cui fare un UPDATE di
--     tutt'altra colonna — e quella riga il guard impedisce di crearla. La
--     forma del trigger si presidia in review, sul changeSet 20260830-10;
--   * il ramo «registro senza emittente: si tace». Dopo il NOT NULL quella
--     riga non e' piu' costruibile, ed e' il test 5 a dirlo. Un test che lo
--     esercitasse dovrebbe prima togliere il vincolo, cioe' provare un
--     database diverso da quello che gira.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 2. VINCOLI DIFFERITI: qui il COMMIT non arriva mai, e la fixture crea un
--   soggetto_ruolo — che porta trigger DEFERRABLE INITIALLY DEFERRED.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- 0) Riferimenti e fixture
-- ============================================================
CREATE TEMP TABLE tmp_gre_costanti AS
SELECT 'pgtap_guard_registro_emittente'::text AS test_scope;

-- ⚠️ La terna (emittente, utility, billing account) si sceglie INSIEME, non a
--   tre pescate indipendenti: si parte DALLA configurazione
--   emittenti_fiscali_utilities e si scende al BA che le corrisponde.
CREATE TEMP TABLE tmp_gre_refs AS
SELECT efu.emittente_soggetto_ruolo_id,
       efu.utility_id,
       (SELECT ba.id
          FROM anagrafiche.billing_account ba
         WHERE ba.utility_id = efu.utility_id
         ORDER BY ba.id
         LIMIT 1) AS billing_account_id,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DRAFT' ORDER BY id LIMIT 1) AS stato_draft_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id
  FROM anagrafiche.emittenti_fiscali_utilities efu
  JOIN anagrafiche.emittenti_fiscali ef
    ON ef.soggetto_ruolo_id = efu.emittente_soggetto_ruolo_id
   AND ef.attivo IS TRUE
 WHERE efu.attivo IS TRUE
   AND EXISTS (SELECT 1 FROM anagrafiche.billing_account ba
                WHERE ba.utility_id = efu.utility_id)
 ORDER BY efu.emittente_soggetto_ruolo_id, efu.utility_id
 LIMIT 1;

-- ⚠️ IL SECONDO EMITTENTE SI COSTRUISCE, non si cerca: un test che iterasse su
--   quelli che ci sono passerebbe a vuoto su un database ricostruito da zero,
--   cioe' in CI — la forma classica del «verde per sottrazione».
-- ⚠️ `codice_interno = 'EF'` e NON il `codice`, che e' modificabile dall'utente.
-- ⚠️ La natura del soggetto non e' libera: trgfn_soggetti_ruoli_guard_natura_ammessa
--   pretende che il tipo soggetto sia fra quelli ammessi per il ruolo.
CREATE TEMP TABLE tmp_gre_altro_ef AS
WITH sogg AS (
  SELECT s.id
    FROM anagrafiche.soggetti s
    JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id
    JOIN config.tipi_ruoli_nature_ammesse na ON na.tipo_soggetto_id = tsd.tipo_soggetto_id
    JOIN config.tipi_ruoli tr ON tr.id = na.tipo_ruolo_id AND tr.codice_interno = 'EF'
   WHERE s.attivo IS TRUE
     AND NOT EXISTS (SELECT 1 FROM anagrafiche.soggetti_ruoli sr
                      WHERE sr.soggetto_id = s.id AND sr.tipo_ruolo_id = tr.id)
   ORDER BY s.id
   LIMIT 1
), ruolo AS (
  INSERT INTO anagrafiche.soggetti_ruoli (soggetto_id, tipo_ruolo_id)
  SELECT sogg.id, (SELECT id FROM config.tipi_ruoli WHERE codice_interno = 'EF')
    FROM sogg
  RETURNING id AS soggetto_ruolo_id
), ins AS (
  INSERT INTO anagrafiche.emittenti_fiscali (soggetto_ruolo_id, codice, brand_meta)
  SELECT r.soggetto_ruolo_id, 'PGTAPGRE',
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_gre_costanti))
    FROM ruolo r
  RETURNING soggetto_ruolo_id
)
SELECT soggetto_ruolo_id FROM ins;

-- Due registri: uno dell'emittente della fattura, uno dell'ALTRO.
CREATE TEMP TABLE tmp_gre_reg AS
WITH ins AS (
  INSERT INTO vendite.registri_fatturazione
      (codice, descrizione, reset_policy, attivo, emittente_soggetto_ruolo_id, meta)
  VALUES
      ('RGRE_MIO',   'Registro dell''emittente della fattura', 'ANNUALE', true,
       (SELECT emittente_soggetto_ruolo_id FROM tmp_gre_refs),
       jsonb_build_object('test_scope', 'pgtap_guard_registro_emittente')),
      ('RGRE_ALTRO', 'Registro di un ALTRO emittente',         'ANNUALE', true,
       (SELECT soggetto_ruolo_id FROM tmp_gre_altro_ef),
       jsonb_build_object('test_scope', 'pgtap_guard_registro_emittente'))
  RETURNING id, codice)
SELECT max(id) FILTER (WHERE codice = 'RGRE_MIO')   AS reg_mio,
       max(id) FILTER (WHERE codice = 'RGRE_ALTRO') AS reg_altro
  FROM ins;

SELECT ok(
  (SELECT emittente_soggetto_ruolo_id IS NOT NULL
      AND billing_account_id          IS NOT NULL
     FROM tmp_gre_refs)
  AND (SELECT soggetto_ruolo_id IS NOT NULL FROM tmp_gre_altro_ef)
  AND (SELECT reg_mio IS NOT NULL AND reg_altro IS NOT NULL FROM tmp_gre_reg)
  AND (SELECT emittente_soggetto_ruolo_id FROM tmp_gre_refs)
      <> (SELECT soggetto_ruolo_id FROM tmp_gre_altro_ef),
  '0) Fixture: due emittenti DISTINTI, un registro per ciascuno');

-- ============================================================
-- 1) ⭐ Il gemello POSITIVO: sul proprio registro la fattura passa
-- ============================================================
CREATE TEMP TABLE tmp_gre_fattura AS
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, stato_doc_fiscale_id, valuta_id, utility_id, meta)
  SELECT (SELECT reg_mio FROM tmp_gre_reg), DATE '2026-06-15',
         r.emittente_soggetto_ruolo_id, r.billing_account_id,
         r.tipo_doc_fiscale_id, r.stato_draft_id, r.valuta_id, r.utility_id,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_gre_costanti))
    FROM tmp_gre_refs r
  RETURNING id)
SELECT id FROM ins;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_gre_fattura),
  '1) Sul registro del PROPRIO emittente la fattura passa (gemello positivo)');

-- ============================================================
-- 2) ⛔ Sul registro dell'ALTRO emittente: respinta
-- ============================================================
-- ⚠️ throws_ok CON lo SQLSTATE: senza, accetterebbe qualunque errore —
--   compreso un errore di battitura della fixture.
PREPARE gre_insert_altro AS
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, stato_doc_fiscale_id, valuta_id, utility_id, meta)
  SELECT (SELECT reg_altro FROM tmp_gre_reg), DATE '2026-06-16',
         r.emittente_soggetto_ruolo_id, r.billing_account_id,
         r.tipo_doc_fiscale_id, r.stato_draft_id, r.valuta_id, r.utility_id,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_gre_costanti))
    FROM tmp_gre_refs r;

SELECT throws_ok(
  'EXECUTE gre_insert_altro',
  'P0001',
  NULL,
  '2) Sul registro di un ALTRO emittente la fattura e'' respinta (P0001)');

-- ============================================================
-- 3) La frase nomina il CODICE del registro
-- ============================================================
-- ⭐ Il codice e non l'id: chi legge l'errore deve poter riconoscere il
--   sezionale, e un id non lo dice a nessuno.
SELECT throws_like(
  'EXECUTE gre_insert_altro',
  '%RGRE_ALTRO%',
  '3) La frase nomina il CODICE del registro');

-- ============================================================
-- 4) ⛔ E non si aggira con un UPDATE
-- ============================================================
PREPARE gre_update_altro AS
  UPDATE vendite.fatture
     SET registro_id = (SELECT reg_altro FROM tmp_gre_reg)
   WHERE id = (SELECT id FROM tmp_gre_fattura);

SELECT throws_ok(
  'EXECUTE gre_update_altro',
  'P0001',
  NULL,
  '4) Spostare la fattura sul registro dell''altro emittente e'' respinto');

-- ============================================================
-- 5) ⛔ Un registro SENZA emittente non si crea piu' (C1-2)
-- ============================================================
-- ⭐ E' l'altra meta' della coppia: e' questo vincolo che rende irraggiungibile
--   il ramo in cui il guard tace.
PREPARE gre_registro_senza_ef AS
  INSERT INTO vendite.registri_fatturazione (codice, descrizione, reset_policy, attivo, meta)
  VALUES ('RGRE_NULLO', 'Registro senza emittente', 'ANNUALE', true,
          jsonb_build_object('test_scope', 'pgtap_guard_registro_emittente'));

SELECT throws_ok(
  'EXECUTE gre_registro_senza_ef',
  '23502',
  NULL,
  '5) Un registro senza emittente non si crea piu'' (NOT NULL)');

SELECT * FROM finish();
ROLLBACK;
