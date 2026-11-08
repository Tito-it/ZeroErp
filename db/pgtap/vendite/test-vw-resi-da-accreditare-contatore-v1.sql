-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-26 (brief-modello-documento-vendita §14, giro 10): la commessa passa a PRONTA_FATTURAZIONE dal verbo vendite.fn_cambia_stato_commessa, che ora chiede l'azione cambia_stato_commessa: il test prova la vista, non il permesso, e la concede all'utente del contesto (dbops.fn_pgtap_concedi_azione). Attese invariate.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): i resi dal builder dbops.fn_pgtap_crea_reso (pg_temp.mk_reso ritirata; quello sulla riga a mano con p_ddt_riga_id, la riga d'ordine resta NULL perche' non c'e' legame; i due di P4 sono due resi distinti sulla stessa riga, come prima); nulla della strada del reso resta scritto a mano.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine (le due spedizioni del P6 con p_qta_da_evadere, poi p_ordine_id); restano scritti a mano la riga aggiunta alla bolla in bozza (il caso del 9) e i resi (giro 2).
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: vw_resi_da_accreditare nella forma §3c — popolata dalla differenza
--       NEGATIVA del contatore, tipo reso degradato a etichetta — step 4,
--       brief-db-fatturazione-ddt-resi §3c/§9-4.
-- (changeset 20260718-01; riancorata alla PARTITA dal 20260817-09)
-- ------------------------------------------------------------
-- Indice test (1..10):
--   1) security_invoker=on sulla vista (regressione V-1: reloption azzerata in
--      silenzio da un CREATE OR REPLACE senza WITH -> bypass RLS)
--   2) P1 reso MAI fatturato -> conto in pari o a credito -> ESCE (chiude 1b:
--      oggi resterebbe in coda per sempre)
--   3) P2 reso su merce fatturata -> accredito dovuto 3
--   4) P2 etichetta DOVUTA (tipo a credito)
--   5) P2 il conto e' esposto (tenuti 7, fatturati 10): la coda dice cosa e'
--      successo, non cosa fare (§7)
--   6) P3 ri-consegna su merce gia' fatturata -> IN CODA, etichetta FACOLTATIVA
--      (oggi invisibile: riapre_residuo=false la tagliava)
--   7-8) P4 distribuzione greedy tra due righe di reso della stessa partita:
--      accredito 1 -> la prima lo prende tutto, alla seconda non resta nulla
--   9) ⭐ P5 reso su merce SENZA origine ordine -> accredito calcolabile e
--      ordine_riga_id NULL (il buco che la slice S4 chiude)
--  10) ⭐ P6 una riga d'ordine, DUE spedizioni: la finestra partiziona per
--      spedizione, non per riga d'ordine — 4 e 0, non 1 e 0
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
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti): azienda + operatore + cliente BA, e il builder apre
--   da se' il contesto su quell'operatore. Niente utente 1 inchiodato.
CREATE TEMP TABLE tmp_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP contatore resi');
-- Il mondo ha gia' aperto il contesto sul suo operatore: la riga lo
--   dichiara (e il guardrail del preambolo la cerca).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_mondo)); END $ctx$;

SELECT plan(10);

-- ============================================================
-- Riferimenti + helper (stessa fixture di
-- test-fn-list-ddt-da-pushare-contatore-v1)
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  -- ⛔ rev 2026-10-13: BA, utility, istanza e ruolo del cliente sono quelli del
  --   mondo costruito (prima: il primo BA del database, che da zero non c'e').
  m.billing_account_id                                                   AS billing_account_id,
  m.utility_id                                                           AS utility_id,
  m.istanza_utility_id                                                   AS istanza_utility_id,
  -- ⛔ rev 2026-10-13: l'articolo si COSTRUISCE (merce non solo-componente, non
  --   gestito: il test non misura il magazzino) — da zero il catalogo ha solo ONERE_*.
  dbops.fn_pgtap_crea_articolo('PGTAP-CONT-RESI', false)                 AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA' AND s.attivo LIMIT 1)        AS sorgente_root_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id
FROM tmp_mondo m;

-- Le partite nascono dal builder della bolla da ordine: cliente del mondo,
-- articolo del file, riga da 10 a 25, trigger CONSEGNATO, causale VENDITA (la
-- sola fatturabile: tiene la bolla eleggibile al push).

-- Helper (test 9): riga aggiunta A MANO a un DDT, senza fulfillment. E' merce
-- che esce e che, fino al 2026-08-17, non apparteneva a nessuna partita.
-- ⚠️ Solo su una bolla in BOZZA (rev 2026-09-22): fuori bozza le righe non si
--   scrivono (trgfn_doc_righe_lock_fuori_bozza).
CREATE OR REPLACE FUNCTION pg_temp.mk_riga_manuale(p_ddt bigint, p_qta numeric)
RETURNS bigint AS $$
DECLARE r RECORD; v_id bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (p_ddt, 900, r.articolo_id, 'Riga aggiunta a mano', p_qta, p_qta, 25, r.iva_id,
          true, false, jsonb_build_object('test_scope','pgtap_accrediti'))
  RETURNING id INTO v_id;
  RETURN v_id;
END $$ LANGUAGE plpgsql;

CREATE TEMP TABLE tmp_com AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa => 'AUTO', p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false, p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01', p_competenza_al => DATE '2026-07-31',
  p_meta => '{}'::jsonb, p_force_new => true) AS commessa_id;
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_com),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs),
  -- ROOT: sorgente COMMESSA (key_selector='id') con uid = id della commessa
  -- stessa. La riga esiste per costruzione, quindi passa il guard sorgente
  -- polimorfa su entrambi i fronti: formato (id::text) ed esistenza nel
  -- target. fn_emit pretende solo che una ROOT esista, non ne dereferenzia
  -- il tipo. rev 2026-07-27 (bonifica: prima era una stringa inventata su
  -- sorgente PREVENTIVO, illegale dal guard del 2026-07-18).
  p_sorgente_chiave => (SELECT commessa_id FROM tmp_com)::text,
  p_sorgente_riga => NULL, p_meta => '{}'::jsonb);

CREATE OR REPLACE FUNCTION pg_temp.mk_af(p_segment varchar, p_qta numeric)
RETURNS void AS $$
DECLARE r RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_com),
    -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
    -- La provenienza e' il documento che la chiave nomina (come nel push).
    p_sorgente_tipo_id => (SELECT k.sorgente_tipo_id FROM dbops.fn_pgtap_provenienza_da_chiave(p_segment) k),
    p_sorgente_chiave => (SELECT k.sorgente_chiave FROM dbops.fn_pgtap_provenienza_da_chiave(p_segment) k),
    p_sorgente_riga => (SELECT k.sorgente_riga FROM dbops.fn_pgtap_provenienza_da_chiave(p_segment) k),
    p_segment_key => p_segment,
    p_articolo_id => r.articolo_id, p_istanza_utility_id => r.istanza_utility_id,
    p_data_attivita => DATE '2026-07-15', p_uom_id => r.uom_id, p_quantita => p_qta,
    p_competenza_mese => DATE '2026-07-01', p_competenza_dal => DATE '2026-07-01', p_competenza_al => DATE '2026-07-31',
    p_prezzo_snapshot => 10.0, p_prezzo_base_snapshot => NULL, p_origine_prezzo => NULL,
    p_tipo_variazione_applicata => NULL, p_valore_variazione_applicata => NULL,
    p_promo_id => NULL, p_contratto_id => NULL, p_categoria_cliente_id_snapshot => NULL, p_classe_utenza_id_snapshot => NULL,
    p_tipo_doc_fiscale_id => r.tipo_doc_fiscale_id, p_stato_approvazione => 'APPROVATA', p_stato_emissione => 'NON_EMESSA',
    p_tipo_movimento => 'NORMALE', p_meta => '{}'::jsonb);
END $$ LANGUAGE plpgsql;

-- ============================================================
-- FIXTURE (il contatore e' set-based: l'ordine di creazione non conta,
-- contano le somme)
--   P1  reso 3, NESSUNA fattura      -> tenuti 7, fatt 0  -> diff +7 -> esce
--   P2  reso 3 a credito, fattura 10 -> tenuti 7, fatt 10 -> accredito 3, DOVUTA
--   P3  reso 3 riconsegna, fattura 10-> tenuti 7, fatt 10 -> accredito 3, FACOLTATIVA
--   P4  resi 2+2 a credito, fattura 7-> tenuti 6, fatt 7  -> accredito 1: greedy
-- ============================================================
-- P1 in bozza: prende la riga a mano di P5, poi va a CONSEGNATO.
CREATE TEMP TABLE tmp_p1 AS
SELECT b.*, NULL::bigint AS riga_manuale_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('accrediti P1', 'DRAFT',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'CONSEGNATO') b;
UPDATE tmp_p1 SET riga_manuale_id = pg_temp.mk_riga_manuale(ddt_id, 6);
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', (SELECT ddt_id FROM tmp_p1), 'CONSEGNATO');
CREATE TEMP TABLE tmp_p1_riga AS
SELECT * FROM dbops.fn_pgtap_crea_reso('accrediti P1', (SELECT ddt_id FROM tmp_p1), 3,
         p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_p1));

CREATE TEMP TABLE tmp_p2 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('accrediti P2',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'CONSEGNATO');
CREATE TEMP TABLE tmp_p2_riga AS
SELECT * FROM dbops.fn_pgtap_crea_reso('accrediti P2', (SELECT ddt_id FROM tmp_p2), 3,
         p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_p2));

CREATE TEMP TABLE tmp_p3 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('accrediti P3',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'CONSEGNATO');
CREATE TEMP TABLE tmp_p3_riga AS
SELECT * FROM dbops.fn_pgtap_crea_reso('accrediti P3', (SELECT ddt_id FROM tmp_p3), 3, 'RESO_PER_RICONSEGNA',
         p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_p3));

CREATE TEMP TABLE tmp_p4 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('accrediti P4',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'CONSEGNATO');
CREATE TEMP TABLE tmp_p4_riga1 AS
SELECT * FROM dbops.fn_pgtap_crea_reso('accrediti P4', (SELECT ddt_id FROM tmp_p4), 2,
         p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_p4));
CREATE TEMP TABLE tmp_p4_riga2 AS
SELECT * FROM dbops.fn_pgtap_crea_reso('accrediti P4', (SELECT ddt_id FROM tmp_p4), 2,
         p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_p4));

-- P5 (test 9) — MERCE SENZA ORIGINE ORDINE.
--   Una riga aggiunta a mano sul DDT di P1 (spedizione mista): 6 pezzi che
--   escono, vengono fatturati e in parte tornano indietro. Fino al 2026-08-17
--   quel reso si registrava e NON produceva alcun accredito, perche' la coda
--   si agganciava a ordine_riga_id — che qui e' NULL.
CREATE TEMP TABLE tmp_p5_riga_ddt AS
SELECT riga_manuale_id AS ddt_riga_id FROM tmp_p1;   -- entrata in bozza, prima della consegna
CREATE TEMP TABLE tmp_p5_riga AS
SELECT * FROM dbops.fn_pgtap_crea_reso('accrediti P5', (SELECT ddt_id FROM tmp_p1), 2,
         p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_p5_riga_ddt));

-- P6 (test 10) — UNA RIGA D'ORDINE, DUE SPEDIZIONI.
--   Spedizione A: 4 pezzi, fatturati tutti e 4, tornati tutti e 4.
--   Spedizione B: 6 pezzi, MAI fatturati, 3 tornati indietro.
--   Le due partizioni danno risposte diverse, ed e' il punto del test.
--   Nel DB di sviluppo il caso non esiste: la fixture lo costruisce.
CREATE TEMP TABLE tmp_p6_a AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('accrediti P6',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs), p_quantita => 10,
         p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'CONSEGNATO',
         p_qta_da_evadere => 4);
CREATE TEMP TABLE tmp_p6_b AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('accrediti P6',
         p_ordine_id => (SELECT ordine_id FROM tmp_p6_a), p_qta_da_evadere => 6);
CREATE TEMP TABLE tmp_p6 AS
SELECT a.ordine_riga_id, a.ddt_uid AS ddt_a_uid, a.ddt_riga_id AS ddt_a_riga,
       b.ddt_uid AS ddt_b_uid, b.ddt_riga_id AS ddt_b_riga
  FROM tmp_p6_a a, tmp_p6_b b;
CREATE TEMP TABLE tmp_p6_riga_a AS
SELECT * FROM dbops.fn_pgtap_crea_reso('accrediti P6', (SELECT ddt_id FROM tmp_p6_a), 4,
         p_ddt_riga_id => (SELECT ddt_a_riga FROM tmp_p6));
CREATE TEMP TABLE tmp_p6_riga_b AS
SELECT * FROM dbops.fn_pgtap_crea_reso('accrediti P6', (SELECT ddt_id FROM tmp_p6_b), 3,
         p_ddt_riga_id => (SELECT ddt_b_riga FROM tmp_p6));

-- Fatturazione: P2 e P3 per 10 (tutto), P4 per 7 (parziale). P1 nessuna.
SELECT pg_temp.mk_af(script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_p2)::text, (SELECT ddt_riga_id FROM tmp_p2)), 10);
SELECT pg_temp.mk_af(script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_p3)::text, (SELECT ddt_riga_id FROM tmp_p3)), 10);
SELECT pg_temp.mk_af(script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_p4)::text, (SELECT ddt_riga_id FROM tmp_p4)), 7);
-- P5: la riga manuale e' fatturata per intero, sul segmento della SUA riga di DDT.
SELECT pg_temp.mk_af(script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_p1)::text, (SELECT ddt_riga_id FROM tmp_p5_riga_ddt)), 6);
-- P6: solo la spedizione A e' fatturata. La B no, di proposito.
SELECT pg_temp.mk_af(script.fn_segment_key('DDT_VENDITA', (SELECT ddt_a_uid FROM tmp_p6)::text, (SELECT ddt_a_riga FROM tmp_p6)), 4);
-- Il test prova la vista, non il permesso: l'azione «rendi pronta» all'utente del contesto.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'cambia_stato_commessa');
SELECT vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM tmp_com), 'PRONTA_FATTURAZIONE');
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com));

-- ============================================================
-- ASSERZIONI
-- ============================================================
-- 1) security_invoker: la reloption sopravvive al changeset (regressione V-1)
SELECT ok(
  (SELECT 'security_invoker=on' = ANY(c.reloptions)
     FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='vendite' AND c.relname='vw_resi_da_accreditare'),
  '1) security_invoker=on ri-specificato sulla vista (no bypass RLS)');

-- 2) P1: merce resa MAI fatturata -> niente da accreditare -> ESCE (chiude 1b)
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.vw_resi_da_accreditare
    WHERE resi_riga_id=(SELECT resi_riga_id FROM tmp_p1_riga)),
  0, '2) P1 reso mai fatturato: conto in pari -> fuori dalla coda (chiude 1b)');

-- 3-5) P2: reso su merce fatturata -> accredito 3, DOVUTA, conto esposto
SELECT is(
  (SELECT accredito_dovuto FROM vendite.vw_resi_da_accreditare
    WHERE resi_riga_id=(SELECT resi_riga_id FROM tmp_p2_riga)),
  3::numeric, '3) P2 reso su merce fatturata: accredito dovuto 3 (10 fatturati - 7 tenuti)');

SELECT is(
  (SELECT etichetta FROM vendite.vw_resi_da_accreditare
    WHERE resi_riga_id=(SELECT resi_riga_id FROM tmp_p2_riga)),
  'DOVUTA'::varchar, '4) P2 tipo a credito -> etichetta DOVUTA (la merce non torna piu'')');

SELECT is(
  (SELECT (tenuti, fatturati) FROM vendite.vw_resi_da_accreditare
    WHERE resi_riga_id=(SELECT resi_riga_id FROM tmp_p2_riga)),
  (7::numeric, 10::numeric), '5) P2 il conto e'' esposto: tenuti 7, fatturati 10 (cosa e'' successo, non cosa fare)');

-- 6) P3: ri-consegna su merce gia' fatturata -> IN CODA come FACOLTATIVA
--    (oggi invisibile: la forma vecchia filtrava riapre_residuo=false)
SELECT is(
  (SELECT etichetta FROM vendite.vw_resi_da_accreditare
    WHERE resi_riga_id=(SELECT resi_riga_id FROM tmp_p3_riga)),
  'FACOLTATIVA'::varchar, '6) P3 ri-consegna su merce fatturata: in coda, etichetta FACOLTATIVA (oggi invisibile)');

-- 7-8) P4: accredito 1 su due righe di reso da 2 -> la prima lo prende tutto
SELECT is(
  (SELECT accredito_dovuto FROM vendite.vw_resi_da_accreditare
    WHERE resi_riga_id=(SELECT resi_riga_id FROM tmp_p4_riga1)),
  1::numeric, '7) P4 greedy: la 1a riga di reso assorbe l''accredito, cappato (1 di 2)');

SELECT is(
  (SELECT COUNT(*)::int FROM vendite.vw_resi_da_accreditare
    WHERE resi_riga_id=(SELECT resi_riga_id FROM tmp_p4_riga2)),
  0, '8) P4 greedy: alla 2a riga non resta accredito -> fuori dalla coda');

-- ============================================================
-- 9) ⭐ MERCE SENZA ORIGINE ORDINE: il buco che la slice S4 chiude.
--    Riga aggiunta a mano, 6 pezzi usciti e fatturati, 2 tornati indietro.
--    `ordine_riga_id` e' NULL, e prima del 2026-08-17 era la chiave con cui la
--    coda si agganciava: il reso si registrava e l'accredito non esisteva.
--    Le due asserzioni in una: c'e' l'accredito, ED e' senza riga d'ordine.
-- ============================================================
SELECT results_eq(
  $q$SELECT accredito_dovuto, ordine_riga_id FROM vendite.vw_resi_da_accreditare
      WHERE resi_riga_id = (SELECT resi_riga_id FROM tmp_p5_riga)$q$,
  $q$VALUES (2::numeric, NULL::bigint)$q$,
  '9) reso su merce SENZA origine ordine: accredito 2 e ordine_riga_id NULL');

-- ============================================================
-- 10) ⭐ LA FINESTRA PARTIZIONA PER SPEDIZIONE, NON PER RIGA D'ORDINE.
--     Una riga d'ordine da 10, due spedizioni:
--       A: 4 usciti, 4 fatturati, 4 tornati  -> accredito 4  (tutto il fatturato torna)
--       B: 6 usciti, 0 fatturati, 3 tornati  -> accredito 0  (non era stato fatturato)
--
--     ⚠️ Con la partizione VECCHIA (per riga d'ordine) il conto si mescolava:
--     tenuti 3, fatturati 4 -> accredito di partita 1, e la prima riga di reso
--     ne prendeva 1 invece di 4. Il reso NON fatturato della spedizione B
--     diluiva l'accredito dovuto sulla A.
--
--     Il caso non esiste nei dati di sviluppo — 3 righe d'ordine sono evase da
--     3 DDT, ma nessuna ha resi da piu' di un DDT — quindi la fixture lo
--     costruisce. E' l'unico posto in cui questa differenza si vede.
-- ============================================================
SELECT results_eq(
  $q$SELECT COALESCE((SELECT accredito_dovuto FROM vendite.vw_resi_da_accreditare
                       WHERE resi_riga_id = (SELECT resi_riga_id FROM tmp_p6_riga_a)), 0),
            COALESCE((SELECT accredito_dovuto FROM vendite.vw_resi_da_accreditare
                       WHERE resi_riga_id = (SELECT resi_riga_id FROM tmp_p6_riga_b)), 0)$q$,
  $q$VALUES (4::numeric, 0::numeric)$q$,
  '10) due spedizioni della stessa riga d''ordine: A accredita 4 (non 1), B nulla');

SELECT * FROM finish();
ROLLBACK;
