-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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

SELECT plan(5);

SET LOCAL zeroerp.allow_lock_columns_override = 'on';
SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';

-- Dal 2026-08-04 il resolver guarda PRIMA l'emittente attivo di sessione
-- (GUC app.current_emittente_id, impersonazione di scope). Questi cinque casi
-- descrivono il ramo "riga di configurazione": la GUC va azzerata, altrimenti
-- l'esito dipenderebbe da come e' stata lasciata la sessione.
SET LOCAL app.current_emittente_id = '';

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
-- Fixture rev 2026-08-04: la selezione passava da
-- risorse_umane_auth_user.ruolo_sistema, colonna rimossa dal changeSet
-- 20260429-19a. Da allora il file falliva nel setup e non eseguiva NESSUNA
-- asserzione (baseline: ERRORE_FIXTURE) — copertura zero su una funzione
-- comunque viva. L'equivalente attuale di "utente operativo" e' l'identita
-- digitale OPERATORE attiva, la stessa usata dagli altri test di scope.
SELECT au.id AS user_id
FROM django.auth_user au
JOIN anagrafiche.identita_digitali idg
  ON idg.auth_user_id      = au.id
 AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
 AND idg.attivo            = true
WHERE au.is_active = true
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
