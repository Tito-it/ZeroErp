-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Elenco test:
-- 1) Esiste almeno una utility in config.utilities
-- 2) Esistono almeno due tipi ruolo in config.tipi_ruoli
-- 3) Esiste una utility senza matrice attiva/valida (precondizione fail-open)
-- 4) Con utility senza matrice, il guard passa (fail-open)
-- 5) Inserita regola utility->ruolo ammesso
-- 6) Con matrice presente, il ruolo ammesso passa
-- 7) Con matrice presente, ruolo non ammesso viene bloccato
-- 8) Regola non attiva non abilita il ruolo
-- 9) Regola fuori validita non abilita il ruolo
-- 10) Duplicato utility+tipo_ruolo bloccato da UNIQUE
-- ------------------------------------------------------------

SELECT plan(10);

-- 1) Utility disponibili
CREATE TEMP TABLE tmp_utilities AS
SELECT id
FROM config.utilities
ORDER BY id;

SELECT ok(
  (SELECT count(*) FROM tmp_utilities) >= 1,
  'Esiste almeno una utility in config.utilities'
);

-- 2) Tipi ruolo disponibili
CREATE TEMP TABLE tmp_tipi_ruoli AS
SELECT id
FROM config.tipi_ruoli
ORDER BY id;

SELECT ok(
  (SELECT count(*) FROM tmp_tipi_ruoli) >= 2,
  'Esistono almeno due tipi ruolo in config.tipi_ruoli'
);

-- 3) Utility senza matrice attiva/valida
CREATE TEMP TABLE tmp_utility_no_matrix AS
SELECT u.id AS utility_id
FROM config.utilities u
WHERE NOT EXISTS (
  SELECT 1
  FROM config.utilities_tipi_ruolo m
  WHERE m.utility_id = u.id
    AND m.attivo = true
    AND (m.valido_dal IS NULL OR m.valido_dal <= CURRENT_DATE)
    AND (m.valido_al IS NULL OR m.valido_al >= CURRENT_DATE)
)
ORDER BY u.id
LIMIT 1;

SELECT is(
  (SELECT count(*)::int FROM tmp_utility_no_matrix),
  1,
  'Esiste una utility senza matrice attiva/valida (precondizione fail-open)'
);

-- Ruoli per test: uno ammesso e uno negato
CREATE TEMP TABLE tmp_ruoli_ctx AS
WITH r AS (
  SELECT id, row_number() OVER (ORDER BY id) AS rn
  FROM config.tipi_ruoli
)
SELECT
  (SELECT id FROM r WHERE rn = 1) AS tipo_ruolo_allow_id,
  (SELECT id FROM r WHERE rn = 2) AS tipo_ruolo_deny_id;

-- 4) Fail-open: nessuna matrice -> consentito
SELECT lives_ok(
  format(
    $$SELECT script.fn_guard_utility_tipo_ruolo(%s, %s, 'pgtap_fail_open');$$,
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_allow_id FROM tmp_ruoli_ctx)
  ),
  'Con utility senza matrice, il guard passa (fail-open)'
);

-- 5) Inserimento regola utility->ruolo ammesso
CREATE TEMP TABLE tmp_rule_allow AS
WITH ins AS (
  INSERT INTO config.utilities_tipi_ruolo (
    utility_id,
    tipo_ruolo_id,
    attivo,
    valido_dal,
    valido_al
  )
  SELECT
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_allow_id FROM tmp_ruoli_ctx),
    true,
    NULL::date,
    NULL::date
  RETURNING id
)
SELECT * FROM ins;

SELECT is(
  (SELECT count(*)::int FROM tmp_rule_allow),
  1,
  'Inserita regola utility->ruolo ammesso'
);

-- 6) Con matrice presente, ruolo ammesso -> passa
SELECT lives_ok(
  format(
    $$SELECT script.fn_guard_utility_tipo_ruolo(%s, %s, 'pgtap_allow');$$,
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_allow_id FROM tmp_ruoli_ctx)
  ),
  'Con matrice presente, il ruolo ammesso passa'
);

-- 7) Con matrice presente, ruolo non ammesso -> blocco
SELECT throws_ok(
  format(
    $$SELECT script.fn_guard_utility_tipo_ruolo(%s, %s, 'pgtap_deny');$$,
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_deny_id FROM tmp_ruoli_ctx)
  ),
  'P0001',
  format(
    'Tipo ruolo non ammesso per utility: %s tipo_ruolo_id: %s',
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_deny_id FROM tmp_ruoli_ctx)
  ),
  'Con matrice presente, ruolo non ammesso viene bloccato'
);

-- 8) Regola non attiva non abilita il ruolo deny
INSERT INTO config.utilities_tipi_ruolo (
  utility_id,
  tipo_ruolo_id,
  attivo,
  valido_dal,
  valido_al
)
SELECT
  (SELECT utility_id FROM tmp_utility_no_matrix),
  (SELECT tipo_ruolo_deny_id FROM tmp_ruoli_ctx),
  false,
  NULL::date,
  NULL::date;

SELECT throws_ok(
  format(
    $$SELECT script.fn_guard_utility_tipo_ruolo(%s, %s, 'pgtap_deny_inactive');$$,
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_deny_id FROM tmp_ruoli_ctx)
  ),
  'P0001',
  format(
    'Tipo ruolo non ammesso per utility: %s tipo_ruolo_id: %s',
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_deny_id FROM tmp_ruoli_ctx)
  ),
  'Regola non attiva non abilita il ruolo'
);

-- 9) Regola fuori validita non abilita il ruolo deny
UPDATE config.utilities_tipi_ruolo
SET attivo = true,
    valido_dal = CURRENT_DATE + 1,
    valido_al = NULL
WHERE utility_id = (SELECT utility_id FROM tmp_utility_no_matrix)
  AND tipo_ruolo_id = (SELECT tipo_ruolo_deny_id FROM tmp_ruoli_ctx);

SELECT throws_ok(
  format(
    $$SELECT script.fn_guard_utility_tipo_ruolo(%s, %s, 'pgtap_deny_out_of_validity');$$,
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_deny_id FROM tmp_ruoli_ctx)
  ),
  'P0001',
  format(
    'Tipo ruolo non ammesso per utility: %s tipo_ruolo_id: %s',
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_deny_id FROM tmp_ruoli_ctx)
  ),
  'Regola fuori validita non abilita il ruolo'
);

-- 10) Duplicato utility+tipo_ruolo -> UNIQUE
SELECT throws_ok(
  format(
    $$INSERT INTO config.utilities_tipi_ruolo(utility_id, tipo_ruolo_id, attivo)
      VALUES (%s, %s, true);$$,
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_allow_id FROM tmp_ruoli_ctx)
  ),
  '23505',
  NULL,
  'Duplicato utility+tipo_ruolo bloccato da UNIQUE'
);

SELECT * FROM finish();
