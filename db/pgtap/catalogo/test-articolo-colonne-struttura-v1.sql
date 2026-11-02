-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2b, 20261019-87 … -99):
--   la natura merce ha destinazione ORDINE_VENDITA, il codice della sorgente (era ORDINE).
-- pgTAP test per Zero ERP
--
-- Le colonne strutturali di un articolo hanno UNA sede leggibile,
-- catalogo.fn_articolo_colonne_struttura(), che le legge dalle regole del form
-- sul predicato dell'uso (dbops.lock_columns_conditional). Il verbo di
-- correzione la usa per le colonne ammesse E per quelle che scrive; il guard,
-- che l'elenco lo ha scritto (UPDATE OF e CASE), le deve avere tutte.
-- Brief: brief-db-articoli-ammessi-per-documento (§9.7.3, R-DB-3)
-- ChangeSet: 20261018-70, 20261018-71
-- ⚠️ rev 2026-10-18: dal 20261018-72 il verbo rifiuta una correzione che
--   renderebbe non ammesse righe di documenti aperti; la riga di U si spegne
--   nella fixture (U resta usato).
--
-- Elenco test (plan 12):
--  La sede
--   1) la funzione c'e', e l'app la puo' eseguire
--   2) restituisce le colonne delle regole accese sul predicato dell'uso,
--      nell'ordine della dichiarazione
--  Le copie che non si derivano (presidi: alla nona colonna diventano rossi)
--   3) il trigger del guard scatta su UPDATE OF esattamente quelle colonne
--   4) il CASE del guard nomina ognuna (NEW.<colonna>)
--   5) il verbo legge la sede: nessuna costante c_ammessi nel corpo
--  Il verbo segue la sede (SUPER_ADMIN)
--   6) corregge due colonne di tipo diverso (boolean, bigint) di un articolo usato
--   7) le colonne non passate restano come erano
--   8) un valore che non e' del tipo della colonna fallisce (22P02), come prima
--   9) una colonna fuori dalla sede: E_PARAMETRO_INVALIDO col suo nome
--  10) una regola nuova nel registro: la sede la include e il verbo la scrive
--  11) una regola spenta (enabled = false) esce dalla sede
--  12) ... e il verbo non la accetta piu'
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _nat AS
SELECT (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'ORDINE_VENDITA' AND nv.attivo ORDER BY nv.id LIMIT 1)   AS merce,
       (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'COMMESSA' AND nv.attivo ORDER BY nv.id LIMIT 1) AS servizio;

CREATE TEMP TABLE _iva AS
SELECT (SELECT i.id FROM config.iva i WHERE i.attivo AND i.aliquota_iva > 0 ORDER BY i.id LIMIT 1) AS id;

-- U: usato (in una riga di preventivo).
CREATE TEMP TABLE _art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-ACS-U', false, p_natura_vendita_id => (SELECT merce FROM _nat)) AS u;

CREATE TEMP TABLE _prev AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgTAP colonne struttura');

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa)
SELECT (SELECT preventivo_id FROM _prev), (SELECT u FROM _art), (SELECT id FROM _iva), 10, 1;

-- La riga si spegne: U resta USATO (l'uso vale in qualunque stato), ma non ha
-- righe vive. Questo file prova la sede delle colonne; il rifiuto per le righe
-- dei documenti aperti (20261018-72, A-11) ha il suo test:
-- catalogo/test-articolo-correzione-righe-aperte-v1.
UPDATE vendite.preventivi_righe SET attivo = false
 WHERE preventivo_id = (SELECT preventivo_id FROM _prev);

-- Le colonne del registro, lette QUI direttamente: e' il termine di paragone.
CREATE TEMP TABLE _registro AS
SELECT array_agg(l.column_name::text ORDER BY l.id) AS colonne
  FROM dbops.lock_columns_conditional l
 WHERE l.schema_name    = 'catalogo'
   AND l.table_name     = 'articoli'
   AND l.condition_expr = 'catalogo.fn_articolo_usato($1::uuid)'
   AND l.enabled;

-- ============================================================
-- La sede (1-2)
-- ============================================================
SELECT ok(
    to_regprocedure('catalogo.fn_articolo_colonne_struttura()') IS NOT NULL
    AND has_function_privilege('zeroerp_app', 'catalogo.fn_articolo_colonne_struttura()', 'EXECUTE'),
    '1) catalogo.fn_articolo_colonne_struttura() c''e'' e l''app la esegue');

SELECT is(
    catalogo.fn_articolo_colonne_struttura(),
    (SELECT colonne FROM _registro),
    '2) la sede = le regole accese del form sul predicato dell''uso, nell''ordine della dichiarazione');

-- ============================================================
-- Le copie che non si derivano (3-5)
-- ============================================================
SELECT is(
    (SELECT array_agg(a.attname::text ORDER BY a.attname)
       FROM pg_trigger t
       CROSS JOIN LATERAL unnest(t.tgattr) AS k(attnum)
       JOIN pg_attribute a ON a.attrelid = t.tgrelid AND a.attnum = k.attnum
      WHERE t.tgrelid = 'catalogo.articoli'::regclass
        AND t.tgname  = 'trg_articoli_a10_guard_struttura_se_usato_upd'),
    (SELECT array_agg(c ORDER BY c) FROM unnest(catalogo.fn_articolo_colonne_struttura()) c),
    '3) il guard scatta su UPDATE OF esattamente le colonne della sede');

SELECT is(
    (SELECT array_agg(c ORDER BY c)
       FROM unnest(catalogo.fn_articolo_colonne_struttura()) c
      WHERE position('NEW.' || c || ' ' IN
                     (SELECT p.prosrc FROM pg_proc p
                       WHERE p.oid = 'catalogo.trgfn_articoli_guard_struttura_se_usato()'::regprocedure)) = 0),
    NULL::text[],
    '4) il CASE del guard nomina ogni colonna della sede (nessuna mancante)');

SELECT ok(
    (SELECT p.prosrc FROM pg_proc p
      WHERE p.oid = 'catalogo.fn_articolo_correggi_struttura(uuid, jsonb)'::regprocedure)
        LIKE '%catalogo.fn_articolo_colonne_struttura()%'
    AND (SELECT p.prosrc FROM pg_proc p
          WHERE p.oid = 'catalogo.fn_articolo_correggi_struttura(uuid, jsonb)'::regprocedure)
        NOT LIKE '%c_ammessi%',
    '5) il verbo legge la sede: nessuna costante c_ammessi');

-- ============================================================
-- Il verbo segue la sede (6-12), da SUPER_ADMIN
-- ============================================================
CREATE TEMP TABLE _sa AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-colonne-struttura', true);
DO $sa$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _sa)); END $sa$;

CREATE TEMP TABLE _prima AS
SELECT a.is_composito, a.gestito_a_magazzino, a.requires_lotto, a.requires_serial,
       a.causale_onere_id, a.listino_tipologia_id
  FROM catalogo.articoli a
 WHERE a.id = (SELECT u FROM _art);

SELECT catalogo.fn_articolo_correggi_struttura(
    (SELECT u FROM _art),
    jsonb_build_object('is_solo_componente', true,
                       'natura_vendita_id',  (SELECT servizio FROM _nat)));

SELECT is(
    (SELECT (a.is_solo_componente, a.natura_vendita_id)::text
       FROM catalogo.articoli a WHERE a.id = (SELECT u FROM _art)),
    (true, (SELECT servizio FROM _nat))::text,
    '6) il SUPER_ADMIN corregge un boolean e un bigint di un articolo usato');

SELECT is(
    (SELECT (a.is_composito, a.gestito_a_magazzino, a.requires_lotto, a.requires_serial,
             a.causale_onere_id, a.listino_tipologia_id)::text
       FROM catalogo.articoli a WHERE a.id = (SELECT u FROM _art)),
    (SELECT (p.is_composito, p.gestito_a_magazzino, p.requires_lotto, p.requires_serial,
             p.causale_onere_id, p.listino_tipologia_id)::text
       FROM _prima p),
    '7) le colonne non passate restano come erano');

SELECT throws_ok(
    format($$SELECT catalogo.fn_articolo_correggi_struttura(%L, '{"requires_lotto": "forse"}'::jsonb)$$,
           (SELECT u FROM _art)),
    '22P02',
    NULL,
    '8) un valore che non e'' del tipo della colonna: 22P02, come col cast scritto a mano');

SELECT throws_like(
    format($$SELECT catalogo.fn_articolo_correggi_struttura(%L, '{"descrizione": "x"}'::jsonb)$$,
           (SELECT u FROM _art)),
    '%non correggibili%descrizione%',
    '9) una colonna fuori dalla sede: E_PARAMETRO_INVALIDO, col suo nome');

-- Una nona regola, nel registro: la sede la vede e il verbo la scrive.
INSERT INTO dbops.lock_columns_conditional
    (schema_name, table_name, column_name, condition_expr, descrizione)
VALUES ('catalogo', 'articoli', 'descrizione', 'catalogo.fn_articolo_usato($1::uuid)',
        'pgTAP: una nona colonna');

SELECT catalogo.fn_articolo_correggi_struttura(
    (SELECT u FROM _art), '{"descrizione": "pgTAP corretta dal verbo"}'::jsonb);

SELECT ok(
    'descrizione' = ANY (catalogo.fn_articolo_colonne_struttura())
    AND (SELECT a.descrizione FROM catalogo.articoli a WHERE a.id = (SELECT u FROM _art))
        = 'pgTAP corretta dal verbo',
    '10) una regola nuova nel registro: la sede la include e il verbo la scrive');

-- Una regola spenta esce dalla sede.
UPDATE dbops.lock_columns_conditional
   SET enabled = false
 WHERE schema_name    = 'catalogo'
   AND table_name     = 'articoli'
   AND column_name    = 'requires_serial'
   AND condition_expr = 'catalogo.fn_articolo_usato($1::uuid)';

SELECT ok(
    NOT ('requires_serial' = ANY (catalogo.fn_articolo_colonne_struttura())),
    '11) una regola spenta esce dalla sede');

SELECT throws_like(
    format($$SELECT catalogo.fn_articolo_correggi_struttura(%L, '{"requires_serial": true}'::jsonb)$$,
           (SELECT u FROM _art)),
    '%non correggibili%requires_serial%',
    '12) ... e il verbo non la accetta piu''');

SELECT * FROM finish();
ROLLBACK;
