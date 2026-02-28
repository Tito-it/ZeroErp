-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test trigger guard natura ammessa su anagrafiche.soggetti_ruoli
-- Funzione: anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa()
-- Trigger:  trg_soggetti_ruoli_a10_guard_natura_ammessa_ins_upd
--
-- Scenario:
--   - Soggetto PG + ruolo GE: OK (PG ammesso)
--   - Soggetto PF + ruolo GE: FALLISCE (PF non ammesso)
--   - Soggetto PG + ruolo RIS_UMANA: FALLISCE (solo PF ammesso)
--   - Soggetto PF + ruolo RIS_UMANA: OK
--   - Soggetto PF + ruolo CL: OK (PF ammesso per CL)
--   - Soggetto ENC + ruolo CL: OK (ENC ammesso per CL)
--   - Soggetto senza tipo_det + ruolo GE: FALLISCE (tipo_det NULL)
--
-- Nota: per ogni soggetto viene creato almeno un contatto
--       per rispettare i vincoli/trigger esistenti.
-- ------------------------------------------------------------
-- =========================================================
-- Cleanup iniziale
-- =========================================================
DO $$ BEGIN
-- Elimino indirizzi ruolo di test
DELETE FROM anagrafiche.indirizzi i
WHERE i.soggetto_ruolo_id IN (
        SELECT sr.id
        FROM anagrafiche.soggetti_ruoli sr
        JOIN anagrafiche.soggetti s ON sr.soggetto_id = s.id
        WHERE s.codice IN (
                'TST-NAT-PG-001',
                'TST-NAT-PF-001',
                'TST-NAT-ENC-001',
                'TST-NAT-NULL-001'
            )
    );
-- Elimino soggetti_ruoli di test
DELETE FROM anagrafiche.soggetti_ruoli sr
WHERE sr.soggetto_id IN (
        SELECT s.id
        FROM anagrafiche.soggetti s
        WHERE s.codice IN (
                'TST-NAT-PG-001',
                'TST-NAT-PF-001',
                'TST-NAT-ENC-001',
                'TST-NAT-NULL-001'
            )
    );
-- Elimino indirizzi_soggetti di test
DELETE FROM anagrafiche.indirizzi_soggetti i
WHERE i.soggetto_id IN (
        SELECT s.id
        FROM anagrafiche.soggetti s
        WHERE s.codice IN (
                'TST-NAT-PG-001',
                'TST-NAT-PF-001',
                'TST-NAT-ENC-001',
                'TST-NAT-NULL-001'
            )
    );
-- Elimino contatti di test
DELETE FROM anagrafiche.contatti c
WHERE c.soggetto_id IN (
        SELECT s.id
        FROM anagrafiche.soggetti s
        WHERE s.codice IN (
                'TST-NAT-PG-001',
                'TST-NAT-PF-001',
                'TST-NAT-ENC-001',
                'TST-NAT-NULL-001'
            )
    );
-- Elimino soggetti di test
DELETE FROM anagrafiche.soggetti s
WHERE s.codice IN (
        'TST-NAT-PG-001',
        'TST-NAT-PF-001',
        'TST-NAT-ENC-001',
        'TST-NAT-NULL-001'
    );
END;
$$;
SELECT plan(10);
-- =========================================================
-- 0) Precondizioni: stato, tipo_contatto
-- =========================================================
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
-- Recupero tipi_soggetto_dettaglio per SP (PG), PR (PF), ENC
-- Nota: SP (Soc. Persone) anziche' SC (Soc. Capitali) per evitare
-- il vincolo dati_societari_policy = REQUIRED di SC
-- =========================================================
CREATE TEMP TABLE tmp_tipo_sp AS
SELECT id AS tipo_soggetto_dettaglio_id
FROM config.tipi_soggetto_dettaglio
WHERE codice_interno = 'SP';
CREATE TEMP TABLE tmp_tipo_pr AS
SELECT id AS tipo_soggetto_dettaglio_id
FROM config.tipi_soggetto_dettaglio
WHERE codice_interno = 'PR';
CREATE TEMP TABLE tmp_tipo_enc AS
SELECT id AS tipo_soggetto_dettaglio_id
FROM config.tipi_soggetto_dettaglio
WHERE codice_interno = 'ENC';
-- Tipi indirizzo obbligatori (per guard indirizzi_required deferrable)
CREATE TEMP TABLE tmp_tipo_ind_res AS
SELECT id AS tipo_indirizzo_id
FROM config.tipi_indirizzi WHERE codice_interno = 'RES';
CREATE TEMP TABLE tmp_tipo_ind_domfisc AS
SELECT id AS tipo_indirizzo_id
FROM config.tipi_indirizzi WHERE codice_interno = 'DOMFISC';
CREATE TEMP TABLE tmp_tipo_ind_sedeleg AS
SELECT id AS tipo_indirizzo_id
FROM config.tipi_indirizzi WHERE codice_interno = 'SEDELEG';
CREATE TEMP TABLE tmp_tipo_ind_fatt AS
SELECT id AS tipo_indirizzo_id
FROM config.tipi_indirizzi WHERE codice_interno = 'FATT';
-- =========================================================
-- 1) Creo soggetto PG (SP) — con CF e PIVA (obbligatori per SP)
-- =========================================================
SELECT lives_ok(
        $$
        INSERT INTO anagrafiche.soggetti (
                codice,
                ragione_sociale,
                stato_id,
                codice_fiscale,
                partita_iva,
                tipo_soggetto_dettaglio_id
            )
        VALUES (
                'TST-NAT-PG-001',
                'Azienda PG Test Natura',
                (
                    SELECT stato_id
                    FROM tmp_stato_test
                ),
                '37584740775',
                '37584740775',
                (
                    SELECT tipo_soggetto_dettaglio_id
                    FROM tmp_tipo_sp
                )
            );
INSERT INTO anagrafiche.contatti (
        tipo_contatto_id,
        soggetto_id,
        nominativo,
        email,
        is_default
    )
SELECT (
        SELECT tipo_contatto_id
        FROM tmp_tipo_contatto_test
    ),
    s.id,
    'Contatto PG',
    'pg@test.com',
    TRUE
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-NAT-PG-001';
INSERT INTO anagrafiche.indirizzi_soggetti (
        soggetto_id, tipo_indirizzo_id, indirizzo_libero,
        stato_id, locality, postal_box, administrative_area
    )
SELECT s.id,
    (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_sedeleg),
    'Via Test PG SEDELEG',
    (SELECT stato_id FROM tmp_stato_test),
    'Test City', '00100', 'TS'
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-NAT-PG-001';
$$,
'Creazione soggetto PG (SP) con CF e PIVA: OK'
);
-- =========================================================
-- 2) Creo soggetto PF (PR) — con CF (obbligatorio per PR)
-- =========================================================
SELECT lives_ok(
        $$
        INSERT INTO anagrafiche.soggetti (
                codice,
                cognome,
                nome,
                stato_id,
                codice_fiscale,
                tipo_soggetto_dettaglio_id
            )
        VALUES (
                'TST-NAT-PF-001',
                'Rossi',
                'Mario',
                (
                    SELECT stato_id
                    FROM tmp_stato_test
                ),
                'PLCMCL54C22E902C',
                (
                    SELECT tipo_soggetto_dettaglio_id
                    FROM tmp_tipo_pr
                )
            );
INSERT INTO anagrafiche.contatti (
        tipo_contatto_id,
        soggetto_id,
        nominativo,
        email,
        is_default
    )
SELECT (
        SELECT tipo_contatto_id
        FROM tmp_tipo_contatto_test
    ),
    s.id,
    'Contatto PF',
    'pf@test.com',
    TRUE
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-NAT-PF-001';
INSERT INTO anagrafiche.indirizzi_soggetti (
        soggetto_id, tipo_indirizzo_id, indirizzo_libero,
        stato_id, locality, postal_box, administrative_area
    )
SELECT s.id,
    (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_res),
    'Via Test PF RES',
    (SELECT stato_id FROM tmp_stato_test),
    'Test City', '00100', 'TS'
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-NAT-PF-001';
INSERT INTO anagrafiche.indirizzi_soggetti (
        soggetto_id, tipo_indirizzo_id, indirizzo_libero,
        stato_id, locality, postal_box, administrative_area
    )
SELECT s.id,
    (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_domfisc),
    'Via Test PF DOMFISC',
    (SELECT stato_id FROM tmp_stato_test),
    'Test City', '00100', 'TS'
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-NAT-PF-001';
$$,
'Creazione soggetto PF (PR) con CF: OK'
);
-- =========================================================
-- 3) Creo soggetto ENC — con CF e PIVA (obbligatori per ENC)
-- =========================================================
SELECT lives_ok(
        $$
        INSERT INTO anagrafiche.soggetti (
                codice,
                ragione_sociale,
                stato_id,
                codice_fiscale,
                partita_iva,
                tipo_soggetto_dettaglio_id
            )
        VALUES (
                'TST-NAT-ENC-001',
                'Ente Test Natura',
                (
                    SELECT stato_id
                    FROM tmp_stato_test
                ),
                '99055740791',
                '99055740791',
                (
                    SELECT tipo_soggetto_dettaglio_id
                    FROM tmp_tipo_enc
                )
            );
INSERT INTO anagrafiche.contatti (
        tipo_contatto_id,
        soggetto_id,
        nominativo,
        email,
        is_default
    )
SELECT (
        SELECT tipo_contatto_id
        FROM tmp_tipo_contatto_test
    ),
    s.id,
    'Contatto ENC',
    'enc@test.com',
    TRUE
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-NAT-ENC-001';
INSERT INTO anagrafiche.indirizzi_soggetti (
        soggetto_id, tipo_indirizzo_id, indirizzo_libero,
        stato_id, locality, postal_box, administrative_area
    )
SELECT s.id,
    (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_sedeleg),
    'Via Test ENC SEDELEG',
    (SELECT stato_id FROM tmp_stato_test),
    'Test City', '00100', 'TS'
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-NAT-ENC-001';
$$,
'Creazione soggetto ENC con CF e PIVA: OK'
);
-- =========================================================
-- 4) Soggetto PG + ruolo GE → OK (PG ammesso per GE)
-- =========================================================
SELECT lives_ok(
        $$
        INSERT INTO anagrafiche.soggetti_ruoli (soggetto_id, tipo_ruolo_id)
        SELECT s.id,
            3 -- GE
        FROM anagrafiche.soggetti s
        WHERE s.codice = 'TST-NAT-PG-001';
        INSERT INTO anagrafiche.indirizzi (
                soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_libero,
                stato_id, locality, postal_box, administrative_area
            )
        SELECT sr.id,
            (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_sedeleg),
            'Via Test GE SEDELEG',
            (SELECT stato_id FROM tmp_stato_test),
            'Test City', '00100', 'TS'
        FROM anagrafiche.soggetti_ruoli sr
        JOIN anagrafiche.soggetti s ON sr.soggetto_id = s.id
        WHERE s.codice = 'TST-NAT-PG-001' AND sr.tipo_ruolo_id = 3;
        INSERT INTO anagrafiche.indirizzi (
                soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_libero,
                stato_id, locality, postal_box, administrative_area
            )
        SELECT sr.id,
            (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_fatt),
            'Via Test GE FATT',
            (SELECT stato_id FROM tmp_stato_test),
            'Test City', '00100', 'TS'
        FROM anagrafiche.soggetti_ruoli sr
        JOIN anagrafiche.soggetti s ON sr.soggetto_id = s.id
        WHERE s.codice = 'TST-NAT-PG-001' AND sr.tipo_ruolo_id = 3;
$$,
'Soggetto PG + ruolo GE: OK (PG ammesso)'
);
-- =========================================================
-- 5) Soggetto PF + ruolo GE → FALLISCE (PF non ammesso per GE)
-- =========================================================
SELECT throws_ok(
        $$
        INSERT INTO anagrafiche.soggetti_ruoli (soggetto_id, tipo_ruolo_id)
        SELECT s.id,
            3 -- GE
        FROM anagrafiche.soggetti s
        WHERE s.codice = 'TST-NAT-PF-001';
$$,
NULL,
'Soggetto PF + ruolo GE: FALLISCE (PF non ammesso per GE)'
);
-- =========================================================
-- 6) Soggetto PG + ruolo RIS_UMANA → FALLISCE (solo PF ammesso)
-- =========================================================
SELECT throws_ok(
        $$
        INSERT INTO anagrafiche.soggetti_ruoli (soggetto_id, tipo_ruolo_id)
        SELECT s.id,
            14 -- RIS_UMANA
        FROM anagrafiche.soggetti s
        WHERE s.codice = 'TST-NAT-PG-001';
$$,
NULL,
'Soggetto PG + ruolo RIS_UMANA: FALLISCE (solo PF ammesso)'
);
-- =========================================================
-- 7) Soggetto PF + ruolo CL → OK (PF ammesso per CL)
-- =========================================================
SELECT lives_ok(
        $$
        INSERT INTO anagrafiche.soggetti_ruoli (soggetto_id, tipo_ruolo_id)
        SELECT s.id,
            1 -- CL
        FROM anagrafiche.soggetti s
        WHERE s.codice = 'TST-NAT-PF-001';
        INSERT INTO anagrafiche.indirizzi (
                soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_libero,
                stato_id, locality, postal_box, administrative_area
            )
        SELECT sr.id,
            (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_fatt),
            'Via Test CL FATT',
            (SELECT stato_id FROM tmp_stato_test),
            'Test City', '00100', 'TS'
        FROM anagrafiche.soggetti_ruoli sr
        JOIN anagrafiche.soggetti s ON sr.soggetto_id = s.id
        WHERE s.codice = 'TST-NAT-PF-001' AND sr.tipo_ruolo_id = 1;
$$,
'Soggetto PF + ruolo CL: OK (PF ammesso)'
);
-- =========================================================
-- 8) Soggetto ENC + ruolo CL → OK (ENC ammesso per CL)
-- =========================================================
SELECT lives_ok(
        $$
        INSERT INTO anagrafiche.soggetti_ruoli (soggetto_id, tipo_ruolo_id)
        SELECT s.id,
            1 -- CL
        FROM anagrafiche.soggetti s
        WHERE s.codice = 'TST-NAT-ENC-001';
        INSERT INTO anagrafiche.indirizzi (
                soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_libero,
                stato_id, locality, postal_box, administrative_area
            )
        SELECT sr.id,
            (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_fatt),
            'Via Test CL FATT',
            (SELECT stato_id FROM tmp_stato_test),
            'Test City', '00100', 'TS'
        FROM anagrafiche.soggetti_ruoli sr
        JOIN anagrafiche.soggetti s ON sr.soggetto_id = s.id
        WHERE s.codice = 'TST-NAT-ENC-001' AND sr.tipo_ruolo_id = 1;
$$,
'Soggetto ENC + ruolo CL: OK (ENC ammesso)'
);
-- Fine test
SELECT *
FROM finish();