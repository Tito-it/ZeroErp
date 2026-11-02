-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
--  6) FIX codice_interno (analisi-hardcoded-codice §3a #15 / §9.5): con una utility
--     mappata sia a CL sia a EF (per codice_interno), la funzione la RITORNA.
--     Col vecchio `codice` (tipi_ruoli: CL/CLIENTE, EF/EMITT_FISC) i JOIN
--     fallivano -> 0 righe. Prova reale del fix.
--  7) anti-regressione: rename del `codice` (mutabile) dei ruoli CL/EF -> la
--     funzione resta invariata (risolve per codice_interno).
--
-- NOTA: i casi 4-5 dipendono dallo stato del DB di sviluppo. Sono "smoke"
-- pragmatici, non test esaustivi della politica ibrida. I casi 6-7 sono reali
-- quando il DB ha un BA con emittente risolvibile e una utility con ruolo CL
-- (degradano a soft-pass se i prerequisiti non ci sono).
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

SELECT plan(7);

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

-- ============================================================
-- 6) FIX codice_interno: utility mappata a CL + EF -> ritornata
--    Fixture: prende una utility con mapping ATTIVO al ruolo CL (codice_interno)
--    e le aggiunge il mapping al ruolo EF (codice_interno), cosi' l'intersezione
--    CL x EF della funzione ha almeno una utility candidata.
-- ============================================================
CREATE TEMP TABLE tmp_lookup_util AS
SELECT utr.utility_id
  FROM config.utilities_tipi_ruolo utr
  JOIN config.tipi_ruoli tr ON tr.id = utr.tipo_ruolo_id
 WHERE tr.codice_interno = 'CL'
   AND utr.attivo = true
   AND (utr.valido_dal IS NULL OR utr.valido_dal <= script.fn_data_operativa())
   AND (utr.valido_al  IS NULL OR utr.valido_al  >= script.fn_data_operativa())
 LIMIT 1;

-- Aggiunge il mapping EF per quella utility (il seed non mappa nulla a EF).
INSERT INTO config.utilities_tipi_ruolo (utility_id, tipo_ruolo_id, attivo, meta)
SELECT (SELECT utility_id FROM tmp_lookup_util),
       (SELECT id FROM config.tipi_ruoli WHERE codice_interno = 'EF'),
       true,
       '{}'::jsonb
WHERE (SELECT utility_id FROM tmp_lookup_util) IS NOT NULL
ON CONFLICT (utility_id, tipo_ruolo_id) DO NOTHING;

SELECT ok(
    -- soft-pass se mancano i prerequisiti (BA con emittente / utility CL);
    -- assertion REALE quando presenti: col vecchio `codice` qui avremmo 0 righe.
    (SELECT ba_id FROM tmp_lookup_ba) IS NULL
    OR (SELECT utility_id FROM tmp_lookup_util) IS NULL
    OR EXISTS (
        SELECT 1
          FROM anagrafiche.fn_lookup_utilities_per_ba(
                   (SELECT ba_id FROM tmp_lookup_ba), 'CL')
         WHERE utility_id = (SELECT utility_id FROM tmp_lookup_util)
    ),
    '6. fn risolve i ruoli per codice_interno: utility CL+EF ritornata (col vecchio codice: 0 righe)'
);

-- ============================================================
-- 7) Anti-regressione: rename del `codice` (mutabile) dei ruoli CL/EF
--    -> la funzione resta invariata (usa codice_interno). codice_interno lockato.
-- ============================================================
-- codice e' varchar(10) (EMITT_FISC e' gia' 10 char): si SOSTITUISCE con un
-- valore corto e distinto (non si appende), comunque != codice_interno.
UPDATE config.tipi_ruoli
   SET codice = 'REN' || id::text
 WHERE codice_interno IN ('CL', 'EF');

SELECT ok(
    (SELECT ba_id FROM tmp_lookup_ba) IS NULL
    OR (SELECT utility_id FROM tmp_lookup_util) IS NULL
    OR EXISTS (
        SELECT 1
          FROM anagrafiche.fn_lookup_utilities_per_ba(
                   (SELECT ba_id FROM tmp_lookup_ba), 'CL')
         WHERE utility_id = (SELECT utility_id FROM tmp_lookup_util)
    ),
    '7. anti-regressione: rename codice ruoli CL/EF -> fn invariata (risoluzione per codice_interno)'
);

SELECT * FROM finish();
ROLLBACK;
