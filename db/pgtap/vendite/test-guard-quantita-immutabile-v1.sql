-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: immutabilità quantita su commesse_attivita (EMESSA) e mirror-enforcement
--       su attivita_fatturabili (= quantita della commessa madre).
-- Brief: brief-db-immutabilita-quantita-e-porta-oneri §4a step 1 (2026-07-21).
--
-- Nota fixture: NON si usa fn_emit (richiede una ROOT source documentale reale,
-- guard esistenza sorgente-polimorfa 2026-07-18, senza bypass). La CA nasce
-- con la commessa come sorgente (una NORMALE senza sorgente e' rifiutata dal
-- vincolo 20261012-27) e l'AF si crea con INSERT
-- diretto coerente alla CA. I guard testati scattano su UPDATE OF quantita,
-- quindi INSERT e flip di stato non li attivano.
-- ------------------------------------------------------------
-- Indice test (1..16):
--   1..4  struttura (funzioni + trigger CA/AF)
--   5     riferimenti minimi disponibili
--   6     commessa creata
--   7     commessa_attivita creata (NON_EMESSA, quantita 1.0)
--   8     CA NON_EMESSA: UPDATE quantita consentito (re-push naturale)
--   9     CA portata a EMESSA (fixture)
--  10     CA EMESSA: UPDATE quantita BLOCCATO
--  11     AF creata (INSERT diretto, quantita = commessa)
--  12     AF mirror: UPDATE quantita = commessa consentito
--  13     AF mirror: UPDATE quantita != commessa BLOCCATO
--  14     bypass GUC: CA EMESSA UPDATE quantita consentito
--  15     bypass GUC: AF UPDATE quantita != commessa consentito
--  16     i due codici errore esistono nel catalogo
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

SELECT plan(16);

-- ===== 1..4 struttura =====
SELECT has_function('vendite', 'trgfn_commesse_attivita_guard_quantita_immutabile',
    '1) funzione guard quantita CA presente');
SELECT has_trigger('vendite', 'commesse_attivita',
    'trg_commesse_attivita_a10_guard_quantita_immutabile_upd',
    '2) trigger guard quantita CA presente');
SELECT has_function('vendite', 'trgfn_attivita_fatturabili_guard_quantita_immutabile',
    '3) funzione guard quantita AF presente');
SELECT has_trigger('vendite', 'attivita_fatturabili',
    'trg_attivita_fatturabili_a10_guard_quantita_immutabile_upd',
    '4) trigger guard quantita AF presente');

-- ===== fixture: riferimenti =====
-- rev 2026-10-27 (lotto 4 di D7): il cliente e l'articolo si COSTRUISCONO.
--   Prima si pescavano il primo BA con emittente e l'ultimo articolo attivo, e
--   su un database ricostruito da zero non c'erano: ora il BA viene da
--   dbops.fn_pgtap_crea_cliente_ba (legato all'azienda di chi agisce, emittente
--   derivato dal BA) e l'articolo da dbops.fn_pgtap_crea_articolo (servizio,
--   non gestito a magazzino). Restano letture di catalogo di SEED:
--   unita_misura, tipi_doc_fiscale, valute, sorgenti.
CREATE TEMP TABLE tmp_cli_gq AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('guard quantita immutabile');

CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_gq) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_gq) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_cli_gq) AS istanza_utility_id,
  (SELECT anagrafiche.fn_get_emittente_fiscale_id(billing_account_id) FROM tmp_cli_gq) AS emittente_soggetto_ruolo_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-GQ-ART', false) AS articolo_id,
  (SELECT id FROM catalogo.unita_misura WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS uom_id,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND utility_id IS NOT NULL
      AND istanza_utility_id IS NOT NULL AND emittente_soggetto_ruolo_id IS NOT NULL
      AND articolo_id IS NOT NULL AND uom_id IS NOT NULL
      AND tipo_doc_fiscale_id IS NOT NULL AND valuta_id IS NOT NULL
   FROM tmp_refs),
  '5) riferimenti minimi disponibili');

-- Commessa
CREATE TEMP TABLE tmp_commessa AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_guard_quantita'),
  p_force_new => true
) AS commessa_id;

SELECT ok((SELECT commessa_id IS NOT NULL FROM tmp_commessa), '6) commessa creata');

-- commessa_attivita: NON_EMESSA, APPROVATA, quantita 1.0, sorgente COMMESSA
-- (la commessa di test: il guard di esistenza della sorgente la trova).
CREATE TEMP TABLE tmp_ca AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa),
  p_segment_key => ('SEG-Q-' || substr(md5(clock_timestamp()::text), 1, 18))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs),
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
  p_qta_operativa => 1.000000,
  p_uom_operativa_id => (SELECT uom_id FROM tmp_refs),
  p_factor_to_base => 1,
  p_posticipa_al => NULL,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs),
  p_valuta_id => (SELECT valuta_id FROM tmp_refs),
  p_area_geografica_id => NULL,
  p_listino_versione_id => NULL,
  p_prezzo_bloccato => true,
  p_pricing_mode => 'FIXED',
  p_prezzo_da_riallineare => false,
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
  p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
  p_sorgente_uid => ((SELECT commessa_id FROM tmp_commessa))::text,
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'GUARD_Q')
) r;

SELECT ok((SELECT commessa_attivita_id IS NOT NULL FROM tmp_ca), '7) commessa_attivita creata');

-- 8) CA NON_EMESSA: UPDATE quantita consentito (la riga non e' ancora un fatto)
SELECT lives_ok(
  $$ UPDATE vendite.commesse_attivita
        SET quantita = 1.500000
      WHERE id = (SELECT commessa_attivita_id FROM tmp_ca) $$,
  '8) CA NON_EMESSA: UPDATE quantita consentito');

-- fixture: porta la CA a EMESSA (UPDATE di stato, non tocca quantita)
UPDATE vendite.commesse_attivita
   SET stato_emissione = 'EMESSA'
 WHERE id = (SELECT commessa_attivita_id FROM tmp_ca);

SELECT is(
  (SELECT stato_emissione FROM vendite.commesse_attivita
    WHERE id = (SELECT commessa_attivita_id FROM tmp_ca)),
  'EMESSA', '9) CA portata a EMESSA (fixture)');

-- 10) CA EMESSA: UPDATE quantita BLOCCATO
SELECT throws_ok(
  $$ UPDATE vendite.commesse_attivita
        SET quantita = 3.000000
      WHERE id = (SELECT commessa_attivita_id FROM tmp_ca) $$,
  'P0001', NULL,
  '10) CA EMESSA: UPDATE quantita bloccato');

-- AF: INSERT diretto coerente alla CA (quantita = commessa = 1.5), senza sorgente.
INSERT INTO vendite.attivita_fatturabili (
  articolo_id, billing_account_id, istanza_utility_id, data_attivita, quantita,
  competenza_mese, competenza_dal, competenza_al, uom_id, qta_operativa,
  uom_operativa_id, factor_to_base, valuta_id, prezzo_unitario, tipo_doc_fiscale_id,
  prezzo_bloccato, approvato, commessa_id, commessa_attivita_id, tipo_movimento
)
SELECT
  r.articolo_id, r.billing_account_id, r.istanza_utility_id, DATE '2026-07-15',
  (SELECT quantita FROM vendite.commesse_attivita WHERE id = (SELECT commessa_attivita_id FROM tmp_ca)),
  DATE '2026-07-01', DATE '2026-07-01', DATE '2026-07-31', r.uom_id, 1.500000,
  r.uom_id, 1, r.valuta_id, 10.0, r.tipo_doc_fiscale_id,
  true, true, (SELECT commessa_id FROM tmp_commessa), (SELECT commessa_attivita_id FROM tmp_ca),
  'NORMALE'
FROM tmp_refs r;

CREATE TEMP TABLE tmp_af AS
SELECT a.id
FROM vendite.attivita_fatturabili a
WHERE a.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca)
ORDER BY a.id DESC LIMIT 1;

SELECT ok((SELECT count(*) = 1 FROM tmp_af), '11) AF creata (INSERT diretto)');

-- 12) AF mirror: UPDATE quantita = commessa (1.5) consentito
SELECT lives_ok(
  $$ UPDATE vendite.attivita_fatturabili
        SET quantita = 1.500000
      WHERE id = (SELECT id FROM tmp_af) $$,
  '12) AF mirror: UPDATE quantita = commessa consentito');

-- 13) AF mirror: UPDATE quantita != commessa BLOCCATO
SELECT throws_ok(
  $$ UPDATE vendite.attivita_fatturabili
        SET quantita = 5.000000
      WHERE id = (SELECT id FROM tmp_af) $$,
  'P0001', NULL,
  '13) AF mirror: UPDATE quantita != commessa bloccato');

-- ===== bypass GUC (armato per il resto della transazione) =====
SELECT set_config('zeroerp.maintenance_reset_lotto_draft', 'on', true);

SELECT lives_ok(
  $$ UPDATE vendite.commesse_attivita
        SET quantita = 3.000000
      WHERE id = (SELECT commessa_attivita_id FROM tmp_ca) $$,
  '14) bypass GUC: CA EMESSA UPDATE quantita consentito');

SELECT lives_ok(
  $$ UPDATE vendite.attivita_fatturabili
        SET quantita = 99.000000
      WHERE id = (SELECT id FROM tmp_af) $$,
  '15) bypass GUC: AF UPDATE quantita != commessa consentito');

SELECT set_config('zeroerp.maintenance_reset_lotto_draft', 'off', true);

-- 16) sanity: i due codici errore esistono nel catalogo
SELECT is(
  (SELECT count(*)::int FROM config.messaggi_errore
    WHERE codice IN ('E_COMMESSA_ATTIVITA_QUANTITA_IMMUTABILE',
                     'E_ATTIVITA_FATTURABILE_QUANTITA_IMMUTABILE')
      AND lingua = 'it'),
  2,
  '16) codici errore immutabilita quantita presenti nel catalogo');

SELECT * FROM finish();
ROLLBACK;
