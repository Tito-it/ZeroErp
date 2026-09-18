-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test — Passo D dell'osservabilita': i registri di fatturazione e push
--   scadono, e la scadenza si scrive alla nascita.
--   Analisi: analisi-osservabilita-log.md §4 Passo D
--   ChangeSet: 20260918-29 (colonne), -30 (BB in dbops), -31 (event_log),
--              -32 (guard con ramo retention), -33 (trigger sui quattro),
--              regole 16-19 di dbops.automation_rules_tbl
--
-- ⭐ COSA PRESIDIA QUESTO FILE, IN UNA RIGA:
--     i QUATTRO registri che il giornale legge insieme (event_log,
--     fatturazione_lotti_log, fatturazione_lotti_task_runs, fatture_log) piu'
--     commesse_push_log nascono con la stessa scadenza, letta da UNA sede
--     (dbops.automation_rules_tbl) da UN trigger (dbops.trgfn_cleanup_at_alla_nascita),
--     e il guard dei log lascia passare la retention senza GUC.
--
-- ⚠️ Le regole 16-19 stanno in 80_data: i changeSet di 20_code NON le
--   precondizionano (guardrail_precondition_seed). Che ci siano lo dice il
--   test 4 — e' qui, non in un sqlCheck, che l'invariante si asserisce.
--
-- ⚠️ Tre fixture dipendono da un lotto e da una fattura dell'emittente
--   dell'operatore: su un database da zero non ci sono e i test relativi
--   skippano, DICHIARANDOLO. commesse_push_log non ha FK ne' RLS: quei test
--   girano ovunque, e sono loro a provare il BB anche in CI.
--
-- Elenco test (plan 15):
--  1) struttura: cleanup_at su tutte e quattro le tabelle
--  2) struttura: il trigger _m50_cleanup_at_ins e' montato su cinque tabelle
--  3) struttura: vendite.fn_event_log_ttl_days non esiste piu' (copia ritirata)
--  4) regole: le cinque tabelle rispondono 750 giorni (regole 15-19)
--  5) regole: una tabella senza override cade sul default *all (30 giorni)
--  6) fn_cleanup_at_params: schema/tabella vuoti → NULL, non un errore
--  7) commesse_push_log: nasce con cleanup_at = run_at + 750 giorni
--  8) commesse_push_log retrodatata: nasce gia' scaduta
--  9) fatturazione_lotti_log: cleanup_at = data_ora + 750 giorni
-- 10) fatturazione_lotti_log: DELETE di una riga VIVA rifiutato senza GUC
-- 11) fatturazione_lotti_log: il purge (dry-run) vede la riga scaduta
-- 12) fatturazione_lotti_log: DELETE di una riga SCADUTA ammesso senza GUC
-- 13) fatturazione_lotti_task_runs: cleanup_at = started_at + 750 giorni
-- 14) fatture_log: la scadenza segue l'orario RISCRITTO da a10_orario_reale
-- 15) fatture_log: il purge di un critico scaduto passa e spegne fatture.critical
--     (la conseguenza dichiarata nel changeSet -29: il critico deriva dal
--     registro e ne eredita la scadenza)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- Fixture: riferimenti dell'emittente dell'operatore (possono mancare)
-- ============================================================
CREATE TEMP TABLE _rif AS
SELECT script.fn_pgtap_emittente_sr_operatore() AS sr_id,
       (SELECT l.id
          FROM vendite.fatturazione_lotti l
         WHERE l.emittente_soggetto_ruolo_id = script.fn_pgtap_emittente_sr_operatore()
         ORDER BY l.id
         LIMIT 1) AS lotto_id,
       -- ⭐ Una fattura NON critica: il test 15 la accende e la spegne, e deve
       --   poter dire che a spegnerla e' stato il purge, non un'altra riga.
       (SELECT f.id
          FROM vendite.fatture f
         WHERE f.emittente_soggetto_ruolo_id = script.fn_pgtap_emittente_sr_operatore()
           AND f.critical IS NOT TRUE
         ORDER BY f.id
         LIMIT 1) AS fattura_id,
       (dbops.fn_cleanup_at_params('vendite', 'fatturazione_lotti_log') ->> 'ttl_days')::integer AS ttl_lotti_log,
       (dbops.fn_cleanup_at_params('vendite', 'fatture_log') ->> 'ttl_days')::integer AS ttl_fatture_log,
       (dbops.fn_cleanup_at_params('vendite', 'fatturazione_lotti_task_runs') ->> 'ttl_days')::integer AS ttl_task_runs,
       (dbops.fn_cleanup_at_params('vendite', 'commesse_push_log') ->> 'ttl_days')::integer AS ttl_push_log;

-- ============================================================
-- 1-3) Struttura
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM information_schema.columns
      WHERE table_schema = 'vendite'
        AND column_name  = 'cleanup_at'
        AND table_name IN ('fatturazione_lotti_log', 'fatture_log',
                           'fatturazione_lotti_task_runs', 'commesse_push_log')),
    4,
    '1. cleanup_at su tutte e quattro le tabelle'
);

SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger t
       JOIN pg_proc p ON p.oid = t.tgfoid
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE NOT t.tgisinternal
        AND n.nspname = 'dbops'
        AND p.proname = 'trgfn_cleanup_at_alla_nascita'
        AND t.tgrelid IN ('vendite.event_log'::regclass,
                          'vendite.fatturazione_lotti_log'::regclass,
                          'vendite.fatture_log'::regclass,
                          'vendite.fatturazione_lotti_task_runs'::regclass,
                          'vendite.commesse_push_log'::regclass)),
    5,
    '2. dbops.trgfn_cleanup_at_alla_nascita montato sui cinque registri'
);

SELECT is(
    (SELECT count(*)::int
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite' AND p.proname = 'fn_event_log_ttl_days'),
    0,
    '3. vendite.fn_event_log_ttl_days non esiste piu'': la copia e'' ritirata'
);

-- ============================================================
-- 4-6) Le regole
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM unnest(ARRAY['event_log', 'fatturazione_lotti_log', 'fatture_log',
                         'fatturazione_lotti_task_runs', 'commesse_push_log']) AS t(nome)
      WHERE (dbops.fn_cleanup_at_params('vendite', t.nome) ->> 'ttl_days')::integer = 750),
    5,
    '4. le cinque tabelle del giornale e del push rispondono 750 giorni (regole 15-19)'
);

-- ⚠️ 30 e' il default DICHIARATO della regola *all (id 11; guide/audit-e-tracciabilita §7).
--   Se un giorno cambia, cambia anche qui: il test pinna che una tabella senza
--   override cada sul default, non che il default valga 30 per sempre.
SELECT is(
    (dbops.fn_cleanup_at_params('vendite', 'fatture') ->> 'ttl_days')::integer,
    30,
    '5. una tabella senza override cade sulla regola *all (default 30 giorni)'
);

SELECT ok(
    dbops.fn_cleanup_at_params('', 'fatture_log') IS NULL
    AND dbops.fn_cleanup_at_params('vendite', NULL) IS NULL,
    '6. schema o tabella vuoti: NULL (nessuna regola), non un errore — la funzione e'' STABLE'
);

-- ============================================================
-- 7-8) commesse_push_log — senza FK ne'' RLS: gira anche in CI
-- ============================================================
CREATE TEMP TABLE _push_viva AS
WITH ins AS (
    INSERT INTO vendite.commesse_push_log (run_at, dry_run, risultato, stato)
    VALUES (now(), true, '{}'::jsonb, 'COMPLETATO')
    RETURNING id, run_at, cleanup_at
)
SELECT * FROM ins;

SELECT is(
    (SELECT p.cleanup_at FROM _push_viva p),
    (SELECT p.run_at + make_interval(days => r.ttl_push_log) FROM _push_viva p, _rif r),
    '7. commesse_push_log: cleanup_at = run_at + il TTL della regola 19'
);

CREATE TEMP TABLE _push_scaduta AS
WITH ins AS (
    INSERT INTO vendite.commesse_push_log (run_at, dry_run, risultato, stato)
    SELECT now() - make_interval(days => r.ttl_push_log + 50), true, '{}'::jsonb, 'COMPLETATO'
      FROM _rif r
    RETURNING id, cleanup_at
)
SELECT * FROM ins;

SELECT ok(
    (SELECT p.cleanup_at <= now() FROM _push_scaduta p),
    '8. commesse_push_log retrodatata: nasce gia'' scaduta (la base e'' run_at, non now())'
);

-- ============================================================
-- 9-12) fatturazione_lotti_log — il guard e la retention
-- ============================================================
CREATE TEMP TABLE _ll_viva AS
WITH ins AS (
    INSERT INTO vendite.fatturazione_lotti_log (lotto_id, data_ora, messaggio, status)
    SELECT r.lotto_id, now(), 'pgTAP scadenza: viva', 'I'
      FROM _rif r
     WHERE r.lotto_id IS NOT NULL
    RETURNING id, data_ora, cleanup_at
)
SELECT * FROM ins;

SELECT CASE
    WHEN (SELECT lotto_id FROM _rif) IS NULL
      THEN skip('nessun lotto dell''emittente dell''operatore', 1)
    ELSE is(
        (SELECT l.cleanup_at FROM _ll_viva l),
        (SELECT l.data_ora + make_interval(days => r.ttl_lotti_log) FROM _ll_viva l, _rif r),
        '9. fatturazione_lotti_log: cleanup_at = data_ora + il TTL della regola 16'
    )
END;

SELECT CASE
    WHEN (SELECT lotto_id FROM _rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    ELSE throws_like(
        format('DELETE FROM vendite.fatturazione_lotti_log WHERE id = %s',
               (SELECT id FROM _ll_viva)),
        '%Cancellazione non permessa%',
        '10. DELETE di una riga VIVA rifiutato senza GUC: il guard e'' ancora un guard'
    )
END;

CREATE TEMP TABLE _ll_scaduta AS
WITH ins AS (
    INSERT INTO vendite.fatturazione_lotti_log (lotto_id, data_ora, messaggio, status)
    SELECT r.lotto_id, now() - make_interval(days => r.ttl_lotti_log + 50), 'pgTAP scadenza: scaduta', 'I'
      FROM _rif r
     WHERE r.lotto_id IS NOT NULL
    RETURNING id, cleanup_at
)
SELECT * FROM ins;

SELECT CASE
    WHEN (SELECT lotto_id FROM _rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    ELSE cmp_ok(
        dbops.fn_purge_cleanup_expired('vendite', 'fatturazione_lotti_log', 'cleanup_at', 5000, true),
        '>=', 1,
        '11. il purge (dry-run) vede la riga scaduta: e'' lui che la ritirera'''
    )
END;

-- ⚠️ Il verbo in un'istruzione SEPARATA dall'asserzione.
CREATE TEMP TABLE _ll_esito AS
WITH del AS (
    DELETE FROM vendite.fatturazione_lotti_log
     WHERE id = (SELECT id FROM _ll_scaduta)
    RETURNING 1
)
SELECT count(*)::int AS righe FROM del;

SELECT CASE
    WHEN (SELECT lotto_id FROM _rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    ELSE is(
        (SELECT righe FROM _ll_esito),
        1,
        '12. DELETE di una riga SCADUTA ammesso senza GUC: e'' la retention che passa'
    )
END;

-- ============================================================
-- 13) fatturazione_lotti_task_runs — la quarta sorgente del giornale
-- ============================================================
CREATE TEMP TABLE _tr AS
WITH ins AS (
    INSERT INTO vendite.fatturazione_lotti_task_runs (lotto_id, task_code, tentativo, task_stato, started_at, ended_at)
    SELECT r.lotto_id, 'PGTAP_SCADENZA', 1, 'COMPLETATO', now(), now()
      FROM _rif r
     WHERE r.lotto_id IS NOT NULL
    RETURNING id, started_at, cleanup_at
)
SELECT * FROM ins;

SELECT CASE
    WHEN (SELECT lotto_id FROM _rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    ELSE is(
        (SELECT t.cleanup_at FROM _tr t),
        (SELECT t.started_at + make_interval(days => r.ttl_task_runs) FROM _tr t, _rif r),
        '13. fatturazione_lotti_task_runs: cleanup_at = started_at + il TTL della regola 18'
    )
END;

-- ============================================================
-- 14-15) fatture_log — l'ordine dei trigger e la conseguenza su critical
-- ============================================================
-- ⭐ data_ora = now() APPOSTA: e' il valore che trg_fatture_log_a10_orario_reale_ins
--   SOSTITUISCE con clock_timestamp(). Se il trigger della scadenza scattasse
--   prima (fase _a10_ invece di _m50_), cleanup_at - data_ora NON farebbe 750
--   giorni esatti: la base sarebbe l'orario di transazione, la colonna quello reale.
CREATE TEMP TABLE _fl_viva AS
WITH ins AS (
    INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status)
    SELECT r.fattura_id, now(), 'pgTAP scadenza: orario riscritto', 'W'
      FROM _rif r
     WHERE r.fattura_id IS NOT NULL
    RETURNING id, data_ora, cleanup_at
)
SELECT * FROM ins;

SELECT CASE
    WHEN (SELECT fattura_id FROM _rif) IS NULL
      THEN skip('nessuna fattura non critica dell''emittente dell''operatore', 1)
    ELSE is(
        (SELECT f.cleanup_at - f.data_ora FROM _fl_viva f),
        (SELECT make_interval(days => r.ttl_fatture_log) FROM _rif r),
        '14. fatture_log: la scadenza segue l''orario RISCRITTO da a10_orario_reale (fase _m50_)'
    )
END;

-- Un critico gia' scaduto: si accende fatture.critical, il purge lo spegne.
CREATE TEMP TABLE _fl_critico AS
WITH ins AS (
    INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status)
    SELECT r.fattura_id, now() - make_interval(days => r.ttl_fatture_log + 50), 'pgTAP scadenza: critico scaduto', 'C'
      FROM _rif r
     WHERE r.fattura_id IS NOT NULL
    RETURNING id, cleanup_at
)
SELECT * FROM ins;

CREATE TEMP TABLE _critical_prima AS
SELECT f.critical FROM vendite.fatture f WHERE f.id = (SELECT fattura_id FROM _rif);

CREATE TEMP TABLE _fl_esito AS
WITH del AS (
    DELETE FROM vendite.fatture_log
     WHERE id = (SELECT id FROM _fl_critico)
    RETURNING 1
)
SELECT count(*)::int AS righe FROM del;

CREATE TEMP TABLE _critical_dopo AS
SELECT f.critical FROM vendite.fatture f WHERE f.id = (SELECT fattura_id FROM _rif);

SELECT CASE
    WHEN (SELECT fattura_id FROM _rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    ELSE ok(
        (SELECT critical FROM _critical_prima) IS TRUE
        AND (SELECT righe FROM _fl_esito) = 1
        AND (SELECT critical FROM _critical_dopo) IS NOT TRUE,
        '15. il purge di un critico scaduto passa dal guard e spegne fatture.critical: il critico eredita la scadenza del registro'
    )
END;

SELECT * FROM finish();
ROLLBACK;
