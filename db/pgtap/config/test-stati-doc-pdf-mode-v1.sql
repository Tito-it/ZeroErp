-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: config.stati_doc_* — colonne pdf_mode / pdf_allow_allegati
--       (bottone PDF data-driven via capabilities)
-- Piano: piano-db-pdf-mode-capabilities-5-domini.md §6
-- ------------------------------------------------------------
-- Indice test (1..22):
--  1-5)   pdf_mode NOT NULL su tutte e 5 le stati_doc_*
--  6-10)  pdf_mode SENZA default (blinda §3: no degrado silenzioso)
-- 11-12)  pdf_allow_allegati NOT NULL + senza default (ddt campione)
-- 13)     CHECK pdf_mode rifiuta valore fuori dominio (23514)
-- 14)     guard NOT NULL: INSERT stato senza pdf_mode -> 23502
-- 15-22)  seed spot-check (incl. orfano PARZIALMENTE_EVASO, regola
--         ANNULLATO=ARCHIVE su tutti i domini, offerta EMESSA allegati)
--
-- 2026-07-16 — Normalizzazione ANNULLATO -> ARCHIVE (contratti/ordini/ddt).
-- Prima erano NONE «verbatim» dalle costanti FE; ora la regola e' unica su
-- tutti e 5 i domini: annullare non cancella la storia, l'archivio PDF di un
-- documento annullato resta consultabile (gia' vero per preventivi/offerte).
-- Test 17/19/22 aggiornati di conseguenza; il 21 non e' piu' un «quirk».
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

SELECT plan(22);

-- ============================================================
-- 1-5) pdf_mode NOT NULL su tutte e 5 le tabelle
-- ============================================================
SELECT col_not_null('config', 'stati_doc_preventivi', 'pdf_mode', '1) preventivi.pdf_mode NOT NULL');
SELECT col_not_null('config', 'stati_doc_offerte',    'pdf_mode', '2) offerte.pdf_mode NOT NULL');
SELECT col_not_null('config', 'stati_doc_contratti',  'pdf_mode', '3) contratti.pdf_mode NOT NULL');
SELECT col_not_null('config', 'stati_doc_ordini',     'pdf_mode', '4) ordini.pdf_mode NOT NULL');
SELECT col_not_null('config', 'stati_doc_ddt',        'pdf_mode', '5) ddt.pdf_mode NOT NULL');

-- ============================================================
-- 6-10) pdf_mode SENZA default (DROP DEFAULT applicato) — via pg_attribute
-- ============================================================
CREATE TEMP TABLE tmp_nodefault AS
SELECT c.relname AS tbl, a.atthasdef
  FROM pg_attribute a
  JOIN pg_class c ON c.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'config'
   AND a.attname = 'pdf_mode'
   AND c.relname IN ('stati_doc_preventivi','stati_doc_offerte','stati_doc_contratti',
                     'stati_doc_ordini','stati_doc_ddt');

SELECT ok((SELECT NOT atthasdef FROM tmp_nodefault WHERE tbl='stati_doc_preventivi'), '6) preventivi.pdf_mode senza default');
SELECT ok((SELECT NOT atthasdef FROM tmp_nodefault WHERE tbl='stati_doc_offerte'),    '7) offerte.pdf_mode senza default');
SELECT ok((SELECT NOT atthasdef FROM tmp_nodefault WHERE tbl='stati_doc_contratti'),  '8) contratti.pdf_mode senza default');
SELECT ok((SELECT NOT atthasdef FROM tmp_nodefault WHERE tbl='stati_doc_ordini'),     '9) ordini.pdf_mode senza default');
SELECT ok((SELECT NOT atthasdef FROM tmp_nodefault WHERE tbl='stati_doc_ddt'),        '10) ddt.pdf_mode senza default');

-- ============================================================
-- 11-12) pdf_allow_allegati NOT NULL + senza default (campione ddt)
-- ============================================================
SELECT col_not_null('config', 'stati_doc_ddt', 'pdf_allow_allegati', '11) ddt.pdf_allow_allegati NOT NULL');
SELECT ok(
  (SELECT NOT a.atthasdef
     FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
     JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='config' AND c.relname='stati_doc_ddt' AND a.attname='pdf_allow_allegati'),
  '12) ddt.pdf_allow_allegati senza default');

-- ============================================================
-- 13) CHECK pdf_mode rifiuta valore fuori dominio
-- ============================================================
SELECT throws_ok(
  $$UPDATE config.stati_doc_ddt SET pdf_mode = 'BOGUS' WHERE codice_interno = 'DRAFT'$$,
  '23514', NULL,
  '13) CHECK pdf_mode rifiuta valore fuori dominio (PREVIEW/ARCHIVE/NONE)');

-- ============================================================
-- 14) guard NOT NULL: INSERT stato senza pdf_mode -> 23502
--     (blinda §3: definizione-stato deve dichiarare pdf_mode)
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO config.stati_doc_ddt (id, codice_interno, codice, descrizione, attivo, ordine, meta, pdf_allow_allegati)
    VALUES (9990, 'TEST_NN', 'TEST_NN', 'Test not null', true, 999, '{}'::jsonb, false)$$,
  '23502', NULL,
  '14) INSERT stato senza pdf_mode -> NOT NULL violation (no degrado silenzioso)');

-- ============================================================
-- 15-22) Seed spot-check
-- ============================================================
-- DDT (pilota): DRAFT=PREVIEW, EMESSO=ARCHIVE, ANNULLATO=ARCHIVE
SELECT is(
  (SELECT pdf_mode FROM config.stati_doc_ddt WHERE codice_interno='DRAFT'),
  'PREVIEW', '15) ddt DRAFT -> PREVIEW');
SELECT is(
  (SELECT pdf_mode FROM config.stati_doc_ddt WHERE codice_interno='EMESSO'),
  'ARCHIVE', '16) ddt EMESSO -> ARCHIVE');
SELECT is(
  (SELECT pdf_mode FROM config.stati_doc_ddt WHERE codice_interno='ANNULLATO'),
  'ARCHIVE', '17) ddt ANNULLATO -> ARCHIVE (archivio consultabile su annullato)');

-- ORDINI: orfano PARZIALMENTE_EVASO classificato ARCHIVE (non NONE)
SELECT is(
  (SELECT pdf_mode FROM config.stati_doc_ordini WHERE codice_interno='PARZIALMENTE_EVASO'),
  'ARCHIVE', '18) ordini PARZIALMENTE_EVASO -> ARCHIVE (orfano classificato, non NONE)');
SELECT is(
  (SELECT pdf_mode FROM config.stati_doc_ordini WHERE codice_interno='ANNULLATO'),
  'ARCHIVE', '19) ordini ANNULLATO -> ARCHIVE (archivio consultabile su annullato)');

-- OFFERTE: EMESSA archive + allow_allegati=true (unico allegati vivo)
SELECT ok(
  (SELECT pdf_mode='ARCHIVE' AND pdf_allow_allegati IS TRUE
     FROM config.stati_doc_offerte WHERE codice_interno='EMESSA'),
  '20) offerte EMESSA -> ARCHIVE + allow_allegati=true');

-- PREVENTIVI: ANNULLATO=ARCHIVE (dal 2026-07-16 e' la regola, non piu' un quirk)
SELECT is(
  (SELECT pdf_mode FROM config.stati_doc_preventivi WHERE codice_interno='ANNULLATO'),
  'ARCHIVE', '21) preventivi ANNULLATO -> ARCHIVE');

-- CONTRATTI: DRAFT=PREVIEW, ATTIVO=ARCHIVE, ANNULLATO=ARCHIVE
SELECT ok(
  (SELECT pdf_mode FROM config.stati_doc_contratti WHERE codice_interno='DRAFT')='PREVIEW'
  AND (SELECT pdf_mode FROM config.stati_doc_contratti WHERE codice_interno='ATTIVO')='ARCHIVE'
  AND (SELECT pdf_mode FROM config.stati_doc_contratti WHERE codice_interno='ANNULLATO')='ARCHIVE',
  '22) contratti DRAFT/ATTIVO/ANNULLATO -> PREVIEW/ARCHIVE/ARCHIVE');

SELECT * FROM finish();
ROLLBACK;
