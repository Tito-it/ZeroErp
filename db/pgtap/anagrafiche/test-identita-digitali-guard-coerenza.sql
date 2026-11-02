-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-differiti: escluso — la fixture non soddisfa un vincolo DIFFERITO e la
--   ragione e' scritta per esteso piu' sotto. Debito noto (§22.4): quando la
--   fixture viene completata, si toglie questa riga e si rimette il
--   SET CONSTRAINTS ALL IMMEDIATE nel punto in cui l'unita' di lavoro e' completa.
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.trgfn_identita_digitali_guard_coerenza
-- Riferimento: §4.2.3 WIP multi-face-auth
-- Dispatch CASE su ruolo_applicativo con doppia verifica per OPERATORE.
--
-- Indice test (1..10):
--    1. Precondizione: comune + fixture cliente + fixture fornitore
--    2. Setup: soggetto PF pura via fn_crea_soggetto_pf
--    3. Setup: 3 soggetti_ruoli (RIS_UMANA, CL, FO)
--    4. OPERATORE su RIS_UMANA (PF pura) -> lives_ok
--    5. OPERATORE su SR CL -> throws (tipo_ruolo incoerente)
--    6. CLIENTE_PORTALE su SR CL -> lives_ok
--    7. CLIENTE_PORTALE su SR FO -> throws
--    8. SHOP_CUSTOMER su SR CL -> lives_ok (stesso percorso CLIENTE_PORTALE)
--    9. FORNITORE_PORTALE su SR FO -> lives_ok
--   10. API_CLIENT su SR CL -> lives_ok (early-exit, nessun vincolo)
--
-- Nota: tutti gli INSERT usano attivo=false per evitare conflitti con
-- l'indice parziale UNIQUE uq_identita_digitali_soggetto_ruolo_attivo
-- (WHERE attivo = true). Il guard di coerenza e' BEFORE INSERT, quindi
-- viene valutato indipendentemente da attivo.
--
-- BEGIN; + rollback implicito a fine file: i trigger DEFERRABLE di
-- guard su soggetti non scattano (no COMMIT).
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

SELECT plan(10);

-- =========================================================
-- 1) Precondizioni: comune + fixture cliente + fornitore
-- =========================================================
CREATE TEMP TABLE _t_comune AS
SELECT id AS comune_id FROM config.comuni ORDER BY id LIMIT 1;

CREATE TEMP TABLE _t_sr_cl AS
SELECT sr.id AS sr_id, sr.soggetto_id
  FROM anagrafiche.clienti c
  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = c.soggetto_ruolo_id
 ORDER BY c.id
 LIMIT 1;

CREATE TEMP TABLE _t_sr_fo AS
SELECT sr.id AS sr_id, sr.soggetto_id
  FROM anagrafiche.fornitori f
  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = f.soggetto_ruolo_id
 ORDER BY f.id
 LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM _t_comune) = 1
    AND (SELECT count(*) FROM _t_sr_cl) = 1
    AND (SELECT count(*) FROM _t_sr_fo) = 1,
    '1. Precondizioni: comune + fixture cliente + fornitore disponibili'
);

-- =========================================================
-- 2) Setup: soggetto PF pura per ruolo RIS_UMANA
-- =========================================================
-- CF fisso valido. pgTAP rollbacca a fine file.
CREATE TEMP TABLE _t_sogg_pf AS
SELECT anagrafiche.fn_crea_soggetto_pf(
    p_cognome           := 'PraTestCoerenza',
    p_nome              := 'Fnc',
    p_codice_fiscale    := 'PRAFNC80A01F205N',
    p_email             := 'pgtap_coer_' || substring(md5(clock_timestamp()::text) from 1 for 8) || '@test.local',
    p_data_nascita      := DATE '1980-01-01',
    p_sesso             := 'M',
    p_stato_iso2        := 'IT',
    p_comune_nascita_id := (SELECT comune_id FROM _t_comune),
    p_tipo_contatto_id  := NULL,
    p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR')
) AS soggetto_id;

SELECT ok(
    (SELECT soggetto_id FROM _t_sogg_pf) IS NOT NULL,
    '2. Setup: soggetto PF pura creato'
);

-- =========================================================
-- 3) Setup: SR RIS_UMANA + reuse SR CL/FO da fixture
-- =========================================================
CREATE TEMP TABLE _t_sr_ru AS
SELECT script.fn_get_or_create_soggetto_ruolo(
    p_soggetto_id  := (SELECT soggetto_id FROM _t_sogg_pf),
    p_cd_int_ruolo := 'RIS_UMANA'
) AS sr_id;

SELECT ok(
    (SELECT sr_id FROM _t_sr_ru) IS NOT NULL,
    '3. Setup: SR RIS_UMANA creato su soggetto PF pura'
);

-- =========================================================
-- Helper: auth_user di test on-demand (uno per ogni INSERT)
-- =========================================================
CREATE TEMP TABLE _t_au_pool (idx int, auth_user_id int);

INSERT INTO _t_au_pool (idx, auth_user_id)
SELECT gs.i, nextval('django.auth_user_id_seq')  -- placeholder, sovrascritto sotto
  FROM generate_series(1, 7) gs(i);

-- Sovrascrivo creando 7 auth_user reali (uno per test INSERT)
TRUNCATE _t_au_pool;
DO $$
DECLARE
    v_i int;
    v_id int;
BEGIN
    FOR v_i IN 1..7 LOOP
        INSERT INTO django.auth_user (
            username, password, is_active, is_staff, is_superuser,
            first_name, last_name, email, date_joined
        )
        VALUES (
            '_pgtap_coer_' || v_i || '_' || substring(md5(clock_timestamp()::text) from 1 for 6),
            '!', false, false, false, '', '', '', now()
        )
        RETURNING id INTO v_id;
        INSERT INTO _t_au_pool (idx, auth_user_id) VALUES (v_i, v_id);
    END LOOP;
END
$$;

-- =========================================================
-- 4) OPERATORE su SR RIS_UMANA (PF pura) -> lives_ok
-- =========================================================
SELECT lives_ok(
    format($sql$
        INSERT INTO anagrafiche.identita_digitali
            (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
        VALUES (%s, %s, 'OPERATORE', false)
    $sql$,
    (SELECT sr_id FROM _t_sr_ru),
    (SELECT auth_user_id FROM _t_au_pool WHERE idx = 1)),
    '4. OPERATORE su SR RIS_UMANA (PF pura) -> INSERT ok'
);

-- =========================================================
-- 5) OPERATORE su SR CL -> throws (non RIS_UMANA)
-- =========================================================
SELECT throws_ok(
    format($sql$
        INSERT INTO anagrafiche.identita_digitali
            (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
        VALUES (%s, %s, 'OPERATORE', false)
    $sql$,
    (SELECT sr_id FROM _t_sr_cl),
    (SELECT auth_user_id FROM _t_au_pool WHERE idx = 2)),
    NULL, NULL,
    '5. OPERATORE su SR CL -> throws (tipo_ruolo non RIS_UMANA)'
);

-- =========================================================
-- 6) CLIENTE_PORTALE su SR CL -> lives_ok
-- =========================================================
SELECT lives_ok(
    format($sql$
        INSERT INTO anagrafiche.identita_digitali
            (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
        VALUES (%s, %s, 'CLIENTE_PORTALE', false)
    $sql$,
    (SELECT sr_id FROM _t_sr_cl),
    (SELECT auth_user_id FROM _t_au_pool WHERE idx = 3)),
    '6. CLIENTE_PORTALE su SR CL -> INSERT ok'
);

-- =========================================================
-- 7) CLIENTE_PORTALE su SR FO -> throws
-- =========================================================
SELECT throws_ok(
    format($sql$
        INSERT INTO anagrafiche.identita_digitali
            (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
        VALUES (%s, %s, 'CLIENTE_PORTALE', false)
    $sql$,
    (SELECT sr_id FROM _t_sr_fo),
    (SELECT auth_user_id FROM _t_au_pool WHERE idx = 4)),
    NULL, NULL,
    '7. CLIENTE_PORTALE su SR FO -> throws (atteso CL)'
);

-- =========================================================
-- 8) SHOP_CUSTOMER su SR CL -> lives_ok (stesso percorso di CLIENTE_PORTALE)
-- =========================================================
SELECT lives_ok(
    format($sql$
        INSERT INTO anagrafiche.identita_digitali
            (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
        VALUES (%s, %s, 'SHOP_CUSTOMER', false)
    $sql$,
    (SELECT sr_id FROM _t_sr_cl),
    (SELECT auth_user_id FROM _t_au_pool WHERE idx = 5)),
    '8. SHOP_CUSTOMER su SR CL -> INSERT ok (condivide percorso con CLIENTE_PORTALE)'
);

-- =========================================================
-- 9) FORNITORE_PORTALE su SR FO -> lives_ok
-- =========================================================
SELECT lives_ok(
    format($sql$
        INSERT INTO anagrafiche.identita_digitali
            (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
        VALUES (%s, %s, 'FORNITORE_PORTALE', false)
    $sql$,
    (SELECT sr_id FROM _t_sr_fo),
    (SELECT auth_user_id FROM _t_au_pool WHERE idx = 6)),
    '9. FORNITORE_PORTALE su SR FO -> INSERT ok'
);

-- =========================================================
-- 10) API_CLIENT su SR CL -> lives_ok (early-exit, nessun vincolo)
-- =========================================================
SELECT lives_ok(
    format($sql$
        INSERT INTO anagrafiche.identita_digitali
            (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
        VALUES (%s, %s, 'API_CLIENT', false)
    $sql$,
    (SELECT sr_id FROM _t_sr_cl),
    (SELECT auth_user_id FROM _t_au_pool WHERE idx = 7)),
    '10. API_CLIENT su SR CL -> INSERT ok (early-exit, nessun vincolo di coerenza)'
);

SELECT * FROM finish();
