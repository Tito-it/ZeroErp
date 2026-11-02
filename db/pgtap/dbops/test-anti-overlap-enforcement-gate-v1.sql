-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: CANCELLO ANTI-REGRESSIONE anti-overlap (refactor-overlap §3.5 / v2 §4.4).
--
-- Trasforma in cancello CI il bug PG18: gli ex_*_no_overlap erano stati declassati
-- da EXCLUDE a semplici CREATE INDEX (non enforçanti). Qui si asserisce che:
--  1) ogni constraint_name attivo in dbops.automazione_overlap esiste come EXCLUDE
--     (pg_constraint.contype='x') — mai mancante/declassato;
--  2) NESSUN oggetto ex_*_no_overlap e' un indice semplice (decoy) non sostenuto
--     da un constraint x/u/p;
--  3) i due vincoli temporali (UNIQUE WITHOUT OVERLAPS) restano contype='u'.
--
-- Read-only: nessuna sandbox, nessun cleanup.
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

SELECT plan(4);

-- 1) Tutte le righe active con constraint_name -> esistono come EXCLUDE (contype x)
SELECT is(
  (SELECT count(*)::int
     FROM dbops.automazione_overlap ao
    WHERE ao.active
      AND ao.constraint_name IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM pg_constraint con
          JOIN pg_class c     ON c.oid = con.conrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = ao.target_schema
           AND c.relname = ao.target_table
           AND con.conname = ao.constraint_name
           AND con.contype = 'x'
      )),
  0,
  'Ogni constraint_name attivo in automazione_overlap esiste come EXCLUDE (contype x)'
);

-- 2) Nessun ex_*_no_overlap e' un indice semplice (decoy) non-constraint
SELECT is(
  (SELECT count(*)::int
     FROM pg_class i
     JOIN pg_index ix     ON ix.indexrelid = i.oid
     JOIN pg_namespace n  ON n.oid = i.relnamespace
    WHERE i.relname LIKE 'ex\_%\_no\_overlap%'
      AND n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND NOT EXISTS (
        SELECT 1 FROM pg_constraint con
         WHERE con.conindid = i.oid AND con.contype IN ('x','u','p')
      )),
  0,
  'Nessun oggetto ex_*_no_overlap e'' un indice semplice (decoy): devono essere constraint'
);

-- 3) Vincoli temporali (PG18 SQL:2011) ancora presenti come UNIQUE WITHOUT OVERLAPS
SELECT ok(
  EXISTS (SELECT 1 FROM pg_constraint
           WHERE conname = 'uq_articoli_componenti_no_overlap' AND contype = 'u'),
  'catalogo.articoli_componenti ha il temporal UNIQUE (contype u)'
);

SELECT ok(
  EXISTS (SELECT 1 FROM pg_constraint
           WHERE conname = 'uq_uom_conv_no_overlap' AND contype = 'u'),
  'catalogo.unita_misura_conversioni ha il temporal UNIQUE (contype u)'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
