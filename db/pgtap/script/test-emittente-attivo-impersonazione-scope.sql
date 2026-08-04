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
--    7. p_auth_user_id NULL (job batch) con emittente attivo -> true
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
SELECT plan(10);

-- ============================================================
-- Fixture: utenti ed emittenti reali del database.
-- Niente skip condizionali: se la fixture manca il test 1 fallisce,
-- perche' un file verde per assenza di dati e' peggio di un file rosso.
-- ============================================================
CREATE TEMP TABLE _fx_sa AS
SELECT au.id AS user_id
  FROM django.auth_user au
 WHERE au.is_active = true
   AND script.fn_is_super_admin(au.id)
 ORDER BY au.id
 LIMIT 1;

CREATE TEMP TABLE _fx_op AS
SELECT au.id AS user_id,
       uef.emittente_fiscale_id AS ef_suo
  FROM django.auth_user au
  JOIN anagrafiche.identita_digitali idg
    ON idg.auth_user_id      = au.id
   AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND idg.attivo            = true
  JOIN config.user_emittenti_fiscali uef
    ON uef.auth_user_id = au.id
 WHERE au.is_active = true
   AND NOT script.fn_is_super_admin(au.id)
 ORDER BY au.id
 LIMIT 1;

-- X = emittente su cui si impersona, Y = un altro emittente qualsiasi.
CREATE TEMP TABLE _fx_ef AS
SELECT (SELECT min(ef.id) FROM anagrafiche.emittenti_fiscali ef) AS ef_x,
       (SELECT max(ef.id) FROM anagrafiche.emittenti_fiscali ef) AS ef_y;

-- ef_altro = un emittente diverso da quello in whitelist all'operatore.
CREATE TEMP TABLE _fx_op_altro AS
SELECT ef.id AS ef_altro
  FROM anagrafiche.emittenti_fiscali ef
 WHERE ef.id <> (SELECT ef_suo FROM _fx_op)
 ORDER BY ef.id
 LIMIT 1;

-- ============================================================
-- 1) Preflight fixture
-- ============================================================
SELECT ok(
    (SELECT count(*) FROM _fx_sa) = 1
    AND (SELECT count(*) FROM _fx_op) = 1
    AND (SELECT count(*) FROM _fx_op_altro) = 1
    AND (SELECT ef_x FROM _fx_ef) IS DISTINCT FROM (SELECT ef_y FROM _fx_ef),
    '1. Fixture presenti: un super admin, un operatore con whitelist, due emittenti distinti'
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
-- 7) Job batch: p_auth_user_id NULL non si auto-blocca
-- ============================================================
DO $$
BEGIN
    PERFORM set_config('app.current_emittente_id',
                       (SELECT ef_x FROM _fx_ef)::text, true);
END $$;

SELECT ok(
    script.fn_check_user_emittente_scope(NULL, (SELECT ef_y FROM _fx_ef)) IS TRUE,
    '7. Job batch (auth_user_id NULL) con emittente attivo: true, non si auto-blocca'
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
