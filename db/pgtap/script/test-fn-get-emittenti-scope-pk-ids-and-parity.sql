-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
--   file pescava fra i dati ESISTENTI l'operatore con whitelist, il super
--   admin e l'utente senza identita', e quando non li trovava rispondeva
--   `true` con l'etichetta «skip se no fixture»: su un database ricostruito dai
--   changelog era VERDE PER SOTTRAZIONE — sei asserzioni, nessuna eseguita.
--   Ora i tre soggetti si costruiscono (due aziende con
--   `dbops.fn_pgtap_crea_emittente_operatore()`, un binding SUPER_ADMIN, un
--   auth_user nudo) e i rami «skip» non esistono piu'.
CREATE TEMP TABLE _mondi AS
SELECT 'CTX' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'SA'  AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

DO $lega$ BEGIN PERFORM config.fn_lega_profilo_identita((SELECT id FROM config.profili_accesso WHERE codice = 'SUPER_ADMIN'), (SELECT identita_id FROM _mondi WHERE lato = 'SA')); END $lega$;

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'CTX'));
END $ctx$;

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
-- Setup: i tre soggetti, letti dalle aziende costruite
-- (operatore con whitelist per i test 2/3/6, super admin per il 4,
-- utente senza identita' OPERATORE per il 5)
-- ============================================================
CREATE TEMP TABLE _t_user_with_ef AS
SELECT m.auth_user_id AS user_id FROM _mondi m WHERE m.lato = 'CTX';

CREATE TEMP TABLE _t_super_admin AS
SELECT m.auth_user_id AS user_id FROM _mondi m WHERE m.lato = 'SA';

-- Un auth_user nudo: attivo, ma senza nessuna identita' digitale.
CREATE TEMP TABLE _t_no_operatore AS
WITH ins AS (
    INSERT INTO django.auth_user
        (username, password, is_active, is_staff, is_superuser,
         first_name, last_name, email, date_joined)
    VALUES ('_pgtap_parity_nudo_' || substring(md5(clock_timestamp()::text) from 1 for 8),
            '!', true, false, false, '', '', '', now())
    RETURNING id
)
SELECT id AS user_id FROM ins;

-- ============================================================
-- 2) Operatore con whitelist -> _pk_ids ritorna array di PK reali
-- ============================================================
SELECT ok(
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
     )) = 0,
    '2. Operatore con whitelist -> _pk_ids ritorna array di PK reali validi'
);

-- ============================================================
-- 3) Parity cardinalita _pk_ids vs _sr_ids per stesso utente
-- ============================================================
SELECT is(
    cardinality(
      script.fn_get_emittenti_scope_pk_ids(
        (SELECT user_id FROM _t_user_with_ef)
      )
    ),
    cardinality(
      script.fn_get_emittenti_scope_sr_ids(
        (SELECT user_id FROM _t_user_with_ef)
      )
    ),
    '3. Parity cardinalita: _pk_ids e _sr_ids hanno stesso numero di elementi per stesso utente'
);

-- ============================================================
-- 4) Parity NULL: super admin -> entrambe NULL
-- ============================================================
SELECT ok(
    script.fn_get_emittenti_scope_pk_ids((SELECT user_id FROM _t_super_admin)) IS NULL
    AND
    script.fn_get_emittenti_scope_sr_ids((SELECT user_id FROM _t_super_admin)) IS NULL,
    '4. Parity NULL: super admin -> entrambe ritornano NULL'
);

-- ============================================================
-- 5) Parity '{}': utente senza identita OPERATORE -> entrambe '{}'
-- ============================================================
SELECT ok(
    script.fn_get_emittenti_scope_pk_ids((SELECT user_id FROM _t_no_operatore))
        = '{}'::bigint[]
    AND
    script.fn_get_emittenti_scope_sr_ids((SELECT user_id FROM _t_no_operatore))
        = '{}'::bigint[],
    '5. Parity []: utente senza identita OPERATORE -> entrambe ritornano ''{}'''
);

-- ============================================================
-- 6) Mapping correttezza: ogni PK in _pk_ids ha la sua SR id in _sr_ids
--    (verifica che il wrapper _sr_ids mappi correttamente).
--    Test: per ogni PK in _pk_ids, la SR id corrispondente
--    (via emittenti_fiscali.soggetto_ruolo_id) deve essere in _sr_ids.
-- ============================================================
SELECT ok(
    (SELECT count(*) FROM unnest(
        script.fn_get_emittenti_scope_pk_ids((SELECT user_id FROM _t_user_with_ef))
     ) AS pk
     WHERE NOT (
       (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef WHERE ef.id = pk)
       = ANY(script.fn_get_emittenti_scope_sr_ids((SELECT user_id FROM _t_user_with_ef)))
     )) = 0,
    '6. Mapping correttezza: ogni PK in _pk_ids ha la sua SR id in _sr_ids'
);

SELECT * FROM finish();
ROLLBACK;
