-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test policy dati societari (config.presenza_policy_enum; fino al 2026-10-09
--   config.dati_societari_policy_enum, brief-db-sesso-senza-default)
-- e trigger:
--   - anagrafiche.trgfn_dati_societari_guard_tipo_soggetto()
--   - anagrafiche.trgfn_soggetti_check_dati_societari_required()
--
-- Scenario:
--   - PR  → policy = NONE      → vietato avere dati_societari
--   - SP  → policy = OPTIONAL  → dati_societari ammessi ma non obbligatori
--   - SC  → policy = REQUIRED  → dati_societari obbligatori
--
-- Nota: per ogni soggetto viene creato almeno un contatto di soggetto
--       per rispettare i vincoli/trigger esistenti.
-- ------------------------------------------------------------
-- =========================================================
-- ============================================================================
-- rev 2026-08-18 — bonifica baseline. Qui c'era un «cleanup iniziale» che
-- cancellava i soggetti di prova delle corse precedenti: non funziona piu'
-- (fk_risorse_umane_soggetti e' RESTRICT e li trattiene), e il file moriva
-- alla riga 48 — ZERO asserzioni su 13.
-- Il file e' gia' BEGIN ... ROLLBACK: residui suoi non ne fa. Il rimedio e'
-- non collidere invece di cancellare — codici e identificativi fiscali unici
-- per corsa.
-- ============================================================================

BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(13);

-- ⚠️ fn(0), fn(1), fn(2) e non tre fn(): nella stessa istruzione la versione
--   senza argomenti tornerebbe sempre lo stesso valore, perche' fra una
--   chiamata e l'altra non c'e' nessun insert che lo occupi.
CREATE TEMP TABLE tmp_run_sfx AS
SELECT substr(md5(clock_timestamp()::text), 1, 8) AS sfx,
       dbops.fn_pgtap_piva_libera(0) AS piva_sc_ok,
       dbops.fn_pgtap_piva_libera(1) AS piva_sc_err,
       dbops.fn_pgtap_piva_libera(2) AS piva_sp,
       dbops.fn_pgtap_cf_libero()    AS cf_pr;
-- =========================================================
-- 0) Precondizioni base: stato, provincia, tipo_contatto
-- =========================================================
-- Stato (prendo il primo disponibile)
CREATE TEMP TABLE tmp_stato_test AS
SELECT id AS stato_id
FROM config.stati
ORDER BY id
LIMIT 1;
SELECT ok(
        (
            SELECT count(*)
            FROM tmp_stato_test
        ) = 1,
        'Esiste almeno uno stato in config.stati'
    );
-- Provincia (per dati_societari.id_prov_iscri_rea)
CREATE TEMP TABLE tmp_provincia_test AS
SELECT id AS provincia_id
FROM config.province
ORDER BY id
LIMIT 1;
SELECT ok(
        (
            SELECT count(*)
            FROM tmp_provincia_test
        ) = 1,
        'Esiste almeno una provincia in config.province'
    );
-- Tipo contatto (per creare contatto di soggetto)
CREATE TEMP TABLE tmp_tipo_contatto_test AS
SELECT id AS tipo_contatto_id
FROM config.tipi_contatti
ORDER BY id
LIMIT 1;
SELECT ok(
        (
            SELECT count(*)
            FROM tmp_tipo_contatto_test
        ) = 1,
        'Esiste almeno un tipo_contatto in config.tipi_contatti'
    );
-- =========================================================
-- 1) Recupero tipi_soggetto_dettaglio per PR / SP / SC
--    e verifica delle policy
-- =========================================================
CREATE TEMP TABLE tmp_tipi_soggetto_policy AS
SELECT id,
    codice_interno,
    dati_societari_policy
FROM config.tipi_soggetto_dettaglio
WHERE codice_interno IN ('PR', 'SP', 'SC');
SELECT is(
        (
            SELECT count(*)::int
            FROM tmp_tipi_soggetto_policy
        ),
        3,
        'Trovati esattamente 3 tipi_soggetto_dettaglio per codici interni PR/SP/SC'
    );
SELECT is(
        (
            SELECT dati_societari_policy::text
            FROM tmp_tipi_soggetto_policy
            WHERE codice_interno = 'PR'
        ),
        'NONE',
        'Tipo PR: dati_societari_policy = NONE'
    );
SELECT is(
        (
            SELECT dati_societari_policy::text
            FROM tmp_tipi_soggetto_policy
            WHERE codice_interno = 'SP'
        ),
        'OPTIONAL',
        'Tipo SP: dati_societari_policy = OPTIONAL'
    );
SELECT is(
        (
            SELECT dati_societari_policy::text
            FROM tmp_tipi_soggetto_policy
            WHERE codice_interno = 'SC'
        ),
        'REQUIRED',
        'Tipo SC: dati_societari_policy = REQUIRED'
    );
-- Tipi indirizzo obbligatori (per guard indirizzi_required deferrable)
CREATE TEMP TABLE tmp_tipo_ind_res AS
SELECT id AS tipo_indirizzo_id
FROM config.tipi_indirizzi
WHERE codice_interno = 'RES';
CREATE TEMP TABLE tmp_tipo_ind_domfisc AS
SELECT id AS tipo_indirizzo_id
FROM config.tipi_indirizzi
WHERE codice_interno = 'DOMFISC';
CREATE TEMP TABLE tmp_tipo_ind_sedeleg AS
SELECT id AS tipo_indirizzo_id
FROM config.tipi_indirizzi
WHERE codice_interno = 'SEDELEG';
-- Split in 3 temp più comode
CREATE TEMP TABLE tmp_tipo_pr AS
SELECT id AS tipo_soggetto_dettaglio_id
FROM tmp_tipi_soggetto_policy
WHERE codice_interno = 'PR';
CREATE TEMP TABLE tmp_tipo_sp AS
SELECT id AS tipo_soggetto_dettaglio_id
FROM tmp_tipi_soggetto_policy
WHERE codice_interno = 'SP';
CREATE TEMP TABLE tmp_tipo_sc AS
SELECT id AS tipo_soggetto_dettaglio_id
FROM tmp_tipi_soggetto_policy
WHERE codice_interno = 'SC';
-- =========================================================
-- 2) Soggetto PR (policy = NONE): vietato dati_societari
-- =========================================================
SELECT lives_ok(
        $$ -- Soggetto PR: solo codice_fiscale, nessuna P.IVA
        -- ⭐ Finestra differita: i guard di completezza su soggetti sono
        --   DEFERRABLE apposta (un soggetto e' una saga). Con IMMEDIATE
        --   scatterebbero sul primo insert, prima che sia completo.
        SET CONSTRAINTS ALL DEFERRED;
        INSERT INTO anagrafiche.soggetti (
                --id,
                codice,
                ragione_sociale,
                cognome,
                nome,
                -- un privato: il sesso e' obbligatorio (sesso_policy REQUIRED)
                sesso,
                stato_id,
                codice_fiscale,
                partita_iva,
                tipo_soggetto_dettaglio_id
            )
        VALUES (
                --uuid_generate_v7(),
                'TST-DSP-PR-001-' || (SELECT sfx FROM tmp_run_sfx),
                NULL,
                'Test PR',
                'Policy NONE',
                'M',
                (
                    SELECT stato_id
                    FROM tmp_stato_test
                ),
                (SELECT cf_pr FROM tmp_run_sfx),
                NULL,
                (
                    SELECT tipo_soggetto_dettaglio_id
                    FROM tmp_tipo_pr
                )
            );
-- Contatto di soggetto (necessario per vincoli esistenti)
INSERT INTO anagrafiche.contatti (
        tipo_contatto_id,
        soggetto_id,
        soggetto_ruolo_id,
        nominativo,
        email,
        telefono,
        cellulare,
        pec,
        note,
        is_default
    )
SELECT (
        SELECT tipo_contatto_id
        FROM tmp_tipo_contatto_test
    ),
    s.id,
    NULL,
    'Contatto soggetto PR',
    'pr.test@example.com',
    NULL,
    NULL,
    NULL,
    'PGTAP – contatto soggetto PR',
    TRUE
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-DSP-PR-001-' || (SELECT sfx FROM tmp_run_sfx);
INSERT INTO anagrafiche.indirizzi_soggetti (
        soggetto_id,
        tipo_indirizzo_id,
        indirizzo_libero,
        stato_id,
        locality,
        postal_box,
        administrative_area
    )
SELECT s.id,
    (
        SELECT tipo_indirizzo_id
        FROM tmp_tipo_ind_res
    ),
    'Via Test PR RES',
    (
        SELECT stato_id
        FROM tmp_stato_test
    ),
    'Test City',
    '00100',
    'TS'
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-DSP-PR-001-' || (SELECT sfx FROM tmp_run_sfx);
INSERT INTO anagrafiche.indirizzi_soggetti (
        soggetto_id,
        tipo_indirizzo_id,
        indirizzo_libero,
        stato_id,
        locality,
        postal_box,
        administrative_area
    )
SELECT s.id,
    (
        SELECT tipo_indirizzo_id
        FROM tmp_tipo_ind_domfisc
    ),
    'Via Test PR DOMFISC',
    (
        SELECT stato_id
        FROM tmp_stato_test
    ),
    'Test City',
    '00100',
    'TS'
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-DSP-PR-001-' || (SELECT sfx FROM tmp_run_sfx);
        -- Saga completa: qui i guard verificano davvero.
        SET CONSTRAINTS ALL IMMEDIATE;
$$,
'Creazione soggetto PR + contatto: OK (policy NONE, senza dati_societari)'
);
-- Tentativo di inserire dati_societari per soggetto PR: deve fallire
SELECT throws_ok(
        $$
        INSERT INTO anagrafiche.dati_societari (
                soggetto_id,
                capitale_sociale,
                id_prov_iscri_rea,
                iscrizione_rea,
                socio_unico,
                liquidazione,
                destinatario_fe,
                pec_fatturazione,
                codice_sdi,
                data_costituzione
            )
        SELECT s.id,
            1000.00,
            (
                SELECT provincia_id
                FROM tmp_provincia_test
            ),
            'PRX-REA-001-' || (SELECT sfx FROM tmp_run_sfx),
            'SU',
            'LN',
            'XXXXXXX001',
            NULL,
            NULL,
            CURRENT_DATE
        FROM anagrafiche.soggetti s
        WHERE s.codice = 'TST-DSP-PR-001-' || (SELECT sfx FROM tmp_run_sfx);
$$,
NULL,
'Soggetto PR (policy NONE): inserimento dati_societari non ammesso'
);
-- =========================================================
-- 3) Soggetto SP (policy = OPTIONAL):
--    - senza dati_societari: commit OK
--    - con dati_societari: commit OK
-- =========================================================
-- 3.a) Senza dati_societari
SELECT lives_ok(
        $$
        -- ⭐ Finestra differita: i guard di completezza su soggetti sono
        --   DEFERRABLE apposta (un soggetto e' una saga). Con IMMEDIATE
        --   scatterebbero sul primo insert, prima che sia completo.
        SET CONSTRAINTS ALL DEFERRED;
        INSERT INTO anagrafiche.soggetti (
                --id,
                codice,
                ragione_sociale,
                cognome,
                nome,
                stato_id,
                codice_fiscale,
                partita_iva,
                tipo_soggetto_dettaglio_id
            )
        VALUES (
                --uuid_generate_v7(),
                'TST-DSP-SP-001-' || (SELECT sfx FROM tmp_run_sfx),
                'Azienda SP OPTIONAL',
                NULL,
                NULL,
                (
                    SELECT stato_id
                    FROM tmp_stato_test
                ),
                (SELECT piva_sp FROM tmp_run_sfx),
                (SELECT piva_sp FROM tmp_run_sfx),
                (
                    SELECT tipo_soggetto_dettaglio_id
                    FROM tmp_tipo_sp
                )
            );
INSERT INTO anagrafiche.contatti (
        tipo_contatto_id,
        soggetto_id,
        soggetto_ruolo_id,
        nominativo,
        email,
        telefono,
        cellulare,
        pec,
        note,
        is_default
    )
SELECT (
        SELECT tipo_contatto_id
        FROM tmp_tipo_contatto_test
    ),
    s.id,
    NULL,
    'Contatto soggetto SP',
    'sp.test@example.com',
    NULL,
    NULL,
    NULL,
    'PGTAP – contatto soggetto SP',
    TRUE
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-DSP-SP-001-' || (SELECT sfx FROM tmp_run_sfx);
INSERT INTO anagrafiche.indirizzi_soggetti (
        soggetto_id,
        tipo_indirizzo_id,
        indirizzo_libero,
        stato_id,
        locality,
        postal_box,
        administrative_area
    )
SELECT s.id,
    (
        SELECT tipo_indirizzo_id
        FROM tmp_tipo_ind_sedeleg
    ),
    'Via Test SP SEDELEG',
    (
        SELECT stato_id
        FROM tmp_stato_test
    ),
    'Test City',
    '00100',
    'TS'
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-DSP-SP-001-' || (SELECT sfx FROM tmp_run_sfx);
        -- Saga completa: qui i guard verificano davvero.
        SET CONSTRAINTS ALL IMMEDIATE;
$$,
'Soggetto SP OPTIONAL senza dati_societari: insert OK'
);
-- 3.b) Inserimento successivo di dati_societari: deve essere ammesso
SELECT lives_ok(
        $$
        -- ⭐ Finestra differita: i guard di completezza su soggetti sono
        --   DEFERRABLE apposta (un soggetto e' una saga). Con IMMEDIATE
        --   scatterebbero sul primo insert, prima che sia completo.
        SET CONSTRAINTS ALL DEFERRED;
        INSERT INTO anagrafiche.dati_societari (
                soggetto_id,
                capitale_sociale,
                id_prov_iscri_rea,
                iscrizione_rea,
                socio_unico,
                liquidazione,
                destinatario_fe,
                pec_fatturazione,
                codice_sdi,
                data_costituzione
            )
        SELECT s.id,
            50000.00,
            (
                SELECT provincia_id
                FROM tmp_provincia_test
            ),
            'SPR-REA-001-' || (SELECT sfx FROM tmp_run_sfx),
            'SM',
            'LN',
            'XXXXXXX002',
            -- ⚠️ PEC e codice SDI hanno un UNIQUE loro (uq_ds_pec_fatt,
            --   uq_ds_codice_sdi): i valori fissi sono bruciati da un residuo.
            'fatt.sp1.' || (SELECT sfx FROM tmp_run_sfx) || '@example.com',
            'SP' || upper(substr((SELECT sfx FROM tmp_run_sfx), 1, 5)),
            CURRENT_DATE
        FROM anagrafiche.soggetti s
        WHERE s.codice = 'TST-DSP-SP-001-' || (SELECT sfx FROM tmp_run_sfx);
        -- Saga completa: qui i guard verificano davvero.
        SET CONSTRAINTS ALL IMMEDIATE;
$$,
'Soggetto SP OPTIONAL con dati_societari: insert OK'
);
-- =========================================================
-- 4) Soggetto SC (policy = REQUIRED):
--    - senza dati_societari: deve fallire quando forziamo i constraint
--    - con dati_societari: OK
-- =========================================================
-- 4.a) Tentativo SENZA dati_societari → deve fallire quando forziamo i constraint
SELECT throws_ok(
        $$
        INSERT INTO anagrafiche.soggetti (
                --id,
                codice,
                ragione_sociale,
                cognome,
                nome,
                stato_id,
                codice_fiscale,
                partita_iva,
                tipo_soggetto_dettaglio_id
            )
        VALUES (
                --uuid_generate_v7(),
                'TST-DSP-SC-ERR-' || (SELECT sfx FROM tmp_run_sfx),
                'Azienda SC REQUIRED senza dati',
                NULL,
                NULL,
                (
                    SELECT stato_id
                    FROM tmp_stato_test
                ),
                (SELECT piva_sc_err FROM tmp_run_sfx),
                (SELECT piva_sc_err FROM tmp_run_sfx),
                (
                    SELECT tipo_soggetto_dettaglio_id
                    FROM tmp_tipo_sc
                )
            );
INSERT INTO anagrafiche.contatti (
        tipo_contatto_id,
        soggetto_id,
        soggetto_ruolo_id,
        nominativo,
        email,
        telefono,
        cellulare,
        pec,
        note,
        is_default
    )
SELECT (
        SELECT tipo_contatto_id
        FROM tmp_tipo_contatto_test
    ),
    s.id,
    NULL,
    'Contatto soggetto SC (err)',
    'sc.err@example.com',
    NULL,
    NULL,
    NULL,
    'PGTAP – contatto soggetto SC senza dati_societari',
    TRUE
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-DSP-SC-ERR-' || (SELECT sfx FROM tmp_run_sfx);
INSERT INTO anagrafiche.indirizzi_soggetti (
        soggetto_id,
        tipo_indirizzo_id,
        indirizzo_libero,
        stato_id,
        locality,
        postal_box,
        administrative_area
    )
SELECT s.id,
    (
        SELECT tipo_indirizzo_id
        FROM tmp_tipo_ind_sedeleg
    ),
    'Via Test SC-ERR SEDELEG',
    (
        SELECT stato_id
        FROM tmp_stato_test
    ),
    'Test City',
    '00100',
    'TS'
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-DSP-SC-ERR-' || (SELECT sfx FROM tmp_run_sfx);
-- Forzo l'esecuzione dei constraint deferrable
SET CONSTRAINTS ALL IMMEDIATE;
$$,
NULL,
'Soggetto SC REQUIRED senza dati_societari: constraint deve fallire'
);
-- 4.b) Caso corretto: SC REQUIRED + dati_societari
SELECT lives_ok(
        $$
        -- ⭐ Finestra differita: i guard di completezza su soggetti sono
        --   DEFERRABLE apposta (un soggetto e' una saga). Con IMMEDIATE
        --   scatterebbero sul primo insert, prima che sia completo.
        SET CONSTRAINTS ALL DEFERRED;
        INSERT INTO anagrafiche.soggetti (
                --id,
                codice,
                ragione_sociale,
                cognome,
                nome,
                stato_id,
                codice_fiscale,
                partita_iva,
                tipo_soggetto_dettaglio_id
            )
        VALUES (
                --uuid_generate_v7(),
                'TST-DSP-SC-OK-' || (SELECT sfx FROM tmp_run_sfx),
                'Azienda SC REQUIRED con dati',
                NULL,
                NULL,
                (
                    SELECT stato_id
                    FROM tmp_stato_test
                ),
                (SELECT piva_sc_ok FROM tmp_run_sfx),
                (SELECT piva_sc_ok FROM tmp_run_sfx),
                (
                    SELECT tipo_soggetto_dettaglio_id
                    FROM tmp_tipo_sc
                )
            );
INSERT INTO anagrafiche.contatti (
        tipo_contatto_id,
        soggetto_id,
        soggetto_ruolo_id,
        nominativo,
        email,
        telefono,
        cellulare,
        pec,
        note,
        is_default
    )
SELECT (
        SELECT tipo_contatto_id
        FROM tmp_tipo_contatto_test
    ),
    s.id,
    NULL,
    'Contatto soggetto SC (ok)',
    'sc.ok@example.com',
    NULL,
    NULL,
    NULL,
    'PGTAP – contatto soggetto SC con dati_societari',
    TRUE
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-DSP-SC-OK-' || (SELECT sfx FROM tmp_run_sfx);
INSERT INTO anagrafiche.dati_societari (
        soggetto_id,
        capitale_sociale,
        id_prov_iscri_rea,
        iscrizione_rea,
        socio_unico,
        liquidazione,
        destinatario_fe,
        pec_fatturazione,
        codice_sdi,
        data_costituzione
    )
SELECT s.id,
    100000.00,
    (
        SELECT provincia_id
        FROM tmp_provincia_test
    ),
    'SCX-REA-OK-' || (SELECT sfx FROM tmp_run_sfx),
    'SM',
    'LN',
    'XXXXXXX003',
    'fatt.sc1.' || (SELECT sfx FROM tmp_run_sfx) || '@example.com',
    'SCCO' || upper(substr((SELECT sfx FROM tmp_run_sfx), 1, 3)),
    CURRENT_DATE
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-DSP-SC-OK-' || (SELECT sfx FROM tmp_run_sfx);
INSERT INTO anagrafiche.indirizzi_soggetti (
        soggetto_id,
        tipo_indirizzo_id,
        indirizzo_libero,
        stato_id,
        locality,
        postal_box,
        administrative_area
    )
SELECT s.id,
    (
        SELECT tipo_indirizzo_id
        FROM tmp_tipo_ind_sedeleg
    ),
    'Via Test SC SEDELEG',
    (
        SELECT stato_id
        FROM tmp_stato_test
    ),
    'Test City',
    '00100',
    'TS'
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-DSP-SC-OK-' || (SELECT sfx FROM tmp_run_sfx);
-- Forzo l'esecuzione dei constraint deferrable per essere sicuro
SET CONSTRAINTS ALL IMMEDIATE;
        -- Saga completa: qui i guard verificano davvero.
        SET CONSTRAINTS ALL IMMEDIATE;
$$,
'Soggetto SC REQUIRED con dati_societari: tutto OK (constraint passato)'
);
-- Fine test
SELECT *
FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
