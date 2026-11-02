-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: l'ASSUNZIONE del ponte di ri-consegna — §23.3 di
--       brief-design-partita-merce-generalizzata.md
--
-- Elenco test (plan 2):
--   1) COPERTURA della misura: quanti ponti esistono (se zero, skip
--      dichiarato invece di un verde per sottrazione)
--   2) ⭐ L'INVARIANTE: nessun ponte copre MENO della quantita' della sua
--      riga di DDT
--
-- ── PERCHE' ESISTE ──────────────────────────────────────────────────────
--
--   `vw_partite_merce` marca `e_riconsegna` con un EXISTS: basta UN legame in
--   `resi_righe_riconsegne` perche' l'INTERA riga di DDT sia dichiarata
--   ri-consegna, e quindi esclusa dal conto (`differenza` NULL) — giusto,
--   perche' quei pezzi sono gia' contati sulla partita d'origine.
--
--   ⚠️ Regge finche' il ponte copre TUTTA la riga. Se un domani
--   `fn_genera_ddt_riconsegna` (o una riga costruita a mano) mettesse sullo
--   stesso rigo un po' di merce resa e un po' di merce NUOVA, la parte nuova
--   sparirebbe dal conto senza che nessuno se ne accorga: non a zero,
--   proprio esclusa.
--
--   Il §19.4 lo aveva dichiarato come assunzione, verificata sui 6 ponti
--   esistenti al 2026-08-17. ⭐ Ma una dichiarazione invecchia da sola e
--   nessuno se ne accorge; un invariante fallisce il giorno in cui
--   l'assunzione cade. E' la stessa scelta fatta per la soglia degli stati
--   in test-vw-situazione-merce-ordine-v1 (test 15).
--
-- ⚠️ NON e' un guard e non vuole diventarlo: il caso misto non e' vietato dal
--   modello, e' solo non gestito dal conto. Se comparira', la decisione
--   (vietarlo, oppure spezzare la riga, oppure contare per quantita' invece
--   che per riga) va presa allora — con il caso vero davanti.
--
-- ⚠️ Runner applicativo: la misura vede cio' che lo scope del contesto pgTAP
--   vede. Il test 1 lo dichiara, cosi' un ambiente in cui il perimetro
--   nasconde tutto non passa in silenzio.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE. Senza, un fallimento a meta' lascia i dati di prova nel
--   database e rompe la corsa successiva, che vede un rosso non suo.
BEGIN;

-- ⚠️ 2. VINCOLI DIFFERITI. Scattano al COMMIT, e qui il COMMIT non arriva mai:
--   senza questa riga il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- ⚠️ 3. CONTESTO APPLICATIVO. Il ponte si legge attraverso `ddt`, che ha RLS.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(2);

-- I ponti visibili, con la quantita' coperta e quella della riga che li porta.
-- La grana e' la riga di DDT NUOVA (quella di ri-consegna): e' lei che
-- `e_riconsegna` esclude in blocco.
CREATE TEMP TABLE tmp_ponti AS
SELECT rc.ddt_riga_id            AS ddt_riga_nuova,
       SUM(rc.qta)               AS coperta,
       MIN(dr.quantita)          AS quantita_riga
  FROM vendite.resi_righe_riconsegne rc
  JOIN vendite.ddt_righe dr ON dr.id = rc.ddt_riga_id
  JOIN vendite.ddt d        ON d.id  = dr.ddt_id
 WHERE dr.attivo IS TRUE
 GROUP BY rc.ddt_riga_id;

-- ============================================================
-- 1) COPERTURA — quanto misura questo file
--    ⚠️ Senza, l'invariante sarebbe verde anche su un database dove i ponti
--    non esistono affatto: la forma giusta, la copertura zero.
-- ============================================================
SELECT CASE WHEN (SELECT COUNT(*) FROM tmp_ponti) = 0
  THEN skip('nessun ponte di ri-consegna visibile in questo contesto: l''invariante del test 2 non e'' misurato', 1)
  ELSE ok(true, '1) copertura: ci sono ponti di ri-consegna da misurare')
END;

-- ============================================================
-- 2) ⭐ L'INVARIANTE
--    Un ponte che copre MENO della riga significa merce nuova sullo stesso
--    rigo di merce ri-consegnata — e quella nuova sparisce dal conto.
-- ============================================================
SELECT is(
  (SELECT COUNT(*)::int FROM tmp_ponti WHERE coperta < quantita_riga),
  0,
  '2) ogni ponte copre TUTTA la sua riga di DDT: nessuna merce nuova sul rigo di una ri-consegna'
);

SELECT * FROM finish();
ROLLBACK;
