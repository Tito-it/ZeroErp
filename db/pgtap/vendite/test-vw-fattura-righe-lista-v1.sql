-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.vw_fattura_righe_lista — le righe di una fattura come LISTA:
--   solo il primo livello, una chiave per ogni riga (anche il padre di un kit,
--   che non ha una PK), i componenti esposti DENTRO la riga padre.
--   Brief: brief-db-liste-righe-documento §8.3 (D-8.3), §8.12.
--   changeSet: 20260928-28.
--
-- ⭐ LA FATTURA SI COSTRUISCE (dbops.fn_pgtap_crea_fattura): nessuna riga letta
--   dal database, quindi il file vale anche su un DB ricostruito da zero, come
--   in CI. Dal DB si leggono solo due aliquote del catalogo config.iva.
--
-- ⛔ COSA PRESIDIA, e perche' proprio questo:
--   · il padre di un kit non ha una PK (fatture_righe_id NULL): senza una
--     chiave calcolata la lista non ha di che paginare, espandere, esportare;
--   · la lista contiene SOLO il livello 0, e i componenti stanno nel padre:
--     e' cio' che fa muovere un kit intero quando si ordina, e non lo spezza
--     fra due pagine (D-8.3);
--   · il legame padre-componenti e' quello della vista madre — fattura, kit,
--     IVA, BA destinatario — quindi un kit con DUE aliquote da' DUE padri, e
--     ciascuno porta i SUOI componenti, non tutti;
--   · i componenti NON esposti non compaiono, e il totale del padre non cambia.
-- ⚠️ NON presidia il legame riga-riga della nota di credito
--   (riga_rettificata_*): costruire una nota di credito numerata e' un giro a
--   se'; le quattro colonne sono le stesse join del repository che la vista
--   sostituisce, provate sui dati di dev (brief §8.12).
--
-- Indice test (1..13):
--    1) security_invoker (fatture_righe e' in RLS)
--    2) la fattura costruita ha le righe attese nella vista MADRE (precondizione)
--    3) la lista contiene solo il livello 0: 1 normale + 1 capofila + 1 parte
--       + 1 padre del kit A + 2 padri del kit B = 6
--    4) ogni riga ha una chiave, e le chiavi sono tutte diverse
--    5) la chiave del padre non dipende dalla lettura: due letture, stesse chiavi
--    6) kit A: due componenti esposti nel padre, il terzo (non esposto) no
--    7) kit A: i componenti in ordine di riga
--    8) kit A: il totale del padre e' quello dei TRE componenti (2+6+9 = 17)
--    9) kit B: due padri, uno per aliquota, un componente ciascuno
--   10) kit B: ciascun padre porta il componente della SUA aliquota
--   11) la riga normale non ha componenti (NULL, non un array vuoto)
--   12) la parte del plafond sta accanto alla capofila: stesso `ordinamento`
--   13) nessun ORDER BY nel corpo della vista
--   14) il CTE `kit` della vista MADRE non e' materializzato (20260928-43)
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come l'applicazione (RLS attiva).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(14);

-- ============================================================
-- FIXTURE — una fattura in bozza, costruita
-- ============================================================
CREATE TEMP TABLE tmp_frl AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('righe lista fattura');

-- Due aliquote DIVERSE dal catalogo di seed (config.iva c'e' anche in CI).
CREATE TEMP TABLE tmp_frl_iva AS
SELECT (SELECT id FROM config.iva WHERE attivo IS TRUE ORDER BY id LIMIT 1)          AS iva_1,
       (SELECT id FROM config.iva WHERE attivo IS TRUE ORDER BY id OFFSET 1 LIMIT 1) AS iva_2;

-- Una riga di kit e' un componente, cioe' un articolo (chk_fatture_righe_kit_articolo,
-- 20261002-43): tre articoli componente, uno per posizione nel kit.
CREATE TEMP TABLE tmp_frl_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGTAP-FRL-KIT') AS padre_id,
       dbops.fn_pgtap_crea_articolo('PGTAP-FRL-C1')  AS c1,
       dbops.fn_pgtap_crea_articolo('PGTAP-FRL-C2')  AS c2,
       dbops.fn_pgtap_crea_articolo('PGTAP-FRL-C3')  AS c3;

-- Scopo: una riga di fattura; kit e capofila facoltativi.
CREATE OR REPLACE FUNCTION pg_temp.fx_riga_frl(
    p_nr integer, p_prezzo numeric, p_iva bigint,
    p_kit text DEFAULT NULL, p_esposizione varchar DEFAULT NULL,
    p_capofila bigint DEFAULT NULL, p_cmp integer DEFAULT NULL)
RETURNS bigint LANGUAGE sql AS $fx$
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione, qta, prezzo_unitario,
         iva_id, kit_key, kit_esposizione, kit_articolo_padre_id, kit_descrizione_padre,
         riga_capofila_id, competenza_dal, competenza_al, kit_qta)
  SELECT (SELECT fattura_id FROM tmp_frl), p_nr,
         (SELECT CASE p_cmp WHEN 1 THEN c1 WHEN 2 THEN c2 WHEN 3 THEN c3 END FROM tmp_frl_art),
         'Riga ' || p_nr, 1, p_prezzo, p_iva,
         p_kit, p_esposizione,
         CASE WHEN p_kit IS NOT NULL THEN (SELECT padre_id FROM tmp_frl_art) END,
         CASE WHEN p_kit IS NOT NULL THEN 'Padre ' || p_kit END,
         p_capofila, script.fn_data_operativa(), script.fn_data_operativa(),
         -- un kit per riga di componente (rev 2026-10-02: kit_qta obbligatoria sulle
         -- righe di kit, chk_fatture_righe_kit_coerente)
         CASE WHEN p_kit IS NOT NULL THEN 1 END
  RETURNING id;
$fx$;

-- 1: riga normale. 2-4: kit A, tre componenti, il terzo NON esposto.
-- 5-6: kit B con due aliquote. 7: capofila, 8: sua parte (plafond).
SELECT pg_temp.fx_riga_frl(1, 10, (SELECT iva_1 FROM tmp_frl_iva));
SELECT pg_temp.fx_riga_frl(2, 2, (SELECT iva_1 FROM tmp_frl_iva), 'KA', 'DESCRITTIVO', p_cmp => 1);
SELECT pg_temp.fx_riga_frl(3, 6, (SELECT iva_1 FROM tmp_frl_iva), 'KA', 'DESCRITTIVO', p_cmp => 2);
SELECT pg_temp.fx_riga_frl(4, 9, (SELECT iva_1 FROM tmp_frl_iva), 'KA', 'NASCOSTO', p_cmp => 3);
SELECT pg_temp.fx_riga_frl(5, 4, (SELECT iva_1 FROM tmp_frl_iva), 'KB', 'DESCRITTIVO', p_cmp => 1);
SELECT pg_temp.fx_riga_frl(6, 5, (SELECT iva_2 FROM tmp_frl_iva), 'KB', 'DESCRITTIVO', p_cmp => 2);
CREATE TEMP TABLE tmp_frl_capofila AS
SELECT pg_temp.fx_riga_frl(7, 30, (SELECT iva_1 FROM tmp_frl_iva)) AS id;
SELECT pg_temp.fx_riga_frl(8, 20, (SELECT iva_2 FROM tmp_frl_iva), NULL, NULL,
                           (SELECT id FROM tmp_frl_capofila));

CREATE TEMP TABLE tmp_frl_lista AS
SELECT * FROM vendite.vw_fattura_righe_lista
 WHERE fattura_id = (SELECT fattura_id FROM tmp_frl);

-- ============================================================
-- 1..3 — forma e perimetro
-- ============================================================
SELECT ok(
    (SELECT c.reloptions @> ARRAY['security_invoker=true'] FROM pg_class c
      WHERE c.oid = 'vendite.vw_fattura_righe_lista'::regclass),
    '1) security_invoker: fatture_righe e'' in RLS');

-- La precondizione: la vista MADRE vede cio' che la fixture ha scritto
-- (1 normale, 1 capofila, 1 parte, 1+2 padri, 2+2 componenti esposti = 10).
SELECT is(
    (SELECT count(*)::integer FROM vendite.vw_fattura_righe_esposte
      WHERE fattura_id = (SELECT fattura_id FROM tmp_frl)),
    10,
    '2) precondizione: la vista madre espone le 10 righe della fixture');

SELECT is((SELECT count(*)::integer FROM tmp_frl_lista), 6,
    '3) la lista ha solo il primo livello: 3 righe vere + 3 padri di kit');

-- ============================================================
-- 4..5 — la chiave
-- ============================================================
SELECT ok(
    (SELECT count(*) = count(DISTINCT riga_key) AND count(riga_key) = count(*)
       FROM tmp_frl_lista),
    '4) ogni riga ha una chiave, e sono tutte diverse (anche i tre padri)');

SELECT set_eq(
    $$SELECT riga_key FROM vendite.vw_fattura_righe_lista
       WHERE fattura_id = (SELECT fattura_id FROM tmp_frl)$$,
    $$SELECT riga_key FROM tmp_frl_lista$$,
    '5) la chiave e'' deterministica: una seconda lettura da'' le stesse chiavi');

-- ============================================================
-- 6..8 — kit A: i componenti nel padre
-- ============================================================
SELECT is(
    (SELECT componenti_numero FROM tmp_frl_lista
      WHERE tipo_riga = 'KIT_PADRE' AND descrizione = 'Padre KA'),
    2,
    '6) kit A: due componenti esposti nel padre, il non esposto no');

SELECT is(
    (SELECT array_agg((c ->> 'riga_nr')::integer ORDER BY o)
       FROM tmp_frl_lista l,
            jsonb_array_elements(l.componenti) WITH ORDINALITY AS j(c, o)
      WHERE l.tipo_riga = 'KIT_PADRE' AND l.descrizione = 'Padre KA'),
    ARRAY[2, 3],
    '7) kit A: i componenti in ordine di riga');

-- ⭐ Esporre o no un componente non cambia MAI il totale: il valore del non
--    esposto e' gia' nel padre.
SELECT is(
    (SELECT importo_riga FROM tmp_frl_lista
      WHERE tipo_riga = 'KIT_PADRE' AND descrizione = 'Padre KA'),
    17.00::numeric,
    '8) kit A: il padre porta il totale dei TRE componenti (2+6+9)');

-- ============================================================
-- 9..10 — kit B: due aliquote, due padri
-- ============================================================
SELECT is(
    (SELECT array_agg(componenti_numero ORDER BY riga_nr) FROM tmp_frl_lista
      WHERE tipo_riga = 'KIT_PADRE' AND descrizione = 'Padre KB'),
    ARRAY[1, 1],
    '9) kit B: due padri (uno per aliquota), un componente ciascuno');

-- ⛔ Il difetto che questa asserzione vede: una partizione senza l'IVA
--    darebbe a ciascun padre ENTRAMBI i componenti.
SELECT is(
    (SELECT count(*)::integer FROM tmp_frl_lista l
      WHERE l.tipo_riga = 'KIT_PADRE' AND l.descrizione = 'Padre KB'
        AND (l.componenti -> 0 ->> 'riga_nr')::integer
            = CASE WHEN l.iva_id = (SELECT iva_1 FROM tmp_frl_iva) THEN 5 ELSE 6 END),
    2,
    '10) kit B: ciascun padre porta il componente della SUA aliquota');

-- ============================================================
-- 11..13
-- ============================================================
SELECT ok(
    (SELECT componenti IS NULL AND componenti_numero = 0 FROM tmp_frl_lista WHERE riga_nr = 1),
    '11) la riga normale non ha componenti: NULL, zero componenti');

SELECT is(
    (SELECT array_agg(ordinamento ORDER BY riga_nr) FROM tmp_frl_lista WHERE riga_nr IN (7, 8)),
    ARRAY[7, 7],
    '12) la parte del plafond ha l''ordinamento della capofila: restano vicine');

-- ⚠️ L'ORDER BY della finestra sta dentro parentesi ed e' legittimo: si cerca
--    solo quello ESTERNO, che pg_get_viewdef stampa in fondo, senza parentesi dopo.
SELECT ok(
    NOT (pg_get_viewdef('vendite.vw_fattura_righe_lista'::regclass) ~* '\mORDER\s+BY\M[^()]*$'),
    '13) nessun ORDER BY esterno nel corpo: l''ordine lo chiede chi legge');

-- ⭐ Il costo registrato in §8.12.4: materializzato, il CTE `kit` si calcolava
--    su TUTTE le fatture a ogni lettura, e il filtro per fattura della lista non
--    ci entrava. La forma e' cio' che il test puo' fissare; il tempo si misura.
SELECT ok(
    pg_get_viewdef('vendite.vw_fattura_righe_esposte'::regclass) ~ 'kit AS NOT MATERIALIZED',
    '14) vw_fattura_righe_esposte: il CTE kit non e'' materializzato (il filtro per fattura ci entra)');

SELECT * FROM finish();
ROLLBACK;
