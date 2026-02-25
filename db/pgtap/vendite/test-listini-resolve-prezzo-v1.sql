-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_resolve_prezzo_listino (changeset 20260224-02)
-- ------------------------------------------------------------
-- Indice test (1..14):
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
-- 11) Tie-break multi-listino per priorita associazione
-- 12) Tie-break multi-listino per priorita versione
-- 13) Pareggio totale -> AMBIGUOUS_PRICE_MATCH (errore)
-- 14) Nessun match -> errore esplicito
-- ------------------------------------------------------------

BEGIN;
SELECT plan(14);

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
  ('PT_L_MAIN_' || substr(md5(clock_timestamp()::text), 1, 12))::varchar(64) AS c_main,
  ('PT_L_A25_' || substr(md5((clock_timestamp() + interval '1 second')::text), 1, 12))::varchar(64) AS c_a25,
  ('PT_L_B25_' || substr(md5((clock_timestamp() + interval '2 second')::text), 1, 12))::varchar(64) AS c_b25,
  ('PT_L_A24_' || substr(md5((clock_timestamp() + interval '3 second')::text), 1, 12))::varchar(64) AS c_a24,
  ('PT_L_B24_' || substr(md5((clock_timestamp() + interval '4 second')::text), 1, 12))::varchar(64) AS c_b24,
  ('PT_L_A23_' || substr(md5((clock_timestamp() + interval '5 second')::text), 1, 12))::varchar(64) AS c_a23,
  ('PT_L_B23_' || substr(md5((clock_timestamp() + interval '6 second')::text), 1, 12))::varchar(64) AS c_b23;

-- Listino principale (2026): test precedenze livelli 1..7.
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
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, priorita, stato)
  SELECT l.id, 'V1', DATE '2026-01-01', DATE '2026-12-31', 100, 'ATTIVA'
  FROM tmp_l_main_lrp l
  RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.listini_associazioni (listino_id, priorita, valido_dal, valido_al)
SELECT l.id, 100, DATE '2026-01-01', DATE '2026-12-31'
FROM tmp_l_main_lrp l;

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

-- Set 2025: tie-break su priorita associazione.
CREATE TEMP TABLE tmp_l_a25_lrp AS
WITH ins AS (
  INSERT INTO vendite.listini (codice, descrizione, dominio)
  SELECT c.c_a25, 'pgTAP listino A 2025', 'COMMERCIO'
  FROM tmp_codes_lrp c
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_l_b25_lrp AS
WITH ins AS (
  INSERT INTO vendite.listini (codice, descrizione, dominio)
  SELECT c.c_b25, 'pgTAP listino B 2025', 'COMMERCIO'
  FROM tmp_codes_lrp c
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_v_a25_lrp AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, priorita, stato)
  SELECT l.id, 'V1', DATE '2025-01-01', DATE '2025-12-31', 100, 'ATTIVA'
  FROM tmp_l_a25_lrp l
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_v_b25_lrp AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, priorita, stato)
  SELECT l.id, 'V1', DATE '2025-01-01', DATE '2025-12-31', 100, 'ATTIVA'
  FROM tmp_l_b25_lrp l
  RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.listini_associazioni (listino_id, priorita, valido_dal, valido_al)
SELECT l.id, 10, DATE '2025-01-01', DATE '2025-12-31'
FROM tmp_l_a25_lrp l;

INSERT INTO vendite.listini_associazioni (listino_id, priorita, valido_dal, valido_al)
SELECT l.id, 20, DATE '2025-01-01', DATE '2025-12-31'
FROM tmp_l_b25_lrp l;

INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.id, r.articolo_id, r.uom_id, 15.1500000000
FROM tmp_v_a25_lrp v
CROSS JOIN tmp_refs_lrp r;

INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.id, r.articolo_id, r.uom_id, 25.2500000000
FROM tmp_v_b25_lrp v
CROSS JOIN tmp_refs_lrp r;

-- Set 2024: tie-break su priorita versione.
CREATE TEMP TABLE tmp_l_a24_lrp AS
WITH ins AS (
  INSERT INTO vendite.listini (codice, descrizione, dominio)
  SELECT c.c_a24, 'pgTAP listino A 2024', 'COMMERCIO'
  FROM tmp_codes_lrp c
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_l_b24_lrp AS
WITH ins AS (
  INSERT INTO vendite.listini (codice, descrizione, dominio)
  SELECT c.c_b24, 'pgTAP listino B 2024', 'COMMERCIO'
  FROM tmp_codes_lrp c
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_v_a24_lrp AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, priorita, stato)
  SELECT l.id, 'V1', DATE '2024-01-01', DATE '2024-12-31', 5, 'ATTIVA'
  FROM tmp_l_a24_lrp l
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_v_b24_lrp AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, priorita, stato)
  SELECT l.id, 'V1', DATE '2024-01-01', DATE '2024-12-31', 50, 'ATTIVA'
  FROM tmp_l_b24_lrp l
  RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.listini_associazioni (listino_id, priorita, valido_dal, valido_al)
SELECT l.id, 30, DATE '2024-01-01', DATE '2024-12-31'
FROM tmp_l_a24_lrp l;

INSERT INTO vendite.listini_associazioni (listino_id, priorita, valido_dal, valido_al)
SELECT l.id, 30, DATE '2024-01-01', DATE '2024-12-31'
FROM tmp_l_b24_lrp l;

INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.id, r.articolo_id, r.uom_id, 35.3500000000
FROM tmp_v_a24_lrp v
CROSS JOIN tmp_refs_lrp r;

INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.id, r.articolo_id, r.uom_id, 45.4500000000
FROM tmp_v_b24_lrp v
CROSS JOIN tmp_refs_lrp r;

-- Set 2023: pareggio totale per test ambiguita.
CREATE TEMP TABLE tmp_l_a23_lrp AS
WITH ins AS (
  INSERT INTO vendite.listini (codice, descrizione, dominio)
  SELECT c.c_a23, 'pgTAP listino A 2023', 'COMMERCIO'
  FROM tmp_codes_lrp c
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_l_b23_lrp AS
WITH ins AS (
  INSERT INTO vendite.listini (codice, descrizione, dominio)
  SELECT c.c_b23, 'pgTAP listino B 2023', 'COMMERCIO'
  FROM tmp_codes_lrp c
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_v_a23_lrp AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, priorita, stato)
  SELECT l.id, 'V1', DATE '2023-01-01', DATE '2023-12-31', 60, 'ATTIVA'
  FROM tmp_l_a23_lrp l
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_v_b23_lrp AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, priorita, stato)
  SELECT l.id, 'V1', DATE '2023-01-01', DATE '2023-12-31', 60, 'ATTIVA'
  FROM tmp_l_b23_lrp l
  RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.listini_associazioni (listino_id, priorita, valido_dal, valido_al)
SELECT l.id, 40, DATE '2023-01-01', DATE '2023-12-31'
FROM tmp_l_a23_lrp l;

INSERT INTO vendite.listini_associazioni (listino_id, priorita, valido_dal, valido_al)
SELECT l.id, 40, DATE '2023-01-01', DATE '2023-12-31'
FROM tmp_l_b23_lrp l;

INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.id, r.articolo_id, r.uom_id, 55.5500000000
FROM tmp_v_a23_lrp v
CROSS JOIN tmp_refs_lrp r;

INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.id, r.articolo_id, r.uom_id, 65.6500000000
FROM tmp_v_b23_lrp v
CROSS JOIN tmp_refs_lrp r;

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

SELECT ok(
  (
    SELECT prezzo = 15.1500000000::numeric
    FROM vendite.fn_resolve_prezzo_listino(
      p_articolo_id => (SELECT articolo_id FROM tmp_refs_lrp),
      p_uom_id => (SELECT uom_id FROM tmp_refs_lrp),
      p_data_riferimento => DATE '2025-06-15',
      p_billing_account_id => NULL,
      p_utility_id => NULL,
      p_emittente_soggetto_ruolo_id => NULL
    )
  ),
  'Tie-break multi-listino per priorita associazione'
);

SELECT ok(
  (
    SELECT prezzo = 35.3500000000::numeric
    FROM vendite.fn_resolve_prezzo_listino(
      p_articolo_id => (SELECT articolo_id FROM tmp_refs_lrp),
      p_uom_id => (SELECT uom_id FROM tmp_refs_lrp),
      p_data_riferimento => DATE '2024-06-15',
      p_billing_account_id => NULL,
      p_utility_id => NULL,
      p_emittente_soggetto_ruolo_id => NULL
    )
  ),
  'Tie-break multi-listino per priorita versione'
);

SELECT throws_ok(
  $$
  SELECT *
  FROM vendite.fn_resolve_prezzo_listino(
    p_articolo_id => (SELECT articolo_id FROM tmp_refs_lrp),
    p_uom_id => (SELECT uom_id FROM tmp_refs_lrp),
    p_data_riferimento => DATE '2023-06-15',
    p_billing_account_id => NULL,
    p_utility_id => NULL,
    p_emittente_soggetto_ruolo_id => NULL
  );
  $$,
  'P0001',
  NULL,
  'Pareggio totale -> AMBIGUOUS_PRICE_MATCH (errore)'
);

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
