-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il canale di una distinta e il suo centro di riscossione dicono la
--       stessa cosa — pagamenti.trgfn_vendite_contabili_guard_ente_centro
--
-- Elenco test (plan 7):
--  1) fixture: un canale col centro BANCA, uno senza centro
--  2) una distinta col canale e il SUO centro nasce
--  3) 🔴 col canale e un ALTRO centro: E_CONTABILE_CENTRO_ENTE_INCOERENTE
--  4) 🔴 con un canale senza centro: E_ENTE_INCASSO_SENZA_CENTRO
--  5) 🔴 cambiare dopo il centro di una distinta col canale: E_CONTABILE_CENTRO_ENTE_INCOERENTE
--  6) senza canale il guard tace: qualunque centro
--  7) Cleanup
--
-- Scopo:
--  - il centro di riscossione di una distinta che arriva da un canale lo
--    decide il CANALE: due valori che possono divergere sono due verita', e
--    la distinta direbbe di essere arrivata da una parte quando il canale
--    dice un'altra (3, 5). Il guard scatta anche sull'UPDATE (5);
--  - un canale senza centro e' una configurazione incompleta, e non si usa
--    per una distinta (4): la colonna del canale e' nullable, quindi il caso
--    il modello lo ammette;
--  - la distinta senza canale — manuale, interna — non e' affare di questo
--    guard (6);
--  - ⚠️ il canale si crea come nell'applicazione, sul conto di incasso
--    dell'azienda (banca con ruolo BANK_B, filiale, conto, legame INCASSO),
--    come in rls/test-rls-pagamenti-perimetro.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore.
CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- ⚠️ 2. CONTESTO APPLICATIVO.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- Il codice del rifiuto (campo CONSTRAINT dell'eccezione)
-- ============================================================
CREATE FUNCTION pg_temp.codice_rifiuto(p_sql text)
RETURNS text
LANGUAGE plpgsql
AS $fn$
DECLARE
    v_codice text;
BEGIN
    BEGIN
        EXECUTE p_sql;
        RETURN 'NESSUN_RIFIUTO';
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME;
        RETURN COALESCE(NULLIF(v_codice, ''), 'SQLSTATE ' || SQLSTATE);
    END;
END;
$fn$;

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_contabile_guard_ente_centro'::text AS test_scope;

-- La banca e la sua filiale: il soggetto-ruolo di una filiale DEVE essere una
-- banca (trgfn_bank_guard_ruolo_bank_branches pretende BANK_B).
CREATE TEMP TABLE tmp_banca AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(
           dbops.fn_pgtap_crea_soggetto_pg('Banca pgTAP guard ente centro'),
           'BANK_B'::character varying) AS banca_sr_id;

CREATE TEMP TABLE tmp_filiale AS
WITH b AS (
    INSERT INTO anagrafiche.bank_branches
        (soggetto_ruolo_id, bank_code, branch_code, name)
    SELECT banca_sr_id, 'PGTAP', 'EC' || banca_sr_id, 'Filiale pgTAP guard ente centro'
      FROM tmp_banca
    RETURNING id
)
SELECT id AS bank_branch FROM b;

-- Il conto di incasso dell'azienda.
CREATE TEMP TABLE tmp_legame AS
WITH conto AS (
  INSERT INTO anagrafiche.conti_bancari (iban, bank_branch_id, attivo, storicizza, meta)
  SELECT 'IT00PGTAPGUARDENTECENTRO0001', f.bank_branch, true, false,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_filiale f
  RETURNING id
), legame AS (
  INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
      (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, storicizza, meta)
  SELECT m.soggetto_ruolo_id, c.id, 'INCASSO', false, false,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM conto c CROSS JOIN _mondo m
  RETURNING id
)
SELECT id AS legame_id FROM legame;

CREATE TEMP TABLE tmp_refs AS
SELECT (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA' ORDER BY c.id LIMIT 1)          AS centro_banca_id,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice_interno = 'COMPENSAZIONI' ORDER BY c.id LIMIT 1)  AS centro_altro_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'BOZZA' ORDER BY s.id LIMIT 1)                               AS d_bozza;

-- Due canali sullo stesso conto: CB col centro BANCA, CN senza centro.
CREATE TEMP TABLE tmp_enti AS
WITH ins AS (
  INSERT INTO pagamenti.enti_incasso
      (codice, descrizione, tipo, attivo, soggetto_ruolo_conto_bancario_id,
       centro_riscossione_id, meta)
  SELECT 'PGTAP_ENTE_CENTRO_' || v.et, 'canale pgtap guard ente centro', 'ALTRO', true,
         (SELECT legame_id FROM tmp_legame),
         CASE v.et WHEN 'CB' THEN r.centro_banca_id END,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti), 'et', v.et)
    FROM tmp_refs r
    CROSS JOIN (VALUES ('CB'), ('CN')) AS v(et)
  RETURNING id, meta ->> 'et' AS et
)
SELECT * FROM ins;

SELECT ok(
    (SELECT centro_banca_id IS NOT NULL AND centro_altro_id IS NOT NULL
            AND centro_banca_id <> centro_altro_id FROM tmp_refs)
    AND (SELECT count(*) = 2 FROM tmp_enti),
    '1) fixture: un canale col centro BANCA, uno senza centro, e due centri diversi');

-- ============================================================
-- 2-4. Alla nascita
-- ============================================================
CREATE FUNCTION pg_temp.sql_distinta(p_ente_id bigint, p_centro_id bigint)
RETURNS text
LANGUAGE sql
AS $fn$
    SELECT format(
        $q$INSERT INTO pagamenti.vendite_contabili
              (centro_riscossione_id, ente_incasso_id, data_contabile, data_registrazione,
               stato_id, origine, meta)
           VALUES (%s, %s, script.fn_data_operativa(), script.fn_data_operativa(), %s, 'MANUALE',
                   jsonb_build_object('test_scope', 'pgtap_contabile_guard_ente_centro'))$q$,
        p_centro_id, COALESCE(p_ente_id::text, 'NULL'), (SELECT d_bozza FROM tmp_refs));
$fn$;

SELECT is(
    pg_temp.codice_rifiuto(pg_temp.sql_distinta(
        (SELECT id FROM tmp_enti WHERE et = 'CB'), (SELECT centro_banca_id FROM tmp_refs))),
    'NESSUN_RIFIUTO',
    '2) una distinta col canale e il SUO centro nasce');

SELECT is(
    pg_temp.codice_rifiuto(pg_temp.sql_distinta(
        (SELECT id FROM tmp_enti WHERE et = 'CB'), (SELECT centro_altro_id FROM tmp_refs))),
    'E_CONTABILE_CENTRO_ENTE_INCOERENTE',
    '3) col canale e un ALTRO centro: rifiutata, il centro lo decide il canale');

SELECT is(
    pg_temp.codice_rifiuto(pg_temp.sql_distinta(
        (SELECT id FROM tmp_enti WHERE et = 'CN'), (SELECT centro_banca_id FROM tmp_refs))),
    'E_ENTE_INCASSO_SENZA_CENTRO',
    '4) con un canale senza centro: rifiutata, la configurazione del canale e'' incompleta');

-- ============================================================
-- 5. Dopo la nascita
-- ============================================================
SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili SET centro_riscossione_id = %s
            WHERE ente_incasso_id = %s
              AND meta ->> 'test_scope' = 'pgtap_contabile_guard_ente_centro'$q$,
        (SELECT centro_altro_id FROM tmp_refs), (SELECT id FROM tmp_enti WHERE et = 'CB'))),
    'E_CONTABILE_CENTRO_ENTE_INCOERENTE',
    '5) cambiare dopo il centro di una distinta col canale: rifiutato anche sull''UPDATE');

-- ============================================================
-- 6. Senza canale
-- ============================================================
SELECT is(
    pg_temp.codice_rifiuto(pg_temp.sql_distinta(NULL, (SELECT centro_altro_id FROM tmp_refs))),
    'NESSUN_RIFIUTO',
    '6) senza canale il guard tace: il centro della distinta lo sceglie chi la apre');

-- ============================================================
-- Cleanup
-- ============================================================
SELECT ok(true, '7) Cleanup: la transazione viene annullata, nessun residuo');

SELECT * FROM finish();
ROLLBACK;
