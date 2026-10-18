-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il verbo di creazione dell'emittente fiscale e il builder che lo usa:
--   anagrafiche.fn_crea_emittente_fiscale  (20261017-09)
--   dbops.fn_pgtap_crea_emittente          (20261017-10)
--   Brief: brief-db-processi-accensione-per-ambiente (§5-ter.1, 2b-1).
--
-- ⭐ Il soggetto si COSTRUISCE (dbops.fn_pgtap_crea_soggetto_pg, partita IVA
--   libera): niente pescato fra i dati.
--
-- Elenco test (plan 14):
--   forma
--    1) INVOKER
--   il caso felice
--    2) crea l'emittente sul soggetto, col ruolo EF
--    3) le chiavi assenti al DEFAULT (attivo true, regime RF01) e regime NON confermato
--    4) un regime dichiarato e' confermato (data e autore)
--    5) i campi opzionali passano (valuta, bollo)
--    6) i registri di numerazione nascono dal trigger, come prima
--   i rifiuti
--    7) una chiave estranea: E_CAMPO_NON_AMMESSO
--    8) ... col campo nel contesto
--    9) una colonna della conferma non si scrive a mano: E_CAMPO_NON_AMMESSO
--   10) campi che non sono un oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA
--   11) codice gia' usato: esce dal vincolo uq:codice (il backend lo traduce per nome)
--   12) secondo emittente sullo stesso soggetto: esce da uq_emittenti_fiscali_ruolo
--   il builder
--   13) dbops.fn_pgtap_crea_emittente crea ancora l'emittente, con la valuta
--   14) ... e il suo corpo chiama il verbo, non scrive la tabella
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(14);

CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

-- Il vincolo violato (23505/23503): CONSTRAINT_NAME porta il suo nome.
CREATE OR REPLACE FUNCTION pg_temp.vincolo_violato(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN unique_violation OR foreign_key_violation THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

CREATE OR REPLACE FUNCTION pg_temp.contesto_campo(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_d text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    -- Il campo viaggia sul canale COLUMN (contratto di fn_log_and_raise_error).
    GET STACKED DIAGNOSTICS v_d = COLUMN_NAME;
    RETURN v_d;
END $$;

-- Due soggetti costruiti, in due istruzioni: la partita IVA libera si legge
--   dal catalogo, e due letture nella stessa istruzione darebbero la stessa.
CREATE TEMP TABLE t_sog AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Emittente verbo pgTAP 1') AS s1, NULL::uuid AS s2;
UPDATE t_sog SET s2 = dbops.fn_pgtap_crea_soggetto_pg('Emittente verbo pgTAP 2');

CREATE TEMP TABLE t_sigla AS
SELECT 'PGTV' || lpad(n::text, 4, '0') AS a,
       'PGTW' || lpad(n::text, 4, '0') AS b
  FROM generate_series(1, 9999) AS n
 WHERE NOT EXISTS (SELECT 1 FROM anagrafiche.emittenti_fiscali e
                    WHERE e.codice IN ('PGTV' || lpad(n::text, 4, '0'), 'PGTW' || lpad(n::text, 4, '0')))
 LIMIT 1;

-- ============================================================
-- Forma
-- ============================================================
SELECT is(
    (SELECT p.prosecdef FROM pg_proc p
      WHERE p.oid = 'anagrafiche.fn_crea_emittente_fiscale(uuid, character varying, jsonb)'::regprocedure),
    false,
    '1. il verbo e'' INVOKER: RLS e permesso restano di chi chiama');

-- ============================================================
-- Il caso felice
-- ============================================================
CREATE TEMP TABLE t_ef1 AS
SELECT e.*
  FROM t_sog s, t_sigla g,
       anagrafiche.fn_crea_emittente_fiscale(s.s1, g.a) AS e;

SELECT is(
    (SELECT format('%s|%s', tr.codice_interno, sr.soggetto_id = s.s1)
       FROM t_ef1 x
       JOIN anagrafiche.emittenti_fiscali ef ON ef.id = x.emittente_fiscale_id
       JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id AND sr.id = x.soggetto_ruolo_id
       JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
       CROSS JOIN t_sog s),
    'EF|t',
    '2. crea l''emittente sul soggetto, col ruolo EF');

SELECT is(
    (SELECT format('%s|%s|%s', ef.attivo, ef.regime_fiscale_rf, ef.regime_fiscale_confermato_il IS NULL)
       FROM t_ef1 x JOIN anagrafiche.emittenti_fiscali ef ON ef.id = x.emittente_fiscale_id),
    't|RF01|t',
    '3. chiavi assenti al DEFAULT (attivo, RF01) e regime NON confermato');

CREATE TEMP TABLE t_ef2 AS
SELECT e.*
  FROM t_sog s, t_sigla g,
       anagrafiche.fn_crea_emittente_fiscale(
           s.s2, g.b,
           jsonb_build_object('regime_fiscale_rf', 'RF01',
                              'valuta_id',         (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1),
                              'bollo_auto',        true,
                              'bollo_soglia',      77.47)) AS e;

SELECT is(
    (SELECT format('%s|%s', ef.regime_fiscale_confermato_il IS NOT NULL, ef.regime_fiscale_confermato_da IS NOT NULL)
       FROM t_ef2 x JOIN anagrafiche.emittenti_fiscali ef ON ef.id = x.emittente_fiscale_id),
    't|t',
    '4. un regime dichiarato e'' confermato: data e autore');

SELECT is(
    (SELECT format('%s|%s|%s', ef.valuta_id IS NOT NULL, ef.bollo_auto, ef.bollo_soglia)
       FROM t_ef2 x JOIN anagrafiche.emittenti_fiscali ef ON ef.id = x.emittente_fiscale_id),
    't|t|77.47',
    '5. i campi opzionali passano (valuta, bollo)');

SELECT cmp_ok(
    (SELECT count(*)::int
       FROM vendite.registri_fatturazione r
       JOIN t_ef1 x ON r.emittente_soggetto_ruolo_id = x.soggetto_ruolo_id),
    '>', 0,
    '6. i registri di numerazione nascono dal trigger, come prima');

-- ============================================================
-- I rifiuti
-- ============================================================
SELECT is(
    pg_temp.codice_errore($$SELECT * FROM anagrafiche.fn_crea_emittente_fiscale(
        (SELECT s1 FROM t_sog), 'PGTX0001', '{"ragione_sociale": "x"}'::jsonb)$$),
    'E_CAMPO_NON_AMMESSO',
    '7. una chiave estranea: E_CAMPO_NON_AMMESSO');

SELECT is(
    pg_temp.contesto_campo($$SELECT * FROM anagrafiche.fn_crea_emittente_fiscale(
        (SELECT s1 FROM t_sog), 'PGTX0001', '{"ragione_sociale": "x"}'::jsonb)$$),
    'ragione_sociale',
    '8. ... e il campo esce sul canale COLUMN, per accenderlo nel form');

SELECT is(
    pg_temp.codice_errore($$SELECT * FROM anagrafiche.fn_crea_emittente_fiscale(
        (SELECT s1 FROM t_sog), 'PGTX0001', '{"regime_fiscale_confermato_il": "2026-01-01"}'::jsonb)$$),
    'E_CAMPO_NON_AMMESSO',
    '9. la conferma del regime non si scrive a mano');

SELECT is(
    pg_temp.codice_errore($$SELECT * FROM anagrafiche.fn_crea_emittente_fiscale(
        (SELECT s1 FROM t_sog), 'PGTX0001', '[]'::jsonb)$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '10. campi che non sono un oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT is(
    pg_temp.vincolo_violato($$SELECT * FROM anagrafiche.fn_crea_emittente_fiscale(
        dbops.fn_pgtap_crea_soggetto_pg('Emittente verbo pgTAP 3'),
        (SELECT a FROM t_sigla))$$),
    'uq:codice',
    '11. codice gia'' usato: esce dal vincolo uq:codice');

SELECT is(
    pg_temp.vincolo_violato($$SELECT * FROM anagrafiche.fn_crea_emittente_fiscale(
        (SELECT s1 FROM t_sog), 'PGTX0002')$$),
    'uq_emittenti_fiscali_ruolo',
    '12. secondo emittente sullo stesso soggetto: esce da uq_emittenti_fiscali_ruolo');

-- ============================================================
-- Il builder
-- ============================================================
-- ⚠️ Il builder in un'istruzione sua: una JOIN nella stessa istruzione non
--   vedrebbe la riga appena creata (fotografia di inizio istruzione).
CREATE TEMP TABLE t_b AS SELECT * FROM dbops.fn_pgtap_crea_emittente();

SELECT is(
    (SELECT format('%s|%s', ef.codice = b.emittente_codice, ef.valuta_id IS NOT NULL)
       FROM t_b b
       JOIN anagrafiche.emittenti_fiscali ef ON ef.id = b.emittente_fiscale_id),
    't|t',
    '13. il builder crea ancora l''emittente, con la valuta');

SELECT ok(
    (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g')
       FROM pg_proc p
      WHERE p.oid = 'dbops.fn_pgtap_crea_emittente(character varying)'::regprocedure)
        ~ 'anagrafiche\.fn_crea_emittente_fiscale\('
    AND (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g')
           FROM pg_proc p
          WHERE p.oid = 'dbops.fn_pgtap_crea_emittente(character varying)'::regprocedure)
        !~* 'INSERT INTO anagrafiche\.emittenti_fiscali',
    '14. il builder chiama il verbo e non scrive piu'' la tabella (regola del 2)');

SELECT * FROM finish();

ROLLBACK;
