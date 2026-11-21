-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- La madre del fornitore:
--   anagrafiche.fn_crea_fornitore   (20261018-30)
--   Brief: brief-db-processi-accensione-per-ambiente (§5-ter.2, 2b-1 lotto 4).
--
-- ⭐ Il caso si COSTRUISCE: soggetti PG dal builder, un indirizzo libero, un
--   contatto. Gli attesi sui tipi obbligatori si leggono dalla matrice del
--   ruolo (config.tipi_ruolo_tipi_indirizzo, seed di catalogo).
-- ⭐ La completezza del ruolo (indirizzi obbligatori) e' un guard DIFFERITO:
--   in IMMEDIATE scatterebbe gia' sull'INSERT del ruolo, dentro la madre. Le
--   scritture girano quindi DEFERRED, come nella transazione del backend, e il
--   test 8 chiude la finestra con SET CONSTRAINTS ALL IMMEDIATE: e' il commit.
--
-- Elenco test (plan 21):
--   forma
--    1) INVOKER
--   il caso felice (ruolo nuovo, contatto, un indirizzo)
--    2) ritorna il fornitore e il suo ruolo FO
--    3) nasce nello stato iniziale VE
--    4) il codice lo genera il trigger
--    5) i campi indicati sono scritti (rating, note)
--    6) il contatto del ruolo e' scritto
--    7) ogni tipo obbligatorio della matrice c'e' (auto-clone del BB)
--    8) ... e la completezza del ruolo regge al controllo (il commit)
--   il ruolo gia' presente (builder), senza contatto ne' indirizzi
--    9) riusa il ruolo esistente
--   10) contatto NULL: nessun contatto di ruolo nuovo
--   11) una chiave a null vale assente: il codice e' generato lo stesso
--   i rifiuti
--   12) lo stato fra i campi: E_CAMPO_NON_AMMESSO
--   13) ... col campo stato_fornitore_id sul canale COLUMN
--   14) soggetto NULL: E_SCRIPT_CHIAMATA_NON_VALIDA
--   15) contatto incompleto: E_CONTATTO_INCOMPLETO (la regola del BB)
--   16) un secondo fornitore sullo stesso soggetto: uq_fornitori_soggetto_ruolo_id
--   i doppioni ritirati e il regime (20261121-03 … -06, brief-db-fornitore-
--   doppioni-del-soggetto, giro B)
--   17) le sei chiavi dei doppioni e il nome vecchio del regime: E_CAMPO_NON_AMMESSO
--   18) regime_fiscale_rf ammesso e scritto
--   19) ... e la vista lo espone con la descrizione del catalogo
--   20) un regime fuori catalogo: fk_fornitori_regimi_fiscali
--   21) tabella e vista non hanno piu' le colonne ritirate
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL DEFERRED;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(21);


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

-- ⚠️ rev 2026-11-17 (brief-db-fornitore-privato-indirizzi §8.3-bis, la (C)): nel seed il
--   fornitore ha un solo obbligatorio (FATT), e con uno solo la copia degli
--   obbligatori non si esercita (il test passerebbe per sottrazione). Il secondo
--   (POSTA, che la societa' del test ammette) lo scrive il test, prima di leggerli.
DELETE FROM config.tipi_ruolo_tipi_indirizzo
 WHERE tipo_ruolo_id = (SELECT id FROM config.tipi_ruoli WHERE codice_interno = 'FO')
   AND tipo_indirizzo_id = (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'POSTA');
INSERT INTO config.tipi_ruolo_tipi_indirizzo (id, tipo_ruolo_id, tipo_indirizzo_id, obbligatorio, attivo)
SELECT (SELECT COALESCE(max(m.id), 0) + 1 FROM config.tipi_ruolo_tipi_indirizzo m), tr.id, ti.id, true, true
  FROM config.tipi_ruoli tr, config.tipi_indirizzi ti
 WHERE tr.codice_interno = 'FO' AND ti.codice_interno = 'POSTA';

-- I tipi obbligatori del fornitore, dalla matrice.
CREATE TEMP TABLE t_obbl AS
SELECT trti.tipo_indirizzo_id
  FROM config.tipi_ruolo_tipi_indirizzo trti
  JOIN config.tipi_ruoli tr ON tr.id = trti.tipo_ruolo_id
 WHERE tr.codice_interno = 'FO' AND trti.attivo AND trti.obbligatorio;

CREATE TEMP TABLE t_s AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Fornitore madre pgTAP')    AS s_nuovo,
       dbops.fn_pgtap_crea_soggetto_pg('Fornitore ruolo pgTAP')    AS s_ruolo,
       dbops.fn_pgtap_crea_soggetto_pg('Fornitore contatto pgTAP') AS s_contatto,
       (SELECT t.id FROM config.tipi_contatti t ORDER BY t.id LIMIT 1) AS tipo_contatto_id;

-- Il secondo soggetto ha gia' il ruolo FO, coi suoi indirizzi (builder).
CREATE TEMP TABLE t_sr AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(s.s_ruolo, 'FO') AS sr_id FROM t_s s;

-- Il caso felice: ruolo nuovo, contatto, un solo indirizzo libero.
-- ⚠️ DEFERRED qui, dopo i builder: dbops.fn_pgtap_crea_soggetto_ruolo chiude
--   la sua finestra e rimette i vincoli IMMEDIATE.
SET CONSTRAINTS ALL DEFERRED;

CREATE TEMP TABLE t_f1 AS
SELECT f.*
  FROM t_s s,
       anagrafiche.fn_crea_fornitore(
           s.s_nuovo,
           jsonb_build_object('rating', 3, 'note', 'Nota madre pgTAP'),
           jsonb_build_object('nominativo', 'Ufficio vendite', 'tipo_contatto_id', s.tipo_contatto_id),
           jsonb_build_array(jsonb_build_object(
               'tipo_indirizzo_id',   (SELECT min(o.tipo_indirizzo_id) FROM t_obbl o),
               'indirizzo_libero',    'Via Fornitori pgTAP 4',
               'stato_id',            1)
               -- rev 2026-10-18: la forma che il guard vuole per lo stato (Italia: comune e CAP)
               || (SELECT jsonb_strip_nulls(to_jsonb(frm)) FROM dbops.fn_pgtap_indirizzo_libero_forma(1) frm))) f;

-- Il ruolo gia' presente: nessun contatto, nessun indirizzo, codice a null.
CREATE TEMP TABLE t_f2 AS
SELECT f.*
  FROM t_s s,
       anagrafiche.fn_crea_fornitore(s.s_ruolo, '{"codice": null}'::jsonb) f;

-- ============================================================
-- Forma
-- ============================================================
SELECT is(
    (SELECT p.prosecdef FROM pg_proc p
      WHERE p.oid = 'anagrafiche.fn_crea_fornitore(uuid, jsonb, jsonb, jsonb)'::regprocedure),
    false,
    '1. la madre e'' INVOKER');

-- ============================================================
-- Il caso felice
-- ============================================================
SELECT is(
    (SELECT format('%s|%s', fo.soggetto_ruolo_id = f.soggetto_ruolo_id, tr.codice_interno)
       FROM t_f1 f
       JOIN anagrafiche.fornitori fo     ON fo.id = f.fornitore_id
       JOIN anagrafiche.soggetti_ruoli sr ON sr.id = f.soggetto_ruolo_id
       JOIN config.tipi_ruoli tr          ON tr.id = sr.tipo_ruolo_id
       JOIN t_s s                         ON s.s_nuovo = sr.soggetto_id),
    't|FO',   -- format() di un boolean: t
    '2. ritorna il fornitore e il suo ruolo FO del soggetto');

SELECT is(
    (SELECT sf.codice_interno::text
       FROM t_f1 f
       JOIN anagrafiche.fornitori fo   ON fo.id = f.fornitore_id
       JOIN config.stati_fornitore sf  ON sf.id = fo.stato_fornitore_id),
    'VE',
    '3. nasce nello stato iniziale VE');

SELECT ok(
    (SELECT NULLIF(btrim(fo.codice), '') IS NOT NULL
       FROM t_f1 f JOIN anagrafiche.fornitori fo ON fo.id = f.fornitore_id),
    '4. il codice lo genera il trigger');

SELECT is(
    (SELECT format('%s|%s', fo.rating, fo.note)
       FROM t_f1 f JOIN anagrafiche.fornitori fo ON fo.id = f.fornitore_id),
    '3|Nota madre pgTAP',
    '5. i campi indicati sono scritti');

SELECT is(
    (SELECT string_agg(c.nominativo, ',')
       FROM t_f1 f JOIN anagrafiche.contatti c ON c.soggetto_ruolo_id = f.soggetto_ruolo_id),
    'Ufficio vendite',
    '6. il contatto del ruolo e'' scritto');

SELECT is(
    (SELECT count(*)::int
       FROM t_obbl o
      WHERE EXISTS (SELECT 1 FROM anagrafiche.indirizzi i, t_f1 f
                     WHERE i.soggetto_ruolo_id = f.soggetto_ruolo_id
                       AND i.tipo_indirizzo_id = o.tipo_indirizzo_id)),
    (SELECT count(*)::int FROM t_obbl),
    '7. ogni tipo obbligatorio della matrice c''e'' (auto-clone del BB)');

SELECT lives_ok(
    $$SET CONSTRAINTS ALL IMMEDIATE$$,
    '8. ... e la completezza del ruolo regge al controllo (il commit)');

-- I rifiuti creano un ruolo prima di fallire: la finestra si riapre.
SET CONSTRAINTS ALL DEFERRED;

-- ============================================================
-- Il ruolo gia' presente
-- ============================================================
SELECT is((SELECT soggetto_ruolo_id FROM t_f2), (SELECT sr_id FROM t_sr),
          '9. riusa il ruolo FO esistente');

SELECT is(
    (SELECT count(*)::int FROM t_f2 f JOIN anagrafiche.contatti c ON c.soggetto_ruolo_id = f.soggetto_ruolo_id),
    0,
    '10. contatto NULL: nessun contatto di ruolo');

SELECT ok(
    (SELECT NULLIF(btrim(fo.codice), '') IS NOT NULL
       FROM t_f2 f JOIN anagrafiche.fornitori fo ON fo.id = f.fornitore_id),
    '11. una chiave a null vale assente: il codice e'' generato lo stesso');

-- ============================================================
-- I rifiuti
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT * FROM anagrafiche.fn_crea_fornitore(
        (SELECT s_contatto FROM t_s), '{"stato_fornitore_id": 2}'::jsonb)$$),
    'E_CAMPO_NON_AMMESSO',
    '12. lo stato fra i campi: E_CAMPO_NON_AMMESSO');

SELECT is(
    pg_temp.colonna_errore($$SELECT * FROM anagrafiche.fn_crea_fornitore(
        (SELECT s_contatto FROM t_s), '{"stato_fornitore_id": 2}'::jsonb)$$),
    'stato_fornitore_id',
    '13. ... col campo stato_fornitore_id sul canale COLUMN');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT * FROM anagrafiche.fn_crea_fornitore(NULL)$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '14. soggetto NULL: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT * FROM anagrafiche.fn_crea_fornitore(
        (SELECT s_contatto FROM t_s), '{}'::jsonb, '{"nominativo": "Senza tipo"}'::jsonb)$$),
    'E_CONTATTO_INCOMPLETO',
    '15. contatto incompleto: E_CONTATTO_INCOMPLETO, la regola del BB');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT * FROM anagrafiche.fn_crea_fornitore((SELECT s_ruolo FROM t_s))$$),
    'uq_fornitori_soggetto_ruolo_id',
    '16. un secondo fornitore sullo stesso soggetto: uq_fornitori_soggetto_ruolo_id');

-- ============================================================
-- I doppioni ritirati e il regime (giro B)
-- ============================================================
SELECT is(
    (SELECT COALESCE(array_agg(k ORDER BY k), '{}'::text[])
       FROM unnest(ARRAY['giorni_pagamento', 'fine_mese', 'split_payment', 'bollo_esente',
                         'canale_fe', 'pec_email', 'regime_fiscale']) AS k
      WHERE dbops.fn_pgtap_codice_errore(format(
                $f$SELECT * FROM anagrafiche.fn_crea_fornitore(
                       (SELECT s_contatto FROM t_s), jsonb_build_object(%L, 'x'))$f$, k))
            IS DISTINCT FROM 'E_CAMPO_NON_AMMESSO'),
    '{}'::text[],
    '17. le chiavi ritirate (sei doppioni e regime_fiscale): tutte E_CAMPO_NON_AMMESSO');

-- Il regime: un soggetto col ruolo dal builder, il primo regime attivo del
-- catalogo (ordine, poi id). Il builder rimette i vincoli IMMEDIATE.
CREATE TEMP TABLE t_rf AS
SELECT rf.codice_interno::text AS rf, rf.descrizione::text AS descrizione
  FROM config.regimi_fiscali rf
 WHERE rf.attivo
 ORDER BY rf.ordine NULLS LAST, rf.id
 LIMIT 1;

CREATE TEMP TABLE t_sreg AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Fornitore regime pgTAP') AS s;
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(s, 'FO') FROM t_sreg;
SET CONSTRAINTS ALL DEFERRED;

CREATE TEMP TABLE t_f3 AS
SELECT f.*
  FROM t_sreg r, t_rf c,
       anagrafiche.fn_crea_fornitore(r.s, jsonb_build_object('regime_fiscale_rf', c.rf)) f;

SELECT is(
    (SELECT fo.regime_fiscale_rf::text
       FROM t_f3 f JOIN anagrafiche.fornitori fo ON fo.id = f.fornitore_id),
    (SELECT rf FROM t_rf),
    '18. regime_fiscale_rf ammesso e scritto');

SELECT is(
    (SELECT format('%s|%s', v.regime_fiscale_rf, v.regime_fiscale_descrizione)
       FROM t_f3 f JOIN anagrafiche.vw_fornitori_dettaglio v ON v.id = f.fornitore_id),
    (SELECT format('%s|%s', rf, descrizione) FROM t_rf),
    '19. la vista espone il regime con la descrizione del catalogo');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT * FROM anagrafiche.fn_crea_fornitore(
        (SELECT s_contatto FROM t_s), '{"regime_fiscale_rf": "RF00"}'::jsonb)$$),
    'fk_fornitori_regimi_fiscali',
    '20. un regime fuori catalogo: fk_fornitori_regimi_fiscali');

SELECT is(
    (SELECT COALESCE(array_agg(format('%s.%s', a.attrelid::regclass, a.attname)
                               ORDER BY a.attrelid::regclass::text, a.attname), '{}'::text[])
       FROM pg_catalog.pg_attribute a
      WHERE a.attrelid IN ('anagrafiche.fornitori'::regclass,
                           'anagrafiche.vw_fornitori_dettaglio'::regclass)
        AND a.attnum > 0 AND NOT a.attisdropped
        AND a.attname IN ('giorni_pagamento', 'fine_mese', 'split_payment', 'bollo_esente',
                          'canale_fe', 'pec_email', 'regime_fiscale')),
    '{}'::text[],
    '21. tabella e vista: le colonne ritirate non ci sono piu''');

SELECT * FROM finish();

ROLLBACK;
