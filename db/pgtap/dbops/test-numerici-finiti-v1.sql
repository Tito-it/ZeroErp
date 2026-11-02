-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — test STRUTTURALE sul catalogo
--   (pg_attribute, pg_constraint) piu' una tabella TEMP: nessuna tabella
--   sotto RLS viene letta, il contesto operatore non cambierebbe nessuna
--   risposta.
-- pgTAP test per Zero ERP
--
-- Un numero che non e' un numero non si scrive: ogni colonna numeric del
--   progetto porta il CHECK «finito», che rifiuta 'NaN', 'Infinity' e
--   '-Infinity'.
--   Brief: brief-db-valore-numerico-non-finito-nei-documenti (§5.2, D-1 e
--   D-2 di Tid, 2026-10-09: CHECK espliciti con presidio, su TUTTE le
--   colonne numeric, storico escluso).
--   ChangeSet: 20261009-10 … -18 (uno per schema: acquisti, anagrafiche,
--   catalogo, config, documenti, magazzino, pagamenti, shop, vendite).
--
-- Elenco test (plan 8):
--  1) ⛔ INVARIANTE: nessuna colonna numeric senza il suo CHECK «finito»,
--        nella forma esatta, su quella sola colonna
--  2) gemello «esiste»: la lente vede le colonne numeric del progetto — il
--        test 1 non e' muto per un catalogo letto male
--  3) la lente vede ENTRAMBE le forme: numeric con scala e senza
--  4-8) il predicato stampato dal catalogo, rimontato su una tabella TEMP,
--        rifiuta NaN, Infinity, -Infinity e accetta un numero e il NULL
--
-- ⭐ PERCHE' UN INVARIANTE E NON I NOMI SANATI. Il difetto rinasce con la
--   prossima colonna numeric scritta senza CHECK: un elenco dei 170 vincoli
--   di oggi direbbe che quelli ci sono; il catalogo dice che NESSUNA colonna
--   ne e' priva, compresa quella nata domani. Chi aggiunge una colonna
--   numeric la scrive cosi':
--     ADD COLUMN x numeric(18,6)
--         CONSTRAINT chk_<tabella>_x_finito
--         CHECK (x > '-Infinity'::numeric AND x < 'Infinity'::numeric)
--
-- ⭐ PERCHE' LA FORMA ESATTA. Il test 1 confronta pg_get_constraintdef con
--   la stampa attesa, non cerca una parola: un CHECK «quasi» uguale (solo
--   <> 'NaN', o un solo lato) lascerebbe passare un valore, e una regex
--   larga lo conterebbe come buono. La stampa e' la stessa per numeric con
--   e senza scala (misurato il 2026-10-09 su PostgreSQL 18). I test 4-8
--   provano che quella stampa RIFIUTA davvero: il test 1 da solo
--   proverebbe solo che 170 vincoli si somigliano.
--
-- ⚠️ pg_attribute e non information_schema.columns: la vista standard
--   mostra solo le colonne su cui il ruolo connesso ha un privilegio, e i
--   pgTAP girano come zeroerp_app. Una tabella senza grant all'app
--   sparirebbe dalla lente e il test 1 passerebbe per sottrazione.
-- ⚠️ Fuori dalla lente: gli schemi di sistema, storico (le tabelle ombra
--   ricordano, non giudicano), le tabelle delle estensioni (pg_depend 'e') e
--   gli schemi temporanei — la TEMP dei test 4-8 non deve entrarci.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- La lente: le colonne numeric delle tabelle del progetto, col loro CHECK
-- ============================================================
CREATE TEMP TABLE _numerici ON COMMIT DROP AS
SELECT n.nspname || '.' || c.relname || '.' || a.attname AS colonna,
       a.atttypmod <> -1                                  AS con_scala,
       EXISTS (
           SELECT 1
             FROM pg_constraint k
            WHERE k.conrelid = c.oid
              AND k.contype  = 'c'
              AND k.conkey   = ARRAY[a.attnum]
              AND pg_get_constraintdef(k.oid) = format(
                    'CHECK (((%1$s > ''-Infinity''::numeric) AND (%1$s < ''Infinity''::numeric)))',
                    quote_ident(a.attname))
       )                                                  AS finito
  FROM pg_attribute a
  JOIN pg_class c     ON c.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relkind IN ('r', 'p')
   AND a.atttypid = 'numeric'::regtype
   AND a.attnum > 0 AND NOT a.attisdropped
   AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'storico')
   AND n.nspname NOT LIKE 'pg\_temp\_%'
   AND n.nspname NOT LIKE 'pg\_toast%'
   AND NOT EXISTS (SELECT 1 FROM pg_depend d
                    WHERE d.classid = 'pg_class'::regclass
                      AND d.objid   = c.oid
                      AND d.deptype = 'e');

-- ============================================================
-- 1. L'invariante, con i NOMI nel messaggio di errore
-- ============================================================
SELECT is(
    (SELECT coalesce(string_agg(colonna, ', ' ORDER BY colonna), '')
       FROM _numerici
      WHERE NOT finito),
    '',
    '1) ogni colonna numeric ha il CHECK «finito» (niente NaN, Infinity, -Infinity), nella forma esatta'
);

-- ============================================================
-- 2. La lente vede: il test 1 non passa per sottrazione
-- ============================================================
SELECT cmp_ok(
    (SELECT count(*) FROM _numerici),
    '>', 150::bigint,
    '2) la lente vede le colonne numeric del progetto (erano 170 il 2026-10-09)'
);

-- ============================================================
-- 3. Le due forme del tipo sono entrambe nella lente
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM _numerici WHERE con_scala)
    AND EXISTS (SELECT 1 FROM _numerici WHERE NOT con_scala),
    '3) la lente vede numeric con scala e senza: la forma attesa vale per entrambe'
);

-- ============================================================
-- 4-8. Il predicato del catalogo rifiuta davvero
--   Si prende la stampa di un vincolo reale e la si rimonta su una TEMP
--   con una colonna dello stesso nome, numeric SENZA scala: e' la forma che
--   ammette tutti e tre i valori, quindi l'unica su cui il CHECK lavora da
--   solo (con la scala gli infiniti li ferma gia' il tipo).
-- ============================================================
DO $$
DECLARE
    v_col text;
    v_def text;
BEGIN
    SELECT a.attname, pg_get_constraintdef(k.oid)
      INTO v_col, v_def
      FROM pg_constraint k
      JOIN pg_attribute a ON a.attrelid = k.conrelid AND a.attnum = k.conkey[1]
     WHERE k.contype = 'c'
       AND k.conname LIKE 'chk\_%\_finito'
     ORDER BY k.conname
     LIMIT 1;

    IF v_def IS NULL THEN
        RAISE EXCEPTION 'nessun CHECK chk_*_finito nel catalogo: i test 4-8 non hanno niente da provare';
    END IF;

    EXECUTE format('CREATE TEMP TABLE _prova_finito (%I numeric) ON COMMIT DROP', v_col);
    EXECUTE format('ALTER TABLE _prova_finito ADD CONSTRAINT chk_prova_finito %s', v_def);
    -- la colonna si rinomina per i test: il CHECK la segue
    EXECUTE format('ALTER TABLE _prova_finito RENAME COLUMN %I TO x', v_col);
END $$;

SELECT throws_ok(
    $$INSERT INTO _prova_finito (x) VALUES ('NaN')$$,
    '23514', NULL,
    '4) NaN e'' rifiutato'
);

SELECT throws_ok(
    $$INSERT INTO _prova_finito (x) VALUES ('Infinity')$$,
    '23514', NULL,
    '5) Infinity e'' rifiutato'
);

SELECT throws_ok(
    $$INSERT INTO _prova_finito (x) VALUES ('-Infinity')$$,
    '23514', NULL,
    '6) -Infinity e'' rifiutato'
);

SELECT lives_ok(
    $$INSERT INTO _prova_finito (x) VALUES (-1234567.123456)$$,
    '7) un numero qualunque, anche negativo, entra'
);

SELECT lives_ok(
    $$INSERT INTO _prova_finito (x) VALUES (NULL)$$,
    '8) il NULL entra: la regola giudica solo un valore presente'
);

SELECT * FROM finish();
ROLLBACK;
