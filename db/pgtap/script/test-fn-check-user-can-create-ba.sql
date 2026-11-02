-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

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
-- 🔴 RIFERIMENTO MORTO rimosso il 2026-08-18: `rau.ruolo_sistema` non esiste
--   piu'. Il cutover multi-face-auth (90_end/20260429-19a e -20) ha eliminato
--   la colonna e l'enum `config.ruolo_sistema`, e ha sostituito la tabella con
--   una VISTA su identita_digitali. `au.is_active` + `rau.attivo` dicono gia'
--   «utente utilizzabile» nel modello nuovo: il predicato si TOGLIE, non si
--   sostituisce con un equivalente inventato.
FROM django.auth_user au
JOIN anagrafiche.identita_digitali i ON i.auth_user_id = au.id
WHERE au.is_active = true
  AND i.ruolo_applicativo = 'OPERATORE'
  AND i.attivo = true
ORDER BY au.id
LIMIT 1;
-- (12-09-2026: la vista risorse_umane_auth_user e' stata ritirata; il JOIN e'
--  sulla madre, con il filtro OPERATORE che la vista applicava.)

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
