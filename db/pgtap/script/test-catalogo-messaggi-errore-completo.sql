-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
-- Indice test (1..7):
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
--   7. ⭐ I `valori` che una fn_check_* emette con un motivo sono ESATTAMENTE
--      i segnaposto del messaggio di quel codice
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
-- ⭐ E DAL 2026-09-08 I TEST 4 E 5 NON HANNO PIU' IL LORO RAMO CIECO.
--    Lo scanner si fermava su una riga sola — `CONTINUE WHEN v_code IS NULL`,
--    «codice in variabile: non misurabile» — e quella riga teneva fuori TUTTO
--    il pattern linee-guida-sql §12.5, dove la madre chiama una fn_check_* e
--    solleva `v_motivi -> 0 ->> 'codice'`. Sono i punti in cui la frase la
--    compone il CHIAMANTE con dati suoi, cioe' quelli dove sbagliare l'arita'
--    e' piu' facile: il presidio era muto proprio li'.
--    ⇒ Adesso il punto esce con `codice` NULL e i suoi `n_valori`, e il ramo B
--    di `_arita` incrocia i codici che quel punto puo' sollevare leggendoli da
--    dbops.vw_punti_primo_motivo (changeSet 20260908-34), che risale alla
--    check. ⚠️ Da qui in avanti questo file DIPENDE da quella vista.
--    Misura del 2026-09-08, prima di C-1: diciannove punti a codice non
--    letterale, tredici legati a una check, e ZERO difetti — nessuno passa meno
--    valori dei segnaposto. Il presidio nasce verde, e va saputo: prova che
--    aggancia, non che ci fosse un guasto.
--    Brief: brief-db-i-motivi-si-fermano-dentro-la-check.md (P-0)
--
-- ⭐ rev 2026-09-17 — DA ~30 s A ~1 s, STESSE RIGHE MISURATE. Tre cose, tutte
--    spiegate accanto al codice: (1) gli scanner giravano SEI volte perche'
--    `_arita` era una VIEW — ora TEMP TABLE, una passata; (2) i cicli a
--    caratteri sono diventati cicli a token (4,8 s -> 0,26 s), con due
--    invarianti che SOLLEVANO invece di contare storto; (3) lo stripper dei
--    commenti toglie anche i `/* ... */`, dove un apostrofo tronco invertiva
--    lo stato stringa/codice. Verificato: le 1.217 righe (funzione, codice,
--    n_valori) e i 67 motivi sono IDENTICI a quelli dello scanner precedente,
--    EXCEPT ALL nei due versi a zero. Il costo era struttura (pg_proc), non
--    dati: il guadagno vale uguale in CI.
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

SELECT plan(7);

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
--
-- ⚠️ rev 2026-09-17: VIA ANCHE I COMMENTI A BLOCCO `/* ... */`. Fino a oggi lo
--    stripper conosceva solo il `--`, e un apostrofo tronco dentro un blocco
--    («puo' essere una UNIQUE», dbops.trgfn_child_requires_active_parent)
--    invertiva lo stato dentro/fuori stringa da li' in poi. Lo scanner
--    vecchio non se ne accorgeva PER CASO — ripartiva da zero a ogni
--    chiamata — ma una lista di argomenti con dentro un blocco cosi'
--    l'avrebbe contata male in silenzio. Sono 24 funzioni con un `/* */`,
--    13 con una chiamata dentro (misura del 2026-09-17). Nessun `/*` sta
--    dentro una stringa; se un giorno ci stesse, l'asserzione sugli apici
--    pari in testa agli scanner lo dice.
CREATE FUNCTION pg_temp.fn_senza_commenti(p_src text) RETURNS text
LANGUAGE plpgsql IMMUTABLE AS $fn$
DECLARE v_riga text; v_out text := ''; v_from int; v_p int; v_abs int; v_pre text;
BEGIN
    FOREACH v_riga IN ARRAY string_to_array(regexp_replace(p_src, '/\*.*?\*/', '', 'g'), E'\n') LOOP
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

-- ============================================================
-- ⭐ rev 2026-09-17 — GLI SCANNER CAMMINANO SUI TOKEN, NON SUI CARATTERI.
--   Fino a oggi tre cicli PL/pgSQL leggevano il sorgente un carattere alla
--   volta (`substr(src, i, 1)`, poi IF sullo stato stringa/parentesi): non e'
--   `substr` a costare — misurato, e' costante anche a fondo corpo — ma il
--   NUMERO di istruzioni interpretate: 1.217 punti × qualche centinaio di
--   caratteri × una decina di istruzioni l'uno, ~4,8 s per una passata su
--   2,1 MB di sorgente. E il costo e' la STRUTTURA (pg_proc), non i dati:
--   identico in CI.
--   Ora `fn_token` spezza il testo UNA volta con una regexp in token —
--   una stringa SQL intera (apici raddoppiati compresi), una parentesi,
--   una virgola, un blocco di tutto il resto — e i cicli camminano sui
--   token: ~8 volte meno iterazioni, e lo stato «dentro una stringa»
--   sparisce, perche' la stringa e' un token solo. Misurato: 4,9 s -> 0,25 s,
--   con le STESSE 1.217 righe (funzione, codice, n_valori) del vecchio
--   scanner, EXCEPT ALL nei due versi a zero, una volta corretto lo stripper
--   dei commenti a blocco (vedi sopra).
--
-- ⛔ L'INVARIANTE CHE RENDE LECITA LA SCORCIATOIA: ogni carattere del testo
--   sta in ESATTAMENTE un token (le quattro alternative della regexp coprono
--   qualunque carattere, e l'apice orfano e' l'ultima). Ogni consumatore lo
--   verifica — `concat(token) = testo` — e se non regge SOLLEVA: un testo che
--   il tokenizzatore non sa leggere non si misura a meta'.
-- ⛔ E LA SECONDA: dopo la pulizia dei commenti gli apici sono PARI. Con un
--   numero dispari le stringhe e il codice si scambiano di posto e ogni
--   conteggio che segue e' falso; lo scanner lo dice invece di contare.
-- ============================================================
CREATE FUNCTION pg_temp.fn_token(p_testo text) RETURNS text[]
LANGUAGE sql IMMUTABLE AS $fn$
  SELECT coalesce(array_agg(t.m[1] ORDER BY t.ord), ARRAY[]::text[])
    FROM regexp_matches(p_testo,
           '(''(?:[^'']|'''')*''|[()\[\],]|[^''()\[\],]+|'')', 'g')
         WITH ORDINALITY AS t(m, ord)
$fn$;

-- Il sorgente di una funzione, pulito e tokenizzato, con i due invarianti
-- verificati. E' l'unico punto da cui gli scanner leggono un corpo.
CREATE FUNCTION pg_temp.fn_token_corpo(p_fn text, p_src text) RETURNS text[]
LANGUAGE plpgsql IMMUTABLE AS $fn$
DECLARE v_src text := pg_temp.fn_senza_commenti(p_src); v_tok text[];
BEGIN
    IF (length(v_src) - length(replace(v_src, '''', ''))) % 2 = 1 THEN
        RAISE EXCEPTION 'scanner: apici DISPARI in % dopo la pulizia dei commenti — '
                        'lo stripper non conosce una forma di commento o di stringa '
                        'di questo corpo, e da qui in poi conterebbe il falso', p_fn;
    END IF;
    v_tok := pg_temp.fn_token(v_src);
    IF array_to_string(v_tok, '') IS DISTINCT FROM v_src THEN
        RAISE EXCEPTION 'scanner: fn_token ha perso caratteri in %', p_fn;
    END IF;
    RETURN v_tok;
END $fn$;

-- Spezza una lista di argomenti sulle virgole di primo livello.
CREATE FUNCTION pg_temp.fn_argomenti(p_lista text) RETURNS text[]
LANGUAGE plpgsql IMMUTABLE AS $fn$
DECLARE v_t text; v_d int := 0; v_buf text := ''; v_out text[] := ARRAY[]::text[];
        v_tok text[] := pg_temp.fn_token(p_lista);
BEGIN
    IF array_to_string(v_tok, '') IS DISTINCT FROM p_lista THEN
        RAISE EXCEPTION 'scanner: fn_token ha perso caratteri in «%»', left(p_lista, 200);
    END IF;
    FOREACH v_t IN ARRAY v_tok LOOP
        IF v_t IN ('(', '[') THEN v_d := v_d + 1;
        ELSIF v_t IN (')', ']') THEN v_d := v_d - 1;
        ELSIF v_t = ',' AND v_d = 0 THEN
            v_out := v_out || btrim(v_buf, E' \t\r\n'); v_buf := ''; CONTINUE;
        END IF;
        v_buf := v_buf || v_t;
    END LOOP;
    RETURN v_out || btrim(v_buf, E' \t\r\n');
END $fn$;

-- (funzione, codice, quanti valori passa). n_valori NULL = l'array e'
-- costruito a runtime: non misurabile staticamente, e i test lo escludono.
CREATE FUNCTION pg_temp.fn_punti_sollevamento()
RETURNS TABLE(funzione text, codice text, n_valori int)
LANGUAGE plpgsql AS $fn$
DECLARE
    r record; v_tok text[]; v_n int; v_i int; v_d int;
    v_buf text; v_args text[]; v_code text; v_tail text;
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
        v_tok := pg_temp.fn_token_corpo(r.fn, r.src);
        v_n := coalesce(array_length(v_tok, 1), 0);
        v_i := 1;
        WHILE v_i < v_n LOOP
            -- Una chiamata e' un token di TESTO che finisce col nome, seguito
            -- dalla parentesi aperta. Il nome dentro una stringa (una
            -- p_funzione passata a un altro logger) non e' una chiamata: lo
            -- scanner a caratteri l'avrebbe rincorsa fino alla prima `(`
            -- successiva e contato una lista di argomenti che non era sua.
            IF left(v_tok[v_i], 1) <> '''' AND v_tok[v_i] ~ 'fn_log_and_raise_error\s*$'
               AND v_tok[v_i + 1] = '(' THEN
                v_i := v_i + 2; v_d := 0; v_buf := '';
                WHILE v_i <= v_n LOOP
                    IF v_tok[v_i] IN ('(', '[') THEN v_d := v_d + 1;
                    ELSIF v_tok[v_i] = ']' THEN v_d := v_d - 1;
                    ELSIF v_tok[v_i] = ')' THEN
                        EXIT WHEN v_d = 0;            -- chiusura della chiamata
                        v_d := v_d - 1;
                    END IF;
                    v_buf := v_buf || v_tok[v_i]; v_i := v_i + 1;
                END LOOP;
                v_args := pg_temp.fn_argomenti(v_buf);
                v_i := v_i + 1;
            ELSE
                v_i := v_i + 1;
                CONTINUE;
            END IF;
            CONTINUE WHEN coalesce(array_length(v_args, 1), 0) < 3;
            v_code := (regexp_match(v_args[3], '^''(E_[A-Z0-9_]{3,})''$'))[1];
            -- ⭐ P-0, 2026-09-08 — QUI C'ERA UN `CONTINUE WHEN v_code IS NULL`,
            --   commentato «codice in variabile: non misurabile». Era una riga
            --   sola e teneva fuori dallo scanner TUTTI i punti del pattern
            --   §12.5 («la madre CHIAMA la check»), che sollevano
            --   `v_motivi -> 0 ->> 'codice'`: al 2026-09-08 diciannove punti, di
            --   cui tredici legati a una fn_check_*.
            --   ⇒ Adesso il punto esce con `codice` NULL e i suoi `n_valori`
            --   misurati: i codici che PUO' sollevare li dice
            --   dbops.vw_punti_primo_motivo, e li incrocia il ramo B di _arita.
            --   ⚠️ Non tutti i punti a codice non letterale sono di quella
            --   famiglia (trgfn_lock_columns, fn_get_next_progressivo,
            --   fn_resolve_prezzo_listino_v2 tengono il codice in una variabile
            --   per altre ragioni): quelli restano fuori dal giudizio, e non si
            --   fingono misurati.
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
-- ============================================================
-- ⭐ LO SCANNER DEI MOTIVI (serve al ramo C, dal 2026-09-09)
-- ============================================================
-- ⛔ PERCHE' SERVE, ed e' un buco che si sarebbe aperto DA SOLO. Con C-1/C-2 i
--   `valori` passano DENTRO la fn_check_*, e il sito smette di chiamare
--   fn_log_and_raise_error: quei punti escono dallo scanner dei rami A e B, e
--   con loro uscirebbe l'unico presidio sulla loro arita'. Una bonifica che
--   riduce la copertura di un cancello e' «verde per sottrazione» — la stessa
--   classe di difetto per cui questo cantiere esiste.
-- ⇒ Si misura dove l'arita' e' andata a vivere: `'valori', jsonb_build_array(…)`
--   accanto al `'codice'` del motivo, dentro la check.
-- ⚠️ Un motivo SENZA `valori` non e' un difetto: e' una check che non li emette
--   ancora (il debito del rubinetto). Esce con n_valori NULL e i test lo
--   ignorano, invece di contarlo come zero.
CREATE FUNCTION pg_temp.fn_motivi_con_valori()
RETURNS TABLE(funzione text, codice text, n_valori int)
LANGUAGE plpgsql AS $fn$
DECLARE
    r record; v_tok text[]; v_n int; v_i int; v_j int; v_k int;
    v_d int; v_buf text; v_code text; v_next int;
BEGIN
    FOR r IN
        SELECT n.nspname || '.' || p.proname AS fn, p.prosrc AS src
          FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
          JOIN pg_language  l ON l.oid = p.prolang
         WHERE l.lanname = 'plpgsql'
           AND n.nspname NOT IN ('pg_catalog', 'information_schema')
           AND p.prosrc LIKE '%''codice''%'
    LOOP
        v_tok := pg_temp.fn_token_corpo(r.fn, r.src);
        v_n := coalesce(array_length(v_tok, 1), 0);
        v_i := 1;
        WHILE v_i <= v_n LOOP
            -- il prossimo motivo: il token "'codice'" seguito — spazi a parte,
            -- che sono token di testo — da una virgola e da un letterale E_...
            IF v_tok[v_i] <> '''codice''' THEN v_i := v_i + 1; CONTINUE; END IF;
            v_j := v_i + 1;
            WHILE v_j <= v_n AND v_tok[v_j] ~ '^\s+$' LOOP v_j := v_j + 1; END LOOP;
            IF v_j > v_n OR v_tok[v_j] <> ',' THEN v_i := v_i + 1; CONTINUE; END IF;
            v_j := v_j + 1;
            WHILE v_j <= v_n AND v_tok[v_j] ~ '^\s+$' LOOP v_j := v_j + 1; END LOOP;
            v_code := CASE WHEN v_j <= v_n
                           THEN (regexp_match(v_tok[v_j], '^''(E_[A-Z0-9_]{3,})''$'))[1] END;
            IF v_code IS NULL THEN v_i := v_i + 1; CONTINUE; END IF;   -- non e' un motivo: e' un'altra chiave
            funzione := r.fn; codice := v_code; n_valori := NULL;
            -- il `valori` di QUESTO motivo sta prima del prossimo `'codice'`
            v_next := v_i + 1;
            WHILE v_next <= v_n AND v_tok[v_next] <> '''codice''' LOOP v_next := v_next + 1; END LOOP;
            v_k := v_i + 1;
            WHILE v_k < v_next AND v_tok[v_k] <> '''valori''' LOOP v_k := v_k + 1; END LOOP;
            IF v_k < v_next THEN
                -- `jsonb_build_array(`: un token di testo che finisce col nome,
                -- seguito dalla parentesi aperta
                WHILE v_k < v_next
                  AND NOT (left(v_tok[v_k], 1) <> '''' AND v_tok[v_k] ~ 'jsonb_build_array$'
                           AND v_tok[v_k + 1] = '(') LOOP
                    v_k := v_k + 1;
                END LOOP;
                IF v_k < v_next THEN
                    -- estrazione BILANCIATA: gli argomenti hanno parentesi
                    -- annidate (COALESCE(...), cast, jsonb_build_object(...))
                    v_k := v_k + 2; v_d := 0; v_buf := '';
                    WHILE v_k <= v_n LOOP
                        IF v_tok[v_k] IN ('(', '[') THEN v_d := v_d + 1;
                        ELSIF v_tok[v_k] = ']' THEN v_d := v_d - 1;
                        ELSIF v_tok[v_k] = ')' THEN
                            EXIT WHEN v_d = 0;
                            v_d := v_d - 1;
                        END IF;
                        v_buf := v_buf || v_tok[v_k]; v_k := v_k + 1;
                    END LOOP;
                    n_valori := CASE WHEN btrim(v_buf, E' \t\r\n') = '' THEN 0
                                     ELSE coalesce(array_length(pg_temp.fn_argomenti(v_buf), 1), 0) END;
                END IF;
            END IF;
            RETURN NEXT;
            v_i := v_i + 1;
        END LOOP;
    END LOOP;
END $fn$;

-- ============================================================
-- ⭐ GLI SCANNER GIRANO UNA VOLTA SOLA — rev 2026-09-17.
--   `_arita` era una TEMP VIEW che nominava `fn_punti_sollevamento()` due
--   volte (rami A e B) ed era letta dai test 4, 5 e 7: SEI esecuzioni di uno
--   scanner che costa ~4,8 s l'una (misura del 2026-09-17: 1.217 punti in
--   478 funzioni, 2,1 MB di sorgente), cioe' ~30 s di file — su dbdev come
--   in CI, perche' il costo e' la STRUTTURA (pg_proc), non i dati.
--   Ora i due scanner si eseguono una volta in due TEMP TABLE e `_arita` e'
--   una TABLE derivata: le asserzioni leggono lo stesso identico risultato,
--   calcolato una volta invece di sei.
-- ============================================================
CREATE TEMP TABLE _punti  AS SELECT * FROM pg_temp.fn_punti_sollevamento();
CREATE TEMP TABLE _motivi AS SELECT * FROM pg_temp.fn_motivi_con_valori();

-- ⭐ rev 2026-10-10 — ANCHE LA VISTA DEL RAMO B SI FOTOGRAFA. Letta da sola
--   dbops.vw_punti_primo_motivo costa ~150 ms (dopo 20261010-43); messa in JOIN
--   con `_punti` dentro `_arita`, il pianificatore la portava dentro un nested
--   loop e rivalutava la sua regex su pg_proc centinaia di volte: 3,2 s per 24
--   righe (misura dbdev, come app). La copia contiene la vista com'e', intera:
--   il ramo B la legge invece di riscriverne il criterio.
CREATE TEMP TABLE _vw_punti_primo_motivo AS SELECT * FROM dbops.vw_punti_primo_motivo;
ANALYZE _punti, _vw_punti_primo_motivo;

CREATE TEMP TABLE _arita AS
-- Ramo A — il codice e' un LETTERALE sulla riga della chiamata.
SELECT DISTINCT 'A'::text AS ramo, s.funzione, s.codice, m.lingua, s.n_valori,
       (length(m.messaggio) - length(replace(m.messaggio, '%s', ''))) / 2 AS n_segnaposto
  FROM _punti s
  JOIN config.messaggi_errore m ON m.codice = s.codice
 WHERE s.n_valori IS NOT NULL
UNION ALL
-- ⭐ Ramo B — il codice viene da un MOTIVO: lo scanner sa quanti valori passa
--   il punto, ma non quale codice uscira'. I codici che quel punto PUO'
--   sollevare li dice dbops.vw_punti_primo_motivo, risalendo alla fn_check_*.
--   ⚠️ PESSIMISTA di proposito: la vista da' l'UNIONE dei codici di tutte le
--   check nominate nel corpo, perche' legge il testo e non sa quale ramo sia
--   stato preso. E' il verso giusto dell'errore — un sito scritto per l'unione
--   e' sicuro su ogni ramo, e un falso positivo costa UNA riga in piu' nel
--   VARIADIC, non un rifiuto sbagliato.
--   ⛔ Senza questo ramo il test 5 e' muto proprio dove il chiamante compone la
--   frase da dati SUOI, cioe' dove sbagliare e' piu' facile.
SELECT DISTINCT 'B'::text AS ramo, s.funzione, v.codice, m.lingua, s.n_valori,
       (length(m.messaggio) - length(replace(m.messaggio, '%s', ''))) / 2 AS n_segnaposto
  FROM _punti s
  JOIN _vw_punti_primo_motivo v ON v.funzione = s.funzione
  JOIN config.messaggi_errore m ON m.codice = v.codice
 WHERE s.codice IS NULL
   AND s.n_valori IS NOT NULL
   AND v.codice IS NOT NULL
UNION ALL
-- ⭐ Ramo C — i `valori` li emette la fn_check_* accanto al proprio codice
--   (linee-guida-sql §12.5.1). E' dove l'arita' e' andata a vivere con C-1:
--   il sito non compone piu' niente, quindi i rami A e B non lo vedono.
--   ⭐ Qui il confronto e' PIU' STRETTO degli altri due, ed e' il guadagno
--   vero del cantiere: si sa esattamente QUALE codice e QUALI valori vanno
--   insieme, senza l'unione pessimista del ramo B.
SELECT DISTINCT 'C'::text AS ramo, m.funzione, m.codice, e.lingua, m.n_valori,
       (length(e.messaggio) - length(replace(e.messaggio, '%s', ''))) / 2 AS n_segnaposto
  FROM _motivi m
  JOIN config.messaggi_errore e ON e.codice = m.codice
 WHERE m.n_valori IS NOT NULL;

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

-- ============================================================
-- 7) ⭐ I `valori` DI UN MOTIVO SONO ESATTAMENTE I SEGNAPOSTO DEL SUO CODICE
-- ============================================================
-- ⭐ QUESTO CANCELLO PRIMA NON ERA POSSIBILE, ed e' il guadagno di C-1.
--   Finche' la frase la componeva il chiamante, si sapeva quanti valori
--   passava un SITO ma non quale codice sarebbe uscito: il confronto poteva
--   solo essere «almeno quanti ne servono al peggiore» (ramo B, pessimista).
--   Ora `valori` e `codice` stanno nello stesso jsonb_build_object, quindi la
--   coppia e' nota — e si puo' pretendere l'UGUAGLIANZA.
--
-- ⛔ E l'uguaglianza prende il caso che i test 4 e 5 non vedono: i valori IN
--   PIU'. `format()` li ignora in silenzio, quindi l'arita' resta «giusta» e a
--   video esce una frase SBAGLIATA — nessun `W_`, nessun rosso. Sono i due
--   difetti vivi trovati il 2026-09-09:
--     · E_LOTTO_NON_PRE_FISCALE, che riceveva il gruppo del documento al posto
--       dello stato del lotto (vendite.fn_escludi_documento_da_giro);
--     · E_SORGENTE_CON_RIGHE_EMESSE, che riceveva il numero dell'ordine al
--       posto del conteggio (vendite.trgfn_ordini_guard_transizione).
--   ⚠️ Nessuno dei due avrebbe fatto scattare il test 5: l'arita' bastava.
--
-- ⚠️ COSA QUESTO TEST NON PROVA — e va detto, altrimenti sembra piu' di quello
--   che e': prova che i valori sono TANTI quanti i segnaposto, non che siano
--   quelli GIUSTI e nell'ORDINE giusto. Quello si vede solo leggendo la frase
--   resa (`throws_like`), ed e' il precedente del 2026-09-01 su
--   E_REGISTRO_SERIE_NON_AMMESSA: due valori, due segnaposto, frase falsa.
--
-- ⚠️ I motivi che NON emettono `valori` restano fuori (n_valori NULL): sono il
--   debito del rubinetto, non un difetto. Erano 34 al 2026-09-09, contro 29
--   motivi misurati qui — il numero da guardare e' che il primo CALI.
SELECT is(
    (SELECT coalesce(string_agg(
                DISTINCT codice || ' [' || lingua || '] <- ' || funzione
                         || ' (emette ' || n_valori || ', il messaggio ne chiede '
                         || n_segnaposto || ')', E'\n'), '')
       FROM _arita
      -- ⚠️ Si filtra sul RAMO, non sul nome della funzione: una fn_check_*
      --   contiene anche punti a codice LETTERALE (il guard di parametro in
      --   testa), che finiscono nel ramo A e non hanno niente a che vedere con
      --   i `valori` di un motivo. Filtrare per nome li tirava dentro, ed e'
      --   costato un rosso a vuoto la prima volta.
      WHERE ramo = 'C' AND n_valori <> n_segnaposto),
    '',
    '7. i valori emessi da un motivo sono esattamente i segnaposto del suo messaggio'
);

SELECT * FROM finish();
ROLLBACK;
