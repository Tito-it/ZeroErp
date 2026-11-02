-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: guard PSP su pagamenti.enti_incasso
-- ------------------------------------------------------------
-- Indice test
-- 1) Presenza trigger function trgfn_enti_incasso_guard_psp
-- 2) Presenza ruolo PSP in config.tipi_ruoli
-- 3) Presenza centro_riscossione attivo
-- 4) Esiste soggetto candidabile per PSP di test
-- 5) Inserimento anagrafiche.psp di test
-- 6) Inserimento enti_incasso tipo PSP valido
-- 7) Blocco tipo PSP senza soggetto_ruolo_id
-- 8) Esiste soggetto_ruolo non-PSP candidabile
-- 9) Blocco tipo PSP con soggetto_ruolo_id non-PSP
-- 10) Esiste un soggetto di natura ammessa per PSP e senza riga anagrafiche.psp
-- 11) Blocco tipo PSP con ruolo PSP non censito in anagrafiche.psp
-- 12) Cleanup completato
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

SELECT plan(12);

-- ============================================================
-- 0) Costanti e cleanup idempotente
-- ============================================================
CREATE TEMP TABLE tmp_costanti_eip AS
SELECT
  'pgtap_enti_incasso_psp'::text AS test_scope,
  ('EIP_PSP_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'))::text AS codice_psp,
  ('EIP_ENTE_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'))::text AS codice_ente;

DELETE FROM pagamenti.enti_incasso
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_eip);

DELETE FROM anagrafiche.psp
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_eip);

-- ============================================================
-- 1) Presenza trigger function
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'pagamenti'
      AND p.proname = 'trgfn_enti_incasso_guard_psp'
  ),
  'Presenza trigger function trgfn_enti_incasso_guard_psp'
);

-- ============================================================
-- 2) Presenza ruolo PSP
-- ============================================================
CREATE TEMP TABLE tmp_ruolo_psp AS
SELECT id
FROM config.tipi_ruoli
WHERE codice_interno = 'PSP';

SELECT is(
  (SELECT count(*)::int FROM tmp_ruolo_psp),
  1,
  'Presenza ruolo PSP in config.tipi_ruoli'
);

-- ============================================================
-- 3) Centro riscossione attivo
-- ============================================================
CREATE TEMP TABLE tmp_centro AS
WITH existing AS (
  SELECT c.id
  FROM pagamenti.centri_riscossione c
  WHERE c.attivo IS TRUE
  ORDER BY c.id
  LIMIT 1
), ins AS (
  INSERT INTO pagamenti.centri_riscossione (
    codice,
    codice_interno,
    descrizione,
    is_compensazione,
    is_fondo_fattura,
    attivo,
    meta
  )
  SELECT
    'EIP_CENTRO_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    'EIP_TEST',
    'Centro riscossione test pgTAP enti_incasso PSP',
    false,
    false,
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_eip))
  WHERE NOT EXISTS (SELECT 1 FROM existing)
  RETURNING id
)
SELECT id FROM existing
UNION ALL
SELECT id FROM ins;

SELECT is(
  (SELECT count(*)::int FROM tmp_centro),
  1,
  'Presenza centro_riscossione attivo'
);

-- ============================================================
-- 4) Soggetto candidabile (senza PSP anagrafico)
-- ============================================================
-- 🔴 NATURA AMMESSA, aggiunto il 2026-08-18.
--   `anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa` esige che la natura
--   del soggetto sia fra quelle che `config.tipi_ruoli_nature_ammesse` prevede
--   per il ruolo: per PSP e' la sola `PG`. Le due fixture di questo file
--   sceglievano invece «il primo soggetto senza riga PSP», e non e' la stessa
--   cosa — la selezione non conteneva la condizione che rende il caso
--   significativo.
--   ⚠️ Il test 4 passava **per fortuna** (il primo soggetto per id e' una PG);
--   la selezione del test 10, che chiede il primo soggetto DIVERSO da quello,
--   pescava una persona fisica e il guard uccideva il file — 2 asserzioni su 11
--   rosse, e le altre eseguite solo perche' il rosso arrivava in fondo.
--   La condizione si legge dalla MATRICE, non si scrive 'PG' a mano: se un
--   domani PSP ammettera' anche altro, la fixture segue senza essere toccata.
CREATE TEMP TABLE tmp_nature_psp AS
SELECT m.tipo_soggetto_id
FROM config.tipi_ruoli_nature_ammesse m
JOIN config.tipi_ruoli tr
  ON tr.id = m.tipo_ruolo_id
 AND tr.codice_interno = 'PSP'
WHERE m.attivo IS TRUE
  AND (m.valido_dal IS NULL OR m.valido_dal <= script.fn_data_operativa())
  AND (m.valido_al  IS NULL OR m.valido_al  >= script.fn_data_operativa());

CREATE TEMP TABLE tmp_soggetto_ok AS
SELECT s.id AS soggetto_id
FROM anagrafiche.soggetti s
JOIN config.tipi_soggetto_dettaglio tsd
  ON tsd.id = s.tipo_soggetto_dettaglio_id
WHERE tsd.tipo_soggetto_id IN (SELECT tipo_soggetto_id FROM tmp_nature_psp)
  AND NOT EXISTS (
  SELECT 1
  FROM anagrafiche.soggetti_ruoli sr
  JOIN config.tipi_ruoli tr
    ON tr.id = sr.tipo_ruolo_id
   AND tr.codice_interno = 'PSP'
  JOIN anagrafiche.psp p
    ON p.soggetto_ruolo_id = sr.id
  WHERE sr.soggetto_id = s.id
)
ORDER BY s.id
LIMIT 1;

SELECT is(
  (SELECT count(*)::int FROM tmp_soggetto_ok),
  1,
  'Esiste soggetto candidabile per PSP di test'
);

CREATE TEMP TABLE tmp_ruolo_psp_ok AS
SELECT script.fn_get_or_create_soggetto_ruolo(
         p_soggetto_id := (SELECT soggetto_id FROM tmp_soggetto_ok),
         p_cd_int_ruolo := 'PSP'
       ) AS soggetto_ruolo_id;

-- ============================================================
-- 5) Inserimento PSP anagrafico
-- ============================================================
CREATE TEMP TABLE tmp_psp_ok AS
WITH ins AS (
  INSERT INTO anagrafiche.psp (
    soggetto_ruolo_id,
    codice,
    descrizione,
    meta
  )
  SELECT
    (SELECT soggetto_ruolo_id FROM tmp_ruolo_psp_ok),
    (SELECT codice_psp FROM tmp_costanti_eip),
    'PSP test pgTAP',
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_eip))
  RETURNING id
)
SELECT * FROM ins;

SELECT is(
  (SELECT count(*)::int FROM tmp_psp_ok),
  1,
  'Inserimento anagrafiche.psp di test'
);

-- ============================================================
-- ⭐ Fixture aggiunta il 2026-08-22 (lotto 6, S3-1)
-- ============================================================
-- Da quel giorno OGNI canale di incasso deve dichiarare su quale conto
-- dell'azienda atterra il suo denaro: e' il perimetro dei soldi non ancora
-- attribuiti (D5), e vale su tutti i `tipo`, PSP compreso — il saldo di un PSP
-- arriva comunque su un conto di accredito dell'emittente.
-- ⚠️ Il conto dev'essere di uso INCASSO: un guard lo impone, perche' l'unicita'
--    che regge il perimetro vive solo sulle righe INCASSO.
-- ⛔ LA FILIALE SI COSTRUISCE (2026-09-23): `anagrafiche.bank_branches` e'
--   dato di MACCHINA, e su un database ricostruito e' vuota — `bank_branch_id`
--   usciva NULL e il conto moriva sul suo NOT NULL.
-- ⚠️ E il titolare del conto e' l'emittente di CHI AGISCE, non «il primo
--   emittente attivo»: sono la stessa riga finche' l'installazione ha
--   un'azienda sola, e su un database ricostruito lo sono per caso.
CREATE TEMP TABLE tmp_banca_eip AS
SELECT * FROM dbops.fn_pgtap_crea_filiale_bancaria('enti incasso psp');

CREATE TEMP TABLE tmp_conto_eip AS
WITH conto AS (
  INSERT INTO anagrafiche.conti_bancari (iban, bank_branch_id, attivo, storicizza, meta)
  SELECT 'IT00PGTAPENTIPSPCONTO0000001',
         (SELECT bank_branch_id FROM tmp_banca_eip),
         true, false,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_eip))
  RETURNING id
), legame AS (
  INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
      (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, storicizza, meta)
  SELECT script.fn_pgtap_emittente_sr_operatore(),
         conto.id, 'INCASSO', false, false,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_eip))
    FROM conto
  RETURNING id
)
SELECT id AS legame_id FROM legame;

-- ============================================================
-- 6) Inserimento enti_incasso tipo PSP valido
-- ============================================================
CREATE TEMP TABLE tmp_ente_ok AS
WITH ins AS (
  INSERT INTO pagamenti.enti_incasso (
    codice,
    codice_interno,
    descrizione,
    tipo,
    attivo,
    centro_riscossione_id,
    soggetto_ruolo_id,
    bank_branch_id,
    soggetto_ruolo_conto_bancario_id,
    formato_flusso,
    regole_match,
    meta
  )
  SELECT
    (SELECT codice_ente FROM tmp_costanti_eip),
    'EIP_PSP',
    'Ente incasso PSP test pgTAP',
    'PSP',
    true,
    (SELECT id FROM tmp_centro),
    (SELECT soggetto_ruolo_id FROM tmp_ruolo_psp_ok),
    NULL,
    (SELECT legame_id FROM tmp_conto_eip),
    'JSON',
    '{}'::jsonb,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_eip))
  RETURNING id
)
SELECT * FROM ins;

SELECT is(
  (SELECT count(*)::int FROM tmp_ente_ok),
  1,
  'Inserimento enti_incasso tipo PSP valido'
);

-- ============================================================
-- 7) Blocco PSP senza soggetto_ruolo_id
-- ============================================================
SELECT throws_ok(
  $$
  INSERT INTO pagamenti.enti_incasso (
    codice,
    descrizione,
    tipo,
    attivo,
    centro_riscossione_id,
    soggetto_ruolo_id,
    bank_branch_id,
    soggetto_ruolo_conto_bancario_id,
    regole_match,
    meta
  )
  VALUES (
    'EIP_NULL_ROLE_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    'Ente PSP senza ruolo',
    'PSP',
    true,
    (SELECT id FROM tmp_centro),
    NULL,
    NULL,
    (SELECT legame_id FROM tmp_conto_eip),
    '{}'::jsonb,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_eip))
  );
  $$,
  'P0001',
  NULL,
  'Blocco tipo PSP senza soggetto_ruolo_id'
);

-- ============================================================
-- 8) Ruolo non-PSP candidabile
-- ============================================================
CREATE TEMP TABLE tmp_ruolo_non_psp AS
SELECT sr.id AS soggetto_ruolo_id
FROM anagrafiche.soggetti_ruoli sr
JOIN config.tipi_ruoli tr
  ON tr.id = sr.tipo_ruolo_id
WHERE tr.codice_interno <> 'PSP'
ORDER BY sr.id
LIMIT 1;

SELECT is(
  (SELECT count(*)::int FROM tmp_ruolo_non_psp),
  1,
  'Esiste soggetto_ruolo non-PSP candidabile'
);

-- ============================================================
-- 9) Blocco PSP con ruolo non-PSP
-- ============================================================
SELECT throws_ok(
  $$
  INSERT INTO pagamenti.enti_incasso (
    codice,
    descrizione,
    tipo,
    attivo,
    centro_riscossione_id,
    soggetto_ruolo_id,
    bank_branch_id,
    soggetto_ruolo_conto_bancario_id,
    regole_match,
    meta
  )
  VALUES (
    'EIP_WRONG_ROLE_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    'Ente PSP con ruolo non-PSP',
    'PSP',
    true,
    (SELECT id FROM tmp_centro),
    (SELECT soggetto_ruolo_id FROM tmp_ruolo_non_psp),
    NULL,
    (SELECT legame_id FROM tmp_conto_eip),
    '{}'::jsonb,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_eip))
  );
  $$,
  'P0001',
  NULL,
  'Blocco tipo PSP con soggetto_ruolo_id non-PSP'
);

-- ============================================================
-- 10) Blocco PSP con ruolo PSP non censito in anagrafiche.psp
-- ============================================================
-- 🔴 Stessa correzione del test 4: il soggetto dev'essere di una natura che
--   PSP ammette, altrimenti la `fn_get_or_create_soggetto_ruolo` qui sotto
--   sbatte nel guard e il file muore prima di arrivare all'asserzione.
--   E' questo il punto in cui il rosso scattava.
CREATE TEMP TABLE tmp_soggetto_no_psp_row AS
SELECT s.id AS soggetto_id
FROM anagrafiche.soggetti s
JOIN config.tipi_soggetto_dettaglio tsd
  ON tsd.id = s.tipo_soggetto_dettaglio_id
WHERE s.id <> (SELECT soggetto_id FROM tmp_soggetto_ok)
  AND tsd.tipo_soggetto_id IN (SELECT tipo_soggetto_id FROM tmp_nature_psp)
  AND NOT EXISTS (
    SELECT 1
    FROM anagrafiche.soggetti_ruoli sr
    JOIN config.tipi_ruoli tr
      ON tr.id = sr.tipo_ruolo_id
     AND tr.codice_interno = 'PSP'
    JOIN anagrafiche.psp p
      ON p.soggetto_ruolo_id = sr.id
    WHERE sr.soggetto_id = s.id
  )
ORDER BY s.id
LIMIT 1;

-- ⚠️ La fixture non verificava di aver trovato qualcosa. Se la selezione fosse
--   tornata vuota, la `fn_get_or_create_soggetto_ruolo` qui sotto riceverebbe
--   `NULL` e alzerebbe un errore SUO, che il `throws_ok` del test 10 —
--   aspettandosi un generico `P0001` — accetterebbe come se il guard avesse
--   fatto il suo lavoro: verde per la ragione sbagliata.
SELECT is(
  (SELECT count(*)::int FROM tmp_soggetto_no_psp_row),
  1,
  'Esiste un soggetto di natura ammessa per PSP e senza riga anagrafiche.psp'
);

CREATE TEMP TABLE tmp_ruolo_psp_senza_riga AS
SELECT script.fn_get_or_create_soggetto_ruolo(
         p_soggetto_id := (SELECT soggetto_id FROM tmp_soggetto_no_psp_row),
         p_cd_int_ruolo := 'PSP'
       ) AS soggetto_ruolo_id;

SELECT throws_ok(
  $$
  INSERT INTO pagamenti.enti_incasso (
    codice,
    descrizione,
    tipo,
    attivo,
    centro_riscossione_id,
    soggetto_ruolo_id,
    bank_branch_id,
    soggetto_ruolo_conto_bancario_id,
    regole_match,
    meta
  )
  VALUES (
    'EIP_NO_PSP_ROW_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    'Ente PSP senza anagrafica PSP',
    'PSP',
    true,
    (SELECT id FROM tmp_centro),
    (SELECT soggetto_ruolo_id FROM tmp_ruolo_psp_senza_riga),
    NULL,
    (SELECT legame_id FROM tmp_conto_eip),
    '{}'::jsonb,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_eip))
  );
  $$,
  'P0001',
  NULL,
  'Blocco tipo PSP con ruolo PSP non censito in anagrafiche.psp'
);

-- ============================================================
-- 11) Cleanup
-- ============================================================
DELETE FROM pagamenti.enti_incasso
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_eip);

DELETE FROM anagrafiche.psp
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_eip);

DELETE FROM pagamenti.centri_riscossione
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_eip);

SELECT is(
  (
    SELECT count(*)::int
    FROM pagamenti.enti_incasso
    WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_eip)
  ),
  0,
  'Cleanup completato'
);

SELECT * FROM finish();

ROLLBACK;
