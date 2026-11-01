-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- La catena vw_indirizzi_resolved_* ricreata da 20261101-13:
--   * le derivate proiettano tipo_indirizzo_codice_interno come la base
--     (richiesta BE del 2026-11-01: il drawer indirizzi del ruolo confronta i
--     tipi col codice_interno della matrice);
--   * tipo_indirizzo_codice e' ti.codice intero, non piu' troncato a
--     varchar(10) (config.tipi_indirizzi.codice e' varchar(15)).
--
-- ⭐ Il caso si COSTRUISCE: un soggetto PG (indirizzi di soggetto) e il suo
--   ruolo FO (indirizzi di ruolo), dai builder. Poi il CODICE (display) dei
--   loro tipi si cambia, dentro la transazione, in un valore di piu' di 10
--   caratteri: e' il codice che l'utente puo' rinominare, solo cosi' la
--   colonna si distingue da tipo_indirizzo_codice e il troncamento si vede.
--   Coi seed di oggi codice = codice_interno, e un test che non li separa
--   sarebbe verde anche sulla colonna sbagliata.
--
-- Elenco test (plan 11):
--   forma
--   1-3) _ruolo, _soggetto, _all hanno le colonne della base, stessi nomi,
--        stesso ordine, stessi tipi (l'asimmetria che ha prodotto il difetto)
--   valore
--   4) la fixture separa codice e codice_interno su ogni tipo che usa
--   5) _ruolo: per ogni indirizzo del ruolo, la colonna e' il codice_interno
--      del tipo della riga
--   6) _soggetto: idem per gli indirizzi del soggetto
--   7) _all: idem sui due layer del soggetto
--   8) _ruolo: ... e non e' il display
--   9) _soggetto: ... e non e' il display
--   il display intero
--  10) la base dichiara tipo_indirizzo_codice col tipo di
--      config.tipi_indirizzi.codice
--  11) _all: il display oltre i 10 caratteri esce intero, sui due layer
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- I builder aprono e richiudono da se' la finestra dei differiti.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _f ON COMMIT DROP AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('pgTAP resolved codice interno') AS soggetto_id,
       NULL::bigint AS sr_id;

UPDATE _f SET sr_id = dbops.fn_pgtap_crea_soggetto_ruolo(soggetto_id, 'FO');

-- Gli indirizzi della fixture, dalle tabelle (non dalle viste esaminate).
CREATE TEMP TABLE _righe ON COMMIT DROP AS
SELECT 'RUOLO'::text AS scope, i.id AS indirizzo_id, i.tipo_indirizzo_id
  FROM anagrafiche.indirizzi i, _f
 WHERE i.soggetto_ruolo_id = _f.sr_id
UNION ALL
SELECT 'SOGGETTO', s.id, s.tipo_indirizzo_id
  FROM anagrafiche.indirizzi_soggetti s, _f
 WHERE s.soggetto_id = _f.soggetto_id;

-- Il display dei tipi usati si allontana dal codice interno (il lock e'
-- solo su codice_interno) e supera i 10 caratteri: 'PGTAP_DISPL' + id,
-- dentro i 15 della colonna.
UPDATE config.tipi_indirizzi ti
   SET codice = 'PGTAP_DISPL' || ti.id
 WHERE ti.id IN (SELECT tipo_indirizzo_id FROM _righe);

-- Le colonne di una vista: nome, posizione, tipo.
CREATE FUNCTION pg_temp.colonne(p_vista regclass)
RETURNS TABLE(attnum smallint, attname name, tipo text)
LANGUAGE sql STABLE AS $$
    SELECT a.attnum, a.attname, format_type(a.atttypid, a.atttypmod)
      FROM pg_attribute a
     WHERE a.attrelid = p_vista AND a.attnum > 0 AND NOT a.attisdropped
$$;

-- ============================================================
-- 1-3) Forma: le derivate hanno le colonne della base
-- ============================================================
SELECT results_eq(
    $$SELECT * FROM pg_temp.colonne('anagrafiche.vw_indirizzi_resolved_ruolo') ORDER BY 1$$,
    $$SELECT * FROM pg_temp.colonne('anagrafiche.vw_indirizzi_resolved_base') ORDER BY 1$$,
    '1) vw_indirizzi_resolved_ruolo: le colonne della base, nello stesso ordine');

SELECT results_eq(
    $$SELECT * FROM pg_temp.colonne('anagrafiche.vw_indirizzi_resolved_soggetto') ORDER BY 1$$,
    $$SELECT * FROM pg_temp.colonne('anagrafiche.vw_indirizzi_resolved_base') ORDER BY 1$$,
    '2) vw_indirizzi_resolved_soggetto: le colonne della base, nello stesso ordine');

SELECT results_eq(
    $$SELECT * FROM pg_temp.colonne('anagrafiche.vw_indirizzi_resolved_all') ORDER BY 1$$,
    $$SELECT * FROM pg_temp.colonne('anagrafiche.vw_indirizzi_resolved_base') ORDER BY 1$$,
    '3) vw_indirizzi_resolved_all: le colonne della base, nello stesso ordine');

-- ============================================================
-- 4) La fixture separa display e codice interno
-- ============================================================
SELECT is(
    (SELECT count(*) FILTER (WHERE r.scope = 'RUOLO')    > 0
        AND count(*) FILTER (WHERE r.scope = 'SOGGETTO') > 0
        AND bool_and(ti.codice::text <> ti.codice_interno::text)
        AND bool_and(length(ti.codice) > 10)
       FROM _righe r
       JOIN config.tipi_indirizzi ti ON ti.id = r.tipo_indirizzo_id),
    true,
    '4) la fixture ha indirizzi nei due layer, e ogni loro tipo ha codice <> codice_interno, oltre i 10 caratteri');

-- ============================================================
-- 5-7) Valore: e' il codice_interno del tipo della riga
-- ============================================================
SELECT set_eq(
    $$SELECT v.indirizzo_id, v.tipo_indirizzo_codice_interno::text
        FROM anagrafiche.vw_indirizzi_resolved_ruolo v, _f
       WHERE v.soggetto_ruolo_id = _f.sr_id$$,
    $$SELECT r.indirizzo_id, ti.codice_interno::text
        FROM _righe r JOIN config.tipi_indirizzi ti ON ti.id = r.tipo_indirizzo_id
       WHERE r.scope = 'RUOLO'$$,
    '5) vw_indirizzi_resolved_ruolo: tipo_indirizzo_codice_interno = config.tipi_indirizzi.codice_interno');

SELECT set_eq(
    $$SELECT v.indirizzo_id, v.tipo_indirizzo_codice_interno::text
        FROM anagrafiche.vw_indirizzi_resolved_soggetto v, _f
       WHERE v.soggetto_id = _f.soggetto_id$$,
    $$SELECT r.indirizzo_id, ti.codice_interno::text
        FROM _righe r JOIN config.tipi_indirizzi ti ON ti.id = r.tipo_indirizzo_id
       WHERE r.scope = 'SOGGETTO'$$,
    '6) vw_indirizzi_resolved_soggetto: tipo_indirizzo_codice_interno = config.tipi_indirizzi.codice_interno');

SELECT set_eq(
    $$SELECT v.scope, v.indirizzo_id, v.tipo_indirizzo_codice_interno::text
        FROM anagrafiche.vw_indirizzi_resolved_all v, _f
       WHERE v.soggetto_id = _f.soggetto_id$$,
    $$SELECT r.scope, r.indirizzo_id, ti.codice_interno::text
        FROM _righe r JOIN config.tipi_indirizzi ti ON ti.id = r.tipo_indirizzo_id$$,
    '7) vw_indirizzi_resolved_all: tipo_indirizzo_codice_interno = config.tipi_indirizzi.codice_interno, sui due layer');

-- ============================================================
-- 8-9) ... e il display resta un'altra colonna
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM anagrafiche.vw_indirizzi_resolved_ruolo v, _f
      WHERE v.soggetto_ruolo_id = _f.sr_id
        AND v.tipo_indirizzo_codice::text = v.tipo_indirizzo_codice_interno::text),
    0,
    '8) vw_indirizzi_resolved_ruolo: la colonna non porta il display');

SELECT is(
    (SELECT count(*)::int
       FROM anagrafiche.vw_indirizzi_resolved_soggetto v, _f
      WHERE v.soggetto_id = _f.soggetto_id
        AND v.tipo_indirizzo_codice::text = v.tipo_indirizzo_codice_interno::text),
    0,
    '9) vw_indirizzi_resolved_soggetto: la colonna non porta il display');

-- ============================================================
-- 10-11) Il display esce intero
-- ============================================================
SELECT is(
    (SELECT format_type(a.atttypid, a.atttypmod) FROM pg_attribute a
      WHERE a.attrelid = 'anagrafiche.vw_indirizzi_resolved_base'::regclass
        AND a.attname = 'tipo_indirizzo_codice'),
    (SELECT format_type(a.atttypid, a.atttypmod) FROM pg_attribute a
      WHERE a.attrelid = 'config.tipi_indirizzi'::regclass
        AND a.attname = 'codice'),
    '10) vw_indirizzi_resolved_base: tipo_indirizzo_codice ha il tipo di config.tipi_indirizzi.codice');

SELECT set_eq(
    $$SELECT v.scope, v.indirizzo_id, v.tipo_indirizzo_codice::text
        FROM anagrafiche.vw_indirizzi_resolved_all v, _f
       WHERE v.soggetto_id = _f.soggetto_id$$,
    $$SELECT r.scope, r.indirizzo_id, ti.codice::text
        FROM _righe r JOIN config.tipi_indirizzi ti ON ti.id = r.tipo_indirizzo_id$$,
    '11) vw_indirizzi_resolved_all: tipo_indirizzo_codice e'' il codice intero, oltre i 10 caratteri');

SELECT * FROM finish();
ROLLBACK;
