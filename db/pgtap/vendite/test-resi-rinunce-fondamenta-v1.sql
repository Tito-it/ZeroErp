-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: fondamenta della chiusura ri-consegna (Fase 1)
--   vendite.resi_righe_rinunce + fn_resi_riga_residuo_riconsegna
--   + trgfn_resi_rinunce_guard + trgfn_resi_riconsegne_guard ESTESO
-- Brief: brief-db-chiusura-riconsegna-reso-definitivo §4.1, §4.2-bis, §4.6.
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
-- Nota fixture: reso in DRAFT su una riga DDT esistente. I due guard NON
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
-- FIXTURE: ordine -> DDT CONSEGNATO -> reso CONFERMATO (ri-consegna)
-- ============================================================
-- Il reso nasce SEMPRE da un DDT (sorgente_tipo_id + sorgente_uid NOT NULL):
-- si riusa una riga DDT esistente, il normalize deriva destinatario/emittente.
-- resi_righe si popola con qta_operativa (il trigger qta_from_operativa calcola
-- `quantita`): passare `quantita` direttamente solleverebbe E_QTA_MISSING.
CREATE TEMP TABLE tmp_refs_rin AS
SELECT
  dr.id                                                      AS ddt_riga_id,
  dr.articolo_id,
  dr.descrizione,
  dr.uom_operativa_id,
  dr.factor_to_base,
  d.uid                                                      AS ddt_uid,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'DDT_VENDITA' AND s.attivo LIMIT 1) AS sorgente_ddt_id,
  (SELECT s.id FROM config.stati_doc_reso s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo LIMIT 1)   AS stato_reso_draft_id,
  -- Tipo reso che RIAPRE il residuo (= per ri-consegna): e' il solo tipo su cui
  -- la rinuncia ha senso, ed e' quello che i due guard pretendono.
  (SELECT tr.id FROM config.tipi_reso tr
    WHERE tr.riapre_residuo IS TRUE AND tr.attivo IS TRUE ORDER BY tr.id LIMIT 1) AS tipo_reso_ric_id
FROM vendite.ddt_righe dr
JOIN vendite.ddt d ON d.id = dr.ddt_id
JOIN config.stati_doc_ddt sd ON sd.id = d.stato_doc_ddt_id
-- Il DDT sorgente DEVE essere CONSEGNATO: trgfn_resi_guard_ddt_consegnato
-- ammette resi solo da li' (e' anche la precondizione del flip DDT->RESO).
WHERE dr.attivo IS TRUE
  AND sd.codice_interno = 'CONSEGNATO'
  -- ...e deve avere ancora CAPIENZA di reso: trgfn_resi_righe_guard_quantita
  -- limita il reso a (consegnato - gia' reso). Si prende la riga con la
  -- capienza maggiore; ne servono >= 3 per l'aritmetica dei test 7-10.
  AND dr.quantita - COALESCE((SELECT SUM(rr.quantita) FROM vendite.resi_righe rr
                               WHERE rr.ddt_riga_id = dr.id AND rr.attivo IS TRUE), 0) >= 3
ORDER BY dr.quantita - COALESCE((SELECT SUM(rr.quantita) FROM vendite.resi_righe rr
                                  WHERE rr.ddt_riga_id = dr.id AND rr.attivo IS TRUE), 0) DESC,
         dr.id
LIMIT 1;

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
         x.articolo_id, x.uom_operativa_id, x.factor_to_base
    INTO r
    FROM tmp_refs_rin x
    JOIN vendite.ddt_righe dr ON dr.id = x.ddt_riga_id
    JOIN vendite.ddt d ON d.id = dr.ddt_id;
  -- Il file pesca la riga d'origine dai dati: se non c'e' (database da zero)
  -- la fixture si ferma qui, e i test lo dicono al 6-bis come prima.
  IF NOT FOUND THEN
    RETURN;
  END IF;
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

CREATE TEMP TABLE tmp_reso_rin AS
WITH ins AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid,
                            storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id, r.ddt_uid, false,
         jsonb_build_object('test_scope', 'pgtap_resi_rinunce')
  FROM tmp_refs_rin r
  RETURNING id)
SELECT id AS reso_id FROM ins;

-- Riga reso da 3 (unita' operativa), tipo ri-consegna. Il reso resta in DRAFT:
-- i guard dei ponti non filtrano lo stato del reso, l'invariante di copertura
-- vale comunque. La conferma e' materia della madre (Fase 2).
-- Base 3 e non 10: e' la capienza di reso realmente disponibile sui DDT
-- consegnati di dev. L'aritmetica sotto e' scalata di conseguenza; il
-- discriminante del test 8 regge identico.
CREATE TEMP TABLE tmp_riga_rin AS
WITH ins AS (
  INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
                                  articolo_id,
                                  descrizione, qta_operativa, uom_operativa_id,
                                  factor_to_base, tipo_reso_id, attivo, storicizza)
  SELECT (SELECT reso_id FROM tmp_reso_rin), 1, r.ddt_riga_id,
         -- ⚠️ `ordine_riga_id` va RICAVATO dal fulfillment, non omesso.
         -- Prima del 2026-08-17 questa fixture lo lasciava vuoto e passava:
         -- la riga di DDT che sceglie dai dati di dev evade un ordine, quindi
         -- il reso risultava su merce ordinata senza riferimento all'ordine —
         -- e in quella condizione `fn_ordine_riga_qta_riconsegna` non riapre
         -- il residuo, cioe' la merce torna e l'ordine non se ne accorge.
         -- Dal guard trgfn_resi_righe_guard_origine_coerente (20260817-13)
         -- quella riga non e' piu' scrivibile. NULL resta corretto solo se la
         -- riga di DDT non evade nulla, ed e' il senso del sotto-select.
         (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f
           WHERE f.ddt_riga_id = r.ddt_riga_id ORDER BY f.id LIMIT 1),
         r.articolo_id,
         r.descrizione, 3.000000, r.uom_operativa_id, r.factor_to_base,
         r.tipo_reso_ric_id, true, false
  FROM tmp_refs_rin r
  RETURNING id)
SELECT id AS resi_riga_id FROM ins;

-- Precondizione esplicita: se i dati di dev non offrissero una riga DDT con
-- capienza 3, il fixture fallirebbe QUI in modo leggibile invece di far
-- fallire i test 7-10 con numeri incomprensibili (fail-visible).
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
