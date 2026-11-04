-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- SQL una tantum — automazione CODICE_MAIUSCOLO (decisione Tid 2026-11-04)
--
-- Porta in upper(btrim(codice)) le righe scritte PRIMA del trigger, sulle
-- tabelle dovute del perimetro (dbops.fn_codice_maiuscolo_perimetro: nel
-- perimetro e non in eccezione). Il trigger normalizza solo le scritture
-- nuove: le righe di ieri restano com'erano finche' qualcuno non le riscrive.
--
-- Quando: DOPO il migrate che porta 20261104-01…-08 (la funzione del
-- perimetro deve esistere). Solo sviluppo: non c'e' produzione (2026-11-04).
-- Chi: Tid, come zeroerp_owner (db/internal.env).
--
-- Come:
--   * la porta del lucchetto di colonna si apre per la sola transazione
--     (SET LOCAL zeroerp.allow_lock_columns_override = 'on'): audit e storico
--     restano accesi, e la modifica resta tracciata;
--   * una tabella alla volta, in un sottoblocco: se una rifiuta (un guard di
--     immutabilita' su un documento chiuso, due codici che differiscono solo
--     per le maiuscole e urtano l'indice UNIQUE) le altre vanno avanti, e il
--     rifiuto esce in un NOTICE col motivo, da sistemare a mano.
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
    r        record;
    v_righe  bigint;
    v_tot    bigint := 0;
    v_rifiuti int   := 0;
BEGIN
    FOR r IN
        SELECT d.schema_name, d.table_name
          FROM dbops.fn_codice_maiuscolo_perimetro(NULL) AS d
         WHERE d.nel_perimetro AND NOT d.in_eccezione
         ORDER BY d.schema_name, d.table_name
    LOOP
        BEGIN
            EXECUTE format(
                'UPDATE %I.%I SET codice = upper(btrim(codice)) '
                'WHERE codice IS DISTINCT FROM upper(btrim(codice))',
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
