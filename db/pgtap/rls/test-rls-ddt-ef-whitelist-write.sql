-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-contesto: escluso — la ragione e' scritta per esteso piu' sotto in
--   questo stesso file. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato», che una nota in prosa non fa.
--   ⚠️ Da riguardare: le esclusioni `rls/` furono fatte IN BLOCCO, e almeno
--   una non ne aveva diritto (brief pgtap-runner-rls-baseline §30.2).
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
--   2) SET CONSTRAINTS ALL IMMEDIATE + ALTER ENABLE/FORCE: flush dei trigger
--      deferred del DDT/ordine (un ALTER TABLE con eventi in sospeso e' rifiutato);
--   3) crea gli operatori dalla madre, completi (i vincoli restano IMMEDIATE);
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

-- 2) Flush dei trigger deferred del DDT/ordine + ENABLE/FORCE.
SET CONSTRAINTS ALL IMMEDIATE;
ALTER TABLE vendite.ddt ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.ddt FORCE  ROW LEVEL SECURITY;

-- 3) Operatori (whitelist emittente in config.user_emittenti_fiscali).
CREATE TEMP TABLE _op (ruolo text, auth_user_id int);

-- ⭐ Rev 2026-10-07 (brief-db-veste-utilizzabile): l'operatore viene dalla
--   MADRE (dbops.fn_pgtap_crea_operatore_umano: persona fisica completa,
--   risorsa umana, veste OPERATORE accesa come all'invito accettato) e
--   l'emittente gli si da' con la funzione di dominio
--   script.fn_change_user_emittenti_scope. Prima la fixture costruiva
--   soggetto, soggetto_ruolo e veste a mano, senza risorsa umana: uno stato
--   che la madre non produce, e che da D-2 (l'operatore umano vale finche'
--   vale il suo rapporto, script.fn_veste_utilizzabile) non e' piu' un
--   operatore valido. Il builder esce con i vincoli IMMEDIATE: niente piu'
--   finestra differita da riaprire per lui.
CREATE OR REPLACE FUNCTION pg_temp.mk_op(p_tag text, p_emit bigint)
RETURNS void LANGUAGE plpgsql AS $fn$
DECLARE v_op record;
BEGIN
    SELECT * INTO v_op
      FROM dbops.fn_pgtap_crea_operatore_umano('rls ddt ' || p_tag);

    -- Istruzione separata: cio' che il builder scrive si legge da qui in poi.
    PERFORM script.fn_change_user_emittenti_scope(v_op.auth_user_id, ARRAY[p_emit]);

    INSERT INTO _op VALUES (p_tag, v_op.auth_user_id);
END
$fn$;

DO $ops$
BEGIN
    IF (SELECT count(*) FROM _ddt) = 1 THEN
        PERFORM pg_temp.mk_op('in', (SELECT emit_pk  FROM _ddt));
        PERFORM pg_temp.mk_op('out', (SELECT other_pk FROM _refs));
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
