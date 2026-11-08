-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-11-07 (brief-db-sorgente-documento-e-riga, giro T.4): la bolla si cancella solo da bozza VUOTA
--   (nessuna riga attiva, 20261106-88). Il 27 cambia attesa: la bolla con la riga evasa e' rifiutata
--   (E_DELETE_DOC_CON_RIGHE); tolta la riga (D-3), la bozza vuota si cancella e l'ordine torna CONFERMATO.
-- pgTAP test per Zero ERP
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): gli ordini senza bolla (re_mk_ordine) da dbops.fn_pgtap_crea_ordine_con_righe, la bolla J da dbops.fn_pgtap_crea_ddt_senza_ordine (DRAFT); restano a mano la bolla standalone di D col legame scritto a mano e il legame in piu' di E (sono il caso).
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): il reso di F dal builder dbops.fn_pgtap_crea_reso, in bozza; restano a mano la conferma (fn_conferma_reso, il test 30 ne misura l'effetto: resta anche l'azione conferma_reso in testa) e la ri-consegna dalla madre in bozza (fn_genera_ddt_riconsegna e' il verbo del 30, e i 31-35 lavorano sulla bolla in bozza).
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine (pg_temp.re_mk_ddt lo chiama e annota le chiavi; ritirata pg_temp.re_avanza); restano a mano gli ordini senza bolla (re_mk_ordine), le bolle standalone di D e J, il legame in piu' di E, le scritture sulle righe e gli annulli (sono il caso), il reso di F (giro 2).
-- rev 2026-10-25 (brief-modello-documento-vendita §7, giro 5): 37 e 42 annullano dal verbo vendite.fn_cambia_stato_ddt (senza conferma) invece che con un UPDATE diretto dello stato, che ora ferma la porta (E_DOC_STATO_SOLO_DAL_VERBO) prima dell'avviso sui legami. Attese invariate.
-- Test: le righe di un DDT nato da un ordine (D28)
--   vendite.fn_ddt_riga_evasa, vendite.trgfn_ddt_righe_guard_riga_evasa,
--   vendite.trgfn_ordini_ful_guard_legame, il lock delle righe sul
--   fulfillment, il ritiro del legame in vendite.trgfn_dlt_block_ordrig_ddtrig,
--   script.fn_check_ddt_riga_correggi_qta_evasa, il verbo
--   vendite.fn_ddt_riga_correggi_qta_evasa, il building block
--   vendite.fn_ordine_proietta_stato_evasione e le colonne nuove di
--   vendite.vw_ddt_righe_dettaglio.
-- ChangeSet: 20261011-05 … -20, -34, -35
-- Brief: brief-db-ddt-righe-evase-dall-ordine (D-1 … D-5, §5)
-- ------------------------------------------------------------
-- Indice test (plan 43):
--   1) gli oggetti nuovi esistono e i tre trigger sono montati
--   2) i quattro codici nuovi sono a catalogo con la loro classe
--   3) ⭐ regola del 2: le sei madri chiamano il BB e non contengono piu' la proiezione
--  A — ordine pippo 10, bolla generata con 10
--   4) l'ordine e' EVASO (il BB dentro fn_genera_ddt_da_ordine)
--   5) la vista: evasa = true, correggi_qta_evasa_blocco NULL
--   6) D-1: UPDATE della quantita' della riga evasa -> E_DDT_RIGA_EVASA_FERMA
--   7) D-1: UPDATE dell'articolo -> E_DDT_RIGA_EVASA_FERMA
--   8) D-1: la descrizione resta libera
--   9) il legame: UPDATE di qta_evasa -> E_DDT_LEGAME_EVASIONE_SOLO_DA_VERBO
--  10) il legame: DELETE diretto -> E_DDT_LEGAME_EVASIONE_SOLO_DA_VERBO
--  11) il legame: i capi non si spostano -> E_DDT_LEGAME_EVASIONE_SOLO_DA_VERBO
--  12) D-2: il verbo a 6 ritorna 6
--  13) D-2: riga 6, qta_evasa 6
--  14) D-2: ordine PARZIALMENTE_EVASO
--  15) D-2: quantita' 0 -> E_QTA_NON_POSITIVA
--  16) una seconda bolla col residuo 4: ordine EVASO
--  17) D-2: il verbo oltre il residuo -> E_QTA_SUPERA_RESIDUO
--  18) D-3: la riga della seconda bolla si toglie in bozza; legame ritirato, ordine PARZIALMENTE_EVASO
--  19) D-5: riga a mano sulla bolla da ordine: entra; evasa = false, motivo RIGA_NON_EVASA
--  20) il verbo sulla riga a mano -> E_DDT_RIGA_NON_EVASA
--  21) la quantita' della riga a mano resta libera
--  22) la bolla (evasa 6 + a mano 5) si emette; l'ordine resta PARZIALMENTE_EVASO per 6
--  23) fuori bozza: il verbo -> E_RIGA_DOC_NON_BOZZA
--  24) D-4: fuori bozza UPDATE di qta_evasa -> E_RIGA_DOC_NON_BOZZA (parla prima il lock)
--  25) fuori bozza: motivo DDT_NON_IN_BOZZA nella vista
--  B — ordine 10, bolla 10, riga tolta in bozza
--  26) D-3: ultimo legame ritirato -> ordine CONFERMATO
--  C — la bolla da ordine si elimina solo vuota
--  27) con la riga evasa la testata non si elimina; tolta la riga (D-3) si', e l'ordine e' CONFERMATO
--  D — bolla standalone con un legame scritto a mano
--  28) motivo DDT_SENZA_ORIGINE; la riga e' evasa, quindi ferma
--  E — una riga che evade due righe d'ordine
--  29) motivo LEGAMI_MULTIPLI
--  F — la ri-consegna di un reso (D-7: la stessa regola)
--  30) il BB nei verbi del reso: conferma -> PARZIALMENTE_EVASO, ri-consegna -> EVASO
--  31) la riga di ri-consegna e' evasa, correzione ammessa
--  32) la sua quantita' non cambia con un UPDATE (E_DDT_RIGA_EVASA_FERMA)
--  33) il verbo a 3: riga, ponte e fulfillment insieme; 1 torna da ri-consegnare
--  34) oltre cio' che resta da ri-consegnare: rifiuto
--  35) si toglie in bozza: ponte e fulfillment ritirati, il reso torna da ri-consegnare
--  G — D-6
--  36) su una bolla emessa non nasce un legame nuovo (fulfillment, ponte)
--  H — D-8: l'annullo di una bolla con legami chiede conferma
--  37) l'annullo dal verbo di stato, senza conferma, e' rifiutato: E_DOC_ANNULLO_CON_LEGAMI
--  38) il verbo con una conferma che non corrisponde: stesso rifiuto
--  39) il verbo confermato, bolla in bozza: ANNULLATO, legame ritirato, ordine CONFERMATO
--  40) il verbo confermato, bolla emessa: ANNULLATO, legame ritirato, ordine CONFERMATO
--  41) fuori bozza la porta del ritiro accesa a mano non toglie un legame
--  42) una bolla senza legami si annulla come prima (dal verbo di stato, senza conferma)
--  43) ⚠️ la porta senza il proprietario: GUC accesa a mano -> rifiuto.
--      ROSSO DA OWNER, VERDE COME APP: da proprietario della tabella la porta
--      si apre per costruzione. Per ultimo.
--
-- ⚠️ LE FIXTURE SI COSTRUISCONO: cliente e articoli dai builder, bolle da
--   ordine da dbops.fn_pgtap_crea_ddt_da_ordine (ordine 10 @20, bolla in
--   bozza o nello stato del caso, per la matrice); gli ordini senza bolla da
--   dbops.fn_pgtap_crea_ordine_con_righe (CONFERMATO), la bolla senza legami
--   di J da dbops.fn_pgtap_crea_ddt_senza_ordine (in bozza).
--   L'articolo NON e' gestito a magazzino: l'emissione non chiede prelievi
--   (il Lotto 3 e' invariato, §5.1).
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga non verrebbero mai esercitati (qui
--   il COMMIT non arriva mai, si chiude in ROLLBACK).
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE +
-- RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(43);

-- La conferma del reso e' un verbo con l'azione conferma_reso (scenario F).
DO $az$ BEGIN
  PERFORM dbops.fn_pgtap_concedi_azione(
      NULLIF(current_setting('app.current_user_id', true), '')::integer, 'conferma_reso');
  -- L'annullo di una bolla emessa e' un'azione (emetti_ddt) del verbo di stato (scenario H).
  PERFORM dbops.fn_pgtap_concedi_azione(
      NULLIF(current_setting('app.current_user_id', true), '')::integer, 'emetti_ddt');
END $az$;

-- ============================================================
-- 1-3) Oggetti, codici, regola del 2
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE (n.nspname, p.proname) IN (('vendite', 'fn_ordine_proietta_stato_evasione'),
                                     ('vendite', 'fn_ddt_riga_evasa'),
                                     ('vendite', 'trgfn_ddt_righe_guard_riga_evasa'),
                                     ('vendite', 'trgfn_ddt_riga_legame_guard'),
                                     ('script',  'fn_check_ddt_riga_correggi_qta_evasa'),
                                     ('vendite', 'fn_ddt_riga_correggi_qta_evasa'),
                                     ('vendite', 'fn_documento_legami'),
                                     ('vendite', 'fn_ddt_riga_ritira_legami'),
                                     ('vendite', 'fn_annulla_ddt')))
  + (SELECT count(*)::int FROM pg_trigger t
      WHERE NOT t.tgisinternal
        AND (t.tgrelid, t.tgname) IN (
              ('vendite.ddt_righe'::regclass, 'trg_ddt_righe_a10_guard_riga_evasa_upd'),
              ('vendite.ordini_righe_fulfillment'::regclass, 'trg_ordini_righe_fulfillment_a05_guard_legame_upd_dlt'),
              ('vendite.resi_righe_riconsegne'::regclass, 'trg_resi_righe_riconsegne_a05_guard_legame_upd_dlt'),
              ('vendite.ordini_righe_fulfillment'::regclass, 'trg_ordini_righe_fulfillment_a05_doc_bozza_ins_upd'),
              ('vendite.resi_righe_riconsegne'::regclass, 'trg_resi_righe_riconsegne_a05_doc_bozza_ins_upd'))),
  14,
  '1) le nove funzioni esistono (il lettore dei legami e'' vendite.fn_documento_legami dal 2026-10-11) e i cinque trigger sono montati');

SELECT is(
  (SELECT string_agg(c.codice || '=' || c.classe, ' ' ORDER BY c.codice)
     FROM config.codici_errore c
    WHERE c.codice IN ('E_DDT_RIGA_EVASA_FERMA', 'E_DDT_RIGA_NON_EVASA',
                       'E_DDT_RIGA_EVASA_LEGAMI_MULTIPLI', 'E_DDT_LEGAME_EVASIONE_SOLO_DA_VERBO')),
  'E_DDT_LEGAME_EVASIONE_SOLO_DA_VERBO=TECNICO E_DDT_RIGA_EVASA_FERMA=CONFLITTO_STATO '
  'E_DDT_RIGA_EVASA_LEGAMI_MULTIPLI=TECNICO E_DDT_RIGA_NON_EVASA=CONFLITTO_STATO',
  '2) i quattro codici nuovi sono a catalogo con la loro classe');

-- ⭐ La regola del 2 presidiata sulla forma: la madre CHIAMA il BB e non
--    contiene piu' la proiezione (il sorgente senza commenti: la prosa che la
--    spiega la nomina apposta).
SELECT is(
  (SELECT count(*)::int FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname IN ('fn_genera_ddt_da_ordine', 'fn_conferma_reso', 'fn_annulla_reso',
                        'fn_chiudi_riconsegna_reso', 'fn_riapri_riconsegna_reso',
                        'fn_genera_ddt_riconsegna')
      AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') LIKE '%vendite.fn_ordine_proietta_stato_evasione(%'
      AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') NOT LIKE '%fn_ordine_ha_residuo_evasione%'
      -- la SCRITTURA dello stato: fn_genera_ddt_da_ordine lo legge (JOIN), e va bene
      AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') !~* 'SET\s+stato_doc_ordine_id'),
  6,
  '3) le sei madri chiamano vendite.fn_ordine_proietta_stato_evasione e non scrivono piu'' lo stato dell''ordine da sole');

-- ============================================================
-- Fixture — COSTRUITE coi builder
-- ============================================================
CREATE TEMP TABLE tmp_cli_re AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgtap_righe_evase');

CREATE TEMP TABLE tmp_refs_re AS
SELECT
  c.billing_account_id,
  c.soggetto_ruolo_id,
  script.fn_pgtap_emittente_operatore()                                                                      AS emittente_fiscale_id,
  -- ⚠️ NON gestiti a magazzino: l'emissione non chiede prelievi.
  dbops.fn_pgtap_crea_articolo('PGT-RE-PIPPO', false)                                                        AS articolo_id,
  dbops.fn_pgtap_crea_articolo('PGT-RE-PLUTO', false)                                                        AS articolo2_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                                   AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)                               AS iva_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno = 'DRAFT'      AND s.attivo LIMIT 1)       AS stato_ddt_draft_id
FROM tmp_cli_re c;

CREATE TEMP TABLE tmp_fix(chiave text PRIMARY KEY, id bigint);
CREATE TEMP TABLE tmp_esito(caso text PRIMARY KEY, sqlstate text, messaggio text, righe int);

-- Un ordine CONFERMATO con una riga (p_qta @20), senza bolla, dal builder:
-- serve dove il caso vuole una riga d'ordine e basta. Qui se ne annotano le chiavi.
CREATE OR REPLACE FUNCTION pg_temp.re_mk_ordine(p_chiave text, p_articolo uuid, p_qta numeric)
RETURNS void AS $$
DECLARE o RECORD;
BEGIN
  SELECT * INTO o FROM dbops.fn_pgtap_crea_ordine_con_righe('righe evase', 'CONFERMATO',
      (SELECT r.billing_account_id FROM tmp_refs_re r),
      p_quantita => p_qta, p_prezzo => 20, p_articolo_id => p_articolo,
      p_data_ordine => DATE '2026-10-01');
  INSERT INTO tmp_fix VALUES (p_chiave || '_ord', o.ordine_id), (p_chiave || '_orr', o.ordine_riga_id);
END $$ LANGUAGE plpgsql;

-- Una bolla da ordine, con la sua riga evasa, dal builder: nello stato chiesto
-- (default DRAFT, per scriverle cio' che il caso prova). Con p_qta_ordine il
-- builder costruisce anche l'ordine (una riga di p_qta_ordine @20) e se ne
-- annotano le chiavi; senza, la bolla evade l'ordine p_ordine gia' annotato.
CREATE OR REPLACE FUNCTION pg_temp.re_mk_ddt(p_chiave text, p_ordine text, p_qta numeric,
                                             p_qta_ordine numeric DEFAULT NULL,
                                             p_stato varchar DEFAULT 'DRAFT')
RETURNS void AS $$
DECLARE r RECORD; b RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs_re;
  IF p_qta_ordine IS NOT NULL THEN
    SELECT * INTO b FROM dbops.fn_pgtap_crea_ddt_da_ordine('righe evase', p_stato, r.billing_account_id,
        p_quantita => p_qta_ordine, p_prezzo => 20, p_articolo_id => r.articolo_id,
        p_qta_da_evadere => p_qta);
    INSERT INTO tmp_fix VALUES (p_ordine || '_ord', b.ordine_id), (p_ordine || '_orr', b.ordine_riga_id);
  ELSE
    SELECT * INTO b FROM dbops.fn_pgtap_crea_ddt_da_ordine('righe evase', p_stato,
        p_ordine_id => (SELECT id FROM tmp_fix WHERE chiave = p_ordine || '_ord'),
        p_qta_da_evadere => p_qta);
  END IF;
  INSERT INTO tmp_fix VALUES (p_chiave || '_ddt', b.ddt_id), (p_chiave || '_dr', b.ddt_riga_id);
END $$ LANGUAGE plpgsql;

-- Esegue un'istruzione e ne cattura l'esito (righe toccate, o SQLSTATE + frase).
CREATE OR REPLACE FUNCTION pg_temp.re_prova(p_caso text, p_sql text)
RETURNS void AS $$
DECLARE v_n int;
BEGIN
  BEGIN
    EXECUTE p_sql;
    GET DIAGNOSTICS v_n = ROW_COUNT;
    INSERT INTO tmp_esito VALUES (p_caso, NULL, NULL, v_n);
  EXCEPTION WHEN OTHERS THEN
    INSERT INTO tmp_esito VALUES (p_caso, SQLSTATE, SQLERRM, NULL);
  END;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pg_temp.re_fix(p_chiave text) RETURNS bigint
  AS $$ SELECT id FROM tmp_fix WHERE chiave = p_chiave $$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION pg_temp.re_stato_ordine(p_chiave text) RETURNS text AS $$
  SELECT s.codice_interno FROM vendite.ordini o
    JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
   WHERE o.id = pg_temp.re_fix(p_chiave || '_ord')
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION pg_temp.re_rifiuto(p_caso text, p_frammento text) RETURNS boolean AS $$
  SELECT e.sqlstate = 'P0001' AND e.messaggio LIKE '%' || p_frammento || '%'
    FROM tmp_esito e WHERE e.caso = p_caso
$$ LANGUAGE sql;

-- ============================================================
-- A — ordine pippo 10, bolla generata con 10
-- ============================================================
SELECT pg_temp.re_mk_ddt('a1', 'a', 10, p_qta_ordine => 10);

SELECT is(pg_temp.re_stato_ordine('a'), 'EVASO',
  '4) evasione completa: l''ordine e'' EVASO (il BB dentro fn_genera_ddt_da_ordine)');

SELECT results_eq(
  format('SELECT evasa, correggi_qta_evasa_blocco FROM vendite.vw_ddt_righe_dettaglio WHERE id = %s',
         pg_temp.re_fix('a1_dr')),
  $$VALUES (true, NULL::text)$$,
  '5) la vista: la riga e'' evasa e la correzione e'' ammessa');

SELECT pg_temp.re_prova('6_upd_qta',
  format('UPDATE vendite.ddt_righe SET qta_operativa = 6 WHERE id = %s', pg_temp.re_fix('a1_dr')));
SELECT ok(pg_temp.re_rifiuto('6_upd_qta', 'viene da un ordine o da un reso'),
  '6) D-1: la quantita'' della riga evasa non cambia con un UPDATE (E_DDT_RIGA_EVASA_FERMA)');

SELECT pg_temp.re_prova('7_upd_art',
  format('UPDATE vendite.ddt_righe SET articolo_id = %L WHERE id = %s',
         (SELECT articolo2_id FROM tmp_refs_re), pg_temp.re_fix('a1_dr')));
SELECT ok(pg_temp.re_rifiuto('7_upd_art', 'viene da un ordine o da un reso'),
  '7) D-1: l''articolo della riga evasa non cambia (E_DDT_RIGA_EVASA_FERMA)');

SELECT pg_temp.re_prova('8_upd_descr',
  format('UPDATE vendite.ddt_righe SET descrizione = ''pippo, descrizione corretta'' WHERE id = %s',
         pg_temp.re_fix('a1_dr')));
SELECT is((SELECT righe FROM tmp_esito WHERE caso = '8_upd_descr'), 1,
  '8) D-1: la descrizione della riga evasa resta libera');

SELECT pg_temp.re_prova('9_ful_upd',
  format('UPDATE vendite.ordini_righe_fulfillment SET qta_evasa = 6 WHERE ddt_riga_id = %s',
         pg_temp.re_fix('a1_dr')));
SELECT ok(pg_temp.re_rifiuto('9_ful_upd', 'non si scrive direttamente'),
  '9) il legame: qta_evasa non cambia fuori dal verbo (E_DDT_LEGAME_EVASIONE_SOLO_DA_VERBO)');

SELECT pg_temp.re_prova('10_ful_dlt',
  format('DELETE FROM vendite.ordini_righe_fulfillment WHERE ddt_riga_id = %s', pg_temp.re_fix('a1_dr')));
SELECT ok(pg_temp.re_rifiuto('10_ful_dlt', 'non si scrive direttamente'),
  '10) il legame: non si toglie lasciando la riga (E_DDT_LEGAME_EVASIONE_SOLO_DA_VERBO)');

-- Una seconda riga di ordine dello stesso articolo, per spostare un capo.
SELECT pg_temp.re_mk_ordine('a_bis', (SELECT articolo_id FROM tmp_refs_re), 10);
SELECT pg_temp.re_prova('11_ful_capo',
  format('UPDATE vendite.ordini_righe_fulfillment SET ordine_riga_id = %s WHERE ddt_riga_id = %s',
         pg_temp.re_fix('a_bis_orr'), pg_temp.re_fix('a1_dr')));
SELECT ok(pg_temp.re_rifiuto('11_ful_capo', 'non si scrive direttamente'),
  '11) il legame: i due capi non si spostano (E_DDT_LEGAME_EVASIONE_SOLO_DA_VERBO)');

-- D-2: il verbo
CREATE TEMP TABLE tmp_verbo AS
SELECT vendite.fn_ddt_riga_correggi_qta_evasa(pg_temp.re_fix('a1_dr'), 6) AS qta;

SELECT is((SELECT qta FROM tmp_verbo), 6.000000::numeric,
  '12) D-2: il verbo ritorna la nuova quantita'' evasa');

SELECT results_eq(
  format($q$SELECT dr.quantita, f.qta_evasa
              FROM vendite.ddt_righe dr
              JOIN vendite.ordini_righe_fulfillment f ON f.ddt_riga_id = dr.id
             WHERE dr.id = %s$q$, pg_temp.re_fix('a1_dr')),
  $$VALUES (6.000000::numeric, 6.000000::numeric)$$,
  '13) D-2: riga e legame cambiano insieme (6 e 6)');

SELECT is(pg_temp.re_stato_ordine('a'), 'PARZIALMENTE_EVASO',
  '14) D-2: il residuo 4 riapre l''ordine (PARZIALMENTE_EVASO)');

SELECT pg_temp.re_prova('15_qta_zero',
  format('SELECT vendite.fn_ddt_riga_correggi_qta_evasa(%s, 0)', pg_temp.re_fix('a1_dr')));
SELECT ok(pg_temp.re_rifiuto('15_qta_zero', 'deve essere positiva'),
  '15) D-2: quantita'' zero -> E_QTA_NON_POSITIVA');

-- Una seconda bolla evade il residuo: l'ordine si chiude.
SELECT pg_temp.re_mk_ddt('a2', 'a', 4);
SELECT is(pg_temp.re_stato_ordine('a'), 'EVASO',
  '16) la seconda bolla evade il residuo 4: ordine EVASO');

SELECT pg_temp.re_prova('17_oltre',
  format('SELECT vendite.fn_ddt_riga_correggi_qta_evasa(%s, 7)', pg_temp.re_fix('a1_dr')));
SELECT ok(pg_temp.re_rifiuto('17_oltre', 'supera residuo'),
  '17) D-2: oltre il residuo -> E_QTA_SUPERA_RESIDUO (il guard del legame, reso-aware)');

-- D-3: la riga evasa della seconda bolla si toglie in bozza.
SELECT pg_temp.re_prova('18_dlt_riga',
  format('DELETE FROM vendite.ddt_righe WHERE id = %s', pg_temp.re_fix('a2_dr')));
SELECT ok(
  (SELECT righe = 1 FROM tmp_esito WHERE caso = '18_dlt_riga')
  AND NOT EXISTS (SELECT 1 FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id = pg_temp.re_fix('a2_dr'))
  AND pg_temp.re_stato_ordine('a') = 'PARZIALMENTE_EVASO',
  '18) D-3: la riga evasa si toglie in bozza, il legame va con lei, l''ordine torna PARZIALMENTE_EVASO');

-- D-5: una riga a mano sulla bolla da ordine (pippo 5 in piu').
SELECT pg_temp.re_prova('19_ins_mano',
  format($q$INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa,
                                           prezzo_unitario, iva_id, storicizza, meta)
            VALUES (%s, 2, %L, 'pippo in piu''', 5, 20, %s, false, '{"test_scope":"pgtap_righe_evase"}')$q$,
         pg_temp.re_fix('a1_ddt'), (SELECT articolo_id FROM tmp_refs_re), (SELECT iva_id FROM tmp_refs_re)));
INSERT INTO tmp_fix
SELECT 'a1_mano', dr.id FROM vendite.ddt_righe dr
 WHERE dr.ddt_id = pg_temp.re_fix('a1_ddt') AND dr.riga_nr = 2;
SELECT ok(
  (SELECT righe = 1 FROM tmp_esito WHERE caso = '19_ins_mano')
  AND (SELECT NOT evasa AND correggi_qta_evasa_blocco = 'RIGA_NON_EVASA'
         FROM vendite.vw_ddt_righe_dettaglio WHERE id = pg_temp.re_fix('a1_mano')),
  '19) D-5: la riga a mano entra; non e'' evasa, motivo RIGA_NON_EVASA');

SELECT pg_temp.re_prova('20_verbo_mano',
  format('SELECT vendite.fn_ddt_riga_correggi_qta_evasa(%s, 3)', pg_temp.re_fix('a1_mano')));
SELECT ok(pg_temp.re_rifiuto('20_verbo_mano', 'non viene da un ordine o da un reso'),
  '20) il verbo sulla riga a mano -> E_DDT_RIGA_NON_EVASA');

SELECT pg_temp.re_prova('21_upd_mano',
  format('UPDATE vendite.ddt_righe SET qta_operativa = 4 WHERE id = %s', pg_temp.re_fix('a1_mano')));
SELECT is((SELECT righe FROM tmp_esito WHERE caso = '21_upd_mano'), 1,
  '21) la quantita'' della riga a mano resta libera');

-- La bolla (evasa 6 + a mano 4) si emette.
SELECT pg_temp.re_prova('22_emetti',
  format('SELECT dbops.fn_pgtap_porta_a_stato(''vendite.ddt'', %s, ''EMESSO'')', pg_temp.re_fix('a1_ddt')));
SELECT ok(
  (SELECT sqlstate IS NULL FROM tmp_esito WHERE caso = '22_emetti')
  AND pg_temp.re_stato_ordine('a') = 'PARZIALMENTE_EVASO',
  '22) la bolla si emette; l''ordine resta evaso per 6 (la riga a mano non lo tocca)');

SELECT pg_temp.re_prova('23_verbo_emesso',
  format('SELECT vendite.fn_ddt_riga_correggi_qta_evasa(%s, 5)', pg_temp.re_fix('a1_dr')));
SELECT ok(pg_temp.re_rifiuto('23_verbo_emesso', 'non e'' piu'' in bozza'),
  '23) fuori bozza il verbo rifiuta (E_RIGA_DOC_NON_BOZZA)');

SELECT pg_temp.re_prova('24_ful_emesso',
  format('UPDATE vendite.ordini_righe_fulfillment SET qta_evasa = 5 WHERE ddt_riga_id = %s',
         pg_temp.re_fix('a1_dr')));
SELECT ok(pg_temp.re_rifiuto('24_ful_emesso', 'non e'' piu'' in bozza'),
  '24) D-4: fuori bozza qta_evasa e'' ferma, e parla prima il lock (E_RIGA_DOC_NON_BOZZA)');

SELECT is(
  (SELECT correggi_qta_evasa_blocco FROM vendite.vw_ddt_righe_dettaglio WHERE id = pg_temp.re_fix('a1_dr')),
  'DDT_NON_IN_BOZZA',
  '25) fuori bozza la vista dice DDT_NON_IN_BOZZA');

-- ============================================================
-- B — ordine 10, bolla 10, la riga si toglie: ultimo legame
-- ============================================================
SELECT pg_temp.re_mk_ddt('b1', 'b', 10, p_qta_ordine => 10);
DELETE FROM vendite.ddt_righe WHERE id = pg_temp.re_fix('b1_dr');
SELECT ok(
  pg_temp.re_stato_ordine('b') = 'CONFERMATO'
  AND vendite.fn_ordine_ha_residuo_evasione(pg_temp.re_fix('b_ord')),
  '26) D-3: tolto l''ultimo legame l''ordine torna CONFERMATO, residuo pieno');

-- ============================================================
-- C — la bolla da ordine si elimina solo vuota
-- ============================================================
-- rev 2026-11-07 (giro T.4): la testata si cancella solo da bozza vuota. La
-- bolla con la riga evasa e' rifiutata; la strada e' D-3, togliere la riga (il
-- legame si ritira con lei), poi la bozza vuota.
-- rev 2026-11-08 (giro Z.2): la frase dice «contenuto», non piu' «righe»: un
-- codice solo per tutti i documenti (Tid, 2026-11-08).
SELECT pg_temp.re_mk_ddt('c1', 'c', 10, p_qta_ordine => 10);
SELECT pg_temp.re_prova('27a_dlt_ddt_con_righe',
  format('DELETE FROM vendite.ddt WHERE id = %s', pg_temp.re_fix('c1_ddt')));
DELETE FROM vendite.ddt_righe WHERE id = pg_temp.re_fix('c1_dr');
SELECT pg_temp.re_prova('27_dlt_ddt',
  format('DELETE FROM vendite.ddt WHERE id = %s', pg_temp.re_fix('c1_ddt')));
SELECT ok(
  (SELECT sqlstate = 'P0001' AND messaggio LIKE '%ha ancora del contenuto%'
     FROM tmp_esito WHERE caso = '27a_dlt_ddt_con_righe')
  AND (SELECT righe = 1 FROM tmp_esito WHERE caso = '27_dlt_ddt')
  AND pg_temp.re_stato_ordine('c') = 'CONFERMATO',
  '27) con la riga evasa la bolla non si elimina; tolta la riga (D-3) la bozza vuota si elimina, ordine CONFERMATO');

-- ============================================================
-- D — bolla standalone con un legame scritto a mano
-- ============================================================
SELECT pg_temp.re_mk_ordine('d', (SELECT articolo_id FROM tmp_refs_re), 10);
DO $d$
DECLARE r RECORD; v_ddt bigint; v_dr bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_re;
  INSERT INTO vendite.ddt (data, stato_doc_ddt_id, destinatario_soggetto_ruolo_id, billing_account_id,
                           valuta_id, emittente_fiscale_id, storicizza, meta)
  VALUES (DATE '2026-10-02', r.stato_ddt_draft_id, r.soggetto_ruolo_id, r.billing_account_id,
          r.valuta_id, r.emittente_fiscale_id, false, '{"test_scope":"pgtap_righe_evase"}')
  RETURNING id INTO v_ddt;
  INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, storicizza, meta)
  VALUES (v_ddt, 1, r.articolo_id, 'pippo standalone', 3, false, '{"test_scope":"pgtap_righe_evase"}')
  RETURNING id INTO v_dr;
  INSERT INTO vendite.ordini_righe_fulfillment (ordine_riga_id, ddt_riga_id, qta_evasa, storicizza)
  VALUES (pg_temp.re_fix('d_orr'), v_dr, 3, false);
  INSERT INTO tmp_fix VALUES ('d1_ddt', v_ddt), ('d1_dr', v_dr);
END $d$;
SELECT pg_temp.re_prova('28_upd_std',
  format('UPDATE vendite.ddt_righe SET qta_operativa = 2 WHERE id = %s', pg_temp.re_fix('d1_dr')));
SELECT ok(
  (SELECT evasa AND correggi_qta_evasa_blocco = 'DDT_SENZA_ORIGINE'
     FROM vendite.vw_ddt_righe_dettaglio WHERE id = pg_temp.re_fix('d1_dr'))
  AND pg_temp.re_rifiuto('28_upd_std', 'viene da un ordine o da un reso'),
  '28) bolla standalone con un legame scritto a mano: motivo DDT_SENZA_ORIGINE, e la riga evasa resta ferma');

-- ============================================================
-- E — una riga che evade due righe d'ordine (forma che nessuna madre produce)
-- ============================================================
SELECT pg_temp.re_mk_ordine('e_bis', (SELECT articolo_id FROM tmp_refs_re), 10);
SELECT pg_temp.re_mk_ddt('e1', 'e', 5, p_qta_ordine => 10);
INSERT INTO vendite.ordini_righe_fulfillment (ordine_riga_id, ddt_riga_id, qta_evasa, storicizza)
VALUES (pg_temp.re_fix('e_bis_orr'), pg_temp.re_fix('e1_dr'), 1, false);
SELECT is(
  (SELECT correggi_qta_evasa_blocco FROM vendite.vw_ddt_righe_dettaglio WHERE id = pg_temp.re_fix('e1_dr')),
  'LEGAMI_MULTIPLI',
  '29) una riga che evade due righe d''ordine: motivo LEGAMI_MULTIPLI');

-- ============================================================
-- F — la ri-consegna di un reso (D-7: la stessa regola)
-- ============================================================
SELECT pg_temp.re_mk_ddt('f1', 'f', 10, p_qta_ordine => 10, p_stato => 'CONSEGNATO');
-- Il reso per ri-consegna di 4, in bozza, dal builder: la conferma e' un passo del caso (30).
CREATE TEMP TABLE tmp_f_reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('righe evase F', pg_temp.re_fix('f1_ddt'), 4, 'RESO_PER_RICONSEGNA', 'DRAFT',
         p_ddt_riga_id => pg_temp.re_fix('f1_dr'), p_ordine_riga_id => pg_temp.re_fix('f_orr'));
INSERT INTO tmp_fix SELECT 'f_reso', reso_id FROM tmp_f_reso;
INSERT INTO tmp_fix SELECT 'f_resi_riga', resi_riga_id FROM tmp_f_reso;
SELECT vendite.fn_conferma_reso(pg_temp.re_fix('f_reso'));
CREATE TEMP TABLE tmp_f_dopo_conferma AS SELECT pg_temp.re_stato_ordine('f') AS stato;
INSERT INTO tmp_fix
SELECT 'f2_ddt', vendite.fn_genera_ddt_riconsegna(pg_temp.re_fix('f_reso'));
INSERT INTO tmp_fix
SELECT 'f2_dr', dr.id FROM vendite.ddt_righe dr WHERE dr.ddt_id = pg_temp.re_fix('f2_ddt') ORDER BY dr.id LIMIT 1;

SELECT is(
  (SELECT stato FROM tmp_f_dopo_conferma) || '>' || pg_temp.re_stato_ordine('f'),
  'PARZIALMENTE_EVASO>EVASO',
  '30) il BB nei verbi del reso: la conferma riapre (PARZIALMENTE_EVASO), la ri-consegna richiude (EVASO)');

SELECT results_eq(
  format('SELECT evasa, correggi_qta_evasa_blocco FROM vendite.vw_ddt_righe_dettaglio WHERE id = %s',
         pg_temp.re_fix('f2_dr')),
  $$VALUES (true, NULL::text)$$,
  '31) D-7: la riga di ri-consegna e'' evasa e la correzione e'' ammessa');

SELECT pg_temp.re_prova('32_upd_ric',
  format('UPDATE vendite.ddt_righe SET qta_operativa = 3 WHERE id = %s', pg_temp.re_fix('f2_dr')));
SELECT ok(pg_temp.re_rifiuto('32_upd_ric', 'viene da un ordine o da un reso'),
  '32) D-7: la quantita'' della riga di ri-consegna non cambia con un UPDATE (E_DDT_RIGA_EVASA_FERMA)');

-- Il verbo sulla ri-consegna: riga, ponte e fulfillment insieme.
SELECT vendite.fn_ddt_riga_correggi_qta_evasa(pg_temp.re_fix('f2_dr'), 3);
SELECT ok(
  (SELECT dr.quantita = 3 FROM vendite.ddt_righe dr WHERE dr.id = pg_temp.re_fix('f2_dr'))
  AND (SELECT rr.qta = 3 FROM vendite.resi_righe_riconsegne rr WHERE rr.ddt_riga_id = pg_temp.re_fix('f2_dr'))
  AND (SELECT f.qta_evasa = 3 FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id = pg_temp.re_fix('f2_dr'))
  AND vendite.fn_resi_riga_residuo_riconsegna(pg_temp.re_fix('f_resi_riga')) = 1
  AND pg_temp.re_stato_ordine('f') = 'PARZIALMENTE_EVASO',
  '33) D-7: il verbo porta a 3 riga, ponte e fulfillment; 1 torna da ri-consegnare, l''ordine si riapre');

SELECT pg_temp.re_prova('34_ric_oltre',
  format('SELECT vendite.fn_ddt_riga_correggi_qta_evasa(%s, 5)', pg_temp.re_fix('f2_dr')));
SELECT is((SELECT sqlstate FROM tmp_esito WHERE caso = '34_ric_oltre'), 'P0001',
  '34) D-7: oltre cio'' che resta da ri-consegnare il verbo rifiuta (guard del legame)');

SELECT pg_temp.re_prova('35_dlt_ric',
  format('DELETE FROM vendite.ddt_righe WHERE id = %s', pg_temp.re_fix('f2_dr')));
SELECT ok(
  (SELECT righe = 1 FROM tmp_esito WHERE caso = '35_dlt_ric')
  AND NOT EXISTS (SELECT 1 FROM vendite.resi_righe_riconsegne rr WHERE rr.ddt_riga_id = pg_temp.re_fix('f2_dr'))
  AND NOT EXISTS (SELECT 1 FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id = pg_temp.re_fix('f2_dr'))
  AND vendite.fn_resi_riga_residuo_riconsegna(pg_temp.re_fix('f_resi_riga')) = 4
  AND pg_temp.re_stato_ordine('f') = 'PARZIALMENTE_EVASO',
  '35) D-7: la riga di ri-consegna si toglie in bozza; ponte e fulfillment ritirati, il reso torna da ri-consegnare per 4');

-- ============================================================
-- G — D-6: nessun legame NUOVO su una bolla gia' emessa (a1 e' emessa, test 22)
-- ============================================================
SELECT pg_temp.re_prova('36a_ins_ful',
  format('INSERT INTO vendite.ordini_righe_fulfillment (ordine_riga_id, ddt_riga_id, qta_evasa, storicizza) VALUES (%s, %s, 1, false)',
         pg_temp.re_fix('a_bis_orr'), pg_temp.re_fix('a1_dr')));
SELECT pg_temp.re_prova('36b_ins_ric',
  format('INSERT INTO vendite.resi_righe_riconsegne (resi_riga_id, ddt_riga_id, qta, storicizza) VALUES (%s, %s, 1, false)',
         pg_temp.re_fix('f_resi_riga'), pg_temp.re_fix('a1_dr')));
SELECT ok(
  pg_temp.re_rifiuto('36a_ins_ful', 'non e'' piu'' in bozza')
  AND pg_temp.re_rifiuto('36b_ins_ric', 'non e'' piu'' in bozza'),
  '36) D-6: su una bolla emessa non nasce un legame nuovo, ne'' con l''ordine ne'' col reso (E_RIGA_DOC_NON_BOZZA)');

-- ============================================================
-- H — D-8: l'annullo di una bolla con legami chiede conferma
-- ============================================================
SELECT pg_temp.re_mk_ddt('h1', 'h', 10, p_qta_ordine => 10);
-- ⚠️ rev 2026-10-25 (§7, giro 5): la strada «diretta» che resta e' il verbo di
--   stato senza conferma; l'UPDATE dello stato lo ferma la porta, prima.
SELECT pg_temp.re_prova('37_annullo_diretto',
  format($q$SELECT * FROM vendite.fn_cambia_stato_ddt(%s, 'ANNULLATO')$q$, pg_temp.re_fix('h1_ddt')));
SELECT ok(pg_temp.re_rifiuto('37_annullo_diretto', 'Serve una conferma'),
  '37) D-8: l''annullo diretto di una bolla con legami e'' rifiutato (E_DOC_ANNULLO_CON_LEGAMI)');

SELECT pg_temp.re_prova('38_conferma_sbagliata',
  format('SELECT * FROM vendite.fn_annulla_ddt(%s, 0)', pg_temp.re_fix('h1_ddt')));
SELECT ok(pg_temp.re_rifiuto('38_conferma_sbagliata', 'Serve una conferma'),
  '38) D-8: una conferma che non corrisponde alle righe legate e'' rifiutata');

SELECT * FROM vendite.fn_annulla_ddt(pg_temp.re_fix('h1_ddt'), 1);
SELECT ok(
  (SELECT s.codice_interno = 'ANNULLATO' FROM vendite.ddt d
     JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id WHERE d.id = pg_temp.re_fix('h1_ddt'))
  AND NOT EXISTS (SELECT 1 FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id = pg_temp.re_fix('h1_dr'))
  AND pg_temp.re_stato_ordine('h') = 'CONFERMATO',
  '39) D-8: confermato, la bolla in bozza si annulla, il legame si ritira, l''ordine torna CONFERMATO');

SELECT pg_temp.re_mk_ddt('i1', 'i', 10, p_qta_ordine => 10, p_stato => 'EMESSO');
SELECT * FROM vendite.fn_annulla_ddt(pg_temp.re_fix('i1_ddt'), 1);
SELECT ok(
  (SELECT s.codice_interno = 'ANNULLATO' FROM vendite.ddt d
     JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id WHERE d.id = pg_temp.re_fix('i1_ddt'))
  AND NOT EXISTS (SELECT 1 FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id = pg_temp.re_fix('i1_dr'))
  AND pg_temp.re_stato_ordine('i') = 'CONFERMATO',
  '40) D-8: confermato, anche la bolla EMESSA si annulla e l''ordine torna CONFERMATO');

SELECT set_config('zeroerp.ddt_riga_ritira_legame', pg_temp.re_fix('a1_dr')::text, true);
SELECT pg_temp.re_prova('41_ritiro_a_mano',
  format('DELETE FROM vendite.ordini_righe_fulfillment WHERE ddt_riga_id = %s', pg_temp.re_fix('a1_dr')));
SELECT set_config('zeroerp.ddt_riga_ritira_legame', '', true);
SELECT ok(pg_temp.re_rifiuto('41_ritiro_a_mano', 'non si scrive direttamente'),
  '41) D-8: fuori bozza la porta del ritiro accesa a mano non toglie un legame');

-- J: una bolla senza ordine, in bozza (2 pezzi), dal builder: l'annullo e' il caso.
INSERT INTO tmp_fix
SELECT 'j1_ddt', b.ddt_id
  FROM dbops.fn_pgtap_crea_ddt_senza_ordine('righe evase J', 'DRAFT',
         (SELECT r.billing_account_id FROM tmp_refs_re r),
         p_quantita => 2, p_articolo_id => (SELECT r.articolo_id FROM tmp_refs_re r),
         p_data => DATE '2026-10-02') b;
-- ⚠️ rev 2026-10-25 (§7, giro 5): dal verbo di stato, senza conferma. Il verbo
--   ritorna i movimenti (nessuno: la bolla non muove merce), quindi la sonda
--   conta UNA riga se il verbo e' passato senza errore.
SELECT pg_temp.re_prova('42_senza_legami',
  format($q$SELECT count(*) FROM vendite.fn_cambia_stato_ddt(%s, 'ANNULLATO')$q$, pg_temp.re_fix('j1_ddt')));
SELECT is((SELECT righe FROM tmp_esito WHERE caso = '42_senza_legami'), 1,
  '42) una bolla senza legami si annulla come prima, senza conferma');

-- ============================================================
-- 43) ⚠️ La porta senza il proprietario. ROSSO DA OWNER, VERDE COME APP.
-- ============================================================
SELECT set_config('zeroerp.ddt_riga_correggi_qta', pg_temp.re_fix('d1_dr')::text, true);
SELECT pg_temp.re_prova('43_porta_a_mano',
  format('UPDATE vendite.ddt_righe SET qta_operativa = 2 WHERE id = %s', pg_temp.re_fix('d1_dr')));
SELECT set_config('zeroerp.ddt_riga_correggi_qta', '', true);
SELECT ok(pg_temp.re_rifiuto('43_porta_a_mano', 'viene da un ordine o da un reso'),
  '43) la GUC accesa a mano non apre la porta: serve anche il proprietario della tabella');

SELECT * FROM finish();
ROLLBACK;
