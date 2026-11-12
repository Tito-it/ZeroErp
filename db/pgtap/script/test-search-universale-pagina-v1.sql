-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce soggetti, ruoli e un cliente di
--   un'azienda nuova; il soggetto del test sono conteggio, ordine e pagina
--   della lista, non il perimetro (lo prova script/test-search-scope-interno-v1
--   con FORCE ROW LEVEL SECURITY).
-- pgTAP test per Zero ERP
--
-- La lista della ricerca universale: il totale e le pagine dicono il vero.
-- Brief: brief-db-ricerca-universale-tetto-10000 (D23; strada B e D-2 di Tid
--   del 2026-10-10), changeSet 20261010-16.
--
-- Elenco test (plan 9):
--   1) il totale e' quello di TUTTE le corrispondenze, non della pagina
--   2) la prima pagina in ordine di ragione sociale comincia dalla prima vera
--   3) ordine discendente: comincia dall'ultima vera
--   4) tre pagine coprono tutte le corrispondenze, senza ripetere nessuno
--   5) oltre l'ultima pagina: zero righe
--   6) il cliente in pagina porta la sua utility (aggregato calcolato per la pagina)
--   7) ...e il suo emittente (aggregato sotto la RLS di clienti)
--   8) un ruolo senza clienti: utility_list NULL
--   9) * ordinare per utility_list -> E_PARAMETRO_INVALIDO (D-2: non piu' ordinabile)
--
-- Scopo:
--  - fino al 2026-10-10 la lista teneva al massimo 10.000 corrispondenze con un
--    LIMIT senza ORDER BY: oltre il tetto totale falso, prima pagina non vera,
--    pagine che potevano ripetere o saltare. Ora conteggio, ordine e pagina si
--    fanno su tutte le corrispondenze, e gli aggregati solo per la pagina.
--  - Non serve fabbricare 10.000 soggetti: il tetto non c'e' piu', e la
--    proprieta' da provare e' che totale e pagine si calcolano sull'INSIEME,
--    mentre la pagina ne mostra una parte. Basta un insieme piu' grande di una
--    pagina (7 soggetti, pagine da 3).
--  - ⚠️ Dichiarato: sotto le 10.000 corrispondenze anche il corpo vecchio
--    passava 1-8. Il caso oltre il vecchio tetto vorrebbe 10.000 soggetti
--    costruiti, e non si fabbrica in un pgTAP. Questi test pinnano le
--    proprieta' della forma nuova (totale sull'insieme, pagine contigue,
--    aggregati per la pagina), che non dipendono da quante sono le
--    corrispondenze; il 9 distingue il corpo nuovo dal vecchio.
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca: sette soggetti col ruolo RE
--   (nessuna entita_esistenza: si vedono se esistono) con un termine che nessun
--   altro soggetto ha, e un cliente col termine suo, legato all'azienda di
--   contesto.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- Contesto applicativo: un'azienda col suo operatore, costruita, e il contesto
-- aperto su di lui. Il cliente costruito dopo si lega a quest'azienda
-- (trigger z90 del billing account).
CREATE TEMP TABLE _op ON COMMIT DROP AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _op));
END $ctx$;


CREATE TEMP TABLE _ruoli ON COMMIT DROP AS
SELECT tr.codice_interno, tr.id FROM config.tipi_ruoli tr;

-- ============================================================
-- Fixture: sette soggetti RE, in un ordine alfabetico noto
-- ============================================================
CREATE TEMP TABLE _re ON COMMIT DROP AS
SELECT l AS lettera,
       dbops.fn_pgtap_crea_soggetto_ruolo(
           dbops.fn_pgtap_crea_soggetto_pg('ZQPAGRE ' || l || ' pgTAP pagina'),
           'RE'::character varying) AS sr_id
  FROM unnest(ARRAY['A', 'B', 'C', 'D', 'E', 'F', 'G']) AS l;

-- Le tre pagine (da 3) in ordine di ragione sociale: chiamate separate, come
-- le fa il backend.
CREATE TEMP TABLE _pagine ON COMMIT DROP AS
SELECT pg.n AS pagina, r.*
  FROM generate_series(0, 2) AS pg(n)
  CROSS JOIN LATERAL script.fn_search_soggetti_universale(
           'ZQPAGRE',
           (SELECT id FROM _ruoli WHERE codice_interno = 'RE'),
           3, pg.n * 3, 'ragione_sociale_completa', 'ASC') r;

-- Il cliente, col termine suo: utility BASE (nessun PDP).
CREATE TEMP TABLE _cl ON COMMIT DROP AS
SELECT * FROM dbops.fn_pgtap_crea_cliente(
           'ZQPAGCL',
           (SELECT u.id FROM config.utilities u WHERE u.codice_interno = 'BASE'));

-- ============================================================
-- 1-5) Totale, ordine, pagine
-- ============================================================

SELECT is(
    (SELECT DISTINCT total_count FROM _pagine WHERE pagina = 0),
    7::bigint,
    '1. il totale e'' quello di tutte le corrispondenze (7), non della pagina (3)'
);

SELECT is(
    (SELECT r.soggetto_ruolo_id FROM _pagine r WHERE r.pagina = 0
      ORDER BY r.ragione_sociale_completa LIMIT 1),
    (SELECT sr_id FROM _re WHERE lettera = 'A'),
    '2. la prima pagina in ordine di ragione sociale comincia dalla prima vera (A)'
);

SELECT is(
    (SELECT r.soggetto_ruolo_id
       FROM script.fn_search_soggetti_universale(
                'ZQPAGRE', (SELECT id FROM _ruoli WHERE codice_interno = 'RE'),
                3, 0, 'ragione_sociale_completa', 'DESC') r
      LIMIT 1),
    (SELECT sr_id FROM _re WHERE lettera = 'G'),
    '3. ordine discendente: la prima pagina comincia dall''ultima vera (G)'
);

SELECT is(
    (SELECT count(*)::text || '/' || count(DISTINCT soggetto_ruolo_id)::text FROM _pagine),
    '7/7',
    '4. tre pagine da 3 coprono tutte le 7 corrispondenze, nessuna ripetuta'
);

SELECT is(
    (SELECT count(*)
       FROM script.fn_search_soggetti_universale(
                'ZQPAGRE', (SELECT id FROM _ruoli WHERE codice_interno = 'RE'),
                3, 9, 'ragione_sociale_completa', 'ASC')),
    0::bigint,
    '5. oltre l''ultima pagina: zero righe'
);

-- ============================================================
-- 6-8) Gli aggregati, calcolati per la pagina
-- ============================================================

SELECT is(
    (SELECT r.utility_list
       FROM script.fn_search_soggetti_universale(
                'ZQPAGCL', (SELECT id FROM _ruoli WHERE codice_interno = 'CL')) r
      WHERE r.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM _cl)),
    'BASE',
    '6. il cliente in pagina porta la sua utility'
);

SELECT is(
    (SELECT r.emittente_ragione_sociale
       FROM script.fn_search_soggetti_universale(
                'ZQPAGCL', (SELECT id FROM _ruoli WHERE codice_interno = 'CL')) r
      WHERE r.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM _cl)),
    (SELECT s.ragione_sociale_completa::text
       FROM anagrafiche.soggetti_ruoli sr
       JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
      WHERE sr.id = script.fn_get_ba_emittente_sr_id((SELECT billing_account_id FROM _cl))),
    '7. il cliente in pagina porta l''emittente del suo billing account'
);

SELECT is(
    (SELECT count(*) FROM _pagine WHERE utility_list IS NOT NULL),
    0::bigint,
    '8. un ruolo senza clienti (RE): utility_list NULL su ogni riga'
);

-- ============================================================
-- 9) D-2: utility_list non e' piu' ordinabile
-- ============================================================

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $q$SELECT * FROM script.fn_search_soggetti_universale('ZQPAGRE', %s, 3, 0, 'utility_list', 'ASC')$q$,
        (SELECT id FROM _ruoli WHERE codice_interno = 'RE'))),
    'E_PARAMETRO_INVALIDO',
    '9. * ordinare per utility_list -> E_PARAMETRO_INVALIDO (D-2: un aggregato non si ordina)'
);

SELECT * FROM finish();
ROLLBACK;
