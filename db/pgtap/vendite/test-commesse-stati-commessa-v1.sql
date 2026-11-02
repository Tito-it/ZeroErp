-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: stati_commessa lookup + refactor FK + fn_list_commesse_emittibili
-- (changeset 20260226-01..06)
-- rev 2026-10-26 (brief-modello-documento-vendita §14, giro 10): IN_ESECUZIONE e' ritirato
--   (attivo = false, C-3): gli stati attivi sono cinque.
-- ⚠️ Attesa cambiata: test 4 (6 -> 5 stati attivi, e IN_ESECUZIONE fra i non attivi), perche' il
--   giro 10 ritira IN_ESECUZIONE dal vocabolario della commessa.
-- rev 2026-10-26 (giro 10, C-1, dopo la corsa di Tid su dbdev): prima di «rendi pronta» e «chiudi»
--   l'azione cambia_stato_commessa all'utente del contesto; il file prova l'emittibilita', non il
--   permesso. Sullo scratch il file e' tronco prima di quel punto (debito preesistente).
-- ------------------------------------------------------------
-- Indice test (1..18):
--  1) Tabella vendite.stati_commessa presente
--  2) FK commesse.stato_commessa_id presente
--  3) Vecchia colonna commesse.stato_commessa rimossa
--  4) 5 stati_commessa presenti e attivi (IN_ESECUZIONE ritirato, giro 10)
--  5) Flag chiude_commessa corretto (CHIUSA/ANNULLATA=true, altri=false)
--  6) Flag emittibile corretto (solo PRONTA_FATTURAZIONE=true)
--  7) Flag modificabile corretto (CHIUSA/ANNULLATA=false, altri=true)
--  8) Trigger lock codice_interno presente
--  9) Trigger child_requires_active_parent presente
-- 10) Trigger prevent_deactivate presente
-- 11) fn_list_commesse_emittibili presente
-- 12) fn_get_commessa_stato restituisce stato_commessa_id e flag
-- 13) Commessa creata in stato BOZZA (stato_commessa_id=1)
-- 14) fn_get_or_create_commessa riusa commessa aperta (chiude=false)
-- 15) fn_upsert_commessa_attivita funziona su commessa modificabile
-- 16) fn_upsert_commessa_attivita bloccata su commessa non modificabile
-- 17) fn_list_commesse_emittibili esclude commesse non emittibili
-- 18) fn_list_commesse_emittibili include commesse emittibili (senza filtro mese)
-- 19) fn_list_commesse_emittibili filtra per competenza_mese corretto
-- 20) fn_list_commesse_emittibili esclude mese non corrispondente
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

SELECT plan(20);

-- ============================================================
-- STRUTTURA DDL
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'vendite' AND table_name = 'stati_commessa'
  ),
  'Tabella vendite.stati_commessa presente'
);

SELECT ok(
  EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'vendite'
      AND table_name = 'commesse'
      AND column_name = 'stato_commessa_id'
  ),
  'FK commesse.stato_commessa_id presente'
);

SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'vendite'
      AND table_name = 'commesse'
      AND column_name = 'stato_commessa'
  ),
  'Vecchia colonna commesse.stato_commessa rimossa'
);

-- ============================================================
-- SEED DATA
-- ============================================================

SELECT is(
  (SELECT string_agg(codice_interno::text, ',' ORDER BY codice_interno)
     FROM vendite.stati_commessa WHERE attivo = true)
  || ' | ritirato: ' ||
  (SELECT string_agg(codice_interno::text, ',' ORDER BY codice_interno)
     FROM vendite.stati_commessa WHERE attivo = false),
  'ANNULLATA,APERTA,BOZZA,CHIUSA,PRONTA_FATTURAZIONE | ritirato: IN_ESECUZIONE',
  '5 stati_commessa presenti e attivi, IN_ESECUZIONE ritirato (giro 10)'
);

SELECT ok(
  (
    SELECT count(*) = 2
    FROM vendite.stati_commessa
    WHERE chiude_commessa = true
      AND codice_interno IN ('CHIUSA', 'ANNULLATA')
  )
  AND NOT EXISTS (
    SELECT 1
    FROM vendite.stati_commessa
    WHERE chiude_commessa = true
      AND codice_interno NOT IN ('CHIUSA', 'ANNULLATA')
  ),
  'Flag chiude_commessa corretto (CHIUSA/ANNULLATA=true, altri=false)'
);

SELECT ok(
  (
    SELECT count(*) = 1
    FROM vendite.stati_commessa
    WHERE emittibile = true
      AND codice_interno = 'PRONTA_FATTURAZIONE'
  )
  AND NOT EXISTS (
    SELECT 1
    FROM vendite.stati_commessa
    WHERE emittibile = true
      AND codice_interno <> 'PRONTA_FATTURAZIONE'
  ),
  'Flag emittibile corretto (solo PRONTA_FATTURAZIONE=true)'
);

SELECT ok(
  (
    SELECT count(*) = 2
    FROM vendite.stati_commessa
    WHERE modificabile = false
      AND codice_interno IN ('CHIUSA', 'ANNULLATA')
  )
  AND NOT EXISTS (
    SELECT 1
    FROM vendite.stati_commessa
    WHERE modificabile = false
      AND codice_interno NOT IN ('CHIUSA', 'ANNULLATA')
  ),
  'Flag modificabile corretto (CHIUSA/ANNULLATA=false, altri=true)'
);

-- ============================================================
-- TRIGGER
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger
    WHERE tgrelid = 'vendite.stati_commessa'::regclass
      AND tgname LIKE '%lock_columns%'
  ),
  'Trigger lock codice_interno presente'
);

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger
    WHERE tgrelid = 'vendite.commesse'::regclass
      AND tgname LIKE '%stati_commessa_require_attivo%'
  ),
  'Trigger child_requires_active_parent presente'
);

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger
    WHERE tgrelid = 'vendite.stati_commessa'::regclass
      AND tgname LIKE '%commesse_block_deact%'
  ),
  'Trigger prevent_deactivate presente'
);

-- ============================================================
-- FUNZIONI
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_commesse_emittibili'
  ),
  'fn_list_commesse_emittibili presente'
);

-- ============================================================
-- SETUP DATI TEST
-- ============================================================

-- Recupera riferimenti minimi per test funzionali
-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba, BA legato all'azienda di chi agisce):
--   prima il billing account si pescava con LIMIT 1, e su un database
--   ricostruito da zero non c'era.
CREATE TEMP TABLE tmp_cli_sc AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('stati commessa');

CREATE TEMP TABLE tmp_refs_sc AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_sc) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_sc) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_cli_sc) AS istanza_utility_id,
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
    WHERE s.codice = 'PREVENTIVO'
    LIMIT 1
  ) AS root_sorgente_tipo_id;

-- Crea commessa di test (force_new per isolamento)
CREATE TEMP TABLE tmp_commessa_sc AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_sc),
  p_utility_id => (SELECT utility_id FROM tmp_refs_sc),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_stati_commessa'),
  p_force_new => true
) AS commessa_id;

-- ============================================================
-- TEST fn_get_commessa_stato con nuovi campi
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_get_commessa_stato((SELECT commessa_id FROM tmp_commessa_sc)) x
    WHERE x.stato_commessa_id = 1
      AND x.stato_commessa = 'BOZZA'
      AND x.chiude_commessa = false
      AND x.emittibile = false
      AND x.modificabile = true
  ),
  'fn_get_commessa_stato restituisce stato_commessa_id e flag'
);

-- ============================================================
-- TEST: commessa creata in BOZZA (default stato_commessa_id=1)
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.commesse c
    WHERE c.id = (SELECT commessa_id FROM tmp_commessa_sc)
      AND c.stato_commessa_id = 1
  ),
  'Commessa creata in stato BOZZA (stato_commessa_id=1)'
);

-- ============================================================
-- TEST: fn_get_or_create_commessa riusa commessa chiude=false
-- ============================================================

CREATE TEMP TABLE tmp_commessa_sc_reuse AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_sc),
  p_utility_id => (SELECT utility_id FROM tmp_refs_sc),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_stati_commessa_reuse'),
  p_force_new => false
) AS commessa_id;

SELECT is(
  (SELECT commessa_id::text FROM tmp_commessa_sc_reuse),
  (SELECT commessa_id::text FROM tmp_commessa_sc),
  'fn_get_or_create_commessa riusa commessa aperta (chiude=false)'
);

-- ============================================================
-- TEST: upsert funziona su commessa modificabile (BOZZA)
-- ============================================================

CREATE TEMP TABLE tmp_upsert_sc AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_sc),
  -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
  p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
  p_sorgente_uid => ((SELECT commessa_id FROM tmp_commessa_sc))::text,
  p_segment_key => ('SEG-SC-' || substr(md5(clock_timestamp()::text), 1, 16))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_sc),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_sc),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_sc),
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
  -- Aggiunto 2026-07-24: la riga nasce APPROVATA+NON_EMESSA = emittibile e il
  -- guard trg_commesse_attivita_a10_guard_tipo_doc_emittibile
  -- (brief-db-guard-tipo-doc-attivita, posteriore a questo test) esige il
  -- tipo_doc. Il riferimento era gia' nel fixture, mancava solo passarlo.
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_sc),
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'SC_UPSERT')
) r;

SELECT ok(
  (SELECT commessa_attivita_id IS NOT NULL FROM tmp_upsert_sc),
  'fn_upsert_commessa_attivita funziona su commessa modificabile'
);

-- ============================================================
-- TEST: porta in PRONTA_FATTURAZIONE e verifica emittibili
--   BOZZA -> PRONTA_FATTURAZIONE: transizione valida (salto push), ammessa
--   dal guard 20260607-02 perche' esiste una riga APPROVATA+NON_EMESSA
--   (creata dal test upsert sopra). Usa la fn entrypoint sanzionata.
-- ============================================================

-- rev 2026-10-26 (giro 10, C-1): «rendi pronta» e «chiudi» chiedono l'azione
--   cambia_stato_commessa; il file prova l'emittibilita', non il permesso.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'cambia_stato_commessa');

SELECT * FROM vendite.fn_cambia_stato_commessa(
  (SELECT commessa_id FROM tmp_commessa_sc),
  'PRONTA_FATTURAZIONE'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_commesse_emittibili() x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_sc)
      AND x.total_non_emesse >= 1
  ),
  'fn_list_commesse_emittibili include commesse emittibili (senza filtro mese)'
);

-- L'attivita` ha competenza_mese = 2026-07-01, filtro con mese corrispondente
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_commesse_emittibili(
      p_competenza_mese => DATE '2026-07-01'
    ) x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_sc)
  ),
  'fn_list_commesse_emittibili filtra per competenza_mese corretto'
);

-- Mese diverso: nessuna attivita` con competenza_mese = 2026-01-01
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_commesse_emittibili(
      p_competenza_mese => DATE '2026-01-01'
    ) x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_sc)
  ),
  'fn_list_commesse_emittibili esclude mese non corrispondente'
);

-- ============================================================
-- TEST: porta in CHIUSA e verifica esclusione + upsert bloccata
--   PRONTA_FATTURAZIONE -> CHIUSA: transizione valida. CHIUSA ha
--   emittibile=false e modificabile=false.
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
   WHERE commessa_id = (SELECT commessa_id FROM tmp_commessa_sc)
     AND stato_approvazione = 'APPROVATA'
     AND stato_emissione    = 'NON_EMESSA';
END
$emissione$;

SELECT * FROM vendite.fn_cambia_stato_commessa(
  (SELECT commessa_id FROM tmp_commessa_sc),
  'CHIUSA'
);

-- CHIUSA non e` emittibile
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_commesse_emittibili() x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_sc)
  ),
  'fn_list_commesse_emittibili esclude commesse non emittibili'
);

SELECT throws_ok(
  $$
    SELECT vendite.fn_upsert_commessa_attivita(
      p_commessa_id => (SELECT commessa_id FROM tmp_commessa_sc),
      -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
      p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
      p_sorgente_uid => ((SELECT commessa_id FROM tmp_commessa_sc))::text,
      p_segment_key => 'SEG-SC-BLOCKED',
      p_articolo_id => (SELECT articolo_id FROM tmp_refs_sc),
      p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_sc),
      p_data_attivita => DATE '2026-07-15',
      p_uom_id => (SELECT uom_id FROM tmp_refs_sc),
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
      p_classe_utenza_id_snapshot => NULL
    );
  $$,
  'P0001',
  NULL,
  'fn_upsert_commessa_attivita bloccata su commessa non modificabile'
);

SELECT * FROM finish();
ROLLBACK;
