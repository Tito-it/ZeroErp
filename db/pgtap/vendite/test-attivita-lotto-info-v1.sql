-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_get_attivita_lotto_info (changeset 20260223-03)
-- ------------------------------------------------------------
-- Indice test (1..8):
-- 1) Funzione fn_get_attivita_lotto_info presente
-- 2) Riferimenti minimi presenti
-- 3) Lotto attivita creato
-- 4) Ritorna una riga per lotto esistente
-- 5) stato_lotto valorizzato
-- 6) stato_operativo valorizzato
-- 7) is_in_esecuzione coerente con stato_lotto
-- 8) Lotto inesistente restituisce 0 righe
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

SELECT plan(8);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_get_attivita_lotto_info'
  ),
  'Funzione fn_get_attivita_lotto_info presente'
);

CREATE TEMP TABLE tmp_refs_ali AS
SELECT
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
    SELECT billing_account_id IS NOT NULL
       AND utility_id IS NOT NULL
       AND emittente_soggetto_ruolo_id IS NOT NULL
    FROM tmp_refs_ali
  ),
  'Riferimenti minimi presenti'
);

CREATE TEMP TABLE tmp_lotto_ali AS
SELECT vendite.fn_get_or_create_lotto_attivita(
  p_lotto_id => NULL,
  p_competenza_mese => date_trunc('month', current_date)::date,
  p_utility_id => (SELECT utility_id FROM tmp_refs_ali),
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ali),
  p_sorgente_tipo_id => NULL,
  p_lock_batch_id => NULL,
  p_meta => jsonb_build_object('test_scope', 'pgtap_attivita_lotto_info'),
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_ali)
) AS lotto_id;

SELECT ok(
  (SELECT lotto_id IS NOT NULL FROM tmp_lotto_ali),
  'Lotto attivita creato'
);

SELECT is(
  (
    SELECT COUNT(*)
    FROM vendite.fn_get_attivita_lotto_info((SELECT lotto_id FROM tmp_lotto_ali))
  ),
  1::bigint,
  'Ritorna una riga per lotto esistente'
);

SELECT ok(
  (
    SELECT stato_lotto IS NOT NULL
    FROM vendite.fn_get_attivita_lotto_info((SELECT lotto_id FROM tmp_lotto_ali))
  ),
  'stato_lotto valorizzato'
);

SELECT ok(
  (
    SELECT stato_operativo IS NOT NULL
    FROM vendite.fn_get_attivita_lotto_info((SELECT lotto_id FROM tmp_lotto_ali))
  ),
  'stato_operativo valorizzato'
);

SELECT ok(
  (
    SELECT is_in_esecuzione = (stato_lotto = 'IN_ESECUZIONE')
    FROM vendite.fn_get_attivita_lotto_info((SELECT lotto_id FROM tmp_lotto_ali))
  ),
  'is_in_esecuzione coerente con stato_lotto'
);

SELECT is(
  (
    SELECT COUNT(*)
    FROM vendite.fn_get_attivita_lotto_info(999999999)
  ),
  0::bigint,
  'Lotto inesistente restituisce 0 righe'
);

SELECT * FROM finish();
ROLLBACK;

