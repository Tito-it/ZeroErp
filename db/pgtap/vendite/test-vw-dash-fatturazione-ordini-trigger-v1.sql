-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
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
-- Riferimenti + helper
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  -- ⛔ rev 2026-10-13: BA, ruolo del cliente ed emittente dal mondo costruito;
  --   l'articolo si costruisce (merce, non gestito: il test non misura il magazzino).
  (SELECT billing_account_id FROM _m)                                    AS billing_account_id,
  (SELECT cliente_soggetto_ruolo_id FROM _m)                             AS soggetto_ruolo_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-DASH-TRIGGER', false)                  AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)              AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT emittente_fiscale_id FROM _m)                                  AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno='CONFERMATO' AND s.attivo LIMIT 1) AS stato_ord_conf_id;

-- Ordine CONFERMATO (stato) con una riga, trigger parametrico, nessun push.
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT, prende la riga, poi passa a CONFERMATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le righe non si scrivono piu' (20261008-90).
CREATE OR REPLACE FUNCTION pg_temp.mk_ordine(p_trigger varchar)
RETURNS bigint AS $$
DECLARE r RECORD; v_ord bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id,
          (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE),
          r.valuta_id,
          DATE '2026-07-15', p_trigger, r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_dash_ord_trigger'))
  RETURNING id INTO v_ord;
  -- trgfn_ordini_normalize eredita il trigger dal BA solo su INSERT: va rimesso.
  UPDATE vendite.ordini SET fatturazione_trigger = p_trigger WHERE id = v_ord;
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ord, 1, r.articolo_id, 'Riga trigger-aware', 10, 10, 25, r.iva_id, true, false,
          jsonb_build_object('test_scope','pgtap_dash_ord_trigger'));
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', v_ord, 'CONFERMATO');
  RETURN v_ord;
END $$ LANGUAGE plpgsql;

CREATE TEMP TABLE tmp_ddt_trg  AS SELECT pg_temp.mk_ordine('CONSEGNATO') AS ordine_id;
CREATE TEMP TABLE tmp_conf_trg AS SELECT pg_temp.mk_ordine('CONFERMATO') AS ordine_id;

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
