-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il preventivo legge il significato dei suoi stati dal vocabolario.
--   ChangeSet: 20261114-08 (vendite.trgfn_preventivi_guard_annullamento), -09
--   (vendite.trgfn_preventivi_guard_transizione, Regola 3), -10
--   (script.fn_available_actions_preventivo, can_edit_righe dal lock), -11
--   (vendite.fn_crea_revisione_preventivo), -12
--   (vendite.vw_dash_fatturazione_preventivi), -13
--   (vendite.fn_preventivo_proietta_stato_smistamento, D-PROI).
--   Brief: brief-db-stati-documento-dal-vocabolario, giro 6a (S-2).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - il guard dell'annullo giudica la destinazione che il vocabolario marca
--     is_abortito;
--   - la Regola 3 del guard di transizione (validita' finita, prezzi) scatta
--     sulla destinazione marcata accettazione;
--   - la capability dice can_edit_righe dal lock delle righe, e il trigger
--     risponde uguale;
--   - la revisione gia' in bozza e' quella nello stato iniziale;
--   - il cruscotto da' DOC_BOZZA nello stato iniziale e IN_ATTESA_ACCETTAZIONE
--     nello stato di emissione;
--   - la proiezione dello smistamento torna da EVASO allo stato di
--     accettazione; EVASO resta la destinazione nominata del processo;
--   - i cinque lettori di significato non nominano i codici degli stati del
--     preventivo, la proiezione nomina solo EVASO (presidio sulla FORMA,
--     dichiarato tale).
--
-- ⭐ LA MARCA SPOSTATA: le colonne si spostano in transazione su un altro
--   stato, e la risposta deve seguirle. Un corpo che ricordasse i codici
--   resterebbe fermo. Ogni marca spostata ha il suo contrasto, letto prima
--   dello spostamento, e si rimette al suo posto prima della successiva.
-- ⭐ I CASI SI COSTRUISCONO, dalle strade dell'applicazione: i preventivi dai
--   builder, i passaggi manuali dal verbo vendite.fn_cambia_stato_preventivo
--   (porta e guard veri, l'azione del passaggio concessa all'operatore), EVASO
--   dal push all'ordine e il ritorno da EVASO dall'annullo dell'ordine
--   (vendite.fn_annulla_ordine). Nessuno skip.
-- ⛔ Mai script.fn_doc_scrivi_stato dal test: la porta vuole il proprietario
--   della tabella, e il runner e' il ruolo applicativo.
-- ⚠️ IL FUSO: due preventivi si emettono con validita_al = oggi nel fuso a
--   ovest; il fuso passa poi a est, e la loro validita' e' finita (la forma di
--   vendite/test-preventivo-scadenza-v1). Il fuso a ovest viene prima del
--   contesto: l'operatore deve nascere nel giorno piu' vecchio del test.
--
-- Elenco test (plan 18):
--   1) contrasto: can_edit_righe vero in bozza, falso in emissione
--   2) contrasto: la riga del preventivo emesso non si scrive (E_RIGA_DOC_NON_BOZZA)
--   3) contrasto: motivo_fermo DOC_BOZZA, IN_ATTESA_ACCETTAZIONE, RIGA_RESIDUA
--   4) contrasto: la prima revisione si crea, la seconda trova la bozza
--   5) contrasto: smistato per intero, il preventivo e' EVASO
--   6) contrasto: da EVASO a RIFIUTATO non c'e' la strada (E_PREV_TRANSIZIONE_NON_AMMESSA)
--   7) contrasto: con la validita' finita l'accettazione si ferma, il rifiuto passa
--   8) contrasto: annullato l'ordine, il preventivo EVASO torna ACCETTATO
--   9) forma: i cinque lettori di significato non nominano i codici
--  10) forma: la proiezione nomina il solo EVASO
--  11) ⭐ iniziale su EMESSO: can_edit_righe falso in DRAFT, vero in EMESSO
--  12) ⭐ ... e la riga del preventivo emesso si scrive davvero
--  13) ⭐ ... il cruscotto da' DOC_BOZZA all'emesso
--  14) ⭐ ... e la revisione dell'emesso trova la bozza: e' lui
--  15) ⭐ emissione su ACCETTATO: il cruscotto da' IN_ATTESA_ACCETTAZIONE all'accettato
--  16) ⭐ is_abortito su RIFIUTATO: il guard dell'annullo parla per primo
--  17) ⭐ accettazione su RIFIUTATO: la Regola 3 ferma il rifiuto dello scaduto
--  18) ⭐ accettazione su EMESSO: annullato l'ordine, il preventivo EVASO va a EMESSO
--
-- ⚠️ Il 12 e' verde anche senza i changeSet del giro: e' la meta' del trigger,
--   che riconosce la bozza dallo stato iniziale dal 20261113-40 (D-LOCK). La
--   capability che deve dire la stessa cosa e' l'11.
-- ------------------------------------------------------------

BEGIN;

-- ⛔ IL FUSO A OVEST VIENE PRIMA DEL CONTESTO (vedi la testata).
UPDATE config.parameters SET default_value = 'Etc/GMT+12' WHERE code = 'SYSTEM_FUSO_ORARIO';

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

-- ============================================================
-- Gli attrezzi
-- ============================================================
CREATE FUNCTION pg_temp.stato_id(p_codice config.stati_doc_preventivi.codice_interno%TYPE)
RETURNS config.stati_doc_preventivi.id%TYPE LANGUAGE sql STABLE AS $$
    SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = p_codice
$$;

CREATE FUNCTION pg_temp.stato(p_id vendite.preventivi.id%TYPE)
RETURNS config.stati_doc_preventivi.codice_interno%TYPE LANGUAGE sql STABLE AS $$
    SELECT s.codice_interno
      FROM vendite.preventivi p
      JOIN config.stati_doc_preventivi s ON s.id = p.stato_doc_preventivo_id
     WHERE p.id = p_id
$$;

CREATE FUNCTION pg_temp.motivo(p_id vendite.preventivi.id%TYPE)
RETURNS vendite.vw_dash_fatturazione_preventivi.motivo_fermo%TYPE LANGUAGE sql STABLE AS $$
    SELECT v.motivo_fermo FROM vendite.vw_dash_fatturazione_preventivi v WHERE v.documento_id = p_id
$$;

-- Il passaggio dal verbo del preventivo: porta e guard veri. L'azione del
-- passaggio si concede all'operatore (la fixture prova lo stato, non il
-- permesso). Rende cio' che l'ha rifiutato (NULL se passa).
CREATE FUNCTION pg_temp.passa(p_id vendite.preventivi.id%TYPE,
                              p_codice config.stati_doc_preventivi.codice_interno%TYPE)
RETURNS text LANGUAGE plpgsql AS $$   -- text: un codice d'errore o un vincolo, nessuna colonna
DECLARE
    v_azione config.azioni_processo.permission_codename%TYPE;
    v_utente config.user_override_azioni.auth_user_id%TYPE;
BEGIN
    SELECT x.azione_processo_codename INTO v_azione
      FROM vendite.preventivi p
     CROSS JOIN LATERAL script.fn_doc_passaggio('vendite.preventivi'::regclass,
                                                p.stato_doc_preventivo_id,
                                                pg_temp.stato_id(p_codice)) x
     WHERE p.id = p_id;
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    IF v_azione IS NOT NULL AND v_utente IS NOT NULL THEN
        PERFORM dbops.fn_pgtap_concedi_azione(v_utente, v_azione);
    END IF;
    RETURN dbops.fn_pgtap_codice_errore(format(
        'SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, %L)', p_id, p_codice));
END
$$;

-- L'annullo dell'ordine, coi legami che il verbo vuole confermati.
CREATE FUNCTION pg_temp.annulla_ordine(p_ordine_id vendite.ordini.id%TYPE)
RETURNS void LANGUAGE sql AS $$
    SELECT vendite.fn_annulla_ordine(
               p_ordine_id,
               (SELECT count(*)::integer   -- integer: la firma del verbo, un conteggio
                  FROM vendite.fn_documento_legami('ORDINE_VENDITA', p_ordine_id)));
$$;

CREATE FUNCTION pg_temp.revisione(p_id vendite.preventivi.id%TYPE)
RETURNS text LANGUAGE sql AS $$   -- text: come pg_temp.passa
    SELECT dbops.fn_pgtap_codice_errore(format(
        'SELECT * FROM vendite.fn_crea_revisione_preventivo(%s, %L)', p_id, 'pgtap'))
$$;

-- ============================================================
-- Fixture: i preventivi, tutti prima di spostare fuso e marche
-- ============================================================
CREATE TEMP TABLE t_prev (caso text PRIMARY KEY,           -- l'etichetta del test
                          id   bigint,                     -- vendite.preventivi.id
                          riga bigint);                    -- vendite.preventivi_righe.id

INSERT INTO t_prev
SELECT 'bozza', b.preventivo_id, NULL
  FROM dbops.fn_pgtap_crea_preventivo('stati dal vocabolario, bozza', 'DRAFT') b;

INSERT INTO t_prev
SELECT c.caso, r.preventivo_id, r.preventivo_riga_id
  FROM (VALUES ('emesso', 'EMESSO'), ('accettato', 'ACCETTATO'),
               ('rev_contrasto', 'EMESSO'), ('rev_marca', 'EMESSO'),
               ('smistato', 'ACCETTATO'),
               ('evaso_contrasto', 'ACCETTATO'), ('evaso_marca', 'ACCETTATO')) c(caso, stato)
 CROSS JOIN LATERAL dbops.fn_pgtap_crea_preventivo_con_righe(
                        'stati dal vocabolario, ' || c.caso, c.stato) r;

-- Smistato per intero: la riga di merce va nell'ordine, e il push proietta.
SELECT vendite.fn_push_preventivo_a_ordine((SELECT id FROM t_prev WHERE caso = 'smistato'));

-- EVASO anche questi due, dal push: l'annullo del loro ordine (test 8 e 18)
-- riapre il residuo, e la proiezione li riporta indietro.
CREATE TEMP TABLE t_ord (caso text PRIMARY KEY,            -- l'etichetta del test
                         ordine bigint);                   -- vendite.ordini.id
INSERT INTO t_ord
SELECT t.caso, vendite.fn_push_preventivo_a_ordine(t.id)
  FROM t_prev t
 WHERE t.caso IN ('evaso_contrasto', 'evaso_marca');

-- La validita' che finisce oggi, nel fuso a ovest: si scrive in bozza, poi
-- il preventivo si emette.
DO $scad$
DECLARE
    v_caso text;                                   -- l'etichetta del test
    v_id   vendite.preventivi.id%TYPE;
BEGIN
    FOREACH v_caso IN ARRAY ARRAY['scaduto_contrasto', 'scaduto_marca'] LOOP
        SELECT b.preventivo_id INTO v_id
          FROM dbops.fn_pgtap_crea_preventivo('stati dal vocabolario, ' || v_caso, 'DRAFT') b;
        UPDATE vendite.preventivi
           SET validita_dal = script.fn_data_operativa() - 10,
               validita_al  = script.fn_data_operativa()
         WHERE id = v_id;
        PERFORM dbops.fn_pgtap_crea_preventivo_con_righe('stati dal vocabolario, ' || v_caso,
                                                         'EMESSO', p_preventivo_id => v_id);
        INSERT INTO t_prev VALUES (v_caso, v_id, NULL);
    END LOOP;
END $scad$;

-- Il tempo passa: almeno un giorno avanti.
UPDATE config.parameters SET default_value = 'Pacific/Kiritimati' WHERE code = 'SYSTEM_FUSO_ORARIO';

CREATE FUNCTION pg_temp.p(p_caso text)   -- text: l'etichetta del test
RETURNS vendite.preventivi.id%TYPE LANGUAGE sql STABLE AS $$
    SELECT id FROM t_prev WHERE caso = p_caso
$$;

-- ============================================================
-- 1-8) I contrasti, col vocabolario del seed
-- ============================================================
SELECT is(
    concat_ws(' ',
        script.fn_available_actions_preventivo(pg_temp.p('bozza'))  ->> 'can_edit_righe',
        script.fn_available_actions_preventivo(pg_temp.p('emesso')) ->> 'can_edit_righe'),
    'true false',
    '1. contrasto: can_edit_righe vero in bozza, falso nello stato di emissione'
);

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.preventivi_righe SET descrizione = COALESCE(descrizione, %L) || %L WHERE id = %s',
        '', ' (modificata)', (SELECT riga FROM t_prev WHERE caso = 'emesso'))),
    'E_RIGA_DOC_NON_BOZZA',
    '2. contrasto: la riga del preventivo emesso non si scrive, e la capability lo diceva'
);

SELECT is(
    concat_ws(' ', pg_temp.motivo(pg_temp.p('bozza')), pg_temp.motivo(pg_temp.p('emesso')),
                   pg_temp.motivo(pg_temp.p('accettato'))),
    'DOC_BOZZA IN_ATTESA_ACCETTAZIONE RIGA_RESIDUA',
    '3. contrasto: il cruscotto da'' DOC_BOZZA in bozza, IN_ATTESA_ACCETTAZIONE nell''emissione, RIGA_RESIDUA nell''accettazione'
);

SELECT is(
    concat_ws('|', COALESCE(pg_temp.revisione(pg_temp.p('rev_contrasto')), 'passa'),
                   pg_temp.revisione(pg_temp.p('rev_contrasto'))),
    'passa|E_PREV_REVISIONE_BOZZA_ESISTENTE',
    '4. contrasto: la prima revisione si crea, la seconda trova quella in bozza'
);

SELECT is(
    pg_temp.stato(pg_temp.p('smistato'))::text,
    'EVASO',
    '5. contrasto: smistato per intero nell''ordine, il preventivo e'' EVASO'
);

SELECT is(
    pg_temp.passa(pg_temp.p('smistato'), 'RIFIUTATO'),
    'E_PREV_TRANSIZIONE_NON_AMMESSA',
    '6. contrasto: da EVASO a RIFIUTATO la matrice non ha la strada, e l''annullo non c''entra'
);

SELECT is(
    concat_ws('|', pg_temp.passa(pg_temp.p('scaduto_contrasto'), 'ACCETTATO'),
                   COALESCE(pg_temp.passa(pg_temp.p('scaduto_contrasto'), 'RIFIUTATO'), 'passa')),
    'E_PREV_VALIDITA_SCADUTA|passa',
    '7. contrasto: con la validita'' finita l''accettazione si ferma, il rifiuto passa'
);

SELECT pg_temp.annulla_ordine((SELECT ordine FROM t_ord WHERE caso = 'evaso_contrasto'));

SELECT is(
    pg_temp.stato(pg_temp.p('evaso_contrasto'))::text,
    'ACCETTATO',
    '8. contrasto: annullato l''ordine, il preventivo EVASO ha di nuovo il residuo e torna ACCETTATO'
);

-- ============================================================
-- 9-10) La forma — presidio sulla FORMA, dichiarato tale
-- ============================================================
-- ⚠️ Prova che i codici non sono scritti nei corpi (commenti tolti) e nella
--   definizione della vista, non che il comportamento sia giusto: quello lo
--   provano i test 1-8 e 11-18.
SELECT is(
    ARRAY(
        SELECT x.oggetto
          FROM (SELECT p.oid::regprocedure::text AS oggetto,
                       regexp_replace(p.prosrc, '--[^\n]*', '', 'g') AS testo
                  FROM pg_proc p
                 WHERE p.oid IN ('vendite.trgfn_preventivi_guard_annullamento()'::regprocedure,
                                 'vendite.trgfn_preventivi_guard_transizione()'::regprocedure,
                                 'script.fn_available_actions_preventivo(bigint)'::regprocedure,
                                 'vendite.fn_crea_revisione_preventivo(bigint,text)'::regprocedure)
                UNION ALL
                SELECT 'vendite.vw_dash_fatturazione_preventivi',
                       pg_get_viewdef('vendite.vw_dash_fatturazione_preventivi'::regclass)) x
         WHERE x.testo ~ '''(DRAFT|EMESSO|ACCETTATO|RIFIUTATO|SCADUTO|ANNULLATO|EVASO)'''
         ORDER BY 1),
    ARRAY[]::text[],
    '9. forma: guard, capability, revisione e cruscotto del preventivo non nominano i codici degli stati'
);

SELECT is(
    (SELECT string_agg(DISTINCT m[1], ',')
       FROM pg_proc p,
            regexp_matches(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'),
                           '''(DRAFT|EMESSO|ACCETTATO|RIFIUTATO|SCADUTO|ANNULLATO|EVASO)''', 'g') m
      WHERE p.oid = 'vendite.fn_preventivo_proietta_stato_smistamento(bigint)'::regprocedure),
    'EVASO',
    '10. forma: la proiezione nomina il solo EVASO, la destinazione del processo'
);

-- ============================================================
-- 11-14) ⭐ La marca spostata: iniziale su EMESSO
-- ============================================================
-- Prima si spegne la marca di partenza: l'indice unico parziale e' immediato.
UPDATE config.stati_doc_preventivi SET iniziale = false WHERE codice_interno = 'DRAFT';
UPDATE config.stati_doc_preventivi SET iniziale = true  WHERE codice_interno = 'EMESSO';

SELECT is(
    concat_ws(' ',
        script.fn_available_actions_preventivo(pg_temp.p('bozza'))  ->> 'can_edit_righe',
        script.fn_available_actions_preventivo(pg_temp.p('emesso')) ->> 'can_edit_righe'),
    'false true',
    '11. con iniziale su EMESSO, can_edit_righe e'' falso in DRAFT e vero nell''emesso'
);

SELECT is(
    COALESCE(dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.preventivi_righe SET descrizione = COALESCE(descrizione, %L) || %L WHERE id = %s',
        '', ' (modificata)', (SELECT riga FROM t_prev WHERE caso = 'emesso'))), 'passa'),
    'passa',
    '12. ... e la riga dell''emesso si scrive davvero: capability e trigger rispondono uguale'
);

SELECT is(
    pg_temp.motivo(pg_temp.p('emesso'))::text,
    'DOC_BOZZA',
    '13. ... il cruscotto da'' DOC_BOZZA all''emesso'
);

SELECT is(
    pg_temp.revisione(pg_temp.p('rev_marca')),
    'E_PREV_REVISIONE_BOZZA_ESISTENTE',
    '14. ... e la revisione dell''emesso trova la bozza: e'' lui, nello stato iniziale'
);

UPDATE config.stati_doc_preventivi SET iniziale = false WHERE codice_interno = 'EMESSO';
UPDATE config.stati_doc_preventivi SET iniziale = true  WHERE codice_interno = 'DRAFT';

-- ============================================================
-- 15) ⭐ La marca spostata: emissione su ACCETTATO
-- ============================================================
UPDATE config.stati_doc_preventivi SET emissione = false WHERE codice_interno = 'EMESSO';
UPDATE config.stati_doc_preventivi SET emissione = true  WHERE codice_interno = 'ACCETTATO';

SELECT is(
    concat_ws(' ', pg_temp.motivo(pg_temp.p('accettato')), pg_temp.motivo(pg_temp.p('emesso'))),
    'IN_ATTESA_ACCETTAZIONE RIGA_RESIDUA',
    '15. con emissione su ACCETTATO, il cruscotto da'' IN_ATTESA_ACCETTAZIONE all''accettato e RIGA_RESIDUA all''emesso'
);

UPDATE config.stati_doc_preventivi SET emissione = false WHERE codice_interno = 'ACCETTATO';
UPDATE config.stati_doc_preventivi SET emissione = true  WHERE codice_interno = 'EMESSO';

-- ============================================================
-- 16) ⭐ La marca spostata: is_abortito su RIFIUTATO
-- ============================================================
-- Lo stesso passaggio del test 6: ora la destinazione e' l'annullo, e il guard
-- dell'annullo (a10_guard_annullamento) parla prima di quello della matrice.
UPDATE config.stati_doc_preventivi SET is_abortito = false WHERE codice_interno = 'ANNULLATO';
UPDATE config.stati_doc_preventivi SET is_abortito = true  WHERE codice_interno = 'RIFIUTATO';

SELECT is(
    pg_temp.passa(pg_temp.p('smistato'), 'RIFIUTATO'),
    'E_PREV_ORDINE_GIA_GENERATO',
    '16. con is_abortito su RIFIUTATO, il preventivo con l''ordine vivo non ci va: parla il guard dell''annullo'
);

UPDATE config.stati_doc_preventivi SET is_abortito = false WHERE codice_interno = 'RIFIUTATO';
UPDATE config.stati_doc_preventivi SET is_abortito = true  WHERE codice_interno = 'ANNULLATO';

-- ============================================================
-- 17) ⭐ La marca spostata: accettazione su RIFIUTATO
-- ============================================================
UPDATE config.stati_doc_preventivi SET accettazione = false WHERE codice_interno = 'ACCETTATO';
UPDATE config.stati_doc_preventivi SET accettazione = true  WHERE codice_interno = 'RIFIUTATO';

SELECT is(
    pg_temp.passa(pg_temp.p('scaduto_marca'), 'RIFIUTATO'),
    'E_PREV_VALIDITA_SCADUTA',
    '17. con accettazione su RIFIUTATO, la Regola 3 ferma il rifiuto dello scaduto'
);

UPDATE config.stati_doc_preventivi SET accettazione = false WHERE codice_interno = 'RIFIUTATO';

-- ============================================================
-- 18) ⭐ La marca spostata: accettazione su EMESSO
-- ============================================================
-- Il ritorno da EVASO va allo stato di accettazione: con la marca su EMESSO la
-- matrice deve avere la strada di processo EVASO -> EMESSO, che il test aggiunge.
UPDATE config.stati_doc_preventivi SET accettazione = true WHERE codice_interno = 'EMESSO';
INSERT INTO config.transizioni_stati_preventivi (stato_da_id, stato_a_id, attivo, meta)
VALUES (pg_temp.stato_id('EVASO'), pg_temp.stato_id('EMESSO'), true, '{"manuale": false}'::jsonb);

SELECT pg_temp.annulla_ordine((SELECT ordine FROM t_ord WHERE caso = 'evaso_marca'));

SELECT is(
    pg_temp.stato(pg_temp.p('evaso_marca'))::text,
    'EMESSO',
    '18. con accettazione su EMESSO, annullato l''ordine, il preventivo EVASO va a EMESSO'
);

SELECT * FROM finish();

ROLLBACK;
