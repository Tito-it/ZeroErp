-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_conto_bancario_predefinito(soggetto_ruolo_id, uso)
-- ------------------------------------------------------------

SELECT plan(6);

-- =========================================================
-- Costanti per il test
-- =========================================================
CREATE TEMP TABLE tmp_costanti_fn_conto AS
SELECT
    'IT88Z0000000000000000000000'::varchar AS iban_incasso,
    'IT99Z0000000000000000000001'::varchar AS iban_generico,
    'BGFNOIT2XXX'::varchar                   AS bic_swift_test,
    'INCASSO'::varchar                      AS uso_incasso,
    'GENERICO'::varchar                     AS uso_generico,
    'PAGAMENTO'::varchar                    AS uso_pagamento;

BEGIN;

-- ---------------------------------------------------------
-- 1) Recupero Gestore (ruolo + soggetto)
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_gestore AS
SELECT
    g.id                AS gestore_id,
    g.soggetto_ruolo_id AS soggetto_ruolo_id,
    sr.soggetto_id      AS soggetto_id
FROM anagrafiche.gestori g
JOIN anagrafiche.soggetti_ruoli sr
  ON sr.id = g.soggetto_ruolo_id
ORDER BY g.id
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_gestore) = 1,
    'Esiste almeno un Gestore (soggetto_ruolo + soggetto)'
);

-- ---------------------------------------------------------
-- 2) Recupero di una bank_branch per collegare i conti
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_bank_branch AS
SELECT
    bb.id,
    bb.bank_code,
    bb.branch_code
FROM anagrafiche.bank_branches bb
ORDER BY bb.id
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_bank_branch) = 1,
    'Esiste almeno una bank_branch da collegare ai conti'
);

-- =========================================================
-- Pulizia scenario per il soggetto del Gestore
-- =========================================================
-- - nessun legame di ruolo per uso INCASSO/PAGAMENTO/GENERICO
-- - nessun legame di soggetto con gli IBAN di test
-- - reset dei predefiniti per INCASSO/GENERICO a livello soggetto
-- =========================================================

-- 2.1) Pulisce legami di ruolo
DELETE FROM anagrafiche.soggetti_ruoli_conti_bancari srb
USING tmp_gestore g,
      tmp_costanti_fn_conto k
WHERE srb.soggetto_ruolo_id = g.soggetto_ruolo_id
  AND srb.uso IN (k.uso_incasso, k.uso_generico, k.uso_pagamento);

-- 2.2) Pulisce legami soggetto_conti_bancari sugli IBAN test
DELETE FROM anagrafiche.soggetti_conti_bancari scb
USING anagrafiche.conti_bancari cb,
      tmp_gestore g,
      tmp_costanti_fn_conto k
WHERE scb.conto_bancario_id = cb.id
  AND scb.soggetto_id       = g.soggetto_id
  AND cb.iban IN (k.iban_incasso, k.iban_generico);

-- 2.3) Cancella conti con gli IBAN di test
DELETE FROM anagrafiche.conti_bancari cb
USING tmp_costanti_fn_conto k
WHERE cb.iban IN (k.iban_incasso, k.iban_generico);

-- 2.4) Disattiva eventuali predefiniti INCASSO/GENERICO per il soggetto del Gestore
UPDATE anagrafiche.soggetti_conti_bancari scb
SET predefinito = FALSE
FROM tmp_gestore g,
     tmp_costanti_fn_conto k
WHERE scb.soggetto_id = g.soggetto_id
  AND scb.uso IN (k.uso_incasso, k.uso_generico)
  AND scb.predefinito = TRUE;

-- ---------------------------------------------------------
-- 3) Crea conto INCASSO a livello soggetto (predefinito)
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_conto_incasso AS
WITH nuovo_conto AS (
    INSERT INTO anagrafiche.conti_bancari (
        iban,
        bic_swift,
        intestatario_predefinito,
        paese,
        attivo,
        verificato,
        meta,
        bank_branch_id
    )
    SELECT
        k.iban_incasso,
        k.bic_swift_test,
        'Conto INCASSO Gestore (fn test)',
        'IT',
        TRUE,
        FALSE,
        jsonb_build_object('test_scope', 'fn_get_conto_predef_incasso'),
        bb.id
    FROM tmp_costanti_fn_conto k,
         tmp_bank_branch bb
    RETURNING id
)
SELECT id
FROM nuovo_conto;

SELECT is(
    (SELECT count(*)::int FROM tmp_conto_incasso),
    1,
    'Creato 1 conto INCASSO globale per il soggetto del Gestore'
);

CREATE TEMP TABLE tmp_link_incasso AS
WITH link AS (
    INSERT INTO anagrafiche.soggetti_conti_bancari (
        soggetto_id,
        conto_bancario_id,
        uso,
        predefinito,
        valido_dal,
        valido_al,
        intestazione_dichiarata,
        verificato,
        bloccato,
        meta
    )
    SELECT
        g.soggetto_id,
        c.id,
        k.uso_incasso,
        TRUE,
        CURRENT_DATE,
        NULL,
        NULL,
        FALSE,
        FALSE,
        jsonb_build_object('test_scope', 'fn_get_conto_predef_incasso')
    FROM tmp_gestore g,
         tmp_conto_incasso c,
         tmp_costanti_fn_conto k
    RETURNING id
)
SELECT id
FROM link;

-- ---------------------------------------------------------
-- 4) Test funzione – caso base (uso = INCASSO)
-- ---------------------------------------------------------
SELECT is(
    (
        SELECT row((f).fonte, (f).conto_bancario_id, (f).uso)::text
        FROM tmp_gestore g,
             tmp_costanti_fn_conto k,
             LATERAL script.fn_get_conto_bancario_predefinito(g.soggetto_ruolo_id, k.uso_incasso) AS f
    ),
    (
        SELECT row('SOGGETTO'::varchar,
                   c.id,
                   k.uso_incasso)::text
        FROM tmp_conto_incasso c,
             tmp_costanti_fn_conto k
    ),
    'fn_get_conto_bancario_predefinito restituisce il conto INCASSO di SOGGETTO come fonte=SOGGETTO'
);

-- ---------------------------------------------------------
-- 5) Crea conto GENERICO e testa fallback da PAGAMENTO → GENERICO
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_conto_generico AS
WITH nuovo_conto AS (
    INSERT INTO anagrafiche.conti_bancari (
        iban,
        bic_swift,
        intestatario_predefinito,
        paese,
        attivo,
        verificato,
        meta,
        bank_branch_id
    )
    SELECT
        k.iban_generico,
        k.bic_swift_test,
        'Conto GENERICO Gestore (fn test)',
        'IT',
        TRUE,
        FALSE,
        jsonb_build_object('test_scope', 'fn_get_conto_predef_generico'),
        bb.id
    FROM tmp_costanti_fn_conto k,
         tmp_bank_branch bb
    RETURNING id
)
SELECT id
FROM nuovo_conto;

CREATE TEMP TABLE tmp_link_generico AS
WITH link AS (
    INSERT INTO anagrafiche.soggetti_conti_bancari (
        soggetto_id,
        conto_bancario_id,
        uso,
        predefinito,
        valido_dal,
        valido_al,
        intestazione_dichiarata,
        verificato,
        bloccato,
        meta
    )
    SELECT
        g.soggetto_id,
        c.id,
        k.uso_generico,
        TRUE,
        CURRENT_DATE,
        NULL,
        NULL,
        FALSE,
        FALSE,
        jsonb_build_object('test_scope', 'fn_get_conto_predef_generico')
    FROM tmp_gestore g,
         tmp_conto_generico c,
         tmp_costanti_fn_conto k
    RETURNING id
)
SELECT id
FROM link;

SELECT is(
    (SELECT count(*)::int FROM tmp_conto_generico),
    1,
    'Creato 1 conto GENERICO per il soggetto del Gestore'
);

-- Nessun conto per uso PAGAMENTO → funzione deve fare fallback a GENERICO
SELECT is(
    (
        SELECT row((f).fonte, (f).conto_bancario_id, (f).uso)::text
        FROM tmp_gestore g,
             tmp_costanti_fn_conto k,
             LATERAL script.fn_get_conto_bancario_predefinito(g.soggetto_ruolo_id, k.uso_pagamento) AS f
    ),
    (
        SELECT row('SOGGETTO'::varchar,
                   c.id,
                   k.uso_generico)::text
        FROM tmp_conto_generico c,
             tmp_costanti_fn_conto k
    ),
    'fn_get_conto_bancario_predefinito fa fallback da uso=PAGAMENTO a uso=GENERICO per il ruolo Gestore'
);

SET CONSTRAINTS ALL IMMEDIATE;
COMMIT;

SELECT * FROM finish();
