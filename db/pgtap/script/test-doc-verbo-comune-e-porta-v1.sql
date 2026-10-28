-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-27 (brief-modello-documento-vendita §15, giro 11): fattura e lotto sono portati al
--   modello. Test 9 e 10: la porta anche su fattura e lotto, nove testate. Test 8: con la fattura
--   non resta nella mappa un documento senza la colonna dell'azione; il documento «non ancora
--   portato» e' l'ordine d'acquisto, fuori mappa (stesso rifiuto, E_SCRIPT_CHIAMATA_NON_VALIDA).
-- ⚠️ Attesa cambiata: test 9 (la lista dichiarata + vendite.fatture, vendite.fatturazione_lotti),
--   test 10 (il conteggio 7 -> 9) e il soggetto del test 8, perche' il giro 11 monta le porte
--   (20261027-17, -18) e mette la colonna sulla matrice fiscale (20261027-01).
-- rev 2026-10-26 (brief-modello-documento-vendita §14, giro 10): la commessa e' portata al modello. Test 9 e
--   10: la porta anche sulla commessa, sette testate.
-- ⚠️ Attesa cambiata: test 9 (la lista dichiarata + vendite.commesse) e 10 (il conteggio 6 -> 7),
--   perche' il giro 10 monta la porta sulla commessa (20261026-34).
-- rev 2026-10-26 (brief-modello-documento-vendita §13, giro 9): l'offerta e' portata al modello. Test 9 e
--   10: la porta anche sull'offerta, sei testate.
-- ⚠️ Attesa cambiata: test 9 (la lista dichiarata + vendite.offerte_commerciali) e 10 (il conteggio
--   5 -> 6), perche' il giro 9 monta la porta sull'offerta (20261026-26).
-- rev 2026-10-26 (brief-modello-documento-vendita §11, giro 8): il contratto e' portato al modello. Test 9 e
--   10: la porta anche sul contratto, cinque testate (attese cambiate: la lista dichiarata e il
--   conteggio 4 -> 5).
-- rev 2026-10-26 (brief-modello-documento-vendita §9.10): test 19-22 nuovi, lo stato che il documento
--   ha gia' (20261026-01) e lo stato sconosciuto della bolla (20261026-02); i due rossi da owner
--   passano da 19-20 a 23-24 (restano in coda).
-- rev 2026-10-25 (brief-modello-documento-vendita §9): l'ordine e' portato al modello. Test 8:
--   il documento non ancora portato e' ora la fattura (portata per ultima fra i documenti della
--   mappa; prima era l'ordine). Test 9 e 10: la porta anche sull'ordine, quattro testate (attese
--   cambiate: la lista dichiarata e il conteggio 3 -> 4).
-- pgTAP test per Zero ERP
--
-- Test: il verbo comune di stato e la porta (bolla e reso)
--   BB script.fn_doc_stato_modello (20261025-07), colonna
--   azione_processo_codename sulle matrici (20261025-08), script.fn_doc_passaggio
--   (-09), script.fn_guard_passaggio (-10), script.fn_doc_scrivi_stato (-11), la
--   porta script.trgfn_doc_stato_solo_dal_verbo (-12) montata su bolla e reso
--   (-13); i verbi di bolla e reso sul verbo comune (-16 … -18); le capability
--   (-20, -21). Brief: brief-modello-documento-vendita §7 (M-1, M-3, M-4, S-1 b,
--   S-2 a, T-3, T-4 di Tid, 2026-10-24/25).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la mappa dice colonna di stato e matrice di una testata; nessuna riga per
--     una tabella che non e' un documento;
--   - l'azione che un passaggio chiede sta sulla sua riga (bolla: emetti_ddt
--     su emissione e annullo dell'emesso; reso: conferma_reso su conferma e
--     annullo del confermato); il lettore unico la rende, e dice se la riga e'
--     di processo;
--   - la porta e' montata su ogni testata il cui verbo scrive con la scrittura
--     comune (oggi bolla e reso: la lista e' dichiarata, un documento per
--     giro), BEFORE UPDATE OF la colonna di stato della mappa;
--   - un UPDATE diretto dello stato e' rifiutato (E_DOC_STATO_SOLO_DAL_VERBO);
--     uno che riscrive lo stesso stato passa;
--   - il verbo chiede l'azione della riga (E_PERMESSO_NEGATO senza), rifiuta i
--     passaggi di processo (E_DOC_PASSAGGIO_DI_PROCESSO), e con l'azione
--     emette; una riga senza azione (annullo di un reso in bozza, M-4) passa;
--   - la capability nasconde il passaggio con l'azione a chi non ce l'ha;
--   - il verbo chiesto con lo stato che il documento ha gia' (la matrice non ha
--     X -> X) e' rifiutato dalla prima riga, E_DOC_GIA_NELLO_STATO, prima dei
--     controlli del verbo; un UPDATE che riscrive lo stesso stato resta lecito
--     (la regola e' del verbo);
--   - uno stato che il vocabolario della bolla non ha: E_STATO_WORKFLOW_NON_TROVATO,
--     come i verbi di ordine e preventivo.
--
-- ⚠️ DIPENDE DAL RUOLO (test 23 e 24): la porta chiede anche che chi scrive sia
--   il proprietario della tabella. Come applicazione (il runner) sono verdi; da
--   owner (la prova dell'SQL estratto prima dell'apply) l'owner E' il
--   proprietario e la sola GUC apre: rossi da owner per costruzione. Per
--   questo stanno in coda.
--
-- rev 2026-10-25 (giro 6, brief §8): test 9 e 10 con il preventivo, che ha la porta.
-- rev 2026-10-25: test 2 e 9 confrontano regclass, non il loro testo (dipende dal
--   search_path: come app il test 2 era rosso, «transizioni_stati_ddt» senza schema).
--
-- Elenco test (plan 24):
--   1) i cinque BB esistono
--   2) la mappa: bolla -> stato_doc_ddt_id, config.transizioni_stati_ddt
--   3) la mappa: una tabella che non e' un documento -> nessuna riga
--   4) la colonna dell'azione sulle due matrici, FK verso il codename del catalogo
--   5) le azioni seminate: bolla emetti_ddt su 1->2 e 2->6, reso conferma_reso
--      su 1->2 e 2->3, nessun'altra riga con un'azione
--   6) il lettore: DRAFT->EMESSO manuale con emetti_ddt; CONSEGNATO->RESO di processo
--   7) il lettore: un passaggio fuori matrice -> nessuna riga
--   8) il lettore su un documento non ancora portato al modello: chiamata non valida
--   9) montaggio della porta: bolla, reso, preventivo (giro 6), ordine (giro 7), contratto (giro 8), offerta (giro 9), commessa (giro 10), fattura e lotto (giro 11), e nessun'altra testata
--  10) montaggio della porta: BEFORE UPDATE OF la colonna di stato della mappa
--  11) le due porte del registro ritirate (E_DDT_/E_RESO_STATO_SOLO_DA_VERBO
--      obsoleti, nessuna funzione li solleva piu')
--  12) capability della bolla in bozza: senza emetti_ddt «Emetti» non c'e'
--  13) il verbo della bolla senza emetti_ddt: E_PERMESSO_NEGATO
--  14) conferma del reso senza conferma_reso: E_PERMESSO_NEGATO
--  15) annullo di un reso in bozza senza azione: passa (M-4)
--  16) capability della bolla: con emetti_ddt «Emetti» c'e'
--  17) il verbo con emetti_ddt emette la bolla
--  18) un passaggio di processo chiesto al verbo: E_DOC_PASSAGGIO_DI_PROCESSO
--  19) il secondo «Emetti» della bolla: E_DOC_GIA_NELLO_STATO
--  20) il secondo annullo del reso: E_DOC_GIA_NELLO_STATO, prima del controllo
--      dello stato del reso
--  21) un UPDATE che riscrive lo stesso stato della bolla: passa
--  22) il verbo della bolla con uno stato che non c'e': E_STATO_WORKFLOW_NON_TROVATO
--  23) UPDATE diretto dello stato della bolla: E_DOC_STATO_SOLO_DAL_VERBO
--      (anche con la GUC accesa dall'applicazione)          [rosso da owner]
--  24) la scrittura comune chiamata dall'applicazione: la porta la ferma
--                                                          [rosso da owner]
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(24);

-- 1) Gli oggetti
SELECT is(
    (SELECT count(*)::integer FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script'
        AND p.proname IN ('fn_doc_stato_modello', 'fn_doc_passaggio', 'fn_guard_passaggio',
                          'fn_doc_scrivi_stato', 'trgfn_doc_stato_solo_dal_verbo')),
    5,
    'i cinque BB del verbo comune e della porta esistono'
);

-- 2-3) La mappa
-- ⚠️ regclass confrontati come regclass: il loro testo dipende dal
-- search_path di chi esegue (come app `config` ci sta, e lo schema sparisce).
SELECT ok(
    (SELECT m.colonna_stato = 'stato_doc_ddt_id'
            AND m.matrice = 'config.transizioni_stati_ddt'::regclass
       FROM script.fn_doc_stato_modello('vendite.ddt'::regclass) m),
    'la mappa: la bolla ha lo stato in stato_doc_ddt_id e i passaggi in config.transizioni_stati_ddt'
);

SELECT is(
    (SELECT count(*)::integer FROM script.fn_doc_stato_modello('config.sorgenti'::regclass)),
    0,
    'la mappa: una tabella che non e'' un documento non ha righe'
);

-- 4) La colonna dell'azione, FK verso la chiave stabile del catalogo
SELECT is(
    (SELECT count(*)::integer
       FROM pg_constraint c
       JOIN pg_attribute a  ON a.attrelid = c.conrelid  AND a.attnum = c.conkey[1]
       JOIN pg_attribute ar ON ar.attrelid = c.confrelid AND ar.attnum = c.confkey[1]
      WHERE c.contype = 'f'
        AND c.conrelid IN ('config.transizioni_stati_ddt'::regclass, 'config.transizioni_stati_reso'::regclass)
        AND a.attname = 'azione_processo_codename'
        AND c.confrelid = 'config.azioni_processo'::regclass
        AND ar.attname = 'permission_codename'),
    2,
    'le matrici di bolla e reso hanno azione_processo_codename, FK verso config.azioni_processo.permission_codename'
);

-- 5) Le azioni seminate (M-3, M-4): una per documento, sui passaggi pesanti
SELECT is(
    (SELECT string_agg(x, ' ' ORDER BY x) FROM (
        SELECT 'ddt:' || sd.codice_interno || '>' || sa.codice_interno || '=' || t.azione_processo_codename AS x
          FROM config.transizioni_stati_ddt t
          JOIN config.stati_doc_ddt sd ON sd.id = t.stato_da_id
          JOIN config.stati_doc_ddt sa ON sa.id = t.stato_a_id
         WHERE t.azione_processo_codename IS NOT NULL
        UNION ALL
        SELECT 'reso:' || sd.codice_interno || '>' || sa.codice_interno || '=' || t.azione_processo_codename
          FROM config.transizioni_stati_reso t
          JOIN config.stati_doc_reso sd ON sd.id = t.stato_da_id
          JOIN config.stati_doc_reso sa ON sa.id = t.stato_a_id
         WHERE t.azione_processo_codename IS NOT NULL) z),
    'ddt:DRAFT>EMESSO=emetti_ddt ddt:EMESSO>ANNULLATO=emetti_ddt reso:CONFERMATO>ANNULLATO=conferma_reso reso:DRAFT>CONFERMATO=conferma_reso',
    'le azioni sulle righe: emetti_ddt su emissione e annullo dell''emesso, conferma_reso su conferma e annullo del confermato, nient''altro'
);

-- Gli id degli stati della bolla, per codice.
CREATE TEMP TABLE t_st AS
SELECT s.codice_interno::text AS cod, s.id FROM config.stati_doc_ddt s;

-- 6) Il lettore unico
SELECT is(
    (SELECT p.manuale::text || ' ' || COALESCE(p.azione_processo_codename, '-')
       FROM script.fn_doc_passaggio('vendite.ddt'::regclass,
                                    (SELECT id FROM t_st WHERE cod = 'DRAFT'),
                                    (SELECT id FROM t_st WHERE cod = 'EMESSO')) p)
    || ' / ' ||
    (SELECT p.manuale::text || ' ' || COALESCE(p.azione_processo_codename, '-')
       FROM script.fn_doc_passaggio('vendite.ddt'::regclass,
                                    (SELECT id FROM t_st WHERE cod = 'CONSEGNATO'),
                                    (SELECT id FROM t_st WHERE cod = 'RESO')) p),
    'true emetti_ddt / false -',
    'il lettore: DRAFT->EMESSO e'' manuale e chiede emetti_ddt; CONSEGNATO->RESO e'' di processo'
);

-- 7) Fuori matrice
SELECT is(
    (SELECT count(*)::integer
       FROM script.fn_doc_passaggio('vendite.ddt'::regclass,
                                    (SELECT id FROM t_st WHERE cod = 'DRAFT'),
                                    (SELECT id FROM t_st WHERE cod = 'CONSEGNATO'))),
    0,
    'il lettore: un passaggio che la matrice non ha (DRAFT->CONSEGNATO) non ha righe'
);

-- 8) Un documento non ancora portato al modello. Dal giro 11 ogni testata della mappa
--    ha la colonna dell'azione: il ramo «matrice senza la colonna» resta difesa
--    dichiarata, e il documento non ancora portato e' l'ordine d'acquisto, fuori
--    mappa (acquisti arriva al modello col suo cantiere, W-1), con lo stesso rifiuto.
SELECT throws_like(
    $$SELECT * FROM script.fn_doc_passaggio('acquisti.ordini'::regclass, 1, 2)$$,
    'Chiamata non valida a script.fn_doc_passaggio%',
    'il lettore su un documento non ancora portato al modello: chiamata non valida'
);

-- 9-10) Il montaggio della porta, dal catalogo
CREATE TEMP TABLE t_porta AS
SELECT g.tgrelid::regclass AS tab, g.tgname::text AS nome,
       pg_get_triggerdef(g.oid) AS def
  FROM pg_trigger g
 WHERE g.tgfoid = 'script.trgfn_doc_stato_solo_dal_verbo()'::regprocedure
   AND NOT g.tgisinternal;

-- ⚠️ La lista e' dichiarata, non ricavata: il modello si porta un documento
-- per giro (M-1). Il documento del giro dopo la allunga qui.
SELECT is(
    (SELECT array_agg(tab::oid ORDER BY tab::oid) FROM t_porta),
    (SELECT array_agg(x::oid ORDER BY x::oid)
       FROM unnest(ARRAY['vendite.ddt'::regclass, 'vendite.resi'::regclass,
                         'vendite.preventivi'::regclass, 'vendite.ordini'::regclass,
                         'vendite.contratti'::regclass, 'vendite.offerte_commerciali'::regclass,
                         'vendite.commesse'::regclass, 'vendite.fatture'::regclass,
                         'vendite.fatturazione_lotti'::regclass]) x),
    'la porta e'' montata su bolla, reso, preventivo, ordine, contratto, offerta, commessa, fattura e lotto, e su nessun''altra testata'
);

SELECT is(
    (SELECT count(*)::integer
       FROM t_porta p
       JOIN LATERAL script.fn_doc_stato_modello(p.tab) m ON true
      WHERE p.def LIKE '%BEFORE UPDATE OF ' || m.colonna_stato || ' ON %'
        AND p.def LIKE '%FOR EACH ROW%'
        AND p.nome LIKE 'trg\_%\_a05\_stato\_solo\_dal\_verbo\_upd'),
    9,
    'la porta: BEFORE UPDATE OF la colonna di stato della mappa, per riga, fascia _a05_'
);

-- 11) Le due copie ritirate: codici obsoleti e nessuna funzione li solleva
SELECT is(
    (SELECT count(*)::integer FROM config.codici_errore c
      WHERE c.codice IN ('E_DDT_STATO_SOLO_DA_VERBO', 'E_RESO_STATO_SOLO_DA_VERBO')
        AND c.obsoleto_dal IS NOT NULL)
    + (SELECT count(*)::integer FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname IN ('vendite', 'script')
          AND p.prokind = 'f'
          AND (pg_get_functiondef(p.oid) LIKE '%''E_DDT_STATO_SOLO_DA_VERBO''%'
               OR pg_get_functiondef(p.oid) LIKE '%''E_RESO_STATO_SOLO_DA_VERBO''%')),
    2,
    'le porte del registro di bolla e reso sono ritirate: codici obsoleti, nessuna funzione li solleva'
);

-- La bolla in bozza dalla strada vera (ordine confermato, bolla dalla madre).
-- In DRAFT il builder non fa passaggi: nessuna azione concessa.
CREATE TEMP TABLE t_bolla AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('verbo comune', 'DRAFT');

-- 12) Permesso => nascondi: chi non ha emetti_ddt non vede «Emetti»
SELECT is(
    (SELECT count(*)::integer
       FROM jsonb_array_elements(script.fn_available_actions_ddt((SELECT ddt_id FROM t_bolla)) -> 'available_actions') a
      WHERE a ->> 'target_state' = 'EMESSO'),
    0,
    'capability della bolla in bozza: senza emetti_ddt il passaggio a EMESSO non c''e'''
);

-- 13) Il verbo chiede l'azione della riga
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_ddt(%s, 'EMESSO')$$, (SELECT ddt_id FROM t_bolla)),
    'Non hai i permessi per questa operazione%',
    'il verbo della bolla senza emetti_ddt: E_PERMESSO_NEGATO'
);

-- Un reso in bozza su una bolla consegnata. ⚠️ Il builder della bolla
-- consegnata passa da fn_pgtap_porta_a_stato, che CONCEDE emetti_ddt
-- all'operatore: da qui in poi l'operatore ce l'ha. conferma_reso no: il reso
-- nasce in bozza.
CREATE TEMP TABLE t_reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('verbo comune', p_stato_codice_interno => 'DRAFT');

-- 14) La conferma chiede conferma_reso, dalla riga DRAFT -> CONFERMATO
SELECT throws_like(
    format($$SELECT vendite.fn_conferma_reso(%s)$$, (SELECT reso_id FROM t_reso)),
    'Non hai i permessi per questa operazione%',
    'la conferma del reso senza conferma_reso: E_PERMESSO_NEGATO'
);

-- 15) L'annullo di una bozza non e' un passaggio pesante (M-4): nessuna azione
SELECT lives_ok(
    format($$SELECT vendite.fn_annulla_reso(%s)$$, (SELECT reso_id FROM t_reso)),
    'l''annullo di un reso in bozza senza conferma_reso passa (riga senza azione, M-4)'
);

-- 16) Con emetti_ddt (concessa dal builder qui sopra) «Emetti» c'e'
SELECT is(
    (SELECT count(*)::integer
       FROM jsonb_array_elements(script.fn_available_actions_ddt((SELECT ddt_id FROM t_bolla)) -> 'available_actions') a
      WHERE a ->> 'target_state' = 'EMESSO'),
    1,
    'capability della bolla in bozza: con emetti_ddt il passaggio a EMESSO c''e'''
);

-- 17) Il verbo con l'azione emette (la bolla non muove merce: nessun movimento
--     restituito, quindi il verbo si chiama a parte e si legge lo stato).
DO $emetti$ BEGIN
    PERFORM 1 FROM vendite.fn_cambia_stato_ddt((SELECT ddt_id FROM t_bolla), 'EMESSO');
END $emetti$;
SELECT is(
    (SELECT s.codice_interno::text
       FROM vendite.ddt d JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id
      WHERE d.id = (SELECT ddt_id FROM t_bolla)),
    'EMESSO',
    'il verbo con emetti_ddt emette la bolla, dalla scrittura comune'
);

-- 18) Un passaggio di processo chiesto al verbo: la bolla del reso e' CONSEGNATA
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_ddt(%s, 'RESO')$$, (SELECT ddt_id FROM t_reso)),
    'Questo passaggio di stato lo fa il sistema%',
    'un passaggio di processo (CONSEGNATO -> RESO) chiesto al verbo: E_DOC_PASSAGGIO_DI_PROCESSO'
);

-- 19) Il secondo «Emetti»: la bolla e' EMESSA (test 17), la matrice non ha
--     EMESSO -> EMESSO. Lo rifiuta la prima riga del verbo.
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_ddt(%s, 'EMESSO')$$, (SELECT ddt_id FROM t_bolla)),
    'Il documento è già nello stato EMESSO%',
    'il secondo «Emetti» della bolla, dal verbo: E_DOC_GIA_NELLO_STATO'
);

-- 20) Il secondo annullo del reso (annullato al test 15): parla la prima riga,
--     prima del controllo dello stato del reso (E_RESO_STATO_NON_ANNULLABILE).
SELECT throws_like(
    format($$SELECT vendite.fn_annulla_reso(%s)$$, (SELECT reso_id FROM t_reso)),
    'Il documento è già nello stato ANNULLATO%',
    'il secondo annullo del reso: E_DOC_GIA_NELLO_STATO, dalla prima riga del verbo'
);

-- 21) La regola e' del verbo, non di ogni UPDATE: riscrivere lo stesso stato
--     (un salvataggio della riga intera) non cambia niente e passa, porta e
--     guard di transizione compresi.
SELECT lives_ok(
    format($$UPDATE vendite.ddt SET stato_doc_ddt_id = stato_doc_ddt_id WHERE id = %s$$,
           (SELECT ddt_id FROM t_bolla)),
    'un UPDATE che riscrive lo stesso stato della bolla: passa'
);

-- 22) Uno stato che il vocabolario non ha: la risposta dei gemelli
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_ddt(%s, 'PGTAP_INESISTENTE')$$, (SELECT ddt_id FROM t_bolla)),
    'Stato di destinazione non trovato o non attivo: PGTAP_INESISTENTE%',
    'il verbo della bolla con uno stato che non c''e'': E_STATO_WORKFLOW_NON_TROVATO, come ordine e preventivo'
);

-- 23) [rosso da owner] Un UPDATE diretto dello stato, anche con la GUC accesa
--     dall'applicazione: la porta chiede anche il proprietario.
SELECT set_config('zeroerp.doc_cambio_stato',
                  'vendite.ddt'::regclass::oid::text || ':' || (SELECT ddt_id FROM t_bolla)::text, true);
SELECT throws_like(
    format($$UPDATE vendite.ddt SET stato_doc_ddt_id = %s WHERE id = %s$$,
           (SELECT id FROM t_st WHERE cod = 'SPEDITO'), (SELECT ddt_id FROM t_bolla)),
    'Lo stato del documento DDT % si cambia solo dalle sue operazioni%',
    'un UPDATE diretto dello stato della bolla, anche con la GUC accesa: E_DOC_STATO_SOLO_DAL_VERBO [rosso da owner]'
);
SELECT set_config('zeroerp.doc_cambio_stato', '', true);

-- 24) [rosso da owner] La scrittura comune chiamata dall'applicazione: da sola
--     non apre niente.
SELECT throws_like(
    format($$SELECT script.fn_doc_scrivi_stato('vendite.ddt'::regclass, %s, %s)$$,
           (SELECT ddt_id FROM t_bolla), (SELECT id FROM t_st WHERE cod = 'SPEDITO')),
    'Lo stato del documento DDT % si cambia solo dalle sue operazioni%',
    'script.fn_doc_scrivi_stato chiamata dall''applicazione: la porta la ferma [rosso da owner]'
);

SELECT * FROM finish();
ROLLBACK;
