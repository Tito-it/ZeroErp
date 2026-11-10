-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: fn_batch_upsert_commessa_attivita + fn_upsert is_new
-- (changeset 20260227-12, 20260227-13)
-- ------------------------------------------------------------
-- Indice test (1..8):
-- 1) fn_batch_upsert_commessa_attivita presente
-- 2) fn_upsert singolo: is_new = true su insert
-- 3) fn_upsert singolo: is_new = false su update (stesso segment_key)
-- 4) Batch array vuoto -> 0/0/0
-- 5) Batch 1 riga nuova -> inserted=1, updated=0
-- 6) Batch riga duplicata (stessa segment_key 2 volte) -> inserted=1, updated=1
-- 7) Batch errore validazione (quantita=0) -> errore raccolto, altre ok
-- 8) Contatori aggregati corretti su batch misto
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

SELECT plan(8);

-- ============================================================
-- TEST 1: Funzione batch presente
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_batch_upsert_commessa_attivita'
  ),
  'fn_batch_upsert_commessa_attivita presente'
);

-- ============================================================
-- SETUP: riferimenti minimi (riusa pattern test-commesse-core)
-- ============================================================

-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba, BA legato all'azienda di chi agisce):
--   prima il billing account si pescava con LIMIT 1, e su un database
--   ricostruito da zero non c'era.
CREATE TEMP TABLE tmp_cli_batch AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('batch upsert commessa attivita');

CREATE TEMP TABLE tmp_batch_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_batch) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_batch) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_cli_batch) AS istanza_utility_id,
  script.fn_pgtap_emittente_sr_operatore() AS emittente_soggetto_ruolo_id,
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
  (
    SELECT t.id
    FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE
    ORDER BY t.id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (
    SELECT v.id
    FROM config.valute v
    ORDER BY v.id
    LIMIT 1
  ) AS valuta_id,
  (
    SELECT s.id
    FROM config.sorgenti s
    WHERE s.codice_interno = 'COMMESSA'
    LIMIT 1
  ) AS root_sorgente_tipo_id;

-- ⚠️ 2026-11-10 (brief-db-revisione-catalogo, giro 2-bis, D26/Q30): un'attivita'
--   senza fattore prende quello alla data, e un'unita' che per l'articolo non si
--   converte si rifiuta (E_UOM_MISSING). «Un'unita' qualunque» accanto a «un
--   articolo qualunque» passava col fattore 1 per difetto: l'unita' e' la base
--   dell'articolo scelto.
UPDATE tmp_batch_refs SET uom_id = (SELECT a.uom_id FROM catalogo.articoli a WHERE a.id = tmp_batch_refs.articolo_id);

-- Crea commessa di test
CREATE TEMP TABLE tmp_batch_commessa AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_batch_refs),
  p_utility_id => (SELECT utility_id FROM tmp_batch_refs),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-06-01',
  p_competenza_al => DATE '2026-06-30',
  p_meta => jsonb_build_object('test_scope', 'pgtap_batch_upsert'),
  p_force_new => true
) AS commessa_id;

-- Link ROOT sorgente (obbligatorio)
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_batch_commessa),
  p_sorgente_tipo_id => (SELECT root_sorgente_tipo_id FROM tmp_batch_refs),
  -- ROOT: sorgente COMMESSA (key_selector='id') con uid = id della commessa
  -- stessa: esiste per costruzione -> passa formato ed esistenza del guard
  -- sorgente polimorfa. rev 2026-07-27 (bonifica).
  p_sorgente_chiave => (SELECT commessa_id FROM tmp_batch_commessa)::text,
  p_sorgente_riga => NULL,
  p_meta => jsonb_build_object('test_scope', 'pgtap_batch_upsert')
);

-- Segment key univoci per test
CREATE TEMP TABLE tmp_batch_keys AS
SELECT
  'BATCH-A-' || substr(md5(clock_timestamp()::text), 1, 10) AS seg_a,
  'BATCH-B-' || substr(md5(clock_timestamp()::text || 'b'), 1, 10) AS seg_b,
  'BATCH-C-' || substr(md5(clock_timestamp()::text || 'c'), 1, 10) AS seg_c;

-- ============================================================
-- TEST 2: fn_upsert singolo: is_new = true su insert
-- ============================================================

CREATE TEMP TABLE tmp_upsert_new AS
SELECT r.attivita_id, r.is_new
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_batch_commessa),
  p_segment_key => ((SELECT x.segment_key FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_batch_commessa)) x) || ':' || (SELECT seg_a FROM tmp_batch_keys))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_batch_refs),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_batch_refs),
  p_data_attivita => DATE '2026-06-15',
  p_uom_id => (SELECT uom_id FROM tmp_batch_refs),
  p_quantita => 1.000000,
  p_competenza_mese => DATE '2026-06-01',
  p_competenza_dal => DATE '2026-06-01',
  p_competenza_al => DATE '2026-06-30',
  p_prezzo_snapshot => 10.0000000000,
  p_prezzo_base_snapshot => NULL,
  p_origine_prezzo => NULL,
  p_tipo_variazione_applicata => NULL,
  p_valore_variazione_applicata => NULL,
  p_promo_id => NULL,
  p_contratto_id => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot => NULL,
  p_sorgente_tipo_id => (SELECT x.sorgente_tipo_id FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_batch_commessa)) x),
  p_sorgente_chiave => (SELECT x.consumo_id::text FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_batch_commessa)) x)
) r;

SELECT ok(
  (SELECT is_new FROM tmp_upsert_new),
  'fn_upsert singolo: is_new = true su insert'
);

-- ============================================================
-- TEST 3: fn_upsert singolo: is_new = false su update
-- ============================================================

CREATE TEMP TABLE tmp_upsert_upd AS
SELECT r.attivita_id, r.is_new
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_batch_commessa),
  p_segment_key => ((SELECT x.segment_key FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_batch_commessa)) x) || ':' || (SELECT seg_a FROM tmp_batch_keys))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_batch_refs),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_batch_refs),
  p_data_attivita => DATE '2026-06-15',
  p_uom_id => (SELECT uom_id FROM tmp_batch_refs),
  p_quantita => 2.000000,
  p_competenza_mese => DATE '2026-06-01',
  p_competenza_dal => DATE '2026-06-01',
  p_competenza_al => DATE '2026-06-30',
  p_prezzo_snapshot => 20.0000000000,
  p_prezzo_base_snapshot => NULL,
  p_origine_prezzo => NULL,
  p_tipo_variazione_applicata => NULL,
  p_valore_variazione_applicata => NULL,
  p_promo_id => NULL,
  p_contratto_id => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot => NULL,
  p_sorgente_tipo_id => (SELECT x.sorgente_tipo_id FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_batch_commessa)) x),
  p_sorgente_chiave => (SELECT x.consumo_id::text FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_batch_commessa)) x)
) r;

SELECT ok(
  NOT (SELECT is_new FROM tmp_upsert_upd),
  'fn_upsert singolo: is_new = false su update'
);

-- ============================================================
-- TEST 4: Batch array vuoto -> 0/0/0
-- ============================================================

SELECT is(
  (SELECT inserted FROM vendite.fn_batch_upsert_commessa_attivita('[]'::jsonb)),
  0,
  'Batch array vuoto: inserted = 0'
);

-- ============================================================
-- Funzione helper per costruire riga JSONB
-- ============================================================

CREATE FUNCTION pg_temp.mk_row(
  p_seg text,
  p_qta numeric DEFAULT 1.0,
  p_prezzo numeric DEFAULT 10.0,
  p_sorgente_uid text DEFAULT NULL
) RETURNS jsonb AS $$
  SELECT jsonb_build_object(
    'commessa_id', (SELECT commessa_id FROM tmp_batch_commessa),
    -- La chiave del push del consumo della commessa (la provenienza), col
    -- suffisso del test: la chiave di una riga con provenienza nomina il suo documento.
    'segment_key', (SELECT x.segment_key FROM dbops.fn_pgtap_consumo_della_commessa(
                       (SELECT commessa_id FROM tmp_batch_commessa)) x) || ':' || p_seg,
    'articolo_id', (SELECT articolo_id FROM tmp_batch_refs)::text,
    'istanza_utility_id', (SELECT istanza_utility_id FROM tmp_batch_refs),
    'data_attivita', '2026-06-15',
    'uom_id', (SELECT uom_id FROM tmp_batch_refs),
    'quantita', p_qta,
    'competenza_mese', '2026-06-01',
    'competenza_dal', '2026-06-01',
    'competenza_al', '2026-06-30',
    'prezzo_snapshot', p_prezzo,
    'sorgente_tipo_id', (SELECT x.sorgente_tipo_id FROM dbops.fn_pgtap_consumo_della_commessa(
                            (SELECT commessa_id FROM tmp_batch_commessa)) x),
    'sorgente_chiave', COALESCE(p_sorgente_uid,
                             (SELECT x.consumo_id::text FROM dbops.fn_pgtap_consumo_della_commessa(
                                (SELECT commessa_id FROM tmp_batch_commessa)) x))
  );
$$ LANGUAGE sql;

-- ============================================================
-- TEST 5: Batch 1 riga nuova -> inserted=1, updated=0
-- ============================================================

CREATE TEMP TABLE tmp_batch_5 AS
SELECT * FROM vendite.fn_batch_upsert_commessa_attivita(
  jsonb_build_array(pg_temp.mk_row((SELECT seg_b FROM tmp_batch_keys)))
);

SELECT ok(
  (SELECT inserted = 1 AND updated = 0 FROM tmp_batch_5),
  'Batch 1 riga nuova: inserted=1, updated=0'
);

-- ============================================================
-- TEST 6: Batch riga duplicata (stessa seg_key 2 volte)
--         -> inserted=1 (prima), updated=1 (seconda)
-- ============================================================

CREATE TEMP TABLE tmp_batch_6 AS
SELECT * FROM vendite.fn_batch_upsert_commessa_attivita(
  jsonb_build_array(
    pg_temp.mk_row((SELECT seg_c FROM tmp_batch_keys), 1.0, 10.0),
    pg_temp.mk_row((SELECT seg_c FROM tmp_batch_keys), 2.0, 20.0)
  )
);

SELECT ok(
  (SELECT inserted = 1 AND updated = 1 FROM tmp_batch_6),
  'Batch riga duplicata: inserted=1, updated=1'
);

-- ============================================================
-- TEST 7: Batch errore validazione (quantita=0) -> raccolto
-- ============================================================

CREATE TEMP TABLE tmp_batch_7 AS
SELECT * FROM vendite.fn_batch_upsert_commessa_attivita(
  jsonb_build_array(
    pg_temp.mk_row('BATCH-ERR-' || substr(md5(clock_timestamp()::text || 'e'), 1, 8), 0, 10.0),
    pg_temp.mk_row('BATCH-OK-' || substr(md5(clock_timestamp()::text || 'f'), 1, 8), 1.0, 10.0)
  )
);

SELECT ok(
  (SELECT total_rows = 2
     AND inserted = 1
     AND jsonb_array_length(errors) = 1
   FROM tmp_batch_7),
  'Batch errore validazione: raccolto in errors, riga ok processata'
);

-- ============================================================
-- TEST 8: Contatori aggregati batch misto (3 righe)
-- ============================================================

-- Pre-calcola segment_key per garantire che riga 1 e 3 condividano la stessa chiave
CREATE TEMP TABLE tmp_batch_8_keys AS
SELECT
  'BATCH-MIX-' || substr(md5(clock_timestamp()::text || 'g'), 1, 8) AS seg_dup,
  'BATCH-MIX-' || substr(md5(clock_timestamp()::text || 'h'), 1, 8) AS seg_new;

CREATE TEMP TABLE tmp_batch_8 AS
SELECT * FROM vendite.fn_batch_upsert_commessa_attivita(
  jsonb_build_array(
    pg_temp.mk_row((SELECT seg_dup FROM tmp_batch_8_keys), 1.0, 10.0),
    pg_temp.mk_row((SELECT seg_new FROM tmp_batch_8_keys), 1.0, 10.0),
    pg_temp.mk_row((SELECT seg_dup FROM tmp_batch_8_keys), 3.0, 30.0)
  )
);

SELECT ok(
  (SELECT total_rows = 3
     AND inserted = 2
     AND updated = 1
     AND jsonb_array_length(errors) = 0
   FROM tmp_batch_8),
  'Batch misto 3 righe: contatori corretti (2 inserted, 1 updated)'
);

SELECT * FROM finish();
ROLLBACK;
