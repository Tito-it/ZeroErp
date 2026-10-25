-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'ordine sul modello del documento, e lo stato d'annullo dal vocabolario
--   Un solo stato d'annullo per vocabolario (20261025-72), l'azione sulla
--   matrice dell'ordine (-73), script.fn_stato_abortito_id (-74), il verbo
--   vendite.fn_cambia_stato_ordine (-75), l'annullo dal verbo (-76), la
--   proiezione dell'evasione dal verbo comune (-79), la porta (-80), la
--   capability (-81). Brief: brief-modello-documento-vendita §9 (giro 7;
--   Z-1 … Z-3 di Tid, 2026-10-25).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - ogni vocabolario ha al massimo uno stato d'annullo, attivo; il lettore
--     lo rende per ogni testata della mappa; fuori mappa: chiamata non valida;
--   - la matrice dell'ordine chiede emetti_ordine sulla conferma e
--     sull'annullo del confermato, e su nient'altro;
--   - chi non ha emetti_ordine non vede «Conferma» e il verbo glielo rifiuta;
--     l'annullo della bozza non chiede azioni;
--   - con l'azione il verbo conferma; un passaggio di processo chiesto al
--     verbo e' rifiutato; l'annullo del confermato passa dal verbo d'annullo;
--   - l'evasione (bolla dall'ordine) porta l'ordine in EVASO o
--     PARZIALMENTE_EVASO attraverso la porta;
--   - la porta: un UPDATE diretto dello stato e' rifiutato.
--
-- ⚠️ DIPENDE DAL RUOLO (test 16): la porta chiede anche che chi scrive sia il
--   proprietario della tabella. Come applicazione (il runner) e' verde; da
--   owner (la prova dell'SQL estratto prima dell'apply) e' rosso per
--   costruzione. Per questo sta in coda.
--
-- Elenco test (plan 16):
--   1) gli oggetti: verbo DEFINER, lettore, proiezione DEFINER, porta montata
--   2) indice unico parziale e CHECK «attivo» sugli otto vocabolari
--   3) fn_stato_abortito_id: per ogni testata della mappa, lo stato is_abortito del vocabolario
--   4) fn_stato_abortito_id: testata fuori mappa -> chiamata non valida
--   5) la matrice dell'ordine: emetti_ordine su conferma e annullo del confermato
--   6) emetti_ordine a catalogo, attiva
--   7) capability in bozza senza emetti_ordine: «Conferma» non c'e', «Annulla» si'
--   8) il verbo senza emetti_ordine: E_PERMESSO_NEGATO
--   9) l'annullo di una bozza senza l'azione: passa (dal verbo d'annullo)
--  10) capability con emetti_ordine: «Conferma» c'e'
--  11) il verbo con emetti_ordine conferma l'ordine
--  12) un passaggio di processo chiesto al verbo (CONFERMATO -> EVASO)
--  13) l'annullo del confermato dal verbo d'annullo: ANNULLATO
--  14) l'evasione piena: l'ordine e' EVASO, attraverso la porta
--  15) l'evasione parziale: l'ordine e' PARZIALMENTE_EVASO
--  16) UPDATE diretto dello stato: E_DOC_STATO_SOLO_DAL_VERBO   [rosso da owner]
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- 1) Gli oggetti e la loro forma
SELECT is(
    (SELECT string_agg(p.proname || ':' || p.prosecdef::text, ' ' ORDER BY p.proname)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE (n.nspname, p.proname) IN (('vendite', 'fn_cambia_stato_ordine'),
                                       ('vendite', 'fn_ordine_proietta_stato_evasione'),
                                       ('script',  'fn_stato_abortito_id')))
    || ' porta:' || EXISTS (SELECT 1 FROM pg_trigger t
                             WHERE t.tgrelid = 'vendite.ordini'::regclass
                               AND t.tgfoid  = 'script.trgfn_doc_stato_solo_dal_verbo()'::regprocedure
                               AND NOT t.tgisinternal)::text,
    'fn_cambia_stato_ordine:true fn_ordine_proietta_stato_evasione:true fn_stato_abortito_id:false porta:true',
    'il verbo e la proiezione sono DEFINER, il lettore INVOKER, la porta e'' montata sull''ordine'
);

-- 2) Al massimo uno stato d'annullo per vocabolario, ed e' attivo
SELECT is(
    (SELECT count(*)::integer FROM pg_index i
       JOIN pg_class c ON c.oid = i.indexrelid
      WHERE i.indisunique AND i.indpred IS NOT NULL
        AND c.relname IN ('uq_stati_doc_preventivi_abortito', 'uq_stati_doc_offerte_abortito',
                          'uq_stati_doc_contratti_abortito', 'uq_stati_doc_ordini_abortito',
                          'uq_stati_doc_ddt_abortito', 'uq_stati_doc_reso_abortito',
                          'uq_stati_doc_fiscale_abortito', 'uq_stati_commessa_abortito'))
    + (SELECT count(*)::integer FROM pg_constraint k
        WHERE k.contype = 'c' AND k.conname LIKE 'chk\_stati\_%\_abortito\_attivo'),
    16,
    'indice unico parziale e CHECK «attivo» sullo stato d''annullo, negli otto vocabolari'
);

-- 3) Il lettore, per ogni testata della mappa: lo stato is_abortito del suo
--    vocabolario, letto dalla colonna (non scritto qui).
CREATE TEMP TABLE t_abort (testata regclass, letto bigint, atteso bigint);

DO $abort$
DECLARE
    v_testata regclass;
    v_voc     regclass;
    v_atteso  bigint;
BEGIN
    FOREACH v_testata IN ARRAY ARRAY['vendite.preventivi', 'vendite.offerte_commerciali',
                                     'vendite.contratti', 'vendite.ordini', 'vendite.ddt',
                                     'vendite.resi', 'vendite.commesse', 'vendite.fatture']::regclass[]
    LOOP
        SELECT m.vocabolario INTO v_voc FROM script.fn_doc_stato_modello(v_testata) m;
        EXECUTE format('SELECT s.id FROM %s s WHERE s.is_abortito', v_voc) INTO v_atteso;
        INSERT INTO t_abort VALUES (v_testata, script.fn_stato_abortito_id(v_testata), v_atteso);
    END LOOP;
END
$abort$;

SELECT is(
    (SELECT count(*)::integer FROM t_abort WHERE atteso IS NOT NULL AND letto = atteso),
    8,
    'fn_stato_abortito_id: per le otto testate, lo stato d''annullo che il vocabolario dichiara'
);

-- 4) Fuori mappa
SELECT throws_like(
    $$SELECT script.fn_stato_abortito_id('config.sorgenti'::regclass)$$,
    'Chiamata non valida a script.fn_stato_abortito_id%',
    'fn_stato_abortito_id: una tabella fuori dalla mappa -> chiamata non valida'
);

-- 5) Le azioni sulla matrice dell'ordine (Z-1)
SELECT is(
    (SELECT string_agg(sd.codice_interno || '>' || sa.codice_interno || '=' || t.azione_processo_codename,
                       ' ' ORDER BY sd.codice_interno, sa.codice_interno)
       FROM config.transizioni_stati_ordini t
       JOIN config.stati_doc_ordini sd ON sd.id = t.stato_da_id
       JOIN config.stati_doc_ordini sa ON sa.id = t.stato_a_id
      WHERE t.azione_processo_codename IS NOT NULL),
    'CONFERMATO>ANNULLATO=emetti_ordine DRAFT>CONFERMATO=emetti_ordine',
    'la matrice dell''ordine: emetti_ordine sulla conferma e sull''annullo del confermato, nient''altro'
);

-- 6) L'azione a catalogo
SELECT ok(
    EXISTS (SELECT 1 FROM config.azioni_processo a
             WHERE a.permission_codename = 'emetti_ordine' AND a.attivo),
    'emetti_ordine e'' a catalogo, attiva'
);

-- Due ordini in bozza con la riga: il builder apre il contesto
-- sull'operatore che costruisce.
CREATE TEMP TABLE t_ord AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('pgTAP ordine al modello', 'DRAFT');

CREATE TEMP TABLE t_bozza AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('pgTAP ordine al modello bozza', 'DRAFT');

-- 7) Permesso => nascondi
SELECT is(
    (SELECT string_agg(a ->> 'key', ' ' ORDER BY a ->> 'key')
       FROM jsonb_array_elements(script.fn_available_actions_ordine((SELECT ordine_id FROM t_ord))
                                 -> 'available_actions') a
      WHERE a ->> 'target_state' IS NOT NULL),
    'annulla',
    'capability dell''ordine in bozza senza emetti_ordine: «Conferma» non c''e'', «Annulla» si'''
);

-- 8) Il verbo chiede l'azione della riga
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_ordine(%s, 'CONFERMATO')$$,
           (SELECT ordine_id FROM t_ord)),
    'Non hai i permessi per questa operazione%',
    'il verbo dell''ordine senza emetti_ordine: E_PERMESSO_NEGATO'
);

-- 9) L'annullo della bozza: riga senza azione (M-4)
-- ⚠️ Il verbo in un'istruzione sua: una lettura nella stessa istruzione
--    vedrebbe la fotografia di prima della chiamata.
SELECT vendite.fn_annulla_ordine((SELECT ordine_id FROM t_bozza));
SELECT is(
    (SELECT s.codice_interno::text FROM vendite.ordini o
       JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
      WHERE o.id = (SELECT ordine_id FROM t_bozza)),
    'ANNULLATO',
    'l''annullo di una bozza senza emetti_ordine: dal verbo d''annullo, nessuna azione'
);

SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'emetti_ordine');

-- 10) Con l'azione «Conferma» c'e'
SELECT is(
    (SELECT string_agg(a ->> 'key', ' ' ORDER BY a ->> 'key')
       FROM jsonb_array_elements(script.fn_available_actions_ordine((SELECT ordine_id FROM t_ord))
                                 -> 'available_actions') a
      WHERE a ->> 'target_state' IS NOT NULL),
    'annulla conferma',
    'capability dell''ordine in bozza con emetti_ordine: «Conferma» c''e'''
);

-- 11) Il verbo con l'azione conferma
SELECT is(
    (SELECT v.stato_precedente::text || '>' || v.stato_nuovo::text
       FROM vendite.fn_cambia_stato_ordine((SELECT ordine_id FROM t_ord), 'CONFERMATO') v),
    'DRAFT>CONFERMATO',
    'il verbo con emetti_ordine conferma l''ordine, dalla scrittura comune'
);

-- 12) CONFERMATO -> EVASO e' di processo (manuale = false): non si chiede a mano
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_ordine(%s, 'EVASO')$$,
           (SELECT ordine_id FROM t_ord)),
    'Questo passaggio di stato lo fa il sistema%',
    'un passaggio di processo (CONFERMATO -> EVASO) chiesto al verbo: E_DOC_PASSAGGIO_DI_PROCESSO'
);

-- 13) L'annullo del confermato: dal verbo d'annullo, che chiama il verbo di stato
-- ⚠️ Il verbo in un'istruzione sua: una lettura nella stessa istruzione
--    vedrebbe la fotografia di prima della chiamata.
SELECT vendite.fn_annulla_ordine((SELECT ordine_id FROM t_ord));
SELECT is(
    (SELECT s.codice_interno::text FROM vendite.ordini o
       JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
      WHERE o.id = (SELECT ordine_id FROM t_ord)),
    'ANNULLATO',
    'l''annullo di un ordine confermato, con emetti_ordine: ANNULLATO dal verbo di stato'
);

-- 14-15) L'evasione: la bolla dall'ordine porta l'ordine in EVASO o in
--        PARZIALMENTE_EVASO, scritto dalla proiezione attraverso la porta.
CREATE TEMP TABLE t_pieno AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgTAP ordine al modello evaso', 'EMESSO',
                                                p_quantita => 10);

SELECT is(
    (SELECT s.codice_interno::text FROM vendite.ordini o
       JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
      WHERE o.id = (SELECT ordine_id FROM t_pieno)),
    'EVASO',
    'l''evasione piena (bolla dall''ordine): l''ordine e'' EVASO, dalla proiezione attraverso la porta'
);

CREATE TEMP TABLE t_parziale AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgTAP ordine al modello parziale', 'EMESSO',
                                                p_quantita => 10, p_qta_da_evadere => 4);

SELECT is(
    (SELECT s.codice_interno::text FROM vendite.ordini o
       JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
      WHERE o.id = (SELECT ordine_id FROM t_parziale)),
    'PARZIALMENTE_EVASO',
    'l''evasione parziale: l''ordine e'' PARZIALMENTE_EVASO'
);

-- 16) [rosso da owner] Un UPDATE diretto dello stato, anche con la GUC accesa
--     dall'applicazione: la porta chiede anche il proprietario.
SELECT set_config('zeroerp.doc_cambio_stato',
                  'vendite.ordini'::regclass::oid::text || ':' || (SELECT ordine_id FROM t_pieno)::text,
                  true);
SELECT throws_like(
    format($$UPDATE vendite.ordini SET stato_doc_ordine_id = %s WHERE id = %s$$,
           script.fn_doc_stato_id('vendite.ordini'::regclass, 'CONFERMATO'), (SELECT ordine_id FROM t_pieno)),
    '%si cambia solo dalle sue operazioni%',
    'un UPDATE diretto dello stato dell''ordine, anche con la GUC accesa: E_DOC_STATO_SOLO_DAL_VERBO [rosso da owner]'
);
SELECT set_config('zeroerp.doc_cambio_stato', '', true);

SELECT * FROM finish();
ROLLBACK;
