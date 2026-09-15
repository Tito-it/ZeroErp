-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: magazzino.valore_giacenza (era costo_medio) e le cinque viste sul
--   registro e sul valore, nella forma del Lotto 1
--   (brief-db-magazzino-lotto-1-terreno-vuoto, sezioni 4.6, 4.8, 7; M-4).
--
-- ⚠️ Le viste si provano sui VALORI, non con has_column (brief modifiche
--   certe, sezione 7: «un has_column sulle viste non basta»): la fixture
--   costruisce tre movimenti e una riga di valore, e si confronta cio' che le
--   viste rispondono con cio' che il registro e la copia contengono.
-- ⚠️ valore_giacenza e' sotto RLS via_magazzino: la scrittura della riga di
--   valore passa perche' l'operatore ha l'emittente del magazzino nel
--   perimetro (helper). E' la prova che la copia e' scrivibile dall'app
--   finche' la primitiva non arriva a chiuderla (Lotto 2).
--
-- Elenco test (plan 12):
--   La rinomina e' di tutto:
--    1) nessun oggetto (vincolo, indice, sequenza, trigger, trigger sui padri, relazione) nomina piu' costo_medio
--    2) la FK articolo che mancava c'e' (fk_mag_valore_giacenza_articolo)
--    3) qta non c'e' piu': la quantita' vive solo nel registro
--    4) la partizione note_costo_medio non esiste e COSTO_MEDIO non e' nel CHECK del padre
--   Le viste, sui valori:
--    5) vw_giacenza = sum(qta) del registro (+5 +4 -2 = 7)
--    6) vw_giacenza_ubicazione distingue due ubicazioni dello stesso magazzino (3 e 4)
--    7) vw_costo_medio = valore / qta con la quantita' dal registro (70 / 7 = 10)
--    8) vw_giacenza_valorizzata: qta dal registro, valore dalla copia, costo = valore / qta
--    9) vw_costo_medio_globale somma i magazzini (un solo magazzino qui: 7, 70, 10)
--   10) senza riga di valore, la giacenza si vede e valore/costo sono NULL (anomalia visibile)
--   La postura:
--   11) security_invoker VERA su tutte e cinque (pg_class.reloptions)
--   12) un articolo inesistente su valore_giacenza -> 23503 (la FK che mancava, esercitata)
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- 1..4 La forma
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM (
        SELECT conname AS n FROM pg_constraint WHERE conrelid = 'magazzino.valore_giacenza'::regclass
        UNION ALL SELECT indexname FROM pg_indexes WHERE schemaname = 'magazzino' AND tablename = 'valore_giacenza'
        UNION ALL SELECT tgname FROM pg_trigger WHERE tgrelid = 'magazzino.valore_giacenza'::regclass AND NOT tgisinternal
        UNION ALL SELECT relname FROM pg_class WHERE relkind = 'S' AND relnamespace = 'magazzino'::regnamespace
        UNION ALL SELECT tgname FROM pg_trigger WHERE NOT tgisinternal AND pg_get_triggerdef(oid) ~ '''costo_medio'''
        UNION ALL SELECT relname FROM pg_class WHERE relnamespace IN ('magazzino'::regnamespace, 'storico'::regnamespace) AND relkind IN ('r', 'p')
    ) x WHERE x.n ~ 'costo_medio'),
    0,
    '1) nessun oggetto nomina piu'' costo_medio (vincoli, indici, sequenze, trigger, padri, relazioni)');

SELECT ok(
    EXISTS (SELECT 1 FROM pg_constraint
             WHERE conrelid = 'magazzino.valore_giacenza'::regclass
               AND conname = 'fk_mag_valore_giacenza_articolo' AND contype = 'f'),
    '2) la FK verso catalogo.articoli, che mancava, c''e''');

SELECT ok(
    NOT EXISTS (SELECT 1 FROM pg_attribute
                 WHERE attrelid = 'magazzino.valore_giacenza'::regclass
                   AND attname = 'qta' AND NOT attisdropped),
    '3) qta non e'' piu'' nell''accumulatore: la quantita'' vive solo nel registro (M-4)');

SELECT ok(
    to_regclass('magazzino.note_costo_medio') IS NULL
    AND NOT EXISTS (SELECT 1 FROM pg_constraint
                     WHERE conrelid = 'magazzino.note'::regclass
                       AND conname = 'chk_note_target_tipo'
                       AND pg_get_constraintdef(oid) ~ 'COSTO_MEDIO'),
    '4) note_costo_medio non esiste e COSTO_MEDIO non e'' piu'' nel CHECK del padre (D-L1-e)');

-- ============================================================
-- Fixture: un magazzino, due ubicazioni, tre movimenti, una riga di valore
-- ============================================================
CREATE TEMP TABLE _mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo));
END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

CREATE TEMP TABLE _fix (mag bigint, art uuid, u1 bigint, u2 bigint);

DO $fix$
DECLARE
    v_ef  magazzino.magazzini.emittente_fiscale_id%TYPE;
    v_ind anagrafiche.indirizzi_dettaglio.id%TYPE;
    v_art catalogo.articoli.id%TYPE;
    v_mag magazzino.magazzini.id%TYPE;
    v_u1  magazzino.ubicazioni.id%TYPE;
    v_u2  magazzino.ubicazioni.id%TYPE;
    v_inv magazzino.inventari.id%TYPE;
    v_ir  magazzino.inventari_righe.id%TYPE;
    v_ret magazzino.rettifiche.id%TYPE;
    v_rr  magazzino.rettifiche_righe.id%TYPE;
    v_tipo_ubi config.tipi_ubicazione.id%TYPE;
    v_cau_inv  magazzino.causali.id%TYPE;
    v_cau_neg  magazzino.causali.id%TYPE;
    v_src_inv  config.sorgenti.id%TYPE;
    v_src_ret  config.sorgenti.id%TYPE;
BEGIN
    SELECT emittente_fiscale_id INTO v_ef FROM _mondo;
    -- L'indirizzo si FABBRICA (dato di macchina: zero righe su un DB da zero);
    -- articolo e tipo di ubicazione sono seed di catalogo, presenti per contratto.
    v_ind := dbops.fn_pgtap_crea_indirizzo_dettaglio('valore');
    SELECT a.id INTO v_art FROM catalogo.articoli a WHERE a.attivo ORDER BY a.id LIMIT 1;
    SELECT t.id INTO v_tipo_ubi FROM config.tipi_ubicazione t WHERE t.attivo ORDER BY t.id LIMIT 1;
    IF v_art IS NULL OR v_tipo_ubi IS NULL THEN
        RAISE EXCEPTION 'fixture: servono un articolo e un tipo di ubicazione attivi (seed di catalogo)';
    END IF;
    SELECT id INTO v_cau_inv FROM magazzino.causali WHERE codice_interno = 'INV_INIZIALE';
    SELECT id INTO v_cau_neg FROM magazzino.causali WHERE codice_interno = 'RETT_NEG';
    SELECT id INTO v_src_inv FROM config.sorgenti WHERE codice_interno = 'INVENTARIO_RIGA';
    SELECT id INTO v_src_ret FROM config.sorgenti WHERE codice_interno = 'RETTIFICA_RIGA';

    INSERT INTO magazzino.magazzini (codice, descrizione, indirizzo_dettaglio_id, emittente_fiscale_id)
    VALUES ('PGT-VG1', 'pgTAP valore', v_ind, v_ef) RETURNING id INTO v_mag;
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id) VALUES (v_mag, 'PGT-U1', v_tipo_ubi) RETURNING id INTO v_u1;
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id) VALUES (v_mag, 'PGT-U2', v_tipo_ubi) RETURNING id INTO v_u2;

    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata) VALUES (v_inv, v_art, 9) RETURNING id INTO v_ir;
    INSERT INTO magazzino.rettifiche (magazzino_id) VALUES (v_mag) RETURNING id INTO v_ret;
    INSERT INTO magazzino.rettifiche_righe (rettifica_id, articolo_id, qta_delta) VALUES (v_ret, v_art, -2) RETURNING id INTO v_rr;

    -- +5 in U1, +4 in U2 (stessa sorgente, tranche diverse), -2 da U1 (rettifica)
    INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, causale_id, qta, costo_unitario, sorgente_tipo_id, sorgente_riga, ubicazione_id) VALUES
        (v_art, v_mag, v_cau_inv,  5, 10, v_src_inv, v_ir, v_u1),
        (v_art, v_mag, v_cau_inv,  4, 10, v_src_inv, v_ir, v_u2),
        (v_art, v_mag, v_cau_neg, -2, 10, v_src_ret, v_rr, v_u1);

    -- La copia del valore: (5 + 4 - 2) * 10 = 70.
    INSERT INTO magazzino.valore_giacenza (articolo_id, magazzino_id, valore) VALUES (v_art, v_mag, 70);

    INSERT INTO _fix VALUES (v_mag, v_art, v_u1, v_u2);
END $fix$;

-- ============================================================
-- 5..10 Le viste, sui valori
-- ============================================================
SELECT is(
    (SELECT g.qta FROM magazzino.vw_giacenza g WHERE g.magazzino_id = (SELECT mag FROM _fix)),
    7::numeric,
    '5) vw_giacenza = sum(qta) del registro: 5 + 4 - 2 = 7, senza join alle causali (M-1)');

SELECT is(
    (SELECT string_agg(g.qta::text, '/' ORDER BY g.ubicazione_id)
       FROM magazzino.vw_giacenza_ubicazione g
      WHERE g.magazzino_id = (SELECT mag FROM _fix)),
    '3.000000/4.000000',
    '6) vw_giacenza_ubicazione distingue le due ubicazioni: U1 = 5 - 2 = 3, U2 = 4');

SELECT is(
    (SELECT c.costo_medio FROM magazzino.vw_costo_medio c WHERE c.magazzino_id = (SELECT mag FROM _fix)),
    (SELECT vg.valore / g.qta
       FROM magazzino.valore_giacenza vg
       JOIN magazzino.vw_giacenza g ON g.articolo_id = vg.articolo_id AND g.magazzino_id = vg.magazzino_id
      WHERE vg.magazzino_id = (SELECT mag FROM _fix)),
    '7) vw_costo_medio = valore della copia / quantita'' del REGISTRO (70 / 7 = 10)');

SELECT is(
    (SELECT v.qta::text || '|' || v.valore::text || '|' || v.costo_medio::text
       FROM magazzino.vw_giacenza_valorizzata v WHERE v.magazzino_id = (SELECT mag FROM _fix)),
    (SELECT g.qta::text || '|' || vg.valore::text || '|' || (vg.valore / g.qta)::text
       FROM magazzino.vw_giacenza g
       JOIN magazzino.valore_giacenza vg ON vg.articolo_id = g.articolo_id AND vg.magazzino_id = g.magazzino_id
      WHERE g.magazzino_id = (SELECT mag FROM _fix)),
    '8) vw_giacenza_valorizzata: qta dal registro, valore dalla copia, costo = valore / qta — due fonti, non una');

SELECT is(
    (SELECT c.qta_tot::text || '|' || c.valore_tot::text || '|' || c.costo_medio_globale::text
       FROM magazzino.vw_costo_medio_globale c WHERE c.articolo_id = (SELECT art FROM _fix)),
    (SELECT sum(g.qta)::text || '|' || sum(vg.valore)::text || '|' || (sum(vg.valore) / sum(g.qta))::text
       FROM magazzino.vw_giacenza g
       LEFT JOIN magazzino.valore_giacenza vg ON vg.articolo_id = g.articolo_id AND vg.magazzino_id = g.magazzino_id
      WHERE g.articolo_id = (SELECT art FROM _fix)),
    '9) vw_costo_medio_globale somma sui magazzini visibili dell''articolo');

DELETE FROM magazzino.valore_giacenza WHERE magazzino_id = (SELECT mag FROM _fix);
SELECT is(
    (SELECT v.qta::text || '|' || coalesce(v.valore::text, 'NULL') || '|' || coalesce(v.costo_medio::text, 'NULL')
       FROM magazzino.vw_giacenza_valorizzata v WHERE v.magazzino_id = (SELECT mag FROM _fix)),
    '7.000000|NULL|NULL',
    '10) senza la riga di valore la giacenza si vede e valore/costo sono NULL: l''anomalia e'' visibile, non nascosta');

-- ============================================================
-- 11..12 La postura
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_class c
      WHERE c.relnamespace = 'magazzino'::regnamespace AND c.relkind = 'v'
        AND c.relname IN ('vw_giacenza', 'vw_giacenza_ubicazione', 'vw_costo_medio',
                          'vw_costo_medio_globale', 'vw_giacenza_valorizzata')
        AND coalesce((SELECT o.option_value::boolean FROM pg_options_to_table(c.reloptions) o
                       WHERE o.option_name = 'security_invoker'), false)),
    5,
    '11) security_invoker e'' VERA su tutte e cinque le viste (pg_class.reloptions)');

SELECT throws_ok(
    $$ INSERT INTO magazzino.valore_giacenza (articolo_id, magazzino_id, valore)
       SELECT gen_random_uuid(), mag, 0 FROM _fix $$,
    '23503', NULL,
    '12) un articolo inesistente su valore_giacenza: la FK che mancava, esercitata');

SELECT * FROM finish();
ROLLBACK;
