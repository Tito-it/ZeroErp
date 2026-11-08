-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: guardrail anti-bypass commessa su vendite.attivita_fatturabili
-- ------------------------------------------------------------
-- Indice test (1..13):
-- 1) funzione trgfn_attivita_fatturabili_guard_commessa presente
-- 2) trigger guard_commessa presente su attivita_fatturabili
-- 3) il parametro attivita_fatturabili_require_commessa e' ritirato: il guard controlla sempre
-- 4) riferimenti minimi disponibili
-- 5) commessa A creata
-- 6) commessa_attivita A creata
-- 7) emit da commessa A inserisce attivita_fatturabile
-- 8) update con coppia coerente consentito
-- 9) blocca link commessa null: col_not_null su commessa_id (e' l'ancora RLS:
--    per UPDATE uscirebbe 42501 dal WITH CHECK prima del NOT NULL)
-- 10) blocca coppia incompleta: commessa_attivita_id NULL -> 23502 (l'ancora
--     c'e', la policy passa e il NOT NULL si raggiunge)
-- 11) blocca mismatch tra commessa_id e commessa_attivita_id (il guard, P0001)
-- 12) coppia coerente accettata
-- 13) emit da commessa resta operativo (no regressione pipeline)
-- Dal 2026-11-08 (20261110-17, -18) il parametro che accendeva il guard e' ritirato:
-- il guard controlla sempre la coerenza, i NULL li rifiuta il vincolo.
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

SELECT plan(13);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'trgfn_attivita_fatturabili_guard_commessa'
  ),
  'funzione trgfn_attivita_fatturabili_guard_commessa presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite'
      AND c.relname = 'attivita_fatturabili'
      AND t.tgname = 'trg_attivita_fatturabili_a10_guard_commessa_ins_upd'
      AND NOT t.tgisinternal
  ),
  'trigger guard_commessa presente su attivita_fatturabili'
);

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM config.parameters p
    WHERE p.code = 'attivita_fatturabili_require_commessa'
  ),
  'il parametro attivita_fatturabili_require_commessa e'' ritirato: il guard controlla sempre'
);

-- rev 2026-10-27 (lotto 4 di D7): il cliente e l'articolo si COSTRUISCONO
--   (dbops.fn_pgtap_crea_cliente_ba, BA gia' legato all'azienda di chi
--   agisce; dbops.fn_pgtap_crea_articolo, con la sua unita' di misura).
--   Prima si pescavano con LIMIT 1, e su un database ricostruito da zero
--   non c'erano. Le chiamate alla madre, sotto, restano.
CREATE TEMP TABLE tmp_guard_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('guardrail commessa');

CREATE TEMP TABLE tmp_guard_art AS
SELECT dbops.fn_pgtap_crea_articolo(
  ('PGT-GRD-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar,
  false) AS articolo_id;

CREATE TEMP TABLE tmp_guard_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_guard_cli) AS billing_account_id,
  (SELECT utility_id FROM tmp_guard_cli) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_guard_cli) AS istanza_utility_id,
  (SELECT anagrafiche.fn_get_emittente_fiscale_id(billing_account_id)
     FROM tmp_guard_cli) AS emittente_soggetto_ruolo_id,
  (SELECT articolo_id FROM tmp_guard_art) AS articolo_id,
  (SELECT a.uom_id FROM catalogo.articoli a
    WHERE a.id = (SELECT articolo_id FROM tmp_guard_art)) AS uom_id,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id,
  (SELECT id FROM config.sorgenti WHERE codice_interno = 'COMMESSA' LIMIT 1) AS src_preventivo_id;

SELECT ok(
  (
    SELECT billing_account_id IS NOT NULL
      AND utility_id IS NOT NULL
      AND istanza_utility_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND uom_id IS NOT NULL
      AND tipo_doc_fiscale_id IS NOT NULL
      AND valuta_id IS NOT NULL
      AND src_preventivo_id IS NOT NULL
    FROM tmp_guard_refs
  ),
  'riferimenti minimi disponibili'
);

-- rev 2026-07-27 (bonifica): RIMOSSO l'upsert su config.sorgenti che questo
-- test faceva qui. Riscriveva la riga di seed della sorgente COMMESSA
-- imponendo target_table='vendite.commesse_attivita' — il valore ERRATO che il
-- brief-db-guard-sorgente-polimorfa (reperto R2) ha corretto nel seed a
-- 'vendite.commesse', perche' tutti i consumatori del collegamento usano l'id
-- della COMMESSA. Con il guard attivo dal 2026-07-18, quell'upsert faceva
-- validare l'esistenza contro la tabella sbagliata e il link falliva.
-- La sorgente COMMESSA esiste gia' nel seed, correttamente configurata: al
-- test basta leggerla (tmp_guard_refs.src_preventivo_id, sopra).
-- ⚠️ Un test non deve riscrivere righe di seed condivise: ne altera il
-- comportamento per tutto il resto della transazione.

CREATE TEMP TABLE tmp_commessa_a AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_guard_refs),
  p_utility_id => (SELECT utility_id FROM tmp_guard_refs),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_guardrail_commessa_a'),
  p_force_new => true
) AS commessa_id;

SELECT ok(
  (SELECT commessa_id IS NOT NULL FROM tmp_commessa_a),
  'commessa A creata'
);

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_a),
  p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_guard_refs),
  -- ROOT: sorgente COMMESSA (key_selector='id') con uid = id della commessa
  -- stessa: esiste per costruzione -> passa formato ed esistenza del guard
  -- sorgente polimorfa. rev 2026-07-27 (bonifica).
  p_sorgente_chiave => (SELECT commessa_id FROM tmp_commessa_a)::text,
  p_sorgente_riga => NULL,
  p_meta => '{}'::jsonb
);

CREATE TEMP TABLE tmp_commessa_att_a AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_a),
  p_segment_key => ((SELECT x.segment_key FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_commessa_a)) x) || ':' || ('SEG-A-' || substr(md5(clock_timestamp()::text), 1, 18))::varchar)::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_guard_refs),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_guard_refs),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_guard_refs),
  p_quantita => 1.000000,
  p_competenza_mese => DATE '2026-07-01',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_prezzo_snapshot => 22.1000000000,
  p_prezzo_base_snapshot => NULL,
  p_origine_prezzo => NULL,
  p_tipo_variazione_applicata => NULL,
  p_valore_variazione_applicata => NULL,
  p_promo_id => NULL,
  p_contratto_id => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot => NULL,
  p_qta_operativa => 1.000000,
  p_uom_operativa_id => (SELECT uom_id FROM tmp_guard_refs),
  p_factor_to_base => 1,
  p_posticipa_al => NULL,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_guard_refs),
  p_valuta_id => (SELECT valuta_id FROM tmp_guard_refs),
  p_area_geografica_id => NULL,
  p_listino_versione_id => NULL,
  p_prezzo_bloccato => true,
  p_pricing_mode => 'FIXED',
  p_prezzo_da_riallineare => false,
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (SELECT x.sorgente_tipo_id FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_commessa_a)) x),
  p_sorgente_chiave => (SELECT x.consumo_id::text FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_commessa_a)) x),
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'GUARD_A')
) r;

SELECT ok(
  (SELECT commessa_attivita_id IS NOT NULL FROM tmp_commessa_att_a),
  'commessa_attivita A creata'
);

CREATE TEMP TABLE tmp_emit_a AS
SELECT *
FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_a),
  p_only_approved => true,
  p_dry_run => false
);

CREATE TEMP TABLE tmp_af_a AS
SELECT a.id
FROM vendite.attivita_fatturabili a
WHERE a.commessa_id = (SELECT commessa_id FROM tmp_commessa_a)
ORDER BY a.id DESC
LIMIT 1;

SELECT ok(
  (SELECT count(*) = 1 FROM tmp_af_a),
  'emit da commessa A inserisce attivita_fatturabile'
);

UPDATE vendite.attivita_fatturabili
SET commessa_id = (SELECT commessa_id FROM tmp_commessa_a),
    commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_commessa_att_a)
WHERE id = (SELECT id FROM tmp_af_a);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili a
    WHERE a.id = (SELECT id FROM tmp_af_a)
      AND a.commessa_id = (SELECT commessa_id FROM tmp_commessa_a)
      AND a.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_commessa_att_a)
  ),
  'update con coppia coerente consentito'
);

-- ⛔ Asserzione STRUTTURALE, non per UPDATE: commessa_id e' la colonna-ancora
--   della policy RLS (perimetro emittente risalendo alla commessa). Sotto il
--   runner applicativo PostgreSQL valuta il WITH CHECK prima del NOT NULL:
--   con commessa_id = NULL la riga esce 42501, e il vincolo non si raggiunge
--   mai (come owner, invece, darebbe 23502: verde in sessione, rosso col
--   runner). Il 42501 non si pinna: sarebbe il sintomo, non il vincolo.
SELECT col_not_null(
  'vendite', 'attivita_fatturabili', 'commessa_id',
  'blocca link commessa null: commessa_id e'' NOT NULL (struttura: e'' l''ancora RLS)'
);

SELECT throws_ok(
  $$
    UPDATE vendite.attivita_fatturabili
    SET commessa_id = (SELECT commessa_id FROM tmp_commessa_a),
        commessa_attivita_id = NULL
    WHERE id = (SELECT id FROM tmp_af_a);
  $$,
  '23502',
  NULL,
  'blocca coppia incompleta: lo rifiuta il NOT NULL'
);

CREATE TEMP TABLE tmp_commessa_b AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_guard_refs),
  p_utility_id => (SELECT utility_id FROM tmp_guard_refs),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-08-01',
  p_competenza_al => DATE '2026-08-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_guardrail_commessa_b'),
  p_force_new => true
) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_b),
  p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_guard_refs),
  -- ROOT: sorgente COMMESSA (key_selector='id') con uid = id della commessa
  -- stessa: esiste per costruzione -> passa formato ed esistenza del guard
  -- sorgente polimorfa. rev 2026-07-27 (bonifica).
  p_sorgente_chiave => (SELECT commessa_id FROM tmp_commessa_b)::text,
  p_sorgente_riga => NULL,
  p_meta => '{}'::jsonb
);

CREATE TEMP TABLE tmp_commessa_att_b AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_b),
  p_segment_key => ((SELECT x.segment_key FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_commessa_b)) x) || ':' || ('SEG-B-' || substr(md5(clock_timestamp()::text), 1, 18))::varchar)::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_guard_refs),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_guard_refs),
  p_data_attivita => DATE '2026-08-10',
  p_uom_id => (SELECT uom_id FROM tmp_guard_refs),
  p_quantita => 1.000000,
  p_competenza_mese => DATE '2026-08-01',
  p_competenza_dal => DATE '2026-08-01',
  p_competenza_al => DATE '2026-08-31',
  p_prezzo_snapshot => 22.1000000000,
  p_prezzo_base_snapshot => NULL,
  p_origine_prezzo => NULL,
  p_tipo_variazione_applicata => NULL,
  p_valore_variazione_applicata => NULL,
  p_promo_id => NULL,
  p_contratto_id => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot => NULL,
  p_qta_operativa => 1.000000,
  p_uom_operativa_id => (SELECT uom_id FROM tmp_guard_refs),
  p_factor_to_base => 1,
  p_posticipa_al => NULL,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_guard_refs),
  p_valuta_id => (SELECT valuta_id FROM tmp_guard_refs),
  p_area_geografica_id => NULL,
  p_listino_versione_id => NULL,
  p_prezzo_bloccato => true,
  p_pricing_mode => 'FIXED',
  p_prezzo_da_riallineare => false,
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (SELECT x.sorgente_tipo_id FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_commessa_b)) x),
  p_sorgente_chiave => (SELECT x.consumo_id::text FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_commessa_b)) x),
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'GUARD_B')
) r;

SELECT throws_ok(
  $$
    UPDATE vendite.attivita_fatturabili
    SET commessa_id = (SELECT commessa_id FROM tmp_commessa_a),
        commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_commessa_att_b)
    WHERE id = (SELECT id FROM tmp_af_a);
  $$,
  'P0001',
  NULL,
  'blocca mismatch tra commessa_id e commessa_attivita_id'
);

UPDATE vendite.attivita_fatturabili
SET commessa_id = (SELECT commessa_id FROM tmp_commessa_a),
    commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_commessa_att_a)
WHERE id = (SELECT id FROM tmp_af_a);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili a
    WHERE a.id = (SELECT id FROM tmp_af_a)
      AND a.commessa_id = (SELECT commessa_id FROM tmp_commessa_a)
      AND a.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_commessa_att_a)
  ),
  'pair coerente accettata'
);

CREATE TEMP TABLE tmp_emit_b AS
SELECT *
FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_b),
  p_only_approved => true,
  p_dry_run => false
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili a
    WHERE a.commessa_id = (SELECT commessa_id FROM tmp_commessa_b)
      AND a.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_commessa_att_b)
  ),
  'emit da commessa resta operativo (no regressione pipeline)'
);

SELECT * FROM finish();
ROLLBACK;
