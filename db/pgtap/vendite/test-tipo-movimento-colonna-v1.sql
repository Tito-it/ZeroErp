-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2d/2e): chiavi del push e ambito degli indirizzi col codice della sorgente.
-- pgTAP test per Zero ERP
-- Test: tipo_movimento promosso da meta (jsonb) a COLONNA su
--       commesse_attivita + attivita_fatturabili, con dominio esteso a ONERE
--       e propagazione 1:1 nell'emissione.
-- (changeset 20260717-01..04 — brief-db-immutabilita-quantita-e-porta-oneri
--  §4c.2, anticipato perche' il contatore tenuti-fatturati della slice
--  DDT/resi filtra su tipo_movimento = 'NORMALE')
-- ------------------------------------------------------------
-- Indice test (1..10):
--   1) commesse_attivita ha la colonna tipo_movimento
--   2) attivita_fatturabili ha la colonna tipo_movimento
--   3) fn_upsert senza p_tipo_movimento -> colonna = NORMALE (default)
--   4) fn_upsert con p_tipo_movimento => 'ONERE' -> colonna = ONERE (dominio esteso)
--   5) una casa sola: meta NON contiene piu' tipo_movimento
--   6) tipo_consumo e' ritirato (20261013-16): la madre non lo scrive in meta
--   7) fn_upsert rifiuta un tipo_movimento fuori dominio (fail-fast parlante)
--   8) il CHECK DB e' la difesa finale: UPDATE diretto fuori dominio bloccato
--   9) emit propaga NORMALE su attivita_fatturabili
--  10) emit propaga ONERE su attivita_fatturabili (cintura del contatore:
--      la riga della porta onere non e' merce)
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

SELECT plan(10);

-- ============================================================
-- TEST 1-2) Le colonne esistono (DDL 20260717-01/02)
-- ============================================================
SELECT has_column('vendite', 'commesse_attivita', 'tipo_movimento',
  '1. commesse_attivita.tipo_movimento e'' una colonna (non piu'' una chiave jsonb)');

SELECT has_column('vendite', 'attivita_fatturabili', 'tipo_movimento',
  '2. attivita_fatturabili.tipo_movimento e'' una colonna (lo specchio della CA)');

-- ============================================================
-- SETUP: riferimenti minimi (stesso pattern di
--        test-fn-emit-attivita-propaga-audit-pricing-v1)
-- ============================================================
CREATE TEMP TABLE tmp_refs_tm AS
SELECT
  (
    SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS billing_account_id,
  (
    SELECT ba.utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS utility_id,
  (
    SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS istanza_utility_id,
  (
    SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE ORDER BY a.data_insert DESC NULLS LAST LIMIT 1
  ) AS articolo_id,
  (
    SELECT u.id FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1
  ) AS uom_id,
  (
    SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'COMMESSA' LIMIT 1
  ) AS root_sorgente_tipo_id,
  (
    SELECT t.id FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1
  ) AS tipo_doc_fiscale_id;

CREATE TEMP TABLE tmp_commessa_tm AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_tm),
  p_utility_id => (SELECT utility_id FROM tmp_refs_tm),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_tipo_movimento'),
  p_force_new => true
) AS commessa_id;

-- Sorgente ROOT obbligatoria per l'emit (il primo link diventa ROOT)
CREATE TEMP TABLE tmp_link_tm AS
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_tm),
  p_sorgente_tipo_id => (SELECT root_sorgente_tipo_id FROM tmp_refs_tm),
  -- ROOT: sorgente COMMESSA (key_selector='id') con uid = id della commessa
  -- stessa: esiste per costruzione, quindi passa il guard sorgente polimorfa
  -- (formato id::text + esistenza nel target). fn_emit pretende solo che una
  -- ROOT esista, non ne dereferenzia il tipo. rev 2026-07-27 (bonifica).
  p_sorgente_uid => (SELECT commessa_id FROM tmp_commessa_tm)::text,
  p_sorgente_riga => 1,
  p_meta => jsonb_build_object('test_scope', 'pgtap_tipo_movimento')
) AS link_id;

-- ------------------------------------------------------------
-- Riga 1 — push "normale": p_tipo_movimento OMESSO di proposito,
--          per provare il DEFAULT della firma (e' il percorso dei sei lister).
-- ------------------------------------------------------------
CREATE TEMP TABLE tmp_ca_normale AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_tm),
  -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
  p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
  p_sorgente_uid => ((SELECT commessa_id FROM tmp_commessa_tm))::text,
  p_segment_key => ('ORDINE_VENDITA:TM:R:' || substr(md5(clock_timestamp()::text), 1, 12))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_tm),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_tm),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_tm),
  p_quantita => 10.000000,
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
  -- tipo_doc valorizzato: il guard tipo_doc emittibile (20260619-05) lo esige
  -- sulle righe APPROVATA+NON_EMESSA.
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_tm),
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_meta => jsonb_build_object('case', 'TIPO_MOV_NORMALE')
) r;

-- ------------------------------------------------------------
-- Riga 2 — porta onere: registro ONERE, quantita 1 fissa positiva
--          (la disciplina della porta; qui interessa il registro).
--          Segment MAN: — namespace che non si incrocia coi push.
-- ------------------------------------------------------------
CREATE TEMP TABLE tmp_ca_onere AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_tm),
  p_segment_key => ('MAN:TM:' || substr(md5(clock_timestamp()::text), 1, 12))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_tm),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_tm),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_tm),
  p_quantita => 1.000000,
  p_competenza_mese => DATE '2026-07-01',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_prezzo_snapshot => 50.0000000000,
  p_prezzo_base_snapshot => NULL,
  p_origine_prezzo => NULL,
  p_tipo_variazione_applicata => NULL,
  p_valore_variazione_applicata => NULL,
  p_promo_id => NULL,
  p_contratto_id => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot => NULL,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_tm),
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_tipo_movimento => 'ONERE',
  p_meta => jsonb_build_object('case', 'TIPO_MOV_ONERE'),
  -- rev 2026-07-27 (bonifica): la causale e' obbligatoria se e solo se
  -- tipo_movimento='ONERE' (CHECK chk_commesse_attivita_causale_onere,
  -- 20260721-04, entrato DOPO questo test).
  p_causale_onere_id => (SELECT id FROM config.causali_onere WHERE attivo ORDER BY id LIMIT 1)
) r;

-- ============================================================
-- TEST 3-4) La fn scrive la colonna
-- ============================================================
SELECT is(
  (SELECT ca.tipo_movimento FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_ca_normale)),
  'NORMALE'::varchar,
  '3. fn_upsert senza p_tipo_movimento -> colonna = NORMALE (default di firma)'
);

SELECT is(
  (SELECT ca.tipo_movimento FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_ca_onere)),
  'ONERE'::varchar,
  '4. fn_upsert con ONERE -> colonna = ONERE (dominio esteso, porta onere)'
);

-- ============================================================
-- TEST 5-6) Una casa sola: il jsonb non ospita piu' il registro,
--           e nemmeno tipo_consumo, ritirato il 2026-10-13 (20261013-16).
-- ============================================================
SELECT ok(
  NOT (SELECT ca.meta ? 'tipo_movimento' FROM vendite.commesse_attivita ca
        WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_ca_onere)),
  '5. una casa sola: meta non contiene piu'' tipo_movimento'
);

SELECT ok(
  NOT (SELECT ca.meta ? 'tipo_consumo' FROM vendite.commesse_attivita ca
        WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_ca_onere)),
  '6. tipo_consumo ritirato: la madre non lo scrive in meta'
);

-- ============================================================
-- TEST 7) Fail-fast parlante della fn su dominio
-- ============================================================
SELECT throws_ok(
  format($$ SELECT vendite.fn_upsert_commessa_attivita(
      p_commessa_id => %s,
      p_segment_key => 'MAN:TM:BAD'::varchar,
      p_articolo_id => %L::uuid,
      p_istanza_utility_id => %s,
      p_data_attivita => DATE '2026-07-15',
      p_uom_id => %s,
      p_quantita => 1.0,
      p_competenza_mese => DATE '2026-07-01',
      p_competenza_dal => DATE '2026-07-01',
      p_competenza_al => DATE '2026-07-31',
      p_prezzo_snapshot => 1.0,
      p_prezzo_base_snapshot => NULL,
      p_origine_prezzo => NULL,
      p_tipo_variazione_applicata => NULL,
      p_valore_variazione_applicata => NULL,
      p_promo_id => NULL,
      p_contratto_id => NULL,
      p_categoria_cliente_id_snapshot => NULL,
      p_classe_utenza_id_snapshot => NULL,
      p_tipo_movimento => 'STORNO_MERCE'
    ) $$,
    (SELECT commessa_id FROM tmp_commessa_tm),
    (SELECT articolo_id FROM tmp_refs_tm),
    (SELECT istanza_utility_id FROM tmp_refs_tm),
    (SELECT uom_id FROM tmp_refs_tm)
  ),
  'P0001',
  NULL,
  '7. fn_upsert rifiuta un tipo_movimento fuori dominio (fail-fast parlante)'
);

-- ============================================================
-- TEST 8) Il CHECK DB e' la difesa finale — era il senso della promozione:
--         il jsonb non vincolava nulla, un UPDATE diretto passava.
-- ============================================================
SELECT throws_ok(
  format($$ UPDATE vendite.commesse_attivita
              SET tipo_movimento = 'QUALSIASI_COSA'
            WHERE id = %s $$,
    (SELECT commessa_attivita_id FROM tmp_ca_normale)
  ),
  '23514',
  NULL,
  '8. CHECK DB difesa finale: UPDATE diretto fuori dominio bloccato'
);

-- ============================================================
-- EMIT: pull commessa -> attivita_fatturabili (entrambe le righe)
-- ============================================================
SELECT * FROM vendite.fn_cambia_stato_commessa(
  (SELECT commessa_id FROM tmp_commessa_tm), 'PRONTA_FATTURAZIONE');

CREATE TEMP TABLE tmp_emit_tm AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  (SELECT commessa_id FROM tmp_commessa_tm)
);

-- ============================================================
-- TEST 9-10) Propagazione 1:1, per riga e non per costante.
--   Le due righe viaggiano nello stesso emit: se la fn scrivesse un valore
--   fisso invece di leggere la CA, il test 10 lo smaschera.
-- ============================================================
SELECT is(
  (SELECT af.tipo_movimento FROM vendite.attivita_fatturabili af
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_normale)),
  'NORMALE'::varchar,
  '9. emit propaga NORMALE su attivita_fatturabili'
);

SELECT is(
  (SELECT af.tipo_movimento FROM vendite.attivita_fatturabili af
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_onere)),
  'ONERE'::varchar,
  '10. emit propaga ONERE su attivita_fatturabili (cintura del contatore: '
  'la riga della porta onere non e'' merce)'
);

SELECT * FROM finish();

ROLLBACK;
