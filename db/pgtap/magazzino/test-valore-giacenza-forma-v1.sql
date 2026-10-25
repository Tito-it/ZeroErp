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
-- ⚠️ RI-COLLOCATO col Lotto 2 (brief-db-magazzino-lotto-2-motore, D-L2-b,
--   sezione 7): la porta del ledger e' chiusa — l'app non scrive movimenti ne'
--   valore_giacenza. La giacenza e la copia si costruiscono attraverso chi
--   scrive il registro, che scrive la copia da sola: e' un test di
--   comportamento. Il magazzino usa le ubicazioni (D-L2-m: ogni movimento ne
--   nomina una), l'articolo e' costruito gestito (helper).
-- ⭐ Rev 2026-09-24 (brief-db-magazzino-verbi-con-permesso, P-4): l'app non
--   esegue piu' la primitiva. La giacenza si costruisce con i VERBI
--   (fn_posta_inventario, fn_posta_rettifica) e il test RESTA come app: le sue
--   asserzioni sono sulle viste, che hanno senso lette sotto RLS. Stessi
--   movimenti di prima (+5 U1 e +4 U2 a costo 10, -2 da U1; +3 e -3 sul secondo
--   articolo), quindi stessi valori attesi. L'operatore riceve registra_magazzino.
--
-- Elenco test (plan 12):
--   La rinomina e' di tutto:
--    1) nessun oggetto (vincolo, indice, sequenza, trigger, trigger sui padri, relazione) nomina piu' costo_medio
--    2) la FK articolo che mancava c'e' (fk_mag_valore_giacenza_articolo)
--    3) qta non c'e' piu': la quantita' vive solo nel registro
--    4) la partizione note_costo_medio non esiste e COSTO_MEDIO non e' un confine di partizione del padre (rev 2026-10-25)
--   Le viste, sui valori:
--    5) vw_giacenza = sum(qta) del registro (+5 +4 -2 = 7)
--    6) vw_giacenza_ubicazione distingue due ubicazioni dello stesso magazzino (3 e 4)
--    7) vw_costo_medio = valore / qta con la quantita' dal registro (70 / 7 = 10)
--    8) vw_giacenza_valorizzata: qta dal registro, valore dalla copia, costo = valore / qta
--    9) vw_costo_medio_globale somma i magazzini (un solo magazzino qui: 7, 70, 10)
--   10) a giacenza zero (+3 -3 su un secondo articolo) valore 0 e costo NULL (C6: la media pretende qta > 0)
--   La postura:
--   11) security_invoker VERA su tutte e cinque (pg_class.reloptions)
--   12) la FK articolo di valore_giacenza esiste (pg_constraint): l'app non puo' piu' esercitarla, la copia la scrive la primitiva
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

-- Rev 2026-10-25 (grammatica unica, lotto 3, 20261025-56): il CHECK chk_note_target_tipo e'
--   ritirato, e un NOT EXISTS su un vincolo che non c'e' sarebbe verde per sottrazione. I tipi
--   ammessi sono i confini delle partizioni: COSTO_MEDIO non deve essere fra quelli, e il padre
--   deve averne (altrimenti la seconda condizione e' vuota).
SELECT ok(
    to_regclass('magazzino.note_costo_medio') IS NULL
    AND EXISTS (SELECT 1 FROM pg_inherits WHERE inhparent = 'magazzino.note'::regclass)
    AND NOT EXISTS (SELECT 1 FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid
                     WHERE i.inhparent = 'magazzino.note'::regclass
                       AND pg_get_expr(c.relpartbound, c.oid) ~ 'COSTO_MEDIO'),
    '4) note_costo_medio non esiste e COSTO_MEDIO non e'' un confine di partizione del padre (D-L1-e)');

-- ============================================================
-- Fixture: un magazzino, due ubicazioni, tre movimenti, una riga di valore
-- ============================================================
CREATE TEMP TABLE _mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo));
END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;
DO $az$ BEGIN PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _mondo), 'registra_magazzino'); END $az$;

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
BEGIN
    SELECT emittente_fiscale_id INTO v_ef FROM _mondo;
    -- L'indirizzo si FABBRICA (dato di macchina: zero righe su un DB da zero);
    -- articolo e tipo di ubicazione sono seed di catalogo, presenti per contratto.
    v_ind := dbops.fn_pgtap_crea_indirizzo_dettaglio('valore');
    -- L'articolo si COSTRUISCE gestito a magazzino (Lotto 2: la primitiva rifiuta un non gestito).
    v_art := dbops.fn_pgtap_crea_articolo('PGT-VG1-ART', true, false, false);
    SELECT t.id INTO v_tipo_ubi FROM config.tipi_ubicazione t WHERE t.attivo ORDER BY t.id LIMIT 1;
    IF v_tipo_ubi IS NULL THEN
        RAISE EXCEPTION 'fixture: serve un tipo di ubicazione attivo (seed di catalogo)';
    END IF;

    -- usa_ubicazioni: i movimenti nominano U1 e U2 (D-L2-m).
    v_mag := magazzino.fn_crea_magazzino('PGT-VG1', 'pgTAP valore', v_ind, jsonb_build_object('usa_ubicazioni', true), v_ef);
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id) VALUES (v_mag, 'PGT-U1', v_tipo_ubi) RETURNING id INTO v_u1;
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id) VALUES (v_mag, 'PGT-U2', v_tipo_ubi) RETURNING id INTO v_u2;

    -- +5 in U1 e +4 in U2 a costo 10 (un inventario, due righe), poi -2 da U1
    -- (una rettifica, alla media): ATTRAVERSO I VERBI, che passano dalla primitiva,
    -- che scrive anche la copia: 50 + 40 - 2 * 10 (media) = 70.
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, ubicazione_id, costo_unitario) VALUES (v_inv, v_art, 5, v_u1, 10) RETURNING id INTO v_ir;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, ubicazione_id, costo_unitario) VALUES (v_inv, v_art, 4, v_u2, 10);
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv;
    PERFORM magazzino.fn_posta_inventario(v_inv);
    INSERT INTO magazzino.rettifiche (magazzino_id) VALUES (v_mag) RETURNING id INTO v_ret;
    INSERT INTO magazzino.rettifiche_righe (rettifica_id, articolo_id, qta_delta, ubicazione_id) VALUES (v_ret, v_art, -2, v_u1) RETURNING id INTO v_rr;
    UPDATE magazzino.rettifiche SET stato_mag_rettifiche = 'CONFIRM' WHERE id = v_ret;
    PERFORM magazzino.fn_posta_rettifica(v_ret);

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

-- Un secondo articolo, +3 e -3: giacenza zero, valore zero, media NULL (C6).
DO $z$
DECLARE v_art2 uuid; v_inv bigint; v_ir bigint; v_ret bigint; v_rr bigint; v_mag bigint; v_u1 bigint;
BEGIN
    SELECT mag, u1 INTO v_mag, v_u1 FROM _fix;
    v_art2 := dbops.fn_pgtap_crea_articolo('PGT-VG1-ZERO', true, false, false);
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, ubicazione_id, costo_unitario) VALUES (v_inv, v_art2, 3, v_u1, 10) RETURNING id INTO v_ir;
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv;
    PERFORM magazzino.fn_posta_inventario(v_inv);
    INSERT INTO magazzino.rettifiche (magazzino_id) VALUES (v_mag) RETURNING id INTO v_ret;
    INSERT INTO magazzino.rettifiche_righe (rettifica_id, articolo_id, qta_delta, ubicazione_id) VALUES (v_ret, v_art2, -3, v_u1) RETURNING id INTO v_rr;
    UPDATE magazzino.rettifiche SET stato_mag_rettifiche = 'CONFIRM' WHERE id = v_ret;
    PERFORM magazzino.fn_posta_rettifica(v_ret);
END $z$;
SELECT is(
    (SELECT trim_scale(v.qta)::text || '|' || trim_scale(v.valore)::text || '|' || coalesce(v.costo_medio::text, 'NULL')
       FROM magazzino.vw_giacenza_valorizzata v JOIN catalogo.articoli a ON a.id = v.articolo_id
      WHERE v.magazzino_id = (SELECT mag FROM _fix) AND a.codice = 'PGT-VG1-ZERO'),
    '0|0|NULL',
    '10) a giacenza zero: valore 0 e costo medio NULL — la media pretende qta > 0 (C6)');

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

SELECT is(
    (SELECT count(*)::int FROM pg_constraint WHERE conrelid = 'magazzino.valore_giacenza'::regclass AND conname = 'fk_mag_valore_giacenza_articolo' AND contype = 'f'),
    1,
    '12) la FK articolo della copia esiste; l''app non puo'' piu'' esercitarla (SELECT soltanto: la copia la scrive la primitiva)');

SELECT * FROM finish();
ROLLBACK;
