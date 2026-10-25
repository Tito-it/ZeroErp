-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Una grammatica sola per i tipi di documento — lotto 3: le note.
--   Le quattro tabelle delle note (vendite, acquisti, magazzino, catalogo) nominano la cosa a
--   cui la nota e' ancorata col codice di config.tipi_entita (G-7), in una colonna lunga come
--   il codice (G-3), legata da una FK e non da un CHECK scritto a mano.
--   Brief: brief-db-grammatica-unica-documenti §14 (L3-1 … L3-6 di Tid, 2026-10-25).
--   ChangeSet: 20261025-53 … -68.
--
-- Elenco test (plan 10):
--   1) target_tipo e' varchar(50) sui quattro padri e su tutte le partizioni
--   2) ogni padre ha la FK su target_tipo verso config.tipi_entita(codice)
--   3) nessun CHECK di padri o partizioni nomina target_tipo: l'elenco a mano e' ritirato
--   4) ⭐ ogni confine di partizione e' un codice di config.tipi_entita — e le partizioni ci sono
--   5) nessun confine porta un codice ritirato (DDT, ORDINE, OFFERTA, ATTIVITAFT, ARTICOLI…)
--   6) catalogo.articoli(_componenti).note_target_tipo: varchar(50), e il CHECK ammette
--      esattamente il confine della partizione delle note a cui punta la FK composta
--   7) trgfn_note_validate_generic e' montata coi soli due argomenti che legge (L3-4)
--   8) nessuna tabella delle note ha due trigger con la stessa funzione e gli stessi argomenti
--      (il doppione ATTIVO scritto a mano, ritirato dal 20261025-53, L3-5)
--   9) dal padre, un codice ritirato non ha partizione: rifiutato dal routing (23514)
--  10) la frase di E_NOTE_RIGA_MISMATCH dice all'operatore la parola della sorgente, non il codice
--
-- ⭐ Legge la STRUTTURA (partizioni, vincoli, trigger) e il SEED di config.tipi_entita e
--   config.sorgenti (80_data): niente dipende dalle righe di oggi, e su un database
--   ricostruito da zero vale uguale. I test 9 e 10 COSTRUISCONO il loro caso.
-- ⚠️ Le tabelle si nominano con pg_namespace/pg_class, mai con regclass::text: un regclass si
--   stampa senza schema quando lo schema e' nel search_path di chi legge.
-- ⚠️ Test 4 e 6: «tutti i confini sono codici» su zero partizioni sarebbe verde per sottrazione;
--   il test pretende anche che le partizioni ci siano.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

CREATE TEMP TABLE _padri AS
SELECT c.oid AS relid, n.nspname AS schema_nome
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relname = 'note' AND c.relkind = 'p'
   AND n.nspname IN ('vendite', 'acquisti', 'magazzino', 'catalogo');

CREATE TEMP TABLE _partizioni AS
SELECT p.schema_nome, c.oid AS relid, c.relname,
       (regexp_match(pg_get_expr(c.relpartbound, c.oid), $r$IN \('([^']+)'\)$r$))[1] AS confine
  FROM _padri p
  JOIN pg_inherits i ON i.inhparent = p.relid
  JOIN pg_class c ON c.oid = i.inhrelid;

-- 1) la lunghezza del codice
SELECT is_empty(
    $$SELECT n.nspname || '.' || c.relname || ' ' || format_type(a.atttypid, a.atttypmod)
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE a.attname = 'target_tipo' AND NOT a.attisdropped
         AND a.attrelid IN (SELECT relid FROM _padri UNION ALL SELECT relid FROM _partizioni)
         AND format_type(a.atttypid, a.atttypmod) <> 'character varying(50)'
       ORDER BY 1$$,
    '1) target_tipo e'' varchar(50) sui quattro padri delle note e su tutte le partizioni (G-3)');

-- 2) la FK verso le entita'
SELECT is(
    (SELECT count(*)::int
       FROM _padri p
      WHERE EXISTS (
            SELECT 1 FROM pg_constraint k
              JOIN pg_attribute a ON a.attrelid = k.conrelid AND a.attnum = ANY (k.conkey)
             WHERE k.conrelid = p.relid AND k.contype = 'f'
               AND k.confrelid = 'config.tipi_entita'::regclass
               AND array_length(k.conkey, 1) = 1 AND a.attname = 'target_tipo')),
    4,
    '2) ognuno dei quattro padri ha la FK su target_tipo verso config.tipi_entita (G-7)');

-- 3) niente piu' elenco a mano
SELECT is_empty(
    $$SELECT n.nspname || '.' || c.relname || ' ' || k.conname
        FROM pg_constraint k
        JOIN pg_class c ON c.oid = k.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE k.contype = 'c'
         AND k.conrelid IN (SELECT relid FROM _padri UNION ALL SELECT relid FROM _partizioni)
         AND pg_get_constraintdef(k.oid) ~ 'target_tipo'
       ORDER BY 1$$,
    '3) nessun CHECK di padri o partizioni nomina target_tipo: lo dice la FK');

-- 4) ⭐ ogni confine e' un'entita', e le partizioni ci sono
SELECT ok(
    EXISTS (SELECT 1 FROM _partizioni)
    AND NOT EXISTS (SELECT 1 FROM _partizioni x
                     WHERE x.confine IS NULL
                        OR NOT EXISTS (SELECT 1 FROM config.tipi_entita te WHERE te.codice = x.confine)),
    '4) ogni confine di partizione delle note e'' un codice di config.tipi_entita (e le partizioni ci sono)');

-- 5) i codici ritirati
SELECT is_empty(
    $$SELECT schema_nome || '.' || relname || ' ' || confine FROM _partizioni
       WHERE confine IN ('DDT', 'ORDINE', 'OFFERTA', 'ATTIVITAFT', 'ARTICOLI', 'ARTICOLI_COMPONENTI')
       ORDER BY 1$$,
    '5) nessun confine porta un codice ritirato dal lotto 3');

-- 6) l'altra meta' della FK composta di catalogo
SELECT is_empty(
    $$WITH coppie(tabella, partizione) AS (
          VALUES ('articoli', 'note_articoli'), ('articoli_componenti', 'note_articoli_componenti'))
      SELECT k.tabella || ': ' || coalesce(format_type(a.atttypid, a.atttypmod), 'colonna assente')
             || ' / CHECK ' || coalesce(ck.ammesso, 'assente') || ' / confine ' || coalesce(pt.confine, 'assente')
        FROM coppie k
        LEFT JOIN pg_class c ON c.relname = k.tabella AND c.relnamespace = 'catalogo'::regnamespace
        LEFT JOIN pg_attribute a ON a.attrelid = c.oid AND a.attname = 'note_target_tipo' AND NOT a.attisdropped
        LEFT JOIN LATERAL (
             SELECT (regexp_match(pg_get_constraintdef(x.oid), $r$= '([^']+)'::text$r$))[1] AS ammesso
               FROM pg_constraint x
              WHERE x.conrelid = c.oid AND x.contype = 'c'
                AND pg_get_constraintdef(x.oid) ~ 'note_target_tipo') ck ON true
        LEFT JOIN _partizioni pt ON pt.schema_nome = 'catalogo' AND pt.relname = k.partizione
       WHERE format_type(a.atttypid, a.atttypmod) IS DISTINCT FROM 'character varying(50)'
          OR ck.ammesso IS NULL OR pt.confine IS NULL
          OR ck.ammesso IS DISTINCT FROM pt.confine$$,
    '6) note_target_tipo di articoli e componenti: varchar(50), e il CHECK ammette il confine della partizione delle note');

-- 7) il validatore coi suoi due argomenti
SELECT is_empty(
    $$SELECT n.nspname || '.' || c.relname || ' ' || t.tgname || ' nargs=' || t.tgnargs
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE NOT t.tgisinternal
         AND t.tgfoid = 'script.trgfn_note_validate_generic'::regproc
         AND t.tgnargs <> 2
       ORDER BY 1$$,
    '7) trgfn_note_validate_generic e'' montata coi soli due argomenti che legge (il dominio viene da NEW.target_tipo)');

-- 8) niente doppioni
SELECT is_empty(
    $$SELECT n.nspname || '.' || c.relname || ' ' || t.tgfoid::regproc::text || ' x' || count(*)
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE NOT t.tgisinternal
         AND t.tgrelid IN (SELECT relid FROM _padri UNION ALL SELECT relid FROM _partizioni)
       GROUP BY n.nspname, c.relname, t.tgfoid, t.tgargs
      HAVING count(*) > 1
       ORDER BY 1$$,
    '8) nessuna tabella delle note ha due trigger con la stessa funzione e gli stessi argomenti');

-- 9) il codice ritirato, dal padre
SELECT throws_ok(
    format($$INSERT INTO vendite.note (target_tipo, target_id, anchor_tipo, posizione, testo, id_stile)
             VALUES ('DDT', -1, 'DOCUMENTO', 'HEADER', 'codice ritirato', %s)$$,
           (SELECT s.id FROM config.note_stili s WHERE s.codice_interno = 'NORMALE')),
    '23514',
    NULL,
    '9) dal padre, il codice ritirato DDT non ha partizione: rifiutato dal routing');

-- 10) la frase per l'operatore
--   Una nota ancorata a una riga che non esiste: il validatore (BEFORE ROW) parla prima di FK
--   e policy. La parola e' config.sorgenti.etichetta di ORDINE_VENDITA («Ordine»), non il codice.
--   ⚠️ Sugli ordini e non sul DDT: l'etichetta del DDT e' «DDT», cioe' proprio il vecchio terzo
--   argomento del trigger, e il test sarebbe verde anche col validatore di prima (coincidenza
--   testuale, provato sul dump di dbdev il 2026-10-25). «Ordine» non e' ne' ORDINE ne' ORDINE_VENDITA.
SELECT throws_like(
    format($$INSERT INTO vendite.note_ordini (target_tipo, target_id, target_riga_id, anchor_tipo, posizione, testo, id_stile)
             VALUES ('ORDINE_VENDITA', -1, -1, 'RIGA', 'BEFORE', 'riga che non c''e''', %s)$$,
           (SELECT s.id FROM config.note_stili s WHERE s.codice_interno = 'NORMALE')),
    format('%%al documento di dominio %s indicato%%',
           (SELECT s.etichetta FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA')),
    '10) E_NOTE_RIGA_MISMATCH dice all''operatore la parola della sorgente (config.sorgenti.etichetta), non il codice');

SELECT * FROM finish();

ROLLBACK;
