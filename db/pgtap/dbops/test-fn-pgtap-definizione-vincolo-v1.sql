-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_definizione_vincolo — la definizione di un vincolo in una
--   forma sola, quella del vincolo nato sul database.
-- ChangeSet: 20261122-40.
--
-- ⭐ Le due forme si COSTRUISCONO, non si cercano nel catalogo: un `IN` su varchar
--   scritto qui nasce nella forma col cast sull'array; lo stesso vincolo scritto col
--   testo che la 18 metteva nel dump (`ANY ((ARRAY[...])::text[])`) la 19 lo riparsa
--   col cast su ogni elemento, come dopo un pg_upgrade. Su un database ricostruito da
--   zero la seconda forma non esiste da nessuna parte: senza costruirla il ramo che la
--   riscrive passerebbe a vuoto.
--
-- Elenco test (plan 8):
--   1) la forma nata resta com'e'
--   2) la forma riletta (cast su ogni elemento) e' davvero diversa: la premessa
--   3) ...e il BB la riporta alla forma nata
--   4) NOT IN (ALL) riletto: stessa cosa
--   5) un letterale con l'apice dentro attraversa la riscrittura
--   6) due array nello stesso vincolo: tutti e due
--   7) un array di text resta com'e' (non e' la forma riletta)
--   8) un vincolo che non c'e': NULL
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- Fixture: le stesse regole, scritte nelle due grafie
-- ============================================================
CREATE TEMP TABLE _v (
    a varchar(10),
    b varchar(10),
    t text,
    CONSTRAINT k_nato     CHECK (a IN ('P', 'C')),
    CONSTRAINT k_riletto  CHECK (((a)::text = ANY ((ARRAY['P'::character varying, 'C'::character varying])::text[]))),
    CONSTRAINT k_all      CHECK (((a)::text <> ALL ((ARRAY['X'::character varying, 'Y'::character varying])::text[]))),
    CONSTRAINT k_apice    CHECK (((a)::text = ANY ((ARRAY['l''uno'::character varying, 'due'::character varying])::text[]))),
    CONSTRAINT k_due      CHECK ((((a)::text = ANY ((ARRAY['P'::character varying])::text[]))
                                  AND ((b)::text = ANY ((ARRAY['Q'::character varying, 'R'::character varying])::text[])))),
    CONSTRAINT k_text     CHECK (t = ANY (ARRAY['UNO', 'DUE']))
) ON COMMIT DROP;

-- ============================================================
-- 1-3. La forma nata e quella riletta
-- ============================================================
SELECT is(
    dbops.fn_pgtap_definizione_vincolo('pg_temp._v', 'k_nato'),
    pg_get_constraintdef((SELECT oid FROM pg_constraint WHERE conrelid = 'pg_temp._v'::regclass AND conname = 'k_nato')),
    '1) la forma nata resta com''e''');

SELECT isnt(
    pg_get_constraintdef((SELECT oid FROM pg_constraint WHERE conrelid = 'pg_temp._v'::regclass AND conname = 'k_riletto')),
    pg_get_constraintdef((SELECT oid FROM pg_constraint WHERE conrelid = 'pg_temp._v'::regclass AND conname = 'k_nato')),
    '2) premessa: la forma riletta ha un altro testo (se diventa verde a vuoto, la 19 ha smesso di riscriverla)');

SELECT is(
    dbops.fn_pgtap_definizione_vincolo('pg_temp._v', 'k_riletto'),
    'CHECK (((a)::text = ANY ((ARRAY[''P''::character varying, ''C''::character varying])::text[])))',
    '3) la forma riletta torna alla forma nata');

-- ============================================================
-- 4-6. Le varianti
-- ============================================================
SELECT is(
    dbops.fn_pgtap_definizione_vincolo('pg_temp._v', 'k_all'),
    'CHECK (((a)::text <> ALL ((ARRAY[''X''::character varying, ''Y''::character varying])::text[])))',
    '4) NOT IN (ALL) riletto: torna alla forma nata');

SELECT is(
    dbops.fn_pgtap_definizione_vincolo('pg_temp._v', 'k_apice'),
    'CHECK (((a)::text = ANY ((ARRAY[''l''''uno''::character varying, ''due''::character varying])::text[])))',
    '5) un letterale con l''apice dentro attraversa la riscrittura');

SELECT is(
    dbops.fn_pgtap_definizione_vincolo('pg_temp._v', 'k_due'),
    'CHECK ((((a)::text = ANY ((ARRAY[''P''::character varying])::text[])) AND ((b)::text = ANY ((ARRAY[''Q''::character varying, ''R''::character varying])::text[]))))',
    '6) due array nello stesso vincolo: si riscrivono tutti e due');

-- ============================================================
-- 7-8. Cio' che non si tocca
-- ============================================================
SELECT is(
    dbops.fn_pgtap_definizione_vincolo('pg_temp._v', 'k_text'),
    pg_get_constraintdef((SELECT oid FROM pg_constraint WHERE conrelid = 'pg_temp._v'::regclass AND conname = 'k_text')),
    '7) un array di text resta com''e''');

SELECT is(
    dbops.fn_pgtap_definizione_vincolo('pg_temp._v', 'k_che_non_esiste'),
    NULL,
    '8) un vincolo che non c''e'': NULL');

SELECT * FROM finish();
ROLLBACK;
