-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test FUNZIONALE scrittura/lettura RLS — vendite.commesse +
--   vendite.commesse_attivita (ef_whitelist).
--
-- Policy rls_commesse_ef_whitelist (via_sr) e rls_commesse_attivita_ef_whitelist
-- (via_commessa, delega al padre). La RLS non e' attiva permanentemente (mirror
-- famiglia): qui si attiva ENABLE + FORCE LOCALE alla transazione per verificare
-- lo scope, poi ROLLBACK ripristina lo stato.
--
-- Fixture SENZA build (usa dati esistenti): sceglie una commessa con emittente
-- risolvibile a emittente_fiscale e con >=1 attivita; ricava un secondo
-- emittente_fiscale per l'operatore off-scope. Soft-skip se non costruibile.
--
-- Ordine (mirror test-rls-resi-ef-whitelist-write):
--   1) _refs: commessa + emittente_fiscale in-scope + emittente_fiscale off-scope;
--   2) SET CONSTRAINTS ALL IMMEDIATE + ENABLE/FORCE su commesse e commesse_attivita;
--   3) crea gli operatori DOPO l'ALTER (check deferred -> rollback);
--   4) casi in-scope / off-scope / no-ruolo con UPDATE no-op (SET meta=meta).
--
-- Indice test (1..5):
--   1. OPERATORE in-scope  -> UPDATE commesse 1 riga
--   2. OPERATORE off-scope -> UPDATE commesse 0 righe (USING isola per emittente)
--   3. nessun ruolo        -> UPDATE commesse 0 righe (gate fail-closed)
--   4. OPERATORE in-scope  -> UPDATE commesse_attivita >0 righe (scope via padre)
--   5. OPERATORE off-scope -> UPDATE commesse_attivita 0 righe
-- ------------------------------------------------------------

BEGIN;
SELECT plan(5);

-- 1) Fixture da dati esistenti (nessun build): commessa in-scope + emittenti.
CREATE TEMP TABLE _refs AS
SELECT
  c.id                            AS commessa_id,
  c.emittente_soggetto_ruolo_id   AS emit_sr,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.soggetto_ruolo_id = c.emittente_soggetto_ruolo_id)              AS emit_in_fiscale,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.soggetto_ruolo_id IS DISTINCT FROM c.emittente_soggetto_ruolo_id
    ORDER BY ef.id LIMIT 1)                                                  AS emit_out_fiscale
FROM vendite.commesse c
WHERE c.emittente_soggetto_ruolo_id IS NOT NULL
  AND (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
        WHERE ef.soggetto_ruolo_id = c.emittente_soggetto_ruolo_id) IS NOT NULL
  AND EXISTS (SELECT 1 FROM vendite.commesse_attivita ca WHERE ca.commessa_id = c.id)
ORDER BY c.id
LIMIT 1;

-- 2) Flush eventuali deferred + ENABLE/FORCE su padre e satellite.
SET CONSTRAINTS ALL IMMEDIATE;
ALTER TABLE vendite.commesse           ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.commesse           FORCE  ROW LEVEL SECURITY;
ALTER TABLE vendite.commesse_attivita  ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.commesse_attivita  FORCE  ROW LEVEL SECURITY;
SET CONSTRAINTS ALL DEFERRED;

-- 3) Operatori DOPO l'ALTER (whitelist emittente in config.user_emittenti_fiscali).
CREATE TEMP TABLE _op (ruolo text, auth_user_id int);

CREATE OR REPLACE FUNCTION pg_temp.mk_op(p_tag text, p_cf text, p_emit bigint)
RETURNS void LANGUAGE plpgsql AS $fn$
DECLARE v_uid int; v_sog uuid; v_sr bigint; v_sfx text;
BEGIN
    v_sfx := substring(md5(clock_timestamp()::text || p_tag) from 1 for 8);
    INSERT INTO django.auth_user (username, password, is_active, is_staff,
        is_superuser, first_name, last_name, email, date_joined)
    VALUES ('_pgtap_rls_comm_' || v_sfx, '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_uid;

    v_sog := anagrafiche.fn_crea_soggetto_pf(
        p_cognome           := 'PnzTestScopeComm' || p_tag,
        p_nome              := 'Fdn',
        p_codice_fiscale    := p_cf,
        p_email             := 'pgtap_rls_comm_' || v_sfx || '@test.local',
        p_data_nascita      := DATE '1980-01-01',
        p_sesso             := 'M',
        p_stato_iso2        := 'IT',
        p_comune_nascita_id := (SELECT id FROM config.comuni ORDER BY id LIMIT 1),
        p_tipo_contatto_id  := NULL);

    v_sr := script.fn_get_or_create_soggetto_ruolo(
        p_soggetto_id := v_sog, p_cd_int_ruolo := 'RIS_UMANA');

    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    VALUES (v_sr, v_uid, 'OPERATORE', true);

    INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
    VALUES (v_uid, p_emit);

    INSERT INTO _op VALUES (p_tag, v_uid);
END
$fn$;

DO $ops$
BEGIN
    IF (SELECT emit_in_fiscale FROM _refs) IS NOT NULL
       AND (SELECT emit_out_fiscale FROM _refs) IS NOT NULL THEN
        PERFORM pg_temp.mk_op('in',  'PNZFDN78A01L219Y', (SELECT emit_in_fiscale  FROM _refs));
        PERFORM pg_temp.mk_op('out', 'LCCRLD80A01L736X', (SELECT emit_out_fiscale FROM _refs));
    END IF;
END
$ops$;

CREATE TEMP TABLE _flags AS
SELECT COALESCE((SELECT commessa_id IS NOT NULL
                   AND emit_in_fiscale IS NOT NULL
                   AND emit_out_fiscale IS NOT NULL FROM _refs), false)
       AND (SELECT count(*) = 2 FROM _op) AS prereq;

CREATE TEMP TABLE _res (caso text, n_righe integer);

-- Caso 1: in-scope commesse -> 1
DO $c1$
DECLARE v_n integer;
BEGIN
    IF (SELECT prereq FROM _flags) THEN
        PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
        PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='in')::text, true);
        UPDATE vendite.commesse SET meta = meta WHERE id = (SELECT commessa_id FROM _refs);
        GET DIAGNOSTICS v_n = ROW_COUNT;
        PERFORM set_config('app.ruolo_applicativo', '', true);
        PERFORM set_config('app.current_user_id', '', true);
    ELSE v_n := 1; END IF;
    INSERT INTO _res VALUES ('c1', v_n);
END
$c1$;

-- Caso 2: off-scope commesse -> 0
DO $c2$
DECLARE v_n integer;
BEGIN
    IF (SELECT prereq FROM _flags) THEN
        PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
        PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='out')::text, true);
        UPDATE vendite.commesse SET meta = meta WHERE id = (SELECT commessa_id FROM _refs);
        GET DIAGNOSTICS v_n = ROW_COUNT;
        PERFORM set_config('app.ruolo_applicativo', '', true);
        PERFORM set_config('app.current_user_id', '', true);
    ELSE v_n := 0; END IF;
    INSERT INTO _res VALUES ('c2', v_n);
END
$c2$;

-- Caso 3: nessun ruolo -> 0 (fail-closed)
DO $c3$
DECLARE v_n integer;
BEGIN
    IF (SELECT prereq FROM _flags) THEN
        PERFORM set_config('app.ruolo_applicativo', '', true);
        PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='in')::text, true);
        UPDATE vendite.commesse SET meta = meta WHERE id = (SELECT commessa_id FROM _refs);
        GET DIAGNOSTICS v_n = ROW_COUNT;
        PERFORM set_config('app.current_user_id', '', true);
    ELSE v_n := 0; END IF;
    INSERT INTO _res VALUES ('c3', v_n);
END
$c3$;

-- Caso 4: in-scope commesse_attivita -> >0 (scope delegato al padre)
DO $c4$
DECLARE v_n integer;
BEGIN
    IF (SELECT prereq FROM _flags) THEN
        PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
        PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='in')::text, true);
        UPDATE vendite.commesse_attivita SET meta = meta WHERE commessa_id = (SELECT commessa_id FROM _refs);
        GET DIAGNOSTICS v_n = ROW_COUNT;
        PERFORM set_config('app.ruolo_applicativo', '', true);
        PERFORM set_config('app.current_user_id', '', true);
    ELSE v_n := 1; END IF;
    INSERT INTO _res VALUES ('c4', v_n);
END
$c4$;

-- Caso 5: off-scope commesse_attivita -> 0
DO $c5$
DECLARE v_n integer;
BEGIN
    IF (SELECT prereq FROM _flags) THEN
        PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
        PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='out')::text, true);
        UPDATE vendite.commesse_attivita SET meta = meta WHERE commessa_id = (SELECT commessa_id FROM _refs);
        GET DIAGNOSTICS v_n = ROW_COUNT;
        PERFORM set_config('app.ruolo_applicativo', '', true);
        PERFORM set_config('app.current_user_id', '', true);
    ELSE v_n := 0; END IF;
    INSERT INTO _res VALUES ('c5', v_n);
END
$c5$;

-- ===================== Asserzioni =====================
SELECT ok((SELECT NOT prereq FROM _flags) OR (SELECT n_righe = 1 FROM _res WHERE caso='c1'),
    '1. OPERATORE in-scope: UPDATE commesse tocca la riga (scope emittente via_sr ok)');
SELECT ok((SELECT NOT prereq FROM _flags) OR (SELECT n_righe = 0 FROM _res WHERE caso='c2'),
    '2. OPERATORE off-scope: UPDATE commesse tocca 0 righe (USING isola per emittente)');
SELECT ok((SELECT NOT prereq FROM _flags) OR (SELECT n_righe = 0 FROM _res WHERE caso='c3'),
    '3. Nessun ruolo: UPDATE commesse tocca 0 righe (gate fail-closed)');
SELECT ok((SELECT NOT prereq FROM _flags) OR (SELECT n_righe > 0 FROM _res WHERE caso='c4'),
    '4. OPERATORE in-scope: UPDATE commesse_attivita tocca le righe (scope via padre)');
SELECT ok((SELECT NOT prereq FROM _flags) OR (SELECT n_righe = 0 FROM _res WHERE caso='c5'),
    '5. OPERATORE off-scope: UPDATE commesse_attivita tocca 0 righe (scope via padre)');

SELECT * FROM finish();
ROLLBACK;
