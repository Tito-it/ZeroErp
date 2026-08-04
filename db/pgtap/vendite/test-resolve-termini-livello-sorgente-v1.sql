-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: T.2 — il livello 1 di vendite.fn_resolve_termini_pagamento
--       risolve la SORGENTE EFFETTIVA e torna raggiungibile.
--       (brief-db-termine-dal-documento-alla-commessa.md §3.2 · changeSet
--        20260803-03) + T.1 (20260803-02, le due colonne del contratto push).
--
-- 🔴 PERCHE' QUESTO FILE ESISTE, ed e' la parte da leggere prima del codice.
--    Il livello 1 sembrava vivo leggendo la funzione, e un primo test in
--    rollback lo aveva CONFERMATO — perche' costruiva l'attivita' a mano con
--    `sorgente_tipo_id = ORDINE_VENDITA`, cioe' con una forma che il pull vero
--    non produce MAI. Il pull scrive `sorgente = COMMESSA`.
--    Un livello si verifica **dal percorso che lo attraversa**, non dal codice
--    che lo dichiara.
--
--    Conseguenza sul disegno di questo file: le fixture **non inventano la
--    forma**. Si parte da attivita' REALI prodotte dal pull e si muove solo il
--    dato di dominio (il termine sul documento), lasciando intatta la forma
--    della sorgente. Il test 1 presidia proprio quella forma: se un domani il
--    pull cambiasse, e' il primo a dirlo.
-- ------------------------------------------------------------
-- Indice test (1..9):
--   1)  ⭐ invariante di forma: le attivita' dal pull portano sorgente COMMESSA
--   2)  ⭐ livello 1 dal PERCORSO REALE: il termine dell'ORDINE vince sul cliente
--   3)  livello 1 porta anche la MODALITA' quando la sorgente e' un ordine
--   4)  PREVENTIVO: porta il termine ma NON la modalita' (discesa indipendente)
--   5)  livello 2: la commessa batte il documento
--   6)  livello 4: senza nulla, default TP_1RATA
--   7)  ⚠️ sorgente polimorfa: un tipo non gestito NON esplode e non vince
--   8)  T.1: le 5 fn_list_*_da_pushare espongono le due colonne
--   9)  T.1: la colonna porta il valore del documento, non un NULL fisso
-- ------------------------------------------------------------

BEGIN;
SELECT plan(9);

-- ============================================================
-- Fixture: attivita' REALI, una per tipo di documento d'origine.
-- Nessuna costruita a mano: si selezionano quelle che il pull ha prodotto.
-- ============================================================
CREATE TEMP TABLE tmp_af AS
SELECT s.codice_interno AS tipo, min(a.id) AS attivita_id
  FROM vendite.attivita_fatturabili a
  JOIN vendite.commesse_attivita ca ON ca.id = a.commessa_attivita_id
  JOIN config.sorgenti s ON s.id = ca.sorgente_tipo_id
 GROUP BY s.codice_interno;

-- ============================================================
-- 1) ⭐ L'invariante di forma che ha ingannato tutti.
--    Se questo test diventa rosso, il pull ha cambiato comportamento e il
--    livello 1 va riletto: e' il primo campanello, non un dettaglio.
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM vendite.attivita_fatturabili a
       JOIN config.sorgenti s ON s.id = a.sorgente_tipo_id
      WHERE s.codice_interno <> 'COMMESSA'
        AND a.commessa_attivita_id IS NOT NULL),
    0,
    '1) invariante: le attivita'' prodotte dal pull portano sorgente COMMESSA');

-- ============================================================
-- 2) ⭐ IL TEST CHE CONTA — livello 1 dal percorso reale.
--    Si prende un'attivita' vera nata da un ORDINE, si mette sull'ordine un
--    termine DIVERSO da quello del cliente, e si verifica che vinca l'ordine.
--    Prima di T.2 qui usciva il termine del cliente: e' il difetto della
--    fattura 2263.
-- ============================================================
CREATE TEMP TABLE tmp_ord AS
SELECT a.id AS attivita_id, o.id AS ordine_id
  FROM tmp_af f
  JOIN vendite.attivita_fatturabili a ON a.id = f.attivita_id
  JOIN vendite.commesse_attivita ca ON ca.id = a.commessa_attivita_id
  JOIN vendite.ordini o ON o.uid::text = ca.sorgente_uid
 WHERE f.tipo = 'ORDINE_VENDITA';

UPDATE vendite.ordini
   SET termine_pagamento_id = 3, modalita_pagamento_id = 5
 WHERE id = (SELECT ordine_id FROM tmp_ord);

SELECT is(
    (SELECT termine_pagamento_id FROM vendite.fn_resolve_termini_pagamento(
        (SELECT attivita_id FROM tmp_ord))),
    3::bigint,
    '2) livello 1 dal percorso reale: vince il termine dell''ORDINE, non del cliente');

-- ============================================================
-- 3) La modalita' viaggia con lo stesso livello.
-- ============================================================
SELECT is(
    (SELECT modalita_pagamento_id FROM vendite.fn_resolve_termini_pagamento(
        (SELECT attivita_id FROM tmp_ord))),
    5,
    '3) livello 1: l''ordine porta anche la modalita'' di pagamento');

-- ============================================================
-- 4) PREVENTIVO: porta il termine, NON la modalita'.
--    I due campi scendono la catena in modo indipendente, e il default
--    esiste solo per il termine: config.modalita_pagamento non ha una riga
--    «predefinita» e sceglierne una finirebbe sulla fattura elettronica.
-- ============================================================
CREATE TEMP TABLE tmp_prev AS
SELECT a.id AS attivita_id, p.id AS preventivo_id
  FROM tmp_af f
  JOIN vendite.attivita_fatturabili a ON a.id = f.attivita_id
  JOIN vendite.commesse_attivita ca ON ca.id = a.commessa_attivita_id
  JOIN vendite.preventivi p ON p.uid::text = ca.sorgente_uid
 WHERE f.tipo = 'PREVENTIVO';

UPDATE vendite.preventivi SET termine_pagamento_id = 2
 WHERE id = (SELECT preventivo_id FROM tmp_prev);
-- il cliente non deve poter coprire il buco della modalita'
UPDATE anagrafiche.clienti SET modalita_pagamento_id = NULL
 WHERE istanza_utility_id = (
   SELECT ba.istanza_utility_id FROM vendite.attivita_fatturabili a
     JOIN anagrafiche.billing_account ba
       ON ba.id = COALESCE((SELECT parent_account_id FROM anagrafiche.billing_account WHERE id = a.billing_account_id), a.billing_account_id)
    WHERE a.id = (SELECT attivita_id FROM tmp_prev));

SELECT is(
    (SELECT termine_pagamento_id::text || '/' || COALESCE(modalita_pagamento_id::text, 'NULL')
       FROM vendite.fn_resolve_termini_pagamento((SELECT attivita_id FROM tmp_prev))),
    '2/NULL',
    '4) PREVENTIVO: porta il termine ma non la modalita'' (discesa indipendente)');

-- ============================================================
-- 5) Livello 2: la commessa e' piu' specifica del documento e vince.
--    ⚠️ Il guard di immutabilita' della chiave scatta se la commessa ha gia'
--    attivita' collegate: si usa la GUC di manutenzione, che e' il canale
--    previsto e non un aggiramento.
-- ============================================================
SET LOCAL zeroerp.maintenance_reset_lotto_draft = 'on';
UPDATE vendite.commesse SET termine_pagamento_id = 4
 WHERE id = (SELECT commessa_id FROM vendite.attivita_fatturabili
              WHERE id = (SELECT attivita_id FROM tmp_ord));
SET LOCAL zeroerp.maintenance_reset_lotto_draft = 'off';

SELECT is(
    (SELECT termine_pagamento_id FROM vendite.fn_resolve_termini_pagamento(
        (SELECT attivita_id FROM tmp_ord))),
    3::bigint,
    '5) il documento (livello 1) precede la commessa (livello 2)');

-- ============================================================
-- 6) Livello 4: tolto tutto, resta il default. Nessuna fattura senza rate.
-- ============================================================
UPDATE vendite.ordini SET termine_pagamento_id = NULL, modalita_pagamento_id = NULL
 WHERE id = (SELECT ordine_id FROM tmp_ord);
SET LOCAL zeroerp.maintenance_reset_lotto_draft = 'on';
UPDATE vendite.commesse SET termine_pagamento_id = NULL
 WHERE id = (SELECT commessa_id FROM vendite.attivita_fatturabili
              WHERE id = (SELECT attivita_id FROM tmp_ord));
SET LOCAL zeroerp.maintenance_reset_lotto_draft = 'off';
UPDATE anagrafiche.clienti SET termine_pagamento_id = NULL
 WHERE istanza_utility_id = (
   SELECT ba.istanza_utility_id FROM vendite.attivita_fatturabili a
     JOIN anagrafiche.billing_account ba
       ON ba.id = COALESCE((SELECT parent_account_id FROM anagrafiche.billing_account WHERE id = a.billing_account_id), a.billing_account_id)
    WHERE a.id = (SELECT attivita_id FROM tmp_ord));

SELECT is(
    (SELECT tp.codice_interno FROM vendite.fn_resolve_termini_pagamento(
        (SELECT attivita_id FROM tmp_ord)) r
       JOIN config.termini_pagamento tp ON tp.id = r.termine_pagamento_id),
    'TP_1RATA',
    '6) senza nulla lungo la catena resta il default TP_1RATA (D-J)');

-- ============================================================
-- 7) ⚠️ Sorgente POLIMORFA: il tipo non gestito non deve esplodere.
--    `commesse_attivita.sorgente_uid` e' TEXT e per convenzione contratti e
--    consumi vi mettono `id::text`, non un uuid; `attivita_fatturabili.
--    sorgente_uid` e' invece UUID. Assegnare senza filtrare farebbe fallire
--    il cast. Il DDT e' il tipo non gestito disponibile sul dato reale.
-- ============================================================
SELECT lives_ok(
    $$ SELECT * FROM vendite.fn_resolve_termini_pagamento(
         (SELECT attivita_id FROM tmp_af WHERE tipo = 'DDT_VENDITA')) $$,
    '7) sorgente non gestita dal livello 1: risolve senza errore di cast');

-- ============================================================
-- 8-9) T.1 — il contratto delle fn di push.
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite' AND p.proname LIKE 'fn\_list\_%\_da\_pushare'
        AND pg_get_function_result(p.oid) LIKE '%termine_pagamento_id%'
        AND pg_get_function_result(p.oid) LIKE '%modalita_pagamento_id%'),
    5,
    '8) tutte e cinque le fn_list_*_da_pushare espongono le due colonne');

-- ⚠️ Serve un ordine ANCORA DA PUSHARE, non quello dietro l'attivita' del
--    test 2: quello e' gia' stato pushato e la fn lo esclude (0 righe), come
--    deve. E' la stessa famiglia di errore che questo file racconta in testa —
--    usare una riga in uno stato che il percorso reale non ha.
CREATE TEMP TABLE tmp_ord_push AS
SELECT min(ordine_id) AS ordine_id
  FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL, NULL);

UPDATE vendite.ordini SET termine_pagamento_id = 3, modalita_pagamento_id = 5
 WHERE id = (SELECT ordine_id FROM tmp_ord_push);

SELECT is(
    (SELECT termine_pagamento_id FROM vendite.fn_list_ordini_da_pushare(
        NULL, NULL, NULL, (SELECT ordine_id FROM tmp_ord_push)) LIMIT 1),
    3::bigint,
    '9) la colonna porta il valore del documento, non un NULL fisso');

SELECT * FROM finish();
ROLLBACK;
