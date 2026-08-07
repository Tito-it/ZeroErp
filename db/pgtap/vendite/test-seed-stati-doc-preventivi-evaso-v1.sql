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
