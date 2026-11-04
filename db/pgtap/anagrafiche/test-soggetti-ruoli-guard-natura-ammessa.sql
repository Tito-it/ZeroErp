-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
-- ============================================================================
-- rev 2026-08-18 — bonifica baseline. Qui c'era un blocco di cinque DELETE di
-- «cleanup iniziale» sui soggetti di prova delle corse precedenti: non
-- funziona piu' (fk_ddt_indirizzi_origine e altre FK RESTRICT li trattengono),
-- e il file moriva alla riga 83 — ZERO asserzioni su 10.
-- Il file e' gia' BEGIN ... ROLLBACK: residui suoi non ne fa. Il rimedio e'
-- non collidere invece di cancellare — codici, partite IVA e codice fiscale
-- unici per corsa.
-- ============================================================================

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

SELECT plan(10);

CREATE TEMP TABLE tmp_run_sfx AS
-- rev 2026-11-04: upper() sul suffisso: il codice si salva in maiuscolo (automazione CODICE_MAIUSCOLO), e la ricerca per valore deve ricomporlo uguale.
SELECT upper(substr(md5(clock_timestamp()::text), 1, 8)) AS sfx,
       -- ⚠️ fn(0) e fn(1), non due fn(): nella stessa istruzione la versione
       --   senza argomenti tornerebbe due volte lo STESSO valore, perche' fra
       --   l'una e l'altra non c'e' nessun insert a occuparlo.
       dbops.fn_pgtap_piva_libera(0) AS piva_pg,
       dbops.fn_pgtap_piva_libera(1) AS piva_enc,
       dbops.fn_pgtap_cf_libero()   AS cf_pf;
-- =========================================================
-- 0) Precondizioni: stato, tipo_contatto
-- =========================================================
CREATE TEMP TABLE tmp_stato_test AS
SELECT id AS stato_id
FROM config.stati
ORDER BY id
LIMIT 1;
-- rev 2026-10-18: i campi della forma che il guard vuole per questo stato
--   (dbops.fn_pgtap_indirizzo_libero_forma: comune e CAP per l'Italia).
ALTER TABLE tmp_stato_test ADD COLUMN comune_id integer, ADD COLUMN codice_postale_id integer,
                           ADD COLUMN locality varchar, ADD COLUMN postal_code varchar;
UPDATE tmp_stato_test
   SET (comune_id, codice_postale_id, locality, postal_code) =
       (SELECT f.comune_id, f.codice_postale_id, f.locality, f.postal_code
          FROM dbops.fn_pgtap_indirizzo_libero_forma(tmp_stato_test.stato_id) f);
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
        -- ⭐ Finestra differita: i guard di completezza su soggetti sono
        --   DEFERRABLE apposta (un soggetto e' una saga). Con IMMEDIATE
        --   scatterebbero sul primo insert, prima che sia completo.
        SET CONSTRAINTS ALL DEFERRED;
        INSERT INTO anagrafiche.soggetti (
                codice,
                ragione_sociale,
                stato_id,
                codice_fiscale,
                partita_iva,
                tipo_soggetto_dettaglio_id
            )
        VALUES (
                'TST-NAT-PG-001-' || (SELECT sfx FROM tmp_run_sfx),
                'Azienda PG Test Natura',
                (
                    SELECT stato_id
                    FROM tmp_stato_test
                ),
                (SELECT piva_pg FROM tmp_run_sfx),
                (SELECT piva_pg FROM tmp_run_sfx),
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
WHERE s.codice = 'TST-NAT-PG-001-' || (SELECT sfx FROM tmp_run_sfx);
INSERT INTO anagrafiche.indirizzi_soggetti (
        soggetto_id, tipo_indirizzo_id, indirizzo_libero,
        stato_id, comune_id, codice_postale_id, locality, postal_code
    )
SELECT s.id,
    (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_sedeleg),
    'Via Test PG SEDELEG',
    (SELECT stato_id FROM tmp_stato_test),
    (SELECT comune_id FROM tmp_stato_test), (SELECT codice_postale_id FROM tmp_stato_test), (SELECT locality FROM tmp_stato_test), (SELECT postal_code FROM tmp_stato_test)
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-NAT-PG-001-' || (SELECT sfx FROM tmp_run_sfx);
        -- Saga completa: qui i guard verificano davvero.
        SET CONSTRAINTS ALL IMMEDIATE;
$$,
'Creazione soggetto PG (SP) con CF e PIVA: OK'
);
-- =========================================================
-- 2) Creo soggetto PF (PR) — con CF (obbligatorio per PR)
-- =========================================================
SELECT lives_ok(
        $$
        -- ⭐ Finestra differita: i guard di completezza su soggetti sono
        --   DEFERRABLE apposta (un soggetto e' una saga). Con IMMEDIATE
        --   scatterebbero sul primo insert, prima che sia completo.
        SET CONSTRAINTS ALL DEFERRED;
        INSERT INTO anagrafiche.soggetti (
                codice,
                cognome,
                nome,
                sesso,   -- un privato: obbligatorio (sesso_policy REQUIRED)
                stato_id,
                codice_fiscale,
                tipo_soggetto_dettaglio_id
            )
        VALUES (
                'TST-NAT-PF-001-' || (SELECT sfx FROM tmp_run_sfx),
                'Rossi',
                'Mario',
                'M',
                (
                    SELECT stato_id
                    FROM tmp_stato_test
                ),
                (SELECT cf_pf FROM tmp_run_sfx),
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
WHERE s.codice = 'TST-NAT-PF-001-' || (SELECT sfx FROM tmp_run_sfx);
INSERT INTO anagrafiche.indirizzi_soggetti (
        soggetto_id, tipo_indirizzo_id, indirizzo_libero,
        stato_id, comune_id, codice_postale_id, locality, postal_code
    )
SELECT s.id,
    (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_res),
    'Via Test PF RES',
    (SELECT stato_id FROM tmp_stato_test),
    (SELECT comune_id FROM tmp_stato_test), (SELECT codice_postale_id FROM tmp_stato_test), (SELECT locality FROM tmp_stato_test), (SELECT postal_code FROM tmp_stato_test)
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-NAT-PF-001-' || (SELECT sfx FROM tmp_run_sfx);
INSERT INTO anagrafiche.indirizzi_soggetti (
        soggetto_id, tipo_indirizzo_id, indirizzo_libero,
        stato_id, comune_id, codice_postale_id, locality, postal_code
    )
SELECT s.id,
    (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_domfisc),
    'Via Test PF DOMFISC',
    (SELECT stato_id FROM tmp_stato_test),
    (SELECT comune_id FROM tmp_stato_test), (SELECT codice_postale_id FROM tmp_stato_test), (SELECT locality FROM tmp_stato_test), (SELECT postal_code FROM tmp_stato_test)
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-NAT-PF-001-' || (SELECT sfx FROM tmp_run_sfx);
        -- Saga completa: qui i guard verificano davvero.
        SET CONSTRAINTS ALL IMMEDIATE;
$$,
'Creazione soggetto PF (PR) con CF: OK'
);
-- =========================================================
-- 3) Creo soggetto ENC — con CF e PIVA (obbligatori per ENC)
-- =========================================================
SELECT lives_ok(
        $$
        -- ⭐ Finestra differita: i guard di completezza su soggetti sono
        --   DEFERRABLE apposta (un soggetto e' una saga). Con IMMEDIATE
        --   scatterebbero sul primo insert, prima che sia completo.
        SET CONSTRAINTS ALL DEFERRED;
        INSERT INTO anagrafiche.soggetti (
                codice,
                ragione_sociale,
                stato_id,
                codice_fiscale,
                partita_iva,
                tipo_soggetto_dettaglio_id
            )
        VALUES (
                'TST-NAT-ENC-001-' || (SELECT sfx FROM tmp_run_sfx),
                'Ente Test Natura',
                (
                    SELECT stato_id
                    FROM tmp_stato_test
                ),
                (SELECT piva_enc FROM tmp_run_sfx),
                (SELECT piva_enc FROM tmp_run_sfx),
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
WHERE s.codice = 'TST-NAT-ENC-001-' || (SELECT sfx FROM tmp_run_sfx);
INSERT INTO anagrafiche.indirizzi_soggetti (
        soggetto_id, tipo_indirizzo_id, indirizzo_libero,
        stato_id, comune_id, codice_postale_id, locality, postal_code
    )
SELECT s.id,
    (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_sedeleg),
    'Via Test ENC SEDELEG',
    (SELECT stato_id FROM tmp_stato_test),
    (SELECT comune_id FROM tmp_stato_test), (SELECT codice_postale_id FROM tmp_stato_test), (SELECT locality FROM tmp_stato_test), (SELECT postal_code FROM tmp_stato_test)
FROM anagrafiche.soggetti s
WHERE s.codice = 'TST-NAT-ENC-001-' || (SELECT sfx FROM tmp_run_sfx);
        -- Saga completa: qui i guard verificano davvero.
        SET CONSTRAINTS ALL IMMEDIATE;
$$,
'Creazione soggetto ENC con CF e PIVA: OK'
);
-- =========================================================
-- 4) Soggetto PG + ruolo GE → OK (PG ammesso per GE)
-- =========================================================
SELECT lives_ok(
        $$
        -- ⭐ Finestra differita: i guard di completezza su soggetti sono
        --   DEFERRABLE apposta (un soggetto e' una saga). Con IMMEDIATE
        --   scatterebbero sul primo insert, prima che sia completo.
        SET CONSTRAINTS ALL DEFERRED;
        INSERT INTO anagrafiche.soggetti_ruoli (soggetto_id, tipo_ruolo_id)
        SELECT s.id,
            3 -- GE
        FROM anagrafiche.soggetti s
        WHERE s.codice = 'TST-NAT-PG-001-' || (SELECT sfx FROM tmp_run_sfx);
        INSERT INTO anagrafiche.indirizzi (
                soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_libero,
                stato_id, comune_id, codice_postale_id, locality, postal_code
            )
        SELECT sr.id,
            (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_sedeleg),
            'Via Test GE SEDELEG',
            (SELECT stato_id FROM tmp_stato_test),
            (SELECT comune_id FROM tmp_stato_test), (SELECT codice_postale_id FROM tmp_stato_test), (SELECT locality FROM tmp_stato_test), (SELECT postal_code FROM tmp_stato_test)
        FROM anagrafiche.soggetti_ruoli sr
        JOIN anagrafiche.soggetti s ON sr.soggetto_id = s.id
        WHERE s.codice = 'TST-NAT-PG-001-' || (SELECT sfx FROM tmp_run_sfx) AND sr.tipo_ruolo_id = 3;
        INSERT INTO anagrafiche.indirizzi (
                soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_libero,
                stato_id, comune_id, codice_postale_id, locality, postal_code
            )
        SELECT sr.id,
            (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_fatt),
            'Via Test GE FATT',
            (SELECT stato_id FROM tmp_stato_test),
            (SELECT comune_id FROM tmp_stato_test), (SELECT codice_postale_id FROM tmp_stato_test), (SELECT locality FROM tmp_stato_test), (SELECT postal_code FROM tmp_stato_test)
        FROM anagrafiche.soggetti_ruoli sr
        JOIN anagrafiche.soggetti s ON sr.soggetto_id = s.id
        WHERE s.codice = 'TST-NAT-PG-001-' || (SELECT sfx FROM tmp_run_sfx) AND sr.tipo_ruolo_id = 3;
        -- Saga completa: qui i guard verificano davvero.
        SET CONSTRAINTS ALL IMMEDIATE;
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
        WHERE s.codice = 'TST-NAT-PF-001-' || (SELECT sfx FROM tmp_run_sfx);
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
        WHERE s.codice = 'TST-NAT-PG-001-' || (SELECT sfx FROM tmp_run_sfx);
$$,
NULL,
'Soggetto PG + ruolo RIS_UMANA: FALLISCE (solo PF ammesso)'
);
-- =========================================================
-- 7) Soggetto PF + ruolo CL → OK (PF ammesso per CL)
-- =========================================================
SELECT lives_ok(
        $$
        -- ⭐ Finestra differita: i guard di completezza su soggetti sono
        --   DEFERRABLE apposta (un soggetto e' una saga). Con IMMEDIATE
        --   scatterebbero sul primo insert, prima che sia completo.
        SET CONSTRAINTS ALL DEFERRED;
        INSERT INTO anagrafiche.soggetti_ruoli (soggetto_id, tipo_ruolo_id)
        SELECT s.id,
            1 -- CL
        FROM anagrafiche.soggetti s
        WHERE s.codice = 'TST-NAT-PF-001-' || (SELECT sfx FROM tmp_run_sfx);
        INSERT INTO anagrafiche.indirizzi (
                soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_libero,
                stato_id, comune_id, codice_postale_id, locality, postal_code
            )
        SELECT sr.id,
            (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_fatt),
            'Via Test CL FATT',
            (SELECT stato_id FROM tmp_stato_test),
            (SELECT comune_id FROM tmp_stato_test), (SELECT codice_postale_id FROM tmp_stato_test), (SELECT locality FROM tmp_stato_test), (SELECT postal_code FROM tmp_stato_test)
        FROM anagrafiche.soggetti_ruoli sr
        JOIN anagrafiche.soggetti s ON sr.soggetto_id = s.id
        WHERE s.codice = 'TST-NAT-PF-001-' || (SELECT sfx FROM tmp_run_sfx) AND sr.tipo_ruolo_id = 1;
        -- Saga completa: qui i guard verificano davvero.
        SET CONSTRAINTS ALL IMMEDIATE;
$$,
'Soggetto PF + ruolo CL: OK (PF ammesso)'
);
-- =========================================================
-- 8) Soggetto ENC + ruolo CL → OK (ENC ammesso per CL)
-- =========================================================
SELECT lives_ok(
        $$
        -- ⭐ Finestra differita: i guard di completezza su soggetti sono
        --   DEFERRABLE apposta (un soggetto e' una saga). Con IMMEDIATE
        --   scatterebbero sul primo insert, prima che sia completo.
        SET CONSTRAINTS ALL DEFERRED;
        INSERT INTO anagrafiche.soggetti_ruoli (soggetto_id, tipo_ruolo_id)
        SELECT s.id,
            1 -- CL
        FROM anagrafiche.soggetti s
        WHERE s.codice = 'TST-NAT-ENC-001-' || (SELECT sfx FROM tmp_run_sfx);
        INSERT INTO anagrafiche.indirizzi (
                soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_libero,
                stato_id, comune_id, codice_postale_id, locality, postal_code
            )
        SELECT sr.id,
            (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_fatt),
            'Via Test CL FATT',
            (SELECT stato_id FROM tmp_stato_test),
            (SELECT comune_id FROM tmp_stato_test), (SELECT codice_postale_id FROM tmp_stato_test), (SELECT locality FROM tmp_stato_test), (SELECT postal_code FROM tmp_stato_test)
        FROM anagrafiche.soggetti_ruoli sr
        JOIN anagrafiche.soggetti s ON sr.soggetto_id = s.id
        WHERE s.codice = 'TST-NAT-ENC-001-' || (SELECT sfx FROM tmp_run_sfx) AND sr.tipo_ruolo_id = 1;
        -- Saga completa: qui i guard verificano davvero.
        SET CONSTRAINTS ALL IMMEDIATE;
$$,
'Soggetto ENC + ruolo CL: OK (ENC ammesso)'
);
-- Fine test
SELECT *
FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
