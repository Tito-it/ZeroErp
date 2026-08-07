-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: Pulizia config.sorgenti — scope + trigger polimorfo + RIGA
-- ------------------------------------------------------------
-- Indice test (1..9):
--  1) Colonna scope presente su config.sorgenti
--  2) Constraint chk_sorgenti_scope attivo
--  3) scope NOT NULL su tutti i record
--  4) Sorgenti PUSH_COMMESSA: 5 record attivi
--  5) Sorgenti PIPELINE_MARKER: 2 record attivi
--  6) Sorgenti ROW_VALIDATOR: tutti disattivati (attivo=false)
--  7) Sorgente POST_INVOICE: FATTURA attiva
--  8) Trigger polimorfo rimosso da attivita_fatturabili
--  9) Sorgenti RIGA archiviate con meta.archived=true
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

SELECT plan(9);

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
-- 9) Sorgenti RIGA archiviate con meta.archived=true
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
