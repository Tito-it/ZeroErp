-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test FUNZIONALE RLS multi-policy — vendite.ordini
--
-- Brief RLS §5/§11. ordini ha TRE policy PERMISSIVE (combinate in OR),
-- ciascuna gated sul proprio ruolo_applicativo:
--   - rls_ordini_cliente_ownership (CLIENTE_PORTALE, per soggetto_ruolo)
--   - rls_ordini_shop              (SHOP_CUSTOMER, canale SHOP)
--   - rls_ordini_ef_whitelist      (OPERATORE, per emittente_fiscale_id)
-- Obiettivo: dimostrare che un OPERATORE vede solo per emittente e NON
-- eredita visibilita' dalle policy cliente/shop (e viceversa il gate per
-- ruolo isola le facce).
--
-- Meccanismo identico a test-rls-fatture-ef-whitelist-functional.sql:
-- ENABLE+FORCE locale alla tx (titodb owner non-superuser -> soggetto),
-- GUC via set_config, fattura/ordine ESISTENTE (no fixture pesante),
-- soft-skip se mancano dati.
--
-- Indice test (1..5) — visibilita' di un ordine noto:
--   1. OPERATORE, whitelist = emittente ordine  -> visibile (policy EF)
--   2. OPERATORE, whitelist = ALTRO emittente    -> NON visibile
--      (EF fallisce; cliente/shop gated off -> nessun leak)
--   3. CLIENTE_PORTALE, identita non proprietaria-> NON visibile
--      (policy cliente non concede; EF gated off) -> "non eredita"
--   4. nessun ruolo (GUC vuoto)                   -> NON visibile (fail-closed)
--   5. DISABLE RLS (kill-switch)                  -> di nuovo visibile
-- ------------------------------------------------------------

BEGIN;
SELECT plan(5);

-- Ordine ESISTENTE con emittente risolvibile (emittente_fiscale_id e' PK
-- diretta su emittenti_fiscali -> NOT NULL garantisce l'esistenza).
CREATE TEMP TABLE _refs AS
WITH o AS (
    SELECT id AS ordine_id, emittente_fiscale_id AS emit_pk, soggetto_ruolo_id
      FROM vendite.ordini
     WHERE emittente_fiscale_id IS NOT NULL
     ORDER BY id
     LIMIT 1
)
SELECT o.ordine_id, o.emit_pk, o.soggetto_ruolo_id,
       (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
         WHERE ef.id <> o.emit_pk ORDER BY ef.id LIMIT 1) AS other_pk
  FROM o;

-- Operatore di test (auth_user + soggetto PF + SR RIS_UMANA + identita OPERATORE).
CREATE TEMP TABLE _op (auth_user_id int, identita_id bigint);
DO $fix$
DECLARE v_uid int; v_sog uuid; v_sr bigint; v_idn bigint;
BEGIN
    INSERT INTO django.auth_user (username, password, is_active, is_staff,
        is_superuser, first_name, last_name, email, date_joined)
    VALUES ('_pgtap_rls_ord_' || substring(md5(clock_timestamp()::text) from 1 for 8),
        '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_uid;

    v_sog := anagrafiche.fn_crea_soggetto_pf(
        p_cognome := 'PnzTestScopeEf', p_nome := 'Fdn',
        p_codice_fiscale := 'PNZFDN78A01L219Y',
        p_email := 'pgtap_rls_ord_' || substring(md5(clock_timestamp()::text) from 1 for 6) || '@test.local',
        p_data_nascita := DATE '1978-01-01', p_sesso := 'M', p_stato_iso2 := 'IT',
        p_comune_nascita_id := (SELECT id FROM config.comuni ORDER BY id LIMIT 1),
        p_tipo_contatto_id := NULL);
    v_sr := script.fn_get_or_create_soggetto_ruolo(p_soggetto_id := v_sog, p_cd_int_ruolo := 'RIS_UMANA');
    INSERT INTO anagrafiche.identita_digitali (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    VALUES (v_sr, v_uid, 'OPERATORE', true) RETURNING id INTO v_idn;
    INSERT INTO _op VALUES (v_uid, v_idn);
END $fix$;

CREATE TEMP TABLE _flags AS
SELECT COALESCE(
    (SELECT ordine_id IS NOT NULL AND emit_pk IS NOT NULL AND other_pk IS NOT NULL
       FROM _refs LIMIT 1), false) AS prereq;

-- RLS gia' ENABLED (Ondata 2-A); aggiungo FORCE locale per assoggettare
-- l'owner titodb (non-superuser). Rollback ripristina lo stato committato.
ALTER TABLE vendite.ordini ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.ordini FORCE  ROW LEVEL SECURITY;

CREATE TEMP TABLE _res (caso text, visibile boolean);

-- c1: OPERATORE, whitelist = emittente ordine -> visibile
DO $c1$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    DELETE FROM config.user_emittenti_fiscali WHERE auth_user_id = (SELECT auth_user_id FROM _op);
    INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
    VALUES ((SELECT auth_user_id FROM _op), (SELECT emit_pk FROM _refs)) ON CONFLICT DO NOTHING;
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op)::text, true);
    INSERT INTO _res SELECT 'c1', EXISTS (SELECT 1 FROM vendite.ordini WHERE id = (SELECT ordine_id FROM _refs));
END $c1$;

-- c2: OPERATORE, whitelist = ALTRO emittente -> NON visibile (no leak cliente/shop)
DO $c2$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    DELETE FROM config.user_emittenti_fiscali WHERE auth_user_id = (SELECT auth_user_id FROM _op);
    INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
    VALUES ((SELECT auth_user_id FROM _op), (SELECT other_pk FROM _refs)) ON CONFLICT DO NOTHING;
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op)::text, true);
    INSERT INTO _res SELECT 'c2', EXISTS (SELECT 1 FROM vendite.ordini WHERE id = (SELECT ordine_id FROM _refs));
END $c2$;

-- c3: CLIENTE_PORTALE con identita NON proprietaria -> NON visibile (non eredita)
DO $c3$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    -- whitelist match (irrilevante: ef policy gated off perche' ruolo != OPERATORE)
    PERFORM set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);
    PERFORM set_config('app.current_identita_id', (SELECT identita_id FROM _op)::text, true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op)::text, true);
    INSERT INTO _res SELECT 'c3', EXISTS (SELECT 1 FROM vendite.ordini WHERE id = (SELECT ordine_id FROM _refs));
END $c3$;

-- c4: nessun ruolo -> NON visibile (fail-closed)
DO $c4$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_identita_id', '', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op)::text, true);
    INSERT INTO _res SELECT 'c4', EXISTS (SELECT 1 FROM vendite.ordini WHERE id = (SELECT ordine_id FROM _refs));
END $c4$;

-- c5: DISABLE RLS (kill-switch) -> di nuovo visibile
ALTER TABLE vendite.ordini NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.ordini DISABLE ROW LEVEL SECURITY;
INSERT INTO _res
SELECT 'c5', EXISTS (SELECT 1 FROM vendite.ordini WHERE id = (SELECT ordine_id FROM _refs));

-- Asserzioni (soft-skip se prereq mancante)
SELECT ok((SELECT NOT prereq FROM _flags) OR      (SELECT visibile FROM _res WHERE caso='c1'),
    '1. OPERATORE whitelist = emittente ordine -> visibile (policy EF)');
SELECT ok((SELECT NOT prereq FROM _flags) OR  NOT (SELECT visibile FROM _res WHERE caso='c2'),
    '2. OPERATORE whitelist = altro emittente -> NON visibile (no leak cliente/shop)');
SELECT ok((SELECT NOT prereq FROM _flags) OR  NOT (SELECT visibile FROM _res WHERE caso='c3'),
    '3. CLIENTE_PORTALE identita non proprietaria -> NON visibile (non eredita)');
SELECT ok((SELECT NOT prereq FROM _flags) OR  NOT (SELECT visibile FROM _res WHERE caso='c4'),
    '4. nessun ruolo -> NON visibile (fail-closed)');
SELECT ok((SELECT NOT prereq FROM _flags) OR      (SELECT visibile FROM _res WHERE caso='c5'),
    '5. DISABLE RLS (kill-switch) -> ordine di nuovo visibile');

SELECT * FROM finish();
ROLLBACK;
