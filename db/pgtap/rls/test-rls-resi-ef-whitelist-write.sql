-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-contesto: escluso — la ragione e' scritta per esteso piu' sotto in
--   questo stesso file. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato», che una nota in prosa non fa.
--   ⚠️ Da riguardare: le esclusioni `rls/` furono fatte IN BLOCCO, e almeno
--   una non ne aveva diritto (brief pgtap-runner-rls-baseline §30.2).
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE vendite.resi ENABLE + FORCE ROW LEVEL SECURITY, locale alla
--   transazione: e' il FORCE a rendere l'owner soggetto alle policy.
-- pgTAP test FUNZIONALE scrittura/lettura RLS — vendite.resi (ef_whitelist)
--
-- Policy rls_resi_ef_whitelist (FOR ALL) su vendite.resi. La RLS non e' attiva
-- permanentemente (mirror ddt/ordini): qui si attiva ENABLE + FORCE LOCALE alla
-- transazione per verificare lo scope, poi ROLLBACK ripristina lo stato.
--
-- Ordine forzato (mirror test-rls-ddt-ef-whitelist-write):
--   1) costruisci un DDT (via fn_genera_ddt_da_ordine, emittente = emit_pk) e un
--      reso da quel DDT (emittente ereditato via trgfn_resi_normalize);
--   2) SET CONSTRAINTS ALL IMMEDIATE + ALTER ENABLE/FORCE su vendite.resi PRIMA
--      di creare gli operatori (flush dei soli trigger deferred DDT/ordine/reso);
--   3) crea gli operatori DOPO l'ALTER (i loro check restano deferred -> rollback);
--   4) casi in-scope / off-scope / no-ruolo con UPDATE no-op (SET meta=meta).
--
-- Conteggio righe aggiornate:
--   in-scope  -> 1 (policy FOR ALL permette lo scope)
--   off-scope -> 0 (USING isola per emittente)
--   no ruolo  -> 0 (gate fail-closed)
-- Soft-skip se mancano 2 emittenti o la fixture non e' costruibile.
--
-- Indice test (1..3):
--   1. OPERATORE in-scope  -> UPDATE 1 riga
--   2. OPERATORE off-scope -> UPDATE 0 righe
--   3. nessun ruolo        -> UPDATE 0 righe
-- ------------------------------------------------------------

BEGIN;
SELECT plan(3);

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

-- 1) Costruisce un DDT (emittente=emit_pk) e un reso da quel DDT.
CREATE TEMP TABLE _reso (reso_id bigint, emit_pk bigint);

DO $build$
DECLARE
  v_ord  vendite.ordini.id%TYPE;
  v_ddt  vendite.ddt.id%TYPE;
  v_reso vendite.resi.id%TYPE;
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
        jsonb_build_object('test_scope','pgtap_rls_resi')
    FROM _refs r
    RETURNING id INTO v_ord;

    INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
        qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
    SELECT v_ord, 1, r.articolo_id, 'Riga RLS resi', 10, 10, 25, r.iva_id, true, false,
        jsonb_build_object('test_scope','pgtap_rls_resi')
    FROM _refs r;

    v_ddt := vendite.fn_genera_ddt_da_ordine(v_ord);

    -- Porta il DDT a CONSEGNATO (guard resi: si rende solo cio' che e' consegnato).
    INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
    SELECT v_ddt, (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON'),
           '{"display":"CON"}'::jsonb ON CONFLICT DO NOTHING;
    UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT id FROM config.stati_doc_ddt WHERE codice_interno='EMESSO'     AND attivo LIMIT 1) WHERE id=v_ddt;
    UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT id FROM config.stati_doc_ddt WHERE codice_interno='SPEDITO'    AND attivo LIMIT 1) WHERE id=v_ddt;
    UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT id FROM config.stati_doc_ddt WHERE codice_interno='CONSEGNATO' AND attivo LIMIT 1) WHERE id=v_ddt;

    -- Reso dal DDT: emittente ereditato via trgfn_resi_normalize.
    INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
    SELECT (SELECT id FROM config.stati_doc_reso WHERE codice_interno='DRAFT' AND attivo IS TRUE LIMIT 1),
           (SELECT id FROM config.sorgenti WHERE codice_interno='DDT_VENDITA' AND attivo IS TRUE LIMIT 1),
           (SELECT uid FROM vendite.ddt WHERE id = v_ddt),
           false, jsonb_build_object('test_scope','pgtap_rls_resi')
    RETURNING id INTO v_reso;

    INSERT INTO _reso VALUES (v_reso, v_emit);
  EXCEPTION WHEN OTHERS THEN
    NULL;  -- fixture non costruibile -> soft-skip
  END;
END
$build$;

-- 2) Flush trigger deferred + ENABLE/FORCE su vendite.resi.
SET CONSTRAINTS ALL IMMEDIATE;
ALTER TABLE vendite.resi ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.resi FORCE  ROW LEVEL SECURITY;
SET CONSTRAINTS ALL DEFERRED;

-- 3) Operatori DOPO l'ALTER.
CREATE TEMP TABLE _op (ruolo text, auth_user_id int);

CREATE OR REPLACE FUNCTION pg_temp.mk_op(p_tag text, p_cf text, p_emit bigint)
RETURNS void LANGUAGE plpgsql AS $fn$
DECLARE v_uid int; v_sog uuid; v_sr bigint; v_sfx text;
BEGIN
    v_sfx := substring(md5(clock_timestamp()::text || p_tag) from 1 for 8);
    INSERT INTO django.auth_user (username, password, is_active, is_staff,
        is_superuser, first_name, last_name, email, date_joined)
    VALUES ('_pgtap_rls_resi_' || v_sfx, '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_uid;

    v_sog := anagrafiche.fn_crea_soggetto_pf(
        p_cognome           := 'PnzTestScopeResi' || p_tag,
        p_nome              := 'Fdn',
        p_codice_fiscale    := p_cf,
        p_email             := 'pgtap_rls_resi_' || v_sfx || '@test.local',
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
    IF (SELECT count(*) FROM _reso) = 1 THEN
        PERFORM pg_temp.mk_op('in',  'PNZFDN78A01L219Y', (SELECT emit_pk  FROM _reso));
        PERFORM pg_temp.mk_op('out', 'LCCRLD80A01L736X', (SELECT other_pk FROM _refs));
    END IF;
END
$ops$;

CREATE TEMP TABLE _flags AS
SELECT COALESCE((SELECT count(*) = 1 FROM _reso), false)
       AND (SELECT count(*) = 2 FROM _op) AS prereq;

CREATE TEMP TABLE _res (caso text, n_righe integer);

-- Caso 1: in-scope -> 1 riga
DO $c1$
DECLARE v_n integer;
BEGIN
    IF (SELECT prereq FROM _flags) THEN
        PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
        PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='in')::text, true);
        UPDATE vendite.resi SET meta = meta WHERE id = (SELECT reso_id FROM _reso);
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
        UPDATE vendite.resi SET meta = meta WHERE id = (SELECT reso_id FROM _reso);
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
        UPDATE vendite.resi SET meta = meta WHERE id = (SELECT reso_id FROM _reso);
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
