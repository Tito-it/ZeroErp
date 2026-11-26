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

-- ⛔ Tolta il 2026-11-18 la riga SET LOCAL zeroerp.allow_lock_columns_override = 'on':
--    il file non scrive colonne bloccate, e dal 2026-11-18 la porta si apre solo per
--    la sessione del migratore (script.fn_porta_manutenzione_aperta,
--    brief-db-seed-primo-impianto-non-si-riscrive §16.9). Accesa «per sicurezza»
--    rendeva verdi per sottrazione le asserzioni che toccano un lucchetto.
-- ⛔ Tolta il 2026-11-25 la riga SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on':
--    dal giro 10 (brief-db-porte-aperte-dalla-sola-guc §10) la porta del DELETE si
--    apre solo dal verbo script.fn_change_user_emittenti_scope. La riga di scope si
--    toglie col builder dbops.fn_pgtap_sposta_scope_operatore, che passa da li'.

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

-- ⛔ Rev 2026-11-26 (giro 10-ter, brief-db-porte-aperte-dalla-sola-guc §10-ter, D-AA a):
--   i due operatori si COSTRUISCONO e nascono senza azienda
--   (dbops.fn_pgtap_crea_operatore_umano). Fino a oggi il file prendeva il primo
--   operatore attivo e gli toglieva l'azienda col builder, prima del 3 e prima del
--   4: dal 20261125-74 l'azienda si toglie solo a un SUPER_ADMIN. Il 3 assegna il
--   primo dal verbo; il 4 prova il secondo, mai assegnato.
CREATE TEMP TABLE tmp_check_user AS
SELECT o.auth_user_id AS user_id
  FROM dbops.fn_pgtap_crea_operatore_umano('can-create-ba-assegnato', false) o;

CREATE TEMP TABLE tmp_check_user_senza AS
SELECT o.auth_user_id AS user_id
  FROM dbops.fn_pgtap_crea_operatore_umano('can-create-ba-senza-azienda', false) o;

-- ============================================================
-- 3) user con riga -> true
-- ============================================================
SELECT dbops.fn_pgtap_sposta_scope_operatore((SELECT user_id FROM tmp_check_user),
                                             (SELECT emittente_pk FROM tmp_check_ctx));

SELECT is(
    script.fn_check_user_can_create_ba((SELECT user_id FROM tmp_check_user)),
    true,
    'user con riga in user_emittenti_fiscali -> true'
);

-- ============================================================
-- 4) operatore senza riga, esistono emittenti attivi -> false
-- ============================================================
SELECT is(
    script.fn_check_user_can_create_ba((SELECT user_id FROM tmp_check_user_senza)),
    false,
    'operatore senza riga + esistono emittenti -> false (vietato creare BA)'
);

SELECT * FROM finish();
ROLLBACK;
