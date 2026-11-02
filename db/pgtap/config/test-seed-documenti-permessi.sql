-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: seed area + azioni processo per dominio documenti
--   - area config.aree_funzionali: 'documenti' attiva, schema_db coerente
--   - azioni config.azioni_processo: documenti_template_manage,
--                                    documenti_asset_manage attive
--   - le 2 azioni puntano alla stessa area 'documenti'
--   - vincoli UNIQUE/FK rispettati
-- ------------------------------------------------------------
-- Indice test (1..7):
--  1) Area 'documenti' presente, attiva, schema_db='documenti'
--  2) Azione 'documenti_template_manage' presente, attiva, pericolosa=false
--  3) Azione 'documenti_asset_manage' presente, attiva, pericolosa=false
--  4) Le 2 azioni puntano alla stessa area 'documenti'
--  5) UNIQUE permission_codename: duplicato 'documenti_template_manage' rifiutato
--  6) FK area_id: INSERT azione con area_id inesistente -> 23503
--  7) Ordinamento area >= 100 (consistenza con seed pratiche=110)
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

SELECT plan(7);

-- ============================================================
-- 1) Area 'documenti' presente, attiva, schema_db coerente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM config.aree_funzionali
     WHERE codice_interno = 'documenti'
       AND attivo = true
       AND schema_db = 'documenti'
  ),
  'Area documenti: presente, attiva, schema_db=documenti'
);

-- ============================================================
-- 2) Azione documenti_template_manage
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM config.azioni_processo
     WHERE permission_codename = 'documenti_template_manage'
       AND attivo = true
       AND pericolosa = false
  ),
  'Azione documenti_template_manage: presente, attiva, pericolosa=false'
);

-- ============================================================
-- 3) Azione documenti_asset_manage
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM config.azioni_processo
     WHERE permission_codename = 'documenti_asset_manage'
       AND attivo = true
       AND pericolosa = false
  ),
  'Azione documenti_asset_manage: presente, attiva, pericolosa=false'
);

-- ============================================================
-- 4) Le 2 azioni puntano alla stessa area 'documenti'
-- ============================================================
SELECT is(
  (SELECT COUNT(DISTINCT ap.area_id)::int
     FROM config.azioni_processo ap
     JOIN config.aree_funzionali af ON af.id = ap.area_id
    WHERE ap.permission_codename IN ('documenti_template_manage', 'documenti_asset_manage')
      AND af.codice_interno = 'documenti'),
  1,
  'Le 2 azioni documenti_* puntano alla stessa area (codice_interno=documenti)'
);

-- ============================================================
-- 5) UNIQUE permission_codename
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO config.azioni_processo (
      area_id, permission_codename, descrizione, pericolosa, attivo, meta
    )
    SELECT id, 'documenti_template_manage', 'duplicato', false, true, '{}'::jsonb
      FROM config.aree_funzionali
     WHERE codice_interno = 'documenti'$$,
  '23505',
  NULL,
  'UNIQUE permission_codename: duplicato documenti_template_manage rifiutato'
);

-- ============================================================
-- 6) FK area_id
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO config.azioni_processo (
      area_id, permission_codename, descrizione, pericolosa, attivo, meta
    )
    VALUES (999999, 'pgtap_fake_action', 'fk fail', false, true, '{}'::jsonb)$$,
  '23503',
  NULL,
  'FK area_id: area_id inesistente -> 23503'
);

-- ============================================================
-- 7) Ordinamento area >= 100 (coerente con seed pratiche=110)
-- ============================================================
SELECT cmp_ok(
  (SELECT ordinamento::integer FROM config.aree_funzionali
    WHERE codice_interno = 'documenti'),
  '>='::text,
  100::integer,
  'Ordinamento area documenti >= 100 (consistenza con aree applicative)'
);

SELECT * FROM finish();
ROLLBACK;
