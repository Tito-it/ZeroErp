-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: §26 B+D — il tipo del documento d'origine + tipo_doc_fiscale_id
-- rev 2026-11-07 (brief-db-sorgente-documento-e-riga, lotto C, giro C.1): il tipo
--   del documento d'origine non si copia piu' sull'attivita' fatturabile
--   (sorgente_origine_tipo_id e le altre sorgente_* si ritirano): si legge dalla
--   riga di commessa, per la FK commessa_attivita_id. La regola §26 resta: il
--   tipo documento viene dal documento di business, non da COMMESSA.
-- ------------------------------------------------------------
-- Indice test (1..10):
--  1) attivita_fatturabili non ha piu' sorgente_origine_tipo_id
--  2) FK commessa_attivita_id -> commesse_attivita: la provenienza
--  3) config.sorgenti[PREVENTIVO].tipo_doc_fiscale_id configurato
--  4) fn_list_preventivi_da_pushare restituisce tipo_doc_fiscale_id
--  5) tipo_doc_fiscale_id coerente con config.sorgenti[PREVENTIVO]
--  6) l'attivita' emessa raggiunge il tipo PREVENTIVO dalla sua riga di commessa
--  7) fn_emit propaga tipo_doc_fiscale_id da commesse_attivita
--  8) Trigger normalize: tipo_doc_fiscale_id gia` valorizzato non sovrascritto
--  9) Trigger normalize: risolve dal tipo del documento della riga di commessa
-- 10) nessun ripiego su una colonna dell'attivita': sorgente_tipo_id non c'e'
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
-- 1) sorgente_origine_tipo_id non c'e' piu': il tipo si legge dalla riga di commessa
-- ============================================================
SELECT hasnt_column(
  'vendite', 'attivita_fatturabili', 'sorgente_origine_tipo_id',
  'attivita_fatturabili non ha sorgente_origine_tipo_id: il tipo d''origine sta sulla riga di commessa'
);

-- ============================================================
-- 2) La provenienza dell'attivita': FK commessa_attivita_id -> commesse_attivita
-- ============================================================
SELECT fk_ok(
  'vendite', 'attivita_fatturabili', 'commessa_attivita_id',
  'vendite', 'commesse_attivita', 'id',
  'FK commessa_attivita_id -> vendite.commesse_attivita: la provenienza dell''attivita'''
);

-- ============================================================
-- 3) config.sorgenti[PREVENTIVO].tipo_doc_fiscale_id configurato
-- ============================================================
SELECT ok(
  (
    SELECT s.tipo_doc_fiscale_id IS NOT NULL
    FROM config.sorgenti s
    WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE
    LIMIT 1
  ),
  'config.sorgenti[PREVENTIVO].tipo_doc_fiscale_id configurato'
);

-- ============================================================
-- Setup: riferimenti per test 4-10
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): cliente, preventivo e articolo si
--   COSTRUISCONO. Prima si pescavano il primo BA con un emittente risolvibile
--   e l'ultimo articolo attivo, e il preventivo si scriveva a mano su quel BA:
--   da zero non c'erano, e la commessa moriva su «p_billing_account_id
--   obbligatorio». Ora il preventivo (bozza) lo scrive il builder sul cliente
--   dell'azienda di chi agisce, e la commessa nasce sul SUO billing account
--   (la madre aggancia il documento alla commessa solo sullo stesso BA).
--   L'articolo e' una merce semplice costruita. Sorgenti, UoM e valuta sono
--   catalogo di seed.
CREATE TEMP TABLE tmp_prev_build_sot AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('sorgente origine tipo doc');

CREATE TEMP TABLE tmp_refs_sot AS
SELECT
  -- ⚠️ PREVENTIVO resta: e' l'oggetto delle asserzioni 3/5/6 (tipo_doc_fiscale
  -- configurato sulla sorgente e propagazione di sorgente_origine_tipo_id).
  -- Lookup per codice_interno (immutabile), non per codice — §6c/§6d.
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1)
    AS sorgente_preventivo_id,
  -- Sorgente per il solo link ROOT, che fn_emit pretende esista ma di cui non
  -- dereferenzia il tipo: COMMESSA (key_selector='id') permette di usare come
  -- chiave l'id della commessa stessa, che esiste per costruzione.
  -- rev 2026-07-27 (bonifica): prima il link usava PREVENTIVO con una stringa
  -- inventata, illegale dal guard del 2026-07-18.
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA' AND s.attivo IS TRUE LIMIT 1)
    AS sorgente_root_id,
  (SELECT s.tipo_doc_fiscale_id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1)
    AS expected_tipo_doc_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice = 'COMMESSA' AND s.attivo IS TRUE LIMIT 1)
    AS sorgente_commessa_id,
  (SELECT s.tipo_doc_fiscale_id FROM config.sorgenti s WHERE s.codice = 'COMMESSA' AND s.attivo IS TRUE LIMIT 1)
    AS commessa_tipo_doc_id,
  (SELECT billing_account_id FROM tmp_prev_build_sot)
    AS billing_account_id,
  (SELECT utility_id FROM tmp_prev_build_sot)
    AS utility_id,
  (SELECT istanza_utility_id FROM tmp_prev_build_sot)
    AS istanza_utility_id,
  (SELECT emittente_soggetto_ruolo_id FROM tmp_prev_build_sot)
    AS emittente_soggetto_ruolo_id,
  dbops.fn_pgtap_crea_articolo('PGT-SOT-ART', false)
    AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)
    AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)
    AS valuta_id;

-- ============================================================
-- 4) fn_list_preventivi_da_pushare restituisce tipo_doc_fiscale_id
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'fn_list_preventivi_da_pushare'
      AND c.column_name = 'tipo_doc_fiscale_id'
  )
  OR EXISTS (
    -- Controlla via pg_proc per RETURNS TABLE
    SELECT 1
    FROM pg_catalog.pg_proc p
    JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_preventivi_da_pushare'
      AND p.proargnames::text LIKE '%tipo_doc_fiscale_id%'
  ),
  'fn_list_preventivi_da_pushare restituisce tipo_doc_fiscale_id'
);

-- ============================================================
-- 5) tipo_doc_fiscale_id coerente con config.sorgenti[PREVENTIVO]
-- ============================================================
-- Verifica che il valore restituito dalla fn_list coincida con config.sorgenti.
-- ⚠️ bool_and su TUTTE le righe, non `p_limit := 1` + `LIMIT 1` su una a caso.
--   Il terzo parametro della funzione E' un limite: chiedendone una sola si
--   collaudava un preventivo qualsiasi, scelto dalla funzione e senza ordine.
--   Cosi' l'asserzione diventa «nessuno di quelli elencati e' incoerente»,
--   che e' quello che il nome dichiara. NULL (nessuna riga) resta ammesso.
SELECT ok(
  (
    SELECT bool_and(p.tipo_doc_fiscale_id = r.expected_tipo_doc_id)
    FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, NULL) p,
         tmp_refs_sot r
  )
  IS NOT FALSE,  -- NULL (nessuna riga) o TRUE sono entrambi ok
  'tipo_doc_fiscale_id coerente con config.sorgenti[PREVENTIVO]'
);

-- ============================================================
-- Setup: commessa + attivita per test emit (6-7)
-- ============================================================
CREATE TEMP TABLE tmp_commessa_sot AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_sot),
  p_utility_id => (SELECT utility_id FROM tmp_refs_sot),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_sorgente_origine'),
  p_force_new => true
) AS commessa_id;

-- Link ROOT (serve solo che ESISTA: fn_emit non ne dereferenzia il tipo)
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_sot),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs_sot),
  p_sorgente_chiave => (SELECT commessa_id FROM tmp_commessa_sot)::text,
  p_sorgente_riga => NULL,
  p_meta => '{}'::jsonb
);

-- Preventivo VERO come sorgente della riga (rev 2026-10-13): basta la testata
--   in bozza sullo stesso billing account. Prima la riga portava un token
--   inventato ('EXT-SOT-...'), che commesse_attivita accettava; dal
--   20261012-46 la madre aggancia il documento alla commessa con
--   fn_link_commessa_sorgente, che ne pretende formato (uuid, key_selector
--   'uid') ed esistenza.
-- rev 2026-10-27 (lotto 4 di D7): la testata non si scrive piu' a mano qui:
--   e' quella del builder (in setup), sul cui billing account nasce la commessa.
CREATE TEMP TABLE tmp_prev_sot AS
SELECT preventivo_id AS id, preventivo_uid AS uid FROM tmp_prev_build_sot;

-- Upsert attivita con sorgente_tipo_id = PREVENTIVO (sorgente originale)
CREATE TEMP TABLE tmp_ca_sot AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_sot),
  p_segment_key => ((SELECT script.fn_segment_key(s.codice_interno, d.documento_uid::text) FROM config.sorgenti s, script.fn_sorgente_documento_da_chiave(s.id, ((SELECT uid::text FROM tmp_prev_sot))::text) d WHERE s.id = (SELECT sorgente_preventivo_id FROM tmp_refs_sot)) || ':' || ('SOT-' || substr(md5(clock_timestamp()::text), 1, 18))::varchar)::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_sot),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_sot),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_sot),
  p_quantita => 3.000000,
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
  p_qta_operativa => 3.000000,
  p_uom_operativa_id => (SELECT uom_id FROM tmp_refs_sot),
  p_factor_to_base => 1,
  p_posticipa_al => NULL,
  p_tipo_doc_fiscale_id => (SELECT expected_tipo_doc_id FROM tmp_refs_sot),
  p_valuta_id => (SELECT valuta_id FROM tmp_refs_sot),
  p_area_geografica_id => NULL,
  p_listino_versione_id => NULL,
  p_prezzo_bloccato => true,
  p_pricing_mode => 'FIXED',
  p_prezzo_da_riallineare => false,
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (SELECT sorgente_preventivo_id FROM tmp_refs_sot),
  p_sorgente_chiave => (SELECT uid::text FROM tmp_prev_sot),
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'SORGENTE_ORIGINE_TEST')
) r;

-- Emit
CREATE TEMP TABLE tmp_emit_sot AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_sot),
  p_only_approved => true,
  p_dry_run => false
);

-- ============================================================
-- 6) L'attivita' emessa raggiunge il tipo d'origine dalla sua riga di commessa
-- ============================================================
SELECT ok(
  (
    SELECT ca.sorgente_tipo_id = r.sorgente_preventivo_id
    FROM vendite.attivita_fatturabili af
    JOIN vendite.commesse_attivita ca ON ca.id = af.commessa_attivita_id
    JOIN tmp_refs_sot r ON true
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_sot)
  ),
  'l''attivita'' emessa raggiunge il tipo PREVENTIVO dalla sua riga di commessa'
);

-- ============================================================
-- 7) fn_emit propaga tipo_doc_fiscale_id
-- ============================================================
SELECT ok(
  (
    SELECT af.tipo_doc_fiscale_id = r.expected_tipo_doc_id
    FROM vendite.attivita_fatturabili af
    JOIN tmp_refs_sot r ON true
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_sot)
  ),
  'fn_emit propaga tipo_doc_fiscale_id da commesse_attivita'
);

-- ============================================================
-- 8) Trigger normalize: tipo_doc_fiscale_id gia` valorizzato non sovrascritto
-- ============================================================
-- La riga AF creata sopra ha gia` tipo_doc_fiscale_id; aggiorniamo un campo trigger
-- e verifichiamo che tipo_doc_fiscale_id non viene sovrascritto.
UPDATE vendite.attivita_fatturabili
SET competenza_mese = DATE '2026-07-01'
WHERE commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_sot);

SELECT ok(
  (
    SELECT af.tipo_doc_fiscale_id = r.expected_tipo_doc_id
    FROM vendite.attivita_fatturabili af
    JOIN tmp_refs_sot r ON true
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_sot)
  ),
  'Trigger normalize: tipo_doc_fiscale_id gia` valorizzato non sovrascritto'
);

-- ============================================================
-- 9) Trigger normalize: risolve dal tipo della riga di commessa
-- ============================================================
-- Azzeriamo tipo_doc_fiscale_id e triggeriamo il normalize; deve risolvere
-- dal tipo del documento della riga di commessa (PREVENTIVO), non da COMMESSA.
UPDATE vendite.attivita_fatturabili
SET tipo_doc_fiscale_id = NULL
WHERE commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_sot);

SELECT ok(
  (
    SELECT af.tipo_doc_fiscale_id = r.expected_tipo_doc_id
    FROM vendite.attivita_fatturabili af
    JOIN tmp_refs_sot r ON true
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_sot)
  ),
  'Trigger normalize: risolve tipo_doc_fiscale_id dal tipo del documento della riga di commessa'
);

-- ============================================================
-- 10) Nessun ripiego su una colonna dell'attivita'
-- ============================================================
-- Il ripiego di prima (sorgente_tipo_id = COMMESSA) leggeva una colonna che non
-- c'e' piu'. La riga di commessa senza documento (onere, rettifica) prende
-- COMMESSA dal normalize: lo prova vendite/test-sorgente-attivita-fatturabili-v1 (10).
SELECT hasnt_column(
  'vendite', 'attivita_fatturabili', 'sorgente_tipo_id',
  'nessun ripiego su una colonna dell''attivita'': sorgente_tipo_id non c''e'''
);

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
