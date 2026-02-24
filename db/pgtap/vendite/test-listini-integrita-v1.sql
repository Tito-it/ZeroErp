-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: integrita` schema listini (changeset 20260224-01)
-- ------------------------------------------------------------
-- Indice test (1..13):
-- 1) Riferimenti minimi disponibili (articolo/uom/BA/utility/emittente)
-- 2) listini.dominio invalido -> check violation
-- 3) listini.codice univoco -> unique violation
-- 4) listini_versioni.priorita > 0 -> check violation
-- 5) listini_versioni.date coerenti -> check violation
-- 6) listini_versioni no-overlap attivo -> exclusion violation
-- 7) listini_versioni (listino_id,codice_versione) univoco -> unique violation
-- 8) listini_righe.prezzo >= 0 -> check violation
-- 9) listini_righe chiave attiva univoca -> unique violation
-- 10) listini_righe duplicato consentito se riga precedente attivo=false
-- 11) listini_associazioni.priorita > 0 -> check violation
-- 12) listini_associazioni.date coerenti -> check violation
-- 13) listini_associazioni chiave attiva univoca -> unique violation
-- ------------------------------------------------------------

BEGIN;
SELECT plan(13);

CREATE TEMP TABLE tmp_refs_li AS
SELECT
  (
    SELECT a.id
    FROM catalogo.articoli a
    WHERE a.attivo IS TRUE
    ORDER BY a.data_insert, a.id
    LIMIT 1
  ) AS articolo_id,
  (
    SELECT u.id
    FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE
    ORDER BY u.data_insert, u.id
    LIMIT 1
  ) AS uom_id,
  (
    SELECT ba.id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS billing_account_id,
  (
    SELECT ba.utility_id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS utility_id,
  (
    SELECT anagrafiche.fn_get_emittente_fiscale_id(ba.id)
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS emittente_soggetto_ruolo_id;

SELECT ok(
  (
    SELECT articolo_id IS NOT NULL
      AND uom_id IS NOT NULL
      AND billing_account_id IS NOT NULL
      AND utility_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL
    FROM tmp_refs_li
  ),
  'Riferimenti minimi disponibili (articolo/uom/BA/utility/emittente)'
);

CREATE TEMP TABLE tmp_codes_li AS
SELECT
  ('LI_A_' || substr(md5(clock_timestamp()::text), 1, 12))::varchar(64) AS c_a,
  ('LI_B_' || substr(md5((clock_timestamp() + interval '1 second')::text), 1, 12))::varchar(64) AS c_b,
  ('LI_C_' || substr(md5((clock_timestamp() + interval '2 second')::text), 1, 12))::varchar(64) AS c_c;

SELECT throws_ok(
  $$
  INSERT INTO vendite.listini (codice, descrizione, dominio)
  VALUES ('LI_BAD_DOMAIN', 'bad domain', 'COMMERCIALE');
  $$,
  '23514',
  NULL,
  'listini.dominio invalido -> check violation'
);

CREATE TEMP TABLE tmp_l_a_li AS
WITH ins AS (
  INSERT INTO vendite.listini (codice, descrizione, dominio)
  SELECT c.c_a, 'listino A integrita', 'UTILITY'
  FROM tmp_codes_li c
  RETURNING id
)
SELECT id FROM ins;

SELECT throws_ok(
  $$
  INSERT INTO vendite.listini (codice, descrizione, dominio)
  SELECT c.c_a, 'dup codice', 'UTILITY'
  FROM tmp_codes_li c;
  $$,
  '23505',
  NULL,
  'listini.codice univoco -> unique violation'
);

SELECT throws_ok(
  $$
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, priorita, stato)
  SELECT l.id, 'BADP', DATE '2026-01-01', DATE '2026-12-31', 0, 'ATTIVA'
  FROM tmp_l_a_li l;
  $$,
  '23514',
  NULL,
  'listini_versioni.priorita > 0 -> check violation'
);

SELECT throws_ok(
  $$
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, priorita, stato)
  SELECT l.id, 'BADD', DATE '2026-06-30', DATE '2026-06-30', 10, 'ATTIVA'
  FROM tmp_l_a_li l;
  $$,
  '23514',
  NULL,
  'listini_versioni.date coerenti -> check violation'
);

CREATE TEMP TABLE tmp_v1_li AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, priorita, stato)
  SELECT l.id, 'V1', DATE '2026-01-01', DATE '2026-06-30', 10, 'ATTIVA'
  FROM tmp_l_a_li l
  RETURNING id
)
SELECT id FROM ins;

SELECT throws_ok(
  $$
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, priorita, stato)
  SELECT l.id, 'V2', DATE '2026-06-15', DATE '2026-12-31', 20, 'ATTIVA'
  FROM tmp_l_a_li l;
  $$,
  '23P01',
  NULL,
  'listini_versioni no-overlap attivo -> exclusion violation'
);

SELECT throws_ok(
  $$
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, priorita, stato)
  SELECT l.id, 'V1', DATE '2027-01-01', DATE '2027-12-31', 20, 'ATTIVA'
  FROM tmp_l_a_li l;
  $$,
  '23505',
  NULL,
  'listini_versioni (listino_id,codice_versione) univoco -> unique violation'
);

SELECT throws_ok(
  $$
  INSERT INTO vendite.listini_righe (
    listino_versione_id, articolo_id, uom_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id, prezzo
  )
  SELECT
    v.id, r.articolo_id, r.uom_id, r.billing_account_id, r.utility_id, r.emittente_soggetto_ruolo_id, -0.0100000000
  FROM tmp_v1_li v
  CROSS JOIN tmp_refs_li r;
  $$,
  '23514',
  NULL,
  'listini_righe.prezzo >= 0 -> check violation'
);

CREATE TEMP TABLE tmp_r1_li AS
WITH ins AS (
  INSERT INTO vendite.listini_righe (
    listino_versione_id, articolo_id, uom_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id, prezzo
  )
  SELECT
    v.id, r.articolo_id, r.uom_id, r.billing_account_id, r.utility_id, r.emittente_soggetto_ruolo_id, 12.3400000000
  FROM tmp_v1_li v
  CROSS JOIN tmp_refs_li r
  RETURNING id
)
SELECT id FROM ins;

SELECT throws_ok(
  $$
  INSERT INTO vendite.listini_righe (
    listino_versione_id, articolo_id, uom_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id, prezzo
  )
  SELECT
    v.id, r.articolo_id, r.uom_id, r.billing_account_id, r.utility_id, r.emittente_soggetto_ruolo_id, 99.9900000000
  FROM tmp_v1_li v
  CROSS JOIN tmp_refs_li r;
  $$,
  '23505',
  NULL,
  'listini_righe chiave attiva univoca -> unique violation'
);

UPDATE vendite.listini_righe
SET attivo = FALSE
WHERE id = (SELECT id FROM tmp_r1_li);

SELECT lives_ok(
  $$
  INSERT INTO vendite.listini_righe (
    listino_versione_id, articolo_id, uom_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id, prezzo
  )
  SELECT
    v.id, r.articolo_id, r.uom_id, r.billing_account_id, r.utility_id, r.emittente_soggetto_ruolo_id, 88.8800000000
  FROM tmp_v1_li v
  CROSS JOIN tmp_refs_li r;
  $$,
  'listini_righe duplicato consentito se riga precedente attivo=false'
);

SELECT throws_ok(
  $$
  INSERT INTO vendite.listini_associazioni (listino_id, priorita, valido_dal, valido_al)
  SELECT l.id, 0, DATE '2026-01-01', DATE '2026-12-31'
  FROM tmp_l_a_li l;
  $$,
  '23514',
  NULL,
  'listini_associazioni.priorita > 0 -> check violation'
);

SELECT throws_ok(
  $$
  INSERT INTO vendite.listini_associazioni (listino_id, priorita, valido_dal, valido_al)
  SELECT l.id, 100, DATE '2026-07-01', DATE '2026-07-01'
  FROM tmp_l_a_li l;
  $$,
  '23514',
  NULL,
  'listini_associazioni.date coerenti -> check violation'
);

CREATE TEMP TABLE tmp_a1_li AS
WITH ins AS (
  INSERT INTO vendite.listini_associazioni (
    listino_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id, priorita, valido_dal, valido_al
  )
  SELECT
    l.id, r.billing_account_id, r.utility_id, r.emittente_soggetto_ruolo_id, 10, DATE '2026-01-01', DATE '2026-12-31'
  FROM tmp_l_a_li l
  CROSS JOIN tmp_refs_li r
  RETURNING id
)
SELECT id FROM ins;

SELECT throws_ok(
  $$
  INSERT INTO vendite.listini_associazioni (
    listino_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id, priorita, valido_dal, valido_al
  )
  SELECT
    l.id, r.billing_account_id, r.utility_id, r.emittente_soggetto_ruolo_id, 20, DATE '2026-01-01', DATE '2026-12-31'
  FROM tmp_l_a_li l
  CROSS JOIN tmp_refs_li r;
  $$,
  '23505',
  NULL,
  'listini_associazioni chiave attiva univoca -> unique violation'
);

SELECT * FROM finish();
ROLLBACK;
