-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2b, 20261019-87 … -99):
--   la natura merce ha destinazione ORDINE_VENDITA, il codice della sorgente (era ORDINE).
-- pgTAP test per Zero ERP
--
-- Il picker degli articoli di una riga (catalogo.fn_articoli_ammessi): i
-- candidati della ricerca col primo motivo di esclusione (NULL = ammesso),
-- prima gli ammessi; la stessa check dei guard, divisa in contesto del
-- documento (letto una volta) e motivi. E la promo (D-6).
-- Brief: brief-db-articoli-ammessi-per-documento (§8.6 A-1, A-2, A-7, D-6;
--   R-7; §9.4)
-- ChangeSet: 20261014-01 -> -05; 20261014-06 (D-7, il kit senza componenti)
--
-- ⭐ TUTTO COSTRUITO: mondo, listino con una versione propria, contratto,
--   preventivo e articoli nascono qui. Nessuna pesca dal catalogo.
--
-- LA FIXTURE — articoli PGT-AMM4-*: A merce nel listino; M merce (tipologia
--   del listino, fuori listino); P composito merce col componente F; F merce;
--   V composito SENZA componenti; C solo componente merce; R servizio
--   ricorrente; X merce SPENTA. Un contratto DRAFT sul listino
--   (versione in vigore con A), un preventivo in bozza.
--
-- ⭐ «Picker e guard non dissentono» (R-7) si prova CONFRONTANDO, per ogni
--   articolo che il picker restituisce, il suo motivo col primo motivo della
--   check dei guard (script.fn_check_articolo_riga), e contando le righe: un
--   confronto su zero righe sarebbe verde per sottrazione.
--
-- Elenco test (plan 26):
--  I parametri
--   1) documento con testata senza id: E_PARAMETRO_INVALIDO (A-1)
--   2) documento non gestito: E_DOC_TIPO_NON_GESTITO anche se la ricerca
--      non trova niente (la validazione precede la ricerca)
--   3) p_limit 0: E_PARAMETRO_INVALIDO
--   4) contratto senza tipo d'eccezione: E_PARAMETRO_INVALIDO
--  Il preventivo
--   5) l'elenco: prima gli ammessi, poi gli esclusi col motivo; lo spento no
--   6) ordine = la posizione, da 1 senza buchi
--   7) il tetto prende i primi: gli ammessi
--   8) la ricerca e' letterale: '%' non fa da jolly
--   9) la ricerca non distingue le maiuscole
--  10) picker e guard non dissentono (ogni riga confrontata)
--  11) il guard rifiuta il solo componente, il motivo del picker
--  12) l'ammesso si scrive
--  Il contratto
--  13) AGGIUNTA: A gia' nel listino, M ammesso
--  14) OVERRIDE: A ammesso, M fuori listino (A-5)
--  15) picker e guard non dissentono, sui tre tipi d'eccezione
--  La versione di listino e la distinta
--  16) versione: P «entra come bundle» (COMPOSITO_COME_BUNDLE), A ammesso
--  17) versione: picker e guard non dissentono
--  18) distinta di P: P stesso escluso (COMPONENTE_PADRE), e non dissentono
--  La promo (D-6)
--  19) picker: C escluso (E_PROMO_ARTICOLO_SOLO_COMPONENTE), P ammesso
--  20) guard: la promo su C e' rifiutata
--  21) guard: la promo sul composito P si scrive
--  22) guard: spostare la promo su C e' rifiutato
--  23) la firma di sempre conosce PROMO_ARTICOLO
--  Il kit senza componenti (D-7)
--  24) ordine: il guard rifiuta il kit vuoto, col motivo del picker
--  25) contratto, AGGIUNTA: il kit vuoto, primo motivo dopo il solo componente
--  26) contratto, ESCLUSIONE: il kit vuoto non si giudica (escludere non vende)
-- ------------------------------------------------------------

BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(26);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE _nat AS
SELECT (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'ORDINE_VENDITA' AND nv.attivo ORDER BY nv.id LIMIT 1)    AS merce,
       (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'CONTRATTO' AND nv.attivo ORDER BY nv.id LIMIT 1) AS ricorrente;

CREATE TEMP TABLE _mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP picker articoli ammessi');

-- La versione del builder nasce ATTIVA: la si chiude nel 2020 e quella in
-- vigore nasce qui (BOZZA, righe, ATTIVA). Stesso impianto della 3b.
CREATE TEMP TABLE _listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM _mondo), 'picker articoli ammessi',
    '2020-01-01'::date, '2020-12-31'::date);

CREATE TEMP TABLE _ver AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, stato)
    SELECT listino_id, 'PGTAP_AMM4_V2', '2021-01-01'::date, 'BOZZA' FROM _listino
    RETURNING id
)
SELECT id FROM ins;

-- La struttura nasce col builder: su un articolo usato non cambia piu' (A-10).
CREATE TEMP TABLE _art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGT-AMM4-' || v.sigla, false,
           p_listino_tipologia_id => CASE WHEN v.sigla = 'M' THEN (SELECT tipologia_id FROM _listino) END,
           p_is_composito         => v.sigla IN ('P', 'V'),
           p_is_solo_componente   => v.sigla = 'C',
           p_natura_vendita_id    => CASE WHEN v.sigla = 'R' THEN (SELECT ricorrente FROM _nat)
                                          ELSE (SELECT merce FROM _nat) END) AS id
  FROM (VALUES ('A'), ('M'), ('P'), ('F'), ('V'), ('C'), ('R'), ('X')) AS v(sigla);

-- Scopo: id di un articolo della fixture per sigla.
CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
  SELECT id FROM _art WHERE sigla = p_sigla;
$fx$;

-- P ha un componente (F); V no: e' il kit vuoto (D-7).
INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)
VALUES (pg_temp.art('P'), pg_temp.art('F'), 1, '2020-01-01');
-- X spento: figli prima, padre poi (la UoM operativa nata col builder).
UPDATE catalogo.articoli_uom_operativa SET attivo = FALSE WHERE articolo_id = pg_temp.art('X');
UPDATE catalogo.articoli SET attivo = FALSE WHERE id = pg_temp.art('X');

SELECT dbops.fn_pgtap_listino_aggiungi_articoli(
    (SELECT id FROM _ver), ARRAY[pg_temp.art('A')], 100.00);
UPDATE vendite.listini_versioni SET stato = 'ATTIVA' WHERE id = (SELECT id FROM _ver);

CREATE TEMP TABLE _ctr AS
WITH ins AS (
    INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,
           stato_doc_contratto_id, listino_id, valido_dal, valido_al)
    SELECT 'PGTAP-AMM4-' || substr(gen_random_uuid()::text, 1, 8),
           m.billing_account_id, m.istanza_utility_id, m.utility_id,
           (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),
           (SELECT listino_id FROM _listino),
           script.fn_data_operativa(), script.fn_data_operativa() + 365
      FROM _mondo m
    RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE _prev AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgTAP picker articoli ammessi');

CREATE TEMP TABLE _iva AS
SELECT (SELECT i.id FROM config.iva i WHERE i.attivo AND i.aliquota_iva > 0 ORDER BY i.id LIMIT 1) AS id;

-- Scopo: l'elenco del picker come testo, «sigla:reason» (OK = ammesso), in ordine.
CREATE OR REPLACE FUNCTION pg_temp.elenco(p_doc text, p_id bigint, p_search text,
                                          p_limit integer DEFAULT NULL, p_tipo text DEFAULT NULL,
                                          p_padre uuid DEFAULT NULL)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT string_agg(replace(f.codice, 'PGT-AMM4-', '') || ':'
                    || COALESCE(f.motivo ->> 'reason', 'OK'), ',' ORDER BY f.ordine)
    FROM catalogo.fn_articoli_ammessi(p_doc, p_id, p_search, p_limit,
                                      p_tipo::vendite.tipo_eccezione_contratto, p_padre) f;
$fx$;

-- Scopo: {righe, dissensi} fra il picker e la check dei guard, articolo per articolo.
CREATE OR REPLACE FUNCTION pg_temp.dissensi(p_doc text, p_id bigint,
                                            p_tipo text DEFAULT NULL, p_padre uuid DEFAULT NULL)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT count(*) || ' righe, '
         || count(*) FILTER (WHERE f.motivo IS DISTINCT FROM
                script.fn_check_articolo_riga(p_doc, p_id, f.articolo_id, NULL,
                    p_tipo::vendite.tipo_eccezione_contratto, p_padre) -> 0) || ' dissensi'
    FROM catalogo.fn_articoli_ammessi(p_doc, p_id, 'PGT-AMM4-', NULL,
                                      p_tipo::vendite.tipo_eccezione_contratto, p_padre) f;
$fx$;

-- ============================================================
-- I parametri (1-4)
-- ============================================================
SELECT throws_like(
    $$ SELECT * FROM catalogo.fn_articoli_ammessi('PREVENTIVO', NULL, 'PGT-AMM4-') $$,
    '%p_documento_id obbligatorio%',
    '1) documento con testata senza id: E_PARAMETRO_INVALIDO (A-1)');

SELECT throws_like(
    $$ SELECT * FROM catalogo.fn_articoli_ammessi('FATTURA', 1, 'PGT-AMM4-NESSUNO') $$,
    '%FATTURA sconosciuto%',
    '2) documento non gestito: E_DOC_TIPO_NON_GESTITO anche senza candidati');

SELECT throws_like(
    format($$ SELECT * FROM catalogo.fn_articoli_ammessi('PREVENTIVO', %s, 'PGT-AMM4-', 0) $$,
           (SELECT preventivo_id FROM _prev)),
    '%p_limit%',
    '3) p_limit 0: E_PARAMETRO_INVALIDO');

SELECT throws_like(
    format($$ SELECT * FROM catalogo.fn_articoli_ammessi('CONTRATTO', %s, 'PGT-AMM4-') $$,
           (SELECT id FROM _ctr)),
    '%p_tipo_eccezione obbligatorio%',
    '4) contratto senza tipo d''eccezione: E_PARAMETRO_INVALIDO');

-- ============================================================
-- Il preventivo (5-12)
-- ============================================================
SELECT is(pg_temp.elenco('PREVENTIVO', (SELECT preventivo_id FROM _prev), 'PGT-AMM4-'),
          'A:OK,F:OK,M:OK,P:OK,C:SOLO_COMPONENTE,R:RICORRENTE_USA_OFFERTA,V:KIT_SENZA_COMPONENTI',
    '5) preventivo: prima gli ammessi, poi gli esclusi col motivo; lo spento no');

SELECT is((SELECT array_agg(f.ordine ORDER BY f.ordine)
             FROM catalogo.fn_articoli_ammessi('PREVENTIVO', (SELECT preventivo_id FROM _prev), 'PGT-AMM4-') f),
          ARRAY[1, 2, 3, 4, 5, 6, 7],
    '6) ordine e'' la posizione, da 1 senza buchi');

SELECT is(pg_temp.elenco('PREVENTIVO', (SELECT preventivo_id FROM _prev), 'PGT-AMM4-', 2),
          'A:OK,F:OK',
    '7) il tetto prende i primi: gli ammessi');

SELECT is((SELECT count(*)::integer
             FROM catalogo.fn_articoli_ammessi('PREVENTIVO', (SELECT preventivo_id FROM _prev), 'PGT-AMM4-%')),
          0,
    '8) la ricerca e'' letterale: ''%'' non fa da jolly');

SELECT is(pg_temp.elenco('PREVENTIVO', (SELECT preventivo_id FROM _prev), 'pgt-amm4-m'),
          'M:OK',
    '9) la ricerca non distingue le maiuscole');

SELECT is(pg_temp.dissensi('PREVENTIVO', (SELECT preventivo_id FROM _prev)),
          '7 righe, 0 dissensi',
    '10) preventivo: picker e guard non dissentono');

SELECT throws_like(
    format($$INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa)
             VALUES (%s, %L, %s, 10, 1)$$,
           (SELECT preventivo_id FROM _prev), pg_temp.art('C'), (SELECT id FROM _iva)),
    '%solo come componente%',
    '11) preventivo: il guard rifiuta il solo componente, il motivo del picker');

SELECT lives_ok(
    format($$INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa)
             VALUES (%s, %L, %s, 10, 1)$$,
           (SELECT preventivo_id FROM _prev), pg_temp.art('M'), (SELECT id FROM _iva)),
    '12) preventivo: l''ammesso si scrive');

-- ============================================================
-- Il contratto (13-15)
-- ============================================================
SELECT is((SELECT string_agg(replace(f.codice, 'PGT-AMM4-', '') || ':'
                             || COALESCE(f.motivo ->> 'reason', 'OK'), ',' ORDER BY f.codice)
             FROM catalogo.fn_articoli_ammessi('CONTRATTO', (SELECT id FROM _ctr), 'PGT-AMM4-',
                                               NULL, 'AGGIUNTA') f
            WHERE f.codice IN ('PGT-AMM4-A', 'PGT-AMM4-M')),
          'A:AGGIUNTA_GIA_IN_LISTINO,M:OK',
    '13) contratto, AGGIUNTA: A gia'' nel listino, M ammesso');

SELECT is((SELECT string_agg(replace(f.codice, 'PGT-AMM4-', '') || ':'
                             || COALESCE(f.motivo ->> 'reason', 'OK'), ',' ORDER BY f.codice)
             FROM catalogo.fn_articoli_ammessi('CONTRATTO', (SELECT id FROM _ctr), 'PGT-AMM4-',
                                               NULL, 'OVERRIDE') f
            WHERE f.codice IN ('PGT-AMM4-A', 'PGT-AMM4-M')),
          'A:OK,M:ECCEZIONE_FUORI_LISTINO',
    '14) contratto, OVERRIDE: A ammesso, M fuori listino (A-5)');

SELECT is(pg_temp.dissensi('CONTRATTO', (SELECT id FROM _ctr), 'AGGIUNTA') || ' | '
          || pg_temp.dissensi('CONTRATTO', (SELECT id FROM _ctr), 'OVERRIDE') || ' | '
          || pg_temp.dissensi('CONTRATTO', (SELECT id FROM _ctr), 'ESCLUSIONE'),
          '7 righe, 0 dissensi | 7 righe, 0 dissensi | 7 righe, 0 dissensi',
    '15) contratto: picker e guard non dissentono, sui tre tipi d''eccezione');

-- ============================================================
-- La versione di listino e la distinta (16-18)
-- ============================================================
SELECT is((SELECT string_agg(replace(f.codice, 'PGT-AMM4-', '') || ':'
                             || COALESCE(f.motivo ->> 'reason', 'OK'), ',' ORDER BY f.codice)
             FROM catalogo.fn_articoli_ammessi('LISTINO_VERSIONE', (SELECT id FROM _ver), 'PGT-AMM4-') f
            WHERE f.codice IN ('PGT-AMM4-A', 'PGT-AMM4-P')),
          'A:OK,P:COMPOSITO_COME_BUNDLE',
    '16) versione di listino: P entra come bundle, A ammesso');

SELECT is(pg_temp.dissensi('LISTINO_VERSIONE', (SELECT id FROM _ver)),
          '7 righe, 0 dissensi',
    '17) versione di listino: picker e guard non dissentono');

SELECT is((SELECT f.motivo ->> 'reason'
             FROM catalogo.fn_articoli_ammessi('ARTICOLO', NULL, 'PGT-AMM4-P', NULL, NULL,
                                               pg_temp.art('P')) f)
          || ' | ' || pg_temp.dissensi('ARTICOLO', NULL, NULL, pg_temp.art('P')),
          'COMPONENTE_PADRE | 7 righe, 0 dissensi',
    '18) distinta di P: P stesso escluso, e picker e guard non dissentono');

-- ============================================================
-- La promo (19-23)
-- ============================================================
SELECT is((SELECT string_agg(replace(f.codice, 'PGT-AMM4-', '') || ':'
                             || COALESCE(f.motivo ->> 'codice', 'OK'), ',' ORDER BY f.codice)
             FROM catalogo.fn_articoli_ammessi('PROMO_ARTICOLO', NULL, 'PGT-AMM4-') f
            WHERE f.codice IN ('PGT-AMM4-C', 'PGT-AMM4-P')),
          'C:E_PROMO_ARTICOLO_SOLO_COMPONENTE,P:OK',
    '19) promo, picker: il solo componente escluso, il composito ammesso');

SELECT throws_like(
    format($$INSERT INTO vendite.promo_articoli (codice, descrizione, articolo_id, uom_id,
                 tipo_variazione, valore_variazione, valido_dal, valido_al)
             SELECT 'PGTAP_AMM4_PROMO_C', 'pgTAP', a.id, a.uom_id, 'PERCENTUALE', -10,
                    script.fn_data_operativa() + 1, script.fn_data_operativa() + 30
               FROM catalogo.articoli a WHERE a.id = %L$$, pg_temp.art('C')),
    '%una promo su di lui%',
    '20) promo, guard: su un solo componente e'' rifiutata');

SELECT lives_ok(
    format($$INSERT INTO vendite.promo_articoli (codice, descrizione, articolo_id, uom_id,
                 tipo_variazione, valore_variazione, valido_dal, valido_al)
             SELECT 'PGTAP_AMM4_PROMO_P', 'pgTAP', a.id, a.uom_id, 'PERCENTUALE', -10,
                    script.fn_data_operativa() + 1, script.fn_data_operativa() + 30
               FROM catalogo.articoli a WHERE a.id = %L$$, pg_temp.art('P')),
    '21) promo, guard: sul composito si scrive');

SELECT throws_like(
    format($$UPDATE vendite.promo_articoli SET articolo_id = %L
              WHERE codice = 'PGTAP_AMM4_PROMO_P'$$, pg_temp.art('C')),
    '%una promo su di lui%',
    '22) promo, guard: spostarla su un solo componente e'' rifiutato');

SELECT is(script.fn_check_articolo_riga('PROMO_ARTICOLO', NULL, pg_temp.art('C')) -> 0 ->> 'codice',
          'E_PROMO_ARTICOLO_SOLO_COMPONENTE',
    '23) la firma di sempre conosce PROMO_ARTICOLO');

-- ============================================================
-- Il kit senza componenti (24-26, D-7)
-- ============================================================
CREATE TEMP TABLE _ord AS
SELECT * FROM dbops.fn_pgtap_crea_ordine('pgTAP picker articoli ammessi');

SELECT throws_like(
    format($$INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione, iva_id, prezzo_unitario, qta_operativa)
             VALUES (%s, 1, %L, 'kit vuoto', %s, 10, 1)$$,
           (SELECT ordine_id FROM _ord), pg_temp.art('V'), (SELECT id FROM _iva)),
    '%non ha nessun componente%',
    '24) ordine: il guard rifiuta il kit vuoto, col motivo del picker');

SELECT is((SELECT f.motivo ->> 'reason'
             FROM catalogo.fn_articoli_ammessi('CONTRATTO', (SELECT id FROM _ctr), 'PGT-AMM4-V',
                                               NULL, 'AGGIUNTA') f),
          'KIT_SENZA_COMPONENTI',
    '25) contratto, AGGIUNTA: il kit vuoto, primo motivo');

SELECT is((SELECT f.motivo ->> 'reason'
             FROM catalogo.fn_articoli_ammessi('CONTRATTO', (SELECT id FROM _ctr), 'PGT-AMM4-V',
                                               NULL, 'ESCLUSIONE') f),
          'ECCEZIONE_FUORI_LISTINO',
    '26) contratto, ESCLUSIONE: il kit vuoto non si giudica, parla solo il listino');

SELECT * FROM finish();
ROLLBACK;
