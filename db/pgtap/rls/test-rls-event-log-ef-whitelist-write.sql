-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test FUNZIONALE lettura/scrittura RLS — vendite.event_log
--   Policy: rls_event_log_ef_whitelist (FOR ALL, adapter SR
--           script.fn_scope_ef_whitelist_via_sr, gate OPERATORE)
--   Brief: docs/it/dev/work-in-progress/brief-db-event-log-scope-e-riga-parlante.md §3.3
--
-- ⭐ PERCHE' QUESTO TEST NON FA DDL, a differenza dei gemelli in `rls/`.
--   Su commesse/resi/ddt il test deve accendere `ENABLE + FORCE` dentro la
--   transazione, perche' li' gira come **owner** e senza FORCE l'owner salta le
--   policy. Qui no: il runner gira come `zeroerp_app`, che NON e' owner
--   (l'owner e' `titodb`), non e' superuser e non ha BYPASSRLS. La policy morde
--   gia', e il test esercita **esattamente la configurazione di esercizio** —
--   niente ALTER, niente marcatore `pgtap-runner: owner`.
--
-- Fixture SENZA build: usa una commessa esistente dell'emittente dell'operatore
-- e un secondo operatore su un emittente diverso. Soft-skip se il secondo
-- operatore non esiste (il perimetro non e' verificabile con un emittente solo).
--
-- Indice test (1..5):
--   1. l'operatore scrive un evento sulla PROPRIA commessa e lo rivede
--   2. un operatore di un ALTRO emittente NON lo vede            (ramo USING)
--   3. un operatore di un ALTRO emittente NON puo' scriverlo     (ramo WITH CHECK)
--   4. senza `app.ruolo_applicativo` non si vede niente          (il cancello)
--   5. ⚠️ svuotando SOLO `app.current_user_id` la riga TORNA visibile —
--      il fail-closed lo da' il RUOLO, non l'utente
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- ============================================================
-- Fixture
-- ============================================================
-- ⚠️ Una sola scelta, proiettata da una temp table: due sotto-select
--    indipendenti potrebbero pescare righe diverse.
CREATE TEMP TABLE _rif AS
SELECT
    (SELECT current_setting('app.current_user_id', true)::integer)   AS op_in,
    script.fn_pgtap_emittente_sr_operatore()                          AS sr_in,
    (SELECT c.id
       FROM vendite.commesse c
      WHERE c.emittente_soggetto_ruolo_id = script.fn_pgtap_emittente_sr_operatore()
      ORDER BY c.id
      LIMIT 1)                                                        AS commessa_id,
    -- Un operatore su un emittente DIVERSO. La whitelist e' la sede canonica.
    (SELECT uef.auth_user_id
       FROM config.user_emittenti_fiscali uef
      WHERE uef.emittente_fiscale_id IS DISTINCT FROM (
                SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
                 WHERE ef.soggetto_ruolo_id = script.fn_pgtap_emittente_sr_operatore())
      ORDER BY uef.auth_user_id
      LIMIT 1)                                                        AS op_out;

-- ⚠️ Il verbo in un'ISTRUZIONE SEPARATA dall'asserzione: la snapshot di
--    statement legge PRIMA delle scritture, e un'asserzione che scrive e
--    controlla nello stesso comando accuserebbe la funzione al posto del test.
CREATE TEMP TABLE _ev AS
SELECT vendite.fn_log_event(
           'TEST_RLS', 'COMMESSA', (SELECT commessa_id FROM _rif),
           'PGTAP_RLS_EVENT'
       ) AS event_id
 WHERE (SELECT commessa_id FROM _rif) IS NOT NULL;

-- ============================================================
-- Asserzioni
-- ============================================================

-- 1) In-scope: l'evento c'e' e si vede.
SELECT CASE
    WHEN (SELECT commessa_id FROM _rif) IS NULL
      THEN skip('nessuna commessa dell''emittente dell''operatore: fixture non costruibile', 1)
    ELSE is(
        (SELECT count(*)::int FROM vendite.event_log el
          WHERE el.id = (SELECT event_id FROM _ev)),
        1,
        'in-scope: l''operatore rivede l''evento che ha appena scritto'
    )
END;

-- 2) Ramo USING: un altro emittente non lo vede.
--    ⚠️ Il cambio di identita' NON invalida le temp table: l'id resta noto al
--    test, e serve proprio a questo — chiedere una riga che si sa esistere.
DO $sw$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT op_out FROM _rif))
      WHERE (SELECT op_out FROM _rif) IS NOT NULL;
END $sw$;

SELECT CASE
    WHEN (SELECT op_out FROM _rif) IS NULL OR (SELECT commessa_id FROM _rif) IS NULL
      THEN skip('serve un secondo operatore su un emittente diverso', 1)
    ELSE is(
        (SELECT count(*)::int FROM vendite.event_log el
          WHERE el.id = (SELECT event_id FROM _ev)),
        0,
        'USING: un operatore di un altro emittente non vede l''evento'
    )
END;

-- 3) Ramo WITH CHECK: e non puo' nemmeno scriverlo.
--    ⭐ La derivazione (SECURITY DEFINER) risolve comunque l'emittente della
--    commessa altrui: e' la policy a negare, non l'invisibilita' del padre.
SELECT CASE
    WHEN (SELECT op_out FROM _rif) IS NULL OR (SELECT commessa_id FROM _rif) IS NULL
      THEN skip('serve un secondo operatore su un emittente diverso', 1)
    ELSE throws_ok(
        format(
            'SELECT vendite.fn_log_event(%L, %L, %s, %L)',
            'TEST_RLS', 'COMMESSA', (SELECT commessa_id FROM _rif), 'PGTAP_RLS_OFFSCOPE'
        ),
        '42501',
        NULL,
        'WITH CHECK: scrivere nel diario di un altro emittente e'' negato dalla policy'
    )
END;

-- 4) Il cancello: senza veste applicativa non si vede niente.
DO $ctx2$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT op_in FROM _rif));
    PERFORM set_config('app.ruolo_applicativo', '', true);
END $ctx2$;

SELECT CASE
    WHEN (SELECT commessa_id FROM _rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    ELSE is(
        (SELECT count(*)::int FROM vendite.event_log el
          WHERE el.id = (SELECT event_id FROM _ev)),
        0,
        'gate: senza app.ruolo_applicativo la policy e'' fail-closed'
    )
END;

-- 5) ⚠️ E il cancello e' il RUOLO, non l'utente. Con la veste OPERATORE e
--    `app.current_user_id` VUOTO la riga torna visibile: la regola 1 di
--    script.fn_check_user_emittente_scope tratta l'utente assente come «job
--    batch, nessun filtro». Non e' un difetto da correggere qui — e' il motivo
--    per cui un test di perimetro NON si scrive svuotando l'utente.
DO $ctx3$ BEGIN
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id',   '',          true);
END $ctx3$;

SELECT CASE
    WHEN (SELECT commessa_id FROM _rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    ELSE is(
        (SELECT count(*)::int FROM vendite.event_log el
          WHERE el.id = (SELECT event_id FROM _ev)),
        1,
        'svuotare solo app.current_user_id NON e'' fail-closed: il cancello e'' il ruolo'
    )
END;

SELECT * FROM finish();
ROLLBACK;
