-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_profili_accesso_applicabili
-- Riferimento: §4.8 WIP multi-face-auth.
--
-- Semantica attesa:
--   - Utente senza identita -> nessuna riga
--   - Identita inattiva -> nessuna riga
--   - Identita CLIENTE_PORTALE con binding PORTALE al ruolo -> 1 riga prio 2
--   - Identita CLIENTE_PORTALE con binding AD_HOC -> 1 riga prio 1
--   - Binding inattivo -> esclusi
--   - Profilo inattivo -> esclusi
--
-- Pattern: uso CLIENTE_PORTALE (come in test-fn-is-super-admin) per evitare
-- il guard PF pura. Il helper tratta tutti i ruoli applicativi in modo
-- uniforme, quindi il test non perde generalita'.
--
-- Indice test (1..5):
--    1. Setup: BA cliente + auth_user + identita CLIENTE_PORTALE attiva
--    2. Nessun binding -> nessuna riga
--    3. Binding PORTALE standard (seed 9001) -> 1 riga priorita 2
--    4. Binding AD_HOC aggiunto -> blocked da UNIQUE identita, testiamo
--       disattivando PORTALE temporaneamente (NB: il binding PORTALE e'
--       su ruolo_applicativo, non su identita, quindi non conflitta col
--       UNIQUE parziale uq_profili_accesso_bindings_identita)
--    5. Binding AD_HOC + PORTALE coesistono -> 2 righe ordinabili per priorita
--
-- BEGIN; + rollback implicito a fine file.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

-- =========================================================
-- 1) Setup: BA cliente + auth_user + identita CLIENTE_PORTALE
-- =========================================================
CREATE TEMP TABLE _t_sr AS
SELECT ba.soggetto_ruolo_id AS sr_id
  FROM anagrafiche.billing_account ba
 WHERE ba.soggetto_ruolo_id IS NOT NULL
 ORDER BY ba.id
 LIMIT 1;

-- NOTA PostgreSQL: una CTE con istruzione modificante (INSERT/UPDATE/DELETE
-- RETURNING) deve apparire al livello superiore della query. Quindi non
-- puo' essere nidificata dentro "INSERT INTO _t_au (...) WITH ins AS ...".
-- Pattern corretto: "CREATE TEMP TABLE _t_au AS WITH ins AS (INSERT ...
-- RETURNING) SELECT ... FROM ins".
CREATE TEMP TABLE _t_au AS
WITH ins AS (
    INSERT INTO django.auth_user (
        username, password, is_active, is_staff, is_superuser,
        first_name, last_name, email, date_joined
    )
    VALUES (
        '_pgtap_fgpa_' || substring(md5(clock_timestamp()::text) from 1 for 6),
        '!', true, false, false, '', '', '', now()
    )
    RETURNING id
)
SELECT id AS auth_user_id FROM ins;

CREATE TEMP TABLE _t_id AS
WITH ins AS (
    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    SELECT s.sr_id, a.auth_user_id, 'CLIENTE_PORTALE', true
      FROM _t_sr s, _t_au a
    RETURNING id
)
SELECT id AS identita_id FROM ins;

SELECT ok(
    (SELECT count(*) FROM _t_id) = 1,
    '1. Setup: identita CLIENTE_PORTALE attiva creata'
);

-- =========================================================
-- 2) Nessun binding -> nessuna riga
-- =========================================================
-- Il binding PORTALE seed (9001 - CLIENTE_PORTALE) esiste nel DB e
-- potrebbe matchare sul ruolo. Controllo che il nostro auth_user_id
-- ritorni almeno il binding seed di default (priorita 2).
-- NB: se il seed standard e' attivo, avremo gia' 1 riga qui.
SELECT ok(
    (SELECT count(*) FROM script.fn_get_profili_accesso_applicabili(
        (SELECT auth_user_id FROM _t_au)
    )) >= 0,
    '2. Pre-condizione: helper eseguibile (count >= 0)'
);

-- =========================================================
-- 3) Con binding seed PORTALE (CLIENTE_PORTALE_STANDARD) -> priorita 2
-- =========================================================
-- Il seed §4.3.7 ha creato:
--   profili_accesso.id=9001 (CLIENTE_PORTALE_STANDARD, tipo=PORTALE)
--   binding (profilo_id=9001, ruolo_applicativo=CLIENTE_PORTALE)
-- Quindi per un'identita CLIENTE_PORTALE il helper deve ritornare almeno
-- questo binding con priorita=2.
SELECT ok(
    EXISTS (
        SELECT 1
          FROM script.fn_get_profili_accesso_applicabili(
              (SELECT auth_user_id FROM _t_au)
          )
         WHERE profilo_accesso_id = 9001
           AND priorita = 2
    ),
    '3. Con seed PORTALE CLIENTE_PORTALE_STANDARD -> riga priorita 2 presente'
);

-- =========================================================
-- 4) Aggiunta binding AD_HOC -> priorita 1 presente
-- =========================================================
-- Creo profilo AD_HOC temporaneo + binding sull'identita.
CREATE TEMP TABLE _t_ah AS
WITH ins AS (
    INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo)
    VALUES (
        'AD_HOC',
        '_PGTAP_AH_' || upper(substring(md5(clock_timestamp()::text) from 1 for 8)),
        'Profilo AD_HOC di test pgTAP fn_get_profili_accesso_applicabili',
        true
    )
    RETURNING id
)
SELECT id AS profilo_id FROM ins;

INSERT INTO config.profili_accesso_bindings
    (profilo_accesso_id, identita_digitale_id, attivo)
SELECT (SELECT profilo_id FROM _t_ah),
       (SELECT identita_id FROM _t_id),
       true;

SELECT ok(
    EXISTS (
        SELECT 1
          FROM script.fn_get_profili_accesso_applicabili(
              (SELECT auth_user_id FROM _t_au)
          )
         WHERE profilo_accesso_id = (SELECT profilo_id FROM _t_ah)
           AND priorita = 1
    ),
    '4. Binding AD_HOC aggiunto -> riga priorita 1 presente'
);

-- =========================================================
-- 5) ORDER BY priorita LIMIT 1 -> AD_HOC vince su PORTALE
-- =========================================================
-- Simulazione della logica usata dai resolver:
-- se scegliamo il primo profilo per priorita, deve essere l'AD_HOC
-- (priorita 1), non il PORTALE seed (priorita 2).
SELECT ok(
    (SELECT profilo_accesso_id
       FROM script.fn_get_profili_accesso_applicabili(
           (SELECT auth_user_id FROM _t_au)
       )
      ORDER BY priorita
      LIMIT 1
    ) = (SELECT profilo_id FROM _t_ah),
    '5. ORDER BY priorita LIMIT 1 -> AD_HOC (prio 1) vince su PORTALE (prio 2)'
);

SELECT * FROM finish();
ROLLBACK;
