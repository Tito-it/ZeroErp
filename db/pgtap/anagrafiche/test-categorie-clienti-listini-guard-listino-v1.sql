-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la riga della matrice categoria -> listino
--   (anagrafiche.categorie_clienti_listini) punta a un listino della SUA
--   utility e del SUO emittente
--   (anagrafiche.trgfn_categorie_clienti_listini_guard_listino).
-- Riferimento: brief-db-coerenza-listino-della-riga-di-commessa §7.4, opzione B
--   di Tid (2026-10-16); changeSet 20261016-06/-07.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - il predicato e' quello di contratti e offerte
--     (script.fn_check_listino_documento), i codici sono della matrice;
--   - listino della utility e dell'emittente della riga: passa;
--   - listino di un'altra utility: E_CATEGORIA_LISTINO_UTILITY_DIVERSA;
--   - listino di un'altra azienda: E_CATEGORIA_LISTINO_EMITTENTE_DIVERSO, in
--     INSERT e in UPDATE del listino;
--   - un UPDATE che non tocca listino, utility o emittente non rilegge il
--     listino (WHEN sul trigger di UPDATE).
--
-- Fixture: due aziende costruite coi builder atomici PRIMA del contesto, come
--   vendite/test-doc-listino-documento-v1: il listino di ALTRUI lo crea ALTRUI.
--   Tre listini: MIO (U1, MIA), ALTRA_U (U2, MIA), ALTRUI (U1, ALTRUI).
--
-- Elenco test (plan 6):
--   1) i due trigger: INSERT senza WHEN, UPDATE con la WHEN sulle tre colonne
--   2) listino MIO: la riga entra
--   3) listino ALTRA_U -> E_CATEGORIA_LISTINO_UTILITY_DIVERSA
--   4) listino ALTRUI -> E_CATEGORIA_LISTINO_EMITTENTE_DIVERSO
--   5) UPDATE della riga buona verso il listino ALTRUI -> rifiutato
--   6) UPDATE della sola variazione: passa
-- ------------------------------------------------------------

BEGIN;

-- Le due aziende si costruiscono PRIMA del contesto.
CREATE TEMP TABLE tmp_cl_mondi AS
SELECT 'MIA'    AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'ALTRUI' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Due utility che ammettono una tipologia di listino (fn_pgtap_crea_listino la
-- pretende): U1 la prima, U2 un'altra.
CREATE TEMP TABLE tmp_cl_u AS
SELECT (array_agg(u.id ORDER BY u.id))[1] AS u1,
       (array_agg(u.id ORDER BY u.id))[2] AS u2
  FROM config.utilities u
 WHERE EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                WHERE ltu.utility_id = u.id AND ltu.attivo);

-- Il listino di ALTRUI lo crea ALTRUI (il guard emittente_scope di
-- vendite.listini non ne accetta un altro).
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM tmp_cl_mondi WHERE lato = 'ALTRUI'));
END $ctx$;

CREATE TEMP TABLE tmp_cl_l_altrui AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT u1 FROM tmp_cl_u), 'matrice altrui');

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM tmp_cl_mondi WHERE lato = 'MIA'));
END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

CREATE TEMP TABLE tmp_cl_l_mio AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT u1 FROM tmp_cl_u), 'matrice mio');

CREATE TEMP TABLE tmp_cl_l_altra_u AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT u2 FROM tmp_cl_u), 'matrice altra utility');

-- Una categoria PROPRIA del test.
CREATE TEMP TABLE tmp_cl_cat AS
WITH ins AS (
    INSERT INTO anagrafiche.categorie_clienti (codice, codice_interno, descrizione, partecipa_promo)
    SELECT s.sigla, s.sigla, 'Fixture pgTAP: guard listino della matrice', FALSE
      FROM (SELECT 'PGTAP-CLG-' || substr(md5(clock_timestamp()::text || random()::text), 1, 12) AS sigla) s
    RETURNING id
)
SELECT id FROM ins;

-- Scopo: il CONSTRAINT_NAME di uno statement che deve fallire (il codice di
-- script.fn_log_and_raise_error), NULL se passa.
CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $fx$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $fx$;

-- Scopo: l'INSERT di una riga della matrice di MIA, utility U1, col listino dato.
CREATE OR REPLACE FUNCTION pg_temp.riga(p_listino bigint, p_dal date)
RETURNS text LANGUAGE sql STABLE AS $fx$
    SELECT format($$INSERT INTO anagrafiche.categorie_clienti_listini (
                        categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id,
                        classe_utenza_id, listino_id, valido_dal)
                    VALUES (%s, %s, %s, NULL, %s, %L)$$,
                  (SELECT id FROM tmp_cl_cat), (SELECT u1 FROM tmp_cl_u),
                  (SELECT soggetto_ruolo_id FROM tmp_cl_mondi WHERE lato = 'MIA'),
                  p_listino, p_dal);
$fx$;

-- ============================================================
-- 1) I trigger
-- ============================================================
-- tgtype: bit 2 BEFORE, bit 4 INSERT, bit 16 UPDATE.
SELECT is(
    (SELECT string_agg(
                regexp_replace(t.tgname, '^trg_categorie_clienti_listini_a10_', '')
                || ':' || CASE WHEN t.tgtype & 4 = 4 THEN 'I' ELSE '' END
                       || CASE WHEN t.tgtype & 16 = 16 THEN 'U' ELSE '' END
                || '(' || (pg_get_triggerdef(t.oid) ~* 'WHEN')::text || ')',
                ' ' ORDER BY t.tgname)
       FROM pg_trigger t
      WHERE t.tgfoid = 'anagrafiche.trgfn_categorie_clienti_listini_guard_listino()'::regprocedure),
    'guard_listino_ins:I(false) guard_listino_upd:U(true)',
    '1) i due trigger: INSERT senza WHEN, UPDATE con la WHEN'
);

-- ============================================================
-- 2-4) INSERT
-- ============================================================
SELECT lives_ok(
    pg_temp.riga((SELECT listino_id FROM tmp_cl_l_mio), script.fn_data_operativa()),
    '2) listino della utility e dell''azienda della riga: entra'
);

SELECT is(
    pg_temp.codice_errore(pg_temp.riga((SELECT listino_id FROM tmp_cl_l_altra_u), '2099-01-01')),
    'E_CATEGORIA_LISTINO_UTILITY_DIVERSA',
    '3) listino di un''altra utility -> E_CATEGORIA_LISTINO_UTILITY_DIVERSA'
);

SELECT is(
    pg_temp.codice_errore(pg_temp.riga((SELECT listino_id FROM tmp_cl_l_altrui), '2099-01-01')),
    'E_CATEGORIA_LISTINO_EMITTENTE_DIVERSO',
    '4) listino di un''altra azienda -> E_CATEGORIA_LISTINO_EMITTENTE_DIVERSO'
);

-- ============================================================
-- 5-6) UPDATE
-- ============================================================
SELECT is(
    pg_temp.codice_errore(format(
        'UPDATE anagrafiche.categorie_clienti_listini SET listino_id = %s WHERE categoria_cliente_id = %s',
        (SELECT listino_id FROM tmp_cl_l_altrui), (SELECT id FROM tmp_cl_cat))),
    'E_CATEGORIA_LISTINO_EMITTENTE_DIVERSO',
    '5) UPDATE della riga verso il listino di un''altra azienda -> E_CATEGORIA_LISTINO_EMITTENTE_DIVERSO'
);

SELECT lives_ok(
    format('UPDATE anagrafiche.categorie_clienti_listini
               SET tipo_variazione = %L, valore_variazione = 5
             WHERE categoria_cliente_id = %s',
           'PERCENTUALE', (SELECT id FROM tmp_cl_cat)),
    '6) UPDATE della sola variazione: passa'
);

SELECT * FROM finish();
ROLLBACK;
