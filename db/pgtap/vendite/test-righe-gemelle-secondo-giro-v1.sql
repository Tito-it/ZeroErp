-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-26 (brief-modello-documento-vendita §13, giro 9): lo stato dell'offerta (pg_temp.stato_offerta, prima dell'1 e del 19) dal verbo con dbops.fn_pgtap_porta_a_stato, non con un UPDATE diretto: la porta dell'offerta lo rifiuta. Le attese non cambiano.
-- rev 2026-10-26 (brief-modello-documento-vendita §11): l'attivazione del contratto (prima del 24) passa
--   da dbops.fn_pgtap_porta_a_stato (il verbo del contratto), non da un UPDATE dello stato: la porta lo
--   ferma. Nessuna attesa cambiata.
-- pgTAP test per Zero ERP
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2a, 20261019-40 … -79):
--   il documento passato ai lettori delle testate, ai legami e ai montaggi del
--   lock e' il codice della sorgente (DDT_VENDITA, ORDINE_VENDITA,
--   OFFERTA_COMMERCIALE, RESO_VENDITA). Restano corti i prefissi delle chiavi
--   (G-8), l'origine dei legami (V7) e l'ambito degli indirizzi (G-6).
--
-- Test: righe e componenti di contratto e offerta — secondo giro. Decisione di
--   Tid del 2026-10-04. Brief: brief-db-righe-esclusione-solo-non-si-vende §8
--   (R-DB2-A, R-DB2-B B1-B4). changeSet: 20261005-10…-14 (tipi e NOT NULL),
--   -15…-18 (lock dei nipoti), -19 (revisione) + CSV lista 106 e codici.
--
-- ⭐ TUTTO COSTRUITO: azienda, cliente, listino, articoli e distinta, offerta,
--   revisione e contratto nascono qui (builder dbops.fn_pgtap_crea_*). Dal
--   database si legge solo il seed di catalogo (stati, lista 103).
--
-- LA FIXTURE — P composito con F (obbligatorio, coeff 2) e G (opzionale,
--   coeff 1); X e Y semplici; nessuno nel listino (le righe sono AGGIUNTE).
--   offerta rev1 in BOZZA: X a 999.999.999.999,999999 (il limite di
--   numeric(18,6)), P coi componenti F a 10 (attivo) e G a 5 (SPENTO, un
--   opzionale tolto). rev1 -> EMESSA -> revisione rev2 (rev1 SUPERATA) ->
--   rev2 EMESSA -> ACCETTATA -> push -> contratto DRAFT -> poi ATTIVO.
--
-- ⛔ COSA PRESIDIA:
--   · B2/B4: le due coppie di gemelle hanno gli stessi tipi, e la stessa
--     nullabilita' (anche user_update dei componenti, dal 20261008-31); il prezzo
--     al limite dell'offerta arriva nel contratto;
--   · B1: la revisione porta i componenti (anche lo spento), rimappati, e il
--     push li porta nel contratto;
--   · B3: i componenti fuori bozza sono rifiutati sulle due tabelle, e il
--     rifiuto di stato parla prima dei guard del componente; il lettore
--     riga -> testata e' DEFINER del proprietario delle righe; i rientri del
--     reso non hanno piu' la loro copia della regola;
--   · R-DB2-A: la lista vendite.offerta_righe e' la gemella della 103.
--
-- Indice test (1..31):
--   1) righe: stessi tipi sulle colonne comuni
--   2) componenti: stessi tipi sulle colonne comuni
--   3) righe: stessa nullabilita'
--   4) componenti: stessa nullabilita' (user_update NOT NULL anche sul contratto dal 20261008-31)
--   5) fn_get_testata_id_di_riga: DEFINER del proprietario delle righe, search_path chiuso
--   6) fn_get_testata_id_di_riga: contratto, offerta, riga assente, id non positivo
--   7) fn_get_testata_id_di_riga: tipo sconosciuto -> E_DOC_TIPO_NON_GESTITO
--   8) building block: livello sconosciuto -> E_DOC_RIGHE_LOCK_MONTAGGIO
--   9) nove adottanti a livello RIGA, con gli argomenti giusti (tre dal 20261008-34, i prelievi dal 20261008-93,
--      i due legami della riga di DDT dal 20261011-15)
--  10) su ogni nipote il lock e' il primo BEFORE ROW
--  11) rientri: la copia ritirata, il guard di coerenza in _a10_ su INSERT/UPDATE
--  12) revisione: stessi componenti della rev1 (anche lo spento)
--  13) revisione: i componenti puntano alle eccezioni della rev2, la rev1 li tiene
--  14) revisione: stesso prezzo della madre (dai componenti attivi)
--  15) offerta in BOZZA: un componente si modifica
--  16) offerta SUPERATA: modificare un componente e' rifiutato (frase)
--  17) offerta SUPERATA: spegnere l'obbligatorio -> parla il lock, non l'obbligatorio
--  18) offerta SUPERATA: togliere un componente e' rifiutato
--  19) push: il contratto riceve i componenti della revisione
--  20) push: il prezzo al limite di numeric(18,6) arriva nel contratto
--  21) contratto: attivo NULL rifiutato (23502)
--  22) contratto: meta NULL rifiutato (23502)
--  23) contratto in DRAFT: un componente si modifica
--  24) contratto ATTIVO: modificare un componente e' rifiutato (frase)
--  25) contratto ATTIVO: aggiungere un componente e' rifiutato
--  26) contratto ATTIVO: togliere un componente e' rifiutato
--  27) lista vendite.offerta_righe: stessi attributi della 103
--  28) lista vendite.offerta_righe: stesse colonne della 103
--  29) lista vendite.offerta_righe: preset di default gemello
--  30) lista vendite.offerta_righe: ogni campo_sorgente e' una colonna di fn_offerta_righe_preview
--  31) lista vendite.offerta_righe: intestazioni nel namespace dell'offerta
-- ------------------------------------------------------------

-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): le righe di
--   contratto e offerta stanno nel PERIMETRO dell'articolo. Gli articoli del builder sono
--   MERCE senza tipologia, che ammette UNA_TANTUM: l'erogazione, scritta CANONE per caso,
--   ora e' UNA_TANTUM (stessa fonte FISSA).

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo): il builder del
-- mondo lo riapre poi sul suo operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(31);

-- ============================================================
-- HELPER
-- ============================================================
-- Scopo: esegue uno statement che deve fallire e ne rende SQLSTATE e i due
--   canali strutturati (CONSTRAINT = codice, COLUMN = campo).
CREATE OR REPLACE FUNCTION pg_temp.canali(p_sql text)
RETURNS text LANGUAGE plpgsql AS $fx$
DECLARE v_cst text; v_col text;
BEGIN
    BEGIN
        EXECUTE p_sql;
        RETURN 'NESSUN ERRORE';
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_cst = CONSTRAINT_NAME, v_col = COLUMN_NAME;
        RETURN SQLSTATE || ' / ' || coalesce(nullif(v_cst, ''), '-') || ' / ' || coalesce(nullif(v_col, ''), '-');
    END;
END;
$fx$;

-- Scopo: il rifiuto di un'istruzione su un componente: codice, DA DOVE viene,
--   frase. ⭐ «Da dove» e' il punto: senza la regola sul componente, una sua
--   modifica fuori bozza la ferma comunque il ricalcolo della riga madre
--   (trgfn_componenti_ricalcola_padre, AFTER), il cui UPDATE incontra il lock
--   delle RIGHE — stesso codice, stessa frase. Era l'effetto che il brief
--   chiedeva di sostituire con una regola: il test lo distingue dalla pila.
CREATE OR REPLACE FUNCTION pg_temp.rifiuto(p_sql text)
RETURNS text LANGUAGE plpgsql AS $fx$
DECLARE v_cst text; v_ctx text; v_msg text;
BEGIN
    BEGIN
        EXECUTE p_sql;
        RETURN 'NESSUN ERRORE';
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_cst = CONSTRAINT_NAME, v_ctx = PG_EXCEPTION_CONTEXT, v_msg = MESSAGE_TEXT;
        RETURN coalesce(nullif(v_cst, ''), SQLSTATE) || ' | '
            || CASE WHEN v_ctx LIKE '%trgfn_componenti_ricalcola_padre%' THEN 'dal ricalcolo della madre'
                    ELSE 'dal componente' END
            || ' | ' || v_msg;
    END;
END;
$fx$;

-- Scopo: le colonne di una tabella che la gemella ha diverse, per tipo
--   (p_cosa = 'tipo') o per nullabilita' ('null'). La FK verso il padre ha un
--   nome per tabella e si confronta come PADRE.
CREATE OR REPLACE FUNCTION pg_temp.differenze(p_a regclass, p_b regclass, p_cosa text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  WITH c AS (
    SELECT a.attrelid,
           CASE WHEN a.attname IN ('contratto_id', 'offerta_id',
                                   'riga_contratto_id', 'eccezione_offerta_id')
                THEN 'PADRE' ELSE a.attname END AS col,
           format_type(a.atttypid, a.atttypmod) AS tipo,
           a.attnotnull
      FROM pg_attribute a
     WHERE a.attrelid IN (p_a, p_b) AND a.attnum > 0 AND NOT a.attisdropped
  )
  SELECT coalesce(string_agg(x.col, ',' ORDER BY x.col), '')
    FROM c x JOIN c y ON y.col = x.col AND y.attrelid = p_b
   WHERE x.attrelid = p_a
     AND CASE p_cosa WHEN 'tipo' THEN x.tipo IS DISTINCT FROM y.tipo
                     ELSE x.attnotnull IS DISTINCT FROM y.attnotnull END;
$fx$;

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE tmp_rg2_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('righe gemelle secondo giro');

CREATE TEMP TABLE tmp_rg2_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_rg2_mondo), 'righe gemelle secondo giro');

CREATE TEMP TABLE tmp_rg2_art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGTAP-RG2-' || v.sigla,
                                             p_is_composito => v.sigla = 'P') AS id
  FROM (VALUES ('P'), ('F'), ('G'), ('X'), ('Y')) AS v(sigla);

-- Scopo: id di un articolo della fixture per sigla.
CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
  SELECT id FROM tmp_rg2_art WHERE sigla = p_sigla;
$fx$;

-- Il composito P: F obbligatorio (coeff 2), G opzionale (coeff 1).
INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, obbligatorio, valido_dal)
VALUES (pg_temp.art('P'), pg_temp.art('F'), 2, TRUE,  '2020-01-01'),
       (pg_temp.art('P'), pg_temp.art('G'), 1, FALSE, '2020-01-01');

-- Offerta rev1, in BOZZA.
CREATE TEMP TABLE tmp_rg2_doc (chiave text PRIMARY KEY, id bigint);
WITH o AS (
    INSERT INTO vendite.offerte_commerciali
           (codice, emittente_fiscale_id, billing_account_id, istanza_utility_id,
            utility_id, listino_id, listino_versione_id, validita_dal, validita_al, stato_doc_offerta_id)
    SELECT 'PGTAP-RG2-' || substr(gen_random_uuid()::text, 1, 8),
           m.emittente_fiscale_id, m.billing_account_id, m.istanza_utility_id,
           m.utility_id, l.listino_id, l.listino_versione_id, script.fn_data_operativa(), script.fn_data_operativa() + 365,
           (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'BOZZA')
      FROM tmp_rg2_mondo m, tmp_rg2_listino l
    RETURNING id
)
INSERT INTO tmp_rg2_doc SELECT 'rev1', o.id FROM o;

-- Scopo: id di un documento della fixture.
CREATE OR REPLACE FUNCTION pg_temp.doc(p_chiave text)
RETURNS bigint LANGUAGE sql STABLE AS $fx$
  SELECT id FROM tmp_rg2_doc WHERE chiave = p_chiave;
$fx$;

-- Scopo: porta un'offerta allo stato chiesto (la transizione non e' in esame,
--   come nei test del push e della revisione): dal verbo, con la fixture
--   dbops.fn_pgtap_porta_a_stato (rev 2026-10-26, giro 9: la porta rifiuta
--   l'UPDATE diretto).
CREATE OR REPLACE FUNCTION pg_temp.stato_offerta(p_id bigint, p_stato text)
RETURNS void LANGUAGE sql AS $fx$
  SELECT NULL::void FROM dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', p_id, p_stato);
$fx$;

-- Le due righe della rev1: X al limite della scala, P composito.
INSERT INTO vendite.offerte_commerciali_eccezioni
       (offerta_id, articolo_id, tipo_eccezione, prezzo_unitario, tipo_erogazione,
        fonte_quantita_attesa, quantita, qta_operativa, uom_operativa_id)
SELECT pg_temp.doc('rev1'), a.id, 'AGGIUNTA', v.prezzo, 'UNA_TANTUM', 'FISSA', 1, 1, a.uom_id
  FROM (VALUES ('X', 999999999999.999999::numeric), ('P', 1::numeric)) AS v(sigla, prezzo)
  JOIN catalogo.articoli a ON a.id = pg_temp.art(v.sigla);

-- Scopo: la riga di un articolo su un'offerta o su un contratto.
CREATE OR REPLACE FUNCTION pg_temp.riga_offerta(p_offerta bigint, p_sigla text)
RETURNS bigint LANGUAGE sql STABLE AS $fx$
  SELECT id FROM vendite.offerte_commerciali_eccezioni
   WHERE offerta_id = p_offerta AND articolo_id = pg_temp.art(p_sigla);
$fx$;
CREATE OR REPLACE FUNCTION pg_temp.riga_contratto(p_contratto bigint, p_sigla text)
RETURNS bigint LANGUAGE sql STABLE AS $fx$
  SELECT id FROM vendite.contratti_righe
   WHERE contratto_id = p_contratto AND articolo_id = pg_temp.art(p_sigla);
$fx$;

-- I componenti di P sulla rev1: F a 10 attivo, G a 5 SPENTO (opzionale tolto).
INSERT INTO vendite.offerte_commerciali_eccezioni_componenti
       (eccezione_offerta_id, articolo_componente_id, componente_id, coeff_qta_snapshot,
        quantita, uom_operativa_id, prezzo_unitario, origine_prezzo, ordine, attivo)
SELECT pg_temp.riga_offerta(pg_temp.doc('rev1'), 'P'), ac.id, ac.componente_id, ac.coeff_qta,
       ac.coeff_qta, a.uom_id,
       CASE WHEN ac.componente_id = pg_temp.art('F') THEN 10 ELSE 5 END,
       'MANUALE',
       CASE WHEN ac.componente_id = pg_temp.art('F') THEN 1 ELSE 2 END,
       ac.componente_id = pg_temp.art('F')
  FROM catalogo.articoli_componenti ac
  JOIN catalogo.articoli a ON a.id = ac.componente_id
 WHERE ac.prodotto_id = pg_temp.art('P');

-- Scopo: i componenti di una riga, in una forma confrontabile fra documenti.
CREATE OR REPLACE FUNCTION pg_temp.componenti_offerta(p_riga bigint)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT string_agg(concat_ws(':', a.sigla, trim_scale(c.coeff_qta_snapshot), trim_scale(c.prezzo_unitario),
                              c.attivo, c.origine_prezzo, c.ordine,
                              coalesce(c.stato_approvazione_prezzo::text, '-')), ' ' ORDER BY a.sigla)
    FROM vendite.offerte_commerciali_eccezioni_componenti c
    JOIN tmp_rg2_art a ON a.id = c.componente_id
   WHERE c.eccezione_offerta_id = p_riga;
$fx$;
CREATE OR REPLACE FUNCTION pg_temp.componenti_contratto(p_riga bigint)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT string_agg(concat_ws(':', a.sigla, trim_scale(c.coeff_qta_snapshot), trim_scale(c.prezzo_unitario),
                              c.attivo, c.origine_prezzo, c.ordine,
                              coalesce(c.stato_approvazione_prezzo::text, '-')), ' ' ORDER BY a.sigla)
    FROM vendite.contratti_righe_componenti c
    JOIN tmp_rg2_art a ON a.id = c.componente_id
   WHERE c.riga_contratto_id = p_riga;
$fx$;

-- rev1 emessa, poi la revisione: rev1 diventa SUPERATA, rev2 nasce in BOZZA.
SELECT pg_temp.stato_offerta(pg_temp.doc('rev1'), 'EMESSA');
INSERT INTO tmp_rg2_doc VALUES ('rev2', vendite.fn_crea_revisione_offerta(pg_temp.doc('rev1'), 'pgtap'));

-- ============================================================
-- 1..4 — B2 e B4: le gemelle hanno la stessa forma
-- ============================================================
SELECT is(
    pg_temp.differenze('vendite.contratti_righe', 'vendite.offerte_commerciali_eccezioni', 'tipo'),
    '',
    '1) righe di contratto e offerta: nessuna colonna comune con un tipo diverso');

SELECT is(
    pg_temp.differenze('vendite.contratti_righe_componenti',
                       'vendite.offerte_commerciali_eccezioni_componenti', 'tipo'),
    '',
    '2) componenti di contratto e offerta: nessuna colonna comune con un tipo diverso');

SELECT is(
    pg_temp.differenze('vendite.contratti_righe', 'vendite.offerte_commerciali_eccezioni', 'null'),
    '',
    '3) righe: stessa nullabilita'' (attivo e meta NOT NULL anche sul contratto)');

-- 🔄 rev 2026-10-08: fino al 20261008-31 user_update era NOT NULL sul
--   componente dell'offerta e nullable altrove, e questo test pinnava
--   l'asimmetria come dichiarata. Il 20261008-31 ha allineato la famiglia
--   (linee-guida-sql §7): ora nessuna differenza. Brief:
--   brief-db-righe-e-componenti-le-altre-famiglie §2.3.
SELECT is(
    pg_temp.differenze('vendite.contratti_righe_componenti',
                       'vendite.offerte_commerciali_eccezioni_componenti', 'null'),
    '',
    '4) componenti: stessa nullabilita'' (user_update NOT NULL su entrambi)');

-- ============================================================
-- 5..11 — B3: il lettore, il building block, gli adottanti
-- ============================================================
SELECT ok(
    (SELECT p.prosecdef
            AND p.provolatile = 's'
            AND p.proconfig @> ARRAY['search_path=pg_catalog, public, pg_temp']   -- pg_temp in coda dal 20261005-27 (D6-bis)
            AND (SELECT bool_and(c.relowner = p.proowner) AND count(*) = 6
                   FROM pg_class c
                  WHERE c.oid IN ('vendite.contratti_righe'::regclass,
                                  'vendite.offerte_commerciali_eccezioni'::regclass,
                                  'vendite.resi_righe'::regclass,
                                  -- dal 20261008-33
                                  'vendite.preventivi_righe'::regclass,
                                  'vendite.ordini_righe'::regclass,
                                  'vendite.ddt_righe'::regclass))
       FROM pg_proc p
      WHERE p.oid = 'script.fn_get_testata_id_di_riga(character varying, bigint)'::regprocedure),
    '5) fn_get_testata_id_di_riga: DEFINER del PROPRIETARIO delle sei tabelle di righe, STABLE, search_path chiuso');

SELECT is(
    concat_ws(',',
        script.fn_get_testata_id_di_riga('OFFERTA_COMMERCIALE', pg_temp.riga_offerta(pg_temp.doc('rev1'), 'P'))
            = pg_temp.doc('rev1'),
        script.fn_get_testata_id_di_riga('OFFERTA_COMMERCIALE', -1) IS NULL,
        script.fn_get_testata_id_di_riga('CONTRATTO', 0) IS NULL,
        script.fn_get_testata_id_di_riga('CONTRATTO', 9223372036854775806) IS NULL,
        script.fn_get_testata_id_di_riga('RESO_VENDITA', NULL) IS NULL),
    't,t,t,t,t',
    '6) fn_get_testata_id_di_riga: la testata della riga; NULL per riga assente o id non positivo');

-- 🔄 rev 2026-10-08: l'esempio era 'DDT', che dal 20261008-33 il lettore
--   conosce. Un valore che nessun documento si chiamera' mai.
SELECT is(
    pg_temp.canali($$SELECT script.fn_get_testata_id_di_riga('TIPO_INESISTENTE', 1)$$),
    'P0001 / E_DOC_TIPO_NON_GESTITO / -',
    '7) fn_get_testata_id_di_riga: un tipo fuori elenco e'' un errore di chiamante');

CREATE TEMP TABLE tmp_rg2_nipote (id bigint, riga_id bigint, tx_id uuid);
CREATE TRIGGER trg_tmp_rg2_nipote_lock BEFORE INSERT ON tmp_rg2_nipote
  FOR EACH ROW EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('CONTRATTO', 'riga_id', 'DRAFT', 'NIPOTE');
SELECT is(
    pg_temp.canali($$INSERT INTO tmp_rg2_nipote VALUES (1, 1, NULL)$$),
    'P0001 / E_DOC_RIGHE_LOCK_MONTAGGIO / -',
    '8) building block: un livello che non e'' TESTATA ne'' RIGA e'' un errore di montaggio');

SELECT is(
    (SELECT string_agg(c.relname || ':' || t.tgname || ':'
                       || substring(pg_get_triggerdef(t.oid) FROM 'trgfn_doc_righe_lock_fuori_bozza\((.*)\)$'),
                       ' | ' ORDER BY c.relname)
       FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_proc p ON p.oid = t.tgfoid
      WHERE NOT t.tgisinternal AND p.proname = 'trgfn_doc_righe_lock_fuori_bozza'
        AND pg_get_triggerdef(t.oid) LIKE '%''RIGA''%'),
    'contratti_righe_componenti:trg_contratti_righe_componenti_a05_doc_bozza_ins_upd_dlt:''CONTRATTO'', ''riga_contratto_id'', ''DRAFT'', ''RIGA'''
    ' | ddt_righe_componenti:trg_ddt_righe_componenti_a05_doc_bozza_ins_upd_dlt:''DDT_VENDITA'', ''riga_ddt_id'', ''DRAFT'', ''RIGA'''
    -- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): il settimo, i
    --   prelievi del DDT, con l'eccezione dell'ubicazione d'arrivo (20261008-93).
    ' | ddt_righe_prelievi:trg_ddt_righe_prelievi_a05_doc_bozza_ins_upd_dlt:''DDT_VENDITA'', ''ddt_riga_id'', ''DRAFT'', ''RIGA'', ''ubicazione_arrivo_id'', ''EMESSO,SPEDITO'''
    ' | offerte_commerciali_eccezioni_componenti:trg_oce_comp_a05_doc_bozza_ins_upd_dlt:''OFFERTA_COMMERCIALE'', ''eccezione_offerta_id'', ''BOZZA'', ''RIGA'''
    ' | ordini_righe_componenti:trg_ordini_righe_componenti_a05_doc_bozza_ins_upd_dlt:''ORDINE_VENDITA'', ''riga_ordine_id'', ''DRAFT'', ''RIGA'''
    -- rev 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine, D-4/D-6/D-7, 20261011-15):
    -- i due legami di una riga di DDT con la sua origine.
    ' | ordini_righe_fulfillment:trg_ordini_righe_fulfillment_a05_doc_bozza_ins_upd:''DDT_VENDITA'', ''ddt_riga_id'', ''DRAFT'', ''RIGA'''
    ' | preventivi_righe_componenti:trg_preventivi_righe_componenti_a05_doc_bozza_ins_upd_dlt:''PREVENTIVO'', ''riga_preventivo_id'', ''DRAFT'', ''RIGA'''
    ' | resi_righe_riconsegne:trg_resi_righe_riconsegne_a05_doc_bozza_ins_upd:''DDT_VENDITA'', ''ddt_riga_id'', ''DRAFT'', ''RIGA'''
    ' | resi_righe_rientri:trg_resi_righe_rientri_a05_doc_bozza_ins_upd_dlt:''RESO_VENDITA'', ''resi_riga_id'', ''DRAFT'', ''RIGA''',
    '9) nove adottanti a livello RIGA: componenti di tutti i documenti di vendita, rientri del reso, prelievi del DDT, i due legami della riga di DDT');

-- Fra i BEFORE ROW parla per primo il nome minore: su ogni nipote dev'essere il lock.
SELECT is(
    (SELECT string_agg(x.relname || '=' || x.primo, ' ' ORDER BY x.relname)
       FROM (SELECT c.relname, min(t.tgname) AS primo
               FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
              WHERE NOT t.tgisinternal
                AND (t.tgtype & 2) = 2      -- BEFORE
                AND (t.tgtype & 1) = 1      -- FOR EACH ROW
                AND c.oid IN ('vendite.contratti_righe_componenti'::regclass,
                              'vendite.offerte_commerciali_eccezioni_componenti'::regclass,
                              'vendite.resi_righe_rientri'::regclass,
                              -- dal 20261008-34
                              'vendite.preventivi_righe_componenti'::regclass,
                              'vendite.ordini_righe_componenti'::regclass,
                              'vendite.ddt_righe_componenti'::regclass)
              GROUP BY c.relname) x),
    'contratti_righe_componenti=trg_contratti_righe_componenti_a05_doc_bozza_ins_upd_dlt'
    ' ddt_righe_componenti=trg_ddt_righe_componenti_a05_doc_bozza_ins_upd_dlt'
    ' offerte_commerciali_eccezioni_componenti=trg_oce_comp_a05_doc_bozza_ins_upd_dlt'
    ' ordini_righe_componenti=trg_ordini_righe_componenti_a05_doc_bozza_ins_upd_dlt'
    ' preventivi_righe_componenti=trg_preventivi_righe_componenti_a05_doc_bozza_ins_upd_dlt'
    ' resi_righe_rientri=trg_resi_righe_rientri_a05_doc_bozza_ins_upd_dlt',
    '10) su ogni tabella nipote il rifiuto di stato e'' il primo BEFORE ROW');

SELECT ok(
    (SELECT p.prosrc NOT LIKE '%E_RIGA_DOC_NON_BOZZA%'
            AND p.prosrc NOT LIKE '%fn_get_stato_testata_documento%'
       FROM pg_proc p WHERE p.oid = 'vendite.trgfn_resi_righe_rientri_guard()'::regprocedure)
    AND (SELECT pg_get_triggerdef(t.oid) LIKE '%BEFORE INSERT OR UPDATE ON vendite.resi_righe_rientri%'
           FROM pg_trigger t
          WHERE t.tgrelid = 'vendite.resi_righe_rientri'::regclass
            AND t.tgname = 'trg_resi_righe_rientri_a10_guard_ins_upd')
    AND NOT EXISTS (SELECT 1 FROM pg_trigger t
                     WHERE t.tgrelid = 'vendite.resi_righe_rientri'::regclass
                       AND t.tgname = 'trg_resi_righe_rientri_a05_guard_ins_upd_dlt'),
    '11) rientri: la copia della regola e'' ritirata dal guard, che resta in _a10_ su INSERT/UPDATE');

-- ============================================================
-- 12..18 — B1 (la revisione) e B3 sull'offerta
-- ============================================================
SELECT is(
    pg_temp.componenti_offerta(pg_temp.riga_offerta(pg_temp.doc('rev2'), 'P')),
    pg_temp.componenti_offerta(pg_temp.riga_offerta(pg_temp.doc('rev1'), 'P')),
    '12) revisione: gli stessi componenti della rev1, anche l''opzionale spento');

SELECT is(
    (SELECT string_agg(d.chiave || '=' || n, ' ' ORDER BY d.chiave)
       FROM tmp_rg2_doc d
       CROSS JOIN LATERAL (
           SELECT count(*) AS n
             FROM vendite.offerte_commerciali_eccezioni_componenti c
             JOIN vendite.offerte_commerciali_eccezioni e ON e.id = c.eccezione_offerta_id
            WHERE e.offerta_id = d.id) x
      WHERE d.chiave IN ('rev1', 'rev2')),
    'rev1=2 rev2=2',
    '13) revisione: due componenti sotto le eccezioni della rev2, e la rev1 tiene i suoi');

SELECT is(
    (SELECT string_agg(trim_scale(e.prezzo_unitario)::text, ',' ORDER BY e.offerta_id)
       FROM vendite.offerte_commerciali_eccezioni e
      WHERE e.offerta_id IN (pg_temp.doc('rev1'), pg_temp.doc('rev2'))
        AND e.articolo_id = pg_temp.art('P')),
    '20,20',
    '14) revisione: la madre ha lo stesso prezzo, ricalcolato dai componenti attivi (F 10 x 2)');

SELECT lives_ok(
    format($$UPDATE vendite.offerte_commerciali_eccezioni_componenti SET meta = '{"pgtap": 1}'
              WHERE eccezione_offerta_id = %s AND componente_id = %L$$,
           pg_temp.riga_offerta(pg_temp.doc('rev2'), 'P'), pg_temp.art('G')),
    '15) offerta in BOZZA (la revisione): un componente si modifica');

SELECT alike(
    pg_temp.rifiuto(format($$UPDATE vendite.offerte_commerciali_eccezioni_componenti SET ordine = 3
                             WHERE eccezione_offerta_id = %s AND componente_id = %L$$,
                          pg_temp.riga_offerta(pg_temp.doc('rev1'), 'P'), pg_temp.art('G'))),
    'E_RIGA_DOC_NON_BOZZA | dal componente | Offerta % non e'' piu'' in bozza (stato SUPERATA): le sue righe si possono modificare%',
    '16) offerta SUPERATA: modificare un componente e'' rifiutato, col nome dell''offerta');

-- ⭐ Spegnere l'obbligatorio F lo rifiuterebbe anche il suo guard
--   (E_DOC_COMPONENTE_OBBLIGATORIO): deve parlare prima lo stato.
SELECT is(
    pg_temp.canali(format($$UPDATE vendite.offerte_commerciali_eccezioni_componenti SET attivo = false
                             WHERE eccezione_offerta_id = %s AND componente_id = %L$$,
                          pg_temp.riga_offerta(pg_temp.doc('rev1'), 'P'), pg_temp.art('F'))),
    'P0001 / E_RIGA_DOC_NON_BOZZA / -',
    '17) offerta SUPERATA: spegnere l''obbligatorio -> parla il rifiuto di stato, non il guard dell''obbligatorio');

SELECT alike(
    pg_temp.rifiuto(format($$DELETE FROM vendite.offerte_commerciali_eccezioni_componenti
                             WHERE eccezione_offerta_id = %s AND componente_id = %L$$,
                          pg_temp.riga_offerta(pg_temp.doc('rev1'), 'P'), pg_temp.art('G'))),
    'E_RIGA_DOC_NON_BOZZA | dal componente | %togliere%',
    '18) offerta SUPERATA: togliere un componente e'' rifiutato');

-- ============================================================
-- 19..26 — il push, B2 al limite, B4, B3 sul contratto
-- ============================================================
SELECT pg_temp.stato_offerta(pg_temp.doc('rev2'), 'EMESSA');
SELECT pg_temp.stato_offerta(pg_temp.doc('rev2'), 'ACCETTATA');
CREATE TEMP TABLE tmp_rg2_push AS
SELECT vendite.fn_push_offerta_a_contratto(pg_temp.doc('rev2'), NULL::bigint, false) AS esito;
INSERT INTO tmp_rg2_doc
SELECT 'contratto', c.id FROM vendite.contratti c WHERE c.offerta_id = pg_temp.doc('rev2');

SELECT is(
    pg_temp.componenti_contratto(pg_temp.riga_contratto(pg_temp.doc('contratto'), 'P')),
    -- ⚠️ contro la rev1, non la rev2: senza la copia la rev2 non ha componenti, e
    --   NULL = NULL passerebbe a vuoto.
    pg_temp.componenti_offerta(pg_temp.riga_offerta(pg_temp.doc('rev1'), 'P')),
    '19) push: il contratto riceve i componenti della revisione (prima la revisione non li aveva)');

SELECT is(
    (SELECT r.prezzo_unitario FROM vendite.contratti_righe r
      WHERE r.id = pg_temp.riga_contratto(pg_temp.doc('contratto'), 'X')),
    999999999999.999999::numeric,
    '20) push: il prezzo al limite di numeric(18,6) passa dall''offerta al contratto');

-- B4: con il contratto ancora in DRAFT (il lock parlerebbe prima del NOT NULL).
SELECT is(
    pg_temp.canali(format($$INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione,
                              prezzo_unitario, tipo_erogazione, fonte_quantita_attesa, qta_operativa, attivo)
                            VALUES (%s, %L, 'AGGIUNTA', 1, 'UNA_TANTUM', 'FISSA', 1, NULL)$$,
                          pg_temp.doc('contratto'), pg_temp.art('Y'))),
    '23502 / - / attivo',
    '21) contratto: una riga con attivo NULL e'' rifiutata (NOT NULL, come sull''offerta)');

SELECT is(
    pg_temp.canali(format($$INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione,
                              prezzo_unitario, tipo_erogazione, fonte_quantita_attesa, qta_operativa, meta)
                            VALUES (%s, %L, 'AGGIUNTA', 1, 'UNA_TANTUM', 'FISSA', 1, NULL)$$,
                          pg_temp.doc('contratto'), pg_temp.art('Y'))),
    '23502 / - / meta',
    '22) contratto: una riga con meta NULL e'' rifiutata');

SELECT lives_ok(
    format($$UPDATE vendite.contratti_righe_componenti SET meta = '{"pgtap": 1}'
              WHERE riga_contratto_id = %s AND componente_id = %L$$,
           pg_temp.riga_contratto(pg_temp.doc('contratto'), 'P'), pg_temp.art('G')),
    '23) contratto in DRAFT: un componente si modifica');

-- rev 2026-10-26 (brief-modello-documento-vendita §11): l'attivazione dal verbo
--   (la porta ferma l'UPDATE diretto dello stato).
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, pg_temp.doc('contratto'), 'ATTIVO');

SELECT alike(
    pg_temp.rifiuto(format($$UPDATE vendite.contratti_righe_componenti SET ordine = 5
                             WHERE riga_contratto_id = %s AND componente_id = %L$$,
                          pg_temp.riga_contratto(pg_temp.doc('contratto'), 'P'), pg_temp.art('G'))),
    'E_RIGA_DOC_NON_BOZZA | dal componente | Contratto % non e'' piu'' in bozza (stato ATTIVO): le sue righe si possono modificare%',
    '24) contratto ATTIVO: modificare un componente e'' rifiutato, col nome del contratto');

SELECT is(
    pg_temp.canali(format($$INSERT INTO vendite.contratti_righe_componenti
                              (riga_contratto_id, articolo_componente_id, componente_id, coeff_qta_snapshot,
                               quantita, uom_operativa_id, prezzo_unitario, origine_prezzo)
                            SELECT %s, ac.id, ac.componente_id, 1, 1, a.uom_id, 1, 'MANUALE'
                              FROM catalogo.articoli_componenti ac JOIN catalogo.articoli a ON a.id = ac.componente_id
                             WHERE ac.prodotto_id = %L AND ac.componente_id = %L$$,
                          pg_temp.riga_contratto(pg_temp.doc('contratto'), 'X'),
                          pg_temp.art('P'), pg_temp.art('G'))),
    'P0001 / E_RIGA_DOC_NON_BOZZA / -',
    '25) contratto ATTIVO: aggiungere un componente e'' rifiutato');

SELECT alike(
    pg_temp.rifiuto(format($$DELETE FROM vendite.contratti_righe_componenti
                             WHERE riga_contratto_id = %s AND componente_id = %L$$,
                          pg_temp.riga_contratto(pg_temp.doc('contratto'), 'P'), pg_temp.art('G'))),
    'E_RIGA_DOC_NON_BOZZA | dal componente | %togliere%',
    '26) contratto ATTIVO: togliere un componente e'' rifiutato');

-- ============================================================
-- 27..31 — R-DB2-A: la lista configurabile delle righe dell'offerta
-- ============================================================
SELECT is(
    (SELECT concat_ws(',', d.schema_dati, coalesce(d.vista_sql, '<null>'), d.attivo, d.multi_emittente,
                      d.perimetro_emittente, d.ricerca_min_caratteri)
       FROM ui.lista_definizione d WHERE d.codice = 'vendite.offerta_righe'),
    (SELECT concat_ws(',', d.schema_dati, coalesce(d.vista_sql, '<null>'), d.attivo, d.multi_emittente,
                      d.perimetro_emittente, d.ricerca_min_caratteri)
       FROM ui.lista_definizione d WHERE d.codice = 'vendite.contratto_righe'),
    '27) vendite.offerta_righe: stessi attributi di vendite.contratto_righe (sorgente funzione, perimetro, soglia)');

-- Scopo: le colonne di una lista, senza le etichette (le intestazioni sono del documento).
CREATE OR REPLACE FUNCTION pg_temp.colonne_lista(p_codice text)
RETURNS SETOF text LANGUAGE sql STABLE AS $fx$
  SELECT concat_ws('|', c.codice, coalesce(c.campo_sorgente, ''), c.tipo_colonna, c.tipo_dato,
                   coalesce(c.formato, ''), coalesce(c.larghezza_default::text, ''), c.ordine_default,
                   c.allineamento, coalesce(c.gruppo_ordine::text, ''), c.filtrabile, c.ordinabile,
                   c.esportabile, c.ricercabile_full, c.sensibile, c.attivo, c.priorita)
    FROM ui.lista_colonna c JOIN ui.lista_definizione d ON d.id = c.lista_id
   WHERE d.codice = p_codice;
$fx$;

SELECT set_eq(
    $$SELECT * FROM pg_temp.colonne_lista('vendite.offerta_righe')$$,
    $$SELECT * FROM pg_temp.colonne_lista('vendite.contratto_righe')$$,
    '28) vendite.offerta_righe: stesse colonne della 103, stesso ordine, stessi flag');

SELECT set_eq(
    $$SELECT concat_ws('|', p.is_default, p.ambito, p.pagina_dimensione, coalesce(p.ordinamento_default::text, ''),
                       c.codice, pc.ordine, pc.visibile, pc.fissata)
        FROM ui.lista_preset p JOIN ui.lista_definizione d ON d.id = p.lista_id
        JOIN ui.lista_preset_colonna pc ON pc.preset_id = p.id
        JOIN ui.lista_colonna c ON c.id = pc.colonna_id
       WHERE d.codice = 'vendite.offerta_righe' AND p.is_default$$,
    $$SELECT concat_ws('|', p.is_default, p.ambito, p.pagina_dimensione, coalesce(p.ordinamento_default::text, ''),
                       c.codice, pc.ordine, pc.visibile, pc.fissata)
        FROM ui.lista_preset p JOIN ui.lista_definizione d ON d.id = p.lista_id
        JOIN ui.lista_preset_colonna pc ON pc.preset_id = p.id
        JOIN ui.lista_colonna c ON c.id = pc.colonna_id
       WHERE d.codice = 'vendite.contratto_righe' AND p.is_default$$,
    '29) vendite.offerta_righe: il preset di default e'' il gemello di quello della 103');

-- ⚠️ Il campo vuoto delle colonne azione e' '' (loader), non NULL: si escludono
--   come le esclude il guard del catalogo.
SELECT is(
    (SELECT coalesce(string_agg(c.campo_sorgente, ',' ORDER BY c.campo_sorgente), '')
       FROM ui.lista_colonna c JOIN ui.lista_definizione d ON d.id = c.lista_id
      WHERE d.codice = 'vendite.offerta_righe'
        AND c.tipo_colonna <> 'azione' AND coalesce(btrim(c.campo_sorgente), '') <> ''
        AND c.campo_sorgente NOT IN (
            SELECT u.nome
              FROM pg_proc p,
                   unnest(p.proargnames, p.proargmodes) AS u(nome, modo)
             WHERE p.oid = 'vendite.fn_offerta_righe_preview(bigint)'::regprocedure
               AND u.modo = 't')),
    '',
    '30) vendite.offerta_righe: ogni campo_sorgente e'' una colonna di vendite.fn_offerta_righe_preview');

SELECT is(
    (SELECT coalesce(string_agg(c.codice || '=' || c.etichetta_i18n_key, ',' ORDER BY c.codice), '')
       FROM ui.lista_colonna c JOIN ui.lista_definizione d ON d.id = c.lista_id
      WHERE d.codice = 'vendite.offerta_righe'
        AND c.etichetta_i18n_key NOT LIKE 'vendite.offerte.col\_%'
        AND c.etichetta_i18n_key <> 'common.col_azioni'),
    '',
    '31) vendite.offerta_righe: le intestazioni stanno nel namespace dell''offerta');

SELECT * FROM finish();
ROLLBACK;
