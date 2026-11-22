-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: un'offerta non esce dalla bozza con un kit col prezzo negoziato senza
--   componenti attivi; il kit a consumo e' esente.
-- Riferimento: brief-db-provenienza-prezzo-segue-il-prezzo §8.19 (D-7-bis «b2» di Tid,
--   2026-11-21); changeSet 20261120-18 … -20, codice E_OFFERTA_EMISSIONE_KIT_SENZA_COMPONENTI.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - un kit in OVERRIDE coi suoi componenti non da' motivi, e nemmeno un OVERRIDE
--     su un articolo semplice (i componenti non li ha per costruzione);
--   - tolti i componenti al kit forzato: un motivo, che nomina offerta e articolo;
--     un kit in AGGIUNTA senza componenti ne da' un altro (l'altro tipo col prezzo
--     negoziato, compreso dalla check);
--   - «Emetti» e' spento con quel motivo, e l'emissione e' rifiutata con quel codice;
--   - rimessi i componenti, l'emissione passa.
--
-- ⭐ TUTTO COSTRUITO: un listino col kit K2 (2 x F1 + 1 x F2) e l'articolo semplice B,
--   forzati nell'offerta; il kit K3, fuori listino, aggiunto senza componenti.
-- ⚠️ Il kit a consumo, esente per D-7-bis, non si costruisce: il modello non lo ammette
--   (vendite.fn_articolo_erogazioni, «il composito si vende solo con la FISSA», I-D6).
--   La check lo esenta lo stesso (quantita' NULL), perche' la decisione resti scritta.
--
-- Elenco test (plan 7):
--   1) la forma: il guard e la capability leggono la check
--   2) il kit forzato coi suoi componenti e l'OVERRIDE semplice: nessun motivo
--   3) senza componenti il kit forzato e il kit aggiunto danno un motivo ciascuno, con offerta e articolo
--   4) «Emetti» spento con KIT_SENZA_COMPONENTI
--   5) l'emissione e' rifiutata con E_OFFERTA_EMISSIONE_KIT_SENZA_COMPONENTI
--   6) rimessi i componenti, l'emissione passa
--   7) la frase ha due segnaposti, quanti sono i valori del motivo
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- Fixture
-- ============================================================
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- «Emetti» lo vede solo chi ha l'azione di processo del passaggio (permesso => nascondi).
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'emetti_offerta');

CREATE FUNCTION pg_temp.msg(p_codice text) RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT split_part(m.messaggio, '%s', 1) || '%' FROM config.messaggi_errore m
   WHERE m.codice = p_codice AND m.lingua = 'it'
$fx$;

CREATE TEMP TABLE _cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'kit con componenti',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE _lis AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM _cli), 'kit con componenti',
                                          p_in_bozza => true);

CREATE TEMP TABLE _art AS
SELECT v.s, dbops.fn_pgtap_crea_articolo(
           ('PGT-OKC-' || v.s || '-' || substr(md5(clock_timestamp()::text), 1, 8))::varchar, false,
           p_is_composito => v.s IN ('K2', 'K3')) AS id
  FROM (VALUES ('K2'), ('K3'), ('B'), ('F1'), ('F2')) v(s);

CREATE FUNCTION pg_temp.art(p text) RETURNS uuid LANGUAGE sql STABLE AS
$fx$ SELECT id FROM _art WHERE s = p $fx$;
CREATE FUNCTION pg_temp.ver() RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT listino_versione_id FROM _lis $fx$;

INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)
SELECT pg_temp.art(k.s), pg_temp.art(c.s), c.coeff, date '2020-01-01'
  FROM (VALUES ('K2'), ('K3')) k(s),
       (VALUES ('F1', 2), ('F2', 1)) c(s, coeff);

SELECT dbops.fn_pgtap_listino_aggiungi_articoli(pg_temp.ver(), ARRAY[pg_temp.art('B')], 60);

INSERT INTO vendite.listini_righe_componenti (listino_versione_id, articolo_componente_id,
       articolo_padre_id, articolo_figlio_id, prezzo, valido_dal)
SELECT pg_temp.ver(), ac.id, ac.prodotto_id, ac.componente_id,
       CASE WHEN ac.componente_id = pg_temp.art('F1') THEN 10 ELSE 30 END, script.fn_data_operativa()
  FROM catalogo.articoli_componenti ac
 WHERE ac.prodotto_id = pg_temp.art('K2');

SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni', pg_temp.ver(), 'ATTIVA');

-- L'offerta in bozza: K2 forzato coi componenti negoziati, B forzato.
CREATE TEMP TABLE _off (id bigint, ecc_k2 bigint);

DO $fx$
DECLARE
    v_off bigint; v_k2 bigint;
    v_qta numeric;
BEGIN
    INSERT INTO vendite.offerte_commerciali (emittente_fiscale_id, billing_account_id,
        istanza_utility_id, utility_id, listino_id, listino_versione_id,
        validita_dal, validita_al, stato_doc_offerta_id)
    SELECT script.fn_pgtap_emittente_operatore(), c.billing_account_id, c.istanza_utility_id,
           c.utility_id, l.listino_id, l.listino_versione_id,
           script.fn_data_operativa(), script.fn_data_operativa() + 364,
           (SELECT s.id FROM config.stati_doc_offerte s WHERE s.iniziale)
      FROM _cli c, _lis l
    RETURNING id INTO v_off;

    INSERT INTO vendite.offerte_commerciali_utilities (offerta_id, istanza_utility_id, utility_id)
    SELECT v_off, c.istanza_utility_id, c.utility_id FROM _cli c;

    SELECT 1.00 INTO v_qta FROM vendite.fn_articolo_erogazioni(pg_temp.art('K2')) e
     WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA' LIMIT 1;
    INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id, tipo_eccezione,
        prezzo_unitario, attivo, qta_operativa)
    VALUES (v_off, pg_temp.art('K2'), 'OVERRIDE', 1, true, v_qta)
    RETURNING id INTO v_k2;
    PERFORM vendite.fn_offerta_eccezione_componenti_init(
        v_k2, script.fn_pgtap_emittente_sr_operatore(), script.fn_data_operativa(),
        jsonb_build_object(pg_temp.art('F1')::text, 20, pg_temp.art('F2')::text, 25));

    SELECT 1.00 INTO v_qta FROM vendite.fn_articolo_erogazioni(pg_temp.art('B')) e
     WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA' LIMIT 1;
    INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id, tipo_eccezione,
        prezzo_unitario, attivo, qta_operativa)
    VALUES (v_off, pg_temp.art('B'), 'OVERRIDE', 50, true, v_qta);

    INSERT INTO _off VALUES (v_off, v_k2);
END $fx$;

-- ============================================================
-- 1) La forma
-- ============================================================
SELECT ok(
    pg_get_functiondef('vendite.trgfn_offerte_commerciali_guard_transizione'::regproc)
        LIKE '%script.fn_check_offerta_kit_con_componenti(NEW.id)%'
    AND pg_get_functiondef('script.fn_available_actions_offerta'::regproc)
        LIKE '%script.fn_check_offerta_kit_con_componenti(p_offerta_id)%',
    '1) il guard della transizione e la capability leggono la check');

-- ============================================================
-- 2-5) Il kit forzato, con e senza componenti
-- ============================================================
SELECT is(
    script.fn_check_offerta_kit_con_componenti((SELECT id FROM _off)),
    '[]'::jsonb,
    '2) il kit forzato coi suoi componenti e l''OVERRIDE semplice: nessun motivo');

DELETE FROM vendite.offerte_commerciali_eccezioni_componenti
 WHERE eccezione_offerta_id = (SELECT ecc_k2 FROM _off);

-- Il kit aggiunto, senza componenti (nessuno chiama la init).
INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id, tipo_eccezione,
    prezzo_unitario, attivo, qta_operativa)
SELECT o.id, pg_temp.art('K3'), 'AGGIUNTA', 1, true, 1.00 FROM _off o;

SELECT is(
    (SELECT jsonb_agg(m ->> 'reason' || '|' || (m -> 'valori' ->> 0) || '|' || (m -> 'valori' ->> 1)
                      || '|' || (m -> 'dettaglio' ->> 'tipo_eccezione')
                      ORDER BY (m -> 'dettaglio' ->> 'eccezione_id')::bigint)
       FROM jsonb_array_elements(script.fn_check_offerta_kit_con_componenti((SELECT id FROM _off))) m),
    (SELECT jsonb_agg('KIT_SENZA_COMPONENTI|' || COALESCE(o.codice, o.id::text) || '|' || a.codice
                      || '|' || e.tipo_eccezione ORDER BY e.id)
       FROM vendite.offerte_commerciali o
       JOIN vendite.offerte_commerciali_eccezioni e ON e.offerta_id = o.id
       JOIN catalogo.articoli a ON a.id = e.articolo_id
      WHERE o.id = (SELECT id FROM _off) AND e.articolo_id IN (pg_temp.art('K2'), pg_temp.art('K3'))),
    '3) senza componenti il kit forzato e il kit aggiunto danno un motivo ciascuno, con offerta e articolo');

SELECT is(
    (SELECT a ->> 'enabled' || '|' || (a ->> 'reason')
       FROM jsonb_array_elements(script.fn_available_actions_offerta((SELECT id FROM _off)) -> 'available_actions') a
       JOIN config.stati_doc_offerte s ON s.codice_interno = a ->> 'target_state'
      WHERE s.emissione),
    'false|KIT_SENZA_COMPONENTI',
    '4) «Emetti» spento con KIT_SENZA_COMPONENTI');

SELECT throws_like(
    format($$SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', %s, 'EMESSA')$$,
           (SELECT id FROM _off)),
    pg_temp.msg('E_OFFERTA_EMISSIONE_KIT_SENZA_COMPONENTI'),
    '5) l''emissione e'' rifiutata con E_OFFERTA_EMISSIONE_KIT_SENZA_COMPONENTI');

-- ============================================================
-- 6) Rimessi i componenti, si emette
-- ============================================================
SELECT vendite.fn_offerta_eccezione_componenti_init(
    e.id, script.fn_pgtap_emittente_sr_operatore(), script.fn_data_operativa(),
    jsonb_build_object(pg_temp.art('F1')::text, 20, pg_temp.art('F2')::text, 25))
  FROM vendite.offerte_commerciali_eccezioni e
 WHERE e.offerta_id = (SELECT id FROM _off) AND e.articolo_id IN (pg_temp.art('K2'), pg_temp.art('K3'));

SELECT lives_ok(
    format($$SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', %s, 'EMESSA')$$,
           (SELECT id FROM _off)),
    '6) rimessi i componenti, l''emissione passa');

-- ============================================================
-- 7) La frase e i suoi valori
-- ============================================================
SELECT is(
    (SELECT (length(m.messaggio) - length(replace(m.messaggio, '%s', ''))) / 2
       FROM config.messaggi_errore m
      WHERE m.codice = 'E_OFFERTA_EMISSIONE_KIT_SENZA_COMPONENTI' AND m.lingua = 'it'),
    2,
    '7) la frase ha due segnaposti, quanti sono i valori del motivo (offerta, articolo)');

SELECT * FROM finish();
ROLLBACK;
