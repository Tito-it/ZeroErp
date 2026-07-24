-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: colonna 'fatturata' in vendite.fn_list_commessa_attivita.
-- Brief: brief-db-flag-fatturata-lista-attivita.md (2026-07-24).
--
-- PERCHE' ESISTE: il drawer di gestione commessa offre le azioni prezzo per
-- riga; il BE le rifiuta su riga fatturata (_assert_non_fatturata legge
-- af.fattura_riga_id), ma il FE non puo' nasconderle prima del click finche' la
-- lista non espone il dato. 'fatturata' e' lo SPECCHIO ESATTO del guard BE:
-- EXISTS di un'attivita_fatturabili della riga con fattura_riga_id valorizzato.
--
-- CRITERIO: fattura_riga_id IS NOT NULL, NON la colonna denormalizzata
-- attivita_fatturabili.fatturato. La relazione CA<->AF e' 1:1
-- (uq_attivita_fatturabili_commessa_attivita).
--
-- Il caso 3 e' il DISCRIMINANTE del brief: riga con AF ma fattura_riga_id NULL
-- (lotto resettato) -> EMESSA ma prezzo ancora modificabile. E' dove
-- stato_emissione sbaglierebbe e fattura_riga_id no.
--
-- Nota fixture: le righe si creano via fn_upsert_commessa_attivita (sourceless);
-- le AF via INSERT diretto (no fn_emit, che esige una ROOT source reale).
-- fattura_riga_id non ha FK -> un id fittizio non-NULL basta per il criterio.
-- Le righe APPROVATA+NON_EMESSA esigono tipo_doc (guard tipo_doc_emittibile):
-- si passa sempre tipo_doc all'upsert.
-- ------------------------------------------------------------
-- Indice test (1..4):
--   1  fn_list_commessa_attivita dichiara la colonna fatturata boolean
--   2  fatturata = false su riga senza attivita_fatturabili
--   3  fatturata = false su riga con AF ma fattura_riga_id NULL (reset-lotto)
--   4  fatturata = true  su riga con AF e fattura_riga_id valorizzato
-- ------------------------------------------------------------

BEGIN;
SELECT plan(4);

-- ============================================================
-- 1 — STRUTTURA
-- ============================================================
SELECT ok(
  pg_get_function_result(
    'vendite.fn_list_commessa_attivita(bigint,character varying,character varying,date,integer,integer)'::regprocedure
  ) LIKE '%fatturata boolean%',
  '1) fn_list_commessa_attivita dichiara la colonna fatturata boolean');

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE tmp_refs_lcf AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS billing_account_id,
  (SELECT ba.utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS utility_id,
  (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1) AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE
    ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE
    ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id;

-- Commessa isolata (force_new), nasce in BOZZA.
CREATE TEMP TABLE tmp_commessa_lcf AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_refs_lcf),
  p_utility_id             => (SELECT utility_id FROM tmp_refs_lcf),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2026-10-01',
  p_competenza_al          => DATE '2026-10-31',
  p_meta                   => jsonb_build_object('test_scope', 'pgtap_lista_fatturata'),
  p_force_new              => true
) AS commessa_id;

-- Scopo: aggiunge una riga alla commessa negli stati richiesti; ritorna l'id.
CREATE OR REPLACE FUNCTION pg_temp.fx_riga_lcf(
  p_seg  vendite.commesse_attivita.segment_key%TYPE,
  p_appr vendite.commesse_attivita.stato_approvazione%TYPE,
  p_emis vendite.commesse_attivita.stato_emissione%TYPE)
RETURNS vendite.commesse_attivita.id%TYPE LANGUAGE sql AS $fx$
  SELECT r.attivita_id
    FROM vendite.fn_upsert_commessa_attivita(
      p_commessa_id                   => (SELECT commessa_id FROM tmp_commessa_lcf),
      p_segment_key                   => p_seg,
      p_articolo_id                   => (SELECT articolo_id FROM tmp_refs_lcf),
      p_istanza_utility_id            => (SELECT istanza_utility_id FROM tmp_refs_lcf),
      p_data_attivita                 => DATE '2026-10-15',
      p_uom_id                        => (SELECT uom_id FROM tmp_refs_lcf),
      p_quantita                      => 1.000000,
      p_competenza_mese               => DATE '2026-10-01',
      p_competenza_dal                => DATE '2026-10-01',
      p_competenza_al                 => DATE '2026-10-31',
      p_prezzo_snapshot               => 10.0000000000,
      p_prezzo_base_snapshot          => NULL,
      p_origine_prezzo                => NULL,
      p_tipo_variazione_applicata     => NULL,
      p_valore_variazione_applicata   => NULL,
      p_promo_id                      => NULL,
      p_contratto_id                  => NULL,
      p_categoria_cliente_id_snapshot => NULL,
      p_classe_utenza_id_snapshot     => NULL,
      p_tipo_doc_fiscale_id           => (SELECT tipo_doc_fiscale_id FROM tmp_refs_lcf),
      p_stato_approvazione            => p_appr,
      p_stato_emissione               => p_emis,
      p_tipo_movimento                => 'NORMALE',
      p_tipo_consumo                  => 'CONGUAGLIO',
      p_meta                          => jsonb_build_object('case', 'LCF')
    ) r;
$fx$;

-- Tre righe: senza AF / AF non fatturata / AF fatturata.
CREATE TEMP TABLE tmp_att_lcf AS
SELECT
  pg_temp.fx_riga_lcf('SEG-LCF-1', 'APPROVATA', 'NON_EMESSA') AS id_senza_af,
  pg_temp.fx_riga_lcf('SEG-LCF-2', 'APPROVATA', 'EMESSA')     AS id_af_non_fatt,
  pg_temp.fx_riga_lcf('SEG-LCF-3', 'APPROVATA', 'EMESSA')     AS id_af_fatt;

-- AF per la riga 2: esiste ma fattura_riga_id NULL (caso reset-lotto).
INSERT INTO vendite.attivita_fatturabili (
  articolo_id, istanza_utility_id, data_attivita, quantita,
  competenza_mese, competenza_dal, competenza_al,
  uom_id, prezzo_unitario, tipo_doc_fiscale_id,
  commessa_id, commessa_attivita_id, fattura_riga_id, fatturato)
SELECT r.articolo_id, r.istanza_utility_id, DATE '2026-10-15', 1,
       DATE '2026-10-01', DATE '2026-10-01', DATE '2026-10-31',
       r.uom_id, 10.000000, r.tipo_doc_fiscale_id,
       (SELECT commessa_id FROM tmp_commessa_lcf),
       (SELECT id_af_non_fatt FROM tmp_att_lcf), NULL, false
FROM tmp_refs_lcf r;

-- AF per la riga 3: fattura_riga_id valorizzato (id fittizio, nessuna FK).
INSERT INTO vendite.attivita_fatturabili (
  articolo_id, istanza_utility_id, data_attivita, quantita,
  competenza_mese, competenza_dal, competenza_al,
  uom_id, prezzo_unitario, tipo_doc_fiscale_id,
  commessa_id, commessa_attivita_id, fattura_riga_id, fatturato)
SELECT r.articolo_id, r.istanza_utility_id, DATE '2026-10-15', 1,
       DATE '2026-10-01', DATE '2026-10-01', DATE '2026-10-31',
       r.uom_id, 10.000000, r.tipo_doc_fiscale_id,
       (SELECT commessa_id FROM tmp_commessa_lcf),
       (SELECT id_af_fatt FROM tmp_att_lcf), 999999, true
FROM tmp_refs_lcf r;

-- ============================================================
-- 2..4 — VALORI
-- ============================================================
SELECT is(
  (SELECT l.fatturata
     FROM vendite.fn_list_commessa_attivita((SELECT commessa_id FROM tmp_commessa_lcf)) l
    WHERE l.id = (SELECT id_senza_af FROM tmp_att_lcf)),
  false,
  '2) fatturata = false su riga senza attivita_fatturabili');

SELECT is(
  (SELECT l.fatturata
     FROM vendite.fn_list_commessa_attivita((SELECT commessa_id FROM tmp_commessa_lcf)) l
    WHERE l.id = (SELECT id_af_non_fatt FROM tmp_att_lcf)),
  false,
  '3) fatturata = false su riga con AF ma fattura_riga_id NULL (reset-lotto)');

SELECT is(
  (SELECT l.fatturata
     FROM vendite.fn_list_commessa_attivita((SELECT commessa_id FROM tmp_commessa_lcf)) l
    WHERE l.id = (SELECT id_af_fatt FROM tmp_att_lcf)),
  true,
  '4) fatturata = true su riga con AF e fattura_riga_id valorizzato');

SELECT * FROM finish();
ROLLBACK;
