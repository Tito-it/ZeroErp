-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: Colonne lineage sulle 5 liste documento (Fase B).
--   Viste: vw_preventivi_lista, vw_offerte_commerciali_lista, vw_ordini_lista,
--          vw_contratti_lista, vw_ddt_lista — estese con fase + colonne lineage.
--   Seed: ui.lista_colonna (pratica/fase/transito su liste 4..8).
--   Brief: brief-db-colonne-lineage-liste §5.
--
-- CI-safe: forma (colonne presenti), security_invoker preservato, presenza/
--   correttezza del seed, invariante seed-agnostica. 1 spot-check §5 (PRV0000185)
--   protetto da skip() se i dati non ci sono.
--
-- Indice test (1..24):
--   1..15) le 5 viste espongono pratica_numero, fase, frontiera_codice
--  16..20) le 5 viste hanno security_invoker attivo (preservato)
--     21)  seed: 15 righe (pratica/fase/transito su liste 4..8)
--     22)  seed: campo_sorgente corretto (pratica->pratica_numero, fase->fase,
--          transito->frontiera_codice)
--     23)  invariante: pratica_numero NULL -> n_pratiche = 0 (preventivi)
--     24)  §5 (skip-able): PRV0000185 -> pratica 'PRA-0000818', frontiera
--          'DDT0000031', fase 'CHIUSO'
--     25)  §7 follow-up: preset default liste 4..8 hanno pratica/fase/transito
--          con visibile=true (15 righe lista_preset_colonna, DDT incluso)
--     26)  §7 follow-up: preset ddt_default (lista 8) creato e is_default
-- ------------------------------------------------------------

BEGIN;
SELECT plan(26);

-- ---- 1..15: colonne nuove presenti sulle 5 viste ------------------------
SELECT has_column('vendite', 'vw_preventivi_lista',          'pratica_numero',  'preventivi: pratica_numero');
SELECT has_column('vendite', 'vw_preventivi_lista',          'fase',            'preventivi: fase');
SELECT has_column('vendite', 'vw_preventivi_lista',          'frontiera_codice','preventivi: frontiera_codice');
SELECT has_column('vendite', 'vw_offerte_commerciali_lista', 'pratica_numero',  'offerte: pratica_numero');
SELECT has_column('vendite', 'vw_offerte_commerciali_lista', 'fase',            'offerte: fase');
SELECT has_column('vendite', 'vw_offerte_commerciali_lista', 'frontiera_codice','offerte: frontiera_codice');
SELECT has_column('vendite', 'vw_ordini_lista',              'pratica_numero',  'ordini: pratica_numero');
SELECT has_column('vendite', 'vw_ordini_lista',              'fase',            'ordini: fase');
SELECT has_column('vendite', 'vw_ordini_lista',              'frontiera_codice','ordini: frontiera_codice');
SELECT has_column('vendite', 'vw_contratti_lista',           'pratica_numero',  'contratti: pratica_numero');
SELECT has_column('vendite', 'vw_contratti_lista',           'fase',            'contratti: fase');
SELECT has_column('vendite', 'vw_contratti_lista',           'frontiera_codice','contratti: frontiera_codice');
SELECT has_column('vendite', 'vw_ddt_lista',                 'pratica_numero',  'ddt: pratica_numero');
SELECT has_column('vendite', 'vw_ddt_lista',                 'fase',            'ddt: fase');
SELECT has_column('vendite', 'vw_ddt_lista',                 'frontiera_codice','ddt: frontiera_codice');

-- ---- 16..20: security_invoker preservato --------------------------------
SELECT ok(EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) o
                   WHERE c.oid='vendite.vw_preventivi_lista'::regclass
                     AND o IN ('security_invoker=on','security_invoker=true')),
          'preventivi: security_invoker preservato');
SELECT ok(EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) o
                   WHERE c.oid='vendite.vw_offerte_commerciali_lista'::regclass
                     AND o IN ('security_invoker=on','security_invoker=true')),
          'offerte: security_invoker preservato');
SELECT ok(EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) o
                   WHERE c.oid='vendite.vw_ordini_lista'::regclass
                     AND o IN ('security_invoker=on','security_invoker=true')),
          'ordini: security_invoker preservato');
SELECT ok(EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) o
                   WHERE c.oid='vendite.vw_contratti_lista'::regclass
                     AND o IN ('security_invoker=on','security_invoker=true')),
          'contratti: security_invoker preservato');
SELECT ok(EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) o
                   WHERE c.oid='vendite.vw_ddt_lista'::regclass
                     AND o IN ('security_invoker=on','security_invoker=true')),
          'ddt: security_invoker preservato');

-- ---- 21..22: seed ui.lista_colonna --------------------------------------
SELECT is(
    (SELECT count(*)::int FROM ui.lista_colonna
      WHERE lista_id IN (4,5,6,7,8) AND codice IN ('pratica','fase','transito') AND attivo),
    15, 'seed: 15 colonne lineage (pratica/fase/transito su liste 4..8)');

SELECT is(
    (SELECT count(*)::int FROM ui.lista_colonna
      WHERE lista_id IN (4,5,6,7,8)
        AND ( (codice = 'pratica'  AND campo_sorgente = 'pratica_numero')
           OR (codice = 'fase'     AND campo_sorgente = 'fase')
           OR (codice = 'transito' AND campo_sorgente = 'frontiera_codice') )),
    15, 'seed: campo_sorgente corretto per le 15 colonne');

-- ---- 23: invariante seed-agnostica --------------------------------------
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_preventivi_lista
      WHERE pratica_numero IS NULL AND n_pratiche > 0),
    0, 'invariante: pratica_numero NULL -> n_pratiche = 0');

-- ---- 24: caso reale §5 (skip-able) --------------------------------------
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM vendite.preventivi WHERE numero = 'PRV0000185') THEN
        is(
            (SELECT pratica_numero || '|' || frontiera_codice || '|' || fase
               FROM vendite.vw_preventivi_lista WHERE numero = 'PRV0000185'),
            'PRA-0000818|DDT0000031|CHIUSO',
            '§5 PRV0000185: pratica + frontiera + fase in lista')
    ELSE skip('PRV0000185 non presente nei dati', 1)
END;

-- ---- 25..26: §7 follow-up — visibilita' di default sui preset 4..8 -------
SELECT is(
    (SELECT count(*)::int
       FROM ui.lista_preset_colonna pc
       JOIN ui.lista_colonna lc ON lc.id = pc.colonna_id
       JOIN ui.lista_preset pr ON pr.id = pc.preset_id AND pr.is_default IS TRUE
      WHERE pc.preset_id IN (4,5,6,7,8)
        AND lc.codice IN ('pratica','fase','transito')
        AND pc.visibile IS TRUE),
    15, 'preset default (5 liste): 15 colonne lineage visibili');

SELECT ok(
    EXISTS (SELECT 1 FROM ui.lista_preset
             WHERE lista_id = 8 AND codice = 'ddt_default' AND is_default IS TRUE AND attivo),
    'preset ddt_default creato e is_default');

SELECT * FROM finish();
ROLLBACK;
