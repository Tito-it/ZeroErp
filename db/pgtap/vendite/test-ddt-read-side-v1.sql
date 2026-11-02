-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine (in bozza); resta scritta a mano l'emissione del test 11, che e' l'asserzione.
-- rev 2026-10-25 (brief-modello-documento-vendita §7, giro 5): lo stato si cambia solo dal verbo
--   (la porta rifiuta l'UPDATE diretto) e «emetti» si nasconde a chi non ha emetti_ddt. Il file
--   prova la lettura, non il permesso: l'operatore riceve emetti_ddt, e il test 11 emette col
--   verbo vendite.fn_cambia_stato_ddt. Attese invariate.
-- pgTAP test per Zero ERP
-- Test: read-side DDT (brief §13)
--   vendite.vw_ddt_lista + script.fn_available_actions_ddt + seed lista ui
-- ------------------------------------------------------------
-- Indice test (1..15):
--  1) vista vendite.vw_ddt_lista presente
--  2) funzione script.fn_available_actions_ddt presente
--  3) ui.lista_definizione 'vendite.ddt' -> vw_ddt_lista
--  4) ui.lista_colonna: colonne DDT seedate (>= 15)
--  5) riferimenti minimi disponibili
--  6) vw_ddt_lista: DDT presente in stato DRAFT
--  7) vw_ddt_lista: destinatario_denominazione valorizzato
--  8) vw_ddt_lista: sorgente ORDINE_VENDITA + ordine_origine_numero corretto
--  9) fn_available_actions_ddt DRAFT: azioni emetti + annulla presenti
-- 10) fn_available_actions_ddt DRAFT: can_edit_testata=true, stato_codice=DRAFT
-- 11) emissione DRAFT->EMESSO consentita
-- 12) fn_available_actions_ddt EMESSO: spedisci presente, emetti assente
-- 13) fn_available_actions_ddt EMESSO: can_edit_testata=true (trasporto, tracciamento, note), ma
--     identita', causale e cliente fra i non modificabili (rev 2026-10-10, D-0/D-10)
-- 14) vw_ddt_lista: numero valorizzato dopo EMESSO
-- 15) fn_available_actions_ddt su DDT inesistente -> NULL
-- 16) nessun arco MANUALE attivo punta a RESO (regola blindata sulla matrice)
-- 17) CONSEGNATO->RESO resta attivo ma manuale:false (flip automatico preservato)
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

SELECT plan(17);

-- ============================================================
-- 1-2) Oggetti presenti
-- ============================================================
SELECT ok(
  EXISTS (SELECT 1 FROM pg_views WHERE schemaname='vendite' AND viewname='vw_ddt_lista'),
  '1) vista vendite.vw_ddt_lista presente'
);
SELECT ok(
  EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
           WHERE n.nspname='script' AND p.proname='fn_available_actions_ddt'),
  '2) funzione script.fn_available_actions_ddt presente'
);

-- ============================================================
-- 3-4) Seed lista ui
-- ============================================================
SELECT is(
  (SELECT vista_sql FROM ui.lista_definizione WHERE codice='vendite.ddt'),
  'vw_ddt_lista', '3) ui.lista_definizione vendite.ddt -> vw_ddt_lista'
);
SELECT cmp_ok(
  (SELECT count(*)::int FROM ui.lista_colonna
    WHERE lista_id = (SELECT id FROM ui.lista_definizione WHERE codice='vendite.ddt')),
  '>=', 15, '4) ui.lista_colonna: colonne DDT seedate (>=15)'
);

-- ============================================================
-- Riferimenti + fixture ordine (per generare un DDT reale)
-- ============================================================
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti). Prima BA, ruolo, emittente e articolo si pescavano col
--   LIMIT 1: su zeroerp_ci erano NULL e l'ordine moriva sul NOT NULL di
--   soggetto_ruolo_id. Ora un'azienda nuova col suo operatore (contesto aperto
--   su di lui), il cliente legato a lei (dbops.fn_pgtap_crea_mondo_cliente) e un
--   articolo merce non gestito (il test non misura il magazzino). Dal DB si
--   legge solo il catalogo di seed. Modello: test-ddt-magazzino-testata-v1.
CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP ddt read-side');
-- rev 2026-10-25 (giro 5): si prova la lettura, non il permesso — l'operatore
--   in sessione riceve emetti_ddt (azione «emetti» e verbo del test 11).
DO $az$ BEGIN
  PERFORM dbops.fn_pgtap_concedi_azione(NULLIF(current_setting('app.current_user_id', true), '')::integer, 'emetti_ddt');
END $az$;

CREATE TEMP TABLE tmp_refs AS
SELECT
  m.billing_account_id,
  m.cliente_soggetto_ruolo_id AS soggetto_ruolo_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-DDT-READSIDE', false) AS articolo_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  m.emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno='CONFERMATO' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ddt s
    WHERE s.codice_interno='EMESSO' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1) AS stato_ddt_emesso_id
FROM _m m;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND soggetto_ruolo_id IS NOT NULL
      AND articolo_id IS NOT NULL AND iva_id IS NOT NULL
      AND emittente_fiscale_id IS NOT NULL AND stato_ord_conf_id IS NOT NULL
   FROM tmp_refs),
  '5) riferimenti minimi disponibili'
);

-- La bolla in bozza dal builder: ordine del cliente del file (trigger
-- SPEDITO, una riga di 10 a 25), evaso tutto. Causale VENDITA e CON li scrive
-- gia' il builder: in bozza la lista non li guarda, e sono cio' che
-- l'emissione del test 11 pretende (il prezzo 25 lo eredita via fulfillment).
CREATE TEMP TABLE tmp_ddt AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgtap_ddt_readside', 'DRAFT',
         p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs),
         p_articolo_id          => (SELECT articolo_id FROM tmp_refs),
         p_fatturazione_trigger => 'SPEDITO');

-- Il numero dell'ordine, per il test 8: letto in un'istruzione a parte.
CREATE TEMP TABLE tmp_ord AS
SELECT o.numero
  FROM vendite.ordini o
 WHERE o.id = (SELECT ordine_id FROM tmp_ddt);

-- ============================================================
-- 6-8) vw_ddt_lista
-- ============================================================
SELECT is(
  (SELECT stato_codice_interno FROM vendite.vw_ddt_lista WHERE id=(SELECT ddt_id FROM tmp_ddt)),
  'DRAFT', '6) vw_ddt_lista: DDT in stato DRAFT'
);
SELECT ok(
  (SELECT destinatario_denominazione IS NOT NULL
     FROM vendite.vw_ddt_lista WHERE id=(SELECT ddt_id FROM tmp_ddt)),
  '7) vw_ddt_lista: destinatario_denominazione valorizzato'
);
SELECT ok(
  (SELECT sorgente_codice_interno = 'ORDINE_VENDITA'
      AND ordine_origine_numero = (SELECT numero FROM tmp_ord)
     FROM vendite.vw_ddt_lista WHERE id=(SELECT ddt_id FROM tmp_ddt)),
  '8) vw_ddt_lista: sorgente ORDINE_VENDITA + ordine_origine_numero corretto'
);

-- ============================================================
-- 9-10) fn_available_actions_ddt in DRAFT
-- ============================================================
CREATE TEMP TABLE tmp_act_draft AS
SELECT script.fn_available_actions_ddt((SELECT ddt_id FROM tmp_ddt)) AS a;

SELECT ok(
  (SELECT (a->'available_actions') @> '[{"key":"emetti"}]'::jsonb
      AND (a->'available_actions') @> '[{"key":"annulla"}]'::jsonb
     FROM tmp_act_draft),
  '9) fn_available_actions_ddt DRAFT: azioni emetti + annulla presenti'
);
SELECT ok(
  (SELECT (a->>'can_edit_testata')::boolean IS TRUE
      AND a->>'stato_codice' = 'DRAFT'
     FROM tmp_act_draft),
  '10) fn_available_actions_ddt DRAFT: can_edit_testata=true, stato_codice=DRAFT'
);

-- ============================================================
-- 11) Emissione DRAFT->EMESSO
-- ============================================================
-- La transizione e' il caso: resta scritta qui, sotto i guard veri
-- (causale e CON dal builder). rev 2026-10-25 (giro 5): dal verbo, non
-- dall'UPDATE diretto che la porta ora rifiuta.
SELECT lives_ok(
  format($q$SELECT * FROM vendite.fn_cambia_stato_ddt(%s, 'EMESSO')$q$,
         (SELECT ddt_id FROM tmp_ddt)),
  '11) emissione DRAFT->EMESSO consentita'
);

-- ============================================================
-- 12-14) Dopo EMESSO
-- ============================================================
CREATE TEMP TABLE tmp_act_emesso AS
SELECT script.fn_available_actions_ddt((SELECT ddt_id FROM tmp_ddt)) AS a;

SELECT ok(
  (SELECT (a->'available_actions') @> '[{"key":"spedisci"}]'::jsonb
      AND NOT ((a->'available_actions') @> '[{"key":"emetti"}]'::jsonb)
     FROM tmp_act_emesso),
  '12) fn_available_actions_ddt EMESSO: spedisci presente, emetti assente'
);
-- ⚠️ rev 2026-10-10 (brief-db-testata-dopo-emissione, fase 2, D-0/D-10): fino
--   a quel giorno il test pretendeva can_edit_testata = false su una bolla
--   emessa. Ora la capability legge la testata dal montaggio del lock: in
--   EMESSO trasporto, tracciamento e note si cambiano ancora, quindi la
--   testata e' modificabile; che la bolla non si RISCRIVA lo dice
--   non_editable_fields, e lo si prova qui.
SELECT ok(
  (SELECT (a->>'can_edit_testata')::boolean IS TRUE
      AND (a->'non_editable_fields') @> '["data","valuta_id","causale_trasporto_id","billing_account_id","numero"]'::jsonb
      AND NOT ((a->'non_editable_fields') @> '["tracking_code"]'::jsonb)
     FROM tmp_act_emesso),
  '13) fn_available_actions_ddt EMESSO: testata modificabile (tracciamento, trasporto, note), data, valuta, causale, cliente e numero fermi'
);
SELECT ok(
  (SELECT numero IS NOT NULL AND btrim(numero) <> ''
     FROM vendite.vw_ddt_lista WHERE id=(SELECT ddt_id FROM tmp_ddt)),
  '14) vw_ddt_lista: numero valorizzato dopo EMESSO'
);

-- ============================================================
-- 15) DDT inesistente -> NULL
-- ============================================================
SELECT ok(
  script.fn_available_actions_ddt(999999999) IS NULL,
  '15) fn_available_actions_ddt su DDT inesistente -> NULL'
);

-- ============================================================
-- 16-17) RESO e' uno stato DERIVATO, non un pulsante.
--   brief-db-rimuovere-azione-segna-reso-ddt (2026-07-25).
--   Il flip DDT->RESO lo fa SOLO fn_conferma_reso su reso totale; il
--   ri-flip RESO->CONSEGNATO solo fn_annulla_reso. Nessun arco MANUALE
--   deve puntare a RESO, altrimenti torna il pulsante «Segna reso».
--   Regola blindata sulla matrice, indipendente dai dati: cattura sia la
--   regressione da re-seed (righe 6/7 riportate manuali) sia un futuro seed
--   sbagliato.
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM config.transizioni_stati_ddt t
     JOIN config.stati_doc_ddt sa ON sa.id = t.stato_a_id
    WHERE sa.codice_interno = 'RESO'
      AND t.attivo IS TRUE
      AND COALESCE((t.meta->>'manuale')::boolean, true) IS TRUE),
  0,
  '16) nessun arco MANUALE attivo punta a RESO (stato derivato, non pulsante)');

-- L'arco CONSEGNATO->RESO deve restare ATTIVO (manuale:false): e' quello che
-- il trigger trgfn_ddt_guard_transizione valida sull'UPDATE interno di
-- fn_conferma_reso. Disattivarlo romperebbe il flip automatico
-- (E_STATO_DDT_TRANSIZIONE_NON_VALIDA).
SELECT ok(
  EXISTS (
    SELECT 1
      FROM config.transizioni_stati_ddt t
      JOIN config.stati_doc_ddt sd ON sd.id = t.stato_da_id
      JOIN config.stati_doc_ddt sa ON sa.id = t.stato_a_id
     WHERE sd.codice_interno = 'CONSEGNATO'
       AND sa.codice_interno = 'RESO'
       AND t.attivo IS TRUE
       AND COALESCE((t.meta->>'manuale')::boolean, true) IS FALSE
  ),
  '17) CONSEGNATO->RESO resta attivo ma manuale:false (flip automatico preservato)');

SELECT * FROM finish();
ROLLBACK;
