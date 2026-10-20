-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2d): l'area della dashboard e' il codice della sorgente (DDT_VENDITA).
-- pgTAP test per Zero ERP
-- Test: vw_dash_fatturazione_ddt — resolver DDT, sesta area della union
--       — step 6, brief-db-fatturazione-ddt-resi §4a / DL-21 emendato.
-- (changeset 20260718-07/-08)
-- ------------------------------------------------------------
-- Indice test (1..8):
--   1) security_invoker=on su resolver e union (regressione V-1: la reloption
--      non e' visibile in pg_get_viewdef e un REPLACE la azzera in silenzio)
--   2) POPOLAZIONE: DDT di ordine trigger CONSEGNATO -> DENTRO (e' lui il
--      veicolo di fatturazione)
--   3) POPOLAZIONE: DDT di ordine trigger CONFERMATO -> FUORI (fattura
--      l'ordine: XOR). Chiude falso positivo + doppio conteggio del valore
--   4) POPOLAZIONE: causale non fatturabile -> FUORI (solo trasporto, DL-28)
--   5) motivo IN_TRANSITO: stato PRIMA del trigger = viaggio in corso, non
--      ritardo (e' FISIOLOGICO, quindi NON finisce nel backlog)
--   6) motivo PUSH_NON_ESEGUITO: dallo stato-trigger in poi senza push
--   7) valore_totale calcolato col prezzo EREDITATO dall'ordine (la riga DDT
--      non ha prezzo proprio): 10 x 25 = 250
--   8) il ramo arriva nella union vw_dash_fatturazione_documenti come 'DDT'
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
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP dash DDT');
-- Il mondo ha gia' aperto il contesto sul suo operatore: la riga lo
--   dichiara (e il guardrail del preambolo la cerca).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;

SELECT plan(8);

-- ============================================================
-- Riferimenti + helper
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  -- ⛔ rev 2026-10-13: BA, ruolo del cliente ed emittente dal mondo costruito;
  --   l'articolo si costruisce (merce, non gestito: il test non misura il magazzino).
  (SELECT billing_account_id FROM _m)                                    AS billing_account_id,
  (SELECT cliente_soggetto_ruolo_id FROM _m)                             AS soggetto_ruolo_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-DASH-DDT', false)                  AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)              AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT emittente_fiscale_id FROM _m)                                  AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno='CONFERMATO' AND s.attivo LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='EMESSO' AND s.attivo LIMIT 1)     AS stato_ddt_emesso_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='SPEDITO' AND s.attivo LIMIT 1)    AS stato_ddt_spedito_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='CONSEGNATO' AND s.attivo LIMIT 1) AS stato_ddt_consegnato_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' LIMIT 1)      AS causale_vendita_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='CAMPIONATURA' LIMIT 1) AS causale_campioni_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')     AS tipo_ind_con_id;

-- Ordine (qta 10, prezzo 25) -> DDT portato allo stato richiesto.
-- La riga DDT resta SENZA prezzo proprio: il resolver deve ereditarlo
-- dall'ordine via fulfillment, come fanno lister e gate.
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT, prende la riga, poi passa a CONFERMATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le righe non si scrivono piu' (20261008-90).
CREATE OR REPLACE FUNCTION pg_temp.mk_caso(p_trigger varchar, p_causale bigint, p_stato bigint)
RETURNS bigint AS $$
DECLARE r RECORD; v_ord bigint; v_ddt bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id,
          (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE),
          r.valuta_id,
          DATE '2026-07-15', p_trigger, r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_dash_ddt'))
  RETURNING id INTO v_ord;
  -- trgfn_ordini_normalize eredita il trigger dal BA solo su INSERT: va rimesso.
  UPDATE vendite.ordini SET fatturazione_trigger = p_trigger WHERE id = v_ord;
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ord, 1, r.articolo_id, 'Riga dash', 10, 10, 25, r.iva_id, true, false,
          jsonb_build_object('test_scope','pgtap_dash_ddt'));
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', v_ord, 'CONFERMATO');
  v_ddt := vendite.fn_genera_ddt_da_ordine(v_ord);
  INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
  VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
  UPDATE vendite.ddt SET causale_trasporto_id = p_causale WHERE id = v_ddt;
  UPDATE vendite.ddt_righe dr SET prezzo_unitario = NULL WHERE dr.ddt_id = v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_emesso_id WHERE id=v_ddt;
  IF p_stato <> r.stato_ddt_emesso_id THEN
    UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_spedito_id WHERE id=v_ddt;
    IF p_stato <> r.stato_ddt_spedito_id THEN
      UPDATE vendite.ddt SET stato_doc_ddt_id=p_stato WHERE id=v_ddt;
    END IF;
  END IF;
  RETURN v_ddt;
END $$ LANGUAGE plpgsql;

-- ============================================================
-- FIXTURE
-- ============================================================
-- A: trigger CONSEGNATO, DDT CONSEGNATO, VENDITA -> dentro, PUSH_NON_ESEGUITO
CREATE TEMP TABLE tmp_a AS
SELECT pg_temp.mk_caso('CONSEGNATO', (SELECT causale_vendita_id FROM tmp_refs),
                       (SELECT stato_ddt_consegnato_id FROM tmp_refs)) AS ddt_id;
-- B: trigger CONFERMATO -> fuori (fattura l'ordine)
CREATE TEMP TABLE tmp_b AS
SELECT pg_temp.mk_caso('CONFERMATO', (SELECT causale_vendita_id FROM tmp_refs),
                       (SELECT stato_ddt_consegnato_id FROM tmp_refs)) AS ddt_id;
-- C: causale CAMPIONATURA -> fuori (solo trasporto)
CREATE TEMP TABLE tmp_c AS
SELECT pg_temp.mk_caso('CONSEGNATO', (SELECT causale_campioni_id FROM tmp_refs),
                       (SELECT stato_ddt_consegnato_id FROM tmp_refs)) AS ddt_id;
-- D: trigger CONSEGNATO ma DDT ancora SPEDITO -> IN_TRANSITO (in viaggio)
CREATE TEMP TABLE tmp_d AS
SELECT pg_temp.mk_caso('CONSEGNATO', (SELECT causale_vendita_id FROM tmp_refs),
                       (SELECT stato_ddt_spedito_id FROM tmp_refs)) AS ddt_id;

-- ============================================================
-- ASSERZIONI
-- ============================================================
-- 1) security_invoker su entrambe (resolver + union)
SELECT ok(
  (SELECT bool_and('security_invoker=on' = ANY(c.reloptions))
     FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='vendite'
      AND c.relname IN ('vw_dash_fatturazione_ddt','vw_dash_fatturazione_documenti')),
  '1) security_invoker=on su resolver DDT e union (no bypass RLS)');

-- 2-4) POPOLAZIONE: dentro chi fattura, fuori chi no
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.vw_dash_fatturazione_ddt WHERE documento_id=(SELECT ddt_id FROM tmp_a)),
  1, '2) DDT di ordine trigger CONSEGNATO -> nel resolver (e'' lui a fatturare)');

SELECT is(
  (SELECT COUNT(*)::int FROM vendite.vw_dash_fatturazione_ddt WHERE documento_id=(SELECT ddt_id FROM tmp_b)),
  0, '3) DDT di ordine trigger CONFERMATO -> FUORI (fattura l''ordine: XOR, niente doppio conteggio)');

SELECT is(
  (SELECT COUNT(*)::int FROM vendite.vw_dash_fatturazione_ddt WHERE documento_id=(SELECT ddt_id FROM tmp_c)),
  0, '4) DDT con causale non fatturabile -> FUORI (solo trasporto, DL-28)');

-- 5-6) motivo_fermo trigger-aware: "in viaggio" != "in ritardo"
SELECT is(
  (SELECT motivo_fermo FROM vendite.vw_dash_fatturazione_ddt WHERE documento_id=(SELECT ddt_id FROM tmp_d)),
  'IN_TRANSITO'::varchar,
  '5) stato PRIMA del trigger -> IN_TRANSITO (viaggio in corso, FISIOLOGICO: fuori dal backlog)');

SELECT is(
  (SELECT motivo_fermo FROM vendite.vw_dash_fatturazione_ddt WHERE documento_id=(SELECT ddt_id FROM tmp_a)),
  'PUSH_NON_ESEGUITO'::varchar,
  '6) dallo stato-trigger in poi senza push -> PUSH_NON_ESEGUITO (RECUPERABILE)');

-- 7) valore col prezzo ereditato dall'ordine (riga DDT senza prezzo proprio)
SELECT is(
  (SELECT valore_totale FROM vendite.vw_dash_fatturazione_ddt WHERE documento_id=(SELECT ddt_id FROM tmp_a)),
  250::numeric,
  '7) valore_totale = 10 x 25 col prezzo EREDITATO dall''ordine (riga DDT senza prezzo proprio)');

-- 8) il ramo arriva nella union
SELECT is(
  (SELECT area FROM vendite.vw_dash_fatturazione_documenti
    WHERE documento_id=(SELECT ddt_id FROM tmp_a) AND area='DDT_VENDITA'),
  'DDT_VENDITA'::varchar,
  '8) il ramo DDT arriva in vw_dash_fatturazione_documenti (le due lenti lo ereditano)');

SELECT * FROM finish();
ROLLBACK;
