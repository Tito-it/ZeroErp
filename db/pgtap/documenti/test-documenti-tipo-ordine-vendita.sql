-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: tipo documento ORDINE_VENDITA per stampa conferma d'ordine
-- ------------------------------------------------------------
-- Indice test (1..4):
--  1) Tipo documento ORDINE_VENDITA presente in documenti.tipi_documento_output
--  2) Tipo documento ORDINE_VENDITA attivo
--  3) Sorgente ORDINE_VENDITA presente e attiva in config.sorgenti (riuso)
--  4) Nessun duplicato di codice ORDINE_VENDITA su tipi_documento_output
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

-- 1) Tipo documento seedato
SELECT is(
  (SELECT COUNT(*)::int FROM documenti.tipi_documento_output
    WHERE codice = 'ORDINE_VENDITA'),
  1,
  'Tipo documento ORDINE_VENDITA presente in tipi_documento_output'
);

-- 2) Tipo documento attivo
SELECT ok(
  (SELECT attivo FROM documenti.tipi_documento_output
    WHERE codice = 'ORDINE_VENDITA'),
  'Tipo documento ORDINE_VENDITA attivo'
);

-- 3) Sorgente riusata (gia presente per push/canali) e attiva
SELECT is(
  (SELECT COUNT(*)::int FROM config.sorgenti
    WHERE codice = 'ORDINE_VENDITA' AND attivo),
  1,
  'Sorgente ORDINE_VENDITA presente e attiva in config.sorgenti'
);

-- 4) Idempotenza seed: nessun codice duplicato
SELECT is(
  (SELECT COUNT(*)::int FROM (
     SELECT codice FROM documenti.tipi_documento_output
      WHERE codice = 'ORDINE_VENDITA'
      GROUP BY codice HAVING COUNT(*) > 1
   ) d),
  0,
  'Idempotenza: nessun codice ORDINE_VENDITA duplicato'
);

SELECT * FROM finish();
ROLLBACK;
