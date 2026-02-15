-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Scopo:
--  - Recuperare un PDP esistente (GAS)
--  - Recuperare un soggetto qualsiasi esistente
--  - Creare una istanza_utility collegata al PDP
--  - Verificare coerenza indirizzo e legami FK
-- ------------------------------------------------------------

SELECT plan(9);


-- =========================================================
--  Pulizia preliminare: rimuove eventuali istanze_utility di test
-- =========================================================

delete from anagrafiche.istanze_utilities
where codice = 'TEST-IU-PDP-001';

-- =========================================================
-- 0) Recupero una utility GAS (precondizione)
-- =========================================================
CREATE TEMP TABLE tmp_utility_gas AS
SELECT id
FROM config.utilities
WHERE codice_interno = 'GAS'
LIMIT 1;

SELECT is(
    (SELECT count(*)::int FROM tmp_utility_gas),
    1,
    'Esiste almeno una utility con codice_interno = GAS'
);

-- =========================================================
-- 1) Recupero un PDP esistente per GAS con indirizzo valorizzato
-- =========================================================
CREATE TEMP TABLE tmp_pdp_test AS
SELECT p.id,
       p.indirizzo_dettaglio_id
FROM anagrafiche.pdp p
JOIN tmp_utility_gas u
  ON p.utility_id = u.id
WHERE p.indirizzo_dettaglio_id IS NOT NULL
LIMIT 1;

SELECT is(
    (SELECT count(*)::int FROM tmp_pdp_test),
    1,
    'Trovato almeno un PDP GAS con indirizzo_dettaglio_id valorizzato'
);

-- =========================================================
-- 2) Recupero un soggetto esistente (qualsiasi)
--    (si assume che il DB di test abbia almeno un soggetto)
-- =========================================================
CREATE TEMP TABLE tmp_soggetto_test AS
SELECT id
FROM anagrafiche.soggetti
where codice = 'TST-PR-001'
ORDER BY data_insert
LIMIT 1;

SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto_test),
    1,
    'Trovato almeno un soggetto da usare per l’istanza_utility'
);

-- =========================================================
-- 3) Creazione istanza_utility collegata al PDP
--    - fittizia = TRUE
--    - indirizzo_dettaglio_id = stesso del PDP
--    - pdp_id = id del PDP
-- =========================================================
WITH ins AS (
    INSERT INTO anagrafiche.istanze_utilities (
        fittizia,
        codice,
        proprietario_inquilino,
        soggetto_id,
        indirizzo_dettaglio_id,
        pdp_id
    )
    SELECT
        FALSE,                               -- fittizia
        'TEST-IU-PDP-001',                  -- codice di test
        'I',                                -- inquilino (valore di default logico)
        s.id,                               -- soggetto di test
        p.indirizzo_dettaglio_id,           -- indirizzo coerente col PDP
        p.id                                -- collegamento al PDP
    FROM tmp_soggetto_test s,
         tmp_pdp_test p
    RETURNING id,
              soggetto_id,
              indirizzo_dettaglio_id,
              pdp_id
)
SELECT *
INTO TEMP TABLE tmp_istanza_test
FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_istanza_test),
    1,
    'Inserita esattamente 1 istanza_utility collegata al PDP'
);

-- =========================================================
-- 4) Verifica coerenza indirizzo istanza ↔ PDP
-- =========================================================
SELECT results_eq(
    $$
    SELECT
        i.indirizzo_dettaglio_id::bigint,
        i.pdp_id::bigint
    FROM tmp_istanza_test i
    $$,
    $$
    SELECT
        p.indirizzo_dettaglio_id::bigint,
        p.id::bigint
    FROM tmp_pdp_test p
    $$,
    'istanza_utility.indirizzo_dettaglio_id e pdp_id coerenti con anagrafiche.pdp'
);

-- =========================================================
-- 5) Verifica esistenza delle righe collegate (FK logica)
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
        FROM anagrafiche.istanze_utilities iu
        JOIN anagrafiche.pdp p
          ON p.id = iu.pdp_id
         AND p.indirizzo_dettaglio_id = iu.indirizzo_dettaglio_id
        JOIN anagrafiche.soggetti s
          ON s.id = iu.soggetto_id
        WHERE iu.id = (SELECT id FROM tmp_istanza_test)
    ),
    'Istanza_utility è collegata coerentemente a PDP e Soggetto'
);

-- =========================================================
-- 6) Verifica vincolo implicito su indirizzo (pdp_id → indirizzo non nullo)
--    (ridondante rispetto alla FK, ma esplicito a livello di test)
-- =========================================================
SELECT ok(
    (
        SELECT indirizzo_dettaglio_id IS NOT NULL
        FROM anagrafiche.istanze_utilities
        WHERE id = (SELECT id FROM tmp_istanza_test)
    ),
    'Per istanza_utility con pdp_id valorizzato, indirizzo_dettaglio_id è NOT NULL'
);


-- =========================================================
-- 7) Non è consentito mettere fittizia = TRUE se pdp_id NON è NULL
-- =========================================================

-- Precondizione: l'istanza di test esiste e ha pdp_id valorizzato
SELECT is(
    (
        SELECT count(*)::int
        FROM anagrafiche.istanze_utilities
        WHERE codice = 'TEST-IU-PDP-001'
          AND pdp_id IS NOT NULL
    ),
    1,
    'Esiste esattamente 1 istanza TEST-IU-PDP-001 con pdp_id valorizzato'
);

-- Tentativo di violare il vincolo: deve sollevare errore di CHECK (23514)
SELECT throws_ok(
    $$
    UPDATE anagrafiche.istanze_utilities
       SET fittizia = TRUE
     WHERE codice = 'TEST-IU-PDP-001';
    $$,
    '23514',                                      -- check_violation
     NULL,                   -- oppure NULL / '' se vuoi ignorare il messaggio
    'threw 23514 per vincolo chk_iu_pdp_not_fittizia'
);



-- Fine test
SELECT * FROM finish();
