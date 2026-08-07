-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: guard sorgente polimorfa MODELLO B (chiave unica testuale) +
--       normalizzazione della chiave in vendite.fn_link_commessa_sorgente
--       (brief-db-guard-sorgente-polimorfa, migrations 20260718-15..19).
--
--       Convenzione (config/manual/sorgenti.md §Convenzione chiave sorgente):
--       sorgente_uid TEXT = id::text per i tipi a key_selector='id',
--       uuid testuale per i tipi a key_selector='uid'.
--
-- Indice test (1..18):
--   1)  riferimenti minimi disponibili (BA + tipi COMMESSA/PREVENTIVO/ORDINE)
--   2)  esiste script.trgfn_guard_sorgente_polimorfa_tipizzata (modello A)
--   3)  NON esiste piu' il vecchio nome trgfn_guard_sorgente_polimorfa
--   4)  esiste script.trgfn_guard_sorgente_polimorfa_testuale (modello B)
--   5)  trigger guard agganciato a pratiche.pratiche_sorgenti
--   6)  trigger guard agganciato a vendite.commesse_sorgenti
--   7)  INSERT canonico id::text (COMMESSA esistente) -> passa
--   8)  INSERT uuid per tipo a chiave id -> P0001 (E_SORG_FORMATO)
--   9)  INSERT id inesistente -> P0001 (E_SORG_NOT_FOUND)
--   10) INSERT uuid inesistente per PREVENTIVO -> P0001 (E_SORG_NOT_FOUND)
--   11) INSERT testo non-uuid per PREVENTIVO -> P0001 (E_SORG_FORMATO)
--   12) fn_link canonico id::text -> stocca com'e' (readback)
--   13) fn_link uuid per COMMESSA (target senza colonna uid) ->
--       P0001 (E_SORG_NORM_NON_RISOLTA)
--   14) fn_link testo non-uuid per PREVENTIVO -> P0001 (E_SORG_FORMATO)
--   15) fn_link uuid inesistente per ORDINE_VENDITA (target CON colonna uid)
--       -> P0001 (E_SORG_NORM_NON_RISOLTA)
--   16) fn_link uuid di un ordine REALE libero -> normalizzato a id::text
--       (skip se nessun ordine libero disponibile)
--   17) censimento commesse_sorgenti: 0 righe non canoniche
--   18) censimento pratiche_sorgenti: 0 righe non canoniche
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

SELECT plan(18);

-- ============================================================
-- Fixture: riferimenti (BA con emittente fiscale) + tipi sorgente
-- ============================================================
CREATE TEMP TABLE tmp_guard_refs AS
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
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA' AND s.attivo LIMIT 1)       AS src_commessa,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO' AND s.attivo LIMIT 1)     AS src_preventivo,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA' AND s.attivo LIMIT 1) AS src_ordine;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND utility_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL
      AND src_commessa IS NOT NULL
      AND src_preventivo IS NOT NULL
      AND src_ordine IS NOT NULL
   FROM tmp_guard_refs),
  '1) riferimenti minimi disponibili (BA + tipi COMMESSA/PREVENTIVO/ORDINE)'
);

-- ============================================================
-- 2..6) oggetti in posto: due funzioni sorelle + trigger agganciati
-- ============================================================
SELECT has_function('script', 'trgfn_guard_sorgente_polimorfa_tipizzata',
  '2) esiste il guard modello A (tipizzata, ex trgfn_guard_sorgente_polimorfa)');

SELECT hasnt_function('script', 'trgfn_guard_sorgente_polimorfa',
  '3) il vecchio nome generico non esiste piu'' (rinomina 20260718-16)');

SELECT has_function('script', 'trgfn_guard_sorgente_polimorfa_testuale',
  '4) esiste il guard modello B (testuale)');

SELECT has_trigger('pratiche', 'pratiche_sorgenti',
  'trg_pratiche_sorgenti_a10_guard_sorgente_ins_upd',
  '5) guard testuale agganciato a pratiche_sorgenti');

SELECT has_trigger('vendite', 'commesse_sorgenti',
  'trg_commesse_sorgenti_a10_guard_sorgente_ins_upd',
  '6) guard testuale agganciato a commesse_sorgenti');

-- ============================================================
-- Fixture: commessa host + 2 commesse "sorgente" (documenti reali per i
-- link a chiave id: usare commesse evita fixture documento pesanti)
-- ============================================================
CREATE TEMP TABLE tmp_guard_commesse AS
SELECT
  vendite.fn_get_or_create_commessa(
    p_billing_account_id => (SELECT billing_account_id FROM tmp_guard_refs),
    p_utility_id => (SELECT utility_id FROM tmp_guard_refs),
    p_tipo_commessa => 'AUTO',
    p_policy_fatturazione => 'DA_DOCUMENTO',
    p_fatturazione_immediata => false,
    p_priorita_operativa => 'NORMALE',
    p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_guard_refs),
    p_competenza_dal => DATE '2026-07-01',
    p_competenza_al => DATE '2026-07-31',
    p_meta => jsonb_build_object('test_scope', 'pgtap_guard_sorgente_host'),
    p_force_new => true
  ) AS commessa_host,
  vendite.fn_get_or_create_commessa(
    p_billing_account_id => (SELECT billing_account_id FROM tmp_guard_refs),
    p_utility_id => (SELECT utility_id FROM tmp_guard_refs),
    p_tipo_commessa => 'AUTO',
    p_policy_fatturazione => 'DA_DOCUMENTO',
    p_fatturazione_immediata => false,
    p_priorita_operativa => 'NORMALE',
    p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_guard_refs),
    p_competenza_dal => DATE '2026-07-01',
    p_competenza_al => DATE '2026-07-31',
    p_meta => jsonb_build_object('test_scope', 'pgtap_guard_sorgente_src1'),
    p_force_new => true
  ) AS commessa_src1,
  vendite.fn_get_or_create_commessa(
    p_billing_account_id => (SELECT billing_account_id FROM tmp_guard_refs),
    p_utility_id => (SELECT utility_id FROM tmp_guard_refs),
    p_tipo_commessa => 'AUTO',
    p_policy_fatturazione => 'DA_DOCUMENTO',
    p_fatturazione_immediata => false,
    p_priorita_operativa => 'NORMALE',
    p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_guard_refs),
    p_competenza_dal => DATE '2026-07-01',
    p_competenza_al => DATE '2026-07-31',
    p_meta => jsonb_build_object('test_scope', 'pgtap_guard_sorgente_src2'),
    p_force_new => true
  ) AS commessa_src2;

-- ============================================================
-- 7) INSERT canonico: tipo a chiave id + id::text di documento esistente
-- ============================================================
SELECT lives_ok(
  format(
    $$INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
      VALUES (%s, %s, %L, 'ROOT')$$,
    (SELECT commessa_host FROM tmp_guard_commesse),
    (SELECT src_commessa FROM tmp_guard_refs),
    (SELECT commessa_src1::text FROM tmp_guard_commesse)
  ),
  '7) INSERT canonico id::text (documento esistente) -> passa il guard'
);

-- ============================================================
-- 8) INSERT uuid per tipo a chiave id -> E_SORG_FORMATO
--    (bypass della fn: e' il guard a dover bloccare)
-- ============================================================
SELECT throws_ok(
  format(
    $$INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
      VALUES (%s, %s, %L, 'COLLEGATO')$$,
    (SELECT commessa_host FROM tmp_guard_commesse),
    (SELECT src_commessa FROM tmp_guard_refs),
    gen_random_uuid()::text
  ),
  'P0001',
  NULL,
  '8) INSERT uuid per tipo a chiave id -> bloccato (E_SORG_FORMATO)'
);

-- ============================================================
-- 9) INSERT id inesistente -> E_SORG_NOT_FOUND
-- ============================================================
SELECT throws_ok(
  format(
    $$INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
      VALUES (%s, %s, %L, 'COLLEGATO')$$,
    (SELECT commessa_host FROM tmp_guard_commesse),
    (SELECT src_commessa FROM tmp_guard_refs),
    '999999999999'
  ),
  'P0001',
  NULL,
  '9) INSERT id inesistente -> bloccato (E_SORG_NOT_FOUND)'
);

-- ============================================================
-- 10) INSERT uuid ben formato ma inesistente per PREVENTIVO -> E_SORG_NOT_FOUND
-- ============================================================
SELECT throws_ok(
  format(
    $$INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
      VALUES (%s, %s, %L, 'COLLEGATO')$$,
    (SELECT commessa_host FROM tmp_guard_commesse),
    (SELECT src_preventivo FROM tmp_guard_refs),
    gen_random_uuid()::text
  ),
  'P0001',
  NULL,
  '10) INSERT uuid inesistente per PREVENTIVO -> bloccato (E_SORG_NOT_FOUND)'
);

-- ============================================================
-- 11) INSERT testo non-uuid per PREVENTIVO -> E_SORG_FORMATO
-- ============================================================
SELECT throws_ok(
  format(
    $$INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
      VALUES (%s, %s, %L, 'COLLEGATO')$$,
    (SELECT commessa_host FROM tmp_guard_commesse),
    (SELECT src_preventivo FROM tmp_guard_refs),
    'prev-fittizio-001'
  ),
  'P0001',
  NULL,
  '11) INSERT testo non-uuid per PREVENTIVO -> bloccato (E_SORG_FORMATO)'
);

-- ============================================================
-- 12) fn_link canonico id::text -> stocca com'e' (readback identico)
--     Due passi: la riga inserita dalla fn non e' visibile allo scan
--     della STESSA statement (visibilita' per command id).
-- ============================================================
CREATE TEMP TABLE tmp_guard_link12 AS
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_host FROM tmp_guard_commesse),
  p_sorgente_tipo_id => (SELECT src_commessa FROM tmp_guard_refs),
  p_sorgente_uid => (SELECT commessa_src2::text FROM tmp_guard_commesse),
  p_sorgente_riga => NULL,
  p_meta => '{}'::jsonb
) AS link_id;

SELECT is(
  (SELECT cs.sorgente_uid
     FROM vendite.commesse_sorgenti cs
    WHERE cs.id = (SELECT link_id FROM tmp_guard_link12)),
  (SELECT commessa_src2::text FROM tmp_guard_commesse),
  '12) fn_link canonico id::text -> stoccato invariato'
);

-- ============================================================
-- 13) fn_link uuid per COMMESSA: target vendite.commesse NON ha colonna uid
--     -> la traduzione non e' possibile, errore parlante (no crash)
-- ============================================================
SELECT throws_ok(
  format(
    $$SELECT vendite.fn_link_commessa_sorgente(%s, %s, %L, NULL, '{}'::jsonb)$$,
    (SELECT commessa_host FROM tmp_guard_commesse),
    (SELECT src_commessa FROM tmp_guard_refs),
    gen_random_uuid()::text
  ),
  'P0001',
  NULL,
  '13) fn_link uuid per tipo id a target senza colonna uid -> E_SORG_NORM_NON_RISOLTA'
);

-- ============================================================
-- 14) fn_link testo non-uuid per PREVENTIVO -> E_SORG_FORMATO (il rubinetto
--     non fa pass-through di spazzatura)
-- ============================================================
SELECT throws_ok(
  format(
    $$SELECT vendite.fn_link_commessa_sorgente(%s, %s, %L, NULL, '{}'::jsonb)$$,
    (SELECT commessa_host FROM tmp_guard_commesse),
    (SELECT src_preventivo FROM tmp_guard_refs),
    'A-' || substr(md5(clock_timestamp()::text), 1, 14)
  ),
  'P0001',
  NULL,
  '14) fn_link testo non-uuid per PREVENTIVO -> E_SORG_FORMATO'
);

-- ============================================================
-- 15) fn_link uuid inesistente per ORDINE_VENDITA (target CON colonna uid):
--     la traduzione parte ma non risolve -> E_SORG_NORM_NON_RISOLTA
-- ============================================================
SELECT throws_ok(
  format(
    $$SELECT vendite.fn_link_commessa_sorgente(%s, %s, %L, NULL, '{}'::jsonb)$$,
    (SELECT commessa_host FROM tmp_guard_commesse),
    (SELECT src_ordine FROM tmp_guard_refs),
    gen_random_uuid()::text
  ),
  'P0001',
  NULL,
  '15) fn_link uuid inesistente per ORDINE_VENDITA -> E_SORG_NORM_NON_RISOLTA'
);

-- ============================================================
-- 16) fn_link con uuid di un ordine REALE non ancora linkato ->
--     normalizzato a id::text (traduzione riuscita). Data-dependent:
--     skip se il DB non ha ordini liberi.
-- ============================================================
CREATE TEMP TABLE tmp_ordine_libero AS
SELECT o.id, o.uid
  FROM vendite.ordini o
 WHERE NOT EXISTS (
         SELECT 1 FROM vendite.commesse_sorgenti cs
          WHERE cs.sorgente_tipo_id = (SELECT src_ordine FROM tmp_guard_refs)
            AND cs.sorgente_uid IN (o.id::text, o.uid::text))
 ORDER BY o.id
 LIMIT 1;

-- Due passi anche qui (visibilita' per command id); la fn viene chiamata
-- solo se esiste un ordine libero (CASE lazy).
CREATE TEMP TABLE tmp_guard_link16 AS
SELECT CASE WHEN EXISTS (SELECT 1 FROM tmp_ordine_libero)
  THEN vendite.fn_link_commessa_sorgente(
    p_commessa_id => (SELECT commessa_host FROM tmp_guard_commesse),
    p_sorgente_tipo_id => (SELECT src_ordine FROM tmp_guard_refs),
    p_sorgente_uid => (SELECT uid::text FROM tmp_ordine_libero),
    p_sorgente_riga => NULL,
    p_meta => '{}'::jsonb)
  ELSE NULL
END AS link_id;

SELECT CASE WHEN EXISTS (SELECT 1 FROM tmp_ordine_libero)
  THEN is(
    (SELECT cs.sorgente_uid
       FROM vendite.commesse_sorgenti cs
      WHERE cs.id = (SELECT link_id FROM tmp_guard_link16)),
    (SELECT id::text FROM tmp_ordine_libero),
    '16) fn_link uuid di ordine reale -> normalizzato a id::text')
  ELSE skip('16) nessun ordine libero nel DB: skip traduzione uuid->id', 1)
END;

-- ============================================================
-- 17..18) censimento: tutte le righe vive rispettano la convenzione
--     (id-selector -> numerico; uid-selector -> uuid). Se questo test e'
--     rosso, PRIMA di applicare i trigger serve la pulizia manuale
--     (brief-db-guard-sorgente-polimorfa, Appendice A).
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM vendite.commesse_sorgenti cs
     JOIN config.sorgenti s ON s.id = cs.sorgente_tipo_id
    WHERE (s.key_selector = 'id'  AND btrim(cs.sorgente_uid) !~ '^[0-9]+$')
       OR (s.key_selector = 'uid' AND btrim(cs.sorgente_uid) !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')),
  0,
  '17) commesse_sorgenti: nessuna riga viva fuori convenzione'
);

SELECT is(
  (SELECT count(*)::int
     FROM pratiche.pratiche_sorgenti ps
     JOIN config.sorgenti s ON s.id = ps.sorgente_tipo_id
    WHERE (s.key_selector = 'id'  AND btrim(ps.sorgente_uid) !~ '^[0-9]+$')
       OR (s.key_selector = 'uid' AND btrim(ps.sorgente_uid) !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')),
  0,
  '18) pratiche_sorgenti: nessuna riga viva fuori convenzione'
);

SELECT * FROM finish();
ROLLBACK;
