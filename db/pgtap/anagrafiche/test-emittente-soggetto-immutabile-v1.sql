-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Un emittente fiscale e' l'emittente di un soggetto (Tid, 2026-11-21,
-- richiesta del BE): il suo ruolo, e quindi il soggetto, non cambia. Lo dice
-- un lock di colonna del registro (dbops.automation_lock_columns) su
-- anagrafiche.emittenti_fiscali.soggetto_ruolo_id, montato dal runner.
-- Con E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE la catena emittente -> ruolo ->
-- soggetto e' immutabile.
--   ChangeSet 90_end/20261121-09; righe nei CSV di 80_data.
--
-- Elenco test (plan 3):
--   1) i due lock dell'emittente sono vivi, coi loro codici (dbops.vw_non_editable_fields)
--   2) UPDATE del ruolo dell'emittente verso un altro ruolo EF: E_EMITTENTE_SOGGETTO_IMMUTABILE
--   3) ... riscrivere lo stesso ruolo passa (un salvataggio che riscrive la riga)
--
-- Scopo: gli emittenti si COSTRUISCONO col builder (regola zero): il test non
-- legge le righe di oggi. Si asserisce il CODICE (canale CONSTRAINT), non un
-- P0001 qualsiasi: il ruolo di destinazione e' un EF vero, quindi il guard
-- del ruolo non avrebbe niente da dire, e senza il lock l'UPDATE morirebbe
-- solo sulla UNIQUE (23505), cioe' per la ragione sbagliata.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- I builder aprono e richiudono da se' la finestra dei differiti.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(3);

-- L'esito di un'istruzione: 'ok', oppure il codice di dominio (canale
-- CONSTRAINT di script.fn_log_and_raise_error), oppure lo SQLSTATE e il
-- messaggio per un errore che non e' di dominio.
CREATE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE
    v_codice text;
    v_stato  text;
    v_msg    text;
BEGIN
    EXECUTE p_sql;
    RETURN 'ok';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME,
                            v_stato = RETURNED_SQLSTATE, v_msg = MESSAGE_TEXT;
    IF v_stato = 'P0001' AND v_codice <> '' THEN
        RETURN v_codice;
    END IF;
    RETURN v_stato || ': ' || v_msg;
END;
$f$;

-- ============================================================
-- Fixture: due emittenti, ciascuno col suo soggetto e il suo ruolo EF
-- ============================================================
CREATE TEMP TABLE _a AS SELECT * FROM dbops.fn_pgtap_crea_emittente('EFSA');
CREATE TEMP TABLE _b AS SELECT * FROM dbops.fn_pgtap_crea_emittente('EFSB');

-- ============================================================
-- 1) I lock sono vivi
-- ============================================================
SELECT is(
    (SELECT array_agg(v.column_name || '=' || v.error_code ORDER BY v.column_name COLLATE "C")
       FROM dbops.vw_non_editable_fields v
      WHERE v.target_schema = 'anagrafiche'
        AND v.target_table = 'emittenti_fiscali'
        AND v.column_name IN ('codice', 'soggetto_ruolo_id')),
    ARRAY['codice=E_CODICE_NON_MODIFICABILE',
          'soggetto_ruolo_id=E_EMITTENTE_SOGGETTO_IMMUTABILE'],
    '1) i due lock dell''emittente sono vivi, coi loro codici');

-- ============================================================
-- 2-3) Il ruolo dell'emittente
-- ============================================================
SELECT is(
    (SELECT pg_temp.esito(format(
         'UPDATE anagrafiche.emittenti_fiscali SET soggetto_ruolo_id = %s WHERE id = %s',
         b.soggetto_ruolo_id, a.emittente_fiscale_id))
       FROM _a a, _b b),
    'E_EMITTENTE_SOGGETTO_IMMUTABILE',
    '2) UPDATE del ruolo dell''emittente verso un altro ruolo EF: E_EMITTENTE_SOGGETTO_IMMUTABILE');

SELECT is(
    (SELECT pg_temp.esito(format(
         'UPDATE anagrafiche.emittenti_fiscali SET soggetto_ruolo_id = %s WHERE id = %s',
         a.soggetto_ruolo_id, a.emittente_fiscale_id))
       FROM _a a),
    'ok',
    '3) riscrivere lo stesso ruolo passa');

SELECT * FROM finish();
ROLLBACK;
