-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-contesto: escluso — la ragione e' scritta per esteso piu' sotto in
--   questo stesso file. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato», che una nota in prosa non fa.
--   ⚠️ Da riguardare: le esclusioni `rls/` furono fatte IN BLOCCO, e almeno
--   una non ne aveva diritto (brief pgtap-runner-rls-baseline §30.2).
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE vendite.fatture ENABLE + FORCE ROW LEVEL SECURITY, locale alla
--   transazione: e' il FORCE a rendere l'owner soggetto alle policy.
-- pgTAP test FUNZIONALE RLS — vendite.fatture (policy EF_WHITELIST)
--
-- Brief RLS §11. A differenza di test-rls-policies-structure.sql (che
-- verifica solo l'ESISTENZA delle policy), questo esercita il RUNTIME.
--
-- Meccanismo (l'utente di test = titodb, owner NON-superuser):
--   - ENABLE + FORCE ROW LEVEL SECURITY locale alla transazione: FORCE
--     assoggetta anche l'owner (titodb) alla RLS, senza bisogno di SET ROLE
--     (titodb non e' superuser, non potrebbe cambiare ruolo). Il ROLLBACK
--     finale annulla ENABLE/FORCE.
--   - GUC simulati via set_config(...,is_local=true); la canonica
--     fn_check_user_emittente_scope e gli helper sono letti con i privilegi
--     di titodb (owner: ha accesso a tutte le tabelle del predicato).
--
-- Fixture LOW-RISK: usa una fattura ESISTENTE (no creazione: FK pesanti).
-- Se mancano fatture / >=2 emittenti -> SOFT-SKIP (i test passano banalmente)
-- cosi' la CI su DB senza dati non rompe.
--
-- >> Eseguito su DB di sviluppo: vedi nota sessione.
--
-- Indice test (1..6) — visibilita' di una fattura nota sotto RLS attiva:
--   1. operatore, whitelist VUOTA            -> visibile (accesso globale)
--   2. operatore, whitelist = emittente fatt -> visibile
--   3. operatore, whitelist = ALTRO emittente-> NON visibile
--   4. ruolo non OPERATORE (gate fallisce)   -> NON visibile
--   5. identita OPERATORE non attiva         -> NON visibile (fail-closed)
--   6. DISABLE RLS (kill-switch)             -> di nuovo visibile
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

SELECT plan(7);

-- =========================================================
-- Fixture: fattura esistente + 2 emittenti + operatore di test
-- =========================================================
-- Scelgo una fattura il cui emittente E' risolvibile (JOIN): evita righe
-- legacy con emittente_soggetto_ruolo_id orfano in emittenti_fiscali.
CREATE TEMP TABLE _refs AS
WITH f AS (
    SELECT fa.id                          AS fattura_id,
           fa.emittente_soggetto_ruolo_id AS emit_sr,
           ef.id                          AS emit_pk
      FROM vendite.fatture fa
      JOIN anagrafiche.emittenti_fiscali ef
        ON ef.soggetto_ruolo_id = fa.emittente_soggetto_ruolo_id
     ORDER BY fa.id
     LIMIT 1
)
SELECT
    f.fattura_id,
    f.emit_sr,
    f.emit_pk,
    (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.id <> f.emit_pk
      ORDER BY ef.id LIMIT 1)             AS other_pk
  FROM f;

-- auth_user + soggetto PF + SR RIS_UMANA + identita OPERATORE attiva.
CREATE TEMP TABLE _op (auth_user_id int, soggetto_id uuid, sr_id bigint, identita_id bigint);

DO $fix$
DECLARE
    v_uid  int;
    v_sog  uuid;
    v_sr   bigint;
    v_idn  bigint;
BEGIN
    INSERT INTO django.auth_user (username, password, is_active, is_staff,
        is_superuser, first_name, last_name, email, date_joined)
    VALUES ('_pgtap_rls_fatt_' || substring(md5(clock_timestamp()::text) from 1 for 8),
        '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_uid;

    -- CF/anagrafica identici al test scope (gia' validati): transazioni
    -- indipendenti con rollback, nessuna collisione.
    v_sog := anagrafiche.fn_crea_soggetto_pf(
        p_cognome           := 'PnzTestScopeEf',
        p_nome              := 'Fdn',
        p_codice_fiscale    := 'PNZFDN78A01L219Y',
        p_email             := 'pgtap_rls_fatt_' || substring(md5(clock_timestamp()::text) from 1 for 6) || '@test.local',
        p_data_nascita      := DATE '1978-01-01',
        p_sesso             := 'M',
        p_stato_iso2        := 'IT',
        p_comune_nascita_id := (SELECT id FROM config.comuni ORDER BY id LIMIT 1),
        p_tipo_contatto_id  := NULL);

    v_sr := script.fn_get_or_create_soggetto_ruolo(
        p_soggetto_id  := v_sog,
        p_cd_int_ruolo := 'RIS_UMANA');

    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    VALUES (v_sr, v_uid, 'OPERATORE', true)
    RETURNING id INTO v_idn;

    INSERT INTO _op VALUES (v_uid, v_sog, v_sr, v_idn);
END
$fix$;

-- prereq: fattura + emittente PK + altro emittente disponibili.
-- COALESCE garantisce SEMPRE una riga booleana (anche se _refs e' vuota).
CREATE TEMP TABLE _flags AS
SELECT COALESCE(
    (SELECT fattura_id IS NOT NULL AND emit_pk IS NOT NULL AND other_pk IS NOT NULL
       FROM _refs LIMIT 1),
    false
) AS prereq;

-- Attiva RLS + FORCE solo dentro questa transazione: FORCE assoggetta
-- l'owner titodb (non-superuser) senza SET ROLE. Rollback annulla tutto.
ALTER TABLE vendite.fatture ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture FORCE  ROW LEVEL SECURITY;

CREATE TEMP TABLE _res (caso text, visibile boolean);

-- ---- Caso 1: whitelist VUOTA -> visibile ----
DO $c1$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    DELETE FROM config.user_emittenti_fiscali WHERE auth_user_id = (SELECT auth_user_id FROM _op);
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op)::text, true);
    INSERT INTO _res SELECT 'c1', EXISTS (SELECT 1 FROM vendite.fatture WHERE id = (SELECT fattura_id FROM _refs));
END $c1$;

-- ---- Caso 2: whitelist = emittente della fattura -> visibile ----
DO $c2$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
    VALUES ((SELECT auth_user_id FROM _op), (SELECT emit_pk FROM _refs)) ON CONFLICT DO NOTHING;
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op)::text, true);
    INSERT INTO _res SELECT 'c2', EXISTS (SELECT 1 FROM vendite.fatture WHERE id = (SELECT fattura_id FROM _refs));
END $c2$;

-- ---- Caso 3: whitelist = ALTRO emittente -> NON visibile ----
DO $c3$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    DELETE FROM config.user_emittenti_fiscali WHERE auth_user_id = (SELECT auth_user_id FROM _op);
    INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
    VALUES ((SELECT auth_user_id FROM _op), (SELECT other_pk FROM _refs)) ON CONFLICT DO NOTHING;
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op)::text, true);
    INSERT INTO _res SELECT 'c3', EXISTS (SELECT 1 FROM vendite.fatture WHERE id = (SELECT fattura_id FROM _refs));
END $c3$;

-- ---- Caso 4: ruolo NON OPERATORE (gate policy fallisce) -> NON visibile ----
DO $c4$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op)::text, true);
    INSERT INTO _res SELECT 'c4', EXISTS (SELECT 1 FROM vendite.fatture WHERE id = (SELECT fattura_id FROM _refs));
END $c4$;

-- ---- Caso 5: identita OPERATORE NON attiva -> NON visibile ----
DO $c5$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    DELETE FROM config.user_emittenti_fiscali WHERE auth_user_id = (SELECT auth_user_id FROM _op);
    UPDATE anagrafiche.identita_digitali SET attivo = false WHERE id = (SELECT identita_id FROM _op);
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op)::text, true);
    INSERT INTO _res SELECT 'c5', EXISTS (SELECT 1 FROM vendite.fatture WHERE id = (SELECT fattura_id FROM _refs));
    UPDATE anagrafiche.identita_digitali SET attivo = true WHERE id = (SELECT identita_id FROM _op);
END $c5$;

-- ---- Caso 6: SUPER_ADMIN -> visibile anche con whitelist non-matching (fix C7) ----
DO $c6$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    -- whitelist = altro emittente: senza super_admin la fattura sarebbe nascosta.
    DELETE FROM config.user_emittenti_fiscali WHERE auth_user_id = (SELECT auth_user_id FROM _op);
    INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
    VALUES ((SELECT auth_user_id FROM _op), (SELECT other_pk FROM _refs)) ON CONFLICT DO NOTHING;
    -- binding SUPER_ADMIN sull'identita OPERATORE dell'operatore di test.
    INSERT INTO config.profili_accesso_bindings (profilo_accesso_id, identita_digitale_id, attivo)
    VALUES (
        (SELECT id FROM config.profili_accesso
          WHERE tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso AND attivo = true
          ORDER BY id LIMIT 1),
        (SELECT identita_id FROM _op),
        true
    );
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op)::text, true);
    INSERT INTO _res SELECT 'c6', EXISTS (SELECT 1 FROM vendite.fatture WHERE id = (SELECT fattura_id FROM _refs));
END $c6$;

-- ---- Caso 7: DISABLE RLS (kill-switch) -> di nuovo visibile ----
ALTER TABLE vendite.fatture NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture DISABLE ROW LEVEL SECURITY;
INSERT INTO _res
SELECT 'c7', EXISTS (SELECT 1 FROM vendite.fatture WHERE id = (SELECT fattura_id FROM _refs));

-- =========================================================
-- Asserzioni (soft-skip se prereq mancante: NOT prereq -> pass)
-- =========================================================
SELECT ok((SELECT NOT prereq FROM _flags) OR      (SELECT visibile FROM _res WHERE caso='c1'),
    '1. operatore whitelist vuota -> fattura visibile (accesso globale)');
SELECT ok((SELECT NOT prereq FROM _flags) OR      (SELECT visibile FROM _res WHERE caso='c2'),
    '2. operatore whitelist = emittente fattura -> visibile');
SELECT ok((SELECT NOT prereq FROM _flags) OR  NOT (SELECT visibile FROM _res WHERE caso='c3'),
    '3. operatore whitelist = altro emittente -> NON visibile');
SELECT ok((SELECT NOT prereq FROM _flags) OR  NOT (SELECT visibile FROM _res WHERE caso='c4'),
    '4. ruolo non OPERATORE -> NON visibile (gate policy)');
SELECT ok((SELECT NOT prereq FROM _flags) OR  NOT (SELECT visibile FROM _res WHERE caso='c5'),
    '5. identita OPERATORE non attiva -> NON visibile (fail-closed)');
SELECT ok((SELECT NOT prereq FROM _flags) OR      (SELECT visibile FROM _res WHERE caso='c6'),
    '6. SUPER_ADMIN -> visibile nonostante whitelist non-matching (fix C7)');
SELECT ok((SELECT NOT prereq FROM _flags) OR      (SELECT visibile FROM _res WHERE caso='c7'),
    '7. DISABLE RLS (kill-switch) -> fattura di nuovo visibile');

SELECT * FROM finish();
ROLLBACK;
