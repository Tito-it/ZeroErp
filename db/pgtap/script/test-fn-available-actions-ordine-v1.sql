-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.fn_available_actions_ordine — capability data-driven ordine
-- ------------------------------------------------------------
-- Brief: docs/it/dev/work-in-progress/brief-ordini-azioni-data-driven.md
-- Indice test (1..10):
-- 1)  Ordine inesistente -> NULL
-- 2)  DRAFT -> available_actions = 2 (conferma + annulla)
-- 3)  DRAFT -> azioni ordinate: prima 'conferma' (CONFERMATO, ordine=20)
-- 4)  DRAFT -> seconda azione 'annulla' (ANNULLATO, ordine=60)
-- 5)  DRAFT -> can_edit_testata=true, can_edit_righe=true, can_change_state=true
-- 6)  DRAFT -> can_push_commessa=false, reason='ORDINE_NON_CONFERMATO'
-- 7)  DRAFT -> non_editable_fields = solo cliente (billing_account_id, soggetto_ruolo_id)
-- 8)  DRAFT -> tutte le azioni hanno label_key valorizzato
-- 9)  CONFERMATO (riga pushabile) -> can_push_commessa=true, push_commessa in azioni
-- 10) CONFERMATO -> can_change_state=false (CONFERMATO->ANNULLATO disattiva), can_edit_testata=false
-- ------------------------------------------------------------
-- Nota emittente: trgfn_ordini_default_emittente (20260601-21) richiede
--   emittente_fiscale_id su INSERT quando la GUC app.current_user_id e' vuota.
--   In pgTAP la GUC e' vuota: gli ordini passano emittente_fiscale_id esplicito.
--   Ordini con billing_account_id=NULL bypassano il guard di coerenza BA
--   (trgfn_ordini_guard_emittente_ba). L'ordine pushabile usa invece un BA
--   reale con emittente coerente via anagrafiche.fn_get_emittente_fiscale_pk.

BEGIN;
SELECT plan(10);

-- Contesto non-API: GUC vuota (emittente passato esplicitamente nei payload).
SELECT set_config('app.current_user_id', '', true);

-- ============================================================
-- Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_refs_aao AS
SELECT
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1
  ) AS emittente_fiscale_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id LIMIT 1
  ) AS soggetto_ruolo_id,
  (SELECT a.id FROM catalogo.articoli a WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST, a.id LIMIT 1
  ) AS articolo_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'CONFERMATO' AND attivo IS TRUE LIMIT 1
  ) AS stato_confermato_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'DRAFT' AND attivo IS TRUE LIMIT 1
  ) AS stato_draft_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  -- BA pushabile (utility/istanza valorizzate, fatturazione CONFERMATO,
  -- emittente risolvibile): rende l'ordine CONFERMATO eleggibile al push.
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND ba.fatturazione_ordini = 'CONFERMATO'
      AND anagrafiche.fn_get_emittente_fiscale_pk(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS push_ba_id;

-- Ordine DRAFT con una riga (fixture test 2-8). BA=NULL, emittente esplicito.
CREATE TEMP TABLE tmp_ord_draft AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza, meta
  )
  SELECT
    r.soggetto_ruolo_id, NULL::bigint, r.emittente_fiscale_id,
    r.stato_draft_id, r.valuta_id, DATE '2026-06-15',
    false, jsonb_build_object('test_scope', 'pgtap_fn_aa_ordine', 'stato', 'draft')
  FROM tmp_refs_aao r
  RETURNING id
)
SELECT * FROM ins;

INSERT INTO vendite.ordini_righe (
  ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, attivo, storicizza, meta
)
SELECT
  o.id, 1, r.articolo_id, 'Riga test pgtap draft',
  5.000000, 5.000000, 12.000000, true, false,
  jsonb_build_object('test_scope', 'pgtap_fn_aa_ordine')
FROM tmp_ord_draft o, tmp_refs_aao r;

-- Ordine CONFERMATO con una riga pushabile (fixture test 9-10).
-- BA reale + emittente coerente; trgfn_ordini_normalize eredita
-- fatturazione_trigger=CONFERMATO dal BA su INSERT.
CREATE TEMP TABLE tmp_ord_conf AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza, meta
  )
  SELECT
    r.soggetto_ruolo_id, r.push_ba_id,
    anagrafiche.fn_get_emittente_fiscale_pk(r.push_ba_id),
    r.stato_confermato_id, r.valuta_id, DATE '2026-06-15',
    false, jsonb_build_object('test_scope', 'pgtap_fn_aa_ordine', 'stato', 'conf')
  FROM tmp_refs_aao r
  WHERE r.push_ba_id IS NOT NULL
  RETURNING id
)
SELECT * FROM ins;

INSERT INTO vendite.ordini_righe (
  ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, attivo, storicizza, meta
)
SELECT
  o.id, 1, r.articolo_id, 'Riga test pgtap conf',
  5.000000, 5.000000, 12.000000, true, false,
  jsonb_build_object('test_scope', 'pgtap_fn_aa_ordine')
FROM tmp_ord_conf o, tmp_refs_aao r;

-- ============================================================
-- TEST 1) Ordine inesistente -> NULL
-- ============================================================
SELECT is(
  script.fn_available_actions_ordine(-1),
  NULL,
  'fn_available_actions_ordine(-1): ordine inesistente -> NULL'
);

-- ============================================================
-- TEST 2) DRAFT -> 2 azioni (conferma + annulla)
-- ============================================================
SELECT is(
  (SELECT jsonb_array_length(
            script.fn_available_actions_ordine(o.id)->'available_actions')
     FROM tmp_ord_draft o),
  2,
  'DRAFT: 2 azioni manuali (conferma + annulla)'
);

-- ============================================================
-- TEST 3) DRAFT -> prima azione 'conferma' (ordinata per stato a.ordine=20)
-- ============================================================
SELECT is(
  (SELECT script.fn_available_actions_ordine(o.id)->'available_actions'->0->>'key'
     FROM tmp_ord_draft o),
  'conferma',
  'DRAFT: prima azione key=''conferma'' (CONFERMATO ordine=20)'
);

-- ============================================================
-- TEST 4) DRAFT -> seconda azione 'annulla' (ANNULLATO ordine=60)
-- ============================================================
SELECT is(
  (SELECT script.fn_available_actions_ordine(o.id)->'available_actions'->1->>'key'
     FROM tmp_ord_draft o),
  'annulla',
  'DRAFT: seconda azione key=''annulla'' (ANNULLATO ordine=60)'
);

-- ============================================================
-- TEST 5) DRAFT -> can_edit_testata/righe=true, can_change_state=true
-- ============================================================
SELECT ok(
  (SELECT (script.fn_available_actions_ordine(o.id)->>'can_edit_testata')::boolean IS TRUE
      AND (script.fn_available_actions_ordine(o.id)->>'can_edit_righe')::boolean IS TRUE
      AND (script.fn_available_actions_ordine(o.id)->>'can_change_state')::boolean IS TRUE
     FROM tmp_ord_draft o),
  'DRAFT: can_edit_testata=true, can_edit_righe=true, can_change_state=true'
);

-- ============================================================
-- TEST 6) DRAFT -> can_push_commessa=false, reason='ORDINE_NON_CONFERMATO'
-- ============================================================
SELECT ok(
  (SELECT (script.fn_available_actions_ordine(o.id)->>'can_push_commessa')::boolean IS FALSE
      AND (script.fn_available_actions_ordine(o.id)->>'can_push_commessa_reason') = 'ORDINE_NON_CONFERMATO'
     FROM tmp_ord_draft o),
  'DRAFT: can_push_commessa=false, reason=ORDINE_NON_CONFERMATO'
);

-- ============================================================
-- TEST 7) DRAFT -> non_editable_fields = solo cliente (2 campi)
-- ============================================================
SELECT ok(
  (SELECT (script.fn_available_actions_ordine(o.id)->'non_editable_fields')
            @> '["billing_account_id","soggetto_ruolo_id"]'::jsonb
      AND jsonb_array_length(
            script.fn_available_actions_ordine(o.id)->'non_editable_fields') = 2
     FROM tmp_ord_draft o),
  'DRAFT: non_editable_fields = cliente immutabile (billing_account_id, soggetto_ruolo_id)'
);

-- ============================================================
-- TEST 8) DRAFT -> tutte le azioni hanno label_key valorizzato
-- ============================================================
SELECT ok(
  (SELECT bool_and((elem->>'label_key') IS NOT NULL AND (elem->>'label_key') <> '')
     FROM tmp_ord_draft o,
          jsonb_array_elements(
            script.fn_available_actions_ordine(o.id)->'available_actions') AS elem),
  'DRAFT: tutte le azioni hanno label_key valorizzato'
);

-- ============================================================
-- TEST 9) CONFERMATO (riga pushabile) -> can_push_commessa=true + azione push_commessa
--         (skip se nessun BA pushabile disponibile nel seed)
-- ============================================================
SELECT CASE
  WHEN (SELECT push_ba_id FROM tmp_refs_aao) IS NULL
  THEN skip('9) skip: nessun billing_account pushabile/coerente nel seed')
  ELSE ok(
    (SELECT (script.fn_available_actions_ordine(o.id)->>'can_push_commessa')::boolean IS TRUE
        AND EXISTS (
              SELECT 1
                FROM jsonb_array_elements(
                       script.fn_available_actions_ordine(o.id)->'available_actions') AS elem
               WHERE elem->>'key' = 'push_commessa')
       FROM tmp_ord_conf o),
    'CONFERMATO: can_push_commessa=true e push_commessa presente in available_actions'
  )
END;

-- ============================================================
-- TEST 10) CONFERMATO -> can_change_state=false (no transizioni manuali attive),
--          can_edit_testata=false
-- ============================================================
SELECT CASE
  WHEN (SELECT push_ba_id FROM tmp_refs_aao) IS NULL
  THEN skip('10) skip: nessun billing_account pushabile/coerente nel seed')
  ELSE ok(
    (SELECT (script.fn_available_actions_ordine(o.id)->>'can_change_state')::boolean IS FALSE
        AND (script.fn_available_actions_ordine(o.id)->>'can_edit_testata')::boolean IS FALSE
       FROM tmp_ord_conf o),
    'CONFERMATO: can_change_state=false (CONFERMATO->ANNULLATO attivo=false), can_edit_testata=false'
  )
END;

SELECT * FROM finish();
ROLLBACK;
