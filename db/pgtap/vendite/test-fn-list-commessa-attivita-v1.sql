-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: fn_list_commessa_attivita
-- (changeset 20260226-10)
-- ------------------------------------------------------------
-- Indice test (1..14):
--  1) Funzione fn_list_commessa_attivita presente
--  2) Commessa di test creata
--  3) Attivita` 1 inserita (APPROVATA, NON_EMESSA, mese 2026-07)
--  4) Attivita` 2 inserita (BOZZA, NON_EMESSA, mese 2026-08)
--  5) Senza filtri: restituisce tutte le attivita`
--  6) Filtro stato_emissione = NON_EMESSA
--  7) Filtro stato_approvazione = APPROVATA (solo attivita` 1)
--  8) Filtro stato_approvazione = BOZZA (solo attivita` 2)
--  9) Filtro competenza_mese = 2026-07 (solo attivita` 1)
-- 10) Filtro competenza_mese = 2026-08 (solo attivita` 2)
-- 11) Filtro competenza_mese inesistente = 2026-01 (0 righe)
-- 12) Paginazione: limit=1 restituisce 1 riga
-- 13) Paginazione: offset=1 salta la prima riga
-- 14) Guard: commessa_id NULL genera errore
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

SELECT plan(14);

-- ============================================================
-- FUNZIONE PRESENTE
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_commessa_attivita'
  ),
  'Funzione fn_list_commessa_attivita presente'
);

-- ============================================================
-- SETUP DATI TEST
-- ============================================================

-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba, BA legato all'azienda di chi agisce):
--   prima il billing account si pescava con LIMIT 1, e su un database
--   ricostruito da zero non c'era.
CREATE TEMP TABLE tmp_cli_lca AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('list commessa attivita');

CREATE TEMP TABLE tmp_refs_lca AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_lca) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_lca) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_cli_lca) AS istanza_utility_id,
  (
    SELECT a.id
    FROM catalogo.articoli a
    WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST
    LIMIT 1
  ) AS articolo_id,
  (
    SELECT u.id
    FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE
    ORDER BY u.id
    LIMIT 1
  ) AS uom_id,
  -- rev 2026-08-18 (bonifica baseline): il tipo documento fiscale mancava, e
  -- da quando esiste trg_commesse_attivita_a10_guard_tipo_doc_emittibile una
  -- riga che nasce APPROVATA + NON_EMESSA senza tipo_doc non e' piu' un caso
  -- ammesso: e' invisibile a fn_list_emittibili_lane, cioe' fatturato perso in
  -- silenzio. Il guard lo dice fail-fast e la fixture moriva li', prima di
  -- eseguire una sola asserzione.
  (
    SELECT t.id
    FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE
    ORDER BY t.id
    LIMIT 1
  ) AS tipo_doc_fiscale_id;

-- Crea commessa di test
CREATE TEMP TABLE tmp_commessa_lca AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_lca),
  p_utility_id => (SELECT utility_id FROM tmp_refs_lca),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-08-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_fn_list_commessa_attivita'),
  p_force_new => true
) AS commessa_id;

SELECT ok(
  (SELECT commessa_id IS NOT NULL FROM tmp_commessa_lca),
  'Commessa di test creata'
);

-- Attivita` 1: APPROVATA, NON_EMESSA, competenza_mese = 2026-07
CREATE TEMP TABLE tmp_att1_lca AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_lca),
  -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
  p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
  p_sorgente_uid => ((SELECT commessa_id FROM tmp_commessa_lca))::text,
  p_segment_key => ('SEG-LCA-1-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_lca),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_lca),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_lca),
  p_quantita => 1.000000,
  p_competenza_mese => DATE '2026-07-01',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_prezzo_snapshot => 10.0000000000,
  p_prezzo_base_snapshot => NULL,
  p_origine_prezzo => NULL,
  p_tipo_variazione_applicata => NULL,
  p_valore_variazione_applicata => NULL,
  p_promo_id => NULL,
  p_contratto_id => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot => NULL,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_lca),
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'LCA_ATT1')
) r;

SELECT ok(
  (SELECT commessa_attivita_id IS NOT NULL FROM tmp_att1_lca),
  'Attivita` 1 inserita (APPROVATA, NON_EMESSA, mese 2026-07)'
);

-- Attivita` 2: BOZZA, NON_EMESSA, competenza_mese = 2026-08
CREATE TEMP TABLE tmp_att2_lca AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_lca),
  -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
  p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
  p_sorgente_uid => ((SELECT commessa_id FROM tmp_commessa_lca))::text,
  p_segment_key => ('SEG-LCA-2-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_lca),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_lca),
  p_data_attivita => DATE '2026-08-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_lca),
  p_quantita => 2.000000,
  p_competenza_mese => DATE '2026-08-01',
  p_competenza_dal => DATE '2026-08-01',
  p_competenza_al => DATE '2026-08-31',
  p_prezzo_snapshot => 20.0000000000,
  p_prezzo_base_snapshot => NULL,
  p_origine_prezzo => NULL,
  p_tipo_variazione_applicata => NULL,
  p_valore_variazione_applicata => NULL,
  p_promo_id => NULL,
  p_contratto_id => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot => NULL,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_lca),
  p_stato_approvazione => 'BOZZA',
  p_stato_emissione => 'NON_EMESSA',
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'LCA_ATT2')
) r;

SELECT ok(
  (SELECT commessa_attivita_id IS NOT NULL FROM tmp_att2_lca),
  'Attivita` 2 inserita (BOZZA, NON_EMESSA, mese 2026-08)'
);

-- ============================================================
-- TEST: senza filtri restituisce tutte le attivita`
-- ============================================================

SELECT is(
  (
    SELECT count(*)::integer
    FROM vendite.fn_list_commessa_attivita(
      p_commessa_id => (SELECT commessa_id FROM tmp_commessa_lca)
    )
  ),
  2,
  'Senza filtri: restituisce tutte le attivita`'
);

-- ============================================================
-- TEST: filtro stato_emissione
-- ============================================================

SELECT is(
  (
    SELECT count(*)::integer
    FROM vendite.fn_list_commessa_attivita(
      p_commessa_id => (SELECT commessa_id FROM tmp_commessa_lca),
      p_stato_emissione => 'NON_EMESSA'
    )
  ),
  2,
  'Filtro stato_emissione = NON_EMESSA'
);

-- ============================================================
-- TEST: filtro stato_approvazione = APPROVATA
-- ============================================================

SELECT is(
  (
    SELECT count(*)::integer
    FROM vendite.fn_list_commessa_attivita(
      p_commessa_id => (SELECT commessa_id FROM tmp_commessa_lca),
      p_stato_approvazione => 'APPROVATA'
    )
  ),
  1,
  'Filtro stato_approvazione = APPROVATA (solo attivita` 1)'
);

-- ============================================================
-- TEST: filtro stato_approvazione = BOZZA
-- ============================================================

SELECT is(
  (
    SELECT count(*)::integer
    FROM vendite.fn_list_commessa_attivita(
      p_commessa_id => (SELECT commessa_id FROM tmp_commessa_lca),
      p_stato_approvazione => 'BOZZA'
    )
  ),
  1,
  'Filtro stato_approvazione = BOZZA (solo attivita` 2)'
);

-- ============================================================
-- TEST: filtro competenza_mese = 2026-07 (solo attivita` 1)
-- ============================================================

SELECT is(
  (
    SELECT count(*)::integer
    FROM vendite.fn_list_commessa_attivita(
      p_commessa_id => (SELECT commessa_id FROM tmp_commessa_lca),
      p_competenza_mese => DATE '2026-07-01'
    )
  ),
  1,
  'Filtro competenza_mese = 2026-07 (solo attivita` 1)'
);

-- ============================================================
-- TEST: filtro competenza_mese = 2026-08 (solo attivita` 2)
-- ============================================================

SELECT is(
  (
    SELECT count(*)::integer
    FROM vendite.fn_list_commessa_attivita(
      p_commessa_id => (SELECT commessa_id FROM tmp_commessa_lca),
      p_competenza_mese => DATE '2026-08-01'
    )
  ),
  1,
  'Filtro competenza_mese = 2026-08 (solo attivita` 2)'
);

-- ============================================================
-- TEST: filtro competenza_mese inesistente (0 righe)
-- ============================================================

SELECT is(
  (
    SELECT count(*)::integer
    FROM vendite.fn_list_commessa_attivita(
      p_commessa_id => (SELECT commessa_id FROM tmp_commessa_lca),
      p_competenza_mese => DATE '2026-01-01'
    )
  ),
  0,
  'Filtro competenza_mese inesistente = 2026-01 (0 righe)'
);

-- ============================================================
-- TEST: paginazione limit=1
-- ============================================================

SELECT is(
  (
    SELECT count(*)::integer
    FROM vendite.fn_list_commessa_attivita(
      p_commessa_id => (SELECT commessa_id FROM tmp_commessa_lca),
      p_limit => 1
    )
  ),
  1,
  'Paginazione: limit=1 restituisce 1 riga'
);

-- ============================================================
-- TEST: paginazione offset=1
-- ============================================================

SELECT is(
  (
    SELECT count(*)::integer
    FROM vendite.fn_list_commessa_attivita(
      p_commessa_id => (SELECT commessa_id FROM tmp_commessa_lca),
      p_limit => 10,
      p_offset => 1
    )
  ),
  1,
  'Paginazione: offset=1 salta la prima riga'
);

-- ============================================================
-- TEST: guard commessa_id NULL genera errore
-- ============================================================

SELECT throws_ok(
  $$
    SELECT * FROM vendite.fn_list_commessa_attivita(
      p_commessa_id => NULL
    );
  $$,
  'P0001',
  NULL,
  'Guard: commessa_id NULL genera errore'
);

SELECT * FROM finish();
ROLLBACK;
