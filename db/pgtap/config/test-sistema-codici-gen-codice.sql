-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: automazione generazione codici/numero (sistema_codici)
--
-- Elenco test:
-- 1) Esiste almeno una configurazione usa_sequenza
-- 2) Trigger function trgfn_<tabella>_gen_codice presente
-- 3) Trigger trg_<tabella>_a10_gen_codice_ins_upd presente
-- 4) Trigger function contiene script.fn_generate_codice
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. In testa e non in coda apposta:
--   in coda scatterebbero tutti insieme DOPO il cleanup, su righe ormai
--   cancellate. Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- ============================================================
-- 0) Configurazioni attive
-- ============================================================
CREATE TEMP TABLE tmp_sistema_codici AS
SELECT DISTINCT
    codice_interno,
    schema_tabella,
    nome_tabella,
    nome_colonna
FROM config.sistema_codici
WHERE usa_sequenza IS TRUE
  AND schema_tabella IS NOT NULL
  AND nome_tabella IS NOT NULL
  AND nome_colonna IS NOT NULL;

SELECT ok(
    (SELECT count(*) FROM tmp_sistema_codici) > 0,
    'Esiste almeno una configurazione usa_sequenza'
);

-- ============================================================
-- 1) Verifica esistenza trigger function
-- ============================================================
CREATE TEMP TABLE tmp_missing_fn AS
SELECT DISTINCT sc.*
FROM tmp_sistema_codici sc
LEFT JOIN pg_proc p
  ON p.proname = format('trgfn_%s_gen_codice', sc.nome_tabella)
LEFT JOIN pg_namespace n
  ON n.oid = p.pronamespace
 AND n.nspname = sc.schema_tabella
WHERE n.oid IS NULL;

SELECT is(
    (SELECT count(*)::int FROM tmp_missing_fn),
    0,
    'Tutte le trigger function trgfn_<tabella>_gen_codice sono presenti'
);
SELECT diag(
    'Trigger function mancanti: ' ||
    COALESCE(
      (SELECT string_agg(DISTINCT format('%s.%s', schema_tabella, format('trgfn_%s_gen_codice', nome_tabella)), ', ')
       FROM tmp_missing_fn),
      'nessuna'
    )
);

-- ============================================================
-- 2) Verifica esistenza trigger
-- ============================================================
CREATE TEMP TABLE tmp_missing_trg AS
SELECT DISTINCT sc.*
FROM tmp_sistema_codici sc
JOIN pg_class c
  ON c.relname = sc.nome_tabella
JOIN pg_namespace n
  ON n.oid = c.relnamespace
 AND n.nspname = sc.schema_tabella
LEFT JOIN pg_proc p
  ON p.proname = format('trgfn_%s_gen_codice', sc.nome_tabella)
LEFT JOIN pg_namespace pn
  ON pn.oid = p.pronamespace
 AND pn.nspname = sc.schema_tabella
LEFT JOIN pg_trigger t
  ON t.tgrelid = c.oid
 AND t.tgfoid = p.oid
 AND NOT t.tgisinternal
WHERE p.oid IS NOT NULL
  AND t.oid IS NULL;

SELECT is(
    (SELECT count(*)::int FROM tmp_missing_trg),
    0,
    'Tutti i trigger trg_<tabella>_a10_gen_codice_ins_upd sono presenti'
);
SELECT diag(
    'Trigger mancanti: ' ||
    COALESCE(
      (SELECT string_agg(DISTINCT format('%s.%s', schema_tabella, nome_tabella), ', ')
       FROM tmp_missing_trg),
      'nessuno'
    )
);

-- ============================================================
-- 3) Verifica corpo funzione (deve chiamare fn_generate_codice)
-- ============================================================
CREATE TEMP TABLE tmp_invalid_fn AS
SELECT DISTINCT sc.*
FROM tmp_sistema_codici sc
JOIN pg_proc p
  ON p.proname = format('trgfn_%s_gen_codice', sc.nome_tabella)
JOIN pg_namespace n
  ON n.oid = p.pronamespace
 AND n.nspname = sc.schema_tabella
WHERE position('script.fn_generate_codice' IN COALESCE(p.prosrc, '')) = 0;

SELECT is(
    (SELECT count(*)::int FROM tmp_invalid_fn),
    0,
    'Le trigger function contengono la chiamata a script.fn_generate_codice'
);
SELECT diag(
    'Trigger function senza generate_codice: ' ||
    COALESCE(
      (SELECT string_agg(DISTINCT format('%s.%s', schema_tabella, format('trgfn_%s_gen_codice', nome_tabella)), ', ')
       FROM tmp_invalid_fn),
      'nessuna'
    )
);

-- ============================================================
-- 4) Verifica condizione coerente col tipo colonna
-- ============================================================
CREATE TEMP TABLE tmp_sistema_codici_tipo AS
SELECT DISTINCT sc.*,
       t.typcategory
FROM tmp_sistema_codici sc
JOIN pg_class c
  ON c.relname = sc.nome_tabella
JOIN pg_namespace n
  ON n.oid = c.relnamespace
 AND n.nspname = sc.schema_tabella
JOIN pg_attribute a
  ON a.attrelid = c.oid
 AND a.attname = sc.nome_colonna
 AND a.attnum > 0
 AND NOT a.attisdropped
JOIN pg_type t
  ON t.oid = a.atttypid;

CREATE TEMP TABLE tmp_invalid_cond_numeric AS
SELECT DISTINCT sc.*
FROM tmp_sistema_codici_tipo sc
JOIN pg_proc p
  ON p.proname = format('trgfn_%s_gen_codice', sc.nome_tabella)
JOIN pg_namespace n
  ON n.oid = p.pronamespace
 AND n.nspname = sc.schema_tabella
WHERE sc.typcategory = 'N'
  AND position(format('NEW.%s = 0', sc.nome_colonna) IN COALESCE(p.prosrc, '')) = 0;

SELECT is(
    (SELECT count(*)::int FROM tmp_invalid_cond_numeric),
    0,
    'Trigger function numeriche con condizione NEW.<colonna> = 0'
);
SELECT diag(
    'Condizione numerica mancante: ' ||
    COALESCE(
      (SELECT string_agg(DISTINCT format('%s.%s', schema_tabella, format('trgfn_%s_gen_codice', nome_tabella)), ', ')
       FROM tmp_invalid_cond_numeric),
      'nessuna'
    )
);

CREATE TEMP TABLE tmp_invalid_cond_text AS
SELECT DISTINCT sc.*
FROM tmp_sistema_codici_tipo sc
JOIN pg_proc p
  ON p.proname = format('trgfn_%s_gen_codice', sc.nome_tabella)
JOIN pg_namespace n
  ON n.oid = p.pronamespace
 AND n.nspname = sc.schema_tabella
WHERE sc.typcategory <> 'N'
  AND position(format('btrim(NEW.%s::text)', sc.nome_colonna) IN COALESCE(p.prosrc, '')) = 0;

SELECT is(
    (SELECT count(*)::int FROM tmp_invalid_cond_text),
    0,
    'Trigger function testuali con btrim(NEW.<colonna>::text)'
);
SELECT diag(
    'Condizione testuale mancante: ' ||
    COALESCE(
      (SELECT string_agg(DISTINCT format('%s.%s', schema_tabella, format('trgfn_%s_gen_codice', nome_tabella)), ', ')
       FROM tmp_invalid_cond_text),
      'nessuna'
    )
);

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
