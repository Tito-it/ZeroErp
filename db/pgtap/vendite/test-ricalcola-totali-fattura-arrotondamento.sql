-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: ricalcolo totali fattura con arrotondamenti/minimo
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Config emittente/utility pronta (upsert: il test possiede i parametri
--    di arrotondamento, non li eredita)
-- 3) Inserimento fattura e riepilogo IVA
-- 4) Ricalcolo totali con arrotondamento (decimali=0)
-- 5) Aggiornamento minimo su soglia
-- 6) Ricalcolo con arrotondamento a 2 decimali
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- ============================================================
-- 0) Riferimenti e costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_rt AS
SELECT 'pgtap_ricalcola_totali_arrotondamento'::text AS test_scope;

-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba, BA dell'azienda di chi agisce) e
--   l'emittente e' quello dell'operatore di contesto. Prima il BA era l'ultimo
--   inserito e l'emittente si pescava da emittenti_fiscali_billing_account (o
--   il default): da zero non c'era niente. Configurazione e fattura restano
--   scritte a mano: sono il caso del test.
CREATE TEMP TABLE tmp_cli_rt AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('ricalcola totali arrotondamento');

CREATE TEMP TABLE tmp_refs_rt AS
SELECT
  NULL::bigint AS registro_id,
  c.billing_account_id,
  c.utility_id,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id,
  script.fn_pgtap_emittente_sr_operatore() AS emittente_soggetto_ruolo_id
FROM tmp_cli_rt c;

-- ⛔ IL REGISTRO SI ALLINEA ALL'EMITTENTE, e prima non lo faceva.
--   La riga sopra sceglieva «un registro qualunque» accanto a un emittente che
--   viene da un'altra parte: che i due coincidessero era un CASO, e dal
--   2026-08-30 vendite.trgfn_fatture_guard_registro_emittente non lo ammette
--   piu'. L'helper risponde con il registro di QUESTO emittente, creandolo se
--   non ce n'e' uno — la riga vive nella transazione del test.
UPDATE tmp_refs_rt SET registro_id = script.fn_pgtap_registro_fattura(emittente_soggetto_ruolo_id);
SELECT ok(
  (SELECT registro_id IS NOT NULL
     AND billing_account_id IS NOT NULL
     AND utility_id IS NOT NULL
     AND tipo_doc_fiscale_id IS NOT NULL
     AND valuta_id IS NOT NULL
     AND emittente_soggetto_ruolo_id IS NOT NULL
   FROM tmp_refs_rt),
  'Riferimenti minimi presenti'
);

-- ============================================================
-- 1) Config emittente/utility (decimali=0)
-- ============================================================
-- ⚠️ 2026-08-01: era una INSERT nuda e presupponeva che la coppia
--   (emittente, utility) NON fosse ancora configurata. Il presupposto e'
--   caduto quando il DB ha preso le configurazioni reali: la coppia (72, 5)
--   esiste, l'unique la respingeva e il file moriva al secondo statement —
--   quindi ZERO asserzioni eseguite, non «quattro su sei» (era la riga 106
--   della baseline, ERRORE_FIXTURE).
--   Ora e' un UPSERT, ed e' la forma giusta anche nel merito: questo test
--   ASSERISCE un arrotondamento preciso (decimali 0, poi 2) e soglie 9/12,
--   quindi deve possedere quei parametri invece di ereditare quelli che
--   trova. Con la INSERT nuda sarebbe passato solo finche' nessuno
--   configurava quell'emittente, e sarebbe diventato data-dependent il
--   giorno dopo.
CREATE TEMP TABLE tmp_conf_rt AS
WITH ins AS (
  INSERT INTO anagrafiche.emittenti_fiscali_utilities (
    emittente_soggetto_ruolo_id,
    utility_id,
    minimo_soglia_min,
    minimo_soglia_max,
    arrotondamento_importi_dec,
    metodo_arrotondamento_importi,
    attivo,
    meta
  )
  SELECT
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_rt),
    (SELECT utility_id FROM tmp_refs_rt),
    9.00,
    12.00,
    0,
    'HALF_UP',
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_rt))
  ON CONFLICT (emittente_soggetto_ruolo_id, utility_id) DO UPDATE
    SET minimo_soglia_min             = EXCLUDED.minimo_soglia_min,
        minimo_soglia_max             = EXCLUDED.minimo_soglia_max,
        arrotondamento_importi_dec    = EXCLUDED.arrotondamento_importi_dec,
        metodo_arrotondamento_importi = EXCLUDED.metodo_arrotondamento_importi,
        -- `attivo` va forzato: fn_ricalcola_totali_fattura filtra su
        -- `attivo IS TRUE` e una configurazione disattivata farebbe cadere il
        -- test su E_CONFIG_MANCANTE, cioe' su un guard diverso da quello in
        -- esame.
        attivo                        = true
    -- `meta` NON si tocca sul ramo di conflitto: la riga preesistente e' di
    -- qualcun altro e non va marcata come roba di test.
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_conf_rt),
  'Config emittente/utility pronta (upsert)'
);

-- ============================================================
-- 2) Fattura + riepilogo IVA
-- ============================================================
CREATE TEMP TABLE tmp_fattura_rt AS
WITH ins AS (
  INSERT INTO vendite.fatture (
    registro_id,
    data,
    emittente_soggetto_ruolo_id,
    billing_account_id,
    tipo_doc_fiscale_id,
    valuta_id,
    -- 3b.3: la fattura porta la propria utility. fn_ricalcola_totali_fattura
    -- la LEGGE da qui (prima la deduceva da lotto/BA) per scegliere la riga
    -- di emittenti_fiscali_utilities, cioe' decimali e metodo di
    -- arrotondamento: senza, il test cade su E_CONFIG_MANCANTE.
    utility_id,
    meta
  )
  SELECT
    (SELECT registro_id FROM tmp_refs_rt),
    script.fn_data_operativa(),
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_rt),
    (SELECT billing_account_id FROM tmp_refs_rt),
    (SELECT tipo_doc_fiscale_id FROM tmp_refs_rt),
    (SELECT valuta_id FROM tmp_refs_rt),
    (SELECT utility_id FROM tmp_refs_rt),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_rt))
  RETURNING id
)
SELECT * FROM ins;

INSERT INTO vendite.fatture_riepiloghi_iva (
  fattura_id,
  imponibile,
  imposta,
  arrotondamento
)
SELECT
  (SELECT id FROM tmp_fattura_rt),
  10.50,
  0.71,
  0;

-- ============================================================
-- 3) Ricalcolo con arrotondamento (decimali=0)
-- ============================================================
SELECT ok(
  (SELECT 1 FROM vendite.fn_ricalcola_totali_fattura((SELECT id FROM tmp_fattura_rt)) LIMIT 1) IS NOT NULL,
  'Ricalcolo totali con arrotondamento'
);

SELECT ok(
  (SELECT minimo
     FROM vendite.fatture
    WHERE id = (SELECT id FROM tmp_fattura_rt)) IS TRUE,
  'Minimo impostato in base a soglia'
);

-- ============================================================
-- 4) Ricalcolo con arrotondamento a 2 decimali
-- ============================================================
UPDATE anagrafiche.emittenti_fiscali_utilities
SET arrotondamento_importi_dec = 2
WHERE id = (SELECT id FROM tmp_conf_rt);

SELECT ok(
  (SELECT 1 FROM vendite.fn_ricalcola_totali_fattura((SELECT id FROM tmp_fattura_rt)) LIMIT 1) IS NOT NULL,
  'Ricalcolo totali con arrotondamento a 2 decimali'
);

-- ============================================================
-- Cleanup
-- ============================================================
UPDATE vendite.fatture
SET storicizza = false
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_rt);

DELETE FROM vendite.fatture_riepiloghi_iva
WHERE fattura_id = (SELECT id FROM tmp_fattura_rt);

DELETE FROM vendite.fatture
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_rt);

DELETE FROM anagrafiche.emittenti_fiscali_utilities
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_rt);

SELECT ok(true, 'Cleanup completato');

SELECT * FROM finish();

ROLLBACK;
