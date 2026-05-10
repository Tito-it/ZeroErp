-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: seed stato EVASO + transizione automatica ACCETTATO → EVASO
-- ------------------------------------------------------------
-- Indice test (1..4):
-- 1) Stato EVASO esiste in config.stati_doc_preventivi con codice_interno='EVASO', attivo=TRUE
-- 2) Stato EVASO ha ordine=45 (tra ACCETTATO=40 e RIFIUTATO=50)
-- 3) Transizione ACCETTATO → EVASO esiste con manuale=false
-- 4) Nessuna transizione in uscita da EVASO (stato terminale)
-- ------------------------------------------------------------

BEGIN;
SELECT plan(4);

-- ============================================================
-- TEST 1) Stato EVASO esiste e attivo
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM config.stati_doc_preventivi
    WHERE codice_interno = 'EVASO'
      AND codice = 'EVASO'
      AND attivo IS TRUE
  ),
  'config.stati_doc_preventivi: EVASO esiste con codice_interno=EVASO, attivo=TRUE'
);

-- ============================================================
-- TEST 2) Ordine corretto (45, subito dopo ACCETTATO=40)
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM config.stati_doc_preventivi
    WHERE codice_interno = 'EVASO'
      AND ordine = 45
  ),
  'config.stati_doc_preventivi: EVASO ha ordine=45 (dopo ACCETTATO=40, prima di RIFIUTATO=50)'
);

-- ============================================================
-- TEST 3) Transizione ACCETTATO → EVASO con manuale=false
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM config.transizioni_stati_preventivi t
    JOIN config.stati_doc_preventivi sd ON sd.id = t.stato_da_id AND sd.codice_interno = 'ACCETTATO'
    JOIN config.stati_doc_preventivi sa ON sa.id = t.stato_a_id AND sa.codice_interno = 'EVASO'
    WHERE t.attivo IS TRUE
      AND (t.meta->>'manuale')::boolean IS FALSE
  ),
  'config.transizioni_stati_preventivi: ACCETTATO → EVASO esiste con manuale=false'
);

-- ============================================================
-- TEST 4) Nessuna transizione in uscita da EVASO (stato terminale)
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM config.transizioni_stati_preventivi t
    JOIN config.stati_doc_preventivi sd ON sd.id = t.stato_da_id AND sd.codice_interno = 'EVASO'
  ),
  'config.transizioni_stati_preventivi: nessuna transizione in uscita da EVASO (stato terminale)'
);

SELECT * FROM finish();
ROLLBACK;
