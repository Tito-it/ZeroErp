-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- La copia di un indirizzo del soggetto in altri tipi, sul soggetto: il verbo,
-- la check di riga, la vista di riga e il BB dell'elemento ricostruito dalla riga.
--   Brief: brief-db-copia-indirizzo-soggetto §4.4, §4.5, giro 3 (D-2).
--   ChangeSet 20261115-34 … -39; codici in config/codici_errore.csv e
--   messaggi_errore.csv, registro in config/azioni_riga.csv.
--   ⚠️ La copia verso il RUOLO (dalla riga del ruolo e dalla riga del soggetto
--   del ruolo) va sulla chiave di destinazione e sta in
--   test-copia-indirizzo-destinazione-v1 (brief-db-copia-indirizzo-destinazione).
--
-- Elenco test (plan 16):
--   presidio
--    1) il verbo scrive dalla singolare: nessuna INSERT nel corpo
--   il soggetto (natura senza matrice: tutti i tipi ammessi)
--    2) copia dal dettaglio: lo stesso dettaglio, il tipo nuovo
--    3) copia libera nazionale: tutte le colonne della forma arrivano
--    4) copia libera estera: tutte le colonne della forma arrivano
--    5) due tipi, il secondo gia' presente: E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE
--    6) ... e il primo non e' rimasto scritto (tutto o niente)
--    7) un tipo ripetuto nell'elenco: E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE
--    8) ... e non e' rimasto scritto
--    9) la sorgente di un altro soggetto: E_INDIRIZZO_SOGGETTO_NON_TROVATO
--   10) un tipo che non esiste: E_TIPO_INDIRIZZO_NON_TROVATO
--   11) l'elenco vuoto: E_SCRIPT_CHIAMATA_NON_VALIDA
--   12) la vista di riga: copia proponibile finche' manca un tipo
--   13) due tipi: gli id nell'ordine dei tipi
--   14) tutti i tipi presenti: la vista spegne col motivo NESSUN_TIPO_PROPONIBILE
--   15) ... e il verbo solleva il codice del primo motivo della check
--   16) la check su un indirizzo che non c'e': E_INDIRIZZO_SOGGETTO_NON_TROVATO
--
-- Scopo:
--  - ogni caso si COSTRUISCE: le matrici si tolgono (fallback permissivo), le
--    sorgenti le scrive il test nelle tre forme (dettaglio, libera del
--    catalogo, libera estera), i soggetti dai builder (regola zero).
--  - «nessun tipo proponibile» si costruisce riempiendo tutti i tipi del
--    catalogo, non contando quelli di oggi.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- La fixture crea il soggetto (padre) e i suoi indirizzi nello stesso
-- builder, che apre e richiude da se' la finestra dei differiti.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ============================================================
-- Fixture
-- ============================================================
-- ⚠️ Le colonne delle tabelle temporanee hanno il tipo esplicito: %TYPE nel DDL
--   di tabella non si scrive (linee-guida-sql §5g).
CREATE TEMP TABLE _f ON COMMIT DROP AS
SELECT script.fn_stato_id_da_iso2('IT') AS it_id,
       (SELECT s.id FROM config.stati s WHERE NOT s.catalogo_comuni_completo ORDER BY s.id LIMIT 1) AS estero_id,
       dbops.fn_pgtap_crea_soggetto_pg('pgTAP copia indirizzo A', 3,
                                       script.fn_stato_id_da_iso2('IT')) AS sogg_a,
       dbops.fn_pgtap_crea_soggetto_pg('pgTAP copia indirizzo B', 3,
                                       script.fn_stato_id_da_iso2('IT')) AS sogg_b;

ALTER TABLE _f ADD COLUMN natura bigint;
UPDATE _f SET natura = (SELECT s.tipo_soggetto_dettaglio_id
                          FROM anagrafiche.soggetti s WHERE s.id = _f.sogg_a);

-- Le due forme libere, dal builder della forma (il tipo si aggiunge caso per caso).
CREATE TEMP TABLE _el ON COMMIT DROP AS
SELECT (SELECT jsonb_strip_nulls(jsonb_build_object('indirizzo_libero', 'Via pgTAP copia 1',
                                                    'stato_id', _f.it_id) || to_jsonb(fm))
          FROM dbops.fn_pgtap_indirizzo_libero_forma(_f.it_id) fm) AS nazionale,
       (SELECT jsonb_strip_nulls(jsonb_build_object('indirizzo_libero', 'pgTAP copy street 2',
                                                    'stato_id', _f.estero_id) || to_jsonb(fm))
          FROM dbops.fn_pgtap_indirizzo_libero_forma(_f.estero_id) fm) AS estera,
       dbops.fn_pgtap_crea_indirizzo_dettaglio('pgTAP copia indirizzo') AS dettaglio_id
  FROM _f;

-- La matrice della natura si toglie: tutti i tipi ammessi.
DELETE FROM config.tipi_soggetto_dettaglio_tipi_indirizzo
 WHERE tipo_soggetto_dettaglio_id = (SELECT natura FROM _f);

CREATE FUNCTION pg_temp.tipo(p_codice config.tipi_indirizzi.codice_interno%TYPE)
RETURNS config.tipi_indirizzi.id%TYPE LANGUAGE sql AS
$f$ SELECT id FROM config.tipi_indirizzi WHERE codice_interno = p_codice $f$;

-- L'indirizzo del soggetto A di un tipo (la riga), e le sue colonne della forma.
CREATE FUNCTION pg_temp.ind_a(p_codice config.tipi_indirizzi.codice_interno%TYPE)
RETURNS anagrafiche.indirizzi_soggetti.id%TYPE LANGUAGE sql AS
$f$ SELECT i.id FROM anagrafiche.indirizzi_soggetti i
     WHERE i.soggetto_id = (SELECT sogg_a FROM _f) AND i.tipo_indirizzo_id = pg_temp.tipo(p_codice) $f$;

CREATE FUNCTION pg_temp.forma_a(p_codice config.tipi_indirizzi.codice_interno%TYPE)
RETURNS jsonb LANGUAGE sql AS
$f$ SELECT jsonb_build_object(
               'indirizzo_dettaglio_id', i.indirizzo_dettaglio_id, 'indirizzo_libero', i.indirizzo_libero,
               'stato_id', i.stato_id, 'comune_id', i.comune_id, 'codice_postale_id', i.codice_postale_id,
               'administrative_area', i.administrative_area, 'locality', i.locality,
               'sublocality', i.sublocality, 'postal_code', i.postal_code)
      FROM anagrafiche.indirizzi_soggetti i WHERE i.id = pg_temp.ind_a(p_codice) $f$;

CREATE FUNCTION pg_temp.copia_a(p_sorgente config.tipi_indirizzi.codice_interno%TYPE, p_tipi text[])
RETURNS text LANGUAGE sql AS
$f$ SELECT dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_copia_indirizzo_soggetto(%L::uuid, %s, %L::text[])',
        (SELECT sogg_a FROM _f), pg_temp.ind_a(p_sorgente), p_tipi)) $f$;

-- Le tre sorgenti del soggetto A: RES dal dettaglio, POSTA nazionale, FORNITURA estera.
DO $w$ BEGIN
    PERFORM anagrafiche.fn_crea_indirizzo_soggetto((SELECT sogg_a FROM _f),
        jsonb_build_object('tipo_indirizzo_codice_interno', 'RES',
                           'indirizzo_dettaglio_id', (SELECT dettaglio_id FROM _el)));
    PERFORM anagrafiche.fn_crea_indirizzo_soggetto((SELECT sogg_a FROM _f),
        (SELECT nazionale FROM _el) || jsonb_build_object('tipo_indirizzo_codice_interno', 'POSTA'));
    PERFORM anagrafiche.fn_crea_indirizzo_soggetto((SELECT sogg_a FROM _f),
        (SELECT estera FROM _el) || jsonb_build_object('tipo_indirizzo_codice_interno', 'FORNITURA'));
END $w$;

-- ============================================================
-- 1) Presidio: i verbi scrivono dalla singolare
-- ============================================================
SELECT ok(
    position('anagrafiche.fn_crea_indirizzo_soggetto(' IN
             pg_get_functiondef('anagrafiche.fn_copia_indirizzo_soggetto(uuid, bigint, text[])'::regprocedure)) > 0
    AND pg_get_functiondef('anagrafiche.fn_copia_indirizzo_soggetto(uuid, bigint, text[])'::regprocedure) !~* 'INSERT\s+INTO',
    '1) il verbo scrive dalla singolare: nessuna INSERT nel corpo');

-- ============================================================
-- 2-16) Il soggetto
-- ============================================================
DO $w$ BEGIN
    IF pg_temp.copia_a('RES', ARRAY['DOMFISC']) IS NOT NULL THEN
        RAISE EXCEPTION 'fixture: copia RES -> DOMFISC rifiutata';
    END IF;
END $w$;
SELECT is(
    (pg_temp.forma_a('DOMFISC') ->> 'indirizzo_dettaglio_id')::bigint,
    (SELECT dettaglio_id FROM _el),
    '2) copia dal dettaglio: lo stesso dettaglio, il tipo nuovo');

DO $w$ BEGIN
    IF pg_temp.copia_a('POSTA', ARRAY['SPED']) IS NOT NULL THEN
        RAISE EXCEPTION 'fixture: copia rifiutata';
    END IF;
END $w$;
SELECT is(pg_temp.forma_a('SPED'), pg_temp.forma_a('POSTA'),
          '3) copia libera nazionale: tutte le colonne della forma arrivano');

DO $w$ BEGIN
    IF pg_temp.copia_a('FORNITURA', ARRAY['CON']) IS NOT NULL THEN
        RAISE EXCEPTION 'fixture: copia rifiutata';
    END IF;
END $w$;
SELECT is(pg_temp.forma_a('CON'), pg_temp.forma_a('FORNITURA'),
          '4) copia libera estera: tutte le colonne della forma arrivano');

SELECT is(pg_temp.copia_a('POSTA', ARRAY['SEDEOP', 'SPED']),
          'E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE',
          '5) due tipi, il secondo gia'' presente: E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE');
SELECT is(pg_temp.ind_a('SEDEOP'), NULL,
          '6) ... e il primo non e'' rimasto scritto (tutto o niente)');

SELECT is(pg_temp.copia_a('POSTA', ARRAY['FATT', 'FATT']),
          'E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE',
          '7) un tipo ripetuto nell''elenco: E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE');
SELECT is(pg_temp.ind_a('FATT'), NULL, '8) ... e non e'' rimasto scritto');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_copia_indirizzo_soggetto(%L::uuid, %s, ARRAY[''SEDELEG''])',
        (SELECT sogg_b FROM _f), pg_temp.ind_a('POSTA'))),
    'E_INDIRIZZO_SOGGETTO_NON_TROVATO',
    '9) la sorgente di un altro soggetto: E_INDIRIZZO_SOGGETTO_NON_TROVATO');

SELECT is(pg_temp.copia_a('POSTA', ARRAY['NONC']), 'E_TIPO_INDIRIZZO_NON_TROVATO',
          '10) un tipo che non esiste: E_TIPO_INDIRIZZO_NON_TROVATO');

SELECT is(pg_temp.copia_a('POSTA', '{}'::text[]), 'E_SCRIPT_CHIAMATA_NON_VALIDA',
          '11) l''elenco vuoto: E_SCRIPT_CHIAMATA_NON_VALIDA');

-- Un tipo del catalogo che A non ha ancora (se c'e'): la copia si propone.
SELECT is(
    (SELECT v.copia_blocco_reason FROM anagrafiche.vw_indirizzi_soggetti_azioni v
      WHERE v.indirizzo_soggetto_id = pg_temp.ind_a('POSTA')),
    CASE WHEN (SELECT count(*) FROM config.tipi_indirizzi)
              > (SELECT count(*) FROM anagrafiche.indirizzi_soggetti i WHERE i.soggetto_id = (SELECT sogg_a FROM _f))
         THEN NULL ELSE 'NESSUN_TIPO_PROPONIBILE' END,
    '12) la vista di riga: copia proponibile finche'' manca un tipo');

CREATE TEMP TABLE _ids ON COMMIT DROP AS
SELECT x.id, x.ord
  FROM unnest(anagrafiche.fn_copia_indirizzo_soggetto(
           (SELECT sogg_a FROM _f), pg_temp.ind_a('POSTA'), ARRAY['FATT', 'SEDEOP']))
       WITH ORDINALITY AS x(id, ord);

-- Le righe nuove si rileggono in un'istruzione dopo: quella che le scrive non le vede.
SELECT is(
    (SELECT string_agg(ti.codice_interno, ',' ORDER BY x.ord)
       FROM _ids x
       JOIN anagrafiche.indirizzi_soggetti i ON i.id = x.id
       JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id),
    'FATT,SEDEOP',
    '13) due tipi: gli id nell''ordine dei tipi');

-- Tutti i tipi del catalogo: si copia POSTA in quelli che mancano.
DO $w$ BEGIN
    PERFORM anagrafiche.fn_copia_indirizzo_soggetto((SELECT sogg_a FROM _f), pg_temp.ind_a('POSTA'), m.tipi)
       FROM (SELECT array_agg(ti.codice_interno::text ORDER BY ti.id) AS tipi
               FROM config.tipi_indirizzi ti
              WHERE NOT EXISTS (SELECT 1 FROM anagrafiche.indirizzi_soggetti i
                                 WHERE i.soggetto_id = (SELECT sogg_a FROM _f)
                                   AND i.tipo_indirizzo_id = ti.id)) m
      WHERE m.tipi IS NOT NULL;
END $w$;

SELECT results_eq(
    format($$SELECT copia_blocco_reason, copia_blocco_reason_key
               FROM anagrafiche.vw_indirizzi_soggetti_azioni WHERE indirizzo_soggetto_id = %s$$,
           pg_temp.ind_a('POSTA')),
    $$VALUES ('NESSUN_TIPO_PROPONIBILE'::text,
              'anagrafiche.indirizzi.copia_blocco.nessun_tipo_proponibile'::text)$$,
    '14) tutti i tipi presenti: la vista spegne col motivo NESSUN_TIPO_PROPONIBILE');

SELECT is(pg_temp.copia_a('POSTA', ARRAY['RES']),
          anagrafiche.fn_check_copia_indirizzo_soggetto(pg_temp.ind_a('POSTA')) -> 0 ->> 'codice',
          '15) ... e il verbo solleva il codice del primo motivo della check');

SELECT is(dbops.fn_pgtap_codice_errore(
              'SELECT anagrafiche.fn_check_copia_indirizzo_soggetto(-1)'),
          'E_INDIRIZZO_SOGGETTO_NON_TROVATO',
          '16) la check su un indirizzo che non c''e'': E_INDIRIZZO_SOGGETTO_NON_TROVATO');

SELECT * FROM finish();
ROLLBACK;
