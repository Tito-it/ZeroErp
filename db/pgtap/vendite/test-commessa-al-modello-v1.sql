-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la commessa sul modello del documento
--   L'azione sulla matrice della commessa (20261026-29) e la matrice nuova
--   (IN_ESECUZIONE ritirato, «riapri» verso APERTA, «chiudi» da APERTA), il
--   verbo vendite.fn_cambia_stato_commessa sul verbo comune e senza p_user
--   (-30), il ponte della push dalla proiezione (-31, -32), l'annullo (-33),
--   la porta (-34), la capability (-35), la fixture degli stati (-36).
--   Brief: brief-modello-documento-vendita §14 (giro 10; C-1 … C-4 di Tid,
--   2026-10-26).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la matrice chiede cambia_stato_commessa su «rendi pronta», «riapri»,
--     «chiudi» e sull'annullo di una commessa non in bozza; l'annullo della
--     bozza no (C-1);
--   - IN_ESECUZIONE e' ritirato: nessuna riga attiva della matrice lo nomina
--     e il verbo non lo trova; BOZZA -> APERTA e' spento; «riapri» porta ad
--     APERTA, e da APERTA si rende pronta, si chiude, si annulla (C-3);
--   - chi non ha l'azione non vede i bottoni e il verbo glieli rifiuta;
--   - il ponte della push porta la commessa a pronta senza l'azione del
--     passaggio manuale (C-2);
--   - il verbo ha la firma (id, stato) (C-4);
--   - la porta: un UPDATE diretto dello stato e' rifiutato.
--
-- Elenco test (plan 20):
--   1) gli oggetti: verbo e proiezione DEFINER, porta montata
--   2) la firma del verbo: (bigint, varchar), una sola
--   3) la matrice: cambia_stato_commessa sui passaggi pesanti, nient'altro
--   4) IN_ESECUZIONE spento e nessuna riga attiva lo nomina; BOZZA -> APERTA spento
--   5) capability in bozza senza l'azione: solo «Annulla»
--   6) il verbo senza l'azione: E_PERMESSO_NEGATO
--   7) il ponte della push senza l'azione: la commessa e' pronta
--   8) l'annullo della bozza senza l'azione: ANNULLATA
--   9) capability in bozza con l'azione: «Annulla» e «Rendi pronta»
--  10) «Rendi pronta» dal verbo: PRONTA_FATTURAZIONE
--  11) un secondo «Rendi pronta»: E_DOC_GIA_NELLO_STATO
--  12) «Riapri»: APERTA
--  13) capability in APERTA: «Annulla», «Chiudi», «Rendi pronta»
--  14) IN_ESECUZIONE chiesto al verbo: E_STATO_WORKFLOW_NON_TROVATO
--  15) BOZZA -> APERTA chiesto al verbo: E_COMMESSA_STATO_TRANSIZIONE_INVALIDA
--  16) la fixture porta una commessa ad APERTA (rendi pronta, riapri)
--  17) l'annullo di una commessa aperta, con la conferma dei legami: ANNULLATA
--  18) il ponte della push su una commessa gia' pronta: niente
--  19) il ponte della push su una commessa annullata: rifiutato dalla matrice
--  20) UPDATE diretto dello stato: E_DOC_STATO_SOLO_DAL_VERBO
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(20);

-- 1) Gli oggetti e la loro forma
SELECT is(
    (SELECT string_agg(p.proname || ':' || p.prosecdef::text, ' ' ORDER BY p.proname)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite'
        AND p.proname IN ('fn_cambia_stato_commessa', 'fn_commessa_proietta_stato_emittibile'))
    || ' porta:' || EXISTS (SELECT 1 FROM pg_trigger t
                             WHERE t.tgrelid = 'vendite.commesse'::regclass
                               AND t.tgfoid  = 'script.trgfn_doc_stato_solo_dal_verbo()'::regprocedure
                               AND NOT t.tgisinternal)::text,
    'fn_cambia_stato_commessa:true fn_commessa_proietta_stato_emittibile:true porta:true',
    'il verbo e la proiezione sono DEFINER, la porta e'' montata sulla commessa'
);

-- 2) La firma (C-4)
SELECT is(
    (SELECT string_agg(pg_get_function_identity_arguments(p.oid), ' | ')
       FROM pg_proc p
      WHERE p.oid IN (SELECT oid FROM pg_proc WHERE proname = 'fn_cambia_stato_commessa'
                        AND pronamespace = 'vendite'::regnamespace)),
    'p_commessa_id bigint, p_stato character varying',
    'il verbo della commessa ha la firma (id, stato), senza p_user, e una sola'
);

-- 3) Le azioni sulla matrice (C-1)
SELECT is(
    (SELECT string_agg(sd.codice_interno || '>' || sa.codice_interno || '=' || t.azione_processo_codename,
                       ' ' ORDER BY sd.codice_interno, sa.codice_interno)
       FROM vendite.transizioni_stati_commessa t
       JOIN vendite.stati_commessa sd ON sd.id = t.stato_da_id
       JOIN vendite.stati_commessa sa ON sa.id = t.stato_a_id
      WHERE t.attivo AND t.azione_processo_codename IS NOT NULL),
    'APERTA>ANNULLATA=cambia_stato_commessa APERTA>CHIUSA=cambia_stato_commessa '
    'APERTA>PRONTA_FATTURAZIONE=cambia_stato_commessa BOZZA>PRONTA_FATTURAZIONE=cambia_stato_commessa '
    'PRONTA_FATTURAZIONE>ANNULLATA=cambia_stato_commessa PRONTA_FATTURAZIONE>APERTA=cambia_stato_commessa '
    'PRONTA_FATTURAZIONE>CHIUSA=cambia_stato_commessa',
    'la matrice: l''azione sui passaggi pesanti; l''annullo della bozza senza'
);

-- 4) IN_ESECUZIONE ritirato, BOZZA -> APERTA spento (C-3)
SELECT is(
    (SELECT s.attivo::text FROM vendite.stati_commessa s WHERE s.codice_interno = 'IN_ESECUZIONE')
    || '|' || (SELECT count(*) FROM vendite.transizioni_stati_commessa t
                 JOIN vendite.stati_commessa sd ON sd.id = t.stato_da_id
                 JOIN vendite.stati_commessa sa ON sa.id = t.stato_a_id
                WHERE t.attivo
                  AND ('IN_ESECUZIONE' IN (sd.codice_interno, sa.codice_interno)
                       OR (sd.codice_interno = 'BOZZA' AND sa.codice_interno = 'APERTA'))),
    'false|0',
    'IN_ESECUZIONE spento, nessuna riga attiva lo nomina, BOZZA -> APERTA spento'
);

-- ── Fixture ─────────────────────────────────────────────────────────
-- Tre commesse in bozza con una riga (il builder la scrive solo se chiesta),
-- una senza: l'annullo della bozza.
CREATE TEMP TABLE t_a AS SELECT * FROM dbops.fn_pgtap_crea_commessa('commessa al modello A', NULL, NULL, true);
CREATE TEMP TABLE t_b AS SELECT * FROM dbops.fn_pgtap_crea_commessa('commessa al modello B');
CREATE TEMP TABLE t_c AS SELECT * FROM dbops.fn_pgtap_crea_commessa('commessa al modello C', NULL, NULL, true);

CREATE FUNCTION pg_temp.stato(p_id bigint) RETURNS varchar LANGUAGE sql AS $f$
    SELECT s.codice_interno FROM vendite.commesse c
      JOIN vendite.stati_commessa s ON s.id = c.stato_commessa_id WHERE c.id = p_id
$f$;

CREATE FUNCTION pg_temp.azioni(p_id bigint) RETURNS text LANGUAGE sql AS $f$
    SELECT string_agg(a ->> 'key', ' ' ORDER BY a ->> 'key')
      FROM jsonb_array_elements(script.fn_available_actions_commessa(p_id) -> 'available_actions') a
$f$;

-- 5) Permesso => nascondi
SELECT is(pg_temp.azioni((SELECT commessa_id FROM t_a)), 'annulla',
    'capability in bozza senza cambia_stato_commessa: solo «Annulla»');

-- 6) Il verbo chiede l'azione della riga
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_commessa(%s, 'PRONTA_FATTURAZIONE')$$,
           (SELECT commessa_id FROM t_a)),
    'Non hai i permessi per questa operazione%',
    '«Rendi pronta» dal verbo senza l''azione: E_PERMESSO_NEGATO'
);

-- 7) Il ponte della push non chiede l'azione del passaggio manuale (C-2)
SELECT vendite.fn_rendi_commessa_emittibile((SELECT commessa_id FROM t_c), NULL, NULL);

SELECT is(pg_temp.stato((SELECT commessa_id FROM t_c)), 'PRONTA_FATTURAZIONE'::varchar,
    'il ponte della push, senza l''azione: la commessa e'' pronta');

-- 8) L'annullo della bozza: riga senza azione (M-4)
SELECT vendite.fn_annulla_commessa((SELECT commessa_id FROM t_b), NULL);

SELECT is(pg_temp.stato((SELECT commessa_id FROM t_b)), 'ANNULLATA'::varchar,
    'l''annullo della bozza senza l''azione: ANNULLATA');

SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'cambia_stato_commessa');

-- 9) Con l'azione
SELECT is(pg_temp.azioni((SELECT commessa_id FROM t_a)), 'annulla rendi_pronta',
    'capability in bozza con cambia_stato_commessa: «Annulla» e «Rendi pronta»');

-- 10) «Rendi pronta» dal verbo. Le righe si approvano prima (la condizione
--     del passaggio, nel guard).
SELECT vendite.fn_approva_commessa_attivita((SELECT commessa_id FROM t_a), NULL, NULL);
SELECT * FROM vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM t_a), 'PRONTA_FATTURAZIONE');

SELECT is(pg_temp.stato((SELECT commessa_id FROM t_a)), 'PRONTA_FATTURAZIONE'::varchar,
    '«Rendi pronta» dal verbo: PRONTA_FATTURAZIONE');

-- 11) Lo stato che ha gia'
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_commessa(%s, 'PRONTA_FATTURAZIONE')$$,
           (SELECT commessa_id FROM t_a)),
    'Il documento è già nello stato%',
    'un secondo «Rendi pronta»: E_DOC_GIA_NELLO_STATO'
);

-- 12) «Riapri» porta ad APERTA (C-3)
SELECT * FROM vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM t_a), 'APERTA');

SELECT is(pg_temp.stato((SELECT commessa_id FROM t_a)), 'APERTA'::varchar,
    '«Riapri» dal verbo: APERTA');

-- 13) Da APERTA
SELECT is(pg_temp.azioni((SELECT commessa_id FROM t_a)), 'annulla chiudi rendi_pronta',
    'capability in APERTA: «Annulla», «Chiudi», «Rendi pronta»');

-- 14) IN_ESECUZIONE e' ritirato
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_commessa(%s, 'IN_ESECUZIONE')$$,
           (SELECT commessa_id FROM t_a)),
    'Stato di destinazione non trovato o non attivo%',
    'IN_ESECUZIONE chiesto al verbo: E_STATO_WORKFLOW_NON_TROVATO'
);

-- 15) BOZZA -> APERTA non c'e' piu'
CREATE TEMP TABLE t_d AS SELECT * FROM dbops.fn_pgtap_crea_commessa('commessa al modello D');

SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_commessa(%s, 'APERTA')$$,
           (SELECT commessa_id FROM t_d)),
    (SELECT left(m.messaggio, 20) || '%' FROM config.messaggi_errore m
      WHERE m.codice = 'E_COMMESSA_STATO_TRANSIZIONE_INVALIDA' AND m.lingua = 'it'),
    'BOZZA -> APERTA chiesto al verbo: E_COMMESSA_STATO_TRANSIZIONE_INVALIDA'
);

-- 16) La fixture: ad APERTA per «rendi pronta» e «riapri»
CREATE TEMP TABLE t_e AS SELECT * FROM dbops.fn_pgtap_crea_commessa('commessa al modello E', NULL, NULL, true);
SELECT vendite.fn_approva_commessa_attivita((SELECT commessa_id FROM t_e), NULL, NULL);
CREATE TEMP TABLE t_e_stato AS
SELECT dbops.fn_pgtap_porta_a_stato('vendite.commesse', (SELECT commessa_id FROM t_e), 'APERTA') AS stato;

SELECT is((SELECT stato FROM t_e_stato), 'APERTA',
    'la fixture porta una commessa ad APERTA dal verbo');

-- 17) L'annullo di una commessa aperta, con la conferma dei legami
CREATE TEMP TABLE t_ann AS
SELECT vendite.fn_annulla_commessa(
           (SELECT commessa_id FROM t_a),
           (SELECT count(*)::integer FROM vendite.fn_documento_legami('COMMESSA', (SELECT commessa_id FROM t_a))))
       AS legami;

SELECT is(pg_temp.stato((SELECT commessa_id FROM t_a)), 'ANNULLATA'::varchar,
    'l''annullo di una commessa aperta, confermato: ANNULLATA');

-- 18) Il ponte su una commessa gia' pronta: niente
SELECT lives_ok(
    format($$SELECT vendite.fn_commessa_proietta_stato_emittibile(%s)$$, (SELECT commessa_id FROM t_c)),
    'il ponte della push su una commessa gia'' pronta: niente da fare'
);

-- 19) Il ponte su una commessa annullata: la matrice rifiuta
SELECT throws_like(
    format($$SELECT vendite.fn_commessa_proietta_stato_emittibile(%s)$$, (SELECT commessa_id FROM t_b)),
    (SELECT left(m.messaggio, 20) || '%' FROM config.messaggi_errore m
      WHERE m.codice = 'E_COMMESSA_STATO_TRANSIZIONE_INVALIDA' AND m.lingua = 'it'),
    'il ponte della push su una commessa annullata: E_COMMESSA_STATO_TRANSIZIONE_INVALIDA'
);

-- 20) La porta
SELECT throws_like(
    format($$UPDATE vendite.commesse SET stato_commessa_id = %s WHERE id = %s$$,
           script.fn_stato_abortito_id('vendite.commesse'::regclass),
           (SELECT commessa_id FROM t_d)),
    'Lo stato del documento%si cambia solo dalle sue operazioni%',
    'UPDATE diretto dello stato della commessa: E_DOC_STATO_SOLO_DAL_VERBO'
);

SELECT * FROM finish();
ROLLBACK;
