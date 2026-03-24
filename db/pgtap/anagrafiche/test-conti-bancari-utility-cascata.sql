-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test cascata conti bancari con utility_id:
--   - Partial unique index (utility NULL e valorizzato)
--   - fn_get_conto_bancario_predefinito con p_utility_id
--   - Cascata 7 livelli: ruolo+utility -> ruolo generico -> soggetto -> GENERICO
--   - Vista flat espone utility_id/utility_codice
-- ------------------------------------------------------------

SELECT plan(10);

-- Indice test (10):
--  1) Esiste almeno un Gestore
--  2) Esiste almeno una utility attiva e una bank_branch
--  3) Conto INCASSO a livello soggetto creato (fallback)
--  4) Conto INCASSO a livello ruolo generico (utility NULL) creato
--  5) Conto INCASSO a livello ruolo per utility specifica creato
--  6) fn_get_conto con utility: restituisce conto ruolo+utility (livello 1)
--  7) fn_get_conto senza utility: restituisce conto ruolo generico (livello 2)
--  8) Partial unique: blocco duplicato predefinito per (ruolo, utility, uso)
--  9) Vista flat: espone utility_codice per riga utility
-- 10) fn_get_conto PAGAMENTO con utility: fallback a GENERICO ruolo+utility

-- =========================================================
-- Costanti
-- =========================================================
CREATE TEMP TABLE tmp_costanti_cb_ut AS
SELECT
    'IT11Z0000000000000000000011'::varchar AS iban_soggetto,
    'IT22Z0000000000000000000022'::varchar AS iban_ruolo_gen,
    'IT33Z0000000000000000000033'::varchar AS iban_ruolo_util,
    'BGFNOIT2XXX'::varchar                AS bic_test;

-- =========================================================
-- Setup: Gestore, utility, bank_branch
-- =========================================================
CREATE TEMP TABLE tmp_g AS
SELECT g.id AS gestore_id, g.soggetto_ruolo_id, sr.soggetto_id
FROM anagrafiche.gestori g
JOIN anagrafiche.soggetti_ruoli sr ON sr.id = g.soggetto_ruolo_id
ORDER BY g.id LIMIT 1;

SELECT ok((SELECT count(*) FROM tmp_g) = 1, '1) Esiste almeno un Gestore');

CREATE TEMP TABLE tmp_util AS
SELECT u.id, u.codice FROM config.utilities u WHERE TRUE ORDER BY u.id LIMIT 1;

CREATE TEMP TABLE tmp_bb AS
SELECT bb.id FROM anagrafiche.bank_branches bb ORDER BY bb.id LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_util) = 1 AND (SELECT count(*) FROM tmp_bb) = 1,
    '2) Utility attiva e bank_branch presenti'
);

-- =========================================================
-- Pulizia: rimuovi legami e conti di test
-- =========================================================
-- Pulizia completa: INCASSO + GENERICO + PAGAMENTO per il ruolo di test
DELETE FROM anagrafiche.soggetti_ruoli_conti_bancari srb
USING tmp_g g WHERE srb.soggetto_ruolo_id = g.soggetto_ruolo_id
  AND srb.uso IN ('INCASSO', 'GENERICO', 'PAGAMENTO');

DELETE FROM anagrafiche.soggetti_conti_bancari scb
USING anagrafiche.conti_bancari cb, tmp_g g, tmp_costanti_cb_ut k
WHERE scb.conto_bancario_id = cb.id AND scb.soggetto_id = g.soggetto_id
  AND cb.iban IN (k.iban_soggetto, k.iban_ruolo_gen, k.iban_ruolo_util);

DELETE FROM anagrafiche.conti_bancari cb
USING tmp_costanti_cb_ut k
WHERE cb.iban IN (k.iban_soggetto, k.iban_ruolo_gen, k.iban_ruolo_util);

-- Disattiva predefiniti esistenti per soggetto (tutti gli usi coinvolti)
UPDATE anagrafiche.soggetti_conti_bancari scb SET predefinito = FALSE
FROM tmp_g g WHERE scb.soggetto_id = g.soggetto_id
  AND scb.uso IN ('INCASSO', 'GENERICO', 'PAGAMENTO') AND scb.predefinito = TRUE;

-- Elimina legami soggetto GENERICO/PAGAMENTO (non solo gli IBAN di test)
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
SELECT g.soggetto_id, c.id, 'INCASSO', TRUE, CURRENT_DATE, FALSE, FALSE, '{}'::jsonb
FROM tmp_g g, tmp_cb_sogg c;

SELECT ok((SELECT count(*)::int FROM tmp_cb_sogg) = 1, '3) Conto INCASSO soggetto creato');

-- =========================================================
-- 4) Conto INCASSO a livello ruolo generico (utility NULL)
-- =========================================================
CREATE TEMP TABLE tmp_cb_ruolo_gen AS
WITH ins AS (
    INSERT INTO anagrafiche.conti_bancari (iban, bic_swift, intestatario_predefinito, paese, attivo, verificato, meta, bank_branch_id)
    SELECT k.iban_ruolo_gen, k.bic_test, 'Test ruolo generico', 'IT', TRUE, FALSE, '{}'::jsonb, bb.id
    FROM tmp_costanti_cb_ut k, tmp_bb bb RETURNING id
) SELECT id FROM ins;

INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, utility_id, valido_dal, verificato, bloccato, meta)
SELECT g.soggetto_ruolo_id, c.id, 'INCASSO', TRUE, NULL, CURRENT_DATE, FALSE, FALSE, '{}'::jsonb
FROM tmp_g g, tmp_cb_ruolo_gen c;

SELECT ok((SELECT count(*)::int FROM tmp_cb_ruolo_gen) = 1, '4) Conto INCASSO ruolo generico creato');

-- =========================================================
-- 5) Conto INCASSO a livello ruolo per utility specifica
-- =========================================================
CREATE TEMP TABLE tmp_cb_ruolo_util AS
WITH ins AS (
    INSERT INTO anagrafiche.conti_bancari (iban, bic_swift, intestatario_predefinito, paese, attivo, verificato, meta, bank_branch_id)
    SELECT k.iban_ruolo_util, k.bic_test, 'Test ruolo utility', 'IT', TRUE, FALSE, '{}'::jsonb, bb.id
    FROM tmp_costanti_cb_ut k, tmp_bb bb RETURNING id
) SELECT id FROM ins;

INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, utility_id, valido_dal, verificato, bloccato, meta)
SELECT g.soggetto_ruolo_id, c.id, 'INCASSO', TRUE, u.id, CURRENT_DATE, FALSE, FALSE, '{}'::jsonb
FROM tmp_g g, tmp_cb_ruolo_util c, tmp_util u;

SELECT ok((SELECT count(*)::int FROM tmp_cb_ruolo_util) = 1, '5) Conto INCASSO ruolo+utility creato');

-- =========================================================
-- 6) fn_get_conto con utility: livello 1 (ruolo+utility+uso)
-- =========================================================
SELECT is(
    (
        SELECT (f).conto_bancario_id::text
        FROM tmp_g g, tmp_util u,
             LATERAL script.fn_get_conto_bancario_predefinito(g.soggetto_ruolo_id, 'INCASSO', u.id) AS f
    ),
    (SELECT id::text FROM tmp_cb_ruolo_util),
    '6) fn_get_conto con utility: restituisce conto ruolo+utility (livello 1)'
);

-- =========================================================
-- 7) fn_get_conto senza utility: livello 2 (ruolo generico)
-- =========================================================
SELECT is(
    (
        SELECT (f).conto_bancario_id::text
        FROM tmp_g g,
             LATERAL script.fn_get_conto_bancario_predefinito(g.soggetto_ruolo_id, 'INCASSO') AS f
    ),
    (SELECT id::text FROM tmp_cb_ruolo_gen),
    '7) fn_get_conto senza utility: restituisce conto ruolo generico (livello 2)'
);

-- =========================================================
-- 8) Partial unique: blocco duplicato predefinito per (ruolo, utility, uso)
-- =========================================================
SELECT throws_ok(
    $$
    INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari (
        soggetto_ruolo_id, conto_bancario_id, uso, predefinito, utility_id,
        valido_dal, verificato, bloccato, meta
    )
    SELECT g.soggetto_ruolo_id,
           (SELECT id FROM tmp_cb_ruolo_gen),
           'INCASSO', TRUE, u.id, CURRENT_DATE, FALSE, FALSE, '{}'::jsonb
    FROM tmp_g g, tmp_util u;
    $$,
    '23505',
    NULL,
    '8) Partial unique blocca 2 predefiniti per (ruolo, utility, INCASSO)'
);

-- =========================================================
-- 9) Vista flat: utility_codice valorizzato per riga utility
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
        FROM anagrafiche.vw_conti_bancari_per_ruolo v
        JOIN tmp_g g ON g.soggetto_ruolo_id = v.soggetto_ruolo_id
        WHERE v.uso = 'INCASSO'
          AND v.utility_codice IS NOT NULL
          AND v.fonte = 'RUOLO'
    ),
    '9) Vista flat: almeno una riga con utility_codice valorizzato'
);

-- =========================================================
-- 10) fn_get_conto PAGAMENTO con utility: NULL (nessun PAGAMENTO ne GENERICO configurato)
-- =========================================================
SELECT ok(
    (
        SELECT (f).soggetto_ruolo_id IS NULL
        FROM tmp_g g, tmp_util u,
             LATERAL script.fn_get_conto_bancario_predefinito(g.soggetto_ruolo_id, 'PAGAMENTO', u.id) AS f
    ),
    '10) fn_get_conto PAGAMENTO con utility: NULL se nessun conto PAGAMENTO ne GENERICO'
);

-- Fine test
SELECT * FROM finish();
