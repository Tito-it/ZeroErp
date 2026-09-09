-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: il soggetto del test e' la separazione fra DUE emittenti,
--   e nessun operatore ne vede due: config.user_emittenti_fiscali ha
--   `uq_user_emittenti_fiscali_auth_user`, cioe' UNIQUE su auth_user_id — «un
--   operatore, un emittente; multiemittente e' solo il super admin». La
--   proprieta' sotto esame (due contatori distinti) e' quindi INOSSERVABILE da
--   dentro un perimetro, per costruzione e non per configurazione. E' una
--   proprieta' del MODELLO — l'emittente sta nella chiave — non del percorso
--   applicativo, che ha il suo presidio in
--   db/pgtap/anagrafiche/test-soggetti-titoli-iva.sql (23 asserzioni, runner app).
-- pgtap-contesto: escluso — discende dal marcatore qui sopra: un contesto
--   operatore restringerebbe la vista a UN emittente e la fixture non
--   potrebbe nemmeno costruire il caso.
-- pgTAP test per Zero ERP
-- Test: I7 / D10-bis — lo stesso soggetto verso DUE emittenti ha DUE plafond,
--       e il consumo dell'uno non intacca l'altro.
--       Piano: brief-db-be-iva-risolutore-e-regime-cliente.md
--       D10-bis · §6 «pgTAP su I7, ed e' quello che nessuno penserebbe di scrivere»
-- ------------------------------------------------------------
-- Elenco test (plan 5):
-- 0) riferimenti minimi presenti                     (la fixture non mente)
-- 1) ⭐ due titoli dello STESSO tipo e periodo, verso due emittenti: si registrano
--       ENTRAMBI — e' l'emittente in chiave che lo permette
-- 2) il consumo sul titolo del primo emittente si registra
-- 3) ⭐ il titolo del SECONDO emittente resta a zero: due contatori, non uno
-- 4) ⭐ e la sua capienza e' ancora INTERA: consumando il plafond pieno lo copre
--       tutto, invece di spezzarsi sul residuo dell'altro
--
-- Scopo:
--   D10-bis e' la decisione meno ovvia di questo cantiere: il titolo APPARTIENE
--   al soggetto — e' lui l'esportatore abituale — ma si PRESENTA a un fornitore
--   preciso, con un protocollo suo e un importo suo. Lo stesso esportatore che
--   compra da due societa' emittenti presenta DUE dichiarazioni.
--
--   ⛔ Senza la colonna dell'emittente in chiave, i due plafond si
--   consumerebbero da UN SOLO contatore. Il difetto non darebbe nessun errore:
--   si vedrebbe soltanto su un plafond esaurito prima del dovuto, cioe' su
--   precisamente il numero che l'Agenzia delle Entrate verifica.
--
--   ⭐ IL TEST 1 E IL TEST 4 PROVANO DUE COSE DIVERSE, e servono tutti e due:
--     * il test 1 guarda il VINCOLO — se l'emittente uscisse dalla chiave di
--       `ex_soggetti_titoli_iva_no_overlap`, il secondo titolo verrebbe
--       rifiutato e il difetto si vedrebbe subito;
--     * il test 4 guarda l'ARITMETICA — se il consumo cercasse il residuo per
--       (soggetto, tipo) invece che per riga di titolo, i due titoli
--       esisterebbero ma condividerebbero la capienza, e il secondo si
--       spezzerebbe su un residuo che non e' il suo. E' il difetto silenzioso,
--       ed e' quello che il test 3 da solo non prenderebbe.
--
--   ⚠️ LA FIXTURE COSTRUISCE I DUE EMITTENTI, non li cerca: un test che
--   iterasse su quelli che ci sono passerebbe a vuoto su un database
--   ricostruito da zero, cioe' in CI — la forma classica del «verde per
--   sottrazione».
--
--   ⛔ E IL PRIMO TENTATIVO E' STATO SCRITTO COME RUNNER APP, con la fixture
--   che aggiungeva i due emittenti alla whitelist dell'operatore. Non regge, e
--   la ragione e' nel modello: `config.user_emittenti_fiscali` ha una UNIQUE su
--   `auth_user_id`. Un operatore ha UN emittente — e' la regola di dominio che
--   `script.fn_pgtap_set_contesto_operatore` cita per esteso. Percio' questo
--   file gira come owner, dichiarato in testa: la RLS delle tre tabelle e'
--   esercitata dall'altro file, quello con le 23 asserzioni.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 3. VINCOLI DIFFERITI: qui il COMMIT non arriva mai. ⭐ E stavolta la riga
--   esercita davvero qualcosa: `anagrafiche.soggetti_ruoli` porta due trigger
--   DEFERRABLE INITIALLY DEFERRED, e la fixture ne crea due.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- ============================================================
-- 0) Riferimenti e fixture
-- ============================================================
CREATE TEMP TABLE tmp_2ef_costanti AS
SELECT 'pgtap_titoli_iva_2ef'::text AS test_scope;

-- ⚠️ `codice_interno = 'EF'` e NON `codice = 'EMITT_FISC'`: il `codice` e'
--   modificabile dall'utente, e un confronto logico su quella colonna smette di
--   agganciarsi in silenzio al primo rename (linee-guida-sql §6c/§6d).
-- ⚠️ La natura del soggetto non e' libera: `trgfn_soggetti_ruoli_guard_natura_ammessa`
--   pretende che il tipo soggetto sia fra quelli ammessi per il ruolo, e senza
--   il join su config.tipi_ruoli_nature_ammesse la fixture morirebbe su un
--   errore di dominio che sembrerebbe un difetto del cantiere.
CREATE TEMP TABLE tmp_2ef_sogg AS
SELECT s.id, row_number() OVER (ORDER BY s.id) AS n
  FROM anagrafiche.soggetti s
  JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id
  JOIN config.tipi_ruoli_nature_ammesse na ON na.tipo_soggetto_id = tsd.tipo_soggetto_id
  JOIN config.tipi_ruoli tr ON tr.id = na.tipo_ruolo_id AND tr.codice_interno = 'EF'
 WHERE s.attivo IS TRUE
   AND NOT EXISTS (SELECT 1 FROM anagrafiche.soggetti_ruoli sr
                    WHERE sr.soggetto_id = s.id AND sr.tipo_ruolo_id = tr.id)
 ORDER BY s.id
 LIMIT 2;

CREATE TEMP TABLE tmp_2ef_emittenti AS
WITH ruoli AS (
  INSERT INTO anagrafiche.soggetti_ruoli (soggetto_id, tipo_ruolo_id)
  SELECT g.id, (SELECT id FROM config.tipi_ruoli WHERE codice_interno = 'EF')
    FROM tmp_2ef_sogg g
  RETURNING id AS soggetto_ruolo_id, soggetto_id
), ins AS (
  INSERT INTO anagrafiche.emittenti_fiscali (soggetto_ruolo_id, codice, brand_meta)
  SELECT r.soggetto_ruolo_id,
         'PGTAP2EF' || g.n,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_2ef_costanti))
    FROM ruoli r JOIN tmp_2ef_sogg g ON g.id = r.soggetto_id
  RETURNING id, codice
)
SELECT id, codice, right(codice, 1)::int AS n FROM ins;

CREATE TEMP TABLE tmp_2ef_refs AS
SELECT
    (SELECT s.id FROM anagrafiche.soggetti s
      WHERE s.attivo IS TRUE ORDER BY s.id LIMIT 1)     AS soggetto_id,
    (SELECT i.id FROM config.iva i
      WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)     AS iva_id,
    (SELECT t.id FROM config.tipi_titolo_iva t
      WHERE t.codice_interno = 'INTENTO')               AS tipo_intento_id,
    (SELECT e.id FROM tmp_2ef_emittenti e WHERE e.n = 1) AS emittente_1_id,
    (SELECT e.id FROM tmp_2ef_emittenti e WHERE e.n = 2) AS emittente_2_id;

SELECT ok(
    (SELECT soggetto_id IS NOT NULL
        AND iva_id           IS NOT NULL
        AND tipo_intento_id  IS NOT NULL
        AND emittente_1_id   IS NOT NULL
        AND emittente_2_id   IS NOT NULL
        AND emittente_1_id  <> emittente_2_id
       FROM tmp_2ef_refs),
    'Due emittenti fiscali COSTRUITI dalla fixture, e distinti'
  );

-- Fattura di appoggio: un movimento di tipo FATTURA ne nomina una per forza
-- (CHECK chk_stiva_movimenti_documento). Ne basta UNA: il consumo si registra
-- sul TITOLO, e l'emittente della fattura non entra nella regola sotto esame.
CREATE TEMP TABLE tmp_2ef_ba AS
WITH cfg AS (
  SELECT efu.emittente_soggetto_ruolo_id, efu.utility_id
    FROM anagrafiche.emittenti_fiscali_utilities efu
   WHERE efu.attivo IS TRUE
     AND EXISTS (SELECT 1 FROM anagrafiche.billing_account ba WHERE ba.utility_id = efu.utility_id)
   ORDER BY efu.emittente_soggetto_ruolo_id, efu.utility_id
   LIMIT 1
)
SELECT (SELECT emittente_soggetto_ruolo_id FROM cfg) AS emittente_soggetto_ruolo_id,
       (SELECT utility_id FROM cfg)                  AS utility_id,
       (SELECT ba.id FROM anagrafiche.billing_account ba
         WHERE ba.utility_id = (SELECT utility_id FROM cfg)
         ORDER BY ba.data_insert DESC NULLS LAST, ba.id DESC LIMIT 1) AS billing_account_id,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DRAFT' ORDER BY id LIMIT 1) AS stato_draft_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id;

CREATE TEMP TABLE tmp_2ef_fattura AS
WITH reg AS (
  -- ⛔ emittente_soggetto_ruolo_id e' NOT NULL dal 2026-08-30 (C1-2,
  --   20260830-11), e dev'essere lo STESSO delle fatture di questo file:
  --   vendite.trgfn_fatture_guard_registro_emittente rifiuta un documento
  --   sul registro di un altro emittente (C1-3, 20260830-10).
  INSERT INTO vendite.registri_fatturazione (codice, descrizione, reset_policy, attivo,
         emittente_soggetto_ruolo_id, meta)
  SELECT 'REG2EF_PGTAP', 'Registro test due emittenti', 'ANNUALE', true,
         (SELECT emittente_soggetto_ruolo_id FROM tmp_2ef_ba),
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_2ef_costanti))
  RETURNING id
), ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, stato_doc_fiscale_id, valuta_id, utility_id, meta)
  SELECT (SELECT id FROM reg), DATE '2026-06-15',
         b.emittente_soggetto_ruolo_id, b.billing_account_id,
         b.tipo_doc_fiscale_id, b.stato_draft_id, b.valuta_id, b.utility_id,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_2ef_costanti))
    FROM tmp_2ef_ba b
  RETURNING id
)
SELECT id FROM ins;

-- ============================================================
-- 1) ⭐ I due titoli convivono: e' l'emittente in chiave
-- ============================================================
-- Stesso soggetto, stesso tipo, STESSO periodo: se l'emittente uscisse dalla
-- chiave di ex_soggetti_titoli_iva_no_overlap, il secondo INSERT verrebbe
-- rifiutato con un 23P01 e il difetto si vedrebbe qui.
CREATE TEMP TABLE tmp_2ef_titoli AS
WITH ins AS (
  INSERT INTO anagrafiche.soggetti_titoli_iva
      (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
       ambito, valido_dal, valido_al, protocollo, plafond)
  SELECT r.soggetto_id, e.id, r.tipo_intento_id, r.iva_id,
         'TUTTO', DATE '2026-01-01', DATE '2026-12-31',
         'PGTAP-2EF-PROT-' || e.n, 1000.00
    FROM tmp_2ef_refs r, tmp_2ef_emittenti e
  RETURNING id, emittente_fiscale_id
)
SELECT i.id, i.emittente_fiscale_id, e.n
  FROM ins i JOIN tmp_2ef_emittenti e ON e.id = i.emittente_fiscale_id;

SELECT is(
    (SELECT count(*)::int FROM tmp_2ef_titoli),
    2,
    'Stesso soggetto, stesso tipo, stesso periodo, DUE emittenti: si registrano entrambi'
  );

-- ============================================================
-- 2-3) Il consumo dell'uno, e il silenzio dell'altro
-- ============================================================
SELECT is(
    (SELECT c.quota_coperta
       FROM anagrafiche.fn_consuma_plafond_titolo_iva(
                (SELECT id FROM tmp_2ef_titoli WHERE n = 1),
                (SELECT id FROM tmp_2ef_fattura),
                400.00, DATE '2026-06-15') c),
    400.00::numeric,
    'Il titolo del primo emittente consuma 400 della sua capienza'
  );

-- ⭐ Il cuore del test. Se i due plafond condividessero un contatore, qui
--   comparirebbe 400 — e nessun errore lo direbbe.
SELECT is(
    (SELECT t.imponibile_utilizzato
       FROM anagrafiche.soggetti_titoli_iva t
      WHERE t.id = (SELECT id FROM tmp_2ef_titoli WHERE n = 2)),
    0::numeric,
    'Il titolo del SECONDO emittente resta a zero: due contatori distinti, non uno'
  );

-- ============================================================
-- 4) ⭐ E la capienza del secondo e' ancora INTERA
-- ============================================================
-- ⚠️ Non e' un doppione del test 3, ed e' il difetto che il 3 da solo non
--   prenderebbe: una colonna a zero e una capienza calcolata sul residuo
--   SBAGLIATO possono convivere. Qui si chiede il plafond PIENO: se il consumo
--   cercasse il residuo per (soggetto, tipo) invece che per riga di titolo, la
--   quota coperta sarebbe 600 e 400 tornerebbero all'aliquota ordinaria — su una
--   fattura, in silenzio.
SELECT is(
    (SELECT (c.quota_coperta, c.quota_ordinaria)::text
       FROM anagrafiche.fn_consuma_plafond_titolo_iva(
                (SELECT id FROM tmp_2ef_titoli WHERE n = 2),
                (SELECT id FROM tmp_2ef_fattura),
                1000.00, DATE '2026-06-15') c),
    '(1000.00,0.00)',
    'Il secondo emittente ha capienza INTERA: copre 1000, non 600'
  );

SELECT * FROM finish();
ROLLBACK;
