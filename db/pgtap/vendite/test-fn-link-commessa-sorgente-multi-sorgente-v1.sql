-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_link_commessa_sorgente in modalita' MULTI-SORGENTE
--       (brief commessa ROOT+COLLEGATO, 2026-06-09; migration 20260609-10/11).
--       Una commessa aggrega 1 ROOT (primaria) + N COLLEGATO (contributori):
--       piu' ordini legittimi convergono dimensionalmente sulla stessa commessa.
--       La fn DECIDE il ruolo (chiamante invariato).
--
-- NOTA 2026-07-18 (brief-db-guard-sorgente-polimorfa): le sorgenti fittizie
-- 'A-xxx' PREVENTIVO non passano piu' — fn_link normalizza/valida la chiave e
-- il guard testuale ne verifica l'esistenza. Le sorgenti ora sono COMMESSE
-- REALI (tipo COMMESSA, key_selector='id', chiave canonica id::text): il
-- test esercita la stessa meccanica ROOT/COLLEGATO con fixture leggere.
--
-- Indice test (1..13, piu' 9a e 11a: piano 15):
--   1) riferimenti minimi disponibili (BA + sorgente COMMESSA)
--   2) due commesse distinte create (p_force_new)
--   3) sorgente A su commessa1 -> ROOT (prima sorgente)
--   4) sorgente B diversa su commessa1 -> COLLEGATO (no E_COMMESSA_ROOT_CONFLITTO)
--   5) sorgente C su commessa1 -> COLLEGATO (N>=2 collegati ammessi)
--   6) re-link sorgente B su commessa1 -> idempotente (stesso id, resta COLLEGATO)
--   7) seconda ROOT esplicita su commessa1 (INSERT diretto) -> bloccata (23505,
--      unique parziale uq_commesse_sorgenti_commessa_root)
--   8) sorgente A su commessa2 -> E_COMMESSA_SORGENTE_ALTRA_COMMESSA (P0001):
--      una sorgente sta in una sola commessa APERTA (commessa1 lo e')
--  Dal 2026-10-12 (20261012-43 … -45, brief-db-annullo-a-valle-riapre-a-monte
--  D-12): il link resta come storia, e conta solo la commessa aperta.
--   9) annullata commessa1, la sorgente A va su commessa2: link nuovo, ROOT
--  10) A ha due link (la storia) e la sua commessa aperta e' commessa2
--  11) re-link di A su commessa2 senza meta nuovo: stesso id, la riga non si
--      riscrive (xmin invariato: niente storico per ogni riga mandata)
--  12) re-link con un meta nuovo: la riga si riscrive col merge
--  13) A su una terza commessa: rifiutata, e l'errore nomina la commessa
--      APERTA (commessa2), non quella annullata
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(15);

-- ============================================================
-- Fixture: riferimenti + token random + 3 uid sorgente distinti
-- ============================================================
-- ⭐ 2026-10-12: il cliente e il suo billing account si COSTRUISCONO
--   (dbops.fn_pgtap_crea_cliente_ba). Prima si prendeva il primo BA dei dati:
--   su un database da zero (lo scratch, la CI) non ce n'era, e il file si
--   fermava al test 1 senza provare niente.
CREATE TEMP TABLE tmp_cli_link AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'link multi-sorgente',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_refs_link AS
SELECT
  c.billing_account_id,
  c.utility_id,
  anagrafiche.fn_get_emittente_fiscale_id(c.billing_account_id) AS emittente_soggetto_ruolo_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice = 'COMMESSA' LIMIT 1) AS sorgente_tipo_id
FROM tmp_cli_link c;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND utility_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL
      AND sorgente_tipo_id IS NOT NULL
   FROM tmp_refs_link),
  '1) riferimenti minimi disponibili (BA + sorgente COMMESSA)'
);

-- Sorgenti REALI: 4 commesse "documento sorgente" (A, B, C, D) — chiave
-- canonica id::text, esistenza garantita (guard testuale soddisfatto).
CREATE TEMP TABLE tmp_src_link AS
SELECT
  s.tag,
  vendite.fn_get_or_create_commessa(
    p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_link),
    p_utility_id => (SELECT utility_id FROM tmp_refs_link),
    p_tipo_commessa => 'AUTO',
    p_policy_fatturazione => 'DA_DOCUMENTO',
    p_fatturazione_immediata => false,
    p_priorita_operativa => 'NORMALE',
    p_competenza_dal => DATE '2026-06-01',
    p_competenza_al => DATE '2026-06-30',
    p_meta => jsonb_build_object('test_scope', 'pgtap_link_multi_src_' || s.tag),
    p_force_new => true
  )::text AS src_uid
FROM (VALUES ('A'), ('B'), ('C'), ('D')) AS s(tag);

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
  p_sorgente_uid => (SELECT src_uid FROM tmp_src_link WHERE tag = 'A'),
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
  p_sorgente_uid => (SELECT src_uid FROM tmp_src_link WHERE tag = 'B'),
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
  p_sorgente_uid => (SELECT src_uid FROM tmp_src_link WHERE tag = 'C'),
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
    p_sorgente_uid => (SELECT src_uid FROM tmp_src_link WHERE tag = 'B'),
    p_sorgente_riga => NULL,
    p_meta => jsonb_build_object('rilink', true)
  ),
  (SELECT link_id FROM tmp_link_b),
  '6) re-link stessa sorgente (B) -> idempotente (stesso id)'
);

-- ============================================================
-- 7) seconda ROOT esplicita su commessa1 (INSERT diretto) -> bloccata (23505)
--    Enforcement a livello vincolo: unique parziale "una sola ROOT".
--    La sorgente D e' reale e libera: passa il guard a10 e cade sul vincolo.
-- ============================================================
SELECT throws_ok(
  format(
    $$INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_id, ruolo_link)
      VALUES (%s, %s, %s, 'ROOT')$$,
    (SELECT commessa1_id FROM tmp_commesse_link),
    (SELECT sorgente_tipo_id FROM tmp_refs_link),
    (SELECT src_uid::bigint FROM tmp_src_link WHERE tag = 'D')
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
    (SELECT src_uid FROM tmp_src_link WHERE tag = 'A')
  ),
  'P0001',
  NULL,
  '8) stessa sorgente (A) su altra commessa -> E_COMMESSA_SORGENTE_ALTRA_COMMESSA'
);

-- ============================================================
-- 9-13) Il link resta come storia; conta solo la commessa aperta
--   (20261012-43 … -45, D-12). commessa1 si annulla dal verbo: non ha
--   righe, quindi nessun legame da confermare.
-- ============================================================
SELECT is(vendite.fn_annulla_commessa((SELECT commessa1_id FROM tmp_commesse_link), NULL), 0,
  '9a) commessa1 annullata dal verbo, senza legami');

CREATE TEMP TABLE tmp_link_a2 AS
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa2_id FROM tmp_commesse_link),
  p_sorgente_tipo_id => (SELECT sorgente_tipo_id FROM tmp_refs_link),
  p_sorgente_uid => (SELECT src_uid FROM tmp_src_link WHERE tag = 'A'),
  p_sorgente_riga => NULL,
  p_meta => '{}'::jsonb
) AS link_id;

SELECT ok(
  (SELECT cs.commessa_id = (SELECT commessa2_id FROM tmp_commesse_link) AND cs.ruolo_link = 'ROOT'
     FROM vendite.commesse_sorgenti cs WHERE cs.id = (SELECT link_id FROM tmp_link_a2)),
  '9) annullata commessa1, la sorgente A va su commessa2: link nuovo, ROOT della commessa2');

SELECT ok(
  (SELECT count(*) = 2 FROM vendite.commesse_sorgenti cs
    WHERE cs.sorgente_tipo_id = (SELECT sorgente_tipo_id FROM tmp_refs_link)
      AND cs.sorgente_id = (SELECT src_uid::bigint FROM tmp_src_link WHERE tag = 'A'))
  AND vendite.fn_commessa_viva_di_sorgente(
        (SELECT sorgente_tipo_id FROM tmp_refs_link),
        (SELECT src_uid::bigint FROM tmp_src_link WHERE tag = 'A'), NULL::uuid)
      = (SELECT commessa2_id FROM tmp_commesse_link),
  '10) A ha due link (la storia), e la sua commessa aperta e'' commessa2');

CREATE TEMP TABLE tmp_xmin_a2 AS
SELECT cs.xmin::text AS x FROM vendite.commesse_sorgenti cs WHERE cs.id = (SELECT link_id FROM tmp_link_a2);

SELECT ok(
  vendite.fn_link_commessa_sorgente(
    p_commessa_id => (SELECT commessa2_id FROM tmp_commesse_link),
    p_sorgente_tipo_id => (SELECT sorgente_tipo_id FROM tmp_refs_link),
    p_sorgente_uid => (SELECT src_uid FROM tmp_src_link WHERE tag = 'A'))
  = (SELECT link_id FROM tmp_link_a2),
  '11a) re-link di A su commessa2: idempotente, stesso id');

SELECT is(
  (SELECT cs.xmin::text FROM vendite.commesse_sorgenti cs WHERE cs.id = (SELECT link_id FROM tmp_link_a2)),
  (SELECT x FROM tmp_xmin_a2),
  '11) senza un meta nuovo la riga del link non si riscrive (niente storico per ogni riga mandata)');

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa2_id FROM tmp_commesse_link),
  p_sorgente_tipo_id => (SELECT sorgente_tipo_id FROM tmp_refs_link),
  p_sorgente_uid => (SELECT src_uid FROM tmp_src_link WHERE tag = 'A'),
  p_meta => jsonb_build_object('rilink', 'pgtap'));
SELECT is(
  (SELECT cs.meta ->> 'rilink' FROM vendite.commesse_sorgenti cs WHERE cs.id = (SELECT link_id FROM tmp_link_a2)),
  'pgtap',
  '12) con un meta nuovo il re-link fa il merge');

-- 13) una terza commessa: rifiutata, e l'errore nomina commessa2 (aperta),
--     non commessa1 (annullata, solo storia).
CREATE TEMP TABLE tmp_commessa3_link AS
SELECT vendite.fn_get_or_create_commessa(
    p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_link),
    p_utility_id => (SELECT utility_id FROM tmp_refs_link),
    p_tipo_commessa => 'AUTO',
    p_policy_fatturazione => 'DA_DOCUMENTO',
    p_fatturazione_immediata => false,
    p_priorita_operativa => 'NORMALE',
    p_competenza_dal => DATE '2026-06-01',
    p_competenza_al => DATE '2026-06-30',
    p_meta => jsonb_build_object('test_scope', 'pgtap_link_multi_3'),
    p_force_new => true) AS commessa3_id;

SELECT throws_like(
  format(
    $$SELECT vendite.fn_link_commessa_sorgente(%s, %s, %L, NULL, '{}'::jsonb)$$,
    (SELECT commessa3_id FROM tmp_commessa3_link),
    (SELECT sorgente_tipo_id FROM tmp_refs_link),
    (SELECT src_uid FROM tmp_src_link WHERE tag = 'A')
  ),
  '%(id ' || (SELECT commessa2_id FROM tmp_commesse_link) || ')%',
  '13) A su una terza commessa: rifiutata, e l''errore nomina la commessa aperta (commessa2)'
);

SELECT * FROM finish();
ROLLBACK;
