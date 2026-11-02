-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- rev 2026-10-29 (brief-db-contratto-righe-periodiche-in-commessa §6.10, G-0-ter; 20261029-39): la riga
--   di listino ha anche l'azione ADERISCI (test 21).
-- rev 2026-10-29 (brief-db-contratto-righe-periodiche-in-commessa §6.8, G-8 di Tid; 20261029-26/-27):
--   competenza_canone ritirata dalle righe: i campi dell'esclusione sono nove (test 1, 2, 6, 11).
-- rev 2026-10-28 (brief-modello-documento-vendita §16, giro 12): la versione di oggi nasce in bozza
--   senza stato e si attiva dal verbo (dbops.fn_pgtap_porta_a_stato), non con un UPDATE dello stato.
--
-- Test: righe di contratto e di offerta — l'esclusione e' solo «non si vende»,
--   e le due tabelle obbediscono alle stesse regole. Decisione di Tid del
--   2026-10-04. Brief: brief-db-righe-esclusione-solo-non-si-vende (R1-R5, R8,
--   R9). changeSet: 20261004-40 e -76 (CHECK, bonifica), -41…-47 (funzioni), -48/-49 (trigger),
--   -70…-75 (lista, ritiri, commenti) + CSV codici e lock.
--   ⚠️ rev 2026-10-19 (20261019-20, brief-db-grammatica-unica-documenti lotto 1):
--   il documento dell'offerta e' OFFERTA_COMMERCIALE (test 25).
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): l'offerta EMESSA nasce
--   in bozza e si porta avanti con dbops.fn_pgtap_porta_a_stato (prima nasceva
--   gia' EMESSA).
--
-- ⭐ TUTTO COSTRUITO: azienda, cliente, listino con un bundle, articoli,
--   contratto, offerte e righe nascono qui (builder dbops.fn_pgtap_crea_*).
--   Nessuna riga letta dal database: vale anche su un DB ricostruito da zero.
--
-- LA FIXTURE — un listino con A, B, C, F standalone e il bundle P (figlio F);
--   X fuori listino. Sullo stesso listino:
--   contratto in DRAFT: B OVERRIDE, C ESCLUSIONE, X AGGIUNTA
--   offerta in BOZZA:   B OVERRIDE, C ESCLUSIONE, X AGGIUNTA
--   offerta EMESSA (emessa senza righe): per il rifiuto «fuori bozza»
--
-- ⛔ COSA PRESIDIA:
--   · R1: le due tabelle vietano i dati di vendita sull'esclusione (CHECK) e la
--     fonte non e' piu' NOT NULL; il guard rifiuta col codice e col CAMPO;
--   · R2: l'esclusione vuota nasce vuota (i trigger di valorizzazione la
--     saltano), le altre righe ricevono ancora la fonte di default;
--   · R3: l'UPDATE di un'esclusione dell'offerta e' rifiutato;
--   · R4: la lista dell'offerta da' i verbi del DB, come quella del contratto,
--     e la lista del contratto e' identica al corpo comune;
--   · R5: le quattro regole del contratto ora valgono sull'offerta (fuori
--     bozza, aggiunta fuori listino, esclusione del figlio di bundle, lock su
--     tipo_eccezione).
--
-- Indice test (1..26):
--    1) contratto: CHECK sui nove campi dell'esclusione
--    2) offerta: lo stesso CHECK
--    3) fonte nullable sulle due tabelle, obbligatoria per CHECK sulle altre righe
--    4) offerta: i cinque trigger nuovi montati sulle funzioni giuste
--    5) contratto: i tre guard sulle funzioni generiche, le quattro vecchie ritirate
--    6) contratto: ESCLUSIONE vuota accettata, e resta vuota (nessun trigger la riempie)
--    7) contratto: ESCLUSIONE con quantita' rifiutata (frase)
--    8) contratto: canali = codice / quantita
--    9) contratto: ESCLUSIONE con la sola erogazione: campo tipo_erogazione
--   10) contratto: un OVERRIDE senza fonte riceve ancora FISSA (R2, WHEN)
--   11) offerta: ESCLUSIONE vuota accettata, e resta vuota
--   12) offerta: ESCLUSIONE con prezzo rifiutata: canali = codice / prezzo_unitario
--   13) offerta: UPDATE di un'esclusione rifiutato (frase)
--   14) offerta: UPDATE di un'esclusione senza cambi passa
--   15) offerta: DELETE di un'esclusione (Ripristina articolo) passa
--   16) offerta EMESSA: aggiungere una riga e' rifiutato (fuori bozza)
--   17) offerta: AGGIUNTA di un articolo del listino rifiutata, col documento
--   18) offerta: ESCLUSIONE del figlio di bundle rifiutata
--   19) offerta: il registro dei lock dichiara tipo_eccezione
--   20) offerta: il lock generato rifiuta il cambio di tipo (skip prima di ci_apply)
--   21) lista dell'offerta: verbi per origine
--   22) lista dell'offerta: «Escludi» spento su F con FIGLIO_DI_BUNDLE
--   23) lista dell'offerta: chiavi uniche, sei righe
--   24) lista del contratto = corpo comune (stesse righe, nei due sensi)
--   25) la check generica sull'offerta: codice, reason, reason_key
--   26) fn_offerta_righe_espanse: l'esclusione resta tolta, B col prezzo forzato
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo): il builder del
-- mondo lo riapre poi sul suo operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(26);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE tmp_rsv_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('esclusione solo non si vende');

-- ⚠️ La versione del builder nasce ATTIVA, e i componenti di un bundle non si
--    scrivono su una versione ATTIVA. La si fa finire nel 2020, e la versione
--    che copre OGGI si costruisce qui: BOZZA, righe, poi ATTIVA.
CREATE TEMP TABLE tmp_rsv_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_rsv_mondo), 'esclusione solo non si vende',
    '2020-01-01'::date, '2020-12-31'::date);

CREATE TEMP TABLE tmp_rsv_ver AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
    SELECT listino_id, 'PGTAP_RSV_V2', '2021-01-01'::date FROM tmp_rsv_listino
    RETURNING id
)
SELECT id FROM ins;

-- Tutti della tipologia del listino; P nasce composito (il bundle).
CREATE TEMP TABLE tmp_rsv_art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGTAP-RSV-' || v.sigla,
           p_listino_tipologia_id => (SELECT tipologia_id FROM tmp_rsv_listino),
           p_is_composito         => v.sigla = 'P') AS id
  FROM (VALUES ('A'), ('B'), ('C'), ('F'), ('P'), ('X')) AS v(sigla);

-- Scopo: id di un articolo della fixture per sigla.
CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
  SELECT id FROM tmp_rsv_art WHERE sigla = p_sigla;
$fx$;

-- Il bundle: P, con F come componente in distinta.
INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)
VALUES (pg_temp.art('P'), pg_temp.art('F'), 1, '2020-01-01');

INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT (SELECT id FROM tmp_rsv_ver), a.id, ar.uom_id, 100.00
  FROM tmp_rsv_art a JOIN catalogo.articoli ar ON ar.id = a.id
 WHERE a.sigla IN ('A', 'B', 'C', 'F');

INSERT INTO vendite.listini_righe_componenti (listino_versione_id, articolo_componente_id,
       articolo_padre_id, articolo_figlio_id, prezzo, valido_dal)
SELECT (SELECT id FROM tmp_rsv_ver), ac.id,
       pg_temp.art('P'), pg_temp.art('F'), 50.00, '2021-01-01'
  FROM catalogo.articoli_componenti ac
 WHERE ac.prodotto_id = pg_temp.art('P') AND ac.componente_id = pg_temp.art('F');

SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni', (SELECT id FROM tmp_rsv_ver), 'ATTIVA');

CREATE TEMP TABLE tmp_rsv_contratto AS
WITH ins AS (
    INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,
           stato_doc_contratto_id, listino_id, valido_dal, valido_al)
    SELECT 'PGTAP-RSV-' || substr(gen_random_uuid()::text, 1, 8),
           m.billing_account_id, m.istanza_utility_id, m.utility_id,
           (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),
           (SELECT listino_id FROM tmp_rsv_listino),
           script.fn_data_operativa(), script.fn_data_operativa() + 365
      FROM tmp_rsv_mondo m
    RETURNING id
)
SELECT id FROM ins;

-- Due offerte sullo stesso listino: una in BOZZA (le righe), una EMESSA senza
-- righe (per il rifiuto «fuori bozza»).
-- ⛔ rev 2026-10-24 (brief-modello-documento-vendita N-1): l'EMESSA nasceva cosi'
--   con un INSERT, senza passare dalla transizione. Ora nascono entrambe in
--   BOZZA (trg_offerte_commerciali_a05_stato_iniziale_ins) e l'EMESSA ci arriva
--   per la matrice, sotto il guard di emissione (senza righe non ha niente da
--   rifiutare). La colonna stato e' lo stato VOLUTO, che fa da etichetta.
CREATE TEMP TABLE tmp_rsv_offerta (id bigint, stato text);

WITH ins AS (
    INSERT INTO vendite.offerte_commerciali
           (codice, emittente_fiscale_id, billing_account_id, istanza_utility_id,
            utility_id, listino_id, validita_dal)
    SELECT 'PGTAP-RSV-O-BOZZA-' || substr(gen_random_uuid()::text, 1, 8),
           m.emittente_fiscale_id, m.billing_account_id, m.istanza_utility_id,
           m.utility_id, l.listino_id, script.fn_data_operativa()
      FROM tmp_rsv_mondo m, tmp_rsv_listino l
    RETURNING id
)
INSERT INTO tmp_rsv_offerta SELECT id, 'BOZZA' FROM ins;

WITH ins AS (
    INSERT INTO vendite.offerte_commerciali
           (codice, emittente_fiscale_id, billing_account_id, istanza_utility_id,
            utility_id, listino_id, validita_dal)
    SELECT 'PGTAP-RSV-O-EMESSA-' || substr(gen_random_uuid()::text, 1, 8),
           m.emittente_fiscale_id, m.billing_account_id, m.istanza_utility_id,
           m.utility_id, l.listino_id, script.fn_data_operativa()
      FROM tmp_rsv_mondo m, tmp_rsv_listino l
    RETURNING id
)
INSERT INTO tmp_rsv_offerta SELECT id, 'EMESSA' FROM ins;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', o.id, o.stato)
  FROM tmp_rsv_offerta o
 WHERE o.stato = 'EMESSA';

-- Scopo: id del documento: 'contratto', 'offerta' (BOZZA), 'emessa'.
CREATE OR REPLACE FUNCTION pg_temp.doc(p_doc text)
RETURNS bigint LANGUAGE sql STABLE AS $fx$
  SELECT CASE p_doc
           WHEN 'contratto' THEN (SELECT id FROM tmp_rsv_contratto)
           WHEN 'offerta'   THEN (SELECT id FROM tmp_rsv_offerta WHERE stato = 'BOZZA')
           WHEN 'emessa'    THEN (SELECT id FROM tmp_rsv_offerta WHERE stato = 'EMESSA')
         END;
$fx$;

-- Scopo: la quantita' di una riga che eredita dall'articolo: 1 se la fonte di
--   default la porta (FISSA), altrimenti vuota (fonte a valle). Rev 2026-10-07,
--   brief-db-offerta-emissione-ed-erogazione §D.4 punto 2 (20261007-28/-30).
CREATE OR REPLACE FUNCTION pg_temp.qta(p_articolo uuid)
RETURNS numeric LANGUAGE sql STABLE AS $fx$
  SELECT 1::numeric FROM vendite.fn_articolo_erogazioni(p_articolo) e
   WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA';
$fx$;

-- Scopo: l'INSERT di una riga, come testo da eseguire o da dare a throws_like.
--   p_doc: 'contratto' | 'offerta' | 'emessa'. Una ESCLUSIONE nasce VUOTA (la
--   regola), le altre coi dati di una riga che si fattura. p_extra: una
--   colonna in piu' da valorizzare sull'esclusione ('col=valore'), per i rifiuti.
CREATE OR REPLACE FUNCTION pg_temp.ins(p_doc text, p_sigla text, p_tipo text,
                                       p_extra_col text DEFAULT NULL,
                                       p_extra_val text DEFAULT NULL)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT CASE
    WHEN p_tipo = 'ESCLUSIONE' THEN format(
      $$INSERT INTO vendite.%I (%I, articolo_id, tipo_eccezione%s)
        VALUES (%s, %L, 'ESCLUSIONE'%s)$$,
      CASE p_doc WHEN 'contratto' THEN 'contratti_righe' ELSE 'offerte_commerciali_eccezioni' END,
      CASE p_doc WHEN 'contratto' THEN 'contratto_id' ELSE 'offerta_id' END,
      COALESCE(', ' || quote_ident(p_extra_col), ''),
      pg_temp.doc(p_doc), pg_temp.art(p_sigla),
      COALESCE(', ' || quote_literal(p_extra_val), ''))
    ELSE format(
      $$INSERT INTO vendite.%I (%I, articolo_id, tipo_eccezione, prezzo_unitario,
               tipo_erogazione, fonte_quantita_attesa, quantita, qta_operativa, uom_operativa_id)
        SELECT %s, a.id, %L, 80.00, NULL, NULL, pg_temp.qta(a.id), pg_temp.qta(a.id), a.uom_id
          FROM catalogo.articoli a WHERE a.id = %L$$,
      CASE p_doc WHEN 'contratto' THEN 'contratti_righe' ELSE 'offerte_commerciali_eccezioni' END,
      CASE p_doc WHEN 'contratto' THEN 'contratto_id' ELSE 'offerta_id' END,
      pg_temp.doc(p_doc), p_tipo, pg_temp.art(p_sigla))
  END;
$fx$;

-- Scopo: esegue uno statement che un guard deve rifiutare e ne rende i due
--   canali strutturati (CONSTRAINT = codice, COLUMN = campo): throws_like legge
--   solo la frase.
CREATE OR REPLACE FUNCTION pg_temp.canali(p_sql text)
RETURNS text LANGUAGE plpgsql AS $fx$
DECLARE v_cst text; v_col text;
BEGIN
    BEGIN
        EXECUTE p_sql;
        RETURN 'NESSUN ERRORE';
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_cst = CONSTRAINT_NAME, v_col = COLUMN_NAME;
        RETURN coalesce(nullif(v_cst, ''), '-') || ' / ' || coalesce(nullif(v_col, ''), '-');
    END;
END;
$fx$;

-- Scopo: esegue un testo SQL (per costruire le righe della fixture).
CREATE OR REPLACE FUNCTION pg_temp.esegui(p_sql text)
RETURNS void LANGUAGE plpgsql AS $fx$ BEGIN EXECUTE p_sql; END; $fx$;

-- Le righe della fixture, sui due documenti in bozza.
SELECT pg_temp.esegui(pg_temp.ins(d, s, t))
  FROM (VALUES ('B', 'OVERRIDE'), ('X', 'AGGIUNTA')) AS r(s, t),
       (VALUES ('contratto'), ('offerta')) AS dd(d);

-- ============================================================
-- 1..5 — la regola nella struttura, e i trigger montati
-- ============================================================
-- ⭐ Le colonne del CHECK lette da conkey, non dal testo deparsato: nove campi
--   di vendita piu' tipo_eccezione, ne' uno di piu' ne' uno di meno.
CREATE OR REPLACE FUNCTION pg_temp.colonne_check(p_tab regclass, p_nome text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT string_agg(a.attname, ',' ORDER BY a.attname)
    FROM pg_constraint c
    JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
   WHERE c.conrelid = p_tab AND c.conname = p_nome AND c.contype = 'c';
$fx$;

SELECT is(
    pg_temp.colonne_check('vendite.contratti_righe', 'chk_contrighe_esclusione_senza_dati'),
    'factor_to_base,fonte_quantita_attesa,generazione_canone,periodicita,'
    'prezzo_unitario,qta_operativa,quantita,tipo_eccezione,tipo_erogazione,uom_operativa_id',
    '1) contratto: il CHECK dell''esclusione copre i nove campi di vendita');

SELECT is(
    pg_temp.colonne_check('vendite.offerte_commerciali_eccezioni', 'chk_offerte_eccezioni_esclusione_senza_dati'),
    'factor_to_base,fonte_quantita_attesa,generazione_canone,periodicita,'
    'prezzo_unitario,qta_operativa,quantita,tipo_eccezione,tipo_erogazione,uom_operativa_id',
    '2) offerta: lo stesso CHECK');

SELECT ok(
    (SELECT bool_and(NOT a.attnotnull) AND count(*) = 2
       FROM pg_attribute a
      WHERE a.attname = 'fonte_quantita_attesa'
        AND a.attrelid IN ('vendite.contratti_righe'::regclass,
                           'vendite.offerte_commerciali_eccezioni'::regclass))
    AND pg_temp.colonne_check('vendite.contratti_righe', 'chk_contrighe_fonte_per_tipo_eccezione')
        = 'fonte_quantita_attesa,tipo_eccezione'
    AND pg_temp.colonne_check('vendite.offerte_commerciali_eccezioni',
                              'chk_offerte_eccezioni_fonte_per_tipo_eccezione')
        = 'fonte_quantita_attesa,tipo_eccezione',
    '3) fonte nullable sulle due tabelle, obbligatoria per CHECK sulle righe che non sono esclusioni');

-- ⛔ rev 2026-10-13 (brief-db-articoli-ammessi-per-documento, Lotto 3b): i guard
--   «aggiunta fuori listino» ed «esclusione figlio di bundle» sono ritirati
--   (20261013-57); le loro regole sono motivi di script.fn_check_articolo_riga,
--   che solleva il guard di tabella script.trgfn_righe_guard_articolo_ammesso.
SELECT is(
    (SELECT string_agg(t.tgname || '>' || p.proname, ' ' ORDER BY t.tgname)
       FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
      WHERE t.tgrelid = 'vendite.offerte_commerciali_eccezioni'::regclass
        AND t.tgname IN ('trg_offerte_commerciali_eccezioni_a05_doc_bozza_ins_upd_dlt',
                         'trg_offerte_commerciali_eccezioni_a05_guard_escl_immut_upd',
                         'trg_offerte_eccezioni_a10_guard_articolo_ammesso_ins_upd',
                         'trg_offerte_eccezioni_a10_guard_esclusione_senza_dati_ins')),
    'trg_offerte_commerciali_eccezioni_a05_doc_bozza_ins_upd_dlt>trgfn_doc_righe_lock_fuori_bozza '
    'trg_offerte_commerciali_eccezioni_a05_guard_escl_immut_upd>trgfn_righe_guard_esclusione_immutabile '
    'trg_offerte_eccezioni_a10_guard_articolo_ammesso_ins_upd>trgfn_righe_guard_articolo_ammesso '
    'trg_offerte_eccezioni_a10_guard_esclusione_senza_dati_ins>trgfn_righe_guard_esclusione_senza_dati',
    '4) offerta: i quattro trigger, ciascuno sulla sua funzione (dal Lotto 3b il guard di articolo)');

SELECT ok(
    (SELECT count(*) = 3
       FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE t.tgrelid = 'vendite.contratti_righe'::regclass
        AND n.nspname = 'script'
        AND (t.tgname, p.proname) IN (
            ('trg_contratti_righe_a05_guard_esclusione_immutabile_upd', 'trgfn_righe_guard_esclusione_immutabile'),
            ('trg_contratti_righe_a10_guard_articolo_ammesso_ins_upd', 'trgfn_righe_guard_articolo_ammesso'),
            ('trg_contratti_righe_a10_guard_esclusione_senza_dati_ins', 'trgfn_righe_guard_esclusione_senza_dati')))
    AND to_regproc('script.trgfn_righe_guard_aggiunta_fuori_listino') IS NULL
    AND to_regproc('script.trgfn_righe_guard_esclusione_figlio_bundle') IS NULL
    AND to_regproc('vendite.trgfn_contratti_righe_guard_esclusione_immutabile') IS NULL
    AND to_regproc('vendite.trgfn_contratti_righe_guard_aggiunta_fuori_listino') IS NULL
    AND to_regproc('vendite.trgfn_contratti_righe_guard_esclusione_figlio_bundle') IS NULL
    AND to_regproc('script.fn_check_esclusione_articolo_contratto') IS NULL,
    '5) contratto: i guard sulle funzioni generiche di script; le quattro del solo contratto ritirate');

-- ============================================================
-- 6..10 — contratto: l'esclusione e' vuota
-- ============================================================
SELECT pg_temp.esegui(pg_temp.ins('contratto', 'C', 'ESCLUSIONE'));

-- ⭐ «Accettata» non basta: i trigger di valorizzazione non devono averla
--   riempita (default FISSA, UdM e fattore dall'articolo). Se fosse rifiutata,
--   l'INSERT sopra fermerebbe il file (Bad plan): il rosso si vede comunque.
SELECT is(
    (SELECT num_nonnulls(prezzo_unitario, quantita, qta_operativa, uom_operativa_id,
                         factor_to_base, tipo_erogazione, fonte_quantita_attesa,
                         periodicita, generazione_canone)
       FROM vendite.contratti_righe
      WHERE contratto_id = pg_temp.doc('contratto') AND articolo_id = pg_temp.art('C')),
    0,
    '6) contratto: l''esclusione resta vuota (nessun trigger la riempie)');

SELECT throws_like(
    pg_temp.ins('contratto', 'A', 'ESCLUSIONE', 'quantita', '1'),
    '%non porta prezzo, quantità né erogazione%',
    '7) contratto: ESCLUSIONE con la quantita'' rifiutata col messaggio del codice');

SELECT is(
    pg_temp.canali(pg_temp.ins('contratto', 'A', 'ESCLUSIONE', 'quantita', '1')),
    'E_RIGA_ESCLUSIONE_CON_DATI / quantita',
    '8) contratto: canali strutturati = il codice / il campo');

-- ⭐ Il CHECK di stamattina lasciava l'erogazione «libera»: ora e' vuota.
SELECT is(
    pg_temp.canali(pg_temp.ins('contratto', 'A', 'ESCLUSIONE', 'tipo_erogazione', 'CANONE')),
    'E_RIGA_ESCLUSIONE_CON_DATI / tipo_erogazione',
    '9) contratto: ESCLUSIONE con la sola erogazione rifiutata, campo tipo_erogazione');

-- R2: il WHEN salta solo l'esclusione. Un OVERRIDE senza fonte riceve ancora un
--   default.
-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): il default
--   viene dall'ARTICOLO (vendite.fn_articolo_erogazioni), e l'erogazione indicata deve
--   stare nel suo perimetro. Prima: CANONE scritto a mano e FISSA dalla matrice, che su
--   un articolo del listino del test (tipologia CONSUMO) oggi e' fuori perimetro.
--   Qui la riga non indica ne' l'erogazione ne' la fonte, e le riceve tutte e due.
INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione, prezzo_unitario,
       quantita, qta_operativa, uom_operativa_id)
SELECT pg_temp.doc('contratto'), a.id, 'OVERRIDE', 90.00, pg_temp.qta(a.id), pg_temp.qta(a.id), a.uom_id
  FROM catalogo.articoli a WHERE a.id = pg_temp.art('A');

SELECT is(
    (SELECT r.tipo_erogazione::text || '/' || r.fonte_quantita_attesa::text
       FROM vendite.contratti_righe r
      WHERE r.contratto_id = pg_temp.doc('contratto') AND r.articolo_id = pg_temp.art('A')),
    (SELECT e.tipo_erogazione::text || '/' || e.fonte_quantita_attesa::text
       FROM vendite.fn_articolo_erogazioni(pg_temp.art('A')) e WHERE e.e_default),
    '10) contratto: un OVERRIDE senza erogazione ne'' fonte riceve il default dell''articolo (il WHEN salta solo l''esclusione)');

-- Tolto, per non cambiare la fixture della lista (A resta DA_LISTINO).
DELETE FROM vendite.contratti_righe
 WHERE contratto_id = pg_temp.doc('contratto') AND articolo_id = pg_temp.art('A');

-- ============================================================
-- 11..15 — offerta: l'esclusione e' vuota e non si modifica (R1, R3)
-- ============================================================
SELECT pg_temp.esegui(pg_temp.ins('offerta', 'C', 'ESCLUSIONE'));

SELECT is(
    (SELECT num_nonnulls(prezzo_unitario, quantita, qta_operativa, uom_operativa_id,
                         factor_to_base, tipo_erogazione, fonte_quantita_attesa,
                         periodicita, generazione_canone)
       FROM vendite.offerte_commerciali_eccezioni
      WHERE offerta_id = pg_temp.doc('offerta') AND articolo_id = pg_temp.art('C')),
    0,
    '11) offerta: ESCLUSIONE vuota accettata, e resta vuota');

SELECT is(
    pg_temp.canali(pg_temp.ins('offerta', 'A', 'ESCLUSIONE', 'prezzo_unitario', '10')),
    'E_RIGA_ESCLUSIONE_CON_DATI / prezzo_unitario',
    '12) offerta: ESCLUSIONE col prezzo rifiutata, campo prezzo_unitario');

SELECT throws_like(
    format($$UPDATE vendite.offerte_commerciali_eccezioni SET ordine = 7
              WHERE offerta_id = %s AND articolo_id = %L$$,
           pg_temp.doc('offerta'), pg_temp.art('C')),
    '%escluso non si modifica%',
    '13) offerta: UPDATE di un''esclusione rifiutato col messaggio del codice');

SELECT lives_ok(
    format($$UPDATE vendite.offerte_commerciali_eccezioni SET ordine = ordine
              WHERE offerta_id = %s AND articolo_id = %L$$,
           pg_temp.doc('offerta'), pg_temp.art('C')),
    '14) offerta: UPDATE di un''esclusione senza cambi passa');

-- Ripristina articolo = DELETE, e poi la si ricrea per la lista.
SELECT lives_ok(
    format($$DELETE FROM vendite.offerte_commerciali_eccezioni
              WHERE offerta_id = %s AND articolo_id = %L$$,
           pg_temp.doc('offerta'), pg_temp.art('C')),
    '15) offerta: DELETE di un''esclusione (Ripristina articolo) passa');
SELECT pg_temp.esegui(pg_temp.ins('offerta', 'C', 'ESCLUSIONE'));

-- ============================================================
-- 16..20 — offerta: le quattro regole del contratto (R5)
-- ============================================================
SELECT throws_like(
    pg_temp.ins('emessa', 'B', 'OVERRIDE'),
    '%non e'' piu'' in bozza%',
    '16) offerta EMESSA: aggiungere una riga e'' rifiutato (fuori bozza)');

SELECT throws_like(
    pg_temp.ins('offerta', 'A', 'AGGIUNTA'),
    '%gia'' presente nel listino di Offerta %',
    '17) offerta: AGGIUNTA di un articolo del listino rifiutata, il messaggio nomina l''offerta');

SELECT throws_like(
    pg_temp.ins('offerta', 'F', 'ESCLUSIONE'),
    '%componente figlio di un bundle%',
    '18) offerta: ESCLUSIONE del componente del bundle rifiutata');

SELECT is(
    (SELECT error_code FROM dbops.automation_lock_columns
      WHERE target_schema = 'vendite' AND target_table = 'offerte_commerciali_eccezioni'
        AND column_name = 'tipo_eccezione' AND enabled),
    'E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE',
    '19) offerta: il registro dei lock dichiara tipo_eccezione, col codice del contratto');

-- ⚠️ Il trigger lo genera ci_apply dal registro: prima, il caso non e'
--   esercitabile, e lo si dichiara (skip) invece di farlo passare a vuoto.
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM pg_trigger
                  WHERE tgrelid = 'vendite.offerte_commerciali_eccezioni'::regclass
                    AND tgname = 'trg_offerte_commerciali_eccezioni_a10_lock_columns_upd')
    THEN throws_like(
        format($$UPDATE vendite.offerte_commerciali_eccezioni
                    SET tipo_eccezione = 'AGGIUNTA'
                  WHERE offerta_id = %s AND articolo_id = %L$$,
               pg_temp.doc('offerta'), pg_temp.art('B')),
        '%tipo di una riga non si cambia%',
        '20) offerta: il lock generato rifiuta il cambio di tipo')
    ELSE skip('20) lock su tipo_eccezione non ancora generato da ci_apply', 1)
END;

-- ============================================================
-- 21..25 — la lista dell'offerta (R4)
-- ============================================================
CREATE TEMP TABLE tmp_rsv_lista AS
SELECT * FROM vendite.fn_offerta_righe_preview(pg_temp.doc('offerta'));

SELECT is(
    (SELECT string_agg(t.sigla || ':' || l.origine || ':' || array_to_string(l.azioni, '+'),
                       ' ' ORDER BY t.sigla)
       FROM tmp_rsv_lista l JOIN tmp_rsv_art t ON t.id = l.articolo_id
      WHERE t.sigla IN ('A', 'B', 'C', 'X')),
    'A:DA_LISTINO:SOVRASCRIVI_PREZZO+ESCLUDI+ADERISCI B:OVERRIDE:MODIFICA+RIPRISTINA_LISTINO '
    'C:ESCLUSIONE:RIPRISTINA_ARTICOLO X:AGGIUNTA:MODIFICA+RIMUOVI',
    '21) lista dell''offerta: i verbi per origine, gli stessi del contratto');

SELECT is(
    (SELECT escludi_blocco_codice FROM tmp_rsv_lista
      WHERE articolo_id = pg_temp.art('F') AND origine = 'DA_LISTINO'),
    'FIGLIO_DI_BUNDLE',
    '22) lista dell''offerta: «Escludi» spento su F col motivo del guard');

SELECT ok(
    (SELECT count(*) = 6 AND count(DISTINCT riga_key) = 6 FROM tmp_rsv_lista),
    '23) lista dell''offerta: A, B, C, F, il bundle P e X, chiavi tutte diverse');

-- ⭐ L'involucro del contratto rende ESATTAMENTE il corpo comune: nei due sensi,
--   e su una lista non vuota (un EXCEPT fra due insiemi vuoti e' verde a vuoto).
SELECT ok(
    (SELECT count(*) = 6 FROM vendite.fn_contratto_righe_preview(pg_temp.doc('contratto')))
    AND NOT EXISTS (
        SELECT * FROM vendite.fn_contratto_righe_preview(pg_temp.doc('contratto'))
        EXCEPT
        SELECT * FROM vendite.fn_documento_righe_preview('CONTRATTO', pg_temp.doc('contratto')))
    AND NOT EXISTS (
        SELECT * FROM vendite.fn_documento_righe_preview('CONTRATTO', pg_temp.doc('contratto'))
        EXCEPT
        SELECT * FROM vendite.fn_contratto_righe_preview(pg_temp.doc('contratto'))),
    '24) lista del contratto = corpo comune, sei righe');

SELECT ok(
    (SELECT m -> 0 ->> 'codice' = 'E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA'
        AND m -> 0 ->> 'reason' = 'FIGLIO_DI_BUNDLE'
        AND m -> 0 ->> 'reason_key' = 'vendite.contratti.escludi_blocco.figlio_di_bundle'
        AND jsonb_array_length(m) = 1
        AND script.fn_check_esclusione_articolo_documento(
                'OFFERTA_COMMERCIALE', pg_temp.doc('offerta'), pg_temp.art('A')) = '[]'::jsonb
       FROM (SELECT script.fn_check_esclusione_articolo_documento(
                 'OFFERTA_COMMERCIALE', pg_temp.doc('offerta'), pg_temp.art('F')) AS m) x),
    '25) la check generica sull''offerta: F un motivo a catalogo, A nessuno');

-- ============================================================
-- 26 — fn_offerta_righe_espanse sul risolutore: stessa risposta
-- ============================================================
SELECT is(
    (SELECT string_agg(t.sigla || ':' || e.origine || ':' || e.prezzo_unitario::numeric(12,2)::text,
                       ' ' ORDER BY t.sigla)
       FROM vendite.fn_offerta_righe_espanse(pg_temp.doc('offerta')) e
       JOIN tmp_rsv_art t ON t.id = e.articolo_id
      WHERE t.sigla IN ('A', 'B', 'C')),
    'A:DA_LISTINO:100.00 B:OVERRIDE:80.00',
    '26) righe espanse dell''offerta: C escluso resta fuori, B col prezzo forzato');

SELECT * FROM finish();
ROLLBACK;
