-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test policy dati societari (config.dati_societari_policy_enum)
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
-- Cleanup iniziale: rimuovo eventuali dati di test preesistenti
-- per evitare errori di chiave duplicata su anagrafiche.soggetti.codice
-- =========================================================
DO $$
DECLARE l_codici text [] := ARRAY [
    'TST-DSP-PR-001','TST-DSP-SP-001','TST-DSP-SC-ERR','TST-DSP-SC-OK'
  ];
BEGIN
DELETE FROM anagrafiche.dati_societari ds
WHERE ds.soggetto_id IN (
        SELECT s.id
        FROM anagrafiche.soggetti s
        WHERE s.codice = ANY(l_codici)
    );
DELETE FROM anagrafiche.indirizzi_soggetti i
WHERE i.soggetto_id IN (
        SELECT s.id
        FROM anagrafiche.soggetti s
        WHERE s.codice = ANY(l_codici)
    );
DELETE FROM anagrafiche.contatti c
WHERE c.soggetto_id IN (
        SELECT s.id
        FROM anagrafiche.soggetti s
        WHERE s.codice = ANY(l_codici)
    );
DELETE FROM anagrafiche.soggetti s
WHERE s.codice = ANY(l_codici);
END;
$$;
SELECT plan(13);
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
                'TST-DSP-PR-001',
                NULL,
                'Test PR',
                'Policy NONE',
                (
                    SELECT stato_id
                    FROM tmp_stato_test
                ),
                'LLLNGL80A01G482C',
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
WHERE s.codice = 'TST-DSP-PR-001';
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
WHERE s.codice = 'TST-DSP-PR-001';
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
WHERE s.codice = 'TST-DSP-PR-001';
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
            'PRX-REA-001',
            'SU',
            'LN',
            'XXXXXXX001',
            NULL,
            NULL,
            CURRENT_DATE
        FROM anagrafiche.soggetti s
        WHERE s.codice = 'TST-DSP-PR-001';
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
                'TST-DSP-SP-001',
                'Azienda SP OPTIONAL',
                NULL,
                NULL,
                (
                    SELECT stato_id
                    FROM tmp_stato_test
                ),
                '18413120074',
                '18413120074',
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
WHERE s.codice = 'TST-DSP-SP-001';
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
WHERE s.codice = 'TST-DSP-SP-001';
$$,
'Soggetto SP OPTIONAL senza dati_societari: insert OK'
);
-- 3.b) Inserimento successivo di dati_societari: deve essere ammesso
SELECT lives_ok(
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
            50000.00,
            (
                SELECT provincia_id
                FROM tmp_provincia_test
            ),
            'SPR-REA-001',
            'SM',
            'LN',
            'XXXXXXX002',
            'fatturazione.sp1@example.com',
            'SPCOX12345',
            CURRENT_DATE
        FROM anagrafiche.soggetti s
        WHERE s.codice = 'TST-DSP-SP-001';
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
                'TST-DSP-SC-ERR',
                'Azienda SC REQUIRED senza dati',
                NULL,
                NULL,
                (
                    SELECT stato_id
                    FROM tmp_stato_test
                ),
                '22439650049',
                '22439650049',
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
WHERE s.codice = 'TST-DSP-SC-ERR';
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
WHERE s.codice = 'TST-DSP-SC-ERR';
-- Forzo l'esecuzione dei constraint deferrable
SET CONSTRAINTS ALL IMMEDIATE;
$$,
NULL,
'Soggetto SC REQUIRED senza dati_societari: constraint deve fallire'
);
-- 4.b) Caso corretto: SC REQUIRED + dati_societari
SELECT lives_ok(
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
                'TST-DSP-SC-OK',
                'Azienda SC REQUIRED con dati',
                NULL,
                NULL,
                (
                    SELECT stato_id
                    FROM tmp_stato_test
                ),
                '13841460473',
                '13841460473',
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
WHERE s.codice = 'TST-DSP-SC-OK';
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
    'SCX-REA-OK',
    'SM',
    'LN',
    'XXXXXXX003',
    'fatturazione.sc1@example.com',
    'SCCOX67890',
    CURRENT_DATE
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-DSP-SC-OK';
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
WHERE s.codice = 'TST-DSP-SC-OK';
-- Forzo l'esecuzione dei constraint deferrable per essere sicuro
SET CONSTRAINTS ALL IMMEDIATE;
$$,
'Soggetto SC REQUIRED con dati_societari: tutto OK (constraint passato)'
);
-- Fine test
SELECT *
FROM finish();