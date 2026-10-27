-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la fattura e il lotto sul modello del documento
--   L'azione sulla matrice fiscale (20261027-01, CSV), il vocabolario e la
--   matrice dello stato del job (-02 … -05) col suo guard (-06), la funzione
--   morta ritirata (-07), il verbo del lotto (-08), i verbi di processo di
--   lotto e fattura (-09, -10), le madri riporta in bozza e annullo (-14,
--   -15), le porte (-17, -18), la capability (-19), la fixture (-20).
--   Brief: brief-modello-documento-vendita §15 (giro 11; F-1 … F-4, Q-F1 …
--   Q-F4, P-1, P-2 di Tid, 2026-10-27).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - «numera» e «riporta in bozza» del lotto chiedono numera_fatture_lotti;
--     l'annullo della bozza nessuna azione (Q-F1, Q-F2); le righe della
--     fattura sono tutte di processo;
--   - chi non ha l'azione non vede i bottoni e il verbo glieli rifiuta;
--   - il giro della pipeline porta il lotto solo negli stati dei suoi step,
--     mai allo stato iniziale (P-2: senza la prima riga del verbo);
--   - lo stato del job ha i passaggi dalla matrice: COMPLETATO -> ERRORE si'
--     (Tid, 2026-08-24), ERRORE -> COMPLETATO no; la colonna e' legata al
--     vocabolario (P-1);
--   - le porte: un UPDATE diretto dello stato di lotto o fattura e' rifiutato.
--
-- ⚠️ Prova pre-apply: il test 4 (le quattro azioni ritirate) legge il CSV
--   di azioni_processo, che l'SQL estratto non carica: e' verde solo dopo il
--   migrate.
--
-- Elenco test (plan 22):
--   1) gli oggetti: tre verbi DEFINER, porta su lotto e fattura
--   2) la matrice: numera_fatture_lotti su numera e riporta in bozza, nient'altro
--   3) i passaggi manuali: i tre del lotto; nessuno della fattura
--   4) le azioni ritirate: genera_fattura, approva_fattura, emetti_fattura, reset_lotto_draft
--   5) lo stato del job: tre stati, cinque passaggi, COMPLETATO -> ERRORE si', ERRORE -> COMPLETATO no
--   6) la colonna del job: FK sul codice, il CHECK ritirato
--   7) la funzione morta non c'e' piu'
--   8) capability del lotto in bozza senza l'azione: solo «annulla»
--   9) capability del lotto emesso senza l'azione: nessun bottone
--  10) il verbo senza l'azione: E_PERMESSO_NEGATO
--  11) capability del lotto emesso con l'azione: «numera», «riporta_a_draft»
--  12) «riporta in bozza» con l'azione: DRAFT
--  13) «riporta in bozza» su un lotto gia' in bozza: niente da fare, DRAFT
--  14) il verbo verso lo stato che ha gia': E_DOC_GIA_NELLO_STATO
--  15) il verbo su un passaggio di processo: E_DOC_PASSAGGIO_DI_PROCESSO
--  16) il giro porta il lotto allo step EMESSA
--  17) il giro verso lo stato iniziale: rifiutato
--  18) il giro verso uno stato che non e' uno step: rifiutato
--  19) l'annullo della bozza: ANNULLATA
--  20) UPDATE diretto dello stato del lotto: E_DOC_STATO_SOLO_DAL_VERBO
--  21) UPDATE diretto dello stato della fattura: E_DOC_STATO_SOLO_DAL_VERBO
--  22) lo stato del job dal guard: IN_ESECUZIONE -> COMPLETATO -> ERRORE, poi ERRORE -> COMPLETATO rifiutato
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(22);

-- 1) Gli oggetti e la loro forma
SELECT is(
    (SELECT string_agg(p.proname || ':' || p.prosecdef::text, ' ' ORDER BY p.proname)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite'
        AND p.proname IN ('fn_cambia_stato_lotto', 'fn_lotto_proietta_stato_step',
                          'fn_fattura_proietta_stato'))
    || ' porte:' || (SELECT count(*) FROM pg_trigger t
                      WHERE t.tgrelid IN ('vendite.fatture'::regclass, 'vendite.fatturazione_lotti'::regclass)
                        AND t.tgfoid = 'script.trgfn_doc_stato_solo_dal_verbo()'::regprocedure
                        AND NOT t.tgisinternal)::text,
    'fn_cambia_stato_lotto:true fn_fattura_proietta_stato:true fn_lotto_proietta_stato_step:true porte:2',
    'i tre verbi sono DEFINER, la porta e'' montata su lotto e fattura'
);

-- 2) Le azioni sulla matrice fiscale (Q-F1, Q-F2)
SELECT is(
    (SELECT string_agg(sd.codice_interno || '>' || sa.codice_interno || '=' || t.azione_processo_codename,
                       ' ' ORDER BY sd.codice_interno, sa.codice_interno)
       FROM config.stati_doc_fiscale_transizioni t
       JOIN config.stati_doc_fiscale sd ON sd.id = t.stato_from_id
       JOIN config.stati_doc_fiscale sa ON sa.id = t.stato_to_id
      WHERE t.ammesso AND t.azione_processo_codename IS NOT NULL),
    'EMESSA>DEFINITIVA=numera_fatture_lotti EMESSA>DRAFT=numera_fatture_lotti',
    'la matrice: numera_fatture_lotti su numera e riporta in bozza, nient''altro'
);

-- 3) I passaggi manuali, letti dal lettore unico
SELECT is(
    (SELECT string_agg(sd.codice_interno || '>' || sa.codice_interno, ' '
                       ORDER BY sd.codice_interno, sa.codice_interno)
       FROM config.stati_doc_fiscale_transizioni t
       JOIN config.stati_doc_fiscale sd ON sd.id = t.stato_from_id
       JOIN config.stati_doc_fiscale sa ON sa.id = t.stato_to_id
       CROSS JOIN LATERAL script.fn_doc_passaggio(
           CASE WHEN t.solo_fattura THEN 'vendite.fatture'::regclass
                ELSE 'vendite.fatturazione_lotti'::regclass END,
           t.stato_from_id, t.stato_to_id) pz
      WHERE t.ammesso AND pz.manuale IS TRUE),
    'DRAFT>ANNULLATA EMESSA>DEFINITIVA EMESSA>DRAFT',
    'manuali i tre passaggi del lotto (annulla, numera, riporta in bozza); nessuno della fattura'
);

-- 4) Le azioni ritirate (F-2, Q-F1). ⚠️ Verde solo dopo il migrate (CSV).
SELECT is(
    (SELECT string_agg(a.permission_codename || ':' || a.attivo::text, ' ' ORDER BY a.permission_codename)
       FROM config.azioni_processo a
      WHERE a.permission_codename IN ('genera_fattura', 'approva_fattura', 'emetti_fattura',
                                      'reset_lotto_draft', 'numera_fatture_lotti')),
    'approva_fattura:false emetti_fattura:false genera_fattura:false numera_fatture_lotti:true reset_lotto_draft:false',
    'le quattro azioni ritirate sono spente, numera_fatture_lotti resta'
);

-- 5) Lo stato del job: vocabolario e matrice (F-4, Q-F4)
SELECT is(
    (SELECT string_agg(s.codice_interno, ' ' ORDER BY s.ordine) FROM config.stati_lotto_job s WHERE s.attivo)
    || ' | ' ||
    (SELECT string_agg(sd.codice_interno || '>' || sa.codice_interno, ' '
                       ORDER BY sd.codice_interno, sa.codice_interno)
       FROM config.transizioni_stati_lotto_job t
       JOIN config.stati_lotto_job sd ON sd.id = t.stato_da_id
       JOIN config.stati_lotto_job sa ON sa.id = t.stato_a_id
      WHERE t.attivo),
    'IN_ESECUZIONE COMPLETATO ERRORE | COMPLETATO>ERRORE COMPLETATO>IN_ESECUZIONE '
    'ERRORE>IN_ESECUZIONE IN_ESECUZIONE>COMPLETATO IN_ESECUZIONE>ERRORE',
    'lo stato del job: tre stati, i cinque passaggi del backend (COMPLETATO -> ERRORE si'', ERRORE -> COMPLETATO no)'
);

-- 6) La colonna del job legata al vocabolario (P-1)
SELECT is(
    (SELECT string_agg(c.conname, ' ' ORDER BY c.conname)
       FROM pg_constraint c
      WHERE c.conrelid = 'vendite.fatturazione_lotti'::regclass
        AND c.conname IN ('fk_fatturazione_lotti_stato_lotto', 'chk_fatturazione_lotti_stato_job')),
    'fk_fatturazione_lotti_stato_lotto',
    'stato_lotto ha la FK sul codice del vocabolario; il CHECK e'' ritirato'
);

-- 7) La seconda copia della regola non c'e' piu'
SELECT hasnt_function('vendite', 'fn_set_fatturazione_lotto_stato',
    'vendite.fn_set_fatturazione_lotto_stato e'' ritirata');

-- ── Fixture ─────────────────────────────────────────────────────────
-- Lotti VUOTI (il builder non scrive fatture): uno in bozza, uno emesso,
-- uno per lo stato del job. La fattura, a parte, emessa.
CREATE TEMP TABLE t_draft AS SELECT * FROM dbops.fn_pgtap_crea_lotto('lotto al modello bozza');
CREATE TEMP TABLE t_emesso AS SELECT * FROM dbops.fn_pgtap_crea_lotto('lotto al modello emesso', 'EMESSA');
CREATE TEMP TABLE t_job AS SELECT * FROM dbops.fn_pgtap_crea_lotto('lotto al modello job');
CREATE TEMP TABLE t_fattura AS SELECT * FROM dbops.fn_pgtap_crea_fattura('fattura al modello', 'EMESSA');

CREATE FUNCTION pg_temp.stato(p_id bigint) RETURNS varchar LANGUAGE sql AS $f$
    SELECT s.codice_interno FROM vendite.fatturazione_lotti l
      JOIN config.stati_doc_fiscale s ON s.id = l.stato_doc_fiscale_id WHERE l.id = p_id
$f$;

CREATE FUNCTION pg_temp.azioni(p_id bigint) RETURNS text LANGUAGE sql AS $f$
    SELECT COALESCE(string_agg(a ->> 'key', ' ' ORDER BY a ->> 'key'), '')
      FROM jsonb_array_elements(script.fn_available_actions_lotto(p_id) -> 'available_actions') a
$f$;

-- 8) Permesso => nascondi: l'annullo della bozza non chiede azioni
SELECT is(pg_temp.azioni((SELECT lotto_id FROM t_draft)), 'annulla',
    'capability del lotto in bozza senza numera_fatture_lotti: solo «annulla»');

-- 9) Il lotto emesso senza l'azione: nessun bottone
SELECT is(pg_temp.azioni((SELECT lotto_id FROM t_emesso)), '',
    'capability del lotto emesso senza numera_fatture_lotti: «numera» e «riporta in bozza» nascosti');

-- 10) Il verbo chiede l'azione della riga
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_lotto(%s, 'DRAFT')$$, (SELECT lotto_id FROM t_emesso)),
    'Non hai i permessi per questa operazione%',
    '«riporta in bozza» dal verbo senza l''azione: E_PERMESSO_NEGATO'
);

SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'numera_fatture_lotti');

-- 11) Con l'azione i bottoni ci sono
SELECT is(pg_temp.azioni((SELECT lotto_id FROM t_emesso)), 'numera riporta_a_draft',
    'capability del lotto emesso con numera_fatture_lotti: «numera» e «riporta in bozza»');

-- 12) La madre «riporta in bozza» col verbo
SELECT is(
    (SELECT pg_temp.stato(l.lotto_id)
       FROM t_emesso l, LATERAL vendite.fn_riporta_lotto_a_draft(l.lotto_id) r),
    'DRAFT',
    '«riporta in bozza» con l''azione: il lotto torna in DRAFT'
);

-- 13) Su un lotto gia' in bozza non c'e' passaggio: la sola pulizia
SELECT is(
    (SELECT pg_temp.stato(l.lotto_id)
       FROM t_emesso l, LATERAL vendite.fn_riporta_lotto_a_draft(l.lotto_id) r),
    'DRAFT',
    '«riporta in bozza» su un lotto gia'' in bozza: nessun errore, resta DRAFT'
);

-- 14) Lo stato che ha gia'
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_lotto(%s, 'DRAFT')$$, (SELECT lotto_id FROM t_draft)),
    'Il documento è già nello stato%',
    'il verbo verso lo stato che il lotto ha gia'': E_DOC_GIA_NELLO_STATO'
);

-- 15) Il passaggio di processo non si chiede a mano
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_lotto(%s, 'EMESSA')$$, (SELECT lotto_id FROM t_draft)),
    'Questo passaggio di stato lo fa il sistema%',
    'DRAFT -> EMESSA chiesto al verbo: E_DOC_PASSAGGIO_DI_PROCESSO'
);

-- 16) Il giro porta il lotto allo step
SELECT vendite.fn_lotto_proietta_stato_step(
    (SELECT lotto_id FROM t_emesso),
    (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno = 'EMESSA'));
SELECT is(pg_temp.stato((SELECT lotto_id FROM t_emesso)), 'EMESSA',
    'il giro della pipeline porta il lotto allo step EMESSA');

-- 17) Il giro non riporta allo stato iniziale (quello e' «riporta in bozza»)
SELECT throws_like(
    format($$SELECT vendite.fn_lotto_proietta_stato_step(%s, %s)$$,
           (SELECT lotto_id FROM t_emesso),
           (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.iniziale)),
    'Parametro non coerente con lotto esistente%',
    'il giro verso lo stato iniziale: E_LOTTO_PARAMETRO_NON_COERENTE'
);

-- 18) Il giro porta solo negli stati dei suoi step
SELECT throws_like(
    format($$SELECT vendite.fn_lotto_proietta_stato_step(%s, %s)$$,
           (SELECT lotto_id FROM t_draft),
           script.fn_stato_abortito_id('vendite.fatturazione_lotti'::regclass)),
    'Parametro non coerente con lotto esistente%',
    'il giro verso uno stato che non e'' uno step (l''annullo): E_LOTTO_PARAMETRO_NON_COERENTE'
);

-- 19) L'annullo della bozza: la madre col verbo, senza azione (Q-F2)
SELECT is(
    (SELECT pg_temp.stato(l.lotto_id)
       FROM t_draft l, LATERAL vendite.fn_annulla_lotto_da_draft(l.lotto_id) r),
    'ANNULLATA',
    'l''annullo del lotto in bozza: ANNULLATA'
);

-- 20) La porta del lotto
SELECT throws_like(
    format($$UPDATE vendite.fatturazione_lotti SET stato_doc_fiscale_id = %s WHERE id = %s$$,
           (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.iniziale),
           (SELECT lotto_id FROM t_emesso)),
    'Lo stato del documento%',
    'UPDATE diretto dello stato del lotto: E_DOC_STATO_SOLO_DAL_VERBO'
);

-- 21) La porta della fattura
SELECT throws_like(
    format($$UPDATE vendite.fatture SET stato_doc_fiscale_id = %s WHERE id = %s$$,
           (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno = 'INVIATA'),
           (SELECT fattura_id FROM t_fattura)),
    'Lo stato del documento%',
    'UPDATE diretto dello stato della fattura: E_DOC_STATO_SOLO_DAL_VERBO'
);

-- 22) Lo stato del job dalla matrice: avanti si', ERRORE -> COMPLETATO no
UPDATE vendite.fatturazione_lotti SET stato_lotto = 'COMPLETATO' WHERE id = (SELECT lotto_id FROM t_job);
UPDATE vendite.fatturazione_lotti SET stato_lotto = 'ERRORE' WHERE id = (SELECT lotto_id FROM t_job);
SELECT throws_like(
    format($$UPDATE vendite.fatturazione_lotti SET stato_lotto = 'COMPLETATO' WHERE id = %s$$,
           (SELECT lotto_id FROM t_job)),
    'Parametro non coerente con lotto esistente%',
    'stato del job: IN_ESECUZIONE -> COMPLETATO -> ERRORE ammessi, ERRORE -> COMPLETATO rifiutato'
);

SELECT * FROM finish();
ROLLBACK;
