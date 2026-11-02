-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test — script.fn_log_and_raise_error: il canale del BERSAGLIO
--   L'errore, oltre a DIRE cosa e' successo, dice SU QUALE COSA — in una
--   casella strutturata dell'eccezione, non dentro la frase.
--   Brief: brief-db-bersaglio-errore.md §4.4, §6 L1
--
-- ⭐ LA REGOLA CHE QUESTO FILE PRESIDIA:
--     Il bersaglio e' un'OFFERTA. Se c'e' viaggia; se e' storto si perde;
--     ma l'errore di dominio parte SEMPRE, con il suo codice.
--   I test 4, 5 e 6 sono quelli che valgono: presidiano che un difetto del
--   bersaglio non diventi mai un difetto dell'errore. E' la stessa lezione del
--   ripiego sulla format() (18-08-2026): la funzione che serve a RIPORTARE un
--   errore non puo' essere quella che lo distrugge.
--
-- Indice test (1..8):
--   1. un bersaglio solo esce nella forma TIPO:id
--   2. due bersagli escono separati da virgola, nell'ordine dell'array
--   3. un id `uid` (uuid) passa: la chiave non e' sempre un numero
--   4. ⭐ oggetto nudo invece dell'array -> canale VUOTO, ma P0001 e codice ci sono
--   5. ⭐ elemento con tipo minuscolo    -> scartato, e il valido resta
--   6. ⭐ array vuoto                    -> canale vuoto, errore intatto
--   7. senza la chiave `bersaglio` il canale resta vuoto (nessuna regressione)
--   8. oltre cinque elementi il canale si ferma a cinque
--
-- ⚠️ Si legge `PG_DATATYPE_NAME` con GET STACKED DIAGNOSTICS, che e' esattamente
--   il canale che il backend leggera' come `diag.datatype_name`: il test misura
--   il contratto, non l'implementazione.
--
-- ⚠️ `throws_ok`/`throws_like` NON bastano qui e non sono usati: quelli
--   guardano il messaggio, e il punto di questo file e' cio' che viaggia
--   ACCANTO al messaggio. Serve catturare l'eccezione e leggerne i canali.
--
-- Runner: `app` (il default). Nessuna scrittura di dominio, nessun DDL
--   permanente: la funzione di appoggio vive in `pg_temp` e muore con la
--   sessione.
--   ⚠️ MA le righe di dbops.error_log RESTANO, e va detto invece di lasciarlo
--   credere: `script.fn_log_error_only` scrive via **dblink**, cioe' in una
--   transazione autonoma, e il ROLLBACK finale non le porta via. Vale per ogni
--   test che esercita un errore di dominio, non solo per questo — e' il
--   disegno del log, non un difetto di questo file.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- Il verbo, una volta sola: solleva e restituisce i due canali.
-- ⚠️ Il codice usato e' un codice VERO a catalogo (E_PARAMETRO_INVALIDO):
--   inventarne uno farebbe ricadere fn_log_error_only sul ramo
--   «messaggio non definito» e il test misurerebbe quel ramo, non questo.
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.solleva(p_ctx jsonb)
RETURNS TABLE(canale text, codice text)
LANGUAGE plpgsql AS $fn$
DECLARE
    -- ⚠️ `text` espliciti: sono i CANALI dell'eccezione, non valori di colonna.
    v_canale text;
    v_codice text;
BEGIN
    BEGIN
        PERFORM script.fn_log_and_raise_error(
            'test', 'pg_temp.solleva', 'E_PARAMETRO_INVALIDO',
            p_ctx, NULL::uuid, 'valore di prova');
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_canale = PG_DATATYPE_NAME,
                                v_codice = CONSTRAINT_NAME;
    END;
    RETURN QUERY SELECT v_canale, v_codice;
END
$fn$;

-- ============================================================
-- I CASI, tutti raccolti in una volta.
-- ⚠️ Il verbo in un'istruzione SEPARATA dalle asserzioni: e' la regola di
--    casa, e qui evita anche di annidare cinque livelli di parentesi dentro
--    un `is()` — che e' esattamente il modo in cui la prima stesura si e'
--    rotta.
-- ============================================================
CREATE TEMP TABLE tmp_bers AS
WITH casi(nome, ctx) AS (
  VALUES
    ('uno',      jsonb_build_object('bersaglio', jsonb_build_array(
                     jsonb_build_object('tipo', 'FATTURA', 'id', '835')))),
    ('due',      jsonb_build_object('bersaglio', jsonb_build_array(
                     jsonb_build_object('tipo', 'FATTURA', 'id', '835'),
                     jsonb_build_object('tipo', 'FATTURA', 'id', '820')))),
    ('uuid',     jsonb_build_object('bersaglio', jsonb_build_array(
                     jsonb_build_object('tipo', 'SOGGETTO',
                                        'id', '0f6a2c1e-2b7d-4f0a-9c31-8a5b6d4e1f22')))),
    ('nudo',     jsonb_build_object('bersaglio',
                     jsonb_build_object('tipo', 'FATTURA', 'id', '835'))),
    ('storto',   jsonb_build_object('bersaglio', jsonb_build_array(
                     jsonb_build_object('tipo', 'fattura', 'id', '835'),
                     jsonb_build_object('tipo', 'FATTURA', 'id', '820')))),
    ('vuoto',    jsonb_build_object('bersaglio', '[]'::jsonb)),
    ('assente',  jsonb_build_object('parametro', 'p_fattura_id', 'valore', '835')),
    ('sette',    jsonb_build_object('bersaglio', (
                     SELECT jsonb_agg(jsonb_build_object('tipo', 'FATTURA', 'id', i::text)
                                      ORDER BY i)
                       FROM generate_series(1, 7) AS i)))
)
SELECT c.nome, e.canale, e.codice
  FROM casi c
  CROSS JOIN LATERAL pg_temp.solleva(c.ctx) AS e;

-- ============================================================
-- 1..3 — il bersaglio viaggia
-- ============================================================
SELECT is(
    (SELECT canale FROM tmp_bers WHERE nome = 'uno'),
    'FATTURA:835',
    '1. Un bersaglio solo esce nella forma TIPO:id'
);

SELECT is(
    (SELECT canale FROM tmp_bers WHERE nome = 'due'),
    'FATTURA:835,FATTURA:820',
    '2. Due bersagli, separati da virgola e nell''ordine dell''array'
);

SELECT is(
    (SELECT canale FROM tmp_bers WHERE nome = 'uuid'),
    'SOGGETTO:0f6a2c1e-2b7d-4f0a-9c31-8a5b6d4e1f22',
    '3. Un id uid (uuid) passa: la chiave dell''entita'' non e'' sempre un numero'
);

-- ============================================================
-- 4..6 — ⭐ il bersaglio storto NON distrugge l'errore
-- ============================================================
SELECT is(
    (SELECT canale || '|' || codice FROM tmp_bers WHERE nome = 'nudo'),
    '|E_PARAMETRO_INVALIDO',
    '4. Oggetto nudo invece dell''array: canale VUOTO, ma il codice di dominio c''e'''
);

SELECT is(
    (SELECT canale FROM tmp_bers WHERE nome = 'storto'),
    'FATTURA:820',
    '5. L''elemento col tipo minuscolo e'' scartato, quello valido resta'
);

SELECT is(
    (SELECT canale || '|' || codice FROM tmp_bers WHERE nome = 'vuoto'),
    '|E_PARAMETRO_INVALIDO',
    '6. Array vuoto: canale vuoto, errore di dominio intatto'
);

-- ============================================================
-- 7 — nessuna regressione su chi non usa il bersaglio
-- ============================================================
SELECT is(
    (SELECT canale FROM tmp_bers WHERE nome = 'assente'),
    '',
    '7. Senza la chiave bersaglio il canale resta vuoto'
);

-- ============================================================
-- 8 — il tetto di cinque
-- ⚠️ Non e' un difetto e non si segnala: oltre cinque il frontend non
--   disegnerebbe piu' un gesto ma un elenco.
-- ============================================================
SELECT is(
    (SELECT canale FROM tmp_bers WHERE nome = 'sette'),
    'FATTURA:1,FATTURA:2,FATTURA:3,FATTURA:4,FATTURA:5',
    '8. Oltre cinque elementi il canale si ferma a cinque'
);

SELECT * FROM finish();

ROLLBACK;
