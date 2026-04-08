-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.fn_lookup_utilities_per_ba
--       Combo utility "guidata da BA" (intersezione ruolo soggetto x ruolo EF).
--
-- Elenco test:
--  1) p_billing_account_id NULL -> throws E_PARAMETRO_INVALIDO
--  2) p_billing_account_id <= 0 -> throws E_PARAMETRO_INVALIDO
--  3) p_ruolo_codice_soggetto NULL -> throws E_PARAMETRO_INVALIDO
--  4) BA esistente + ruolo CL -> ritorna >= 0 righe (smoke), tutte con
--     codice utility non nullo e is_personalizzata_per_ef boolean.
--  5) is_personalizzata_per_ef = true se esiste row in
--     emittenti_fiscali_utilities per (emittente, utility), false altrimenti.
--
-- NOTA: i casi 4-5 dipendono dallo stato del DB di sviluppo. Sono "smoke"
-- pragmatici, non test esaustivi della politica ibrida.
-- ------------------------------------------------------------

BEGIN;

SELECT plan(5);

-- ============================================================
-- 1) p_billing_account_id NULL -> throws
-- ============================================================
SELECT throws_like(
    $$ SELECT * FROM anagrafiche.fn_lookup_utilities_per_ba(NULL, 'CL') $$,
    '%p_billing_account_id%',
    'fn_lookup_utilities_per_ba(NULL, ''CL'') -> throws parametro invalido'
);

-- ============================================================
-- 2) p_billing_account_id <= 0 -> throws
-- ============================================================
SELECT throws_like(
    $$ SELECT * FROM anagrafiche.fn_lookup_utilities_per_ba(-1, 'CL') $$,
    '%p_billing_account_id%',
    'fn_lookup_utilities_per_ba(-1, ''CL'') -> throws parametro invalido'
);

-- ============================================================
-- 3) p_ruolo_codice_soggetto NULL -> throws
-- ============================================================
-- Serve un BA "valido" per superare il primo guard.
-- Precalcoliamo: BA con mapping specifico in emittenti_fiscali_billing_account
-- + emittente PK risolto. Se non c'e' nulla -> i casi 4-5 sono skip soft.
CREATE TEMP TABLE tmp_lookup_ba AS
SELECT ba.id                  AS ba_id,
       ef.id                  AS emittente_pk,
       ef.soggetto_ruolo_id   AS emittente_sr_id
FROM anagrafiche.billing_account ba
JOIN anagrafiche.emittenti_fiscali_billing_account efba
  ON efba.billing_account_id = ba.id
JOIN anagrafiche.emittenti_fiscali ef
  ON ef.soggetto_ruolo_id = efba.emittente_soggetto_ruolo_id
WHERE ef.attivo = true
LIMIT 1;

SELECT throws_like(
    $$ SELECT * FROM anagrafiche.fn_lookup_utilities_per_ba(
           coalesce((SELECT ba_id FROM tmp_lookup_ba), 1::bigint),
           NULL
       ) $$,
    '%p_ruolo_codice_soggetto%',
    'fn_lookup_utilities_per_ba(BA, NULL) -> throws parametro invalido'
);

-- ============================================================
-- 4) Smoke: ritorno tabellare per ruolo CL (utility cliente)
-- ============================================================
CREATE TEMP TABLE tmp_lookup_results AS
SELECT *
  FROM anagrafiche.fn_lookup_utilities_per_ba(
      (SELECT ba_id FROM tmp_lookup_ba),
      'CL'
  )
 WHERE (SELECT ba_id FROM tmp_lookup_ba) IS NOT NULL;

SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM tmp_lookup_results WHERE codice IS NULL OR codice = ''
    ),
    'Tutte le righe ritornate hanno codice utility valorizzato'
);

-- ============================================================
-- 5) is_personalizzata_per_ef coerente con emittenti_fiscali_utilities
--    Verifica: se r.is_personalizzata_per_ef = true allora deve esistere
--    una riga attiva in emittenti_fiscali_utilities per (emittente del BA,
--    utility_id). Emittente PK precalcolato in tmp_lookup_ba per evitare
--    chiamate ripetute a fn_get_emittente_fiscale_pk dentro NOT EXISTS.
-- ============================================================
SELECT is(
    (SELECT COUNT(*)::int
       FROM tmp_lookup_results r
      WHERE r.is_personalizzata_per_ef = true
        AND NOT EXISTS (
            SELECT 1
              FROM anagrafiche.emittenti_fiscali_utilities efu
             WHERE efu.utility_id = r.utility_id
               AND efu.attivo = true
               AND efu.emittente_soggetto_ruolo_id =
                   (SELECT emittente_sr_id FROM tmp_lookup_ba)
        )
    ),
    0,
    'is_personalizzata_per_ef coerente con emittenti_fiscali_utilities'
);

SELECT * FROM finish();
ROLLBACK;
