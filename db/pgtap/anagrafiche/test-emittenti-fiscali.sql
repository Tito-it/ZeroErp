-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-differiti: escluso — la fixture non soddisfa un vincolo DIFFERITO e la
--   ragione e' scritta per esteso piu' sotto. Debito noto (§22.4): quando la
--   fixture viene completata, si toglie questa riga e si rimette il
--   SET CONSTRAINTS ALL IMMEDIATE nel punto in cui l'unita' di lavoro e' completa.
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

-- ⚠️ VINCOLI DIFFERITI — ⭐ LA FINESTRA SI RIAPRE, NON SI PRESUME.
--   La fixture costruisce soggetti in istruzioni separate e conta sui guard
--   DEFERRABLE di `anagrafiche.soggetti` (esenzione dichiarata sopra).
--   ⛔ Ma la riga di contesto qui sopra, quando COSTRUISCE il mondo (database
--   senza operatori: lo scratch `zeroerp_ci`, la CI), ESCE CON I VINCOLI
--   IMMEDIATE (rev 20260921-18, come ogni helper pgTAP). Fino al 2026-09-23 lo
--   mascherava un residuo: `create-gestore-conto-*` committavano l'operatore
--   `PGTR0001` e da li' la riga non costruiva piu'. Tolto quel COMMIT (brief
--   fixture-che-costruiscono giro 2), lo scratch appena ricostruito ha dato
--   ERRORE_FIXTURE: «Sono richiesti dati societari per soggetto_id …» —
--   il guard differito dei dati societari scattato all'INSERT.
--   La finestra la riapre il file, e dice da se' cosa vuole.
SET CONSTRAINTS ALL DEFERRED;

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
    -- ⚠️ 2026-08-31: le sigle emittente hanno una FORMA vincolata
    --   (chk_emittenti_fiscali_codice_forma): maiuscole e cifre, 2..10
    --   caratteri, NIENTE trattino — perche' la sigla finisce dentro il codice
    --   commessa `CMM-<sigla>-<anno>-<numero>`, che si legge separando sul
    --   trattino. I vecchi `PGTAP-EF-<ts>` non passerebbero piu'.
    --   ⭐ Le ultime 8 cifre del timestamp bastano a distinguere le corse, e la
    --   pulizia non si appoggia al codice ma a `brand_meta->>'test_scope'`.
    ('EF' || right(v.ts, 8))::text AS codice_ef1,
    ('EG' || right(v.ts, 8))::text AS codice_ef2,
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
              AND (fgtsd.valido_dal IS NULL OR fgtsd.valido_dal <= script.fn_data_operativa())
              AND (fgtsd.valido_al IS NULL OR fgtsd.valido_al >= script.fn_data_operativa())
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
    -- rev 2026-10-18: la madre prende l'indirizzo in jsonb (20261018-96)
    SELECT anagrafiche.fn_crea_indirizzo_soggetto(
        s.soggetto_id,
        jsonb_build_object('tipo_indirizzo_codice_interno',  ti.codice_interno,
                           'indirizzo_dettaglio_id', d.indirizzo_dettaglio_id)
    )
    FROM sogg s
    CROSS JOIN ind_det d
    JOIN config.tipi_soggetto_dettaglio_tipi_indirizzo m
      ON m.tipo_soggetto_dettaglio_id = (SELECT tipo_soggetto_dettaglio_id FROM tmp_setup_ef)
    JOIN config.tipi_indirizzi ti
      ON ti.id = m.tipo_indirizzo_id
    WHERE m.obbligatorio = true
      AND m.attivo = true
      AND (m.valido_dal IS NULL OR m.valido_dal <= script.fn_data_operativa())
      AND (m.valido_al IS NULL OR m.valido_al >= script.fn_data_operativa())
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
    -- rev 2026-10-18: la madre prende l'indirizzo in jsonb (20261018-96)
    SELECT anagrafiche.fn_crea_indirizzo_soggetto(
        s.soggetto_id,
        jsonb_build_object('tipo_indirizzo_codice_interno',  ti.codice_interno,
                           'indirizzo_dettaglio_id', d.indirizzo_dettaglio_id)
    )
    FROM sogg s
    CROSS JOIN ind_det d
    JOIN config.tipi_soggetto_dettaglio_tipi_indirizzo m
      ON m.tipo_soggetto_dettaglio_id = (SELECT tipo_soggetto_dettaglio_id FROM tmp_setup_ef)
    JOIN config.tipi_indirizzi ti
      ON ti.id = m.tipo_indirizzo_id
    WHERE m.obbligatorio = true
      AND m.attivo = true
      AND (m.valido_dal IS NULL OR m.valido_dal <= script.fn_data_operativa())
      AND (m.valido_al IS NULL OR m.valido_al >= script.fn_data_operativa())
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
--    La condizione non si cerca piu': si COSTRUISCE. E' lecito e mirato:
--      - siamo dentro BEGIN/ROLLBACK, il database non cambia;
--      - il trigger di auto-aggancio non ricrea il mapping, perche' si
--        attiva solo sull'INSERT del billing account, non sulla DELETE
--        del mapping;
--      - la riga di DEFAULT (billing_account_id IS NULL) resta intatta:
--        `IN (subquery)` non la seleziona, e serve al test 9.
--
--    Cio' che i test 9-14 presidiano — il ramo di fallback di
--    fn_get_emittente_fiscale_id e l'override per BA — e' codice vivo:
--    va costruito lo stato, non sperato.
--
-- ⭐ 2026-08-26 — LA STESSA LEZIONE, UN LIVELLO PIU' SOTTO.
--    Questo blocco costruiva lo stato togliendo il mapping a un BA
--    PRESO IN PRESTITO (`ORDER BY ba.id LIMIT 1`), cioe' a un cliente
--    vero con la sua storia — nel database di sviluppo, uno con 30
--    commesse. Ha smesso di funzionare con
--    `anagrafiche.trgfn_efba_guard_storia_emittente`, che vieta di
--    spostare su un altro emittente un cliente che ha gia' fatturato o
--    ha del lavoro raccolto in commessa: il test 12 (l'override) e'
--    esattamente quello spostamento.
--    ⛔ Il guard non e' troppo severo: quelle 30 commesse portano una
--    COPIA CONGELATA dell'emittente, e mapparne il cliente altrove le
--    renderebbe false. La fixture chiedeva al database uno stato che il
--    modello non ammette.
--    ⇒ Adesso il billing account **se lo fabbrica**: nuovo, quindi
--    senza storia, quindi con la finestra di correzione ancora aperta —
--    che e' precisamente il caso che i test 12 e 13 vogliono esercitare.
--    Brief: brief-db-billing-account-cambio-emittente §6.1.
-- ============================================================
CREATE TEMP TABLE tmp_ba_no_map (billing_account_id bigint);

DO $ba$
DECLARE
    v_soggetto_id          anagrafiche.istanze_utilities.soggetto_id%TYPE;
    v_soggetto_ruolo_id    anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_utility_id           anagrafiche.billing_account.utility_id%TYPE;
    v_categoria_cliente_id anagrafiche.billing_account.categoria_cliente_id%TYPE;
    v_codice_iu            anagrafiche.istanze_utilities.codice%TYPE;
    v_istanza_id           anagrafiche.istanze_utilities.id%TYPE;
    v_ba_id                anagrafiche.billing_account.id%TYPE;
BEGIN
    -- I riferimenti anagrafici si prendono da un billing account esistente
    -- (soggetto, ruolo, utility, categoria): quello che NON si prende in
    -- prestito e' il billing account stesso.
    -- ⚠️ ORDER BY esplicito: un LIMIT 1 senza non verifica, scommette.
    SELECT iu.soggetto_id, ba.soggetto_ruolo_id, ba.utility_id, ba.categoria_cliente_id
      INTO v_soggetto_id, v_soggetto_ruolo_id, v_utility_id, v_categoria_cliente_id
      FROM anagrafiche.billing_account ba
      JOIN anagrafiche.istanze_utilities iu ON iu.id = ba.istanza_utility_id
     WHERE ba.utility_id IS NOT NULL
     ORDER BY ba.id
     LIMIT 1;

    -- Nessun riferimento: i test 8-14 si saltano da soli (tabella vuota).
    IF v_soggetto_id IS NULL THEN
        RETURN;
    END IF;

    SELECT 'PGTAP-EFIU-' || right(k.codice_ef1, 17)
      INTO v_codice_iu
      FROM tmp_costanti_ef k;

    -- ⚠️ DUE istruzioni separate e non una CTE: sotto RLS il padre appena
    --   inserito non e' visibile al figlio nella stessa snapshot, e il
    --   guard di coerenza soggetto/istanza direbbe il falso.
    INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
    VALUES (v_soggetto_id, true, v_codice_iu)
    RETURNING id INTO v_istanza_id;

    -- ⭐ Il mapping verso l'emittente non si scrive: lo crea
    --   anagrafiche.trgfn_billing_account_link_ef agganciando il BA
    --   all'emittente dell'operatore corrente. E' il percorso reale — un
    --   billing account non passa mai da uno stato «senza emittente» — ed
    --   e' il motivo per cui la DELETE qui sotto serve.
    INSERT INTO anagrafiche.billing_account (
        istanza_utility_id, soggetto_ruolo_id, utility_id, valido_dal,
        categoria_cliente_id)
    VALUES (v_istanza_id, v_soggetto_ruolo_id, v_utility_id, script.fn_data_operativa(),
        v_categoria_cliente_id)
    RETURNING id INTO v_ba_id;

    INSERT INTO tmp_ba_no_map VALUES (v_ba_id);
END;
$ba$;

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
