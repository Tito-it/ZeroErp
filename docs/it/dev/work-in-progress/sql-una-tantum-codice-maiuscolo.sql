-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- SQL una tantum — automazione CODICE_MAIUSCOLO (decisione Tid 2026-11-04)
--
-- Porta nella forma di script.fn_codice_normalizzato le righe scritte PRIMA
-- del trigger, o scritte quando il trigger usava la mappatura semplice
-- (upper() con la collation libc: 'STRAßE' invece di 'STRASSE'), sulle
-- tabelle dovute del perimetro (dbops.fn_codice_maiuscolo_perimetro: nel
-- perimetro e non in eccezione). Il trigger normalizza solo le scritture
-- nuove: le righe di ieri restano com'erano finche' qualcuno non le riscrive.
--
-- Rev 2026-11-04 (richiesta BE brief-be-codice-maiuscolo §6): la forma dal BB
-- (20261104-32, mappatura Unicode completa) e le collisioni elencate PRIMA.
--
-- Quando: DOPO il migrate che porta 20261104-32…-44. Idempotente: rilanciato
-- su righe gia' normalizzate non cambia niente. Solo sviluppo: non c'e'
-- produzione (2026-11-04).
-- Chi: Tid, come zeroerp_owner (db/internal.env).
--
-- Come, in due fasi nella stessa transazione:
--   1. ELENCO, senza scrivere: per ogni indice UNIQUE che contiene `codice`,
--      i gruppi di righe che dopo la normalizzazione avrebbero la stessa
--      chiave (anche gli indici parziali, col loro predicato); e le righe il
--      cui codice normalizzato supera la colonna varchar(n). ⛔ Se ce n'e'
--      anche una sola, lo script si FERMA (ROLLBACK): sono da sistemare a
--      mano, decidendo quale riga cambia codice — non lo decide uno script.
--   2. BONIFICA, solo se l'elenco e' vuoto: una tabella alla volta, in un
--      sottoblocco. La porta del lucchetto di colonna si apre per la sola
--      transazione (SET LOCAL zeroerp.allow_lock_columns_override = 'on'):
--      audit e storico restano accesi, e la modifica resta tracciata. Se una
--      tabella rifiuta (un guard di immutabilita' su un documento chiuso) le
--      altre vanno avanti, e il rifiuto esce in un NOTICE col motivo.
--   ⚠️ Gli indici UNIQUE su espressioni non si possono ricalcolare da qui:
--      escono in un NOTICE «da guardare», senza fermare lo script.
--
-- Uso:
--   set -a; . db/internal.env; set +a
--   psql -v ON_ERROR_STOP=1 -f docs/it/dev/work-in-progress/sql-una-tantum-codice-maiuscolo.sql
-- Alla fine il pgTAP db/pgtap/dbops/test-codice-maiuscolo-v1.sql, test 6, dice
-- se resta qualcosa.
-- ------------------------------------------------------------

BEGIN;

SET LOCAL zeroerp.allow_lock_columns_override = 'on';

DO $bonifica$
DECLARE
    r          record;
    ix         record;
    v_cols     text;
    v_gruppi   bigint;
    v_righe    bigint;
    v_max      integer;
    v_problemi int    := 0;
    v_tot      bigint := 0;
    v_rifiuti  int    := 0;
BEGIN
    -- ============================================================
    -- 1. ELENCO: collisioni sugli UNIQUE e codici troppo lunghi
    -- ============================================================
    FOR r IN
        SELECT d.schema_name, d.table_name,
               format('%I.%I', d.schema_name, d.table_name)::regclass AS rel
          FROM dbops.fn_codice_maiuscolo_perimetro(NULL) AS d
         WHERE d.nel_perimetro AND NOT d.in_eccezione
         ORDER BY d.schema_name, d.table_name
    LOOP
        FOR ix IN
            SELECT i.indexrelid::regclass AS indice,
                   i.indexprs IS NOT NULL AS su_espressioni,
                   pg_get_expr(i.indpred, i.indrelid) AS predicato,
                   ARRAY(SELECT a.attname::text
                           FROM unnest(i.indkey::int2[]) WITH ORDINALITY AS k(attnum, ord)
                           JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = k.attnum
                          ORDER BY k.ord) AS colonne
              FROM pg_index i
              JOIN pg_attribute ac ON ac.attrelid = i.indrelid AND ac.attname = 'codice'
             WHERE i.indrelid = r.rel
               AND i.indisunique
               AND ac.attnum = ANY (i.indkey::int2[])
        LOOP
            IF ix.su_espressioni THEN
                RAISE NOTICE 'GUARDARE %: UNIQUE con espressioni, non ricalcolabile', ix.indice;
                CONTINUE;
            END IF;

            SELECT string_agg(CASE WHEN c = 'codice'
                                   THEN 'script.fn_codice_normalizzato(codice)'
                                   ELSE quote_ident(c) END, ', ')
              INTO v_cols
              FROM unnest(ix.colonne) AS c;

            EXECUTE format(
                'SELECT count(*) FROM (SELECT 1 FROM %s WHERE codice IS NOT NULL %s '
                'GROUP BY %s HAVING count(*) > 1) g',
                r.rel,
                CASE WHEN ix.predicato IS NULL THEN '' ELSE 'AND (' || ix.predicato || ')' END,
                v_cols)
               INTO v_gruppi;

            IF v_gruppi > 0 THEN
                v_problemi := v_problemi + 1;
                RAISE NOTICE 'COLLISIONE %.% su %: % gruppi con la stessa chiave dopo la normalizzazione (%)',
                    r.schema_name, r.table_name, ix.indice, v_gruppi, v_cols;
            END IF;
        END LOOP;

        SELECT CASE WHEN a.atttypmod > 4 THEN a.atttypmod - 4 END
          INTO v_max
          FROM pg_attribute a
         WHERE a.attrelid = r.rel AND a.attname = 'codice' AND NOT a.attisdropped;

        IF v_max IS NOT NULL THEN
            EXECUTE format(
                'SELECT count(*) FROM %s WHERE char_length(script.fn_codice_normalizzato(codice)) > %s',
                r.rel, v_max)
               INTO v_righe;
            IF v_righe > 0 THEN
                v_problemi := v_problemi + 1;
                RAISE NOTICE 'TROPPO LUNGO %.%: % righe superano varchar(%) in maiuscolo',
                    r.schema_name, r.table_name, v_righe, v_max;
            END IF;
        END IF;
    END LOOP;

    IF v_problemi > 0 THEN
        RAISE EXCEPTION 'Bonifica FERMATA: % problemi elencati sopra, da sistemare a mano prima di rilanciare', v_problemi;
    END IF;
    RAISE NOTICE 'Elenco vuoto: nessuna collisione e nessun codice troppo lungo';

    -- ============================================================
    -- 2. BONIFICA
    -- ============================================================
    FOR r IN
        SELECT d.schema_name, d.table_name
          FROM dbops.fn_codice_maiuscolo_perimetro(NULL) AS d
         WHERE d.nel_perimetro AND NOT d.in_eccezione
         ORDER BY d.schema_name, d.table_name
    LOOP
        BEGIN
            EXECUTE format(
                'UPDATE %I.%I SET codice = script.fn_codice_normalizzato(codice) '
                'WHERE codice IS DISTINCT FROM script.fn_codice_normalizzato(codice)',
                r.schema_name, r.table_name);
            GET DIAGNOSTICS v_righe = ROW_COUNT;
            IF v_righe > 0 THEN
                RAISE NOTICE 'OK      %.%: % righe', r.schema_name, r.table_name, v_righe;
                v_tot := v_tot + v_righe;
            END IF;
        EXCEPTION WHEN others THEN
            v_rifiuti := v_rifiuti + 1;
            RAISE NOTICE 'RIFIUTO %.%: [%] %', r.schema_name, r.table_name, SQLSTATE, SQLERRM;
        END;
    END LOOP;

    RAISE NOTICE 'Totale: % righe normalizzate, % tabelle rifiutate', v_tot, v_rifiuti;
END
$bonifica$;

COMMIT;
