-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Regressione: operatore JSONB ? nelle 4 fn_*_riga_componenti_init
-- Bug: ?? (doppio) non riconosciuto da PG anche dentro $function$;
--      fix con ? singolo in migration 20260513-25..28.
--
-- Indice test:
--   1) jsonb ? text: chiave presente -> TRUE  (regression sempre eseguita)
--   2) jsonb ? text: chiave assente  -> FALSE (regression sempre eseguita)
--   3) jsonb ? in blocco PL/pgSQL: lives_ok (replica contesto fn_init)
--   4) fn_preventivo_riga_componenti_init con override non-match:
--      nessun crash su operatore ? — data-dependent, skip se no composito
--   5) fn_preventivo_riga_componenti_init: override prezzo=0 su componente
--      obbligatorio -> raise E_PARAMETRO_INVALIDO — data-dependent
-- ------------------------------------------------------------

BEGIN;
SELECT plan(5);

-- =========================================================
-- 1) Regressione: jsonb ? text ritorna TRUE se chiave presente
-- =========================================================
SELECT ok(
    ('{"comp-uuid": 99.50}'::jsonb ? 'comp-uuid'),
    '1) jsonb ? text: chiave presente -> TRUE (regression fix ?? bug)'
);

-- =========================================================
-- 2) Regressione: jsonb ? text ritorna FALSE se chiave assente
-- =========================================================
SELECT ok(
    NOT ('{"comp-uuid": 99.50}'::jsonb ? 'altro-uuid'),
    '2) jsonb ? text: chiave assente -> FALSE'
);

-- =========================================================
-- 3) Operatore ? funziona dentro blocco PL/pgSQL
--    Replica il contesto del loop FOR in fn_*_riga_componenti_init.
--    Se il bug ?? fosse presente, questo DO block solleva
--    ERROR 42883: operatore non esiste: jsonb ?? text.
-- =========================================================
SELECT lives_ok(
    $$
    DO $inner$
    DECLARE
        v_overrides jsonb := '{"some-uuid-key": 15.00}'::jsonb;
        v_chiave    text  := 'some-uuid-key';
        v_trovato   boolean;
    BEGIN
        v_trovato := (v_overrides ? v_chiave);
        IF NOT v_trovato THEN
            RAISE EXCEPTION 'jsonb ? non ha trovato la chiave attesa';
        END IF;
    END
    $inner$
    $$,
    '3) jsonb ? in blocco PL/pgSQL: nessuna eccezione (regression ?? bug)'
);

-- =========================================================
-- 4) fn_preventivo_riga_componenti_init con override non-match
--    La chiave nel JSON non corrisponde a nessun componente BoM:
--    la fn esegue il ramo resolver (non override), ma l'operatore ?
--    DEVE essere chiamato senza crash. Errori business (P0001) sono
--    attesi e catturati; errori 42883 (operatore non esiste) propagano
--    e fanno fallire il test — regressione corretta.
--    Skip se nessuna riga preventivo con articolo composito disponibile.
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
             SELECT 1 FROM vendite.preventivi_righe pr
               JOIN catalogo.articoli a ON a.id = pr.articolo_id
              WHERE a.is_composito = TRUE
                AND EXISTS (
                    SELECT 1 FROM catalogo.articoli_componenti ac
                     WHERE ac.prodotto_id = a.id
                       AND COALESCE(ac.attivo, TRUE) = TRUE
                       AND ac.validita @> CURRENT_DATE
                )
         )
    THEN skip('4) nessuna riga composita con BoM attiva: skip test operatore ?')
    ELSE lives_ok(
        $$
        DO $inner$
        DECLARE
            v_riga_id bigint;
            v_dummy   integer;
        BEGIN
            SELECT pr.id INTO v_riga_id
              FROM vendite.preventivi_righe pr
              JOIN catalogo.articoli a ON a.id = pr.articolo_id
             WHERE a.is_composito = TRUE
               AND EXISTS (
                   SELECT 1 FROM catalogo.articoli_componenti ac
                    WHERE ac.prodotto_id = a.id
                      AND COALESCE(ac.attivo, TRUE) = TRUE
                      AND ac.validita @> CURRENT_DATE
               )
             LIMIT 1;

            BEGIN
                SELECT vendite.fn_preventivo_riga_componenti_init(
                    v_riga_id,
                    1::bigint,
                    CURRENT_DATE,
                    '{"chiave-non-esistente-xxxxxxxx": 50.00}'::jsonb
                ) INTO v_dummy;
            EXCEPTION WHEN SQLSTATE 'P0001' THEN
                -- Errori business attesi (resolver fail, emittente invalido, BOM vuota)
                -- L'importante e' che NON sia SQLSTATE 42883 (operatore non esiste)
                NULL;
            END;
        END
        $inner$
        $$,
        '4) fn_init con override non-match: nessun crash su operatore ? (regression ??)'
    )
END;

-- =========================================================
-- 5) fn_preventivo_riga_componenti_init: override con prezzo=0
--    su componente obbligatorio -> raise E_PARAMETRO_INVALIDO.
--    Questo test verifica che il path override venga EFFETTIVAMENTE
--    percorso (chiave trovata + guard prezzo) e che il ? abbia
--    funzionato correttamente restituendo TRUE.
--    Skip se nessun componente obbligatorio attivo su preventivo composito.
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
             SELECT 1 FROM vendite.preventivi_righe pr
               JOIN catalogo.articoli a ON a.id = pr.articolo_id
               JOIN catalogo.articoli_componenti ac ON ac.prodotto_id = a.id
              WHERE a.is_composito = TRUE
                AND COALESCE(ac.obbligatorio, TRUE) = TRUE
                AND COALESCE(ac.attivo, TRUE) = TRUE
                AND ac.validita @> CURRENT_DATE
         )
    THEN skip('5) nessun componente obbligatorio su preventivo composito: skip')
    ELSE throws_like(
        $$
        DO $inner$
        DECLARE
            v_riga_id   bigint;
            v_comp_id   uuid;
            v_overrides jsonb;
        BEGIN
            SELECT pr.id, ac.componente_id
              INTO v_riga_id, v_comp_id
              FROM vendite.preventivi_righe pr
              JOIN catalogo.articoli a ON a.id = pr.articolo_id
              JOIN catalogo.articoli_componenti ac ON ac.prodotto_id = a.id
             WHERE a.is_composito = TRUE
               AND COALESCE(ac.obbligatorio, TRUE) = TRUE
               AND COALESCE(ac.attivo, TRUE) = TRUE
               AND ac.validita @> CURRENT_DATE
             LIMIT 1;

            IF v_riga_id IS NULL THEN RETURN; END IF;

            -- Override con prezzo=0 per componente obbligatorio:
            -- il ? deve trovare la chiave (TRUE) e il guard deve bloccare
            v_overrides := jsonb_build_object(v_comp_id::text, 0);

            PERFORM vendite.fn_preventivo_riga_componenti_init(
                v_riga_id,
                1::bigint,
                CURRENT_DATE,
                v_overrides
            );
        END
        $inner$
        $$,
        -- Il testo del messaggio proviene dai parametri VARIADIC di fn_log_and_raise_error
        -- (qui: p_riga_id::text). L'hint 'prezzo override...' è nel context JSONB, non nel
        -- messaggio. Matchiamo su 'Parametro non valido' che identifica E_PARAMETRO_INVALIDO.
        '%Parametro non valido%',
        '5) fn_init override prezzo=0 su obbligatorio -> raise E_PARAMETRO_INVALIDO'
    )
END;

SELECT * FROM finish();
ROLLBACK;
