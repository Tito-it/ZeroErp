-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: gli eventi di dbops.sessioni_utente sono gesti, e la scadenza non lo e'
-- (Q14 ⑨).
-- Brief: brief-db-revisione-dbops, giro 9, blocco 9b (§24). changeSet 20261109-49.
--
-- Elenco test (plan 2):
--   1) il vincolo non ammette SCADENZA
--   2) il vincolo ammette ancora i cinque eventi che qualcuno compie
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(2);

SELECT doesnt_match(
    (SELECT pg_get_constraintdef(oid) FROM pg_constraint
      WHERE conrelid = 'dbops.sessioni_utente'::regclass
        AND conname = 'chk_sessioni_utente_evento'),
    'SCADENZA',
    '1) chk_sessioni_utente_evento non ammette SCADENZA: nessuno la compie');

SELECT is(
    (SELECT array_agg(v ORDER BY v)
       FROM (SELECT (regexp_matches(pg_get_constraintdef(oid), '''([A-Z_]+)''::text', 'g'))[1] AS v
               FROM pg_constraint
              WHERE conrelid = 'dbops.sessioni_utente'::regclass
                AND conname = 'chk_sessioni_utente_evento') x),
    ARRAY['LOGIN', 'LOGOUT', 'REFRESH', 'REVOCA', 'TOTP_DISABILITATO']::text[],
    '2) gli eventi ammessi sono i cinque gesti: login, refresh, logout, revoca, secondo fattore disattivato');

SELECT * FROM finish();

ROLLBACK;
