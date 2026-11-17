-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Il titolare di un indirizzo e' la sua identita' (Tid, 2026-11-18): un
-- indirizzo di ruolo non passa a un altro ruolo, un indirizzo del soggetto
-- non passa a un altro soggetto. Lo dicono due lock di colonna del registro
-- (dbops.automation_lock_columns), montati dal runner.
--   Brief: brief-db-fornitore-privato-indirizzi §15, giro 7.
--   ChangeSet 90_end/20261116-46; righe nei CSV di 80_data.
--
-- Elenco test (plan 5):
--   1) i due lock sono vivi, coi loro codici (dbops.vw_non_editable_fields)
--   2) UPDATE del ruolo di un indirizzo di ruolo: E_INDIRIZZO_RUOLO_TITOLARE_IMMUTABILE
--   3) ... riscrivere lo stesso ruolo passa (un salvataggio che riscrive la riga)
--   4) UPDATE del soggetto di un indirizzo del soggetto: E_INDIRIZZO_SOGGETTO_TITOLARE_IMMUTABILE
--   5) ... riscrivere lo stesso soggetto passa
--
-- Scopo: i soggetti, i ruoli e i loro indirizzi si COSTRUISCONO coi builder
-- (regola zero): il test non legge le righe di oggi. Si asserisce il CODICE
-- (canale CONSTRAINT), non un P0001 qualsiasi: un altro guard che rifiutasse
-- prima farebbe passare il test per la ragione sbagliata.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- I builder aprono e richiudono da se' la finestra dei differiti.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

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
-- Fixture: due privati, ciascuno col ruolo cliente e i suoi indirizzi
-- ============================================================
CREATE TEMP TABLE _s AS
SELECT dbops.fn_pgtap_crea_soggetto_pf('Titolare', 'A') AS sogg_a,
       dbops.fn_pgtap_crea_soggetto_pf('Titolare', 'B') AS sogg_b;

CREATE TEMP TABLE _r AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(s.sogg_a, 'CL') AS sr_a,
       dbops.fn_pgtap_crea_soggetto_ruolo(s.sogg_b, 'CL') AS sr_b
  FROM _s s;

CREATE TEMP TABLE _f AS
SELECT s.sogg_a, s.sogg_b, r.sr_a, r.sr_b,
       (SELECT min(i.id) FROM anagrafiche.indirizzi i WHERE i.soggetto_ruolo_id = r.sr_a) AS ind_ruolo_a,
       (SELECT min(i.id) FROM anagrafiche.indirizzi_soggetti i WHERE i.soggetto_id = s.sogg_a) AS ind_sogg_a
  FROM _s s, _r r;

-- ============================================================
-- 1) I lock sono vivi
-- ============================================================
SELECT is(
    (SELECT array_agg(v.target_table || '.' || v.column_name || '=' || v.error_code
                      ORDER BY v.target_table COLLATE "C")
       FROM dbops.vw_non_editable_fields v
      WHERE v.target_schema = 'anagrafiche'
        AND (v.target_table, v.column_name) IN (('indirizzi', 'soggetto_ruolo_id'),
                                                 ('indirizzi_soggetti', 'soggetto_id'))),
    ARRAY['indirizzi.soggetto_ruolo_id=E_INDIRIZZO_RUOLO_TITOLARE_IMMUTABILE',
          'indirizzi_soggetti.soggetto_id=E_INDIRIZZO_SOGGETTO_TITOLARE_IMMUTABILE'],
    '1) i due lock del titolare sono vivi, coi loro codici');

-- ============================================================
-- 2-3) L'indirizzo di ruolo
-- ============================================================
SELECT is(
    (SELECT pg_temp.esito(format(
         'UPDATE anagrafiche.indirizzi SET soggetto_ruolo_id = %s WHERE id = %s', f.sr_b, f.ind_ruolo_a))
       FROM _f f),
    'E_INDIRIZZO_RUOLO_TITOLARE_IMMUTABILE',
    '2) UPDATE del ruolo di un indirizzo di ruolo: E_INDIRIZZO_RUOLO_TITOLARE_IMMUTABILE');

SELECT is(
    (SELECT pg_temp.esito(format(
         'UPDATE anagrafiche.indirizzi SET soggetto_ruolo_id = %s WHERE id = %s', f.sr_a, f.ind_ruolo_a))
       FROM _f f),
    'ok',
    '3) riscrivere lo stesso ruolo passa');

-- ============================================================
-- 4-5) L'indirizzo del soggetto
-- ============================================================
SELECT is(
    (SELECT pg_temp.esito(format(
         'UPDATE anagrafiche.indirizzi_soggetti SET soggetto_id = %L::uuid WHERE id = %s', f.sogg_b, f.ind_sogg_a))
       FROM _f f),
    'E_INDIRIZZO_SOGGETTO_TITOLARE_IMMUTABILE',
    '4) UPDATE del soggetto di un indirizzo del soggetto: E_INDIRIZZO_SOGGETTO_TITOLARE_IMMUTABILE');

SELECT is(
    (SELECT pg_temp.esito(format(
         'UPDATE anagrafiche.indirizzi_soggetti SET soggetto_id = %L::uuid WHERE id = %s', f.sogg_a, f.ind_sogg_a))
       FROM _f f),
    'ok',
    '5) riscrivere lo stesso soggetto passa');

SELECT * FROM finish();
ROLLBACK;
