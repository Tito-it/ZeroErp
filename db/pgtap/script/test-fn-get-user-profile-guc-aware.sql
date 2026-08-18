-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_user_profile - top-level ruolo_applicativo
-- GUC-aware (post migration 20260421-05).
--
-- Contesto:
--   Fix bug §13.7 pr-b-shop-b2c: utente multi-veste
--   (OPERATORE + CLIENTE_PORTALE) loggato su canale portale
--   riceveva top-level='OPERATORE' invece di 'CLIENTE_PORTALE'
--   perche' il campo veniva popolato dall'identita OPERATORE
--   caricata dalla query iniziale, ignorando il contesto di sessione.
--   Post-fix il top-level legge app.ruolo_applicativo con fallback
--   all'identita OPERATORE (tool/cron/psql).
--
-- Semantica attesa:
--   - GUC app.ruolo_applicativo popolata -> top-level = GUC
--   - GUC vuota/assente -> top-level = ruolo_applicativo dell'identita
--     OPERATORE caricata (fallback legacy)
--   - User senza identita OPERATORE -> raise E_ADMIN_VALIDAZIONE
--     (comportamento pre-fix preservato)
--
-- Indice test (1..4):
--    1. Multi-veste + GUC=CLIENTE_PORTALE -> top-level=CLIENTE_PORTALE
--    2. GUC vuota + user con identita OPERATORE -> top-level=OPERATORE
--    3. Single-veste OPERATORE + GUC=OPERATORE -> top-level=OPERATORE
--    4. Regressione: GUC vuota + user senza OPERATORE -> raise
--       E_ADMIN_VALIDAZIONE
--
-- Fixture: uso tid (auth_user_id=1) che ha identita OPERATORE via
-- seed 20260419-95. Per il caso multi-veste aggiungo un'identita
-- CLIENTE_PORTALE su un SR-CL libero. Per il caso 4 creo un fresh
-- auth_user + identita CLIENTE_PORTALE (senza OPERATORE).
--
-- BEGIN + ROLLBACK isolamento completo.
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

-- =========================================================
-- Setup: tid (auth_user_id=1) esiste con identita OPERATORE.
-- Recupero un SR-CL libero per aggiungere un'identita
-- CLIENTE_PORTALE collegata allo stesso auth_user.
-- =========================================================
CREATE TEMP TABLE _t_tid AS
SELECT 1::int AS auth_user_id;

CREATE TEMP TABLE _t_sr_cl_libero AS
WITH sr_liberi AS (
    SELECT DISTINCT sr.id AS sr_id
      FROM anagrafiche.clienti        c
      JOIN anagrafiche.soggetti_ruoli sr ON sr.id = c.soggetto_ruolo_id
      JOIN anagrafiche.soggetti       s  ON s.id = sr.soggetto_id
     WHERE s.attivo = true
       AND NOT EXISTS (
           SELECT 1
             FROM anagrafiche.identita_digitali id
            WHERE id.soggetto_ruolo_id = sr.id
              AND id.attivo = true
       )
)
SELECT sr_id
  FROM sr_liberi
 ORDER BY sr_id
 LIMIT 1;

-- Aggiungo identita CLIENTE_PORTALE a tid (setup multi-veste).
-- L'insert scatta il guard coerenza; se il SR-CL e' gia' un cliente
-- valido con soggetto attivo, il guard passa. Skip-friendly se il
-- pool SR-CL liberi e' vuoto.
DO $pgtap$
DECLARE
    v_sr_cl bigint;
BEGIN
    SELECT sr_id INTO v_sr_cl FROM _t_sr_cl_libero;
    IF v_sr_cl IS NULL THEN
        RAISE NOTICE 'Nessun SR-CL libero: test 1 usera'' skip';
        RETURN;
    END IF;

    -- 🔴 PULIZIA D'INGRESSO, aggiunta il 2026-08-18.
    --   Il test crea la SECONDA veste dell'utente 1 (multi-veste: OPERATORE +
    --   CLIENTE_PORTALE) per verificare che la GUC scelga quale prevale. Ma
    --   `uq_identita_digitali_auth_user_ruolo` e' unica su
    --   (auth_user_id, ruolo_applicativo), e in sviluppo quella veste ORA
    --   ESISTE gia' come dato vero: l'INSERT moriva e con lui l'intero file.
    --   ⚠️ La fixture dava per scontato che nessuno avesse gia' quella veste.
    --   Il file e' transazionale: l'identita' vera torna al ROLLBACK.
    DELETE FROM anagrafiche.identita_digitali
     WHERE auth_user_id = 1
       AND ruolo_applicativo = 'CLIENTE_PORTALE'::config.ruolo_applicativo;

    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    VALUES (v_sr_cl, 1, 'CLIENTE_PORTALE', true);
END
$pgtap$;

-- =========================================================
-- 1) Multi-veste + GUC=CLIENTE_PORTALE -> top-level=CLIENTE_PORTALE
-- =========================================================
SET LOCAL app.ruolo_applicativo = 'CLIENTE_PORTALE';

SELECT CASE
    WHEN EXISTS (SELECT 1 FROM _t_sr_cl_libero)
    THEN is(
        (script.fn_get_user_profile(1) ->> 'ruolo_applicativo'),
        'CLIENTE_PORTALE',
        '1. Multi-veste + GUC=CLIENTE_PORTALE -> top-level=CLIENTE_PORTALE'
    )
    ELSE skip('Nessun SR-CL libero: setup multi-veste non possibile', 1)
END;

-- =========================================================
-- 2) GUC vuota + user con identita OPERATORE -> top-level=OPERATORE
-- =========================================================
-- SET LOCAL a '' simula GUC non settata (NULLIF('','')=NULL).
SET LOCAL app.ruolo_applicativo = '';

SELECT is(
    (script.fn_get_user_profile(1) ->> 'ruolo_applicativo'),
    'OPERATORE',
    '2. GUC vuota + user con identita OPERATORE -> top-level=OPERATORE (fallback)'
);

-- =========================================================
-- 3) Single-veste OPERATORE + GUC=OPERATORE -> top-level=OPERATORE
-- =========================================================
-- Rimuovo l'identita CLIENTE_PORTALE aggiunta dal setup per simulare
-- single-veste (solo OPERATORE). DELETE perche' UPDATE attivo=false
-- scatenerebbe altro trigger; in transazione BEGIN il DELETE e'
-- rollbackato.
DELETE FROM anagrafiche.identita_digitali
 WHERE auth_user_id = 1
   AND ruolo_applicativo = 'CLIENTE_PORTALE'::config.ruolo_applicativo;

SET LOCAL app.ruolo_applicativo = 'OPERATORE';

SELECT is(
    (script.fn_get_user_profile(1) ->> 'ruolo_applicativo'),
    'OPERATORE',
    '3. Single-veste OPERATORE + GUC=OPERATORE -> top-level=OPERATORE'
);

-- =========================================================
-- 4) Regressione: GUC vuota + user senza identita OPERATORE
--    -> raise E_ADMIN_VALIDAZIONE (guard invariato).
-- =========================================================
-- Creo fresh auth_user + identita CLIENTE_PORTALE (senza OPERATORE).
-- Uso un SR-CL ancora libero (potrebbe non esserci se pool esiguo).
CREATE TEMP TABLE _t_sr_cl_libero_2 AS
WITH sr_liberi AS (
    SELECT DISTINCT sr.id AS sr_id
      FROM anagrafiche.clienti        c
      JOIN anagrafiche.soggetti_ruoli sr ON sr.id = c.soggetto_ruolo_id
      JOIN anagrafiche.soggetti       s  ON s.id = sr.soggetto_id
     WHERE s.attivo = true
       AND NOT EXISTS (
           SELECT 1
             FROM anagrafiche.identita_digitali id
            WHERE id.soggetto_ruolo_id = sr.id
              AND id.attivo = true
       )
)
SELECT sr_id
  FROM sr_liberi
 ORDER BY sr_id
 LIMIT 1;

CREATE TEMP TABLE _t_au_portale_only (auth_user_id int);
DO $pgtap$
DECLARE
    v_au     int;
    v_sr_cl  bigint;
BEGIN
    SELECT sr_id INTO v_sr_cl FROM _t_sr_cl_libero_2;
    IF v_sr_cl IS NULL THEN
        RETURN;
    END IF;

    INSERT INTO django.auth_user
        (username, password, is_active, is_staff, is_superuser,
         first_name, last_name, email, date_joined)
    VALUES
        ('_pgtap_profile_portale_only_' || substring(md5(clock_timestamp()::text) from 1 for 8),
         '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_au;

    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    VALUES (v_sr_cl, v_au, 'CLIENTE_PORTALE', true);

    INSERT INTO _t_au_portale_only (auth_user_id) VALUES (v_au);
END
$pgtap$;

SET LOCAL app.ruolo_applicativo = '';

SELECT CASE
    WHEN EXISTS (SELECT 1 FROM _t_au_portale_only)
    THEN throws_ok(
        format(
            $sql$ SELECT script.fn_get_user_profile(%L::int) $sql$,
            (SELECT auth_user_id FROM _t_au_portale_only)
        ),
        NULL,
        NULL,
        '4. Regressione: user senza identita OPERATORE -> raise E_ADMIN_VALIDAZIONE'
    )
    ELSE skip('Nessun SR-CL libero: setup portale-only non possibile', 1)
END;

SELECT * FROM finish();
ROLLBACK;
