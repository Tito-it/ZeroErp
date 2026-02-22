-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: matrice sorgente->branch/policy attivita (changeset 20260222-16..17)
-- ------------------------------------------------------------
-- Indice test (1..14):
-- 1) Sorgenti minime disponibili
-- 2) Tabella attivita_fatturabili_sorgenti_branch_policy presente
-- 3) Funzione fn_resolve_attivita_sorgente_branch_policy presente
-- 4) Seed PREVENTIVO abilitata con branch PREVENTIVI
-- 5) Seed DDT_VENDITA disabilitata
-- 6) Seed FATTURA con acquisizione_mode=PULL e block_scope=GLOBAL
-- 7) Resolve PREVENTIVO (require_abilitata=true)
-- 8) Resolve ATTIVITA_CONSUMI (require_abilitata=true)
-- 9) Resolve DDT_VENDITA con require_abilitata=false
-- 10) Resolve DDT_VENDITA con require_abilitata=true -> errore
-- 11) Resolve FATTURA con require_abilitata=false
-- 12) Resolve con sorgente_tipo_id=0 -> errore
-- 13) Nessuna sorgente *_RIGA abilitata in seed
-- 14) Priorita sempre > 0
-- ------------------------------------------------------------

BEGIN;
SELECT plan(14);

CREATE TEMP TABLE tmp_refs_asbp AS
SELECT
  (SELECT id FROM config.sorgenti WHERE codice = 'PREVENTIVO' LIMIT 1) AS preventivo_id,
  (SELECT id FROM config.sorgenti WHERE codice = 'ATTIVITA_CONSUMI' LIMIT 1) AS consumi_id,
  (SELECT id FROM config.sorgenti WHERE codice = 'DDT_VENDITA' LIMIT 1) AS ddt_id,
  (SELECT id FROM config.sorgenti WHERE codice = 'FATTURA' LIMIT 1) AS fattura_id;

SELECT ok(
  (
    SELECT preventivo_id IS NOT NULL
       AND consumi_id IS NOT NULL
       AND ddt_id IS NOT NULL
       AND fattura_id IS NOT NULL
    FROM tmp_refs_asbp
  ),
  'Sorgenti minime disponibili'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.tables t
    WHERE t.table_schema = 'vendite'
      AND t.table_name = 'attivita_fatturabili_sorgenti_branch_policy'
  ),
  'Tabella attivita_fatturabili_sorgenti_branch_policy presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_resolve_attivita_sorgente_branch_policy'
  ),
  'Funzione fn_resolve_attivita_sorgente_branch_policy presente'
);

SELECT ok(
  (
    SELECT p.abilitata IS TRUE
       AND p.branch_code = 'PREVENTIVI'
       AND p.acquisizione_mode = 'PUSH'
       AND p.block_scope = 'BRANCH'
    FROM vendite.attivita_fatturabili_sorgenti_branch_policy p
    WHERE p.sorgente_tipo_id = (SELECT preventivo_id FROM tmp_refs_asbp)
      AND p.attivo IS TRUE
  ),
  'Seed PREVENTIVO abilitata con branch PREVENTIVI'
);

SELECT ok(
  (
    SELECT p.abilitata IS FALSE
    FROM vendite.attivita_fatturabili_sorgenti_branch_policy p
    WHERE p.sorgente_tipo_id = (SELECT ddt_id FROM tmp_refs_asbp)
      AND p.attivo IS TRUE
  ),
  'Seed DDT_VENDITA disabilitata'
);

SELECT ok(
  (
    SELECT p.abilitata IS FALSE
       AND p.acquisizione_mode = 'PULL'
       AND p.block_scope = 'GLOBAL'
    FROM vendite.attivita_fatturabili_sorgenti_branch_policy p
    WHERE p.sorgente_tipo_id = (SELECT fattura_id FROM tmp_refs_asbp)
      AND p.attivo IS TRUE
  ),
  'Seed FATTURA con acquisizione_mode=PULL e block_scope=GLOBAL'
);

SELECT ok(
  (
    SELECT r.branch_code = 'PREVENTIVI'
       AND r.abilitata IS TRUE
       AND r.acquisizione_mode = 'PUSH'
    FROM vendite.fn_resolve_attivita_sorgente_branch_policy(
      p_sorgente_tipo_id => (SELECT preventivo_id FROM tmp_refs_asbp),
      p_require_abilitata => true
    ) r
  ),
  'Resolve PREVENTIVO (require_abilitata=true)'
);

SELECT ok(
  (
    SELECT r.branch_code = 'CONSUMI'
       AND r.abilitata IS TRUE
    FROM vendite.fn_resolve_attivita_sorgente_branch_policy(
      p_sorgente_tipo_id => (SELECT consumi_id FROM tmp_refs_asbp),
      p_require_abilitata => true
    ) r
  ),
  'Resolve ATTIVITA_CONSUMI (require_abilitata=true)'
);

SELECT ok(
  (
    SELECT r.branch_code = 'DDT'
       AND r.abilitata IS FALSE
    FROM vendite.fn_resolve_attivita_sorgente_branch_policy(
      p_sorgente_tipo_id => (SELECT ddt_id FROM tmp_refs_asbp),
      p_require_abilitata => false
    ) r
  ),
  'Resolve DDT_VENDITA con require_abilitata=false'
);

SELECT throws_ok(
  $$
  SELECT *
  FROM vendite.fn_resolve_attivita_sorgente_branch_policy(
    p_sorgente_tipo_id => (SELECT ddt_id FROM tmp_refs_asbp),
    p_require_abilitata => true
  );
  $$,
  'P0001',
  NULL,
  'Resolve DDT_VENDITA con require_abilitata=true -> errore'
);

SELECT ok(
  (
    SELECT r.branch_code = 'POST_FATTURA'
       AND r.abilitata IS FALSE
       AND r.acquisizione_mode = 'PULL'
       AND r.block_scope = 'GLOBAL'
    FROM vendite.fn_resolve_attivita_sorgente_branch_policy(
      p_sorgente_tipo_id => (SELECT fattura_id FROM tmp_refs_asbp),
      p_require_abilitata => false
    ) r
  ),
  'Resolve FATTURA con require_abilitata=false'
);

SELECT throws_ok(
  $$
  SELECT *
  FROM vendite.fn_resolve_attivita_sorgente_branch_policy(
    p_sorgente_tipo_id => 0,
    p_require_abilitata => true
  );
  $$,
  'P0001',
  NULL,
  'Resolve con sorgente_tipo_id=0 -> errore'
);

SELECT ok(
  (
    SELECT count(*) = 0
    FROM vendite.attivita_fatturabili_sorgenti_branch_policy p
    JOIN config.sorgenti s ON s.id = p.sorgente_tipo_id
    WHERE p.attivo IS TRUE
      AND p.abilitata IS TRUE
      AND s.codice LIKE '%_RIGA'
  ),
  'Nessuna sorgente *_RIGA abilitata in seed'
);

SELECT ok(
  (
    SELECT count(*) = 0
    FROM vendite.attivita_fatturabili_sorgenti_branch_policy p
    WHERE p.attivo IS TRUE
      AND p.priorita <= 0
  ),
  'Priorita sempre > 0'
);

SELECT * FROM finish();
ROLLBACK;
