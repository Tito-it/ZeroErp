-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.fn_available_actions_commessa (capability ciclo di vita commessa)
-- (changeset 20260616-03 + seed transizioni manuali 20260607-05 arricchito)
-- ------------------------------------------------------------
-- Indice test (1..6):
--  1) BOZZA: azione 'annulla' disponibile
--  2) BOZZA: azioni manuali = {annulla, rendi_pronta} (automatica ->APERTA esclusa)
--  3) BOZZA: can_edit_righe = true (stato modificabile)
--  4) PRONTA: azioni = {chiudi, riapri, annulla}
--  5) PRONTA: is_emittibile = true
--  6) CHIUSA (terminale): available_actions=[], can_change_state=false, can_edit_righe=false
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

SELECT plan(6);

-- ============================================================
-- SETUP
-- ============================================================
-- Il cliente si COSTRUISCE (rev 2026-10-27, lotto 4 di D7): prima il BA si
--   pescava con LIMIT 1, e su un database ricostruito da zero non c'era.
CREATE TEMP TABLE tmp_cli_aa AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('available actions commessa');

CREATE TEMP TABLE tmp_refs_aa AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_aa) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_aa) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_cli_aa) AS istanza_utility_id,
  (
    SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE ORDER BY a.data_insert DESC NULLS LAST LIMIT 1
  ) AS articolo_id,
  (
    SELECT u.id FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1
  ) AS uom_id,
  -- Aggiunto 2026-07-24: la riga nasce APPROVATA+NON_EMESSA = emittibile, e il
  -- guard trg_commesse_attivita_a10_guard_tipo_doc_emittibile
  -- (brief-db-guard-tipo-doc-attivita, posteriore a questo test) esige
  -- tipo_doc_fiscale_id valorizzato. Senza, il fixture abortisce la transazione
  -- e il file intero resta rosso.
  (
    SELECT t.id FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1
  ) AS tipo_doc_fiscale_id;

CREATE TEMP TABLE tmp_commessa_aa AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_aa),
  p_utility_id => (SELECT utility_id FROM tmp_refs_aa),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_aa_commessa'),
  p_force_new => true
) AS commessa_id;

-- rev 2026-10-27: l'operatore del test riceve cambia_stato_commessa (giro 10).
-- Serve due volte: il verbo lo chiede (senza, E_PERMESSO_NEGATO), e dal 20261026-35
-- fn_available_actions_commessa NASCONDE il passaggio a chi non ha l'azione, quindi
-- senza permesso il test 2 vedrebbe {annulla} e non {annulla, rendi_pronta}.
-- Qui, prima dei test di BOZZA: le capability si misurano su chi PUO' agire.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'cambia_stato_commessa');

-- ============================================================
-- STATO BOZZA (1)
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM jsonb_array_elements(
      script.fn_available_actions_commessa((SELECT commessa_id FROM tmp_commessa_aa)) -> 'available_actions'
    ) e WHERE e->>'key' = 'annulla'
  ),
  'BOZZA: azione annulla disponibile'
);

-- Adeguamento 2026-08-04 (brief-db-emittibilita-visibile-e-sbloccabile §3.3,
-- changeSet 20260804-27): da BOZZA le azioni manuali sono DUE. La transizione
-- ->PRONTA_FATTURAZIONE era dichiarata automatica e ora e' `rendi_pronta`,
-- un bottone che nasce spento quando la commessa non e' pronta e porta con se'
-- il motivo. Resta automatica la sola ->APERTA.
--
-- ⚠️ Si asserisce l'INSIEME delle chiavi, non piu' il conteggio: `= 2` sarebbe
-- passato anche con due azioni sbagliate, ed e' esattamente il modo in cui un
-- test smette di misurare quello per cui era stato scritto.
SELECT is(
  (
    SELECT array_agg(e->>'key' ORDER BY e->>'key') FROM jsonb_array_elements(
      script.fn_available_actions_commessa((SELECT commessa_id FROM tmp_commessa_aa)) -> 'available_actions'
    ) e
  ),
  ARRAY['annulla', 'rendi_pronta'],
  'BOZZA: azioni manuali = {annulla, rendi_pronta} (automatica ->APERTA esclusa)'
);

SELECT is(
  (script.fn_available_actions_commessa((SELECT commessa_id FROM tmp_commessa_aa)) ->> 'can_edit_righe')::boolean,
  true,
  'BOZZA: can_edit_righe = true'
);

-- ============================================================
-- Porta in PRONTA_FATTURAZIONE: serve >=1 riga APPROVATA + NON_EMESSA
-- ============================================================
CREATE TEMP TABLE tmp_ca_aa AS
SELECT r.attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_aa),
  -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
  p_sorgente_tipo_id => (SELECT x.sorgente_tipo_id FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_commessa_aa)) x),
  p_sorgente_uid => (SELECT x.consumo_id::text FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_commessa_aa)) x),
  p_segment_key => ((SELECT x.segment_key FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_commessa_aa)) x) || ':' || ('SEG-AA-' || substr(md5(clock_timestamp()::text), 1, 14))::varchar)::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_aa),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_aa),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_aa),
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
  -- Obbligatorio sulla riga emittibile (vedi nota su tmp_refs).
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_aa),
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'AA')
) r;

SELECT * FROM vendite.fn_cambia_stato_commessa(
  (SELECT commessa_id FROM tmp_commessa_aa), 'PRONTA_FATTURAZIONE');

-- ============================================================
-- STATO PRONTA_FATTURAZIONE (4)
-- ============================================================
SELECT is(
  (
    SELECT count(*)::int FROM jsonb_array_elements(
      script.fn_available_actions_commessa((SELECT commessa_id FROM tmp_commessa_aa)) -> 'available_actions'
    ) e WHERE e->>'key' IN ('chiudi', 'riapri', 'annulla')
  ),
  3,
  'PRONTA: azioni = {chiudi, riapri, annulla}'
);

SELECT is(
  (script.fn_available_actions_commessa((SELECT commessa_id FROM tmp_commessa_aa)) ->> 'is_emittibile')::boolean,
  true,
  'PRONTA: is_emittibile = true'
);

-- ============================================================
-- Porta in CHIUSA (terminale) e verifica
-- ============================================================
-- Adeguamento 2026-07-24 (brief-db-guard-uscita-commessa-e-capabilities, D2):
-- la chiusura esige che non restino righe APPROVATE+NON_EMESSE, altrimenti le
-- si perderebbe per sempre (CHIUSA e' terminale). Il percorso realistico e'
-- che la riga venga prima EMESSA: qui la si emette per poter osservare lo
-- stato CHIUSA, che e' l'oggetto del test.
DO $emissione$
BEGIN
  UPDATE vendite.commesse_attivita
     SET stato_emissione = 'EMESSA'
   WHERE commessa_id = (SELECT commessa_id FROM tmp_commessa_aa)
     AND stato_approvazione = 'APPROVATA'
     AND stato_emissione    = 'NON_EMESSA';
END
$emissione$;

SELECT * FROM vendite.fn_cambia_stato_commessa(
  (SELECT commessa_id FROM tmp_commessa_aa), 'CHIUSA');

SELECT ok(
  (
    SELECT jsonb_array_length(r -> 'available_actions') = 0
       AND (r ->> 'can_change_state')::boolean = false
       AND (r ->> 'can_edit_righe')::boolean = false
    FROM (SELECT script.fn_available_actions_commessa((SELECT commessa_id FROM tmp_commessa_aa)) AS r) s
  ),
  'CHIUSA: available_actions=[], can_change_state=false, can_edit_righe=false'
);

SELECT * FROM finish();

ROLLBACK;
