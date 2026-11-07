-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il patto fra una versione di template e la forma dei dati che legge.
-- Oggetti:
--   documenti.template_documenti_versioni.versione_contesto      (20260930-14/-16)
--   documenti.fn_guard_versione_contesto                          (20260930-18)
--   documenti.trgfn_documenti_generati_guard_versione_contesto    (20260930-19)
--   trg_documenti_generati_a10_guard_versione_contesto_ins        (20260930-20)
-- La pubblicazione (20260930-21) e l'immutabilita' da PUBBLICATA (20260930-17)
-- hanno i loro test: test-fn-pubblica-template-documento-versione-v1 (8-11) e
-- test-documenti-template-versioni (10-11).
-- Brief: brief-db-documenti-versione-contesto-template.md
--
-- Elenco test (plan 15):
--  1) versione_contesto e' NOT NULL
--  2) ... e senza default: chi crea una versione dichiara la forma
--  3) CHECK: la forma si numera da 1 (23514 su 0)
--  4) guard: stessa forma -> passa
--  5) guard: forme diverse -> E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA, con le due
--     forme nella frase
--  6) guard: forma dei dati NULL -> _NON_VERIFICABILE («la forma dichiarata dai dati»)
--  7) guard: versione NULL -> _NON_VERIFICABILE («la versione del template»)
--  8) guard: versione inesistente -> E_DOCUMENTI_VERSIONE_NOT_FOUND
--  9) stampa con _meta.context_version uguale alla forma della versione -> si registra
-- 10) stampa con una forma diversa -> E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA
-- 11) stampa senza _meta -> _NON_VERIFICABILE
-- 12) stampa con la forma scritta come stringa "1" -> _NON_VERIFICABILE, non 22P02
-- 13) su una stampa incoerente E fuori forma parla la coerenza (ordine dei guard)
-- 14) i due codici sono a catalogo con la loro classe
-- 15) ... e con la frase italiana
--
-- Scopo:
--  - ⭐ i casi sono COSTRUITI: una versione alla forma 1, una alla forma 2, e
--    contesti scritti a mano — non una popolazione di documenti esistenti;
--  - il 13 pinna una scelta: a una riga incoerente la frase giusta e' quella
--    della coerenza (check_coerenza < guard_versione_contesto in ordine
--    alfabetico dei BEFORE ROW, linee-guida-trigger §a05/a10);
--  - il 12 pinna il CASE del trigger: un cast diretto darebbe 22P02.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⭐ La stampa e' di un preventivo VERO, del mondo dell'operatore in sessione: dal
--   lotto D di brief-db-sorgente-documento-e-riga il guard unico verifica che il
--   documento stampato esista, e la chiave di un preventivo e' il suo uid.
CREATE TEMP TABLE _dg_src AS
SELECT p.preventivo_uid FROM dbops.fn_pgtap_crea_preventivo('dg versione contesto', 'DRAFT') p;


SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- Fixture: un template dell'emittente di chi agisce, due versioni
-- ============================================================
-- Dal DB si legge solo il catalogo di seed (sorgente, tipo output, motore):
-- l'emittente si deriva dal contesto, non si pesca.
CREATE TEMP TABLE tmp_dvc_ctx AS
SELECT script.fn_pgtap_emittente_operatore()                            AS emittente_id,
       (SELECT s.id FROM config.sorgenti s
         WHERE s.codice_interno = 'PREVENTIVO')                         AS sorgente_id,
       (SELECT t.id FROM documenti.tipi_documento_output t
         WHERE t.codice_interno = 'PREVENTIVO')                         AS tipo_output_id,
       (SELECT r.id FROM documenti.render_engine_documento r
         WHERE r.codice_interno = 'WEASYPRINT')                         AS render_id;

CREATE TEMP TABLE tmp_dvc_template AS
WITH ins AS (
    INSERT INTO documenti.template_documenti (
        tipo_documento_output_id, codice, codice_interno, descrizione,
        sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
        is_default, attivo
    )
    SELECT tipo_output_id, 'PGTAP-DVC', 'PGTAP_DVC', 'Template pgTAP forma dati',
           sorgente_id, 'pgtap.builder', emittente_id, false, true
      FROM tmp_dvc_ctx
    RETURNING id
)
SELECT id FROM ins;

-- ⚠️ In un'istruzione separata dal padre (guida pgTAP, «Padre e figlio»).
-- V1 legge la forma 1, V2 la forma 2. BOZZA: il patto non guarda lo stato.
CREATE TEMP TABLE tmp_dvc_v AS
WITH ins AS (
    INSERT INTO documenti.template_documenti_versioni (
        template_documento_id, versione, stato, titolo, html_template,
        render_engine_id, versione_contesto
    )
    SELECT (SELECT id FROM tmp_dvc_template), n, 'BOZZA', 'Versione ' || n, '<p>v' || n || '</p>',
           (SELECT render_id FROM tmp_dvc_ctx), n
      FROM generate_series(1, 2) n
    RETURNING id, versione
)
SELECT id, versione FROM ins;

-- ============================================================
-- 1-3) La colonna
-- ============================================================
SELECT col_not_null('documenti', 'template_documenti_versioni', 'versione_contesto',
    '1) versione_contesto e'' NOT NULL');

SELECT col_hasnt_default('documenti', 'template_documenti_versioni', 'versione_contesto',
    '2) versione_contesto non ha default: la forma la dichiara chi crea la versione');

SELECT throws_ok(
    format($q$UPDATE documenti.template_documenti_versioni SET versione_contesto = 0 WHERE id = %s$q$,
           (SELECT id FROM tmp_dvc_v WHERE versione = 1)),
    '23514',
    NULL,
    '3) CHECK chk_template_documenti_versioni_versione_contesto_pos: la forma 0 non esiste'
);

-- ============================================================
-- 4-8) Il guard, chiamato come lo chiama il backend prima del render
-- ============================================================
SELECT lives_ok(
    format($q$SELECT documenti.fn_guard_versione_contesto(%s, 2)$q$,
           (SELECT id FROM tmp_dvc_v WHERE versione = 2)),
    '4) V2 legge la forma 2, i dati sono alla 2: passa'
);

SELECT throws_like(
    format($q$SELECT documenti.fn_guard_versione_contesto(%s, 2)$q$,
           (SELECT id FROM tmp_dvc_v WHERE versione = 1)),
    '%versione 1 del template «Template pgTAP forma dati» legge i dati nella forma 1, ma il sistema li prepara nella forma 2%',
    '5) V1 legge la forma 1, i dati sono alla 2: E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA con versione, template e forme'
);

SELECT throws_like(
    format($q$SELECT documenti.fn_guard_versione_contesto(%s, NULL)$q$,
           (SELECT id FROM tmp_dvc_v WHERE versione = 1)),
    '%manca la forma dichiarata dai dati%',
    '6) forma dei dati NULL: _NON_VERIFICABILE, non un passaggio'
);

SELECT throws_like(
    $q$SELECT documenti.fn_guard_versione_contesto(NULL, 1)$q$,
    '%manca la versione del template%',
    '7) versione NULL: _NON_VERIFICABILE'
);

SELECT throws_like(
    $q$SELECT documenti.fn_guard_versione_contesto(9223372036854775807, 1)$q$,
    '%9223372036854775807 non esiste%',
    '8) versione inesistente: E_DOCUMENTI_VERSIONE_NOT_FOUND'
);

-- ============================================================
-- 9-13) Il trigger sulle stampe
-- ============================================================
-- Una stampa della V1 (forma 1). Il contesto e' l'unica cosa che varia fra i
-- casi: la funzione di comodo lo riceve e compone il resto della riga.
CREATE TEMP TABLE tmp_dvc_seq (n integer);
INSERT INTO tmp_dvc_seq VALUES (0);

CREATE FUNCTION pg_temp.fn_dvc_stampa(p_contesto jsonb, p_tipo_output_id bigint DEFAULT NULL)
RETURNS void LANGUAGE plpgsql AS $f$
DECLARE
    v_n integer;
BEGIN
    UPDATE tmp_dvc_seq SET n = n + 1 RETURNING n INTO v_n;
    INSERT INTO documenti.documenti_generati (
        tipo_documento_output_id, template_documento_id, template_versione_id,
        sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
        titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
        emittente_fiscale_id
    )
    SELECT coalesce(p_tipo_output_id, c.tipo_output_id),
           (SELECT id FROM tmp_dvc_template),
           (SELECT id FROM tmp_dvc_v WHERE versione = 1),
           c.sorgente_id,
           (SELECT preventivo_uid FROM _dg_src), NULL, v_n,
           'Stampa pgTAP ' || v_n, 'pgtap-dvc-' || v_n || '.pdf',
           p_contesto,
           repeat('1', 64), repeat('2', 64), repeat('3', 64),
           c.emittente_id
      FROM tmp_dvc_ctx c;
END
$f$;

SELECT lives_ok(
    $q$SELECT pg_temp.fn_dvc_stampa('{"tot": 1, "_meta": {"context_version": 1}}'::jsonb)$q$,
    '9) contesto alla forma 1 su una versione che legge la 1: la stampa si registra'
);

SELECT throws_like(
    $q$SELECT pg_temp.fn_dvc_stampa('{"tot": 1, "_meta": {"context_version": 2}}'::jsonb)$q$,
    '%legge i dati nella forma 1, ma il sistema li prepara nella forma 2%',
    '10) contesto alla forma 2 su una versione che legge la 1: la stampa non si registra'
);

SELECT throws_like(
    $q$SELECT pg_temp.fn_dvc_stampa('{"tot": 1}'::jsonb)$q$,
    '%manca la forma dichiarata dai dati%',
    '11) contesto senza _meta: _NON_VERIFICABILE'
);

SELECT throws_like(
    $q$SELECT pg_temp.fn_dvc_stampa('{"tot": 1, "_meta": {"context_version": "1"}}'::jsonb)$q$,
    '%manca la forma dichiarata dai dati%',
    '12) forma scritta come stringa: _NON_VERIFICABILE, non un 22P02 del cast'
);

SELECT throws_like(
    $q$SELECT pg_temp.fn_dvc_stampa('{"tot": 1}'::jsonb, 999999999)$q$,
    '%Incoerenza referenziale%',
    '13) tipo output incoerente E contesto senza forma: parla la coerenza, che viene prima'
);

-- ============================================================
-- 14-15) I codici a catalogo
-- ============================================================
SELECT is(
    (SELECT string_agg(c.codice || '=' || c.classe, ', ' ORDER BY c.codice)
       FROM config.codici_errore c
      WHERE c.codice IN ('E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA',
                         'E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE')),
    'E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA=CONFLITTO_STATO, E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE=TECNICO',
    '14) i due codici sono a catalogo: DIVERSA e'' un conflitto (409), NON_VERIFICABILE un chiamante rotto (500)'
);

SELECT is(
    (SELECT count(*)::integer
       FROM config.messaggi_errore m
      WHERE m.lingua = 'it'
        AND m.codice IN ('E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA',
                         'E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE')),
    2,
    '15) ... e hanno la frase italiana'
);

SELECT * FROM finish();
ROLLBACK;
