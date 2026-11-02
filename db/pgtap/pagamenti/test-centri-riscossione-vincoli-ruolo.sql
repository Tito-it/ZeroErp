-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: i due ruoli di pagamenti.centri_riscossione, e il seed dei centri
--
-- Presidia i passi P-1 e P-2 del lotto 1 del cantiere incassi
--   (brief-db-posting-e-abbinamento-rata.md §2.0).
--
-- ⭐ ASSERISCE IL COMPORTAMENTO, NON L'ESISTENZA DEI VINCOLI. «Il vincolo
--    esiste» verificherebbe l'ipotesi su CHI impedisce una cosa, non il fatto
--    che sia impedita — e questa tabella e' proprio quella su cui due vincoli
--    DICHIARATI non erano mai nati, quindi la lezione e' fresca.
--
-- Elenco test (plan 10):
-- 1)  Il centro interno FONDI_FATTURA esiste dopo il solo giro delle migrazioni
-- 2)  Il centro interno COMPENSAZIONI esiste dopo il solo giro delle migrazioni
-- 3)  I tre centri reali (BANCA, POSTE, CASSA) esistono e sono attivi
-- 4)  Esiste UN SOLO centro di compensazione
-- 5)  Esiste UN SOLO centro fondo-fattura
-- 6)  Nessun centro ha tutti e due i ruoli
-- 7)  🔴 C-1: un TERZO centro neutro ENTRA (col vecchio UNIQUE totale non entrava)
-- 8)  Un SECONDO centro di compensazione e' rifiutato
-- 9)  Un SECONDO centro fondo-fattura e' rifiutato
-- 10) 🔴 C-1-bis: un centro che dice si' a ENTRAMBI i ruoli e' rifiutato
--
-- Scopo:
--  - i test 1..3 presidiano il SEED (P-2): senza, su un database ricostruito da
--    zero la tabella e' vuota e non funzionano ne' i fondi fattura ne' le
--    compensazioni. Il difetto era invisibile perche' tutti i pgTAP di
--    `pagamenti` si fabbricano il centro quando non lo trovano;
--  - i test 7..10 presidiano i VINCOLI (P-1): l'unico su `is_compensazione` era
--    TOTALE su un booleano — il `where:` scritto su un `addUniqueConstraint`,
--    che quell'attributo non ha, era stato ignorato in silenzio — quindi la
--    tabella non poteva contenere piu' di DUE righe; il gemello su
--    `is_fondo_fattura` non era mai esistito; e il CHECK di esclusivita',
--    dichiarato in 20260211-21, non era mai stato eseguito.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Contesto applicativo: il test gira come gira l'applicazione (ruolo
--   OPERATORE + RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, che qui non arriva mai (si chiude in
--   ROLLBACK). Senza questa riga il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- 0) Pulizia dei residui di questo test
--   Sta DENTRO la transazione, quindi non tocca nulla in modo definitivo: serve
--   solo perche' i test 7..10 usano codici FISSI (throws_ok vuole SQL letterale,
--   non interpolabile) e un residuo li farebbe fallire con l'errore sbagliato —
--   un 23505 sul codice invece che sul ruolo.
-- ============================================================
DELETE FROM pagamenti.centri_riscossione
 WHERE meta ->> 'test_scope' = 'pgtap_centri_riscossione_ruoli';

-- ============================================================
-- 1) Il centro interno dei fondi fattura
--   E' quello che vendite.fn_sync_contabili_fondo_fattura cerca per poter
--   scrivere le righe contabili del fondo.
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM pagamenti.centri_riscossione
     WHERE codice_interno = 'FONDI_FATTURA'
       AND is_fondo_fattura
       AND attivo
  ),
  'Il centro interno FONDI_FATTURA esiste, e'' attivo e porta il proprio ruolo'
);

-- ============================================================
-- 2) Il centro interno delle compensazioni
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM pagamenti.centri_riscossione
     WHERE codice_interno = 'COMPENSAZIONI'
       AND is_compensazione
       AND attivo
  ),
  'Il centro interno COMPENSAZIONI esiste, e'' attivo e porta il proprio ruolo'
);

-- ============================================================
-- 3) I centri REALI
--   Senza di essi una contabile di incasso vero non e' creabile: i due centri
--   interni non sono cassa, sono trasferimenti dentro casa.
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM pagamenti.centri_riscossione
    WHERE codice_interno IN ('BANCA', 'POSTE', 'CASSA')
      AND attivo
      AND NOT is_compensazione
      AND NOT is_fondo_fattura),
  3,
  'I tre centri di incasso reale (BANCA, POSTE, CASSA) esistono, attivi e senza ruoli interni'
);

-- ============================================================
-- 4) Un solo centro di compensazione
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM pagamenti.centri_riscossione WHERE is_compensazione),
  1,
  'Il centro di compensazione e'' uno solo'
);

-- ============================================================
-- 5) Un solo centro fondo-fattura
--   ⭐ E' cio' che rende il LIMIT 1 di vendite.fn_sync_contabili_fondo_fattura
--   la lettura di una riga garantita, invece di una scommessa sull'ordine degli id.
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM pagamenti.centri_riscossione WHERE is_fondo_fattura),
  1,
  'Il centro dei fondi fattura e'' uno solo'
);

-- ============================================================
-- 6) I due ruoli non convivono su nessuna riga
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM pagamenti.centri_riscossione
    WHERE is_compensazione AND is_fondo_fattura),
  0,
  'Nessun centro porta tutti e due i ruoli interni'
);

-- ============================================================
-- 7) 🔴 C-1 — un TERZO centro neutro entra
--   Con il vecchio UNIQUE TOTALE su is_compensazione questa INSERT falliva:
--   esisteva gia' una riga con false, e il vincolo ne ammetteva una sola.
--   E' il test che dice che la tabella non e' piu' limitata a due righe.
-- ============================================================
SELECT lives_ok(
  $$
  INSERT INTO pagamenti.centri_riscossione
    (codice, codice_interno, descrizione, is_compensazione, is_fondo_fattura, attivo, meta)
  VALUES
    ('CRVR_NEUTRO', 'CRVR_NEUTRO', 'Centro di prova senza ruoli interni',
     false, false, true,
     '{"test_scope":"pgtap_centri_riscossione_ruoli"}'::jsonb);
  $$,
  'Un centro senza ruoli interni si aggiunge anche quando ce ne sono gia'' altri'
);

-- ============================================================
-- 8) Un secondo centro di compensazione non entra
-- ============================================================
SELECT throws_ok(
  $$
  INSERT INTO pagamenti.centri_riscossione
    (codice, codice_interno, descrizione, is_compensazione, is_fondo_fattura, attivo, meta)
  VALUES
    ('CRVR_COMP2', 'CRVR_COMP2', 'Secondo centro di compensazione',
     true, false, true,
     '{"test_scope":"pgtap_centri_riscossione_ruoli"}'::jsonb);
  $$,
  '23505',
  NULL,
  'Un secondo centro di compensazione non si aggiunge'
);

-- ============================================================
-- 9) Un secondo centro fondo-fattura non entra
-- ============================================================
SELECT throws_ok(
  $$
  INSERT INTO pagamenti.centri_riscossione
    (codice, codice_interno, descrizione, is_compensazione, is_fondo_fattura, attivo, meta)
  VALUES
    ('CRVR_FONDO2', 'CRVR_FONDO2', 'Secondo centro fondo fattura',
     false, true, true,
     '{"test_scope":"pgtap_centri_riscossione_ruoli"}'::jsonb);
  $$,
  '23505',
  NULL,
  'Un secondo centro dei fondi fattura non si aggiunge'
);

-- ============================================================
-- 10) 🔴 C-1-bis — un centro che e' due ruoli insieme non entra
--   ⚠️ Lo SQLSTATE atteso e' quello del CHECK e non quello dell'unicita' perche'
--   PostgreSQL valuta i vincoli di CHECK sulla tupla PRIMA di inserire nelle
--   chiavi: una riga che dice si' a entrambi violerebbe anche i due unici
--   parziali, ma il primo a rispondere e' il CHECK.
-- ============================================================
SELECT throws_ok(
  $$
  INSERT INTO pagamenti.centri_riscossione
    (codice, codice_interno, descrizione, is_compensazione, is_fondo_fattura, attivo, meta)
  VALUES
    ('CRVR_DOPPIO', 'CRVR_DOPPIO', 'Centro che dice si a entrambi i ruoli',
     true, true, true,
     '{"test_scope":"pgtap_centri_riscossione_ruoli"}'::jsonb);
  $$,
  '23514',
  NULL,
  'Un centro non puo'' essere compensazione e fondo fattura insieme'
);

SELECT * FROM finish();
ROLLBACK;
