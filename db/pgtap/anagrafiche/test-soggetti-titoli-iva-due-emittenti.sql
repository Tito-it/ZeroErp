-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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

-- ⛔ 2026-09-23: «la fixture costruisce i due emittenti» era vero a meta'. Li
--   costruiva promuovendo a EF «i primi due soggetti attivi senza quel
--   ruolo», e il titolare del titolo era «il primo soggetto attivo»: su un
--   database ricostruito dai changelog, prima che il file giri, di soggetti ce
--   ne sono pochi o nessuno, e la fixture moriva un passo dopo (registro con
--   emittente NULL). Ora i due emittenti li costruisce il builder — soggetto
--   persona giuridica, ruolo EF, valuta — e il titolare e' un soggetto suo.
-- ⚠️ Due ISTRUZIONI, non un generate_series: un LATERAL che non dipende dalla
--   riga il planner lo esegue UNA volta, e i «due» emittenti erano lo stesso.
CREATE TEMP TABLE tmp_2ef_emittenti AS
SELECT e.emittente_fiscale_id AS id, e.emittente_codice AS codice, 1 AS n
  FROM dbops.fn_pgtap_crea_emittente() e;

INSERT INTO tmp_2ef_emittenti
SELECT e.emittente_fiscale_id, e.emittente_codice, 2
  FROM dbops.fn_pgtap_crea_emittente() e;

CREATE TEMP TABLE tmp_2ef_refs AS
SELECT
    dbops.fn_pgtap_crea_soggetto_pg('Esportatore abituale 2EF') AS soggetto_id,
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
-- ⛔ 2026-09-23: era scritta a mano su mattoni PESCATI (la prima coppia
--   emittente/utility configurata, il BA piu' recente), e il registro nasceva
--   con emittente NULL su un database ricostruito. La costruisce il builder.
CREATE TEMP TABLE tmp_2ef_fattura AS
SELECT f.fattura_id AS id FROM dbops.fn_pgtap_crea_fattura('titoli IVA 2EF') f;

-- ⚠️ Dal 2026-10-04 (20261004-05/-06, brief-db-bom-flag-quantita-e-kit-in-
--   fattura §13) la forma a una riga e' ritirata e la madre vuole righe vere
--   (l'imponibile passato deve essere quello della riga): due righe, 400 e 1000.
CREATE TEMP TABLE tmp_2ef_righe AS
WITH a AS (SELECT dbops.fn_pgtap_crea_articolo('PGTAP-2EF-ART') AS id),
     u AS (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1),
     ins AS (
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione, uom_id,
         qta, prezzo_unitario, iva_id, competenza_dal, competenza_al)
  SELECT (SELECT id FROM tmp_2ef_fattura), v.nr, (SELECT id FROM a), 'Riga ' || v.nr,
         (SELECT id FROM u), 1, v.imp, (SELECT iva_id FROM tmp_2ef_refs),
         script.fn_data_operativa(), script.fn_data_operativa()
    FROM (VALUES (1, 400.00), (2, 1000.00)) v(nr, imp)
  RETURNING id, riga_nr)
SELECT max(id) FILTER (WHERE riga_nr = 1) AS r400,
       max(id) FILTER (WHERE riga_nr = 2) AS r1000
  FROM ins;

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
       FROM anagrafiche.fn_consuma_plafond_titolo_iva_righe(
                (SELECT id FROM tmp_2ef_titoli WHERE n = 1),
                (SELECT id FROM tmp_2ef_fattura),
                ARRAY[(SELECT r400 FROM tmp_2ef_righe)], ARRAY[400.00], DATE '2026-06-15') c),
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
       FROM anagrafiche.fn_consuma_plafond_titolo_iva_righe(
                (SELECT id FROM tmp_2ef_titoli WHERE n = 2),
                (SELECT id FROM tmp_2ef_fattura),
                ARRAY[(SELECT r1000 FROM tmp_2ef_righe)], ARRAY[1000.00], DATE '2026-06-15') c),
    '(1000.00,0.00)',
    'Il secondo emittente ha capienza INTERA: copre 1000, non 600'
  );

SELECT * FROM finish();
ROLLBACK;
