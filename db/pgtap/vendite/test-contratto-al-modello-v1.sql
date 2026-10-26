-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il contratto sul modello del documento
--   L'azione sulla matrice del contratto (20261026-03), il guard di
--   transizione sulla matrice (-04), il verbo vendite.fn_cambia_stato_contratto
--   (-05), la cessazione con la sua data vendite.fn_cessa_contratto (-06), la
--   cessazione automatica vendite.fn_cessa_contratti_scaduti (-07) e il
--   framework che la chiama (-08), l'annullo dal verbo (-09), la porta (-10),
--   la capability (-11). Brief: brief-modello-documento-vendita §11 (giro 8;
--   Y-1 … Y-3 di Tid, 2026-10-26).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la matrice del contratto chiede emetti_contratto sull'attivazione e
--     sulla cessazione, e su nient'altro; il guard di transizione legge la
--     matrice (un passaggio spento e' rifiutato);
--   - chi non ha emetti_contratto non vede «Attiva» e il verbo glielo
--     rifiuta; l'annullo della bozza non chiede azioni;
--   - la cessazione: senza data rifiutata; data passata rifiutata (niente
--     riscrittura storica); data futura = solo la data, lo stato resta
--     ATTIVO (programmata); data di oggi = CESSATO; un contratto in bozza non
--     si cessa; un secondo «Cessa» e' lo stato che ha gia';
--   - il cambio di stato generico verso CESSATO chiede la data arrivata;
--   - il job cessa i contratti attivi scaduti dal suo verbo, attraverso il
--     framework della chiusura per scadenza; nessuna funzione legge o accende
--     piu' la GUC app.cessazione_automatica;
--   - la porta: un UPDATE diretto dello stato e' rifiutato.
--
-- ⚠️ DIPENDE DAL RUOLO (test 22): la porta chiede anche che chi scrive sia il
--   proprietario della tabella. Come applicazione (il runner) e' verde; da
--   owner (la prova dell'SQL estratto prima dell'apply) e' rosso per
--   costruzione. Per questo sta in coda.
--
-- Elenco test (plan 22):
--   1) gli oggetti: verbo, cessazione e job DEFINER, porta montata
--   2) la matrice del contratto: emetti_contratto su attivazione e cessazione
--   3) emetti_contratto a catalogo, attiva
--   4) nessuna funzione legge o accende la GUC app.cessazione_automatica
--   5) capability in bozza senza emetti_contratto: «Attiva» non c'e', «Annulla» si'
--   6) il verbo senza emetti_contratto: E_PERMESSO_NEGATO
--   7) l'annullo di una bozza senza l'azione: passa (dal verbo d'annullo)
--   8) capability con emetti_contratto: «Attiva» c'e'
--   9) il contratto attivo, costruito dal verbo
--  10) cessazione senza data: E_CONTRATTO_CESSAZIONE_SENZA_DATA
--  11) cessazione con una data passata: E_CONTRATTO_VALIDO_AL_RETROATTIVO
--  12) cessazione di una bozza: E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA
--  13) cessazione con una data futura: programmata, lo stato resta ATTIVO
--  14) ... e la data e' scritta
--  15) il cambio di stato generico verso CESSATO con la data futura: rifiutato
--  16) cessazione con la data di oggi: CESSATO
--  17) un secondo «Cessa»: E_DOC_GIA_NELLO_STATO
--  18) il job: il contratto attivo scaduto e' CESSATO, dal framework
--  19) il job: il framework conta il contratto sotto vendite.contratti
--  20) il job non tocca un contratto attivo che scade oggi
--  21) il guard legge la matrice: un passaggio spento e' rifiutato
--  22) UPDATE diretto dello stato: E_DOC_STATO_SOLO_DAL_VERBO   [rosso da owner]
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
        AND p.proname IN ('fn_cambia_stato_contratto', 'fn_cessa_contratto', 'fn_cessa_contratti_scaduti'))
    || ' porta:' || EXISTS (SELECT 1 FROM pg_trigger t
                             WHERE t.tgrelid = 'vendite.contratti'::regclass
                               AND t.tgfoid  = 'script.trgfn_doc_stato_solo_dal_verbo()'::regprocedure
                               AND NOT t.tgisinternal)::text,
    'fn_cambia_stato_contratto:true fn_cessa_contratti_scaduti:true fn_cessa_contratto:true porta:true',
    'il verbo, la cessazione e il job sono DEFINER, la porta e'' montata sul contratto'
);

-- 2) Le azioni sulla matrice del contratto (Y-1)
SELECT is(
    (SELECT string_agg(sd.codice_interno || '>' || sa.codice_interno || '=' || t.azione_processo_codename,
                       ' ' ORDER BY sd.codice_interno, sa.codice_interno)
       FROM config.transizioni_stati_contratti t
       JOIN config.stati_doc_contratti sd ON sd.id = t.stato_da_id
       JOIN config.stati_doc_contratti sa ON sa.id = t.stato_a_id
      WHERE t.azione_processo_codename IS NOT NULL),
    'ATTIVO>CESSATO=emetti_contratto DRAFT>ATTIVO=emetti_contratto',
    'la matrice del contratto: emetti_contratto sull''attivazione e sulla cessazione, nient''altro'
);

-- 3) L'azione a catalogo
SELECT ok(
    EXISTS (SELECT 1 FROM config.azioni_processo a
             WHERE a.permission_codename = 'emetti_contratto' AND a.attivo),
    'emetti_contratto e'' a catalogo, attiva'
);

-- 4) La GUC ritirata: nessuna funzione la legge o la accende (i commenti
--    che la citano come precedente non contano: si cerca la chiamata).
SELECT is(
    (SELECT string_agg(p.oid::regprocedure::text, ', ' ORDER BY 1)
       FROM pg_proc p
      WHERE p.prokind = 'f'
        AND p.pronamespace NOT IN ('pg_catalog'::regnamespace, 'information_schema'::regnamespace)
        AND pg_get_functiondef(p.oid) ~ $re$(current_setting|set_config)\(\s*'app\.cessazione_automatica'$re$),
    NULL,
    'nessuna funzione legge o accende la GUC app.cessazione_automatica'
);

-- Due contratti in bozza: il builder costruisce il cliente nell'azienda di
-- chi agisce.
CREATE TEMP TABLE t_bozza AS
SELECT * FROM dbops.fn_pgtap_crea_contratto('pgTAP contratto al modello', 'DRAFT');

CREATE TEMP TABLE t_bozza2 AS
SELECT * FROM dbops.fn_pgtap_crea_contratto('pgTAP contratto al modello bozza', 'DRAFT');

-- 5) Permesso => nascondi
SELECT is(
    (SELECT string_agg(a ->> 'key', ' ' ORDER BY a ->> 'key')
       FROM jsonb_array_elements(script.fn_available_actions_contratto((SELECT contratto_id FROM t_bozza))
                                 -> 'available_actions') a),
    'annulla',
    'capability del contratto in bozza senza emetti_contratto: «Attiva» non c''e'', «Annulla» si'''
);

-- 6) Il verbo chiede l'azione della riga
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_contratto(%s, 'ATTIVO')$$,
           (SELECT contratto_id FROM t_bozza)),
    'Non hai i permessi per questa operazione%',
    'il verbo del contratto senza emetti_contratto: E_PERMESSO_NEGATO'
);

-- 7) L'annullo della bozza: riga senza azione (M-4)
-- ⚠️ Il verbo in un'istruzione sua: una lettura nella stessa istruzione
--    vedrebbe la fotografia di prima della chiamata.
SELECT vendite.fn_annulla_contratto((SELECT contratto_id FROM t_bozza2));
SELECT is(
    (SELECT s.codice_interno::text FROM vendite.contratti c
       JOIN config.stati_doc_contratti s ON s.id = c.stato_doc_contratto_id
      WHERE c.id = (SELECT contratto_id FROM t_bozza2)),
    'ANNULLATO',
    'l''annullo di una bozza senza emetti_contratto: dal verbo d''annullo, nessuna azione'
);

SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'emetti_contratto');

-- 8) Con l'azione «Attiva» c'e'
SELECT is(
    (SELECT string_agg(a ->> 'key', ' ' ORDER BY a ->> 'key')
       FROM jsonb_array_elements(script.fn_available_actions_contratto((SELECT contratto_id FROM t_bozza))
                                 -> 'available_actions') a),
    'annulla attiva',
    'capability del contratto in bozza con emetti_contratto: «Attiva» c''e'''
);

-- 9) Il contratto attivo, dal builder: passa dal verbo (la fixture degli stati)
CREATE TEMP TABLE t_attivo AS
SELECT * FROM dbops.fn_pgtap_crea_contratto('pgTAP contratto al modello attivo', 'ATTIVO');

SELECT is(
    (SELECT s.codice_interno::text FROM vendite.contratti c
       JOIN config.stati_doc_contratti s ON s.id = c.stato_doc_contratto_id
      WHERE c.id = (SELECT contratto_id FROM t_attivo)),
    'ATTIVO',
    'il contratto attivo del builder, dal verbo attraverso la porta'
);

-- 10) La cessazione chiede la data
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cessa_contratto(%s, NULL)$$, (SELECT contratto_id FROM t_attivo)),
    'Per cessare il contratto serve la data di fine%',
    'la cessazione senza data: E_CONTRATTO_CESSAZIONE_SENZA_DATA'
);

-- 11) Niente riscrittura storica
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cessa_contratto(%s, %L::date)$$,
           (SELECT contratto_id FROM t_attivo), script.fn_data_operativa() - 1),
    'Cessazione contratto non ammessa: data fine validita''%nel passato%',
    'la cessazione con una data passata: E_CONTRATTO_VALIDO_AL_RETROATTIVO'
);

-- 12) Una bozza non si cessa, neanche programmata: la strada la dice la matrice
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cessa_contratto(%s, %L::date)$$,
           (SELECT contratto_id FROM t_bozza), script.fn_data_operativa() + 30),
    'Contratto %: transizione stato DRAFT -> CESSATO non ammessa%',
    'la cessazione di una bozza: E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA'
);

-- 13-14) La cessazione programmata: solo la data
SELECT is(
    (SELECT v.stato_precedente::text || '>' || v.stato_nuovo::text || ' programmata:' || v.programmata::text
       FROM vendite.fn_cessa_contratto((SELECT contratto_id FROM t_attivo),
                                       script.fn_data_operativa() + 30) v),
    'ATTIVO>ATTIVO programmata:true',
    'la cessazione con una data futura: programmata, lo stato resta ATTIVO'
);
SELECT is(
    (SELECT c.valido_al FROM vendite.contratti c WHERE c.id = (SELECT contratto_id FROM t_attivo)),
    script.fn_data_operativa() + 30,
    'la cessazione programmata scrive la data di fine'
);

-- 15) Il cambio di stato generico non scavalca la data: CESSATO chiede la
--     data arrivata
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_contratto(%s, 'CESSATO')$$,
           (SELECT contratto_id FROM t_attivo)),
    'Contratto %: transizione stato ATTIVO -> CESSATO non ammessa%',
    'il cambio di stato generico verso CESSATO con la data futura: E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA'
);

-- 16) La cessazione di oggi: CESSATO
SELECT is(
    (SELECT v.stato_precedente::text || '>' || v.stato_nuovo::text || ' programmata:' || v.programmata::text
       FROM vendite.fn_cessa_contratto((SELECT contratto_id FROM t_attivo),
                                       script.fn_data_operativa()) v),
    'ATTIVO>CESSATO programmata:false',
    'la cessazione con la data di oggi: CESSATO, dalla scrittura comune'
);

-- 17) Un secondo «Cessa»: lo stato che il contratto ha gia'
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cessa_contratto(%s, %L::date)$$,
           (SELECT contratto_id FROM t_attivo), script.fn_data_operativa()),
    'Il documento è già nello stato CESSATO%',
    'un secondo «Cessa»: E_DOC_GIA_NELLO_STATO'
);

-- 18-20) Il job. Un contratto attivo che e' scaduto ieri, e uno che scade
--        oggi: il primo lo cessa, il secondo no.
CREATE TEMP TABLE t_scaduto AS
SELECT * FROM dbops.fn_pgtap_crea_contratto('pgTAP contratto al modello scaduto', 'ATTIVO',
                                            p_valido_dal => script.fn_data_operativa() - 60,
                                            p_valido_al  => script.fn_data_operativa() - 1);
CREATE TEMP TABLE t_oggi AS
SELECT * FROM dbops.fn_pgtap_crea_contratto('pgTAP contratto al modello oggi', 'ATTIVO',
                                            p_valido_dal => script.fn_data_operativa() - 60,
                                            p_valido_al  => script.fn_data_operativa());

CREATE TEMP TABLE t_job AS
SELECT dbops.fn_apply_chiusura_scadenze() AS esito;

SELECT is(
    (SELECT s.codice_interno::text FROM vendite.contratti c
       JOIN config.stati_doc_contratti s ON s.id = c.stato_doc_contratto_id
      WHERE c.id = (SELECT contratto_id FROM t_scaduto)),
    'CESSATO',
    'il job: il contratto attivo scaduto e'' CESSATO, dal suo verbo attraverso il framework'
);
SELECT ok(
    (SELECT (esito ->> 'vendite.contratti')::integer >= 1 FROM t_job),
    'il job: il framework conta i contratti cessati sotto vendite.contratti'
);
SELECT is(
    (SELECT s.codice_interno::text FROM vendite.contratti c
       JOIN config.stati_doc_contratti s ON s.id = c.stato_doc_contratto_id
      WHERE c.id = (SELECT contratto_id FROM t_oggi)),
    'ATTIVO',
    'il job non cessa un contratto che scade oggi'
);

-- 21) Il guard legge la matrice: spento DRAFT -> ANNULLATO nella tabella,
--     l'annullo della bozza e' rifiutato (prima i passaggi erano negli IF).
UPDATE config.transizioni_stati_contratti t
   SET attivo = false
 WHERE t.stato_da_id = script.fn_doc_stato_id('vendite.contratti'::regclass, 'DRAFT')
   AND t.stato_a_id  = script.fn_stato_abortito_id('vendite.contratti'::regclass);
SELECT throws_like(
    format($$SELECT vendite.fn_annulla_contratto(%s)$$, (SELECT contratto_id FROM t_bozza)),
    'Contratto %: transizione stato DRAFT -> ANNULLATO non ammessa%',
    'il guard legge la matrice: un passaggio spento e'' rifiutato'
);

-- 22) [rosso da owner] Un UPDATE diretto dello stato, anche con la GUC accesa
--     dall'applicazione: la porta chiede anche il proprietario.
SELECT set_config('zeroerp.doc_cambio_stato',
                  'vendite.contratti'::regclass::oid::text || ':' || (SELECT contratto_id FROM t_oggi)::text,
                  true);
SELECT throws_like(
    format($$UPDATE vendite.contratti SET stato_doc_contratto_id = %s WHERE id = %s$$,
           script.fn_doc_stato_id('vendite.contratti'::regclass, 'CESSATO'), (SELECT contratto_id FROM t_oggi)),
    '%si cambia solo dalle sue operazioni%',
    'un UPDATE diretto dello stato del contratto, anche con la GUC accesa: E_DOC_STATO_SOLO_DAL_VERBO [rosso da owner]'
);
SELECT set_config('zeroerp.doc_cambio_stato', '', true);

SELECT * FROM finish();
ROLLBACK;
