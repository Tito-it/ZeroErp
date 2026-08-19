-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: presidio del catalogo config.messaggi_errore lato DB.
--       Ogni codice che una funzione VIVA passa a
--       script.fn_log_and_raise_error / fn_log_error_only deve esistere a
--       catalogo, altrimenti al primo guasto la riga in dbops.error_log
--       finisce sotto E_MESSAGGIO_NON_DEFINITO.
--
-- Origine: brief-db-seed-messaggi-errore-mancanti.md §9.6 (il gemello lato DB
--   del guardrail BE) e brief-db-seed-messaggi-errore-round-2.md §1.
--
-- Indice test (1..4):
--   1. Il catalogo e' popolato e E_MESSAGGIO_NON_DEFINITO esiste (preflight:
--      senza, il ripiego stesso non funziona)
--   2. ZERO codici sollevati da funzioni vive e assenti dal catalogo
--      ** e' il test che presidia il disallineamento **
--   3. Nessun codice a catalogo e' duplicato per (codice, lingua)
--   4. Nessun messaggio con segnaposto viene sollevato passando ZERO valori
--      (il ramo format() si salta e il %s esce a video LETTERALE)
--   5. Nessun punto di sollevamento passa MENO valori dei segnaposto del suo
--      messaggio (format() alza 22023 e l'errore di dominio SPARISCE)
--   6. Nessun messaggio con piu' di sei segnaposto (refuso di seed)
--
-- ⭐ I test 4 e 5 sono stati SCRITTI il 2026-08-18. Prima al loro posto c'era
--    il solo test "nessun messaggio con piu' di sei %s" — che e' oggi il 6 —
--    con in testata la descrizione della proprieta' vera ("il numero di %s va
--    calibrato sull'arita' MINIMA dei call-site"). La proprieta' era dichiarata
--    e non misurata: la soglia dei sei segnaposto e' una PROXY, e nessuna
--    proxy sul numero di segnaposto puo' dire quanti valori passa un
--    chiamante. Con quel test verde, il 2026-08-18 il catalogo aveva 2 punti
--    del primo tipo e 8 del secondo.
--    Brief: docs/it/dev/work-done/brief-db-segnaposti-messaggi-errore.md
--
-- PERCHE' LEGGE IL DATABASE E NON I FILE. Il gemello lato BE analizza l'AST
-- del codice Python; qui la fonte e' pg_proc.prosrc, cioe' la funzione VIVA.
-- Non e' un dettaglio: al primo giro questo test ha trovato
-- E_FATTURA_NON_ANNULLABILE, sollevato da un trigger definito nella cartella
-- legacy db/changelog/migrations/ — una scansione dei soli YAML di
-- migrations_v2 non l'avrebbe mai visto.
--
-- ⚠️ SE IL TEST 2 DIVENTA ROSSO, la riga di output dice quale codice e quale
-- funzione: si aggiunge il codice a
-- db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv (append,
-- id progressivo). NON si crea un changeSet nuovo: il CSV e' caricato da
-- loader runOnChange.
--
-- ⚠️ Il numero di %s del messaggio va calibrato sull'arita' MINIMA dei
-- call-site: in fn_log_and_raise_error la format() non e' protetta da
-- EXCEPTION, quindi un segnaposto di troppo trasforma l'errore di dominio in
-- un «too few arguments for format()».
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

SELECT plan(6);

-- Codici sollevati dalle funzioni vive. Il quantificatore e' limitato a 200
-- perche' PostgreSQL non ammette ripetizioni oltre 255, ed e' non-greedy per
-- fermarsi al PRIMO literal E_* dopo l'apertura della chiamata (il terzo
-- argomento, p_error_code).
CREATE TEMP VIEW _codici_sollevati AS
SELECT DISTINCT
       n.nspname || '.' || p.proname AS funzione,
       (regexp_matches(
            p.prosrc,
            'fn_log_(?:and_raise_error|error_only)\s*\(.{0,200}?''(E_[A-Z0-9_]{3,})''',
            'g'))[1] AS codice
  FROM pg_proc p
  JOIN pg_namespace n ON n.oid = p.pronamespace
  JOIN pg_language  l ON l.oid = p.prolang
 WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
   AND l.lanname = 'plpgsql';

-- ============================================================
-- LO SCANNER DELL'ARITA' (serve ai test 4 e 5)
-- ============================================================
-- La temp view qui sopra risponde a "quale codice"; i test 4 e 5 chiedono
-- "quanti valori", e per quello una regexp non basta: bisogna contare le
-- virgole di PRIMO livello dentro alla chiamata, cioe' saltare le parentesi
-- annidate (jsonb_build_object(...), format(...), concat(...)) e le stringhe.
--
-- ⚠️ PRIMA VANNO VIA I COMMENTI, e non e' un dettaglio: nei corpi ci sono
--    commenti in italiano fra un argomento e l'altro, e un apostrofo dentro a
--    un commento ("NEW.target_riga_id e' bigint") fa credere a qualunque
--    conteggio che da li' in poi sia aperta una stringa. Senza questo passo
--    trgfn_note_validate_generic risulta passare 1 valore invece di 3, cioe'
--    un FALSO POSITIVO su un punto sano.
--
-- ⚠️ `btrim(x)` con un solo argomento toglie SOLO gli spazi, non i newline.
--    Con gli argomenti scritti a capo (la forma normale qui dentro) il terzo
--    argomento resta "\n            'E_...'" e non somiglia piu' a un
--    letterale: lo scanner perdeva meta' dei punti in silenzio.
CREATE FUNCTION pg_temp.fn_senza_commenti(p_src text) RETURNS text
LANGUAGE plpgsql IMMUTABLE AS $fn$
DECLARE v_riga text; v_out text := ''; v_from int; v_p int; v_abs int; v_pre text;
BEGIN
    FOREACH v_riga IN ARRAY string_to_array(p_src, E'\n') LOOP
        v_from := 1;
        LOOP
            v_p := position('--' IN substr(v_riga, v_from));
            EXIT WHEN v_p = 0;
            v_abs := v_from + v_p - 1;
            v_pre := left(v_riga, v_abs - 1);
            -- un `--` conta come commento solo se le virgolette che lo
            -- precedono sulla riga sono in numero pari
            IF (length(v_pre) - length(replace(v_pre, '''', ''))) % 2 = 0 THEN
                v_riga := v_pre; EXIT;
            END IF;
            v_from := v_abs + 2;
        END LOOP;
        v_out := v_out || v_riga || E'\n';
    END LOOP;
    RETURN v_out;
END $fn$;

-- Spezza una lista di argomenti sulle virgole di primo livello.
CREATE FUNCTION pg_temp.fn_argomenti(p_lista text) RETURNS text[]
LANGUAGE plpgsql IMMUTABLE AS $fn$
DECLARE v_i int := 1; v_n int := length(p_lista); v_c text; v_d int := 0;
        v_q boolean := false; v_buf text := ''; v_out text[] := ARRAY[]::text[];
BEGIN
    WHILE v_i <= v_n LOOP
        v_c := substr(p_lista, v_i, 1);
        IF v_q THEN
            IF v_c = '''' THEN
                IF substr(p_lista, v_i + 1, 1) = '''' THEN
                    v_buf := v_buf || ''''''; v_i := v_i + 2; CONTINUE;
                END IF;
                v_q := false;
            END IF;
            v_buf := v_buf || v_c; v_i := v_i + 1; CONTINUE;
        END IF;
        IF v_c = '''' THEN v_q := true;
        ELSIF v_c IN ('(', '[') THEN v_d := v_d + 1;
        ELSIF v_c IN (')', ']') THEN v_d := v_d - 1;
        ELSIF v_c = ',' AND v_d = 0 THEN
            v_out := v_out || btrim(v_buf, E' \t\r\n'); v_buf := ''; v_i := v_i + 1; CONTINUE;
        END IF;
        v_buf := v_buf || v_c; v_i := v_i + 1;
    END LOOP;
    RETURN v_out || btrim(v_buf, E' \t\r\n');
END $fn$;

-- (funzione, codice, quanti valori passa). n_valori NULL = l'array e'
-- costruito a runtime: non misurabile staticamente, e i test lo escludono.
CREATE FUNCTION pg_temp.fn_punti_sollevamento()
RETURNS TABLE(funzione text, codice text, n_valori int)
LANGUAGE plpgsql AS $fn$
DECLARE
    r record; v_src text; v_n int; v_i int; v_c text; v_d int; v_q boolean;
    v_buf text; v_args text[]; v_p int; v_code text; v_tail text;
BEGIN
    FOR r IN
        SELECT n.nspname || '.' || p.proname AS fn, p.prosrc AS src
          FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
          JOIN pg_language  l ON l.oid = p.prolang
         WHERE l.lanname = 'plpgsql'
           AND n.nspname NOT IN ('pg_catalog', 'information_schema')
           AND p.prosrc LIKE '%fn_log_and_raise_error%'
    LOOP
        v_src := pg_temp.fn_senza_commenti(r.src);
        v_n := length(v_src);
        v_i := 1;
        LOOP
            v_p := position('fn_log_and_raise_error' IN substr(v_src, v_i));
            EXIT WHEN v_p = 0;
            v_i := v_i + v_p - 1 + length('fn_log_and_raise_error');
            v_p := position('(' IN substr(v_src, v_i));
            EXIT WHEN v_p = 0;
            v_i := v_i + v_p;                        -- primo carattere dopo la parentesi
            v_d := 0; v_q := false; v_buf := '';
            WHILE v_i <= v_n LOOP
                v_c := substr(v_src, v_i, 1);
                IF v_q THEN
                    IF v_c = '''' THEN
                        IF substr(v_src, v_i + 1, 1) = '''' THEN
                            v_buf := v_buf || ''''''; v_i := v_i + 2; CONTINUE;
                        END IF;
                        v_q := false;
                    END IF;
                    v_buf := v_buf || v_c; v_i := v_i + 1; CONTINUE;
                END IF;
                IF v_c = '''' THEN v_q := true;
                ELSIF v_c IN ('(', '[') THEN v_d := v_d + 1;
                ELSIF v_c = ']' THEN v_d := v_d - 1;
                ELSIF v_c = ')' THEN
                    EXIT WHEN v_d = 0;                -- chiusura della chiamata
                    v_d := v_d - 1;
                END IF;
                v_buf := v_buf || v_c; v_i := v_i + 1;
            END LOOP;
            v_args := pg_temp.fn_argomenti(v_buf);
            v_i := v_i + 1;
            CONTINUE WHEN coalesce(array_length(v_args, 1), 0) < 3;
            v_code := (regexp_match(v_args[3], '^''(E_[A-Z0-9_]{3,})''$'))[1];
            CONTINUE WHEN v_code IS NULL;             -- codice in variabile: non misurabile
            funzione := r.fn; codice := v_code;
            IF array_length(v_args, 1) <= 5 THEN
                n_valori := 0;                        -- nessun valore dopo p_tx_id
            ELSIF array_length(v_args, 1) = 6
              AND upper(btrim(v_args[6], E' \t\r\n')) LIKE 'VARIADIC%' THEN
                v_tail := btrim(substr(btrim(v_args[6], E' \t\r\n'), 9), E' \t\r\n');
                v_tail := btrim(regexp_replace(v_tail, '::\s*\w+\s*\[\s*\]\s*$', ''), E' \t\r\n');
                IF upper(v_tail) LIKE 'ARRAY[%' AND right(v_tail, 1) = ']' THEN
                    v_tail := btrim(substr(v_tail, 7, length(v_tail) - 7), E' \t\r\n');
                    n_valori := CASE WHEN v_tail = '' THEN 0
                                     ELSE array_length(pg_temp.fn_argomenti(v_tail), 1) END;
                ELSE
                    n_valori := NULL;                 -- array a runtime
                END IF;
            ELSE
                n_valori := array_length(v_args, 1) - 5;
            END IF;
            RETURN NEXT;
        END LOOP;
    END LOOP;
END $fn$;

-- Punti misurabili incrociati col catalogo, per lingua: un messaggio 'en' con
-- un numero di segnaposto diverso dall'italiano romperebbe le sole sessioni
-- inglesi, ed e' esattamente il caso che non si nota.
CREATE TEMP VIEW _arita AS
SELECT DISTINCT s.funzione, s.codice, m.lingua, s.n_valori,
       (length(m.messaggio) - length(replace(m.messaggio, '%s', ''))) / 2 AS n_segnaposto
  FROM pg_temp.fn_punti_sollevamento() s
  JOIN config.messaggi_errore m ON m.codice = s.codice
 WHERE s.n_valori IS NOT NULL;

-- ============================================================
-- 1) Preflight: catalogo popolato e ripiego disponibile
-- ============================================================
-- ⚠️ QUESTO NOME E' SCRITTO A MANO IN TRE POSTI, ed e' il motivo per cui il
--   test 1 e' rimasto rosso dopo la rinomina del 2026-08-07:
--     · il corpo di script.fn_log_error_only, che lo cerca per nome esatto;
--     · db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv
--       (e, dal 2026-08-07, anche codici_errore.csv);
--     · qui.
--   Non e' derivabile: e' una costante di ripiego, e un ripiego che si risolve
--   con una query avrebbe bisogno del ripiego. Rinominarlo vuol dire toccare
--   tutti e tre — se ne tocchi due, questo test e' il terzo che te lo dice.
SELECT ok(
    (SELECT count(*) FROM config.messaggi_errore) > 100
    AND EXISTS (
        SELECT 1 FROM config.messaggi_errore
         WHERE codice = 'E_MESSAGGIO_NON_DEFINITO' AND lingua = 'it'
    ),
    '1. Catalogo popolato e E_MESSAGGIO_NON_DEFINITO presente (il ripiego funziona)'
);

-- ============================================================
-- 2) Nessun codice sollevato resta senza voce a catalogo
-- ============================================================
SELECT is(
    (SELECT coalesce(string_agg(x.codice || ' <- ' || x.funzione, E'\n'), '')
       FROM (
            SELECT c.codice, min(c.funzione) AS funzione
              FROM _codici_sollevati c
             WHERE NOT EXISTS (
                   SELECT 1 FROM config.messaggi_errore m
                    WHERE m.codice = c.codice
             )
             GROUP BY c.codice
             ORDER BY c.codice
       ) x),
    '',
    '2. Ogni codice sollevato da una funzione viva esiste in config.messaggi_errore'
);

-- ============================================================
-- 3) Nessun duplicato (codice, lingua) — il vincolo esiste, qui si
--    verifica che sia ancora in piedi dopo i seed
-- ============================================================
SELECT is(
    (SELECT count(*) FROM (
        SELECT codice, lingua FROM config.messaggi_errore
         GROUP BY codice, lingua HAVING count(*) > 1
     ) d)::bigint,
    0::bigint,
    '3. Nessuna coppia (codice, lingua) duplicata a catalogo'
);

-- ============================================================
-- 4) Il segnaposto che nessuno riempie: esce a video LETTERALE
-- ============================================================
-- `fn_log_and_raise_error` chiama format() solo se l'array dei valori NON e'
-- vuoto (`array_length(p_valori,1) IS NOT NULL`). Con `VARIADIC ARRAY[]::text[]`
-- quel ramo si salta, il template resta com'e' ed e' il template che arriva al
-- client: l'operatore legge un `(%s)`.
-- L'errore di dominio, qui, sopravvive (resta P0001 col suo CONSTRAINT): il
-- danno e' solo il testo. E' il caso segnalato il 2026-08-18 su
-- E_ARTICOLO_NON_COMPOSITO.
SELECT is(
    (SELECT coalesce(string_agg(DISTINCT codice || ' [' || lingua || '] <- ' || funzione, E'\n'), '')
       FROM _arita
      WHERE n_valori = 0 AND n_segnaposto > 0),
    '',
    '4. Nessun messaggio con segnaposto viene sollevato passando zero valori'
);

-- ============================================================
-- 5) Meno valori dei segnaposto: l'errore di dominio SPARISCE
-- ============================================================
-- Questo e' peggio del 4, ed e' il motivo per cui i due test sono separati.
-- `format()` con meno argomenti dei segnaposto NON degrada: alza
-- «numero di argomenti non sufficiente per format()», SQLSTATE 22023.
-- L'eccezione parte da DENTRO fn_log_and_raise_error, quindi il RAISE di
-- dominio non viene mai eseguito: niente P0001, niente CONSTRAINT, niente
-- COLUMN. Il guard blocca lo stesso — ma il backend non ha piu' il codice su
-- cui decidere 409/404/403, e l'operatore legge un errore interno al posto
-- della frase che spiega cosa correggere.
-- Il contratto rotto e' quello di guardrail_codice_errore_strutturato.sql.
--
-- ⚠️ La forma piu' frequente non e' "ho dimenticato un valore": e' il
--    chiamante che passa UNA FRASE GIA' COMPOSTA (format(...)/concat(...))
--    come valore unico, mentre a catalogo il messaggio ha i suoi segnaposto.
--    Sono due messaggi scritti due volte che non si compongono — e in quella
--    forma la frase composta nel plpgsql non e' nemmeno traducibile.
SELECT is(
    (SELECT coalesce(string_agg(
                DISTINCT codice || ' [' || lingua || '] <- ' || funzione
                         || ' (passa ' || n_valori || ', ne servono ' || n_segnaposto || ')',
                E'\n'), '')
       FROM _arita
      WHERE n_valori > 0 AND n_valori < n_segnaposto),
    '',
    '5. Nessun punto di sollevamento passa meno valori dei segnaposto del messaggio'
);

-- ============================================================
-- 6) Nessun template con un numero implausibile di segnaposto:
--    oltre sei %s il messaggio non e' piu' leggibile e quasi certamente
--    e' un errore di scrittura del seed
-- ============================================================
SELECT is(
    (SELECT coalesce(string_agg(codice, ', '), '')
       FROM config.messaggi_errore
      WHERE (length(messaggio) - length(replace(messaggio, '%s', ''))) / 2 > 6),
    '',
    '6. Nessun messaggio con piu'' di sei segnaposto %s'
);

SELECT * FROM finish();
ROLLBACK;
