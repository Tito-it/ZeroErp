-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.trgfn_fatture_guard_numero_fiscale — una fattura numerata
--   non si cancella, e registro, anno, serie e numero non cambiano piu'.
--   ChangeSet 20261004-80 (funzione), -81 (trigger _a05_).
-- Brief: brief-db-esclusioni-implicite (Q-4).
--
-- Elenco test (plan 11):
--  Struttura
--   1) il trigger e' BEFORE UPDATE OR DELETE, senza colonne (niente OF), con
--      WHEN su OLD.numero, e la funzione e' SECURITY INVOKER
--  Cio' che passa — i controlli: un guard che negasse tutto sarebbe verde ai
--  test 6-10 senza essere corretto
--   2) una fattura NON numerata si cancella
--   3) la numerazione (numero e anno da NULL) passa
--   4) un UPDATE che riscrive il numero UGUALE passa (il confronto e' sul
--      valore, non sulla lista del SET)
--   5) un UPDATE di una colonna non fiscale su una numerata passa
--  Cio' che si ferma
--   6) DELETE di una fattura numerata
--   7) UPDATE che toglie il numero (numero = NULL): il retro della DELETE
--   8) UPDATE che cambia il numero
--   9) UPDATE che cambia la serie
--  10) UPDATE che cambia l'anno
--  Presidi
--  11) i due codici sono registrati, vivi, CONFLITTO_STATO, e hanno la frase
--
-- Scopo:
--  - ⭐ il caso si COSTRUISCE: due fatture DRAFT dal builder, una delle due
--    numerata qui con un UPDATE da NULL (la stessa scrittura di
--    fn_assign_numero_fattura). Il test non chiede ai dati di oggi di
--    contenere una fattura numerata;
--  - ⚠️ gli errori si asseriscono sulla FRASE (throws_like): i due codici sono
--    entrambi P0001, e P0001 direbbe solo «errore di dominio». I pattern si
--    fermano prima e dopo il segnaposto del numero;
--  - la corsa che il guard chiude (numerazione concorrente fra la check e la
--    DELETE di fn_cleanup_fatture_by_ids) richiede due sessioni: qui si prova
--    l'invariante che la rende innocua — la DELETE di una numerata non passa
--    da nessuna strada.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il test gira come l'applicazione (zeroerp_app, RLS
-- attiva). Su un database vuoto questa riga costruisce azienda + operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- Vincoli differiti: scattano a fine istruzione, non al COMMIT che qui non
-- arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- Fixture: due fatture DRAFT dello stesso cliente
-- ============================================================
-- ⛔ Il builder scrive: si legge in un'istruzione separata.
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP guard numero fiscale');

CREATE TEMP TABLE _f AS
SELECT (SELECT f.fattura_id FROM dbops.fn_pgtap_crea_fattura('guard numero libera', 'DRAFT',
            (SELECT m.billing_account_id FROM _m m)) f) AS libera,
       (SELECT f.fattura_id FROM dbops.fn_pgtap_crea_fattura('guard numero numerata', 'DRAFT',
            (SELECT m.billing_account_id FROM _m m)) f) AS numerata;

-- ============================================================
-- 1) Struttura
-- ============================================================
-- ⚠️ Niente OF: un trigger UPDATE OF scatta solo se la colonna e' nel SET, e
--   NON se la cambia un altro trigger BEFORE. Il confronto OLD/NEW sta nella
--   funzione, e il trigger deve vedere ogni UPDATE.
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_proc p ON p.oid = t.tgfoid
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE t.tgrelid = 'vendite.fatture'::regclass
           AND t.tgname  = 'trg_fatture_a05_guard_numero_fiscale_upd_dlt'
           AND NOT t.tgisinternal
           AND (t.tgtype & 2)  <> 0                       -- BEFORE
           AND (t.tgtype & 1)  <> 0                       -- FOR EACH ROW
           AND (t.tgtype & 8)  <> 0                       -- DELETE
           AND (t.tgtype & 16) <> 0                       -- UPDATE
           AND cardinality(t.tgattr::int2[]) = 0          -- niente OF
           AND pg_get_triggerdef(t.oid) LIKE '%WHEN%old.numero IS NOT NULL%'
           AND n.nspname = 'vendite'
           AND p.proname = 'trgfn_fatture_guard_numero_fiscale'
           AND NOT p.prosecdef),
    '1) trigger BEFORE UPDATE OR DELETE, senza OF, WHEN su OLD.numero; funzione INVOKER'
);

-- ============================================================
-- 2-5) Cio' che passa
-- ============================================================
SELECT lives_ok(
    $$DELETE FROM vendite.fatture WHERE id = (SELECT libera FROM _f)$$,
    '2) una fattura NON numerata si cancella'
);

-- La stessa scrittura di vendite.fn_assign_numero_fattura: anno e numero da
-- NULL. Il WHEN del trigger la lascia fuori.
SELECT lives_ok(
    $$UPDATE vendite.fatture
         SET anno   = EXTRACT(YEAR FROM script.fn_data_operativa())::smallint,
             numero = 987654321
       WHERE id = (SELECT numerata FROM _f)$$,
    '3) la numerazione (numero e anno da NULL) passa'
);

SELECT lives_ok(
    $$UPDATE vendite.fatture SET numero = numero WHERE id = (SELECT numerata FROM _f)$$,
    '4) riscrivere il numero UGUALE passa: il confronto e'' sul valore, non sul SET'
);

SELECT lives_ok(
    $$UPDATE vendite.fatture
         SET meta = meta || jsonb_build_object('pgtap_guard_numero', true)
       WHERE id = (SELECT numerata FROM _f)$$,
    '5) un UPDATE di una colonna non fiscale su una numerata passa'
);

-- ============================================================
-- 6-10) Cio' che si ferma
-- ============================================================
SELECT throws_like(
    $$DELETE FROM vendite.fatture WHERE id = (SELECT numerata FROM _f)$$,
    '%ha già un numero fiscale: non si può cancellare%',
    '6) DELETE di una fattura numerata: E_FATTURA_NUMERATA_NON_CANCELLABILE'
);

-- ⭐ Il retro: senza questo ramo bastava togliere il numero e poi cancellare.
SELECT throws_like(
    $$UPDATE vendite.fatture SET numero = NULL WHERE id = (SELECT numerata FROM _f)$$,
    '%ha già un numero fiscale: registro, anno, serie e numero non si possono più cambiare%',
    '7) togliere il numero a una numerata: E_FATTURA_NUMERO_NON_MODIFICABILE'
);

SELECT throws_like(
    $$UPDATE vendite.fatture SET numero = numero + 1 WHERE id = (SELECT numerata FROM _f)$$,
    '%ha già un numero fiscale: registro, anno, serie e numero non si possono più cambiare%',
    '8) cambiare il numero: E_FATTURA_NUMERO_NON_MODIFICABILE'
);

SELECT throws_like(
    $$UPDATE vendite.fatture SET serie = 'PGTZ' WHERE id = (SELECT numerata FROM _f)$$,
    '%ha già un numero fiscale: registro, anno, serie e numero non si possono più cambiare%',
    '9) cambiare la serie: E_FATTURA_NUMERO_NON_MODIFICABILE'
);

SELECT throws_like(
    $$UPDATE vendite.fatture SET anno = anno + 1 WHERE id = (SELECT numerata FROM _f)$$,
    '%ha già un numero fiscale: registro, anno, serie e numero non si possono più cambiare%',
    '10) cambiare l''anno: E_FATTURA_NUMERO_NON_MODIFICABILE'
);

-- ============================================================
-- 11) Presidi sul catalogo dei codici
-- ============================================================
SELECT is(
    (SELECT jsonb_agg(ce.codice || ':' || ce.classe ORDER BY ce.codice)
       FROM config.codici_errore ce
       JOIN config.messaggi_errore me
         ON me.codice = ce.codice AND me.lingua = 'it'
      WHERE ce.codice IN ('E_FATTURA_NUMERATA_NON_CANCELLABILE',
                          'E_FATTURA_NUMERO_NON_MODIFICABILE')
        AND ce.obsoleto_dal IS NULL),
    '["E_FATTURA_NUMERATA_NON_CANCELLABILE:CONFLITTO_STATO", "E_FATTURA_NUMERO_NON_MODIFICABILE:CONFLITTO_STATO"]'::jsonb,
    '11) i due codici sono registrati, vivi, CONFLITTO_STATO, con la frase italiana'
);

-- ============================================================
-- Chiusura: niente cleanup, ci pensa il ROLLBACK
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
