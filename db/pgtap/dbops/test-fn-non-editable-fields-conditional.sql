-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_non_editable_fields — lock condizionali BoM articoli
-- (migration 20260522-02..04)
--
-- Verifica che fn_non_editable_fields restituisca correttamente i
-- flag di struttura bloccati in base alla presenza di BoM attive:
--
--   is_composito / requires_serial: bloccati se articolo PADRE di BoM attiva
--   is_solo_componente: bloccato se articolo FIGLIO in BoM attiva
--   is_composito: bloccato anche se articolo FIGLIO semplice di una BoM in
--     vigore o futura (20261013-04: la distinta ha un livello solo)
--
-- Setup fixture (4 articoli, 2 righe BoM, ROLLBACK finale):
--   LCC_X   standalone — nessuna BoM
--   LCC_W   padre — BoM W→Z (in vigore), W→Y (futura)
--   LCC_Z   figlio di una BoM in vigore
--   LCC_Y   figlio di una BoM futura
--
-- Indice test (1..4):
--   1. LCC_X (standalone):     nessuno dei 3 flag nei condizionali
--   2. LCC_W (padre):          is_composito + requires_serial presenti;
--                              is_solo_componente assente
--   3. LCC_Z (figlio in vigore): is_solo_componente e is_composito presenti;
--                              requires_serial assente
--   4. LCC_Y (figlio futuro):  is_composito presente; is_solo_componente e
--                              requires_serial assenti (le regole 20260522-04
--                              guardano la BoM in vigore, la 20261013-04 anche
--                              quella futura)
--
-- 🔴 rev 2026-10-13 (brief-db-articoli-ammessi-per-documento D-4). Prima Y era
--   «padre+figlio» (padre in Y→Z, figlio in W→Y, entrambi compositi), e il
--   test 4 voleva tutti e tre i flag bloccati. Era una distinta a due livelli:
--   catalogo.trgfn_articoli_componenti_guard_un_livello (20261013-01) la
--   rifiuta, e il caso non puo' piu' esistere. Il test 3 diceva anche che
--   is_composito su un figlio NON e' bloccato: dal 20261013-04 lo e', perche'
--   un componente non diventa composito.
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

SELECT plan(4);

-- =========================================================
-- Fixture: crea articoli e BoM nella transazione corrente
-- =========================================================
DO $$
DECLARE
    v_uom_id integer;
    v_x_id   uuid;
    v_w_id   uuid;
    v_y_id   uuid;
    v_z_id   uuid;
BEGIN
    -- Recupera una UoM attiva qualsiasi (prerequisito per INSERT articoli)
    SELECT id INTO v_uom_id
      FROM catalogo.unita_misura
     WHERE attivo = TRUE
     LIMIT 1;
    IF v_uom_id IS NULL THEN
        RAISE EXCEPTION 'Fixture: nessuna unita_misura attiva disponibile.';
    END IF;

    -- Codici con prefisso LCC_ (Lock Columns Conditional) per non collidere
    -- con seed permanenti (ART_TEST_BASE/FALLBACK usati da altri test).
    --
    -- is_composito = TRUE obbligatorio sul padre (W): guard
    -- trgfn_articoli_componenti_guard_is_composito lo richiede su prodotto_id.
    -- I figli (Y, Z) restano semplici: la distinta ha un livello solo
    -- (trgfn_articoli_componenti_guard_un_livello).
    -- fn_non_editable_fields flagga is_solo_componente su Z in base alla
    -- presenza come componente_id nelle BoM, non al valore corrente del flag.
    INSERT INTO catalogo.articoli (codice, descrizione, uom_id, attivo, is_composito)
    VALUES
        ('LCC_TEST_X', 'Test LCC standalone',         v_uom_id, TRUE, FALSE),
        ('LCC_TEST_W', 'Test LCC padre',               v_uom_id, TRUE, TRUE),
        ('LCC_TEST_Y', 'Test LCC figlio BoM futura',   v_uom_id, TRUE, FALSE),
        ('LCC_TEST_Z', 'Test LCC figlio BoM in vigore', v_uom_id, TRUE, FALSE);

    -- Recupera id articoli appena creati
    SELECT id INTO v_w_id FROM catalogo.articoli WHERE codice = 'LCC_TEST_W';
    SELECT id INTO v_y_id FROM catalogo.articoli WHERE codice = 'LCC_TEST_Y';
    SELECT id INTO v_z_id FROM catalogo.articoli WHERE codice = 'LCC_TEST_Z';

    -- BoM W → Z  (W e' padre, Z e' figlio)
    INSERT INTO catalogo.articoli_componenti
        (prodotto_id, componente_id, coeff_qta, valido_dal, attivo)
    VALUES
        (v_w_id, v_z_id, 1, script.fn_data_operativa(), TRUE);

    -- BoM W → Y  futura (parte fra dieci giorni)
    INSERT INTO catalogo.articoli_componenti
        (prodotto_id, componente_id, coeff_qta, valido_dal, attivo)
    VALUES
        (v_w_id, v_y_id, 1, script.fn_data_operativa() + 10, TRUE);
END;
$$;

-- =========================================================
-- Test 1: LCC_X (standalone) — nessuno dei 3 flag condizionali
-- =========================================================
SELECT ok(
    NOT (
        dbops.fn_non_editable_fields(
            'catalogo', 'articoli',
            (SELECT id::text FROM catalogo.articoli WHERE codice = 'LCC_TEST_X')
        ) @> ARRAY['is_composito', 'is_solo_componente', 'requires_serial']
    ),
    '1) LCC_X standalone: nessun flag di struttura bloccato'
);

-- =========================================================
-- Test 2: LCC_W (padre solo) — is_composito + requires_serial bloccati;
--          is_solo_componente assente
-- =========================================================
SELECT ok(
    (
        dbops.fn_non_editable_fields(
            'catalogo', 'articoli',
            (SELECT id::text FROM catalogo.articoli WHERE codice = 'LCC_TEST_W')
        ) @> ARRAY['is_composito', 'requires_serial']
    )
    AND NOT (
        dbops.fn_non_editable_fields(
            'catalogo', 'articoli',
            (SELECT id::text FROM catalogo.articoli WHERE codice = 'LCC_TEST_W')
        ) @> ARRAY['is_solo_componente']
    ),
    '2) LCC_W padre solo: is_composito+requires_serial bloccati; is_solo_componente no'
);

-- =========================================================
-- Test 3: LCC_Z (figlio in vigore) — is_solo_componente e is_composito
--          bloccati; requires_serial assente
-- =========================================================
SELECT ok(
    (
        dbops.fn_non_editable_fields(
            'catalogo', 'articoli',
            (SELECT id::text FROM catalogo.articoli WHERE codice = 'LCC_TEST_Z')
        ) @> ARRAY['is_solo_componente', 'is_composito']
    )
    AND NOT (
        'requires_serial' = ANY (dbops.fn_non_editable_fields(
            'catalogo', 'articoli',
            (SELECT id::text FROM catalogo.articoli WHERE codice = 'LCC_TEST_Z')))
    ),
    '3) LCC_Z figlio in vigore: is_solo_componente e is_composito bloccati; requires_serial no'
);

-- =========================================================
-- Test 4: LCC_Y (figlio di una BoM futura) — is_composito bloccato;
--          is_solo_componente e requires_serial assenti
-- =========================================================
SELECT ok(
    (
        'is_composito' = ANY (dbops.fn_non_editable_fields(
            'catalogo', 'articoli',
            (SELECT id::text FROM catalogo.articoli WHERE codice = 'LCC_TEST_Y')))
    )
    AND NOT (
        dbops.fn_non_editable_fields(
            'catalogo', 'articoli',
            (SELECT id::text FROM catalogo.articoli WHERE codice = 'LCC_TEST_Y')
        ) && ARRAY['is_solo_componente', 'requires_serial']
    ),
    '4) LCC_Y figlio di una BoM futura: is_composito bloccato; is_solo_componente e requires_serial no'
);

SELECT * FROM finish();
ROLLBACK;
