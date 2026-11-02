-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
--  T06) Costruito il soggetto di test
--  T07) Costruito un PDP GAS con indirizzo valorizzato
--  T08) Create 4 istanze di test
--  T09) Inserimento cliente GAS con PDP valorizzato (OK)
--  T10) Sync utility cliente <- billing account (caso GAS)
--  T11) Blocco: utility richiede_pdp=true ma pdp_id NULL
--  T12) Blocco: mismatch utility tra billing account e PDP
--  T13) Inserimento cliente con utility richiede_pdp=false e pdp_id NULL (OK)
--  T14) Sync utility cliente <- billing account (caso no-PDP)
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

-- ⛔ 2026-09-23: soggetto e PDP erano dati di QUESTA macchina — il soggetto
--   per una partita IVA di dbdev, il PDP «il primo GAS con un indirizzo». Su
--   un database ricostruito dai changelog non ci sono, e la fixture moriva su
--   «Non e' stato fornito un valore per pdp_id». Ora si COSTRUISCONO: un
--   soggetto persona giuridica col suo ruolo CL (indirizzi di ruolo compresi)
--   e un PDP GAS nuovo, su un indirizzo suo.
CREATE TEMP TABLE tmp_soggetto_test AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Cliente PDP policy') AS id;

SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto_test WHERE id IS NOT NULL),
    1,
    'T06 Costruito il soggetto di test'
);

CREATE TEMP TABLE tmp_sr_test AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(s.id, 'CL') AS soggetto_ruolo_id
FROM tmp_soggetto_test s;

CREATE TEMP TABLE tmp_pdp_gas AS
SELECT p.pdp_id AS id,
       p.indirizzo_dettaglio_id,
       p.utility_id
FROM dbops.fn_pgtap_crea_pdp('GAS') p;

SELECT is(
    (SELECT count(*)::int FROM tmp_pdp_gas WHERE indirizzo_dettaglio_id IS NOT NULL),
    1,
    'T07 Costruito un PDP GAS con indirizzo valorizzato'
);

-- Categoria cliente: `billing_account.categoria_cliente_id` e' diventata
-- NOT NULL dopo la scrittura di questo file. Si prende per CODICE INTERNO e non
-- con un LIMIT 1: un `LIMIT` senza `ORDER BY` non verifica, scommette — e qui
-- fra le categorie ci sono anche residui di smoke test disattivati.
CREATE TEMP TABLE tmp_categoria_cliente AS
SELECT id FROM anagrafiche.categorie_clienti WHERE codice_interno = 'STANDARD';

-- Data base per evitare conflitti con dati gia' presenti nel DB di test
CREATE TEMP TABLE tmp_date_base AS
SELECT (script.fn_data_operativa() + 30)::date AS d0;

-- Chiusura preventiva eventuale cliente attivo sul PDP alla data test
CREATE TEMP TABLE tmp_subentro_pre AS
SELECT script.fn_subentro_cliente(
    (SELECT id FROM tmp_pdp_gas),
    (SELECT d0 FROM tmp_date_base)
) AS cliente_chiuso_id;

-- =========================================================
-- 1) Dati di test (4 istanze + 4 billing account)
-- =========================================================
-- ⭐ FINESTRA DIFFERITA. Un'istanza utility non e' un INSERT, e' una SAGA:
--   `trg_istanze_utilities_z90_require_utility_dichiarata_ins` e' un
--   CONSTRAINT TRIGGER DEFERRABLE INITIALLY DEFERRED che al COMMIT pretende
--   almeno un satellite (billing_account, istanze_dati_precontrattuali o
--   cliente) — un'istanza senza satellite non e' uno stato legale del modello.
--   Il preambolo obbligatorio (SET CONSTRAINTS ALL IMMEDIATE) lo fa scattare sul
--   PRIMO insert, cioe' prima che i billing account qui sotto possano esistere:
--   e' li' che questo file moriva, con ZERO asserzioni eseguite.
--   Si apre la finestra, si costruiscono le quattro istanze CON i loro quattro
--   BA, e si RICHIUDE: la verifica non si perde, si sposta dove il modello la
--   vuole.
SET CONSTRAINTS ALL DEFERRED;

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
        codice,
        categoria_cliente_id
    )
    SELECT iu1.id, sr.soggetto_ruolo_id, ug.id, tc.ba1, cc.id
    FROM anagrafiche.istanze_utilities iu1, tmp_sr_test sr, tmp_utility_gas ug, tmp_codes tc,
         tmp_categoria_cliente cc
    WHERE iu1.codice = tc.iu1
    UNION ALL
    SELECT iu2.id, sr.soggetto_ruolo_id, ug.id, tc.ba2, cc.id
    FROM anagrafiche.istanze_utilities iu2, tmp_sr_test sr, tmp_utility_gas ug, tmp_codes tc,
         tmp_categoria_cliente cc
    WHERE iu2.codice = tc.iu2
    UNION ALL
    SELECT iu3.id, sr.soggetto_ruolo_id, unp.id, tc.ba3, cc.id
    FROM anagrafiche.istanze_utilities iu3, tmp_sr_test sr, tmp_utility_no_pdp unp, tmp_codes tc,
         tmp_categoria_cliente cc
    WHERE iu3.codice = tc.iu3
    UNION ALL
    SELECT iu4.id, sr.soggetto_ruolo_id, unp.id, tc.ba4, cc.id
    FROM anagrafiche.istanze_utilities iu4, tmp_sr_test sr, tmp_utility_no_pdp unp, tmp_codes tc,
         tmp_categoria_cliente cc
    WHERE iu4.codice = tc.iu4
    RETURNING id, codice, utility_id, istanza_utility_id
)
SELECT *
FROM ins;

-- Saga completa: ogni istanza ha il suo billing account, il guard differito
-- scatta QUI e le trova finite.
SET CONSTRAINTS ALL IMMEDIATE;

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
        -- ⚠️ rev 2026-08-29: via `iva_id` — non esiste piu' su
        --   anagrafiche.clienti (changeSet 20260829-22). tmp_iva resta:
        --   la sua asserzione fa parte del plan.
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
        p.id,
        NULL::integer
    FROM tmp_sr_test sr,
         tmp_stato_attivo st,
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
        -- ⚠️ rev 2026-08-29: via `iva_id` — non esiste piu' su
        --   anagrafiche.clienti (changeSet 20260829-22). tmp_iva resta:
        --   la sua asserzione fa parte del plan.
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
        NULL::bigint,
        NULL::integer
    FROM tmp_sr_test sr,
         tmp_stato_attivo st,
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
        -- ⚠️ rev 2026-08-29: via `iva_id` — non esiste piu' su
        --   anagrafiche.clienti (changeSet 20260829-22). tmp_iva resta:
        --   la sua asserzione fa parte del plan.
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
        p.id,
        NULL::integer
    FROM tmp_sr_test sr,
         tmp_stato_attivo st,
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
        -- ⚠️ rev 2026-08-29: via `iva_id` — non esiste piu' su
        --   anagrafiche.clienti (changeSet 20260829-22). tmp_iva resta:
        --   la sua asserzione fa parte del plan.
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
        NULL::bigint,
        NULL::integer
    FROM tmp_sr_test sr,
         tmp_stato_attivo st,
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

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
