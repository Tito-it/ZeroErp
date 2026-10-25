-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): i due ordini CONFERMATI da dbops.fn_pgtap_crea_ordine_con_righe (10 x 25, data 2026-07-15, trigger CONSEGNATO / CONFERMATO scritto in bozza), ritirato l'helper pg_temp.mk_ordine e i riferimenti rimasti senza lettori.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2d): l'area della dashboard e' il codice della sorgente (ORDINE_VENDITA).
-- pgTAP test per Zero ERP
-- Test: vw_dash_fatturazione_ordini trigger-aware (IN_ATTESA_DDT) — step 7,
--       brief-db-fatturazione-ddt-resi §4b / DL-20.
-- (changeset 20260718-12 + seed motivi_fermo IN_ATTESA_DDT)
-- ------------------------------------------------------------
-- Indice test (1..5):
--   1) security_invoker=on sulla vista (regressione V-1)
--   2) ordine trigger CONSEGNATO senza push -> IN_ATTESA_DDT (non e' lui a
--      pushare: il falso positivo PUSH_NON_ESEGUITO perpetuo sparisce)
--   3) lo stesso ordine NON e' nel backlog (IN_ATTESA_DDT e' FISIOLOGICO:
--      la regola di classe lo esclude da sola, nessun caso speciale)
--   4) ordine trigger CONFERMATO senza push -> PUSH_NON_ESEGUITO (invariato)
--   5) lo stesso ordine E' nel backlog, classe RECUPERABILE (invariato)
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
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (in CI l'utente 1 non esiste;
--   anagrafiche e articoli sono vuoti). fn_pgtap_crea_mondo_cliente fa azienda,
--   operatore, cliente BA legato a quell'azienda e APRE il contesto da se'.
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP dash trigger');
-- Il mondo ha gia' aperto il contesto sul suo operatore: la riga lo
--   dichiara (e il guardrail del preambolo la cerca).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;

SELECT plan(5);

-- ============================================================
-- Riferimenti
-- ============================================================
-- ⛔ rev 2026-10-13: BA dal mondo costruito; l'articolo si costruisce (merce,
--   non gestito: il test non misura il magazzino).
CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT billing_account_id FROM _m)                                    AS billing_account_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-DASH-TRIGGER', false)              AS articolo_id;

-- Ordine CONFERMATO (stato) con una riga 10 x 25, trigger del caso scritto in
--   bozza (il normalize lo eredita dal BA solo all'INSERT), nessun push.
CREATE TEMP TABLE tmp_ddt_trg AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('dash_ord_trigger consegnato', 'CONFERMATO',
    p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
    p_quantita => 10, p_prezzo => 25, p_articolo_id => (SELECT articolo_id FROM tmp_refs),
    p_fatturazione_trigger => 'CONSEGNATO', p_data_ordine => DATE '2026-07-15');
CREATE TEMP TABLE tmp_conf_trg AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('dash_ord_trigger confermato', 'CONFERMATO',
    p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
    p_quantita => 10, p_prezzo => 25, p_articolo_id => (SELECT articolo_id FROM tmp_refs),
    p_fatturazione_trigger => 'CONFERMATO', p_data_ordine => DATE '2026-07-15');

-- ============================================================
-- ASSERZIONI
-- ============================================================
SELECT ok(
  (SELECT 'security_invoker=on' = ANY(c.reloptions)
     FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='vendite' AND c.relname='vw_dash_fatturazione_ordini'),
  '1) security_invoker=on ri-specificato su vw_dash_fatturazione_ordini (no bypass RLS)');

-- 2) trigger CONSEGNATO: il push spetta ai DDT -> IN_ATTESA_DDT
SELECT is(
  (SELECT motivo_fermo FROM vendite.vw_dash_fatturazione_ordini
    WHERE documento_id=(SELECT ordine_id FROM tmp_ddt_trg)),
  'IN_ATTESA_DDT'::varchar,
  '2) ordine trigger CONSEGNATO senza push -> IN_ATTESA_DDT (il falso positivo sparisce)');

-- 3) FISIOLOGICO -> fuori dal backlog per la regola di classe, da solo
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.vw_dash_backlog_documenti
    WHERE area='ORDINE_VENDITA' AND documento_id=(SELECT ordine_id FROM tmp_ddt_trg)),
  0, '3) IN_ATTESA_DDT e'' FISIOLOGICO: l''ordine sparisce dal backlog (resta nel serbatoio)');

-- 4-5) trigger CONFERMATO: tutto come prima
SELECT is(
  (SELECT motivo_fermo FROM vendite.vw_dash_fatturazione_ordini
    WHERE documento_id=(SELECT ordine_id FROM tmp_conf_trg)),
  'PUSH_NON_ESEGUITO'::varchar,
  '4) ordine trigger CONFERMATO senza push -> PUSH_NON_ESEGUITO (invariato)');

SELECT is(
  (SELECT b.classe FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area='ORDINE_VENDITA' AND b.documento_id=(SELECT ordine_id FROM tmp_conf_trg)),
  'RECUPERABILE'::varchar,
  '5) e resta nel backlog come RECUPERABILE (invariato)');

SELECT * FROM finish();
ROLLBACK;
