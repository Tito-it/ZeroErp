-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la bolla legge il significato dei suoi stati dal vocabolario.
--   ChangeSet: 20261114-36 (script.fn_available_actions_ddt), -37
--   (script.fn_check_ddt_riga_correggi_qta_evasa), -38 (vendite.fn_annulla_ddt),
--   -39 (vendite.trgfn_ddt_gen_numero_emesso), -40
--   (vendite.trgfn_ddt_guard_causale_emissione), -41
--   (vendite.trgfn_ddt_guard_indirizzi_obbligatori), -42
--   (vendite.trgfn_ddt_guard_transizione), -43
--   (vendite.trgfn_ddt_guard_transizione_approvazione), -44
--   (vendite.trgfn_ddt_riga_legame_guard), -45 (vendite.vw_dash_fatturazione_ddt),
--   -46 (vendite.vw_ddt_lista, pdf_mode).
--   Brief: brief-db-stati-documento-dal-vocabolario, giro 6d (S-2).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la capability dice can_edit_righe dal lock delle righe, e il trigger
--     risponde uguale;
--   - la correzione della quantita' evasa si ferma dove il lock delle righe
--     non lascia scrivere;
--   - il numero si assegna nello stato di emissione;
--   - l'annullo porta la bolla nello stato che il vocabolario marca
--     is_abortito;
--   - il cruscotto da' DOC_BOZZA nello stato iniziale;
--   - la lista porta pdf_mode;
--   - i lettori di significato non nominano DRAFT, EMESSO e ANNULLATO; le
--     destinazioni del processo (SPEDITO, CONSEGNATO, RESO) restano dove il
--     processo le nomina (presidio sulla FORMA, dichiarato tale).
--
-- ⭐ LA MARCA SPOSTATA: le colonne si spostano in transazione su un altro
--   stato, e la risposta deve seguirle. Ogni marca ha il suo contrasto, letto
--   prima dello spostamento, e si rimette al suo posto prima della successiva.
--   Gli indici unici parziali sono immediati: prima si spegne la marca di
--   partenza, poi si accende l'altra.
-- ⭐ I CASI SI COSTRUISCONO, dalle strade dell'applicazione: le bolle dai
--   builder, i passaggi dal verbo vendite.fn_cambia_stato_ddt con l'azione
--   del passaggio concessa all'operatore, l'annullo da vendite.fn_annulla_ddt.
--   Nessuno skip.
--
-- Elenco test (plan 14):
--   1) contrasto: can_edit_righe vero in bozza, falso nell'emessa
--   2) contrasto: la riga dell'emessa non si scrive (E_RIGA_DOC_NON_BOZZA)
--   3) contrasto: la correzione della quantita' evasa e' ferma nell'emessa
--   4) contrasto: il numero c'e' nell'emessa, non in bozza
--   5) contrasto: il cruscotto da' DOC_BOZZA in bozza
--   6) contrasto: la lista da' PREVIEW in bozza e ARCHIVE nell'emessa
--   7) contrasto: l'annullo porta la bozza in ANNULLATO
--   8) forma: i lettori di significato non nominano DRAFT, EMESSO, ANNULLATO
--   9) ⭐ iniziale su EMESSO: can_edit_righe falso in DRAFT, vero nell'emessa
--  10) ⭐ ... e la riga dell'emessa si scrive davvero
--  11) ⭐ ... il cruscotto da' DOC_BOZZA all'emessa
--  12) ⭐ ... e la correzione della quantita' non e' piu' ferma per lo stato
--  13) ⭐ emissione su SPEDITO: emessa, la bolla non prende il numero
--  14) ⭐ is_abortito su CONSEGNATO: l'annullo va verso CONSEGNATO, che la
--      matrice non ha dalla bozza
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE t_ddt (caso text PRIMARY KEY,   -- l'etichetta del test
                         id   bigint,             -- vendite.ddt.id
                         riga bigint);            -- vendite.ddt_righe.id

INSERT INTO t_ddt
SELECT c.caso, d.ddt_id, d.ddt_riga_id
  FROM (VALUES ('bozza', 'DRAFT'), ('emessa', 'EMESSO'),
               ('emetti_contrasto', 'DRAFT'), ('emetti_marca', 'DRAFT'),
               ('annulla_contrasto', 'DRAFT'), ('annulla_marca', 'DRAFT')) c(caso, stato)
 CROSS JOIN LATERAL dbops.fn_pgtap_crea_ddt_senza_ordine('stati dal vocabolario, ' || c.caso, c.stato) d;

-- Le bolle dall'ordine: la correzione della quantita' evasa vale per loro.
INSERT INTO t_ddt
SELECT c.caso, d.ddt_id, d.ddt_riga_id
  FROM (VALUES ('evasa_emessa', 'EMESSO')) c(caso, stato)
 CROSS JOIN LATERAL dbops.fn_pgtap_crea_ddt_da_ordine('stati dal vocabolario, ' || c.caso, c.stato,
                                                      p_quantita => 10, p_qta_da_evadere => 4) d;

CREATE FUNCTION pg_temp.d(p_caso text)   -- text: l'etichetta del test
RETURNS vendite.ddt.id%TYPE LANGUAGE sql STABLE AS $$
    SELECT id FROM t_ddt WHERE caso = p_caso
$$;

CREATE FUNCTION pg_temp.r(p_caso text)   -- text: l'etichetta del test
RETURNS vendite.ddt_righe.id%TYPE LANGUAGE sql STABLE AS $$
    SELECT riga FROM t_ddt WHERE caso = p_caso
$$;

CREATE FUNCTION pg_temp.cap(p_caso text, p_chiave text)   -- text: etichetta e chiave del blob
RETURNS text LANGUAGE sql STABLE AS $$                    -- text: un valore del blob jsonb
    SELECT script.fn_available_actions_ddt(pg_temp.d(p_caso)) ->> p_chiave
$$;

CREATE FUNCTION pg_temp.stato(p_caso text)   -- text: l'etichetta del test
RETURNS config.stati_doc_ddt.codice_interno%TYPE LANGUAGE sql STABLE AS $$
    SELECT s.codice_interno FROM vendite.ddt d
      JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id
     WHERE d.id = pg_temp.d(p_caso)
$$;

CREATE FUNCTION pg_temp.motivo(p_caso text)   -- text: l'etichetta del test
RETURNS vendite.vw_dash_fatturazione_ddt.motivo_fermo%TYPE LANGUAGE sql STABLE AS $$
    SELECT v.motivo_fermo FROM vendite.vw_dash_fatturazione_ddt v WHERE v.documento_id = pg_temp.d(p_caso)
$$;

CREATE FUNCTION pg_temp.scrivi_riga(p_caso text)   -- text: l'etichetta del test
RETURNS text LANGUAGE sql AS $$                    -- text: un codice d'errore, nessuna colonna
    SELECT dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.ddt_righe SET descrizione = COALESCE(descrizione, %L) || %L WHERE id = %s',
        '', ' (modificata)', pg_temp.r(p_caso)))
$$;

-- Il primo motivo della correzione della quantita' evasa, o «ammessa».
CREATE FUNCTION pg_temp.correggi(p_caso text)   -- text: l'etichetta del test
RETURNS text LANGUAGE sql STABLE AS $$          -- text: un reason del blob jsonb
    SELECT COALESCE(script.fn_check_ddt_riga_correggi_qta_evasa(pg_temp.r(p_caso)) -> 0 ->> 'reason', 'ammessa')
$$;

-- Il passaggio dal verbo della bolla: porta e guard veri. L'azione del
-- passaggio si concede all'operatore. Rende cio' che l'ha rifiutato (NULL se
-- passa).
CREATE FUNCTION pg_temp.passa(p_id vendite.ddt.id%TYPE,
                              p_codice config.stati_doc_ddt.codice_interno%TYPE)
RETURNS text LANGUAGE plpgsql AS $$   -- text: un codice d'errore o un vincolo, nessuna colonna
DECLARE
    v_azione config.azioni_processo.permission_codename%TYPE;
    v_utente config.user_override_azioni.auth_user_id%TYPE;
BEGIN
    SELECT x.azione_processo_codename INTO v_azione
      FROM vendite.ddt d
     CROSS JOIN LATERAL script.fn_doc_passaggio(
                'vendite.ddt'::regclass, d.stato_doc_ddt_id,
                (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno = p_codice)) x
     WHERE d.id = p_id;
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    IF v_azione IS NOT NULL AND v_utente IS NOT NULL THEN
        PERFORM dbops.fn_pgtap_concedi_azione(v_utente, v_azione);
    END IF;
    RETURN dbops.fn_pgtap_codice_errore(format(
        'SELECT * FROM vendite.fn_cambia_stato_ddt(%s, %L)', p_id, p_codice));
END
$$;

-- L'annullo dal verbo, coi legami che vuole confermati.
CREATE FUNCTION pg_temp.annulla(p_caso text)   -- text: l'etichetta del test
RETURNS text LANGUAGE sql AS $$                -- text: un codice d'errore, nessuna colonna
    SELECT dbops.fn_pgtap_codice_errore(format(
        'SELECT * FROM vendite.fn_annulla_ddt(%s, %s)', pg_temp.d(p_caso),
        (SELECT count(*)::integer   -- integer: la firma del verbo, un conteggio
           FROM vendite.fn_documento_legami('DDT_VENDITA', pg_temp.d(p_caso)))))
$$;

-- ============================================================
-- 1-7) I contrasti, col vocabolario del seed
-- ============================================================
SELECT is(
    concat_ws(' ', pg_temp.cap('bozza', 'can_edit_righe'), pg_temp.cap('emessa', 'can_edit_righe')),
    'true false',
    '1. contrasto: can_edit_righe vero in bozza, falso nello stato di emissione'
);

SELECT is(
    pg_temp.scrivi_riga('emessa'),
    'E_RIGA_DOC_NON_BOZZA',
    '2. contrasto: la riga dell''emessa non si scrive, e la capability lo diceva'
);

SELECT is(
    pg_temp.correggi('evasa_emessa'),
    'DDT_NON_IN_BOZZA',
    '3. contrasto: la correzione della quantita'' evasa e'' ferma nell''emessa'
);

SELECT is(
    concat_ws(' ', ((SELECT numero FROM vendite.ddt WHERE id = pg_temp.d('emessa')) IS NOT NULL)::text,
                   ((SELECT numero FROM vendite.ddt WHERE id = pg_temp.d('bozza')) IS NOT NULL)::text),
    'true false',
    '4. contrasto: il numero c''e'' nell''emessa, non in bozza'
);

SELECT is(
    pg_temp.motivo('bozza')::text,
    'DOC_BOZZA',
    '5. contrasto: il cruscotto da'' DOC_BOZZA in bozza'
);

SELECT is(
    concat_ws(' ', (SELECT v.pdf_mode FROM vendite.vw_ddt_lista v WHERE v.id = pg_temp.d('bozza')),
                   (SELECT v.pdf_mode FROM vendite.vw_ddt_lista v WHERE v.id = pg_temp.d('emessa'))),
    'PREVIEW ARCHIVE',
    '6. contrasto: la lista da'' PREVIEW in bozza e ARCHIVE nell''emessa'
);

-- ⚠️ L'annullo in un'istruzione sua: pg_temp.stato e' STABLE, e nella stessa
--   istruzione vedrebbe la bolla com'era all'inizio.
CREATE TEMP TABLE t_annullo AS SELECT COALESCE(pg_temp.annulla('annulla_contrasto'), 'passa') AS esito;

SELECT is(
    concat_ws('|', (SELECT esito FROM t_annullo), pg_temp.stato('annulla_contrasto')::text),
    'passa|ANNULLATO',
    '7. contrasto: l''annullo porta la bozza nello stato di annullo, ANNULLATO'
);

-- ============================================================
-- 8) La forma — presidio sulla FORMA, dichiarato tale
-- ============================================================
-- ⚠️ Prova che i codici del significato non sono scritti nei corpi (commenti
--   tolti) e nelle viste, non che il comportamento sia giusto.
SELECT is(
    ARRAY(
        SELECT x.oggetto
          FROM (SELECT n.nspname || '.' || p.proname AS oggetto,
                       regexp_replace(pg_get_functiondef(p.oid), '--[^\n]*', '', 'g') AS testo
                  FROM pg_proc p
                  JOIN pg_namespace n ON n.oid = p.pronamespace
                 WHERE p.oid IN ('script.fn_available_actions_ddt(bigint)'::regprocedure,
                                 'script.fn_check_ddt_riga_correggi_qta_evasa(bigint)'::regprocedure,
                                 'vendite.fn_annulla_ddt(bigint,integer)'::regprocedure,
                                 'vendite.trgfn_ddt_gen_numero_emesso()'::regprocedure,
                                 'vendite.trgfn_ddt_guard_causale_emissione()'::regprocedure,
                                 'vendite.trgfn_ddt_guard_indirizzi_obbligatori()'::regprocedure,
                                 'vendite.trgfn_ddt_guard_transizione()'::regprocedure,
                                 'vendite.trgfn_ddt_guard_transizione_approvazione()'::regprocedure,
                                 'vendite.trgfn_ddt_riga_legame_guard()'::regprocedure)
                UNION ALL
                SELECT 'vendite.vw_dash_fatturazione_ddt',
                       pg_get_viewdef('vendite.vw_dash_fatturazione_ddt'::regclass)) x
         WHERE x.testo ~ '''(DRAFT|EMESSO|ANNULLATO)'''
         ORDER BY 1),
    ARRAY[]::text[],
    '8. forma: capability, check, annullo, numero, guard e cruscotto della bolla non nominano DRAFT, EMESSO, ANNULLATO'
);

-- ============================================================
-- 9-12) ⭐ La marca spostata: iniziale su EMESSO
-- ============================================================
UPDATE config.stati_doc_ddt SET iniziale = false WHERE codice_interno = 'DRAFT';
UPDATE config.stati_doc_ddt SET iniziale = true  WHERE codice_interno = 'EMESSO';

SELECT is(
    concat_ws(' ', pg_temp.cap('bozza', 'can_edit_righe'), pg_temp.cap('emessa', 'can_edit_righe')),
    'false true',
    '9. con iniziale su EMESSO, can_edit_righe e'' falso in DRAFT e vero nell''emessa'
);

SELECT is(
    COALESCE(pg_temp.scrivi_riga('emessa'), 'passa'),
    'passa',
    '10. ... e la riga dell''emessa si scrive davvero: capability e trigger rispondono uguale'
);

SELECT is(
    pg_temp.motivo('emessa')::text,
    'DOC_BOZZA',
    '11. ... il cruscotto da'' DOC_BOZZA all''emessa'
);

SELECT isnt(
    pg_temp.correggi('evasa_emessa'),
    'DDT_NON_IN_BOZZA',
    '12. ... e la correzione della quantita'' non e'' piu'' ferma per lo stato'
);

UPDATE config.stati_doc_ddt SET iniziale = false WHERE codice_interno = 'EMESSO';
UPDATE config.stati_doc_ddt SET iniziale = true  WHERE codice_interno = 'DRAFT';

-- ============================================================
-- 13) ⭐ La marca spostata: emissione su SPEDITO
-- ============================================================
-- Il contrasto: emessa col vocabolario del seed, la bolla prende il numero.
SELECT pg_temp.passa(pg_temp.d('emetti_contrasto'), 'EMESSO');

UPDATE config.stati_doc_ddt SET emissione = false WHERE codice_interno = 'EMESSO';
UPDATE config.stati_doc_ddt SET emissione = true  WHERE codice_interno = 'SPEDITO';

SELECT pg_temp.passa(pg_temp.d('emetti_marca'), 'EMESSO');

SELECT is(
    concat_ws(' ', pg_temp.stato('emetti_contrasto')::text,
                   ((SELECT numero FROM vendite.ddt WHERE id = pg_temp.d('emetti_contrasto')) IS NOT NULL)::text,
                   pg_temp.stato('emetti_marca')::text,
                   ((SELECT numero FROM vendite.ddt WHERE id = pg_temp.d('emetti_marca')) IS NOT NULL)::text),
    'EMESSO true EMESSO false',
    '13. con emissione su SPEDITO, la bolla portata in EMESSO non prende il numero (il contrasto si'')'
);

UPDATE config.stati_doc_ddt SET emissione = false WHERE codice_interno = 'SPEDITO';
UPDATE config.stati_doc_ddt SET emissione = true  WHERE codice_interno = 'EMESSO';

-- ============================================================
-- 14) ⭐ La marca spostata: is_abortito su CONSEGNATO
-- ============================================================
UPDATE config.stati_doc_ddt SET is_abortito = false WHERE codice_interno = 'ANNULLATO';
UPDATE config.stati_doc_ddt SET is_abortito = true  WHERE codice_interno = 'CONSEGNATO';

SELECT is(
    pg_temp.annulla('annulla_marca'),
    'E_STATO_DDT_TRANSIZIONE_NON_VALIDA',
    '14. con is_abortito su CONSEGNATO, l''annullo va verso CONSEGNATO, che la matrice non ha dalla bozza'
);

SELECT * FROM finish();

ROLLBACK;
