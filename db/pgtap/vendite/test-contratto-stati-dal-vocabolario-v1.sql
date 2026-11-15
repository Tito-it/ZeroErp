-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il contratto legge il significato dei suoi stati dal vocabolario.
--   ChangeSet: 20261114-27 (script.fn_available_actions_contratto), -28
--   (vendite.fn_get_contratto_attivo), -29
--   (vendite.trgfn_contratti_freeze_listino_versione), -30
--   (vendite.trgfn_contratti_guard_transizione_stato), -31
--   (vendite.trgfn_contratti_set_categoria_cliente_snapshot), -32 (lo snapshot
--   is_draft_snapshot dallo stato iniziale), -33 (via is_bozza); giro 6c-bis:
--   -35 (la categoria solo alla nascita, il congelamento e' del lock).
--   Brief: brief-db-stati-documento-dal-vocabolario, giro 6c (S-2, D-BOZZA (a)).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la capability dice can_edit_righe dal lock delle righe;
--   - la categoria del cliente fissata nel contratto si cambia solo nello stato
--     iniziale. ⚠️ Fuori bozza parla per primo il lock della testata
--     (a05, E_DOC_CONDIZIONI_FUORI_BOZZA), non il guard della categoria (a10):
--     leggono tutti e due lo stato iniziale, e il test asserisce il rifiuto che
--     arriva davvero;
--   - il contratto in bozza (is_draft_snapshot) e' quello nello stato
--     iniziale: lo snapshot lo copia da iniziale, e is_bozza non c'e' piu';
--   - il contratto in vigore e' quello nello stato di emissione;
--   - verso lo stato di cessazione serve la data di fine arrivata;
--   - i cinque lettori non nominano i codici degli stati (presidio sulla
--     FORMA, dichiarato tale).
--
-- ⭐ LA MARCA SPOSTATA: le colonne si spostano in transazione su un altro
--   stato, e la risposta deve seguirle. Ogni marca ha il suo contrasto, letto
--   prima dello spostamento, e si rimette al suo posto prima della successiva.
--   Gli indici unici parziali sono immediati: prima si spegne la marca di
--   partenza, poi si accende l'altra.
-- ⭐ I CASI SI COSTRUISCONO, dalle strade dell'applicazione: i contratti dal
--   builder (un cliente ciascuno: l'esclusivita' del periodo non scatta), i
--   passaggi dal verbo vendite.fn_cambia_stato_contratto con l'azione del
--   passaggio concessa all'operatore. Nessuno skip.
--
-- Elenco test (plan 14):
--   1) contrasto: can_edit_righe vero in bozza, falso nell'attivo
--   2) contrasto: il contratto in vigore per il cliente dell'attivo e' lui
--   3) contrasto: la categoria si cambia in bozza, non nell'attivo
--   4) contrasto: is_draft_snapshot vero in bozza, falso nell'attivo
--   5) contrasto: la bozza si annulla senza data di fine
--   6) forma: i cinque lettori non nominano i codici degli stati
--   7) forma: config.stati_doc_contratti non ha piu' is_bozza
--   8) ⭐ iniziale su ATTIVO: can_edit_righe falso in DRAFT, vero nell'attivo
--   9) ⭐ ... la categoria dell'attivo si cambia, quella della DRAFT no
--  10) ⭐ ... e scritto l'attivo, il suo is_draft_snapshot e' vero
--  11) ⭐ emissione su DRAFT: il contratto in vigore e' la DRAFT, non l'attivo
--  12) ⭐ cessazione su ANNULLATO: la bozza senza data di fine non si annulla
--  13) forma: il guard della categoria e' ritirato (giro 6c-bis, -35): il trigger
--      e' solo BEFORE INSERT e la funzione non solleva piu' il codice
--  14) alla nascita, senza categoria, il contratto la prende dal billing account
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE t_con (caso    text PRIMARY KEY,   -- l'etichetta del test
                         id      bigint,             -- vendite.contratti.id
                         ba      bigint,             -- anagrafiche.billing_account.id
                         utility integer);           -- config.utilities.id

INSERT INTO t_con
SELECT c.caso, k.contratto_id, k.billing_account_id, k.utility_id
  FROM (VALUES ('bozza', 'DRAFT'), ('attivo', 'ATTIVO'),
               ('annulla_contrasto', 'DRAFT'), ('annulla_marca', 'DRAFT')) c(caso, stato)
 CROSS JOIN LATERAL dbops.fn_pgtap_crea_contratto(
                        'stati dal vocabolario, ' || c.caso, c.stato,
                        p_valido_dal => script.fn_data_operativa()) k;

CREATE FUNCTION pg_temp.c(p_caso text)   -- text: l'etichetta del test
RETURNS vendite.contratti.id%TYPE LANGUAGE sql STABLE AS $$
    SELECT id FROM t_con WHERE caso = p_caso
$$;

CREATE FUNCTION pg_temp.cap(p_caso text, p_chiave text)   -- text: etichetta e chiave del blob
RETURNS text LANGUAGE sql STABLE AS $$                    -- text: un valore del blob jsonb
    SELECT script.fn_available_actions_contratto(pg_temp.c(p_caso)) ->> p_chiave
$$;

-- Il contratto in vigore per il cliente e la fornitura di un caso, oggi.
CREATE FUNCTION pg_temp.in_vigore(p_caso text)   -- text: l'etichetta del test
RETURNS vendite.contratti.id%TYPE LANGUAGE sql STABLE AS $$
    SELECT vendite.fn_get_contratto_attivo(t.ba, t.utility, script.fn_data_operativa())
      FROM t_con t WHERE t.caso = p_caso
$$;

-- Cambia la categoria fissata nel contratto con un'altra del catalogo.
-- Rende cio' che l'ha rifiutato (NULL se passa).
CREATE FUNCTION pg_temp.cambia_categoria(p_caso text)   -- text: l'etichetta del test
RETURNS text LANGUAGE sql AS $$                         -- text: un codice d'errore, nessuna colonna
    SELECT dbops.fn_pgtap_codice_errore(format(
        'UPDATE vendite.contratti SET categoria_cliente_id_snapshot = %s WHERE id = %s',
        (SELECT cc.id FROM anagrafiche.categorie_clienti cc
          WHERE cc.id IS DISTINCT FROM (SELECT k.categoria_cliente_id_snapshot
                                          FROM vendite.contratti k WHERE k.id = pg_temp.c(p_caso))
          ORDER BY cc.id LIMIT 1),
        pg_temp.c(p_caso)))
$$;

-- Il passaggio dal verbo del contratto: porta e guard veri. L'azione del
-- passaggio si concede all'operatore. Rende cio' che l'ha rifiutato (NULL se
-- passa).
CREATE FUNCTION pg_temp.passa(p_id vendite.contratti.id%TYPE,
                              p_codice config.stati_doc_contratti.codice_interno%TYPE)
RETURNS text LANGUAGE plpgsql AS $$   -- text: un codice d'errore o un vincolo, nessuna colonna
DECLARE
    v_azione config.azioni_processo.permission_codename%TYPE;
    v_utente config.user_override_azioni.auth_user_id%TYPE;
BEGIN
    SELECT x.azione_processo_codename INTO v_azione
      FROM vendite.contratti k
     CROSS JOIN LATERAL script.fn_doc_passaggio(
                'vendite.contratti'::regclass, k.stato_doc_contratto_id,
                (SELECT s.id FROM config.stati_doc_contratti s WHERE s.codice_interno = p_codice)) x
     WHERE k.id = p_id;
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    IF v_azione IS NOT NULL AND v_utente IS NOT NULL THEN
        PERFORM dbops.fn_pgtap_concedi_azione(v_utente, v_azione);
    END IF;
    RETURN dbops.fn_pgtap_codice_errore(format(
        'SELECT * FROM vendite.fn_cambia_stato_contratto(%s, %L)', p_id, p_codice));
END
$$;

-- ============================================================
-- 1-5) I contrasti, col vocabolario del seed
-- ============================================================
SELECT is(
    concat_ws(' ', pg_temp.cap('bozza', 'can_edit_righe'), pg_temp.cap('attivo', 'can_edit_righe')),
    'true false',
    '1. contrasto: can_edit_righe vero in bozza, falso nello stato di emissione'
);

SELECT is(
    pg_temp.in_vigore('attivo'),
    pg_temp.c('attivo'),
    '2. contrasto: per il cliente e la fornitura dell''attivo, il contratto in vigore e'' lui'
);

SELECT is(
    concat_ws('|', COALESCE(pg_temp.cambia_categoria('bozza'), 'passa'),
                   pg_temp.cambia_categoria('attivo')),
    'passa|E_DOC_CONDIZIONI_FUORI_BOZZA',
    '3. contrasto: la categoria si cambia in bozza, non nell''attivo (parla il lock della testata)'
);

SELECT is(
    concat_ws(' ', (SELECT is_draft_snapshot FROM vendite.contratti WHERE id = pg_temp.c('bozza'))::text,
                   (SELECT is_draft_snapshot FROM vendite.contratti WHERE id = pg_temp.c('attivo'))::text),
    'true false',
    '4. contrasto: is_draft_snapshot vero in bozza, falso nell''attivo'
);

SELECT is(
    COALESCE(pg_temp.passa(pg_temp.c('annulla_contrasto'), 'ANNULLATO'), 'passa'),
    'passa',
    '5. contrasto: la bozza si annulla senza data di fine'
);

-- ============================================================
-- 6-7) La forma — presidio sulla FORMA, dichiarato tale
-- ============================================================
-- ⚠️ Prova che i codici non sono scritti nei corpi (commenti tolti), non che
--   il comportamento sia giusto: quello lo provano gli altri test.
SELECT is(
    ARRAY(
        SELECT p.oid::regprocedure::text
          FROM pg_proc p
         WHERE p.oid IN ('script.fn_available_actions_contratto(bigint)'::regprocedure,
                         'vendite.fn_get_contratto_attivo(bigint,integer,date)'::regprocedure,
                         'vendite.trgfn_contratti_freeze_listino_versione()'::regprocedure,
                         'vendite.trgfn_contratti_guard_transizione_stato()'::regprocedure,
                         'vendite.trgfn_contratti_set_categoria_cliente_snapshot()'::regprocedure)
           AND regexp_replace(pg_get_functiondef(p.oid), '--[^\n]*', '', 'g')
               ~ '''(DRAFT|ATTIVO|CESSATO|ANNULLATO)'''
         ORDER BY 1),
    ARRAY[]::text[],
    '6. forma: capability, contratto in vigore, freeze, guard e categoria non nominano i codici degli stati'
);

SELECT hasnt_column('config', 'stati_doc_contratti', 'is_bozza',
    '7. forma: config.stati_doc_contratti non ha piu'' is_bozza: la bozza e'' lo stato iniziale');

-- ============================================================
-- 8-10) ⭐ La marca spostata: iniziale su ATTIVO
-- ============================================================
UPDATE config.stati_doc_contratti SET iniziale = false WHERE codice_interno = 'DRAFT';
UPDATE config.stati_doc_contratti SET iniziale = true  WHERE codice_interno = 'ATTIVO';

SELECT is(
    concat_ws(' ', pg_temp.cap('bozza', 'can_edit_righe'), pg_temp.cap('attivo', 'can_edit_righe')),
    'false true',
    '8. con iniziale su ATTIVO, can_edit_righe e'' falso in DRAFT e vero nell''attivo'
);

SELECT is(
    concat_ws('|', COALESCE(pg_temp.cambia_categoria('attivo'), 'passa'),
                   pg_temp.cambia_categoria('bozza')),
    'passa|E_DOC_CONDIZIONI_FUORI_BOZZA',
    '9. ... la categoria dell''attivo si cambia, quella della DRAFT no'
);

-- La scrittura del 9 ha ripassato lo snapshot sull'attivo.
SELECT is(
    (SELECT is_draft_snapshot FROM vendite.contratti WHERE id = pg_temp.c('attivo')),
    true,
    '10. ... e scritto l''attivo, il suo is_draft_snapshot segue lo stato iniziale: e'' vero'
);

UPDATE config.stati_doc_contratti SET iniziale = false WHERE codice_interno = 'ATTIVO';
UPDATE config.stati_doc_contratti SET iniziale = true  WHERE codice_interno = 'DRAFT';

-- ============================================================
-- 11) ⭐ La marca spostata: emissione su DRAFT
-- ============================================================
UPDATE config.stati_doc_contratti SET emissione = false WHERE codice_interno = 'ATTIVO';
UPDATE config.stati_doc_contratti SET emissione = true  WHERE codice_interno = 'DRAFT';

SELECT is(
    concat_ws(' ', (pg_temp.in_vigore('bozza') = pg_temp.c('bozza'))::text,
                   COALESCE(pg_temp.in_vigore('attivo')::text, 'nessuno')),
    'true nessuno',
    '11. con emissione su DRAFT, il contratto in vigore e'' la DRAFT, e l''attivo non lo e'' piu'''
);

UPDATE config.stati_doc_contratti SET emissione = false WHERE codice_interno = 'DRAFT';
UPDATE config.stati_doc_contratti SET emissione = true  WHERE codice_interno = 'ATTIVO';

-- ============================================================
-- 12) ⭐ La marca spostata: cessazione su ANNULLATO
-- ============================================================
UPDATE config.stati_doc_contratti SET cessazione = false WHERE codice_interno = 'CESSATO';
UPDATE config.stati_doc_contratti SET cessazione = true  WHERE codice_interno = 'ANNULLATO';

SELECT is(
    pg_temp.passa(pg_temp.c('annulla_marca'), 'ANNULLATO'),
    'E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA',
    '12. con cessazione su ANNULLATO, la bozza senza data di fine non ci va: la condizione segue la marca'
);

-- ============================================================
-- 13-14) Il guard della categoria ritirato (giro 6c-bis)
-- ============================================================
UPDATE config.stati_doc_contratti SET cessazione = false WHERE codice_interno = 'ANNULLATO';
UPDATE config.stati_doc_contratti SET cessazione = true  WHERE codice_interno = 'CESSATO';

SELECT ok(
    EXISTS (SELECT 1 FROM pg_trigger t
             WHERE t.tgrelid = 'vendite.contratti'::regclass
               AND t.tgfoid  = 'vendite.trgfn_contratti_set_categoria_cliente_snapshot()'::regprocedure
               AND NOT t.tgisinternal)
    AND NOT EXISTS (SELECT 1 FROM pg_trigger t
                     WHERE t.tgrelid = 'vendite.contratti'::regclass
                       AND t.tgfoid  = 'vendite.trgfn_contratti_set_categoria_cliente_snapshot()'::regprocedure
                       AND (t.tgtype & 16) <> 0)                 -- 16: UPDATE
    AND regexp_replace(pg_get_functiondef('vendite.trgfn_contratti_set_categoria_cliente_snapshot()'::regprocedure),
                       '--[^\n]*', '', 'g') !~ 'E_CONTRATTO_CATEGORIA_SNAPSHOT_IMMUTABILE',
    '13. forma: il trigger della categoria e'' solo BEFORE INSERT, e la funzione non solleva piu'' il codice ritirato'
);

SELECT is(
    (SELECT k.categoria_cliente_id_snapshot FROM vendite.contratti k WHERE k.id = pg_temp.c('annulla_marca')),
    (SELECT ba.categoria_cliente_id FROM anagrafiche.billing_account ba
      WHERE ba.id = (SELECT t.ba FROM t_con t WHERE t.caso = 'annulla_marca')),
    '14. alla nascita, senza categoria, il contratto la prende dal billing account'
);

SELECT * FROM finish();

ROLLBACK;
