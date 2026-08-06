-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Scopo:
--  - Verificare policy utility/PDP su anagrafiche.trgfn_clienti_sync_utility_from_ba()
--
-- Indice test (14):
--  T01) Esiste utility GAS
--  T02) GAS ha richiede_pdp=true
--  T03) Esiste almeno una utility non GAS/ENERGIA/IDRICO con richiede_pdp=false
--  T04) Esiste stato cliente AT
--  T05) Esiste IVA codice 22
--  T06) Esiste soggetto di test
--  T07) Esiste PDP GAS con indirizzo valorizzato
--  T08) Create 4 istanze di test
--  T09) Inserimento cliente GAS con PDP valorizzato (OK)
--  T10) Sync utility cliente <- billing account (caso GAS)
--  T11) Blocco: utility richiede_pdp=true ma pdp_id NULL
--  T12) Blocco: mismatch utility tra billing account e PDP
--  T13) Inserimento cliente con utility richiede_pdp=false e pdp_id NULL (OK)
--  T14) Sync utility cliente <- billing account (caso no-PDP)
-- ------------------------------------------------------------

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- ⚠️ Questo file non apre una transazione propria: la riga va prima di plan().
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(14);

-- =========================================================
-- Codici test univoci runtime (evita cleanup distruttivo)
-- =========================================================
CREATE TEMP TABLE tmp_codes AS
WITH s AS (
    SELECT upper(substring(md5(random()::text || clock_timestamp()::text), 1, 4)) AS suffix
)
SELECT
    ('TST-IU-UP1-' || suffix)::varchar(50) AS iu1,
    ('TST-IU-UP2-' || suffix)::varchar(50) AS iu2,
    ('TST-IU-UP3-' || suffix)::varchar(50) AS iu3,
    ('TST-IU-UP4-' || suffix)::varchar(50) AS iu4,
    ('TST-BA-UP1-' || suffix)::varchar(50) AS ba1,
    ('TST-BA-UP2-' || suffix)::varchar(50) AS ba2,
    ('TST-BA-UP3-' || suffix)::varchar(50) AS ba3,
    ('TST-BA-UP4-' || suffix)::varchar(50) AS ba4,
    ('TST-CLI-UP1-' || suffix)::varchar(50) AS cli1,
    ('TST-CLI-UP2-' || suffix)::varchar(50) AS cli2,
    ('TST-CLI-UP3-' || suffix)::varchar(50) AS cli3,
    ('TST-CLI-UP4-' || suffix)::varchar(50) AS cli4
FROM s;

-- =========================================================
-- 0) Precondizioni
-- =========================================================
CREATE TEMP TABLE tmp_utility_gas AS
SELECT id, coalesce(richiede_pdp, false) AS richiede_pdp
FROM config.utilities
WHERE codice_interno = 'GAS'
LIMIT 1;

SELECT is(
    (SELECT count(*)::int FROM tmp_utility_gas),
    1,
    'T01 Esiste utility GAS in config.utilities'
);

SELECT ok(
    (SELECT richiede_pdp FROM tmp_utility_gas),
    'T02 Per GAS il flag richiede_pdp e'' true'
);

CREATE TEMP TABLE tmp_utility_no_pdp AS
SELECT id, codice_interno
FROM config.utilities
WHERE coalesce(richiede_pdp, false) = false
  AND codice_interno NOT IN ('GAS', 'ENERGIA', 'IDRICO')
ORDER BY id
LIMIT 1;

SELECT is(
    (SELECT count(*)::int FROM tmp_utility_no_pdp),
    1,
    'T03 Esiste almeno una utility con richiede_pdp=false diversa da GAS/ENERGIA/IDRICO'
);

CREATE TEMP TABLE tmp_stato_attivo AS
SELECT id
FROM config.stati_cliente
WHERE codice_interno = 'AT'
LIMIT 1;

SELECT is(
    (SELECT count(*)::int FROM tmp_stato_attivo),
    1,
    'T04 Esiste stato_cliente AT'
);

CREATE TEMP TABLE tmp_iva AS
SELECT id
FROM config.iva
WHERE codice = '22'
LIMIT 1;

SELECT is(
    (SELECT count(*)::int FROM tmp_iva),
    1,
    'T05 Esiste aliquota IVA codice=22'
);

CREATE TEMP TABLE tmp_soggetto_test AS
SELECT id
FROM anagrafiche.soggetti
WHERE partita_iva = '24551170426'
LIMIT 1;

SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto_test),
    1,
    'T06 Trovato soggetto di test'
);

CREATE TEMP TABLE tmp_sr_test AS
SELECT script.fn_get_or_create_soggetto_ruolo(s.id, 'CL') AS soggetto_ruolo_id
FROM tmp_soggetto_test s;

CREATE TEMP TABLE tmp_pdp_gas AS
SELECT p.id,
       p.indirizzo_dettaglio_id,
       p.utility_id AS utility_id
FROM anagrafiche.pdp p
JOIN tmp_utility_gas ug
  ON ug.id = p.utility_id
WHERE p.indirizzo_dettaglio_id IS NOT NULL
LIMIT 1;

SELECT is(
    (SELECT count(*)::int FROM tmp_pdp_gas),
    1,
    'T07 Trovato PDP GAS con indirizzo valorizzato'
);

-- Data base per evitare conflitti con dati gia' presenti nel DB di test
CREATE TEMP TABLE tmp_date_base AS
SELECT (current_date + 30)::date AS d0;

-- Chiusura preventiva eventuale cliente attivo sul PDP alla data test
CREATE TEMP TABLE tmp_subentro_pre AS
SELECT script.fn_subentro_cliente(
    (SELECT id FROM tmp_pdp_gas),
    (SELECT d0 FROM tmp_date_base)
) AS cliente_chiuso_id;

-- =========================================================
-- 1) Dati di test (4 istanze + 4 billing account)
-- =========================================================
CREATE TEMP TABLE tmp_iu_created AS
WITH ins AS (
    INSERT INTO anagrafiche.istanze_utilities (
        fittizia,
        codice,
        proprietario_inquilino,
        soggetto_id,
        indirizzo_dettaglio_id,
        pdp_id
    )
    SELECT false, tc.iu1, 'P', s.id, p.indirizzo_dettaglio_id, p.id
    FROM tmp_soggetto_test s, tmp_pdp_gas p, tmp_codes tc
    UNION ALL
    SELECT true, tc.iu2, 'P', s.id, NULL::bigint, NULL::bigint
    FROM tmp_soggetto_test s, tmp_codes tc
    UNION ALL
    SELECT false, tc.iu3, 'P', s.id, p.indirizzo_dettaglio_id, p.id
    FROM tmp_soggetto_test s, tmp_pdp_gas p, tmp_codes tc
    UNION ALL
    SELECT true, tc.iu4, 'P', s.id, NULL::bigint, NULL::bigint
    FROM tmp_soggetto_test s, tmp_codes tc
    RETURNING id, codice
)
SELECT *
FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_iu_created),
    4,
    'T08 Create 4 istanze di test per i diversi scenari utility/PDP'
);

CREATE TEMP TABLE tmp_ba_created AS
WITH ins AS (
    INSERT INTO anagrafiche.billing_account (
        istanza_utility_id,
        soggetto_ruolo_id,
        utility_id,
        codice
    )
    SELECT iu1.id, sr.soggetto_ruolo_id, ug.id, tc.ba1
    FROM anagrafiche.istanze_utilities iu1, tmp_sr_test sr, tmp_utility_gas ug, tmp_codes tc
    WHERE iu1.codice = tc.iu1
    UNION ALL
    SELECT iu2.id, sr.soggetto_ruolo_id, ug.id, tc.ba2
    FROM anagrafiche.istanze_utilities iu2, tmp_sr_test sr, tmp_utility_gas ug, tmp_codes tc
    WHERE iu2.codice = tc.iu2
    UNION ALL
    SELECT iu3.id, sr.soggetto_ruolo_id, unp.id, tc.ba3
    FROM anagrafiche.istanze_utilities iu3, tmp_sr_test sr, tmp_utility_no_pdp unp, tmp_codes tc
    WHERE iu3.codice = tc.iu3
    UNION ALL
    SELECT iu4.id, sr.soggetto_ruolo_id, unp.id, tc.ba4
    FROM anagrafiche.istanze_utilities iu4, tmp_sr_test sr, tmp_utility_no_pdp unp, tmp_codes tc
    WHERE iu4.codice = tc.iu4
    RETURNING id, codice, utility_id, istanza_utility_id
)
SELECT *
FROM ins;

-- =========================================================
-- 2) Caso OK: utility richiede PDP + PDP presente e coerente
-- =========================================================
CREATE TEMP TABLE tmp_cli_ok_gas AS
WITH ins AS (
    INSERT INTO anagrafiche.clienti (
        soggetto_ruolo_id,
        istanza_utility_id,
        stato_cliente_id,
        data_attivazione,
        billing_account_id,
        codice_cliente_importato,
        iva_id,
        pdp_id,
        utility_id
    )
    SELECT
        sr.soggetto_ruolo_id,
        iu.id,
        st.id,
        dt.d0,
        ba.id,
        tc.cli1,
        iv.id,
        p.id,
        NULL::integer
    FROM tmp_sr_test sr,
         tmp_stato_attivo st,
         tmp_iva iv,
         tmp_date_base dt,
         tmp_codes tc,
         anagrafiche.istanze_utilities iu,
         anagrafiche.billing_account ba,
         tmp_pdp_gas p
    WHERE iu.codice = tc.iu1
      AND ba.codice = tc.ba1
    RETURNING id, utility_id, billing_account_id
)
SELECT *
FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_cli_ok_gas),
    1,
    'T09 Inserimento cliente GAS con PDP valorizzato: OK'
);

SELECT results_eq(
    $$
    SELECT c.utility_id::int
    FROM anagrafiche.clienti c
    WHERE c.codice_cliente_importato = (SELECT cli1 FROM tmp_codes)
    $$,
    $$
    SELECT ba.utility_id::int
    FROM anagrafiche.billing_account ba
    WHERE ba.codice = (SELECT ba1 FROM tmp_codes)
    $$,
    'T10 clienti.utility_id sincronizzato con billing_account.utility_id (caso GAS valido)'
);

-- =========================================================
-- 3) Caso KO: utility richiede PDP ma cliente.pdp_id NULL
-- =========================================================
SELECT throws_ok(
    $$
    INSERT INTO anagrafiche.clienti (
        soggetto_ruolo_id,
        istanza_utility_id,
        stato_cliente_id,
        data_attivazione,
        billing_account_id,
        codice_cliente_importato,
        iva_id,
        pdp_id,
        utility_id
    )
    SELECT
        sr.soggetto_ruolo_id,
        iu.id,
        st.id,
        (dt.d0 + 1),
        ba.id,
        tc.cli2,
        iv.id,
        NULL::bigint,
        NULL::integer
    FROM tmp_sr_test sr,
         tmp_stato_attivo st,
         tmp_iva iv,
         tmp_date_base dt,
         tmp_codes tc,
         anagrafiche.istanze_utilities iu,
         anagrafiche.billing_account ba
    WHERE iu.codice = tc.iu2
      AND ba.codice = tc.ba2;
    $$,
    NULL,
    NULL,
    'T11 Blocco inserimento: per utility richiede_pdp=true il pdp_id e'' obbligatorio'
);

-- =========================================================
-- 4) Caso KO: PDP presente ma utility BA diversa dalla utility PDP
-- =========================================================
-- Chiude il cliente valido inserito al punto T09 per evitare overlap
CREATE TEMP TABLE tmp_subentro_pre_mismatch AS
SELECT script.fn_subentro_cliente(
    (SELECT id FROM tmp_pdp_gas),
    (SELECT d0 + 2 FROM tmp_date_base)
) AS cliente_chiuso_id;

SELECT throws_ok(
    $$
    INSERT INTO anagrafiche.clienti (
        soggetto_ruolo_id,
        istanza_utility_id,
        stato_cliente_id,
        data_attivazione,
        billing_account_id,
        codice_cliente_importato,
        iva_id,
        pdp_id,
        utility_id
    )
    SELECT
        sr.soggetto_ruolo_id,
        iu.id,
        st.id,
        (dt.d0 + 2),
        ba.id,
        tc.cli3,
        iv.id,
        p.id,
        NULL::integer
    FROM tmp_sr_test sr,
         tmp_stato_attivo st,
         tmp_iva iv,
         tmp_date_base dt,
         tmp_codes tc,
         anagrafiche.istanze_utilities iu,
         anagrafiche.billing_account ba,
         tmp_pdp_gas p
    WHERE iu.codice = tc.iu3
      AND ba.codice = tc.ba3;
    $$,
    NULL,
    NULL,
    'T12 Blocco inserimento: mismatch utility tra billing_account e PDP'
);

-- =========================================================
-- 5) Caso OK: utility richiede_pdp=false con cliente.pdp_id NULL
-- =========================================================
CREATE TEMP TABLE tmp_cli_ok_no_pdp AS
WITH ins AS (
    INSERT INTO anagrafiche.clienti (
        soggetto_ruolo_id,
        istanza_utility_id,
        stato_cliente_id,
        data_attivazione,
        billing_account_id,
        codice_cliente_importato,
        iva_id,
        pdp_id,
        utility_id
    )
    SELECT
        sr.soggetto_ruolo_id,
        iu.id,
        st.id,
        (dt.d0 + 3),
        ba.id,
        tc.cli4,
        iv.id,
        NULL::bigint,
        NULL::integer
    FROM tmp_sr_test sr,
         tmp_stato_attivo st,
         tmp_iva iv,
         tmp_date_base dt,
         tmp_codes tc,
         anagrafiche.istanze_utilities iu,
         anagrafiche.billing_account ba
    WHERE iu.codice = tc.iu4
      AND ba.codice = tc.ba4
    RETURNING id, utility_id, billing_account_id
)
SELECT *
FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_cli_ok_no_pdp),
    1,
    'T13 Inserimento cliente con utility richiede_pdp=false e pdp_id NULL: OK'
);

SELECT results_eq(
    $$
    SELECT c.utility_id::int
    FROM anagrafiche.clienti c
    WHERE c.codice_cliente_importato = (SELECT cli4 FROM tmp_codes)
    $$,
    $$
    SELECT ba.utility_id::int
    FROM anagrafiche.billing_account ba
    WHERE ba.codice = (SELECT ba4 FROM tmp_codes)
    $$,
    'T14 clienti.utility_id sincronizzato con billing_account.utility_id (caso no-PDP valido)'
);

SELECT * FROM finish();
