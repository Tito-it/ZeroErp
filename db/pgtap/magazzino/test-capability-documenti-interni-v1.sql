-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: LA CAPABILITY dei documenti interni di magazzino (R-1 del Lotto 2-bis)
--   — script.fn_available_actions_inventario / _rettifica, la matrice
--   condivisa magazzino.fn_documento_interno_transizioni e la check condivisa
--   script.fn_check_documento_interno_registrabile.
--   Brief: brief-db-magazzino-lotto-2-bis-be-fe, R-1.
--
-- ⭐ Il soggetto vero di questo file NON sono i pulsanti: e' che la capability
--   e il guard NON POSSONO DIVERGERE. Per questo il test 3 non confronta la
--   funzione con un elenco scritto a mano, ma con cio' che il guard AMMETTE
--   davvero, transizione per transizione, COSTRUENDO tutti e dodici i casi:
--   se un giorno
--   qualcuno cambiasse la matrice in un posto solo, qui diventa rosso.
--   (linee-guida-sql §12.2 punto 1: «il predicato e' lo STESSO del guard».)
--
-- ⚠️ Fixture COSTRUITA: un magazzino a ubicazioni, un articolo gestito, uno
--   NON gestito — il mondo di oggi su dbdev non c'entra.
--
-- Elenco test (plan 14):
--   La matrice, in una sede sola:
--    1) fn_documento_interno_transizioni: DRAFT, CONFIRM, POSTED, CANCEL
--    2) uno stato che non esiste (e NULL) -> {}, non un errore
--    3) ⭐ la matrice COINCIDE col guard, su tutte e dodici le transizioni fra i
--       quattro stati: le cinque ammesse passano, le sette vietate sollevano
--       E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA
--   Le azioni:
--    4) DRAFT: conferma (CONFIRM) + annulla (CANCEL), in quest'ordine, e POSTED NON c'e'
--    5) CONFIRM: riapri (DRAFT) + annulla (CANCEL); can_change_state vero
--    6) POSTED: nessuna azione, can_change_state falso, stato_info_key posted
--    7) CANCEL: nessuna azione, stato_info_key cancel
--    8) le label_key stanno tutte sotto magazzino.documenti_interni.
--    9) l'annullamento chiede conferma, gli altri no
--   Il verbo irreversibile:
--   10) DRAFT -> can_registra falso, reason DOCUMENTO_NON_CONFERMATO
--   11) CONFIRM senza righe -> DOCUMENTO_SENZA_RIGHE; con riga buona -> can_registra vero
--   12) CONFIRM con riga non postabile -> RIGHE_NON_POSTABILI, e il CODICE e' quello della riga
--   13) POSTED -> reason DOCUMENTO_GIA_REGISTRATO (non «non confermato»: sarebbe falso)
--   14) documento inesistente -> NULL (il 404 lo da' il BE), e la rettifica si comporta uguale
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;
-- Rev 2026-09-24 (brief-db-magazzino-verbi-con-permesso §3.2): fn_posta_inventario e
--   fn_posta_rettifica sono VERBI e applicano registra_magazzino (script.fn_guard_azione);
--   l'operatore di fixture e' tecnico e non ha azioni: il permesso si costruisce qui.
DO $az$ BEGIN PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _mondo), 'registra_magazzino'); END $az$;

CREATE TEMP TABLE _fix (mag bigint, ubi bigint, art uuid, art_no uuid);
DO $fix$
DECLARE v_mag bigint; v_ubi bigint; v_art uuid; v_nog uuid; v_tipo bigint;
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-L2B-U', true);
    SELECT t.id INTO v_tipo FROM config.tipi_ubicazione t ORDER BY t.id LIMIT 1;
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id) VALUES (v_mag, 'UX', v_tipo) RETURNING id INTO v_ubi;
    v_art := dbops.fn_pgtap_crea_articolo('PGT-L2B-ART', true, false, false);
    v_nog := dbops.fn_pgtap_crea_articolo('PGT-L2B-NO', false, false, false);
    INSERT INTO _fix VALUES (v_mag, v_ubi, v_art, v_nog);
END $fix$;

-- ============================================================
-- 1-2 La matrice
-- ============================================================
SELECT is(
    (SELECT (magazzino.fn_documento_interno_transizioni('DRAFT'),
             magazzino.fn_documento_interno_transizioni('CONFIRM'),
             magazzino.fn_documento_interno_transizioni('POSTED'),
             magazzino.fn_documento_interno_transizioni('CANCEL'))::text),
    '("{CONFIRM,CANCEL}","{POSTED,CANCEL,DRAFT}",{},{})',
    '1) la matrice: DRAFT e CONFIRM hanno un seguito, POSTED e CANCEL no');

SELECT is(
    (SELECT (magazzino.fn_documento_interno_transizioni('PIPPO'),
             magazzino.fn_documento_interno_transizioni(NULL))::text),
    '({},{})',
    '2) uno stato che non esiste non e'' un errore: nessuna destinazione (il cancello sui valori e'' il CHECK)');

-- ============================================================
-- 3 ⭐ La matrice COINCIDE con cio' che il guard ammette
--   Si costruiscono tutte e dodici le transizioni possibili fra i quattro
--   stati e si confronta «la funzione la ammette» con «il guard l'ha lasciata
--   passare». Un elenco scritto a mano qui sarebbe una TERZA copia.
-- ============================================================
CREATE TEMP TABLE _matrice (stato_da text, stato_a text, ammessa_funzione boolean, passata_guard boolean);
DO $m$
DECLARE v_da text; v_a text; v_id bigint; v_ok boolean; v_cod text;
BEGIN
    FOREACH v_da IN ARRAY ARRAY['DRAFT', 'CONFIRM', 'POSTED', 'CANCEL'] LOOP
        FOREACH v_a IN ARRAY ARRAY['DRAFT', 'CONFIRM', 'POSTED', 'CANCEL'] LOOP
            CONTINUE WHEN v_a = v_da;    -- «nessun cambio» esce subito dal guard

            -- Un documento nello stato di partenza. POSTED e CANCEL si
            -- raggiungono passando per la matrice (POSTED solo attraverso
            -- l'operazione: qui basta CANCEL come terminale, e POSTED lo
            -- si ottiene col posting di una riga buona).
            INSERT INTO magazzino.inventari (magazzino_id) SELECT mag FROM _fix RETURNING id INTO v_id;
            IF v_da = 'CONFIRM' THEN
                UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_id;
            ELSIF v_da = 'CANCEL' THEN
                UPDATE magazzino.inventari SET stato_mag_inventario = 'CANCEL' WHERE id = v_id;
            ELSIF v_da = 'POSTED' THEN
                INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, ubicazione_id, costo_unitario)
                SELECT v_id, art, 1, ubi, 1 FROM _fix;
                UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_id;
                PERFORM * FROM magazzino.fn_posta_inventario(v_id);
            END IF;

            -- ⚠️ La porta POSTED e' un cancello A PARTE (GUC dell'operazione E
            --    proprietario, D-V1): come app CONFIRM -> POSTED la rifiuta sempre,
            --    pur essendo nella matrice. Il guard controlla la matrice PRIMA
            --    della porta, quindi il rifiuto della porta vuol dire «la matrice
            --    l'ha ammessa»: si legge dal codice (CONSTRAINT_NAME), e il test
            --    misura la sola MATRICE. La porta ha il suo test in
            --    test-documenti-interni-guard-v1. (Fino al 2026-09-25 qui si
            --    accendeva la GUC dall'app: dopo D-V1 non apre piu'.)
            BEGIN
                UPDATE magazzino.inventari SET stato_mag_inventario = v_a WHERE id = v_id;
                v_ok := true;
            EXCEPTION WHEN OTHERS THEN
                GET STACKED DIAGNOSTICS v_cod = CONSTRAINT_NAME;
                v_ok := v_cod IS NOT DISTINCT FROM 'E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE';
            END;

            INSERT INTO _matrice
            VALUES (v_da, v_a, v_a = ANY (magazzino.fn_documento_interno_transizioni(v_da)), v_ok);
        END LOOP;
    END LOOP;
END $m$;

SELECT is(
    (SELECT (count(*) FILTER (WHERE ammessa_funzione IS DISTINCT FROM passata_guard),
             count(*) FILTER (WHERE ammessa_funzione),
             count(*))::text FROM _matrice),
    '(0,5,12)',
    '3) la funzione e il guard dicono la STESSA cosa su tutte e dodici le transizioni (cinque ammesse)');

-- ============================================================
-- 4-9 Le azioni che il drawer disegna
-- ============================================================
CREATE TEMP TABLE _doc (etichetta text, inv bigint);
DO $d$
DECLARE v_id bigint;
BEGIN
    -- DRAFT, vuoto
    INSERT INTO magazzino.inventari (magazzino_id) SELECT mag FROM _fix RETURNING id INTO v_id;
    INSERT INTO _doc VALUES ('draft', v_id);

    -- CONFIRM senza righe
    INSERT INTO magazzino.inventari (magazzino_id) SELECT mag FROM _fix RETURNING id INTO v_id;
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_id;
    INSERT INTO _doc VALUES ('confirm_vuoto', v_id);

    -- CONFIRM con una riga buona
    INSERT INTO magazzino.inventari (magazzino_id) SELECT mag FROM _fix RETURNING id INTO v_id;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, ubicazione_id, costo_unitario)
    SELECT v_id, art, 5, ubi, 2 FROM _fix;
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_id;
    INSERT INTO _doc VALUES ('confirm_buono', v_id);

    -- CONFIRM con una riga che la primitiva rifiuterebbe (articolo NON gestito)
    INSERT INTO magazzino.inventari (magazzino_id) SELECT mag FROM _fix RETURNING id INTO v_id;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, ubicazione_id)
    SELECT v_id, art_no, 5, ubi FROM _fix;
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_id;
    INSERT INTO _doc VALUES ('confirm_rotto', v_id);

    -- POSTED: si arriva registrando
    INSERT INTO magazzino.inventari (magazzino_id) SELECT mag FROM _fix RETURNING id INTO v_id;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, ubicazione_id, costo_unitario)
    SELECT v_id, art, 3, ubi, 2 FROM _fix;
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_id;
    PERFORM * FROM magazzino.fn_posta_inventario(v_id);
    INSERT INTO _doc VALUES ('posted', v_id);

    -- CANCEL
    INSERT INTO magazzino.inventari (magazzino_id) SELECT mag FROM _fix RETURNING id INTO v_id;
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CANCEL' WHERE id = v_id;
    INSERT INTO _doc VALUES ('cancel', v_id);
END $d$;

SELECT is(
    (SELECT (c -> 'available_actions' -> 0 ->> 'key',
             c -> 'available_actions' -> 0 ->> 'target_state',
             c -> 'available_actions' -> 1 ->> 'key',
             c -> 'available_actions' -> 1 ->> 'target_state',
             jsonb_array_length(c -> 'available_actions'),
             c ->> 'can_edit_righe', c ->> 'can_delete')::text
       FROM script.fn_available_actions_inventario((SELECT inv FROM _doc WHERE etichetta = 'draft')) AS c),
    '(conferma,CONFIRM,annulla,CANCEL,2,true,true)',
    '4) in bozza: conferma e annulla, e la bozza si modifica e si cancella');

SELECT is(
    (SELECT (c -> 'available_actions' -> 0 ->> 'key',
             c -> 'available_actions' -> 1 ->> 'key',
             jsonb_array_length(c -> 'available_actions'),
             c ->> 'can_change_state', c ->> 'can_edit_righe')::text
       FROM script.fn_available_actions_inventario((SELECT inv FROM _doc WHERE etichetta = 'confirm_buono')) AS c),
    '(riapri,annulla,2,true,false)',
    '5) confermato: riapri e annulla — e POSTED NON e'' un pulsante (lo apre solo l''operazione)');

SELECT is(
    (SELECT (jsonb_array_length(c -> 'available_actions'),
             c ->> 'can_change_state', c ->> 'stato_info_key', c ->> 'can_edit_righe')::text
       FROM script.fn_available_actions_inventario((SELECT inv FROM _doc WHERE etichetta = 'posted')) AS c),
    '(0,false,magazzino.documenti_interni.stato_info.posted,false)',
    '6) registrato: nessuna azione, ma una nota che dice come si corregge');

SELECT is(
    (SELECT (jsonb_array_length(c -> 'available_actions'), c ->> 'stato_info_key')::text
       FROM script.fn_available_actions_inventario((SELECT inv FROM _doc WHERE etichetta = 'cancel')) AS c),
    '(0,magazzino.documenti_interni.stato_info.cancel)',
    '7) annullato: terminale, con la sua nota');

SELECT is(
    (SELECT count(*)::int
       FROM _doc d
       CROSS JOIN LATERAL script.fn_available_actions_inventario(d.inv) AS c
       CROSS JOIN LATERAL jsonb_array_elements(c -> 'available_actions') AS a
      WHERE a ->> 'label_key' NOT LIKE 'magazzino.documenti_interni.azione.%'
         OR a ->> 'label_key' IS NULL),
    0,
    '8) ogni azione porta la sua chiave i18n, tutte nello stesso namespace');

SELECT is(
    (SELECT (a ->> 'requires_confirm')::text
       FROM script.fn_available_actions_inventario((SELECT inv FROM _doc WHERE etichetta = 'draft')) AS c
       CROSS JOIN LATERAL jsonb_array_elements(c -> 'available_actions') AS a
      WHERE a ->> 'key' = 'annulla'),
    'true',
    '9) annullare chiede conferma: e'' l''uscita da cui non si torna indietro');

-- ============================================================
-- 10-13 La terna di «Registra»
-- ============================================================
SELECT is(
    (SELECT (c ->> 'can_registra', c ->> 'can_registra_reason', c ->> 'can_registra_reason_key')::text
       FROM script.fn_available_actions_inventario((SELECT inv FROM _doc WHERE etichetta = 'draft')) AS c),
    '(false,DOCUMENTO_NON_CONFERMATO,magazzino.documenti_interni.registra_reason.non_confermato)',
    '10) una bozza non si registra, e il pulsante lo dice');

SELECT is(
    (SELECT ((SELECT (c ->> 'can_registra') || '/' || (c ->> 'can_registra_reason')
                FROM script.fn_available_actions_inventario((SELECT inv FROM _doc WHERE etichetta = 'confirm_vuoto')) AS c),
             (SELECT (c2 ->> 'can_registra') || '/' || COALESCE(c2 ->> 'can_registra_reason', '-')
                FROM script.fn_available_actions_inventario((SELECT inv FROM _doc WHERE etichetta = 'confirm_buono')) AS c2))::text),
    '(false/DOCUMENTO_SENZA_RIGHE,true/-)',
    '11) confermato senza righe: no, e perche''; confermato con una riga buona: si''');

-- ⭐ Il codice del terzo motivo e' quello della RIGA (la stessa check che la
--    primitiva chiama): la frase che l'operatore legge non cambia, cambia solo
--    il vestito del pulsante.
SELECT is(
    (SELECT (m -> 0 ->> 'codice', m -> 0 ->> 'reason', m -> 0 -> 'dettaglio' ->> 'campo')::text
       FROM (SELECT script.fn_check_documento_interno_registrabile('INVENTARIO', (SELECT inv FROM _doc WHERE etichetta = 'confirm_rotto')) AS m) x),
    '(E_MAG_ARTICOLO_NON_GESTITO,RIGHE_NON_POSTABILI,articolo_id)',
    '12) riga non postabile: il codice e'' quello della riga, il motivo e'' del documento');

SELECT is(
    (SELECT (c ->> 'can_registra', c ->> 'can_registra_reason')::text
       FROM script.fn_available_actions_inventario((SELECT inv FROM _doc WHERE etichetta = 'posted')) AS c),
    '(false,DOCUMENTO_GIA_REGISTRATO)',
    '13) su un documento registrato il motivo e'' «gia'' registrato», non «non confermato» (sarebbe falso)');

-- ============================================================
-- 14 Fuori perimetro, e la rettifica
-- ============================================================
CREATE TEMP TABLE _ret AS SELECT NULL::bigint AS id;
DO $r$
DECLARE v_id bigint;
BEGIN
    INSERT INTO magazzino.rettifiche (magazzino_id) SELECT mag FROM _fix RETURNING id INTO v_id;
    INSERT INTO magazzino.rettifiche_righe (rettifica_id, articolo_id, qta_delta, ubicazione_id, costo_unitario, motivo)
    SELECT v_id, art, 2, ubi, 1, 'pgtap' FROM _fix;
    UPDATE magazzino.rettifiche SET stato_mag_rettifiche = 'CONFIRM' WHERE id = v_id;
    UPDATE _ret SET id = v_id;
END $r$;

SELECT is(
    (SELECT (script.fn_available_actions_inventario(999999999) IS NULL,
             script.fn_available_actions_rettifica(999999999) IS NULL,
             (SELECT (c ->> 'stato_codice') || '/' || (c ->> 'can_registra') || '/' ||
                     (c -> 'available_actions' -> 0 ->> 'key')
                FROM script.fn_available_actions_rettifica((SELECT id FROM _ret)) AS c))::text),
    '(t,t,CONFIRM/true/riapri)',
    '14) un documento che non si legge torna NULL (il 404 lo da'' il BE), e la rettifica si comporta come l''inventario');

SELECT * FROM finish();
ROLLBACK;
