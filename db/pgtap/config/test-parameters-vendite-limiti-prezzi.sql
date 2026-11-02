-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: seed config.parameters per L2 autorizzazioni prezzi (Sprint D).
--
-- Elenco test:
--  1) VENDITE_MAX_SCONTO_PCT presente nel seed
--  2) VENDITE_MAX_MAGGIORAZIONE_PCT presente nel seed
--  3) Default VENDITE_MAX_SCONTO_PCT = '0' (sicuro: nessuno sconto ammesso)
--  4) Default VENDITE_MAX_MAGGIORAZIONE_PCT = '0'
--  5) fn_get_parameter_full risolve VENDITE_MAX_SCONTO_PCT con default '0'
--  6) Override user personalizza il valore per VENDITE_MAX_SCONTO_PCT
--  7) Override user personalizza anche VENDITE_MAX_MAGGIORAZIONE_PCT
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
-- ============================================================
-- 1-2) Chiavi presenti nel seed
-- ============================================================
SELECT ok(
    EXISTS(
      SELECT 1
      FROM config.parameters
      WHERE code = 'VENDITE_MAX_SCONTO_PCT'
    ),
    '1) VENDITE_MAX_SCONTO_PCT presente in config.parameters'
  );
SELECT ok(
    EXISTS(
      SELECT 1
      FROM config.parameters
      WHERE code = 'VENDITE_MAX_MAGGIORAZIONE_PCT'
    ),
    '2) VENDITE_MAX_MAGGIORAZIONE_PCT presente in config.parameters'
  );
-- ============================================================
-- 3-4) Default value = '0' (sicuro)
-- ============================================================
SELECT is(
    (
      SELECT default_value
      FROM config.parameters
      WHERE code = 'VENDITE_MAX_SCONTO_PCT'
    ),
    '0'::text,
    '3) Default VENDITE_MAX_SCONTO_PCT = 0 (conservativo, admin deve override per abilitare sconti)'
  );
SELECT is(
    (
      SELECT default_value
      FROM config.parameters
      WHERE code = 'VENDITE_MAX_MAGGIORAZIONE_PCT'
    ),
    '0'::text,
    '4) Default VENDITE_MAX_MAGGIORAZIONE_PCT = 0'
  );
-- ============================================================
-- 5) fn_get_parameter_full risolve con default quando nessun override.
-- Firma: (p_code text, p_emittente_fiscale_id bigint, p_django_user_id integer,
--        p_group_ids integer[], p_session_key text, p_function_name text)
-- ============================================================
SELECT is(
    script.fn_get_parameter_full('VENDITE_MAX_SCONTO_PCT'),
    '0'::text,
    '5) fn_get_parameter_full ritorna default "0" quando nessun override'
  );
-- ============================================================
-- 6-7) Override user cambia il valore risolto
-- ============================================================
-- Setup: user di test + override.
-- Nota: parameter_overrides NON ha scope_code/scope_value: lo scope e'
-- determinato dalle colonne django_user_id/django_group_id/emittente_fiscale_id
-- valorizzate (NULL = wildcard). Unique uq_overrides_full_scope_v5 NULLS NOT
-- DISTINCT su (parameter_id, emittente_fiscale_id, django_user_id,
-- django_group_id, categoria_cliente_id, session_key, function_name).
CREATE TEMP TABLE tmp_l2_test AS
SELECT id AS user_id
FROM django.auth_user
ORDER BY id
LIMIT 1;
INSERT INTO config.parameter_overrides (
    parameter_id,
    overridden_value,
    django_user_id
  )
SELECT (
    SELECT id
    FROM config.parameters
    WHERE code = 'VENDITE_MAX_SCONTO_PCT'
  ),
  '15',
  t.user_id
FROM tmp_l2_test t
WHERE EXISTS (
    SELECT 1
    FROM tmp_l2_test
  )
-- Col vincolo v5 NULLS NOT DISTINCT (20261007-70) l'ambito e' uno: se sul DB
-- esiste gia' un override puro per questo parametro e questo ambito, lo si
-- riscrive invece di aggiungerne un secondo (prima nasceva un doppione e la
-- cascata ne sceglieva uno a caso). ROLLBACK in coda ripristina il valore.
ON CONFLICT ON CONSTRAINT uq_overrides_full_scope_v5
DO UPDATE SET overridden_value = EXCLUDED.overridden_value, attivo = true;
INSERT INTO config.parameter_overrides (
    parameter_id,
    overridden_value,
    django_user_id
  )
SELECT (
    SELECT id
    FROM config.parameters
    WHERE code = 'VENDITE_MAX_MAGGIORAZIONE_PCT'
  ),
  '5',
  t.user_id
FROM tmp_l2_test t
WHERE EXISTS (
    SELECT 1
    FROM tmp_l2_test
  )
-- Col vincolo v5 NULLS NOT DISTINCT (20261007-70) l'ambito e' uno: se sul DB
-- esiste gia' un override puro per questo parametro e questo ambito, lo si
-- riscrive invece di aggiungerne un secondo (prima nasceva un doppione e la
-- cascata ne sceglieva uno a caso). ROLLBACK in coda ripristina il valore.
ON CONFLICT ON CONSTRAINT uq_overrides_full_scope_v5
DO UPDATE SET overridden_value = EXCLUDED.overridden_value, attivo = true;
SELECT is(
    script.fn_get_parameter_full(
      'VENDITE_MAX_SCONTO_PCT',
      p_django_user_id := (
        SELECT user_id
        FROM tmp_l2_test
      )::integer
    ),
    '15'::text,
    '6) Override user VENDITE_MAX_SCONTO_PCT=15 sovrascrive default 0'
  );
SELECT is(
    script.fn_get_parameter_full(
      'VENDITE_MAX_MAGGIORAZIONE_PCT',
      p_django_user_id := (
        SELECT user_id
        FROM tmp_l2_test
      )::integer
    ),
    '5'::text,
    '7) Override user VENDITE_MAX_MAGGIORAZIONE_PCT=5 sovrascrive default 0'
  );
SELECT *
FROM finish();
ROLLBACK;