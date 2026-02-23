-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
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
-- ------------------------------------------------------------

BEGIN;
SELECT plan(6);

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

SELECT * FROM finish();
ROLLBACK;

