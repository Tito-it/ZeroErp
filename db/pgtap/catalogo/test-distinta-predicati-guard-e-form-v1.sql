-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- I flag di struttura dell'articolo e la distinta: il guard
-- (catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva) e il form
-- (dbops.fn_non_editable_fields, regole di dbops.lock_columns_conditional)
-- chiamano gli STESSI tre predicati catalogo.fn_*, e quindi rispondono uguale.
-- Brief: brief-db-revisione-dbops, giro 10a (D28, N3)
--
-- Elenco test (plan 7):
--  1-3) i tre predicati esistono
--  4)   ⭐ nessuna regola del form su catalogo.articoli ricopia la distinta
--       (nessuna condition_expr legge catalogo.articoli_componenti)
--  5)   ⭐ nemmeno il guard: chiama i predicati
--  6)   ⭐ per quattro articoli costruiti e i tre flag, il form spegne la colonna
--       se e solo se il guard rifiuterebbe la modifica (l'elenco dei disaccordi
--       e' vuoto)
--  7)   controllo: le colonne spente sono cinque, quelle attese (il 6 non e'
--       verde perche' nessuno rifiuta niente)
--
-- Fixture (ROLLBACK finale):
--   DPG_X  semplice, fuori da ogni distinta
--   DPG_W  composito, padre di W->Z (in vigore) e W->Y (futura)
--   DPG_Z  semplice, componente in vigore
--   DPG_Y  semplice, componente di una distinta futura
-- Il guard si prova cambiando il flag in un blocco che si annulla sempre: un
--   rifiuto della distinta (E_BOM_MODIFICA_VIETATA, E_BOM_COMPONENTE_DIVENTA_COMPOSITO)
--   vale «rifiuta», un UPDATE che passa vale «accetta», ogni altro errore si rilancia.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

SELECT has_function('catalogo', 'fn_articolo_padre_di_distinta_in_vigore', ARRAY['uuid'],
    '1) catalogo.fn_articolo_padre_di_distinta_in_vigore(uuid) esiste');
SELECT has_function('catalogo', 'fn_articolo_componente_di_distinta_in_vigore', ARRAY['uuid'],
    '2) catalogo.fn_articolo_componente_di_distinta_in_vigore(uuid) esiste');
SELECT has_function('catalogo', 'fn_articolo_primo_padre_da_oggi', ARRAY['uuid'],
    '3) catalogo.fn_articolo_primo_padre_da_oggi(uuid) esiste');

SELECT is(
    (SELECT COALESCE(array_agg(l.column_name || ' #' || l.id ORDER BY l.id), ARRAY[]::text[])
       FROM dbops.lock_columns_conditional l
      WHERE l.schema_name = 'catalogo' AND l.table_name = 'articoli'
        AND l.condition_expr LIKE '%articoli\_componenti%'),
    ARRAY[]::text[],
    '4) nessuna regola del form su catalogo.articoli ricopia la distinta: chiamano i predicati');

SELECT ok(
    strpos(pg_get_functiondef('catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva()'::regprocedure),
           'articoli_componenti') = 0,
    '5) il guard dei flag di struttura non ricopia la distinta: chiama i predicati');

-- =========================================================
-- Fixture
-- =========================================================
DO $$
DECLARE
    v_uom_id integer;
    v_w_id   uuid;
    v_y_id   uuid;
    v_z_id   uuid;
BEGIN
    SELECT id INTO v_uom_id FROM catalogo.unita_misura WHERE attivo = TRUE LIMIT 1;
    IF v_uom_id IS NULL THEN
        RAISE EXCEPTION 'Fixture: nessuna unita_misura attiva disponibile.';
    END IF;

    INSERT INTO catalogo.articoli (codice, descrizione, uom_id, attivo, is_composito)
    VALUES ('DPG_X', 'pgTAP predicati: semplice',              v_uom_id, TRUE, FALSE),
           ('DPG_W', 'pgTAP predicati: padre',                 v_uom_id, TRUE, TRUE),
           ('DPG_Y', 'pgTAP predicati: componente futuro',     v_uom_id, TRUE, FALSE),
           ('DPG_Z', 'pgTAP predicati: componente in vigore',  v_uom_id, TRUE, FALSE);

    SELECT id INTO v_w_id FROM catalogo.articoli WHERE codice = 'DPG_W';
    SELECT id INTO v_y_id FROM catalogo.articoli WHERE codice = 'DPG_Y';
    SELECT id INTO v_z_id FROM catalogo.articoli WHERE codice = 'DPG_Z';

    INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal, attivo)
    VALUES (v_w_id, v_z_id, 1, script.fn_data_operativa(), TRUE),
           (v_w_id, v_y_id, 1, script.fn_data_operativa() + 10, TRUE);
END;
$$;

-- Il guard: true = rifiuta per la distinta, false = accetta. Lo stato non cambia mai.
CREATE FUNCTION pg_temp.guard_rifiuta(p_id uuid, p_col text)
 RETURNS boolean
 LANGUAGE plpgsql
AS $f$
BEGIN
    BEGIN
        EXECUTE format('UPDATE catalogo.articoli SET %1$I = NOT COALESCE(%1$I, false) WHERE id = $1', p_col)
          USING p_id;
        RAISE EXCEPTION 'PGTAP_UPDATE_PASSATO';
    EXCEPTION WHEN OTHERS THEN
        IF SQLERRM = 'PGTAP_UPDATE_PASSATO' THEN
            RETURN false;
        END IF;
        IF SQLERRM LIKE '%Struttura BoM immutabile%' OR SQLERRM LIKE '%diventare composito%' THEN
            RETURN true;
        END IF;
        RAISE;
    END;
END;
$f$;

CREATE TEMP TABLE _dpg ON COMMIT DROP AS
SELECT a.codice, c.col,
       c.col = ANY (dbops.fn_non_editable_fields('catalogo', 'articoli', a.id::text)) AS form_spenta,
       pg_temp.guard_rifiuta(a.id, c.col) AS guard_rifiuta
  FROM catalogo.articoli a
 CROSS JOIN unnest(ARRAY['is_composito', 'requires_serial', 'is_solo_componente']) AS c(col)
 WHERE a.codice IN ('DPG_X', 'DPG_W', 'DPG_Y', 'DPG_Z');

SELECT is(
    (SELECT COALESCE(array_agg(codice || '.' || col || ' form=' || form_spenta || ' guard=' || guard_rifiuta
                               ORDER BY codice, col), ARRAY[]::text[])
       FROM _dpg
      WHERE form_spenta IS DISTINCT FROM guard_rifiuta),
    ARRAY[]::text[],
    '6) per ogni articolo e flag, il form spegne la colonna se e solo se il guard rifiuta la modifica');

SELECT is(
    (SELECT array_agg(codice || '.' || col ORDER BY codice, col) FROM _dpg WHERE guard_rifiuta),
    ARRAY['DPG_W.is_composito', 'DPG_W.requires_serial',
          'DPG_Y.is_composito',
          'DPG_Z.is_composito', 'DPG_Z.is_solo_componente'],
    '7) i rifiuti sono quelli della distinta: padre (check 1), componente in vigore (check 2), componente in vigore o futuro (check 3)');

SELECT * FROM finish();
ROLLBACK;
