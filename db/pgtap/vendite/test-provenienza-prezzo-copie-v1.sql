-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la provenienza del prezzo si copia col prezzo da un documento
--   all'altro (R-4), e versione e riga di listino dei componenti stanno nelle
--   colonne, non nel contesto (D-3).
-- Riferimento: brief-db-provenienza-prezzo-segue-il-prezzo §8.8 (giro 3);
--   changeSet 20261113-23 … -37.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - un override di componente e' un prezzo (MANUALE) o un oggetto che porta la
--     sua provenienza (vendite.fn_componente_override);
--   - il contesto salvato dal resolver non ha le chiavi che hanno una colonna
--     (vendite.fn_prezzo_resolver_contesto);
--   - la revisione del preventivo copia la provenienza delle righe;
--   - la bolla generata dall'ordine copia la provenienza delle righe;
--   - le sette funzioni di copia scrivono le colonne della provenienza, le cinque
--     init passano dai due building block e non scrivono piu' la riga di listino
--     nel contesto;
--   - nessun componente tiene piu' versione, riga, listino o origine nel contesto.
--
-- Elenco test (plan 8):
--   1) override: un numero e un testo sono MANUALE; un oggetto porta la provenienza
--   2) il contesto del resolver senza prezzo, origine, versione, riga ed esito
--   3) revisione del preventivo: la riga nuova ha la provenienza della vecchia
--   4) bolla dall'ordine: la riga ha la provenienza della riga d'ordine
--   5) le sette funzioni di copia scrivono le quattro colonne della provenienza
--   6) le cinque init leggono l'override e il contesto dai building block
--   7) le cinque init non scrivono piu' la riga di listino nel contesto
--   8) nessun componente tiene versione, riga, listino o origine nel contesto
--
-- ⚠️ I componenti di un kit copiati con l'override-oggetto (preventivo -> ordine)
--   non si costruiscono qui (un kit con distinta e listino): li presidiano la
--   forma (6) e la funzione pura (1).
-- ⚠️ Il test 8 conta i cattivi sulle righe che ci sono: su un database da zero
--   e' vero per costruzione; il caso costruito e' il 7 (nessuno li scrive piu').
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM t_mondo));
END $ctx$;

CREATE TEMP TABLE t_u AS
SELECT min(u.id) AS utility_id
  FROM config.utilities u
 WHERE EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                WHERE ltu.utility_id = u.id AND ltu.attivo);

CREATE TEMP TABLE t_l AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_u), 'provenienza copie');

CREATE TEMP TABLE t_art AS
SELECT dbops.fn_pgtap_crea_articolo(('PGT-PCO-' || substr(md5(clock_timestamp()::text), 1, 10))::varchar, false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM t_l)) AS a1;

CREATE TEMP TABLE t_r AS
WITH ins AS (
    INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
    SELECT (SELECT listino_versione_id FROM t_l), a.id, a.uom_id, 50.00
      FROM catalogo.articoli a WHERE a.id = (SELECT a1 FROM t_art)
    RETURNING id
)
SELECT id AS r1 FROM ins;

CREATE OR REPLACE FUNCTION pg_temp.da_listino(p_tab regclass, p_fk text, p_doc bigint)
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    EXECUTE format(
        'UPDATE %s SET origine_prezzo = %L, listino_versione_id = %s, listino_riga_id = %s,
                       prezzo_resolver_context = %L::jsonb
          WHERE %I = %s',
        p_tab, 'CATEGORIA', (SELECT listino_versione_id FROM t_l), (SELECT r1 FROM t_r),
        '{"prezzo_base_snapshot": 50}', p_fk, p_doc);
END $f$;

-- Preventivo: in bozza la riga dichiara R1, poi EMESSO, poi la revisione.
CREATE TEMP TABLE t_p AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo_con_righe('provenienza copie P', 'DRAFT',
    p_prezzo => 50, p_articolo_id => (SELECT a1 FROM t_art));
SELECT pg_temp.da_listino('vendite.preventivi_righe', 'preventivo_id', (SELECT preventivo_id FROM t_p));
SELECT dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT preventivo_id FROM t_p), 'EMESSO');
CREATE TEMP TABLE t_rev AS
SELECT r.nuovo_preventivo_id AS id
  FROM vendite.fn_crea_revisione_preventivo((SELECT preventivo_id FROM t_p), NULL) r;

-- Ordine: in bozza la riga dichiara R1, poi confermato, poi la bolla.
CREATE TEMP TABLE t_o AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe(
    'provenienza copie O', 'DRAFT', p_fatturazione_trigger => 'SPEDITO',
    p_quantita => 2, p_prezzo => 50, p_articolo_id => (SELECT a1 FROM t_art));
SELECT pg_temp.da_listino('vendite.ordini_righe', 'ordine_id', (SELECT ordine_id FROM t_o));
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ordini', (SELECT ordine_id FROM t_o), 'CONFERMATO');
CREATE TEMP TABLE t_d AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('provenienza copie D', 'DRAFT',
    p_ordine_id => (SELECT ordine_id FROM t_o));

-- ============================================================
-- 1-2) Le due funzioni pure
-- ============================================================
SELECT is(
    ARRAY[
        (SELECT row(o.*)::text FROM vendite.fn_componente_override('12.5'::jsonb) o),
        (SELECT row(o.*)::text FROM vendite.fn_componente_override('"7"'::jsonb) o),
        (SELECT row(o.*)::text FROM vendite.fn_componente_override(
            '{"prezzo": 9, "origine_prezzo": "CATEGORIA", "listino_versione_id": 3, "listino_riga_id": 4,
              "prezzo_resolver_context": {"promo_id": 5}}'::jsonb) o),
        (SELECT row(o.*)::text FROM vendite.fn_componente_override('{"prezzo": 9}'::jsonb) o)
    ],
    ARRAY['(12.5,MANUALE,,,)', '(7,MANUALE,,,)', '(9,CATEGORIA,3,4,"{""promo_id"": 5}")', '(9,MANUALE,,,)'],
    '1) override: un numero e un testo sono MANUALE; un oggetto porta la provenienza che dichiara'
);

SELECT is(
    vendite.fn_prezzo_resolver_contesto(
        '{"prezzo_finale": 1, "origine": "CATEGORIA", "listino_versione_id": 2, "listino_riga_id": 3,
          "esito_codice": null, "esito_context": null, "esito_valori": null,
          "prezzo_base_snapshot": 4, "promo_id": 5, "contratto_id": 6}'::jsonb),
    '{"prezzo_base_snapshot": 4, "promo_id": 5, "contratto_id": 6}'::jsonb,
    '2) il contesto del resolver senza prezzo, origine, versione, riga ed esito'
);

-- ============================================================
-- 3-4) Le copie, sul percorso vero
-- ============================================================
SELECT is(
    (SELECT r.origine_prezzo || '|' || (r.listino_riga_id = (SELECT r1 FROM t_r))::text || '|'
            || (r.prezzo_resolver_context ->> 'prezzo_base_snapshot')
       FROM vendite.preventivi_righe r
      WHERE r.preventivo_id = (SELECT id FROM t_rev)),
    'CATEGORIA|true|50',
    '3) revisione del preventivo: la riga nuova ha la provenienza della vecchia'
);

SELECT is(
    (SELECT r.origine_prezzo || '|' || (r.listino_riga_id = (SELECT r1 FROM t_r))::text || '|'
            || (r.listino_versione_id = (SELECT listino_versione_id FROM t_l))::text
       FROM vendite.ddt_righe r
      WHERE r.ddt_id = (SELECT ddt_id FROM t_d)),
    'CATEGORIA|true|true',
    '4) bolla dall''ordine: la riga ha la provenienza della riga d''ordine'
);

-- ============================================================
-- 5-8) La forma
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_proc p
      WHERE p.pronamespace = 'vendite'::regnamespace
        AND p.proname IN ('fn_crea_revisione_preventivo', 'fn_crea_revisione_offerta',
                          'fn_push_offerta_a_contratto', 'fn_push_preventivo_a_ordine',
                          'fn_genera_ordine_da_offerta', 'fn_genera_ddt_da_ordine',
                          'fn_genera_ddt_riconsegna')
        AND pg_get_functiondef(p.oid) ~ 'origine_prezzo,\s*listino_versione_id,\s*listino_riga_id,\s*prezzo_resolver_context'),
    7,
    '5) le sette funzioni di copia scrivono le quattro colonne della provenienza'
);

SELECT is(
    (SELECT count(*)::int FROM pg_proc p
      WHERE p.pronamespace = 'vendite'::regnamespace
        AND p.proname IN ('fn_preventivo_riga_componenti_init', 'fn_ordine_riga_componenti_init',
                          'fn_ddt_riga_componenti_init', 'fn_contratto_riga_componenti_init',
                          'fn_offerta_eccezione_componenti_init')
        AND pg_get_functiondef(p.oid) LIKE '%vendite.fn_componente_override(%'
        AND pg_get_functiondef(p.oid) LIKE '%vendite.fn_prezzo_resolver_contesto(to_jsonb(v_resolve))%'),
    5,
    '6) le cinque init leggono l''override e il contesto dai building block'
);

SELECT is(
    (SELECT count(*)::int FROM pg_proc p
      WHERE p.pronamespace = 'vendite'::regnamespace
        AND p.proname IN ('fn_preventivo_riga_componenti_init', 'fn_ordine_riga_componenti_init',
                          'fn_ddt_riga_componenti_init', 'fn_contratto_riga_componenti_init',
                          'fn_offerta_eccezione_componenti_init')
        AND pg_get_functiondef(p.oid) ~ $$'listino_riga_id',\s*v_resolve$$),
    0,
    '7) le cinque init non scrivono piu'' la riga di listino nel contesto'
);

SELECT is(
    (SELECT count(*)::int FROM (
        SELECT prezzo_resolver_context c FROM vendite.preventivi_righe_componenti
        UNION ALL SELECT prezzo_resolver_context FROM vendite.ordini_righe_componenti
        UNION ALL SELECT prezzo_resolver_context FROM vendite.contratti_righe_componenti
        UNION ALL SELECT prezzo_resolver_context FROM vendite.ddt_righe_componenti
        UNION ALL SELECT prezzo_resolver_context FROM vendite.offerte_commerciali_eccezioni_componenti) x
      WHERE jsonb_exists_any(x.c, ARRAY['listino_id', 'listino_versione_id', 'listino_riga_id', 'origine'])),
    0,
    '8) nessun componente tiene versione, riga, listino o origine nel contesto'
);

SELECT * FROM finish();
ROLLBACK;
