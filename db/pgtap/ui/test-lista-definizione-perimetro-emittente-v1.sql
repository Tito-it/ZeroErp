-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il TERZO CASO del perimetro emittente di una lista
--       ui.lista_definizione.perimetro_emittente   (20260902-01)
--       seed della lista famiglie                  (20260902-02)
--       ui.fn_resolve_lista_config                 (20260902-03)
--       Piano: brief-be-fe-crud-registri-di-numerazione, sezione 11.16
-- ------------------------------------------------------------
-- Elenco test (plan 7):
-- 1) ⭐ Il risolutore porta la chiave `perimetro_emittente`
-- 2) ⭐ La lista delle famiglie dichiara di NON avere perimetro
-- 3) ⭐ ...e resta `multi_emittente = false`, che e' la verita'
-- 4) ⛔ Dall'APPLICAZIONE quel flag non si scrive affatto: parla il guard
-- 5) ⛔ ...e dietro il guard c'e' il CHECK, per chi il guard lo attraversa
-- 6) ⭐ Le altre liste non cambiano: il default e' «con perimetro»
-- 7) ⛔⛔ La vista di certificazione resta a ZERO righe
--
-- Scopo:
--   ⭐ IL TEST CHE CONTA E' IL 7, ed e' il motivo per cui questa colonna
--   esiste. La strada breve era dichiarare la lista famiglie
--   `multi_emittente = true` — cioe' vantare una capacita' che non ha — e la
--   vista di certificazione l'avrebbe intercettata. Il 7 verifica che la
--   strada lunga NON abbia pagato quel prezzo.
--
--   ⛔ E il 3 e' il suo gemello dal lato opposto: se un domani qualcuno
--   «semplificasse» mettendo `t` al posto della colonna nuova, il 3 diventa
--   rosso prima del 7, e dice perche'.
--
-- ⚠️ COSA QUESTO FILE NON PROVA: che il frontend entri davvero senza chiedere
--   l'emittente. La chiave viaggia nella configurazione risolta; chi la legge
--   e' fuori dal database (§11.16, richiesta BE-F9/FE-F7).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- 1/2/3) La chiave, e cosa dice sulla lista famiglie
-- ============================================================
SELECT ok(
    ui.fn_resolve_lista_config('vendite.famiglie_documento', NULL, NULL) ? 'perimetro_emittente',
    '1) La configurazione risolta porta la chiave `perimetro_emittente`');

SELECT is(
    (ui.fn_resolve_lista_config('vendite.famiglie_documento', NULL, NULL) ->> 'perimetro_emittente'),
    'false',
    '2) La lista delle famiglie dichiara di NON avere un perimetro emittente');

-- ⭐ Il gemello: la strada breve sarebbe stata mettere `t` qui. Se qualcuno la
--   prendesse, questo test lo dice prima che lo dica la vista del test 7.
SELECT is(
    (ui.fn_resolve_lista_config('vendite.famiglie_documento', NULL, NULL) ->> 'multi_emittente'),
    'false',
    '3) ...e resta multi_emittente = false, che e'' la verita'': non ha emittenti da dire');

-- ============================================================
-- 4/5) ⛔ «Non ho emittenti, e so dirti quale sono» — DUE muri
-- ============================================================
-- 🔴 DAVANTI A `multi_emittente` CI SONO DUE PRESIDI, E NON DICONO LA STESSA
--   COSA. Il primo e' il guard trg_ui_lista_definizione_a10_guard_multi_emittente_ins_upd:
--   quel flag non si scrive DALL'APPLICAZIONE, punto — si dichiara nel seed.
--   Il secondo e' il CHECK di coerenza, che vale per tutti, migrate compreso.
--
-- ⚠️ Questa distinzione si e' vista SOLO lanciando il test come applicazione:
--   girando da owner il guard esce subito (pg_has_role) e a rifiutare e' il
--   CHECK, quindi un test scritto in quella condizione chiede il 23514 e lo
--   ottiene. In esercizio arriva un P0001, e il test diventa rosso su un
--   database sano. ⛔ Un presidio che passa solo nella veste sbagliata non
--   presidia: prova la veste.
PREPARE incoerente AS
UPDATE ui.lista_definizione SET multi_emittente = TRUE
 WHERE codice = 'vendite.famiglie_documento';

SELECT throws_ok(
    'incoerente', 'P0001',
    NULL,
    '4) Dall''applicazione il flag non si scrive affatto: a rifiutare e'' il guard');

-- ⭐ Il secondo muro si prova sulla STRUTTURA e non sul comportamento: per
--   vederlo agire servirebbe la veste dell'owner, che questo file non ha e non
--   deve avere. Se qualcuno togliesse il CHECK, questo test diventa rosso.
SELECT is(
    (SELECT pg_get_constraintdef(oid)
       FROM pg_constraint
      WHERE conname = 'chk_ui_lista_definizione_perimetro_coerente'),
    'CHECK ((perimetro_emittente OR (NOT multi_emittente)))',
    '5) ...e dietro il guard c''e'' il CHECK, che vale anche per il migrate');

-- ============================================================
-- 6) ⭐ Le altre non cambiano
-- ============================================================
-- ⚠️ Derivato, non un elenco: si contano le liste attive che NON hanno
--   dichiarato la globalita'. Il default e' «con perimetro», quindi una lista
--   nuova nasce come nascevano tutte prima del 2026-09-02.
SELECT is(
    (SELECT count(*)::int
       FROM ui.lista_definizione
      WHERE attivo
        AND NOT perimetro_emittente
        AND codice <> 'vendite.famiglie_documento'),
    0,
    '6) Nessun''altra lista ha dichiarato di essere globale: il default non si eredita');

-- ============================================================
-- 7) ⛔⛔ Il prezzo che NON si e' pagato
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM dbops.vw_liste_multi_emittente_non_certificate),
    0,
    '7) La vista di certificazione resta a zero righe: nessun adesivo senza collaudo');

SELECT * FROM finish();
ROLLBACK;
