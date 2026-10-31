-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le liste del push a commessa non aprono il filtro di stato quando lo
--       stato non si trova nel catalogo.
-- Oggetti: vendite.fn_list_*_da_pushare (20261010-52 preventivi,
--   20261010-55 contratti) e, dal 2026-10-31, la sede della regola del push
--   dei contratti vendite.fn_contratti_addebiti_maturati (20261031-02), che
--   il lister dei contratti chiama.
-- Riferimento: brief-db-istanza-nasce-col-ba-residui (D-2, decisione di Tid
--   del 2026-10-10); brief-modello-documento-vendita §17 (2026-10-31).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - lo stato di partenza lo dice il vocabolario: l'accettazione per il
--     preventivo, l'emissione e la cessazione per il contratto (colonne
--     accettazione, emissione, cessazione; lettori script.fn_stato_*_id). Se
--     il vocabolario non ne marca uno, la lista SOLLEVA E_CONFIG_MANCANTE:
--     non lista documenti in uno stato qualunque (fino al 2026-10-31 il
--     rifiuto era E_CODICE sul letterale, e il test leggeva il corpo);
--   - nessuna lista del push filtra lo stato nella forma
--     `v_stato_..._id IS NULL OR ...`, che con lo stato assente fa cadere il
--     filtro.
--
-- Elenco test (plan 3):
--   1) nessuna fn_list_*_da_pushare di vendite ha la forma `v_stato_..._id IS NULL OR`
--   2) preventivi: nessuno stato di accettazione -> E_CONFIG_MANCANTE
--   3) contratti: nessuno stato di cessazione -> E_CONFIG_MANCANTE (dalla sede
--      vendite.fn_contratti_addebiti_maturati, attraverso il lister)
--   4) contratti: nessuno stato di emissione -> E_CONFIG_MANCANTE
--
-- ⭐ Dal 2026-10-31 i casi 2-4 si COSTRUISCONO: togliere la marca a uno stato
--   (accettazione = false) e' un UPDATE che nessun guard ferma e nessun
--   documento impedisce, al contrario dello spegnimento dello stato. Il test 1
--   resta un presidio sulla forma, dichiarato: la forma che apre il filtro e'
--   un modo di scrivere, non un caso da costruire.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — legge il catalogo delle funzioni, e i casi 2-4 si fermano
--   prima di leggere un documento.

SELECT plan(4);

-- ============================================================
-- 1) Nessuna lista del push apre il filtro di stato
-- ============================================================
SELECT is(
    (SELECT string_agg(p.proname, ', ' ORDER BY p.proname)
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite'
        AND p.proname ~ '^fn_list_.*_da_pushare$'
        AND p.prosrc ~* 'v_stato_\w+_id\s+IS\s+NULL\s+OR'),
    NULL,
    '1. Nessuna fn_list_*_da_pushare filtra lo stato con «IS NULL OR» (che con lo stato assente lista tutto)'
);

-- ============================================================
-- 2-4) Il vocabolario senza la marca: la lista si ferma. Ogni caso nella
--      sua transazione annidata, per non lasciare la marca tolta al
--      successivo.
-- ============================================================
SAVEPOINT s_prev;
UPDATE config.stati_doc_preventivi SET accettazione = false WHERE accettazione;
SELECT throws_like(
    $$SELECT * FROM vendite.fn_list_preventivi_da_pushare()$$,
    'Configurazione mancante: stato di accettazione%',
    '2. fn_list_preventivi_da_pushare: nessuno stato di accettazione nel vocabolario -> E_CONFIG_MANCANTE'
);
ROLLBACK TO SAVEPOINT s_prev;

SAVEPOINT s_cess;
UPDATE config.stati_doc_contratti SET cessazione = false WHERE cessazione;
SELECT throws_like(
    $$SELECT * FROM vendite.fn_list_contratti_da_pushare()$$,
    'Configurazione mancante: stato di cessazione%',
    '3. fn_list_contratti_da_pushare: nessuno stato di cessazione nel vocabolario -> E_CONFIG_MANCANTE (dalla sede fn_contratti_addebiti_maturati)'
);
ROLLBACK TO SAVEPOINT s_cess;

SAVEPOINT s_emis;
UPDATE config.stati_doc_contratti SET emissione = false WHERE emissione;
SELECT throws_like(
    $$SELECT * FROM vendite.fn_list_contratti_da_pushare()$$,
    'Configurazione mancante: stato di emissione%',
    '4. fn_list_contratti_da_pushare: nessuno stato di emissione nel vocabolario -> E_CONFIG_MANCANTE'
);
ROLLBACK TO SAVEPOINT s_emis;

SELECT * FROM finish();
ROLLBACK;
