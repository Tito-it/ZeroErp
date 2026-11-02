-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_get_lotto_segnalazioni_summary v2 (changeset 20260223-02)
-- ------------------------------------------------------------
-- Indice test (1..6):
-- 1) Funzione fn_get_lotto_segnalazioni_summary presente
-- 2) Lotto inesistente: funzione restituisce una riga
-- 3) Lotto inesistente: fatture_critical_count = 0
-- 4) Lotto inesistente: lotto_info_count = 0
-- 5) Lotto inesistente: fatture_stato_esecuzione_errore_count = 0
-- 6) Nuova colonna fatture_stato_esecuzione_errore_count presente in output
-- 7) Colonna `fermo` (D-1, 2026-09-19) presente, UNDICESIMA e ultima: il
--    backend legge la riga per posizione. Fino al 19-09 l'ultima era la decima,
--    esiti_stato_esecuzione_errore_count (D2, 2026-09-12): il pin si sposta con
--    la colonna, la ragione resta.
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

SELECT plan(7);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_get_lotto_segnalazioni_summary'
  ),
  'Funzione fn_get_lotto_segnalazioni_summary presente'
);

SELECT is(
  (
    SELECT COUNT(*)
    FROM vendite.fn_get_lotto_segnalazioni_summary(999999999)
  ),
  1::bigint,
  'Lotto inesistente: funzione restituisce una riga'
);

SELECT is(
  (
    SELECT fatture_critical_count
    FROM vendite.fn_get_lotto_segnalazioni_summary(999999999)
  ),
  0::bigint,
  'Lotto inesistente: fatture_critical_count = 0'
);

SELECT is(
  (
    SELECT lotto_info_count
    FROM vendite.fn_get_lotto_segnalazioni_summary(999999999)
  ),
  0::bigint,
  'Lotto inesistente: lotto_info_count = 0'
);

SELECT is(
  (
    SELECT fatture_stato_esecuzione_errore_count
    FROM vendite.fn_get_lotto_segnalazioni_summary(999999999)
  ),
  0::bigint,
  'Lotto inesistente: fatture_stato_esecuzione_errore_count = 0'
);

SELECT ok(
  (
    SELECT to_jsonb(x) ? 'fatture_stato_esecuzione_errore_count'
    FROM vendite.fn_get_lotto_segnalazioni_summary(999999999) AS x
  ),
  'Nuova colonna fatture_stato_esecuzione_errore_count presente in output'
);

-- 7) D-1 (brief-db-osservabilita-lotto-fermo-r6-indici, changeSet
--    20260919-02): il verdetto `fermo` esiste ed e' in CODA, undicesimo, dopo
--    il decimo conteggio (D2, 20260912-16). La posizione non e' estetica: il
--    backend mappa la riga per posizione, e una colonna in mezzo farebbe
--    scivolare le altre senza che niente protesti.
SELECT is(
  (
    SELECT a.proargnames[array_upper(a.proargnames, 1) - 1] || ' < ' ||
           a.proargnames[array_upper(a.proargnames, 1)]
      FROM pg_proc a JOIN pg_namespace n ON n.oid = a.pronamespace
     WHERE n.nspname = 'vendite' AND a.proname = 'fn_get_lotto_segnalazioni_summary'
  ),
  'esiti_stato_esecuzione_errore_count < fermo',
  'Colonna fermo presente in output, undicesima e ULTIMA, dopo esiti_stato_esecuzione_errore_count'
);

SELECT * FROM finish();
ROLLBACK;

