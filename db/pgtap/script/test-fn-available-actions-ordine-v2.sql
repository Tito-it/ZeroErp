-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.fn_available_actions_ordine — decoupling fatturazione <->
--       spedizione (rev 20260710-02): can_push su PARZIALMENTE_EVASO/EVASO,
--       nuovi reason ORDINE_GIA_FATTURATO / ORDINE_FATTURA_DA_DDT
-- Piano: piano-db-fix-orfano-push-ordine-confermato.md §4.2
-- Brief: brief-db-ddt-vendita-evasione-e-stati §16
-- ------------------------------------------------------------
-- Indice test (1..9):
--  1) riferimenti minimi disponibili (BA pushabile CONFERMATO)
--  2) orfano EVASO (trigger CONFERMATO, mai pushato) -> can_push_commessa=true
--  3) orfano EVASO -> azione push_commessa presente in available_actions
--  4) PARZIALMENTE_EVASO -> can_push_commessa=true
--  5) dopo push simulato (EMESSA) -> can_push=false + reason ORDINE_GIA_FATTURATO
--  6) reason_key = 'vendite.ordini.push_commessa_reason.gia_fatturato'
--  7) trigger SPEDITO (stato CONFERMATO) -> reason ORDINE_FATTURA_DA_DDT
--  8) DRAFT -> reason ORDINE_NON_CONFERMATO (non-regressione v1)
--  9) namespace i18n: ogni reason_key emessa sta sotto 'vendite.ordini.'
-- ------------------------------------------------------------
-- Nota emittente: come v1 — GUC app.current_user_id vuota, emittente
--   passato esplicito nei payload.
-- Nota skip-tolerance: fallback OR su BA pushabile mancante (pattern v1).

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

SELECT plan(9);

-- Contesto non-API: GUC vuota (emittente passato esplicitamente).
-- ⛔ 2026-09-04 — QUI IL TEST SPEGNEVA IL GUARD, e adesso non piu'.
--   La riga rimossa era `set_config('app.current_user_id', '', true)`: senza
--   utente in sessione `script.trgfn_guard_emittente_scope` usciva subito con
--   RETURN NEW, e le fixture entravano senza che nessuno guardasse l'emittente.
--   La fase 6 di `brief-db-processi-automatici-identita-e-perimetro` chiude quel
--   ramo — una sessione applicativa senza utente non scrive piu'.
--   ⇒ Il contesto operatore del preambolo RESTA valido per tutto il file, e le
--     fixture prendono l'emittente su cui quell'operatore puo' davvero scrivere
--     (`script.fn_pgtap_emittente_operatore()`).
--   ⭐ Non e' una riparazione di comodo: prima questo file collaudava il
--     comportamento di una porta aperta, adesso attraversa il guard come lo
--     attraversa l'applicazione.

-- ============================================================
-- Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_refs_aa2 AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND ba.fatturazione_ordini = 'CONFERMATO'
      AND anagrafiche.fn_get_emittente_fiscale_pk(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1)                          AS push_ba_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr
    ORDER BY sr.id LIMIT 1)                          AS soggetto_ruolo_id,
  -- ⛔ L'emittente NON si pesca, si DERIVA (2026-09-23, guida pgTAP §5): con
  --   una sola azienda a catalogo «il primo attivo» e quello di chi agisce
  --   coincidevano per caso, su un database ricostruito no.
  script.fn_pgtap_emittente_operatore()  AS emittente_fiscale_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE
      AND COALESCE(a.is_composito, FALSE) IS FALSE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1)  AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT i.id FROM config.iva i
    WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)    AS iva_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno = 'CONFERMATO' AND s.attivo IS TRUE LIMIT 1) AS stato_conf_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE LIMIT 1)      AS stato_draft_id;

SELECT ok(
  (SELECT push_ba_id IS NOT NULL
      AND soggetto_ruolo_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND stato_conf_id IS NOT NULL
   FROM tmp_refs_aa2),
  '1) riferimenti minimi disponibili (BA pushabile CONFERMATO)'
);

-- ============================================================
-- FIXTURE A: orfano — ordine trigger CONFERMATO evaso FULL, mai pushato
-- ============================================================
CREATE TEMP TABLE tmp_ord_aa2_a AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.push_ba_id,
         anagrafiche.fn_get_emittente_fiscale_pk(r.push_ba_id),
         r.stato_conf_id, r.valuta_id, DATE '2026-07-05', false,
         jsonb_build_object('test_scope','pgtap_fn_aa_ordine_v2','fix','orfano_a')
  FROM tmp_refs_aa2 r
  WHERE r.push_ba_id IS NOT NULL
  RETURNING id, uid)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ord_aa2_a_riga AS
WITH ins AS (
  INSERT INTO vendite.ordini_righe (
    ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id,
    attivo, storicizza, meta)
  SELECT o.id, 1, r.articolo_id, 'Riga orfano AA2',
         10.000000, 10.000000, 30.000000, r.iva_id,
         true, false, jsonb_build_object('test_scope','pgtap_fn_aa_ordine_v2')
  FROM tmp_ord_aa2_a o, tmp_refs_aa2 r
  RETURNING id)
SELECT * FROM ins;

-- Evasione FULL -> ordine EVASO (skip-tolerant)
SELECT vendite.fn_genera_ddt_da_ordine((SELECT id FROM tmp_ord_aa2_a))
 WHERE EXISTS (SELECT 1 FROM tmp_ord_aa2_a);

-- 2) orfano EVASO -> can_push_commessa = true
SELECT ok(
  ((script.fn_available_actions_ordine(
      (SELECT id FROM tmp_ord_aa2_a)))->>'can_push_commessa')::boolean
  OR (SELECT push_ba_id IS NULL FROM tmp_refs_aa2),
  '2) orfano EVASO trigger CONFERMATO -> can_push_commessa=true (fix)'
);

-- 3) azione push_commessa presente
SELECT ok(
  EXISTS (
    SELECT 1
      FROM jsonb_array_elements(
             (script.fn_available_actions_ordine(
                (SELECT id FROM tmp_ord_aa2_a)))->'available_actions') AS a
     WHERE a->>'key' = 'push_commessa')
  OR (SELECT push_ba_id IS NULL FROM tmp_refs_aa2),
  '3) orfano EVASO -> push_commessa in available_actions'
);

-- ============================================================
-- FIXTURE B: PARZIALMENTE_EVASO (evasione 4/10)
-- ============================================================
CREATE TEMP TABLE tmp_ord_aa2_b AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.push_ba_id,
         anagrafiche.fn_get_emittente_fiscale_pk(r.push_ba_id),
         r.stato_conf_id, r.valuta_id, DATE '2026-07-06', false,
         jsonb_build_object('test_scope','pgtap_fn_aa_ordine_v2','fix','parz_b')
  FROM tmp_refs_aa2 r
  WHERE r.push_ba_id IS NOT NULL
  RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ord_aa2_b_riga AS
WITH ins AS (
  INSERT INTO vendite.ordini_righe (
    ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id,
    attivo, storicizza, meta)
  SELECT o.id, 1, r.articolo_id, 'Riga parziale BB2',
         10.000000, 10.000000, 20.000000, r.iva_id,
         true, false, jsonb_build_object('test_scope','pgtap_fn_aa_ordine_v2')
  FROM tmp_ord_aa2_b o, tmp_refs_aa2 r
  RETURNING id)
SELECT * FROM ins;

SELECT vendite.fn_genera_ddt_da_ordine(
         (SELECT id FROM tmp_ord_aa2_b),
         jsonb_build_array(jsonb_build_object(
             'ordine_riga_id', (SELECT id FROM tmp_ord_aa2_b_riga),
             'qta_da_evadere', 4)))
 WHERE EXISTS (SELECT 1 FROM tmp_ord_aa2_b);

-- 4) PARZIALMENTE_EVASO -> can_push = true
SELECT ok(
  ((script.fn_available_actions_ordine(
      (SELECT id FROM tmp_ord_aa2_b)))->>'can_push_commessa')::boolean
  OR (SELECT push_ba_id IS NULL FROM tmp_refs_aa2),
  '4) PARZIALMENTE_EVASO trigger CONFERMATO -> can_push_commessa=true'
);

-- ============================================================
-- 5-6) Push simulato sull'orfano A (attivita EMESSA) -> GIA_FATTURATO
-- ============================================================
CREATE TEMP TABLE tmp_pushrow_aa2 AS
SELECT * FROM vendite.fn_list_ordini_da_pushare(
         p_ordine_id => (SELECT id FROM tmp_ord_aa2_a));

CREATE TEMP TABLE tmp_commessa_aa2 AS
SELECT vendite.fn_get_or_create_commessa(
         p_billing_account_id          => pr.billing_account_id,
         p_utility_id                  => pr.utility_id,
         p_competenza_dal              => pr.competenza_dal,
         p_competenza_al               => pr.competenza_al,
         p_meta => jsonb_build_object('test_scope','pgtap_fn_aa_ordine_v2')
       ) AS commessa_id
  FROM tmp_pushrow_aa2 pr
 LIMIT 1;

SELECT vendite.fn_upsert_commessa_attivita(
         p_commessa_id                   => c.commessa_id,
         p_segment_key                   => pr.segment_key,
         p_articolo_id                   => pr.articolo_id,
         p_istanza_utility_id            => pr.istanza_utility_id,
         p_data_attivita                 => pr.data_attivita,
         p_uom_id                        => pr.uom_id,
         p_quantita                      => pr.quantita,
         p_competenza_mese               => pr.competenza_mese,
         p_competenza_dal                => pr.competenza_dal,
         p_competenza_al                 => pr.competenza_al,
         p_prezzo_snapshot               => pr.prezzo_snapshot,
         p_prezzo_base_snapshot          => NULL,
         p_origine_prezzo                => NULL,
         p_tipo_variazione_applicata     => NULL,
         p_valore_variazione_applicata   => NULL,
         p_promo_id                      => NULL,
         p_contratto_id                  => NULL,
         p_categoria_cliente_id_snapshot => NULL,
         p_classe_utenza_id_snapshot     => NULL,
         p_qta_operativa                 => pr.qta_operativa,
         p_uom_operativa_id              => pr.uom_operativa_id,
         p_factor_to_base                => pr.factor_to_base,
         p_tipo_doc_fiscale_id           => pr.tipo_doc_fiscale_id,
         p_valuta_id                     => pr.valuta_id,
         p_prezzo_bloccato               => pr.prezzo_bloccato,
         p_pricing_mode                  => pr.pricing_mode,
         p_stato_emissione               => 'EMESSA',
         p_sorgente_tipo_id              => pr.sorgente_tipo_id,
         p_sorgente_uid                  => pr.sorgente_uid,
         p_meta                          => pr.meta)
  FROM tmp_pushrow_aa2 pr, tmp_commessa_aa2 c;

-- 5) dopo EMESSA: can_push=false + reason GIA_FATTURATO
SELECT ok(
  ((NOT ((script.fn_available_actions_ordine(
            (SELECT id FROM tmp_ord_aa2_a)))->>'can_push_commessa')::boolean)
   AND (script.fn_available_actions_ordine(
          (SELECT id FROM tmp_ord_aa2_a)))->>'can_push_commessa_reason'
       = 'ORDINE_GIA_FATTURATO')
  OR (SELECT push_ba_id IS NULL FROM tmp_refs_aa2),
  '5) dopo push simulato (EMESSA) -> can_push=false + ORDINE_GIA_FATTURATO'
);

-- 6) reason_key coerente — namespace vendite.ordini.* (20260719-12):
--    il namespace `ordini.*` non esiste nei locales FE, la chiave non si
--    risolveva e il banner restava muto.
SELECT ok(
  ((script.fn_available_actions_ordine(
      (SELECT id FROM tmp_ord_aa2_a)))->>'can_push_commessa_reason_key'
     = 'vendite.ordini.push_commessa_reason.gia_fatturato')
  OR (SELECT push_ba_id IS NULL FROM tmp_refs_aa2),
  '6) reason_key = vendite.ordini.push_commessa_reason.gia_fatturato'
);

-- ============================================================
-- 7) trigger SPEDITO (stato CONFERMATO) -> ORDINE_FATTURA_DA_DDT
-- ============================================================
CREATE TEMP TABLE tmp_ord_aa2_c AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.push_ba_id,
         anagrafiche.fn_get_emittente_fiscale_pk(r.push_ba_id),
         r.stato_conf_id, r.valuta_id, DATE '2026-07-07', false,
         jsonb_build_object('test_scope','pgtap_fn_aa_ordine_v2','fix','spedito_c')
  FROM tmp_refs_aa2 r
  WHERE r.push_ba_id IS NOT NULL
  RETURNING id)
SELECT * FROM ins;

-- normalize e' INSERT-only: il trigger si aggiorna DOPO l'INSERT
UPDATE vendite.ordini
   SET fatturazione_trigger = 'SPEDITO'
 WHERE id = (SELECT id FROM tmp_ord_aa2_c);

INSERT INTO vendite.ordini_righe (
  ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, iva_id,
  attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'Riga spedito CC2',
       5.000000, 5.000000, 15.000000, r.iva_id,
       true, false, jsonb_build_object('test_scope','pgtap_fn_aa_ordine_v2')
FROM tmp_ord_aa2_c o, tmp_refs_aa2 r;

SELECT ok(
  (((script.fn_available_actions_ordine(
       (SELECT id FROM tmp_ord_aa2_c)))->>'can_push_commessa')::boolean IS FALSE
   AND (script.fn_available_actions_ordine(
          (SELECT id FROM tmp_ord_aa2_c)))->>'can_push_commessa_reason'
       = 'ORDINE_FATTURA_DA_DDT')
  OR (SELECT push_ba_id IS NULL FROM tmp_refs_aa2),
  '7) trigger SPEDITO -> can_push=false + ORDINE_FATTURA_DA_DDT (pusha il DDT)'
);

-- ============================================================
-- 8) DRAFT -> ORDINE_NON_CONFERMATO (non-regressione v1)
-- ============================================================
CREATE TEMP TABLE tmp_ord_aa2_d AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, NULL::bigint, r.emittente_fiscale_id,
         r.stato_draft_id, r.valuta_id, DATE '2026-07-08', false,
         jsonb_build_object('test_scope','pgtap_fn_aa_ordine_v2','fix','draft_d')
  FROM tmp_refs_aa2 r
  RETURNING id)
SELECT * FROM ins;

SELECT ok(
  ((script.fn_available_actions_ordine(
      (SELECT id FROM tmp_ord_aa2_d)))->>'can_push_commessa_reason'
     = 'ORDINE_NON_CONFERMATO'),
  '8) DRAFT -> reason ORDINE_NON_CONFERMATO (non-regressione v1)'
);

-- ============================================================
-- 9) Guard di namespace i18n — anti-ereditarieta'
-- ============================================================
-- Il difetto originario (reason_key sotto `ordini.*`, radice inesistente
-- nei locales FE) e' nato con la funzione e si e' propagato per un mese e
-- mezzo attraverso 5 revisioni, perche' ogni CREATE OR REPLACE riparte dal
-- corpo della precedente e nessuno rileggeva quelle righe. Una chiave non
-- risolta non da' errore: da' testo mancante, quindi passa inosservata.
-- Questo test rende l'errore rumoroso al primo copia-incolla sbagliato.
-- Copre 3 rami su 5 (gia_fatturato, fattura_da_ddt, non_confermato):
-- gli altri due condividono lo stesso prefisso nello stesso blocco IF.
-- Convenzione: docs/it/dev/frontend/i18n-namespace-radici.md
SELECT ok(
  (SELECT bool_and(k LIKE 'vendite.ordini.push_commessa_reason.%')
     FROM (
       SELECT (script.fn_available_actions_ordine(
                 (SELECT id FROM tmp_ord_aa2_a)))->>'can_push_commessa_reason_key' AS k
       UNION ALL
       SELECT (script.fn_available_actions_ordine(
                 (SELECT id FROM tmp_ord_aa2_c)))->>'can_push_commessa_reason_key'
       UNION ALL
       SELECT (script.fn_available_actions_ordine(
                 (SELECT id FROM tmp_ord_aa2_d)))->>'can_push_commessa_reason_key'
     ) q
    WHERE k IS NOT NULL)
  OR (SELECT push_ba_id IS NULL FROM tmp_refs_aa2),
  '9) tutte le reason_key emesse stanno sotto vendite.ordini.push_commessa_reason.*'
);

SELECT * FROM finish();
ROLLBACK;
