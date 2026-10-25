-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.trgfn_default_emittente_fiscale — l'emittente di default in un
--   building block solo, e le copie di vendite ritirate.
--   Brief: brief-db-emittente-di-default-un-bb-solo (P-6; D1..D5 confermate da
--   Tid il 2026-09-15). ChangeSet 20260915-36 .. 20260915-46.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): riga e conferma dell'ordine del
--   test 13 da dbops.fn_pgtap_crea_ordine_con_righe (p_ordine_id); la testata resta a mano
--   (nasce senza emittente dall'operatore A: e' la premessa del caso).
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in bozza e si
--   portano avanti con dbops.fn_pgtap_porta_a_stato (prima nascevano gia' CONFERMATO
--   l'ordine del test 13, con una riga ora scritta dal test, ed EMESSO il preventivo del 18).
-- rev 2026-10-25 (brief-modello-documento-vendita §8, giro 6): il preventivo del test 18 si
--   emette con una riga (merce, 1 x 10) da dbops.fn_pgtap_crea_preventivo_con_righe
--   (p_preventivo_id): l'emissione senza righe e' rifiutata. La testata resta a mano (nasce
--   con l'emittente di A, e' la premessa di D3); il test legge l'emittente, non le righe.
--
-- Elenco test (plan 18):
--   LA FORMA
--    1) la funzione esiste in script
--    2) le quattro copie di vendite (ordini, preventivi, contratti, ddt) non esistono piu'
--    3) trgfn_commesse_default_emittente RESTA: non era una copia (deriva dal BA)
--    4) nessuna funzione viva nomina le copie ne' i tre codici ritirati (scansione prosrc)
--    5) catalogo: i tre codici hanno obsoleto_dal; E_EMITTENTE_NON_RISOLTO e' DATO_ERRATO
--       con un messaggio «it» senza segnaposto
--    6) le UNDICI tabelle montate sul BB sono esattamente quelle di brief sezione 5
--    7) nessuna tabella ancorata su emittente_fiscale_id NOT NULL fuori dall'elenco
--       porta il trigger, e le escluse motivate (resi, documenti_generati, commesse,
--       config.user_emittent*) non lo hanno
--    8) su ogni tabella montata il default ORDINA PRIMA di guard_emittente_* e normalize (D5)
--    9) ddt porta i due argomenti ('LASCIA_NULL', 'SALTA_CON_SORGENTE') (D4)
--   IL COMPORTAMENTO (fixture costruita: aziende A, B, S; SA = operatore di S con
--   binding SUPER_ADMIN; una quarta azienda Z il cui operatore e' un SECONDO
--   super admin, mai attore; un indirizzo; un BA di A)
--   10) operatore A, magazzino senza emittente -> A
--   11) SA in modalita' «tutti» (assegnato a S), emittente ESPLICITO A -> resta A
--   12) SA con emittente attivo B -> B (l'attivo di sessione vince sull'assegnato)
--   13) ddt SALTA_CON_SORGENTE: SA (assegnato a S) evade un ordine di A -> il DDT porta A
--   -- da qui il SA e' «admin globale»: senza riga in user_emittenti_fiscali
--   14) SA senza emittente, magazzino senza emittente -> E_EMITTENTE_NON_RISOLTO (P0001, frase)
--   15) GUC app.current_user_id vuota -> E_EMITTENTE_NON_RISOLTO
--   16) ddt LASCIA_NULL: SA senza emittente, DDT DRAFT senza sorgente con BA di A
--       -> nessun errore dal default, emittente dal BA via normalize
--   17) trigger montato con un argomento non ammesso -> E_TRIGGER_ARGOMENTI_INVALIDI
--   18) D3: la rev N+1 di un preventivo di A, creata dal SA senza emittente, porta A
--       (prima: il default di sessione, e la revisione era impossibile)
--
-- ⚠️ La fixture SI COSTRUISCE, non si cerca: su un DB ricostruito da zero non
--   c'e' nessun operatore, nessun BA, nessun indirizzo. Le tre aziende nascono
--   in tre istruzioni (l'ordine di creazione e' portante: la prima e' il
--   default sullo scratch), il contesto si sposta con
--   script.fn_pgtap_set_contesto_operatore(<utente>) ad ogni cambio di attore.
-- ⚠️ IL SECONDO SUPER ADMIN (Z) NON E' UN VEZZO: fn_change_user_emittenti_scope
--   passa da fn_check_ultimo_super_admin_attivo e rifiuta il cambio di scope
--   all'ULTIMO SA attivo (E_PROFILO_ULTIMO_SUPER_ADMIN). Su dbdev un altro SA
--   c'e' sempre; sul database scratch (da zero) il SA del test sarebbe l'unico
--   e il file moriva in fixture (ERRORE_FIXTURE, 2026-09-17). La fixture si
--   costruisce, non si cerca: anche il «non ultimo» va costruito.
-- ⚠️ Le GUC sono transazionali (is_local): il file e' UNA transazione che
--   chiude in ROLLBACK, e dopo la GUC vuota del test 15 il contesto si rimette.
-- ⚠️ throws_like sulla FRASE, mai throws_ok(…, NULL, NULL): il default e il
--   guard di scope sono entrambi P0001, e la frase e' cio' che li distingue.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

-- ============================================================
-- LA FORMA
-- ============================================================
SELECT has_function('script', 'trgfn_default_emittente_fiscale',
    '1. script.trgfn_default_emittente_fiscale esiste');

SELECT is(
    (SELECT count(*)::int FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite'
        AND p.proname IN ('trgfn_ordini_default_emittente', 'trgfn_preventivi_default_emittente',
                          'trgfn_contratti_default_emittente', 'trgfn_ddt_default_emittente')),
    0,
    '2. le quattro copie di vendite non esistono piu''');

SELECT has_function('vendite', 'trgfn_commesse_default_emittente',
    '3. trgfn_commesse_default_emittente resta: deriva dal billing account, non era una copia');

SELECT is(
    (SELECT count(*)::int FROM pg_proc p
      WHERE p.prosrc ~ '(trgfn_(ordini|preventivi|contratti|ddt)_default_emittente|E_(ORDINE|PREV|CONTRATTO)_EMITTENTE_NON_RISOLTO)'),
    0,
    '4. nessuna funzione viva nomina le copie ritirate ne'' i tre codici ritirati');

SELECT ok(
    (SELECT count(*) FROM config.codici_errore
      WHERE codice IN ('E_ORDINE_EMITTENTE_NON_RISOLTO', 'E_PREV_EMITTENTE_NON_RISOLTO', 'E_CONTRATTO_EMITTENTE_NON_RISOLTO')
        AND obsoleto_dal IS NOT NULL) = 3
    AND EXISTS (SELECT 1 FROM config.codici_errore
                 WHERE codice = 'E_EMITTENTE_NON_RISOLTO' AND classe = 'DATO_ERRATO' AND obsoleto_dal IS NULL)
    AND EXISTS (SELECT 1 FROM config.messaggi_errore
                 WHERE codice = 'E_EMITTENTE_NON_RISOLTO' AND lingua = 'it'
                   AND messaggio NOT LIKE '%\%s%' ESCAPE '\'),
    '5. catalogo: tre codici in obsoleto_dal, E_EMITTENTE_NON_RISOLTO DATO_ERRATO con messaggio senza segnaposto');

-- Le tabelle attese, con lo schema: e' l'elenco di brief sezione 5, scritto qui
-- perche' una tabella montata in piu' «per imitazione» faccia rosso.
CREATE TEMP TABLE _attese (rel text PRIMARY KEY) ON COMMIT DROP;
INSERT INTO _attese VALUES
    ('vendite.ordini'), ('vendite.preventivi'), ('vendite.contratti'), ('vendite.ddt'),
    ('vendite.offerte_commerciali'), ('magazzino.magazzini'), ('magazzino.assets'),
    ('pratiche.pratiche'), ('documenti.template_documenti'), ('documenti.template_asset'),
    ('anagrafiche.soggetti_titoli_iva');
CREATE TEMP TABLE _escluse (rel text PRIMARY KEY, perche text) ON COMMIT DROP;
INSERT INTO _escluse VALUES
    ('vendite.resi',                 'eredita dal DDT sorgente / dal BA nel normalize'),
    ('documenti.documenti_generati', 'il BE lo deriva dal documento sorgente'),
    ('vendite.commesse',             'altra colonna, dal BA: non e'' una copia'),
    ('config.user_emittente_attivo', 'e'' la mappa stessa'),
    ('config.user_emittenti_fiscali','e'' la mappa stessa');

CREATE TEMP TABLE _montate ON COMMIT DROP AS
SELECT n.nspname || '.' || c.relname AS rel, t.tgname
  FROM pg_trigger t
  JOIN pg_class c ON c.oid = t.tgrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  JOIN pg_proc p ON p.oid = t.tgfoid
  JOIN pg_namespace pn ON pn.oid = p.pronamespace
 WHERE pn.nspname = 'script' AND p.proname = 'trgfn_default_emittente_fiscale'
   AND NOT t.tgisinternal;

SELECT is(
    (SELECT array_agg(rel ORDER BY rel) FROM _montate),
    (SELECT array_agg(rel ORDER BY rel) FROM _attese),
    '6. le undici tabelle montate sul BB sono esattamente quelle attese');

SELECT is(
    (SELECT count(*)::int
       FROM information_schema.columns col
      WHERE col.column_name = 'emittente_fiscale_id' AND col.is_nullable = 'NO'
        AND col.table_schema <> 'storico'
        AND (col.table_schema || '.' || col.table_name) NOT IN (SELECT rel FROM _attese)
        AND (col.table_schema || '.' || col.table_name) IN (SELECT rel FROM _montate))
    + (SELECT count(*)::int FROM _escluse e WHERE e.rel IN (SELECT rel FROM _montate)),
    0,
    '7. nessuna tabella fuori dall''elenco porta il trigger, e le escluse motivate non lo hanno');

SELECT is(
    (SELECT count(*)::int
       FROM _montate m
       JOIN pg_trigger o ON o.tgrelid = m.rel::regclass AND NOT o.tgisinternal
        AND (o.tgname LIKE '%guard_emittente%' OR o.tgname LIKE '%normalize%')
      WHERE m.tgname >= o.tgname),
    0,
    '8. su ogni tabella montata il default ordina prima di guard_emittente_* e normalize (D5)');

SELECT ok(
    (SELECT pg_get_triggerdef(t.oid) FROM pg_trigger t
      WHERE t.tgrelid = 'vendite.ddt'::regclass AND t.tgname = 'trg_ddt_a10_default_emittente_ins')
    LIKE '%(''LASCIA_NULL'', ''SALTA_CON_SORGENTE'')',
    '9. ddt porta i due argomenti LASCIA_NULL + SALTA_CON_SORGENTE (D4)');

-- ============================================================
-- Fixture: tre aziende in tre istruzioni, il SA, un indirizzo, un BA di A
-- ============================================================
CREATE TEMP TABLE _m ON COMMIT DROP AS
SELECT 'A'::text AS lato, m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;
INSERT INTO _m SELECT 'B', m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;
INSERT INTO _m SELECT 'S', m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;
INSERT INTO _m SELECT 'Z', m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;
-- il SA: l'operatore di S con binding al profilo SUPER_ADMIN (definizione di fn_is_super_admin).
-- ⚠️ E un SECONDO SA (l'operatore di Z, mai attore): senza, sul database da zero S
--   sarebbe l'ultimo SA e fn_change_user_emittenti_scope lo rifiuterebbe (vedi testa).
DO $lega$
BEGIN
    PERFORM config.fn_lega_profilo_identita((SELECT id FROM config.profili_accesso WHERE codice = 'SUPER_ADMIN'), m.identita_id) FROM _m m WHERE m.lato IN ('S', 'Z');
END
$lega$;

CREATE TEMP TABLE _fix (
    ind bigint, ba bigint, ba_istanza bigint, ba_utility integer, ba_sr bigint,
    valuta bigint, stato_ddt_draft bigint,
    causale bigint, sorg_ordine bigint
) ON COMMIT DROP;

-- il BA lo crea l'operatore di A (un admin globale non puo' creare BA)
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m WHERE lato = 'A')); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;
DO $fix$
DECLARE r record;
BEGIN
    SELECT * INTO r FROM dbops.fn_pgtap_crea_cliente_ba('default-emittente', NULL, (SELECT soggetto_ruolo_id FROM _m WHERE lato = 'A'));
    INSERT INTO _fix VALUES (
        dbops.fn_pgtap_crea_indirizzo_dettaglio('default-emittente'),
        r.billing_account_id, r.istanza_utility_id, r.utility_id, r.soggetto_ruolo_id,
        (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1),
        (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno = 'DRAFT' AND s.attivo ORDER BY s.id LIMIT 1),
        (SELECT c.id FROM config.causali_trasporto c WHERE c.codice = 'VENDITA' ORDER BY c.id LIMIT 1),
        (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA' AND s.attivo ORDER BY s.id LIMIT 1));
END $fix$;
SET LOCAL zeroerp.allow_lock_columns_override = 'on';

-- ============================================================
-- IL COMPORTAMENTO
-- ============================================================
-- 10) operatore A, magazzino senza emittente -> A
CREATE TEMP TABLE _r10 ON COMMIT DROP AS
WITH ins AS (
        INSERT INTO magazzino.magazzini (codice, descrizione, indirizzo_dettaglio_id)
        SELECT 'PGT-DE-10', 'default emittente 10', f.ind FROM _fix f
    RETURNING emittente_fiscale_id)
SELECT emittente_fiscale_id FROM ins;
SELECT is(
    (SELECT emittente_fiscale_id FROM _r10),
    (SELECT emittente_fiscale_id FROM _m WHERE lato = 'A'),
    '10. operatore A, magazzino senza emittente -> l''emittente dell''operatore');

-- 11) SA «tutti» (assegnato a S), esplicito A -> A
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m WHERE lato = 'S')); END $ctx$;
CREATE TEMP TABLE _r11 ON COMMIT DROP AS
WITH ins AS (
        INSERT INTO magazzino.magazzini (codice, descrizione, indirizzo_dettaglio_id, emittente_fiscale_id)
        SELECT 'PGT-DE-11', 'default emittente 11', f.ind, (SELECT emittente_fiscale_id FROM _m WHERE lato = 'A') FROM _fix f
    RETURNING emittente_fiscale_id)
SELECT emittente_fiscale_id FROM ins;
SELECT is(
    (SELECT emittente_fiscale_id FROM _r11),
    (SELECT emittente_fiscale_id FROM _m WHERE lato = 'A'),
    '11. valore esplicito (A) non sovrascritto, anche se il SA avrebbe un default (S)');

-- 12) SA con emittente attivo B -> B
SELECT set_config('app.current_emittente_id', (SELECT emittente_fiscale_id::text FROM _m WHERE lato = 'B'), true);
CREATE TEMP TABLE _r12 ON COMMIT DROP AS
WITH ins AS (
        INSERT INTO magazzino.magazzini (codice, descrizione, indirizzo_dettaglio_id)
        SELECT 'PGT-DE-12', 'default emittente 12', f.ind FROM _fix f
    RETURNING emittente_fiscale_id)
SELECT emittente_fiscale_id FROM ins;
SELECT is(
    (SELECT emittente_fiscale_id FROM _r12),
    (SELECT emittente_fiscale_id FROM _m WHERE lato = 'B'),
    '12. SA con emittente attivo B -> B: l''attivo di sessione vince sull''assegnato');
SELECT set_config('app.current_emittente_id', '', true);

-- 13) ddt SALTA_CON_SORGENTE: un ordine di A (creato dall'operatore A), evaso dal SA
--     «tutti» assegnato a S -> il DDT porta A, non S (il normalize eredita dall'ordine
--     solo se il default NON ha gia' riempito la colonna)
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m WHERE lato = 'A')); END $ctx$;
CREATE TEMP TABLE _ord ON COMMIT DROP AS
WITH ins AS (
    INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, valuta_id, data, storicizza, meta)
    SELECT f.ba_sr, f.ba, f.valuta, script.fn_data_operativa(), false, '{}'::jsonb FROM _fix f
    RETURNING id, uid, emittente_fiscale_id)
SELECT * FROM ins;
-- L'ordine nasce DRAFT; la riga (DRAFT->CONFERMATO la pretende) e la conferma per
--   la matrice le scrive il builder sulla testata del test.
DO $x$ BEGIN
    PERFORM dbops.fn_pgtap_crea_ordine_con_righe('default-emittente 13', 'CONFERMATO',
        p_quantita => 1, p_prezzo => 10, p_ordine_id => (SELECT id FROM _ord));
END $x$;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m WHERE lato = 'S')); END $ctx$;
CREATE TEMP TABLE _r13 ON COMMIT DROP AS
WITH ins AS (
        INSERT INTO vendite.ddt (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, data, sorgente_tipo_id, sorgente_uid,
                                 causale_trasporto_id, storicizza, meta)
        SELECT f.ba_sr, f.stato_ddt_draft, script.fn_data_operativa(), f.sorg_ordine, (SELECT uid FROM _ord), f.causale, false, '{}'::jsonb
          FROM _fix f
    RETURNING emittente_fiscale_id)
SELECT emittente_fiscale_id FROM ins;
SELECT is(
    (SELECT emittente_fiscale_id FROM _r13),
    (SELECT emittente_fiscale_id FROM _m WHERE lato = 'A'),
    '13. ddt SALTA_CON_SORGENTE: DDT da ordine di A evaso dal SA assegnato a S -> porta A (dal padre)');

-- ------------------------------------------------------------
-- Da qui il SA e' un «admin globale»: nessuna riga in user_emittenti_fiscali.
-- Si usa la funzione di dominio, non un DELETE: e' la sede del modello 1-a-1.
-- ------------------------------------------------------------
SELECT script.fn_change_user_emittenti_scope((SELECT auth_user_id FROM _m WHERE lato = 'S'), '{}'::bigint[]);

-- 14) SA senza emittente, senza valore -> E_EMITTENTE_NON_RISOLTO
SELECT throws_like(
    $$ INSERT INTO magazzino.magazzini (codice, descrizione, indirizzo_dettaglio_id)
       SELECT 'PGT-DE-14', 'default emittente 14', f.ind FROM _fix f $$,
    'Nessun emittente fiscale attivo%',
    '14. admin globale senza emittente attivo, riga senza emittente -> E_EMITTENTE_NON_RISOLTO');

-- 15) GUC vuota -> E_EMITTENTE_NON_RISOLTO (poi il contesto si rimette)
SELECT set_config('app.current_user_id', '', true);
SELECT throws_like(
    $$ INSERT INTO magazzino.magazzini (codice, descrizione, indirizzo_dettaglio_id)
       SELECT 'PGT-DE-15', 'default emittente 15', f.ind FROM _fix f $$,
    'Nessun emittente fiscale attivo%',
    '15. GUC app.current_user_id vuota -> E_EMITTENTE_NON_RISOLTO');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m WHERE lato = 'S')); END $ctx$;

-- 16) ddt LASCIA_NULL: SA senza emittente, DDT DRAFT senza sorgente con BA di A
--     -> il default lascia NULL senza sollevare, il normalize deriva dal BA
CREATE TEMP TABLE _r16 ON COMMIT DROP AS
WITH ins AS (
        INSERT INTO vendite.ddt (destinatario_soggetto_ruolo_id, billing_account_id, stato_doc_ddt_id, data,
                                 causale_trasporto_id, storicizza, meta)
        SELECT f.ba_sr, f.ba, f.stato_ddt_draft, script.fn_data_operativa(), f.causale, false, '{}'::jsonb FROM _fix f
    RETURNING emittente_fiscale_id)
SELECT emittente_fiscale_id FROM ins;
SELECT is(
    (SELECT emittente_fiscale_id FROM _r16),
    (SELECT emittente_fiscale_id FROM _m WHERE lato = 'A'),
    '16. ddt LASCIA_NULL: admin globale, DDT senza sorgente -> nessun errore, emittente dal BA via normalize');

-- 17) argomento non ammesso -> E_TRIGGER_ARGOMENTI_INVALIDI al primo INSERT
CREATE TEMP TABLE _t_bad (id serial, emittente_fiscale_id bigint) ON COMMIT DROP;
CREATE TRIGGER trg_bad BEFORE INSERT ON _t_bad FOR EACH ROW
    EXECUTE FUNCTION script.trgfn_default_emittente_fiscale('BOH');
SELECT throws_like(
    $$ INSERT INTO _t_bad DEFAULT VALUES $$,
    'Trigger montato con argomenti non validi%',
    '17. argomento di montaggio non ammesso -> E_TRIGGER_ARGOMENTI_INVALIDI');

-- 18) D3: preventivo di A in EMESSO (creato dall'operatore A); il SA senza emittente
--     lo revisiona: la rev 1 porta A. Prima della 20260915-41 la testata non copiava
--     l'ancora e il default di sessione sollevava (o, con un emittente attivo diverso,
--     il guard BA rifiutava): la revisione era impossibile.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m WHERE lato = 'A')); END $ctx$;
CREATE TEMP TABLE _prev ON COMMIT DROP AS
WITH ins AS (
    INSERT INTO vendite.preventivi (numero, rev, billing_account_id, istanza_utility_id, utility_id,
                                    validita_dal, validita_al, valuta_id, data,
                                    emittente_fiscale_id, storicizza, meta)
    SELECT 'PGT-DE-' || substr(md5(clock_timestamp()::text), 1, 8), 0, f.ba, f.ba_istanza, f.ba_utility,
           script.fn_data_operativa(), script.fn_data_operativa() + 30, f.valuta, script.fn_data_operativa(),
           (SELECT emittente_fiscale_id FROM _m WHERE lato = 'A'), false, '{}'::jsonb
      FROM _fix f
    RETURNING id)
SELECT id FROM ins;
-- rev 2026-10-24: il preventivo nasce DRAFT e passa a EMESSO per la matrice.
-- rev 2026-10-25 (§8, giro 6): con una riga (merce, 1 x 10) scritta in bozza dal builder,
--   sotto il contesto dell'operatore A: senza righe l'emissione e' rifiutata.
DO $x$ BEGIN PERFORM dbops.fn_pgtap_crea_preventivo_con_righe('default emittente', 'EMESSO', p_preventivo_id => (SELECT id FROM _prev)); END $x$;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m WHERE lato = 'S')); END $ctx$;
-- ⚠️ il verbo in un'istruzione SEPARATA dalla lettura: nella stessa istruzione la
--   riga appena scritta non e' nella snapshot e la lettura torna NULL.
CREATE TEMP TABLE _rev ON COMMIT DROP AS
SELECT * FROM vendite.fn_crea_revisione_preventivo((SELECT id FROM _prev), 'pgtap');
SELECT is(
    (SELECT p.emittente_fiscale_id FROM vendite.preventivi p
      WHERE p.id = (SELECT nuovo_preventivo_id FROM _rev)),
    (SELECT emittente_fiscale_id FROM _m WHERE lato = 'A'),
    '18. D3: la rev N+1 copia l''emittente della rev N (A), anche creata da un admin globale senza emittente');

SELECT * FROM finish();
ROLLBACK;
