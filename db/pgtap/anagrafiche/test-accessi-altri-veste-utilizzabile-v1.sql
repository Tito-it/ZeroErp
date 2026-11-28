-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: nella lista «Altri accessi» ogni veste dice, accanto al suo stato, se
--       apre la porta oggi (utilizzabile, da script.fn_veste_utilizzabile);
--       lo stato resta il ciclo di vita della veste, e ATTIVO vuol dire accesa
-- ChangeSet: 20261127-43 (vw_accessi_altri, la chiave utilizzabile),
--            20261127-44 (il COMMENT di fn_veste_utilizzabile)
-- Brief: brief-db-accessi-area-clienti, giro 3 (S64)
--
-- Gira come l'applicazione (runner di default). Le vesti le inserisce l'app
-- spente, come il backend; le accende e le data la fixture
-- dbops.fn_pgtap_imposta_veste, l'unica strada dell'app dopo il 20261127-09.
--
-- ⚠️ Due condizioni della regola non si costruiscono qui, e si dichiarano:
--   - il soggetto spento: un soggetto che ha un soggetto_ruolo non si
--     disattiva (guard «figli prima»), e una veste ha sempre un ruolo;
--   - il rapporto chiuso dell'operatore: una credenziale con una veste
--     OPERATORE non sta in questa vista (categoria OPERATORE).
--   La regola intera la prova script/test-fn-veste-utilizzabile-v1; qui si
--   prova che la vista la legge da li', e non la ricopia (1).
-- Le date sono relative alla data operativa: nessuna data fissa che scade.
--
-- Elenco test (plan 6):
--    1) la vista legge script.fn_veste_utilizzabile (forma: la regola ha una
--       sede sola)
--    2) accesa e nelle sue date: ATTIVO, utilizzabile
--    3) accesa e scaduta ieri: ATTIVO, non utilizzabile
--    4) accesa e valida da domani: ATTIVO, non utilizzabile
--    5) spenta: DISATTIVO, non utilizzabile
--    6) il riassunto stato_accesso della veste scaduta resta ATTIVO: lo stato
--       non guarda le date, le guarda utilizzabile
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- Fixture
-- ============================================================
-- Due ruoli cliente: una veste accesa per ruolo e tipo
-- (uq_identita_digitali_sr_ruolo_attivo).
CREATE TEMP TABLE _cli1 AS
SELECT c.soggetto_ruolo_id AS sr_id FROM dbops.fn_pgtap_crea_cliente_ba('g3-s64') c;
CREATE TEMP TABLE _cli2 AS
SELECT c.soggetto_ruolo_id AS sr_id FROM dbops.fn_pgtap_crea_cliente_ba('g3-s64-bis') c;
SET CONSTRAINTS ALL IMMEDIATE;

-- Una credenziale nuda, con un nome che non collide.
CREATE OR REPLACE FUNCTION pg_temp.credenziale(p_nome text) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE v_id integer;  -- ⚠️ niente %TYPE su django.*
BEGIN
    INSERT INTO django.auth_user (username, password, is_active, is_staff, is_superuser,
                                  first_name, last_name, email, date_joined)
    VALUES ('_pgtap_g3_' || p_nome || '_' || substring(md5(clock_timestamp()::text) FROM 1 FOR 8),
            '!', false, false, false, '', '', '', now())
    RETURNING id INTO v_id;
    RETURN v_id;
END $$;

-- Una credenziale per caso, con una veste sola: la credenziale e la veste
-- si chiamano come il caso.
CREATE TEMP TABLE _v (nome text PRIMARY KEY, auth_user_id integer, identita_id bigint);

CREATE OR REPLACE FUNCTION pg_temp.veste(p_nome text, p_sr bigint, p_ruolo text, p_campi jsonb)
RETURNS void
LANGUAGE plpgsql AS $$
DECLARE
    v_auth anagrafiche.identita_digitali.auth_user_id%TYPE := pg_temp.credenziale(p_nome);
    v_id   anagrafiche.identita_digitali.id%TYPE;
BEGIN
    INSERT INTO anagrafiche.identita_digitali (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    VALUES (p_sr, v_auth, p_ruolo::config.ruolo_applicativo, false)
    RETURNING id INTO v_id;
    PERFORM dbops.fn_pgtap_imposta_veste(v_id, p_campi);
    INSERT INTO _v VALUES (p_nome, v_auth, v_id);
END $$;

SELECT pg_temp.veste('ok', (SELECT sr_id FROM _cli1), 'CLIENTE_PORTALE',
    jsonb_build_object('attivo', true, 'valido_dal', script.fn_data_operativa() - 10, 'valido_al', NULL));
SELECT pg_temp.veste('scaduta', (SELECT sr_id FROM _cli2), 'CLIENTE_PORTALE',
    jsonb_build_object('attivo', true, 'valido_dal', script.fn_data_operativa() - 10,
                       'valido_al', script.fn_data_operativa() - 1));
SELECT pg_temp.veste('futura', (SELECT sr_id FROM _cli1), 'SHOP_CUSTOMER',
    jsonb_build_object('attivo', true, 'valido_dal', script.fn_data_operativa() + 1, 'valido_al', NULL));
SELECT pg_temp.veste('spenta', (SELECT sr_id FROM _cli2), 'SHOP_CUSTOMER',
    jsonb_build_object('valido_dal', script.fn_data_operativa() - 10, 'valido_al', NULL));

-- La voce della veste nella vista, e la riga della sua credenziale.
CREATE OR REPLACE FUNCTION pg_temp.voce(p_nome text) RETURNS jsonb
LANGUAGE sql AS $$
    SELECT e
      FROM anagrafiche.vw_accessi_altri v
      CROSS JOIN LATERAL jsonb_array_elements(v.vesti) e
      JOIN _v ON _v.nome = p_nome
     WHERE v.auth_user_id = _v.auth_user_id
       AND (e ->> 'identita_id')::bigint = _v.identita_id
$$;

-- ============================================================
-- 1 La forma
-- ============================================================
-- ⚠️ Per OID, non sul testo: pg_get_viewdef toglie lo schema che sta nel
-- search_path di chi legge (l'app ha script, l'owner no), e la stessa vista
-- si scrive in due modi. La regola di riscrittura della vista dipende dalla
-- funzione in pg_depend, qualunque sia il ruolo.
SELECT ok(
    EXISTS (SELECT 1
              FROM pg_depend d
              JOIN pg_rewrite r ON r.oid = d.objid
             WHERE d.classid    = 'pg_rewrite'::regclass
               AND r.ev_class   = 'anagrafiche.vw_accessi_altri'::regclass
               AND d.refclassid = 'pg_proc'::regclass
               AND d.refobjid   = 'script.fn_veste_utilizzabile(bigint)'::regprocedure),
    '1) la vista legge script.fn_veste_utilizzabile: la regola ha una sede sola');

-- ============================================================
-- 2-5 Le vesti
-- ============================================================
SELECT is(
    (SELECT jsonb_build_object('stato', e -> 'stato', 'utilizzabile', e -> 'utilizzabile') FROM pg_temp.voce('ok') e),
    '{"stato": "ATTIVO", "utilizzabile": true}'::jsonb,
    '2) accesa e nelle sue date: ATTIVO, utilizzabile');

SELECT is(
    (SELECT jsonb_build_object('stato', e -> 'stato', 'utilizzabile', e -> 'utilizzabile') FROM pg_temp.voce('scaduta') e),
    '{"stato": "ATTIVO", "utilizzabile": false}'::jsonb,
    '3) accesa e scaduta ieri: ATTIVO, non utilizzabile');

SELECT is(
    (SELECT jsonb_build_object('stato', e -> 'stato', 'utilizzabile', e -> 'utilizzabile') FROM pg_temp.voce('futura') e),
    '{"stato": "ATTIVO", "utilizzabile": false}'::jsonb,
    '4) accesa e valida da domani: ATTIVO, non utilizzabile');

SELECT is(
    (SELECT jsonb_build_object('stato', e -> 'stato', 'utilizzabile', e -> 'utilizzabile') FROM pg_temp.voce('spenta') e),
    '{"stato": "DISATTIVO", "utilizzabile": false}'::jsonb,
    '5) spenta: DISATTIVO, non utilizzabile');

-- ============================================================
-- 6 Il riassunto
-- ============================================================
SELECT is(
    (SELECT v.stato_accesso
       FROM anagrafiche.vw_accessi_altri v
       JOIN _v ON _v.auth_user_id = v.auth_user_id
      WHERE _v.nome = 'scaduta'),
    'ATTIVO',
    '6) il riassunto della credenziale con la sola veste scaduta resta ATTIVO');

SELECT * FROM finish();
ROLLBACK;
