-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: filtro fatturazione_immediata in vendite.fn_list_commesse_emittibili
-- (changeset 20260615-11)
-- ------------------------------------------------------------
-- Indice test (1..6):
--  1) filtro true  -> include la commessa immediata
--  2) filtro true  -> esclude la commessa differita
--  3) filtro false -> include la commessa differita
--  4) filtro false -> esclude la commessa immediata
--  5) senza filtro (NULL) -> include entrambe (retro-compat)
--  6) output: colonna fatturazione_immediata coerente per ogni commessa
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
-- SETUP: riferimenti minimi (billing account con emittente fiscale)
-- ============================================================
CREATE TEMP TABLE tmp_refs_fi AS
SELECT
  (
    SELECT ba.id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS billing_account_id,
  (
    SELECT ba.utility_id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS utility_id,
  (
    SELECT ba.istanza_utility_id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS istanza_utility_id,
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
  -- rev 2026-08-18 (bonifica baseline): mancava il tipo documento fiscale.
  -- Entrambe le righe qui nascono APPROVATA + NON_EMESSA, cioe' emittibili, e
  -- da trg_commesse_attivita_a10_guard_tipo_doc_emittibile quello stato senza
  -- tipo_doc non e' piu' ammesso: una riga cosi' e' invisibile a
  -- fn_list_emittibili_lane e nessun processo la ripesca. La fixture moriva
  -- prima della prima asserzione (0 su 6 eseguite).
  (
    SELECT t.id
    FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE
    ORDER BY t.id
    LIMIT 1
  ) AS tipo_doc_fiscale_id;

-- ============================================================
-- SETUP: due commesse stesso perimetro/competenza, una immediata e una differita.
--   fatturazione_immediata e' parte della chiave di dedup di
--   fn_get_or_create_commessa, quindi sono comunque due commesse distinte.
-- ============================================================
CREATE TEMP TABLE tmp_commessa_imm AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_fi),
  p_utility_id => (SELECT utility_id FROM tmp_refs_fi),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => true,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_fi_immediata'),
  p_force_new => true
) AS commessa_id;

CREATE TEMP TABLE tmp_commessa_dif AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_fi),
  p_utility_id => (SELECT utility_id FROM tmp_refs_fi),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_fi_differita'),
  p_force_new => true
) AS commessa_id;

-- ============================================================
-- SETUP: una riga APPROVATA + NON_EMESSA per ciascuna commessa
--   (necessaria sia per l'emittibilita' sia per il guard di transizione
--    BOZZA -> PRONTA_FATTURAZIONE).
-- ============================================================
CREATE TEMP TABLE tmp_up_imm AS
SELECT r.attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_imm),
  -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
  p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
  p_sorgente_uid => ((SELECT commessa_id FROM tmp_commessa_imm))::text,
  p_segment_key => ('SEG-FI-IMM-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_fi),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_fi),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_fi),
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
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_fi),
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'FI_IMM')
) r;

CREATE TEMP TABLE tmp_up_dif AS
SELECT r.attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_dif),
  -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
  p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
  p_sorgente_uid => ((SELECT commessa_id FROM tmp_commessa_dif))::text,
  p_segment_key => ('SEG-FI-DIF-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_fi),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_fi),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_fi),
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
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_fi),
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'FI_DIF')
) r;

-- Porta entrambe in PRONTA_FATTURAZIONE (stato emittibile)
-- rev 2026-10-27: il verbo della commessa chiede cambia_stato_commessa
-- all'operatore del test (giro 10); senza, su un db dove l'operatore non ce l'ha,
-- si ferma qui con E_PERMESSO_NEGATO.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'cambia_stato_commessa');
SELECT * FROM vendite.fn_cambia_stato_commessa(
  (SELECT commessa_id FROM tmp_commessa_imm), 'PRONTA_FATTURAZIONE');
SELECT * FROM vendite.fn_cambia_stato_commessa(
  (SELECT commessa_id FROM tmp_commessa_dif), 'PRONTA_FATTURAZIONE');

-- ============================================================
-- TEST 1-2: filtro true -> solo immediata
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_commesse_emittibili(p_fatturazione_immediata => true) x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_imm)
  ),
  'filtro true -> include la commessa immediata'
);

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_commesse_emittibili(p_fatturazione_immediata => true) x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_dif)
  ),
  'filtro true -> esclude la commessa differita'
);

-- ============================================================
-- TEST 3-4: filtro false -> solo differita
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_commesse_emittibili(p_fatturazione_immediata => false) x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_dif)
  ),
  'filtro false -> include la commessa differita'
);

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_commesse_emittibili(p_fatturazione_immediata => false) x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_imm)
  ),
  'filtro false -> esclude la commessa immediata'
);

-- ============================================================
-- TEST 5: senza filtro (NULL) -> entrambe (retro-compat)
-- ============================================================
SELECT is(
  (
    SELECT count(*)::int
    FROM vendite.fn_list_commesse_emittibili() x
    WHERE x.commessa_id IN (
      (SELECT commessa_id FROM tmp_commessa_imm),
      (SELECT commessa_id FROM tmp_commessa_dif)
    )
  ),
  2,
  'senza filtro (NULL) -> include entrambe (retro-compat)'
);

-- ============================================================
-- TEST 6: colonna output fatturazione_immediata coerente
-- ============================================================
SELECT ok(
  (
    SELECT x.fatturazione_immediata
    FROM vendite.fn_list_commesse_emittibili() x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_imm)
  ) IS TRUE
  AND (
    SELECT x.fatturazione_immediata
    FROM vendite.fn_list_commesse_emittibili() x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_dif)
  ) IS FALSE,
  'output: colonna fatturazione_immediata coerente per ogni commessa'
);

SELECT * FROM finish();

ROLLBACK;
