-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: immutabilita' della colonna canale_origine su
--   - anagrafiche.billing_account
--   - vendite.ordini
--   - vendite.fatture
-- Riferimento: migration 20260420-04 (§6.4 guida multi-face v2.0).
--
-- Trigger verificato:
--   trg_<tab>_a10_canale_origine_immutable_upd ->
--     script.trgfn_canale_origine_immutable()
--   Solleva E_CANALE_ORIGINE_IMMUTABILE su modifica della colonna.
--   UPDATE OF canale_origine: non scatta se la colonna non e'
--   nel SET.
--
-- Strategia: UPDATE ... SET canale_origine = '<valore>' con WHERE
-- che punta a una riga esistente. Verifica:
--   - stesso valore (no-op) -> lives_ok (IS DISTINCT FROM e' false)
--   - valore diverso -> throws (trigger blocca)
-- I test usano tutti UPDATE OF canale_origine esplicito per
-- forzare lo scatto del trigger; un UPDATE che non tocca la
-- colonna non farebbe scattare (e non va testato qui).
--
-- Indice test (1..5):
--    1. Precondizione: fixture BA + ordine + fattura disponibili
--    2. UPDATE BA canale_origine = canale_origine (stesso valore) -> lives_ok
--    3. UPDATE BA canale_origine da ADMIN a PORTALE -> throws
--    4. UPDATE vendite.ordini canale_origine da ADMIN a SHOP -> throws
--    5. UPDATE vendite.fatture canale_origine da ADMIN a PORTALE -> throws
--
-- BEGIN; + rollback implicito a fine file.
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

SELECT plan(5);

-- =========================================================
-- 1) Precondizione informativa: fixture BA + ordine + fattura.
--    Le 3 fixture sono indipendenti: se una manca, solo il test
--    corrispondente skippa (gli altri proseguono).
-- =========================================================
CREATE TEMP TABLE _t_ba AS
SELECT id AS ba_id
  FROM anagrafiche.billing_account
 ORDER BY id
 LIMIT 1;

CREATE TEMP TABLE _t_ordine AS
SELECT id AS ord_id
  FROM vendite.ordini
 ORDER BY id
 LIMIT 1;

CREATE TEMP TABLE _t_fattura AS
SELECT id AS fat_id
  FROM vendite.fatture
 ORDER BY id
 LIMIT 1;

SELECT ok(
    true,
    format(
        '1. Precondizioni (informativa): BA=%s, ordine=%s, fattura=%s disponibili',
        (SELECT count(*) FROM _t_ba),
        (SELECT count(*) FROM _t_ordine),
        (SELECT count(*) FROM _t_fattura)
    )
);

-- =========================================================
-- 2) UPDATE BA canale_origine = valore corrente -> lives_ok
--    Il trigger usa IS DISTINCT FROM: stesso valore, nessun errore.
-- =========================================================
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM _t_ba) THEN
        lives_ok(
            format($sql$
                UPDATE anagrafiche.billing_account
                   SET canale_origine = canale_origine
                 WHERE id = %s
            $sql$, (SELECT ba_id FROM _t_ba)),
            '2. UPDATE BA canale_origine=canale_origine (stesso valore) -> ok'
        )
    ELSE skip('Nessun BA in anagrafiche.billing_account: test 2 skippato', 1)
END;

-- =========================================================
-- 3) UPDATE BA canale_origine ADMIN -> PORTALE -> throws
-- =========================================================
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM _t_ba) THEN
        throws_ok(
            format($sql$
                UPDATE anagrafiche.billing_account
                   SET canale_origine = 'PORTALE'::config.canale_origine
                 WHERE id = %s
            $sql$, (SELECT ba_id FROM _t_ba)),
            NULL, NULL,
            '3. UPDATE BA canale_origine ADMIN->PORTALE -> throws E_CANALE_ORIGINE_IMMUTABILE'
        )
    ELSE skip('Nessun BA disponibile: test 3 skippato', 1)
END;

-- =========================================================
-- 4) UPDATE vendite.ordini canale_origine ADMIN -> SHOP -> throws
-- =========================================================
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM _t_ordine) THEN
        throws_ok(
            format($sql$
                UPDATE vendite.ordini
                   SET canale_origine = 'SHOP'::config.canale_origine
                 WHERE id = %s
            $sql$, (SELECT ord_id FROM _t_ordine)),
            NULL, NULL,
            '4. UPDATE vendite.ordini canale ADMIN->SHOP -> throws E_CANALE_ORIGINE_IMMUTABILE'
        )
    ELSE skip('Nessun ordine in vendite.ordini: test 4 skippato', 1)
END;

-- =========================================================
-- 5) UPDATE vendite.fatture canale_origine ADMIN -> PORTALE -> throws
-- =========================================================
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM _t_fattura) THEN
        throws_ok(
            format($sql$
                UPDATE vendite.fatture
                   SET canale_origine = 'PORTALE'::config.canale_origine
                 WHERE id = %s
            $sql$, (SELECT fat_id FROM _t_fattura)),
            NULL, NULL,
            '5. UPDATE vendite.fatture canale ADMIN->PORTALE -> throws E_CANALE_ORIGINE_IMMUTABILE'
        )
    ELSE skip('Nessuna fattura in vendite.fatture: test 5 skippato', 1)
END;

SELECT * FROM finish();
ROLLBACK;
