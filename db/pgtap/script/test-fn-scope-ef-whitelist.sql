-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_scope_ef_whitelist
-- Riferimento: §4.4 WIP multi-face-auth, policy EF_WHITELIST.
--
-- Semantica attesa:
--   - identita inesistente/inattiva     -> false (fail-closed)
--   - identita attiva, whitelist vuota  -> true (accesso globale legacy)
--   - identita attiva, target in lista  -> true
--   - identita attiva, target non lista -> false
--
-- Indice test (1..7):
--    1. Precondizione: fixture emittente_fiscale disponibile
--    2. Setup: soggetto PF pura + SR RIS_UMANA + 2 identita (attiva, inattiva)
--    3. Identita inesistente -> false (fail-closed)
--    4. Identita inattiva (no whitelist) -> false
--    5. Identita attiva, whitelist vuota -> true (accesso globale)
--    6. Setup: popola user_emittenti_fiscali con 1 riga per identita attiva
--    7. Identita attiva, target EF in lista -> true
--    8. Identita attiva, target SR qualsiasi fuori whitelist -> false
--
-- BEGIN; + rollback implicito a fine file (guard DEFERRABLE soggetti
-- non scattano senza COMMIT).
-- ------------------------------------------------------------

BEGIN;
SELECT plan(8);

-- =========================================================
-- 1) Precondizione: un emittente_fiscale disponibile
-- =========================================================
CREATE TEMP TABLE _t_ef AS
SELECT ef.id            AS ef_id,
       ef.soggetto_ruolo_id AS ef_sr_id
  FROM anagrafiche.emittenti_fiscali ef
 WHERE ef.attivo = true
 ORDER BY ef.id
 LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM _t_ef) = 1,
    '1. Precondizione: un emittente_fiscale attivo disponibile'
);

-- =========================================================
-- 2) Setup: soggetto PF pura + SR RIS_UMANA + 2 auth_user + 2 identita
-- =========================================================
CREATE TEMP TABLE _t_comune AS
SELECT id AS comune_id FROM config.comuni ORDER BY id LIMIT 1;

-- CF fisso valido. pgTAP rollbacca a fine file; il CF puo' essere riusato
-- in altri file test senza conflitti (transazioni indipendenti).
CREATE TEMP TABLE _t_sogg_pf AS
SELECT anagrafiche.fn_crea_soggetto_pf(
    p_cognome           := 'PnzTestScopeEf',
    p_nome              := 'Fdn',
    p_codice_fiscale    := 'PNZFDN78A01L219Y',
    p_email             := 'pgtap_scope_ef_' || substring(md5(clock_timestamp()::text) from 1 for 6) || '@test.local',
    p_data_nascita      := DATE '1978-01-01',
    p_sesso             := 'M',
    p_stato_iso2        := 'IT',
    p_comune_nascita_id := (SELECT comune_id FROM _t_comune),
    p_tipo_contatto_id  := NULL
) AS soggetto_id;

CREATE TEMP TABLE _t_sr_ru AS
SELECT script.fn_get_or_create_soggetto_ruolo(
    p_soggetto_id  := (SELECT soggetto_id FROM _t_sogg_pf),
    p_cd_int_ruolo := 'RIS_UMANA'
) AS sr_id;

-- 2 auth_user distinti (uno per identita attiva, uno per inattiva)
CREATE TEMP TABLE _t_au (idx int, auth_user_id int);
DO $$
DECLARE v_i int; v_id int;
BEGIN
    FOR v_i IN 1..2 LOOP
        INSERT INTO django.auth_user (
            username, password, is_active, is_staff, is_superuser,
            first_name, last_name, email, date_joined
        )
        VALUES (
            '_pgtap_scope_ef_' || v_i || '_' || substring(md5(clock_timestamp()::text) from 1 for 6),
            '!', true, false, false, '', '', '', now()
        )
        RETURNING id INTO v_id;
        INSERT INTO _t_au (idx, auth_user_id) VALUES (v_i, v_id);
    END LOOP;
END
$$;

-- Identita attiva (idx=1) e inattiva (idx=2).
-- Entrambe su stesso SR ma attivo mutex via indice parziale: setto
-- attivo=false per l'inattiva, attivo=true per quella attiva.
CREATE TEMP TABLE _t_id (idx int, identita_id bigint);
WITH ins_attiva AS (
    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    SELECT (SELECT sr_id FROM _t_sr_ru),
           (SELECT auth_user_id FROM _t_au WHERE idx = 1),
           'OPERATORE',
           true
    RETURNING id
)
INSERT INTO _t_id (idx, identita_id)
SELECT 1, id FROM ins_attiva;

-- Per l'inattiva, uso un SR diverso per evitare conflitto con UNIQUE parziale
-- (anche se attivo=false, l'INSERT non dovrebbe violare l'indice WHERE attivo=true).
WITH ins_inattiva AS (
    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    SELECT (SELECT sr_id FROM _t_sr_ru),
           (SELECT auth_user_id FROM _t_au WHERE idx = 2),
           'OPERATORE',
           false
    RETURNING id
)
INSERT INTO _t_id (idx, identita_id)
SELECT 2, id FROM ins_inattiva;

SELECT ok(
    (SELECT count(*) FROM _t_id) = 2,
    '2. Setup: 2 identita create (1 attiva, 1 inattiva) su SR RIS_UMANA'
);

-- =========================================================
-- 3) Identita inesistente -> false
-- =========================================================
SELECT ok(
    script.fn_scope_ef_whitelist(
        (SELECT COALESCE(MAX(id), 0) + 999999 FROM anagrafiche.identita_digitali),
        (SELECT ef_sr_id FROM _t_ef)
    ) = false,
    '3. Identita inesistente -> false (fail-closed)'
);

-- =========================================================
-- 4) Identita inattiva -> false
-- =========================================================
SELECT ok(
    script.fn_scope_ef_whitelist(
        (SELECT identita_id FROM _t_id WHERE idx = 2),
        (SELECT ef_sr_id FROM _t_ef)
    ) = false,
    '4. Identita inattiva -> false (fail-closed)'
);

-- =========================================================
-- 5) Identita attiva, whitelist vuota -> true (accesso globale)
-- =========================================================
-- L'auth_user dell'identita attiva NON ha righe in user_emittenti_fiscali,
-- quindi la whitelist e' vuota = accesso globale.
SELECT ok(
    script.fn_scope_ef_whitelist(
        (SELECT identita_id FROM _t_id WHERE idx = 1),
        (SELECT ef_sr_id FROM _t_ef)
    ) = true,
    '5. Identita attiva, whitelist vuota -> true (accesso globale legacy)'
);

-- =========================================================
-- 6) Setup: popola user_emittenti_fiscali per identita attiva
-- =========================================================
INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
VALUES (
    (SELECT auth_user_id FROM _t_au WHERE idx = 1),
    (SELECT ef_id FROM _t_ef)
)
ON CONFLICT DO NOTHING;

SELECT ok(
    EXISTS (
        SELECT 1 FROM config.user_emittenti_fiscali
         WHERE auth_user_id = (SELECT auth_user_id FROM _t_au WHERE idx = 1)
    ),
    '6. Setup: whitelist popolata per identita attiva (1 EF autorizzato)'
);

-- =========================================================
-- 7) Target EF in lista -> true
-- =========================================================
SELECT ok(
    script.fn_scope_ef_whitelist(
        (SELECT identita_id FROM _t_id WHERE idx = 1),
        (SELECT ef_sr_id FROM _t_ef)
    ) = true,
    '7. Identita attiva con whitelist valorizzata, target in lista -> true'
);

-- =========================================================
-- 8) Target fuori whitelist -> false
-- =========================================================
-- Uso il soggetto_ruolo_id della risorsa umana stessa (SR RIS_UMANA) come
-- target: non e' un emittente fiscale, quindi non appare nella whitelist.
-- La funzione cerca match su emittenti_fiscali.soggetto_ruolo_id = p_target,
-- che fallira'.
SELECT ok(
    script.fn_scope_ef_whitelist(
        (SELECT identita_id FROM _t_id WHERE idx = 1),
        (SELECT sr_id FROM _t_sr_ru)
    ) = false,
    '8. Identita attiva con whitelist, target SR non emittente -> false'
);

SELECT * FROM finish();
