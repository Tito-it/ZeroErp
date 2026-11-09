-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Le unita' di misura: il fattore ha una sede, alla data del documento, e le
-- regole delle unita' le tiene il database.
--   - catalogo.fn_get_uom_factor(articolo, unita', data): base, mappatura alla
--     data (catalogo.fn_uom_operativa_alla_data), conversione generale nei due
--     versi; NULL se non c'e';
--   - catalogo.articoli_uom_operativa versionata (UNIQUE WITHOUT OVERLAPS), la
--     riga base fissa (CHECK) e protetta (guard), rounding_mode e require_lot
--     ritirate;
--   - script.trgfn_qta_from_operativa: fattore alla data del documento, senza
--     fattore la riga si rifiuta (E_UOM_MISSING), max_decimals applicato,
--     cambio d'unita' che rilegge il fattore; nessun DEFAULT 1 sul fattore;
--   - catalogo.unita_misura_conversioni: una conversione per coppia, stessa
--     tipologia; catalogo.unita_misura: tipologia in uso, calendario = TEMPO;
--   - l'articolo che nasce spento ha la riga base spenta.
-- Brief: brief-db-revisione-catalogo, giro 2 (D2, D3, D6, D7, D8, D12, D13,
-- D14, D17, D22, D23; Q3, Q4, Q7, Q13).
--
-- Elenco test (plan 31; il 25 sono due asserzioni):
--  1)  fn_get_uom_factor ha la data in coda; la firma a due argomenti non c'e'
--  2)  rounding_mode e require_lot ritirate (tabella e vista)
--  3)  il parametro del default di rounding_mode e' ritirato
--  4)  fattore dell'unita' base: 1
--  5)  mappatura versionata: 6 fino a ieri, 12 da oggi
--  6)  due mappature sovrapposte: rifiutate
--  7)  conversione generale diretta: 1000
--  8)  conversione generale inversa: 1/1000
--  9)  una conversione per coppia: il verso opposto sovrapposto e' rifiutato
--  10) nessuna mappatura ne' conversione: NULL
--  11) nessun DEFAULT sul fattore di ordini, bolle e resi
--  12) riga di preventivo in KG: quantita' 2000, fattore 1000 fotografato
--  13) riga in un'unita' senza conversione: E_UOM_MISSING
--  14) riga nel cartone oggi: fattore 12
--  15) riga nel cartone su un preventivo di ieri: fattore 6
--  16) UPDATE che cambia solo l'unita': il fattore si rilegge
--  17) max_decimals 0: 1,5 cartoni rifiutati (E_QTA_OPERATIVA_DECIMALI)
--  18) max_decimals 0: 2,0 cartoni ammessi (gli zeri in coda non contano)
--  19) riga base: fattore diverso da 1 rifiutato (CHECK)
--  20) riga base: unita' spostata rifiutata (E_UOM_RIGA_BASE_IMMUTABILE)
--  21) riga base: cancellazione rifiutata
--  22) riga base nuova su un'altra unita': rifiutata
--  23) riga non base: si cancella
--  24) la cancellazione dell'articolo porta via la riga base
--  25) articolo creato spento: nasce, con la riga base spenta
--  26) conversione fra tipologie diverse: E_UOM_CONVERSIONE_TIPO_DIVERSO
--  27) tipologia di un'unita' in una conversione: E_UOM_TIPO_IN_USO
--  28) tipologia di un'unita' senza conversioni: si cambia
--  29) calendario su un'unita' di massa: E_UOM_CALENDARIO_NON_TEMPO
--  30) calendario su un'unita' di tempo: ammesso
--
-- Fixture costruita (ROLLBACK finale): unita', conversioni, articoli e
-- preventivi sono del test; le tipologie si scelgono per codice_interno.
-- ------------------------------------------------------------

BEGIN;

-- Vincoli differiti a fine istruzione: senza, al ROLLBACK non scatterebbero mai.
SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(31);

-- Le tipologie, per codice_interno (bloccato).
CREATE TEMP TABLE _t_tipo AS
SELECT (SELECT id FROM catalogo.uom_tipi WHERE codice_interno = 'MASSA')       AS massa,
       (SELECT id FROM catalogo.uom_tipi WHERE codice_interno = 'IMBALLAGGIO') AS imballo,
       (SELECT id FROM catalogo.uom_tipi WHERE codice_interno = 'TEMPO')       AS tempo,
       (SELECT id FROM catalogo.uom_tipi WHERE codice_interno = 'VOLUME')      AS volume;

-- Un'unita' di prova
CREATE FUNCTION pg_temp.unita(p_codice text, p_tipo bigint)
 RETURNS bigint
 LANGUAGE sql
AS $f$
    INSERT INTO catalogo.unita_misura (codice, descrizione, tipo_uom_id)
    VALUES (p_codice, p_codice, p_tipo)
    RETURNING id;
$f$;

CREATE TEMP TABLE _t_u AS
SELECT pg_temp.unita('PGTU-G',   t.massa)   AS g,
       pg_temp.unita('PGTU-KG',  t.massa)   AS kg,
       pg_temp.unita('PGTU-MG',  t.massa)   AS mg,
       pg_temp.unita('PGTU-HG',  t.massa)   AS hg,
       pg_temp.unita('PGTU-T',   t.massa)   AS ton,
       pg_temp.unita('PGTU-CRT', t.imballo) AS crt,
       pg_temp.unita('PGTU-GG',  t.tempo)   AS gg
  FROM _t_tipo t;

-- Le conversioni generali: KG -> G e G -> MG (la seconda si legge all'inverso).
INSERT INTO catalogo.unita_misura_conversioni (uom_from_id, uom_to_id, fattore, valido_dal)
SELECT u.kg, u.g, 1000, script.fn_data_operativa() - 30 FROM _t_u u
UNION ALL
SELECT u.g, u.mg, 1000, script.fn_data_operativa() - 30 FROM _t_u u;

-- Gli articoli, con base il grammo.
CREATE TEMP TABLE _t_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-UOM2-A', true, false, false, (SELECT g FROM _t_u)) AS a,
       dbops.fn_pgtap_crea_articolo('PGT-UOM2-B', true, false, false, (SELECT g FROM _t_u)) AS b;

-- Il cartone dell'articolo A: 6 grammi fino a ieri, 12 da oggi, e da oggi
-- senza decimali.
INSERT INTO catalogo.articoli_uom_operativa (articolo_id, uom_id, factor_to_base, valido_dal, valido_al, max_decimals)
SELECT a.a, u.crt, 6, NULL, script.fn_data_operativa() - 1, 6 FROM _t_art a, _t_u u
UNION ALL
SELECT a.a, u.crt, 12, script.fn_data_operativa(), NULL, 0 FROM _t_art a, _t_u u;

-- ============================================================
-- La struttura (1-3)
-- ============================================================
SELECT ok(
    to_regprocedure('catalogo.fn_get_uom_factor(uuid, bigint, date)') IS NOT NULL
    AND to_regprocedure('catalogo.fn_get_uom_factor(uuid, bigint)') IS NULL,
    '1) fn_get_uom_factor(articolo, unita'', data); la firma senza data non c''e'' piu''');

SELECT ok(
    NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = 'catalogo'
                   AND table_name IN ('articoli_uom_operativa', 'vw_articoli_uom_operativa_dettaglio')
                   AND column_name IN ('rounding_mode', 'require_lot')),
    '2) rounding_mode e require_lot ritirate, dalla tabella e dalla vista');

SELECT ok(
    NOT EXISTS (SELECT 1 FROM config.parameters WHERE code = 'CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE'),
    '3) il parametro del default di rounding_mode e'' ritirato');

-- ============================================================
-- Il fattore (4-11)
-- ============================================================
SELECT is(catalogo.fn_get_uom_factor((SELECT a FROM _t_art), (SELECT g FROM _t_u), script.fn_data_operativa()),
          1::numeric,
    '4) l''unita'' base vale 1');

SELECT is(
    catalogo.fn_get_uom_factor((SELECT a FROM _t_art), (SELECT crt FROM _t_u), script.fn_data_operativa() - 1)::text
    || '/' ||
    catalogo.fn_get_uom_factor((SELECT a FROM _t_art), (SELECT crt FROM _t_u), script.fn_data_operativa())::text,
    '6.000000/12.000000',
    '5) la mappatura alla data: 6 fino a ieri, 12 da oggi');

SELECT throws_ok(
    $$ INSERT INTO catalogo.articoli_uom_operativa (articolo_id, uom_id, factor_to_base, valido_dal)
       SELECT a.a, u.crt, 24, script.fn_data_operativa() + 5 FROM _t_art a, _t_u u $$,
    '23P01', NULL,
    '6) due mappature della stessa unita'' nello stesso periodo: rifiutate');

SELECT is(catalogo.fn_get_uom_factor((SELECT b FROM _t_art), (SELECT kg FROM _t_u), script.fn_data_operativa()),
          1000::numeric,
    '7) conversione generale diretta (KG -> G): 1000');

SELECT is(catalogo.fn_get_uom_factor((SELECT b FROM _t_art), (SELECT mg FROM _t_u), script.fn_data_operativa()),
          0.001::numeric,
    '8) conversione generale inversa (G -> MG letta da MG): 1/1000');

SELECT throws_ok(
    $$ INSERT INTO catalogo.unita_misura_conversioni (uom_from_id, uom_to_id, fattore, valido_dal)
       SELECT u.g, u.kg, 0.001, script.fn_data_operativa() FROM _t_u u $$,
    '23P01', NULL,
    '9) una conversione per coppia: G -> KG accanto a KG -> G e'' rifiutata');

SELECT is(catalogo.fn_get_uom_factor((SELECT b FROM _t_art), (SELECT hg FROM _t_u), script.fn_data_operativa()),
          NULL::numeric,
    '10) nessuna mappatura ne'' conversione: NULL');

SELECT ok(
    NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = 'vendite' AND column_name = 'factor_to_base'
                   AND table_name IN ('ordini_righe', 'ddt_righe', 'resi_righe')
                   AND column_default IS NOT NULL),
    '11) nessun DEFAULT sul fattore di ordini, bolle e resi: lo scrive il trigger');

-- ============================================================
-- Le righe di documento (12-18)
-- ============================================================
CREATE TEMP TABLE _t_prev AS
SELECT p.preventivo_id AS oggi FROM dbops.fn_pgtap_crea_preventivo('PGT-UOM2', 'DRAFT') p;

CREATE TEMP TABLE _t_prev_ieri AS
SELECT p.preventivo_id AS ieri FROM dbops.fn_pgtap_crea_preventivo('PGT-UOM2-IERI', 'DRAFT') p;

UPDATE vendite.preventivi SET data = script.fn_data_operativa() - 1
 WHERE id = (SELECT ieri FROM _t_prev_ieri);

-- Una riga di preventivo dell'articolo A
CREATE FUNCTION pg_temp.riga(p_preventivo bigint, p_uom bigint, p_qta numeric)
 RETURNS bigint
 LANGUAGE sql
AS $f$
    INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa, uom_operativa_id)
    SELECT p_preventivo, a.a, ka.iva_id, 10, p_qta, p_uom
      FROM _t_art a JOIN catalogo.articoli ka ON ka.id = a.a
    RETURNING id;
$f$;

CREATE TEMP TABLE _t_r_kg AS SELECT pg_temp.riga((SELECT oggi FROM _t_prev), (SELECT kg FROM _t_u), 2) AS id;

SELECT is(
    (SELECT r.quantita::text || '/' || r.factor_to_base::text FROM vendite.preventivi_righe r WHERE r.id = (SELECT id FROM _t_r_kg)),
    '2000.000000/1000.000000',
    '12) riga in KG: quantita'' 2000 grammi, fattore 1000 fotografato sulla riga');

SELECT throws_like(
    format('SELECT pg_temp.riga(%s, %s, 1)', (SELECT oggi FROM _t_prev), (SELECT hg FROM _t_u)),
    '%non si converte nell''unità base%',
    '13) riga in un''unita'' senza conversione: E_UOM_MISSING, non fattore 1');

CREATE TEMP TABLE _t_r_crt AS SELECT pg_temp.riga((SELECT oggi FROM _t_prev), (SELECT crt FROM _t_u), 2) AS id;

SELECT is(
    (SELECT r.factor_to_base FROM vendite.preventivi_righe r WHERE r.id = (SELECT id FROM _t_r_crt)),
    12::numeric,
    '14) riga nel cartone su un preventivo di oggi: fattore 12');

CREATE TEMP TABLE _t_r_ieri AS SELECT pg_temp.riga((SELECT ieri FROM _t_prev_ieri), (SELECT crt FROM _t_u), 2) AS id;

SELECT is(
    (SELECT r.factor_to_base FROM vendite.preventivi_righe r WHERE r.id = (SELECT id FROM _t_r_ieri)),
    6::numeric,
    '15) riga nel cartone su un preventivo di ieri: fattore 6, quello alla data del documento');

UPDATE vendite.preventivi_righe SET uom_operativa_id = (SELECT crt FROM _t_u)
 WHERE id = (SELECT id FROM _t_r_kg);

SELECT is(
    (SELECT r.quantita::text || '/' || r.factor_to_base::text FROM vendite.preventivi_righe r WHERE r.id = (SELECT id FROM _t_r_kg)),
    '24.000000/12.000000',
    '16) UPDATE che cambia solo l''unita'' (KG -> cartone): il fattore si rilegge');

SELECT throws_like(
    format('SELECT pg_temp.riga(%s, %s, 1.5)', (SELECT oggi FROM _t_prev), (SELECT crt FROM _t_u)),
    '%troppi decimali%',
    '17) max_decimals 0: 1,5 cartoni rifiutati (E_QTA_OPERATIVA_DECIMALI)');

SELECT lives_ok(
    format('SELECT pg_temp.riga(%s, %s, 2.000)', (SELECT oggi FROM _t_prev), (SELECT crt FROM _t_u)),
    '18) max_decimals 0: 2,000 cartoni ammessi, gli zeri in coda non contano');

-- ============================================================
-- La riga base (19-25)
-- ============================================================
SELECT throws_ok(
    $$ UPDATE catalogo.articoli_uom_operativa SET factor_to_base = 2
        WHERE articolo_id = (SELECT b FROM _t_art) AND is_base $$,
    '23514', NULL,
    '19) riga base con fattore diverso da 1: rifiutata dal CHECK');

SELECT throws_like(
    $$ UPDATE catalogo.articoli_uom_operativa SET uom_id = (SELECT kg FROM _t_u)
        WHERE articolo_id = (SELECT b FROM _t_art) AND is_base $$,
    '%non si cambia e non si toglie%',
    '20) riga base spostata su un''altra unita'': E_UOM_RIGA_BASE_IMMUTABILE');

SELECT throws_like(
    $$ DELETE FROM catalogo.articoli_uom_operativa
        WHERE articolo_id = (SELECT b FROM _t_art) AND is_base $$,
    '%non si cambia e non si toglie%',
    '21) riga base cancellata: E_UOM_RIGA_BASE_IMMUTABILE');

SELECT throws_like(
    $$ INSERT INTO catalogo.articoli_uom_operativa (articolo_id, uom_id, is_base, factor_to_base)
       SELECT a.b, u.kg, true, 1 FROM _t_art a, _t_u u $$,
    '%non si cambia e non si toglie%',
    '22) una riga base su un''unita'' diversa da quella dell''articolo: rifiutata');

SELECT lives_ok(
    $$ DELETE FROM catalogo.articoli_uom_operativa
        WHERE articolo_id = (SELECT a FROM _t_art) AND uom_id = (SELECT crt FROM _t_u)
          AND valido_dal IS NULL $$,
    '23) una riga che non e'' la base si cancella');

CREATE TEMP TABLE _t_art_via AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-UOM2-VIA', true, false, false, (SELECT g FROM _t_u)) AS id;

SELECT lives_ok(
    $$ DELETE FROM catalogo.articoli WHERE id = (SELECT id FROM _t_art_via) $$,
    '24) cancellare l''articolo porta via la sua riga base (ON DELETE CASCADE)');

-- Un articolo che nasce spento: la riga dell'articolo B, con un id e un codice nuovi.
SELECT lives_ok(
    $$ INSERT INTO catalogo.articoli
       SELECT (jsonb_populate_record(NULL::catalogo.articoli,
                   to_jsonb(a) || jsonb_build_object('id', uuidv7(), 'codice', 'PGT-UOM2-SPENTO', 'attivo', false))).*
         FROM catalogo.articoli a
        WHERE a.id = (SELECT b FROM _t_art) $$,
    '25a) un articolo creato spento nasce');

SELECT is(
    (SELECT o.attivo FROM catalogo.articoli_uom_operativa o
       JOIN catalogo.articoli a ON a.id = o.articolo_id
      WHERE a.codice = 'PGT-UOM2-SPENTO' AND o.is_base),
    false,
    '25b) ... e la sua riga base nasce spenta');

-- ============================================================
-- Le unita' e le conversioni (26-30)
-- ============================================================
SELECT throws_like(
    $$ INSERT INTO catalogo.unita_misura_conversioni (uom_from_id, uom_to_id, fattore, valido_dal)
       SELECT u.crt, u.g, 6, script.fn_data_operativa() FROM _t_u u $$,
    '%unità di tipologia diversa%',
    '26) conversione fra tipologie diverse: E_UOM_CONVERSIONE_TIPO_DIVERSO');

SELECT throws_like(
    $$ UPDATE catalogo.unita_misura SET tipo_uom_id = (SELECT volume FROM _t_tipo)
        WHERE id = (SELECT kg FROM _t_u) $$,
    '%compare in una conversione%',
    '27) la tipologia di un''unita'' in una conversione non cambia: E_UOM_TIPO_IN_USO');

SELECT lives_ok(
    $$ UPDATE catalogo.unita_misura SET tipo_uom_id = (SELECT volume FROM _t_tipo)
        WHERE id = (SELECT ton FROM _t_u) $$,
    '28) la tipologia di un''unita'' senza conversioni si cambia');

SELECT throws_like(
    $$ UPDATE catalogo.unita_misura SET conta_dal_calendario = 'GIORNO'
        WHERE id = (SELECT hg FROM _t_u) $$,
    '%solo se è un''unità di tempo%',
    '29) un''unita'' di massa non si conta dal calendario: E_UOM_CALENDARIO_NON_TEMPO');

SELECT lives_ok(
    $$ UPDATE catalogo.unita_misura SET conta_dal_calendario = 'GIORNO'
        WHERE id = (SELECT gg FROM _t_u) $$,
    '30) un''unita'' di tempo si conta dal calendario');

SELECT * FROM finish();
ROLLBACK;
