-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_resolve_commessa_prezzi (changeset 20260224-03)
-- ------------------------------------------------------------
-- Indice test (1..11):
-- 1) Funzione fn_resolve_commessa_prezzi presente
-- 2) p_lotto_id non valido -> errore
-- 3) Lotto inesistente -> errore
-- 4) Riferimenti minimi disponibili
-- 5) Lotto attivita creato
-- 6) La funzione ritorna una riga per ogni attivita del lotto
-- 7) Caso OK -> prezzo coerente, stale=false
-- 8) Caso PRICE_STALE -> prezzo differente, stale=true
-- 9) Caso PREZZO_ASSENTE
-- 10) Caso UOM_ASSENTE
-- 11) Caso ERRORE_RESOLVER (ambiguous price match)
-- ------------------------------------------------------------

BEGIN;
SELECT plan(11);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_resolve_commessa_prezzi'
  ),
  'Funzione fn_resolve_commessa_prezzi presente'
);

SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_resolve_commessa_prezzi(0); $$,
  'P0001',
  NULL,
  'p_lotto_id non valido -> errore'
);

SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_resolve_commessa_prezzi(999999999); $$,
  'P0001',
  NULL,
  'Lotto inesistente -> errore'
);

CREATE TEMP TABLE tmp_refs_lrcp AS
SELECT
  (
    SELECT a.id
    FROM catalogo.articoli a
    WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST
    LIMIT 1
  ) AS articolo_id,
  (
    SELECT u.id
    FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE
    ORDER BY u.id
    LIMIT 1
  ) AS uom_id,
  (
    SELECT ba.id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS billing_account_id,
  (
    SELECT ba.utility_id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS utility_id,
  (
    SELECT ba.istanza_utility_id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS istanza_utility_id,
  (
    SELECT anagrafiche.fn_get_emittente_fiscale_id(ba.id)
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS emittente_soggetto_ruolo_id,
  (
    SELECT t.id
    FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE
    ORDER BY t.id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (
    SELECT v.id
    FROM config.valute v
    ORDER BY v.id
    LIMIT 1
  ) AS valuta_id;

CREATE TEMP TABLE tmp_codes_lrcp AS
SELECT
  ('LRC_OK_' || substr(md5(clock_timestamp()::text), 1, 10))::varchar(64) AS c_ok,
  ('LRC_A1_' || substr(md5((clock_timestamp() + interval '1 second')::text), 1, 10))::varchar(64) AS c_a1,
  ('LRC_A2_' || substr(md5((clock_timestamp() + interval '2 second')::text), 1, 10))::varchar(64) AS c_a2;

SELECT ok(
  (
    SELECT articolo_id IS NOT NULL
      AND uom_id IS NOT NULL
      AND billing_account_id IS NOT NULL
      AND utility_id IS NOT NULL
      AND istanza_utility_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL
      AND tipo_doc_fiscale_id IS NOT NULL
      AND valuta_id IS NOT NULL
    FROM tmp_refs_lrcp
  ),
  'Riferimenti minimi disponibili'
);

-- Lotto di test.
CREATE TEMP TABLE tmp_lotto_lrcp AS
SELECT vendite.fn_get_or_create_lotto_attivita(
  p_lotto_id => NULL,
  p_competenza_mese => DATE '2026-06-01',
  p_utility_id => (SELECT utility_id FROM tmp_refs_lrcp),
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_lrcp),
  p_sorgente_tipo_id => NULL,
  p_lock_batch_id => NULL,
  p_meta => jsonb_build_object('test_scope', 'pgtap_fn_resolve_commessa_prezzi'),
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_lrcp)
) AS lotto_id;

SELECT ok(
  (SELECT lotto_id IS NOT NULL FROM tmp_lotto_lrcp),
  'Lotto attivita creato'
);

-- Listino 2026 per casi OK/STALE.
CREATE TEMP TABLE tmp_listino_ok_lrcp AS
WITH ins AS (
  INSERT INTO vendite.listini (codice, descrizione, dominio)
  SELECT c.c_ok, 'listino ok fn_resolve_commessa_prezzi', 'UTILITY'
  FROM tmp_codes_lrcp c
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_listino_ok_v_lrcp AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, priorita, stato)
  SELECT l.id, 'V1', DATE '2026-01-01', DATE '2026-12-31', 10, 'ATTIVA'
  FROM tmp_listino_ok_lrcp l
  RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.listini_associazioni (
  listino_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id, priorita, valido_dal, valido_al
)
SELECT
  l.id,
  r.billing_account_id,
  r.utility_id,
  r.emittente_soggetto_ruolo_id,
  10,
  DATE '2026-01-01',
  DATE '2026-12-31'
FROM tmp_listino_ok_lrcp l
CROSS JOIN tmp_refs_lrcp r;

INSERT INTO vendite.listini_righe (
  listino_versione_id, articolo_id, uom_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id, prezzo
)
SELECT
  v.id,
  r.articolo_id,
  r.uom_id,
  r.billing_account_id,
  r.utility_id,
  r.emittente_soggetto_ruolo_id,
  10.1000000000
FROM tmp_listino_ok_v_lrcp v
CROSS JOIN tmp_refs_lrcp r;

-- Due listini 2023 con pari priorita` per generare AMBIGUOUS.
CREATE TEMP TABLE tmp_listino_a1_lrcp AS
WITH ins AS (
  INSERT INTO vendite.listini (codice, descrizione, dominio)
  SELECT c.c_a1, 'listino ambig 1', 'COMMERCIO'
  FROM tmp_codes_lrcp c
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_listino_a2_lrcp AS
WITH ins AS (
  INSERT INTO vendite.listini (codice, descrizione, dominio)
  SELECT c.c_a2, 'listino ambig 2', 'COMMERCIO'
  FROM tmp_codes_lrcp c
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_listino_a1_v_lrcp AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, priorita, stato)
  SELECT l.id, 'V1', DATE '2023-01-01', DATE '2023-12-31', 50, 'ATTIVA'
  FROM tmp_listino_a1_lrcp l
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_listino_a2_v_lrcp AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, priorita, stato)
  SELECT l.id, 'V1', DATE '2023-01-01', DATE '2023-12-31', 50, 'ATTIVA'
  FROM tmp_listino_a2_lrcp l
  RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.listini_associazioni (listino_id, priorita, valido_dal, valido_al)
SELECT id, 30, DATE '2023-01-01', DATE '2023-12-31'
FROM tmp_listino_a1_lrcp
UNION ALL
SELECT id, 30, DATE '2023-01-01', DATE '2023-12-31'
FROM tmp_listino_a2_lrcp;

INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.id, r.articolo_id, r.uom_id, 9.9000000000
FROM tmp_listino_a1_v_lrcp v
CROSS JOIN tmp_refs_lrcp r
UNION ALL
SELECT v.id, r.articolo_id, r.uom_id, 8.8000000000
FROM tmp_listino_a2_v_lrcp v
CROSS JOIN tmp_refs_lrcp r;

-- Attivita` di test nel lotto: OK, STALE, PREZZO_ASSENTE, UOM_ASSENTE, ERRORE_RESOLVER.
CREATE TEMP TABLE tmp_att_ok_lrcp AS
WITH ins AS (
  INSERT INTO vendite.attivita_fatturabili (
    articolo_id, istanza_utility_id, billing_account_id, data_attivita,
    quantita, competenza_mese, tipo_doc_fiscale_id, valuta_id, uom_id,
    prezzo_unitario, lotto_attivita_id, meta
  )
  SELECT
    r.articolo_id, r.istanza_utility_id, r.billing_account_id, DATE '2026-06-15',
    1, DATE '2026-06-01', r.tipo_doc_fiscale_id, r.valuta_id, r.uom_id,
    10.1000000000, l.lotto_id,
    jsonb_build_object('case', 'OK')
  FROM tmp_refs_lrcp r
  CROSS JOIN tmp_lotto_lrcp l
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_att_stale_lrcp AS
WITH ins AS (
  INSERT INTO vendite.attivita_fatturabili (
    articolo_id, istanza_utility_id, billing_account_id, data_attivita,
    quantita, competenza_mese, tipo_doc_fiscale_id, valuta_id, uom_id,
    prezzo_unitario, lotto_attivita_id, meta
  )
  SELECT
    r.articolo_id, r.istanza_utility_id, r.billing_account_id, DATE '2026-06-15',
    1, DATE '2026-06-01', r.tipo_doc_fiscale_id, r.valuta_id, r.uom_id,
    11.1000000000, l.lotto_id,
    jsonb_build_object('case', 'STALE')
  FROM tmp_refs_lrcp r
  CROSS JOIN tmp_lotto_lrcp l
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_att_no_price_lrcp AS
WITH ins AS (
  INSERT INTO vendite.attivita_fatturabili (
    articolo_id, istanza_utility_id, billing_account_id, data_attivita,
    quantita, competenza_mese, tipo_doc_fiscale_id, valuta_id, uom_id,
    prezzo_unitario, lotto_attivita_id, meta
  )
  SELECT
    r.articolo_id, r.istanza_utility_id, r.billing_account_id, DATE '2026-06-15',
    1, DATE '2026-06-01', r.tipo_doc_fiscale_id, r.valuta_id, r.uom_id,
    NULL, l.lotto_id,
    jsonb_build_object('case', 'NO_PRICE')
  FROM tmp_refs_lrcp r
  CROSS JOIN tmp_lotto_lrcp l
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_att_no_uom_lrcp AS
WITH ins AS (
  INSERT INTO vendite.attivita_fatturabili (
    articolo_id, istanza_utility_id, billing_account_id, data_attivita,
    quantita, competenza_mese, tipo_doc_fiscale_id, valuta_id, uom_id,
    prezzo_unitario, lotto_attivita_id, meta
  )
  SELECT
    r.articolo_id, r.istanza_utility_id, r.billing_account_id, DATE '2026-06-15',
    1, DATE '2026-06-01', r.tipo_doc_fiscale_id, r.valuta_id, NULL,
    10.1000000000, l.lotto_id,
    jsonb_build_object('case', 'NO_UOM')
  FROM tmp_refs_lrcp r
  CROSS JOIN tmp_lotto_lrcp l
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_att_err_lrcp AS
WITH ins AS (
  INSERT INTO vendite.attivita_fatturabili (
    articolo_id, istanza_utility_id, billing_account_id, data_attivita,
    quantita, competenza_mese, tipo_doc_fiscale_id, valuta_id, uom_id,
    prezzo_unitario, lotto_attivita_id, meta
  )
  SELECT
    r.articolo_id, r.istanza_utility_id, r.billing_account_id, DATE '2023-06-15',
    1, DATE '2023-06-01', r.tipo_doc_fiscale_id, r.valuta_id, r.uom_id,
    10.0000000000, l.lotto_id,
    jsonb_build_object('case', 'ERR_RESOLVER')
  FROM tmp_refs_lrcp r
  CROSS JOIN tmp_lotto_lrcp l
  RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_res_lrcp AS
SELECT *
FROM vendite.fn_resolve_commessa_prezzi((SELECT lotto_id FROM tmp_lotto_lrcp));

SELECT is(
  (SELECT count(*) FROM tmp_res_lrcp),
  5::bigint,
  'La funzione ritorna una riga per ogni attivita del lotto'
);

SELECT ok(
  (
    SELECT esito = 'OK'
       AND stale IS FALSE
       AND delta_prezzo = 0::numeric(22,10)
    FROM tmp_res_lrcp
    WHERE attivita_id = (SELECT id FROM tmp_att_ok_lrcp)
  ),
  'Caso OK -> prezzo coerente, stale=false'
);

SELECT ok(
  (
    SELECT esito = 'PRICE_STALE'
       AND stale IS TRUE
       AND delta_prezzo <> 0::numeric(22,10)
    FROM tmp_res_lrcp
    WHERE attivita_id = (SELECT id FROM tmp_att_stale_lrcp)
  ),
  'Caso PRICE_STALE -> prezzo differente, stale=true'
);

SELECT is(
  (
    SELECT esito
    FROM tmp_res_lrcp
    WHERE attivita_id = (SELECT id FROM tmp_att_no_price_lrcp)
  ),
  'PREZZO_ASSENTE'::text,
  'Caso PREZZO_ASSENTE'
);

SELECT is(
  (
    SELECT esito
    FROM tmp_res_lrcp
    WHERE attivita_id = (SELECT id FROM tmp_att_no_uom_lrcp)
  ),
  'UOM_ASSENTE'::text,
  'Caso UOM_ASSENTE'
);

SELECT is(
  (
    SELECT esito
    FROM tmp_res_lrcp
    WHERE attivita_id = (SELECT id FROM tmp_att_err_lrcp)
  ),
  'ERRORE_RESOLVER'::text,
  'Caso ERRORE_RESOLVER (ambiguous price match)'
);

SELECT * FROM finish();
ROLLBACK;
