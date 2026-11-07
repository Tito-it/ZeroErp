-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: funzioni core commesse (changeset 20260224-10..14)
-- ------------------------------------------------------------
-- Indice test (1..21):
-- 1) fn_get_or_create_commessa presente
-- 2) fn_link_commessa_sorgente presente
-- 3) fn_upsert_commessa_attivita presente
-- 4) fn_emit_attivita_fatturabili_da_commessa presente
-- 5) fn_get_commessa_stato presente
-- 6) fn_link_commessa_sorgente valida input (commessa_id=0 -> errore)
-- 7) Riferimenti minimi disponibili
-- 8) Seed sorgente COMMESSA presente/attivo
-- 9) Commessa creata
-- 10) Link ROOT inserito
-- 11) Link ROOT idempotente (stesso id)
-- 12) Seconda sorgente diversa sulla stessa commessa -> COLLEGATO (multi-sorgente)
-- 13) Upsert commessa_attivita insert
-- 14) Upsert commessa_attivita update stesso segment_key
-- 15) Override documento su commessa_attivita (listino_versione_id + prezzo_bloccato)
-- 16) Emit dry-run con only_approved=true conta 1 candidato insert
-- 17) Emit reale inserisce 1 riga AF
-- 18) Rerun emit (stato_emissione riaperto) aggiorna riga AF esistente
-- 19) Rerun emit propaga aggiornamento prezzo_snapshot/prezzo_bloccato su AF
-- 20) Propagazione snapshot su AF (commessa/prezzo_bloccato/sorgente)
-- 21) fn_get_commessa_stato restituisce contatori coerenti
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

SELECT plan(21);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_get_or_create_commessa'
  ),
  'fn_get_or_create_commessa presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_link_commessa_sorgente'
  ),
  'fn_link_commessa_sorgente presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_upsert_commessa_attivita'
  ),
  'fn_upsert_commessa_attivita presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_emit_attivita_fatturabili_da_commessa'
  ),
  'fn_emit_attivita_fatturabili_da_commessa presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_get_commessa_stato'
  ),
  'fn_get_commessa_stato presente'
);

SELECT throws_ok(
  $$ SELECT vendite.fn_link_commessa_sorgente(0, 1, 'X', NULL, '{}'::jsonb); $$,
  'P0001',
  NULL,
  'fn_link_commessa_sorgente valida input (commessa_id=0 -> errore)'
);

-- rev 2026-10-27 (lotto 4 di D7): il cliente e l'articolo si COSTRUISCONO
--   (dbops.fn_pgtap_crea_cliente_ba, BA gia' legato all'azienda di chi
--   agisce; dbops.fn_pgtap_crea_articolo, con la sua unita' di misura).
--   Prima si pescavano con LIMIT 1, e su un database ricostruito da zero
--   non c'erano. Le chiamate alla madre, sotto, restano.
CREATE TEMP TABLE tmp_cli_commesse_core AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('commesse core');

CREATE TEMP TABLE tmp_art_commesse_core AS
SELECT dbops.fn_pgtap_crea_articolo(
  ('PGT-CORE-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar,
  false) AS articolo_id;

CREATE TEMP TABLE tmp_refs_commesse_core AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_commesse_core) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_commesse_core) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_cli_commesse_core) AS istanza_utility_id,
  (SELECT anagrafiche.fn_get_emittente_fiscale_id(billing_account_id)
     FROM tmp_cli_commesse_core) AS emittente_soggetto_ruolo_id,
  (SELECT articolo_id FROM tmp_art_commesse_core) AS articolo_id,
  (SELECT a.uom_id FROM catalogo.articoli a
    WHERE a.id = (SELECT articolo_id FROM tmp_art_commesse_core)) AS uom_id,
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
    -- rev 2026-07-27: COMMESSA (key_selector='id') + lookup per codice_interno
    -- immutabile, non per codice (etichetta modificabile) — §6c/§6d.
    WHERE s.codice_interno = 'COMMESSA' AND s.attivo IS TRUE
    LIMIT 1
  ) AS root_sorgente_tipo_id;

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
      AND root_sorgente_tipo_id IS NOT NULL
    FROM tmp_refs_commesse_core
  ),
  'Riferimenti minimi disponibili'
);

-- rev 2026-07-27 (bonifica): RIMOSSO l'upsert su config.sorgenti che stava qui.
-- Riscriveva la riga di seed della sorgente COMMESSA imponendo
-- target_table='vendite.commesse_attivita' — il valore ERRATO corretto nel seed
-- dal brief-db-guard-sorgente-polimorfa (reperto R2): i consumatori del
-- collegamento usano l'id della COMMESSA, non della riga di attivita'.
-- Col guard attivo dal 2026-07-18 quell'upsert faceva validare l'esistenza
-- contro la tabella sbagliata, e ogni link falliva.
-- ⚠️ Un test non deve riscrivere righe di seed condivise: ne altera il
-- comportamento per tutto il resto della transazione. Il seed e' gia' corretto;
-- l'asserzione qui sotto ne verifica la presenza, che e' il vero scopo.

SELECT ok(
  EXISTS (
    SELECT 1
    FROM config.sorgenti s
    WHERE s.codice = 'COMMESSA'
      AND s.attivo IS TRUE
  ),
  'Seed sorgente COMMESSA presente/attivo'
);

CREATE TEMP TABLE tmp_commessa_core AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_commesse_core),
  p_utility_id => (SELECT utility_id FROM tmp_refs_commesse_core),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-06-01',
  p_competenza_al => DATE '2026-06-30',
  p_meta => jsonb_build_object('test_scope', 'pgtap_commesse_core'),
  p_force_new => true
) AS commessa_id;

SELECT ok(
  (SELECT commessa_id IS NOT NULL FROM tmp_commessa_core),
  'Commessa creata'
);

CREATE TEMP TABLE tmp_link_core AS
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
  p_sorgente_tipo_id => (SELECT root_sorgente_tipo_id FROM tmp_refs_commesse_core),
  -- ROOT: uid = id della commessa stessa, esiste per costruzione.
  p_sorgente_uid => (SELECT commessa_id FROM tmp_commessa_core)::text,
  p_sorgente_riga => NULL,
  p_meta => jsonb_build_object('test_scope', 'pgtap_commesse_core')
) AS link_id;

SELECT ok(
  (SELECT link_id IS NOT NULL FROM tmp_link_core),
  'Link ROOT inserito'
);

CREATE TEMP TABLE tmp_link_core_reuse AS
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
  p_sorgente_tipo_id => (SELECT root_sorgente_tipo_id FROM tmp_refs_commesse_core),
  -- La chiave che il link ha stoccato (COMMESSA: l'id, in sorgente_id), resa a testo
  -- come la passa il chiamante.
  p_sorgente_uid => (
    SELECT COALESCE(cs.sorgente_id::text, cs.sorgente_uid::text)
    FROM vendite.commesse_sorgenti cs
    WHERE cs.id = (SELECT link_id FROM tmp_link_core)
  ),
  p_sorgente_riga => NULL,
  p_meta => jsonb_build_object('idempotent', true)
) AS link_id;

SELECT is(
  (SELECT link_id::text FROM tmp_link_core_reuse),
  (SELECT link_id::text FROM tmp_link_core),
  'Link ROOT idempotente (stesso id)'
);

-- Commessa multi-sorgente (brief 2026-06-09): una 2a sorgente DIVERSA sulla
-- stessa commessa non e' piu' un conflitto, ma il flusso normale -> COLLEGATO.
--
-- rev 2026-07-27 (bonifica): la 2a chiave deve essere DIVERSA dalla ROOT (se
-- coincidesse, fn_link sarebbe idempotente e restituirebbe il link ROOT, non un
-- COLLEGATO) ma comunque RISOLVIBILE nel target. Si crea quindi una seconda
-- commessa reale e se ne usa l'id: due chiavi distinte, entrambe esistenti.
CREATE TEMP TABLE tmp_commessa_core_2 AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_commesse_core),
  p_utility_id => (SELECT utility_id FROM tmp_refs_commesse_core),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-06-01',
  p_competenza_al => DATE '2026-06-30',
  p_meta => jsonb_build_object('test_scope', 'pgtap_commesse_core_collegato'),
  p_force_new => true
) AS commessa_id;

CREATE TEMP TABLE tmp_link_core_collegato AS
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
  p_sorgente_tipo_id => (SELECT root_sorgente_tipo_id FROM tmp_refs_commesse_core),
  p_sorgente_uid => (SELECT commessa_id FROM tmp_commessa_core_2)::text,
  p_sorgente_riga => NULL,
  p_meta => '{}'::jsonb
) AS link_id;

SELECT is(
  (SELECT cs.ruolo_link
     FROM vendite.commesse_sorgenti cs
    WHERE cs.id = (SELECT link_id FROM tmp_link_core_collegato)),
  'COLLEGATO',
  'Seconda sorgente diversa sulla stessa commessa -> COLLEGATO (multi-sorgente)'
);

CREATE TEMP TABLE tmp_upsert_core AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
  p_segment_key => ((SELECT x.segment_key FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_commessa_core)) x) || ':' || ('SEG-' || substr(md5(clock_timestamp()::text), 1, 18))::varchar)::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_commesse_core),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_commesse_core),
  p_data_attivita => DATE '2026-06-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_commesse_core),
  p_quantita => 2.000000,
  p_competenza_mese => DATE '2026-06-01',
  p_competenza_dal => DATE '2026-06-01',
  p_competenza_al => DATE '2026-06-30',
  p_prezzo_snapshot => 22.1000000000,
  p_prezzo_base_snapshot => NULL,
  p_origine_prezzo => NULL,
  p_tipo_variazione_applicata => NULL,
  p_valore_variazione_applicata => NULL,
  p_promo_id => NULL,
  p_contratto_id => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot => NULL,
  p_qta_operativa => 2.000000,
  p_uom_operativa_id => (SELECT uom_id FROM tmp_refs_commesse_core),
  p_factor_to_base => 1,
  p_posticipa_al => NULL,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_commesse_core),
  p_valuta_id => (SELECT valuta_id FROM tmp_refs_commesse_core),
  p_area_geografica_id => NULL,
  p_listino_versione_id => NULL,
  p_prezzo_bloccato => true,
  p_pricing_mode => 'FIXED',
  p_prezzo_da_riallineare => false,
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (SELECT x.sorgente_tipo_id FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_commessa_core)) x),
  p_sorgente_uid => (SELECT x.consumo_id::text FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_commessa_core)) x),
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'UPSERT_INSERT')
) r;

SELECT ok(
  (SELECT commessa_attivita_id IS NOT NULL FROM tmp_upsert_core),
  'Upsert commessa_attivita insert'
);

-- ⛔ 2026-09-05 — LISTINO E VERSIONE IN DUE ISTRUZIONI, e non e' stile.
--   Dal changeSet 20260905-05 `vendite.listini_versioni` ha una policy RLS che
--   risolve il perimetro passando dal LISTINO PADRE. Il padre e la figlia
--   stavano in due CTE della STESSA istruzione, e li' non funziona: la policy
--   legge `vendite.listini` con lo snapshot dell'istruzione, che non contiene
--   la riga appena scritta dalla CTE sorella. Padre invisibile -> perimetro
--   NULL -> «la nuova riga viola la regola di sicurezza per riga».
--   ⚠️ Non e' un difetto della policy ne' della fixture: e' la regola
--   `reference_rls_cte_stessa_snapshot`, e vale per chiunque — backend
--   compreso — scriva padre e figlio in un colpo solo su una famiglia protetta.
--   ⇒ Il listino si crea PRIMA, in un'istruzione sua.
-- ⚠️ L'INSERT resta dentro una CTE perche' `CREATE TABLE AS` non accetta
--   un'istruzione di scrittura al primo livello. Cio' che conta e' che le DUE
--   scritture stiano in DUE istruzioni: e' il salto di snapshot che serve alla
--   policy, non la forma della CTE.
-- rev 2026-10-27 (lotto 4 di D7): il listino e la sua versione ATTIVA si
--   COSTRUISCONO (dbops.fn_pgtap_crea_listino, emittente di chi agisce,
--   tipologia ammessa per l'utility), in un'istruzione sua come sopra.
--   Prima copiavano utility, tipologia ed emittente del primo listino
--   attivo, che su un database ricostruito da zero non c'era.
CREATE TEMP TABLE tmp_lst_core_build AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
  (SELECT utility_id FROM tmp_refs_commesse_core),
  'override documento', DATE '2026-01-01', DATE '2026-12-31');

CREATE TEMP TABLE tmp_lst_core_update AS
SELECT listino_id AS id FROM tmp_lst_core_build;

CREATE TEMP TABLE tmp_lst_v_core_update AS
SELECT listino_versione_id AS id FROM tmp_lst_core_build;

CREATE TEMP TABLE tmp_upsert_core_update AS
WITH lst_v AS (
  SELECT id FROM tmp_lst_v_core_update
)
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
  -- la chiave di una riga gia' scritta: ha gia' la provenienza nel prefisso
  p_segment_key => ((
    SELECT ca.segment_key
    FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_upsert_core)
  ))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_commesse_core),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_commesse_core),
  p_data_attivita => DATE '2026-06-16',
  p_uom_id => (SELECT uom_id FROM tmp_refs_commesse_core),
  p_quantita => 3.000000,
  p_competenza_mese => DATE '2026-06-01',
  p_competenza_dal => DATE '2026-06-01',
  p_competenza_al => DATE '2026-06-30',
  p_prezzo_snapshot => 22.1000000000,
  p_prezzo_base_snapshot => NULL,
  p_origine_prezzo => NULL,
  p_tipo_variazione_applicata => NULL,
  p_valore_variazione_applicata => NULL,
  p_promo_id => NULL,
  p_contratto_id => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot => NULL,
  p_qta_operativa => 3.000000,
  p_uom_operativa_id => (SELECT uom_id FROM tmp_refs_commesse_core),
  p_factor_to_base => 1,
  p_posticipa_al => NULL,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_commesse_core),
  p_valuta_id => (SELECT valuta_id FROM tmp_refs_commesse_core),
  p_area_geografica_id => NULL,
  p_listino_versione_id => (SELECT id FROM lst_v),
  p_prezzo_bloccato => true,
  p_pricing_mode => 'FIXED',
  p_prezzo_da_riallineare => false,
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (SELECT x.sorgente_tipo_id FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_commessa_core)) x),
  p_sorgente_uid => (SELECT x.consumo_id::text FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_commessa_core)) x),
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'UPSERT_UPDATE')
) r;

SELECT is(
  (SELECT commessa_attivita_id::text FROM tmp_upsert_core_update),
  (SELECT commessa_attivita_id::text FROM tmp_upsert_core),
  'Upsert commessa_attivita update stesso segment_key'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_upsert_core)
      AND ca.prezzo_bloccato IS TRUE
      AND ca.listino_versione_id IS NOT NULL
  ),
  'Override documento su commessa_attivita (listino_versione_id + prezzo_bloccato)'
);

CREATE TEMP TABLE tmp_emit_dry_core AS
SELECT *
FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
  p_only_approved => true,
  p_dry_run => true
);

SELECT ok(
  (
    SELECT total_candidate = 1
       AND inserted_rows = 1
       AND updated_rows = 0
    FROM tmp_emit_dry_core
  ),
  'Emit dry-run con only_approved=true conta 1 candidato insert'
);

CREATE TEMP TABLE tmp_emit_real_core AS
SELECT *
FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
  p_only_approved => true,
  p_dry_run => false
);

SELECT ok(
  (
    SELECT total_candidate = 1
       AND inserted_rows = 1
       AND updated_rows = 0
    FROM tmp_emit_real_core
  ),
  'Emit reale inserisce 1 riga AF'
);

UPDATE vendite.commesse_attivita
SET stato_emissione = 'NON_EMESSA'
WHERE id = (SELECT commessa_attivita_id FROM tmp_upsert_core);

SELECT * FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
  -- la chiave di una riga gia' scritta: ha gia' la provenienza nel prefisso
  p_segment_key => ((
    SELECT ca.segment_key
    FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_upsert_core)
  ))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_commesse_core),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_commesse_core),
  p_data_attivita => DATE '2026-06-16',
  p_uom_id => (SELECT uom_id FROM tmp_refs_commesse_core),
  p_quantita => 3.000000,
  p_competenza_mese => DATE '2026-06-01',
  p_competenza_dal => DATE '2026-06-01',
  p_competenza_al => DATE '2026-06-30',
  p_prezzo_snapshot => 23.1000000000,
  p_prezzo_base_snapshot => NULL,
  p_origine_prezzo => NULL,
  p_tipo_variazione_applicata => NULL,
  p_valore_variazione_applicata => NULL,
  p_promo_id => NULL,
  p_contratto_id => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot => NULL,
  p_qta_operativa => 3.000000,
  p_uom_operativa_id => (SELECT uom_id FROM tmp_refs_commesse_core),
  p_factor_to_base => 1,
  p_posticipa_al => NULL,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_commesse_core),
  p_valuta_id => (SELECT valuta_id FROM tmp_refs_commesse_core),
  p_area_geografica_id => NULL,
  p_listino_versione_id => NULL,
  p_prezzo_bloccato => false,
  p_pricing_mode => 'FIXED',
  p_prezzo_da_riallineare => false,
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (SELECT x.sorgente_tipo_id FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_commessa_core)) x),
  p_sorgente_uid => (SELECT x.consumo_id::text FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_commessa_core)) x),
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('case', 'UPSERT_PRICE_UPDATE')
);

CREATE TEMP TABLE tmp_emit_rerun_core AS
SELECT *
FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_core),
  p_only_approved => true,
  p_dry_run => false
);

SELECT ok(
  (
    SELECT total_candidate = 1
       AND inserted_rows = 0
       AND updated_rows = 1
    FROM tmp_emit_rerun_core
  ),
  'Rerun emit (stato_emissione riaperto) aggiorna riga AF esistente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili af
    WHERE af.commessa_id = (SELECT commessa_id FROM tmp_commessa_core)
      AND af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_upsert_core)
      AND af.prezzo_unitario = 23.1000000000
      AND af.prezzo_bloccato IS FALSE
  ),
  'Rerun emit propaga aggiornamento prezzo_snapshot/prezzo_bloccato su AF'
);

SELECT ok(
  EXISTS (
    SELECT 1
    -- rev 2026-11-07 (lotto C, giro C.1 di brief-db-sorgente-documento-e-riga):
    --   la provenienza dell'AF e' la riga di commessa (commessa_id +
    --   commessa_attivita_id), non piu' una copia in sorgente_* con tipo COMMESSA.
    FROM vendite.attivita_fatturabili af
    WHERE af.commessa_id = (SELECT commessa_id FROM tmp_commessa_core)
      AND af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_upsert_core)
      AND af.prezzo_bloccato IS FALSE
  ),
  'Propagazione snapshot su AF (commessa/prezzo_bloccato/provenienza dalla riga di commessa)'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_get_commessa_stato((SELECT commessa_id FROM tmp_commessa_core)) x
    WHERE x.total_attivita >= 1
      AND x.total_approvate >= 1
      AND x.total_emesse >= 1
  ),
  'fn_get_commessa_stato restituisce contatori coerenti'
);

SELECT * FROM finish();
ROLLBACK;
