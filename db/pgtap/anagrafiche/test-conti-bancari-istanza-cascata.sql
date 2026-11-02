-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test cascata conti bancari con istanza_utility_id:
--   - Partial unique index (istanza NULL e valorizzato)
--   - fn_get_conto_bancario_predefinito con p_istanza_utility_id
--   - Cascata 7 livelli: ruolo+istanza -> ruolo generico -> soggetto -> GENERICO
--   - Vista flat espone istanza_utility_id
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

SELECT plan(10);

-- Indice test (10):
--  1) Esiste almeno un cliente con istanza_utility_id
--  2) Esiste almeno una bank_branch
--  3) Conto INCASSO a livello soggetto creato (fallback)
--  4) Conto INCASSO a livello ruolo generico (istanza NULL) creato
--  5) Conto INCASSO a livello ruolo per istanza specifica creato
--  6) fn_get_conto con istanza: restituisce conto ruolo+istanza (livello 1)
--  7) fn_get_conto senza istanza: restituisce conto ruolo generico (livello 2)
--  8) Partial unique: blocco duplicato predefinito per (ruolo, istanza, uso)
--  9) Vista flat: istanza_utility_id valorizzato per riga istanza
-- 10) fn_get_conto PAGAMENTO con istanza: NULL (nessun PAGAMENTO ne GENERICO)

-- =========================================================
-- Costanti
-- =========================================================
CREATE TEMP TABLE tmp_costanti_cb_ut AS
SELECT
    'IT11Z0000000000000000000011'::varchar AS iban_soggetto,
    'IT22Z0000000000000000000022'::varchar AS iban_ruolo_gen,
    'IT33Z0000000000000000000033'::varchar AS iban_ruolo_ist,
    'BGFNOIT2XXX'::varchar                AS bic_test;

-- =========================================================
-- Setup: cliente con istanza, bank_branch
--
-- rev 2026-09-23 (brief-db-fixture-che-costruiscono-giro-2, lotto 2).
--   Cliente e filiale si PESCAVANO («il primo cliente con istanza», «la
--   prima bank_branch»): su un database ricostruito (la CI) non c'e' ne'
--   l'uno ne' l'altra — anagrafiche.bank_branches e' dato di MACCHINA — e
--   il file restava con otto asserzioni rosse su dieci. Ora il cliente
--   (soggetto -> ruolo CL -> istanza -> BA) viene da
--   dbops.fn_pgtap_crea_cliente_ba e la filiale da
--   dbops.fn_pgtap_crea_filiale_bancaria. Il ruolo e il soggetto sono
--   nuovi: la «Pulizia» qui sotto sul ruolo e sul soggetto non trova
--   niente, e resta per gli IBAN fissi di test.
--   ⛔ Cio' che i builder scrivono si legge in un'istruzione SEPARATA.
-- =========================================================
CREATE TEMP TABLE tmp_cli_cb AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('conti istanza cascata');

CREATE TEMP TABLE tmp_g AS
SELECT c.soggetto_ruolo_id, c.soggetto_id, c.istanza_utility_id
FROM tmp_cli_cb c;

SELECT ok((SELECT count(*) FROM tmp_g) = 1, '1) Cliente con istanza costruito');

CREATE TEMP TABLE tmp_bb AS
SELECT bank_branch_id AS id
  FROM dbops.fn_pgtap_crea_filiale_bancaria('conti istanza cascata');

SELECT ok(
    (SELECT count(*) FROM tmp_bb) = 1,
    '2) Bank_branch costruita'
);

-- =========================================================
-- Pulizia
-- =========================================================
-- Pulizia completa: INCASSO + GENERICO + PAGAMENTO per il ruolo di test
DELETE FROM anagrafiche.soggetti_ruoli_conti_bancari srb
USING tmp_g g WHERE srb.soggetto_ruolo_id = g.soggetto_ruolo_id
  AND srb.uso IN ('INCASSO', 'GENERICO', 'PAGAMENTO');

-- Elimina TUTTI i legami soggetto per gli IBAN di test (qualsiasi soggetto)
DELETE FROM anagrafiche.soggetti_conti_bancari scb
USING anagrafiche.conti_bancari cb, tmp_costanti_cb_ut k
WHERE scb.conto_bancario_id = cb.id
  AND cb.iban IN (k.iban_soggetto, k.iban_ruolo_gen, k.iban_ruolo_ist);

-- Elimina TUTTI i legami ruolo per gli IBAN di test (qualsiasi ruolo)
DELETE FROM anagrafiche.soggetti_ruoli_conti_bancari srb
USING anagrafiche.conti_bancari cb, tmp_costanti_cb_ut k
WHERE srb.conto_bancario_id = cb.id
  AND cb.iban IN (k.iban_soggetto, k.iban_ruolo_gen, k.iban_ruolo_ist);

DELETE FROM anagrafiche.conti_bancari cb
USING tmp_costanti_cb_ut k
WHERE cb.iban IN (k.iban_soggetto, k.iban_ruolo_gen, k.iban_ruolo_ist);

-- Disattiva predefiniti esistenti per soggetto
UPDATE anagrafiche.soggetti_conti_bancari scb SET predefinito = FALSE
FROM tmp_g g WHERE scb.soggetto_id = g.soggetto_id
  AND scb.uso IN ('INCASSO', 'GENERICO', 'PAGAMENTO') AND scb.predefinito = TRUE;

DELETE FROM anagrafiche.soggetti_conti_bancari scb
USING tmp_g g
WHERE scb.soggetto_id = g.soggetto_id
  AND scb.uso IN ('GENERICO', 'PAGAMENTO');

-- =========================================================
-- 3) Conto INCASSO a livello soggetto (fallback finale)
-- =========================================================
CREATE TEMP TABLE tmp_cb_sogg AS
WITH ins AS (
    INSERT INTO anagrafiche.conti_bancari (iban, bic_swift, intestatario_predefinito, paese, attivo, verificato, meta, bank_branch_id)
    SELECT k.iban_soggetto, k.bic_test, 'Test soggetto', 'IT', TRUE, FALSE, '{}'::jsonb, bb.id
    FROM tmp_costanti_cb_ut k, tmp_bb bb RETURNING id
) SELECT id FROM ins;

INSERT INTO anagrafiche.soggetti_conti_bancari (soggetto_id, conto_bancario_id, uso, predefinito, valido_dal, verificato, bloccato, meta)
SELECT g.soggetto_id, c.id, 'INCASSO', TRUE, script.fn_data_operativa(), FALSE, FALSE, '{}'::jsonb
FROM tmp_g g, tmp_cb_sogg c;

SELECT ok((SELECT count(*)::int FROM tmp_cb_sogg) = 1, '3) Conto INCASSO soggetto creato');

-- =========================================================
-- 4) Conto INCASSO a livello ruolo generico (istanza NULL)
-- =========================================================
CREATE TEMP TABLE tmp_cb_ruolo_gen AS
WITH ins AS (
    INSERT INTO anagrafiche.conti_bancari (iban, bic_swift, intestatario_predefinito, paese, attivo, verificato, meta, bank_branch_id)
    SELECT k.iban_ruolo_gen, k.bic_test, 'Test ruolo generico', 'IT', TRUE, FALSE, '{}'::jsonb, bb.id
    FROM tmp_costanti_cb_ut k, tmp_bb bb RETURNING id
) SELECT id FROM ins;

INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, istanza_utility_id, valido_dal, verificato, bloccato, meta)
SELECT g.soggetto_ruolo_id, c.id, 'INCASSO', TRUE, NULL, script.fn_data_operativa(), FALSE, FALSE, '{}'::jsonb
FROM tmp_g g, tmp_cb_ruolo_gen c;

SELECT ok((SELECT count(*)::int FROM tmp_cb_ruolo_gen) = 1, '4) Conto INCASSO ruolo generico creato');

-- =========================================================
-- 5) Conto INCASSO a livello ruolo per istanza specifica
-- =========================================================
CREATE TEMP TABLE tmp_cb_ruolo_ist AS
WITH ins AS (
    INSERT INTO anagrafiche.conti_bancari (iban, bic_swift, intestatario_predefinito, paese, attivo, verificato, meta, bank_branch_id)
    SELECT k.iban_ruolo_ist, k.bic_test, 'Test ruolo istanza', 'IT', TRUE, FALSE, '{}'::jsonb, bb.id
    FROM tmp_costanti_cb_ut k, tmp_bb bb RETURNING id
) SELECT id FROM ins;

INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, istanza_utility_id, valido_dal, verificato, bloccato, meta)
SELECT g.soggetto_ruolo_id, c.id, 'INCASSO', TRUE, g.istanza_utility_id, script.fn_data_operativa(), FALSE, FALSE, '{}'::jsonb
FROM tmp_g g, tmp_cb_ruolo_ist c;

SELECT ok((SELECT count(*)::int FROM tmp_cb_ruolo_ist) = 1, '5) Conto INCASSO ruolo+istanza creato');

-- =========================================================
-- 6) fn_get_conto con istanza: livello 1 (ruolo+istanza+uso)
-- =========================================================
SELECT is(
    (
        SELECT (f).conto_bancario_id::text
        FROM tmp_g g,
             LATERAL script.fn_get_conto_bancario_predefinito(g.soggetto_ruolo_id, 'INCASSO', g.istanza_utility_id) AS f
    ),
    (SELECT id::text FROM tmp_cb_ruolo_ist),
    '6) fn_get_conto con istanza: restituisce conto ruolo+istanza (livello 1)'
);

-- =========================================================
-- 7) fn_get_conto senza istanza: livello 2 (ruolo generico)
-- =========================================================
SELECT is(
    (
        SELECT (f).conto_bancario_id::text
        FROM tmp_g g,
             LATERAL script.fn_get_conto_bancario_predefinito(g.soggetto_ruolo_id, 'INCASSO') AS f
    ),
    (SELECT id::text FROM tmp_cb_ruolo_gen),
    '7) fn_get_conto senza istanza: restituisce conto ruolo generico (livello 2)'
);

-- =========================================================
-- 8) Partial unique: blocco duplicato predefinito per (ruolo, istanza, uso)
-- =========================================================
SELECT throws_ok(
    $$
    INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari (
        soggetto_ruolo_id, conto_bancario_id, uso, predefinito, istanza_utility_id,
        valido_dal, verificato, bloccato, meta
    )
    SELECT g.soggetto_ruolo_id,
           (SELECT id FROM tmp_cb_ruolo_gen),
           'INCASSO', TRUE, g.istanza_utility_id, script.fn_data_operativa(), FALSE, FALSE, '{}'::jsonb
    FROM tmp_g g;
    $$,
    '23505',
    NULL,
    '8) Partial unique blocca 2 predefiniti per (ruolo, istanza, INCASSO)'
);

-- =========================================================
-- 9) Vista flat: istanza_utility_id valorizzato per riga istanza
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
        FROM anagrafiche.vw_conti_bancari_per_ruolo v
        JOIN tmp_g g ON g.soggetto_ruolo_id = v.soggetto_ruolo_id
        WHERE v.uso = 'INCASSO'
          AND v.istanza_utility_id IS NOT NULL
          AND v.fonte = 'RUOLO'
    ),
    '9) Vista flat: almeno una riga con istanza_utility_id valorizzato'
);

-- =========================================================
-- 10) fn_get_conto PAGAMENTO con istanza: NULL (nessun PAGAMENTO ne GENERICO)
-- =========================================================
SELECT ok(
    (
        SELECT (f).soggetto_ruolo_id IS NULL
        FROM tmp_g g,
             LATERAL script.fn_get_conto_bancario_predefinito(g.soggetto_ruolo_id, 'PAGAMENTO', g.istanza_utility_id) AS f
    ),
    '10) fn_get_conto PAGAMENTO con istanza: NULL se nessun conto PAGAMENTO ne GENERICO'
);

-- Fine test
SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
