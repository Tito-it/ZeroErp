-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- rev 2026-10-28 (brief-modello-documento-vendita §16, giro 12): la BOZZA nasce senza stato (trigger
--   della nascita); lo stato si legge dal vocabolario config.stati_doc_listino_versioni.
-- ⚠️ Attesa cambiata: test 6 (una versione non nasce CHIUSA: la nascita in uno stato diverso dallo
--   stato iniziale e' rifiutata prima del CHECK, E_DOC_STATO_INIZIALE_NON_VALIDO).
--
-- Test: un listino con storia non si spegne con l'interruttore; una versione
--   CHIUSA ha sempre la fine validita'.
--   vendite.fn_listino_ha_storia, vendite.trgfn_listini_guard_spegnimento_storia,
--   CHECK chk_listini_versioni_chiusa_con_fine.
-- Riferimento: decisione di Tid del 2026-10-21 («un listino con storia si
--   spegne solo con la fine validita'»), D-1 del 2026-10-22 (che cosa e' la
--   storia); richiesta BE §9.8 di brief-be-utenti-di-sviluppo. changeSet
--   20261022-02 … -05; codice E_LISTINO_CON_STORIA_NON_SPEGNIBILE.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - un listino HA STORIA se ha almeno una versione ATTIVA o CHIUSA; una
--     BOZZA non conta, e nemmeno l'assenza di versioni;
--   - spegnere un listino con storia e' rifiutato col codice suo (il rimedio:
--     la fine validita' alla versione), non con quello generico «figli prima»;
--   - un listino senza storia si spegne;
--   - una versione inserita gia' CHIUSA senza fine validita' e' rifiutata.
--
-- Elenco test (plan 7):
--   1) listino con una versione ATTIVA: ha storia
--   2) listino con una sola BOZZA: non ha storia
--   3) listino senza versioni: non ha storia
--   4) spegnere il listino con storia -> E_LISTINO_CON_STORIA_NON_SPEGNIBILE
--   5) spegnere il listino senza versioni: passa
--   6) versione inserita CHIUSA senza valido_al -> E_DOC_STATO_INIZIALE_NON_VALIDO
--   7) il codice e' registrato, classe CONFLITTO_STATO
--
-- ⚠️ I rifiuti si asseriscono sul CODICE (CONSTRAINT_NAME dell'eccezione, o il
--   nome del CHECK), non su un errore qualunque.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- Fixture
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' OR SQLSTATE '23514' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

CREATE TEMP TABLE t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM t_mondo));
END $ctx$;

-- Una utility che ammette una tipologia di listino (fn_pgtap_crea_listino la
-- pretende).
CREATE TEMP TABLE t_u AS
SELECT min(u.id) AS utility_id
  FROM config.utilities u
 WHERE EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                WHERE ltu.utility_id = u.id AND ltu.attivo);

-- Il listino CON storia: una versione ATTIVA.
CREATE TEMP TABLE t_storia AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_u), 'spegnimento storia');

-- Due listini SENZA storia, della stessa azienda, utility e tipologia: uno
-- con una sola BOZZA, uno senza versioni.
CREATE TEMP TABLE t_senza AS
WITH ins AS (
    INSERT INTO vendite.listini (codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP_LST_' || substr(md5(clock_timestamp()::text || random()::text || g::text), 1, 16),
           'Fixture pgTAP: listino senza storia ' || g,
           u.utility_id, s.tipologia_id, m.soggetto_ruolo_id
      FROM generate_series(1, 2) g, t_u u, t_storia s, t_mondo m
    RETURNING id
)
SELECT min(id) AS con_bozza, max(id) AS vuoto FROM ins;

INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
SELECT con_bozza, 'PGTAP_BOZZA', script.fn_data_operativa() FROM t_senza;

-- ============================================================
-- 1-3) La storia
-- ============================================================
SELECT ok(
    vendite.fn_listino_ha_storia((SELECT listino_id FROM t_storia)),
    '1) un listino con una versione ATTIVA ha storia'
);

SELECT ok(
    NOT vendite.fn_listino_ha_storia((SELECT con_bozza FROM t_senza)),
    '2) un listino con una sola BOZZA non ha storia (nessuno ci ha preso un prezzo)'
);

SELECT ok(
    NOT vendite.fn_listino_ha_storia((SELECT vuoto FROM t_senza)),
    '3) un listino senza versioni non ha storia'
);

-- ============================================================
-- 4-5) Lo spegnimento
-- ============================================================
SELECT is(
    pg_temp.codice_errore(format(
        'UPDATE vendite.listini SET attivo = false WHERE id = %s',
        (SELECT listino_id FROM t_storia))),
    'E_LISTINO_CON_STORIA_NON_SPEGNIBILE',
    '4) spegnere un listino con storia -> E_LISTINO_CON_STORIA_NON_SPEGNIBILE (prima della catena generica)'
);

UPDATE vendite.listini SET attivo = false WHERE id = (SELECT vuoto FROM t_senza);

SELECT is(
    (SELECT l.attivo FROM vendite.listini l WHERE l.id = (SELECT vuoto FROM t_senza)),
    false,
    '5) un listino senza storia si spegne'
);

-- ============================================================
-- 6) Una versione CHIUSA ha sempre la fine validita'
-- ============================================================
SELECT is(
    pg_temp.codice_errore(format(
        $$INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal,
                                                stato_doc_listino_versione_id)
          VALUES (%s, 'PGTAP_CHIUSA', DATE '2020-01-01', %s)$$,
        (SELECT con_bozza FROM t_senza),
        script.fn_doc_stato_id('vendite.listini_versioni'::regclass, 'CHIUSA'))),
    'E_DOC_STATO_INIZIALE_NON_VALIDO',
    '6) una versione inserita gia'' CHIUSA senza fine validita'' -> E_DOC_STATO_INIZIALE_NON_VALIDO (non nasce CHIUSA)'
);

-- ============================================================
-- 7) Il codice e' registrato
-- ============================================================
SELECT is(
    (SELECT ce.classe::text FROM config.codici_errore ce
      WHERE ce.codice = 'E_LISTINO_CON_STORIA_NON_SPEGNIBILE'),
    'CONFLITTO_STATO',
    '7) E_LISTINO_CON_STORIA_NON_SPEGNIBILE e'' registrato, classe CONFLITTO_STATO'
);

SELECT * FROM finish();
ROLLBACK;
