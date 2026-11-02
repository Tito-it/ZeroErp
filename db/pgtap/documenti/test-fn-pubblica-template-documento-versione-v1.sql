-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: documenti.fn_pubblica_template_documento_versione — l'ordine delle
--       date lo giudica il guard comune, e la chiusura delle versioni
--       precedenti non dipende da p_valido_al.
-- Oggetti:
--   documenti.fn_pubblica_template_documento_versione   (rev 20260924-02)
--   script.trgfn_guard_date_validita                    (20260923-40)
--   documenti.fn_guard_versione_contesto                (20260930-18)
-- Brief: brief-db-guard-date-validita.md §13;
--        brief-db-documenti-versione-contesto-template.md (test 8-11, firma a 4)
--
-- Elenco test (plan 11):
--  1) date invertite -> parla il guard comune (E_DATA_AL_MINORE_DAL), non il
--     daterange della ricerca (22000) ne' il vecchio E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO
--  2) i due canali strutturati: CONSTRAINT = E_DATA_AL_MINORE_DAL, COLUMN = valido_al
--  3) il rifiuto e' atomico: la versione pubblicata prima resta PUBBLICATA e
--     aperta, la bozza resta BOZZA
--  4) pubblicazione con fine validita': la versione aperta che la precede
--     viene chiusa (versioni_obsolete = 1)
--  5) ... chiusa al giorno prima di p_valido_dal e resa OBSOLETA
--  6) una versione gia' chiusa PRIMA di p_valido_dal non si tocca
--     (versioni_obsolete = 0)
--  7) ... e resta PUBBLICATA con la sua fine
--  8) forma dichiarata 2, builder alla 1 -> E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA (rev 20260930-21)
--  9) ... e il rifiuto e' atomico: V3 pubblicata e aperta, V4 bozza
-- 10) p_versione_contesto NULL -> E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE
-- 11) forma dichiarata 2, builder alla 2 -> pubblicata (D-C4)
--
-- Scopo:
--  - ⭐ i test 1-3 provano il ritiro della copia (20260924-02): la regola del
--    periodo ha una sede sola. ⚠️ Il ritiro da solo non bastava: la ricerca
--    delle versioni da chiudere costruiva daterange(p_valido_dal, p_valido_al)
--    e con le date invertite sollevava 22000 PRIMA dell'UPDATE — il test 1 lo
--    distingue perche' pretende la FRASE del guard;
--  - ⭐ i test 4-7 provano che la ricerca riscritta su [p_valido_dal, oltre)
--    chiude lo STESSO insieme di prima: una versione aperta si chiude anche
--    quando la nuova ha una fine (p_valido_al non conta), una gia' chiusa prima
--    dell'inizio della nuova no. Sono casi COSTRUITI, non una popolazione:
--    verdi anche prima della revisione, ed e' voluto — fissano l'equivalenza.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- Fixture: un template dell'emittente di chi agisce, tre bozze
-- ============================================================
CREATE TEMP TABLE tmp_ptv_ctx AS
SELECT script.fn_pgtap_emittente_operatore()                            AS emittente_id,
       (SELECT s.id FROM config.sorgenti s
         WHERE s.codice_interno = 'PREVENTIVO')                         AS sorgente_id,
       (SELECT t.id FROM documenti.tipi_documento_output t
         WHERE t.codice_interno = 'PREVENTIVO')                         AS tipo_output_id,
       (SELECT r.id FROM documenti.render_engine_documento r
         WHERE r.codice_interno = 'WEASYPRINT')                         AS render_id;

CREATE TEMP TABLE tmp_ptv_template AS
WITH ins AS (
    INSERT INTO documenti.template_documenti (
        tipo_documento_output_id, codice, codice_interno, descrizione,
        sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
        is_default, attivo
    )
    SELECT tipo_output_id, 'PGTAP-PTV', 'PGTAP_PTV', 'Template per test pubblicazione',
           sorgente_id, 'pgtap.builder', emittente_id, false, true
      FROM tmp_ptv_ctx
    RETURNING id
)
SELECT id FROM ins;

-- ⚠️ In un'istruzione separata dal padre (guida pgTAP, «Padre e figlio»).
CREATE TEMP TABLE tmp_ptv_v AS
WITH ins AS (
    INSERT INTO documenti.template_documenti_versioni (
        template_documento_id, versione, stato, titolo, html_template, render_engine_id,
        versione_contesto
    )
    -- V1-V3 leggono la forma 1; la V4 e' preparata per la forma 2 (D-C4).
    SELECT (SELECT id FROM tmp_ptv_template), n, 'BOZZA', 'Versione ' || n, '<p>v' || n || '</p>',
           (SELECT render_id FROM tmp_ptv_ctx), CASE WHEN n = 4 THEN 2 ELSE 1 END
      FROM generate_series(1, 4) n
    RETURNING id, versione
)
SELECT id, versione FROM ins;

-- La V1 aperta dal 2026-01-01: la base su cui si pubblica dopo.
SELECT documenti.fn_pubblica_template_documento_versione(
    (SELECT id FROM tmp_ptv_v WHERE versione = 1), DATE '2026-01-01', 1, NULL);

-- ============================================================
-- 1-3) Date invertite: il guard comune, e nessuna traccia
-- ============================================================
SELECT throws_like(
    format($q$SELECT documenti.fn_pubblica_template_documento_versione(%s, DATE '2026-03-01', 1, DATE '2026-02-01')$q$,
           (SELECT id FROM tmp_ptv_v WHERE versione = 2)),
    '%è inferiore alla data dal%',
    '1) date invertite: parla il guard comune, non il daterange della ricerca ne'' il vecchio codice'
);

CREATE TEMP TABLE tmp_ptv_diag (vincolo text, campo text);

DO $diag$
DECLARE v_cst text; v_col text;
BEGIN
    BEGIN
        PERFORM documenti.fn_pubblica_template_documento_versione(
            (SELECT id FROM tmp_ptv_v WHERE versione = 2), DATE '2026-03-01', 1, DATE '2026-02-01');
        INSERT INTO tmp_ptv_diag VALUES (NULL, NULL);
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_cst = CONSTRAINT_NAME, v_col = COLUMN_NAME;
        INSERT INTO tmp_ptv_diag VALUES (nullif(v_cst, ''), nullif(v_col, ''));
    END;
END $diag$;

SELECT is(
    (SELECT coalesce(vincolo, '-') || ' / ' || coalesce(campo, '-') FROM tmp_ptv_diag),
    'E_DATA_AL_MINORE_DAL / valido_al',
    '2) canali strutturati: il codice del guard comune e il campo valido_al'
);

SELECT is(
    (SELECT string_agg(t.versione || '=' || t.stato || '[' || coalesce(t.valido_al::text, 'aperta') || ']', ', ' ORDER BY t.versione)
       FROM documenti.template_documenti_versioni t
      WHERE t.id IN (SELECT id FROM tmp_ptv_v WHERE versione IN (1, 2))),
    '1=PUBBLICATA[aperta], 2=BOZZA[aperta]',
    '3) rifiuto atomico: la V1 resta pubblicata e aperta, la V2 resta bozza'
);

-- ============================================================
-- 4-5) Pubblicazione con una fine: la versione aperta si chiude
-- ============================================================
CREATE TEMP TABLE tmp_ptv_esito_v2 AS
SELECT * FROM documenti.fn_pubblica_template_documento_versione(
    (SELECT id FROM tmp_ptv_v WHERE versione = 2), DATE '2026-03-01', 1, DATE '2026-06-30');

SELECT is(
    (SELECT versioni_obsolete FROM tmp_ptv_esito_v2),
    1,
    '4) V2 [2026-03-01, 2026-06-30]: la V1 aperta si sovrappone e si chiude, anche se la V2 ha una fine'
);

SELECT is(
    (SELECT t.stato || '[' || t.valido_al || ']'
       FROM documenti.template_documenti_versioni t
      WHERE t.id = (SELECT id FROM tmp_ptv_v WHERE versione = 1)),
    'OBSOLETA[2026-02-28]',
    '5) la V1 e'' OBSOLETA e chiusa al giorno prima dell''inizio della V2'
);

-- ============================================================
-- 6-7) Una versione gia' chiusa prima dell'inizio della nuova non si tocca
-- ============================================================
CREATE TEMP TABLE tmp_ptv_esito_v3 AS
SELECT * FROM documenti.fn_pubblica_template_documento_versione(
    (SELECT id FROM tmp_ptv_v WHERE versione = 3), DATE '2026-08-01', 1, NULL);

SELECT is(
    (SELECT versioni_obsolete FROM tmp_ptv_esito_v3),
    0,
    '6) V3 dal 2026-08-01: la V2, chiusa il 2026-06-30, non si sovrappone e non si chiude'
);

SELECT is(
    (SELECT t.stato || '[' || t.valido_al || ']'
       FROM documenti.template_documenti_versioni t
      WHERE t.id = (SELECT id FROM tmp_ptv_v WHERE versione = 2)),
    'PUBBLICATA[2026-06-30]',
    '7) la V2 resta PUBBLICATA con la sua fine'
);

-- ============================================================
-- 8-11) Il patto versione/forma dei dati alla pubblicazione (rev 20260930-21)
-- ============================================================
-- La V4 dichiara di leggere la forma 2. Il builder (qui: il chiamante) dice
-- di produrre la forma 1: non si pubblica.
SELECT throws_like(
    format($q$SELECT documenti.fn_pubblica_template_documento_versione(%s, DATE '2026-10-01', 1, NULL)$q$,
           (SELECT id FROM tmp_ptv_v WHERE versione = 4)),
    '%legge i dati nella forma 2, ma il sistema li prepara nella forma 1%',
    '8) forma dichiarata 2, builder alla 1: E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA, con le due forme nella frase'
);

-- Il rifiuto arriva PRIMA di chiudere le versioni precedenti: niente da annullare.
SELECT is(
    (SELECT string_agg(t.versione || '=' || t.stato || '[' || coalesce(t.valido_al::text, 'aperta') || ']', ', ' ORDER BY t.versione)
       FROM documenti.template_documenti_versioni t
      WHERE t.id IN (SELECT id FROM tmp_ptv_v WHERE versione IN (3, 4))),
    '3=PUBBLICATA[aperta], 4=BOZZA[aperta]',
    '9) rifiuto atomico: la V3 resta pubblicata e aperta, la V4 resta bozza'
);

-- Senza la forma del builder il controllo non si fa: TECNICO, non un passaggio.
SELECT throws_like(
    format($q$SELECT documenti.fn_pubblica_template_documento_versione(%s, DATE '2026-10-01', NULL, NULL)$q$,
           (SELECT id FROM tmp_ptv_v WHERE versione = 4)),
    '%manca la forma dichiarata dai dati%',
    '10) p_versione_contesto NULL: E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE, non un salto del controllo'
);

-- D-C4 fino in fondo: la bozza preparata per la forma 2 si pubblica quando il
-- builder produce la 2.
CREATE TEMP TABLE tmp_ptv_esito_v4 AS
SELECT * FROM documenti.fn_pubblica_template_documento_versione(
    (SELECT id FROM tmp_ptv_v WHERE versione = 4), DATE '2026-10-01', 2, NULL);

SELECT is(
    (SELECT t.stato || '/' || t.versione_contesto
       FROM documenti.template_documenti_versioni t
      WHERE t.id = (SELECT id FROM tmp_ptv_v WHERE versione = 4)),
    'PUBBLICATA/2',
    '11) forma dichiarata 2, builder alla 2: la V4 si pubblica'
);

SELECT * FROM finish();
ROLLBACK;
