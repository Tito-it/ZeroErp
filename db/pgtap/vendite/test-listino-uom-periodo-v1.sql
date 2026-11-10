-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'unita' di un prezzo di listino si converte per l'articolo in ogni giorno
--   del periodo della versione, da tutti e tre i lati (D25, Q24, Q27).
--   - la riga: vendite.trgfn_listini_righe_guard_uom_periodo;
--   - il periodo: vendite.trgfn_listini_versioni_guard_uom_periodo, e per una
--     bozza l'attivazione (script.fn_check_versione_listino_attivabile, motivo 4);
--   - il catalogo: catalogo.trgfn_uom_guard_listini_attivi, con
--     vendite.fn_listini_attivi_uom_non_convertibili.
--
-- Elenco test (plan 18):
--  1) riga nuova in bozza, unita' senza conversione -> E_LISTINO_UOM_NON_CONVERTIBILE
--  2) riga nuova in bozza, unita' mappata per tutto il periodo: passa
--  3) riga nuova in bozza aperta, mappatura che finisce fra trenta giorni:
--     rifiutata, col primo giorno scoperto
--  4) rettifica in una versione ATTIVA, unita' senza conversione: rifiutata
--  5) bozza allungata oltre la fine della mappatura: rifiutata
--  6) bozza allungata dentro la mappatura: passa
--  7) bozza accorciata: passa
--  8) una mappatura futura usata solo da una bozza si toglie (il terzo lato conta
--     le ATTIVE)
--  9) dopo: la bozza rotta dal catalogo non si attiva, motivo 4
-- 10) dopo: il verbo d'attivazione la rifiuta -> E_LISTINO_UOM_NON_CONVERTIBILE
-- 11) dopo: la sua riga spenta non si riaccende
-- 12) il lettore, chiusa a ieri la mappatura di un prezzo ATTIVO: la riga, nel
--     perimetro
-- 13) la stessa chiusura -> E_UOM_CHIUSURA_CON_LISTINI_ATTIVI
-- 14) chiudi a ieri e inserisci da oggi, a vincoli differiti: passa
-- 15) chiusura della conversione generale di un prezzo ATTIVO: rifiutata
-- 16) il lettore, mappatura di un prezzo in un listino di un'altra azienda: la sola
--     esistenza (nessuna riga, fuori perimetro)
-- 17) la sua chiusura: rifiutata, coi prezzi che non si vedono contati
-- 18) una mappatura usata solo da una bozza si chiude
--
-- Scopo:
--  - Q24: prima la regola stava solo nel backend (BE17), alla decorrenza della
--    versione. Q27: il catalogo che cambia sotto un listino attivo si rifiuta.
--
-- Mondo: due aziende costruite (MIA, ALTRUI); unita', mappature, conversioni e
--   articoli costruiti; un listino per azienda, versioni costruite qui (date
--   relative al giorno aziendale).
-- ------------------------------------------------------------

BEGIN;

-- Le due aziende si costruiscono PRIMA del contesto.
CREATE TEMP TABLE tmp_lu_mondi AS
SELECT 'MIA'    AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'ALTRUI' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Una utility che ammette una tipologia di listino (fn_pgtap_crea_listino la pretende).
CREATE TEMP TABLE tmp_lu_ut AS
SELECT min(u.id) AS u
  FROM config.utilities u
 WHERE EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                WHERE ltu.utility_id = u.id AND ltu.attivo);

CREATE OR REPLACE FUNCTION pg_temp.oggi() RETURNS date LANGUAGE sql STABLE AS
$fx$ SELECT script.fn_data_operativa() $fx$;

-- Scopo: il messaggio intero di un codice, coi segnaposto come jolly, per throws_like.
CREATE OR REPLACE FUNCTION pg_temp.msg(p_codice text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT '%' || replace(m.messaggio, '%s', '%') || '%' FROM config.messaggi_errore m
   WHERE m.codice = p_codice AND m.lingua = 'it'
$fx$;

CREATE OR REPLACE FUNCTION pg_temp.unita(p_codice text, p_tipo text) RETURNS bigint
LANGUAGE sql AS $fx$
    INSERT INTO catalogo.unita_misura (codice, descrizione, tipo_uom_id)
    SELECT p_codice, p_codice, t.id FROM catalogo.uom_tipi t WHERE t.codice_interno = p_tipo
    RETURNING id
$fx$;

CREATE TEMP TABLE tmp_lu_u AS
SELECT v.k, pg_temp.unita('PGTLU-' || v.k, v.t) AS id
  FROM (VALUES ('G', 'MASSA'), ('KG', 'MASSA'),
               ('CRT', 'IMBALLAGGIO'), ('PAL', 'IMBALLAGGIO'), ('Q', 'IMBALLAGGIO'),
               ('CRT2', 'IMBALLAGGIO')) v(k, t);

CREATE OR REPLACE FUNCTION pg_temp.u(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_lu_u WHERE k = p $fx$;

-- ============================================================
-- Il lato ALTRUI: il listino, con un prezzo di C in CRT2.
-- ============================================================
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM tmp_lu_mondi WHERE lato = 'ALTRUI'));
END $ctx$;

-- Una versione chiusa nel passato: le versioni del test non le si sovrappongono.
CREATE TEMP TABLE tmp_lu_l_altrui AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT u FROM tmp_lu_ut), 'uom altrui',
                                          pg_temp.oggi() - 200, pg_temp.oggi() - 150);

-- Articoli: comuni a tutte le aziende, della tipologia del listino, base G.
CREATE TEMP TABLE tmp_lu_art AS
SELECT v.s, dbops.fn_pgtap_crea_articolo('PGTLU-' || v.s,
         p_uom_id               => pg_temp.u('G'),
         p_listino_tipologia_id => (SELECT tipologia_id FROM tmp_lu_l_altrui)) AS id
  FROM (VALUES ('A'), ('B'), ('C'), ('S')) v(s);

CREATE OR REPLACE FUNCTION pg_temp.art(p text) RETURNS uuid LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_lu_art WHERE s = p $fx$;

-- Le mappature: A in CRT (aperta), in PAL (fino a fra trenta giorni), in Q (futura);
--   C in CRT2 (aperta). La conversione generale KG -> G (aperta).
CREATE TEMP TABLE tmp_lu_m AS
WITH ins AS (
  INSERT INTO catalogo.articoli_uom_operativa (articolo_id, uom_id, factor_to_base, valido_dal, valido_al)
  SELECT pg_temp.art(v.a), pg_temp.u(v.k), v.f, pg_temp.oggi() + v.dal, pg_temp.oggi() + v.al
    FROM (VALUES ('A', 'CRT', 6, -30, NULL::integer), ('A', 'PAL', 10, -30, 30),
                 ('A', 'Q', 2, 1, NULL), ('C', 'CRT2', 3, -30, NULL)) v(a, k, f, dal, al)
  RETURNING id, articolo_id, uom_id)
SELECT a.s || '-' || u.k AS k, ins.id
  FROM ins JOIN tmp_lu_art a ON a.id = ins.articolo_id JOIN tmp_lu_u u ON u.id = ins.uom_id;

CREATE OR REPLACE FUNCTION pg_temp.m(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_lu_m WHERE k = p $fx$;

CREATE TEMP TABLE tmp_lu_c AS
WITH ins AS (
  INSERT INTO catalogo.unita_misura_conversioni (uom_from_id, uom_to_id, fattore, valido_dal)
  VALUES (pg_temp.u('KG'), pg_temp.u('G'), 1000, pg_temp.oggi() - 30)
  RETURNING id)
SELECT id FROM ins;

-- Scopo: una versione di listino in bozza, con la riga d'appoggio (la check
--   d'attivazione vuole un prezzo).
CREATE OR REPLACE FUNCTION pg_temp.versione(p_listino bigint, p_cod text, p_dal date, p_al date)
RETURNS bigint LANGUAGE plpgsql AS $fx$
DECLARE v bigint;
BEGIN
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al)
    VALUES (p_listino, p_cod, p_dal, p_al) RETURNING id INTO v;
    PERFORM dbops.fn_pgtap_listino_aggiungi_articoli(v, ARRAY[pg_temp.art('S')], 10);
    RETURN v;
END $fx$;

-- Scopo: il prezzo dell'articolo p_a nell'unita' p_u, nella versione p_v.
CREATE OR REPLACE FUNCTION pg_temp.riga_sql(p_v bigint, p_a text, p_u text) RETURNS text
LANGUAGE sql STABLE AS $fx$
    SELECT format('INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
                   VALUES (%s, %L, %s, 10)', p_v, pg_temp.art(p_a), pg_temp.u(p_u))
$fx$;

CREATE TEMP TABLE tmp_lu_ver (k text, id bigint);

DO $fx$
DECLARE v bigint;
BEGIN
    v := pg_temp.versione((SELECT listino_id FROM tmp_lu_l_altrui), 'PGTLU_ALT', pg_temp.oggi() - 20, NULL);
    EXECUTE pg_temp.riga_sql(v, 'C', 'CRT2');
    PERFORM vendite.fn_attiva_versione_listino(v);
    INSERT INTO tmp_lu_ver VALUES ('ALT', v);
END $fx$;

-- ============================================================
-- Il lato MIA.
-- ============================================================
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM tmp_lu_mondi WHERE lato = 'MIA'));
END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

CREATE TEMP TABLE tmp_lu_l_mio AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT u FROM tmp_lu_ut), 'uom mio',
                                          pg_temp.oggi() - 200, pg_temp.oggi() - 150);

DO $fx$
DECLARE v bigint;
BEGIN
    -- ATT: ATTIVA da venti giorni fa, aperta: A in CRT, B in KG.
    v := pg_temp.versione((SELECT listino_id FROM tmp_lu_l_mio), 'PGTLU_ATT', pg_temp.oggi() - 20, NULL);
    EXECUTE pg_temp.riga_sql(v, 'A', 'CRT');
    EXECUTE pg_temp.riga_sql(v, 'B', 'KG');
    PERFORM vendite.fn_attiva_versione_listino(v);
    INSERT INTO tmp_lu_ver VALUES ('ATT', v);

    -- BOZ0: bozza da oggi, aperta, senza prezzi oltre l'appoggio.
    v := pg_temp.versione((SELECT listino_id FROM tmp_lu_l_mio), 'PGTLU_BOZ0', pg_temp.oggi(), NULL);
    INSERT INTO tmp_lu_ver VALUES ('BOZ0', v);

    -- BOZ1: bozza fra dieci e venti giorni: A in PAL.
    v := pg_temp.versione((SELECT listino_id FROM tmp_lu_l_mio), 'PGTLU_BOZ1', pg_temp.oggi() + 10, pg_temp.oggi() + 20);
    EXECUTE pg_temp.riga_sql(v, 'A', 'PAL');
    INSERT INTO tmp_lu_ver VALUES ('BOZ1', v);

    -- BOZ2: bozza da dopodomani, aperta: A in Q.
    v := pg_temp.versione((SELECT listino_id FROM tmp_lu_l_mio), 'PGTLU_BOZ2', pg_temp.oggi() + 2, NULL);
    EXECUTE pg_temp.riga_sql(v, 'A', 'Q');
    INSERT INTO tmp_lu_ver VALUES ('BOZ2', v);
END $fx$;

CREATE OR REPLACE FUNCTION pg_temp.ver(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_lu_ver WHERE k = p $fx$;

-- Scopo: che cosa dice il lettore dei listini attivi DOPO un'istruzione sul
--   catalogo, a vincoli differiti; poi l'istruzione si annulla.
CREATE OR REPLACE FUNCTION pg_temp.lettore_dopo(p_sql text, p_art text, p_uom text, p_altra text)
RETURNS jsonb LANGUAGE plpgsql AS $fx$
DECLARE v jsonb;
BEGIN
    BEGIN
        EXECUTE 'SET CONSTRAINTS ALL DEFERRED';
        EXECUTE p_sql;
        SELECT jsonb_agg(jsonb_build_object('riga', x.riga_id IS NOT NULL, 'perimetro', x.nel_perimetro))
          INTO v
          FROM vendite.fn_listini_attivi_uom_non_convertibili(pg_temp.art(p_art), pg_temp.u(p_uom),
                                                              pg_temp.u(p_altra)) x;
        RAISE EXCEPTION 'pgtap-annulla';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'pgtap-annulla' THEN RAISE; END IF;
    END;
    EXECUTE 'SET CONSTRAINTS ALL IMMEDIATE';
    RETURN v;
END $fx$;

-- ============================================================
-- Il primo lato: la riga.
-- ============================================================

-- 1
SELECT throws_like(pg_temp.riga_sql(pg_temp.ver('BOZ0'), 'B', 'CRT'),
    pg_temp.msg('E_LISTINO_UOM_NON_CONVERTIBILE'),
    '1) riga nuova in bozza, unita'' senza conversione: rifiutata');

-- 2
SELECT lives_ok(pg_temp.riga_sql(pg_temp.ver('BOZ0'), 'A', 'CRT'),
    '2) riga nuova in bozza, unita'' mappata per tutto il periodo: passa');

-- 3
SELECT throws_like(pg_temp.riga_sql(pg_temp.ver('BOZ0'), 'A', 'PAL'),
    '%' || to_char(pg_temp.oggi() + 31, 'DD/MM/YYYY') || '%',
    '3) bozza aperta, mappatura che finisce fra trenta giorni: rifiutata dal giorno dopo');

-- 4
SELECT throws_like(pg_temp.riga_sql(pg_temp.ver('ATT'), 'B', 'CRT'),
    pg_temp.msg('E_LISTINO_UOM_NON_CONVERTIBILE'),
    '4) rettifica in una versione ATTIVA, unita'' senza conversione: rifiutata');

-- ============================================================
-- Il secondo lato: il periodo.
-- ============================================================

-- 5
SELECT throws_like(
    format('UPDATE vendite.listini_versioni SET valido_al = %L WHERE id = %s',
           pg_temp.oggi() + 40, pg_temp.ver('BOZ1')),
    pg_temp.msg('E_LISTINO_UOM_NON_CONVERTIBILE'),
    '5) bozza allungata oltre la fine della mappatura del suo prezzo: rifiutata');

-- 6
SELECT lives_ok(
    format('UPDATE vendite.listini_versioni SET valido_al = %L WHERE id = %s',
           pg_temp.oggi() + 25, pg_temp.ver('BOZ1')),
    '6) bozza allungata dentro la mappatura: passa');

-- 7
SELECT lives_ok(
    format('UPDATE vendite.listini_versioni SET valido_al = %L WHERE id = %s',
           pg_temp.oggi() + 15, pg_temp.ver('BOZ1')),
    '7) bozza accorciata: passa');

-- 8
SELECT lives_ok(
    format('DELETE FROM catalogo.articoli_uom_operativa WHERE id = %s', pg_temp.m('A-Q')),
    '8) una mappatura futura usata solo da una bozza si toglie');

-- 9
SELECT is(script.fn_check_versione_listino_attivabile(pg_temp.ver('BOZ2')) -> 0 ->> 'codice',
          'E_LISTINO_UOM_NON_CONVERTIBILE',
    '9) dopo: la bozza rotta dal catalogo non si attiva (motivo 4)');

-- 10
SELECT throws_like(
    format('SELECT vendite.fn_attiva_versione_listino(%s)', pg_temp.ver('BOZ2')),
    pg_temp.msg('E_LISTINO_UOM_NON_CONVERTIBILE'),
    '10) dopo: il verbo d''attivazione la rifiuta');

-- 11
UPDATE vendite.listini_righe SET attivo = false
 WHERE listino_versione_id = pg_temp.ver('BOZ2') AND uom_id = pg_temp.u('Q');
SELECT throws_like(
    format('UPDATE vendite.listini_righe SET attivo = true WHERE listino_versione_id = %s AND uom_id = %s',
           pg_temp.ver('BOZ2'), pg_temp.u('Q')),
    pg_temp.msg('E_LISTINO_UOM_NON_CONVERTIBILE'),
    '11) dopo: la sua riga spenta non si riaccende');

-- ============================================================
-- Il terzo lato: il catalogo.
-- ============================================================

-- 12
SELECT is(
    pg_temp.lettore_dopo(
        format('UPDATE catalogo.articoli_uom_operativa SET valido_al = %L WHERE id = %s',
               pg_temp.oggi() - 1, pg_temp.m('A-CRT')),
        'A', 'CRT', NULL),
    '[{"riga": true, "perimetro": true}]'::jsonb,
    '12) il lettore: chiusa a ieri la mappatura di un prezzo ATTIVO, la riga nel perimetro');

-- 13
SELECT throws_like(
    format('UPDATE catalogo.articoli_uom_operativa SET valido_al = %L WHERE id = %s',
           pg_temp.oggi() - 1, pg_temp.m('A-CRT')),
    pg_temp.msg('E_UOM_CHIUSURA_CON_LISTINI_ATTIVI'),
    '13) la stessa chiusura: rifiutata');

-- 14
SELECT lives_ok(
    format($s$SET CONSTRAINTS ALL DEFERRED;
              UPDATE catalogo.articoli_uom_operativa SET valido_al = %L WHERE id = %s;
              INSERT INTO catalogo.articoli_uom_operativa (articolo_id, uom_id, factor_to_base, valido_dal)
              VALUES (%L, %s, 12, %L);
              SET CONSTRAINTS ALL IMMEDIATE$s$,
           pg_temp.oggi() - 1, pg_temp.m('A-CRT'), pg_temp.art('A'), pg_temp.u('CRT'), pg_temp.oggi()),
    '14) chiudi a ieri e inserisci da oggi, a vincoli differiti: passa');

-- 15
SELECT throws_like(
    format('UPDATE catalogo.unita_misura_conversioni SET valido_al = %L WHERE id = %s',
           pg_temp.oggi() - 1, (SELECT id FROM tmp_lu_c)),
    pg_temp.msg('E_UOM_CHIUSURA_CON_LISTINI_ATTIVI'),
    '15) chiusura della conversione generale di un prezzo ATTIVO: rifiutata');

-- 16
SELECT is(
    pg_temp.lettore_dopo(
        format('UPDATE catalogo.articoli_uom_operativa SET valido_al = %L WHERE id = %s',
               pg_temp.oggi() - 1, pg_temp.m('C-CRT2')),
        'C', 'CRT2', NULL),
    '[{"riga": false, "perimetro": false}]'::jsonb,
    '16) il lettore, prezzo in un listino di un''altra azienda: solo l''esistenza');

-- 17
SELECT throws_like(
    format('UPDATE catalogo.articoli_uom_operativa SET valido_al = %L WHERE id = %s',
           pg_temp.oggi() - 1, pg_temp.m('C-CRT2')),
    '%(1 in listini%',
    '17) la sua chiusura: rifiutata, coi prezzi che non si vedono contati');

-- 18
SELECT lives_ok(
    format('UPDATE catalogo.articoli_uom_operativa SET valido_al = %L WHERE id = %s',
           pg_temp.oggi() - 1, pg_temp.m('A-PAL')),
    '18) una mappatura usata solo da una bozza si chiude: la bozza la giudica l''attivazione');

SELECT * FROM finish();
ROLLBACK;
