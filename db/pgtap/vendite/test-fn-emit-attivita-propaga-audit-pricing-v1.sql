-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: fn_emit_attivita_fatturabili_da_commessa propaga lo snapshot
--       audit pricing v5 (8 colonne) da commesse_attivita ad attivita_fatturabili
-- (changeset 20260616-01)
-- ------------------------------------------------------------
-- Indice test (1..6):
--  1) emit inserisce 1 riga
--  2) prezzo_base_snapshot propagato su attivita_fatturabili
--  3) origine_prezzo propagato
--  4) tipo_variazione_applicata + valore_variazione_applicata propagati
--  5) re-run idempotente: la riga ora EMESSA non e' piu' candidata
--  6) anti-regressione: rename codice sorgente COMMESSA -> risoluzione per codice_interno (no E_CODICE)
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
-- SETUP: riferimenti minimi
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba, BA legato all'azienda di chi agisce):
--   prima il billing account si pescava con LIMIT 1, e su un database
--   ricostruito da zero non c'era.
CREATE TEMP TABLE tmp_cli_au AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('emit propaga audit pricing');

CREATE TEMP TABLE tmp_refs_au AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_au) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_au) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_cli_au) AS istanza_utility_id,
  (
    SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE ORDER BY a.data_insert DESC NULLS LAST LIMIT 1
  ) AS articolo_id,
  (
    SELECT u.id FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1
  ) AS uom_id,
  (
    -- rev 2026-07-27 (bonifica): ROOT su sorgente COMMESSA (key_selector='id'),
    -- e lookup per codice_interno (immutabile) invece che per codice
    -- (etichetta modificabile) — linee-guida-sql §6c/§6d.
    SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'COMMESSA' AND s.attivo LIMIT 1
  ) AS root_sorgente_tipo_id,
  (
    SELECT t.id FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1
  ) AS tipo_doc_fiscale_id;

-- Commessa di test isolata
CREATE TEMP TABLE tmp_commessa_au AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_au),
  p_utility_id => (SELECT utility_id FROM tmp_refs_au),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_emit_audit'),
  p_force_new => true
) AS commessa_id;

-- Sorgente ROOT obbligatoria per l'emit (il primo link diventa ROOT)
CREATE TEMP TABLE tmp_link_au AS
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_au),
  p_sorgente_tipo_id => (SELECT root_sorgente_tipo_id FROM tmp_refs_au),
  -- ROOT: sorgente COMMESSA (key_selector='id') con uid = id della commessa
  -- stessa: esiste per costruzione, quindi passa il guard sorgente polimorfa
  -- (formato id::text + esistenza nel target). fn_emit pretende solo che una
  -- ROOT esista, non ne dereferenzia il tipo. rev 2026-07-27 (bonifica).
  p_sorgente_uid => (SELECT commessa_id FROM tmp_commessa_au)::text,
  p_sorgente_riga => 1,
  p_meta => jsonb_build_object('test_scope', 'pgtap_emit_audit')
) AS link_id;

-- Riga commessa APPROVATA + NON_EMESSA
CREATE TEMP TABLE tmp_ca_au AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_au),
  -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
  p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
  p_sorgente_uid => ((SELECT commessa_id FROM tmp_commessa_au))::text,
  p_segment_key => ('SEG-AU-' || substr(md5(clock_timestamp()::text), 1, 14))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_au),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_au),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_au),
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
  -- tipo_doc valorizzato: il guard tipo_doc emittibile (20260619-05) richiede
  -- tipo_doc_fiscale_id NOT NULL sulle righe APPROVATA+NON_EMESSA.
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_au),
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'AUDIT')
) r;

-- Valorizza lo snapshot audit sulla riga commessa (isola la logica di emit:
-- colonne non-FK, nessun fixture promo/contratto/categoria/classe).
UPDATE vendite.commesse_attivita
   SET prezzo_base_snapshot = 12.5000000000,
       origine_prezzo = 'MANUALE',
       tipo_variazione_applicata = 'NESSUNA',
       valore_variazione_applicata = 3.5000000000
 WHERE id = (SELECT commessa_attivita_id FROM tmp_ca_au);

-- Porta in PRONTA_FATTURAZIONE (emittibile)
-- rev 2026-10-27: il verbo della commessa chiede cambia_stato_commessa
-- all'operatore del test (giro 10); senza, su un db dove l'operatore non ce l'ha,
-- si ferma qui con E_PERMESSO_NEGATO.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'cambia_stato_commessa');
SELECT * FROM vendite.fn_cambia_stato_commessa(
  (SELECT commessa_id FROM tmp_commessa_au), 'PRONTA_FATTURAZIONE');

-- ============================================================
-- EMIT (pull commessa -> attivita_fatturabili)
-- ============================================================
CREATE TEMP TABLE tmp_emit_au AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  (SELECT commessa_id FROM tmp_commessa_au)
);

SELECT is(
  (SELECT inserted_rows FROM tmp_emit_au),
  1,
  'emit inserisce 1 riga'
);

-- Riga AF emessa, individuata via commessa_attivita_id
SELECT is(
  (SELECT a.prezzo_base_snapshot FROM vendite.attivita_fatturabili a
    WHERE a.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_au)),
  12.5000000000::numeric,
  'prezzo_base_snapshot propagato su attivita_fatturabili'
);

SELECT is(
  (SELECT a.origine_prezzo FROM vendite.attivita_fatturabili a
    WHERE a.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_au)),
  'MANUALE',
  'origine_prezzo propagato'
);

SELECT ok(
  (
    SELECT a.tipo_variazione_applicata = 'NESSUNA'
       AND a.valore_variazione_applicata = 3.5000000000
    FROM vendite.attivita_fatturabili a
    WHERE a.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_au)
  ),
  'tipo_variazione_applicata + valore_variazione_applicata propagati'
);

-- ============================================================
-- Re-run idempotente: la riga e' ora EMESSA, non piu' candidata
-- ============================================================
CREATE TEMP TABLE tmp_emit_au2 AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  (SELECT commessa_id FROM tmp_commessa_au)
);

SELECT is(
  (SELECT total_candidate FROM tmp_emit_au2),
  0,
  're-run idempotente: la riga ora EMESSA non e'' piu'' candidata'
);

-- ============================================================
-- TEST 6) Anti-regressione codice_interno (analisi-hardcoded-codice §3a):
--   rinominando il `codice` (mutabile) della sorgente COMMESSA, l'emit DEVE
--   continuare a risolverla per `codice_interno` (immutabile): nessun E_CODICE.
--   dry_run = true: raggiunge il lookup sorgente senza mutare dati.
-- ============================================================
UPDATE config.sorgenti
   SET codice = codice || '_RENAMED'
 WHERE codice_interno = 'COMMESSA';

SELECT lives_ok(
  $$ SELECT 1 FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
        (SELECT commessa_id FROM tmp_commessa_au), true, true) $$,
  '6. anti-regressione: rename codice sorgente COMMESSA -> emit risolve per codice_interno (no E_CODICE)'
);

SELECT * FROM finish();

ROLLBACK;
