-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il verbo degli indirizzi di un ruolo e il builder che lo usa:
--   anagrafiche.fn_crea_indirizzi_ruolo   (20261017-11)
--   dbops.fn_pgtap_crea_soggetto_ruolo    (20261017-12)
--   Brief: brief-db-processi-accensione-per-ambiente (§5-ter.2, 2b-1 lotto 2).
--
-- ⭐ Il caso si COSTRUISCE: un soggetto PG, il suo ruolo fornitore, una via
--   dal builder dei dettagli. Gli attesi sui tipi obbligatori si leggono dalla
--   matrice del ruolo (config.tipi_ruolo_tipi_indirizzo, seed di catalogo),
--   non si scrivono a mano.
--
-- Elenco test (plan 18):
--   forma
--    1) INVOKER
--   l'auto-clone
--    2) un indirizzo libero: scrive anche gli altri obbligatori, clonati
--    3) ... cioe' ogni tipo obbligatorio della matrice del ruolo c'e'
--    4) ... e il clone porta lo stesso indirizzo del primo
--    5) i vincoli differiti (completezza del ruolo) reggono al controllo
--    6) una seconda chiamata coi tipi gia' presenti: 0, niente duplicati
--    7) elenco vuoto: 0, nemmeno i cloni
--   le tre forme dell'indirizzo
--    8) dettaglio gia' risolto: usato com'e'
--    9) due vie sulla stessa strada con civici diversi: due dettagli diversi
--       (il backend riusava il primo per tutti)
--   10) il tipo per codice interno
--   i rifiuti
--   11) tipo inesistente: E_TIPO_INDIRIZZO_NON_TROVATO
--   12) ... col campo tipo_indirizzo_codice_interno sul canale COLUMN
--   13) chiave estranea: E_CAMPO_NON_AMMESSO
--   14) un elemento che non e' un oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA
--   15) indirizzi che non sono un elenco: E_SCRIPT_CHIAMATA_NON_VALIDA
--   16) ruolo inesistente: E_SOGGETTO_RUOLO_NON_TROVATO
--   il builder
--   17) dbops.fn_pgtap_crea_soggetto_ruolo scrive ancora gli obbligatori
--   18) ... e il suo corpo chiama il verbo, non scrive la tabella
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(18);

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

CREATE OR REPLACE FUNCTION pg_temp.colonna_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = COLUMN_NAME;
    RETURN v_c;
END $$;

-- I tipi obbligatori del fornitore, dalla matrice.
CREATE TEMP TABLE t_obbl AS
SELECT trti.tipo_indirizzo_id, ti.codice_interno
  FROM config.tipi_ruolo_tipi_indirizzo trti
  JOIN config.tipi_ruoli tr      ON tr.id = trti.tipo_ruolo_id
  JOIN config.tipi_indirizzi ti  ON ti.id = trti.tipo_indirizzo_id
 WHERE tr.codice_interno = 'FO' AND trti.attivo AND trti.obbligatorio;

-- Il soggetto e il suo ruolo FO, ancora senza indirizzi: la finestra dei
-- vincoli differiti resta aperta fino al test 5.
CREATE TEMP TABLE t_sr AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Fornitore indirizzi pgTAP') AS soggetto_id, NULL::bigint AS sr_id;

SET CONSTRAINTS ALL DEFERRED;
UPDATE t_sr SET sr_id = script.fn_get_or_create_soggetto_ruolo(p_soggetto_id := soggetto_id, p_cd_int_ruolo := 'FO');

-- Il primo obbligatorio, libero.
CREATE TEMP TABLE t_n1 AS
SELECT anagrafiche.fn_crea_indirizzi_ruolo(
           s.sr_id,
           jsonb_build_array(jsonb_build_object(
               'tipo_indirizzo_id',   (SELECT min(o.tipo_indirizzo_id) FROM t_obbl o),
               'indirizzo_libero',    'Via Indirizzi pgTAP 7',
               'stato_id',            1)
               -- rev 2026-10-18: la forma che il guard vuole per lo stato (Italia: comune e CAP)
               || (SELECT jsonb_strip_nulls(to_jsonb(frm)) FROM dbops.fn_pgtap_indirizzo_libero_forma(1) frm))) AS n
  FROM t_sr s;

-- ============================================================
-- Forma
-- ============================================================
SELECT is(
    (SELECT p.prosecdef FROM pg_proc p
      WHERE p.oid = 'anagrafiche.fn_crea_indirizzi_ruolo(bigint, jsonb)'::regprocedure),
    false,
    '1. il verbo e'' INVOKER');

-- ============================================================
-- L'auto-clone
-- ============================================================
SELECT is((SELECT n FROM t_n1), (SELECT count(*)::int FROM t_obbl),
          '2. un indirizzo libero: il verbo scrive tutti gli obbligatori, gli altri clonati');

SELECT is(
    (SELECT count(*)::int
       FROM t_obbl o
      WHERE EXISTS (SELECT 1 FROM anagrafiche.indirizzi i, t_sr s
                     WHERE i.soggetto_ruolo_id = s.sr_id AND i.tipo_indirizzo_id = o.tipo_indirizzo_id)),
    (SELECT count(*)::int FROM t_obbl),
    '3. ogni tipo obbligatorio della matrice del ruolo c''e''');

SELECT is(
    (SELECT count(DISTINCT i.indirizzo_libero)::int || '|' || min(i.indirizzo_libero)
       FROM anagrafiche.indirizzi i, t_sr s
      WHERE i.soggetto_ruolo_id = s.sr_id),
    '1|Via Indirizzi pgTAP 7',
    '4. il clone porta lo stesso indirizzo del primo');

SELECT lives_ok('SET CONSTRAINTS ALL IMMEDIATE',
                '5. i vincoli differiti del ruolo reggono: la completezza c''e''');

SELECT is(
    (SELECT anagrafiche.fn_crea_indirizzi_ruolo(
                s.sr_id,
                jsonb_build_array(jsonb_build_object(
                    'tipo_indirizzo_id', (SELECT min(o.tipo_indirizzo_id) FROM t_obbl o),
                    'indirizzo_libero',  'Altra via', 'stato_id', 1)
               -- rev 2026-10-18: la forma che il guard vuole per lo stato (Italia: comune e CAP)
               || (SELECT jsonb_strip_nulls(to_jsonb(frm)) FROM dbops.fn_pgtap_indirizzo_libero_forma(1) frm)))
       FROM t_sr s),
    0,
    '6. i tipi gia'' presenti si saltano: 0, niente duplicati');

SELECT is((SELECT anagrafiche.fn_crea_indirizzi_ruolo(s.sr_id, '[]'::jsonb) FROM t_sr s), 0,
          '7. elenco vuoto: 0, nemmeno i cloni');

-- ============================================================
-- Le tre forme: su un secondo ruolo (cliente) dello stesso soggetto
-- ============================================================
-- ⚠️ Il dettaglio PRIMA del ruolo, in un'istruzione sua: un builder puo'
--   richiudere i vincoli differiti, e la completezza del ruolo cliente
--   scatterebbe prima che il verbo gli scriva gli indirizzi.
CREATE TEMP TABLE t_cl AS
SELECT NULL::bigint AS sr_id, dbops.fn_pgtap_crea_indirizzo_dettaglio('Indirizzi ruolo pgTAP') AS det_id;

SET CONSTRAINTS ALL DEFERRED;
UPDATE t_cl SET sr_id = (SELECT script.fn_get_or_create_soggetto_ruolo(p_soggetto_id := s.soggetto_id, p_cd_int_ruolo := 'CL')
                           FROM t_sr s);

-- I tipi ammessi per il cliente, dalla matrice: tre diversi, per tre forme.
CREATE TEMP TABLE t_tipi_cl AS
SELECT ti.id AS tipo_id, ti.codice_interno, row_number() OVER (ORDER BY trti.obbligatorio DESC, ti.id) AS n
  FROM config.tipi_ruolo_tipi_indirizzo trti
  JOIN config.tipi_ruoli tr     ON tr.id = trti.tipo_ruolo_id
  JOIN config.tipi_indirizzi ti ON ti.id = trti.tipo_indirizzo_id
 WHERE tr.codice_interno = 'CL' AND trti.attivo;

CREATE TEMP TABLE t_n2 AS
SELECT anagrafiche.fn_crea_indirizzi_ruolo(
           c.sr_id,
           jsonb_build_array(
               jsonb_build_object('tipo_indirizzo_id', (SELECT tipo_id FROM t_tipi_cl WHERE n = 1),
                                  'indirizzo_dettaglio_id', c.det_id),
               jsonb_build_object('tipo_indirizzo_id', (SELECT tipo_id FROM t_tipi_cl WHERE n = 2),
                                  'stradario_id', d.stradario_id, 'civico', 9001),
               jsonb_build_object('tipo_indirizzo_codice_interno', lower((SELECT codice_interno FROM t_tipi_cl WHERE n = 3)),
                                  'stradario_id', d.stradario_id, 'civico', 9002))) AS n
  FROM t_cl c
  JOIN anagrafiche.indirizzi_dettaglio d ON d.id = c.det_id;

SELECT is(
    (SELECT i.indirizzo_dettaglio_id = c.det_id
       FROM anagrafiche.indirizzi i JOIN t_cl c ON c.sr_id = i.soggetto_ruolo_id
      WHERE i.tipo_indirizzo_id = (SELECT tipo_id FROM t_tipi_cl WHERE n = 1)),
    true,
    '8. dettaglio gia'' risolto: usato com''e''');

SELECT is(
    (SELECT count(DISTINCT i.indirizzo_dettaglio_id)::int
       FROM anagrafiche.indirizzi i JOIN t_cl c ON c.sr_id = i.soggetto_ruolo_id
      WHERE i.tipo_indirizzo_id IN (SELECT tipo_id FROM t_tipi_cl WHERE n IN (2, 3))),
    2,
    '9. due civici sulla stessa strada: due dettagli diversi (il backend riusava il primo)');

SELECT ok(
    EXISTS (SELECT 1 FROM anagrafiche.indirizzi i JOIN t_cl c ON c.sr_id = i.soggetto_ruolo_id
             WHERE i.tipo_indirizzo_id = (SELECT tipo_id FROM t_tipi_cl WHERE n = 3)),
    '10. il tipo per codice interno (anche in minuscolo)');

-- ============================================================
-- I rifiuti
-- ============================================================
SELECT is(
    pg_temp.codice_errore($$SELECT anagrafiche.fn_crea_indirizzi_ruolo(
        (SELECT sr_id FROM t_sr), '[{"tipo_indirizzo_codice_interno": "PGTAP-NON-ESISTE", "indirizzo_libero": "x"}]'::jsonb)$$),
    'E_TIPO_INDIRIZZO_NON_TROVATO',
    '11. tipo inesistente: E_TIPO_INDIRIZZO_NON_TROVATO');

SELECT is(
    pg_temp.colonna_errore($$SELECT anagrafiche.fn_crea_indirizzi_ruolo(
        (SELECT sr_id FROM t_sr), '[{"tipo_indirizzo_codice_interno": "PGTAP-NON-ESISTE", "indirizzo_libero": "x"}]'::jsonb)$$),
    'tipo_indirizzo_codice_interno',
    '12. ... col campo sul canale COLUMN');

SELECT is(
    pg_temp.codice_errore($$SELECT anagrafiche.fn_crea_indirizzi_ruolo(
        (SELECT sr_id FROM t_sr), '[{"tipo_indirizzo_id": 1, "descrizione": "x"}]'::jsonb)$$),
    'E_CAMPO_NON_AMMESSO',
    '13. chiave estranea: E_CAMPO_NON_AMMESSO');

SELECT is(
    pg_temp.codice_errore($$SELECT anagrafiche.fn_crea_indirizzi_ruolo((SELECT sr_id FROM t_sr), '[1]'::jsonb)$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '14. un elemento che non e'' un oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT is(
    pg_temp.codice_errore($$SELECT anagrafiche.fn_crea_indirizzi_ruolo((SELECT sr_id FROM t_sr), '{}'::jsonb)$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '15. indirizzi che non sono un elenco: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT is(
    pg_temp.codice_errore($$SELECT anagrafiche.fn_crea_indirizzi_ruolo(-1, '[]'::jsonb)$$),
    'E_SOGGETTO_RUOLO_NON_TROVATO',
    '16. ruolo inesistente: E_SOGGETTO_RUOLO_NON_TROVATO');

SET CONSTRAINTS ALL IMMEDIATE;

-- ============================================================
-- Il builder
-- ============================================================
CREATE TEMP TABLE t_b AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(dbops.fn_pgtap_crea_soggetto_pg('Fornitore builder pgTAP'), 'FO') AS sr_id;

SELECT is(
    (SELECT count(*)::int
       FROM t_obbl o
      WHERE EXISTS (SELECT 1 FROM anagrafiche.indirizzi i, t_b b
                     WHERE i.soggetto_ruolo_id = b.sr_id AND i.tipo_indirizzo_id = o.tipo_indirizzo_id)),
    (SELECT count(*)::int FROM t_obbl),
    '17. il builder scrive ancora tutti gli obbligatori del ruolo');

SELECT ok(
    (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g')
       FROM pg_proc p
      WHERE p.oid = 'dbops.fn_pgtap_crea_soggetto_ruolo(uuid, character varying, integer)'::regprocedure)
        ~ 'anagrafiche\.fn_crea_indirizzi_ruolo\('
    AND (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g')
           FROM pg_proc p
          WHERE p.oid = 'dbops.fn_pgtap_crea_soggetto_ruolo(uuid, character varying, integer)'::regprocedure)
        !~* 'INSERT INTO anagrafiche\.indirizzi',
    '18. il builder chiama il verbo e non scrive piu'' la tabella (regola del 2)');

SELECT * FROM finish();

ROLLBACK;
