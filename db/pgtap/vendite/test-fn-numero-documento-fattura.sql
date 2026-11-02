-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_numero_documento_fattura — la sede UNICA che compone il
--   numero documento di una fattura: «numero - serie», senza anno.
--   Brief: brief-db-lineage-residui-root-e-sorgente-ddt §3.6-ter.
--   changeSet: 20260829-15.
--
-- ⭐ INTERAMENTE SEED-AGNOSTICO, e non per caso: la funzione e' PURA, prende i
--   due valori e non legge nessuna tabella. Quindi qui non serve NESSUNA
--   fixture — niente soggetti, niente fatture, niente contesto. E' la prova
--   pratica del perche' la sede unica prende i valori e non l'id della
--   fattura: una fn(p_fattura_id) si sarebbe potuta testare solo costruendo
--   un documento, cioe' molto piu' in la' e molto piu' fragile.
--
-- ⛔ COSA PRESIDIA DAVVERO. Non «la funzione concatena»: presidia i due rami
--   in cui una composizione scritta a mano sbaglia in SILENZIO —
--     · serie NULL: `numero::text || ' - ' || serie` non da' '1', da' NULL,
--       cioe' il numero SPARISCE senza nessun errore;
--     · serie stringa vuota: da' '1 - ', un trattino orfano a video.
--   Sono i due casi che chi riscrive la regola non ha ragione di ricordare.
--
-- Indice test (1..10):
--    1) la funzione esiste con la firma attesa
--    2) e' IMMUTABLE (cosi' il pianificatore la inlinea nelle viste)
--    3) ⭐⭐ NON e' STRICT — meta' della regola dipende da questo
--    4) caso pieno: numero + serie
--    5) serie NULL -> il numero da solo, nessun trattino orfano
--    6) serie stringa vuota -> idem
--    7) serie di soli spazi -> idem (i tre modi di «non avere serie»)
--    8) spazi attorno alla serie -> ripuliti
--    9) numero NULL -> NULL, anche con la serie valorizzata
--   10) NULL, NULL -> NULL
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- ⚠️ Qui la RLS non morde niente — la funzione non legge tabelle — ma il
--   contesto si mette lo stesso: un file che fa eccezione insegna che
--   l'eccezione si puo' fare.
--   Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

-- ---- 1..3: la forma della funzione ---------------------------------------
SELECT has_function('vendite', 'fn_numero_documento_fattura',
                    ARRAY['bigint', 'character varying'],
                    '1) fn_numero_documento_fattura(bigint, varchar) esiste');

-- ⭐ IMMUTABLE non e' un'etichetta: e' cio' che permette al pianificatore di
--    INLINEARE la funzione nella select list di vw_documento_lineage_nodi.
--    Declassata a STABLE o VOLATILE diventerebbe una chiamata per riga su
--    tutte le fatture del grafo — nessun errore, solo un piano peggiore.
SELECT is(
    (SELECT provolatile::text FROM pg_proc
      WHERE oid = 'vendite.fn_numero_documento_fattura(bigint,character varying)'::regprocedure),
    'i', '2) e'' IMMUTABLE: viene inlineata nella vista, non chiamata per riga');

-- ⭐⭐ IL TEST CHE VALE PIU' DEGLI ALTRI NOVE.
--    `STRICT` (proisstrict) fa tornare NULL appena UN parametro e' NULL, senza
--    nemmeno entrare nel corpo. Qui la serie NULL e' un caso NORMALE — il
--    documento senza serie — e il risultato giusto e' il numero da solo.
-- ⛔ Aggiungere STRICT «per igiene» spegnerebbe meta' della regola e NON
--    farebbe fallire nessuno degli altri test di forma: passerebbe la firma,
--    passerebbe IMMUTABLE, e il numero sparirebbe dalle note di credito senza
--    serie. Questo test e' il solo che lo direbbe.
SELECT is(
    (SELECT proisstrict FROM pg_proc
      WHERE oid = 'vendite.fn_numero_documento_fattura(bigint,character varying)'::regprocedure),
    false, '3) NON e'' STRICT: serie NULL deve dare il numero, non NULL');

-- ---- 4..8: la composizione, e i tre modi di non avere serie --------------
SELECT is(
    vendite.fn_numero_documento_fattura(103::bigint, 'VX2'::varchar),
    '103 - VX2'::varchar,
    '4) caso pieno: «numero - serie», e l''anno non c''e''');

-- ⛔ I TRE MODI DI «NON AVERE SERIE» devono dare lo stesso risultato, e sono
--    tre perche' significano cose diverse nel dato ma la stessa a video:
--    NULL = mai serializzata, '' = serializzata a vuoto, '   ' = sporcizia.
SELECT is(
    vendite.fn_numero_documento_fattura(1::bigint, NULL::varchar),
    '1'::varchar,
    '5) serie NULL: il numero da solo, senza trattino orfano');

SELECT is(
    vendite.fn_numero_documento_fattura(1::bigint, ''::varchar),
    '1'::varchar,
    '6) serie stringa vuota: idem');

SELECT is(
    vendite.fn_numero_documento_fattura(1::bigint, '   '::varchar),
    '1'::varchar,
    '7) serie di soli spazi: idem');

SELECT is(
    vendite.fn_numero_documento_fattura(103::bigint, '  VX2  '::varchar),
    '103 - VX2'::varchar,
    '8) gli spazi attorno alla serie non entrano nel codice');

-- ---- 9..10: il documento non numerato ------------------------------------
-- ⛔ NULL e NON la stringa vuota, ed e' una scelta: '' e' un valore, e un chip
--    che riceve '' disegna una casella vuota invece di usare la sua fallback
--    (`vendite.lineage.non_numerato`). NULL dice «non c'e'», '' dice «c'e', ed
--    e' niente».
-- ⚠️ Il ramo «non numerata» viene PRIMA di quello sulla serie: senza numero
--    non c'e' niente da comporre, nemmeno con una serie valorizzata. Il test 9
--    e' quello che verifica l'ordine, non il 10.
SELECT is(
    vendite.fn_numero_documento_fattura(NULL::bigint, 'VX2'::varchar),
    NULL::varchar,
    '9) numero NULL: NULL anche con la serie valorizzata (l''ordine dei rami)');

SELECT is(
    vendite.fn_numero_documento_fattura(NULL::bigint, NULL::varchar),
    NULL::varchar,
    '10) tutto NULL: NULL');

SELECT * FROM finish();
ROLLBACK;
