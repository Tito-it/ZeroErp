-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: fondamenta della chiusura ri-consegna (Fase 1)
--   vendite.resi_righe_rinunce + fn_resi_riga_residuo_riconsegna
--   + trgfn_resi_rinunce_guard + trgfn_resi_riconsegne_guard ESTESO
-- Brief: brief-db-chiusura-riconsegna-reso-definitivo §4.1, §4.2-bis, §4.6.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): il reso dal builder dbops.fn_pgtap_crea_reso, in DRAFT, su una bolla da ordine costruita: la fixture pescava dai dati (riga di bolla e tipo di reso) ed era rossa in partenza; restano scritti a mano la bolla di ri-consegna in bozza e i ponti (riconsegne, rinunce), che sono il caso.
--
-- COSA PRESIDIA: l'invariante condiviso dalle DUE uscite di una riga reso per
-- ri-consegna — ri-spedire al cliente oppure dichiarare la quota definitiva
-- (rinuncia):
--
--     quantita >= Sigma riconsegnate + Sigma rinunciate
--
-- Le due uscite consumano la STESSA copertura, quindi l'invariante va
-- presidiato dai due lati: il guard delle rinunce (nuovo) e quello delle
-- ri-consegne (esteso il 2026-07-26). Il test 8 e' il discriminante: prima
-- dell'estensione il guard gemello sommava solo le riconsegne e avrebbe
-- lasciato ri-spedire merce gia' rinunciata.
--
-- Nota fixture: reso in DRAFT su una bolla da ordine costruita. I due guard NON
-- filtrano lo stato del reso: l'invariante di copertura vale comunque, e la
-- conferma e' materia della madre. Le rinunce si inseriscono DIRETTAMENTE sul
-- ponte: fn_chiudi_riconsegna_reso e' Fase 2, qui si testano le fondamenta.
-- ------------------------------------------------------------
-- Indice test (1..11):
--   1  tabella vendite.resi_righe_rinunce presente
--   2  nessuna UNIQUE su resi_riga_id (rinunce ripetute lecite, §4.1-bis)
--   3  indice su resi_riga_id presente (helper: SUM per riga)
--   4  fn_resi_riga_residuo_riconsegna presente
--   5  helper: parametro invalido -> errore parlante
--   6  helper: riga inesistente -> 0 (non errore)
--   6b fixture: riga reso da 10 in unita' base
--   7  helper: residuo = quantita - Sigma ric - Sigma rin
--   8  [IL PUNTO] ri-consegna che eccede il residuo TENENDO CONTO delle
--      rinunce -> rifiutata (guard gemello esteso)
--   9  over-rinuncia -> rifiutata
--  10  rinunce ripetute sulla stessa riga -> ammesse
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

SELECT plan(11);

-- ============================================================
-- 1..4 STRUTTURA
-- ============================================================
SELECT has_table('vendite', 'resi_righe_rinunce',
    '1) tabella vendite.resi_righe_rinunce presente');

-- La gemella ha uq_resi_riconsegne_pair perche' ogni ri-consegna punta a una
-- riga DDT. La rinuncia non ha secondo termine: una UNIQUE su resi_riga_id
-- vieterebbe le rinunce ripetute, che sono il caso d'uso.
SELECT is(
  (SELECT count(*)::int
     FROM pg_index i
     JOIN pg_class c ON c.oid = i.indrelid
     JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite'
      AND c.relname = 'resi_righe_rinunce'
      AND i.indisunique
      AND i.indnatts = 1
      AND i.indkey[0] = (SELECT attnum FROM pg_attribute
                          WHERE attrelid = c.oid AND attname = 'resi_riga_id')),
  0,
  '2) nessuna UNIQUE sul solo resi_riga_id (rinunce ripetute lecite)');

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_indexes
     WHERE schemaname = 'vendite'
       AND tablename = 'resi_righe_rinunce'
       AND indexdef LIKE '%(resi_riga_id)%'
  ),
  '3) indice su resi_riga_id presente (helper fa SUM per riga)');

SELECT has_function('vendite', 'fn_resi_riga_residuo_riconsegna',
    '4) vendite.fn_resi_riga_residuo_riconsegna presente');

-- ============================================================
-- 5-6) Helper: guard parametro e riga inesistente
-- ============================================================
SELECT throws_ok(
  $$ SELECT vendite.fn_resi_riga_residuo_riconsegna(0) $$,
  'P0001', NULL,
  '5) helper: parametro invalido -> errore parlante');

-- Riga inesistente = 0, non errore: la fn e' letta da viste che la valutano
-- su insiemi in movimento, un raise le farebbe fallire per una riga cancellata.
SELECT is(
  vendite.fn_resi_riga_residuo_riconsegna(999999999),
  0::numeric,
  '6) helper: riga inesistente -> 0 (non errore)');

-- ============================================================
-- FIXTURE: ordine -> DDT CONSEGNATO -> reso DRAFT (ri-consegna)
-- ============================================================
-- ⛔ rev 2026-10-25 (brief-db-pgtap-reso-costruito): la fixture si COSTRUISCE.
--   Prima pescava una riga di bolla consegnata con capienza >= 3 fra i dati
--   del database e il tipo di reso col primo `riapre_residuo` per id: su uno
--   scratch senza bolle la riga del reso nasceva vuota (6-bis «have NULL»), e
--   il tipo pescato non era quello di ri-consegna (il ponte del test 7 moriva
--   su «Aggancio ri-consegna ammesso solo su righe reso di tipo ri-consegna»).
-- Il reso dal builder: bolla da ordine consegnata (10 pezzi), riga del reso
-- da 3 in unita' operativa, tipo RESO_PER_RICONSEGNA, riga d'ordine dal
-- legame. Resta in DRAFT: i guard dei ponti non filtrano lo stato del reso,
-- l'invariante di copertura vale comunque. La conferma e' materia della madre
-- (Fase 2).
CREATE TEMP TABLE tmp_reso_rin AS
SELECT * FROM dbops.fn_pgtap_crea_reso('resi_rinunce', NULL, 3, 'RESO_PER_RICONSEGNA', 'DRAFT');

CREATE TEMP TABLE tmp_riga_rin AS SELECT resi_riga_id FROM tmp_reso_rin;

-- ⭐ rev 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine, D-6/D-7): il ponte
--   di ri-consegna punta a una riga di una bolla di RI-CONSEGNA, e un legame
--   nasce solo con la bolla in bozza (lock delle righe montato sul ponte). Fino
--   a quel giorno la fixture lo scriveva sulla riga del DDT d'ORIGINE, gia'
--   consegnato: una forma che nessuna madre produce e che ora il lock rifiuta.
--   La bolla di destinazione e' una bozza dello stesso cliente, con una riga
--   dello stesso articolo.
CREATE TEMP TABLE tmp_ddt_ric AS SELECT NULL::bigint AS ddt_id, NULL::bigint AS ddt_riga_id;
DO $ric$
DECLARE r RECORD; v_ddt bigint; v_dr bigint;
BEGIN
  SELECT d.destinatario_soggetto_ruolo_id, d.billing_account_id, d.valuta_id, d.emittente_fiscale_id,
         dr.articolo_id, dr.uom_operativa_id, dr.factor_to_base
    INTO STRICT r
    FROM tmp_reso_rin x
    JOIN vendite.ddt_righe dr ON dr.id = x.ddt_riga_id
    JOIN vendite.ddt d ON d.id = dr.ddt_id;
  INSERT INTO vendite.ddt (data, stato_doc_ddt_id, destinatario_soggetto_ruolo_id, billing_account_id,
                           valuta_id, emittente_fiscale_id, storicizza, meta)
  VALUES (script.fn_data_operativa(),
          (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno = 'DRAFT' AND s.attivo LIMIT 1),
          r.destinatario_soggetto_ruolo_id, r.billing_account_id, r.valuta_id, r.emittente_fiscale_id,
          false, jsonb_build_object('test_scope', 'pgtap_resi_rinunce'))
  RETURNING id INTO v_ddt;
  INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa,
                                 uom_operativa_id, factor_to_base, storicizza, meta)
  VALUES (v_ddt, 1, r.articolo_id, 'ri-consegna pgTAP', 1, r.uom_operativa_id, r.factor_to_base,
          false, jsonb_build_object('test_scope', 'pgtap_resi_rinunce'))
  RETURNING id INTO v_dr;
  UPDATE tmp_ddt_ric SET ddt_id = v_ddt, ddt_riga_id = v_dr;
END $ric$;

-- Precondizione esplicita: se la fixture non costruisse la riga da 3, il file
-- fallirebbe QUI in modo leggibile invece di far fallire i test 7-10 con
-- numeri incomprensibili (fail-visible).
SELECT is(
  (SELECT rr.quantita FROM vendite.resi_righe rr
    WHERE rr.id = (SELECT resi_riga_id FROM tmp_riga_rin)),
  3.000000::numeric,
  '6-bis) fixture: riga reso da 3 in unita'' base');

-- ============================================================
-- 7) Aritmetica dell'helper: 3 − 1 ric − 1 rin = 1
-- ============================================================
INSERT INTO vendite.resi_righe_riconsegne (resi_riga_id, ddt_riga_id, qta)
SELECT (SELECT resi_riga_id FROM tmp_riga_rin),
       (SELECT ddt_riga_id FROM tmp_ddt_ric), 1.000000;

INSERT INTO vendite.resi_righe_rinunce (resi_riga_id, qta, note)
SELECT (SELECT resi_riga_id FROM tmp_riga_rin), 1.000000, 'pgtap fondamenta';

SELECT is(
  vendite.fn_resi_riga_residuo_riconsegna((SELECT resi_riga_id FROM tmp_riga_rin)),
  1.000000::numeric,
  '7) helper: residuo = quantita - Sigma riconsegnate - Sigma rinunciate');

-- ============================================================
-- 8) IL PUNTO: la ri-consegna deve tenere conto delle RINUNCE.
--    Residuo effettivo 1 (3 - 1 ric - 1 rin). Ri-spedirne 2 va rifiutato.
--    Col guard gemello NON esteso il calcolo sarebbe 3 - 1 = 2 -> PASSEREBBE,
--    portando Sigma ric + Sigma rin = 4 > 3 (invariante violato).
--    E' l'unico test che distingue il guard esteso da quello vecchio.
-- ============================================================
SELECT throws_ok(
  format($$ INSERT INTO vendite.resi_righe_riconsegne (resi_riga_id, ddt_riga_id, qta)
            VALUES (%s, %s, 2.000000) $$,
         (SELECT resi_riga_id FROM tmp_riga_rin),
         (SELECT ddt_riga_id FROM tmp_ddt_ric)),
  'P0001', NULL,
  '8) ri-consegna oltre il residuo AL NETTO delle rinunce -> rifiutata');

-- ============================================================
-- 9-10) Guard rinunce: over-rinuncia e ripetibilita'
-- ============================================================
SELECT throws_ok(
  format($$ INSERT INTO vendite.resi_righe_rinunce (resi_riga_id, qta)
            VALUES (%s, 2.000000) $$,
         (SELECT resi_riga_id FROM tmp_riga_rin)),
  'P0001', NULL,
  '9) over-rinuncia (2 su residuo 1) -> rifiutata');

-- Rinuncia ripetuta sulla stessa riga: ammessa (nessuna UNIQUE), residuo 1 -> 0
SELECT lives_ok(
  format($$ INSERT INTO vendite.resi_righe_rinunce (resi_riga_id, qta)
            VALUES (%s, 1.000000) $$,
         (SELECT resi_riga_id FROM tmp_riga_rin)),
  '10) rinuncia ripetuta sulla stessa riga reso -> ammessa');

SELECT * FROM finish();
ROLLBACK;
