-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'ordine generato dall'offerta copia la provenienza del prezzo che le
--   righe espanse dell'offerta gli danno, e il kit col prezzo forzato tiene i
--   suoi componenti.
-- Riferimento: brief-db-provenienza-prezzo-segue-il-prezzo §8.16 (giro 5);
--   changeSet 20261120-13 … -17.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la riga presa dal listino dell'offerta e' CONTRATTO_LISTINO (il listino
--     fissato dal documento) con versione, riga di listino e, nel contesto, il
--     prezzo base e la variazione globale dell'offerta;
--   - la riga con l'OVERRIDE copia la provenienza dell'eccezione;
--   - il kit dal listino e' COMPONENTI, e i suoi componenti LISTINO_BUNDLE con la
--     versione e senza riga;
--   - il kit col prezzo forzato prende i componenti DELL'ECCEZIONE, ciascuno con
--     la sua provenienza: l'ordine vale il prezzo negoziato, non la somma del listino;
--   - il kit aggiunto (AGGIUNTA composita) prende anche lui i componenti dell'eccezione;
--   - ogni riga dell'ordine ha per numero la sua posizione fra le righe espanse.
--
-- ⭐ TUTTO COSTRUITO. Un listino con A e B semplici (100 e 60) e due kit K e K2
--   (2 x F1 a 10 + 1 x F2 a 30: 50 dal listino). L'offerta ha la variazione
--   globale PERCENTUALE -10, un OVERRIDE su B a 80, un OVERRIDE su K2 coi
--   componenti F1 negoziato a 20 (MANUALE) e F2 al prezzo del listino, 30, con la
--   provenienza LISTINO_BUNDLE (70), e il kit K3, fuori listino, in AGGIUNTA coi
--   componenti F1 a 15 e F2 a 5 (35). I numeri si leggono a mano.
-- ⚠️ F2 di K2 non e' MANUALE apposta: MANUALE e' anche il ripiego di
--   vendite.fn_componente_override quando l'override non porta l'origine, e con
--   due componenti MANUALE il test 8 non distinguerebbe la provenienza copiata da
--   quella persa.
--
-- Elenco test (plan 10):
--   1) la forma: la riga di listino in coda al nucleo, la provenienza in coda alle righe espanse
--   2) righe espanse: A dal listino con la sua provenienza
--   3) righe espanse: K2 forzato porta i componenti dell'eccezione, non quelli del listino
--   4) ordine, A: CONTRATTO_LISTINO, versione e riga di listino, 90
--   5) ordine, A: nel contesto prezzo base 100 e la variazione -10 %
--   6) ordine, B: la provenienza dell'eccezione (MANUALE, nessun listino), 80
--   7) ordine, K: il kit e' COMPONENTI a 50, i componenti LISTINO_BUNDLE con la versione, senza riga
--   8) ordine, K2: il kit vale il prezzo negoziato (70), i componenti hanno prezzi e provenienza dell'eccezione
--   9) ordine: ogni riga ha per numero la sua posizione fra le righe espanse
--  10) ordine, K3 aggiunto: COMPONENTI a 35, coi componenti dell'eccezione
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- Fixture
-- ============================================================
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

CREATE TEMP TABLE _cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'provenienza offerta ordine',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

-- Le righe di listino si scrivono solo in bozza: la versione nasce in bozza,
-- prende le righe e si attiva dal verbo.
CREATE TEMP TABLE _lis AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM _cli), 'provenienza offerta ordine',
                                          p_in_bozza => true);

CREATE TEMP TABLE _art AS
SELECT v.s, dbops.fn_pgtap_crea_articolo(
           ('PGT-POO-' || v.s || '-' || substr(md5(clock_timestamp()::text), 1, 8))::varchar, false,
           p_is_composito => v.s IN ('K', 'K2', 'K3')) AS id
  FROM (VALUES ('A'), ('B'), ('K'), ('K2'), ('K3'), ('F1'), ('F2')) v(s);

CREATE FUNCTION pg_temp.art(p text) RETURNS uuid LANGUAGE sql STABLE AS
$fx$ SELECT id FROM _art WHERE s = p $fx$;
CREATE FUNCTION pg_temp.ver() RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT listino_versione_id FROM _lis $fx$;

INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)
SELECT pg_temp.art(k.s), pg_temp.art(c.s), c.coeff, date '2020-01-01'
  FROM (VALUES ('K'), ('K2'), ('K3')) k(s),
       (VALUES ('F1', 2), ('F2', 1)) c(s, coeff);

SELECT dbops.fn_pgtap_listino_aggiungi_articoli(pg_temp.ver(), ARRAY[pg_temp.art('A')], 100);
SELECT dbops.fn_pgtap_listino_aggiungi_articoli(pg_temp.ver(), ARRAY[pg_temp.art('B')], 60);

INSERT INTO vendite.listini_righe_componenti (listino_versione_id, articolo_componente_id,
       articolo_padre_id, articolo_figlio_id, prezzo, valido_dal)
SELECT pg_temp.ver(), ac.id, ac.prodotto_id, ac.componente_id,
       CASE WHEN ac.componente_id = pg_temp.art('F1') THEN 10 ELSE 30 END, script.fn_data_operativa()
  FROM catalogo.articoli_componenti ac
 WHERE ac.prodotto_id IN (pg_temp.art('K'), pg_temp.art('K2'));

SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni', pg_temp.ver(), 'ATTIVA');

CREATE TEMP TABLE _ra AS
SELECT lr.id FROM vendite.listini_righe lr
 WHERE lr.listino_versione_id = pg_temp.ver() AND lr.articolo_id = pg_temp.art('A');

-- L'offerta: variazione globale -10 %, OVERRIDE su B e su K2, AGGIUNTA di K3.
CREATE TEMP TABLE _off (id bigint, ecc_b bigint, ecc_k2 bigint, ecc_k3 bigint);

DO $fx$
DECLARE
    v_off bigint; v_b bigint; v_k2 bigint; v_k3 bigint;
    v_qta numeric;
BEGIN
    INSERT INTO vendite.offerte_commerciali (emittente_fiscale_id, billing_account_id,
        istanza_utility_id, utility_id, listino_id, listino_versione_id,
        tipo_variazione_globale, valore_variazione_globale,
        validita_dal, validita_al, stato_doc_offerta_id)
    SELECT script.fn_pgtap_emittente_operatore(), c.billing_account_id, c.istanza_utility_id,
           c.utility_id, l.listino_id, l.listino_versione_id, 'PERCENTUALE', -10,
           script.fn_data_operativa(), script.fn_data_operativa() + 364,
           (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'BOZZA')
      FROM _cli c, _lis l
    RETURNING id INTO v_off;

    INSERT INTO vendite.offerte_commerciali_utilities (offerta_id, istanza_utility_id, utility_id)
    SELECT v_off, c.istanza_utility_id, c.utility_id FROM _cli c;

    SELECT 1.00 INTO v_qta FROM vendite.fn_articolo_erogazioni(pg_temp.art('B')) e
     WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA' LIMIT 1;
    INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id, tipo_eccezione,
        prezzo_unitario, attivo, qta_operativa)
    VALUES (v_off, pg_temp.art('B'), 'OVERRIDE', 80, true, v_qta)
    RETURNING id INTO v_b;

    SELECT 1.00 INTO v_qta FROM vendite.fn_articolo_erogazioni(pg_temp.art('K2')) e
     WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA' LIMIT 1;
    INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id, tipo_eccezione,
        prezzo_unitario, attivo, qta_operativa)
    VALUES (v_off, pg_temp.art('K2'), 'OVERRIDE', 1, true, v_qta)
    RETURNING id INTO v_k2;
    -- F1 negoziato (un numero: MANUALE); F2 al prezzo del listino, con la sua
    -- provenienza (l'override-oggetto di vendite.fn_componente_override).
    PERFORM vendite.fn_offerta_eccezione_componenti_init(
        v_k2, script.fn_pgtap_emittente_sr_operatore(), script.fn_data_operativa(),
        jsonb_build_object(
            pg_temp.art('F1')::text, 20,
            pg_temp.art('F2')::text, jsonb_build_object(
                'prezzo',              30,
                'origine_prezzo',      'LISTINO_BUNDLE',
                'listino_versione_id', pg_temp.ver(),
                'prezzo_resolver_context', jsonb_build_object(
                    'prezzo_base_snapshot', 30, 'tipo_variazione_applicata', 'NESSUNA',
                    'valore_variazione_applicata', 0))));

    SELECT 1.00 INTO v_qta FROM vendite.fn_articolo_erogazioni(pg_temp.art('K3')) e
     WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA' LIMIT 1;
    INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id, tipo_eccezione,
        prezzo_unitario, attivo, qta_operativa)
    VALUES (v_off, pg_temp.art('K3'), 'AGGIUNTA', 1, true, v_qta)
    RETURNING id INTO v_k3;
    PERFORM vendite.fn_offerta_eccezione_componenti_init(
        v_k3, script.fn_pgtap_emittente_sr_operatore(), script.fn_data_operativa(),
        jsonb_build_object(pg_temp.art('F1')::text, 15, pg_temp.art('F2')::text, 5));

    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', v_off, 'ACCETTATA');
    INSERT INTO _off VALUES (v_off, v_b, v_k2, v_k3);
END $fx$;

CREATE TEMP TABLE _esp AS
SELECT e.*, e.ordinality AS pos
  FROM vendite.fn_offerta_righe_espanse((SELECT id FROM _off)) WITH ORDINALITY AS e;

CREATE TEMP TABLE _ord AS
SELECT vendite.fn_genera_ordine_da_offerta((SELECT id FROM _off)) AS id;

CREATE FUNCTION pg_temp.riga(p text) RETURNS vendite.ordini_righe LANGUAGE sql STABLE AS
$fx$ SELECT r.* FROM vendite.ordini_righe r
      WHERE r.ordine_id = (SELECT id FROM _ord) AND r.articolo_id = pg_temp.art(p) $fx$;

-- ============================================================
-- 1) La forma
-- ============================================================
SELECT ok(
    pg_get_function_result('vendite.fn_espandi_listino_versione'::regproc) LIKE '%componenti jsonb, listino_riga_id bigint)'
    AND pg_get_function_result('vendite.fn_offerta_righe_espanse'::regproc)
        LIKE '%eccezione_id bigint, origine_prezzo character varying, listino_versione_id bigint, listino_riga_id bigint, prezzo_resolver_context jsonb)',
    '1) la riga di listino in coda al nucleo, la provenienza in coda alle righe espanse');

-- ============================================================
-- 2-3) Le righe espanse
-- ============================================================
SELECT is(
    (SELECT e.origine || '|' || e.origine_prezzo || '|' || (e.listino_versione_id = pg_temp.ver())::text
            || '|' || (e.listino_riga_id = (SELECT id FROM _ra))::text || '|' || e.prezzo_unitario::numeric(12,2)
       FROM _esp e WHERE e.articolo_id = pg_temp.art('A')),
    'DA_LISTINO|CONTRATTO_LISTINO|true|true|90.00',
    '2) righe espanse: A dal listino con la sua provenienza');

SELECT is(
    (SELECT string_agg((c ->> 'prezzo')::numeric(12,2)::text || ':' || COALESCE(c ->> 'origine_prezzo', '-'),
                       ' ' ORDER BY (c ->> 'prezzo')::numeric)
       FROM _esp e, jsonb_array_elements(e.componenti) c
      WHERE e.articolo_id = pg_temp.art('K2')),
    '20.00:MANUALE 30.00:LISTINO_BUNDLE',
    '3) righe espanse: K2 forzato porta i componenti dell''eccezione, non quelli del listino');

-- ============================================================
-- 4-9) L'ordine
-- ============================================================
SELECT is(
    (SELECT r.origine_prezzo || '|' || (r.listino_versione_id = pg_temp.ver())::text || '|'
            || (r.listino_riga_id = (SELECT id FROM _ra))::text || '|' || r.prezzo_unitario::numeric(12,2)
       FROM pg_temp.riga('A') r),
    'CONTRATTO_LISTINO|true|true|90.00',
    '4) ordine, A: CONTRATTO_LISTINO, versione e riga di listino, 90');

SELECT is(
    (SELECT (r.prezzo_resolver_context ->> 'prezzo_base_snapshot')::numeric(12,2) || '|'
            || (r.prezzo_resolver_context ->> 'tipo_variazione_applicata') || '|'
            || (r.prezzo_resolver_context ->> 'valore_variazione_applicata')::numeric(12,2)
       FROM pg_temp.riga('A') r),
    '100.00|PERCENTUALE|-10.00',
    '5) ordine, A: nel contesto prezzo base 100 e la variazione -10 %');

SELECT is(
    (SELECT r.origine_prezzo || '|' || num_nulls(r.listino_versione_id, r.listino_riga_id) || '|'
            || r.prezzo_unitario::numeric(12,2)
       FROM pg_temp.riga('B') r),
    (SELECT e.origine_prezzo || '|2|80.00' FROM vendite.offerte_commerciali_eccezioni e
      WHERE e.id = (SELECT ecc_b FROM _off)),
    '6) ordine, B: la provenienza dell''eccezione (MANUALE, nessun listino), 80');

SELECT is(
    (SELECT r.origine_prezzo || '|' || r.prezzo_unitario::numeric(12,2) || '|'
            || (SELECT string_agg(c.origine_prezzo || ':' || (c.listino_versione_id = pg_temp.ver())::text
                                  || ':' || (c.listino_riga_id IS NULL)::text
                                  || ':' || c.prezzo_unitario::numeric(12,2),
                                  ' ' ORDER BY c.prezzo_unitario)
                  FROM vendite.ordini_righe_componenti c WHERE c.riga_ordine_id = r.id)
       FROM pg_temp.riga('K') r),
    'COMPONENTI|50.00|LISTINO_BUNDLE:true:true:10.00 LISTINO_BUNDLE:true:true:30.00',
    '7) ordine, K: il kit e'' COMPONENTI a 50, i componenti LISTINO_BUNDLE con la versione, senza riga');

SELECT is(
    (SELECT r.origine_prezzo || '|' || r.prezzo_unitario::numeric(12,2) || '|'
            || (SELECT string_agg(c.origine_prezzo || ':'
                                  || COALESCE((c.listino_versione_id = pg_temp.ver())::text, '-')
                                  || ':' || c.prezzo_unitario::numeric(12,2),
                                  ' ' ORDER BY c.prezzo_unitario)
                  FROM vendite.ordini_righe_componenti c WHERE c.riga_ordine_id = r.id)
       FROM pg_temp.riga('K2') r),
    'COMPONENTI|70.00|MANUALE:-:20.00 LISTINO_BUNDLE:true:30.00',
    '8) ordine, K2: il kit vale il prezzo negoziato (70), i componenti hanno prezzi e provenienza dell''eccezione');

-- Il listino della fixture ha anche la riga d'appoggio di fn_pgtap_crea_listino: si
-- confronta ogni riga con la sua posizione, non un numero fisso di righe.
SELECT is(
    (SELECT count(*) FILTER (WHERE r.riga_nr = e.pos)::text || '/' || count(*)::text
       FROM vendite.ordini_righe r
       JOIN _esp e ON e.articolo_id = r.articolo_id
      WHERE r.ordine_id = (SELECT id FROM _ord)),
    (SELECT count(*)::text || '/' || count(*)::text FROM _esp),
    '9) ordine: ogni riga ha per numero la sua posizione fra le righe espanse');

-- K3 non sta nel listino: i suoi componenti possono venire solo dall'eccezione.
SELECT is(
    (SELECT r.origine_prezzo || '|' || r.prezzo_unitario::numeric(12,2) || '|'
            || (SELECT string_agg(c.origine_prezzo || ':' || c.prezzo_unitario::numeric(12,2),
                                  ' ' ORDER BY c.prezzo_unitario)
                  FROM vendite.ordini_righe_componenti c WHERE c.riga_ordine_id = r.id)
       FROM pg_temp.riga('K3') r),
    'COMPONENTI|35.00|MANUALE:5.00 MANUALE:15.00',
    '10) ordine, K3 aggiunto: COMPONENTI a 35, coi componenti dell''eccezione');

SELECT * FROM finish();
ROLLBACK;
