-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Funzione: dbops.fn_get_lookup_codici
-- ------------------------------------------------------------
-- Indice test
-- 1) Presenza funzione dbops.fn_get_lookup_codici
-- 2) utilities: ordine descrizione ASC (no filtro attivo)
-- 3) utilities: ordine codice DESC (no filtro attivo)
-- 4) iva: ordine descrizione ASC (no filtro attivo)
-- 5) iva: ordine codice DESC (no filtro attivo)
-- 6) temp table: default p_attivo_only=true filtra non attivi
-- 7) temp table: p_attivo_only=false include anche non attivi
-- 8) temp table: ordine descrizione DESC
-- 9) errore su p_order_col non valido
-- 10) errore su p_order_dir non valido
-- 11) errore su id uuid non ammesso
-- 12) ⭐ spareggio: a parita' di descrizione l'ordine e' per id, nello STESSO
--     verso (ASC e DESC, caso COSTRUITO con quattro descrizioni uguali)
-- 13) ⭐ p_limit/p_offset sfogliano senza ripetere ne' saltare righe: le pagine
--     da due, concatenate, sono la lista intera nello stesso ordine
--
-- ⭐ D57 di brief-db-revisione-dbops (giro 7): fino al 2026-11-07 l'ORDER BY non
--   aveva spareggio, e a parita' di valore l'ordine lo sceglieva il piano. Le
--   attese dei test 2-5 prendono lo spareggio anche loro: senza, confrontavano due
--   ordini entrambi indeterminati, e il verde dipendeva dai dati del catalogo.
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

SELECT plan(13);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'dbops'
      AND p.proname = 'fn_get_lookup_codici'
  ),
  'Presenza funzione dbops.fn_get_lookup_codici'
);

SELECT results_eq(
  $$
  SELECT id, codice, descrizione
  FROM dbops.fn_get_lookup_codici(
    'config.utilities'::regclass,
    'descrizione',
    'ASC',
    false,
    5,
    0
  )
  $$,
  $$
  SELECT u.id::bigint, u.codice::text, u.descrizione::text
  FROM config.utilities u
  ORDER BY u.descrizione ASC NULLS LAST, u.id ASC
  LIMIT 5
  $$,
  'utilities: ordine descrizione ASC (no filtro attivo)'
);

SELECT results_eq(
  $$
  SELECT id, codice, descrizione
  FROM dbops.fn_get_lookup_codici(
    'config.utilities'::regclass,
    'codice',
    'DESC',
    false,
    5,
    0
  )
  $$,
  $$
  SELECT u.id::bigint, u.codice::text, u.descrizione::text
  FROM config.utilities u
  ORDER BY u.codice DESC NULLS LAST, u.id DESC
  LIMIT 5
  $$,
  'utilities: ordine codice DESC (no filtro attivo)'
);

SELECT results_eq(
  $$
  SELECT id, codice, descrizione
  FROM dbops.fn_get_lookup_codici(
    'config.iva'::regclass,
    'descrizione',
    'ASC',
    false,
    5,
    0
  )
  $$,
  $$
  SELECT i.id::bigint, i.codice::text, i.descrizione::text
  FROM config.iva i
  ORDER BY i.descrizione ASC NULLS LAST, i.id ASC
  LIMIT 5
  $$,
  'iva: ordine descrizione ASC (no filtro attivo)'
);

SELECT results_eq(
  $$
  SELECT id, codice, descrizione
  FROM dbops.fn_get_lookup_codici(
    'config.iva'::regclass,
    'codice',
    'DESC',
    false,
    5,
    0
  )
  $$,
  $$
  SELECT i.id::bigint, i.codice::text, i.descrizione::text
  FROM config.iva i
  ORDER BY i.codice DESC NULLS LAST, i.id DESC
  LIMIT 5
  $$,
  'iva: ordine codice DESC (no filtro attivo)'
);

CREATE TEMP TABLE tmp_lookup_attivo (
  id bigint PRIMARY KEY,
  codice text NOT NULL,
  descrizione text NOT NULL,
  attivo boolean NOT NULL
);

INSERT INTO tmp_lookup_attivo (id, codice, descrizione, attivo)
VALUES
  (1, 'C01', 'Alpha', true),
  (2, 'C02', 'Beta', false),
  (3, 'C03', 'Gamma', true);

SELECT results_eq(
  $$
  SELECT id, codice, descrizione
  FROM dbops.fn_get_lookup_codici('pg_temp.tmp_lookup_attivo'::regclass)
  $$,
  $$
  SELECT id::bigint, codice::text, descrizione::text
  FROM pg_temp.tmp_lookup_attivo
  WHERE attivo IS TRUE
  ORDER BY descrizione ASC NULLS LAST, id ASC
  LIMIT 200
  $$,
  'temp table: default p_attivo_only=true filtra non attivi'
);

SELECT results_eq(
  $$
  SELECT id, codice, descrizione
  FROM dbops.fn_get_lookup_codici(
    'pg_temp.tmp_lookup_attivo'::regclass,
    'descrizione',
    'ASC',
    false,
    200,
    0
  )
  $$,
  $$
  SELECT id::bigint, codice::text, descrizione::text
  FROM pg_temp.tmp_lookup_attivo
  ORDER BY descrizione ASC NULLS LAST, id ASC
  LIMIT 200
  $$,
  'temp table: p_attivo_only=false include anche non attivi'
);

SELECT results_eq(
  $$
  SELECT id, codice, descrizione
  FROM dbops.fn_get_lookup_codici(
    'pg_temp.tmp_lookup_attivo'::regclass,
    'descrizione',
    'DESC',
    false,
    200,
    0
  )
  $$,
  $$
  SELECT id::bigint, codice::text, descrizione::text
  FROM pg_temp.tmp_lookup_attivo
  ORDER BY descrizione DESC NULLS LAST, id DESC
  LIMIT 200
  $$,
  'temp table: ordine descrizione DESC'
);

SELECT throws_ok(
  $$
  SELECT *
  FROM dbops.fn_get_lookup_codici(
    'pg_temp.tmp_lookup_attivo'::regclass,
    'colonna_non_valida',
    'ASC',
    false
  );
  $$,
  'P0001',
  NULL,
  'errore su p_order_col non valido'
);

SELECT throws_ok(
  $$
  SELECT *
  FROM dbops.fn_get_lookup_codici(
    'pg_temp.tmp_lookup_attivo'::regclass,
    'codice',
    'UP',
    false
  );
  $$,
  'P0001',
  NULL,
  'errore su p_order_dir non valido'
);

CREATE TEMP TABLE tmp_lookup_uuid (
  id uuid PRIMARY KEY,
  codice text NOT NULL,
  descrizione text NOT NULL
);

INSERT INTO tmp_lookup_uuid (id, codice, descrizione)
VALUES ('00000000-0000-0000-0000-000000000001', 'U01', 'UUID row');

SELECT throws_ok(
  $$
  SELECT *
  FROM dbops.fn_get_lookup_codici(
    'pg_temp.tmp_lookup_uuid'::regclass,
    'descrizione',
    'ASC',
    false
  );
  $$,
  'P0001',
  NULL,
  'errore su id uuid non ammesso'
);

-- ------------------------------------------------------------
-- 12-13) Lo spareggio sull'id (D57). Quattro righe con la stessa descrizione,
--   inserite in un ordine che non e' quello degli id: senza spareggio l'ordine
--   lo deciderebbe il piano (qui, l'ordine fisico di inserimento).
-- ------------------------------------------------------------
CREATE TEMP TABLE tmp_lookup_pari (
  id bigint PRIMARY KEY,
  codice text NOT NULL,
  descrizione text NOT NULL
);

INSERT INTO tmp_lookup_pari (id, codice, descrizione)
VALUES
  (40, 'P40', 'Uguale'),
  (10, 'P10', 'Uguale'),
  (30, 'P30', 'Uguale'),
  (20, 'P20', 'Uguale'),
  (50, 'P50', 'Zeta');

SELECT ok(
  (SELECT array_agg(id) FROM dbops.fn_get_lookup_codici(
     'pg_temp.tmp_lookup_pari'::regclass, 'descrizione', 'ASC', false, NULL, 0))
    = ARRAY[10, 20, 30, 40, 50]::bigint[]
  AND
  (SELECT array_agg(id) FROM dbops.fn_get_lookup_codici(
     'pg_temp.tmp_lookup_pari'::regclass, 'descrizione', 'DESC', false, NULL, 0))
    = ARRAY[50, 40, 30, 20, 10]::bigint[],
  '12) Spareggio: a parita'' di descrizione si ordina per id, nello stesso verso (ASC e DESC)'
);

SELECT is(
  (SELECT array_agg(r.id ORDER BY pag.n, r.ord)
     FROM generate_series(0, 2) pag(n)
     CROSS JOIN LATERAL (
       SELECT f.id, row_number() OVER () AS ord
         FROM dbops.fn_get_lookup_codici(
                'pg_temp.tmp_lookup_pari'::regclass, 'descrizione', 'ASC', false, 2, pag.n * 2) f
     ) r),
  ARRAY[10, 20, 30, 40, 50]::bigint[],
  '13) Le pagine da due (offset 0, 2, 4), concatenate, sono la lista intera: nessuna riga ripetuta o saltata'
);

SELECT * FROM finish();

ROLLBACK;
