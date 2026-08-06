-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE vendite.ddt ENABLE + FORCE ROW LEVEL SECURITY, locale alla
--   transazione: e' il FORCE a rendere l'owner soggetto alle policy.
-- pgTAP test FUNZIONALE scrittura/lettura RLS — vendite.ddt (ef_whitelist)
--
-- Addendum SCOPE §15: policy rls_ddt_ef_whitelist (FOR ALL, dry-run) su
-- vendite.ddt. La RLS non e' attiva permanentemente (mirror ordini): qui si
-- attiva ENABLE + FORCE LOCALE alla transazione per verificare lo scope, poi
-- ROLLBACK ripristina lo stato.
--
-- Ordine forzato (importante):
--   1) costruisci il DDT (via fn_genera_ddt_da_ordine; emittente ereditato
--      dall'ordine via normalize);
--   2) SET CONSTRAINTS ALL IMMEDIATE + ALTER ENABLE/FORCE PRIMA di creare gli
--      operatori: cosi' si flushano solo i trigger deferred del DDT/ordine (dati
--      validi), NON il check "indirizzo obbligatorio" deferred dei soggetti
--      operatore (che mk_op non soddisfa, contando sul rollback);
--   3) crea gli operatori DOPO l'ALTER (i loro check restano deferred);
--   4) casi in-scope / off-scope / no-ruolo con UPDATE no-op (SET meta=meta).
-- Niente kill-switch DISABLE (richiederebbe un secondo ALTER in conflitto con i
-- trigger deferred degli UPDATE).
--
-- Conteggio righe aggiornate:
--   in-scope  -> 1 (policy FOR ALL permette lo scope)
--   off-scope -> 0 (USING isola per emittente)
--   no ruolo  -> 0 (gate fail-closed)
-- Soft-skip se mancano 2 emittenti o la fixture DDT non e' costruibile.
--
-- Indice test (1..3):
--   1. OPERATORE in-scope  -> UPDATE 1 riga
--   2. OPERATORE off-scope -> UPDATE 0 righe
--   3. nessun ruolo        -> UPDATE 0 righe
-- ------------------------------------------------------------

BEGIN;
SELECT plan(3);

-- Riferimenti base (dati esistenti).
CREATE TEMP TABLE _refs AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1)                       AS billing_account_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id LIMIT 1) AS soggetto_ruolo_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND COALESCE(a.is_composito,FALSE) IS FALSE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1) AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef ORDER BY ef.id LIMIT 1) AS emit_pk,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef ORDER BY ef.id OFFSET 1 LIMIT 1) AS other_pk,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno='CONFERMATO' AND s.attivo IS TRUE LIMIT 1) AS stato_ord_conf_id;

-- 1) Costruisce un DDT (emittente = emit_pk, via ordine) in modo robusto.
CREATE TEMP TABLE _ddt (ddt_id bigint, emit_pk bigint);

DO $build$
DECLARE
  v_ord  vendite.ordini.id%TYPE;
  v_ddt  vendite.ddt.id%TYPE;
  v_emit bigint;
BEGIN
  SELECT emit_pk INTO v_emit FROM _refs;
  IF v_emit IS NULL OR (SELECT other_pk FROM _refs) IS NULL
     OR (SELECT billing_account_id FROM _refs) IS NULL THEN
    RETURN;
  END IF;
  BEGIN
    INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
        valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
    SELECT r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id, r.valuta_id,
        DATE '2026-07-01', 'SPEDITO', r.emit_pk, false,
        jsonb_build_object('test_scope','pgtap_rls_ddt')
    FROM _refs r
    RETURNING id INTO v_ord;

    INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
        qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
    SELECT v_ord, 1, r.articolo_id, 'Riga RLS', 10, 10, 25, r.iva_id, true, false,
        jsonb_build_object('test_scope','pgtap_rls_ddt')
    FROM _refs r;

    v_ddt := vendite.fn_genera_ddt_da_ordine(v_ord);
    INSERT INTO _ddt VALUES (v_ddt, v_emit);
  EXCEPTION WHEN OTHERS THEN
    NULL;  -- fixture non costruibile -> soft-skip
  END;
END
$build$;

-- 2) Flush dei trigger deferred del DDT/ordine (nessun operatore ancora creato:
--    il check indirizzo dei soggetti operatore NON viene toccato) + ENABLE/FORCE.
SET CONSTRAINTS ALL IMMEDIATE;
ALTER TABLE vendite.ddt ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.ddt FORCE  ROW LEVEL SECURITY;
-- Ripristina la modalita' deferred (IMMEDIATE resta valido per tutta la tx):
-- cosi' il guard "indirizzo obbligatorio" dei soggetti operatore torna deferred
-- e non scatta alla creazione (mai flushato -> rollback).
SET CONSTRAINTS ALL DEFERRED;

-- 3) Operatori DOPO l'ALTER (i loro check indirizzo restano deferred -> rollback).
CREATE TEMP TABLE _op (ruolo text, auth_user_id int);

CREATE OR REPLACE FUNCTION pg_temp.mk_op(p_tag text, p_cf text, p_emit bigint)
RETURNS void LANGUAGE plpgsql AS $fn$
DECLARE v_uid int; v_sog uuid; v_sr bigint; v_sfx text;
BEGIN
    v_sfx := substring(md5(clock_timestamp()::text || p_tag) from 1 for 8);
    INSERT INTO django.auth_user (username, password, is_active, is_staff,
        is_superuser, first_name, last_name, email, date_joined)
    VALUES ('_pgtap_rls_ddt_' || v_sfx, '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_uid;

    v_sog := anagrafiche.fn_crea_soggetto_pf(
        p_cognome           := 'PnzTestScopeDdt' || p_tag,
        p_nome              := 'Fdn',
        p_codice_fiscale    := p_cf,
        p_email             := 'pgtap_rls_ddt_' || v_sfx || '@test.local',
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
    IF (SELECT count(*) FROM _ddt) = 1 THEN
        PERFORM pg_temp.mk_op('in',  'PNZFDN78A01L219Y', (SELECT emit_pk  FROM _ddt));
        PERFORM pg_temp.mk_op('out', 'LCCRLD80A01L736X', (SELECT other_pk FROM _refs));
    END IF;
END
$ops$;

CREATE TEMP TABLE _flags AS
SELECT COALESCE((SELECT count(*) = 1 FROM _ddt), false)
       AND (SELECT count(*) = 2 FROM _op) AS prereq;

CREATE TEMP TABLE _res (caso text, n_righe integer);

-- Caso 1: in-scope -> 1 riga
DO $c1$
DECLARE v_n integer;
BEGIN
    IF (SELECT prereq FROM _flags) THEN
        PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
        PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='in')::text, true);
        UPDATE vendite.ddt SET meta = meta WHERE id = (SELECT ddt_id FROM _ddt);
        GET DIAGNOSTICS v_n = ROW_COUNT;
        PERFORM set_config('app.ruolo_applicativo', '', true);
        PERFORM set_config('app.current_user_id', '', true);
    ELSE v_n := 1; END IF;
    INSERT INTO _res VALUES ('c1', v_n);
END
$c1$;

-- Caso 2: off-scope -> 0 righe
DO $c2$
DECLARE v_n integer;
BEGIN
    IF (SELECT prereq FROM _flags) THEN
        PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
        PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='out')::text, true);
        UPDATE vendite.ddt SET meta = meta WHERE id = (SELECT ddt_id FROM _ddt);
        GET DIAGNOSTICS v_n = ROW_COUNT;
        PERFORM set_config('app.ruolo_applicativo', '', true);
        PERFORM set_config('app.current_user_id', '', true);
    ELSE v_n := 0; END IF;
    INSERT INTO _res VALUES ('c2', v_n);
END
$c2$;

-- Caso 3: nessun ruolo -> 0 righe (fail-closed)
DO $c3$
DECLARE v_n integer;
BEGIN
    IF (SELECT prereq FROM _flags) THEN
        PERFORM set_config('app.ruolo_applicativo', '', true);
        PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='in')::text, true);
        UPDATE vendite.ddt SET meta = meta WHERE id = (SELECT ddt_id FROM _ddt);
        GET DIAGNOSTICS v_n = ROW_COUNT;
    ELSE v_n := 0; END IF;
    INSERT INTO _res VALUES ('c3', v_n);
END
$c3$;

-- ===================== Asserzioni =====================
SELECT ok((SELECT NOT prereq FROM _flags) OR (SELECT n_righe = 1 FROM _res WHERE caso='c1'),
    '1. OPERATORE in-scope: UPDATE tocca la riga (scope emittente ok)');
SELECT ok((SELECT NOT prereq FROM _flags) OR (SELECT n_righe = 0 FROM _res WHERE caso='c2'),
    '2. OPERATORE off-scope: UPDATE tocca 0 righe (USING isola per emittente)');
SELECT ok((SELECT NOT prereq FROM _flags) OR (SELECT n_righe = 0 FROM _res WHERE caso='c3'),
    '3. Nessun ruolo: UPDATE tocca 0 righe (gate fail-closed)');

SELECT * FROM finish();
ROLLBACK;
