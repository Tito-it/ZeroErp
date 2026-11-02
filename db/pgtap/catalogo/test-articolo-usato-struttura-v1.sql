-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2b, 20261019-87 … -99):
--   la natura merce ha destinazione ORDINE_VENDITA, il codice della sorgente (era ORDINE).
-- pgTAP test per Zero ERP
--
-- Un articolo USATO non cambia i flag che decidono come si vende e come sta a
-- magazzino; la correzione di un errore di caricamento passa solo dal verbo
-- amministratore. Gli articoli sono unici per tutte le aziende: l'uso conta
-- anche quando sta in un documento che chi modifica non vede.
-- Brief: brief-db-articoli-ammessi-per-documento (§8.6 A-10, §9.3 Lotto 3u)
-- ChangeSet: 20261013-47 -> -52
--
-- Elenco test (plan 17):
--  Il predicato (catalogo.fn_articolo_usato)
--   1) un articolo appena costruito non e' usato
--   2) in una riga di preventivo in bozza e' usato
--   3) la riga spenta (attivo = false) conta ancora: «in qualunque stato»
--  Il guard (catalogo.trgfn_articoli_guard_struttura_se_usato)
--   4) usato: is_solo_componente -> E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE
--   5) usato: natura_vendita_id -> rifiutato
--   6) usato: gestito_a_magazzino -> rifiutato
--   7) usato: iva_id resta libera
--   8) usato: la descrizione resta libera
--   9) non usato: is_solo_componente cambia
--  Il verbo amministratore (catalogo.fn_articolo_correggi_struttura)
--  10) chi non e' SUPER_ADMIN: E_PERMESSO_NEGATO
--  11) una colonna non correggibile: E_PARAMETRO_INVALIDO
--  12) il SUPER_ADMIN corregge la natura di un articolo usato
--  Il form (dbops.fn_non_editable_fields)
--  13) usato: natura_vendita_id spento
--  14) non usato: is_solo_componente acceso
--  Piu' aziende
--  15) l'articolo e' in un preventivo di un'altra azienda: il guard rifiuta lo
--      stesso (il predicato e' SECURITY DEFINER)
--  Il ritiro
--  16) il guard «solo componente in bozza» (20261013-44/-45) non c'e' piu'
--  La porta
--  17) la GUC accesa a mano non apre: serve il proprietario della tabella
--      ⚠️ rosso da owner, verde come app (da owner il proprietario c'e')
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _nat AS
SELECT (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'ORDINE_VENDITA' AND nv.attivo ORDER BY nv.id LIMIT 1)   AS merce,
       (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'COMMESSA' AND nv.attivo ORDER BY nv.id LIMIT 1) AS servizio;

CREATE TEMP TABLE _iva AS
SELECT (SELECT i.id FROM config.iva i WHERE i.attivo AND i.aliquota_iva > 0 ORDER BY i.id LIMIT 1)        AS id,
       (SELECT i.id FROM config.iva i WHERE i.attivo AND i.aliquota_iva > 0 ORDER BY i.id OFFSET 1 LIMIT 1) AS altra;

-- U: sara' usato. L: resta libero. X: usato da un'altra azienda.
CREATE TEMP TABLE _art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-AUS-U', false, p_natura_vendita_id => (SELECT merce FROM _nat)) AS u,
       dbops.fn_pgtap_crea_articolo('PGT-AUS-L', false, p_natura_vendita_id => (SELECT merce FROM _nat)) AS l,
       dbops.fn_pgtap_crea_articolo('PGT-AUS-X', false, p_natura_vendita_id => (SELECT merce FROM _nat)) AS x;

-- ============================================================
-- Il predicato (1-3)
-- ============================================================
SELECT is(catalogo.fn_articolo_usato((SELECT u FROM _art)), false,
    '1) un articolo appena costruito non e'' usato');

CREATE TEMP TABLE _prev AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgTAP articolo usato');

CREATE TEMP TABLE _pr AS
WITH ins AS (
    INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa)
    SELECT (SELECT preventivo_id FROM _prev), (SELECT u FROM _art), (SELECT id FROM _iva), 10, 1
    RETURNING id
)
SELECT * FROM ins;

SELECT is(catalogo.fn_articolo_usato((SELECT u FROM _art)), true,
    '2) in una riga di preventivo in bozza e'' usato');

UPDATE vendite.preventivi_righe SET attivo = false WHERE id = (SELECT id FROM _pr);

SELECT is(catalogo.fn_articolo_usato((SELECT u FROM _art)), true,
    '3) la riga spenta conta ancora: l''uso vale in qualunque stato');

-- ============================================================
-- Il guard (4-9)
-- ============================================================
SELECT throws_like(
    format($$UPDATE catalogo.articoli SET is_solo_componente = true WHERE id = %L$$, (SELECT u FROM _art)),
    '%già usato%',
    '4) usato: is_solo_componente non cambia (E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE)');

SELECT throws_like(
    format($$UPDATE catalogo.articoli SET natura_vendita_id = %s WHERE id = %L$$,
           (SELECT servizio FROM _nat), (SELECT u FROM _art)),
    '%già usato%',
    '5) usato: la natura di vendita non cambia');

SELECT throws_like(
    format($$UPDATE catalogo.articoli SET gestito_a_magazzino = true WHERE id = %L$$, (SELECT u FROM _art)),
    '%già usato%',
    '6) usato: «gestito a magazzino» non cambia');

SELECT lives_ok(
    format($$UPDATE catalogo.articoli SET iva_id = %s WHERE id = %L$$,
           COALESCE((SELECT altra FROM _iva), (SELECT id FROM _iva)), (SELECT u FROM _art)),
    '7) usato: l''aliquota IVA resta libera');

SELECT lives_ok(
    format($$UPDATE catalogo.articoli SET descrizione = 'pgTAP descrizione nuova' WHERE id = %L$$,
           (SELECT u FROM _art)),
    '8) usato: la descrizione resta libera');

SELECT lives_ok(
    format($$UPDATE catalogo.articoli SET is_solo_componente = true WHERE id = %L$$, (SELECT l FROM _art)),
    '9) non usato: is_solo_componente cambia');
UPDATE catalogo.articoli SET is_solo_componente = false WHERE id = (SELECT l FROM _art);

-- ============================================================
-- Il verbo amministratore (10-12)
-- ============================================================
SELECT throws_like(
    format($$SELECT catalogo.fn_articolo_correggi_struttura(%L, '{"is_solo_componente": true}'::jsonb)$$,
           (SELECT u FROM _art)),
    '%permessi%',
    '10) chi non e'' SUPER_ADMIN non corregge: E_PERMESSO_NEGATO');

-- Come SUPER_ADMIN, per i due casi del verbo: il contesto si rimette dopo.
CREATE TEMP TABLE _ctx AS SELECT current_setting('app.current_user_id', true) AS prima;
CREATE TEMP TABLE _sa AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-articolo-usato', true);
DO $sa$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _sa)); END $sa$;

SELECT throws_like(
    format($$SELECT catalogo.fn_articolo_correggi_struttura(%L, '{"descrizione": "x"}'::jsonb)$$,
           (SELECT u FROM _art)),
    '%non correggibili%',
    '11) una colonna fuori dalle otto: E_PARAMETRO_INVALIDO');

SELECT catalogo.fn_articolo_correggi_struttura(
    (SELECT u FROM _art), jsonb_build_object('natura_vendita_id', (SELECT servizio FROM _nat)));

SELECT is((SELECT natura_vendita_id FROM catalogo.articoli WHERE id = (SELECT u FROM _art)),
          (SELECT servizio FROM _nat),
    '12) il SUPER_ADMIN corregge la natura di un articolo usato');

DO $back$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT prima FROM _ctx)::integer); END $back$;

-- ============================================================
-- Il form (13-14)
-- ============================================================
SELECT ok(
    'natura_vendita_id' = ANY (dbops.fn_non_editable_fields('catalogo', 'articoli', (SELECT u FROM _art)::text)),
    '13) usato: il form spegne la natura di vendita');

SELECT ok(
    NOT ('is_solo_componente' = ANY (dbops.fn_non_editable_fields('catalogo', 'articoli', (SELECT l FROM _art)::text))),
    '14) non usato: il form lascia acceso is_solo_componente');

-- ============================================================
-- Piu' aziende (15)
-- ============================================================
-- X va in un preventivo di un'ALTRA azienda: chi modifica l'articolo non lo vede.
CREATE TEMP TABLE _b AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $b$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _b)); END $b$;
CREATE TEMP TABLE _prev_b AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgTAP articolo usato altra azienda');
INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa)
SELECT (SELECT preventivo_id FROM _prev_b), (SELECT x FROM _art), (SELECT id FROM _iva), 10, 1;
DO $a$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT prima FROM _ctx)::integer); END $a$;

SELECT throws_like(
    format($$UPDATE catalogo.articoli SET is_solo_componente = true WHERE id = %L$$, (SELECT x FROM _art)),
    '%già usato%',
    '15) usato in un documento di un''altra azienda: il guard rifiuta lo stesso');

-- ============================================================
-- Il ritiro (16)
-- ============================================================
SELECT ok(
    NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_articoli_a10_guard_solo_componente_in_bozza_upd')
    AND to_regprocedure('catalogo.trgfn_articoli_guard_solo_componente_in_bozza()') IS NULL,
    '16) il guard «solo componente in bozza» e la sua funzione non ci sono piu''');

-- ============================================================
-- La porta (17) — per ultima: da owner e' rossa per costruzione
-- ============================================================
SELECT throws_like(
    format($f$DO $p$ BEGIN
               PERFORM set_config('zeroerp.articolo_correggi_struttura', %L, true);
               UPDATE catalogo.articoli SET is_solo_componente = true WHERE id = %L;
             END $p$$f$,
           (SELECT u FROM _art), (SELECT u FROM _art)),
    '%già usato%',
    '17) la GUC accesa a mano non apre la porta: serve il proprietario (rosso da owner, verde come app)');

SELECT * FROM finish();
ROLLBACK;
