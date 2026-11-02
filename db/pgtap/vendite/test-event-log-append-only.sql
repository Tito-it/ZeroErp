-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test — vendite.trgfn_event_log_append_only
--   Brief: brief-db-event-log-scope-e-riga-parlante.md §3.4
--
-- ⭐ LA DISTINZIONE CHE QUESTO FILE PRESIDIA:
--     append-only vuol dire che non puoi ALTERARE ne' CANCELLARE LA STORIA;
--     non vuol dire che non puoi RITIRARE CIO' CHE HA PASSATO LA SUA SCADENZA.
--
--   Prima del 2026-08-22 il trigger vietava `UPDATE` e `DELETE` senza
--   distinzioni, e con un `RAISE EXCEPTION` nudo. Conseguenza misurata: la
--   retention standard NON poteva funzionare — `dbops.fn_apply_cleanup_at`
--   valorizza con un UPDATE e `dbops.fn_purge_cleanup_expired` cancella con un
--   DELETE, e la regola `*all` di `dbops.automation_rules_tbl` li avrebbe
--   lanciati su questa tabella al primo giro del job settimanale.
--
--   ⭐ E il veto sull'UPDATE non e' solo un divieto: e' cio' che rende
--   `cleanup_at` IMMUTABILE. Nessuno puo' anticipare la scadenza di una riga
--   scomoda — ed e' il test 3 a dimostrarlo, perche' e' l'unico modo di far
--   sparire una riga viva.
--
-- Indice test (1..5):
--   1. UPDATE vietato, con codice registrato (non un RAISE nudo)
--   2. DELETE di una riga VIVA vietato, con codice registrato
--   3. la scadenza non si puo' anticipare: l'UPDATE su cleanup_at e' vietato
--   4. DELETE di una riga SCADUTA ammesso — e' la retention che passa
--   5. DELETE con la GUC di manutenzione ammesso — parita' con i log gemelli
--      (vendite.trgfn_logs_guard_delete su fatture_log e fatturazione_lotti_log)
--
-- ⏱️ 2026-09-18 (Passo D dell'osservabilita'): la parita' e' diventata completa
--   nell'altro verso — anche trgfn_logs_guard_delete ammette il DELETE di una
--   riga SCADUTA (20260918-32), e cleanup_at lo scrive per tutti lo stesso BB,
--   dbops.trgfn_cleanup_at_alla_nascita (qui montato da 20260918-31 al posto
--   del passo 4 di deriva_scope). Il comportamento che questo file pinna non
--   cambia di una virgola.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- ============================================================
-- Fixture — due righe: una viva e una gia' scaduta
-- ============================================================
CREATE TEMP TABLE _rif AS
SELECT (SELECT c.id
          FROM vendite.commesse c
         WHERE c.emittente_soggetto_ruolo_id = script.fn_pgtap_emittente_sr_operatore()
         ORDER BY c.id
         LIMIT 1) AS commessa_id;

-- Riga VIVA: `cleanup_at` lo calcola il trigger su `now()`.
CREATE TEMP TABLE _viva AS
SELECT vendite.fn_log_event('COMMESSA',
                            (SELECT commessa_id FROM _rif), 'PGTAP_VIVA') AS id
 WHERE (SELECT commessa_id FROM _rif) IS NOT NULL;

-- Riga SCADUTA: si ottiene datando l'evento nel passato — il trigger calcola
-- `cleanup_at` da `event_time`, non da `now()`. ⚠️ Serve l'INSERT diretto:
-- `fn_log_event` non espone `event_time`, ed e' giusto cosi' (un diario non
-- lascia scegliere al chiamante quando e' successo).
CREATE TEMP TABLE _scaduta AS
WITH ins AS (
    INSERT INTO vendite.event_log (event_time, entity_type, entity_id, event_code)
    -- ⏱️ 2026-09-18 (Passo D): il TTL si legge dal BB generico, non piu' da
    --   vendite.fn_event_log_ttl_days, ritirata (20260918-31).
    SELECT now() - make_interval(days => COALESCE((dbops.fn_cleanup_at_params('vendite', 'event_log') ->> 'ttl_days')::integer, 750) + 50),
           'COMMESSA', r.commessa_id, 'PGTAP_SCADUTA'
      FROM _rif r
     WHERE r.commessa_id IS NOT NULL
    RETURNING id
)
SELECT id FROM ins;

-- ============================================================
-- Asserzioni
-- ============================================================

-- 1) La storia non si modifica.
SELECT CASE
    WHEN (SELECT commessa_id FROM _rif) IS NULL
      THEN skip('nessuna commessa dell''emittente dell''operatore', 1)
    ELSE throws_like(
        format('UPDATE vendite.event_log SET severity = ''WARN'' WHERE id = %s',
               (SELECT id FROM _viva)),
        '%Modifica non permessa%',
        'UPDATE vietato, e con un codice registrato (non un RAISE nudo)'
    )
END;

-- 2) E non si cancella, finche' e' viva.
SELECT CASE
    WHEN (SELECT commessa_id FROM _rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    ELSE throws_like(
        format('DELETE FROM vendite.event_log WHERE id = %s', (SELECT id FROM _viva)),
        '%Cancellazione non permessa%',
        'DELETE di una riga viva vietato, con codice registrato'
    )
END;

-- 3) ⭐ E la scadenza stessa e' immutabile: e' il veto sull'UPDATE a garantirlo.
--    Senza, chiunque potrebbe portare `cleanup_at` nel passato e poi cancellare
--    la riga passando dal ramo della retention — cioe' il veto sul DELETE
--    varrebbe zero.
SELECT CASE
    WHEN (SELECT commessa_id FROM _rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    ELSE throws_like(
        format('UPDATE vendite.event_log SET cleanup_at = now() - interval ''1 day'' WHERE id = %s',
               (SELECT id FROM _viva)),
        '%Modifica non permessa%',
        'la scadenza non si puo'' anticipare: cleanup_at e'' immutabile per costruzione'
    )
END;

-- 4) La retention passa: una riga scaduta si ritira.
--    ⚠️ Il verbo in un'istruzione SEPARATA dall'asserzione.
CREATE TEMP TABLE _esito_scaduta AS
WITH del AS (
    DELETE FROM vendite.event_log
     WHERE id = (SELECT id FROM _scaduta)
    RETURNING 1
)
SELECT count(*)::int AS righe FROM del;

SELECT CASE
    WHEN (SELECT commessa_id FROM _rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    ELSE is(
        (SELECT righe FROM _esito_scaduta),
        1,
        'DELETE di una riga SCADUTA ammesso: e'' la retention, non una manomissione'
    )
END;

-- 5) La manutenzione straordinaria: stessa leva dei log gemelli.
DO $guc$ BEGIN
    PERFORM set_config('zeroerp.maintenance_allow_delete_logs', 'on', true);
END $guc$;

CREATE TEMP TABLE _esito_guc AS
WITH del AS (
    DELETE FROM vendite.event_log
     WHERE id = (SELECT id FROM _viva)
    RETURNING 1
)
SELECT count(*)::int AS righe FROM del;

SELECT CASE
    WHEN (SELECT commessa_id FROM _rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    ELSE is(
        (SELECT righe FROM _esito_guc),
        1,
        'DELETE con zeroerp.maintenance_allow_delete_logs: parita'' con i log gemelli'
    )
END;

SELECT * FROM finish();
ROLLBACK;
