-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'offerta legge il significato dei suoi stati dal vocabolario.
--   ChangeSet: 20261112-59 (colonna rifiuto), -60 (script.fn_stato_rifiuto_id),
--   -61 (guard di transizione), -62 (capability), -63
--   (vendite.vw_dash_fatturazione_offerte), -64 (dbops.fn_pgtap_crea_offerta),
--   -65 (vendite.vw_offerte_commerciali_lista.is_scaduta, D-SCAD); 20261113-38
--   (vendite.fn_offerta_scaduta), -39 (la vista la compone, V-1); -40
--   (script.fn_doc_lock_regola: la bozza dal vocabolario, D-LOCK), -41
--   (can_edit_eccezioni dal lock, V-2).
--   Brief: brief-db-stati-documento-dal-vocabolario, giro 2 (③, S-2, S-3,
--   S-10).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - il guard scrive la data del passaggio dal significato della
--     destinazione: emissione -> data_emissione, accettazione ->
--     data_accettazione, rifiuto -> data_rifiuto; l'emissione dallo stato
--     iniziale congela la versione di listino;
--   - lo stato di rifiuto lo dice la colonna rifiuto, al massimo uno per
--     vocabolario, e lo legge script.fn_stato_rifiuto_id (NULL dove il
--     vocabolario non ha la colonna);
--   - la capability espone stato_terminale (la colonna terminale dello stato
--     corrente) e decide «in bozza» dallo stato iniziale, attraverso il lock;
--   - il lock delle righe e dei satelliti riconosce la bozza dallo stato
--     iniziale del vocabolario: capability e trigger rispondono uguale;
--   - il cruscotto delle offerte da' DOC_BOZZA nello stato iniziale e
--     IN_ATTESA_ACCETTAZIONE nello stato di emissione;
--   - la lista dice is_scaduta solo se la validita' e' passata E lo stato non
--     ha ancora un esito (il cliente non ha risposto); la regola la dice
--     vendite.fn_offerta_scaduta, pura sui valori, e la vista la compone;
--   - guard, capability e vista non nominano i codici degli stati
--     dell'offerta (presidio sulla FORMA, dichiarato tale).
--
-- ⭐ LA MARCA SPOSTATA: le colonne si spostano in transazione su un altro
--   stato, e la risposta deve seguirle. Un corpo che ricordasse i codici
--   resterebbe fermo. Ogni marca spostata ha il suo contrasto, letto prima
--   dello spostamento.
-- ⭐ I CASI SI COSTRUISCONO: le offerte dal builder, sul cliente del primo.
--   Nessuno skip.
--
-- Elenco test (plan 23):
--   1) il builder: l'offerta nasce nello stato iniziale
--   2) l'emissione dallo stato iniziale: versione di listino congelata e
--      data_emissione scritta
--   3) il rifiuto: data_rifiuto scritta, data_accettazione no
--   4) stato_terminale della capability: false in bozza, true nel rifiuto
--   5) script.fn_stato_rifiuto_id: RIFIUTATA (offerta), RIFIUTATO
--      (preventivo), NULL (contratto, senza la colonna)
--   6) un secondo stato di rifiuto nello stesso vocabolario: 23505
--   7) ⭐ marca spostata: con accettazione su RIFIUTATA (e rifiuto tolto), lo
--      stesso passaggio scrive data_accettazione e non data_rifiuto
--   8) contrasto: can_edit_eccezioni vero in bozza, falso in emissione
--   9) contrasto: motivo_fermo DOC_BOZZA in bozza, IN_ATTESA_ACCETTAZIONE in
--      emissione
--  10) ⭐ marca spostata: con iniziale su EMESSA, l'offerta emessa ha
--      can_edit_eccezioni vero
--  11) ⭐ ... e motivo_fermo DOC_BOZZA
--  12) forma: guard, capability e vista non nominano i codici dell'offerta
--  13) lista: l'offerta emessa con la validita' passata e' scaduta
--  14) lista: la rifiutata con la validita' passata non lo e' (ha un esito)
--  15) ⭐ marca spostata: con un esito sullo stato EMESSA, l'emessa con la
--      validita' passata non e' piu' scaduta
--  16) vendite.fn_offerta_scaduta sui valori: senza esito e con la validita'
--      passata si'; con un esito, senza validita', o con la validita' che
--      scade oggi no
--  17) vendite.fn_offerta_scaduta e' IMMUTABLE e non STRICT (esito NULL e'
--      il caso normale)
--  18) forma: la vista compone vendite.fn_offerta_scaduta e non riscrive la
--      regola (presidio sulla FORMA, dichiarato tale)
--  19) contrasto: con lo stato iniziale su BOZZA, l'indirizzo dell'offerta
--      emessa non si toglie, e la capability lo dice
--  20) ⭐ marca spostata: con iniziale su EMESSA il lock legge EMESSA come
--      bozza
--  21) ⭐ ... l'indirizzo dell'offerta in bozza non si toglie piu'
--  22) ⭐ ... quello dell'offerta emessa si', e la capability lo proponeva
--  23) ... ed e' tolto davvero
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(23);

-- ============================================================
-- Fixture: tre offerte dello stesso cliente
-- ============================================================
CREATE TEMP TABLE t_bozza AS
SELECT * FROM dbops.fn_pgtap_crea_offerta('offerta dal vocabolario', 'BOZZA');

CREATE TEMP TABLE t_emessa AS
SELECT * FROM dbops.fn_pgtap_crea_offerta(
    'offerta dal vocabolario, emessa', 'EMESSA',
    (SELECT b.billing_account_id FROM t_bozza b));

CREATE TEMP TABLE t_rifiutata AS
SELECT * FROM dbops.fn_pgtap_crea_offerta(
    'offerta dal vocabolario, rifiutata', 'RIFIUTATA',
    (SELECT b.billing_account_id FROM t_bozza b));

-- Le due offerte della scadenza (test 13-15): nascono in bozza, la validita'
-- si porta nel passato finche' l'offerta si modifica, poi si portano avanti.
-- Si costruiscono qui, prima che il test sposti lo stato iniziale.
CREATE TEMP TABLE t_scad_emessa AS
SELECT * FROM dbops.fn_pgtap_crea_offerta(
    'offerta dal vocabolario, scaduta emessa', 'BOZZA',
    (SELECT b.billing_account_id FROM t_bozza b));
CREATE TEMP TABLE t_scad_rifiutata AS
SELECT * FROM dbops.fn_pgtap_crea_offerta(
    'offerta dal vocabolario, scaduta rifiutata', 'BOZZA',
    (SELECT b.billing_account_id FROM t_bozza b));

UPDATE vendite.offerte_commerciali o
   SET validita_dal = script.fn_data_operativa() - 30,
       validita_al  = script.fn_data_operativa() - 1
 WHERE o.id IN ((SELECT e.offerta_id FROM t_scad_emessa e),
                (SELECT r.offerta_id FROM t_scad_rifiutata r));

SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali'::regclass,
                                    (SELECT e.offerta_id FROM t_scad_emessa e), 'EMESSA');
SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali'::regclass,
                                    (SELECT r.offerta_id FROM t_scad_rifiutata r), 'RIFIUTATA');

-- ============================================================
-- 1-3) Il builder e le date del passaggio
-- ============================================================
SELECT is(
    (SELECT b.stato_doc_offerta_id FROM t_bozza b),
    script.fn_doc_stato_iniziale_id('vendite.offerte_commerciali'::regclass),
    '1. il builder: l''offerta nasce nello stato iniziale del vocabolario'
);

SELECT is(
    (SELECT (o.listino_versione_id IS NOT NULL) || ' ' || (o.data_emissione IS NOT NULL)
       FROM vendite.offerte_commerciali o
      WHERE o.id = (SELECT e.offerta_id FROM t_emessa e)),
    'true true',
    '2. l''emissione dallo stato iniziale congela la versione di listino e scrive data_emissione'
);

SELECT is(
    (SELECT (o.data_rifiuto IS NOT NULL) || ' ' || (o.data_accettazione IS NOT NULL)
       FROM vendite.offerte_commerciali o
      WHERE o.id = (SELECT r.offerta_id FROM t_rifiutata r)),
    'true false',
    '3. lo stato di rifiuto scrive data_rifiuto, e non data_accettazione'
);

-- ============================================================
-- 4) stato_terminale della capability
-- ============================================================
SELECT is(
    (script.fn_available_actions_offerta((SELECT b.offerta_id FROM t_bozza b)) ->> 'stato_terminale')
    || ' ' ||
    (script.fn_available_actions_offerta((SELECT r.offerta_id FROM t_rifiutata r)) ->> 'stato_terminale'),
    'false true',
    '4. la capability espone stato_terminale: false in bozza, true nel rifiuto'
);

-- ============================================================
-- 5-6) Il lettore e l'unicita' dello stato di rifiuto
-- ============================================================
SELECT is(
    COALESCE((SELECT s.codice_interno FROM config.stati_doc_offerte s
               WHERE s.id = script.fn_stato_rifiuto_id('vendite.offerte_commerciali'::regclass)), 'NULL')
    || ' ' ||
    COALESCE((SELECT s.codice_interno FROM config.stati_doc_preventivi s
               WHERE s.id = script.fn_stato_rifiuto_id('vendite.preventivi'::regclass)), 'NULL')
    || ' ' ||
    COALESCE(script.fn_stato_rifiuto_id('vendite.contratti'::regclass)::text, 'NULL'),
    'RIFIUTATA RIFIUTATO NULL',
    '5. script.fn_stato_rifiuto_id: RIFIUTATA, RIFIUTATO, NULL dove il vocabolario non ha la colonna'
);

SELECT throws_ok(
    $$UPDATE config.stati_doc_offerte SET rifiuto = true WHERE codice_interno = 'ANNULLATA'$$,
    '23505',
    NULL,
    '6. un secondo stato di rifiuto nello stesso vocabolario e'' rifiutato (uq_stati_doc_offerte_rifiuto)'
);

-- ============================================================
-- 7) ⭐ La marca spostata: le date seguono le colonne
-- ============================================================
-- L'accettazione passa su RIFIUTATA e il rifiuto si toglie. Prima si spegne
-- la marca di partenza: l'indice unico parziale e' immediato.
UPDATE config.stati_doc_offerte SET rifiuto = false WHERE codice_interno = 'RIFIUTATA';
UPDATE config.stati_doc_offerte SET accettazione = false WHERE codice_interno = 'ACCETTATA';
UPDATE config.stati_doc_offerte SET accettazione = true WHERE codice_interno = 'RIFIUTATA';

CREATE TEMP TABLE t_spostata AS
SELECT * FROM dbops.fn_pgtap_crea_offerta(
    'offerta dal vocabolario, marca spostata', 'EMESSA',
    (SELECT b.billing_account_id FROM t_bozza b));

SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali'::regclass,
                                    (SELECT s.offerta_id FROM t_spostata s), 'RIFIUTATA');

SELECT is(
    (SELECT (o.data_accettazione IS NOT NULL) || ' ' || (o.data_rifiuto IS NOT NULL)
       FROM vendite.offerte_commerciali o
      WHERE o.id = (SELECT s.offerta_id FROM t_spostata s)),
    'true false',
    '7. con accettazione su RIFIUTATA, lo stesso passaggio scrive data_accettazione e non data_rifiuto'
);

-- Le marche tornano al loro posto per i test che seguono.
UPDATE config.stati_doc_offerte SET accettazione = false WHERE codice_interno = 'RIFIUTATA';
UPDATE config.stati_doc_offerte SET accettazione = true WHERE codice_interno = 'ACCETTATA';
UPDATE config.stati_doc_offerte SET rifiuto = true WHERE codice_interno = 'RIFIUTATA';

-- ============================================================
-- 8-9) I contrasti: bozza ed emissione con le marche al loro posto
-- ============================================================
SELECT is(
    (script.fn_available_actions_offerta((SELECT b.offerta_id FROM t_bozza b)) ->> 'can_edit_eccezioni')
    || ' ' ||
    (script.fn_available_actions_offerta((SELECT e.offerta_id FROM t_emessa e)) ->> 'can_edit_eccezioni'),
    'true false',
    '8. contrasto: can_edit_eccezioni vero in bozza, falso in emissione'
);

SELECT is(
    (SELECT string_agg(v.motivo_fermo, ' ' ORDER BY v.documento_id)
       FROM vendite.vw_dash_fatturazione_offerte v
      WHERE v.documento_id IN ((SELECT b.offerta_id FROM t_bozza b),
                               (SELECT e.offerta_id FROM t_emessa e))),
    'DOC_BOZZA IN_ATTESA_ACCETTAZIONE',
    '9. contrasto: motivo_fermo DOC_BOZZA in bozza, IN_ATTESA_ACCETTAZIONE in emissione'
);

-- ============================================================
-- 10-11) ⭐ La marca spostata: lo stato iniziale su EMESSA
-- ============================================================
-- Ultimo spostamento del test: dopo, nessuna offerta nasce piu'.
UPDATE config.stati_doc_offerte SET iniziale = false WHERE codice_interno = 'BOZZA';
UPDATE config.stati_doc_offerte SET iniziale = true WHERE codice_interno = 'EMESSA';

SELECT is(
    script.fn_available_actions_offerta((SELECT e.offerta_id FROM t_emessa e)) ->> 'can_edit_eccezioni',
    'true',
    '10. con iniziale su EMESSA, l''offerta emessa ha can_edit_eccezioni vero'
);

SELECT is(
    (SELECT v.motivo_fermo
       FROM vendite.vw_dash_fatturazione_offerte v
      WHERE v.documento_id = (SELECT e.offerta_id FROM t_emessa e))::text,
    'DOC_BOZZA',
    '11. con iniziale su EMESSA, il cruscotto da'' DOC_BOZZA all''offerta emessa'
);

-- ============================================================
-- 12) La forma — presidio sulla FORMA, dichiarato tale
-- ============================================================
-- ⚠️ Prova che i codici non sono scritti nei corpi (commenti tolti) e nella
--   definizione della vista, non che il comportamento sia giusto: quello lo
--   provano i test 1-11.
SELECT is(
    ARRAY(
        SELECT x.oggetto
          FROM (SELECT p.oid::regprocedure::text AS oggetto,
                       regexp_replace(p.prosrc, '--[^\n]*', '', 'g') AS testo
                  FROM pg_proc p
                 WHERE p.oid IN ('vendite.trgfn_offerte_commerciali_guard_transizione()'::regprocedure,
                                 'script.fn_available_actions_offerta(bigint)'::regprocedure)
                UNION ALL
                SELECT 'vendite.vw_dash_fatturazione_offerte',
                       pg_get_viewdef('vendite.vw_dash_fatturazione_offerte'::regclass)) x
         WHERE x.testo ~ '''(BOZZA|EMESSA|ACCETTATA|RIFIUTATA|SUPERATA|ANNULLATA)'''
         ORDER BY 1),
    ARRAY[]::text[],
    '12. forma: guard, capability e cruscotto delle offerte non nominano i codici degli stati dell''offerta'
);

-- ============================================================
-- 13-15) La scadenza nella lista: la regola intera, dal vocabolario
-- ============================================================
SELECT is(
    (SELECT v.is_scaduta FROM vendite.vw_offerte_commerciali_lista v
      WHERE v.id = (SELECT e.offerta_id FROM t_scad_emessa e)),
    true,
    '13. lista: l''offerta emessa con la validita'' passata e'' scaduta'
);

SELECT is(
    (SELECT v.is_scaduta FROM vendite.vw_offerte_commerciali_lista v
      WHERE v.id = (SELECT r.offerta_id FROM t_scad_rifiutata r)),
    false,
    '14. lista: la rifiutata con la validita'' passata non e'' scaduta: il cliente ha risposto'
);

-- ⭐ La marca spostata: lo stato EMESSA prende un esito. Se la vista
--   ricordasse i codici BOZZA ed EMESSA, la risposta resterebbe true.
UPDATE config.stati_doc_offerte SET esito = 'POSITIVO' WHERE codice_interno = 'EMESSA';

SELECT is(
    (SELECT v.is_scaduta FROM vendite.vw_offerte_commerciali_lista v
      WHERE v.id = (SELECT e.offerta_id FROM t_scad_emessa e)),
    false,
    '15. con un esito sullo stato EMESSA, la stessa offerta non e'' piu'' scaduta'
);

-- ============================================================
-- 16-18) La sede della regola: vendite.fn_offerta_scaduta
-- ============================================================
-- I casi si costruiscono sui valori: la funzione e' pura, nessuna fixture.
-- concat_ws stampa i booleani come t/f.
SELECT is(
    concat_ws(' ',
        vendite.fn_offerta_scaduta(NULL,       DATE '2026-01-09', DATE '2026-01-10'),
        vendite.fn_offerta_scaduta('POSITIVO', DATE '2026-01-09', DATE '2026-01-10'),
        vendite.fn_offerta_scaduta('NEGATIVO', DATE '2026-01-09', DATE '2026-01-10'),
        vendite.fn_offerta_scaduta(NULL,       NULL,              DATE '2026-01-10'),
        vendite.fn_offerta_scaduta(NULL,       DATE '2026-01-10', DATE '2026-01-10')),
    't f f f f',
    '16. fn_offerta_scaduta: scaduta senza esito e con la validita'' passata; non con un esito, senza validita'' o con la validita'' che scade oggi'
);

SELECT is(
    (SELECT p.provolatile::text || ' ' || p.proisstrict::text
       FROM pg_proc p
      WHERE p.oid = 'vendite.fn_offerta_scaduta(character varying, date, date)'::regprocedure),
    'i false',
    '17. fn_offerta_scaduta e'' IMMUTABLE e non STRICT: esito NULL e'' il caso normale'
);

-- ⚠️ Presidio sulla FORMA: prova che la vista chiama la funzione e non nomina
--   esito fuori da quella chiamata, non che il valore sia giusto: quello lo
--   provano i test 13-15, attraverso la vista.
SELECT ok(
    pg_get_viewdef('vendite.vw_offerte_commerciali_lista'::regclass) ~ 'fn_offerta_scaduta\(sdo\.esito, o\.validita_al'
    AND pg_get_viewdef('vendite.vw_offerte_commerciali_lista'::regclass) !~ 'esito IS NULL',
    '18. forma: vendite.vw_offerte_commerciali_lista compone vendite.fn_offerta_scaduta e non riscrive la regola'
);

-- ============================================================
-- 19-23) Il lock dal vocabolario: trigger e capability insieme
-- ============================================================
-- Lo stato iniziale torna su BOZZA per il contrasto (l'indice unico parziale
-- e' immediato: prima si spegne la marca di partenza).
UPDATE config.stati_doc_offerte SET iniziale = false WHERE codice_interno = 'EMESSA';
UPDATE config.stati_doc_offerte SET iniziale = true WHERE codice_interno = 'BOZZA';

SELECT is(
    COALESCE(dbops.fn_pgtap_codice_errore(format(
        $$DELETE FROM vendite.offerte_commerciali_indirizzi WHERE offerta_id = %s$$,
        (SELECT e.offerta_id FROM t_emessa e))), 'PASSA')
    || '|' ||
    (script.fn_available_actions_offerta((SELECT e.offerta_id FROM t_emessa e)) ->> 'can_edit_indirizzi'),
    'E_DOC_DATI_COLLEGATI_NON_BOZZA|false',
    '19. contrasto: con iniziale su BOZZA, l''indirizzo dell''offerta emessa non si toglie, e la capability lo dice'
);

-- ⭐ La marca spostata: lo stato iniziale su EMESSA. Un lock che leggesse il
--   codice del montaggio resterebbe su BOZZA.
UPDATE config.stati_doc_offerte SET iniziale = false WHERE codice_interno = 'BOZZA';
UPDATE config.stati_doc_offerte SET iniziale = true WHERE codice_interno = 'EMESSA';

SELECT is(
    (SELECT m.regola ->> 'stato_bozza'
       FROM script.fn_doc_lock_montaggi('vendite.offerte_commerciali_eccezioni'::regclass) m)
    || '|' ||
    ((SELECT count(*) FROM vendite.offerte_commerciali_indirizzi i
       WHERE i.offerta_id = (SELECT e.offerta_id FROM t_emessa e)) > 0)::text,
    'EMESSA|true',
    '20. con iniziale su EMESSA il lock legge EMESSA come bozza (e l''offerta emessa ha un indirizzo da togliere)'
);

SELECT is(
    COALESCE(dbops.fn_pgtap_codice_errore(format(
        $$DELETE FROM vendite.offerte_commerciali_indirizzi WHERE offerta_id = %s$$,
        (SELECT b.offerta_id FROM t_bozza b))), 'PASSA'),
    'E_DOC_DATI_COLLEGATI_NON_BOZZA',
    '21. con iniziale su EMESSA, l''indirizzo dell''offerta in BOZZA non si toglie piu'''
);

SELECT is(
    (script.fn_available_actions_offerta((SELECT e.offerta_id FROM t_emessa e)) ->> 'can_edit_indirizzi')
    || '|' ||
    COALESCE(dbops.fn_pgtap_codice_errore(format(
        $$DELETE FROM vendite.offerte_commerciali_indirizzi WHERE offerta_id = %s$$,
        (SELECT e.offerta_id FROM t_emessa e))), 'PASSA'),
    'true|PASSA',
    '22. con iniziale su EMESSA, la capability propone l''indirizzo dell''offerta emessa e il trigger lo lascia togliere'
);

SELECT is(
    (SELECT count(*)::int FROM vendite.offerte_commerciali_indirizzi i
      WHERE i.offerta_id = (SELECT e.offerta_id FROM t_emessa e)),
    0,
    '23. ... e l''indirizzo e'' tolto davvero'
);

SELECT * FROM finish();
ROLLBACK;
