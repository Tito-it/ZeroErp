-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Trigger: dbops.trgfn_prevent_deactivate_if_children
-- Caso: config.stati_pdp (padre) -> anagrafiche.pdp (figlio con attivo)
-- ------------------------------------------------------------

SELECT plan(12);

CREATE TEMP TABLE tmp_test_keys AS
SELECT '*$*' AS ts;

-- =========================================================
-- 0) Verifica presenza trigger BLOCK su stati_pdp
-- =========================================================
CREATE TEMP TABLE tmp_trg_block AS
SELECT EXISTS (
    SELECT 1
    FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'config'
      AND c.relname = 'stati_pdp'
      AND t.tgname ILIKE '%block_deact%'
      AND NOT t.tgisinternal
) AS has_trg;

SELECT ok(
    (SELECT has_trg FROM tmp_trg_block),
    'Trigger BLOCK presente su config.stati_pdp'
);

-- =========================================================
-- 1) Crea stato_pdp di test
-- =========================================================
WITH ins AS (
    INSERT INTO config.stati_pdp (codice_interno, codice, descrizione, attivo)
    VALUES (
        'TST_PDP_' || (SELECT ts FROM tmp_test_keys),
        'TST_PDP_' || (SELECT ts FROM tmp_test_keys),
        'Stato PDP test trgfn_prevent_deactivate_if_children',
        true
    )
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_stato_pdp
FROM ins;

SELECT ok(
    (SELECT count(*) FROM tmp_stato_pdp) = 1,
    'Creato stato_pdp di test'
);

-- =========================================================
-- 2) Disattivazione senza figli: deve passare
-- =========================================================
SELECT lives_ok(
    $$
    UPDATE config.stati_pdp
    SET attivo = false
    WHERE id = (SELECT id FROM tmp_stato_pdp);
    $$,
    'Disattivazione stato_pdp senza figli: OK'
);

SELECT is(
    (SELECT attivo FROM config.stati_pdp WHERE id = (SELECT id FROM tmp_stato_pdp)),
    false,
    'stato_pdp disattivato quando non ci sono figli'
);

-- Riattiva per il test con figlio
SELECT lives_ok(
    $$
    UPDATE config.stati_pdp
    SET attivo = true
    WHERE id = (SELECT id FROM tmp_stato_pdp);
    $$,
    'Riattivazione stato_pdp per test con figlio'
);

-- =========================================================
-- 3) Inserimento PDP figlio (se prerequisiti presenti)
-- =========================================================
CREATE TEMP TABLE tmp_pdp_base AS
SELECT
    (SELECT id FROM config.utilities ORDER BY id LIMIT 1) AS utility_id,
    (SELECT id FROM anagrafiche.indirizzi_dettaglio ORDER BY id LIMIT 1) AS indirizzo_id;

SELECT ok(
    (SELECT utility_id IS NOT NULL AND indirizzo_id IS NOT NULL FROM tmp_pdp_base),
    'Prerequisiti presenti per inserimento PDP'
);

SELECT CASE
    WHEN (SELECT utility_id IS NOT NULL AND indirizzo_id IS NOT NULL FROM tmp_pdp_base) THEN
        lives_ok(
            $$
            INSERT INTO anagrafiche.pdp (pdp, utilities_id, indirizzo_dettaglio_id, stato_pdp_id)
            SELECT
                'PDP-TST-BLOCK-' || (SELECT ts FROM tmp_test_keys),
                utility_id,
                indirizzo_id,
                (SELECT id FROM tmp_stato_pdp)
            FROM tmp_pdp_base;
            $$,
            'Inserito PDP figlio di test'
        )
    ELSE
        ok(true, 'Prerequisiti mancanti: inserimento PDP skipped')
END;

CREATE TEMP TABLE tmp_pdp_child AS
SELECT id
FROM anagrafiche.pdp
WHERE stato_pdp_id = (SELECT id FROM tmp_stato_pdp)
ORDER BY id
LIMIT 1;

-- =========================================================
-- 4) Disattivazione con figlio: deve fallire
-- =========================================================
SELECT CASE
    WHEN (SELECT utility_id IS NOT NULL AND indirizzo_id IS NOT NULL FROM tmp_pdp_base) THEN
        throws_ok(
            $$
            UPDATE config.stati_pdp
            SET attivo = false
            WHERE id = (SELECT id FROM tmp_stato_pdp);
            $$,
            NULL,
            NULL,
            'Disattivazione stato_pdp con figli: bloccata'
        )
    ELSE
        ok(true, 'Prerequisiti mancanti: test blocco skipped')
END;

-- =========================================================
-- 5) Disattivazione figlio e blocco sbloccato sul padre
-- =========================================================
SELECT CASE
    WHEN (SELECT count(*) FROM tmp_pdp_child) = 1 THEN
        lives_ok(
            $$
            UPDATE anagrafiche.pdp
            SET attivo = false
            WHERE id = (SELECT id FROM tmp_pdp_child);
            $$,
            'Disattivazione PDP figlio: OK'
        )
    ELSE
        ok(true, 'PDP figlio non presente: test disattivazione figlio skipped')
END;

SELECT CASE
    WHEN (SELECT count(*) FROM tmp_pdp_child) = 1 THEN
        is(
            (SELECT attivo FROM anagrafiche.pdp WHERE id = (SELECT id FROM tmp_pdp_child)),
            false,
            'PDP figlio disattivato'
        )
    ELSE
        ok(true, 'PDP figlio non presente: check attivo skipped')
END;

SELECT CASE
    WHEN (SELECT count(*) FROM tmp_pdp_child) = 1 THEN
        lives_ok(
            $$
            UPDATE config.stati_pdp
            SET attivo = false
            WHERE id = (SELECT id FROM tmp_stato_pdp);
            $$,
            'Disattivazione stato_pdp con figli disattivi: OK'
        )
    ELSE
        ok(true, 'PDP figlio non presente: test disattivazione padre skipped')
END;

SELECT CASE
    WHEN (SELECT count(*) FROM tmp_pdp_child) = 1 THEN
        is(
            (SELECT attivo FROM config.stati_pdp WHERE id = (SELECT id FROM tmp_stato_pdp)),
            false,
            'stato_pdp disattivato con figli disattivi'
        )
    ELSE
        ok(true, 'PDP figlio non presente: check attivo padre skipped')
END;

-- Cleanup
DELETE FROM anagrafiche.pdp
WHERE stato_pdp_id = (SELECT id FROM tmp_stato_pdp);

DELETE FROM config.stati_pdp
WHERE id = (SELECT id FROM tmp_stato_pdp);
