-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_check_user_can_create_ba
--       Pure check (no raise) per il guard BEFORE INSERT su billing_account.
--
-- Elenco test:
--  1) NULL  -> false (input invalido, no raise)
--  2) -1    -> false
--  3) user con riga in user_emittenti_fiscali -> true (operatore di EF)
--  4) user senza riga, esistono emittenti attivi -> false (admin globale vietato)
--
-- NOTA: il caso "0 emittenti attivi -> true" non e' testabile in modo pulito
-- in pgTAP perche' la disattivazione globale degli EF e' bloccata dai trigger
-- di guardia (children attivi). E' coperto a livello di unit test logica
-- (la funzione conta WHERE attivo=true).
-- ------------------------------------------------------------

BEGIN;

SELECT plan(4);

SET LOCAL zeroerp.allow_lock_columns_override = 'on';
SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';

-- ============================================================
-- 1) NULL -> false
-- ============================================================
SELECT is(
    script.fn_check_user_can_create_ba(NULL),
    false,
    'fn_check_user_can_create_ba(NULL) -> false (no raise)'
);

-- ============================================================
-- 2) -1 -> false
-- ============================================================
SELECT is(
    script.fn_check_user_can_create_ba(-1),
    false,
    'fn_check_user_can_create_ba(-1) -> false'
);

-- ============================================================
-- Setup contesto
-- ============================================================
CREATE TEMP TABLE tmp_check_ctx AS
SELECT
    ef.id AS emittente_pk
FROM anagrafiche.emittenti_fiscali ef
WHERE ef.attivo = true
ORDER BY ef.id
LIMIT 1;

CREATE TEMP TABLE tmp_check_user AS
SELECT au.id AS user_id
FROM django.auth_user au
JOIN anagrafiche.risorse_umane_auth_user rau ON rau.auth_user_id = au.id
WHERE au.is_active = true
  AND rau.attivo = true
  AND rau.ruolo_sistema <> 'DISABILITATO'::config.ruolo_sistema
ORDER BY au.id
LIMIT 1;

-- Pulizia preventiva
DELETE FROM config.user_emittenti_fiscali
WHERE auth_user_id = (SELECT user_id FROM tmp_check_user);

-- ============================================================
-- 3) user con riga -> true
-- ============================================================
INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
SELECT (SELECT user_id FROM tmp_check_user),
       (SELECT emittente_pk FROM tmp_check_ctx);

SELECT is(
    script.fn_check_user_can_create_ba((SELECT user_id FROM tmp_check_user)),
    true,
    'user con riga in user_emittenti_fiscali -> true'
);

-- ============================================================
-- 4) user senza riga, esistono emittenti attivi -> false
-- ============================================================
DELETE FROM config.user_emittenti_fiscali
WHERE auth_user_id = (SELECT user_id FROM tmp_check_user);

SELECT is(
    script.fn_check_user_can_create_ba((SELECT user_id FROM tmp_check_user)),
    false,
    'admin globale + esistono emittenti -> false (vietato creare BA)'
);

SELECT * FROM finish();
ROLLBACK;
