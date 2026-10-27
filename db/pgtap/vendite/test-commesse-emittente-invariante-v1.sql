-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'emittente della commessa e' un invariante derivato dal billing account
-- Oggetti:
--   vendite.trgfn_commesse_default_emittente()      (20260826-39)
--   vendite.trgfn_commesse_guard_emittente_ba()     (20260826-40)
--   vendite.commesse.emittente_soggetto_ruolo_id NOT NULL (20260826-41)
--
-- Elenco test (plan 7):
--  1) Precondizioni: BA dell'operatore + un soggetto_ruolo estraneo
--  2) La colonna e' NOT NULL                                        [H1]
--  3) INSERT senza emittente -> la riga nasce con quello del BA     [L1]
--  4) INSERT con un emittente DIVERSO -> P0001                      [L2]
--  5) ... e la frase nomina la commessa e i due emittenti           [L2]
--  6) UPDATE che sposta l'emittente -> P0001                        [L2]
--  7) UPDATE di una colonna QUALSIASI -> passa                      [presidia UPDATE OF]
--
-- Scopo:
--  - il 3) prova che l'emittente non va piu' passato da fuori (D-1);
--  - il 4/5/6) provano che un valore diverso da quello derivato non entra,
--    da QUALUNQUE scrittore — qui si scrive con una INSERT diretta, non
--    passando da vendite.fn_get_or_create_commessa, ed e' il punto;
--  - ⭐ il 7) e' l'asserzione che presidia la scelta `UPDATE OF` del guard:
--    senza, il giorno in cui qualcuno la togliesse (rivalidando a ogni
--    UPDATE) le commesse si congelerebbero al primo cambio di mapping del
--    billing account, e non se ne accorgerebbe nessuno.
--
-- Piano: brief-db-emittente-commessa-invariante, L8 (§7.8)
-- ------------------------------------------------------------

-- =========================================================
-- Cleanup iniziale (idempotente, FUORI dalla transazione)
-- ⚠️ In coda non verrebbe raggiunto mai: il runner gira con ON_ERROR_STOP.
-- =========================================================
DO $$
BEGIN
    DELETE FROM vendite.commesse c
     WHERE c.codice LIKE 'TST-EMITT-INV-%';
END;
$$;

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione
-- (ruolo OPERATORE + RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- =========================================================
-- 0) Riferimenti: un billing account su cui l'operatore SCRIVE davvero
-- =========================================================
-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba, BA gia' legato all'azienda di chi
--   agisce: l'unico su cui la policy rls_commesse_ef_whitelist lo lascia
--   scrivere), e l'emittente estraneo e' un'ALTRA azienda costruita
--   (dbops.fn_pgtap_crea_emittente_operatore). Prima si pescavano con
--   LIMIT 1, e su un database ricostruito da zero non c'erano.
CREATE TEMP TABLE tmp_cli_emitt_inv AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('emittente invariante');

CREATE TEMP TABLE tmp_altra_emitt_inv AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE tmp_refs_emitt_inv AS
SELECT
    c.billing_account_id                             AS billing_account_id,
    c.utility_id                                     AS utility_id,
    script.fn_pgtap_emittente_sr_operatore()         AS emittente_sr_ok,
    -- Un soggetto_ruolo diverso dall'emittente dell'operatore: il guard
    -- confronta due soggetti_ruoli, e la sola FK in gioco e'
    -- fk_commesse_emittente verso anagrafiche.soggetti_ruoli.
    a.soggetto_ruolo_id                              AS emittente_sr_estraneo
  FROM tmp_cli_emitt_inv c
 CROSS JOIN tmp_altra_emitt_inv a;

SELECT ok(
    (SELECT billing_account_id IS NOT NULL
        AND utility_id IS NOT NULL
        AND emittente_sr_ok IS NOT NULL
        AND emittente_sr_estraneo IS NOT NULL
     FROM tmp_refs_emitt_inv),
    'Precondizioni: billing account dell''operatore + un soggetto_ruolo estraneo'
);

-- =========================================================
-- 2) H1 — la colonna e' NOT NULL
-- =========================================================
SELECT col_not_null(
    'vendite', 'commesse', 'emittente_soggetto_ruolo_id',
    'H1: vendite.commesse.emittente_soggetto_ruolo_id e'' NOT NULL (chiave di perimetro)'
);

-- =========================================================
-- 3) L1 — INSERT senza emittente: la riga nasce con quello del BA
-- =========================================================
-- ⚠️ Il verbo va chiamato in un'istruzione SEPARATA dall'asserzione: la
--   snapshot di statement leggerebbe PRIMA delle scritture, e il rosso
--   accuserebbe il trigger invece del test.
INSERT INTO vendite.commesse (codice, billing_account_id, utility_id)
SELECT 'TST-EMITT-INV-DERIVA', r.billing_account_id, r.utility_id
  FROM tmp_refs_emitt_inv r;

SELECT is(
    (SELECT c.emittente_soggetto_ruolo_id
       FROM vendite.commesse c
      WHERE c.codice = 'TST-EMITT-INV-DERIVA'),
    (SELECT r.emittente_sr_ok FROM tmp_refs_emitt_inv r),
    'L1: la commessa nasce con l''emittente DERIVATO dal billing account'
);

-- =========================================================
-- 4/5) L2 — INSERT con un emittente diverso: si blocca, e lo dice
-- =========================================================
SELECT throws_ok(
    format(
        $q$INSERT INTO vendite.commesse (codice, billing_account_id, utility_id, emittente_soggetto_ruolo_id)
           VALUES ('TST-EMITT-INV-DIVERSO', %s, %s, %s)$q$,
        (SELECT billing_account_id    FROM tmp_refs_emitt_inv),
        (SELECT utility_id            FROM tmp_refs_emitt_inv),
        (SELECT emittente_sr_estraneo FROM tmp_refs_emitt_inv)
    ),
    'P0001',
    NULL,
    'L2: una INSERT DIRETTA con un emittente diverso da quello del BA e'' respinta'
);

-- ⚠️ throws_like sulla frase: qui il messaggio E'' la posta in gioco — deve
--   nominare la commessa e i due emittenti, non i nomi delle colonne.
SELECT throws_like(
    format(
        $q$INSERT INTO vendite.commesse (codice, billing_account_id, utility_id, emittente_soggetto_ruolo_id)
           VALUES ('TST-EMITT-INV-DIVERSO-2', %s, %s, %s)$q$,
        (SELECT billing_account_id    FROM tmp_refs_emitt_inv),
        (SELECT utility_id            FROM tmp_refs_emitt_inv),
        (SELECT emittente_sr_estraneo FROM tmp_refs_emitt_inv)
    ),
    -- rev 2026-10-10 (brief-db-guard-emittente-ba-unico, D-2/D-3): la frase e'
    --   quella del BB, «l'azienda indicata (…) non e' quella del cliente (…,
    --   billing account …)», con i nomi delle aziende.
    '%TST-EMITT-INV-DIVERSO-2%non e%quella del cliente%billing account%',
    'L2: la frase nomina la commessa e i due emittenti'
);

-- =========================================================
-- 6) L2 — UPDATE che sposta l'emittente: si blocca
-- =========================================================
SELECT throws_ok(
    format(
        $q$UPDATE vendite.commesse SET emittente_soggetto_ruolo_id = %s
            WHERE codice = 'TST-EMITT-INV-DERIVA'$q$,
        (SELECT emittente_sr_estraneo FROM tmp_refs_emitt_inv)
    ),
    'P0001',
    NULL,
    'L2: spostare l''emittente di una commessa esistente e'' respinto'
);

-- =========================================================
-- 7) ⭐ UPDATE di una colonna QUALSIASI: deve passare
-- =========================================================
-- E' l'asserzione che presidia `UPDATE OF`. Se un giorno il guard venisse
-- montato su UPDATE nudo, questa diventerebbe rossa — ed e' l'unico posto in
-- cui quel cambiamento si vedrebbe prima che, al primo spostamento di mapping
-- del billing account, tutte le commesse del cliente diventino non piu'
-- modificabili.
SELECT lives_ok(
    $q$UPDATE vendite.commesse SET priorita_operativa = 'ALTA'
        WHERE codice = 'TST-EMITT-INV-DERIVA'$q$,
    'UPDATE di una colonna estranea alla coppia: passa (il guard e'' UPDATE OF)'
);

SELECT * FROM finish();
ROLLBACK;
