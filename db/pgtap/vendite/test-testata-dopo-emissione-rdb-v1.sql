-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-26 (brief-modello-documento-vendita §13, giro 9): l'emissione di OFF_EMETTI (prima del 13) dal
--   verbo vendite.fn_cambia_stato_offerta, con emetti_offerta concessa all'utente del contesto, non con
--   un UPDATE dello stato: la porta dell'offerta lo ferma. Nessuna attesa cambiata.
-- rev 2026-10-26 (brief-modello-documento-vendita §11): l'attivazione del contratto CON_ATTIVA passa da
--   dbops.fn_pgtap_porta_a_stato (il verbo del contratto), non da un UPDATE dello stato: la porta lo
--   ferma. Nessuna attesa cambiata.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): i due ordini da dbops.fn_pgtap_crea_ordine_con_righe in bozza (2 x 10 sull'articolo X, trigger SPEDITO); a mano restano l'indirizzo scritto in bozza (premessa dei satelliti) e la conferma che lo segue, il preventivo (fuori dalle tre strade del giro) e il listino.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2d): gli ambiti degli indirizzi col codice della sorgente (ORDINE_VENDITA, PREVENTIVO, CONTRATTO); 'DDT' in pg_temp.righe e' un argomento della grammatica dei montaggi e resta.
-- pgTAP test per Zero ERP
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima l'offerta
--   OFF_RIFIUTATA nasceva gia' RIFIUTATA e il contratto del test 35 gia' ATTIVO).
--   Il 35 prova lo snapshot della nascita sul contratto nato in DRAFT e attivato;
--   il 37 (nuovo, piano 37) che l'INSERT diretto in ATTIVO ora e' rifiutato alla
--   nascita (E_DOC_STATO_INIZIALE_NON_VALIDO).
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2a, 20261019-40 … -79):
--   il documento passato ai lettori delle testate, ai legami e ai montaggi del
--   lock e' il codice della sorgente (DDT_VENDITA, ORDINE_VENDITA,
--   OFFERTA_COMMERCIALE, RESO_VENDITA). Restano corti i prefissi delle chiavi
--   (G-8), l'origine dei legami (V7) e l'ambito degli indirizzi (G-6).
--
-- Test: le richieste R-DB-1 … R-DB-4 del brief e il congelamento del listino
--   all'uscita dalla bozza.
--   ChangeSet 20261011-21 … -33, CSV dei codici (E_DOC_DATI_COLLEGATI_NON_BOZZA,
--   E_DOC_LISTINO_CAMBIO_CON_RIGHE, E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI).
-- Brief: brief-db-testata-dopo-emissione (§10.1, §11; D-11 e D-12 di Tid)
--
-- Elenco test (plan 37):
--  La grammatica e i montaggi (R-DB-3, D-12)
--   1) RIGHE: il codice e' il settimo argomento, default E_RIGA_DOC_NON_BOZZA; oltre sette e' un montaggio sbagliato
--   2) i sette satelliti hanno il lock delle righe, col codice dei satelliti e senza eccezioni (scritto dal test)
--   3) gli adottanti di prima restano su E_RIGA_DOC_NON_BOZZA
--   4) script.fn_doc_riga_modificabile: aperta in bozza, chiusa fuori; una tabella senza lock e' aperta
--  I satelliti di un ordine e di un preventivo veri (R-DB-3)
--   5) ordine in bozza: l'indirizzo si aggiunge
--   6) ordine CONFERMATO: aggiungere un indirizzo e' rifiutato col codice dei satelliti
--   7) ... modificarlo pure
--   8) ... toglierlo pure
--   9) ... e la frase parla di indirizzi e fornitura, non di righe
--  10) la capability dell'ordine: can_edit_indirizzi vero in bozza, falso confermato
--  11) preventivo EMESSO: indirizzo rifiutato, e la capability lo dice
--  L'offerta (R-DB-2, R-DB-3) e il congelamento del listino
--  12) BOZZA: fornitura e indirizzi modificabili, motivazione_rifiuto non fra i non modificabili
--  13) BOZZA -> EMESSA: la versione del listino si congela (quella in vigore)
--  14) EMESSA: la versione congelata non si cambia piu' (lock di testata)
--  15) EMESSA: aggiungere la fornitura e' rifiutato col codice dei satelliti
--  16) EMESSA: la capability spegne fornitura e indirizzi; motivazione_rifiuto resta modificabile (D-10)
--  17) RIFIUTATA: motivazione_rifiuto fra i non modificabili (documento chiuso, dal montaggio)
--  Il contratto e il congelamento del listino
--  18) DRAFT -> ATTIVO: la versione del listino si congela (quella in vigore)
--  19) ATTIVO: la versione congelata non si cambia piu'
--  20) ATTIVO: la fornitura e gli indirizzi chiusi, e la capability lo dice
--  Il listino sotto le righe (R-DB-4, D-11)
--  21) i montaggi: il guard del listino con righe su contratto e offerta, e l'ordine dei rifiuti (lock, poi righe, poi utility/emittente)
--  22) contratto DRAFT con righe: un altro listino e' rifiutato (E_DOC_LISTINO_CAMBIO_CON_RIGHE)
--  23) ... col campo listino_id
--  24) contratto DRAFT con un'esclusione: togliere il listino e' rifiutato (E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI)
--  25) contratto DRAFT con la sola aggiunta: il listino si toglie
--  26) contratto DRAFT senza righe: il listino si cambia
--  27) offerta BOZZA con righe: un altro listino e' rifiutato (la stessa regola, D-11)
--  28) contratto ATTIVO: parla prima il lock di testata
--  29) la check: listino invariato, nessun motivo; documento sconosciuto, errore di chiamante
--  Il cliente della bolla (R-DB-1)
--  30) bolla senza sorgente: nessun vincolo, e il cliente non e' fra i non modificabili in bozza
--  31) bolla da ordine: il vincolo SORGENTE, e il cliente fra i non modificabili in bozza
--  32) ... e il guard rifiuta il cambio di cliente (capability e guard dicono la stessa cosa)
--  33) ⭐ la regola sta in un posto solo: guard e capability chiamano vendite.fn_ddt_vincoli_cliente,
--      il guard non legge piu' il fulfillment da se', la capability non scrive il cliente fra le costanti
--  34) i codici nuovi sono a catalogo con la loro classe e il messaggio; i due del contratto ritirati
--  La nascita (D-13 di Tid, 20261011-40, -41)
--  35) un contratto nato (in DRAFT) e attivato porta lo snapshot della fornitura scritto dal trigger alla nascita
--  36) ... ma una fornitura scritta DIRETTAMENTE su un contratto attivo nato in questa transazione e' rifiutata
--  37) un contratto non nasce gia' ATTIVO: E_DOC_STATO_INIZIALE_NON_VALIDO (rev 2026-10-24)
--
-- Scopo:
--  - ⭐ i casi si COSTRUISCONO: mondo, listino, articoli, documenti nati in
--    bozza, transizioni vere (dbops.fn_pgtap_porta_a_stato per ordine e
--    preventivo, l'UPDATE dello stato per offerta e contratto, come il
--    backend). Nessuna riga letta dal database: vale su un DB ricostruito.
--  - ⭐ 2 confronta i montaggi con la tabella attesa scritta dal test: un
--    satellite in piu' o in meno lo rompe.
--  - ⭐ 13/14 e 18/19 sono il «Non fatto» del §9.4: l'UPDATE che esce dalla
--    bozza scrive la versione (il lock guarda lo stato di prima), e dopo
--    nessuno la cambia.
--  - i rifiuti si leggono dal canale CONSTRAINT (P0001 + codice).
--  - ⚠️ 21 e 33 leggono la STRUTTURA (trigger e corpi delle funzioni), non dati.
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo): il builder del
-- mondo lo riapre poi sul suo operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(37);

-- Il codice di dominio di un errore, dal canale CONSTRAINT (P0001); per gli
-- altri, SQLSTATE e vincolo. 'PASSA' se non solleva.
CREATE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE v_s text; v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN 'PASSA';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_s = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME;
    RETURN CASE WHEN v_s = 'P0001' AND coalesce(v_c, '') <> '' THEN v_c
                ELSE v_s || coalesce(' ' || nullif(v_c, ''), '') END;
END
$f$;

-- Il campo di un rifiuto, dal canale COLUMN.
CREATE FUNCTION pg_temp.campo(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE v_col text;
BEGIN
    EXECUTE p_sql;
    RETURN 'NESSUN ERRORE';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_col = COLUMN_NAME;
    RETURN coalesce(v_col, '');
END
$f$;

-- La regola di un montaggio di prova, con gli argomenti contati da 0 come TG_ARGV.
CREATE FUNCTION pg_temp.righe(VARIADIC p text[]) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $f$
    SELECT script.fn_doc_lock_regola('RIGHE', ('[0:' || (cardinality(p) - 1) || ']=' || p::text)::text[])
$f$;

-- =========================================================
-- 1-4) La grammatica e i montaggi
-- =========================================================
SELECT is(
    ARRAY[pg_temp.righe('DDT', 'ddt_id') ->> 'codice',
          pg_temp.righe('DDT', 'ddt_id', 'DRAFT', 'TESTATA', '', '', 'E_X') ->> 'codice',
          coalesce(pg_temp.righe('DDT', 'ddt_id', 'DRAFT', 'TESTATA', '', '', 'E_X') ->> 'errore', 'ok'),
          (pg_temp.righe('DDT', 'ddt_id', 'DRAFT', 'TESTATA', '', '', 'E_X', 'troppo') ->> 'errore') IS NOT NULL || ''],
    ARRAY['E_RIGA_DOC_NON_BOZZA', 'E_X', 'ok', 'true'],
    '1) RIGHE: il codice e'' il settimo argomento (default E_RIGA_DOC_NON_BOZZA); [4] e [5] vuoti insieme non sono un montaggio a meta''; oltre sette argomenti e'' un errore'
);

CREATE TEMP TABLE _sat (tabella text, documento text, fk text, bozza text);
INSERT INTO _sat VALUES
    ('vendite.ddt_indirizzi',                 'DDT_VENDITA',        'ddt_id',        'DRAFT'),
    ('vendite.ordini_indirizzi',              'ORDINE_VENDITA',     'ordine_id',     'DRAFT'),
    ('vendite.preventivi_indirizzi',          'PREVENTIVO', 'preventivo_id', 'DRAFT'),
    ('vendite.offerte_commerciali_indirizzi', 'OFFERTA_COMMERCIALE',    'offerta_id',    'BOZZA'),
    ('vendite.contratti_indirizzi',           'CONTRATTO',  'contratto_id',  'DRAFT'),
    ('vendite.offerte_commerciali_utilities', 'OFFERTA_COMMERCIALE',    'offerta_id',    'BOZZA'),
    ('vendite.contratti_utilities',           'CONTRATTO',  'contratto_id',  'DRAFT');

SELECT set_eq(
    $$SELECT s.tabella, s.documento, s.fk, s.bozza,
             'E_DOC_DATI_COLLEGATI_NON_BOZZA' AS codice, '[]' AS ammesse, 'TESTATA' AS livello
        FROM _sat s$$,
    $$SELECT s.tabella, m.regola ->> 'documento' AS documento, m.regola ->> 'colonna_fk' AS fk,
             m.regola ->> 'stato_bozza' AS bozza, m.regola ->> 'codice' AS codice,
             (m.regola -> 'colonne_ammesse')::text AS ammesse, m.regola ->> 'livello' AS livello
        FROM _sat s
        CROSS JOIN LATERAL script.fn_doc_lock_montaggi(s.tabella::regclass) AS m
       WHERE m.regola ->> 'building_block' = 'RIGHE'
         AND m.regola ->> 'errore' IS NULL$$,
    '2) i sette satelliti: un lock delle righe ciascuno, col documento, la FK, la bozza e il codice dei satelliti, nessuna eccezione'
);

SELECT is(
    (SELECT count(*)::int
       FROM pg_catalog.pg_trigger t
       JOIN pg_catalog.pg_class c ON c.oid = t.tgrelid
       JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
      CROSS JOIN LATERAL script.fn_doc_lock_montaggi(t.tgrelid) AS m
      WHERE NOT t.tgisinternal
        AND m.trigger_nome = t.tgname
        AND t.tgfoid = 'vendite.trgfn_doc_righe_lock_fuori_bozza'::regproc
        AND (n.nspname || '.' || c.relname) NOT IN (SELECT tabella FROM _sat)
        AND m.regola ->> 'codice' IS DISTINCT FROM 'E_RIGA_DOC_NON_BOZZA'),
    0,
    '3) gli adottanti di prima (righe, componenti, rientri, prelievi) restano su E_RIGA_DOC_NON_BOZZA'
);

SELECT is(
    ARRAY[script.fn_doc_riga_modificabile('vendite.ordini_indirizzi'::regclass, 'DRAFT'),
          script.fn_doc_riga_modificabile('vendite.ordini_indirizzi'::regclass, 'CONFERMATO'),
          script.fn_doc_riga_modificabile('vendite.offerte_commerciali_utilities'::regclass, 'BOZZA'),
          script.fn_doc_riga_modificabile('vendite.offerte_commerciali_utilities'::regclass, 'EMESSA'),
          script.fn_doc_riga_modificabile('config.valute'::regclass, 'QUALSIASI')],
    ARRAY[true, false, true, false, true],
    '4) script.fn_doc_riga_modificabile: aperta in bozza, chiusa fuori; una tabella senza lock e'' aperta, come il database'
);

-- =========================================================
-- Il mondo: un cliente, un listino con una versione in vigore e due
-- articoli (A nel listino, X fuori), un secondo listino della stessa
-- utility, due ordini e un preventivo nati in bozza.
-- =========================================================
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP testata dopo emissione R-DB');

-- ⚠️ La versione del builder nasce ATTIVA: la si fa finire nel 2020, e la
--    versione che copre OGGI si costruisce qui (BOZZA, righe, ATTIVA), come
--    in test-righe-esclusione-solo-non-si-vende-v1.
CREATE TEMP TABLE _l AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM _m), 'R-DB',
                                          '2020-01-01'::date, '2020-12-31'::date);

CREATE TEMP TABLE _v AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, stato)
    SELECT listino_id, 'PGTAP_RDB_V2', '2021-01-01'::date, 'BOZZA' FROM _l
    RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE _art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGTAP-RDB-' || v.sigla,
           p_listino_tipologia_id => (SELECT tipologia_id FROM _l)) AS id
  FROM (VALUES ('A'), ('X')) AS v(sigla);

CREATE FUNCTION pg_temp.art(p_sigla text) RETURNS uuid
LANGUAGE sql STABLE AS $f$ SELECT id FROM _art WHERE sigla = p_sigla $f$;

INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT (SELECT id FROM _v), a.id, a.uom_id, 100.00
  FROM catalogo.articoli a WHERE a.id = pg_temp.art('A');

UPDATE vendite.listini_versioni SET stato = 'ATTIVA' WHERE id = (SELECT id FROM _v);

-- Il secondo listino: stessa utility, stessa azienda.
CREATE TEMP TABLE _l2 AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM _m), 'R-DB secondo');

CREATE TEMP TABLE _k AS
SELECT (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE AND i.aliquota_iva > 0 ORDER BY i.id LIMIT 1) AS iva_id,
       (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id;

CREATE TEMP TABLE _doc (chiave text PRIMARY KEY, id bigint);

CREATE FUNCTION pg_temp.doc(p text) RETURNS bigint
LANGUAGE sql STABLE AS $f$ SELECT id FROM _doc WHERE chiave = p $f$;

-- Il tipo d'indirizzo ammesso per un ambito (il primo, per id).
CREATE FUNCTION pg_temp.tipo(p_ambito text) RETURNS integer
LANGUAGE sql STABLE AS $f$
    SELECT a.tipo_indirizzo_id FROM config.tipi_indirizzi_allowed a
     WHERE a.ambito = p_ambito AND a.attivo ORDER BY a.tipo_indirizzo_id LIMIT 1
$f$;

-- Gli ordini: in bozza con una riga 2 x 10 sull'articolo X (fuori listino) e
--   il trigger SPEDITO. Quello da confermare esce dalla bozza piu' sotto, dopo
--   aver preso l'indirizzo: la conferma non sta nel builder.
CREATE TEMP TABLE _o_conf AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('testata dopo emissione R-DB conf', 'DRAFT',
    p_billing_account_id => (SELECT billing_account_id FROM _m),
    p_quantita => 2, p_prezzo => 10, p_articolo_id => pg_temp.art('X'),
    p_fatturazione_trigger => 'SPEDITO', p_data_ordine => script.fn_data_operativa());
CREATE TEMP TABLE _o_draft AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('testata dopo emissione R-DB draft', 'DRAFT',
    p_billing_account_id => (SELECT billing_account_id FROM _m),
    p_quantita => 2, p_prezzo => 10, p_articolo_id => pg_temp.art('X'),
    p_fatturazione_trigger => 'SPEDITO', p_data_ordine => script.fn_data_operativa());
INSERT INTO _doc
SELECT 'ORD_CONF', ordine_id FROM _o_conf
UNION ALL
SELECT 'ORD_DRAFT', ordine_id FROM _o_draft;

DO $fixture$
DECLARE
    c    record;
    k    record;
    v_id bigint;
BEGIN
    SELECT * INTO c FROM _m;
    SELECT * INTO k FROM _k;

    INSERT INTO vendite.preventivi
        (numero, stato_doc_preventivo_id, utility_id, istanza_utility_id,
         billing_account_id, data, emittente_fiscale_id, valuta_id)
    VALUES
        ('PGT-RDB-' || substring(md5(clock_timestamp()::text) FOR 6),
         (SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'DRAFT'),
         c.utility_id, c.istanza_utility_id, c.billing_account_id,
         script.fn_data_operativa(), c.emittente_fiscale_id, k.valuta_id)
    RETURNING id INTO v_id;

    INSERT INTO vendite.preventivi_righe
        (preventivo_id, articolo_id, quantita, qta_operativa, prezzo_unitario, iva_id, ordine)
    VALUES (v_id, pg_temp.art('X'), 2, 2, 10, k.iva_id, 1);

    INSERT INTO _doc VALUES ('PREV', v_id);

    -- L'indirizzo dell'ordine da confermare, scritto in bozza.
    INSERT INTO vendite.ordini_indirizzi (ordine_id, tipo_indirizzo_id, snapshot)
    VALUES (pg_temp.doc('ORD_CONF'), pg_temp.tipo('ORDINE_VENDITA'), '{"display":"pgtap"}'::jsonb);

    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', pg_temp.doc('ORD_CONF'), 'CONFERMATO');
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', v_id, 'EMESSO');
END
$fixture$;

-- =========================================================
-- 5-11) I satelliti di un ordine e di un preventivo veri
-- =========================================================
SELECT is(
    pg_temp.esito(format(
        $$INSERT INTO vendite.ordini_indirizzi (ordine_id, tipo_indirizzo_id, snapshot)
          VALUES (%s, %s, '{"display":"pgtap"}')$$,
        pg_temp.doc('ORD_DRAFT'), pg_temp.tipo('ORDINE_VENDITA'))),
    'PASSA',
    '5) ordine in bozza: l''indirizzo si aggiunge'
);

SELECT is(
    pg_temp.esito(format(
        $$INSERT INTO vendite.ordini_indirizzi (ordine_id, tipo_indirizzo_id, snapshot)
          SELECT %s, a.tipo_indirizzo_id, '{"display":"pgtap"}'
            FROM config.tipi_indirizzi_allowed a
           WHERE a.ambito = 'ORDINE_VENDITA' AND a.attivo AND a.tipo_indirizzo_id <> %s
           LIMIT 1$$,
        pg_temp.doc('ORD_CONF'), pg_temp.tipo('ORDINE_VENDITA'))),
    'E_DOC_DATI_COLLEGATI_NON_BOZZA',
    '6) ordine CONFERMATO: aggiungere un indirizzo e'' rifiutato col codice dei satelliti'
);

SELECT is(
    pg_temp.esito(format(
        $$UPDATE vendite.ordini_indirizzi SET snapshot = '{"display":"altro"}' WHERE ordine_id = %s$$,
        pg_temp.doc('ORD_CONF'))),
    'E_DOC_DATI_COLLEGATI_NON_BOZZA',
    '7) ... modificarlo pure'
);

SELECT is(
    pg_temp.esito(format($$DELETE FROM vendite.ordini_indirizzi WHERE ordine_id = %s$$, pg_temp.doc('ORD_CONF'))),
    'E_DOC_DATI_COLLEGATI_NON_BOZZA',
    '8) ... toglierlo pure'
);

SELECT throws_like(
    format($$DELETE FROM vendite.ordini_indirizzi WHERE ordine_id = %s$$, pg_temp.doc('ORD_CONF')),
    '%indirizzi e fornitura si possono togliere solo%',
    '9) ... e la frase parla di indirizzi e fornitura, col verbo tentato, non di righe'
);

SELECT is(
    ARRAY[(script.fn_available_actions_ordine(pg_temp.doc('ORD_DRAFT')) ->> 'can_edit_indirizzi')::boolean,
          (script.fn_available_actions_ordine(pg_temp.doc('ORD_CONF'))  ->> 'can_edit_indirizzi')::boolean],
    ARRAY[true, false],
    '10) la capability dell''ordine: can_edit_indirizzi vero in bozza, falso confermato (dal montaggio)'
);

SELECT is(
    pg_temp.esito(format(
        $$INSERT INTO vendite.preventivi_indirizzi (preventivo_id, tipo_indirizzo_id, snapshot)
          VALUES (%s, %s, '{"display":"pgtap"}')$$,
        pg_temp.doc('PREV'), pg_temp.tipo('PREVENTIVO')))
      || '|' || (script.fn_available_actions_preventivo(pg_temp.doc('PREV')) ->> 'can_edit_indirizzi'),
    'E_DOC_DATI_COLLEGATI_NON_BOZZA|false',
    '11) preventivo EMESSO: l''indirizzo e'' rifiutato, e la capability lo dice'
);

-- =========================================================
-- 12-17) L'offerta e il congelamento del listino
-- =========================================================
-- Tre offerte sul listino del mondo, senza versione fissata: due in BOZZA
-- (una si emette, una prende le righe), una RIFIUTATA (il documento chiuso,
-- per la capability).
-- rev 2026-10-24: nascono tutte in BOZZA (trigger della nascita); la RIFIUTATA
--   ci arriva per la matrice (BOZZA -> EMESSA -> RIFIUTATA), sotto i guard veri.

DO $off$
DECLARE
    r    record;
    v_id bigint;
BEGIN
    FOR r IN SELECT * FROM (VALUES ('OFF_EMETTI', 'BOZZA'), ('OFF_RIGHE', 'BOZZA'),
                                   ('OFF_RIFIUTATA', 'RIFIUTATA')) AS x(k, s) LOOP
        INSERT INTO vendite.offerte_commerciali
               (codice, emittente_fiscale_id, billing_account_id, istanza_utility_id,
                utility_id, listino_id, validita_dal)
        SELECT 'PGTAP-RDB-O-' || r.k || '-' || substr(gen_random_uuid()::text, 1, 8),
               m.emittente_fiscale_id, m.billing_account_id, m.istanza_utility_id,
               m.utility_id, l.listino_id, script.fn_data_operativa()
          FROM _m m, _l l
        RETURNING id INTO v_id;
        INSERT INTO _doc VALUES (r.k, v_id);
        IF r.s <> 'BOZZA' THEN
            PERFORM dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', v_id, r.s);
        END IF;
    END LOOP;
END
$off$;

SELECT is(
    (SELECT (c ->> 'can_edit_utility') || '|' || (c ->> 'can_edit_indirizzi') || '|'
            || ((c -> 'non_editable_fields') ? 'motivazione_rifiuto')::text
       FROM (SELECT script.fn_available_actions_offerta(pg_temp.doc('OFF_EMETTI')) AS c) x),
    'true|true|false',
    '12) offerta BOZZA: fornitura e indirizzi modificabili, motivazione_rifiuto non fra i non modificabili (R-DB-2)'
);

-- L'emissione dal verbo dell'offerta (rev 2026-10-26, giro 9: la porta rifiuta
-- l'UPDATE diretto); l'azione emetti_offerta all'utente del contesto: il test
-- prova il congelamento, non il permesso.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'emetti_offerta');
SELECT * FROM vendite.fn_cambia_stato_offerta(pg_temp.doc('OFF_EMETTI'), 'EMESSA', NULL);

SELECT is(
    (SELECT o.listino_versione_id FROM vendite.offerte_commerciali o WHERE o.id = pg_temp.doc('OFF_EMETTI')),
    (SELECT id FROM _v),
    '13) BOZZA -> EMESSA: l''uscita dalla bozza congela la versione del listino in vigore (il lock guarda lo stato di prima)'
);

SELECT is(
    pg_temp.esito(format(
        $$UPDATE vendite.offerte_commerciali SET listino_versione_id = NULL WHERE id = %s$$,
        pg_temp.doc('OFF_EMETTI'))),
    'E_DOC_CONDIZIONI_FUORI_BOZZA',
    '14) EMESSA: la versione congelata non si cambia piu'''
);

SELECT is(
    pg_temp.esito(format(
        $$INSERT INTO vendite.offerte_commerciali_utilities (offerta_id, istanza_utility_id, utility_id)
          SELECT %s, m.istanza_utility_id, m.utility_id FROM _m m$$,
        pg_temp.doc('OFF_EMETTI'))),
    'E_DOC_DATI_COLLEGATI_NON_BOZZA',
    '15) EMESSA: aggiungere la fornitura e'' rifiutato col codice dei satelliti'
);

SELECT is(
    (SELECT (c ->> 'can_edit_utility') || '|' || (c ->> 'can_edit_indirizzi') || '|'
            || ((c -> 'non_editable_fields') ? 'motivazione_rifiuto')::text
       FROM (SELECT script.fn_available_actions_offerta(pg_temp.doc('OFF_EMETTI')) AS c) x),
    'false|false|false',
    '16) EMESSA: la capability spegne fornitura e indirizzi; motivazione_rifiuto resta modificabile (D-10)'
);

SELECT ok(
    (script.fn_available_actions_offerta(pg_temp.doc('OFF_RIFIUTATA')) -> 'non_editable_fields') ? 'motivazione_rifiuto',
    '17) RIFIUTATA: motivazione_rifiuto fra i non modificabili, dal montaggio (documento chiuso)'
);

-- =========================================================
-- 18-20) Il contratto e il congelamento del listino
-- =========================================================
-- Quattro contratti sul listino del mondo, in DRAFT, su periodi disgiunti:
-- uno si attiva, tre servono al listino sotto le righe (22-26).
DO $con$
DECLARE
    v_k  text;
    v_n  integer := 0;
    v_id bigint;
BEGIN
    -- Periodi disgiunti: lo stesso cliente non ha due contratti sovrapposti,
    -- nemmeno in DRAFT (ex_contratti_no_overlap). Quello da attivare parte
    -- oggi; gli altri, uno per anno, piu' avanti.
    FOREACH v_k IN ARRAY ARRAY['CON_ATTIVA', 'CON_RIGHE', 'CON_AGGIUNTA', 'CON_VUOTO'] LOOP
        INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,
               stato_doc_contratto_id, listino_id, valido_dal, valido_al)
        SELECT 'PGT-RDB-' || v_k || '-' || substr(gen_random_uuid()::text, 1, 8),
               m.billing_account_id, m.istanza_utility_id, m.utility_id,
               (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),
               l.listino_id,
               script.fn_data_operativa() + v_n * 400,
               script.fn_data_operativa() + v_n * 400 + 365
          FROM _m m, _l l
        RETURNING id INTO v_id;
        INSERT INTO _doc VALUES (v_k, v_id);
        v_n := v_n + 1;
    END LOOP;
END
$con$;

-- rev 2026-10-26 (brief-modello-documento-vendita §11): l'attivazione dal verbo
--   (la porta ferma l'UPDATE diretto dello stato).
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, pg_temp.doc('CON_ATTIVA'), 'ATTIVO');

SELECT is(
    (SELECT c.listino_versione_id FROM vendite.contratti c WHERE c.id = pg_temp.doc('CON_ATTIVA')),
    (SELECT id FROM _v),
    '18) DRAFT -> ATTIVO: l''attivazione congela la versione del listino in vigore'
);

SELECT is(
    pg_temp.esito(format(
        $$UPDATE vendite.contratti SET listino_versione_id = NULL WHERE id = %s$$,
        pg_temp.doc('CON_ATTIVA'))),
    'E_DOC_CONDIZIONI_FUORI_BOZZA',
    '19) ATTIVO: la versione congelata non si cambia piu'''
);

SELECT is(
    pg_temp.esito(format(
        $$INSERT INTO vendite.contratti_indirizzi (contratto_id, tipo_indirizzo_id, snapshot)
          VALUES (%s, %s, '{"display":"pgtap"}')$$,
        pg_temp.doc('CON_ATTIVA'), pg_temp.tipo('CONTRATTO')))
      || '|' || (SELECT (c ->> 'can_edit_utility') || '|' || (c ->> 'can_edit_indirizzi')
                   FROM (SELECT script.fn_available_actions_contratto(pg_temp.doc('CON_ATTIVA')) AS c) x)
      || '|' || (SELECT (c ->> 'can_edit_utility') || '|' || (c ->> 'can_edit_indirizzi')
                   FROM (SELECT script.fn_available_actions_contratto(pg_temp.doc('CON_VUOTO')) AS c) x),
    'E_DOC_DATI_COLLEGATI_NON_BOZZA|false|false|true|true',
    '20) ATTIVO: l''indirizzo e'' rifiutato, e la capability spegne fornitura e indirizzi (in DRAFT accese)'
);

-- =========================================================
-- 21-29) Il listino sotto le righe (R-DB-4, D-11)
-- =========================================================
SELECT is(
    (SELECT string_agg(c.relname || ':' || t.tgname, ',' ORDER BY c.relname, t.tgname)
       FROM pg_catalog.pg_trigger t
       JOIN pg_catalog.pg_class c ON c.oid = t.tgrelid
      WHERE t.tgrelid IN ('vendite.contratti'::regclass, 'vendite.offerte_commerciali'::regclass)
        AND NOT t.tgisinternal
        AND t.tgname ~ '_(a05_lock_fuori_bozza|a10_guard_listino_con_righe|a10_guard_listino_documento)_upd$'),
    'contratti:trg_contratti_a05_lock_fuori_bozza_upd,'
    'contratti:trg_contratti_a10_guard_listino_con_righe_upd,'
    'contratti:trg_contratti_a10_guard_listino_documento_upd,'
    'offerte_commerciali:trg_offerte_commerciali_a05_lock_fuori_bozza_upd,'
    'offerte_commerciali:trg_offerte_commerciali_a10_guard_listino_con_righe_upd,'
    'offerte_commerciali:trg_offerte_commerciali_a10_guard_listino_documento_upd',
    '21) il guard del listino con righe su contratto e offerta, e l''ordine alfabetico dei rifiuti: il lock, poi le righe, poi utility ed emittente'
);

-- Le righe: un'esclusione di A (nel listino) e un'aggiunta di X (fuori).
-- L'esclusione nasce vuota; l'aggiunta coi dati di una riga che si fattura.
INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione)
VALUES (pg_temp.doc('CON_RIGHE'), pg_temp.art('A'), 'ESCLUSIONE');

INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id, tipo_eccezione)
VALUES (pg_temp.doc('OFF_RIGHE'), pg_temp.art('A'), 'ESCLUSIONE');

INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione, prezzo_unitario,
       quantita, qta_operativa, uom_operativa_id)
SELECT pg_temp.doc('CON_AGGIUNTA'), a.id, 'AGGIUNTA', 80.00, e.q, e.q, a.uom_id
  FROM catalogo.articoli a
  LEFT JOIN LATERAL (SELECT 1::numeric AS q FROM vendite.fn_articolo_erogazioni(a.id) x
                      WHERE x.e_default AND x.fonte_quantita_attesa = 'FISSA') e ON true
 WHERE a.id = pg_temp.art('X');

SELECT is(
    pg_temp.esito(format($$UPDATE vendite.contratti SET listino_id = %s WHERE id = %s$$,
                         (SELECT listino_id FROM _l2), pg_temp.doc('CON_RIGHE'))),
    'E_DOC_LISTINO_CAMBIO_CON_RIGHE',
    '22) contratto DRAFT con righe: un altro listino e'' rifiutato'
);

SELECT is(
    pg_temp.campo(format($$UPDATE vendite.contratti SET listino_id = %s WHERE id = %s$$,
                         (SELECT listino_id FROM _l2), pg_temp.doc('CON_RIGHE'))),
    'listino_id',
    '23) ... col campo listino_id'
);

SELECT is(
    pg_temp.esito(format($$UPDATE vendite.contratti SET listino_id = NULL WHERE id = %s$$,
                         pg_temp.doc('CON_RIGHE'))),
    'E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI',
    '24) contratto DRAFT con un''esclusione: togliere il listino e'' rifiutato'
);

SELECT is(
    pg_temp.esito(format($$UPDATE vendite.contratti SET listino_id = NULL WHERE id = %s$$,
                         pg_temp.doc('CON_AGGIUNTA'))),
    'PASSA',
    '25) contratto DRAFT con la sola aggiunta: il listino si toglie (l''aggiunta vale anche senza)'
);

SELECT is(
    pg_temp.esito(format($$UPDATE vendite.contratti SET listino_id = %s WHERE id = %s$$,
                         (SELECT listino_id FROM _l2), pg_temp.doc('CON_VUOTO'))),
    'PASSA',
    '26) contratto DRAFT senza righe: il listino si cambia'
);

SELECT is(
    pg_temp.esito(format($$UPDATE vendite.offerte_commerciali SET listino_id = %s WHERE id = %s$$,
                         (SELECT listino_id FROM _l2), pg_temp.doc('OFF_RIGHE'))),
    'E_DOC_LISTINO_CAMBIO_CON_RIGHE',
    '27) offerta BOZZA con righe: un altro listino e'' rifiutato, la stessa regola del contratto (D-11)'
);

SELECT is(
    pg_temp.esito(format($$UPDATE vendite.contratti SET listino_id = %s WHERE id = %s$$,
                         (SELECT listino_id FROM _l2), pg_temp.doc('CON_ATTIVA'))),
    'E_DOC_CONDIZIONI_FUORI_BOZZA',
    '28) contratto ATTIVO: un altro listino, e parla prima il lock di testata'
);

SELECT is(
    script.fn_check_listino_cambiabile('CONTRATTO', pg_temp.doc('CON_RIGHE'),
                                       (SELECT listino_id FROM _l), (SELECT listino_id FROM _l))::text
      || '|' || pg_temp.esito($$SELECT script.fn_check_listino_cambiabile('ORDINE', 1, 1, 2)$$),
    '[]|E_DOC_TIPO_NON_GESTITO',
    '29) la check: listino invariato, nessun motivo; un documento che non ha la regola e'' un errore di chiamante'
);

-- =========================================================
-- 30-33) Il cliente della bolla (R-DB-1)
-- =========================================================
DO $ddt$
DECLARE
    c record;
BEGIN
    SELECT * INTO c FROM _m;
    INSERT INTO _doc VALUES
        ('DDT_LIBERA',    dbops.fn_pgtap_crea_ddt(c.billing_account_id, c.cliente_soggetto_ruolo_id, 'VENDITA')),
        ('DDT_DA_ORDINE', dbops.fn_pgtap_crea_ddt(c.billing_account_id, c.cliente_soggetto_ruolo_id, 'VENDITA'));

    -- La bolla da ordine: la sorgente di testata e' l'ordine confermato,
    -- che ha lo stesso cliente.
    UPDATE vendite.ddt d
       SET sorgente_tipo_id = (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA'),
           sorgente_uid     = (SELECT o.uid FROM vendite.ordini o WHERE o.id = pg_temp.doc('ORD_CONF'))
     WHERE d.id = pg_temp.doc('DDT_DA_ORDINE');
END
$ddt$;

SELECT is(
    (SELECT count(*)::text FROM vendite.ddt d
      CROSS JOIN LATERAL vendite.fn_ddt_vincoli_cliente(d.id, d.sorgente_tipo_id, d.sorgente_uid)
      WHERE d.id = pg_temp.doc('DDT_LIBERA'))
      || '|' || ((script.fn_available_actions_ddt(pg_temp.doc('DDT_LIBERA')) -> 'non_editable_fields')
                 ? 'billing_account_id')::text,
    '0|false',
    '30) bolla senza sorgente: nessun vincolo, e in bozza il cliente si sceglie (D-2 di ba-coppia)'
);

SELECT is(
    (SELECT string_agg(v.vincolo || ':' || v.sorgente || ':' || (v.billing_account_id = (SELECT billing_account_id FROM _m))::text, ',')
       FROM vendite.ddt d
      CROSS JOIN LATERAL vendite.fn_ddt_vincoli_cliente(d.id, d.sorgente_tipo_id, d.sorgente_uid) AS v
      WHERE d.id = pg_temp.doc('DDT_DA_ORDINE'))
      || '|' || ((script.fn_available_actions_ddt(pg_temp.doc('DDT_DA_ORDINE')) -> 'non_editable_fields')
                 ? 'billing_account_id')::text,
    'SORGENTE:ORDINE_VENDITA:true|true',
    '31) bolla da ordine: il vincolo e'' la sorgente, col cliente dell''ordine, e in bozza il cliente e'' fra i non modificabili'
);

SELECT is(
    pg_temp.esito(format($$UPDATE vendite.ddt SET billing_account_id = NULL WHERE id = %s$$,
                         pg_temp.doc('DDT_DA_ORDINE'))),
    'E_DOC_CLIENTE_DIVERSO_DA_SORGENTE',
    '32) ... e il guard rifiuta il cambio di cliente: la capability lo spegne dove il guard rifiuta'
);

SELECT is(
    ARRAY[(SELECT p.prosrc ~ 'fn_ddt_vincoli_cliente' FROM pg_catalog.pg_proc p
            WHERE p.oid = 'vendite.trgfn_ddt_guard_cliente_sorgente'::regproc),
          (SELECT p.prosrc ~ 'ordini_righe_fulfillment' FROM pg_catalog.pg_proc p
            WHERE p.oid = 'vendite.trgfn_ddt_guard_cliente_sorgente'::regproc),
          (SELECT p.prosrc ~ 'fn_ddt_vincoli_cliente' FROM pg_catalog.pg_proc p
            WHERE p.oid = 'script.fn_available_actions_ddt'::regproc),
          (SELECT p.prosrc ~ 'c_non_edit_draft CONSTANT jsonb :=\s*''\[[^]]*billing_account_id'
             FROM pg_catalog.pg_proc p
            WHERE p.oid = 'script.fn_available_actions_ddt'::regproc)],
    ARRAY[true, false, true, false],
    '33) la regola sta in un posto solo: guard e capability chiamano vendite.fn_ddt_vincoli_cliente; il guard non legge il fulfillment da se''; il cliente non e'' fra le costanti della capability'
);

-- =========================================================
-- 34) I codici
-- =========================================================
SELECT is(
    (SELECT string_agg(ce.codice || ':' || ce.classe || ':' || coalesce(ce.obsoleto_dal::text, '-') || ':'
                       || (EXISTS (SELECT 1 FROM config.messaggi_errore me
                                    WHERE me.codice = ce.codice AND me.lingua = 'it'))::text,
                       ',' ORDER BY ce.codice)
       FROM config.codici_errore ce
      WHERE ce.codice IN ('E_DOC_DATI_COLLEGATI_NON_BOZZA', 'E_DOC_LISTINO_CAMBIO_CON_RIGHE',
                          'E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI',
                          'E_CONTRATTO_CAMPI_BLOCCATI_CON_RIGHE', 'E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI')),
    'E_CONTRATTO_CAMPI_BLOCCATI_CON_RIGHE:NON_ESEGUIBILE:2026-10-11:true,'
    'E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI:NON_ESEGUIBILE:2026-10-11:true,'
    'E_DOC_DATI_COLLEGATI_NON_BOZZA:CONFLITTO_STATO:-:true,'
    'E_DOC_LISTINO_CAMBIO_CON_RIGHE:NON_ESEGUIBILE:-:true,'
    'E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI:NON_ESEGUIBILE:-:true',
    '34) i codici nuovi sono a catalogo con classe e messaggio; i due del contratto sono ritirati (il messaggio resta)'
);

-- =========================================================
-- 35-36) La nascita (D-13 di Tid)
-- =========================================================
-- I dati precontrattuali dell'istanza: da qui ogni contratto nuovo del
-- cliente riceve lo snapshot della fornitura (AFTER INSERT). I quattro
-- contratti di sopra sono nati prima, e non ce l'hanno.
INSERT INTO anagrafiche.istanze_dati_precontrattuali (istanza_utility_id, utility_id)
SELECT m.istanza_utility_id, m.utility_id FROM _m m;

-- ⚠️ L'esito si scrive in una tabella, e lo snapshot si conta DOPO, in
--    un'istruzione sua: nella stessa istruzione la sotto-select vedrebbe la
--    fotografia di prima dell'INSERT.
-- ⛔ rev 2026-10-24 (brief-modello-documento-vendita N-1): fino a oggi il
--    contratto si INSERIVA gia' ATTIVO. Ora nasce in DRAFT (trigger della
--    nascita) e si attiva per la matrice, in un'istruzione sua: lo snapshot
--    resta quello scritto alla nascita, e lo stato si legge nell'asserzione.
CREATE TEMP TABLE _nato AS
SELECT pg_temp.esito(format(
        $$INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,
               listino_id, valido_dal, valido_al)
          SELECT 'PGT-RDB-NATO-ATTIVO', m.billing_account_id, m.istanza_utility_id, m.utility_id,
                 l.listino_id, %L::date, %L::date
            FROM _m m, _l l$$,
        script.fn_data_operativa() + 2000, script.fn_data_operativa() + 2365)) AS esito;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti', c.id, 'ATTIVO')
  FROM vendite.contratti c
 WHERE c.numero = 'PGT-RDB-NATO-ATTIVO';

SELECT is(
    (SELECT esito FROM _nato)
      || '|' || (SELECT s.codice_interno::text FROM vendite.contratti c
                   JOIN config.stati_doc_contratti s ON s.id = c.stato_doc_contratto_id
                  WHERE c.numero = 'PGT-RDB-NATO-ATTIVO')
      || '|' || (SELECT count(*)::text FROM vendite.contratti_utilities cu
                   JOIN vendite.contratti c ON c.id = cu.contratto_id
                  WHERE c.numero = 'PGT-RDB-NATO-ATTIVO'),
    'PASSA|ATTIVO|1',
    '35) un contratto nato in DRAFT e attivato porta lo snapshot della fornitura scritto dal trigger: e'' parte della sua nascita'
);

SELECT is(
    pg_temp.esito(format(
        $$INSERT INTO vendite.contratti_utilities (contratto_id, istanza_utility_id, utility_id)
          SELECT %s, m.istanza_utility_id, m.utility_id FROM _m m$$,
        pg_temp.doc('CON_ATTIVA'))),
    'E_DOC_DATI_COLLEGATI_NON_BOZZA',
    '36) ... ma la fornitura scritta DIRETTAMENTE su un contratto attivo, nato in questa stessa transazione, e'' rifiutata'
);

-- 37) La strada di prima del 35 non c'e' piu': un INSERT che dice ATTIVO lo
--     rifiuta il trigger della nascita (trg_contratti_a05_stato_iniziale_ins).
SELECT is(
    pg_temp.esito(format(
        $$INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,
               stato_doc_contratto_id, listino_id, valido_dal, valido_al)
          SELECT 'PGT-RDB-NATO-ATTIVO-2', m.billing_account_id, m.istanza_utility_id, m.utility_id,
                 (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO'),
                 l.listino_id, %L::date, %L::date
            FROM _m m, _l l$$,
        script.fn_data_operativa() + 3000, script.fn_data_operativa() + 3365)),
    'E_DOC_STATO_INIZIALE_NON_VALIDO',
    '37) un contratto non nasce gia'' ATTIVO: lo rifiuta il trigger della nascita (E_DOC_STATO_INIZIALE_NON_VALIDO)'
);

SELECT * FROM finish();

ROLLBACK;
