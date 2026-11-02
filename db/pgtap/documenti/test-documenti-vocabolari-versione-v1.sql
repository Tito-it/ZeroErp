-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: i valori ammessi di una versione di template stanno in TRE VOCABOLARI,
--   non piu' in tre CHECK.
-- Oggetti:
--   documenti.formati_template, documenti.formati_pagina,
--   documenti.orientamenti_pagina                                  (20261004-20)
--   seed dei tre vocabolari                                        (20261004-21)
--   FK da template_documenti_versioni + ritiro dei tre CHECK       (20261004-22)
--   righe in config.tabelle_gestibili (lookup si', pannello no)    (R-DB-2)
-- Brief: brief-db-vocabolari-versione-template.md
--
-- Elenco test (plan 14):
--  1) formati_template: HTML, HTML_MARKDOWN_BLOCKS, per nome
--  2) formati_pagina: A3, A4, LETTER, per nome
--  3) orientamenti_pagina: LANDSCAPE, PORTRAIT, per nome
--  4) nessuno dei tre ha `attivo`: si leggono, non si configurano
--  5) le tre FK esistono, su codice_interno, RESTRICT in update e delete
--  6) i tre CHECK sono ritirati: la FK e' la sede unica
--  7) una versione nata coi DEFAULT di colonna passa: i default sono a catalogo
--  8) page_format fuori catalogo (A5) -> 23503
--  9) formato_template fuori catalogo (MARKDOWN) -> 23503
-- 10) page_orientation fuori catalogo -> 23503
-- 11) gli altri valori a catalogo passano (HTML_MARKDOWN_BLOCKS, A3, LANDSCAPE)
-- 12) i tre vocabolari sono nel lookup e non nel pannello
-- 13) etichetta_key = documenti.<tabella>.<codice_interno minuscolo>
-- 14) il lock su codice_interno e' montato sui tre (ci_apply)
--
-- Scopo:
--  - ⭐ i casi sono COSTRUITI: un template dell'emittente di chi agisce e una
--    versione BOZZA; dal DB si legge solo il catalogo di seed;
--  - 8-10 sono A5 e MARKDOWN apposta: sono i due valori che la copia del
--    frontend offriva e il DB rifiutava (brief, sezione 2);
--  - ⚠️ 14 dipende da ci_apply (il lock nasce per la sola presenza di
--    codice_interno): su un DB migrato senza ci_apply e' rosso, ed e' giusto.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- 1-3) I vocabolari, per nome
-- ============================================================
SELECT is(
    (SELECT string_agg(codice_interno, ',' ORDER BY codice_interno) FROM documenti.formati_template),
    'HTML,HTML_MARKDOWN_BLOCKS',
    '1) formati_template: HTML, HTML_MARKDOWN_BLOCKS');

SELECT is(
    (SELECT string_agg(codice_interno, ',' ORDER BY codice_interno) FROM documenti.formati_pagina),
    'A3,A4,LETTER',
    '2) formati_pagina: A3, A4, LETTER');

SELECT is(
    (SELECT string_agg(codice_interno, ',' ORDER BY codice_interno) FROM documenti.orientamenti_pagina),
    'LANDSCAPE,PORTRAIT',
    '3) orientamenti_pagina: LANDSCAPE, PORTRAIT');

-- ============================================================
-- 4-6) La forma
-- ============================================================
SELECT is(
    (SELECT COALESCE(string_agg(c.table_name, ',' ORDER BY c.table_name), '')
       FROM information_schema.columns c
      WHERE c.table_schema = 'documenti'
        AND c.table_name IN ('formati_template', 'formati_pagina', 'orientamenti_pagina')
        AND c.column_name = 'attivo'),
    '',
    '4) nessun vocabolario ha attivo: si leggono, non si configurano');

SELECT is(
    (SELECT string_agg(format('%s:%s->%s.%s:%s%s', a.attname, c.conname, rc.relname, ra.attname,
                              c.confupdtype, c.confdeltype),
                       ',' ORDER BY c.conname)
       FROM pg_catalog.pg_constraint c
       JOIN pg_catalog.pg_class t ON t.oid = c.conrelid
       JOIN pg_catalog.pg_namespace n ON n.oid = t.relnamespace
       JOIN pg_catalog.pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
       JOIN pg_catalog.pg_class rc ON rc.oid = c.confrelid
       JOIN pg_catalog.pg_attribute ra ON ra.attrelid = c.confrelid AND ra.attnum = c.confkey[1]
      WHERE n.nspname = 'documenti'
        AND t.relname = 'template_documenti_versioni'
        AND c.contype = 'f'
        AND rc.relname IN ('formati_template', 'formati_pagina', 'orientamenti_pagina')),
    'page_format:fk_template_documenti_versioni_formati_pagina->formati_pagina.codice_interno:rr,'
    'formato_template:fk_template_documenti_versioni_formati_template->formati_template.codice_interno:rr,'
    'page_orientation:fk_template_documenti_versioni_orientamenti_pagina->orientamenti_pagina.codice_interno:rr',
    '5) tre FK su codice_interno, RESTRICT in update e delete');

SELECT is(
    (SELECT COALESCE(string_agg(c.conname, ',' ORDER BY c.conname), '')
       FROM pg_catalog.pg_constraint c
      WHERE c.conname IN ('chk_template_documenti_versioni_formato',
                          'chk_template_documenti_versioni_page_format',
                          'chk_template_documenti_versioni_orientation')),
    '',
    '6) i tre CHECK sono ritirati: la FK e'' la sede unica');

-- ============================================================
-- Fixture: un template dell'emittente di chi agisce, una versione BOZZA
-- ============================================================
CREATE TEMP TABLE tmp_dvv_ctx AS
SELECT script.fn_pgtap_emittente_operatore()                            AS emittente_id,
       (SELECT s.id FROM config.sorgenti s
         WHERE s.codice_interno = 'PREVENTIVO')                         AS sorgente_id,
       (SELECT t.id FROM documenti.tipi_documento_output t
         WHERE t.codice_interno = 'PREVENTIVO')                         AS tipo_output_id,
       (SELECT r.id FROM documenti.render_engine_documento r
         WHERE r.codice_interno = 'WEASYPRINT')                         AS render_id;

CREATE TEMP TABLE tmp_dvv_template AS
WITH ins AS (
    INSERT INTO documenti.template_documenti (
        tipo_documento_output_id, codice, codice_interno, descrizione,
        sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
        is_default, attivo
    )
    SELECT tipo_output_id, 'PGTAP-DVV', 'PGTAP_DVV', 'Template pgTAP vocabolari versione',
           sorgente_id, 'pgtap.builder', emittente_id, false, true
      FROM tmp_dvv_ctx
    RETURNING id
)
SELECT id FROM ins;

-- ============================================================
-- 7) I default di colonna sono a catalogo
-- ============================================================
-- ⚠️ In un'istruzione separata dal padre (guida pgTAP, «Padre e figlio»).
-- formato_template, page_format e page_orientation NON si scrivono: li danno i
-- DEFAULT della tabella, e la FK li deve trovare.
CREATE TEMP TABLE tmp_dvv_v AS
WITH ins AS (
    INSERT INTO documenti.template_documenti_versioni (
        template_documento_id, versione, stato, titolo, html_template,
        render_engine_id, versione_contesto
    )
    SELECT (SELECT id FROM tmp_dvv_template), 1, 'BOZZA', 'Versione 1', '<p>v1</p>',
           (SELECT render_id FROM tmp_dvv_ctx), 1
    RETURNING id, formato_template, page_format, page_orientation
)
SELECT id, formato_template, page_format, page_orientation FROM ins;

SELECT is(
    (SELECT format('%s|%s|%s', formato_template, page_format, page_orientation) FROM tmp_dvv_v),
    'HTML|A4|PORTRAIT',
    '7) una versione nata coi DEFAULT passa: HTML, A4, PORTRAIT sono a catalogo');

-- ============================================================
-- 8-11) Il cancello e' la FK
-- ============================================================
SELECT throws_ok(
    format($q$UPDATE documenti.template_documenti_versioni SET page_format = 'A5' WHERE id = %s$q$,
           (SELECT id FROM tmp_dvv_v)),
    '23503',
    NULL,
    '8) page_format A5, fuori catalogo: rifiutato dalla FK');

SELECT throws_ok(
    format($q$UPDATE documenti.template_documenti_versioni SET formato_template = 'MARKDOWN' WHERE id = %s$q$,
           (SELECT id FROM tmp_dvv_v)),
    '23503',
    NULL,
    '9) formato_template MARKDOWN, fuori catalogo: rifiutato dalla FK');

SELECT throws_ok(
    format($q$UPDATE documenti.template_documenti_versioni SET page_orientation = 'PGTAP_OBLIQUO' WHERE id = %s$q$,
           (SELECT id FROM tmp_dvv_v)),
    '23503',
    NULL,
    '10) page_orientation fuori catalogo: rifiutato dalla FK');

SELECT lives_ok(
    format($q$UPDATE documenti.template_documenti_versioni
                 SET formato_template = 'HTML_MARKDOWN_BLOCKS', page_format = 'A3',
                     page_orientation = 'LANDSCAPE'
               WHERE id = %s$q$,
           (SELECT id FROM tmp_dvv_v)),
    '11) i valori a catalogo passano: HTML_MARKDOWN_BLOCKS, A3, LANDSCAPE');

-- ============================================================
-- 12-14) Lookup, etichette, lock
-- ============================================================
SELECT is(
    (SELECT string_agg(format('%s=%s|%s', tg.codice_interno, tg.lookup::text, tg.pannello::text),
                       ',' ORDER BY tg.codice_interno)
       FROM config.tabelle_gestibili tg
      WHERE tg.codice_interno IN ('documenti.formati_template', 'documenti.formati_pagina',
                                  'documenti.orientamenti_pagina')),
    'documenti.formati_pagina=true|false,documenti.formati_template=true|false,'
    'documenti.orientamenti_pagina=true|false',
    '12) i tre vocabolari: nel lookup si'', nel pannello no');

SELECT is(
    (SELECT COALESCE(string_agg(v.tabella || '.' || v.codice_interno, ',' ORDER BY v.tabella, v.codice_interno), '')
       FROM (SELECT 'formati_template' AS tabella, codice_interno, etichetta_key FROM documenti.formati_template
             UNION ALL
             SELECT 'formati_pagina', codice_interno, etichetta_key FROM documenti.formati_pagina
             UNION ALL
             SELECT 'orientamenti_pagina', codice_interno, etichetta_key FROM documenti.orientamenti_pagina) v
      WHERE v.etichetta_key IS DISTINCT FROM 'documenti.' || v.tabella || '.' || lower(v.codice_interno)),
    '',
    '13) etichetta_key = documenti.<tabella>.<codice_interno minuscolo>, su ogni riga');

SELECT is(
    (SELECT string_agg(c.relname, ',' ORDER BY c.relname)
       FROM pg_catalog.pg_trigger tg
       JOIN pg_catalog.pg_class c ON c.oid = tg.tgrelid
       JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'documenti'
        AND c.relname IN ('formati_template', 'formati_pagina', 'orientamenti_pagina')
        AND tg.tgfoid = 'script.trgfn_lock_columns()'::regprocedure
        AND NOT tg.tgisinternal),
    'formati_pagina,formati_template,orientamenti_pagina',
    '14) lock su codice_interno montato sui tre vocabolari (ci_apply)');

SELECT * FROM finish();
ROLLBACK;
