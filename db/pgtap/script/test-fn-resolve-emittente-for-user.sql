-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_resolve_emittente_for_user
--       Resolver "emittente fiscale di un utente" (modello 1-a-1).
--
-- Elenco test:
--  1) param NULL  -> solleva E_PARAMETRO_INVALIDO
--  2) param <= 0  -> solleva E_PARAMETRO_INVALIDO
--  3) user inesistente -> ritorna NULL (no raise)
--  4) user con 1 riga in user_emittenti_fiscali -> ritorna PK emittente
--  5) user senza riga (admin globale) -> ritorna NULL
-- ------------------------------------------------------------

BEGIN;

SELECT plan(5);

SET LOCAL zeroerp.allow_lock_columns_override = 'on';
SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';

-- ============================================================
-- Setup contesto: serve almeno un emittente attivo nel DB di sviluppo
-- ============================================================
CREATE TEMP TABLE tmp_resolve_ctx AS
SELECT
    ef.id              AS emittente_pk,
    ef.soggetto_ruolo_id AS emittente_sr_id
FROM anagrafiche.emittenti_fiscali ef
WHERE ef.attivo = true
ORDER BY ef.id
LIMIT 1;

CREATE TEMP TABLE tmp_resolve_user AS
SELECT au.id AS user_id
FROM django.auth_user au
JOIN anagrafiche.risorse_umane_auth_user rau ON rau.auth_user_id = au.id
WHERE au.is_active = true
  AND rau.attivo = true
  AND rau.ruolo_sistema <> 'DISABILITATO'::config.ruolo_sistema
ORDER BY au.id
LIMIT 1;

-- ============================================================
-- 1) param NULL -> throws E_PARAMETRO_INVALIDO
-- ============================================================
SELECT throws_like(
    $$ SELECT script.fn_resolve_emittente_for_user(NULL) $$,
    '%p_auth_user_id%',
    'fn_resolve_emittente_for_user(NULL) solleva errore parametro invalido'
);

-- ============================================================
-- 2) param <= 0 -> throws E_PARAMETRO_INVALIDO
-- ============================================================
SELECT throws_like(
    $$ SELECT script.fn_resolve_emittente_for_user(-1) $$,
    '%p_auth_user_id%',
    'fn_resolve_emittente_for_user(-1) solleva errore parametro invalido'
);

-- ============================================================
-- 3) user inesistente -> ritorna NULL
-- ============================================================
SELECT is(
    script.fn_resolve_emittente_for_user(99999999),
    NULL::bigint,
    'utente inesistente -> NULL'
);

-- ============================================================
-- 4) user con 1 riga in user_emittenti_fiscali -> PK emittente
-- ============================================================
DELETE FROM config.user_emittenti_fiscali
WHERE auth_user_id = (SELECT user_id FROM tmp_resolve_user);

INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
SELECT (SELECT user_id FROM tmp_resolve_user),
       (SELECT emittente_pk FROM tmp_resolve_ctx);

SELECT is(
    script.fn_resolve_emittente_for_user((SELECT user_id FROM tmp_resolve_user)),
    (SELECT emittente_pk FROM tmp_resolve_ctx),
    'user con 1 riga su EF attivo -> PK emittente corretto'
);

-- ============================================================
-- 5) user senza riga (admin globale) -> ritorna NULL
-- ============================================================
DELETE FROM config.user_emittenti_fiscali
WHERE auth_user_id = (SELECT user_id FROM tmp_resolve_user);

SELECT is(
    script.fn_resolve_emittente_for_user((SELECT user_id FROM tmp_resolve_user)),
    NULL::bigint,
    'user senza riga (admin globale) -> NULL'
);

SELECT * FROM finish();
ROLLBACK;
