-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce un'AZIENDA — emittente fiscale,
--   utente tecnico e identita' digitale (dbops.fn_pgtap_crea_emittente_operatore)
--   — e un operatore dentro un perimetro non crea l'azienda in cui lavora.
--   E' il criterio 2 di scripts/testpgtap.sh. Dal contesto in poi si lavora
--   nei panni dell'operatore costruito.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): la testata dell'ordine da dbops.fn_pgtap_crea_ordine (DRAFT, senza righe), col contesto dell'operatore aperto prima; restano a mano le righe d'ordine (il caso dei test 7-14) e i preventivi.
-- pgTAP test — una DATA DI CONSEGNA non viene prima della DATA DEL DOCUMENTO
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2a, 20261019-40 … -79):
--   il documento passato ai lettori delle testate, ai legami e ai montaggi del
--   lock e' il codice della sorgente (DDT_VENDITA, ORDINE_VENDITA,
--   OFFERTA_COMMERCIALE, RESO_VENDITA). Restano corti i prefissi delle chiavi
--   (G-8), l'origine dei legami (V7) e l'ambito degli indirizzi (G-6).
--   script.fn_data_consegna_ammessa (la regola), script.fn_doc_date_consegna_anteriori
--   (il lettore DEFINER), script.trgfn_doc_righe_guard_data_consegna (riga),
--   script.trgfn_doc_testata_guard_data_consegna_righe (testata), e le due copie di
--   righe che con una data anteriore la AZZERANO: vendite.fn_push_preventivo_a_ordine,
--   vendite.fn_crea_revisione_preventivo.
--   ChangeSet: 20261013-62 … -68. Collaudo date di consegna (2026-10-13), decisione di
--   Tid sulle copie: azzerare, non rifiutare e non portare alla data del documento.
--
-- Elenco test (plan 22):
--   STRUTTURA
--    1) quattro funzioni, il lettore DEFINER con search_path, quattro trigger montati
--    2) i due codici nuovi a catalogo, DATO_ERRATO, con la frase in italiano
--    3) la regola: NULL ammessa, stessa data ammessa, il giorno prima no
--    4) ⭐ un elenco solo: le colonne di consegna stanno nel lettore, non nei guard
--   IL LETTORE, dalla riga (senza DDL: le righe si passano come jsonb)
--    5) una data anteriore NON cambiata non si rigiudica (una riga scritta prima della regola)
--    6) …cambiata si', e cosi' la riga che torna attiva; una riga spenta mai
--   RIGHE DELL'ORDINE (ordine DRAFT con la data di oggi)
--    7) INSERT con la richiesta di ieri: E_DOC_RIGA_DATA_CONSEGNA_ANTERIORE, campo la colonna
--    8) la frase dice il documento, la data di consegna e la data del documento
--    9) la stessa data del documento, e la data vuota: passano
--   10) UPDATE della confermata a ieri: rifiutato, campo data_consegna_confermata
--   11) una riga SPENTA con una data anteriore passa; riaccenderla no
--   LA TESTATA DELL'ORDINE
--   12) spostare la data dell'ordine oltre una consegna: E_DOC_DATA_OLTRE_CONSEGNA_RIGHE, campo data
--   13) la frase dice la consegna piu' bassa, il limite
--   14) retrodatare l'ordine passa, e la riga spenta non blocca il ritorno a oggi
--   IL PREVENTIVO
--   15) riga di preventivo con la richiesta di ieri: rifiutata
--   16) data del preventivo oltre la consegna di una riga: rifiutata
--   IL PUSH preventivo -> ordine (percorso reale)
--   17) ⭐ la richiesta anteriore alla data dell'ordine arriva NULL, quella futura si copia
--   18) la riga di preventivo conserva la sua: la richiesta vera resta raggiungibile
--   19) il push non fallisce: l'ordine nasce, in DRAFT
--   LA REVISIONE N -> N+1 (percorso reale)
--   20) ⭐ la richiesta anteriore alla data della rev N+1 arriva NULL, quella futura si copia
--   21) la rev N conserva le sue date
--   22) la rev N+1 nasce con la data di oggi: e' il riferimento usato
--
-- ⚠️ IL MONDO SI COSTRUISCE, NON SI CERCA (la forma di test-date-consegna-ordine-v1):
--   azienda coi suoi registri, cliente legato a QUELLA azienda, articolo MERCE.
-- ⚠️ Le date sono RELATIVE A OGGI (script.fn_data_operativa()): il push e la
--   revisione datano il documento nuovo oggi, e una data fissa invecchierebbe.
-- ------------------------------------------------------------
BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(22);

CREATE TEMP TABLE _d AS
SELECT script.fn_data_operativa() AS oggi;

-- L'esito di un'istruzione: PASSA, o «codice|campo» del rifiuto (P0001 porta il
-- codice in CONSTRAINT_NAME e il campo in COLUMN_NAME), o lo SQLSTATE.
CREATE OR REPLACE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE v_s text; v_c text; v_col text;
BEGIN
    EXECUTE p_sql;
    RETURN 'PASSA';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_s = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME, v_col = COLUMN_NAME;
    RETURN CASE WHEN v_s = 'P0001' AND coalesce(v_c, '') <> ''
                THEN v_c || '|' || coalesce(nullif(v_col, ''), '-')
                ELSE v_s || coalesce(' ' || nullif(v_c, ''), '') END;
END
$f$;

-- La frase del rifiuto.
CREATE OR REPLACE FUNCTION pg_temp.frase(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
BEGIN
    EXECUTE p_sql;
    RETURN 'PASSA';
EXCEPTION WHEN OTHERS THEN
    RETURN SQLERRM;
END
$f$;

CREATE OR REPLACE FUNCTION pg_temp.gg(p_giorni integer) RETURNS date
  AS $$ SELECT oggi + p_giorni FROM _d $$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION pg_temp.it(p_data date) RETURNS text
  AS $$ SELECT to_char(p_data, 'DD/MM/YYYY') $$ LANGUAGE sql;

-- ============================================================
-- STRUTTURA
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'script'
      AND p.proname IN ('fn_data_consegna_ammessa', 'fn_doc_date_consegna_anteriori',
                        'trgfn_doc_righe_guard_data_consegna',
                        'trgfn_doc_testata_guard_data_consegna_righe'))
  + (SELECT count(*)::int FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script' AND p.proname = 'fn_doc_date_consegna_anteriori'
        AND p.prosecdef
        AND EXISTS (SELECT 1 FROM unnest(p.proconfig) c WHERE c LIKE 'search_path=%'))
  + (SELECT count(*)::int FROM pg_trigger t
      WHERE NOT t.tgisinternal
        AND (t.tgrelid, t.tgname) IN (
              ('vendite.ordini_righe'::regclass,     'trg_ordini_righe_a10_guard_data_consegna_vs_doc_ins_upd'),
              ('vendite.preventivi_righe'::regclass, 'trg_preventivi_righe_a10_guard_data_consegna_vs_doc_ins_upd'),
              ('vendite.ordini'::regclass,           'trg_ordini_a10_guard_data_vs_consegne_righe_upd'),
              ('vendite.preventivi'::regclass,       'trg_preventivi_a10_guard_data_vs_consegne_righe_upd'))),
  9,
  '1) quattro funzioni, il lettore SECURITY DEFINER con search_path, quattro trigger montati');

SELECT is(
  (SELECT string_agg(c.codice || '=' || c.classe || '/' || (m.messaggio IS NOT NULL)::text, ', ' ORDER BY c.codice)
     FROM config.codici_errore c
     LEFT JOIN config.messaggi_errore m ON m.codice = c.codice AND m.lingua = 'it'
    WHERE c.codice IN ('E_DOC_RIGA_DATA_CONSEGNA_ANTERIORE', 'E_DOC_DATA_OLTRE_CONSEGNA_RIGHE')),
  'E_DOC_DATA_OLTRE_CONSEGNA_RIGHE=DATO_ERRATO/true, E_DOC_RIGA_DATA_CONSEGNA_ANTERIORE=DATO_ERRATO/true',
  '2) i due codici nuovi sono a catalogo, DATO_ERRATO, con la frase in italiano');

SELECT is(
  (SELECT string_agg(script.fn_data_consegna_ammessa(x.c, x.d)::text, ',' ORDER BY x.n)
     FROM (VALUES (1, NULL::date,    pg_temp.gg(0)),
                  (2, pg_temp.gg(0), pg_temp.gg(0)),
                  (3, pg_temp.gg(1), pg_temp.gg(0)),
                  (4, pg_temp.gg(-1), pg_temp.gg(0)),
                  (5, pg_temp.gg(-1), NULL::date)) AS x(n, c, d)),
  'true,true,true,false,true',
  '3) la regola: NULL ammessa, stessa data ammessa, il giorno dopo ammessa, il giorno prima NO, senza documento nessun confronto');

-- ⭐ L'elenco delle colonne di consegna sta in UN posto: il lettore. I due guard
--    non ne nominano nessuna (sorgente senza commenti). Se domani un guard
--    elencasse le sue, i due lati potrebbero divergere alla prima colonna nuova.
SELECT ok(
  (SELECT bool_and(CASE WHEN p.proname = 'fn_doc_date_consegna_anteriori'
                        THEN regexp_replace(p.prosrc, '--[^\n]*', '', 'g') LIKE '%data_consegna_richiesta_cliente%'
                         AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') LIKE '%data_consegna_confermata%'
                        ELSE regexp_replace(p.prosrc, '--[^\n]*', '', 'g') NOT LIKE '%data\_consegna\_%'
                         AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ 'script\.fn_doc_date_consegna_anteriori\s*\('
                   END)
     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'script'
      AND p.proname IN ('fn_doc_date_consegna_anteriori', 'trgfn_doc_righe_guard_data_consegna',
                        'trgfn_doc_testata_guard_data_consegna_righe')),
  '4) un elenco solo: le colonne di consegna le nomina il lettore, i due guard lo chiamano e non ne nominano nessuna');

-- ============================================================
-- Fixture: il mondo, da owner
-- ============================================================
CREATE TEMP TABLE _mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE _cliente AS
SELECT c.*
  FROM _mondo m
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba(
      'Consegna vs documento', NULL, m.soggetto_ruolo_id) c;

-- Articolo MERCE (natura di default = destinazione ORDINE): la vista dei
-- smistabili lo lascia passare verso l'ordine.
CREATE TEMP TABLE _articolo AS
WITH a AS (
    INSERT INTO catalogo.articoli (codice, descrizione, uom_id)
    SELECT 'PGTAP-CONSDOC-' || substr(md5(random()::text), 1, 10),
           'Articolo pgTAP consegna vs documento',
           (SELECT um.id FROM catalogo.unita_misura um WHERE um.attivo IS TRUE ORDER BY um.id LIMIT 1)
    RETURNING id
)
SELECT id AS articolo_id FROM a;

CREATE TEMP TABLE _refs AS
SELECT (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)        AS iva_id,
       (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                            AS valuta_id,
       (SELECT s.id FROM config.stati_doc_preventivi s
         WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE)                            AS stato_prev_draft_id;

-- ============================================================
-- IL LETTORE, dalla riga: le righe come jsonb, nessuna DDL
-- (serve una testata vera: il lettore ne legge la data)
-- ============================================================
-- ⭐ Da qui nei panni dell'operatore costruito: la testata la scrive il
--    builder, che lavora nell'azienda di chi agisce (il lettore dei test 5-6
--    giudica righe passate come jsonb: il contesto non lo tocca).
DO $ctx$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo));
END $ctx$;

-- La testata dell'ordine, DRAFT con la data di oggi (il default della
-- colonna), senza righe: le righe sono il caso.
CREATE TEMP TABLE _ord AS
SELECT o.ordine_id
  FROM dbops.fn_pgtap_crea_ordine('pgtap_consegna_vs_documento', 'DRAFT',
         (SELECT c.billing_account_id FROM _cliente c)) o;

-- Una riga «di prima della regola»: la richiesta e' di ieri.
CREATE TEMP TABLE _j AS
SELECT jsonb_build_object('attivo', true, 'ordine_id', o.ordine_id,
                          'data_consegna_richiesta_cliente', pg_temp.gg(-1),
                          'data_consegna_confermata', pg_temp.gg(3)) AS riga
  FROM _ord o;

SELECT is(
  (SELECT count(*)::int
     FROM _ord o, _j j,
          script.fn_doc_date_consegna_anteriori('ORDINE_VENDITA', o.ordine_id, NULL,
              j.riga || jsonb_build_object('data_consegna_confermata', pg_temp.gg(4)),
              j.riga) a),
  0,
  '5) la richiesta di ieri NON cambiata non si rigiudica: un UPDATE che non tocca quella data passa');

SELECT is(
  (SELECT string_agg(x.tag || '=' || x.n::text, ', ' ORDER BY x.tag)
     FROM (SELECT 'a_cambiata' AS tag, count(*) AS n
             FROM _ord o, _j j,
                  script.fn_doc_date_consegna_anteriori('ORDINE_VENDITA', o.ordine_id, NULL,
                      j.riga || jsonb_build_object('data_consegna_richiesta_cliente', pg_temp.gg(-2)),
                      j.riga) a
           UNION ALL
           SELECT 'b_riaccesa', count(*)
             FROM _ord o, _j j,
                  script.fn_doc_date_consegna_anteriori('ORDINE_VENDITA', o.ordine_id, NULL,
                      j.riga, j.riga || '{"attivo": false}'::jsonb) a
           UNION ALL
           SELECT 'c_spenta', count(*)
             FROM _ord o, _j j,
                  script.fn_doc_date_consegna_anteriori('ORDINE_VENDITA', o.ordine_id, NULL,
                      j.riga || '{"attivo": false}'::jsonb, NULL) a) x),
  'a_cambiata=1, b_riaccesa=1, c_spenta=0',
  '6) cambiata si rigiudica; la riga che torna attiva si rigiudica tutta; una riga spenta non si giudica');

-- ============================================================
-- RIGHE DELL'ORDINE (DRAFT, data di oggi)
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.ins_riga_ordine(p_nr integer, p_richiesta date, p_confermata date)
RETURNS text AS $$
  SELECT pg_temp.esito(format(
    'INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione, qta_operativa,
                                       quantita, prezzo_unitario, iva_id,
                                       data_consegna_richiesta_cliente, data_consegna_confermata)
     SELECT o.ordine_id, %s, a.articolo_id, ''Riga pgTAP consegna'', 1, 1, 10, r.iva_id, %L::date, %L::date
       FROM _ord o, _articolo a, _refs r', p_nr, p_richiesta, p_confermata))
$$ LANGUAGE sql;

SELECT is(
  pg_temp.ins_riga_ordine(1, pg_temp.gg(-1), NULL),
  'E_DOC_RIGA_DATA_CONSEGNA_ANTERIORE|data_consegna_richiesta_cliente',
  '7) INSERT con la richiesta di ieri: rifiutata, e il campo da accendere e'' la richiesta');

SELECT is(
  pg_temp.frase(format(
    'INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione, qta_operativa,
                                       quantita, prezzo_unitario, iva_id, data_consegna_richiesta_cliente)
     SELECT o.ordine_id, 1, a.articolo_id, ''x'', 1, 1, 10, r.iva_id, %L::date
       FROM _ord o, _articolo a, _refs r', pg_temp.gg(-1))),
  (SELECT 'Ordine ' || coalesce(o.numero, '#' || o.id::text)
          || ': la data di consegna ' || pg_temp.it(pg_temp.gg(-1))
          || ' è anteriore alla data del documento (' || pg_temp.it(pg_temp.gg(0)) || ').'
     FROM vendite.ordini o WHERE o.id = (SELECT ordine_id FROM _ord)),
  '8) la frase dice il documento, la data di consegna e la data del documento');

SELECT is(
  pg_temp.ins_riga_ordine(1, pg_temp.gg(0), NULL) || ' / ' || pg_temp.ins_riga_ordine(2, NULL, NULL),
  'PASSA / PASSA',
  '9) la stessa data del documento passa (consegna in giornata), e la data vuota pure («nessuna data»)');

CREATE TEMP TABLE _r AS
SELECT max(r.id) FILTER (WHERE r.riga_nr = 1) AS r1,
       max(r.id) FILTER (WHERE r.riga_nr = 2) AS r2
  FROM vendite.ordini_righe r WHERE r.ordine_id = (SELECT ordine_id FROM _ord);

SELECT is(
  pg_temp.esito(format('UPDATE vendite.ordini_righe SET data_consegna_confermata = %L::date WHERE id = %s',
                       pg_temp.gg(-1), (SELECT r1 FROM _r)))
  || ' / ' ||
  pg_temp.esito(format('UPDATE vendite.ordini_righe SET data_consegna_confermata = %L::date WHERE id = %s',
                       pg_temp.gg(3), (SELECT r1 FROM _r))),
  'E_DOC_RIGA_DATA_CONSEGNA_ANTERIORE|data_consegna_confermata / PASSA',
  '10) la confermata a ieri e'' rifiutata (campo la confermata), fra tre giorni passa');

SELECT is(
  pg_temp.esito(format('UPDATE vendite.ordini_righe SET attivo = false, data_consegna_richiesta_cliente = %L::date WHERE id = %s',
                       pg_temp.gg(-2), (SELECT r2 FROM _r)))
  || ' / ' ||
  pg_temp.esito(format('UPDATE vendite.ordini_righe SET attivo = true WHERE id = %s', (SELECT r2 FROM _r))),
  'PASSA / E_DOC_RIGA_DATA_CONSEGNA_ANTERIORE|data_consegna_richiesta_cliente',
  '11) una riga SPENTA non fa parte del documento e passa con una data anteriore; riaccenderla e'' rifiutato');

-- ============================================================
-- LA TESTATA DELL'ORDINE — riga 1: richiesta oggi, confermata fra 3 giorni
-- ============================================================
SELECT is(
  pg_temp.esito(format('UPDATE vendite.ordini SET data = %L::date WHERE id = %s',
                       pg_temp.gg(1), (SELECT ordine_id FROM _ord))),
  'E_DOC_DATA_OLTRE_CONSEGNA_RIGHE|data',
  '12) la data dell''ordine non si sposta oltre una consegna gia'' scritta: rifiutata, campo data');

SELECT is(
  pg_temp.frase(format('UPDATE vendite.ordini SET data = %L::date WHERE id = %s',
                       pg_temp.gg(5), (SELECT ordine_id FROM _ord))),
  (SELECT 'Ordine ' || coalesce(o.numero, '#' || o.id::text)
          || ': la data del documento non può diventare ' || pg_temp.it(pg_temp.gg(5))
          || ', perché una riga ha la consegna il ' || pg_temp.it(pg_temp.gg(0)) || '.'
     FROM vendite.ordini o WHERE o.id = (SELECT ordine_id FROM _ord)),
  '13) la frase dice la data chiesta e la consegna piu'' bassa (oggi, non fra tre giorni): il limite');

SELECT is(
  pg_temp.esito(format('UPDATE vendite.ordini SET data = %L::date WHERE id = %s',
                       pg_temp.gg(-5), (SELECT ordine_id FROM _ord)))
  || ' / ' ||
  pg_temp.esito(format('UPDATE vendite.ordini SET data = %L::date WHERE id = %s',
                       pg_temp.gg(0), (SELECT ordine_id FROM _ord))),
  'PASSA / PASSA',
  '14) retrodatare l''ordine passa, e tornare a oggi pure: la riga spenta con la data di due giorni fa non conta');

-- ============================================================
-- IL PREVENTIVO (DRAFT, data di oggi dal default)
-- ============================================================
CREATE TEMP TABLE _prev AS
WITH p AS (
    INSERT INTO vendite.preventivi
        (numero, billing_account_id, istanza_utility_id, utility_id, valuta_id,
         stato_doc_preventivo_id, emittente_fiscale_id, meta)
    SELECT 'PGTAP-CONSDOC-' || substr(md5(random()::text), 1, 8),
           c.billing_account_id, c.istanza_utility_id, c.utility_id, r.valuta_id,
           r.stato_prev_draft_id, m.emittente_fiscale_id,
           jsonb_build_object('test_scope', 'pgtap_consegna_vs_documento')
      FROM _cliente c, _mondo m, _refs r
    RETURNING id
)
SELECT id AS preventivo_id FROM p;

CREATE OR REPLACE FUNCTION pg_temp.ins_riga_prev(p_prev bigint, p_ordine integer, p_richiesta date)
RETURNS text AS $$
  SELECT pg_temp.esito(format(
    'INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, prezzo_unitario, qta_operativa,
                                           iva_id, ordine, data_consegna_richiesta_cliente)
     SELECT %s, a.articolo_id, 10.00, 2, r.iva_id, %s, %L::date
       FROM _articolo a, _refs r', p_prev, p_ordine, p_richiesta))
$$ LANGUAGE sql;

SELECT is(
  pg_temp.ins_riga_prev((SELECT preventivo_id FROM _prev), 1, pg_temp.gg(-1)),
  'E_DOC_RIGA_DATA_CONSEGNA_ANTERIORE|data_consegna_richiesta_cliente',
  '15) riga di preventivo con la richiesta di ieri: rifiutata');

SELECT is(
  pg_temp.ins_riga_prev((SELECT preventivo_id FROM _prev), 1, pg_temp.gg(5))
  || ' / ' ||
  pg_temp.esito(format('UPDATE vendite.preventivi SET data = %L::date WHERE id = %s',
                       pg_temp.gg(10), (SELECT preventivo_id FROM _prev))),
  'PASSA / E_DOC_DATA_OLTRE_CONSEGNA_RIGHE|data',
  '16) la data del preventivo non si sposta oltre la consegna di una sua riga');

-- ============================================================
-- IL PUSH preventivo -> ordine, sul percorso reale
--   Preventivo datato 10 giorni fa, con la richiesta a -5 (valida per LUI),
--   a +5 e senza data. L'ordine nasce oggi: -5 e' gia' passata.
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.mk_preventivo(p_stato text) RETURNS bigint
LANGUAGE plpgsql AS $f$
DECLARE v_id bigint;
BEGIN
    INSERT INTO vendite.preventivi
        (numero, billing_account_id, istanza_utility_id, utility_id, valuta_id,
         stato_doc_preventivo_id, emittente_fiscale_id, data, meta)
    SELECT 'PGTAP-CONSDOC-' || substr(md5(random()::text), 1, 8),
           c.billing_account_id, c.istanza_utility_id, c.utility_id, r.valuta_id,
           r.stato_prev_draft_id, m.emittente_fiscale_id, pg_temp.gg(-10),
           jsonb_build_object('test_scope', 'pgtap_consegna_vs_documento')
      FROM _cliente c, _mondo m, _refs r
    RETURNING id INTO v_id;

    INSERT INTO vendite.preventivi_righe
        (preventivo_id, articolo_id, prezzo_unitario, qta_operativa, iva_id, ordine,
         data_consegna_richiesta_cliente)
    SELECT v_id, a.articolo_id, 10.00, 2, r.iva_id, x.ordine, x.d
      FROM _articolo a, _refs r,
           (VALUES (1, pg_temp.gg(-5)), (2, pg_temp.gg(5)), (3, NULL::date)) AS x(ordine, d);

    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', v_id, p_stato);
    RETURN v_id;
END
$f$;

CREATE TEMP TABLE _push AS
SELECT pg_temp.mk_preventivo('ACCETTATO') AS preventivo_id;

CREATE TEMP TABLE _push_ord AS
SELECT vendite.fn_push_preventivo_a_ordine((SELECT preventivo_id FROM _push)) AS ordine_id;

SELECT is(
  (SELECT string_agg(pr.ordine || ':' || coalesce((orr.data_consegna_richiesta_cliente - pg_temp.gg(0))::text, 'NULL'),
                     ',' ORDER BY pr.ordine)
     FROM vendite.ordini_righe orr
     JOIN vendite.preventivi_righe pr ON pr.id = orr.preventivo_riga_id
    WHERE orr.ordine_id = (SELECT ordine_id FROM _push_ord)),
  '1:NULL,2:5,3:NULL',
  '17) ⭐ push: la richiesta di 5 giorni fa arriva NULL (anteriore all''ordine di oggi), quella fra 5 giorni si copia, la vuota resta vuota');

SELECT is(
  (SELECT string_agg(pr.ordine || ':' || coalesce((pr.data_consegna_richiesta_cliente - pg_temp.gg(0))::text, 'NULL'),
                     ',' ORDER BY pr.ordine)
     FROM vendite.preventivi_righe pr
    WHERE pr.preventivo_id = (SELECT preventivo_id FROM _push)),
  '1:-5,2:5,3:NULL',
  '18) la riga di preventivo conserva la sua richiesta: quella vera resta raggiungibile da preventivo_riga_id');

SELECT is(
  (SELECT s.codice_interno::text || '|' || (o.data = pg_temp.gg(0))::text
     FROM vendite.ordini o JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
    WHERE o.id = (SELECT ordine_id FROM _push_ord)),
  'DRAFT|true',
  '19) il push non fallisce: l''ordine nasce DRAFT, con la data di oggi, e la data si riscrive li''');

-- ============================================================
-- LA REVISIONE N -> N+1, sul percorso reale
-- ============================================================
CREATE TEMP TABLE _rev_n AS
SELECT pg_temp.mk_preventivo('EMESSO') AS preventivo_id;

CREATE TEMP TABLE _rev AS
SELECT r.nuovo_preventivo_id
  FROM vendite.fn_crea_revisione_preventivo((SELECT preventivo_id FROM _rev_n), 'pgtap') r;

SELECT is(
  (SELECT string_agg(pr.ordine || ':' || coalesce((pr.data_consegna_richiesta_cliente - pg_temp.gg(0))::text, 'NULL'),
                     ',' ORDER BY pr.ordine)
     FROM vendite.preventivi_righe pr
    WHERE pr.preventivo_id = (SELECT nuovo_preventivo_id FROM _rev)),
  '1:NULL,2:5,3:NULL',
  '20) ⭐ revisione: la richiesta di 5 giorni fa arriva NULL sulla rev N+1, quella fra 5 giorni si copia');

SELECT is(
  (SELECT string_agg(pr.ordine || ':' || coalesce((pr.data_consegna_richiesta_cliente - pg_temp.gg(0))::text, 'NULL'),
                     ',' ORDER BY pr.ordine)
     FROM vendite.preventivi_righe pr
    WHERE pr.preventivo_id = (SELECT preventivo_id FROM _rev_n)),
  '1:-5,2:5,3:NULL',
  '21) la rev N conserva le sue date: la revisione azzera sulla copia, non sulla sorgente');

SELECT is(
  (SELECT (p.data = pg_temp.gg(0))::text FROM vendite.preventivi p
    WHERE p.id = (SELECT nuovo_preventivo_id FROM _rev)),
  'true',
  '22) la rev N+1 nasce con la data di oggi: e'' il riferimento contro cui la data e'' stata giudicata');

SELECT * FROM finish();
ROLLBACK;
