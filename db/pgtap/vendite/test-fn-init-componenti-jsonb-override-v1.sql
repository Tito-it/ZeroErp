-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
                       AND ac.validita @> script.fn_data_operativa()
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
                      AND ac.validita @> script.fn_data_operativa()
               )
             LIMIT 1;

            BEGIN
                SELECT vendite.fn_preventivo_riga_componenti_init(
                    v_riga_id,
                    1::bigint,
                    script.fn_data_operativa(),
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
--    Verifica che il ramo override venga EFFETTIVAMENTE percorso
--    (chiave trovata dall'operatore ? + guard prezzo) e non che la
--    funzione, semplicemente, sollevi qualcosa.
--
-- ⚠️ IL SOGGETTO NON SI PESCA A CASO, e prima si faceva (corretto il
--    2026-08-05, dopo un rosso intermittente). Due difetti insieme:
--
--    1. MANCAVA LA CONDIZIONE CHE CONTA. La funzione ha una guardia di
--       idempotenza in testa — «se la riga ha gia' componenti, RETURN 0» —
--       e quindi su quelle righe non arriva MAI al guard del prezzo.
--       Misurato: dei 44 candidati che il test accettava, **33 uscivano
--       subito con RETURN 0** e solo 11 potevano far scattare il guard.
--       Il test aveva quindi tre probabilita' su quattro di fallire, e
--       quando era verde lo era per fortuna.
--
--    2. DUE `LIMIT 1` INDIPENDENTI, SENZA `ORDER BY`. Uno nell'EXISTS che
--       decide lo skip, uno nella SELECT che sceglie il soggetto: potevano
--       pescare righe diverse, e quale uscisse dipendeva dal piano del
--       planner. Dimostrato: cambiando `enable_hashjoin` la stessa query
--       restituiva la riga 163 oppure la 128.
--
--    Ora il soggetto si sceglie UNA VOLTA, con la condizione di
--    idempotenza inclusa e un ORDER BY che rende la scelta ripetibile, e
--    lo stesso soggetto serve sia allo skip sia all'asserzione.
-- =========================================================
CREATE TEMP TABLE _t_ovr AS
SELECT pr.id AS riga_id, ac.componente_id
  FROM vendite.preventivi_righe pr
  JOIN catalogo.articoli a  ON a.id = pr.articolo_id
  JOIN catalogo.articoli_componenti ac ON ac.prodotto_id = a.id
 WHERE a.is_composito = TRUE
   AND COALESCE(ac.obbligatorio, TRUE) = TRUE
   AND COALESCE(ac.attivo, TRUE) = TRUE
   AND ac.validita @> script.fn_data_operativa()
   -- LA condizione che mancava: la funzione esce con RETURN 0 se la riga
   -- ha gia' componenti, e non raggiunge mai il guard che si vuole provare.
   AND NOT EXISTS (
       SELECT 1 FROM vendite.preventivi_righe_componenti c
        WHERE c.riga_preventivo_id = pr.id)
   -- Preventivo in BOZZA (aggiunto il 2026-10-13): fuori bozza il lock
   -- trg_preventivi_righe_componenti_a05_doc_bozza rifiuta l'INSERT dei
   -- componenti fratelli (E_RIGA_DOC_NON_BOZZA) prima che il guard sul
   -- prezzo parli. Stato letto con lo stesso lettore del lock; 'DRAFT' e'
   -- lo stato bozza dichiarato nei suoi tgargs.
   AND (SELECT s.stato
          FROM script.fn_get_stato_testata_documento('PREVENTIVO', pr.preventivo_id) s) = 'DRAFT'
 -- Scelta ripetibile: senza, il soggetto cambia col piano di esecuzione.
 ORDER BY pr.id, ac.componente_id
 LIMIT 1;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM _t_ovr)
    THEN skip('5) nessuna riga composita SENZA componenti gia'' inizializzati: il guard non e'' raggiungibile, skip')
    ELSE throws_like(
        format(
            $$
            DO $inner$
            BEGIN
                -- Override con prezzo=0 su un componente OBBLIGATORIO di una
                -- riga non ancora inizializzata: l'operatore ? deve trovare la
                -- chiave e il guard deve bloccare.
                PERFORM vendite.fn_preventivo_riga_componenti_init(
                    %L::bigint, 1::bigint, script.fn_data_operativa(), %L::jsonb);
            END
            $inner$
            $$,
            (SELECT riga_id FROM _t_ovr),
            -- ⚠️ L'override copre TUTTA la BoM, non il solo soggetto (corretto
            --   il 2026-10-13, dopo un rosso «Contratto … modalita' C: articolo
            --   … non negoziato»). Il loop della funzione non ha ORDER BY: un
            --   componente senza override passa dal resolver, e se il resolver
            --   fallisce PRIMA di arrivare al soggetto l'errore e' quello del
            --   prezzo, non il guard. Con tutti i componenti in override il
            --   resolver non viene mai chiamato: i fratelli prendono 1 e
            --   passano, il soggetto prende 0 e fa scattare il guard,
            --   qualunque sia l'ordine.
            (SELECT jsonb_object_agg(
                        ac.componente_id::text,
                        CASE WHEN ac.componente_id = t.componente_id THEN 0 ELSE 1 END)
               FROM _t_ovr t
               JOIN vendite.preventivi_righe pr ON pr.id = t.riga_id
               JOIN catalogo.articoli_componenti ac ON ac.prodotto_id = pr.articolo_id
              WHERE COALESCE(ac.attivo, TRUE) = TRUE
                AND ac.validita @> script.fn_data_operativa())
        ),
        -- Il testo viene dai parametri VARIADIC di fn_log_and_raise_error
        -- (qui p_riga_id::text); l'hint 'prezzo override...' sta nel context
        -- JSONB, non nel messaggio. Si matcha su 'Parametro non valido', che
        -- identifica E_PARAMETRO_INVALIDO.
        '%Parametro non valido%',
        '5) fn_init override prezzo=0 su obbligatorio -> raise E_PARAMETRO_INVALIDO'
    )
END;

SELECT * FROM finish();
ROLLBACK;
