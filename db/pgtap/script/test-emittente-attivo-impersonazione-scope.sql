-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: impersonazione di scope emittente (GUC app.current_emittente_id)
--   su script.fn_check_user_emittente_scope, fn_get_emittenti_scope_pk_ids,
--   fn_get_emittenti_scope_sr_ids, fn_resolve_emittente_for_user,
--   fn_check_user_can_create_ba e sull'adapter fn_scope_ef_whitelist_via_sr.
--
-- Origine: brief-db-impersonazione-scope-emittente.md §4.5 (casi 1..8) e §8.10
--   (casi aggiunti dalla verifica DB).
--
-- Indice test (1..10):
--    1. Preflight fixture: super admin, operatore con whitelist, 2 emittenti
--    2. Super admin SENZA emittente attivo -> _pk_ids NULL e check true
--       (nessuna regressione: e' il comportamento di oggi)
--    3. Super admin con emittente attivo X -> _pk_ids = {X}
--    4. Super admin con emittente attivo X -> check(X) true, check(Y) FALSE
--    5. Operatore con emittente attivo su un emittente NON suo ->
--       _pk_ids '{}' e check false  ** INVARIANTE DI SICUREZZA **
--    6. Operatore con emittente attivo sul proprio emittente -> invariato
--    7. p_auth_user_id NULL con emittente attivo -> FALSE (rev 2026-10-04, Q-1:
--       era true, «job batch»; un utente NULL non vede niente)
--    8. Adapter _via_sr con soggetto_ruolo non mappato + emittente attivo ->
--       false (fail-closed: IS DISTINCT FROM, non <>)
--    9. Emittente attivo INESISTENTE -> _pk_ids '{}' E _sr_ids '{}'
--       ** REGRESSIONE FAIL-OPEN: array_agg su zero righe ritorna NULL **
--   10. fn_resolve_emittente_for_user e fn_check_user_can_create_ba
--       seguono l'emittente attivo del super admin
--
-- Il test 5 e' quello che non deve mai diventare rosso: e' l'invariante
-- «la selezione e' solo restringente, mai allargante» del §2 del brief.
--
-- Il test 9 e' il guardiano del coalesce in fn_get_emittenti_scope_sr_ids:
-- se torna rosso, qualcuno l'ha tolto e la mappatura a vuoto e' di nuovo
-- «vede tutto».
--
-- COPERTURA RLS. Non c'e' un test end-to-end su vendite.fatture (caso 8 del
-- §4.5 del brief) perche' richiede SET ROLE e il runner RLS dedicato. E'
-- accettabile qui perche' tutte e 11 le policy RLS con ruolo OPERATORE
-- delegano ai cinque adapter fn_scope_ef_whitelist*, che a loro volta
-- delegano alla canonica: il test 8 verifica proprio quella catena.
--
-- IMPORTANTE: nessun SAVEPOINT/ROLLBACK TO SAVEPOINT (rompe state pgTAP).
-- La GUC e' impostata con set_config(..., is_local => true): muore col
-- ROLLBACK finale.
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
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (2026-09-12). Fino a quel giorno il
--   file pescava fra i dati ESISTENTI un super admin, un operatore con
--   whitelist e due emittenti: su un database ricostruito dai changelog non
--   c'e' niente di tutto questo, e il file moriva nella fixture — l'invariante
--   «la selezione e' solo restringente» (test 5) restava collaudato solo su
--   dbdev. Tre aziende con `dbops.fn_pgtap_crea_emittente_operatore()`, PRIMA
--   di aprire il contesto: CTX (il contesto), OP (l'operatore con whitelist),
--   SA (che diventa super admin con un binding al profilo SUPER_ADMIN).
--   Niente skip condizionali: se la fixture manca il test 1 fallisce, perche'
--   un file verde per assenza di dati e' peggio di un file rosso.
CREATE TEMP TABLE _mondi AS
SELECT 'CTX' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'OP'  AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'SA'  AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

DO $lega$ BEGIN PERFORM config.fn_lega_profilo_identita((SELECT id FROM config.profili_accesso WHERE codice = 'SUPER_ADMIN'), (SELECT identita_id FROM _mondi WHERE lato = 'SA')); END $lega$;

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'CTX'));
END $ctx$;

SELECT plan(10);

-- ============================================================
-- Fixture: i ruoli del test, letti dalle aziende costruite
-- ============================================================
CREATE TEMP TABLE _fx_sa AS
SELECT m.auth_user_id AS user_id FROM _mondi m WHERE m.lato = 'SA';

CREATE TEMP TABLE _fx_op AS
SELECT m.auth_user_id AS user_id,
       m.emittente_fiscale_id AS ef_suo
  FROM _mondi m WHERE m.lato = 'OP';

-- X = emittente su cui si impersona, Y = un altro emittente: due aziende
-- diverse da quella dell'operatore.
CREATE TEMP TABLE _fx_ef AS
SELECT (SELECT m.emittente_fiscale_id FROM _mondi m WHERE m.lato = 'CTX') AS ef_x,
       (SELECT m.emittente_fiscale_id FROM _mondi m WHERE m.lato = 'SA')  AS ef_y;

-- ef_altro = un emittente diverso da quello in whitelist all'operatore.
CREATE TEMP TABLE _fx_op_altro AS
SELECT m.emittente_fiscale_id AS ef_altro FROM _mondi m WHERE m.lato = 'CTX';

-- ============================================================
-- 1) Preflight fixture
-- ============================================================
SELECT ok(
    script.fn_is_super_admin((SELECT user_id FROM _fx_sa))
    AND NOT script.fn_is_super_admin((SELECT user_id FROM _fx_op))
    AND (SELECT ef_suo FROM _fx_op) IS NOT NULL
    AND (SELECT ef_altro FROM _fx_op_altro) IS DISTINCT FROM (SELECT ef_suo FROM _fx_op)
    AND (SELECT ef_x FROM _fx_ef) IS DISTINCT FROM (SELECT ef_y FROM _fx_ef),
    '1. Fixture costruita: un super admin, un operatore con whitelist, due emittenti distinti'
);

-- ============================================================
-- 2) Super admin SENZA emittente attivo: comportamento di oggi
-- ============================================================
DO $$ BEGIN PERFORM set_config('app.current_emittente_id', '', true); END $$;

SELECT ok(
    script.fn_get_emittenti_scope_pk_ids((SELECT user_id FROM _fx_sa)) IS NULL
    AND script.fn_check_user_emittente_scope(
            (SELECT user_id FROM _fx_sa), (SELECT ef_x FROM _fx_ef)) IS TRUE,
    '2. Super admin senza emittente attivo: _pk_ids NULL e check true (nessuna regressione)'
);

-- ============================================================
-- 3) Super admin con emittente attivo X: universo ∩ {X} = {X}
-- ============================================================
DO $$
BEGIN
    PERFORM set_config('app.current_emittente_id',
                       (SELECT ef_x FROM _fx_ef)::text, true);
END $$;

SELECT is(
    script.fn_get_emittenti_scope_pk_ids((SELECT user_id FROM _fx_sa)),
    ARRAY[(SELECT ef_x FROM _fx_ef)],
    '3. Super admin con emittente attivo X: _pk_ids = {X} (era NULL = tutto)'
);

-- ============================================================
-- 4) Lo stesso super admin non vede piu' gli altri emittenti
-- ============================================================
SELECT ok(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM _fx_sa), (SELECT ef_x FROM _fx_ef)) IS TRUE
    AND script.fn_check_user_emittente_scope(
        (SELECT user_id FROM _fx_sa), (SELECT ef_y FROM _fx_ef)) IS FALSE,
    '4. Super admin con emittente attivo X: check(X) true, check(Y) false'
);

-- ============================================================
-- 5) INVARIANTE: l'emittente attivo non allarga mai
--    Operatore con whitelist {A} ed emittente attivo su B
-- ============================================================
DO $$
BEGIN
    PERFORM set_config('app.current_emittente_id',
                       (SELECT ef_altro FROM _fx_op_altro)::text, true);
END $$;

SELECT ok(
    script.fn_get_emittenti_scope_pk_ids((SELECT user_id FROM _fx_op)) = '{}'::bigint[]
    AND script.fn_check_user_emittente_scope(
            (SELECT user_id FROM _fx_op),
            (SELECT ef_altro FROM _fx_op_altro)) IS FALSE,
    '5. INVARIANTE: operatore con emittente attivo fuori whitelist -> {} e false (non allarga)'
);

-- ============================================================
-- 6) Operatore con emittente attivo sul PROPRIO emittente: invariato
-- ============================================================
DO $$
BEGIN
    PERFORM set_config('app.current_emittente_id',
                       (SELECT ef_suo FROM _fx_op)::text, true);
END $$;

SELECT ok(
    script.fn_get_emittenti_scope_pk_ids((SELECT user_id FROM _fx_op))
        = ARRAY[(SELECT ef_suo FROM _fx_op)]
    AND script.fn_check_user_emittente_scope(
            (SELECT user_id FROM _fx_op), (SELECT ef_suo FROM _fx_op)) IS TRUE,
    '6. Operatore con emittente attivo sul proprio emittente: invariato'
);

-- ============================================================
-- 7) Utente NULL: nessun accesso, nemmeno con l'emittente attivo
-- ============================================================
-- ⚠️ Rev 2026-10-04 (Q-1, brief-db-esclusioni-implicite): qui si asseriva
--   TRUE («job batch, non si auto-blocca»). La canonica risponde ora FALSE a
--   un utente NULL: le policy restavano chiuse solo per la veste, e con la
--   veste OPERATORE e l'utente vuoto una sessione vedeva tutte le aziende. Chi
--   lavora senza utente e senza RLS (owner, BYPASSRLS) non passa di qui.
DO $$
BEGIN
    PERFORM set_config('app.current_emittente_id',
                       (SELECT ef_x FROM _fx_ef)::text, true);
END $$;

SELECT ok(
    script.fn_check_user_emittente_scope(NULL, (SELECT ef_y FROM _fx_ef)) IS FALSE,
    '7. Utente NULL con emittente attivo: false (era true, «job batch»)'
);

-- ============================================================
-- 8) Adapter _via_sr con riferimento non risolvibile: fail-closed
--    (e' il motivo di IS DISTINCT FROM invece di <>: il subselect
--     dell'adapter passa NULL alla canonica)
-- ============================================================
SELECT ok(
    script.fn_scope_ef_whitelist_via_sr(
        (SELECT user_id FROM _fx_sa),
        -9999999::bigint
    ) IS FALSE,
    '8. Adapter _via_sr con SR non mappato + emittente attivo: false (fail-closed)'
);

-- ============================================================
-- 9) Emittente attivo INESISTENTE: entrambe le gemelle fail-closed.
--    Prima del coalesce, _sr_ids ritornava NULL = "vede tutto".
-- ============================================================
DO $$ BEGIN PERFORM set_config('app.current_emittente_id', '999999999', true); END $$;

SELECT ok(
    script.fn_get_emittenti_scope_pk_ids((SELECT user_id FROM _fx_sa)) = ARRAY[999999999::bigint]
    AND script.fn_get_emittenti_scope_sr_ids((SELECT user_id FROM _fx_sa)) = '{}'::bigint[]
    AND script.fn_check_user_emittente_scope(
            (SELECT user_id FROM _fx_sa), (SELECT ef_x FROM _fx_ef)) IS FALSE,
    '9. Emittente attivo inesistente: _sr_ids ''{}'' (NON NULL) e check false — regressione fail-open'
);

-- ============================================================
-- 10) Dentro quale emittente si crea: resolver e gate dei BA
--     seguono l'emittente attivo del super admin
-- ============================================================
DO $$
BEGIN
    PERFORM set_config('app.current_emittente_id',
                       (SELECT ef_x FROM _fx_ef)::text, true);
END $$;

SELECT ok(
    script.fn_resolve_emittente_for_user((SELECT user_id FROM _fx_sa))
        = (SELECT ef_x FROM _fx_ef)
    AND script.fn_check_user_can_create_ba((SELECT user_id FROM _fx_sa)) IS TRUE,
    '10. Super admin con emittente attivo X: resolver -> X e can_create_ba -> true'
);

SELECT * FROM finish();
ROLLBACK;
