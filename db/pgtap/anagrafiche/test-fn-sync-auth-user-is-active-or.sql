-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.fn_sync_auth_user_is_active semantica OR
-- Riferimento: migration 20260420-10 (§9 guida multi-face v2.0).
--
-- Semantica attesa post 20-04-2026:
--   auth_user.is_active = true SE ESISTE almeno una identita con
--     - attivo = true
--     - script.fn_data_operativa() in [valido_dal, valido_al]
--     - soggetto parent attivo
--   Altrimenti auth_user.is_active = false.
--   ⚠️ Rev 2026-10-02 (brief-db-be-fe-area-accessi R-DB-1): fino a quel
--   giorno c'era anche «ruolo_applicativo != DISABILITATO». DISABILITATO non
--   e' piu' un tipo di veste: la tabella viva lo rifiuta, e «spenta» si legge
--   solo da attivo. I test 4 e 5 sono stati riscritti su questo.
--
-- Strategia: creo auth_user vuoti, aggiungo identita con varie
-- combinazioni, chiamo fn_sync_auth_user_is_active esplicitamente,
-- verifico il valore risultante di auth_user.is_active.
-- Nota: i trigger sync automatici scattano sugli INSERT/UPDATE
-- di identita_digitali, quindi il chiamante esplicito serve solo
-- come assert esplicito dello stato coerente.
--
-- Indice test (1..6):
--    1. Precondizione: SR CL + 5 auth_user pool, soggetti attivi
--    2. User con 1 identita CLIENTE_PORTALE attiva -> is_active=true
--    3. User con 2 identita attive (CLIENTE_PORTALE + SHOP_CUSTOMER)
--       -> is_active=true
--    4. Una veste DISABILITATO non entra piu' nella tabella viva:
--       E_RUOLO_APPLICATIVO_RITIRATO (rev 2026-10-02)
--    5. User con 1 identita CLIENTE_PORTALE attiva + 1 SHOP_CUSTOMER
--       spenta -> is_active=true (OR: basta la veste utilizzabile)
--    6. User con 1 identita CLIENTE_PORTALE ma attivo=false
--       -> is_active=false (nessuna identita utilizzabile)
--
-- Vincoli di test: fixture 5 SR CL **liberi** (senza identita attive e
-- con soggetto attivo) per evitare collisioni con l'indice parziale
-- uq_identita_digitali_sr_ruolo_attivo. Skip-safe se ne trova <5.
--
-- BEGIN; + rollback implicito.
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

SELECT plan(6);

-- =========================================================
-- 1) Precondizione: 5 SR CL liberi + 5 auth_user
--    NOTA: anagrafiche.clienti NON ha UNIQUE su soggetto_ruolo_id
--    (un SR-CL puo' avere N clienti, uno per istanza utility).
--    Il JOIN clienti moltiplica i SR -> CTE con DISTINCT garantisce
--    SR univoci prima del row_number().
-- =========================================================
CREATE TEMP TABLE _t_sr_cl AS
WITH sr_liberi AS (
    SELECT DISTINCT sr.id AS sr_id
      FROM anagrafiche.clienti        c
      JOIN anagrafiche.soggetti_ruoli sr ON sr.id = c.soggetto_ruolo_id
      JOIN anagrafiche.soggetti       s  ON s.id = sr.soggetto_id
     WHERE s.attivo = true
       AND NOT EXISTS (
           SELECT 1
             FROM anagrafiche.identita_digitali id
            WHERE id.soggetto_ruolo_id = sr.id
              AND id.attivo = true
       )
)
SELECT sr_id,
       row_number() OVER (ORDER BY sr_id) AS rn
  FROM sr_liberi
 ORDER BY sr_id
 LIMIT 5;


CREATE TEMP TABLE _t_au_pool (idx int, auth_user_id int);
DO $$
DECLARE
    v_i int;
    v_id int;
BEGIN
    FOR v_i IN 1..5 LOOP
        INSERT INTO django.auth_user (
            username, password, is_active, is_staff, is_superuser,
            first_name, last_name, email, date_joined
        )
        VALUES (
            '_pgtap_sync_or_' || v_i || '_' || substring(md5(clock_timestamp()::text) from 1 for 6),
            '!', false, false, false, '', '', '', now()
        )
        RETURNING id INTO v_id;
        INSERT INTO _t_au_pool (idx, auth_user_id) VALUES (v_i, v_id);
    END LOOP;
END
$$;

SELECT ok(
    (SELECT count(*) FROM _t_sr_cl)   = 5
    AND (SELECT count(*) FROM _t_au_pool) = 5,
    '1. Precondizioni: 5 SR CL liberi + 5 auth_user pool'
);

-- =========================================================
-- Tutti gli INSERT sono gate'd su 'count(_t_sr_cl) = 5' via WHERE
-- clause: se la fixture non e' completa, nessun INSERT viene fatto
-- e i test 2-6 skippano uniformemente.
-- =========================================================

-- =========================================================
-- 2) User con 1 identita CLIENTE_PORTALE attiva -> is_active=true
-- =========================================================
-- La veste dal BB anagrafiche.fn_crea_veste_portale (rev 2026-10-18,
-- brief-db-processi-accensione-per-ambiente 2b-1 lotto 6).
DO $veste$
BEGIN
    PERFORM 1 FROM (
        SELECT anagrafiche.fn_crea_veste_portale((SELECT auth_user_id FROM _t_au_pool WHERE idx = 1), (SELECT sr_id FROM _t_sr_cl WHERE rn = 1), 'CLIENTE_PORTALE'::config.ruolo_applicativo, true) WHERE (SELECT count(*) FROM _t_sr_cl) = 5
    ) AS v;
END
$veste$;

SELECT anagrafiche.fn_sync_auth_user_is_active(
    (SELECT auth_user_id FROM _t_au_pool WHERE idx = 1)
)
 WHERE (SELECT count(*) FROM _t_sr_cl) = 5;

SELECT CASE
    WHEN (SELECT count(*) FROM _t_sr_cl) = 5 THEN
        is(
            (SELECT is_active FROM django.auth_user
              WHERE id = (SELECT auth_user_id FROM _t_au_pool WHERE idx = 1)),
            true,
            '2. 1 identita CLIENTE_PORTALE attiva -> is_active=true'
        )
    ELSE skip('fixture insufficiente (<5 SR CL liberi): test 2 skippato', 1)
END;

-- =========================================================
-- 3) User con 2 identita attive (CLIENTE_PORTALE + SHOP_CUSTOMER)
--    -> is_active=true (entrambe concorrono via OR)
-- =========================================================
-- La veste dal BB anagrafiche.fn_crea_veste_portale (rev 2026-10-18,
-- brief-db-processi-accensione-per-ambiente 2b-1 lotto 6).
DO $veste$
BEGIN
    PERFORM 1 FROM (
        SELECT anagrafiche.fn_crea_veste_portale((SELECT auth_user_id FROM _t_au_pool WHERE idx = 2), (SELECT sr_id FROM _t_sr_cl WHERE rn = 2), 'CLIENTE_PORTALE'::config.ruolo_applicativo, true) WHERE (SELECT count(*) FROM _t_sr_cl) = 5
        UNION ALL
        SELECT anagrafiche.fn_crea_veste_portale((SELECT auth_user_id FROM _t_au_pool WHERE idx = 2), (SELECT sr_id FROM _t_sr_cl WHERE rn = 2), 'SHOP_CUSTOMER'::config.ruolo_applicativo, true) WHERE (SELECT count(*) FROM _t_sr_cl) = 5
    ) AS v;
END
$veste$;

SELECT anagrafiche.fn_sync_auth_user_is_active(
    (SELECT auth_user_id FROM _t_au_pool WHERE idx = 2)
)
 WHERE (SELECT count(*) FROM _t_sr_cl) = 5;

SELECT CASE
    WHEN (SELECT count(*) FROM _t_sr_cl) = 5 THEN
        is(
            (SELECT is_active FROM django.auth_user
              WHERE id = (SELECT auth_user_id FROM _t_au_pool WHERE idx = 2)),
            true,
            '3. 2 identita attive (CLIENTE_PORTALE + SHOP_CUSTOMER) -> is_active=true'
        )
    ELSE skip('fixture insufficiente: test 3 skippato', 1)
END;

-- =========================================================
-- 4) Una veste DISABILITATO non entra nella tabella viva
--    (rev 2026-10-02, R-DB-1): il guard di coerenza parla prima
--    del CHECK chk_identita_digitali_ruolo_non_ritirato, col
--    codice che dice il rimedio. Il codice viaggia nel canale
--    CONSTRAINT_NAME dell'eccezione P0001.
-- =========================================================
CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

SELECT CASE
    WHEN (SELECT count(*) FROM _t_sr_cl) = 5 THEN
        is(
            pg_temp.codice_errore(format(
                $$INSERT INTO anagrafiche.identita_digitali
                      (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
                  VALUES (%s, %s, 'DISABILITATO'::config.ruolo_applicativo, false)$$,
                (SELECT sr_id FROM _t_sr_cl WHERE rn = 3),
                (SELECT auth_user_id FROM _t_au_pool WHERE idx = 3))),
            'E_RUOLO_APPLICATIVO_RITIRATO',
            '4. Una veste DISABILITATO e'' rifiutata: E_RUOLO_APPLICATIVO_RITIRATO'
        )
    ELSE skip('fixture insufficiente: test 4 skippato', 1)
END;

-- =========================================================
-- 5) User con CLIENTE_PORTALE attiva + SHOP_CUSTOMER spenta
--    -> is_active=true (OR: basta la veste utilizzabile)
-- =========================================================
-- La veste dal BB anagrafiche.fn_crea_veste_portale (rev 2026-10-18,
-- brief-db-processi-accensione-per-ambiente 2b-1 lotto 6).
DO $veste$
BEGIN
    PERFORM 1 FROM (
        SELECT anagrafiche.fn_crea_veste_portale((SELECT auth_user_id FROM _t_au_pool WHERE idx = 4), (SELECT sr_id FROM _t_sr_cl WHERE rn = 4), 'CLIENTE_PORTALE'::config.ruolo_applicativo, true) WHERE (SELECT count(*) FROM _t_sr_cl) = 5
        UNION ALL
        SELECT anagrafiche.fn_crea_veste_portale((SELECT auth_user_id FROM _t_au_pool WHERE idx = 4), (SELECT sr_id FROM _t_sr_cl WHERE rn = 4), 'SHOP_CUSTOMER'::config.ruolo_applicativo, false) WHERE (SELECT count(*) FROM _t_sr_cl) = 5
    ) AS v;
END
$veste$;

SELECT anagrafiche.fn_sync_auth_user_is_active(
    (SELECT auth_user_id FROM _t_au_pool WHERE idx = 4)
)
 WHERE (SELECT count(*) FROM _t_sr_cl) = 5;

SELECT CASE
    WHEN (SELECT count(*) FROM _t_sr_cl) = 5 THEN
        is(
            (SELECT is_active FROM django.auth_user
              WHERE id = (SELECT auth_user_id FROM _t_au_pool WHERE idx = 4)),
            true,
            '5. CLIENTE_PORTALE attiva + SHOP_CUSTOMER spenta -> is_active=true (OR)'
        )
    ELSE skip('fixture insufficiente: test 5 skippato', 1)
END;

-- =========================================================
-- 6) User con sola identita CLIENTE_PORTALE ma attivo=false
--    -> is_active=false (nessuna identita utilizzabile)
-- =========================================================
-- La veste dal BB anagrafiche.fn_crea_veste_portale (rev 2026-10-18,
-- brief-db-processi-accensione-per-ambiente 2b-1 lotto 6).
DO $veste$
BEGIN
    PERFORM 1 FROM (
        SELECT anagrafiche.fn_crea_veste_portale((SELECT auth_user_id FROM _t_au_pool WHERE idx = 5), (SELECT sr_id FROM _t_sr_cl WHERE rn = 5), 'CLIENTE_PORTALE'::config.ruolo_applicativo, false) WHERE (SELECT count(*) FROM _t_sr_cl) = 5
    ) AS v;
END
$veste$;

SELECT anagrafiche.fn_sync_auth_user_is_active(
    (SELECT auth_user_id FROM _t_au_pool WHERE idx = 5)
)
 WHERE (SELECT count(*) FROM _t_sr_cl) = 5;

SELECT CASE
    WHEN (SELECT count(*) FROM _t_sr_cl) = 5 THEN
        is(
            (SELECT is_active FROM django.auth_user
              WHERE id = (SELECT auth_user_id FROM _t_au_pool WHERE idx = 5)),
            false,
            '6. Sola identita CLIENTE_PORTALE attivo=false -> is_active=false'
        )
    ELSE skip('fixture insufficiente: test 6 skippato', 1)
END;

SELECT * FROM finish();
ROLLBACK;
