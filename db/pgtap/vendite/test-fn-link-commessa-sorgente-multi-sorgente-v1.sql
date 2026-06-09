-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_link_commessa_sorgente in modalita' MULTI-SORGENTE
--       (brief commessa ROOT+COLLEGATO, 2026-06-09; migration 20260609-10/11).
--       Una commessa aggrega 1 ROOT (primaria) + N COLLEGATO (contributori):
--       piu' ordini legittimi convergono dimensionalmente sulla stessa commessa.
--       La fn DECIDE il ruolo (chiamante invariato).
--
-- Indice test (1..8):
--   1) riferimenti minimi disponibili (BA + sorgente PREVENTIVO)
--   2) due commesse distinte create (p_force_new)
--   3) sorgente A su commessa1 -> ROOT (prima sorgente)
--   4) sorgente B diversa su commessa1 -> COLLEGATO (no E_COMMESSA_ROOT_CONFLITTO)
--   5) sorgente C su commessa1 -> COLLEGATO (N>=2 collegati ammessi)
--   6) re-link sorgente B su commessa1 -> idempotente (stesso id, resta COLLEGATO)
--   7) seconda ROOT esplicita su commessa1 (INSERT diretto) -> bloccata (23505,
--      unique parziale uq_commesse_sorgenti_commessa_root)
--   8) sorgente A su commessa2 -> E_COMMESSA_SORGENTE_ALTRA_COMMESSA (P0001):
--      una sorgente appartiene a una sola commessa (uq_commesse_sorgenti_src_uid)
-- ------------------------------------------------------------

BEGIN;
SELECT plan(8);

-- ============================================================
-- Fixture: riferimenti + token random + 3 uid sorgente distinti
-- ============================================================
CREATE TEMP TABLE tmp_refs_link AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS billing_account_id,
  (SELECT ba.utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS utility_id,
  (SELECT anagrafiche.fn_get_emittente_fiscale_id(ba.id) FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS emittente_soggetto_ruolo_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice = 'PREVENTIVO' LIMIT 1) AS sorgente_tipo_id,
  ('A-' || substr(md5(clock_timestamp()::text), 1, 14))::text AS uid_a,
  ('B-' || substr(md5(clock_timestamp()::text || 'b'), 1, 14))::text AS uid_b,
  ('C-' || substr(md5(clock_timestamp()::text || 'c'), 1, 14))::text AS uid_c;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND utility_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL
      AND sorgente_tipo_id IS NOT NULL
   FROM tmp_refs_link),
  '1) riferimenti minimi disponibili (BA + sorgente PREVENTIVO)'
);

-- Due commesse DISTINTE (p_force_new): commessa2 serve solo al test 8.
CREATE TEMP TABLE tmp_commesse_link AS
SELECT
  vendite.fn_get_or_create_commessa(
    p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_link),
    p_utility_id => (SELECT utility_id FROM tmp_refs_link),
    p_tipo_commessa => 'AUTO',
    p_policy_fatturazione => 'DA_DOCUMENTO',
    p_fatturazione_immediata => false,
    p_priorita_operativa => 'NORMALE',
    p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_link),
    p_competenza_dal => DATE '2026-06-01',
    p_competenza_al => DATE '2026-06-30',
    p_meta => jsonb_build_object('test_scope', 'pgtap_link_multi'),
    p_force_new => true
  ) AS commessa1_id,
  vendite.fn_get_or_create_commessa(
    p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_link),
    p_utility_id => (SELECT utility_id FROM tmp_refs_link),
    p_tipo_commessa => 'AUTO',
    p_policy_fatturazione => 'DA_DOCUMENTO',
    p_fatturazione_immediata => false,
    p_priorita_operativa => 'NORMALE',
    p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_link),
    p_competenza_dal => DATE '2026-06-01',
    p_competenza_al => DATE '2026-06-30',
    p_meta => jsonb_build_object('test_scope', 'pgtap_link_multi_2'),
    p_force_new => true
  ) AS commessa2_id;

SELECT ok(
  (SELECT commessa1_id IS NOT NULL
      AND commessa2_id IS NOT NULL
      AND commessa1_id <> commessa2_id
   FROM tmp_commesse_link),
  '2) due commesse distinte create (p_force_new)'
);

-- ============================================================
-- 3) sorgente A su commessa1 -> ROOT (prima sorgente)
-- ============================================================
CREATE TEMP TABLE tmp_link_a AS
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa1_id FROM tmp_commesse_link),
  p_sorgente_tipo_id => (SELECT sorgente_tipo_id FROM tmp_refs_link),
  p_sorgente_uid => (SELECT uid_a FROM tmp_refs_link),
  p_sorgente_riga => NULL,
  p_meta => jsonb_build_object('src', 'A')
) AS link_id;

SELECT is(
  (SELECT cs.ruolo_link FROM vendite.commesse_sorgenti cs
    WHERE cs.id = (SELECT link_id FROM tmp_link_a)),
  'ROOT',
  '3) prima sorgente (A) su commessa1 -> ROOT'
);

-- ============================================================
-- 4) sorgente B diversa su commessa1 -> COLLEGATO
-- ============================================================
CREATE TEMP TABLE tmp_link_b AS
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa1_id FROM tmp_commesse_link),
  p_sorgente_tipo_id => (SELECT sorgente_tipo_id FROM tmp_refs_link),
  p_sorgente_uid => (SELECT uid_b FROM tmp_refs_link),
  p_sorgente_riga => NULL,
  p_meta => jsonb_build_object('src', 'B')
) AS link_id;

SELECT is(
  (SELECT cs.ruolo_link FROM vendite.commesse_sorgenti cs
    WHERE cs.id = (SELECT link_id FROM tmp_link_b)),
  'COLLEGATO',
  '4) seconda sorgente (B) su commessa1 -> COLLEGATO (no ROOT_CONFLITTO)'
);

-- ============================================================
-- 5) sorgente C su commessa1 -> COLLEGATO (N>=2 collegati)
-- ============================================================
CREATE TEMP TABLE tmp_link_c AS
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa1_id FROM tmp_commesse_link),
  p_sorgente_tipo_id => (SELECT sorgente_tipo_id FROM tmp_refs_link),
  p_sorgente_uid => (SELECT uid_c FROM tmp_refs_link),
  p_sorgente_riga => NULL,
  p_meta => jsonb_build_object('src', 'C')
) AS link_id;

SELECT is(
  (SELECT count(*)::int FROM vendite.commesse_sorgenti cs
    WHERE cs.commessa_id = (SELECT commessa1_id FROM tmp_commesse_link)
      AND cs.ruolo_link = 'COLLEGATO'),
  2,
  '5) terza sorgente (C) su commessa1 -> COLLEGATO (N>=2 collegati ammessi)'
);

-- ============================================================
-- 6) re-link sorgente B -> idempotente (stesso id, resta COLLEGATO)
-- ============================================================
SELECT is(
  vendite.fn_link_commessa_sorgente(
    p_commessa_id => (SELECT commessa1_id FROM tmp_commesse_link),
    p_sorgente_tipo_id => (SELECT sorgente_tipo_id FROM tmp_refs_link),
    p_sorgente_uid => (SELECT uid_b FROM tmp_refs_link),
    p_sorgente_riga => NULL,
    p_meta => jsonb_build_object('rilink', true)
  ),
  (SELECT link_id FROM tmp_link_b),
  '6) re-link stessa sorgente (B) -> idempotente (stesso id)'
);

-- ============================================================
-- 7) seconda ROOT esplicita su commessa1 (INSERT diretto) -> bloccata (23505)
--    Enforcement a livello vincolo: unique parziale "una sola ROOT".
-- ============================================================
SELECT throws_ok(
  format(
    $$INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
      VALUES (%s, %s, %L, 'ROOT')$$,
    (SELECT commessa1_id FROM tmp_commesse_link),
    (SELECT sorgente_tipo_id FROM tmp_refs_link),
    'EXPLICIT-ROOT-2-' || substr(md5(clock_timestamp()::text), 1, 8)
  ),
  '23505',
  NULL,
  '7) seconda ROOT esplicita su commessa1 -> bloccata (uq_commesse_sorgenti_commessa_root)'
);

-- ============================================================
-- 8) sorgente A su commessa2 -> E_COMMESSA_SORGENTE_ALTRA_COMMESSA (P0001)
--    Una sorgente appartiene a una sola commessa.
-- ============================================================
SELECT throws_ok(
  format(
    $$SELECT vendite.fn_link_commessa_sorgente(%s, %s, %L, NULL, '{}'::jsonb)$$,
    (SELECT commessa2_id FROM tmp_commesse_link),
    (SELECT sorgente_tipo_id FROM tmp_refs_link),
    (SELECT uid_a FROM tmp_refs_link)
  ),
  'P0001',
  NULL,
  '8) stessa sorgente (A) su altra commessa -> E_COMMESSA_SORGENTE_ALTRA_COMMESSA'
);

SELECT * FROM finish();
ROLLBACK;
