-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.fn_available_actions_ordine — capability data-driven ordine
-- ------------------------------------------------------------
-- Brief: brief-ordini-azioni-data-driven.md
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
-- 10) CONFERMATO -> can_change_state=true (CONFERMATO->ANNULLATO RIACCESA dal
--     cantiere «vie d'uscita per l'operatore», 20260804-33/34/35),
--     can_edit_testata=false, azioni = annulla + push_commessa
-- ------------------------------------------------------------
-- Nota emittente: trgfn_ordini_default_emittente (20260601-21) richiede
--   emittente_fiscale_id su INSERT quando la GUC app.current_user_id e' vuota.
--   In pgTAP la GUC e' vuota: gli ordini passano emittente_fiscale_id esplicito.
--   Ordini con billing_account_id=NULL bypassano il guard di coerenza BA
--   (trgfn_ordini_guard_emittente_ba). L'ordine pushabile usa invece un BA
--   reale con emittente coerente via anagrafiche.fn_get_emittente_fiscale_pk.

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

-- Contesto non-API: GUC vuota (emittente passato esplicitamente nei payload).
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
CREATE TEMP TABLE tmp_refs_aao AS
SELECT
  -- ⛔ L'emittente NON si pesca, si DERIVA (2026-09-23, guida pgTAP §5): con
  --   una sola azienda a catalogo «il primo attivo» e quello di chi agisce
  --   coincidevano per caso, su un database ricostruito no.
  script.fn_pgtap_emittente_operatore() AS emittente_fiscale_id,
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
-- TEST 10) CONFERMATO -> can_change_state=TRUE, can_edit_testata=false
--
--   rev 04-08-2026 — ⚠️ ATTESA CAMBIATA, e non e' una regressione.
--   Fino al 2026-08-04 il test pretendeva `can_change_state = false`,
--   con la motivazione «CONFERMATO->ANNULLATO attivo=false». Il cantiere
--   *vie d'uscita per l'operatore* (`20260804-33/34/35`, applicato alle
--   13:25) ha portato quella riga di `config.transizioni_stati_ordini` a
--   `attivo = true`: poter annullare un ordine confermato e' lo scopo
--   dichiarato di quel lavoro. Il test era rimasto indietro rispetto
--   alla decisione, non il contrario.
--
--   ⚠️ `can_edit_testata` resta **false**, ed e' il punto che rende il
--   test ancora utile: una via d'uscita non e' un permesso di modifica.
--   Un ordine confermato si annulla, non si riscrive. Se un domani
--   `can_edit_testata` diventasse true, e' qui che si deve accorgere
--   qualcuno.
--
--   Si asserisce anche l'INSIEME delle chiavi (`annulla` +
--   `push_commessa`) invece del solo booleano: `can_change_state = true`
--   sarebbe vero anche se la transizione accesa fosse un'altra.
-- ============================================================
SELECT CASE
  WHEN (SELECT push_ba_id FROM tmp_refs_aao) IS NULL
  THEN skip('10) skip: nessun billing_account pushabile/coerente nel seed')
  ELSE ok(
    (SELECT (script.fn_available_actions_ordine(o.id)->>'can_change_state')::boolean IS TRUE
        AND (script.fn_available_actions_ordine(o.id)->>'can_edit_testata')::boolean IS FALSE
        AND (SELECT jsonb_agg(elem->>'key' ORDER BY elem->>'key')
               FROM jsonb_array_elements(
                      script.fn_available_actions_ordine(o.id)->'available_actions'
                    ) AS elem)
            = '["annulla", "push_commessa"]'::jsonb
       FROM tmp_ord_conf o),
    'CONFERMATO: can_change_state=true (CONFERMATO->ANNULLATO riacceso), can_edit_testata=false, azioni = annulla + push_commessa'
  )
END;

SELECT * FROM finish();
ROLLBACK;
