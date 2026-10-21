-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: insert e vincoli FK su anagrafiche.istanze_dati_precontrattuali
--       usando utility_id = 2 (GAS), una istanza_utility COSTRUITA
--       e una classe_utenza del seed di catalogo.
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. Messa in testa e non in coda
--   apposta: in coda scatterebbero tutti insieme DOPO il cleanup, su righe
--   ormai cancellate, e fallirebbero per un motivo che non riguarda il test.
--   Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- ============================================================
-- 0) Costanti e precondizioni
-- ============================================================
CREATE TEMP TABLE tmp_costanti_idp AS
SELECT
    2::integer AS utility_id,
    'pgtap_istanze_dati_precontrattuali'::text AS test_scope;

-- 0.1: Esiste la utility GAS con id=2
CREATE TEMP TABLE tmp_utility_gas AS
SELECT id AS utility_id
FROM config.utilities
WHERE id = (SELECT utility_id FROM tmp_costanti_idp)
  AND codice_interno = 'GAS';

SELECT is(
    (SELECT count(*)::int FROM tmp_utility_gas),
    1,
    'Esiste esattamente 1 utility GAS con id = 2'
);

-- 0.2: Esiste almeno una classe_utenza
-- ⚠️ rev 2026-09-23 (brief-db-fixture-che-costruiscono-giro-2, lotto 2):
--   config.classi_utenze e' CATALOGO, ma il suo CSV nessuno lo caricava: da
--   zero la tabella era vuota e il file moriva qui. Il seed nasce con
--   20260923-52 (tipi_utenze) e 20260923-53 (classi_utenze).
CREATE TEMP TABLE tmp_classe_utenza AS
SELECT id AS classe_utenza_id
FROM config.classi_utenze
ORDER BY id
LIMIT 1;

SELECT is(
    (SELECT count(*)::int FROM tmp_classe_utenza),
    1,
    'Esiste almeno una classe_utenza'
);

-- 0.3: Una istanza_utility senza record per utility_id=2
-- ⚠️ rev 2026-09-23: l'istanza si PESCAVA («la prima senza dati GAS»): su
--   un database ricostruito non ce n'e' nessuna. Ora viene da un cliente
--   COSTRUITO con dbops.fn_pgtap_crea_cliente_ba. ⛔ Cio' che il builder
--   scrive si legge in un'istruzione SEPARATA.
-- ⚠️ rev 2026-10-08 (brief-db-istanza-nasce-col-ba, R-1): il cliente si
--   costruisce sul BA GAS. Fino a quel giorno nasceva su un'altra utility
--   «apposta», e i dati GAS si scrivevano su una coppia (istanza, GAS) senza
--   BA: e' il caso che fk_idp_billing_account_coppia ora rifiuta. L'istanza
--   nasce comunque senza dati precontrattuali GAS: il builder non li scrive.
CREATE TEMP TABLE tmp_cli_idp AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'dati precontrattuali',
    (SELECT utility_id FROM tmp_costanti_idp));

CREATE TEMP TABLE tmp_istanza_utility AS
SELECT c.istanza_utility_id
FROM tmp_cli_idp c
WHERE NOT EXISTS (
    SELECT 1 FROM anagrafiche.istanze_dati_precontrattuali idp
     WHERE idp.istanza_utility_id = c.istanza_utility_id
       AND idp.utility_id = (SELECT utility_id FROM tmp_costanti_idp));

SELECT is(
    (SELECT count(*)::int FROM tmp_istanza_utility),
    1,
    'Esiste almeno una istanza_utility disponibile per utility_id=2'
);

-- Cleanup righe di test precedenti
DELETE FROM anagrafiche.istanze_dati_precontrattuali
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_idp);

-- ============================================================
-- 1) Verifica vincoli FK (errori attesi)
-- ============================================================

-- 1.1: utility_id -> config.utilities: FK, letta dal CATALOGO
-- ⛔ Non per INSERT (rev 2026-10-08). Sotto RLS il WITH CHECK della policy
--   (il BA da script.fn_get_ba_id_da_coppia, 20261021-26) vede la coppia solo attraverso
--   il suo BA, e PostgreSQL lo valuta all'INSERT PRIMA della FK: una utility
--   inesistente non ha BA, quindi col runner app la riga esce 42501 e la FK
--   non si raggiunge mai (come owner darebbe 23503). Era il rosso
--   ASSERZIONE della baseline CI dal 2026-09-09. Pinnare il 42501 sarebbe
--   pinnare il sintomo: la regola e' la FK.
SELECT is(
    -- ⚠️ nome della tabella da pg_class/pg_namespace: regclass::text
    --   omette lo schema secondo il search_path di chi legge
    (SELECT string_agg(a.attname || '->' || rn.nspname || '.' || rc.relname, ',')
       FROM pg_constraint c
       JOIN pg_attribute a  ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
       JOIN pg_class rc     ON rc.oid = c.confrelid
       JOIN pg_namespace rn ON rn.oid = rc.relnamespace
      WHERE c.contype  = 'f'
        AND c.conrelid = 'anagrafiche.istanze_dati_precontrattuali'::regclass
        AND c.conname  = 'fk_idp_utilities'
        AND c.confrelid = 'config.utilities'::regclass),
    'utility_id->config.utilities',
    'FK fk_idp_utilities: utility_id verso config.utilities'
);

-- 1.2: classe_utenza_id inesistente → FK violation
SELECT throws_ok(
    $$
    INSERT INTO anagrafiche.istanze_dati_precontrattuali (
        istanza_utility_id,
        utility_id,
        classe_utenza_id,
        param_1_num,
        param_2_txt,
        meta
    )
    SELECT
        iu.istanza_utility_id,
        k.utility_id,
        -1,
        1.00,
        'TEST-FK-CLASSE',
        jsonb_build_object('test_scope', 'pgtap_istanze_dati_precontrattuali')
    FROM tmp_istanza_utility iu,
         tmp_costanti_idp k;
    $$,
    '23503',
    NULL,
    'FK violation su classe_utenza_id inesistente'
);

-- 1.3: istanza_utility_id -> anagrafiche.istanze_utilities: FK, dal CATALOGO
-- ⛔ Non per INSERT, per la stessa ragione dell'1.1: un'istanza inesistente
--   non ha BA, e il WITH CHECK della policy parla (42501) prima della FK.
SELECT is(
    -- ⚠️ nome della tabella da pg_class/pg_namespace: regclass::text
    --   omette lo schema secondo il search_path di chi legge
    (SELECT string_agg(a.attname || '->' || rn.nspname || '.' || rc.relname, ',')
       FROM pg_constraint c
       JOIN pg_attribute a  ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
       JOIN pg_class rc     ON rc.oid = c.confrelid
       JOIN pg_namespace rn ON rn.oid = rc.relnamespace
      WHERE c.contype  = 'f'
        AND c.conrelid = 'anagrafiche.istanze_dati_precontrattuali'::regclass
        AND c.conname  = 'fk_idp_istanze_utilities'
        AND c.confrelid = 'anagrafiche.istanze_utilities'::regclass),
    'istanza_utility_id->anagrafiche.istanze_utilities',
    'FK fk_idp_istanze_utilities: istanza_utility_id verso anagrafiche.istanze_utilities'
);

-- ============================================================
-- 2) Inserimento valido
-- ============================================================
CREATE TEMP TABLE tmp_idp_test AS
WITH ins AS (
    INSERT INTO anagrafiche.istanze_dati_precontrattuali (
        istanza_utility_id,
        utility_id,
        classe_utenza_id,
        param_1_num,
        param_2_txt,
        meta
    )
    SELECT
        iu.istanza_utility_id,
        k.utility_id,
        cu.classe_utenza_id,
        12.50,
        'TEST-PGTAP',
        jsonb_build_object('test_scope', k.test_scope)
    FROM tmp_istanza_utility iu,
         tmp_costanti_idp k,
         tmp_classe_utenza cu
    RETURNING id
)
SELECT id
FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_idp_test),
    1,
    'Inserita 1 riga valida in istanze_dati_precontrattuali'
);

SELECT ok(
    EXISTS (
        SELECT 1
        FROM anagrafiche.istanze_dati_precontrattuali idp
        JOIN tmp_idp_test t
          ON t.id = idp.id
        WHERE idp.utility_id = (SELECT utility_id FROM tmp_costanti_idp)
          AND idp.classe_utenza_id = (SELECT classe_utenza_id FROM tmp_classe_utenza)
    ),
    'La riga inserita ha FK valide verso utility e classe utenza'
);

-- Cleanup riga di test
/*
DELETE FROM anagrafiche.istanze_dati_precontrattuali
WHERE id IN (SELECT id FROM tmp_idp_test);
*/
-- Fine test
SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
