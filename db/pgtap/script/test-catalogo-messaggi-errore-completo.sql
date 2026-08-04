-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: presidio del catalogo config.messaggi_errore lato DB.
--       Ogni codice che una funzione VIVA passa a
--       script.fn_log_and_raise_error / fn_log_error_only deve esistere a
--       catalogo, altrimenti al primo guasto la riga in dbops.error_log
--       finisce sotto MESSAGGIO_NON_DEFINITO.
--
-- Origine: brief-db-seed-messaggi-errore-mancanti.md §9.6 (il gemello lato DB
--   del guardrail BE) e brief-db-seed-messaggi-errore-round-2.md §1.
--
-- Indice test (1..4):
--   1. Il catalogo e' popolato e MESSAGGIO_NON_DEFINITO esiste (preflight:
--      senza, il ripiego stesso non funziona)
--   2. ZERO codici sollevati da funzioni vive e assenti dal catalogo
--      ** e' il test che presidia il disallineamento **
--   3. Nessun codice a catalogo e' duplicato per (codice, lingua)
--   4. Ogni messaggio ha almeno un segnaposto %s se e solo se serve:
--      i template con %s non devono avere piu' segnaposto di quanti
--      valori passa il call-site con meno argomenti
--      (verifica leggera: nessun messaggio con piu' di 6 %s)
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
SELECT plan(4);

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
-- 1) Preflight: catalogo popolato e ripiego disponibile
-- ============================================================
SELECT ok(
    (SELECT count(*) FROM config.messaggi_errore) > 100
    AND EXISTS (
        SELECT 1 FROM config.messaggi_errore
         WHERE codice = 'MESSAGGIO_NON_DEFINITO' AND lingua = 'it'
    ),
    '1. Catalogo popolato e MESSAGGIO_NON_DEFINITO presente (il ripiego funziona)'
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
-- 4) Nessun template con un numero implausibile di segnaposto:
--    oltre sei %s il messaggio non e' piu' leggibile e quasi certamente
--    e' un errore di scrittura del seed
-- ============================================================
SELECT is(
    (SELECT coalesce(string_agg(codice, ', '), '')
       FROM config.messaggi_errore
      WHERE (length(messaggio) - length(replace(messaggio, '%s', ''))) / 2 > 6),
    '',
    '4. Nessun messaggio con piu'' di sei segnaposto %s'
);

SELECT * FROM finish();
ROLLBACK;
