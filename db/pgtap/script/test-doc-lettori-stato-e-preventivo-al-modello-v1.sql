-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-26 (brief-modello-documento-vendita §9.10): test 19 nuovo, il secondo «Emetti»
--   (20261026-01, E_DOC_GIA_NELLO_STATO); i test 19-22 passano a 20-23.
-- pgTAP test per Zero ERP
--
-- Test: i lettori dello stato e il preventivo sul modello del documento
--   Colonna emissione sui vocabolari (20261025-37), azione sulla matrice del
--   preventivo (-38), script.fn_doc_stato_id (-39), script.fn_stato_emissione_id
--   (-40), script.fn_doc_azione_passaggio (-41), il verbo del preventivo sul
--   verbo comune (-42, -43), la porta sul preventivo (-46), la capability (-47).
--   Brief: brief-modello-documento-vendita §8 (giro 6; U-1 … U-3 di Tid,
--   2026-10-25).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - codice -> id: lo stato ATTIVO con quel codice_interno nel vocabolario
--     della testata; NULL per un codice che non c'e' o uno stato spento (U-3);
--     testata fuori mappa: chiamata non valida;
--   - lo stato di emissione lo dichiara il vocabolario (al massimo uno, ed e'
--     attivo) nei cinque documenti che si emettono; reso, commessa e fattura
--     non si emettono (NULL);
--   - la matrice del preventivo chiede emetti_preventivo sull'emissione e
--     sull'annullo dell'emesso e dell'accettato (U-1, U-2), e su nient'altro;
--   - la domanda intera dice stati, emissione e riga del passaggio di un
--     documento che si vede; nessuna riga per un documento che non c'e';
--   - il verbo chiede l'azione della riga, rifiuta i passaggi di processo,
--     l'emissione senza righe e il secondo «Emetti» (E_DOC_GIA_NELLO_STATO); l'annullo della bozza non chiede azioni;
--   - la capability nasconde il passaggio con l'azione a chi non ce l'ha;
--   - la porta: un UPDATE diretto dello stato e' rifiutato.
--
-- ⚠️ DIPENDE DAL RUOLO (test 23): la porta chiede anche che chi scrive sia il
--   proprietario della tabella. Come applicazione (il runner) e' verde; da
--   owner (la prova dell'SQL estratto prima dell'apply) e' rosso per
--   costruzione. Per questo sta in coda.
--
-- Elenco test (plan 23):
--   1) i tre lettori esistono
--   2) fn_doc_stato_id: EMESSO del preventivo -> il suo id
--   3) fn_doc_stato_id: un codice che non c'e' -> NULL
--   4) fn_doc_stato_id: uno stato spento -> NULL (U-3)
--   5) fn_doc_stato_id: testata fuori mappa -> chiamata non valida
--   6) la colonna emissione: cinque vocabolari, indice unico parziale e CHECK
--   7) gli stati di emissione seminati, uno per vocabolario
--   8) fn_stato_emissione_id: preventivo -> EMESSO; reso, commessa e fattura -> NULL
--   9) le azioni sulla matrice del preventivo: emetti_preventivo su tre righe
--  10) l'azione nuova a catalogo
--  11) domanda intera, bozza -> EMESSO: emissione, riga manuale, emetti_preventivo
--  12) domanda intera, bozza -> ACCETTATO: fuori matrice, nessuna azione
--  13) domanda intera, codice ignoto: stato chiesto NULL, fuori matrice
--  14) domanda intera, documento che non c'e': nessuna riga
--  15) capability in bozza senza emetti_preventivo: «Emetti» non c'e'
--  16) il verbo senza emetti_preventivo: E_PERMESSO_NEGATO
--  17) capability con emetti_preventivo: «Emetti» c'e'
--  18) il verbo con emetti_preventivo emette il preventivo
--  19) il secondo «Emetti» dal verbo: E_DOC_GIA_NELLO_STATO
--  20) un passaggio di processo chiesto al verbo (EMESSO -> SCADUTO)
--  21) l'emissione senza righe: E_PREV_NESSUNA_RIGA_ATTIVA
--  22) l'annullo di una bozza: nessuna azione, passa
--  23) UPDATE diretto dello stato: E_DOC_STATO_SOLO_DAL_VERBO   [rosso da owner]
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(23);

-- 1) Gli oggetti
SELECT is(
    (SELECT count(*)::integer FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script'
        AND p.proname IN ('fn_doc_stato_id', 'fn_stato_emissione_id', 'fn_doc_azione_passaggio')),
    3,
    'i tre lettori del modello esistono'
);

-- Gli id degli stati del preventivo, per codice.
CREATE TEMP TABLE t_st AS
SELECT s.codice_interno::text AS cod, s.id FROM config.stati_doc_preventivi s;

-- 2-5) Codice -> id
SELECT is(
    script.fn_doc_stato_id('vendite.preventivi'::regclass, 'EMESSO'),
    (SELECT id FROM t_st WHERE cod = 'EMESSO'),
    'fn_doc_stato_id: EMESSO del preventivo -> il suo id'
);

SELECT ok(
    script.fn_doc_stato_id('vendite.preventivi'::regclass, 'PGTAP_NON_ESISTE') IS NULL,
    'fn_doc_stato_id: un codice che il vocabolario non ha -> NULL'
);

-- Uno stato spento, costruito qui: nessun documento lo usa.
INSERT INTO config.stati_doc_preventivi (id, codice_interno, codice, descrizione, attivo,
                                         fase, pdf_mode, pdf_allow_allegati)
VALUES (990601, 'PGTAP_SPENTO', 'PGTAP_SPENTO', 'pgTAP stato spento', false,
        'CHIUSO', 'ARCHIVE', false);

SELECT ok(
    script.fn_doc_stato_id('vendite.preventivi'::regclass, 'PGTAP_SPENTO') IS NULL,
    'fn_doc_stato_id: uno stato spento non e'' una destinazione -> NULL (U-3)'
);

SELECT throws_like(
    $$SELECT script.fn_doc_stato_id('config.sorgenti'::regclass, 'EMESSO')$$,
    'Chiamata non valida a script.fn_doc_stato_id%',
    'fn_doc_stato_id: una tabella fuori dalla mappa -> chiamata non valida'
);

-- 6) La colonna, l'indice unico parziale e il CHECK sui cinque vocabolari
SELECT is(
    (SELECT count(*)::integer FROM pg_attribute a
      WHERE a.attname = 'emissione' AND NOT a.attisdropped AND a.attnotnull
        AND a.attrelid IN ('config.stati_doc_preventivi'::regclass, 'config.stati_doc_offerte'::regclass,
                           'config.stati_doc_contratti'::regclass, 'config.stati_doc_ordini'::regclass,
                           'config.stati_doc_ddt'::regclass))
    + (SELECT count(*)::integer FROM pg_index i
        JOIN pg_class c ON c.oid = i.indexrelid
       WHERE i.indisunique AND i.indpred IS NOT NULL
         AND c.relname LIKE 'uq\_stati\_doc\_%\_emissione')
    + (SELECT count(*)::integer FROM pg_constraint k
        WHERE k.contype = 'c' AND k.conname LIKE 'chk\_stati\_doc\_%\_emissione\_attivo'),
    15,
    'la colonna emissione (NOT NULL) sui cinque vocabolari, con indice unico parziale e CHECK «attivo»'
);

-- 7) Gli stati di emissione seminati
SELECT is(
    (SELECT string_agg(x, ' ' ORDER BY x) FROM (
        SELECT 'contratti:' || codice_interno AS x FROM config.stati_doc_contratti WHERE emissione
        UNION ALL SELECT 'ddt:' || codice_interno FROM config.stati_doc_ddt WHERE emissione
        UNION ALL SELECT 'offerte:' || codice_interno FROM config.stati_doc_offerte WHERE emissione
        UNION ALL SELECT 'ordini:' || codice_interno FROM config.stati_doc_ordini WHERE emissione
        UNION ALL SELECT 'preventivi:' || codice_interno FROM config.stati_doc_preventivi WHERE emissione) z),
    'contratti:ATTIVO ddt:EMESSO offerte:EMESSA ordini:CONFERMATO preventivi:EMESSO',
    'gli stati di emissione seminati: uno per vocabolario'
);

-- 8) Il lettore dello stato di emissione
SELECT is(
    ARRAY[script.fn_stato_emissione_id('vendite.preventivi'::regclass),
          script.fn_stato_emissione_id('vendite.resi'::regclass),
          script.fn_stato_emissione_id('vendite.commesse'::regclass),
          script.fn_stato_emissione_id('vendite.fatture'::regclass)],
    ARRAY[(SELECT id FROM t_st WHERE cod = 'EMESSO'), NULL, NULL, NULL]::bigint[],
    'fn_stato_emissione_id: il preventivo si emette in EMESSO; reso, commessa e fattura non si emettono'
);

-- 9) Le azioni sulla matrice del preventivo (U-1, U-2)
SELECT is(
    (SELECT string_agg(sd.codice_interno || '>' || sa.codice_interno || '=' || t.azione_processo_codename,
                       ' ' ORDER BY sd.codice_interno, sa.codice_interno)
       FROM config.transizioni_stati_preventivi t
       JOIN config.stati_doc_preventivi sd ON sd.id = t.stato_da_id
       JOIN config.stati_doc_preventivi sa ON sa.id = t.stato_a_id
      WHERE t.azione_processo_codename IS NOT NULL),
    'ACCETTATO>ANNULLATO=emetti_preventivo DRAFT>EMESSO=emetti_preventivo EMESSO>ANNULLATO=emetti_preventivo',
    'la matrice del preventivo: emetti_preventivo su emissione e annullo dell''emesso e dell''accettato, nient''altro'
);

-- 10) L'azione nuova a catalogo
SELECT ok(
    EXISTS (SELECT 1 FROM config.azioni_processo a
             WHERE a.permission_codename = 'emetti_preventivo' AND a.attivo),
    'emetti_preventivo e'' a catalogo, attiva'
);

-- Il preventivo in bozza, con una riga: il builder apre il contesto
-- sull'operatore che costruisce.
CREATE TEMP TABLE t_prev AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgTAP lettori e preventivo');

CREATE TEMP TABLE t_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-G6-A', false,
           p_natura_vendita_id => (SELECT nv.id FROM config.nature_vendita nv
                                    WHERE nv.destinazione_tipo = 'ORDINE_VENDITA' AND nv.attivo
                                    ORDER BY nv.id LIMIT 1)) AS id;

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa)
SELECT (SELECT preventivo_id FROM t_prev), (SELECT id FROM t_art),
       (SELECT i.id FROM config.iva i WHERE i.attivo AND i.aliquota_iva > 0 ORDER BY i.id LIMIT 1),
       10, 1;

-- 11-14) La domanda intera
SELECT is(
    (SELECT a.emissione::text || ' ' || a.nella_matrice::text || ' ' || a.manuale::text || ' '
            || COALESCE(a.azione_processo_codename, '-')
       FROM script.fn_doc_azione_passaggio('vendite.preventivi'::regclass,
                                           (SELECT preventivo_id FROM t_prev), 'EMESSO') a
      WHERE a.stato_da_id = (SELECT id FROM t_st WHERE cod = 'DRAFT')
        AND a.stato_a_id  = (SELECT id FROM t_st WHERE cod = 'EMESSO')),
    'true true true emetti_preventivo',
    'domanda intera, bozza -> EMESSO: e'' l''emissione, riga manuale, chiede emetti_preventivo'
);

SELECT is(
    (SELECT a.emissione::text || ' ' || a.nella_matrice::text || ' '
            || COALESCE(a.manuale::text, '-') || ' ' || COALESCE(a.azione_processo_codename, '-')
       FROM script.fn_doc_azione_passaggio('vendite.preventivi'::regclass,
                                           (SELECT preventivo_id FROM t_prev), 'ACCETTATO') a),
    'false false - -',
    'domanda intera, bozza -> ACCETTATO: fuori matrice, nessuna riga del passaggio'
);

SELECT is(
    (SELECT COALESCE(a.stato_a_id::text, '-') || ' ' || a.nella_matrice::text || ' ' || a.emissione::text
       FROM script.fn_doc_azione_passaggio('vendite.preventivi'::regclass,
                                           (SELECT preventivo_id FROM t_prev), 'PGTAP_NON_ESISTE') a),
    '- false false',
    'domanda intera, codice ignoto: stato chiesto NULL, fuori matrice, non e'' l''emissione'
);

SELECT is(
    (SELECT count(*)::integer
       FROM script.fn_doc_azione_passaggio('vendite.preventivi'::regclass, -1, 'EMESSO')),
    0,
    'domanda intera, documento che non c''e'': nessuna riga'
);

-- 15) Permesso => nascondi: chi non ha emetti_preventivo non vede «Emetti»
SELECT is(
    (SELECT count(*)::integer
       FROM jsonb_array_elements(script.fn_available_actions_preventivo((SELECT preventivo_id FROM t_prev))
                                 -> 'available_actions') a
      WHERE a ->> 'target_state' = 'EMESSO'),
    0,
    'capability del preventivo in bozza: senza emetti_preventivo il passaggio a EMESSO non c''e'''
);

-- 16) Il verbo chiede l'azione della riga
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, 'EMESSO')$$,
           (SELECT preventivo_id FROM t_prev)),
    'Non hai i permessi per questa operazione%',
    'il verbo del preventivo senza emetti_preventivo: E_PERMESSO_NEGATO'
);

SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'emetti_preventivo');

-- 17) Con l'azione «Emetti» c'e'
SELECT is(
    (SELECT count(*)::integer
       FROM jsonb_array_elements(script.fn_available_actions_preventivo((SELECT preventivo_id FROM t_prev))
                                 -> 'available_actions') a
      WHERE a ->> 'target_state' = 'EMESSO'),
    1,
    'capability del preventivo in bozza: con emetti_preventivo il passaggio a EMESSO c''e'''
);

-- 18) Il verbo con l'azione emette
SELECT is(
    (SELECT v.stato_precedente::text || '>' || v.stato_nuovo::text
       FROM vendite.fn_cambia_stato_preventivo((SELECT preventivo_id FROM t_prev), 'EMESSO') v),
    'DRAFT>EMESSO',
    'il verbo con emetti_preventivo emette il preventivo, dalla scrittura comune'
);

-- 19) Il secondo «Emetti»: la matrice non ha EMESSO -> EMESSO, e il guard di
--     transizione non lo vede (lo stato non cambia). Lo rifiuta la prima riga
--     del verbo, prima che il backend generi un secondo PDF (brief §9.8).
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, 'EMESSO')$$,
           (SELECT preventivo_id FROM t_prev)),
    'Il documento è già nello stato EMESSO%',
    'il secondo «Emetti» del preventivo, dal verbo: E_DOC_GIA_NELLO_STATO'
);

-- 20) EMESSO -> SCADUTO e' di processo (manuale = false): non si chiede a mano
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, 'SCADUTO')$$,
           (SELECT preventivo_id FROM t_prev)),
    'Questo passaggio di stato lo fa il sistema%',
    'un passaggio di processo (EMESSO -> SCADUTO) chiesto al verbo: E_DOC_PASSAGGIO_DI_PROCESSO'
);

-- Un secondo preventivo, in bozza e senza righe.
CREATE TEMP TABLE t_vuoto AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgTAP lettori e preventivo vuoto');

-- 21) L'emissione chiede almeno una riga attiva (con l'azione concessa)
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, 'EMESSO')$$,
           (SELECT preventivo_id FROM t_vuoto)),
    '%senza righe attive%',
    'l''emissione di un preventivo senza righe: E_PREV_NESSUNA_RIGA_ATTIVA'
);

-- 22) L'annullo della bozza: riga senza azione (M-4)
SELECT is(
    (SELECT v.stato_nuovo::text
       FROM vendite.fn_cambia_stato_preventivo((SELECT preventivo_id FROM t_vuoto), 'ANNULLATO') v),
    'ANNULLATO',
    'l''annullo di una bozza: nessuna azione, il verbo passa'
);

-- 23) [rosso da owner] Un UPDATE diretto dello stato, anche con la GUC accesa
--     dall'applicazione: la porta chiede anche il proprietario.
SELECT set_config('zeroerp.doc_cambio_stato',
                  'vendite.preventivi'::regclass::oid::text || ':' || (SELECT preventivo_id FROM t_prev)::text,
                  true);
SELECT throws_like(
    format($$UPDATE vendite.preventivi SET stato_doc_preventivo_id = %s WHERE id = %s$$,
           (SELECT id FROM t_st WHERE cod = 'ACCETTATO'), (SELECT preventivo_id FROM t_prev)),
    'Lo stato del documento Preventivo % si cambia solo dalle sue operazioni%',
    'un UPDATE diretto dello stato del preventivo, anche con la GUC accesa: E_DOC_STATO_SOLO_DAL_VERBO [rosso da owner]'
);
SELECT set_config('zeroerp.doc_cambio_stato', '', true);

SELECT * FROM finish();
ROLLBACK;
