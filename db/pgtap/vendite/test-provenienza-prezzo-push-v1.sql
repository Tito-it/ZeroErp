-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la provenienza del prezzo viaggia col prezzo nel push (R-3) e una riga
--   di listino citata da un documento e' «propagata» (D-4).
-- Riferimento: brief-db-provenienza-prezzo-segue-il-prezzo §8.7 (giro 2), §8.5
--   (D-4 di Tid, 2026-11-13); changeSet 20261113-13 … -22.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - il contesto del resolver si legge con le chiavi del risultato del
--     resolver, e conta solo per un'origine da listino
--     (vendite.fn_provenienza_prezzo_esplosa);
--   - i cinque lister restituiscono le dieci colonne della provenienza della
--     riga di commessa, e girano;
--   - l'ordine restituisce la provenienza della sua riga; la riga scritta a mano
--     esce MANUALE, senza listino;
--   - la bolla senza prezzo prende prezzo E provenienza dalla riga d'ordine
--     (stesso COALESCE, F-4);
--   - vendite.fn_contratti_addebiti_maturati e' la proiezione di
--     vendite.fn_contratti_addebiti_maturati_con_provenienza;
--   - una riga di listino citata da una riga d'ordine o da una riga di
--     preventivo in bozza non si rettifica e non si cancella
--     (E_RIGA_LISTINO_PROPAGATA); una non citata si'.
--
-- Elenco test (plan 14):
--   1) il contesto da listino si legge con le chiavi del resolver
--   2) con MANUALE il contesto non conta
--   3) i cinque lister hanno in coda le dieci colonne della provenienza
--   4) i cinque lister e le due funzioni dei contratti girano
--   5) la vecchia funzione dei contratti e' la proiezione della nuova (stesse righe)
--   6) ordine: la riga da listino esce con origine, riga, versione e contesto
--   7) ordine: la riga scritta a mano esce MANUALE, senza listino ne' contesto
--   8) bolla senza prezzo: prezzo e provenienza della riga d'ordine
--   9) la riga di listino citata da un ordine non si rettifica (propagata)
--  10) e non si cancella
--  11) la riga di listino citata da un preventivo IN BOZZA non si rettifica
--  12) una riga di listino che nessuno cita si rettifica
--  13) il guard di stato guarda le dieci tabelle dei documenti
--  14) la riga di listino non esce piu' dal meta del push dei contratti
--
-- ⚠️ Il test 5 confronta le righe che i contratti di questo database danno:
--   e' la forma della proiezione (stesse colonne, stesse righe), non la
--   regola dei rami. Su un database senza contratti e' vero per costruzione;
--   la regola dei rami la provano i test dei contratti in commessa.
-- ⚠️ D-4 sui componenti: stesso ramo UNION ALL delle righe principali, presidiato
--   dalla forma (test 13), non da un kit costruito.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

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
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_u), 'provenienza push');

-- a1 (da listino), a2 (a mano), a3 (il preventivo in bozza), a4 (nessuno lo cita).
CREATE TEMP TABLE t_art AS
SELECT dbops.fn_pgtap_crea_articolo(('PGT-PPU-1' || substr(md5(clock_timestamp()::text), 1, 10))::varchar, false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM t_l)) AS a1,
       dbops.fn_pgtap_crea_articolo(('PGT-PPU-2' || substr(md5(clock_timestamp()::text), 1, 10))::varchar, false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM t_l)) AS a2,
       dbops.fn_pgtap_crea_articolo(('PGT-PPU-3' || substr(md5(clock_timestamp()::text), 1, 10))::varchar, false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM t_l)) AS a3,
       dbops.fn_pgtap_crea_articolo(('PGT-PPU-4' || substr(md5(clock_timestamp()::text), 1, 10))::varchar, false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM t_l)) AS a4;

CREATE TEMP TABLE t_r AS
WITH ins AS (
    INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
    SELECT (SELECT listino_versione_id FROM t_l), a.id, a.uom_id, 50.00
      FROM catalogo.articoli a
     WHERE a.id IN ((SELECT a1 FROM t_art), (SELECT a3 FROM t_art), (SELECT a4 FROM t_art))
    RETURNING id, articolo_id
)
SELECT (SELECT id FROM ins WHERE articolo_id = (SELECT a1 FROM t_art)) AS r1,
       (SELECT id FROM ins WHERE articolo_id = (SELECT a3 FROM t_art)) AS r3,
       (SELECT id FROM ins WHERE articolo_id = (SELECT a4 FROM t_art)) AS r4;

-- Il contesto del resolver che il pricing gate scriverebbe.
CREATE TEMP TABLE t_ctx AS
SELECT jsonb_build_object('prezzo_base_snapshot', 55, 'tipo_variazione_applicata', 'PERCENTUALE',
                          'valore_variazione_applicata', -9.0909, 'categoria_cliente_id_snapshot', NULL,
                          'listino_id', 0) AS ctx;

-- Dichiara la provenienza da listino (R1) sulle righe di a1 di un documento in bozza.
CREATE OR REPLACE FUNCTION pg_temp.da_listino(p_tab regclass, p_fk text, p_doc bigint, p_art uuid, p_riga bigint)
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    EXECUTE format(
        'UPDATE %s SET origine_prezzo = %L, listino_versione_id = %s, listino_riga_id = %s,
                       prezzo_resolver_context = %L::jsonb
          WHERE %I = %s AND articolo_id = %L::uuid',
        p_tab, 'CATEGORIA', (SELECT listino_versione_id FROM t_l), p_riga,
        (SELECT ctx FROM t_ctx)::text, p_fk, p_doc, p_art);
END $f$;

-- O1: trigger CONFERMATO, due righe: a1 da listino, a2 a mano.
CREATE TEMP TABLE t_o1 AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe(
    'provenienza push O1', 'DRAFT', p_fatturazione_trigger => 'CONFERMATO',
    p_righe => jsonb_build_array(
        jsonb_build_object('articolo_id', (SELECT a1 FROM t_art), 'quantita', 2, 'prezzo', 50),
        jsonb_build_object('articolo_id', (SELECT a2 FROM t_art), 'quantita', 1, 'prezzo', 33)));
SELECT pg_temp.da_listino('vendite.ordini_righe', 'ordine_id', (SELECT ordine_id FROM t_o1), (SELECT a1 FROM t_art),
                          (SELECT r1 FROM t_r));
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ordini', (SELECT ordine_id FROM t_o1), 'CONFERMATO');

-- O2: trigger SPEDITO, a1 da listino; la bolla nasce dall'ordine e perde in bozza
-- il prezzo che la madre copia: il prezzo, e la provenienza, li da' la riga d'ordine.
CREATE TEMP TABLE t_o2 AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe(
    'provenienza push O2', 'DRAFT', p_fatturazione_trigger => 'SPEDITO',
    p_quantita => 3, p_prezzo => 50, p_articolo_id => (SELECT a1 FROM t_art));
SELECT pg_temp.da_listino('vendite.ordini_righe', 'ordine_id', (SELECT ordine_id FROM t_o2), (SELECT a1 FROM t_art),
                          (SELECT r1 FROM t_r));
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ordini', (SELECT ordine_id FROM t_o2), 'CONFERMATO');

CREATE TEMP TABLE t_d AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('provenienza push DDT', 'DRAFT',
    p_ordine_id => (SELECT ordine_id FROM t_o2));
UPDATE vendite.ddt_righe SET prezzo_unitario = NULL WHERE ddt_id = (SELECT ddt_id FROM t_d);
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', (SELECT ddt_id FROM t_d), 'SPEDITO');

-- Il preventivo in bozza che cita R3.
CREATE TEMP TABLE t_p AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo_con_righe('provenienza push P', 'DRAFT',
    p_prezzo => 50, p_articolo_id => (SELECT a3 FROM t_art));
SELECT pg_temp.da_listino('vendite.preventivi_righe', 'preventivo_id', (SELECT preventivo_id FROM t_p),
                          (SELECT a3 FROM t_art), (SELECT r3 FROM t_r));

-- ============================================================
-- 1-2) La traduzione del contesto
-- ============================================================
SELECT is(
    (SELECT row(e.*)::text FROM vendite.fn_provenienza_prezzo_esplosa(
        'CATEGORIA', 7, 8,
        '{"prezzo_base_snapshot": 55, "tipo_variazione_applicata": "PERCENTUALE",
          "valore_variazione_applicata": -9.0909, "promo_id": 3, "contratto_id": 4,
          "categoria_cliente_id_snapshot": 5, "classe_utenza_id_snapshot": 6, "esito_codice": null}'::jsonb) e),
    '(CATEGORIA,7,8,55,PERCENTUALE,-9.0909,3,4,5,6)',
    '1) contesto da listino: le chiavi del resolver nelle dieci colonne (contratto_id come prezzo_contratto_id)'
);

SELECT is(
    (SELECT row(e.*)::text FROM vendite.fn_provenienza_prezzo_esplosa(
        'MANUALE', NULL, NULL, '{"prezzo_base_snapshot": 55, "promo_id": 3}'::jsonb) e),
    '(MANUALE,,,,,,,,,)',
    '2) MANUALE: il contesto non conta'
);

-- ============================================================
-- 3-5) La forma
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_proc p
      WHERE p.pronamespace = 'vendite'::regnamespace
        AND p.proname IN ('fn_list_preventivi_da_pushare', 'fn_list_ordini_da_pushare', 'fn_list_ddt_da_pushare',
                          'fn_list_contratti_da_pushare', 'fn_list_consumi_da_pushare')
        AND pg_get_function_result(p.oid) LIKE
            '%origine_prezzo character varying, listino_versione_id bigint, listino_riga_id bigint, '
            'prezzo_base_snapshot numeric, tipo_variazione_applicata character varying, '
            'valore_variazione_applicata numeric, promo_id bigint, prezzo_contratto_id bigint, '
            'categoria_cliente_id_snapshot smallint, classe_utenza_id_snapshot integer)'),
    5,
    '3) i cinque lister hanno in coda le dieci colonne della provenienza'
);

SELECT lives_ok(
    $$SELECT (SELECT count(*) FROM vendite.fn_list_preventivi_da_pushare())
           + (SELECT count(*) FROM vendite.fn_list_ordini_da_pushare())
           + (SELECT count(*) FROM vendite.fn_list_ddt_da_pushare())
           + (SELECT count(*) FROM vendite.fn_list_contratti_da_pushare())
           + (SELECT count(*) FROM vendite.fn_list_consumi_da_pushare())
           + (SELECT count(*) FROM vendite.fn_contratti_addebiti_maturati())
           + (SELECT count(*) FROM vendite.fn_contratti_addebiti_maturati_con_provenienza())$$,
    '4) i cinque lister e le due funzioni dei contratti girano'
);

SELECT is(
    (SELECT count(*)::int FROM (
        (SELECT contratto_id, riga_id, segment_key, articolo_id, quantita, prezzo_snapshot, prezzo_bloccato, meta, ramo, scarto
           FROM vendite.fn_contratti_addebiti_maturati()
         EXCEPT ALL
         SELECT contratto_id, riga_id, segment_key, articolo_id, quantita, prezzo_snapshot, prezzo_bloccato, meta, ramo, scarto
           FROM vendite.fn_contratti_addebiti_maturati_con_provenienza())
        UNION ALL
        (SELECT contratto_id, riga_id, segment_key, articolo_id, quantita, prezzo_snapshot, prezzo_bloccato, meta, ramo, scarto
           FROM vendite.fn_contratti_addebiti_maturati_con_provenienza()
         EXCEPT ALL
         SELECT contratto_id, riga_id, segment_key, articolo_id, quantita, prezzo_snapshot, prezzo_bloccato, meta, ramo, scarto
           FROM vendite.fn_contratti_addebiti_maturati())) d),
    0,
    '5) la vecchia funzione dei contratti da'' le stesse righe della nuova, senza la provenienza'
);

-- ============================================================
-- 6-8) Il push porta la provenienza
-- ============================================================
SELECT is(
    (SELECT l.origine_prezzo || '|' || (l.listino_riga_id = (SELECT r1 FROM t_r))::text || '|'
            || (l.listino_versione_id = (SELECT listino_versione_id FROM t_l))::text || '|'
            || l.prezzo_base_snapshot::text || '|' || l.tipo_variazione_applicata
       FROM vendite.fn_list_ordini_da_pushare(p_ordine_id := (SELECT ordine_id FROM t_o1)) l
      WHERE l.articolo_id = (SELECT a1 FROM t_art)),
    'CATEGORIA|true|true|55|PERCENTUALE',
    '6) ordine: la riga da listino esce con origine, riga, versione e contesto'
);

SELECT is(
    (SELECT l.origine_prezzo || '|' || coalesce(l.listino_riga_id::text, '-') || '|'
            || coalesce(l.prezzo_base_snapshot::text, '-')
       FROM vendite.fn_list_ordini_da_pushare(p_ordine_id := (SELECT ordine_id FROM t_o1)) l
      WHERE l.articolo_id = (SELECT a2 FROM t_art)),
    'MANUALE|-|-',
    '7) ordine: la riga scritta a mano esce MANUALE, senza listino ne'' contesto'
);

SELECT is(
    (SELECT (l.prezzo_snapshot = 50)::text || '|' || l.origine_prezzo || '|'
            || (l.listino_riga_id = (SELECT r1 FROM t_r))::text
       FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL, (SELECT ddt_id FROM t_d)) l),
    'true|CATEGORIA|true',
    '8) bolla senza prezzo: prezzo e provenienza della riga d''ordine (F-4)'
);

-- ============================================================
-- 9-13) D-4: la riga di listino citata da un documento e' propagata
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.listini_righe SET prezzo = 51 WHERE id = %s', (SELECT r1 FROM t_r))),
    'E_RIGA_LISTINO_PROPAGATA',
    '9) la riga di listino citata da un ordine non si rettifica'
);

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'DELETE FROM vendite.listini_righe WHERE id = %s', (SELECT r1 FROM t_r))),
    'E_RIGA_LISTINO_PROPAGATA',
    '10) e non si cancella'
);

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.listini_righe SET prezzo = 51 WHERE id = %s', (SELECT r3 FROM t_r))),
    'E_RIGA_LISTINO_PROPAGATA',
    '11) la riga di listino citata da un preventivo in bozza non si rettifica'
);

SELECT lives_ok(
    format('UPDATE vendite.listini_righe SET prezzo = 51 WHERE id = %s', (SELECT r4 FROM t_r)),
    '12) una riga di listino che nessuno cita si rettifica'
);

SELECT is(
    (SELECT count(*)::int
       FROM unnest(ARRAY['preventivi_righe', 'preventivi_righe_componenti', 'ordini_righe',
                         'ordini_righe_componenti', 'contratti_righe', 'contratti_righe_componenti',
                         'ddt_righe', 'ddt_righe_componenti', 'offerte_commerciali_eccezioni',
                         'offerte_commerciali_eccezioni_componenti']) t
      WHERE pg_get_functiondef('vendite.trgfn_listini_righe_guard_stato'::regproc)
            ~ ('FROM vendite\.' || t || '\s+WHERE listino_riga_id = OLD\.id')),
    10,
    '13) il guard di stato guarda le righe e i componenti dei cinque documenti'
);

-- ============================================================
-- 14) D-3: la riga di listino non sta nel meta del push dei contratti
-- ============================================================
SELECT ok(
    pg_get_functiondef('vendite.fn_contratti_addebiti_maturati_con_provenienza(date,bigint,bigint)'::regprocedure)
        NOT LIKE $$%'listino_riga_id',%$$,
    '14) la riga di listino non esce piu'' dal meta del push dei contratti'
);

SELECT * FROM finish();
ROLLBACK;
