-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- L'unita' catastale e' di un'istanza sola, si clona quando nasce il legame
-- con l'istanza precedente, e la tabella ponte e l'unita' lasciata seguono
-- l'istanza. Giro 5 (T7b) di brief-db-revisione-anagrafiche §22: S11 (senza
-- scelta), D-T7b-6 e D-T7b-7 di Tid (2026-11-25).
--
-- ⭐ Scritto ROSSO prima dei changeSet: su ogni caso segnato «(rosso)» il
--   comportamento di prima dava un altro esito.
--
-- Elenco test (plan 10):
--   S11
--    1) l'indice unico su istanze_utilities.catasto_unita_immobiliare_id,
--       parziale sulle righe con l'unita'                          (rosso)
--    2) due istanze sulla stessa unita': 23505 sull'indice          (rosso)
--   D-T7b-6, il clone
--    3) un'istanza che nasce con la precedente riceve il clone      (rosso)
--    4) ... un'unita' sua, non quella della precedente
--    5) la precedente riscritta uguale, dopo un'unita' comparsa sulla
--       precedente, non clona                                       (rosso)
--   D-T7b-7, la ponte e l'unita' lasciata
--    6) il cambio di civico: la coppia di prima esce dalla ponte    (rosso)
--    7) ... e c'e' quella nuova
--    8) il civico di prima, senza piu' coppie, si spegne            (rosso)
--    9) il cambio di unita': l'unita' di prima, che nessuno nomina
--       piu', non c'e' piu'                                         (rosso)
--   10) ... e la nuova ha la sua coppia col civico
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

-- L'esito di un'istruzione: 'ok'; per un errore di dominio il codice e il
-- campo; per ogni altro errore lo SQLSTATE e il vincolo.
CREATE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE
    v_codice text;
    v_campo  text;
    v_stato  text;
BEGIN
    EXECUTE p_sql;
    RETURN 'ok';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME, v_campo = COLUMN_NAME,
                            v_stato = RETURNED_SQLSTATE;
    IF v_stato = 'P0001' AND v_codice <> '' THEN
        RETURN v_codice || '/' || COALESCE(NULLIF(v_campo, ''), '-');
    END IF;
    RETURN v_stato || '/' || COALESCE(NULLIF(v_codice, ''), '-');
END;
$f$;

-- Un'unita' catastale nuova, col suo id.
CREATE FUNCTION pg_temp.unita(p_foglio text) RETURNS bigint
LANGUAGE sql AS $f$
    INSERT INTO anagrafiche.catasto_unita_immobiliari (
        sezione_catastale, foglio_catastale, particella, subalterno,
        categoria_catastale, classe_catastale, rendita_catastale, consistenza,
        tipo_accatastamento, immobile_rurale, destinazione_immobile,
        anno_protocollo, superficie, storicizza)
    VALUES ('T7B', p_foglio, 'T7B01', '0001', 'A/2', '1', 100, 1, 'U', false, 'AB', 2025, 80, true)
    RETURNING id
$f$;

-- ============================================================
-- Fixture: due istanze (A, B) dei builder, ciascuna col suo civico
-- ============================================================
-- ⚠️ Il builder del civico usa i primi 10 caratteri dell'etichetta come
--   interno: etichette brevi e diverse, o i civici sono lo stesso.
-- Le istanze nate qui sotto, senza satellite, restano nella finestra
-- differita del loro guard (require_utility_dichiarata): non sono l'oggetto
-- del test, e il ROLLBACK le porta via.
CREATE TEMP TABLE _f AS
SELECT a.istanza_utility_id AS ist_a, a.soggetto_id AS sogg_a,
       b.istanza_utility_id AS ist_b,
       dbops.fn_pgtap_crea_indirizzo_dettaglio('T7B A') AS civ_a,
       dbops.fn_pgtap_crea_indirizzo_dettaglio('T7B B') AS civ_b,
       dbops.fn_pgtap_crea_indirizzo_dettaglio('T7B C') AS civ_c,
       dbops.fn_pgtap_crea_indirizzo_dettaglio('T7B A2') AS civ_a2,
       pg_temp.unita('UA') AS u_a
  FROM dbops.fn_pgtap_crea_cliente_ba('pgTAP T7b catasto A') a,
       dbops.fn_pgtap_crea_cliente_ba('pgTAP T7b catasto B') b;

UPDATE anagrafiche.istanze_utilities i
   SET indirizzo_dettaglio_id = f.civ_a, catasto_unita_immobiliare_id = f.u_a
  FROM _f f WHERE i.id = f.ist_a;
UPDATE anagrafiche.istanze_utilities i
   SET indirizzo_dettaglio_id = f.civ_b
  FROM _f f WHERE i.id = f.ist_b;

SET CONSTRAINTS anagrafiche.trg_istanze_utilities_z90_require_utility_dichiarata_ins DEFERRED;

-- ============================================================
-- S11: un'unita', un'istanza
-- ============================================================
SELECT is(
    (SELECT format('%s|%s', i.indisunique::text,
                   regexp_replace(pg_get_indexdef(i.indexrelid), '^.* USING ', ''))
       FROM pg_index i
       JOIN pg_class c ON c.oid = i.indexrelid
      WHERE i.indrelid = 'anagrafiche.istanze_utilities'::regclass
        AND c.relname = 'uq_istanze_utilities_catasto_unita_immobiliare'),
    'true|btree (catasto_unita_immobiliare_id) WHERE (catasto_unita_immobiliare_id IS NOT NULL)',
    '1) l''indice unico dell''unita'' dell''istanza, sulle righe che ne hanno una');

SELECT is(
    pg_temp.esito(format(
        'UPDATE anagrafiche.istanze_utilities SET catasto_unita_immobiliare_id = %s WHERE id = %s',
        (SELECT u_a FROM _f), (SELECT ist_b FROM _f))),
    '23505/uq_istanze_utilities_catasto_unita_immobiliare',
    '2) due istanze sulla stessa unita'' non si scrivono');

-- ============================================================
-- D-T7b-6: il clone quando nasce il legame
-- ============================================================
CREATE TEMP TABLE _n AS
WITH n AS (
    INSERT INTO anagrafiche.istanze_utilities (fittizia, codice, soggetto_id, indirizzo_dettaglio_id, parent_istanza_id)
    SELECT true, 'PGTAPT7BC' || substr(md5(clock_timestamp()::text), 1, 8), f.sogg_a, f.civ_c, f.ist_a
      FROM _f f
    RETURNING id)
SELECT id AS ist_c FROM n;

SELECT isnt(
    (SELECT i.catasto_unita_immobiliare_id FROM anagrafiche.istanze_utilities i, _n n WHERE i.id = n.ist_c),
    NULL,
    '3) l''istanza che nasce con la precedente riceve il clone dell''unita''');

SELECT is(
    (SELECT format('%s|%s', (i.catasto_unita_immobiliare_id <> f.u_a)::text, u.foglio_catastale)
       FROM anagrafiche.istanze_utilities i, _n n, _f f, anagrafiche.catasto_unita_immobiliari u
      WHERE i.id = n.ist_c AND u.id = i.catasto_unita_immobiliare_id),
    'true|UA',
    '4) ... un''unita'' sua, copia di quella della precedente');

-- Un'istanza D che nasce con la precedente B, quando B non ha ancora
-- l'unita': niente da clonare. Poi B ne riceve una, e la precedente di D
-- si riscrive uguale (e' cio' che fa il ramo delle fittizie di
-- trgfn_clienti_set_parent_istanza).
CREATE TEMP TABLE _d AS
WITH n AS (
    INSERT INTO anagrafiche.istanze_utilities (fittizia, codice, soggetto_id, indirizzo_dettaglio_id, parent_istanza_id)
    SELECT true, 'PGTAPT7BD' || substr(md5(clock_timestamp()::text), 1, 8), f.sogg_a, f.civ_b, f.ist_b
      FROM _f f
    RETURNING id)
SELECT id AS ist_d FROM n;

UPDATE anagrafiche.istanze_utilities i
   SET catasto_unita_immobiliare_id = pg_temp.unita('UB')
  FROM _f f WHERE i.id = f.ist_b;
UPDATE anagrafiche.istanze_utilities i
   SET parent_istanza_id = i.parent_istanza_id
  FROM _d d WHERE i.id = d.ist_d;

SELECT is(
    (SELECT i.catasto_unita_immobiliare_id FROM anagrafiche.istanze_utilities i, _d d WHERE i.id = d.ist_d),
    NULL,
    '5) la precedente riscritta uguale non clona l''unita'' comparsa dopo');

-- ============================================================
-- D-T7b-7: la ponte e l'unita' lasciata
-- ============================================================
UPDATE anagrafiche.istanze_utilities i
   SET indirizzo_dettaglio_id = f.civ_a2
  FROM _f f WHERE i.id = f.ist_a;

SELECT is(
    (SELECT count(*)::int FROM anagrafiche.catasto_unita_immobiliari_indirizzi x, _f f
      WHERE x.catasto_unita_id = f.u_a AND x.indirizzo_dettaglio_id = f.civ_a),
    0,
    '6) il cambio di civico: la coppia di prima esce dalla ponte');

SELECT is(
    (SELECT count(*)::int FROM anagrafiche.catasto_unita_immobiliari_indirizzi x, _f f
      WHERE x.catasto_unita_id = f.u_a AND x.indirizzo_dettaglio_id = f.civ_a2),
    1,
    '7) ... e c''e'' quella nuova');

SELECT is(
    pg_temp.esito(format('UPDATE anagrafiche.indirizzi_dettaglio SET attivo = false WHERE id = %s',
                         (SELECT civ_a FROM _f))),
    'ok',
    '8) il civico di prima, senza piu'' coppie, si spegne');

CREATE TEMP TABLE _u AS SELECT pg_temp.unita('UA2') AS u_a2;
UPDATE anagrafiche.istanze_utilities i
   SET catasto_unita_immobiliare_id = u.u_a2
  FROM _f f, _u u WHERE i.id = f.ist_a;

SELECT is(
    (SELECT count(*)::int FROM anagrafiche.catasto_unita_immobiliari c, _f f WHERE c.id = f.u_a),
    0,
    '9) il cambio di unita'': l''unita'' di prima, che nessuna istanza nomina, non c''e'' piu''');

SELECT is(
    (SELECT count(*)::int FROM anagrafiche.catasto_unita_immobiliari_indirizzi x, _f f, _u u
      WHERE x.catasto_unita_id = u.u_a2 AND x.indirizzo_dettaglio_id = f.civ_a2),
    1,
    '10) ... e la nuova ha la sua coppia col civico');

SELECT * FROM finish();
ROLLBACK;
