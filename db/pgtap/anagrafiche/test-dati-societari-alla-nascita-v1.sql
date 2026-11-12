-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-differiti: escluso — i soggetti costruiti qui restano SENZA indirizzi:
--   il soggetto del test e' la nascita dei dati societari (il BB, le due porte
--   di creazione, il verbo e i suoi guard BEFORE ROW), che scatta dentro la
--   chiamata, non la saga di completezza, che ha i suoi test. Con IMMEDIATE i
--   guard differiti di soggetti rifiuterebbero ogni fixture prima
--   dell'asserzione. La finestra la apre il file subito dopo il contesto.
-- pgTAP test per Zero ERP
--
-- I dati societari alla nascita di un soggetto: la data di costituzione della
-- societa', la sezione della ditta individuale, una regola sola per le due porte.
--   Brief: brief-db-dati-societari-in-creazione (E-1 (a), D-1 §3.1)
--   changeSet 20261020-01 (BB della nascita), -02 (fn_crea_soggetto_pg),
--   -03 (fn_crea_soggetto_pf)
--
-- Elenco test (plan 18):
--   struttura
--    1) una funzione sola per nome (BB, pg, pf): nessun overload dal DROP+CREATE
--    2) il BB e' SECURITY INVOKER (la porta di scrittura resta il verbo DEFINER)
--    3) fn_crea_soggetto_pg: p_data_costituzione e' l'ultimo parametro, date
--    4) fn_crea_soggetto_pf: i dieci campi in coda, coi nomi di fn_crea_soggetto_pg
--    5) regola del 2: le due porte chiamano il BB, nessuna chiama piu' il verbo
--   il BB
--    6) soggetto NULL -> E_PARAMETRO_INVALIDO
--    7) soggetto inesistente -> E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO
--   societa' ed enti (fn_crea_soggetto_pg)
--    8) una SRL con la data di costituzione: la data e' nella tabella (prima NULL)
--    9) un ente (OPTIONAL) con i soli socio unico e liquidazione: nessuna riga
--   ditta individuale (fn_crea_soggetto_pf)
--   10) con forma «Ditta individuale», canale P, PEC e data -> nasce
--   11) ... e la sua riga porta forma, canale, PEC e data (prima: nessuna riga)
--   12) senza sezione -> nasce, senza riga (OPTIONAL)
--   13) testi vuoti e socio unico soltanto -> nessuna riga (la sezione non c'e')
--   14) canale C senza codice SDI -> E_DATI_SOCIETARI_CODICE_SDI_MANCANTE
--   15) ... e il soggetto non e' nato: una chiamata sola, atomica
--   16) la sezione senza forma -> NOT NULL della forma (23502), come in modifica
--   privato (fn_crea_soggetto_pf)
--   17) con la sezione (la sola data) -> E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO, non scartata
--   18) senza sezione -> nasce, senza riga
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il test gira come l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- La finestra differita la dichiara il file (vedi l'esenzione in testa).
SET CONSTRAINTS ALL DEFERRED;

SELECT plan(18);


CREATE OR REPLACE FUNCTION pg_temp.corpo(p_nome text) RETURNS text
LANGUAGE sql AS $f$
    SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g')
      FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'anagrafiche' AND p.proname = p_nome
$f$;

CREATE TEMP TABLE _ref AS
SELECT (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'SC')  AS sc,
       (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'ENC') AS enc,
       (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'DI')  AS di,
       (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR')  AS pr,
       (SELECT id FROM config.forme_giuridiche WHERE codice = 'SRL') AS srl,
       (SELECT id FROM config.forme_giuridiche WHERE codice = 'DI')  AS forma_di,
       (SELECT p.id FROM config.province p ORDER BY p.id LIMIT 1)    AS prov;

-- ============================================================
-- Struttura
-- ============================================================
SELECT is(
    (SELECT string_agg(p.proname || '=' || p.n, ',' ORDER BY p.proname)
       FROM (SELECT p.proname::text AS proname, count(*)::text AS n
               FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
              WHERE n.nspname = 'anagrafiche'
                AND p.proname IN ('fn_crea_soggetto_pf', 'fn_crea_soggetto_pg',
                                  'fn_scrivi_dati_societari_alla_nascita')
              GROUP BY p.proname) p),
    'fn_crea_soggetto_pf=1,fn_crea_soggetto_pg=1,fn_scrivi_dati_societari_alla_nascita=1',
    '1. una funzione sola per nome: il DROP della firma vecchia non lascia overload');

SELECT ok(
    EXISTS (SELECT 1 FROM pg_catalog.pg_proc p
              JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'anagrafiche' AND p.proname = 'fn_scrivi_dati_societari_alla_nascita'
               AND NOT p.prosecdef),
    '2. il BB della nascita e'' SECURITY INVOKER: la porta di scrittura resta il verbo');

SELECT is(
    (SELECT p.proargnames[p.pronargs] || ' ' || format_type(p.proargtypes[p.pronargs - 1], NULL)
       FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'anagrafiche' AND p.proname = 'fn_crea_soggetto_pg'),
    'p_data_costituzione date',
    '3. fn_crea_soggetto_pg: p_data_costituzione e'' l''ultimo parametro (in coda)');

-- I dieci campi della sezione: in pg stanno fra p_stato_iso2 e p_tipo_contatto_id
-- (posizioni 7..15) piu' la data in coda; in pf sono gli ultimi dieci.
SELECT is(
    (SELECT array_to_string(pf.proargnames[12:21], ',')
       FROM pg_catalog.pg_proc pf JOIN pg_catalog.pg_namespace n ON n.oid = pf.pronamespace
      WHERE n.nspname = 'anagrafiche' AND pf.proname = 'fn_crea_soggetto_pf' AND pf.pronargs = 21),
    (SELECT array_to_string(pg.proargnames[7:15] || 'p_data_costituzione'::text, ',')
       FROM pg_catalog.pg_proc pg JOIN pg_catalog.pg_namespace n ON n.oid = pg.pronamespace
      WHERE n.nspname = 'anagrafiche' AND pg.proname = 'fn_crea_soggetto_pg'),
    '4. fn_crea_soggetto_pf: i dieci campi della sezione in coda, con gli stessi nomi di fn_crea_soggetto_pg');

SELECT is(
    (SELECT string_agg(f || '=' || (pg_temp.corpo(f) ~ 'anagrafiche\.fn_scrivi_dati_societari_alla_nascita\(')::text
                       || '/' || (pg_temp.corpo(f) ~ 'anagrafiche\.fn_scrivi_dati_societari\(')::text, ',' ORDER BY f)
       FROM unnest(ARRAY['fn_crea_soggetto_pf', 'fn_crea_soggetto_pg']) f),
    'fn_crea_soggetto_pf=true/false,fn_crea_soggetto_pg=true/false',
    '5. regola del 2: le due porte chiamano il BB della nascita, nessuna chiama piu'' il verbo da se''');

-- ============================================================
-- Il BB: il soggetto
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT anagrafiche.fn_scrivi_dati_societari_alla_nascita(
        NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL)$$),
    'E_PARAMETRO_INVALIDO',
    '6. soggetto NULL -> E_PARAMETRO_INVALIDO (un chiamante rotto, non «niente da scrivere»)');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT anagrafiche.fn_scrivi_dati_societari_alla_nascita(
        '00000000-0000-0000-0000-000000000000', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL)$$),
    'E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO',
    '7. soggetto inesistente -> E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO');

-- ============================================================
-- Societa' ed enti: fn_crea_soggetto_pg
-- ============================================================
CREATE TEMP TABLE _srl AS
SELECT anagrafiche.fn_crea_soggetto_pg(
           p_ragione_sociale := 'Nascita DS pgTAP srl',
           p_tipo_soggetto_dettaglio_id := (SELECT sc FROM _ref),
           p_email := 'pgtap.nascita.ds.srl@example.com',
           p_partita_iva := v.piva, p_codice_fiscale := v.piva,
           p_forma_giuridica_id := (SELECT srl FROM _ref), p_id_prov_iscri_rea := (SELECT prov FROM _ref),
           p_iscrizione_rea := 'REA-PGTAP-N08', p_capitale_sociale := 10000,
           p_data_costituzione := DATE '2001-02-03') AS id
  FROM (SELECT dbops.fn_pgtap_piva_libera(21) AS piva) v;

SELECT is(
    (SELECT ds.data_costituzione FROM anagrafiche.dati_societari ds
      WHERE ds.soggetto_id = (SELECT id FROM _srl)),
    DATE '2001-02-03',
    '8. una SRL nata con la data di costituzione: la data e'' nella tabella (prima il verbo la riceveva NULL)');

CREATE TEMP TABLE _enc AS
SELECT anagrafiche.fn_crea_soggetto_pg(
           p_ragione_sociale := 'Nascita DS pgTAP ente',
           p_tipo_soggetto_dettaglio_id := (SELECT enc FROM _ref),
           p_email := 'pgtap.nascita.ds.enc@example.com',
           p_partita_iva := v.piva, p_codice_fiscale := v.piva,
           p_socio_unico := 'SM', p_liquidazione := 'LN') AS id
  FROM (SELECT dbops.fn_pgtap_piva_libera(22) AS piva) v;

SELECT is(
    (SELECT count(*)::int FROM anagrafiche.dati_societari ds WHERE ds.soggetto_id = (SELECT id FROM _enc)),
    0,
    '9. un ente (OPTIONAL) con i soli socio unico e liquidazione: nessuna riga (hanno sempre un valore, non fanno la sezione)');

-- ============================================================
-- Ditta individuale: fn_crea_soggetto_pf
-- ============================================================
CREATE TEMP TABLE _di (id uuid);
SELECT lives_ok(
    format($$INSERT INTO _di
             SELECT anagrafiche.fn_crea_soggetto_pf(
                 p_cognome := 'Nascita', p_nome := 'Ditta', p_codice_fiscale := %L,
                 p_email := 'pgtap.nascita.ds.di@example.com',
                 p_tipo_soggetto_dettaglio_id := %s, p_partita_iva := %L,
                 p_forma_giuridica_id := %s, p_destinatario_fe := 'P',
                 p_pec_fatturazione := 'ditta.pgtap@pec.example.com',
                 p_data_costituzione := DATE '2010-11-12')$$,
           dbops.fn_pgtap_cf_libero(), (SELECT di FROM _ref), dbops.fn_pgtap_piva_libera(23),
           (SELECT forma_di FROM _ref)),
    '10. una ditta individuale con forma, canale P, PEC e data nasce');

SELECT is(
    (SELECT count(*)::text || '|' || bool_and(ds.forma_giuridica_id = (SELECT forma_di FROM _ref))::text
            || '|' || max(ds.destinatario_fe) || '|' || max(ds.pec_fatturazione)
            || '|' || max(ds.data_costituzione)::text
       FROM anagrafiche.dati_societari ds WHERE ds.soggetto_id = (SELECT id FROM _di)),
    '1|true|P|ditta.pgtap@pec.example.com|2010-11-12',
    '11. ... e i suoi dati societari ci sono, interi (prima la sezione si perdeva in silenzio)');

CREATE TEMP TABLE _di_vuota AS
SELECT anagrafiche.fn_crea_soggetto_pf(
           p_cognome := 'Nascita', p_nome := 'Senza sezione', p_codice_fiscale := dbops.fn_pgtap_cf_libero(),
           p_email := 'pgtap.nascita.ds.di.vuota@example.com',
           p_tipo_soggetto_dettaglio_id := (SELECT di FROM _ref),
           p_partita_iva := dbops.fn_pgtap_piva_libera(24)) AS id;

SELECT is(
    (SELECT count(*)::int FROM _di_vuota s
       JOIN anagrafiche.soggetti so ON so.id = s.id
       LEFT JOIN anagrafiche.dati_societari ds ON ds.soggetto_id = s.id
      WHERE ds.id IS NULL),
    1,
    '12. una ditta individuale senza sezione nasce, senza dati societari (OPTIONAL)');

CREATE TEMP TABLE _di_bianca AS
SELECT anagrafiche.fn_crea_soggetto_pf(
           p_cognome := 'Nascita', p_nome := 'Sezione bianca', p_codice_fiscale := dbops.fn_pgtap_cf_libero(),
           p_email := 'pgtap.nascita.ds.di.bianca@example.com',
           p_tipo_soggetto_dettaglio_id := (SELECT di FROM _ref),
           p_partita_iva := dbops.fn_pgtap_piva_libera(25),
           p_iscrizione_rea := '  ', p_pec_fatturazione := '', p_codice_sdi := ' ',
           p_socio_unico := 'SU', p_liquidazione := 'LN') AS id;

SELECT is(
    (SELECT count(*)::int FROM anagrafiche.dati_societari ds WHERE ds.soggetto_id = (SELECT id FROM _di_bianca)),
    0,
    '13. testi vuoti e il solo socio unico: la sezione non c''e'', nessuna riga');

CREATE TEMP TABLE _cf_atomico AS SELECT dbops.fn_pgtap_cf_libero() AS cf;

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$SELECT anagrafiche.fn_crea_soggetto_pf(
              p_cognome := 'Nascita', p_nome := 'Canale C', p_codice_fiscale := %L,
              p_email := 'pgtap.nascita.ds.di.c@example.com',
              p_tipo_soggetto_dettaglio_id := %s, p_partita_iva := %L,
              p_forma_giuridica_id := %s, p_destinatario_fe := 'C')$$,
        (SELECT cf FROM _cf_atomico), (SELECT di FROM _ref), dbops.fn_pgtap_piva_libera(26),
        (SELECT forma_di FROM _ref))),
    'E_DATI_SOCIETARI_CODICE_SDI_MANCANTE',
    '14. una ditta individuale col canale C e senza codice SDI -> E_DATI_SOCIETARI_CODICE_SDI_MANCANTE');

SELECT is(
    (SELECT count(*)::int FROM anagrafiche.soggetti s WHERE s.codice_fiscale = (SELECT cf FROM _cf_atomico)),
    0,
    '15. ... e il soggetto non e'' nato: soggetto e sezione sono una chiamata sola, atomica');

SELECT throws_ok(
    format($$SELECT anagrafiche.fn_crea_soggetto_pf(
               p_cognome := 'Nascita', p_nome := 'Senza forma', p_codice_fiscale := %L,
               p_email := 'pgtap.nascita.ds.di.forma@example.com',
               p_tipo_soggetto_dettaglio_id := %s, p_partita_iva := %L,
               p_destinatario_fe := 'P', p_pec_fatturazione := 'senza.forma@pec.example.com')$$,
           dbops.fn_pgtap_cf_libero(), (SELECT di FROM _ref), dbops.fn_pgtap_piva_libera(27)),
    '23502', NULL,
    '16. la sezione senza forma -> NOT NULL della forma (23502), come in modifica (C-2)');

-- ============================================================
-- Privato: fn_crea_soggetto_pf
-- ============================================================
-- ⚠️ La sezione senza forma: con una forma parlerebbe prima il guard BEFORE ROW
--   della forma (E_FORMA_GIURIDICA_NON_AMMESSA_PER_TIPO_SOGGETTO, l'ordine e' per
--   nome), e il test non vedrebbe il guard della natura.
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$SELECT anagrafiche.fn_crea_soggetto_pf(
              p_cognome := 'Nascita', p_nome := 'Privato', p_codice_fiscale := %L,
              p_email := 'pgtap.nascita.ds.pr@example.com', p_sesso := 'F',
              p_tipo_soggetto_dettaglio_id := %s,
              p_data_costituzione := DATE '2015-01-01')$$,
        dbops.fn_pgtap_cf_libero(), (SELECT pr FROM _ref))),
    'E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO',
    '17. un privato (NONE) con la sezione -> E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO: rifiutata, non scartata');

CREATE TEMP TABLE _pr AS
SELECT anagrafiche.fn_crea_soggetto_pf(
           p_cognome := 'Nascita', p_nome := 'Privato senza', p_codice_fiscale := dbops.fn_pgtap_cf_libero(),
           p_email := 'pgtap.nascita.ds.pr.vuoto@example.com', p_sesso := 'M',
           p_tipo_soggetto_dettaglio_id := (SELECT pr FROM _ref)) AS id;

SELECT is(
    (SELECT count(*)::int FROM _pr s
       JOIN anagrafiche.soggetti so ON so.id = s.id
       LEFT JOIN anagrafiche.dati_societari ds ON ds.soggetto_id = s.id
      WHERE ds.id IS NULL),
    1,
    '18. un privato senza sezione nasce, senza dati societari');

SELECT * FROM finish();
ROLLBACK;
