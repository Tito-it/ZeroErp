-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test — il catalogo dei registri del giornale e la vista che li cuce
--   config.registri_giornale (20260919-08, seed 20260919-09)
--   script.vw_giornale_entita (rev 20260919-04)
--   Brief: brief-db-registri-giornale-catalogo, sezione 4.3
--
-- Elenco test (plan 13):
--   LA FORMA
--    1) la tabella c'e', con le colonne del contratto (lookup generico + etichetta_key,
--       sorgente, obsoleto_dal)
--    2) ⛔ e SENZA `attivo`: l'asse del ritiro e' uno solo (obsoleto_dal), come tipi_entita
--   I DUE VERSI — sulla DEFINIZIONE della vista, non sulle sue righe
--    3) la regex legge almeno un letterale da pg_get_viewdef (senza, 4 e 5 sarebbero
--       verdi per sottrazione)
--    4) ⛔ ogni registro che la vista EMETTE e' a catalogo e vivo (obsoleto_dal IS NULL)
--    5) ⛔ ogni registro VIVO a catalogo ha il suo ramo nella vista
--    6) ⭐ la `sorgente` di ogni riga viva si risolve ED e' una dipendenza viva della vista
--   IL CONTRATTO CON I CONSUMATORI
--    7) il lookup generico legge il catalogo e restituisce esattamente i registri vivi
--    8) l'etichetta_key segue il patto: config.registri_giornale.<codice_interno minuscolo>
--   I VINCOLI — un caso ciascuno
--    9) ⛔ codice_interno fuori alfabeto (minuscolo) -> CHECK (23514)
--   10) ⛔ etichetta_key fuori namespace -> CHECK (23514)
--   11) ⛔ sorgente non qualificata -> CHECK (23514)
--   12) ⛔ codice_interno duplicato -> UNIQUE (23505)
--   13) ⛔ codice_interno e' immutabile: il lock generato da ci_apply rifiuta l'UPDATE
--
-- Scopo:
--  - ⭐ E' il test che rende il catalogo una SEDE e non una quarta copia del
--    vocabolario: senza i test 4 e 5, config.registri_giornale sarebbe una
--    tabella da tenere allineata a mano alla vista, come la costante del
--    backend che vuole sostituire. Un ramo nuovo senza la sua riga fa rosso;
--    una riga seminata senza il suo UNION ALL fa rosso.
--  - I due versi si leggono dalla DEFINIZIONE (pg_get_viewdef), non dalle
--    righe: un test che iterasse sul contenuto del giornale passerebbe a
--    vuoto su un database ricostruito da zero (regola zero, corollario sui
--    test). Il test 3 e' il guard del metro: se la forma della vista cambia
--    e la regex non legge piu' niente, e' lui a dirlo, non un verde muto.
--
-- ⚠️ IL TEST 13 DIPENDE DA `ci_apply`. Il lock su codice_interno lo genera il
--   framework delle automazioni (per la sola presenza della colonna,
--   linee-guida-sql 6b) nella SECONDA passata di Liquibase in CI, o col job
--   pgAgent delle 21:00 su dev: su un database migrato senza --ci-apply e'
--   rosso PER ASSENZA, non per difetto. Sta per ultimo apposta: se il lock
--   manca l'UPDATE passa, e non deve sporcare i test prima di lui.
--
-- ⚠️ I test 9-12 NON lasciano righe: ogni INSERT e' respinto. Vengono dopo
--   il 4 e il 5 comunque, cosi' un vincolo che un giorno si allargasse non
--   farebbe rosso il verso sbagliato.
--   ⚠️ E danno un `id` ESPLICITO (999999): il seed ha id fissi e un INSERT
--   senza id prenderebbe l'id 1 dalla sequence — il 12 sarebbe verde per la
--   PK e non per l'UNIQUE su codice_interno (trovato il 19-09 nella mutazione).
--   Il resync della sequence sta nel seed (20260919-09), ma il test non ci
--   conta: prova il vincolo che dice, non la sequence.
--
-- Runner: applicazione (default). config.* non ha RLS; leggere un catalogo,
--   la definizione di una vista e i cataloghi di sistema e' cio' che
--   l'applicazione fa.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- Fixture: i due insiemi, letti UNA volta
-- ============================================================
--   ⚠️ TEMP TABLE e non TEMP VIEW: pg_get_viewdef e pg_depend si leggono una
--   volta sola, e ogni asserzione confronta insiemi gia' materializzati.
CREATE TEMP TABLE tmp_rg_letterali ON COMMIT DROP AS
SELECT m[1] AS registro
  FROM regexp_matches(
         pg_get_viewdef('script.vw_giornale_entita'::regclass),
         '''([A-Z][A-Z0-9_]*)''::text AS registro',
         'g') AS m;

--   Le relazioni che la regola di riscrittura della vista referenzia: sono le
--   tabelle dei FROM e dei JOIN di ogni ramo, e sono un fatto di catalogo
--   (pg_depend), non una lettura del testo.
CREATE TEMP TABLE tmp_rg_dipendenze ON COMMIT DROP AS
SELECT DISTINCT d.refobjid AS relid
  FROM pg_rewrite r
  JOIN pg_depend  d ON d.objid = r.oid AND d.classid = 'pg_rewrite'::regclass
 WHERE r.ev_class   = 'script.vw_giornale_entita'::regclass
   AND d.refclassid = 'pg_class'::regclass
   AND d.refobjid  <> r.ev_class;

-- ============================================================
-- 1-2) LA FORMA
-- ============================================================
SELECT ok(
    ARRAY['codice', 'codice_interno', 'descrizione', 'etichetta_key', 'id',
          'obsoleto_dal', 'sorgente']::text[]
        <@ (SELECT array_agg(c.column_name::text ORDER BY c.column_name)
              FROM information_schema.columns c
             WHERE c.table_schema = 'config' AND c.table_name = 'registri_giornale'),
    '1) config.registri_giornale ha le colonne del contratto (lookup generico + etichetta_key, sorgente, obsoleto_dal)'
);

--   ⛔ Non e' una dimenticanza, e il test lo pinna: un registro non si assegna
--   a niente e le righe vecchie del diario restano leggibili. Il ritiro di un
--   ramo e' obsoleto_dal; un secondo flag sarebbe una domanda senza risposta
--   (stessa scelta di config.tipi_entita e config.eventi_dominio).
SELECT hasnt_column(
    'config', 'registri_giornale', 'attivo',
    '2) niente colonna attivo: l''asse del ritiro e'' uno solo (obsoleto_dal)'
);

-- ============================================================
-- 3-6) I DUE VERSI, sulla definizione della vista
-- ============================================================
--   ⚠️ Il guard del metro. Se la vista venisse riscritta in una forma che la
--   regex non legge (un CASE, una funzione, un cast diverso), 4 e 5 sarebbero
--   verdi su insiemi vuoti: e' il verde per sottrazione, e questo lo impedisce.
SELECT cmp_ok(
    (SELECT count(*)::int FROM tmp_rg_letterali), '>', 0,
    '3) la regex legge almeno un letterale ''X''::text AS registro dalla definizione della vista'
);

SELECT is_empty(
    $$ SELECT l.registro
         FROM tmp_rg_letterali l
        WHERE NOT EXISTS (
                SELECT 1 FROM config.registri_giornale rg
                 WHERE rg.codice_interno = l.registro
                   AND rg.obsoleto_dal IS NULL) $$,
    '4) ogni registro che la vista emette e'' a catalogo e vivo (un ramo senza la sua riga)'
);

SELECT is_empty(
    $$ SELECT rg.codice_interno
         FROM config.registri_giornale rg
        WHERE rg.obsoleto_dal IS NULL
          AND NOT EXISTS (
                SELECT 1 FROM tmp_rg_letterali l
                 WHERE l.registro = rg.codice_interno) $$,
    '5) ogni registro vivo a catalogo ha il suo ramo nella vista (una riga senza il suo UNION ALL)'
);

--   ⭐ E' il lavoro che il brief chiedeva a un tipo regclass, fatto dove si
--   puo' fare davvero: il nome si risolve OGGI, e la tabella e' fra quelle
--   che la vista legge OGGI. Una sorgente rinominata o sostituita in un ramo
--   fa rosso qui, non un numero muto in una colonna.
SELECT is_empty(
    $$ SELECT rg.codice_interno, rg.sorgente
         FROM config.registri_giornale rg
        WHERE rg.obsoleto_dal IS NULL
          AND (   to_regclass(rg.sorgente) IS NULL
               OR NOT EXISTS (
                    SELECT 1 FROM tmp_rg_dipendenze d
                     WHERE d.relid = to_regclass(rg.sorgente))) $$,
    '6) la sorgente di ogni registro vivo si risolve ed e'' una dipendenza della vista'
);

-- ============================================================
-- 7-8) IL CONTRATTO CON I CONSUMATORI
-- ============================================================
--   Il lookup generico e' il lettore che il frontend montera'
--   (<LookupSelect rel="config.registri_giornale">): se la forma della
--   tabella non gli va bene, e' qui che si vede, non nel drawer.
SELECT set_eq(
    $$ SELECT k.codice_interno
         FROM dbops.fn_get_lookup_codici('config.registri_giornale'::regclass) k $$,
    $$ SELECT rg.codice_interno
         FROM config.registri_giornale rg
        WHERE rg.obsoleto_dal IS NULL $$,
    '7) il lookup generico legge il catalogo e restituisce esattamente i registri vivi'
);

--   Il CHECK garantisce il namespace; il patto completo — il suffisso e' il
--   codice_interno minuscolo — lo pinna il test, perche' e' la convenzione
--   con cui il frontend scrive le chiavi nei locales.
SELECT is_empty(
    $$ SELECT rg.codice_interno, rg.etichetta_key
         FROM config.registri_giornale rg
        WHERE rg.etichetta_key <> 'config.registri_giornale.' || lower(rg.codice_interno) $$,
    '8) etichetta_key = config.registri_giornale.<codice_interno minuscolo>, su ogni riga'
);

-- ============================================================
-- 9-12) I VINCOLI
-- ============================================================
SELECT throws_ok(
    $$ INSERT INTO config.registri_giornale
           (id, codice_interno, codice, descrizione, etichetta_key, sorgente)
       VALUES (999999, 'pgtap_minuscolo', 'PGTAP', 'pgtap', 'config.registri_giornale.pgtap', 'vendite.event_log') $$,
    '23514', NULL,
    '9) codice_interno fuori alfabeto (minuscolo) -> rifiutato dal CHECK'
);

SELECT throws_ok(
    $$ INSERT INTO config.registri_giornale
           (id, codice_interno, codice, descrizione, etichetta_key, sorgente)
       VALUES (999999, 'PGTAP_NS', 'PGTAP_NS', 'pgtap', 'vendite.giornale.pgtap', 'vendite.event_log') $$,
    '23514', NULL,
    '10) etichetta_key fuori dal namespace config.registri_giornale.* -> rifiutata dal CHECK'
);

SELECT throws_ok(
    $$ INSERT INTO config.registri_giornale
           (id, codice_interno, codice, descrizione, etichetta_key, sorgente)
       VALUES (999999, 'PGTAP_SRC', 'PGTAP_SRC', 'pgtap', 'config.registri_giornale.pgtap_src', 'event_log') $$,
    '23514', NULL,
    '11) sorgente senza schema -> rifiutata dal CHECK'
);

SELECT throws_ok(
    $$ INSERT INTO config.registri_giornale
           (id, codice_interno, codice, descrizione, etichetta_key, sorgente)
       VALUES (999999, 'EVENT_LOG', 'PGTAP_DUP', 'pgtap', 'config.registri_giornale.event_log', 'vendite.event_log') $$,
    '23505', NULL,
    '12) codice_interno duplicato -> rifiutato dall''UNIQUE'
);

-- ============================================================
-- 13) IL LOCK — cio' che nessun changeSet scrive
-- ============================================================
--   ⛔ Il lock e' implicito (la sola presenza della colonna codice_interno lo
--   provisiona) e nasce a ci_apply: vedi l'intestazione. Ultimo apposta.
SELECT throws_like(
    $$ UPDATE config.registri_giornale
          SET codice_interno = 'EVENT_LOG_RINOMINATO'
        WHERE codice_interno = 'EVENT_LOG' $$,
    '%Impossibile modificare il valore interno%',
    '13) codice_interno e'' immutabile: il lock generato da ci_apply rifiuta l''UPDATE'
);

SELECT * FROM finish();
ROLLBACK;
