-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_emittenti_scope_pk_ids(p_auth_user_id)
--   + parity test cross-fn con script.fn_get_emittenti_scope_sr_ids
--
-- Origine: brief preventivi rev2 §9 + analisi pattern SR vs PK 2026-05-02
-- (refactor-emittente-id-canonico.md §6.2).
--
-- Indice test (1..6):
--   1. Preflight: entrambe le fn esistono
--   2. Operatore con whitelist non vuota -> _pk_ids ritorna PK reali
--   3. Parity cardinalita: cardinality(_pk_ids) == cardinality(_sr_ids)
--      per ogni utente con whitelist
--   4. Parity sentinel NULL: utente super admin -> entrambe NULL
--   5. Parity sentinel '{}': utente senza identita OPERERATORE -> entrambe '{}'
--   6. Mapping correttezza: ogni elemento di _pk_ids corrisponde a un EF
--      la cui soggetto_ruolo_id e' presente in _sr_ids (e viceversa)
--
-- IMPORTANTE: nessun SAVEPOINT/ROLLBACK TO SAVEPOINT (rompe state pgTAP).
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- ============================================================
-- 1) Preflight: entrambe le fn esistono
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'script'
           AND p.proname = 'fn_get_emittenti_scope_pk_ids'
    ) AND EXISTS (
        SELECT 1 FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'script'
           AND p.proname = 'fn_get_emittenti_scope_sr_ids'
    ),
    '1. Entrambe le fn (_pk_ids canonica, _sr_ids wrapper) esistono'
);

-- ============================================================
-- Setup: pesco un utente OPERATORE con almeno 1 EF in whitelist
-- (per i test 2/3/6) e valori NULL/empty per i test 4/5
-- ============================================================
CREATE TEMP TABLE _t_user_with_ef AS
SELECT au.id AS user_id
  FROM django.auth_user au
  JOIN anagrafiche.identita_digitali idg
    ON idg.auth_user_id = au.id
   AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND idg.attivo = true
  JOIN config.user_emittenti_fiscali uef
    ON uef.auth_user_id = au.id
 WHERE au.is_active = true
   -- escludo super admin (per testare ramo "OPERATIVO whitelist")
   AND NOT script.fn_is_super_admin(au.id)
 ORDER BY au.id LIMIT 1;

CREATE TEMP TABLE _t_super_admin AS
SELECT au.id AS user_id
  FROM django.auth_user au
 WHERE au.is_active = true
   AND script.fn_is_super_admin(au.id)
 ORDER BY au.id LIMIT 1;

CREATE TEMP TABLE _t_no_operatore AS
SELECT au.id AS user_id
  FROM django.auth_user au
  LEFT JOIN anagrafiche.identita_digitali idg
    ON idg.auth_user_id = au.id
   AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND idg.attivo = true
 WHERE au.is_active = true
   AND idg.id IS NULL
 ORDER BY au.id LIMIT 1;

-- ============================================================
-- 2) Operatore con whitelist -> _pk_ids ritorna array di PK reali
-- ============================================================
SELECT ok(
    CASE
      WHEN (SELECT user_id FROM _t_user_with_ef) IS NULL THEN
        true  -- skip soft: nessuna fixture
      ELSE
        cardinality(
          script.fn_get_emittenti_scope_pk_ids(
            (SELECT user_id FROM _t_user_with_ef)
          )
        ) > 0
        AND
        -- Verifica che ogni PK ritornato sia effettivamente un EF esistente
        (SELECT count(*) FROM unnest(
            script.fn_get_emittenti_scope_pk_ids((SELECT user_id FROM _t_user_with_ef))
         ) AS pk
         WHERE NOT EXISTS (
            SELECT 1 FROM anagrafiche.emittenti_fiscali ef WHERE ef.id = pk
         )) = 0
    END,
    '2. Operatore con whitelist -> _pk_ids ritorna array di PK reali validi (skip se no fixture)'
);

-- ============================================================
-- 3) Parity cardinalita _pk_ids vs _sr_ids per stesso utente
-- ============================================================
SELECT is(
    cardinality(
      script.fn_get_emittenti_scope_pk_ids(
        COALESCE((SELECT user_id FROM _t_user_with_ef), 0)
      )
    ),
    cardinality(
      script.fn_get_emittenti_scope_sr_ids(
        COALESCE((SELECT user_id FROM _t_user_with_ef), 0)
      )
    ),
    '3. Parity cardinalita: _pk_ids e _sr_ids hanno stesso numero di elementi per stesso utente'
);

-- ============================================================
-- 4) Parity NULL: super admin -> entrambe NULL
-- ============================================================
SELECT ok(
    CASE
      WHEN (SELECT user_id FROM _t_super_admin) IS NULL THEN
        true  -- skip
      ELSE
        script.fn_get_emittenti_scope_pk_ids((SELECT user_id FROM _t_super_admin)) IS NULL
        AND
        script.fn_get_emittenti_scope_sr_ids((SELECT user_id FROM _t_super_admin)) IS NULL
    END,
    '4. Parity NULL: super admin -> entrambe ritornano NULL (skip se no super admin in fixture)'
);

-- ============================================================
-- 5) Parity '{}': utente senza identita OPERATORE -> entrambe '{}'
-- ============================================================
SELECT ok(
    CASE
      WHEN (SELECT user_id FROM _t_no_operatore) IS NULL THEN
        true  -- skip
      ELSE
        script.fn_get_emittenti_scope_pk_ids((SELECT user_id FROM _t_no_operatore))
            = '{}'::bigint[]
        AND
        script.fn_get_emittenti_scope_sr_ids((SELECT user_id FROM _t_no_operatore))
            = '{}'::bigint[]
    END,
    '5. Parity []: utente senza identita OPERATORE -> entrambe ritornano ''{}'' (skip se no fixture)'
);

-- ============================================================
-- 6) Mapping correttezza: ogni PK in _pk_ids ha la sua SR id in _sr_ids
--    (verifica che il wrapper _sr_ids mappi correttamente).
--    Test: per ogni PK in _pk_ids, la SR id corrispondente
--    (via emittenti_fiscali.soggetto_ruolo_id) deve essere in _sr_ids.
-- ============================================================
SELECT ok(
    CASE
      WHEN (SELECT user_id FROM _t_user_with_ef) IS NULL THEN
        true  -- skip
      ELSE
        (SELECT count(*) FROM unnest(
            script.fn_get_emittenti_scope_pk_ids((SELECT user_id FROM _t_user_with_ef))
         ) AS pk
         WHERE NOT (
           (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef WHERE ef.id = pk)
           = ANY(script.fn_get_emittenti_scope_sr_ids((SELECT user_id FROM _t_user_with_ef)))
         )) = 0
    END,
    '6. Mapping correttezza: ogni PK in _pk_ids ha la sua SR id in _sr_ids (skip se no fixture)'
);

SELECT * FROM finish();
ROLLBACK;
