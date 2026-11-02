-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): la riga dell'ordine di A da dbops.fn_pgtap_crea_ordine_con_righe sulla testata del caso (p_ordine_id, resta DRAFT: la conferma e' il 29), l'ordine di E2 da dbops.fn_pgtap_crea_ordine; restano a mano le testate di ordini e bolle (il caso: BA, utility, causali, BA NULL) e la riga di pg_temp.ddt_bozza (nessun builder scrive una riga su una testata del test; le bolle senza BA il builder non le fa).
--
-- Test: ordine, DDT e reso parlano del cliente come preventivo, offerta e
--   contratto — il billing account, e le copie in testata legate a lui.
--   Brief: docs/it/dev/work-done/brief-db-esecutivi-ba-coppia.md
--   ChangeSet 20261009-62 ... -92, 20261010-02 ... -07 (giro 2: BB delle copie
--   dal BA, sorgente non trovata = errore).
--
-- ⭐ I soggetti li FABBRICA (dbops.fn_pgtap_crea_emittente_operatore,
--   fn_pgtap_crea_cliente_ba): il test non pesca dai dati della macchina e
--   gira uguale su un database ricostruito da zero (AGENTS.md, corollario sui
--   test). Due clienti, A e B, dello stesso emittente.
-- ⚠️ I lock di colonna (test 22-24) li genera l'automazione dal registro
--   dbops.automation_lock_columns (90_end, converge a ogni migrate): prima
--   dell'apply non ci sono.
--
-- Indice test (1..30):
--   STRUTTURA
--    1) le quattro FK composte verso uq_billing_account_id_cliente
--    2) ordini: billing_account_id e utility_id NOT NULL
--    3) causali che vogliono il cliente: VENDITA, OMAGGIO, CAMPIONATURA, CONTO_VISIONE
--   ORDINE (D-1, D-5)
--    4) un ordine senza BA non nasce (23502)
--    5) col BA di A e il ruolo di B non nasce (E_DOC_CLIENTE_DIVERSO_DA_BA, BB)
--    6) senza utility nasce, con la utility del BA
--   DDT (D-2, D-4, D-5)
--    7) standalone col BA e senza utility: la utility la mette il BA
--    8) utility senza BA: CHECK «tutti e due o nessuno» (23514)
--    9) col BA di A e il destinatario di B: E_DOC_CLIENTE_DIVERSO_DA_BA (BB)
--   10) in bozza il BA si sceglie: destinatario e utility lo seguono
--   11) bozza CONTO_VISIONE senza BA: la check d'emissione ha il motivo
--   12) bozza TRASFERIMENTO senza BA: nessun motivo cliente
--   13) l'emissione di un CONTO_VISIONE senza BA e' rifiutata (E_DDT_CLIENTE_OBBLIGATORIO)
--   14) col BA l'emissione passa
--   15) fuori bozza il cliente non cambia (E_DDT_CLIENTE_IMMUTABILE)
--   16) fuori bozza la causale non cambia (E_DDT_CAUSALE_IMMUTABILE, frase nuova)
--   CATENA (D-6)
--   17) DDT da ordine senza BA: BA, utility e destinatario dall'ordine
--   18) DDT da ordine col BA di un altro cliente: rifiutato
--   19) fulfillment fra l'ordine di A e il DDT di B: rifiutato
--   20) il BA di un DDT che evade gia' righe d'ordine non cambia, nemmeno in bozza
--   21) reso col BA diverso dal suo DDT: rifiutato
--   IDENTITA' (D-7)
--   22) il ruolo di un BA non cambia (E_BA_ISTANZA_IMMUTABILE, parla il lock)
--   23) il soggetto di un'istanza non cambia (E_ISTANZA_SOGGETTO_IMMUTABILE)
--   24) il lock del cliente copre le quattro colonne della fornitura
--   25) un BA non nasce su un ruolo che non e' CLIENTE
--   26) il guard del ruolo del BA sta in fascia _a20_, dopo il lock
--   PUSH
--   27) la diagnosi legge il BA dalla testata del DDT
--   EMITTENTE (brief §9.8)
--   28) fuori bozza il DDT non cambia emittente (E_DOC_EMITTENTE_FUORI_BOZZA)
--   29) fuori bozza l'ordine non cambia emittente
--   30) preventivo: emittente sul BB fuori bozza, non piu' nel lock assoluto (§9.9)
--   GIRO 2 (brief §10.2 e §10.3, 2026-10-10)
--   31) ordine con la utility di un altro BA: E_DOC_CLIENTE_DIVERSO_DA_BA
--   32) cliente col BA di A e il ruolo di B: E_DOC_CLIENTE_DIVERSO_DA_BA (prima 23503)
--   33) DDT: il BA tolto in bozza toglie la utility e lascia il destinatario
--   34) omaggio e campionatura senza BA: la check d'emissione ha il motivo cliente
--   35) DDT senza BA (conto lavoro) consegnato: il reso nasce senza BA (D-3, «NULL compreso»)
--   36) DDT con un ordine sorgente che non esiste: E_DOC_SORGENTE_NON_TROVATA
--   37) reso spostato su un DDT che non esiste: E_DOC_SORGENTE_NON_TROVATA (UPDATE)
--   38) lock dell'emittente fuori bozza montato su offerte, contratti e resi
--   39) DDT di E1 dall'ordine di E2 (invisibile): E_DOC_SORGENTE_NON_TROVATA
--       ⚠️ ROSSO DA OWNER, VERDE COME APP: da owner la RLS non c'e', l'ordine si
--       vede e parla E_DOC_CLIENTE_DIVERSO_DA_SORGENTE. Per ultimo: cambia
--       contesto (memoria del progetto, prova pre-apply da owner).
-- rev 2026-10-25 (brief-modello-documento-vendita §7, giro 5): emissioni e
--   consegne delle bolle da dbops.fn_pgtap_porta_a_stato (il verbo), non piu'
--   con un UPDATE diretto dello stato (E_DOC_STATO_SOLO_DAL_VERBO). Il 13 prova
--   lo stesso guard d'emissione dal verbo: l'attesa non cambia.
-- ------------------------------------------------------------
BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(39);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Il test gira come applicazione (RLS attiva): si agisce come l'operatore
-- dell'emittente appena creato, e il billing account dei clienti lo lega a
-- quell'emittente il trigger z90 (il terzo argomento dell'helper serve solo
-- da owner: sotto la RLS il BA non ancora legato non si vede).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;

CREATE TEMP TABLE _c AS
SELECT 'A' AS lato, c.* FROM dbops.fn_pgtap_crea_cliente_ba('esecutivi A') c
UNION ALL
SELECT 'B' AS lato, c.* FROM dbops.fn_pgtap_crea_cliente_ba('esecutivi B') c;

SET CONSTRAINTS ALL IMMEDIATE;

CREATE TEMP TABLE _k AS
SELECT (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'DRAFT')   AS ord_draft,
       (SELECT id FROM config.stati_doc_ddt    WHERE codice_interno = 'DRAFT')   AS ddt_draft,
       (SELECT id FROM config.stati_doc_ddt    WHERE codice_interno = 'EMESSO')  AS ddt_emesso,
       (SELECT id FROM config.stati_doc_ddt    WHERE codice_interno = 'SPEDITO') AS ddt_spedito,
       (SELECT id FROM config.stati_doc_ddt    WHERE codice_interno = 'CONSEGNATO') AS ddt_consegnato,
       (SELECT id FROM config.stati_doc_reso   WHERE codice_interno = 'DRAFT')   AS reso_draft,
       (SELECT id FROM config.causali_trasporto WHERE codice = 'CONTO_VISIONE')  AS cv,
       (SELECT id FROM config.causali_trasporto WHERE codice = 'TRASFERIMENTO')  AS trasf,
       (SELECT id FROM config.causali_trasporto WHERE codice = 'VENDITA')        AS vendita,
       (SELECT id FROM config.causali_trasporto WHERE codice = 'OMAGGIO')        AS omaggio,
       (SELECT id FROM config.causali_trasporto WHERE codice = 'CAMPIONATURA')   AS campionatura,
       (SELECT id FROM config.causali_trasporto WHERE codice = 'CONTO_LAVORO')   AS conto_lavoro,
       (SELECT id FROM config.sorgenti WHERE codice_interno = 'ORDINE_VENDITA')  AS src_ordine,
       (SELECT id FROM config.sorgenti WHERE codice_interno = 'DDT_VENDITA')     AS src_ddt,
       (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'CON')       AS ind_con,
-- 🔴 rev 2026-10-13 (brief-db-articoli-ammessi-per-documento D-1/D-2): l'articolo si
--   COSTRUISCE. Prima si pescava dal catalogo (il primo per id, o il piu' recente):
--   il primo per id e' l'onere del seed ONERE_SENZA_CONTRATTO (natura servizio), e
--   da 20261013-42 ordine e bolla portano solo merce. Un articolo costruito ha solo
--   le proprieta' che il test gli da' (merce, non gestito a magazzino).
       dbops.fn_pgtap_crea_articolo('PGT-EBC-ART', false)              AS articolo,
       (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                  AS valuta,
       (SELECT emittente_fiscale_id FROM _m)                                     AS ef;

-- Un DDT in bozza con una riga e l'indirizzo di consegna obbligatorio: pronto
-- a uscire dalla bozza se causale e cliente lo consentono.
CREATE FUNCTION pg_temp.ddt_bozza(p_ba bigint, p_dest bigint, p_causale bigint)
RETURNS bigint LANGUAGE plpgsql AS $f$
DECLARE v_id bigint;
BEGIN
    INSERT INTO vendite.ddt
        (destinatario_soggetto_ruolo_id, billing_account_id, stato_doc_ddt_id,
         emittente_fiscale_id, causale_trasporto_id)
    SELECT p_dest, p_ba, k.ddt_draft, k.ef, p_causale FROM _k k
    RETURNING id INTO v_id;
    INSERT INTO vendite.ddt_righe
        (ddt_id, riga_nr, articolo_id, descrizione, quantita, qta_operativa)
    SELECT v_id, 1, k.articolo, 'Riga pgTAP esecutivi', 1, 1 FROM _k k;
    INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
    SELECT v_id, k.ind_con, '{"pgtap": true}'::jsonb FROM _k k;
    RETURN v_id;
END $f$;

-- ============================================================
-- STRUTTURA
-- ============================================================
SELECT is(
    -- ⚠️ schema e nome dal catalogo, non regclass::text: quello dipende dal
    --   search_path, e come app esce «clienti» invece di «anagrafiche.clienti».
    (SELECT string_agg(n.nspname || '.' || r.relname || '.' || c.conname, ', ' ORDER BY c.conname)
       FROM pg_constraint c
       JOIN pg_class r ON r.oid = c.conrelid
       JOIN pg_namespace n ON n.oid = r.relnamespace
      WHERE c.contype = 'f'
        AND c.confrelid = 'anagrafiche.billing_account'::regclass
        AND c.conname IN ('fk_ordini_ba_cliente', 'fk_ddt_ba_cliente',
                          'fk_resi_ba_cliente', 'fk_clienti_ba_cliente')
        AND (SELECT array_agg(a.attname ORDER BY k.n)
               FROM unnest(c.confkey) WITH ORDINALITY k(attnum, n)
               JOIN pg_attribute a ON a.attrelid = c.confrelid AND a.attnum = k.attnum)
            = ARRAY['id', 'soggetto_ruolo_id', 'utility_id']::name[]),
    'anagrafiche.clienti.fk_clienti_ba_cliente, vendite.ddt.fk_ddt_ba_cliente, vendite.ordini.fk_ordini_ba_cliente, vendite.resi.fk_resi_ba_cliente',
    '1) le quattro FK composte puntano a (id, soggetto_ruolo_id, utility_id) del billing account');

SELECT is(
    (SELECT string_agg(attname || '=' || attnotnull, ',' ORDER BY attname)
       FROM pg_attribute
      WHERE attrelid = 'vendite.ordini'::regclass
        AND attname IN ('billing_account_id', 'utility_id')),
    'billing_account_id=true,utility_id=true',
    '2) ordini: billing_account_id e utility_id NOT NULL');

SELECT is(
    (SELECT string_agg(codice, ',' ORDER BY codice)
       FROM config.causali_trasporto WHERE richiede_cliente),
    'CAMPIONATURA,CONTO_VISIONE,OMAGGIO,VENDITA',
    '3) vogliono il cliente vendita, omaggio, campionatura e conto visione (D-2-bis); non il reso a fornitore');

-- ============================================================
-- ORDINE
-- ============================================================
SELECT throws_ok(
    format($q$INSERT INTO vendite.ordini (soggetto_ruolo_id, stato_doc_ordine_id, emittente_fiscale_id, valuta_id)
              VALUES (%s, %s, %s, %s)$q$,
           (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'A'),
           (SELECT ord_draft FROM _k), (SELECT ef FROM _k), (SELECT valuta FROM _k)),
    '23502', NULL,
    '4) un ordine senza billing account non nasce (D-1)');

SELECT throws_like(
    format($q$INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id, emittente_fiscale_id, valuta_id)
              VALUES (%s, %s, %s, %s, %s)$q$,
           (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'B'),
           (SELECT billing_account_id FROM _c WHERE lato = 'A'),
           (SELECT ord_draft FROM _k), (SELECT ef FROM _k), (SELECT valuta FROM _k)),
    '%il cliente non corrisponde al billing account%',
    '5) col BA di A e il ruolo di B l''ordine non nasce: E_DOC_CLIENTE_DIVERSO_DA_BA dal BB (la FK composta resta sotto)');

CREATE TEMP TABLE _ord AS
WITH o AS (
    INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
                                emittente_fiscale_id, valuta_id)
    SELECT c.soggetto_ruolo_id, c.billing_account_id, k.ord_draft, k.ef, k.valuta
      FROM _c c, _k k WHERE c.lato = 'A'
    RETURNING id, uid, billing_account_id, utility_id
)
SELECT * FROM o;

SELECT is(
    (SELECT utility_id FROM _ord),
    (SELECT utility_id FROM _c WHERE lato = 'A'),
    '6) senza utility l''ordine nasce con quella del suo BA (copia scritta da chi la conosce)');

-- La riga (5 a 10) sulla testata del caso, che resta in bozza: la conferma e'
-- un passo del test 29.
CREATE TEMP TABLE _ord_riga AS
SELECT o.ordine_riga_id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('esecutivi A', 'DRAFT',
         p_quantita => 5, p_prezzo => 10, p_articolo_id => (SELECT articolo FROM _k),
         p_ordine_id => (SELECT id FROM _ord)) o;

-- ============================================================
-- DDT
-- ============================================================
CREATE TEMP TABLE _d AS
SELECT pg_temp.ddt_bozza((SELECT billing_account_id FROM _c WHERE lato = 'A'),
                         (SELECT soggetto_ruolo_id  FROM _c WHERE lato = 'A'),
                         (SELECT cv FROM _k)) AS con_ba,
       pg_temp.ddt_bozza(NULL,
                         (SELECT soggetto_ruolo_id  FROM _c WHERE lato = 'A'),
                         (SELECT cv FROM _k)) AS senza_ba,
       pg_temp.ddt_bozza(NULL,
                         (SELECT soggetto_ruolo_id  FROM _c WHERE lato = 'B'),
                         (SELECT trasf FROM _k)) AS trasf;

SELECT is(
    (SELECT utility_id FROM vendite.ddt WHERE id = (SELECT con_ba FROM _d)),
    (SELECT utility_id FROM _c WHERE lato = 'A'),
    '7) DDT standalone col BA e senza utility: la utility la mette il BA');

SELECT throws_ok(
    format($q$INSERT INTO vendite.ddt (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, emittente_fiscale_id, utility_id)
              VALUES (%s, %s, %s, %s)$q$,
           (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'A'),
           (SELECT ddt_draft FROM _k), (SELECT ef FROM _k),
           (SELECT utility_id FROM _c WHERE lato = 'A')),
    '23514', NULL,
    '8) utility senza billing account: chk_ddt_ba_utility_insieme');

SELECT throws_like(
    format($q$INSERT INTO vendite.ddt (destinatario_soggetto_ruolo_id, billing_account_id, stato_doc_ddt_id, emittente_fiscale_id)
              VALUES (%s, %s, %s, %s)$q$,
           (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'B'),
           (SELECT billing_account_id FROM _c WHERE lato = 'A'),
           (SELECT ddt_draft FROM _k), (SELECT ef FROM _k)),
    '%il cliente non corrisponde al billing account%',
    '9) col BA di A il destinatario non e'' B: la consegna a terzi passa dagli indirizzi (D-4)');

-- 10) in bozza il BA si sceglie, e le copie lo seguono
UPDATE vendite.ddt
   SET billing_account_id = (SELECT billing_account_id FROM _c WHERE lato = 'B')
 WHERE id = (SELECT trasf FROM _d);

SELECT is(
    (SELECT (destinatario_soggetto_ruolo_id, utility_id)::text FROM vendite.ddt WHERE id = (SELECT trasf FROM _d)),
    (SELECT (soggetto_ruolo_id, utility_id)::text FROM _c WHERE lato = 'B'),
    '10) in bozza il BA si sceglie: destinatario e utility seguono il billing account');

UPDATE vendite.ddt SET billing_account_id = NULL WHERE id = (SELECT trasf FROM _d);

CREATE TEMP TABLE _t33 AS
SELECT d.utility_id, d.destinatario_soggetto_ruolo_id FROM vendite.ddt d WHERE d.id = (SELECT trasf FROM _d);

SELECT ok(
    (SELECT script.fn_check_ddt_emittibile(d) @> '[{"codice": "E_DDT_CLIENTE_OBBLIGATORIO"}]'
       FROM vendite.ddt d WHERE d.id = (SELECT senza_ba FROM _d)),
    '11) conto visione senza BA: la check d''emissione ha il motivo E_DDT_CLIENTE_OBBLIGATORIO');

SELECT ok(
    (SELECT NOT (script.fn_check_ddt_emittibile(d) @> '[{"codice": "E_DDT_CLIENTE_OBBLIGATORIO"}]')
       FROM vendite.ddt d WHERE d.id = (SELECT trasf FROM _d)),
    '12) trasferimento senza BA: la causale non vuole un cliente, nessun motivo');

SELECT throws_like(
    format($q$SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', %s, 'EMESSO')$q$,
           (SELECT senza_ba FROM _d)),
    '%manda la merce a un cliente%',
    '13) l''emissione di un conto visione senza BA e'' rifiutata: E_DDT_CLIENTE_OBBLIGATORIO');

SELECT lives_ok(
    format($q$SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', %s, 'EMESSO')$q$,
           (SELECT con_ba FROM _d)),
    '14) col BA il conto visione si emette');

SELECT throws_like(
    format('UPDATE vendite.ddt SET billing_account_id = %s WHERE id = %s',
           (SELECT billing_account_id FROM _c WHERE lato = 'B'), (SELECT con_ba FROM _d)),
    '%il cliente si sceglie solo in bozza%',
    '15) fuori bozza il cliente non cambia: E_DDT_CLIENTE_IMMUTABILE dal BB di testata');

SELECT throws_like(
    format('UPDATE vendite.ddt SET causale_trasporto_id = %s WHERE id = %s',
           (SELECT vendita FROM _k), (SELECT con_ba FROM _d)),
    '%la causale di trasporto si sceglie solo in bozza%',
    '16) fuori bozza la causale non cambia: E_DDT_CAUSALE_IMMUTABILE dal BB di testata');

-- ============================================================
-- CATENA
-- ============================================================
CREATE TEMP TABLE _dord AS
WITH d AS (
    INSERT INTO vendite.ddt (stato_doc_ddt_id, emittente_fiscale_id, sorgente_tipo_id, sorgente_uid)
    SELECT k.ddt_draft, k.ef, k.src_ordine, o.uid FROM _k k, _ord o
    RETURNING id, billing_account_id, utility_id, destinatario_soggetto_ruolo_id
)
SELECT * FROM d;

SELECT is(
    (SELECT (billing_account_id, utility_id, destinatario_soggetto_ruolo_id)::text FROM _dord),
    (SELECT (billing_account_id, utility_id, soggetto_ruolo_id)::text FROM _c WHERE lato = 'A'),
    '17) DDT da ordine senza BA: billing account, utility e destinatario sono quelli dell''ordine');

SELECT throws_like(
    format($q$INSERT INTO vendite.ddt (destinatario_soggetto_ruolo_id, billing_account_id, stato_doc_ddt_id, emittente_fiscale_id, sorgente_tipo_id, sorgente_uid)
              VALUES (%s, %s, %s, %s, %s, %L)$q$,
           (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'B'),
           (SELECT billing_account_id FROM _c WHERE lato = 'B'),
           (SELECT ddt_draft FROM _k), (SELECT ef FROM _k),
           (SELECT src_ordine FROM _k), (SELECT uid FROM _ord)),
    '%il cliente deve essere quello di ordine%',
    '18) DDT dall''ordine di A col BA di B: E_DOC_CLIENTE_DIVERSO_DA_SORGENTE (D-6)');

-- La riga di DDT della bozza di B (trasferimento, BA tolto al test 10: si
-- rimette quello di B) contro la riga d'ordine di A.
UPDATE vendite.ddt SET billing_account_id = (SELECT billing_account_id FROM _c WHERE lato = 'B')
 WHERE id = (SELECT trasf FROM _d);

SELECT throws_like(
    format($q$INSERT INTO vendite.ordini_righe_fulfillment (ordine_riga_id, ddt_riga_id, qta_evasa)
              VALUES (%s, %s, 1)$q$,
           (SELECT r.id FROM vendite.ordini_righe r WHERE r.ordine_id = (SELECT id FROM _ord)),
           (SELECT r.id FROM vendite.ddt_righe r WHERE r.ddt_id = (SELECT trasf FROM _d))),
    '%il cliente deve essere quello di ordine%',
    '19) una riga di DDT di B non evade la riga d''ordine di A');

-- 20) il DDT da ordine (A) evade la riga dell'ordine: poi il BA non cambia
INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, quantita, qta_operativa)
SELECT d.id, 1, k.articolo, 'Riga evasione pgTAP', 1, 1 FROM _dord d, _k k;
INSERT INTO vendite.ordini_righe_fulfillment (ordine_riga_id, ddt_riga_id, qta_evasa)
SELECT (SELECT r.id FROM vendite.ordini_righe r WHERE r.ordine_id = (SELECT id FROM _ord)),
       (SELECT r.id FROM vendite.ddt_righe r WHERE r.ddt_id = (SELECT id FROM _dord)), 1;
UPDATE vendite.ddt SET sorgente_tipo_id = NULL, sorgente_uid = NULL WHERE id = (SELECT id FROM _dord);

SELECT throws_like(
    format('UPDATE vendite.ddt SET billing_account_id = %s WHERE id = %s',
           (SELECT billing_account_id FROM _c WHERE lato = 'B'), (SELECT id FROM _dord)),
    '%il cliente deve essere quello di ordine%',
    '20) in bozza, ma il DDT evade gia'' righe d''ordine: il BA non cambia');

-- 21) il reso dal DDT di A (emesso al test 14, portato a consegnato)
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', (SELECT con_ba FROM _d), 'CONSEGNATO');

SELECT throws_like(
    format($q$INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, destinatario_soggetto_ruolo_id, billing_account_id, emittente_fiscale_id)
              VALUES (%s, %s, %L, %s, %s, %s)$q$,
           (SELECT reso_draft FROM _k), (SELECT src_ddt FROM _k),
           (SELECT uid FROM vendite.ddt WHERE id = (SELECT con_ba FROM _d)),
           (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'B'),
           (SELECT billing_account_id FROM _c WHERE lato = 'B'),
           (SELECT ef FROM _k)),
    '%il cliente deve essere quello di DDT%',
    '21) il reso ha il BA del suo DDT: con un altro, E_DOC_CLIENTE_DIVERSO_DA_SORGENTE (D-3, D-6)');

-- ============================================================
-- IDENTITA'
-- ============================================================
SELECT throws_like(
    format('UPDATE anagrafiche.billing_account SET soggetto_ruolo_id = %s WHERE id = %s',
           (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'B'),
           (SELECT billing_account_id FROM _c WHERE lato = 'A')),
    '%appartiene per sempre alla sua fornitura e al suo cliente%',
    '22) il ruolo di un BA non cambia: parla il lock, prima del guard di coerenza (D-7)');

SELECT throws_like(
    format('UPDATE anagrafiche.istanze_utilities SET soggetto_id = %L WHERE id = %s',
           (SELECT soggetto_id FROM _c WHERE lato = 'B'),
           (SELECT istanza_utility_id FROM _c WHERE lato = 'A')),
    '%appartiene per sempre al suo soggetto%',
    '23) il soggetto di un''istanza non cambia (D-7)');

SELECT is(
    (SELECT array_to_string(ARRAY(SELECT x FROM unnest(dbops.fn_trigger_argomenti(t.tgargs)) WITH ORDINALITY a(x, n)
                                    WHERE n % 2 = 1 ORDER BY x), ',')
       FROM pg_trigger t
      WHERE t.tgrelid = 'anagrafiche.clienti'::regclass
        AND t.tgname = 'trg_clienti_a10_lock_columns_upd'),
    'billing_account_id,istanza_utility_id,soggetto_ruolo_id,utility_id',
    '24) il lock del cliente copre le quattro colonne della fornitura (D-7)');

SELECT throws_like(
    format($q$INSERT INTO anagrafiche.billing_account (istanza_utility_id, soggetto_ruolo_id, utility_id, codice, categoria_cliente_id, valuta_id)
              VALUES (%s, %s, %s, 'PGTAPFO1', (SELECT id FROM anagrafiche.categorie_clienti ORDER BY id LIMIT 1), %s)$q$,
           (SELECT istanza_utility_id FROM _c WHERE lato = 'A'),
           dbops.fn_pgtap_crea_soggetto_ruolo((SELECT soggetto_id FROM _c WHERE lato = 'A'), 'FO'::varchar),
           (SELECT u.id FROM config.utilities u
             WHERE u.id <> (SELECT utility_id FROM _c WHERE lato = 'A') ORDER BY u.id LIMIT 1),
           (SELECT valuta FROM _k)),
    '%soggetti ruoli%',
    '25) un billing account non nasce sul ruolo FORNITORE del soggetto giusto (D-7, BB fn_guard_soggetto_ruolo)');

SELECT is(
    (SELECT string_agg(tgname, ',' ORDER BY tgname) FROM pg_trigger
      WHERE tgrelid = 'anagrafiche.billing_account'::regclass
        AND tgname LIKE 'trg_billing_account_a%_guard_soggetto_coerenza_istanza_ins_upd'),
    'trg_billing_account_a20_guard_soggetto_coerenza_istanza_ins_upd',
    '26) il guard del ruolo del BA sta in fascia _a20_: dopo trg_billing_account_a10_lock_columns_upd');

-- ============================================================
-- PUSH
-- ============================================================
SELECT is(
    (SELECT DISTINCT billing_account_id FROM vendite.fn_ddt_push_diagnosi((SELECT con_ba FROM _d))),
    (SELECT billing_account_id FROM _c WHERE lato = 'A'),
    '27) la diagnosi del push legge il BA dalla testata del DDT');

-- ============================================================
-- EMITTENTE
-- ============================================================
-- ⚠️ Il valore nuovo e' un id che non esiste: il lock (_a05_) parla prima del
--   guard di perimetro e della FK, e il test non dipende da un secondo
--   emittente visibile all'operatore.
SELECT throws_like(
    format('UPDATE vendite.ddt SET emittente_fiscale_id = -1 WHERE id = %s', (SELECT con_ba FROM _d)),
    '%l''azienda che lo emette si sceglie solo in bozza%',
    '28) fuori bozza il DDT non cambia l''azienda che lo emette (E_DOC_EMITTENTE_FUORI_BOZZA)');

DO $s$ BEGIN PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', (SELECT id FROM _ord), 'CONFERMATO'); END $s$;

SELECT throws_like(
    format('UPDATE vendite.ordini SET emittente_fiscale_id = -1 WHERE id = %s', (SELECT id FROM _ord)),
    '%l''azienda che lo emette si sceglie solo in bozza%',
    '29) fuori bozza l''ordine non cambia l''azienda che lo emette');

SELECT is(
    (SELECT string_agg(t.tgname || ':' || ('emittente_fiscale_id' = ANY (dbops.fn_trigger_argomenti(t.tgargs)))::text,
                       ',' ORDER BY t.tgname)
       FROM pg_trigger t
      WHERE t.tgrelid = 'vendite.preventivi'::regclass
        AND t.tgname IN ('trg_preventivi_a05_lock_fuori_bozza_upd', 'trg_preventivi_a10_lock_columns_upd')),
    'trg_preventivi_a05_lock_fuori_bozza_upd:true,trg_preventivi_a10_lock_columns_upd:false',
    '30) preventivo: l''emittente sta nel BB fuori bozza, non piu'' nel lock assoluto (codice dell''operatore)');

-- ============================================================
-- GIRO 2 (brief §10.2 e §10.3, 2026-10-10)
-- ============================================================
SELECT throws_like(
    format($q$INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, utility_id, stato_doc_ordine_id, emittente_fiscale_id, valuta_id)
              VALUES (%s, %s, %s, %s, %s, %s)$q$,
           (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'A'),
           (SELECT billing_account_id FROM _c WHERE lato = 'A'),
           (SELECT u.id FROM config.utilities u
             WHERE u.id <> (SELECT utility_id FROM _c WHERE lato = 'A') ORDER BY u.id LIMIT 1),
           (SELECT ord_draft FROM _k), (SELECT ef FROM _k), (SELECT valuta FROM _k)),
    '%la utility non corrisponde al billing account%',
    '31) ordine con una utility diversa da quella del suo BA: E_DOC_CLIENTE_DIVERSO_DA_BA');

SELECT throws_like(
    format($q$INSERT INTO anagrafiche.clienti (soggetto_ruolo_id, istanza_utility_id, stato_cliente_id, billing_account_id)
              VALUES (%s, %s, (SELECT id FROM config.stati_cliente WHERE codice_interno = 'PR' LIMIT 1), %s)$q$,
           (SELECT soggetto_ruolo_id   FROM _c WHERE lato = 'B'),
           (SELECT istanza_utility_id  FROM _c WHERE lato = 'A'),
           (SELECT billing_account_id  FROM _c WHERE lato = 'A')),
    '%il cliente non corrisponde al billing account%',
    '32) cliente col BA di A e il ruolo di B: E_DOC_CLIENTE_DIVERSO_DA_BA, come ordine e DDT (prima il 23503 della FK)');

SELECT is(
    (SELECT (utility_id IS NULL) AND destinatario_soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'B') FROM _t33),
    true,
    '33) DDT: il BA tolto in bozza toglie la utility (CHECK tutti e due o nessuno) e lascia il destinatario');

-- ⚠️ Le bolle si creano PRIMA e si leggono dopo: una query non vede le righe
--   che inserisce lei stessa (stessa istantanea).
CREATE TEMP TABLE _d34 AS
SELECT ct.codice,
       pg_temp.ddt_bozza(NULL, (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'A'), ct.id) AS id
  FROM config.causali_trasporto ct
 WHERE ct.id IN ((SELECT omaggio FROM _k), (SELECT campionatura FROM _k));

SELECT is(
    (SELECT string_agg(x.codice, ',' ORDER BY x.codice)
       FROM _d34 x
       JOIN vendite.ddt d ON d.id = x.id
      WHERE script.fn_check_ddt_emittibile(d) @> '[{"codice": "E_DDT_CLIENTE_OBBLIGATORIO"}]'),
    'CAMPIONATURA,OMAGGIO',
    '34) omaggio e campionatura senza BA: non si emettono, la causale vuole un cliente (D-2 b)');

-- 35) una bolla di conto lavoro senza BA, portata a consegnata, e il suo reso
CREATE TEMP TABLE _cl AS
SELECT pg_temp.ddt_bozza(NULL, (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'A'),
                         (SELECT conto_lavoro FROM _k)) AS id;
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', (SELECT id FROM _cl), 'CONSEGNATO');

CREATE TEMP TABLE _r35 AS
WITH r AS (
    INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, destinatario_soggetto_ruolo_id, emittente_fiscale_id)
    SELECT k.reso_draft, k.src_ddt, d.uid, d.destinatario_soggetto_ruolo_id, k.ef
      FROM _k k, vendite.ddt d WHERE d.id = (SELECT id FROM _cl)
    RETURNING id, billing_account_id, utility_id
)
SELECT * FROM r;

SELECT is(
    (SELECT (billing_account_id IS NULL AND utility_id IS NULL) FROM _r35),
    true,
    '35) dal DDT di conto lavoro senza BA il reso nasce senza BA: «quello del DDT, NULL compreso» (D-3)');

SELECT throws_like(
    format($q$INSERT INTO vendite.ddt (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, emittente_fiscale_id, sorgente_tipo_id, sorgente_uid)
              VALUES (%s, %s, %s, %s, %L)$q$,
           (SELECT soggetto_ruolo_id FROM _c WHERE lato = 'A'),
           (SELECT ddt_draft FROM _k), (SELECT ef FROM _k),
           (SELECT src_ordine FROM _k), gen_random_uuid()),
    '%il documento da cui nasce (ordine) non esiste o non e'' visibile%',
    '36) DDT che dichiara un ordine che non esiste: E_DOC_SORGENTE_NON_TROVATA (fail-closed)');

SELECT throws_like(
    format('UPDATE vendite.resi SET sorgente_uid = %L WHERE id = %s',
           gen_random_uuid(), (SELECT id FROM _r35)),
    '%il documento da cui nasce (DDT) non esiste o non e'' visibile%',
    '37) reso spostato su un DDT che non esiste: E_DOC_SORGENTE_NON_TROVATA (su UPDATE il guard del consegnato non gira)');

SELECT is(
    (SELECT string_agg(c.relname || ':' || ('emittente_fiscale_id' = ANY (dbops.fn_trigger_argomenti(t.tgargs)))::text,
                       ',' ORDER BY c.relname)
       FROM pg_trigger t
       JOIN pg_class c ON c.oid = t.tgrelid
       JOIN pg_proc p ON p.oid = t.tgfoid
      WHERE p.proname = 'trgfn_doc_testata_lock_fuori_bozza'
        AND t.tgrelid IN ('vendite.offerte_commerciali'::regclass, 'vendite.contratti'::regclass,
                          'vendite.resi'::regclass)),
    'contratti:true,offerte_commerciali:true,resi:true',
    '38) l''emittente fuori bozza e'' nel BB di testata anche su offerte, contratti e resi (§9.8)');

-- 39) un secondo emittente, col suo cliente e il suo ordine; poi si torna
--     all'operatore del primo, che quell'ordine non lo vede.
CREATE TEMP TABLE _m2 AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m2)); END $ctx$;
CREATE TEMP TABLE _c2 AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('esecutivi E2') c;
SET CONSTRAINTS ALL IMMEDIATE;
CREATE TEMP TABLE _ord2 AS
SELECT o.ordine_uid AS uid
  FROM dbops.fn_pgtap_crea_ordine('esecutivi E2', 'DRAFT', (SELECT billing_account_id FROM _c2)) o;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;

SELECT throws_like(
    format($q$INSERT INTO vendite.ddt (destinatario_soggetto_ruolo_id, billing_account_id, stato_doc_ddt_id, emittente_fiscale_id, sorgente_tipo_id, sorgente_uid)
              VALUES (%s, %s, %s, %s, %s, %L)$q$,
           (SELECT soggetto_ruolo_id  FROM _c WHERE lato = 'A'),
           (SELECT billing_account_id FROM _c WHERE lato = 'A'),
           (SELECT ddt_draft FROM _k), (SELECT ef FROM _k),
           (SELECT src_ordine FROM _k), (SELECT uid FROM _ord2)),
    '%il documento da cui nasce (ordine) non esiste o non e'' visibile%',
    '39) DDT di E1 col BA di E1 dall''ordine di E2, invisibile: E_DOC_SORGENTE_NON_TROVATA (rosso da owner, verde come app)');

SELECT * FROM finish();
ROLLBACK;
