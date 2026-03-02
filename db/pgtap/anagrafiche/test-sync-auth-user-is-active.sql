-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test sync auth_user.is_active:
--
--   Funzione fn_sync_auth_user_is_active:
--     1. Precondizione: qualifica DIPENDENTE esiste
--     2. Precondizione: soggetto gestore esiste
--     3. Precondizione: auth_user disponibile
--     4. Setup: risorsa umana gestore + bridge + auth_user attivo
--     5. fn_sync con risorsa attiva + bridge attivo -> is_active = true
--     6. fn_sync con risorsa disattivata -> is_active = false
--     7. fn_sync riattivazione risorsa -> is_active = true
--     8. fn_sync con bridge disattivato -> is_active = false
--     9. fn_sync riattivazione bridge -> is_active = true
--    10. fn_sync risorsa senza bridge -> return false (noop)
--
--   Trigger sync (1.2, 1.3):
--    11. UPDATE risorse_umane_auth_user.attivo = false -> auth_user.is_active = false
--    12. UPDATE risorse_umane_auth_user.attivo = true  -> auth_user.is_active = true
--    13. UPDATE risorse_umane.valido_al nel passato -> auth_user.is_active = false
--    14. UPDATE risorse_umane.attivo = false -> auth_user.is_active = false
--    15. Riattivazione risorse_umane + bridge -> auth_user.is_active = true
--
--   Funzione fn_sync_auth_user_expired:
--    16. Setup: risorsa con valido_al ieri + auth_user forzato attivo
--    17. fn_sync_auth_user_expired -> disattiva l'utente, return >= 1
--    18. auth_user.is_active = false dopo batch
--
-- Nota ATTIVO framework:
--   Il trigger trg_risorse_umane_a10_risorse_umane_auth_user_block_deact_upd
--   (trgfn_prevent_deactivate_if_children) impedisce la disattivazione del
--   padre (risorse_umane) se esistono figli attivi in risorse_umane_auth_user.
--   Il trigger trg_risorse_umane_auth_user_a10_risorse_umane_require_at_*
--   (trgfn_child_requires_active_parent) impedisce l'attivazione del bridge
--   se il padre non e' attivo.
--   I test rispettano questi vincoli: disattivazione child-first,
--   riattivazione parent-first.
-- ------------------------------------------------------------

SELECT plan(18);

-- =========================================================
-- 1) Precondizione: esiste la qualifica DIPENDENTE
-- =========================================================
CREATE TEMP TABLE _t_qualifica AS
SELECT id AS qualifica_id
  FROM config.qualifiche
 WHERE codice_interno = 'DIPENDENTE'
 LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM _t_qualifica) = 1,
    '1. Esiste la qualifica DIPENDENTE in config.qualifiche'
);

-- =========================================================
-- 2) Precondizione: soggetto gestore esiste
-- =========================================================
CREATE TEMP TABLE _t_soggetto_gestore AS
SELECT sr.soggetto_id
  FROM anagrafiche.gestori g
  JOIN anagrafiche.soggetti_ruoli sr
    ON sr.id = g.soggetto_ruolo_id
 ORDER BY sr.soggetto_id
 LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM _t_soggetto_gestore) = 1,
    '2. Trovato soggetto gestore per test'
);

-- =========================================================
-- 3) Setup: auth_user di test dedicato
-- =========================================================
-- Crea un auth_user dedicato per il test (rollback automatico a fine transazione)
WITH ins AS (
    INSERT INTO django.auth_user (
        username, password, is_active, is_staff, is_superuser,
        first_name, last_name, email, date_joined
    )
    VALUES (
        '_pgtap_sync_' || md5(clock_timestamp()::text),
        '!', true, false, false,
        '', '', '', now()
    )
    RETURNING id
)
SELECT id AS auth_user_id
INTO TEMP TABLE _t_auth_user
FROM ins;

SELECT ok(
    (SELECT count(*) FROM _t_auth_user) = 1,
    '3. Creato auth_user di test per collegamento'
);

-- =========================================================
-- 4) Setup: risorsa umana gestore + bridge
-- =========================================================
CREATE TEMP TABLE _t_soggetto_ruolo AS
SELECT script.fn_get_or_create_soggetto_ruolo(
    p_soggetto_id  := (SELECT soggetto_id FROM _t_soggetto_gestore),
    p_cd_int_ruolo := 'RIS_UMANA'
) AS soggetto_ruolo_id;

-- Inserisci o recupera risorsa umana
WITH ins AS (
    INSERT INTO anagrafiche.risorse_umane (
        soggetto_ruolo_id,
        soggetto_id,
        qualifica_id,
        valido_dal,
        attivo
    )
    SELECT
        sr.soggetto_ruolo_id,
        sg.soggetto_id,
        q.qualifica_id,
        CURRENT_DATE,
        true
    FROM _t_soggetto_gestore sg,
         _t_soggetto_ruolo sr,
         _t_qualifica q
    WHERE NOT EXISTS (
        SELECT 1
          FROM anagrafiche.risorse_umane ru
         WHERE ru.soggetto_ruolo_id = sr.soggetto_ruolo_id
    )
    RETURNING id
)
SELECT COALESCE(
    (SELECT id FROM ins),
    (
        SELECT ru.id
          FROM anagrafiche.risorse_umane ru
          JOIN _t_soggetto_ruolo sr
            ON ru.soggetto_ruolo_id = sr.soggetto_ruolo_id
    )
) AS id
INTO TEMP TABLE _t_risorsa;

-- Assicuriamo che la risorsa sia attiva e senza scadenza
UPDATE anagrafiche.risorse_umane
   SET attivo = true,
       valido_dal = CURRENT_DATE,
       valido_al = NULL
 WHERE id = (SELECT id FROM _t_risorsa);

-- Inserisci bridge (se non esiste gia')
INSERT INTO anagrafiche.risorse_umane_auth_user (
    risorsa_umana_id,
    auth_user_id,
    attivo
)
SELECT
    r.id,
    au.auth_user_id,
    true
FROM _t_risorsa r,
     _t_auth_user au
WHERE NOT EXISTS (
    SELECT 1
      FROM anagrafiche.risorse_umane_auth_user rau
     WHERE rau.risorsa_umana_id = r.id
)
ON CONFLICT DO NOTHING;

-- Rilegge l'auth_user effettivamente collegato nel bridge.
-- Se il bridge esisteva da un run precedente, _t_auth_user puntava a un
-- auth_user diverso; senza questo step fn_sync aggiornerebbe l'auth_user
-- nel bridge mentre il test controllerebbe quello appena creato.
TRUNCATE _t_auth_user;
INSERT INTO _t_auth_user (auth_user_id)
SELECT rau.auth_user_id
  FROM anagrafiche.risorse_umane_auth_user rau
 WHERE rau.risorsa_umana_id = (SELECT id FROM _t_risorsa);

-- Assicuriamo auth_user attivo
UPDATE django.auth_user
   SET is_active = true
 WHERE id = (SELECT auth_user_id FROM _t_auth_user);

SELECT ok(
    EXISTS (
        SELECT 1
          FROM anagrafiche.risorse_umane_auth_user rau
         WHERE rau.risorsa_umana_id = (SELECT id FROM _t_risorsa)
    ),
    '4. Setup: bridge risorsa-auth_user creato'
);

-- =========================================================
-- 5) fn_sync: risorsa attiva + bridge attivo -> is_active true
-- =========================================================
SELECT anagrafiche.fn_sync_auth_user_is_active((SELECT id FROM _t_risorsa));

SELECT ok(
    (SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _t_auth_user)) = true,
    '5. fn_sync: risorsa attiva + bridge attivo -> is_active = true'
);

-- =========================================================
-- 6) fn_sync: risorsa disattivata -> is_active false
-- =========================================================
-- Per disattivare il padre dobbiamo prima disattivare il figlio
-- (vincolo ATTIVO/BLOCK: trgfn_prevent_deactivate_if_children)
UPDATE anagrafiche.risorse_umane_auth_user
   SET attivo = false
 WHERE risorsa_umana_id = (SELECT id FROM _t_risorsa);

UPDATE anagrafiche.risorse_umane
   SET attivo = false
 WHERE id = (SELECT id FROM _t_risorsa);

-- Forza is_active = true per testare la funzione pura
UPDATE django.auth_user
   SET is_active = true
 WHERE id = (SELECT auth_user_id FROM _t_auth_user);

SELECT anagrafiche.fn_sync_auth_user_is_active((SELECT id FROM _t_risorsa));

SELECT ok(
    (SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _t_auth_user)) = false,
    '6. fn_sync: risorsa disattivata -> is_active = false'
);

-- =========================================================
-- 7) fn_sync: riattivazione risorsa -> is_active true
-- =========================================================
-- Riattivazione: prima il padre, poi il figlio
-- (vincolo ATTIVO/REQUIRE: trgfn_child_requires_active_parent)
UPDATE anagrafiche.risorse_umane
   SET attivo = true
 WHERE id = (SELECT id FROM _t_risorsa);

UPDATE anagrafiche.risorse_umane_auth_user
   SET attivo = true
 WHERE risorsa_umana_id = (SELECT id FROM _t_risorsa);

SELECT anagrafiche.fn_sync_auth_user_is_active((SELECT id FROM _t_risorsa));

SELECT ok(
    (SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _t_auth_user)) = true,
    '7. fn_sync: riattivazione risorsa -> is_active = true'
);

-- =========================================================
-- 8) fn_sync: bridge disattivato -> is_active false
-- =========================================================
UPDATE anagrafiche.risorse_umane_auth_user
   SET attivo = false
 WHERE risorsa_umana_id = (SELECT id FROM _t_risorsa);

-- Riporto is_active a true per testare la funzione pura
UPDATE django.auth_user SET is_active = true WHERE id = (SELECT auth_user_id FROM _t_auth_user);

SELECT anagrafiche.fn_sync_auth_user_is_active((SELECT id FROM _t_risorsa));

SELECT ok(
    (SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _t_auth_user)) = false,
    '8. fn_sync: bridge disattivato -> is_active = false'
);

-- =========================================================
-- 9) fn_sync: riattivazione bridge -> is_active true
-- =========================================================
UPDATE anagrafiche.risorse_umane_auth_user
   SET attivo = true
 WHERE risorsa_umana_id = (SELECT id FROM _t_risorsa);

SELECT anagrafiche.fn_sync_auth_user_is_active((SELECT id FROM _t_risorsa));

SELECT ok(
    (SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _t_auth_user)) = true,
    '9. fn_sync: riattivazione bridge -> is_active = true'
);

-- =========================================================
-- 10) fn_sync: risorsa senza bridge -> noop (return false)
-- =========================================================
-- Uso un ID fittizio di risorsa che non ha bridge
SELECT ok(
    anagrafiche.fn_sync_auth_user_is_active(
        (SELECT COALESCE(MAX(id), 0) + 99999 FROM anagrafiche.risorse_umane)
    ) = false,
    '10. fn_sync: risorsa senza bridge -> return false'
);

-- =========================================================
-- TRIGGER TESTS (1.2, 1.3)
-- Ripristino stato pulito
-- =========================================================
UPDATE anagrafiche.risorse_umane
   SET attivo = true, valido_dal = CURRENT_DATE, valido_al = NULL
 WHERE id = (SELECT id FROM _t_risorsa);

UPDATE anagrafiche.risorse_umane_auth_user
   SET attivo = true
 WHERE risorsa_umana_id = (SELECT id FROM _t_risorsa);

UPDATE django.auth_user
   SET is_active = true
 WHERE id = (SELECT auth_user_id FROM _t_auth_user);

-- =========================================================
-- 11) Trigger 1.3: UPDATE bridge.attivo = false -> is_active false
-- =========================================================
UPDATE anagrafiche.risorse_umane_auth_user
   SET attivo = false
 WHERE risorsa_umana_id = (SELECT id FROM _t_risorsa);

SELECT ok(
    (SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _t_auth_user)) = false,
    '11. Trigger 1.3: bridge.attivo = false -> is_active = false'
);

-- =========================================================
-- 12) Trigger 1.3: UPDATE bridge.attivo = true -> is_active true
-- =========================================================
UPDATE anagrafiche.risorse_umane_auth_user
   SET attivo = true
 WHERE risorsa_umana_id = (SELECT id FROM _t_risorsa);

SELECT ok(
    (SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _t_auth_user)) = true,
    '12. Trigger 1.3: bridge.attivo = true -> is_active = true'
);

-- =========================================================
-- 13) Trigger 1.2: valido_al nel passato -> is_active false
-- =========================================================
UPDATE anagrafiche.risorse_umane
   SET valido_dal = CURRENT_DATE - INTERVAL '30 days',
       valido_al = CURRENT_DATE - INTERVAL '1 day'
 WHERE id = (SELECT id FROM _t_risorsa);

SELECT ok(
    (SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _t_auth_user)) = false,
    '13. Trigger 1.2: valido_al nel passato -> is_active = false'
);

-- Ripristino finestra temporale
UPDATE anagrafiche.risorse_umane
   SET valido_dal = CURRENT_DATE,
       valido_al = NULL
 WHERE id = (SELECT id FROM _t_risorsa);

-- =========================================================
-- 14) Trigger 1.2: risorse_umane.attivo = false -> is_active false
-- =========================================================
-- Disattivazione child-first (vincolo ATTIVO/BLOCK)
UPDATE anagrafiche.risorse_umane_auth_user
   SET attivo = false
 WHERE risorsa_umana_id = (SELECT id FROM _t_risorsa);

-- Forza is_active = true per isolare l'effetto del trigger 1.2
UPDATE django.auth_user
   SET is_active = true
 WHERE id = (SELECT auth_user_id FROM _t_auth_user);

UPDATE anagrafiche.risorse_umane
   SET attivo = false
 WHERE id = (SELECT id FROM _t_risorsa);

SELECT ok(
    (SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _t_auth_user)) = false,
    '14. Trigger 1.2: risorse_umane.attivo = false -> is_active = false'
);

-- =========================================================
-- 15) Trigger 1.2 + 1.3: riattivazione -> is_active true
-- =========================================================
-- Riattivazione parent-first (vincolo ATTIVO/REQUIRE)
UPDATE anagrafiche.risorse_umane
   SET attivo = true
 WHERE id = (SELECT id FROM _t_risorsa);

UPDATE anagrafiche.risorse_umane_auth_user
   SET attivo = true
 WHERE risorsa_umana_id = (SELECT id FROM _t_risorsa);

SELECT ok(
    (SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _t_auth_user)) = true,
    '15. Trigger 1.2 + 1.3: riattivazione parent + bridge -> is_active = true'
);

-- =========================================================
-- BATCH TEST (fn_sync_auth_user_expired)
-- =========================================================

-- =========================================================
-- 16) Setup: risorsa con valido_al ieri + auth_user forzato attivo
-- =========================================================
UPDATE anagrafiche.risorse_umane
   SET valido_dal = CURRENT_DATE - INTERVAL '30 days',
       valido_al = CURRENT_DATE - INTERVAL '1 day'
 WHERE id = (SELECT id FROM _t_risorsa);

-- Forza auth_user attivo per testare la batch
UPDATE django.auth_user
   SET is_active = true
 WHERE id = (SELECT auth_user_id FROM _t_auth_user);

SELECT ok(
    (SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _t_auth_user)) = true,
    '16. Setup: auth_user forzato attivo con risorsa scaduta'
);

-- =========================================================
-- 17) fn_sync_auth_user_expired -> disattiva e ritorna >= 1
-- =========================================================
SELECT ok(
    anagrafiche.fn_sync_auth_user_expired() >= 1,
    '17. fn_sync_auth_user_expired: disattiva utente scaduto, return >= 1'
);

-- Verifica che l'utente sia stato effettivamente disattivato
SELECT ok(
    (SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _t_auth_user)) = false,
    '18. fn_sync_auth_user_expired: auth_user.is_active = false dopo batch'
);

SELECT * FROM finish();
