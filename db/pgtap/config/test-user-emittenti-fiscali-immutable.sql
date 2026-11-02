-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: immutabilita' di config.user_emittenti_fiscali
--       - trigger a10_lock_emittente_upd (script.trgfn_lock_columns)
--       - trigger a10_guard_delete_dlt   (config.trgfn_user_emittenti_fiscali_guard_delete)
--
-- Elenco test:
--  1) UPDATE su emittente_fiscale_id -> bloccato
--  2) DELETE su utente attivo -> bloccato (E_USER_EMITTENTE_DELETE_VIETATO)
--  3) DELETE su utente con override GUC -> consentito
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

SELECT plan(3);

-- ============================================================
-- Setup contesto
-- ============================================================
CREATE TEMP TABLE tmp_imm_ctx AS
SELECT
    ef.id AS emittente_pk
FROM anagrafiche.emittenti_fiscali ef
WHERE ef.attivo = true
ORDER BY ef.id
LIMIT 2;

-- Servono almeno 2 emittenti attivi per testare l'UPDATE su un id diverso.
-- Se ce n'e' uno solo riusiamo lo stesso (l'UPDATE allora avviene su stesso
-- valore e il trigger lock_columns NON solleva: quel test diventa skip soft).

-- 🔴 RIFERIMENTO MORTO, corretto il 2026-08-18.
--   Questa query filtrava su `rau.ruolo_sistema <> 'DISABILITATO'`. La colonna
--   NON ESISTE PIU': il cutover multi-face-auth (2026-04-19) ha archiviato la
--   tabella in `_legacy_risorse_umane_auth_user` e l'ha sostituita con una
--   VISTA che legge da `identita_digitali`, dove quel concetto e' `attivo`.
--
--   ⚠️ L'effetto non era «un test rosso»: era un test che eseguiva ZERO
--   asserzioni su 3. Moriva qui, prima di arrivarci — e siccome il file stava
--   in baseline-rossi.tsv, il runner taceva. L'immutabilita' di
--   config.user_emittenti_fiscali non era verificata da nessuno da mesi,
--   proprio mentre quella tabella veniva toccata (20260818-12, -13).
--
--   ⭐ Il predicato non viene sostituito con un equivalente: viene TOLTO.
--   `au.is_active` + `rau.attivo` dicono gia' «utente utilizzabile» nel modello
--   nuovo, e inventare un terzo filtro sarebbe una regola in piu' che nessuno
--   ha chiesto.
-- Dalla madre identita_digitali (12-09-2026: la vista risorse_umane_auth_user
-- e' stata ritirata; `rau.attivo` era `identita_digitali.attivo`).
CREATE TEMP TABLE tmp_imm_user AS
SELECT au.id AS user_id
FROM django.auth_user au
JOIN anagrafiche.identita_digitali i ON i.auth_user_id = au.id
WHERE au.is_active = true
  AND i.ruolo_applicativo = 'OPERATORE'
  AND i.attivo = true
ORDER BY au.id
LIMIT 1;

-- Pulizia preventiva (con override per saltare il guard delete)
SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
WHERE auth_user_id = (SELECT user_id FROM tmp_imm_user);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

-- Inserimento associazione iniziale (sul primo EF disponibile)
INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
SELECT (SELECT user_id FROM tmp_imm_user),
       (SELECT emittente_pk FROM tmp_imm_ctx ORDER BY emittente_pk LIMIT 1);

-- ============================================================
-- 1) UPDATE su emittente_fiscale_id -> bloccato
-- ============================================================
SELECT throws_like(
    $$ UPDATE config.user_emittenti_fiscali
          SET emittente_fiscale_id = (
              SELECT coalesce(
                  (SELECT emittente_pk FROM tmp_imm_ctx
                    WHERE emittente_pk <> (
                        SELECT emittente_fiscale_id
                          FROM config.user_emittenti_fiscali
                         WHERE auth_user_id = (SELECT user_id FROM tmp_imm_user)
                    )
                    LIMIT 1),
                  -1::bigint
              )
          )
        WHERE auth_user_id = (SELECT user_id FROM tmp_imm_user) $$,
    -- rev 2026-09-26: la frase del codice DEDICATO (E_EMITTENTE_NON_MODIFICABILE).
    --   Prima era '%emittente%', che passava anche col messaggio generico di
    --   E_CODICE_NON_MODIFICABILE perche' il NOME DELLA COLONNA contiene
    --   «emittente»: verde per coincidenza, e dev e CI rispondevano con due
    --   codici diversi (brief-db-lock-di-colonna-fuori-registro).
    '%emittente fiscale di un operatore%',
    'UPDATE su emittente_fiscale_id -> bloccato dal lock di colonna con E_EMITTENTE_NON_MODIFICABILE'
);

-- ============================================================
-- 2) DELETE con utente attivo -> bloccato
-- ============================================================
SELECT throws_like(
    $$ DELETE FROM config.user_emittenti_fiscali
        WHERE auth_user_id = (SELECT user_id FROM tmp_imm_user) $$,
    '%Eliminazione vietata%',
    'DELETE su utente attivo -> bloccato (E_USER_EMITTENTE_DELETE_VIETATO)'
);

-- ============================================================
-- 3) DELETE con override GUC -> consentito
-- ============================================================
SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';

SELECT lives_ok(
    $$ DELETE FROM config.user_emittenti_fiscali
        WHERE auth_user_id = (SELECT user_id FROM tmp_imm_user) $$,
    'DELETE con override GUC -> consentito'
);

SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

SELECT * FROM finish();
ROLLBACK;
