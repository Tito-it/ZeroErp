-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il vocabolario dei due cataloghi di stato contabili
--
-- Presidia i passi S1-1, S1-2 e S1-21 del lotto 2 del cantiere incassi
--   (brief-db-posting-e-abbinamento-rata.md §2.1).
--
-- Elenco test (plan 10):
-- 1) STORNATA è RITIRATA con obsoleto_dal, e resta ATTIVA
-- 2) Nessun altro stato di riga è ritirato
-- 3) 🔴 S1-21: SCARTATA NON è più uno stato finale
-- 4) richiede_abbinamento è vero SOLO su ABBINATA e POSTATA
-- 5) ⚠️ richiede_abbinamento non è derivabile da is_final
-- 7) ⭐ lavorata: non lavorati SOLO IMPORTATA e DA_ABBINARE (D20-a)
-- 8) ⭐ is_registrabile: SOLO VALIDATA (D20-d)
-- 9) ⭐ righe_lavorabili: false SOLO su ANNULLATA (D-1, 2026-09-30)
-- 10) ⚠️ righe_lavorabili non è derivabile da is_final
-- 6) C-8: codice_interno è obbligatorio su entrambi i cataloghi
--
-- Scopo:
--  - il ritiro si fa con `obsoleto_dal`, MAI con `attivo = false`: quello
--    spegnerebbe la riga e romperebbe le istanze che la referenziano. Il test 1
--    verifica ENTRAMBE le metà, perché ritirare spegnendo è l'errore facile;
--  - il test 3 presidia una CONTRADDIZIONE sanata: il catalogo marcava SCARTATA
--    finale mentre la matrice ammette SCARTATA -> SOSPESA. Un catalogo che
--    dichiara una cosa mentre la matrice ne permette un'altra insegna il falso;
--  - il test 5 è il presidio della decisione di forma: se un giorno qualcuno
--    volesse derivare l'obbligo di abbinamento da `is_final`, questo test dice
--    perché non si può — POSTATA e SCARTATA sono entrambe finali e vogliono cose
--    opposte.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- 1) STORNATA: ritirata, ma NON spenta
-- ============================================================
SELECT is(
  (SELECT (obsoleto_dal IS NOT NULL AND attivo IS TRUE)
     FROM pagamenti.vendite_contabili_righe_stati
    WHERE codice_interno = 'STORNATA'),
  true,
  'STORNATA e'' ritirata con obsoleto_dal e resta ATTIVA: il ritiro non spegne la riga'
);

-- ============================================================
-- 2) E nessun altro è ritirato
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM pagamenti.vendite_contabili_righe_stati
    WHERE obsoleto_dal IS NOT NULL),
  1,
  'Un solo stato di riga e'' ritirato, ed e'' STORNATA'
);

-- ============================================================
-- 3) 🔴 S1-21 — SCARTATA non è finale
--   Da lì si torna a SOSPESA per riprendere in mano la riga.
-- ============================================================
SELECT is(
  (SELECT is_final FROM pagamenti.vendite_contabili_righe_stati
    WHERE codice_interno = 'SCARTATA'),
  false,
  'SCARTATA non e'' uno stato finale: la matrice ammette SCARTATA -> SOSPESA'
);

-- ============================================================
-- 4) richiede_abbinamento: solo ABBINATA e POSTATA
-- ============================================================
SELECT is(
  (SELECT array_agg(codice_interno ORDER BY codice_interno)
     FROM pagamenti.vendite_contabili_righe_stati
    WHERE richiede_abbinamento),
  ARRAY['ABBINATA', 'POSTATA']::text[],
  'Pretendono fattura e cliente solo ABBINATA e POSTATA (D14-a)'
);

-- ============================================================
-- 5) ⚠️ E non è derivabile da is_final
--   POSTATA e SCARTATA sono entrambe... no: dal test 3 SCARTATA non è più
--   finale. Il caso che regge la decisione è l'altro verso: ABBINATA pretende
--   l'abbinamento e NON è finale. Una regola costruita su is_final la
--   mancherebbe del tutto.
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM pagamenti.vendite_contabili_righe_stati
    WHERE richiede_abbinamento AND is_final IS FALSE),
  1,
  'Almeno uno stato pretende l''abbinamento senza essere finale: is_final non basta a derivarlo'
);

-- ============================================================
-- 6) C-8 — codice_interno obbligatorio su entrambi i cataloghi
--   È la chiave con cui TUTTO il codice risolve questi stati, e il lock su
--   quella colonna impedisce di valorizzarla dopo.
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM information_schema.columns
    WHERE table_schema = 'pagamenti'
      AND table_name IN ('vendite_contabili_stati', 'vendite_contabili_righe_stati')
      AND column_name = 'codice_interno'
      AND is_nullable = 'NO'),
  2,
  'codice_interno e'' obbligatorio su tutti e due i cataloghi di stato'
);

-- ============================================================
-- 7) ⭐ D20-a — `lavorata`: non lavorati SOLO IMPORTATA e DA_ABBINARE
--   E' la bandiera che la check di validazione legge: uno stato in piu' a
--   false, o uno in meno, cambia che cosa entra in VALIDATA.
-- ============================================================
SELECT is(
  (SELECT array_agg(codice_interno ORDER BY codice_interno)
     FROM pagamenti.vendite_contabili_righe_stati
    WHERE lavorata IS NOT TRUE),
  ARRAY['DA_ABBINARE', 'IMPORTATA']::text[],
  'D20-a: sono «non lavorati» solo DA_ABBINARE e IMPORTATA — la sospesa e'' stata guardata'
);

-- ============================================================
-- 8) ⭐ D20-d — `is_registrabile`: SOLO VALIDATA
--   La madre del posting la legge al posto del letterale; il dettaglio la
--   espone per spegnere «Registra» col motivo.
-- ============================================================
SELECT is(
  (SELECT array_agg(codice_interno ORDER BY codice_interno)
     FROM pagamenti.vendite_contabili_stati
    WHERE is_registrabile),
  ARRAY['VALIDATA']::text[],
  'D20-d: si registra solo da VALIDATA, e lo dice il catalogo'
);

-- ============================================================
-- 9) ⭐ D-1 (2026-09-30) — `righe_lavorabili`: false SOLO su ANNULLATA
--   La leggono la quinta mossa del guard sulle righe, la check di
--   eliminabilita', la coda del riconciliatore e il frontend. Uno stato in
--   piu' a false congela le righe di un documento vivo; uno in meno riapre
--   quelle di un documento che «non e' mai successo».
--   brief-db-righe-distinta-annullata-fuori-dalle-code §3.
-- ============================================================
SELECT is(
  (SELECT array_agg(codice_interno ORDER BY codice_interno)
     FROM pagamenti.vendite_contabili_stati
    WHERE righe_lavorabili IS NOT TRUE),
  ARRAY['ANNULLATA']::text[],
  'D-1: le righe non si lavorano piu'' solo sotto una ANNULLATA'
);

-- ============================================================
-- 10) ⚠️ La bandiera NON e' derivabile da is_final
--   Il presidio della decisione di forma: CHIUSA e ANNULLATA sono entrambe
--   finali e vogliono cose opposte per le righe — sotto la CHIUSA la
--   registrazione tardiva e «Riprendi» restano vivi. Se un giorno qualcuno
--   volesse leggere is_final al posto della bandiera, questo test dice
--   perche' non si puo'.
-- ============================================================
SELECT is(
  (SELECT array_agg(codice_interno ORDER BY codice_interno)
     FROM pagamenti.vendite_contabili_stati
    WHERE is_final AND righe_lavorabili),
  ARRAY['CHIUSA']::text[],
  'D-1: CHIUSA e'' finale ma le sue righe si lavorano ancora — is_final non risponde alla domanda'
);

SELECT * FROM finish();
ROLLBACK;
