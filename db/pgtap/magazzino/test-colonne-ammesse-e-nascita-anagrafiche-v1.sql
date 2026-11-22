-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Le colonne ammesse delle anagrafiche di magazzino e i BB di nascita che le
-- leggono:
--   magazzino.fn_{magazzini,ubicazioni,lotti,assets}_colonne_ammesse (20261122-01)
--   magazzino.fn_crea_magazzino che legge la lista                  (20261122-02)
--   magazzino.fn_crea_ubicazione, fn_crea_lotto, fn_crea_asset       (20261122-03 … -05)
--   Brief: brief-db-magazzino-tutte-le-scritture-dal-verbo, D-M2, D-M4, D-M7.
--
-- ⭐ Il caso si COSTRUISCE: un operatore costruito in sessione, con TUTTO
--   sull'area magazzino (scelta del test), il suo magazzino dal builder, gli
--   articoli dal builder (uno a lotti, uno a seriale).
--   ⚠️ I BB sono INVOKER e le tabelle sono chiuse all'applicazione (Lotto 1,
--   90_end/20261122-10): la nascita si prova dai verbi fn_aggiungi_*, che
--   chiamano i BB. Le regole sono quelle dei BB, la strada e' quella dell'app.
--
-- Elenco test (plan 22):
--   le liste
--    1-4) ogni colonna di ogni lista, nei due gesti, esiste nella sua tabella
--    5) nessuna lista nomina una colonna di sistema o l'emittente
--    6) nessuna lista nomina l'identita' della nascita (magazzino_id, articolo_id)
--    7) attivo: in modifica si', alla nascita no (magazzini, ubicazioni, lotti)
--    8) il seriale non ha colonne da modificare
--    9) un gesto sbagliato: E_SCRIPT_CHIAMATA_NON_VALIDA
--   la forma dei BB
--   10) fn_crea_magazzino legge la lista e non ha piu' la sua costante
--   11) i tre BB nuovi sono INVOKER, e leggono la loro lista
--   il caso felice
--   12) ubicazione: nasce nel magazzino indicato, coi campi di p_campi
--   13) ... e nasce attiva
--   14) lotto: nasce sull'articolo, con la scadenza di p_campi
--   15) seriale: l'emittente e' quello della sessione
--   16) magazzino: la lista di oggi da' ancora usa_ubicazioni fra i campi
--   i rifiuti
--   17) ubicazione con attivo fra i campi: E_CAMPO_NON_AMMESSO
--   18) ubicazione con magazzino_id fra i campi: E_CAMPO_NON_AMMESSO
--   19) lotto con articolo_id fra i campi: E_CAMPO_NON_AMMESSO
--   20) seriale con emittente_fiscale_id fra i campi: E_CAMPO_NON_AMMESSO
--   21) campi che non sono un oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA
--   22) magazzino con attivo fra i campi: E_CAMPO_NON_AMMESSO, come prima
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(22);

CREATE TEMP TABLE t_op AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM t_op)); END $ctx$;
INSERT INTO config.user_override_aree (auth_user_id, area_id, livello, motivo)
SELECT o.auth_user_id, af.id, 'TUTTO', 'pgTAP: nascita delle anagrafiche dai verbi'
  FROM t_op o, config.aree_funzionali af
 WHERE af.schema_db = 'magazzino';


CREATE OR REPLACE FUNCTION pg_temp.corpo(p regprocedure) RETURNS text
LANGUAGE sql AS $$
    SELECT regexp_replace(p2.prosrc, '--[^\n]*', '', 'g') FROM pg_proc p2 WHERE p2.oid = p
$$;

-- Le colonne delle liste che la tabella non ha, nei due gesti.
CREATE OR REPLACE FUNCTION pg_temp.fuori_tabella(p_tabella regclass, p_lista text[]) RETURNS text[]
LANGUAGE sql AS $$
    SELECT COALESCE(array_agg(c ORDER BY c), ARRAY[]::text[])
      FROM unnest(p_lista) AS c
     WHERE NOT EXISTS (SELECT 1 FROM pg_attribute a
                        WHERE a.attrelid = p_tabella AND a.attname = c
                          AND a.attnum > 0 AND NOT a.attisdropped)
$$;

CREATE TEMP TABLE t_liste AS
SELECT 'magazzino.magazzini'::regclass AS tab,
       magazzino.fn_magazzini_colonne_ammesse('crea')     AS crea,
       magazzino.fn_magazzini_colonne_ammesse('modifica') AS modifica
UNION ALL
SELECT 'magazzino.ubicazioni', magazzino.fn_ubicazioni_colonne_ammesse('crea'),
       magazzino.fn_ubicazioni_colonne_ammesse('modifica')
UNION ALL
SELECT 'magazzino.lotti', magazzino.fn_lotti_colonne_ammesse('crea'),
       magazzino.fn_lotti_colonne_ammesse('modifica')
UNION ALL
SELECT 'magazzino.assets', magazzino.fn_assets_colonne_ammesse('crea'),
       magazzino.fn_assets_colonne_ammesse('modifica');

-- I soggetti: un magazzino con le ubicazioni, un articolo a lotti, uno a seriale.
CREATE TEMP TABLE t_f AS
SELECT dbops.fn_pgtap_crea_magazzino('PGT-NAS-MAG', true)                    AS mag,
       dbops.fn_pgtap_crea_articolo('PGT-NAS-LOTTI',   true, true,  false)   AS art_lotti,
       dbops.fn_pgtap_crea_articolo('PGT-NAS-SERIALE', true, false, true)    AS art_ser,
       (SELECT t.id FROM config.tipi_ubicazione t WHERE t.attivo ORDER BY t.id LIMIT 1) AS tipo,
       (SELECT s.id FROM config.stati_assets s WHERE s.attivo ORDER BY s.id LIMIT 1)    AS stato,
       (SELECT o.id FROM config.assets_ownership o WHERE o.attivo ORDER BY o.id LIMIT 1) AS prop,
       script.fn_pgtap_emittente_operatore()                                  AS ef;

CREATE TEMP TABLE t_g AS
SELECT magazzino.fn_aggiungi_ubicazione(f.mag, 'PGT-NAS-U1', f.tipo,
                                    '{"descrizione": "Ubicazione di prova", "corsia": "A"}'::jsonb) AS ubi,
       magazzino.fn_aggiungi_lotto(f.art_lotti, 'PGT-NAS-L1', DATE '2026-11-01',
                               '{"data_scadenza": "2027-11-01"}'::jsonb)                          AS lotto,
       magazzino.fn_aggiungi_asset(f.art_ser, 'PGT-NAS-SN1', f.stato, f.prop)                     AS asset
  FROM t_f f;

-- ============================================================
-- Le liste
-- ============================================================
SELECT is(pg_temp.fuori_tabella(l.tab, l.crea || l.modifica), ARRAY[]::text[],
          format('%s. le colonne ammesse di %s esistono nella tabella', n, l.tab))
  FROM (SELECT l.*, row_number() OVER (ORDER BY l.tab::text) AS n FROM t_liste l) l
 ORDER BY n;

SELECT is(
    (SELECT COALESCE(array_agg(DISTINCT c ORDER BY c), ARRAY[]::text[])
       FROM t_liste l, unnest(l.crea || l.modifica) AS c
      WHERE c = ANY (ARRAY['id', 'uid', 'data_insert', 'user_insert', 'data_update',
                           'user_update', 'tx_id', 'storicizza', 'emittente_fiscale_id'])),
    ARRAY[]::text[],
    '5. nessuna lista nomina una colonna di sistema o l''emittente');

SELECT is(
    (SELECT COALESCE(array_agg(DISTINCT c ORDER BY c), ARRAY[]::text[])
       FROM t_liste l, unnest(l.crea || l.modifica) AS c
      WHERE c IN ('magazzino_id', 'articolo_id')),
    ARRAY[]::text[],
    '6. nessuna lista nomina l''identita'' della nascita');

SELECT is(
    (SELECT array_agg(format('%s:%s:%s', l.tab, 'attivo' = ANY (l.crea), 'attivo' = ANY (l.modifica))
                      ORDER BY l.tab::text)
       FROM t_liste l WHERE l.tab <> 'magazzino.assets'::regclass),
    ARRAY['magazzino.lotti:f:t', 'magazzino.magazzini:f:t',
          'magazzino.ubicazioni:f:t'],
    '7. attivo: in modifica si'', alla nascita no');

SELECT is(magazzino.fn_assets_colonne_ammesse('modifica'), ARRAY[]::text[],
          '8. il seriale non ha colonne da modificare');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_lotti_colonne_ammesse('cancella')$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '9. un gesto sbagliato: E_SCRIPT_CHIAMATA_NON_VALIDA');

-- ============================================================
-- La forma dei BB
-- ============================================================
SELECT ok(
    pg_temp.corpo('magazzino.fn_crea_magazzino(character varying, character varying, bigint, jsonb, bigint)'::regprocedure)
        ~ 'magazzino\.fn_magazzini_colonne_ammesse\(''crea''\)'
    AND pg_temp.corpo('magazzino.fn_crea_magazzino(character varying, character varying, bigint, jsonb, bigint)'::regprocedure)
        !~ 'c_ammesse',
    '10. fn_crea_magazzino legge la lista e non ha piu'' la sua costante');

SELECT is(
    (SELECT array_agg(format('%s:%s:%s', p.proname, p.prosecdef,
                             pg_temp.corpo(p.oid::regprocedure) ~ ('magazzino\.fn_' ||
                                 CASE p.proname WHEN 'fn_crea_ubicazione' THEN 'ubicazioni'
                                                WHEN 'fn_crea_lotto'      THEN 'lotti'
                                                ELSE 'assets' END || '_colonne_ammesse\(''crea''\)'))
                      ORDER BY p.proname)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'magazzino'
        AND p.proname IN ('fn_crea_ubicazione', 'fn_crea_lotto', 'fn_crea_asset')),
    ARRAY['fn_crea_asset:f:t', 'fn_crea_lotto:f:t', 'fn_crea_ubicazione:f:t'],
    '11. i tre BB nuovi sono INVOKER, e leggono la loro lista');

-- ============================================================
-- Il caso felice
-- ============================================================
SELECT is((SELECT format('%s|%s|%s', u.magazzino_id = f.mag, u.descrizione, u.corsia)
             FROM t_g g CROSS JOIN t_f f JOIN magazzino.ubicazioni u ON u.id = g.ubi),
          't|Ubicazione di prova|A',
          '12. ubicazione: nasce nel magazzino indicato, coi campi di p_campi');

SELECT ok((SELECT u.attivo FROM t_g g JOIN magazzino.ubicazioni u ON u.id = g.ubi),
          '13. ... e nasce attiva');

SELECT is((SELECT format('%s|%s', l.articolo_id = f.art_lotti, l.data_scadenza)
             FROM t_g g CROSS JOIN t_f f JOIN magazzino.lotti l ON l.id = g.lotto),
          't|2027-11-01',
          '14. lotto: nasce sull''articolo, con la scadenza di p_campi');

SELECT is((SELECT a.emittente_fiscale_id FROM t_g g JOIN magazzino.assets a ON a.id = g.asset),
          (SELECT ef FROM t_f),
          '15. seriale: l''emittente e'' quello della sessione');

SELECT ok(
    (SELECT mg.usa_ubicazioni FROM t_f f JOIN magazzino.magazzini mg ON mg.id = f.mag),
    '16. magazzino: la lista di oggi da'' ancora usa_ubicazioni fra i campi');

-- ============================================================
-- I rifiuti
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_ubicazione(
        (SELECT mag FROM t_f), 'PGT-NAS-UX', (SELECT tipo FROM t_f), '{"attivo": false}'::jsonb)$$),
    'E_CAMPO_NON_AMMESSO',
    '17. ubicazione con attivo fra i campi: E_CAMPO_NON_AMMESSO');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_ubicazione(
        (SELECT mag FROM t_f), 'PGT-NAS-UY', (SELECT tipo FROM t_f),
        jsonb_build_object('magazzino_id', (SELECT mag FROM t_f)))$$),
    'E_CAMPO_NON_AMMESSO',
    '18. ubicazione con magazzino_id fra i campi: E_CAMPO_NON_AMMESSO');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_lotto(
        (SELECT art_lotti FROM t_f), 'PGT-NAS-LX', DATE '2026-11-01',
        jsonb_build_object('articolo_id', (SELECT art_lotti FROM t_f)))$$),
    'E_CAMPO_NON_AMMESSO',
    '19. lotto con articolo_id fra i campi: E_CAMPO_NON_AMMESSO');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_asset(
        (SELECT art_ser FROM t_f), 'PGT-NAS-SNX', (SELECT stato FROM t_f), (SELECT prop FROM t_f),
        jsonb_build_object('emittente_fiscale_id', (SELECT ef FROM t_f)))$$),
    'E_CAMPO_NON_AMMESSO',
    '20. seriale con emittente_fiscale_id fra i campi: E_CAMPO_NON_AMMESSO');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_lotto(
        (SELECT art_lotti FROM t_f), 'PGT-NAS-LY', DATE '2026-11-01', '[]'::jsonb)$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '21. campi che non sono un oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_magazzino('PGT-NAS-MX', 'x',
        dbops.fn_pgtap_crea_indirizzo_dettaglio('PGT-NAS-MX'), '{"attivo": false}'::jsonb)$$),
    'E_CAMPO_NON_AMMESSO',
    '22. magazzino con attivo fra i campi: E_CAMPO_NON_AMMESSO, come prima');

SELECT * FROM finish();

ROLLBACK;
