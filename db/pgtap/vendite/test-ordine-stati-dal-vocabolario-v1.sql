-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'ordine legge il significato dei suoi stati dal vocabolario.
--   ChangeSet: 20261114-14 (script.fn_available_actions_ordine), -15
--   (vendite.trgfn_ordini_guard_transizione), -16
--   (vendite.fn_ordine_proietta_stato_evasione), -17
--   (vendite.fn_genera_ddt_da_ordine), -18 (vendite.fn_list_ordini_da_pushare),
--   -19 (vendite.fn_situazione_merce_ordine), -20
--   (vendite.vw_dash_fatturazione_ordini); giro 6b-bis (D-EVAD): -22
--   (script.fn_check_ordine_evadibile), -23 (la bolla dalla check), -24
--   (can_genera_ddt nella capability).
--   Brief: brief-db-stati-documento-dal-vocabolario, giri 6b e 6b-bis (S-2).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la capability riconosce la bozza dallo stato iniziale (prezzi, reason
--     del push, data di consegna confermata) e l'annullo da is_abortito; dice
--     can_edit_righe dal lock delle righe, e il trigger risponde uguale;
--   - il guard di transizione chiede la riga attiva dallo stato iniziale allo
--     stato di emissione;
--   - la push-list esclude lo stato iniziale e quello di annullo;
--   - la proiezione dell'evasione, senza legami, torna allo stato di
--     emissione; EVASO e PARZIALMENTE_EVASO restano le destinazioni nominate
--     del processo;
--   - la bolla si genera dallo stato di emissione e da PARZIALMENTE_EVASO, e
--     la capability lo dice con can_genera_ddt dalla stessa check;
--   - la situazione merce impegna la riga dallo stato di emissione in poi;
--   - il cruscotto da' DOC_BOZZA nello stato iniziale;
--   - i lettori di significato non nominano i codici degli stati dell'ordine
--     (fatturazione_trigger e' un altro asse), la bolla nessuno; proiezione e
--     check dell'evadibilita' nominano solo le destinazioni del processo
--     (presidio sulla FORMA, dichiarato tale).
--
-- ⭐ LA MARCA SPOSTATA: le colonne si spostano in transazione su un altro
--   stato, e la risposta deve seguirle. Un corpo che ricordasse i codici
--   resterebbe fermo. Ogni marca spostata ha il suo contrasto, letto prima
--   dello spostamento, e si rimette al suo posto prima della successiva.
--   Gli indici unici parziali sono immediati: prima si spegne la marca di
--   partenza, poi si accende l'altra.
-- ⭐ I CASI SI COSTRUISCONO, dalle strade dell'applicazione: gli ordini dai
--   builder, i passaggi manuali dal verbo vendite.fn_cambia_stato_ordine
--   (porta e guard veri, l'azione del passaggio concessa all'operatore),
--   l'evasione dalla bolla (dbops.fn_pgtap_crea_ddt_da_ordine) e il ritorno
--   dall'annullo della bolla (vendite.fn_annulla_ddt). Nessuno skip.
-- ⛔ Mai script.fn_doc_scrivi_stato dal test: la porta vuole il proprietario
--   della tabella, e il runner e' il ruolo applicativo.
--
-- Elenco test (plan 24):
--   1) contrasto: can_edit_righe vero in bozza, falso nello stato di emissione
--   2) contrasto: la riga dell'ordine confermato non si scrive (E_RIGA_DOC_NON_BOZZA)
--   3) contrasto: le reason del push in bozza e nell'annullato
--   4) contrasto: la push-list ha il confermato e l'evaso, non la bozza
--   5) contrasto: la data di consegna confermata in bozza: ORDINE_IN_BOZZA
--   6) contrasto: il cruscotto da' DOC_BOZZA in bozza, PUSH_NON_ESEGUITO al confermato
--   7) contrasto: l'ordine vuoto non si conferma, e si annulla
--   8) contrasto: la bolla non si genera dalla bozza, si genera dal confermato
--   8-bis) contrasto: can_genera_ddt falso in bozza (ORDINE_NON_EVADIBILE), vero al confermato
--   9) contrasto: annullata la bolla, l'ordine torna CONFERMATO
--  10) contrasto: da_spedire c'e' sul confermato, non sulla bozza
--  11) forma: i lettori di significato non nominano i codici degli stati
--  12) forma: proiezione e check dell'evadibilita' nominano solo le destinazioni del processo
--  13) ⭐ iniziale su CONFERMATO: capability (righe, push, data di consegna)
--  14) ⭐ ... e la riga del confermato si scrive davvero
--  15) ⭐ ... il cruscotto da' DOC_BOZZA al confermato
--  16) ⭐ ... e la push-list ha la DRAFT, non il confermato
--  17) ⭐ emissione su EVASO: la bolla non si genera dal confermato
--  17-bis) ⭐ ... e la capability lo dice: can_genera_ddt falso sul confermato
--  18) ⭐ ... da_spedire non c'e' piu' sul confermato
--  19) ⭐ ... e annullata la bolla, l'ordine va a EVASO
--  20) ⭐ is_abortito su EVASO: la reason del push segue la marca
--  21) ⭐ ... e la push-list non ha piu' l'evaso
--  22) ⭐ emissione su ANNULLATO: l'ordine vuoto non si annulla (la Regola 2)
--
-- ⚠️ Il 14 e' verde anche senza i changeSet del giro: e' la meta' del trigger,
--   che riconosce la bozza dallo stato iniziale dal 20261113-40 (D-LOCK). La
--   capability che deve dire la stessa cosa e' il 13.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(24);

-- ============================================================
-- Gli attrezzi
-- ============================================================
CREATE TEMP TABLE t_ord (caso text PRIMARY KEY,            -- l'etichetta del test
                         id   bigint,                      -- vendite.ordini.id
                         riga bigint,                      -- vendite.ordini_righe.id
                         ddt  bigint);                     -- vendite.ddt.id

CREATE FUNCTION pg_temp.o(p_caso text)   -- text: l'etichetta del test
RETURNS vendite.ordini.id%TYPE LANGUAGE sql STABLE AS $$
    SELECT id FROM t_ord WHERE caso = p_caso
$$;

CREATE FUNCTION pg_temp.stato(p_id vendite.ordini.id%TYPE)
RETURNS config.stati_doc_ordini.codice_interno%TYPE LANGUAGE sql STABLE AS $$
    SELECT s.codice_interno
      FROM vendite.ordini o
      JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
     WHERE o.id = p_id
$$;

CREATE FUNCTION pg_temp.cap(p_caso text, p_chiave text)   -- text: etichetta e chiave del blob
RETURNS text LANGUAGE sql STABLE AS $$                    -- text: un valore del blob jsonb
    SELECT script.fn_available_actions_ordine(pg_temp.o(p_caso)) ->> p_chiave
$$;

CREATE FUNCTION pg_temp.motivo(p_caso text)   -- text: l'etichetta del test
RETURNS vendite.vw_dash_fatturazione_ordini.motivo_fermo%TYPE LANGUAGE sql STABLE AS $$
    SELECT v.motivo_fermo FROM vendite.vw_dash_fatturazione_ordini v
     WHERE v.documento_id = pg_temp.o(p_caso)
$$;

CREATE FUNCTION pg_temp.in_push(p_caso text)   -- text: l'etichetta del test
RETURNS boolean LANGUAGE sql STABLE AS $$      -- boolean: un'esistenza
    SELECT EXISTS (SELECT 1 FROM vendite.fn_list_ordini_da_pushare(p_ordine_id := pg_temp.o(p_caso)))
$$;

CREATE FUNCTION pg_temp.da_spedire(p_caso text)   -- text: l'etichetta del test
RETURNS numeric LANGUAGE sql STABLE AS $$         -- numeric: la colonna calcolata della funzione
    SELECT s.da_spedire FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[pg_temp.o(p_caso)]) s
     WHERE s.ordine_riga_id = (SELECT riga FROM t_ord WHERE caso = p_caso)
$$;

-- Il passaggio dal verbo dell'ordine: porta e guard veri. L'azione del
-- passaggio si concede all'operatore (la fixture prova lo stato, non il
-- permesso). Rende cio' che l'ha rifiutato (NULL se passa).
CREATE FUNCTION pg_temp.passa(p_id vendite.ordini.id%TYPE,
                              p_codice config.stati_doc_ordini.codice_interno%TYPE)
RETURNS text LANGUAGE plpgsql AS $$   -- text: un codice d'errore o un vincolo, nessuna colonna
DECLARE
    v_azione config.azioni_processo.permission_codename%TYPE;
    v_utente config.user_override_azioni.auth_user_id%TYPE;
BEGIN
    SELECT x.azione_processo_codename INTO v_azione
      FROM vendite.ordini o
     CROSS JOIN LATERAL script.fn_doc_passaggio(
                'vendite.ordini'::regclass, o.stato_doc_ordine_id,
                (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = p_codice)) x
     WHERE o.id = p_id;
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    IF v_azione IS NOT NULL AND v_utente IS NOT NULL THEN
        PERFORM dbops.fn_pgtap_concedi_azione(v_utente, v_azione);
    END IF;
    RETURN dbops.fn_pgtap_codice_errore(format(
        'SELECT * FROM vendite.fn_cambia_stato_ordine(%s, %L)', p_id, p_codice));
END
$$;

CREATE FUNCTION pg_temp.genera_ddt(p_caso text)   -- text: l'etichetta del test
RETURNS text LANGUAGE sql AS $$                   -- text: come pg_temp.passa
    SELECT dbops.fn_pgtap_codice_errore(format(
        'SELECT vendite.fn_genera_ddt_da_ordine(%s)', pg_temp.o(p_caso)))
$$;

-- L'annullo della bolla, coi legami che il verbo vuole confermati: ritira il
-- legame di evasione, e la proiezione riporta l'ordine indietro.
CREATE FUNCTION pg_temp.annulla_ddt(p_caso text)   -- text: l'etichetta del test
RETURNS void LANGUAGE sql AS $$
    SELECT vendite.fn_annulla_ddt(
               d.ddt,
               (SELECT count(*)::integer   -- integer: la firma del verbo, un conteggio
                  FROM vendite.fn_documento_legami('DDT_VENDITA', d.ddt)))
      FROM t_ord d WHERE d.caso = p_caso;
$$;

-- ============================================================
-- Fixture: gli ordini, tutti prima di spostare le marche
-- ============================================================
INSERT INTO t_ord
SELECT c.caso, r.ordine_id, r.ordine_riga_id, NULL
  FROM (VALUES ('bozza', 'DRAFT'), ('conf', 'CONFERMATO'), ('annullato', 'DRAFT'),
               ('evad_contrasto', 'CONFERMATO'), ('evad_marca', 'CONFERMATO')) c(caso, stato)
 CROSS JOIN LATERAL dbops.fn_pgtap_crea_ordine_con_righe(
                        'stati dal vocabolario, ' || c.caso, c.stato,
                        p_fatturazione_trigger => 'CONFERMATO') r;

-- Gli ordini vuoti: nascono in bozza, senza righe.
INSERT INTO t_ord
SELECT c.caso, b.ordine_id, NULL, NULL
  FROM (VALUES ('vuoto_contrasto'), ('vuoto_marca')) c(caso)
 CROSS JOIN LATERAL dbops.fn_pgtap_crea_ordine('stati dal vocabolario, ' || c.caso, 'DRAFT') b;

-- Evaso per intero dalla bolla emessa; evasi in parte da una bolla in bozza,
-- che il test annulla (9 e 19).
INSERT INTO t_ord
SELECT 'evaso', d.ordine_id, d.ordine_riga_id, d.ddt_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('stati dal vocabolario, evaso', 'EMESSO',
                                         p_quantita => 10,
                                         p_fatturazione_trigger => 'CONFERMATO') d;

INSERT INTO t_ord
SELECT c.caso, d.ordine_id, d.ordine_riga_id, d.ddt_id
  FROM (VALUES ('ritorno_contrasto'), ('ritorno_marca')) c(caso)
 CROSS JOIN LATERAL dbops.fn_pgtap_crea_ddt_da_ordine('stati dal vocabolario, ' || c.caso, 'DRAFT',
                                                      p_quantita => 10, p_qta_da_evadere => 4) d;

SELECT pg_temp.passa(pg_temp.o('annullato'), 'ANNULLATO');

-- ============================================================
-- 1-10) I contrasti, col vocabolario del seed
-- ============================================================
SELECT is(
    concat_ws(' ', pg_temp.cap('bozza', 'can_edit_righe'), pg_temp.cap('conf', 'can_edit_righe')),
    'true false',
    '1. contrasto: can_edit_righe vero in bozza, falso nello stato di emissione'
);

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.ordini_righe SET descrizione = COALESCE(descrizione, %L) || %L WHERE id = %s',
        '', ' (modificata)', (SELECT riga FROM t_ord WHERE caso = 'conf'))),
    'E_RIGA_DOC_NON_BOZZA',
    '2. contrasto: la riga dell''ordine confermato non si scrive, e la capability lo diceva'
);

SELECT is(
    concat_ws(' ', pg_temp.cap('bozza', 'can_push_commessa_reason'),
                   pg_temp.cap('annullato', 'can_push_commessa_reason')),
    'ORDINE_NON_CONFERMATO ORDINE_ANNULLATO',
    '3. contrasto: le reason del push nello stato iniziale e in quello di annullo'
);

SELECT is(
    concat_ws(' ', pg_temp.in_push('bozza')::text, pg_temp.in_push('conf')::text,
                   pg_temp.in_push('evaso')::text),
    'false true true',
    '4. contrasto: la push-list ha il confermato e l''evaso, non la bozza'
);

SELECT is(
    pg_temp.cap('bozza', 'can_edit_data_consegna_confermata_reason'),
    'ORDINE_IN_BOZZA',
    '5. contrasto: la data di consegna confermata in bozza si scrive dalla riga (ORDINE_IN_BOZZA)'
);

SELECT is(
    concat_ws(' ', pg_temp.motivo('bozza'), pg_temp.motivo('conf')),
    'DOC_BOZZA PUSH_NON_ESEGUITO',
    '6. contrasto: il cruscotto da'' DOC_BOZZA in bozza, PUSH_NON_ESEGUITO al confermato'
);

SELECT is(
    concat_ws('|', pg_temp.passa(pg_temp.o('vuoto_marca'), 'CONFERMATO'),
                   COALESCE(pg_temp.passa(pg_temp.o('vuoto_contrasto'), 'ANNULLATO'), 'passa')),
    'E_ORDINE_CONFERMA_SENZA_RIGHE|passa',
    '7. contrasto: l''ordine vuoto non si conferma (Regola 2), e si annulla'
);

SELECT is(
    concat_ws('|', pg_temp.genera_ddt('bozza'), COALESCE(pg_temp.genera_ddt('evad_contrasto'), 'passa')),
    'E_DDT_ORDINE_STATO_NON_EVADIBILE|passa',
    '8. contrasto: la bolla non si genera dalla bozza, si genera dal confermato'
);

SELECT is(
    concat_ws(' ', pg_temp.cap('bozza', 'can_genera_ddt'), pg_temp.cap('bozza', 'can_genera_ddt_reason'),
                   pg_temp.cap('conf', 'can_genera_ddt'),
                   COALESCE(pg_temp.cap('conf', 'can_genera_ddt_reason'), 'nessuna')),
    'false ORDINE_NON_EVADIBILE true nessuna',
    '8-bis. contrasto: can_genera_ddt falso in bozza col motivo, vero al confermato: la stessa check della bolla'
);

SELECT pg_temp.annulla_ddt('ritorno_contrasto');

SELECT is(
    pg_temp.stato(pg_temp.o('ritorno_contrasto'))::text,
    'CONFERMATO',
    '9. contrasto: annullata la bolla, l''ordine senza legami torna CONFERMATO'
);

SELECT is(
    concat_ws(' ', (pg_temp.da_spedire('conf') IS NOT NULL)::text,
                   (pg_temp.da_spedire('bozza') IS NOT NULL)::text),
    'true false',
    '10. contrasto: da_spedire c''e'' sul confermato (riga impegnata), non sulla bozza'
);

-- ============================================================
-- 11-12) La forma — presidio sulla FORMA, dichiarato tale
-- ============================================================
-- ⚠️ Prova che i codici non sono scritti nei corpi (commenti tolti) e nella
--   definizione della vista, non che il comportamento sia giusto: quello lo
--   provano i test 1-10 e 13-22. Il confronto con fatturazione_trigger si
--   toglie prima: e' un altro asse, che riusa il nome CONFERMATO.
-- ⚠️ pg_get_functiondef e non prosrc: vendite.fn_situazione_merce_ordine e'
--   BEGIN ATOMIC, e il suo prosrc e' vuoto.
SELECT is(
    ARRAY(
        SELECT x.oggetto
          FROM (SELECT p.oid::regprocedure::text AS oggetto,
                       regexp_replace(
                           regexp_replace(pg_get_functiondef(p.oid), '--[^\n]*', '', 'g'),
                           '(fatturazione_trigger|v_fatt_trg)\s*(IS DISTINCT FROM|=)\s*''CONFERMATO''',
                           '', 'g') AS testo
                  FROM pg_proc p
                 WHERE p.oid IN ('script.fn_available_actions_ordine(bigint)'::regprocedure,
                                 'vendite.trgfn_ordini_guard_transizione()'::regprocedure,
                                 'vendite.fn_list_ordini_da_pushare(date,bigint,integer,bigint)'::regprocedure,
                                 'vendite.fn_situazione_merce_ordine(bigint[],bigint[])'::regprocedure,
                                 'vendite.fn_genera_ddt_da_ordine(bigint,jsonb,date)'::regprocedure)
                UNION ALL
                SELECT 'vendite.vw_dash_fatturazione_ordini',
                       pg_get_viewdef('vendite.vw_dash_fatturazione_ordini'::regclass)) x
         WHERE x.testo ~ '''(DRAFT|CONFERMATO|PARZIALMENTE_EVASO|EVASO|ANNULLATO)'''
         ORDER BY 1),
    ARRAY[]::text[],
    '11. forma: capability, guard, push-list, situazione merce, bolla e cruscotto dell''ordine non nominano i codici degli stati'
);

SELECT is(
    (SELECT string_agg(x.oggetto || ':' || x.codici, ' | ' ORDER BY x.oggetto)
       -- ⚠️ Il nome si compone dal catalogo, schema compreso: regprocedure::text
       --   lo stampa senza lo schema che sta nel search_path, e il runner
       --   applicativo ha script nel suo.
       FROM (SELECT n.nspname || '.' || p.proname || '(' ||
                    pg_get_function_identity_arguments(p.oid) || ')' AS oggetto,
                    (SELECT string_agg(DISTINCT m[1], ',' ORDER BY m[1])
                       FROM regexp_matches(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'),
                                           '''(DRAFT|CONFERMATO|PARZIALMENTE_EVASO|EVASO|ANNULLATO)''',
                                           'g') m) AS codici
               FROM pg_proc p
               JOIN pg_namespace n ON n.oid = p.pronamespace
              WHERE p.oid IN ('vendite.fn_ordine_proietta_stato_evasione(bigint)'::regprocedure,
                              'script.fn_check_ordine_evadibile(bigint)'::regprocedure)) x),
    'script.fn_check_ordine_evadibile(p_ordine_id bigint):PARZIALMENTE_EVASO | '
    'vendite.fn_ordine_proietta_stato_evasione(p_ordine_id bigint):EVASO,PARZIALMENTE_EVASO',
    '12. forma: proiezione e check dell''evadibilita'' nominano solo le destinazioni del processo'
);

-- ============================================================
-- 13-16) ⭐ La marca spostata: iniziale su CONFERMATO
-- ============================================================
UPDATE config.stati_doc_ordini SET iniziale = false WHERE codice_interno = 'DRAFT';
UPDATE config.stati_doc_ordini SET iniziale = true  WHERE codice_interno = 'CONFERMATO';

SELECT is(
    concat_ws(' ', pg_temp.cap('bozza', 'can_edit_righe'), pg_temp.cap('conf', 'can_edit_righe'),
                   pg_temp.cap('conf', 'can_push_commessa_reason'),
                   pg_temp.cap('conf', 'can_edit_data_consegna_confermata_reason')),
    'false true ORDINE_NON_CONFERMATO ORDINE_IN_BOZZA',
    '13. con iniziale su CONFERMATO, la capability tratta il confermato da bozza: righe, push, data di consegna'
);

SELECT is(
    COALESCE(dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.ordini_righe SET descrizione = COALESCE(descrizione, %L) || %L WHERE id = %s',
        '', ' (modificata)', (SELECT riga FROM t_ord WHERE caso = 'conf'))), 'passa'),
    'passa',
    '14. ... e la riga del confermato si scrive davvero: capability e trigger rispondono uguale'
);

SELECT is(
    pg_temp.motivo('conf')::text,
    'DOC_BOZZA',
    '15. ... il cruscotto da'' DOC_BOZZA al confermato'
);

SELECT is(
    concat_ws(' ', pg_temp.in_push('bozza')::text, pg_temp.in_push('conf')::text),
    'true false',
    '16. ... e la push-list ha la DRAFT, non il confermato'
);

UPDATE config.stati_doc_ordini SET iniziale = false WHERE codice_interno = 'CONFERMATO';
UPDATE config.stati_doc_ordini SET iniziale = true  WHERE codice_interno = 'DRAFT';

-- ============================================================
-- 17-19) ⭐ La marca spostata: emissione su EVASO
-- ============================================================
UPDATE config.stati_doc_ordini SET emissione = false WHERE codice_interno = 'CONFERMATO';
UPDATE config.stati_doc_ordini SET emissione = true  WHERE codice_interno = 'EVASO';

SELECT is(
    pg_temp.genera_ddt('evad_marca'),
    'E_DDT_ORDINE_STATO_NON_EVADIBILE',
    '17. con emissione su EVASO, la bolla non si genera dal confermato'
);

SELECT is(
    concat_ws(' ', pg_temp.cap('conf', 'can_genera_ddt'), pg_temp.cap('conf', 'can_genera_ddt_reason')),
    'false ORDINE_NON_EVADIBILE',
    '17-bis. ... e la capability lo dice: can_genera_ddt falso sul confermato, col motivo'
);

SELECT ok(
    pg_temp.da_spedire('conf') IS NULL,
    '18. ... e la riga del confermato non e'' piu'' impegnata: da_spedire non c''e'''
);

-- Annullata la bolla, l'ordine non ha legami: la proiezione lo porta allo
-- stato di emissione, ora EVASO (la matrice ha PARZIALMENTE_EVASO -> EVASO).
SELECT pg_temp.annulla_ddt('ritorno_marca');

SELECT is(
    pg_temp.stato(pg_temp.o('ritorno_marca'))::text,
    'EVASO',
    '19. ... e annullata la bolla, l''ordine senza legami va allo stato di emissione: EVASO'
);

UPDATE config.stati_doc_ordini SET emissione = false WHERE codice_interno = 'EVASO';
UPDATE config.stati_doc_ordini SET emissione = true  WHERE codice_interno = 'CONFERMATO';

-- ============================================================
-- 20-21) ⭐ La marca spostata: is_abortito su EVASO
-- ============================================================
UPDATE config.stati_doc_ordini SET is_abortito = false WHERE codice_interno = 'ANNULLATO';
UPDATE config.stati_doc_ordini SET is_abortito = true  WHERE codice_interno = 'EVASO';

SELECT is(
    concat_ws(' ', pg_temp.cap('evaso', 'can_push_commessa_reason'),
                   COALESCE(pg_temp.cap('annullato', 'can_push_commessa_reason'), 'nessuna')),
    'ORDINE_ANNULLATO nessuna',
    '20. con is_abortito su EVASO, la reason ORDINE_ANNULLATO va all''evaso e lascia l''annullato'
);

SELECT ok(
    NOT pg_temp.in_push('evaso'),
    '21. ... e la push-list non ha piu'' l''evaso'
);

UPDATE config.stati_doc_ordini SET is_abortito = false WHERE codice_interno = 'EVASO';
UPDATE config.stati_doc_ordini SET is_abortito = true  WHERE codice_interno = 'ANNULLATO';

-- ============================================================
-- 22) ⭐ La marca spostata: emissione su ANNULLATO
-- ============================================================
UPDATE config.stati_doc_ordini SET emissione = false WHERE codice_interno = 'CONFERMATO';
UPDATE config.stati_doc_ordini SET emissione = true  WHERE codice_interno = 'ANNULLATO';

SELECT is(
    pg_temp.passa(pg_temp.o('vuoto_marca'), 'ANNULLATO'),
    'E_ORDINE_CONFERMA_SENZA_RIGHE',
    '22. con emissione su ANNULLATO, l''ordine vuoto non ci va: la Regola 2 segue la marca'
);

SELECT * FROM finish();

ROLLBACK;
