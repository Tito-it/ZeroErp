-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce DUE aziende e una commessa, e
--   una commessa pretende un billing account. Come `zeroerp_app` l'INSERT del
--   BA muore al RETURNING quando l'emittente di chi agisce non e' quello di
--   default (la policy di lettura risolve il BA non ancora mappato sul default;
--   il legame lo scrive un trigger AFTER). Da owner la policy si esercita con
--   `FORCE ROW LEVEL SECURITY` locale alla transazione, come nei gemelli
--   `*-satelliti.sql`.
-- pgTAP test FUNZIONALE lettura/scrittura RLS — vendite.event_log
--   Policy: rls_event_log_ef_whitelist (FOR ALL, adapter SR
--           script.fn_scope_ef_whitelist_via_sr, gate OPERATORE)
--   Brief: brief-db-event-log-scope-e-riga-parlante.md §3.3
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (2026-09-12). Fino a quel giorno il
--   file cercava una commessa ESISTENTE dell'emittente dell'operatore e un
--   secondo operatore su un altro emittente, e quando non li trovava SALTAVA:
--   su un database ricostruito dai changelog moriva nella fixture, e i due rami
--   della policy (USING e WITH CHECK) restavano collaudati solo su dbdev.
--   Ora: due aziende con `dbops.fn_pgtap_crea_emittente_operatore()`, un
--   cliente della prima con `dbops.fn_pgtap_crea_cliente_ba(..., A)` e la sua
--   commessa — l'emittente della commessa lo deriva dal BA il trigger
--   `trgfn_commesse_default_emittente`, non si passa a mano. Niente piu' `skip`.
--   ⚠️ Fino a quel giorno il file girava come `zeroerp_app` senza DDL ed era
--   la sua ragione d'orgoglio: il costo del cambio e' scritto nel marcatore.
--
-- Indice test (1..5):
--   1. l'operatore scrive un evento sulla PROPRIA commessa e lo rivede
--   2. un operatore di un ALTRO emittente NON lo vede            (ramo USING)
--   3. un operatore di un ALTRO emittente NON puo' scriverlo     (ramo WITH CHECK)
--   4. senza `app.ruolo_applicativo` non si vede niente          (il cancello)
--   5. svuotando SOLO `app.current_user_id` la riga resta invisibile —
--      chiude anche l'utente, non solo il ruolo (rev 2026-10-05: fino a
--      20261004-82 l'utente NULL era «job batch» e la riga tornava visibile)
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- ============================================================
-- Fixture: il mondo, POI il contesto
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'IN'  AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'OUT' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- ⛔ Il BA va LEGATO al proprio emittente (terzo parametro): senza,
--   `anagrafiche.fn_get_emittente_fiscale_id` ricade sull'emittente di DEFAULT
--   dell'installazione, e la commessa nascerebbe di un'altra azienda.
CREATE TEMP TABLE _cliente AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba(
    'RLS event_log', NULL, (SELECT soggetto_ruolo_id FROM _mondi WHERE lato = 'IN')) c;

CREATE TEMP TABLE _commessa AS
WITH c AS (
    INSERT INTO vendite.commesse
        (codice, billing_account_id, utility_id, competenza_dal, competenza_al)
    SELECT 'PGTAP-EV-' || cl.billing_account_id,
           cl.billing_account_id, cl.utility_id,
           date_trunc('month', script.fn_data_operativa())::date,
           (date_trunc('month', script.fn_data_operativa()) + interval '1 month - 1 day')::date
      FROM _cliente cl
    RETURNING id, emittente_soggetto_ruolo_id
)
SELECT id AS commessa_id, emittente_soggetto_ruolo_id FROM c;

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'IN'));
END $ctx$;

-- Da owner la policy non morde: si accende per la durata della transazione.
ALTER TABLE vendite.event_log FORCE ROW LEVEL SECURITY;

-- ⚠️ Una sola scelta, proiettata da una temp table: due sotto-select
--    indipendenti potrebbero pescare righe diverse.
CREATE TEMP TABLE _rif AS
SELECT (SELECT m.auth_user_id      FROM _mondi m WHERE m.lato = 'IN')  AS op_in,
       (SELECT m.soggetto_ruolo_id FROM _mondi m WHERE m.lato = 'IN')  AS sr_in,
       (SELECT c.commessa_id       FROM _commessa c)                    AS commessa_id,
       (SELECT m.auth_user_id      FROM _mondi m WHERE m.lato = 'OUT') AS op_out;

-- ⚠️ Il verbo in un'ISTRUZIONE SEPARATA dall'asserzione: la snapshot di
--    statement legge PRIMA delle scritture, e un'asserzione che scrive e
--    controlla nello stesso comando accuserebbe la funzione al posto del test.
CREATE TEMP TABLE _ev AS
SELECT vendite.fn_log_event(
           'COMMESSA', (SELECT commessa_id FROM _rif),
           'PGTAP_RLS_EVENT'
       ) AS event_id;

-- ============================================================
-- Asserzioni
-- ============================================================

-- 1) In-scope: l'evento c'e' e si vede.
SELECT is(
    (SELECT count(*)::int FROM vendite.event_log el
      WHERE el.id = (SELECT event_id FROM _ev)),
    1,
    'in-scope: l''operatore rivede l''evento che ha appena scritto'
);

-- 2) Ramo USING: un altro emittente non lo vede.
--    ⚠️ Il cambio di identita' NON invalida le temp table: l'id resta noto al
--    test, e serve proprio a questo — chiedere una riga che si sa esistere.
DO $sw$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT op_out FROM _rif));
END $sw$;

SELECT is(
    (SELECT count(*)::int FROM vendite.event_log el
      WHERE el.id = (SELECT event_id FROM _ev)),
    0,
    'USING: un operatore di un altro emittente non vede l''evento'
);

-- 3) Ramo WITH CHECK: e non puo' nemmeno scriverlo.
--    ⭐ La derivazione (SECURITY DEFINER) risolve comunque l'emittente della
--    commessa altrui: e' la policy a negare, non l'invisibilita' del padre.
SELECT throws_ok(
    format(
        'SELECT vendite.fn_log_event(%L, %s, %L)',
        'COMMESSA', (SELECT commessa_id FROM _rif), 'PGTAP_RLS_OFFSCOPE'
    ),
    '42501',
    NULL,
    'WITH CHECK: scrivere nel diario di un altro emittente e'' negato dalla policy'
);

-- 4) Il cancello: senza veste applicativa non si vede niente.
DO $ctx2$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT op_in FROM _rif));
    PERFORM set_config('app.ruolo_applicativo', '', true);
END $ctx2$;

SELECT is(
    (SELECT count(*)::int FROM vendite.event_log el
      WHERE el.id = (SELECT event_id FROM _ev)),
    0,
    'gate: senza app.ruolo_applicativo la policy e'' fail-closed'
);

-- 5) ⭐ Chiude anche l'UTENTE, non solo il ruolo. Con la veste OPERATORE e
--    `app.current_user_id` VUOTO la riga resta invisibile: dal changeSet
--    20261004-82 script.fn_check_user_emittente_scope risponde false con
--    l'utente NULL (brief-db-esclusioni-implicite, Q-1). Fino a quel giorno
--    questa asserzione pinnava il contrario — l'utente assente come «job
--    batch, nessun filtro», la riga visibile — cioe' il difetto che Q-1 ha
--    chiuso: una veste impostata senza utente vedeva tutte le aziende.
DO $ctx3$ BEGIN
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id',   '',          true);
END $ctx3$;

SELECT is(
    (SELECT count(*)::int FROM vendite.event_log el
      WHERE el.id = (SELECT event_id FROM _ev)),
    0,
    'svuotare solo app.current_user_id e'' fail-closed: con la veste e senza utente non si vede niente'
);

ALTER TABLE vendite.event_log NO FORCE ROW LEVEL SECURITY;

SELECT * FROM finish();
ROLLBACK;
