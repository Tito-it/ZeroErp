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
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): i due ordini da
--   dbops.fn_pgtap_crea_ordine_con_righe (DRAFT e CONFERMATO, 5 x 12, data 2026-06-15),
--   ognuno col suo cliente costruito. ⚠️ CURATO: l'ordine pushabile pescava un billing
--   account dal database (push_ba_id, «il primo» utility/istanza/fatturazione CONFERMATO),
--   e i test 9-10 andavano in skip dove non c'era. Ora il cliente si costruisce e la
--   condizione che quel BA rendeva vera (fatturazione al CONFERMATO) si scrive sull'ordine:
--   9 e 10 girano sempre.

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
-- Ordine DRAFT con una riga (fixture test 2-8).
CREATE TEMP TABLE tmp_ord_draft AS
SELECT o.ordine_id AS id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('capability ordine draft', 'DRAFT',
           p_quantita => 5, p_prezzo => 12, p_data_ordine => DATE '2026-06-15') o;

-- Ordine CONFERMATO con una riga pushabile (fixture test 9-10): fatturazione al
-- CONFERMATO, la condizione che lo rende eleggibile al push.
CREATE TEMP TABLE tmp_ord_conf AS
SELECT o.ordine_id AS id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('capability ordine conf', 'CONFERMATO',
           p_quantita => 5, p_prezzo => 12, p_data_ordine => DATE '2026-06-15',
           p_fatturazione_trigger => 'CONFERMATO') o;

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
-- ============================================================
SELECT ok(
    (SELECT (script.fn_available_actions_ordine(o.id)->>'can_push_commessa')::boolean IS TRUE
        AND EXISTS (
              SELECT 1
                FROM jsonb_array_elements(
                       script.fn_available_actions_ordine(o.id)->'available_actions') AS elem
               WHERE elem->>'key' = 'push_commessa')
       FROM tmp_ord_conf o),
    'CONFERMATO: can_push_commessa=true e push_commessa presente in available_actions'
);

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
--   ⚠️ `can_edit_testata` era **false**, e questo test ne pinnava il
--   senso: una via d'uscita non e' un permesso di modifica. Un ordine
--   confermato si annulla, non si riscrive.
--   ⭐ rev 2026-10-10 (brief-db-testata-dopo-emissione, fase 2, D-0/D-10):
--   can_edit_testata si legge dal montaggio del lock di testata e vuol dire
--   «in questo stato almeno un campo della testata si cambia» (le note, nei
--   documenti vivi). Che il documento non si RISCRIVA lo dice
--   non_editable_fields, che deve contenere identita' e condizioni.
--   Il senso resta, e si prova dove ora sta: can_edit_testata e' true
--   (le note), e data, valuta, pagamento e cliente sono fra i
--   non_editable_fields.
--
--   Si asserisce anche l'INSIEME delle chiavi (`annulla` +
--   `push_commessa`) invece del solo booleano: `can_change_state = true`
--   sarebbe vero anche se la transizione accesa fosse un'altra.
-- ============================================================
SELECT ok(
    (SELECT (script.fn_available_actions_ordine(o.id)->>'can_change_state')::boolean IS TRUE
        AND (script.fn_available_actions_ordine(o.id)->>'can_edit_testata')::boolean IS TRUE
        AND (script.fn_available_actions_ordine(o.id)->'non_editable_fields')
            @> '["data","valuta_id","termine_pagamento_id","modalita_pagamento_id","billing_account_id"]'
        AND (SELECT jsonb_agg(elem->>'key' ORDER BY elem->>'key')
               FROM jsonb_array_elements(
                      script.fn_available_actions_ordine(o.id)->'available_actions'
                    ) AS elem)
            = '["annulla", "push_commessa"]'::jsonb
       FROM tmp_ord_conf o),
    'CONFERMATO: can_change_state=true (CONFERMATO->ANNULLATO riacceso), can_edit_testata=true (solo le note: identita'', condizioni e cliente non modificabili), azioni = annulla + push_commessa'
);

SELECT * FROM finish();
ROLLBACK;
