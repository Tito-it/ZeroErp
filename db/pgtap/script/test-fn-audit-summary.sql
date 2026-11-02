-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_audit_summary(p_audit_source_code, p_storico_id)
--   (Fase 5 P1 2026-04-29).
--
-- Strategia:
--   - 4 guard sul contratto parametri.
--   - 1 source inesistente.
--   - 1 storico_id inesistente.
--   - 1 smoke test "happy path" su una storico row esistente
--     (verifica struttura jsonb ritornato; il contenuto specifico del
--     diff dipende dai dati reali e non e' assertabile portabile in CI).
--
-- Niente SAVEPOINT (azzera il counter pgTAP).
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

-- =========================================================
-- I 6 errori sollevati dalla fn passano per
-- script.fn_log_and_raise_error(): il messaggio finale viene letto da
-- config.messaggi_errore (codici 406-408) con sostituzione %s. I
-- pattern throws_like matchano sottostringhe stabili dei messaggi
-- italiani; cambiare un messaggio nel CSV richiede aggiornare anche
-- questi pattern (caso noto, accettato per i18n).
-- =========================================================

-- =========================================================
-- 1..2) Guard p_audit_source_code (codice 406)
-- =========================================================
SELECT throws_like(
    $$ SELECT script.fn_audit_summary(NULL::text, 1::bigint) $$,
    '%p_audit_source_code non valido%',
    '1) audit_source_code NULL -> raise E_AUDIT_SUMMARY_PARAM_NON_VALIDO'
);

SELECT throws_like(
    $$ SELECT script.fn_audit_summary('   '::text, 1::bigint) $$,
    '%p_audit_source_code non valido%',
    '2) audit_source_code blank -> raise E_AUDIT_SUMMARY_PARAM_NON_VALIDO'
);

-- =========================================================
-- 3..4) Guard p_storico_id (codice 406)
-- =========================================================
SELECT throws_like(
    $$ SELECT script.fn_audit_summary('user_override_aree'::text, NULL::bigint) $$,
    '%p_storico_id non valido%',
    '3) storico_id NULL -> raise E_AUDIT_SUMMARY_PARAM_NON_VALIDO'
);

SELECT throws_like(
    $$ SELECT script.fn_audit_summary('user_override_aree'::text, 0::bigint) $$,
    '%p_storico_id non valido%',
    '4) storico_id <= 0 -> raise E_AUDIT_SUMMARY_PARAM_NON_VALIDO'
);

-- =========================================================
-- 5) Source inesistente -> codice 407 E_AUDIT_SOURCE_NON_TROVATO
-- =========================================================
SELECT throws_like(
    $$ SELECT script.fn_audit_summary('source_che_non_esiste_mai'::text, 1::bigint) $$,
    '%non trovato in dbops.audit_sources%',
    '5) audit_source_code non registrato -> raise E_AUDIT_SOURCE_NON_TROVATO'
);

-- =========================================================
-- 6) Storico_id inesistente -> codice 408 E_AUDIT_SNAPSHOT_NON_TROVATO
-- =========================================================
SELECT throws_like(
    $$ SELECT script.fn_audit_summary('user_override_aree'::text, 999999999::bigint) $$,
    '%snapshot non trovato%',
    '6) storico_id non presente in storico.user_override_aree -> raise E_AUDIT_SNAPSHOT_NON_TROVATO'
);

-- =========================================================
-- 7) Smoke test happy path: cerco UNA storico row esistente fra
--    le audit_sources note (4 candidati con copertura tipica:
--    identita_digitali via backfill multi-face, profili_accesso_*
--    via cutover permessi). Verifico che il ritorno sia jsonb con
--    chiavi 'summary' e 'diff' (contratto pubblico).
--
--    Skip soft se nessuna delle 4 storico ha dati (CI vergine).
--    Pattern §4.ter: SELECT CASE ... THEN ok ELSE skip END (no
--    PERFORM ok dentro DO: pgTAP traccia il counter dei test
--    solo via SELECT top-level).
-- =========================================================

-- Pre-calcolo: prima coppia (code, storico_id) trovata con dati.
-- Modello legacy profili_reparto_* dismesso il 2026-05-04: i candidati
-- sono ora identita_digitali e le 3 storico del nuovo modello
-- profili_accesso_aree/_azioni/_bindings.
CREATE TEMP TABLE _t_smoke AS
SELECT *
  FROM (
      SELECT 'identita_digitali'::text AS code,
             (SELECT min(id) FROM storico.identita_digitali) AS storico_id
       UNION ALL
      SELECT 'profili_accesso_aree',
             (SELECT min(id) FROM storico.profili_accesso_aree)
       UNION ALL
      SELECT 'profili_accesso_azioni',
             (SELECT min(id) FROM storico.profili_accesso_azioni)
       UNION ALL
      SELECT 'profili_accesso_bindings',
             (SELECT min(id) FROM storico.profili_accesso_bindings)
  ) c
 WHERE storico_id IS NOT NULL
 ORDER BY storico_id
 LIMIT 1;

-- Materializza il risultato per evitare chiamate multiple alla fn.
CREATE TEMP TABLE _t_smoke_result AS
SELECT CASE
    WHEN (SELECT count(*) FROM _t_smoke) = 0 THEN NULL::jsonb
    ELSE script.fn_audit_summary(
        (SELECT code FROM _t_smoke),
        (SELECT storico_id FROM _t_smoke)
    )
END AS result;

SELECT CASE
    WHEN (SELECT result FROM _t_smoke_result) IS NULL THEN
        skip('Nessuna storico tra i 3 candidati ha dati (CI vergine)', 1)
    ELSE
        ok(
            (SELECT result FROM _t_smoke_result) ?& ARRAY['summary','diff']
            AND jsonb_typeof((SELECT result -> 'diff' FROM _t_smoke_result)) = 'array',
            '7) Smoke test happy path: ritorno jsonb con chiavi {summary, diff[]}'
        )
END;

SELECT * FROM finish();
ROLLBACK;
