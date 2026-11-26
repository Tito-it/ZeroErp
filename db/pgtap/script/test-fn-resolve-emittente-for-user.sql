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

-- ⛔ Tolta il 2026-11-18 la riga SET LOCAL zeroerp.allow_lock_columns_override = 'on':
--    il file non scrive colonne bloccate, e dal 2026-11-18 la porta si apre solo per
--    la sessione del migratore (script.fn_porta_manutenzione_aperta,
--    brief-db-seed-primo-impianto-non-si-riscrive §16.9). Accesa «per sicurezza»
--    rendeva verdi per sottrazione le asserzioni che toccano un lucchetto.
-- ⛔ Tolta il 2026-11-25 la riga SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on':
--    dal giro 10 (brief-db-porte-aperte-dalla-sola-guc §10) la porta del DELETE si
--    apre solo dal verbo script.fn_change_user_emittenti_scope. La riga di scope si
--    toglie col builder dbops.fn_pgtap_sposta_scope_operatore, che passa da li'.

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

-- ⛔ Rev 2026-11-26 (giro 10-ter, brief-db-porte-aperte-dalla-sola-guc §10-ter, D-AA a):
--   l'operatore si COSTRUISCE, non si cerca fra gli esistenti, e nasce senza
--   azienda (dbops.fn_pgtap_crea_operatore_umano). Fino a oggi il file prendeva il
--   primo operatore attivo e gli toglieva l'azienda col builder: dal 20261125-74
--   l'azienda si toglie solo a un SUPER_ADMIN. Il caso 5, «senza riga», e' il
--   SUPER_ADMIN costruito: l'unico utente per cui la riga mancante e' legittima.
CREATE TEMP TABLE tmp_resolve_user AS
SELECT o.auth_user_id AS user_id
  FROM dbops.fn_pgtap_crea_operatore_umano('resolve-operatore', false) o;

CREATE TEMP TABLE tmp_resolve_sa AS
SELECT o.auth_user_id AS user_id
  FROM dbops.fn_pgtap_crea_operatore_umano('resolve-super-admin', true) o;

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
-- L'operatore costruito nasce senza azienda: la riga la scrive il verbo.
SELECT dbops.fn_pgtap_sposta_scope_operatore((SELECT user_id FROM tmp_resolve_user),
                                             (SELECT emittente_pk FROM tmp_resolve_ctx));

SELECT is(
    script.fn_resolve_emittente_for_user((SELECT user_id FROM tmp_resolve_user)),
    (SELECT emittente_pk FROM tmp_resolve_ctx),
    'user con 1 riga su EF attivo -> PK emittente corretto'
);

-- ============================================================
-- 5) SUPER_ADMIN senza riga (admin globale) -> ritorna NULL
-- ============================================================
SELECT is(
    script.fn_resolve_emittente_for_user((SELECT user_id FROM tmp_resolve_sa)),
    NULL::bigint,
    'user senza riga (admin globale) -> NULL'
);

SELECT * FROM finish();
ROLLBACK;
