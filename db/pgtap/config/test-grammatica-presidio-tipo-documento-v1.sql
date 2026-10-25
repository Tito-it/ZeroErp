-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Una grammatica sola per i tipi di documento — lotto 4: il presidio contro la ricaduta.
--   Ogni colonna che porta un tipo di documento e' legata da una FK al catalogo
--   (config.sorgenti, o config.tipi_entita per cio' che si puo' indicare: G-7), e' lunga come
--   il codice (G-3) e non ha un CHECK con l'elenco dei codici scritto a mano: un tipo nuovo e'
--   una riga del CSV, non un vincolo da riscrivere.
--   Brief: brief-db-grammatica-unica-documenti §15 (G-4, L4-1 di Tid, 2026-10-25).
--   Primo pezzo, per le sole note: config/test-grammatica-note-target-tipo-v1 (lotto 3).
--
-- Elenco test (plan 6):
--   1) ⭐ ogni colonna della grammatica (sotto) e' ancorata al catalogo: FK diretta, o una FK
--      composta verso una colonna che lo e' (un passo); fuori, le sole eccezioni dichiarate
--   2) le eccezioni sono vive: la colonna c'e' e non e' ancorata (se lo diventa, l'eccezione si
--      toglie)
--   3) ogni colonna con la FK sul CODICE del catalogo e' lunga almeno come
--      config.sorgenti.codice_interno, o senza limite (G-3)
--   4) nessun CHECK su una colonna della grammatica elenca due o piu' codici del catalogo
--   5) la grammatica trova colonne di tutti e tre i tipi di ancoraggio: FK diretta verso le
--      sorgenti, verso le entita', per un passo (contro il verde per sottrazione del test 1)
--   6) nessuna colonna ancorata direttamente al catalogo ha un nome fuori dalla grammatica,
--      salvo quelle dichiarate (contro la grammatica che invecchia: chi nomina una colonna in
--      modo nuovo la aggiunge qui)
--
-- ⭐ La GRAMMATICA dei nomi e' la definizione del presidio: una colonna porta un tipo di
--   documento se si chiama
--     [prefisso_]sorgente[_qualcosa]_tipo_id   (sorgente_tipo_id, target_sorgente_tipo_id,
--                                               sorgente_origine_tipo_id, attende_…)
--     [prefisso_]target_tipo                    (le note e le loro FK composte)
--     entity_type, …_origine_tipo, destinazione_tipo, sorgente_codice_interno
--   Il test 6 la tiene allineata dall'altra parte: chi ancora una colonna col nome nuovo lo vede.
-- ⭐ Legge la STRUTTURA (colonne, vincoli) e il SEED dei due cataloghi (80_data): niente
--   dipende dalle righe di oggi, e su un database ricostruito da zero vale uguale.
-- ⚠️ L4-1 (Tid, 2026-10-25) = A: la FK lega il NOME del tipo, non l'accensione. Il catalogo lo
--   scrive solo chi migra, e le FK sull'id gia' impediscono di spegnere un tipo che ha
--   documenti (block_deact dell'automazione ATTIVO): il presidio non prova l'accensione.
-- ⚠️ Le tabelle si nominano con pg_namespace/pg_class, mai con regclass::text: un regclass si
--   stampa senza schema quando lo schema e' nel search_path di chi legge.
-- ------------------------------------------------------------

BEGIN;

SELECT plan(6);

-- La grammatica, una volta sola.
CREATE TEMP TABLE _grammatica(re) AS
VALUES ('^(.*_)?sorgente(_[a-z]+)?_tipo_id$|^(.*_)?target_tipo$|^entity_type$|_origine_tipo$|^destinazione_tipo$|^sorgente_codice_interno$');

-- Le eccezioni, ognuna col suo motivo. Si dichiarano qui, non si allarga la grammatica.
CREATE TEMP TABLE _eccezioni(colonna, motivo) AS
VALUES ('pratiche.reconcile_errori.sorgente_tipo_id',
        'registro append-only dei fallimenti del reconcile: «nessuna FK, log resiliente per definizione» (COMMENT della tabella, 20260706-18)');

-- Colonne ancorate al catalogo con un nome fuori dalla grammatica, e perche'.
CREATE TEMP TABLE _fuori_grammatica(colonna, motivo) AS
VALUES ('config.tipi_indirizzi_allowed.ambito',
        'l''ambito degli indirizzi ammessi e'' il codice della sorgente a cui valgono'),
       ('vendite.famiglie_documento.codice_interno',
        'la famiglia di numerazione si chiama col codice della sorgente che numera');

CREATE TEMP TABLE _catalogo AS
SELECT 'config.sorgenti'::regclass::oid AS relid
UNION ALL
SELECT 'config.tipi_entita'::regclass::oid;

-- Le colonne della grammatica: tabelle e padri partizionati, non le partizioni (ereditano).
CREATE TEMP TABLE _colonne AS
SELECT a.attrelid, a.attnum, n.nspname || '.' || c.relname || '.' || a.attname AS colonna
  FROM pg_attribute a
  JOIN pg_class c ON c.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relkind IN ('r', 'p') AND NOT c.relispartition
   AND a.attnum > 0 AND NOT a.attisdropped
   AND n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'
   AND a.attname ~ (SELECT re FROM _grammatica);

-- Le colonne con una FK a colonna sola verso il catalogo, e verso cosa.
CREATE TEMP TABLE _dirette AS
SELECT k.conrelid AS relid, k.conkey[1] AS attnum, k.confrelid, k.confkey[1] AS ref_attnum
  FROM pg_constraint k
 WHERE k.contype = 'f' AND array_length(k.conkey, 1) = 1
   AND k.confrelid IN (SELECT relid FROM _catalogo);

CREATE TEMP TABLE _ancoraggio AS
SELECT g.colonna,
       -- l'oid, non il nome: regclass::text perde lo schema nel search_path di chi legge
       (SELECT min(d.confrelid) FROM _dirette d
         WHERE d.relid = g.attrelid AND d.attnum = g.attnum) AS diretta_verso,
       EXISTS (
         SELECT 1 FROM pg_constraint k
           CROSS JOIN LATERAL unnest(k.conkey, k.confkey) AS u(mia, sua)
           JOIN _dirette d ON d.relid = k.confrelid AND d.attnum = u.sua
          WHERE k.contype = 'f' AND k.conrelid = g.attrelid AND u.mia = g.attnum) AS per_un_passo
  FROM _colonne g;

-- 1) l'ancoraggio
SELECT is_empty(
    $$SELECT a.colonna FROM _ancoraggio a
       WHERE a.diretta_verso IS NULL AND NOT a.per_un_passo
         AND a.colonna NOT IN (SELECT colonna FROM _eccezioni)
       ORDER BY 1$$,
    '1) ogni colonna che porta un tipo di documento ha la FK verso il catalogo (diretta o per un passo), salvo le eccezioni dichiarate');

-- 2) le eccezioni sono vive
SELECT is_empty(
    $$SELECT e.colonna FROM _eccezioni e
       WHERE NOT EXISTS (SELECT 1 FROM _ancoraggio a
                          WHERE a.colonna = e.colonna
                            AND a.diretta_verso IS NULL AND NOT a.per_un_passo)
       ORDER BY 1$$,
    '2) ogni eccezione dichiarata nomina una colonna che esiste e non e'' ancorata');

-- 3) la lunghezza del codice (G-3), su tutte le FK al codice, anche fuori grammatica
SELECT is_empty(
    $$SELECT n.nspname || '.' || c.relname || '.' || a.attname || ' ' || format_type(a.atttypid, a.atttypmod)
        FROM _dirette d
        JOIN pg_attribute r ON r.attrelid = d.confrelid AND r.attnum = d.ref_attnum
        JOIN pg_attribute a ON a.attrelid = d.relid AND a.attnum = d.attnum
        JOIN pg_class c ON c.oid = d.relid
        JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE r.attname <> 'id'
         AND NOT c.relispartition
         AND a.atttypmod <> -1
         AND a.atttypmod < (SELECT s.atttypmod FROM pg_attribute s
                             WHERE s.attrelid = 'config.sorgenti'::regclass
                               AND s.attname = 'codice_interno')
       ORDER BY 1$$,
    '3) ogni colonna con la FK sul codice del catalogo e'' lunga almeno come config.sorgenti.codice_interno (G-3)');

-- 4) nessun elenco a mano
SELECT is_empty(
    $$WITH codici AS (
          SELECT s.codice_interno::text AS codice FROM config.sorgenti s
          UNION
          SELECT e.codice FROM config.tipi_entita e)
      SELECT n.nspname || '.' || c.relname || ' ' || k.conname
        FROM pg_constraint k
        JOIN pg_class c ON c.oid = k.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE k.contype = 'c'
         AND EXISTS (SELECT 1 FROM _colonne g
                      WHERE g.attrelid = k.conrelid AND g.attnum = ANY (k.conkey))
         AND (SELECT count(*) FROM codici x
               WHERE pg_get_constraintdef(k.oid) LIKE '%''' || x.codice || '''%') >= 2
       ORDER BY 1$$,
    '4) nessun CHECK su una colonna che porta un tipo di documento elenca i codici a mano');

-- 5) la grammatica trova qualcosa di ogni tipo
SELECT is(
    (SELECT ARRAY[
        count(*) FILTER (WHERE diretta_verso = 'config.sorgenti'::regclass::oid) > 0,
        count(*) FILTER (WHERE diretta_verso = 'config.tipi_entita'::regclass::oid) > 0,
        count(*) FILTER (WHERE diretta_verso IS NULL AND per_un_passo) > 0]
       FROM _ancoraggio),
    ARRAY[true, true, true],
    '5) la grammatica trova colonne con la FK verso le sorgenti, verso le entita'' e per un passo');

-- 6) la grammatica non invecchia
SELECT is_empty(
    $$SELECT n.nspname || '.' || c.relname || '.' || a.attname
        FROM _dirette d
        JOIN pg_attribute a ON a.attrelid = d.relid AND a.attnum = d.attnum
        JOIN pg_class c ON c.oid = d.relid
        JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE NOT c.relispartition
         AND a.attname !~ (SELECT re FROM _grammatica)
         AND n.nspname || '.' || c.relname || '.' || a.attname
             NOT IN (SELECT colonna FROM _fuori_grammatica)
       ORDER BY 1$$,
    '6) ogni colonna ancorata al catalogo ha un nome della grammatica, o e'' dichiarata fuori');

SELECT * FROM finish();
ROLLBACK;
