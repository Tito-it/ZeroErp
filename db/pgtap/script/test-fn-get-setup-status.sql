-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_setup_status
--       Stato di setup operatore-emittente in jsonb.
--
-- Elenco test:
--  1) Output ha tutte e 5 le chiavi attese
--  2) emittenti_attivi e' un numero >= 0
--  3) operatori_non_assegnati = operatori_totali - operatori_assegnati
--     (con clamp a 0)
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

SELECT plan(3);

CREATE TEMP TABLE tmp_setup AS
SELECT script.fn_get_setup_status() AS s;

-- ============================================================
-- 1) Tutte le chiavi attese presenti
-- ============================================================
SELECT is(
    (SELECT (s ? 'emittenti_attivi')
        AND (s ? 'operatori_totali')
        AND (s ? 'operatori_assegnati')
        AND (s ? 'operatori_admin_globali')
        AND (s ? 'operatori_non_assegnati')
       FROM tmp_setup),
    true,
    'Output jsonb contiene tutte le 5 chiavi attese'
);

-- ============================================================
-- 2) emittenti_attivi >= 0
-- ============================================================
SELECT cmp_ok(
    (SELECT (s->>'emittenti_attivi')::int FROM tmp_setup),
    '>=',
    0,
    'emittenti_attivi >= 0'
);

-- ============================================================
-- 3) operatori_non_assegnati = max(operatori_totali - operatori_assegnati, 0)
-- ============================================================
SELECT is(
    (SELECT (s->>'operatori_non_assegnati')::int FROM tmp_setup),
    (SELECT greatest(
                (s->>'operatori_totali')::int - (s->>'operatori_assegnati')::int,
                0
            )
       FROM tmp_setup),
    'operatori_non_assegnati = max(totali - assegnati, 0)'
);

SELECT * FROM finish();
ROLLBACK;
