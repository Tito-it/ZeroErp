-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- CF e P.IVA valorizzati di un soggetto non si cambiano e non si svuotano, salvo il SUPER_ADMIN;
-- un campo vuoto si riempie (decisione di Tid, 2026-11-09).
-- Brief: brief-db-revisione-dbops, S-BE-3 (§32).
-- ChangeSet: 20_code/anagrafiche/20261110-95 (la regola), -96 (il guard),
--            80_data/changelog/20261110-97 (il registro del form).
--
-- I soggetti e le due persone (un operatore senza privilegi, un SUPER_ADMIN) si costruiscono.
--
-- Elenco test (plan 11):
--  1) il guard e' montato: BEFORE UPDATE OF codice_fiscale, partita_iva
--  2) ⭐ l'operatore che cambia un CF scritto: E_SOGGETTO_ID_FISCALE_IMMUTABILE, campo codice_fiscale
--  3) ⭐ l'operatore che cambia una P.IVA scritta: lo stesso, campo partita_iva
--  4) ⭐ l'operatore che svuota la P.IVA: lo stesso
--  5) riscrivere lo stesso valore non e' un cambio: passa
--  6) il form dell'operatore spegne CF e P.IVA (dbops.fn_non_editable_fields)
--  7) ⭐ il SUPER_ADMIN corregge il CF e la P.IVA: passa
--  8) il form del SUPER_ADMIN li lascia accesi
--  9) il form spegne solo il campo scritto: un campo vuoto resta acceso
-- 10) ⭐ un campo vuoto si riempie, anche dall'operatore
-- 11) ... e da li' in poi e' bloccato anche lui
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _sa AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-idfiscale', true);
CREATE TEMP TABLE _op AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-OP-idfiscale', false);

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _op)); END $ctx$;

CREATE TEMP TABLE _sog AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('pgTAP id fiscale A') AS a,
       dbops.fn_pgtap_crea_soggetto_pg('pgTAP id fiscale B') AS b;

-- Il codice e la colonna del rifiuto: fn_log_and_raise_error li mette in CONSTRAINT_NAME e
--   COLUMN_NAME; ogni altro errore torna col suo SQLSTATE.
CREATE OR REPLACE FUNCTION pg_temp.rifiuto(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text; v_col text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION
    WHEN SQLSTATE 'P0001' THEN
        GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME, v_col = COLUMN_NAME;
        RETURN v_c || ' / ' || COALESCE(v_col, '-');
    WHEN OTHERS THEN
        RETURN SQLSTATE || ' ' || SQLERRM;
END $$;

CREATE OR REPLACE FUNCTION pg_temp.agisci(p_auth_user_id integer) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(p_auth_user_id);
END $$;

-- ============================================================
-- 1) Il montaggio
-- ============================================================
SELECT is(
    (SELECT string_agg(a.attname, ',' ORDER BY a.attname)
       FROM pg_trigger t
       JOIN pg_attribute a ON a.attrelid = t.tgrelid AND a.attnum = ANY (t.tgattr)
      WHERE t.tgrelid = 'anagrafiche.soggetti'::regclass
        AND t.tgfoid = 'anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile'::regproc
        AND (t.tgtype & 2) <> 0     -- BEFORE
        AND (t.tgtype & 16) <> 0),  -- UPDATE
    'codice_fiscale,partita_iva',
    '1) il guard e'' montato BEFORE UPDATE OF codice_fiscale, partita_iva');

-- ============================================================
-- L'operatore
-- ============================================================
SELECT is(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti SET codice_fiscale = %L WHERE id = %L$$,
                           dbops.fn_pgtap_piva_libera(), (SELECT a FROM _sog))),
    'E_SOGGETTO_ID_FISCALE_IMMUTABILE / codice_fiscale',
    '2) l''operatore non cambia un CF scritto');

SELECT is(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti SET partita_iva = %L WHERE id = %L$$,
                           dbops.fn_pgtap_piva_libera(), (SELECT a FROM _sog))),
    'E_SOGGETTO_ID_FISCALE_IMMUTABILE / partita_iva',
    '3) l''operatore non cambia una P.IVA scritta');

SELECT is(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti SET tipo_soggetto_dettaglio_id = NULL, partita_iva = NULL WHERE id = %L$$,
                           (SELECT a FROM _sog))),
    'E_SOGGETTO_ID_FISCALE_IMMUTABILE / partita_iva',
    '4) l''operatore non svuota una P.IVA scritta');

SELECT is(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti SET codice_fiscale = codice_fiscale, partita_iva = partita_iva WHERE id = %L$$,
                           (SELECT a FROM _sog))),
    NULL,
    '5) riscrivere lo stesso valore non e'' un cambio');

SELECT is(
    (SELECT array_to_string(ARRAY(
        SELECT c FROM unnest(dbops.fn_non_editable_fields('anagrafiche', 'soggetti', (SELECT a FROM _sog)::text)) c
         WHERE c IN ('codice_fiscale', 'partita_iva') ORDER BY c), ',')),
    'codice_fiscale,partita_iva',
    '6) il form dell''operatore spegne CF e P.IVA');

-- ============================================================
-- Il SUPER_ADMIN
-- ============================================================
SELECT pg_temp.agisci((SELECT auth_user_id FROM _sa));

CREATE TEMP TABLE _nuovo AS SELECT dbops.fn_pgtap_piva_libera() AS piva;

SELECT is(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti SET codice_fiscale = %L, partita_iva = %L WHERE id = %L$$,
                           (SELECT piva FROM _nuovo), (SELECT piva FROM _nuovo), (SELECT a FROM _sog))),
    NULL,
    '7) il SUPER_ADMIN corregge CF e P.IVA');

SELECT is(
    (SELECT array_to_string(ARRAY(
        SELECT c FROM unnest(dbops.fn_non_editable_fields('anagrafiche', 'soggetti', (SELECT a FROM _sog)::text)) c
         WHERE c IN ('codice_fiscale', 'partita_iva') ORDER BY c), ',')),
    '',
    '8) il form del SUPER_ADMIN lascia CF e P.IVA accesi');

-- Il SUPER_ADMIN svuota la P.IVA del soggetto B (a tipo NULL: il guard dell'obbligo non la pretende).
UPDATE anagrafiche.soggetti SET tipo_soggetto_dettaglio_id = NULL, partita_iva = NULL
 WHERE id = (SELECT b FROM _sog);

-- ============================================================
-- Il campo vuoto
-- ============================================================
SELECT pg_temp.agisci((SELECT auth_user_id FROM _op));

SELECT is(
    (SELECT array_to_string(ARRAY(
        SELECT c FROM unnest(dbops.fn_non_editable_fields('anagrafiche', 'soggetti', (SELECT b FROM _sog)::text)) c
         WHERE c IN ('codice_fiscale', 'partita_iva') ORDER BY c), ',')),
    'codice_fiscale',
    '9) il form spegne solo il campo scritto: la P.IVA vuota resta accesa');

SELECT is(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti SET partita_iva = codice_fiscale WHERE id = %L$$,
                           (SELECT b FROM _sog))),
    NULL,
    '10) l''operatore riempie una P.IVA vuota');

SELECT is(
    pg_temp.rifiuto(format($$UPDATE anagrafiche.soggetti SET partita_iva = %L WHERE id = %L$$,
                           dbops.fn_pgtap_piva_libera(), (SELECT b FROM _sog))),
    'E_SOGGETTO_ID_FISCALE_IMMUTABILE / partita_iva',
    '11) riempita, la P.IVA e'' bloccata anche lei');

SELECT * FROM finish();
ROLLBACK;
