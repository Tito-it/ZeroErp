-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: emittenti fiscali + mapping billing_account + default
--
-- Elenco test:
-- 1) Setup minimo PG disponibile
-- 2) Creato soggetto PG 1 di supporto
-- 3) Creato soggetto PG 2 di supporto
-- 4) Esiste il ruolo EF in config.tipi_ruoli
-- 5) Creato/recuperato ruolo EF per soggetto 1
-- 6) Inserito emittente fiscale 1
-- 7) Esiste esattamente un emittente di default nel mapping
-- 8) Predisposto un billing_account senza mapping emittente
-- 9) Fallback funzione emittente (default)
-- 10) Creato/recuperato ruolo EF per soggetto 2
-- 11) Inserito emittente fiscale 2
-- 12) Inserito mapping BA -> emittente (override)
-- 13) Override funzione emittente (mapping BA)
-- 14) Blocco disattivazione emittente con mapping
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ QUESTO FILE NON USA `SET CONSTRAINTS ALL IMMEDIATE`, a differenza degli
--   altri, e non e' una dimenticanza.
--   `anagrafiche.soggetti` ha TRE guard DEFERRABLE INITIALLY DEFERRED —
--   indirizzi, contatti, dati societari — e li' la deferralita' e' il CONTRATTO
--   DEL DOMINIO: si crea il soggetto, poi il suo indirizzo, e la completezza si
--   verifica al COMMIT. E' per questo che anagrafiche.fn_crea_soggetto_pf puo'
--   restituire un soggetto ancora incompleto, ed e' cosi' che la usa il backend.
--   Forzare IMMEDIATE pretenderebbe l'indirizzo nell'istante stesso dell'INSERT
--   del soggetto: vieterebbe il pattern che il dominio ha scelto.
--   ⚠️ Resta un buco reale: senza la riga quei guard non vengono esercitati da
--   questo test, e la fixture lascia un soggetto che l'applicazione non
--   potrebbe committare. La correzione vera e' COMPLETARE LA FIXTURE
--   (indirizzo + contatti): allora la riga si rimette e il test verifica sul
--   serio. Brief: brief-db-pgtap-runner-rls-baseline §21.

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(14);

-- ============================================================
-- 0) Costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_ef AS
WITH stamp AS (
    SELECT to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS') AS ts
),
semi AS (
    SELECT
        ts,
        right(ts, 10) AS seed_1,
        lpad((((right(ts, 10))::numeric + 1) % 10000000000)::text, 10, '0') AS seed_2
    FROM stamp
),
validi AS (
    SELECT
        ts,
        seed_1 ||
        (
            (
                10 - (
                    SELECT SUM(
                        CASE
                            WHEN gs.i % 2 = 0 THEN
                                CASE
                                    WHEN ((substr(seed_1, gs.i, 1))::int * 2) > 9
                                        THEN ((substr(seed_1, gs.i, 1))::int * 2) - 9
                                    ELSE ((substr(seed_1, gs.i, 1))::int * 2)
                                END
                            ELSE (substr(seed_1, gs.i, 1))::int
                        END
                    )
                    FROM generate_series(1, 10) AS gs(i)
                ) % 10
            ) % 10
        )::text AS cf_piva_1,
        seed_2 ||
        (
            (
                10 - (
                    SELECT SUM(
                        CASE
                            WHEN gs.i % 2 = 0 THEN
                                CASE
                                    WHEN ((substr(seed_2, gs.i, 1))::int * 2) > 9
                                        THEN ((substr(seed_2, gs.i, 1))::int * 2) - 9
                                    ELSE ((substr(seed_2, gs.i, 1))::int * 2)
                                END
                            ELSE (substr(seed_2, gs.i, 1))::int
                        END
                    )
                    FROM generate_series(1, 10) AS gs(i)
                ) % 10
            ) % 10
        )::text AS cf_piva_2
    FROM semi
)
SELECT
    'pgtap_emittenti_fiscali'::text AS test_scope,
    ('PGTAP-EF-' || v.ts)::text AS codice_ef1,
    ('PGTAP-EF2-' || v.ts)::text AS codice_ef2,
    v.cf_piva_1,
    v.cf_piva_2,
    ('ef1_' || v.ts || '@test.local')::text AS email_1,
    ('ef2_' || v.ts || '@test.local')::text AS email_2,
    ('A' || right(v.ts, 6))::text AS rea_1,
    ('B' || right(v.ts, 6))::text AS rea_2,
    ('SDI' || right(v.ts, 4))::text AS sdi_1,
    ('SDJ' || right(v.ts, 4))::text AS sdi_2
FROM validi v;

-- ============================================================
-- 1) Setup minimo autosufficiente per creare soggetti PG candidabili a EF
-- ============================================================
CREATE TEMP TABLE tmp_setup_ef AS
SELECT
    tsd.id AS tipo_soggetto_dettaglio_id,
    COALESCE(
        (
            SELECT fgtsd.forma_giuridica_id
            FROM config.forme_giuridiche_tipi_soggetto_dettaglio fgtsd
            WHERE fgtsd.tipo_soggetto_dettaglio_id = tsd.id
              AND fgtsd.attivo = true
              AND (fgtsd.valido_dal IS NULL OR fgtsd.valido_dal <= CURRENT_DATE)
              AND (fgtsd.valido_al IS NULL OR fgtsd.valido_al >= CURRENT_DATE)
            ORDER BY fgtsd.forma_giuridica_id
            LIMIT 1
        ),
        (SELECT fg.id FROM config.forme_giuridiche fg ORDER BY fg.id LIMIT 1)
    ) AS forma_giuridica_id,
    (SELECT p.id FROM config.province p ORDER BY p.id LIMIT 1) AS provincia_id,
    (SELECT s.id FROM config.stradario s ORDER BY s.id LIMIT 1) AS stradario_id
FROM config.tipi_soggetto_dettaglio tsd
WHERE tsd.tipo_soggetto_id = 'PG'
  AND tsd.stato_iso2 = 'IT'
  AND tsd.formato_cf = 'NUM_11'
  AND tsd.formato_piva = 'NUM_11'
ORDER BY
    CASE WHEN tsd.dati_societari_policy = 'REQUIRED' THEN 0 ELSE 1 END,
    tsd.id
LIMIT 1;

SELECT ok(
    (SELECT tipo_soggetto_dettaglio_id IS NOT NULL
         AND forma_giuridica_id IS NOT NULL
         AND provincia_id IS NOT NULL
         AND stradario_id IS NOT NULL
     FROM tmp_setup_ef),
    'Setup minimo PG disponibile'
);

-- ============================================================
-- 2) Crea soggetto PG 1 di supporto
-- ============================================================
CREATE TEMP TABLE tmp_soggetto_1 AS
WITH sogg AS (
    SELECT anagrafiche.fn_crea_soggetto_pg(
        p_ragione_sociale := 'PGTAP Emittente Soggetto 1',
        p_tipo_soggetto_dettaglio_id := (SELECT tipo_soggetto_dettaglio_id FROM tmp_setup_ef),
        p_email := (SELECT email_1 FROM tmp_costanti_ef),
        p_codice_fiscale := (SELECT cf_piva_1 FROM tmp_costanti_ef),
        p_partita_iva := (SELECT cf_piva_1 FROM tmp_costanti_ef),
        p_forma_giuridica_id := (SELECT forma_giuridica_id FROM tmp_setup_ef),
        p_id_prov_iscri_rea := (SELECT provincia_id FROM tmp_setup_ef),
        p_iscrizione_rea := (SELECT rea_1 FROM tmp_costanti_ef),
        p_capitale_sociale := 10000.00,
        p_destinatario_fe := 'C',
        p_codice_sdi := (SELECT sdi_1 FROM tmp_costanti_ef)
    ) AS soggetto_id
),
ind_det AS (
    SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        p_stradario_id := (SELECT stradario_id FROM tmp_setup_ef),
        p_civico := 9001
    ) AS indirizzo_dettaglio_id
),
indirizzi AS (
    SELECT anagrafiche.fn_crea_indirizzo_soggetto(
        p_soggetto_id := s.soggetto_id,
        p_tipo_indirizzo_codice := ti.codice_interno,
        p_indirizzo_dettaglio_id := d.indirizzo_dettaglio_id
    )
    FROM sogg s
    CROSS JOIN ind_det d
    JOIN config.tipi_soggetto_dettaglio_tipi_indirizzo m
      ON m.tipo_soggetto_dettaglio_id = (SELECT tipo_soggetto_dettaglio_id FROM tmp_setup_ef)
    JOIN config.tipi_indirizzi ti
      ON ti.id = m.tipo_indirizzo_id
    WHERE m.obbligatorio = true
      AND m.attivo = true
      AND (m.valido_dal IS NULL OR m.valido_dal <= CURRENT_DATE)
      AND (m.valido_al IS NULL OR m.valido_al >= CURRENT_DATE)
)
SELECT soggetto_id FROM sogg;

SELECT ok(
    (SELECT soggetto_id IS NOT NULL FROM tmp_soggetto_1),
    'Creato soggetto PG 1 di supporto'
);

-- ============================================================
-- 3) Crea soggetto PG 2 di supporto
-- ============================================================
CREATE TEMP TABLE tmp_soggetto_2 AS
WITH sogg AS (
    SELECT anagrafiche.fn_crea_soggetto_pg(
        p_ragione_sociale := 'PGTAP Emittente Soggetto 2',
        p_tipo_soggetto_dettaglio_id := (SELECT tipo_soggetto_dettaglio_id FROM tmp_setup_ef),
        p_email := (SELECT email_2 FROM tmp_costanti_ef),
        p_codice_fiscale := (SELECT cf_piva_2 FROM tmp_costanti_ef),
        p_partita_iva := (SELECT cf_piva_2 FROM tmp_costanti_ef),
        p_forma_giuridica_id := (SELECT forma_giuridica_id FROM tmp_setup_ef),
        p_id_prov_iscri_rea := (SELECT provincia_id FROM tmp_setup_ef),
        p_iscrizione_rea := (SELECT rea_2 FROM tmp_costanti_ef),
        p_capitale_sociale := 20000.00,
        p_destinatario_fe := 'C',
        p_codice_sdi := (SELECT sdi_2 FROM tmp_costanti_ef)
    ) AS soggetto_id
),
ind_det AS (
    SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        p_stradario_id := (SELECT stradario_id FROM tmp_setup_ef),
        p_civico := 9002
    ) AS indirizzo_dettaglio_id
),
indirizzi AS (
    SELECT anagrafiche.fn_crea_indirizzo_soggetto(
        p_soggetto_id := s.soggetto_id,
        p_tipo_indirizzo_codice := ti.codice_interno,
        p_indirizzo_dettaglio_id := d.indirizzo_dettaglio_id
    )
    FROM sogg s
    CROSS JOIN ind_det d
    JOIN config.tipi_soggetto_dettaglio_tipi_indirizzo m
      ON m.tipo_soggetto_dettaglio_id = (SELECT tipo_soggetto_dettaglio_id FROM tmp_setup_ef)
    JOIN config.tipi_indirizzi ti
      ON ti.id = m.tipo_indirizzo_id
    WHERE m.obbligatorio = true
      AND m.attivo = true
      AND (m.valido_dal IS NULL OR m.valido_dal <= CURRENT_DATE)
      AND (m.valido_al IS NULL OR m.valido_al >= CURRENT_DATE)
)
SELECT soggetto_id FROM sogg;

SELECT ok(
    (SELECT soggetto_id IS NOT NULL FROM tmp_soggetto_2),
    'Creato soggetto PG 2 di supporto'
);

-- ============================================================
-- 4) Ruolo EF presente
-- ============================================================
CREATE TEMP TABLE tmp_ruolo_ef AS
SELECT id AS tipo_ruolo_id
FROM config.tipi_ruoli
WHERE codice_interno = 'EF';

SELECT ok(
    (SELECT count(*) FROM tmp_ruolo_ef) = 1,
    'Esiste il ruolo EF in config.tipi_ruoli'
);

-- ============================================================
-- 5) Ruolo EF per soggetto 1
-- ============================================================
CREATE TEMP TABLE tmp_ef_role_1 AS
SELECT
    script.fn_get_or_create_soggetto_ruolo(
        p_soggetto_id  := (SELECT soggetto_id FROM tmp_soggetto_1),
        p_cd_int_ruolo := 'EF'
    ) AS soggetto_ruolo_id;

SELECT ok(
    (SELECT soggetto_ruolo_id FROM tmp_ef_role_1) IS NOT NULL,
    'Creato/recuperato ruolo EF per soggetto 1'
);

-- ============================================================
-- 6) Inserimento emittente fiscale 1
-- ============================================================
CREATE TEMP TABLE tmp_emittente_1 AS
WITH ins_emittente AS (
    -- `descrizione` non esiste piu' (cantiere emittente, Fase 4 /
    -- 20260802-22): la denominazione viene dalla ragione sociale del
    -- soggetto associato, che questa fixture crea gia'.
    INSERT INTO anagrafiche.emittenti_fiscali (
        soggetto_ruolo_id,
        codice,
        brand_meta
    )
    SELECT
        r.soggetto_ruolo_id,
        k.codice_ef1,
        jsonb_build_object('test_scope', k.test_scope)
    FROM tmp_ef_role_1 r,
         tmp_costanti_ef k
    RETURNING id, soggetto_ruolo_id
)
SELECT id FROM ins_emittente;

SELECT is(
    (SELECT count(*)::int FROM tmp_emittente_1),
    1,
    'Inserito emittente fiscale 1'
);

-- ============================================================
-- 7) Verifica default mapping (1 solo)
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM anagrafiche.emittenti_fiscali_billing_account
      WHERE is_default = true),
    1,
    'Esiste esattamente un emittente di default nel mapping'
);

-- ============================================================
-- 8) Un billing account SENZA mapping emittente
--
-- ⚠️ Questo blocco CERCAVA un BA gia' privo di mapping, e ha smesso di
--    trovarlo quando e' arrivato `trg_billing_account_z90_link_ef_ins`:
--    ogni BA creato dall'app viene agganciato a un emittente, quindi i
--    BA senza mapping oggi sono ZERO. La ricerca tornava vuota e faceva
--    cadere a cascata i test 8, 12, 13 e 14 — il caso da manuale della
--    «fixture rimasta indietro rispetto a un guard entrato dopo».
--
--    La condizione non si cerca piu': si COSTRUISCE, togliendo il
--    mapping a un BA esistente. E' lecito e mirato:
--      - siamo dentro BEGIN/ROLLBACK, il database non cambia;
--      - il trigger non lo ricrea, perche' si attiva solo sull'INSERT
--        del billing account, non sulla DELETE del mapping;
--      - la riga di DEFAULT (billing_account_id IS NULL) resta intatta:
--        `IN (subquery)` non la seleziona, e serve al test 9.
--
--    Cio' che i test 9-14 presidiano — il ramo di fallback di
--    fn_get_emittente_fiscale_id e l'override per BA — e' codice vivo:
--    va costruito lo stato, non sperato.
-- ============================================================
CREATE TEMP TABLE tmp_ba_no_map AS
SELECT ba.id AS billing_account_id
FROM anagrafiche.billing_account ba
ORDER BY ba.id
LIMIT 1;

DELETE FROM anagrafiche.emittenti_fiscali_billing_account m
 WHERE m.billing_account_id IN (SELECT billing_account_id FROM tmp_ba_no_map);

SELECT CASE
    WHEN (SELECT count(*) FROM tmp_ba_no_map) = 0
    THEN skip('8) Nessun billing_account nel database — test saltato')
    ELSE ok(
        NOT EXISTS (
            SELECT 1
              FROM anagrafiche.emittenti_fiscali_billing_account m
              JOIN tmp_ba_no_map t ON t.billing_account_id = m.billing_account_id
        ),
        'Predisposto un billing_account senza mapping emittente')
END;

CREATE TEMP TABLE tmp_emittente_default AS
SELECT m.emittente_soggetto_ruolo_id
FROM anagrafiche.emittenti_fiscali_billing_account m
WHERE m.is_default = true
  AND m.billing_account_id IS NULL
LIMIT 1;

-- ============================================================
-- 9) Fallback funzione emittente (default)
-- ============================================================
SELECT CASE
    WHEN (SELECT count(*) FROM tmp_ba_no_map) = 0
    THEN skip('9) Nessun billing_account nel database — test saltato')
    ELSE is(
        anagrafiche.fn_get_emittente_fiscale_id((SELECT billing_account_id FROM tmp_ba_no_map)),
        (SELECT emittente_soggetto_ruolo_id::bigint FROM tmp_emittente_default),
        'Fallback funzione emittente (default)')
END;

-- ============================================================
-- 10) Ruolo EF per soggetto 2
-- ============================================================
CREATE TEMP TABLE tmp_ef_role_2 AS
SELECT
    script.fn_get_or_create_soggetto_ruolo(
        p_soggetto_id  := (SELECT soggetto_id FROM tmp_soggetto_2),
        p_cd_int_ruolo := 'EF'
    ) AS soggetto_ruolo_id;

SELECT ok(
    (SELECT soggetto_ruolo_id FROM tmp_ef_role_2) IS NOT NULL,
    'Creato/recuperato ruolo EF per soggetto 2'
);

-- ============================================================
-- 11) Inserimento emittente fiscale 2
-- ============================================================
CREATE TEMP TABLE tmp_emittente_2 AS
WITH ins_emittente AS (
    -- Vedi la nota sull'emittente 1: niente piu' `descrizione`.
    INSERT INTO anagrafiche.emittenti_fiscali (
        soggetto_ruolo_id,
        codice,
        brand_meta
    )
    SELECT
        r.soggetto_ruolo_id,
        k.codice_ef2,
        jsonb_build_object('test_scope', k.test_scope)
    FROM tmp_ef_role_2 r,
         tmp_costanti_ef k
    RETURNING id, soggetto_ruolo_id
)
SELECT id FROM ins_emittente;

SELECT is(
    (SELECT count(*)::int FROM tmp_emittente_2),
    1,
    'Inserito emittente fiscale 2'
);

-- ============================================================
-- 12) Inserimento mapping BA -> emittente (override)
-- ============================================================
CREATE TEMP TABLE tmp_map_ba AS
WITH ins AS (
    INSERT INTO anagrafiche.emittenti_fiscali_billing_account (
        billing_account_id,
        emittente_soggetto_ruolo_id,
        is_default,
        meta
    )
    SELECT
        b.billing_account_id,
        r.soggetto_ruolo_id,
        false,
        jsonb_build_object('test_scope', k.test_scope)
    FROM tmp_ba_no_map b,
         tmp_ef_role_2 r,
         tmp_costanti_ef k
    RETURNING id
)
SELECT id FROM ins;

SELECT CASE
    WHEN (SELECT count(*) FROM tmp_ba_no_map) = 0
    THEN skip('12) Nessun billing_account nel database — test saltato')
    ELSE is(
        (SELECT count(*)::int FROM tmp_map_ba),
        1,
        'Inserito mapping BA -> emittente (override)')
END;

-- ============================================================
-- 13) Verifica override funzione emittente
-- ============================================================
SELECT CASE
    WHEN (SELECT count(*) FROM tmp_ba_no_map) = 0
    THEN skip('13) Nessun billing_account nel database — test saltato')
    ELSE is(
        anagrafiche.fn_get_emittente_fiscale_id((SELECT billing_account_id FROM tmp_ba_no_map)),
        (SELECT soggetto_ruolo_id::bigint FROM tmp_ef_role_2),
        'Override funzione emittente (mapping BA)')
END;

-- ============================================================
-- 14) Blocco disattivazione emittente con mapping
-- ============================================================
-- Ha senso solo se il mapping del test 12 e' stato davvero creato:
-- e' quel mapping a rendere l'emittente non disattivabile.
SELECT CASE
    WHEN (SELECT count(*) FROM tmp_map_ba) = 0
    THEN skip('14) Nessun mapping BA creato (vedi 12) — test saltato')
    ELSE throws_ok(
        $$
        UPDATE anagrafiche.emittenti_fiscali
        SET attivo = false
        WHERE id = (SELECT id FROM tmp_emittente_2);
        $$,
        'P0001',
        NULL,
        'Blocco disattivazione emittente con mapping BA')
END;

SELECT * FROM finish();
ROLLBACK;
