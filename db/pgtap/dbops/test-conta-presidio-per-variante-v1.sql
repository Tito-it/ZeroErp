-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture semina su dbops.presidi — catalogo che a
--   runtime non scrive nessuno (lo popola il mirror CSV di 80_data) e su cui il
--   ruolo applicativo ha SELECT-only — e crea uno schema e delle viste di prova,
--   cioe' DDL. Stessa situazione, e stessa motivazione, di test-catalogo-presidi-v1.
--
-- Test: il conteggio dei presidi PER VARIANTE, e la sua sede unica
-- Brief: brief-db-presidio-processi-testo-per-causa.md §6.2 (R-2)
--
-- Elenco test (plan 13):
--  1) ⛔ una vista NON a catalogo solleva, e non torna zero (nessun gruppo)
--  2) ⛔ il NULL cade nello stesso rifiuto
--  3) presidio SENZA variante: UNA riga, variante NULL, la vista intera
--  4) ⭐ presidio senza variante e vista VUOTA: la riga c'e' lo stesso, a zero
--  5) ⭐ COSTRUITO: due cause con conteggi diversi, il filtro di stato che
--     esclude, una causa tutta allo stato atteso che NON esce, il gruppo NULL
--  6) fn_conta_presidio sullo stesso presidio = la somma dei gruppi
--  7) presidio con variante e niente da guardare: ZERO gruppi
--  8) ⭐ ...e fn_conta_presidio torna 0, non NULL
--  9) ⭐ fn_conta_presidio NON contiene piu' il filtro: chiama la sede
-- 10) la sede e' SECURITY DEFINER, fn_conta_presidio no
-- 11) search_path pinnato sulle due funzioni
-- 12) zeroerp_app ha EXECUTE sulla sede
-- 13) sui presidi VERI che dichiarano colonna_variante la sede risponde, e la
--     somma dei gruppi e' il conteggio
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ PERCHE' IL TEST 9 E NON «GLI ESITI COINCIDONO». Il contratto del brief
--   chiedeva «la somma dei conteggi e' uguale a fn_conta_presidio per ogni
--   presidio». Dal -42 fn_conta_presidio E' quella somma: il confronto sarebbe
--   vero per costruzione e non proverebbe niente. Quello che puo' rompersi e'
--   che qualcuno rimetta un filtro dentro fn_conta_presidio — una seconda
--   copia, che prima o poi diverge. Il presidio e' quindi sul SORGENTE:
--   linee-guida-sql §12.5.2, «il presidio da scrivere non e' "gli esiti
--   coincidono", e' "la madre non contiene piu' il predicato"».
--   Il test 13 resta, ma per un'altra ragione: esegue la sede sulle viste
--   VERE con variante, cioe' prova che la colonna dichiarata esiste e che il
--   GROUP BY gira li', non su una vista finta.
--
-- ⭐ I casi si COSTRUISCONO (5-8): su un database ricostruito da zero (la CI)
--   il presidio dei processi e' vuoto, e un test che contasse le righe di
--   oggi passerebbe a vuoto.
--
-- ⚠️ La fixture vive in uno SCHEMA SUO e non in `dbops`: se le viste nascessero
--   li', il verso 1 di test-catalogo-presidi-v1 non c'entrerebbe (gira in
--   un'altra transazione), ma chi copia la fixture la porterebbe in dbops.
--
-- ── ⚠️ LIMITI DICHIARATI ────────────────────────────────────────
--   · Gira da owner: l'attraversamento della RLS da `zeroerp_app` senza GUC
--     non si vede da qui. I presupposti (il proprietario delle tabelle) li
--     asserisce test-catalogo-presidi-v1 test 11, che dal 2026-10-10 nomina
--     la sede.
--   · Il test 13 su un catalogo senza presidi con variante passerebbe a
--     vuoto: per questo lo dice ed e' rosso («misura degradata»). Oggi il
--     presidio dei processi la dichiara per seed, su ogni installazione.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- Fixture — schema suo
-- ============================================================
CREATE SCHEMA pgtap_conta_variante_fixture;

-- Senza variante, senza stato: quattro righe.
CREATE VIEW pgtap_conta_variante_fixture.vw_intera AS
SELECT * FROM (VALUES (1), (2), (3), (4)) AS t(n);

-- Senza variante, vuota: la forma di una vista sana.
CREATE VIEW pgtap_conta_variante_fixture.vw_vuota AS
SELECT n FROM (VALUES (1)) AS t(n) WHERE false;

-- ⭐ Con variante E con stato, costruita per distinguere ogni ramo:
--   A: due righe da guardare + una allo stato atteso   -> A = 2
--   B: una riga da guardare                            -> B = 1
--   C: solo righe allo stato atteso                    -> C NON esce
--   NULL: una riga KO e una con lo stato NUOVO         -> NULL = 2
--   ⚠️ La causa e' un integer apposta: la sede deve renderla testo (::text).
--   ⚠️ CIRCOSTANZA_NUOVA e' lo stato che qualcuno aggiungera' domani: deve
--     contare (si conta il DIVERSO dall'atteso), come nel test 10 del catalogo.
CREATE VIEW pgtap_conta_variante_fixture.vw_cause AS
SELECT * FROM (VALUES
    ('OK',                10),
    ('KO',                10),
    ('KO',                10),
    ('KO',                20),
    ('OK',                30),
    ('OK',                30),
    ('KO',                NULL::integer),
    ('CIRCOSTANZA_NUOVA', NULL::integer)
) AS t(stato, causa);

-- Con variante, tutte le righe allo stato atteso: niente da guardare.
CREATE VIEW pgtap_conta_variante_fixture.vw_cause_sane AS
SELECT * FROM (VALUES ('OK', 'A'), ('OK', 'B')) AS t(stato, causa);

INSERT INTO dbops.presidi (vista, natura, colonna_stato, stato_atteso,
                           cadenza, perimetro, nota, chi_agisce, colonna_variante)
VALUES ('pgtap_conta_variante_fixture.vw_intera', 'ZERO', NULL, NULL,
        'MAI', 'LIBERO', 'fixture pgTAP: senza variante', 'SVILUPPO', NULL),
       ('pgtap_conta_variante_fixture.vw_vuota', 'ZERO', NULL, NULL,
        'MAI', 'LIBERO', 'fixture pgTAP: senza variante, vuota', 'SVILUPPO', NULL),
       ('pgtap_conta_variante_fixture.vw_cause', 'ZERO', 'stato', 'OK',
        'MAI', 'LIBERO', 'fixture pgTAP: con variante e stato', 'SVILUPPO', 'causa'),
       ('pgtap_conta_variante_fixture.vw_cause_sane', 'ZERO', 'stato', 'OK',
        'MAI', 'LIBERO', 'fixture pgTAP: con variante, sana', 'SVILUPPO', 'causa');

-- ============================================================
-- 1) e 2) Il perimetro e' il catalogo: rifiuta, non torna zero
-- ============================================================
-- ⚠️ Con lo SQLSTATE: throws_ok(sql, NULL, NULL) accetta QUALUNQUE errore,
--   compreso un permesso negato che non c'entra niente.
SELECT throws_ok(
    $$SELECT * FROM dbops.fn_conta_presidio_per_variante('dbops.vw_che_non_esiste_affatto')$$,
    'P0001', NULL,
    '1) una vista non a catalogo e'' rifiutata, non contata a zero');

SELECT throws_ok(
    $$SELECT * FROM dbops.fn_conta_presidio_per_variante(NULL)$$,
    'P0001', NULL,
    '2) il NULL cade nello stesso rifiuto');

-- ============================================================
-- 3) e 4) Senza variante: UNA riga, anche a zero
-- ============================================================
SELECT is(
    (SELECT string_agg(coalesce(variante, '<NULL>') || ':' || conteggio, '|')
       FROM dbops.fn_conta_presidio_per_variante('pgtap_conta_variante_fixture.vw_intera')),
    '<NULL>:4',
    '3) senza variante: una riga, variante NULL, la vista intera');

-- ⭐ E' il ramo che rende «una lettura sola» vera per il BE: senza questa riga
--   un presidio sano senza variante non avrebbe gruppi, e il chiamante
--   dovrebbe distinguere «zero» da «niente».
SELECT is(
    (SELECT string_agg(coalesce(variante, '<NULL>') || ':' || conteggio, '|')
       FROM dbops.fn_conta_presidio_per_variante('pgtap_conta_variante_fixture.vw_vuota')),
    '<NULL>:0',
    '4) senza variante e vista vuota: la riga c''e'' lo stesso, a zero');

-- ============================================================
-- 5) ⭐ COSTRUITO: cause diverse, filtro di stato, gruppo NULL
-- ============================================================
-- ⚠️ WITH ORDINALITY: si asserisce anche l'ordine che la sede consegna
--   (per valore, il NULL in coda), che il BE puo' leggere cosi' com'e'.
-- ⛔ Se C comparisse, il filtro di stato non filtra; se NULL mancasse, il
--   gruppo senza causa sparirebbe dal conteggio in silenzio; se NULL valesse 1,
--   lo stato NUOVO cadrebbe nel silenzio.
SELECT is(
    (SELECT string_agg(coalesce(c.variante, '<NULL>') || ':' || c.conteggio, '|'
                       ORDER BY c.ord)
       FROM dbops.fn_conta_presidio_per_variante('pgtap_conta_variante_fixture.vw_cause')
            WITH ORDINALITY AS c(variante, conteggio, ord)),
    '10:2|20:1|<NULL>:2',
    '5) per causa: conteggi diversi, il filtro di stato esclude, la causa sana non esce, il NULL e'' un gruppo');

-- ============================================================
-- 6) fn_conta_presidio = la somma dei gruppi
-- ============================================================
SELECT is(
    dbops.fn_conta_presidio('pgtap_conta_variante_fixture.vw_cause'),
    5::bigint,
    '6) fn_conta_presidio sullo stesso presidio conta la somma dei gruppi');

-- ============================================================
-- 7) e 8) Con variante e niente da guardare: zero gruppi, conteggio 0
-- ============================================================
SELECT is(
    (SELECT count(*) FROM dbops.fn_conta_presidio_per_variante('pgtap_conta_variante_fixture.vw_cause_sane')),
    0::bigint,
    '7) con variante e niente da guardare: nessun gruppo (i valori a zero non escono)');

-- ⛔ La somma di niente e' NULL: senza il coalesce il digest riceverebbe un
--   NULL, che non e' «niente da guardare».
SELECT is(
    dbops.fn_conta_presidio('pgtap_conta_variante_fixture.vw_cause_sane'),
    0::bigint,
    '8) ...e fn_conta_presidio torna 0, non NULL');

-- ============================================================
-- 9) ⭐ fn_conta_presidio non contiene piu' il filtro
-- ============================================================
-- Il sorgente senza commenti `--` (un presidio sul testo si accende sulla
-- prosa che lo spiega): nessuna lettura del catalogo, nessuna colonna di
-- stato, nessun confronto — e la chiamata alla sede.
SELECT is(
    (SELECT (src !~ '\mdbops\.presidi\M'
             AND src !~* 'colonna_stato|stato_atteso|IS DISTINCT FROM|EXECUTE'
             AND src ~ 'dbops\.fn_conta_presidio_per_variante\s*\(')
       FROM (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g') AS src
               FROM pg_proc p
               JOIN pg_namespace n ON n.oid = p.pronamespace
              WHERE n.nspname = 'dbops'
                AND p.proname = 'fn_conta_presidio') s),
    true,
    '9) fn_conta_presidio non riscrive perimetro ne'' filtro: chiama la sede');

-- ============================================================
-- 10) e 11) Sicurezza e search_path
-- ============================================================
SELECT is(
    (SELECT string_agg(p.proname || '=' || CASE WHEN p.prosecdef THEN 'DEFINER' ELSE 'INVOKER' END,
                       ', ' ORDER BY p.proname)
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'dbops'
        AND p.proname IN ('fn_conta_presidio', 'fn_conta_presidio_per_variante')),
    'fn_conta_presidio=INVOKER, fn_conta_presidio_per_variante=DEFINER',
    '10) la sede e'' SECURITY DEFINER, la somma no');

SELECT is(
    (SELECT string_agg(p.proname || ':' || array_to_string(p.proconfig, ','),
                       ' / ' ORDER BY p.proname)
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'dbops'
        AND p.proname IN ('fn_conta_presidio', 'fn_conta_presidio_per_variante')),
    'fn_conta_presidio:search_path=pg_catalog, pg_temp / fn_conta_presidio_per_variante:search_path=pg_catalog, pg_temp',
    '11) search_path pinnato sulle due funzioni');

-- ============================================================
-- 12) GRANT
-- ============================================================
-- ⭐ has_function_privilege sul ruolo, mai information_schema (cieco sugli
--   altri ruoli: linee-guida-sql §11.8).
SELECT ok(
    has_function_privilege('zeroerp_app',
                           'dbops.fn_conta_presidio_per_variante(text)', 'EXECUTE'),
    '12) zeroerp_app ha EXECUTE su fn_conta_presidio_per_variante');

-- ============================================================
-- 13) Sui presidi VERI con variante la sede gira, e la somma torna
-- ============================================================
-- ⚠️ Solo i presidi con colonna_variante: e' il ramo nuovo, e il solo che
--   puo' rompersi su una vista vera (colonna rinominata, tipo). Rieseguire
--   ogni presidio costerebbe due volte le viste piu' pesanti (riferimenti
--   morti compila ogni funzione) per provare una somma vera per costruzione.
-- ⚠️ La fixture e' esclusa per schema: e' gia' provata sopra.
-- ⛔ Misura non degradata: senza presidi veri con variante il confronto
--   passerebbe a vuoto, e lo dice invece di tacere.
SELECT is(
    CASE
        WHEN NOT EXISTS (SELECT 1 FROM dbops.presidi p
                          WHERE p.colonna_variante IS NOT NULL
                            AND p.attivo
                            AND p.obsoleto_dal IS NULL
                            AND split_part(p.vista, '.', 1) <> 'pgtap_conta_variante_fixture')
        THEN 'misura degradata: nessun presidio a catalogo dichiara colonna_variante'
        ELSE coalesce((
            SELECT string_agg(p.vista, ', ' ORDER BY p.vista)
              FROM dbops.presidi p
             WHERE p.colonna_variante IS NOT NULL
               AND p.attivo
               AND p.obsoleto_dal IS NULL
               AND split_part(p.vista, '.', 1) <> 'pgtap_conta_variante_fixture'
               AND dbops.fn_conta_presidio(p.vista)
                   IS DISTINCT FROM (SELECT coalesce(sum(c.conteggio), 0)::bigint
                                       FROM dbops.fn_conta_presidio_per_variante(p.vista) c)), '')
    END,
    '',
    '13) sui presidi veri con variante la sede risponde, e la somma dei gruppi e'' il conteggio');

SELECT * FROM finish();
ROLLBACK;
