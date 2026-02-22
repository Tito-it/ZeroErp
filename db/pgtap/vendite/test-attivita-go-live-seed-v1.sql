-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: seed operativo go-live attivita_fatturabili (sorgenti + registry dominio)
-- ------------------------------------------------------------
-- Indice test (1..12):
-- 1) Policy sorgente PREVENTIVO presente e abilitata
-- 2) Policy sorgente CONTRATTO presente e abilitata
-- 3) Policy sorgente ORDINE_VENDITA presente e abilitata
-- 4) Policy sorgente ATTIVITA presente e abilitata
-- 5) Policy sorgente ATTIVITA_CONSUMI presente e abilitata
-- 6) Policy sorgente DDT_VENDITA presente e disabilitata
-- 7) Policy sorgente FATTURA presente e disabilitata
-- 8) Nessuna sorgente *_RIGA abilitata
-- 9) Resolve PREVENTIVO (require_abilitata=true) ritorna branch PREVENTIVI
-- 10) Resolve DDT_VENDITA (require_abilitata=true) genera errore
-- 11) Registry dominio ATTIVITA_FATTURABILI contiene task minimi attesi
-- 12) Implementazioni default dominio ATTIVITA_FATTURABILI tutte attive
-- ------------------------------------------------------------

BEGIN;
SELECT plan(12);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili_sorgenti_branch_policy p
    JOIN config.sorgenti s ON s.id = p.sorgente_tipo_id
    WHERE s.codice = 'PREVENTIVO'
      AND p.attivo IS TRUE
      AND p.abilitata IS TRUE
  ),
  'Policy sorgente PREVENTIVO presente e abilitata'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili_sorgenti_branch_policy p
    JOIN config.sorgenti s ON s.id = p.sorgente_tipo_id
    WHERE s.codice = 'CONTRATTO'
      AND p.attivo IS TRUE
      AND p.abilitata IS TRUE
  ),
  'Policy sorgente CONTRATTO presente e abilitata'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili_sorgenti_branch_policy p
    JOIN config.sorgenti s ON s.id = p.sorgente_tipo_id
    WHERE s.codice = 'ORDINE_VENDITA'
      AND p.attivo IS TRUE
      AND p.abilitata IS TRUE
  ),
  'Policy sorgente ORDINE_VENDITA presente e abilitata'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili_sorgenti_branch_policy p
    JOIN config.sorgenti s ON s.id = p.sorgente_tipo_id
    WHERE s.codice = 'ATTIVITA'
      AND p.attivo IS TRUE
      AND p.abilitata IS TRUE
  ),
  'Policy sorgente ATTIVITA presente e abilitata'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili_sorgenti_branch_policy p
    JOIN config.sorgenti s ON s.id = p.sorgente_tipo_id
    WHERE s.codice = 'ATTIVITA_CONSUMI'
      AND p.attivo IS TRUE
      AND p.abilitata IS TRUE
  ),
  'Policy sorgente ATTIVITA_CONSUMI presente e abilitata'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili_sorgenti_branch_policy p
    JOIN config.sorgenti s ON s.id = p.sorgente_tipo_id
    WHERE s.codice = 'DDT_VENDITA'
      AND p.attivo IS TRUE
      AND p.abilitata IS FALSE
  ),
  'Policy sorgente DDT_VENDITA presente e disabilitata'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili_sorgenti_branch_policy p
    JOIN config.sorgenti s ON s.id = p.sorgente_tipo_id
    WHERE s.codice = 'FATTURA'
      AND p.attivo IS TRUE
      AND p.abilitata IS FALSE
  ),
  'Policy sorgente FATTURA presente e disabilitata'
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
  'Nessuna sorgente *_RIGA abilitata'
);

SELECT ok(
  (
    SELECT r.branch_code = 'PREVENTIVI'
    FROM vendite.fn_resolve_attivita_sorgente_branch_policy(
      p_sorgente_tipo_id => (SELECT id FROM config.sorgenti WHERE codice = 'PREVENTIVO' LIMIT 1),
      p_require_abilitata => true
    ) r
  ),
  'Resolve PREVENTIVO (require_abilitata=true) ritorna branch PREVENTIVI'
);

SELECT throws_ok(
  $$
  SELECT *
  FROM vendite.fn_resolve_attivita_sorgente_branch_policy(
    p_sorgente_tipo_id => (SELECT id FROM config.sorgenti WHERE codice = 'DDT_VENDITA' LIMIT 1),
    p_require_abilitata => true
  );
  $$,
  'P0001',
  NULL,
  'Resolve DDT_VENDITA (require_abilitata=true) genera errore'
);

SELECT ok(
  (
    SELECT count(*) = 7
    FROM dbops.pipeline_task_registry r
    JOIN dbops.domini_task d ON d.id = r.dominio_id
    WHERE d.codice = 'ATTIVITA_FATTURABILI'
      AND r.attivo IS TRUE
      AND r.task_code IN (
        'acquisisci_preventivi',
        'acquisisci_contratti',
        'acquisisci_ordini',
        'acquisisci_attivita_consumi',
        'normalizza_attivita',
        'valida_attivita',
        'deduplica_attivita'
      )
  ),
  'Registry dominio ATTIVITA_FATTURABILI contiene task minimi attesi'
);

SELECT ok(
  (
    SELECT count(*) = 7
    FROM dbops.pipeline_task_registry r
    JOIN dbops.domini_task d ON d.id = r.dominio_id
    JOIN dbops.pipeline_task_registry_impl i ON i.task_registry_id = r.id
    WHERE d.codice = 'ATTIVITA_FATTURABILI'
      AND r.attivo IS TRUE
      AND i.attivo IS TRUE
      AND i.is_default IS TRUE
      AND i.handler_code IN (
        'acquisisci_preventivi_default',
        'acquisisci_contratti_default',
        'acquisisci_ordini_default',
        'acquisisci_attivita_consumi_default',
        'normalizza_attivita_default',
        'valida_attivita_default',
        'deduplica_attivita_default'
      )
  ),
  'Implementazioni default dominio ATTIVITA_FATTURABILI tutte attive'
);

SELECT * FROM finish();
ROLLBACK;
