-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_resolve_prezzo_listino
--       Refactor 2026-04-09 fase 2 (vedi WIP listini-commercio):
--         - Univocita stretta per scope dimensionale (no piu multi-listino)
--         - Drop colonne priorita su listini_associazioni e listini_versioni
--         - Resolver senza tie-break su priorita
-- ------------------------------------------------------------
-- Indice test (1..11):
-- 1) Funzione fn_resolve_prezzo_listino presente
-- 2) Riferimenti minimi disponibili (articolo/uom/BA/utility/emittente)
-- 3) p_data_riferimento NULL -> errore
-- 4) p_uom_id non valido -> errore
-- 5) Precedenza fallback articolo+uom (match_level=7)
-- 6) Precedenza BA+articolo+uom non-utility (match_level=4)
-- 7) Precedenza BA+emittente+articolo+uom non-utility (match_level=3)
-- 8) Precedenza utility+articolo+uom (match_level=6)
-- 9) Precedenza BA+utility+articolo+uom (match_level=2)
-- 10) Precedenza BA+utility+emittente+articolo+uom (match_level=1)
-- 11) Nessun match -> errore esplicito
--
-- Note refactor 2026-04-09:
-- I test originali 11 (tie-break priorita associazione), 12 (tie-break
-- priorita versione) e 13 (pareggio totale -> ambiguous) sono stati RIMOSSI
-- perche' strutturalmente impossibili dopo l'introduzione di
-- ex_listini_associazioni_no_overlap (fase 1) e il drop delle colonne
-- priorita (fase 2). Il guard tie_count > 1 nel resolver resta come paranoid
-- check ma non scatta mai per costruzione, quindi non e' testabile via
-- INSERT applicativa.
-- ------------------------------------------------------------

BEGIN;
SELECT plan(11);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_resolve_prezzo_listino'
  ),
  'Funzione fn_resolve_prezzo_listino presente'
);

CREATE TEMP TABLE tmp_refs_lrp AS
SELECT
  (
    SELECT a.id
    FROM catalogo.articoli a
    WHERE a.attivo IS TRUE
    ORDER BY a.data_insert, a.id
    LIMIT 1
  ) AS articolo_id,
  (
    SELECT u.id
    FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE
    ORDER BY u.data_insert, u.id
    LIMIT 1
  ) AS uom_id,
  (
    SELECT ba.id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS billing_account_id,
  (
    SELECT ba.utility_id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS utility_id,
  (
    SELECT anagrafiche.fn_get_emittente_fiscale_id(ba.id)
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS emittente_soggetto_ruolo_id;

SELECT ok(
  (
    SELECT articolo_id IS NOT NULL
      AND uom_id IS NOT NULL
      AND billing_account_id IS NOT NULL
      AND utility_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL
    FROM tmp_refs_lrp
  ),
  'Riferimenti minimi disponibili (articolo/uom/BA/utility/emittente)'
);

CREATE TEMP TABLE tmp_codes_lrp AS
SELECT
  ('PT_L_MAIN_' || substr(md5(clock_timestamp()::text), 1, 12))::varchar(64) AS c_main;

-- ------------------------------------------------------------
-- Listino principale 2026: copre i 7 livelli di match
-- ------------------------------------------------------------
-- Strategia: 1 listino + 1 versione ATTIVA + 6 righe con scope crescente.
-- Le righe sono distinte per (BA, utility, emittente) quindi non violano
-- uq_listini_righe_key_attiva. Il listino e l'unica associazione attiva
-- per scope (NULL,NULL,NULL) sull'intervallo 2026-01-01..2026-12-31:
-- non viola ex_listini_associazioni_no_overlap.
-- ------------------------------------------------------------

CREATE TEMP TABLE tmp_l_main_lrp AS
WITH ins AS (
  INSERT INTO vendite.listini (codice, descrizione, dominio)
  SELECT c.c_main, 'pgTAP listino main resolver', 'UTILITY'
  FROM tmp_codes_lrp c
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_v_main_lrp AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, stato)
  SELECT l.id, 'V1', DATE '2026-01-01', DATE '2026-12-31', 'ATTIVA'
  FROM tmp_l_main_lrp l
  RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.listini_associazioni (listino_id, valido_dal, valido_al)
SELECT l.id, DATE '2026-01-01', DATE '2026-12-31'
FROM tmp_l_main_lrp l;

-- 6 righe di prezzo con scope crescenti: il match_rank scegliera' il piu specifico
INSERT INTO vendite.listini_righe (
  listino_versione_id, articolo_id, uom_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id, prezzo
)
SELECT v.id, r.articolo_id, r.uom_id, NULL, NULL, NULL, 10.1000000000
FROM tmp_v_main_lrp v
CROSS JOIN tmp_refs_lrp r;

INSERT INTO vendite.listini_righe (
  listino_versione_id, articolo_id, uom_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id, prezzo
)
SELECT v.id, r.articolo_id, r.uom_id, r.billing_account_id, NULL, NULL, 20.2000000000
FROM tmp_v_main_lrp v
CROSS JOIN tmp_refs_lrp r;

INSERT INTO vendite.listini_righe (
  listino_versione_id, articolo_id, uom_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id, prezzo
)
SELECT v.id, r.articolo_id, r.uom_id, r.billing_account_id, NULL, r.emittente_soggetto_ruolo_id, 30.3000000000
FROM tmp_v_main_lrp v
CROSS JOIN tmp_refs_lrp r;

INSERT INTO vendite.listini_righe (
  listino_versione_id, articolo_id, uom_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id, prezzo
)
SELECT v.id, r.articolo_id, r.uom_id, NULL, r.utility_id, NULL, 40.4000000000
FROM tmp_v_main_lrp v
CROSS JOIN tmp_refs_lrp r;

INSERT INTO vendite.listini_righe (
  listino_versione_id, articolo_id, uom_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id, prezzo
)
SELECT v.id, r.articolo_id, r.uom_id, r.billing_account_id, r.utility_id, NULL, 50.5000000000
FROM tmp_v_main_lrp v
CROSS JOIN tmp_refs_lrp r;

INSERT INTO vendite.listini_righe (
  listino_versione_id, articolo_id, uom_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id, prezzo
)
SELECT v.id, r.articolo_id, r.uom_id, r.billing_account_id, r.utility_id, r.emittente_soggetto_ruolo_id, 60.6000000000
FROM tmp_v_main_lrp v
CROSS JOIN tmp_refs_lrp r;

-- ============================================================
-- Test 3: p_data_riferimento NULL -> errore
-- ============================================================
SELECT throws_ok(
  $$
  SELECT *
  FROM vendite.fn_resolve_prezzo_listino(
    p_articolo_id => (SELECT articolo_id FROM tmp_refs_lrp),
    p_uom_id => (SELECT uom_id FROM tmp_refs_lrp),
    p_data_riferimento => NULL,
    p_billing_account_id => NULL,
    p_utility_id => NULL,
    p_emittente_soggetto_ruolo_id => NULL
  );
  $$,
  'P0001',
  NULL,
  'p_data_riferimento NULL -> errore'
);

-- ============================================================
-- Test 4: p_uom_id non valido -> errore
-- ============================================================
SELECT throws_ok(
  $$
  SELECT *
  FROM vendite.fn_resolve_prezzo_listino(
    p_articolo_id => (SELECT articolo_id FROM tmp_refs_lrp),
    p_uom_id => 0,
    p_data_riferimento => DATE '2026-06-15',
    p_billing_account_id => NULL,
    p_utility_id => NULL,
    p_emittente_soggetto_ruolo_id => NULL
  );
  $$,
  'P0001',
  NULL,
  'p_uom_id non valido -> errore'
);

-- ============================================================
-- Test 5: match_level 7 (fallback articolo+uom)
-- ============================================================
SELECT ok(
  (
    SELECT match_level = 7
       AND prezzo = 10.1000000000::numeric
    FROM vendite.fn_resolve_prezzo_listino(
      p_articolo_id => (SELECT articolo_id FROM tmp_refs_lrp),
      p_uom_id => (SELECT uom_id FROM tmp_refs_lrp),
      p_data_riferimento => DATE '2026-06-15',
      p_billing_account_id => NULL,
      p_utility_id => NULL,
      p_emittente_soggetto_ruolo_id => NULL
    )
  ),
  'Precedenza fallback articolo+uom (match_level=7)'
);

-- ============================================================
-- Test 6: match_level 4 (BA + articolo+uom non-utility)
-- ============================================================
SELECT ok(
  (
    SELECT match_level = 4
       AND prezzo = 20.2000000000::numeric
    FROM vendite.fn_resolve_prezzo_listino(
      p_articolo_id => (SELECT articolo_id FROM tmp_refs_lrp),
      p_uom_id => (SELECT uom_id FROM tmp_refs_lrp),
      p_data_riferimento => DATE '2026-06-15',
      p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_lrp),
      p_utility_id => NULL,
      p_emittente_soggetto_ruolo_id => NULL
    )
  ),
  'Precedenza BA+articolo+uom non-utility (match_level=4)'
);

-- ============================================================
-- Test 7: match_level 3 (BA + emittente + articolo+uom)
-- ============================================================
SELECT ok(
  (
    SELECT match_level = 3
       AND prezzo = 30.3000000000::numeric
    FROM vendite.fn_resolve_prezzo_listino(
      p_articolo_id => (SELECT articolo_id FROM tmp_refs_lrp),
      p_uom_id => (SELECT uom_id FROM tmp_refs_lrp),
      p_data_riferimento => DATE '2026-06-15',
      p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_lrp),
      p_utility_id => NULL,
      p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_lrp)
    )
  ),
  'Precedenza BA+emittente+articolo+uom non-utility (match_level=3)'
);

-- ============================================================
-- Test 8: match_level 6 (utility + articolo+uom)
-- ============================================================
SELECT ok(
  (
    SELECT match_level = 6
       AND prezzo = 40.4000000000::numeric
    FROM vendite.fn_resolve_prezzo_listino(
      p_articolo_id => (SELECT articolo_id FROM tmp_refs_lrp),
      p_uom_id => (SELECT uom_id FROM tmp_refs_lrp),
      p_data_riferimento => DATE '2026-06-15',
      p_billing_account_id => NULL,
      p_utility_id => (SELECT utility_id FROM tmp_refs_lrp),
      p_emittente_soggetto_ruolo_id => NULL
    )
  ),
  'Precedenza utility+articolo+uom (match_level=6)'
);

-- ============================================================
-- Test 9: match_level 2 (BA + utility + articolo+uom)
-- ============================================================
SELECT ok(
  (
    SELECT match_level = 2
       AND prezzo = 50.5000000000::numeric
    FROM vendite.fn_resolve_prezzo_listino(
      p_articolo_id => (SELECT articolo_id FROM tmp_refs_lrp),
      p_uom_id => (SELECT uom_id FROM tmp_refs_lrp),
      p_data_riferimento => DATE '2026-06-15',
      p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_lrp),
      p_utility_id => (SELECT utility_id FROM tmp_refs_lrp),
      p_emittente_soggetto_ruolo_id => NULL
    )
  ),
  'Precedenza BA+utility+articolo+uom (match_level=2)'
);

-- ============================================================
-- Test 10: match_level 1 (BA + utility + emittente + articolo+uom)
-- ============================================================
SELECT ok(
  (
    SELECT match_level = 1
       AND prezzo = 60.6000000000::numeric
    FROM vendite.fn_resolve_prezzo_listino(
      p_articolo_id => (SELECT articolo_id FROM tmp_refs_lrp),
      p_uom_id => (SELECT uom_id FROM tmp_refs_lrp),
      p_data_riferimento => DATE '2026-06-15',
      p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_lrp),
      p_utility_id => (SELECT utility_id FROM tmp_refs_lrp),
      p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_lrp)
    )
  ),
  'Precedenza BA+utility+emittente+articolo+uom (match_level=1)'
);

-- ============================================================
-- Test 11: nessun match (data fuori intervallo) -> errore esplicito
-- ============================================================
SELECT throws_ok(
  $$
  SELECT *
  FROM vendite.fn_resolve_prezzo_listino(
    p_articolo_id => (SELECT articolo_id FROM tmp_refs_lrp),
    p_uom_id => (SELECT uom_id FROM tmp_refs_lrp),
    p_data_riferimento => DATE '2022-06-15',
    p_billing_account_id => NULL,
    p_utility_id => NULL,
    p_emittente_soggetto_ruolo_id => NULL
  );
  $$,
  'P0001',
  NULL,
  'Nessun match -> errore esplicito'
);

SELECT * FROM finish();
ROLLBACK;
