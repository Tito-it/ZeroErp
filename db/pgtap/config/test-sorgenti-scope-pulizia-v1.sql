-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: Pulizia config.sorgenti — scope + trigger polimorfo + RIGA
-- ------------------------------------------------------------
-- Indice test (1..10):
--  1) Colonna scope presente su config.sorgenti
--  2) Constraint chk_sorgenti_scope attivo
--  3) scope NOT NULL su tutti i record
--  4) Sorgenti PUSH_COMMESSA: 5 record attivi
--  5) Sorgenti PIPELINE_MARKER: 2 record attivi
--  6) Sorgenti ROW_VALIDATOR: tutti disattivati (attivo=false)
--  7) Sorgente POST_INVOICE: FATTURA attiva
--  8) Trigger polimorfo rimosso da attivita_fatturabili
--  9) Branch policy: nessuna riga RIGA residua
-- 10) Sorgenti RIGA archiviate con meta.archived=true
-- ------------------------------------------------------------

BEGIN;
SELECT plan(10);

-- ============================================================
-- 1) Colonna scope presente su config.sorgenti
-- ============================================================
SELECT has_column(
  'config', 'sorgenti', 'scope',
  'Colonna scope presente su config.sorgenti'
);

-- ============================================================
-- 2) Constraint chk_sorgenti_scope attivo
-- ============================================================
SELECT col_has_check(
  'config', 'sorgenti', 'scope',
  'Check constraint su colonna scope'
);

-- ============================================================
-- 3) scope NOT NULL su tutti i record
-- ============================================================
SELECT col_not_null(
  'config', 'sorgenti', 'scope',
  'Colonna scope e` NOT NULL'
);

-- ============================================================
-- 4) Sorgenti PUSH_COMMESSA: 5 record attivi
-- ============================================================
SELECT ok(
  (
    SELECT count(*) = 5
    FROM config.sorgenti s
    WHERE s.scope = 'PUSH_COMMESSA'
      AND s.attivo IS TRUE
  ),
  'PUSH_COMMESSA: 5 sorgenti attive (PREVENTIVO, CONTRATTO, ORDINE_VENDITA, DDT_VENDITA, ATTIVITA_CONSUMI)'
);

-- ============================================================
-- 5) Sorgenti PIPELINE_MARKER: 2 record attivi
-- ============================================================
SELECT ok(
  (
    SELECT count(*) = 2
    FROM config.sorgenti s
    WHERE s.scope = 'PIPELINE_MARKER'
      AND s.attivo IS TRUE
  ),
  'PIPELINE_MARKER: 2 sorgenti attive (ATTIVITA, COMMESSA)'
);

-- ============================================================
-- 6) Sorgenti ROW_VALIDATOR: tutti disattivati
-- ============================================================
SELECT ok(
  (
    SELECT count(*) = 0
    FROM config.sorgenti s
    WHERE s.scope = 'ROW_VALIDATOR'
      AND s.attivo IS TRUE
  ),
  'ROW_VALIDATOR: nessuna sorgente attiva (tutte archiviate)'
);

-- ============================================================
-- 7) Sorgente POST_INVOICE: FATTURA attiva
-- ============================================================
SELECT ok(
  (
    SELECT count(*) = 1
    FROM config.sorgenti s
    WHERE s.scope = 'POST_INVOICE'
      AND s.codice = 'FATTURA'
      AND s.attivo IS TRUE
  ),
  'POST_INVOICE: FATTURA attiva'
);

-- ============================================================
-- 8) Trigger polimorfo rimosso da attivita_fatturabili
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM pg_trigger t
    WHERE t.tgrelid = 'vendite.attivita_fatturabili'::regclass
      AND t.tgname = 'trg_attivita_fatturabili_a10_guard_fonte_ins_upd'
  ),
  'Trigger polimorfo trg_attivita_fatturabili_a10_guard_fonte_ins_upd rimosso'
);

-- ============================================================
-- 9) Branch policy: nessuna riga RIGA residua
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili_sorgenti_branch_policy bp
    WHERE bp.sorgente_tipo_id IN (3, 5, 7, 9, 11)
  ),
  'Branch policy: nessuna riga per sorgenti RIGA (3,5,7,9,11)'
);

-- ============================================================
-- 10) Sorgenti RIGA archiviate con meta.archived=true
-- ============================================================
SELECT ok(
  (
    SELECT count(*) = 5
    FROM config.sorgenti s
    WHERE s.scope = 'ROW_VALIDATOR'
      AND s.attivo IS FALSE
      AND (s.meta->>'archived')::boolean IS TRUE
  ),
  'Sorgenti RIGA: 5 record archiviati con meta.archived=true'
);

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
