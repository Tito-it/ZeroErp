-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la chiusura di un legame di distinta coi suoi prezzi bundle
--   (catalogo.fn_chiudi_legame_distinta, vendite.fn_prezzi_legame_oltre_la_fine,
--   script.fn_check_legame_distinta_chiudibile, il guard della distinta e la porta
--   del guard d'immutabilita' dei prezzi).
--
-- Elenco test (plan 21):
--  1) il lettore: L1 chiuso a ieri tocca due prezzi, uno CHIUDE (versione ATTIVA) e
--     uno TOGLIE (bozza che comincia dopo)
--  2) la check su L1 a ieri: nessun motivo
--  3) UPDATE diretto della fine di L1 -> l'avviso E_BOM_CHIUSURA_CON_PREZZI
--  4) col solo diritto sul catalogo il verbo rifiuta un legame con prezzi
--     (E_PERMESSO_NEGATO: servono anche i listini, Q21)
--  4-bis) col diritto anche sui listini, senza conferma -> E_BOM_CHIUSURA_CON_PREZZI
--  5) il verbo con la conferma sbagliata -> E_BOM_CHIUSURA_CON_PREZZI
--  6) il verbo con la conferma giusta: un prezzo chiuso, uno tolto
--  7) dopo: il legame finisce ieri
--  8) dopo: il prezzo della versione ATTIVA finisce ieri, col prezzo di prima
--  9) dopo: il prezzo della bozza non c'e' piu'
-- 10) la porta senza il proprietario non apre: un prezzo di versione ATTIVA non si
--     accorcia dall'applicazione nemmeno con la GUC
-- 11) L2 ha un prezzo ATTIVO che comincia fra trenta giorni: la check da'
--     E_BOM_CHIUSURA_PRIMA_DEI_PREZZI con quella data
-- 12) il verbo su L2 a ieri -> E_BOM_CHIUSURA_PRIMA_DEI_PREZZI
-- 13) UPDATE diretto su L2 a ieri -> E_BOM_CHIUSURA_PRIMA_DEI_PREZZI (parla prima
--     cio' che vieta)
-- 14) il verbo su L2 al primo giorno ammesso, con la conferma: chiude
-- 15) L3 e' prezzato nel listino di un'altra azienda: il lettore ne dice solo
--     l'esistenza (nel_perimetro false, riga e prezzo NULL)
-- 16) il verbo su L3 -> E_BOM_CHIUSURA_PREZZI_ALTRE_AZIENDE
-- 17) UPDATE diretto su L3 -> E_BOM_CHIUSURA_PREZZI_ALTRE_AZIENDE
-- 18) L4 senza prezzi: il verbo chiude senza conferma (0 chiusi, 0 tolti)
-- 19) legame inesistente -> E_BOM_LEGAME_NOT_FOUND
-- 20) senza permesso (utente senza veste) -> E_PERMESSO_NEGATO
--
-- Scopo:
--  - un prezzo bundle sta dentro il periodo del suo legame (FK temporale): chiudendo
--    il legame si chiudono anche i prezzi, mai in silenzio, mai fuori dal perimetro
--    di chi chiude, mai accorciando un prezzo prima del suo inizio.
--
-- Mondo: due aziende costruite (MIA, ALTRUI); articoli e legami costruiti; un
--   listino per azienda, con versioni costruite qui (date relative al giorno
--   aziendale). I livelli d'area dell'operatore MIA li scrive il test (catalogo
--   TUTTO; vendite prima LETTURA, poi TUTTO).
--
-- ⚠️ Il test 10 e' ROSSO DA OWNER e verde come app, per costruzione: la porta si
--   apre al proprietario della tabella, e la prova prima dell'apply gira da owner.
-- ------------------------------------------------------------

BEGIN;

-- Le due aziende si costruiscono PRIMA del contesto.
CREATE TEMP TABLE tmp_cl_mondi AS
SELECT 'MIA'    AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'ALTRUI' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Una utility che ammette una tipologia di listino (fn_pgtap_crea_listino la pretende).
CREATE TEMP TABLE tmp_cl_u AS
SELECT min(u.id) AS u
  FROM config.utilities u
 WHERE EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                WHERE ltu.utility_id = u.id AND ltu.attivo);

CREATE OR REPLACE FUNCTION pg_temp.oggi() RETURNS date LANGUAGE sql STABLE AS
$fx$ SELECT script.fn_data_operativa() $fx$;

-- Scopo: il prefisso fisso del messaggio di un codice, per throws_like.
CREATE OR REPLACE FUNCTION pg_temp.msg(p_codice text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT split_part(m.messaggio, '%s', 1) || '%' FROM config.messaggi_errore m
   WHERE m.codice = p_codice AND m.lingua = 'it'
$fx$;

-- ============================================================
-- Il lato ALTRUI: il suo listino, con un prezzo bundle di L3.
-- ============================================================
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM tmp_cl_mondi WHERE lato = 'ALTRUI'));
END $ctx$;

-- Una versione chiusa nel passato: le versioni del test non le si sovrappongono.
CREATE TEMP TABLE tmp_cl_l_altrui AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT u FROM tmp_cl_u), 'legame altrui',
                                          pg_temp.oggi() - 200, pg_temp.oggi() - 150);

-- Articoli e legami: comuni a tutte le aziende, della tipologia del listino.
CREATE TEMP TABLE tmp_cl_art AS
SELECT v.s, dbops.fn_pgtap_crea_articolo('PGTAP-CLP-' || v.s,
         p_listino_tipologia_id => (SELECT tipologia_id FROM tmp_cl_l_altrui),
         p_is_composito         => v.s = 'K') AS id
  FROM (VALUES ('K'), ('F1'), ('F2'), ('F3'), ('F4'), ('S')) v(s);

CREATE OR REPLACE FUNCTION pg_temp.art(p text) RETURNS uuid LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_cl_art WHERE s = p $fx$;

CREATE TEMP TABLE tmp_cl_leg AS
WITH ins AS (
  INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)
  SELECT pg_temp.art('K'), pg_temp.art(v.f), 2, pg_temp.oggi() - 100
    FROM (VALUES ('F1'), ('F2'), ('F3'), ('F4')) v(f)
  RETURNING id, componente_id)
SELECT 'L' || substr(a.s, 2) AS l, ins.id
  FROM ins JOIN tmp_cl_art a ON a.id = ins.componente_id;

CREATE OR REPLACE FUNCTION pg_temp.leg(p text) RETURNS uuid LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_cl_leg WHERE l = p $fx$;

-- Scopo: una versione di listino in bozza, con la riga d'appoggio (la check
--   d'attivazione vuole un prezzo).
CREATE OR REPLACE FUNCTION pg_temp.versione(p_listino bigint, p_cod text, p_dal date)
RETURNS bigint LANGUAGE plpgsql AS $fx$
DECLARE v bigint;
BEGIN
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
    VALUES (p_listino, p_cod, p_dal) RETURNING id INTO v;
    PERFORM dbops.fn_pgtap_listino_aggiungi_articoli(v, ARRAY[pg_temp.art('S')], 10);
    RETURN v;
END $fx$;

-- Scopo: un prezzo bundle del legame p_l nella versione p_v, dal p_dal, aperto.
CREATE OR REPLACE FUNCTION pg_temp.prezzo(p_v bigint, p_l text, p_dal date, p_prezzo numeric)
RETURNS bigint LANGUAGE sql AS $fx$
    INSERT INTO vendite.listini_righe_componenti
        (listino_versione_id, articolo_componente_id, articolo_padre_id, articolo_figlio_id,
         prezzo, valido_dal)
    SELECT p_v, ac.id, ac.prodotto_id, ac.componente_id, p_prezzo, p_dal
      FROM catalogo.articoli_componenti ac
     WHERE ac.id = pg_temp.leg(p_l)
    RETURNING id
$fx$;

CREATE TEMP TABLE tmp_cl_ver (k text, id bigint);
CREATE TEMP TABLE tmp_cl_pr  (k text, id bigint);

DO $fx$
DECLARE v bigint;
BEGIN
    v := pg_temp.versione((SELECT listino_id FROM tmp_cl_l_altrui), 'PGTAP_ALT', pg_temp.oggi() - 50);
    INSERT INTO tmp_cl_pr VALUES ('P_ALT_L3', pg_temp.prezzo(v, 'L3', pg_temp.oggi() - 50, 7));
    PERFORM vendite.fn_attiva_versione_listino(v);
    INSERT INTO tmp_cl_ver VALUES ('ALT', v);
END $fx$;

-- ============================================================
-- Il lato MIA: il listino con una versione ATTIVA e una bozza dopo.
-- ============================================================
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM tmp_cl_mondi WHERE lato = 'MIA'));
END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(21);

CREATE TEMP TABLE tmp_cl_l_mio AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT u FROM tmp_cl_u), 'legame mio',
                                          pg_temp.oggi() - 200, pg_temp.oggi() - 150);

DO $fx$
DECLARE v bigint;
BEGIN
    -- ATT: ATTIVA da cinquanta giorni fa, aperta. L1 dal suo inizio; L2 fra trenta giorni.
    v := pg_temp.versione((SELECT listino_id FROM tmp_cl_l_mio), 'PGTAP_ATT', pg_temp.oggi() - 50);
    INSERT INTO tmp_cl_pr VALUES ('P_ATT_L1', pg_temp.prezzo(v, 'L1', pg_temp.oggi() - 50, 11));
    INSERT INTO tmp_cl_pr VALUES ('P_ATT_L2', pg_temp.prezzo(v, 'L2', pg_temp.oggi() + 30, 13));
    PERFORM vendite.fn_attiva_versione_listino(v);
    INSERT INTO tmp_cl_ver VALUES ('ATT', v);

    -- BOZ: in bozza, fra sessanta giorni. L1 dal suo inizio.
    v := pg_temp.versione((SELECT listino_id FROM tmp_cl_l_mio), 'PGTAP_BOZ', pg_temp.oggi() + 60);
    INSERT INTO tmp_cl_pr VALUES ('P_BOZ_L1', pg_temp.prezzo(v, 'L1', pg_temp.oggi() + 60, 17));
    INSERT INTO tmp_cl_ver VALUES ('BOZ', v);
END $fx$;

CREATE OR REPLACE FUNCTION pg_temp.pr(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_cl_pr WHERE k = p $fx$;

-- Scopo: il livello su un'area dell'operatore MIA, come lo scrive il pannello dei
--   permessi. L'operatore costruito non ha il catalogo, e ha gia' la sua riga sulle
--   vendite: si scrive o si cambia.
CREATE OR REPLACE FUNCTION pg_temp.livello_area(p_area text, p_livello text) RETURNS void
LANGUAGE sql AS $fx$
    INSERT INTO config.user_override_aree (auth_user_id, area_id, livello, motivo)
    SELECT m.auth_user_id, af.id, p_livello::config.livello_accesso,
           'pgTAP: chiusura del legame coi prezzi'
      FROM tmp_cl_mondi m, config.aree_funzionali af
     WHERE m.lato = 'MIA' AND af.schema_db = p_area
    ON CONFLICT (auth_user_id, area_id) DO UPDATE SET livello = EXCLUDED.livello
$fx$;

SELECT pg_temp.livello_area('catalogo', 'TUTTO');
SELECT pg_temp.livello_area('vendite', 'LETTURA');

-- ============================================================
-- L1: un prezzo da chiudere, uno da togliere.
-- ============================================================

-- 1
SELECT results_eq(
    $q$ SELECT riga_id, esito, nel_perimetro
          FROM vendite.fn_prezzi_legame_oltre_la_fine(pg_temp.leg('L1'), pg_temp.oggi() - 1)
         ORDER BY riga_id $q$,
    $q$ VALUES (pg_temp.pr('P_ATT_L1'), 'CHIUDE', true),
               (pg_temp.pr('P_BOZ_L1'), 'TOGLIE', true) $q$,
    '1) il lettore: L1 a ieri tocca il prezzo ATTIVO (CHIUDE) e quello della bozza dopo (TOGLIE)');

-- 2
SELECT is(script.fn_check_legame_distinta_chiudibile(pg_temp.leg('L1'), pg_temp.oggi() - 1),
          '[]'::jsonb,
          '2) la check su L1 a ieri: nessun motivo che vieta');

-- 3
SELECT throws_like(
    format('UPDATE catalogo.articoli_componenti SET valido_al = %L WHERE id = %L',
           pg_temp.oggi() - 1, pg_temp.leg('L1')),
    pg_temp.msg('E_BOM_CHIUSURA_CON_PREZZI'),
    '3) UPDATE diretto della fine di L1: l''avviso coi prezzi');

-- 4
SELECT throws_like(
    format('SELECT * FROM catalogo.fn_chiudi_legame_distinta(%L, %L, 2)',
           pg_temp.leg('L1'), pg_temp.oggi() - 1),
    pg_temp.msg('E_PERMESSO_NEGATO'),
    '4) col solo diritto sul catalogo, un legame con prezzi non si chiude: servono anche i listini');

SELECT pg_temp.livello_area('vendite', 'TUTTO');

-- 4-bis
SELECT throws_like(
    format('SELECT * FROM catalogo.fn_chiudi_legame_distinta(%L, %L)',
           pg_temp.leg('L1'), pg_temp.oggi() - 1),
    pg_temp.msg('E_BOM_CHIUSURA_CON_PREZZI'),
    '4-bis) il verbo senza conferma: l''avviso');

-- 5
SELECT throws_like(
    format('SELECT * FROM catalogo.fn_chiudi_legame_distinta(%L, %L, 1)',
           pg_temp.leg('L1'), pg_temp.oggi() - 1),
    pg_temp.msg('E_BOM_CHIUSURA_CON_PREZZI'),
    '5) il verbo con la conferma che non corrisponde: l''avviso');

-- 6
SELECT results_eq(
    format('SELECT prezzi_chiusi, prezzi_tolti FROM catalogo.fn_chiudi_legame_distinta(%L, %L, 2)',
           pg_temp.leg('L1'), pg_temp.oggi() - 1),
    $q$ VALUES (1, 1) $q$,
    '6) il verbo con la conferma giusta: un prezzo chiuso, uno tolto');

-- 7
SELECT is((SELECT valido_al FROM catalogo.articoli_componenti WHERE id = pg_temp.leg('L1')),
          pg_temp.oggi() - 1,
          '7) il legame L1 finisce ieri');

-- 8
SELECT results_eq(
    format('SELECT valido_al, prezzo FROM vendite.listini_righe_componenti WHERE id = %s',
           pg_temp.pr('P_ATT_L1')),
    format('VALUES (%L::date, 11::numeric)', pg_temp.oggi() - 1),
    '8) il prezzo della versione ATTIVA finisce ieri, col prezzo di prima');

-- 9
SELECT is((SELECT count(*)::integer FROM vendite.listini_righe_componenti
            WHERE id = pg_temp.pr('P_BOZ_L1')),
          0,
          '9) il prezzo della bozza che cominciava dopo non c''e'' piu''');

-- 10
SELECT set_config('zeroerp.legame_distinta_chiudi', pg_temp.leg('L2')::text, true);
SELECT throws_ok(
    format('UPDATE vendite.listini_righe_componenti SET valido_al = %L WHERE id = %s',
           pg_temp.oggi() + 40, pg_temp.pr('P_ATT_L2')),
    'P0001', NULL,
    '10) la porta senza il proprietario non apre: dall''applicazione la fine di un prezzo ATTIVO non cambia');
SELECT set_config('zeroerp.legame_distinta_chiudi', '', true);

-- ============================================================
-- L2: il prezzo ATTIVO comincia fra trenta giorni.
-- ============================================================

-- 11
SELECT is(
    script.fn_check_legame_distinta_chiudibile(pg_temp.leg('L2'), pg_temp.oggi() - 1) -> 0
      -> 'dettaglio' ->> 'valido_al_min',
    (pg_temp.oggi() + 30)::text,
    '11) la check su L2 a ieri: il primo motivo da'' come prima fine l''inizio del prezzo');

-- 12
SELECT throws_like(
    format('SELECT * FROM catalogo.fn_chiudi_legame_distinta(%L, %L, 1)',
           pg_temp.leg('L2'), pg_temp.oggi() - 1),
    pg_temp.msg('E_BOM_CHIUSURA_PRIMA_DEI_PREZZI'),
    '12) il verbo su L2 a ieri: E_BOM_CHIUSURA_PRIMA_DEI_PREZZI');

-- 13
SELECT throws_like(
    format('UPDATE catalogo.articoli_componenti SET valido_al = %L WHERE id = %L',
           pg_temp.oggi() - 1, pg_temp.leg('L2')),
    pg_temp.msg('E_BOM_CHIUSURA_PRIMA_DEI_PREZZI'),
    '13) UPDATE diretto su L2 a ieri: parla prima cio'' che vieta');

-- 14
SELECT results_eq(
    format('SELECT valido_al_dopo, prezzi_chiusi FROM catalogo.fn_chiudi_legame_distinta(%L, %L, 1)',
           pg_temp.leg('L2'), pg_temp.oggi() + 30),
    format('VALUES (%L::date, 1)', pg_temp.oggi() + 30),
    '14) il verbo su L2 al primo giorno ammesso, con la conferma: chiude');

-- ============================================================
-- L3: prezzato da un'altra azienda.
-- ============================================================

-- 15
SELECT results_eq(
    $q$ SELECT riga_id, prezzo, nel_perimetro, esito
          FROM vendite.fn_prezzi_legame_oltre_la_fine(pg_temp.leg('L3'), pg_temp.oggi() - 1) $q$,
    $q$ VALUES (NULL::bigint, NULL::numeric, false, 'CHIUDE') $q$,
    '15) il prezzo di un''altra azienda: se ne sa solo che c''e''');

-- 16
SELECT throws_like(
    format('SELECT * FROM catalogo.fn_chiudi_legame_distinta(%L, %L, 1)',
           pg_temp.leg('L3'), pg_temp.oggi() - 1),
    pg_temp.msg('E_BOM_CHIUSURA_PREZZI_ALTRE_AZIENDE'),
    '16) il verbo su L3: E_BOM_CHIUSURA_PREZZI_ALTRE_AZIENDE');

-- 17
SELECT throws_like(
    format('UPDATE catalogo.articoli_componenti SET valido_al = %L WHERE id = %L',
           pg_temp.oggi() - 1, pg_temp.leg('L3')),
    pg_temp.msg('E_BOM_CHIUSURA_PREZZI_ALTRE_AZIENDE'),
    '17) UPDATE diretto su L3: E_BOM_CHIUSURA_PREZZI_ALTRE_AZIENDE');

-- ============================================================
-- L4 senza prezzi, legame assente, permesso.
-- ============================================================

-- 18
SELECT results_eq(
    format('SELECT prezzi_chiusi, prezzi_tolti FROM catalogo.fn_chiudi_legame_distinta(%L, %L)',
           pg_temp.leg('L4'), pg_temp.oggi() - 1),
    $q$ VALUES (0, 0) $q$,
    '18) L4 senza prezzi: il verbo chiude senza conferma');

-- 19
SELECT throws_like(
    format('SELECT * FROM catalogo.fn_chiudi_legame_distinta(%L, %L)',
           uuidv7(), pg_temp.oggi() - 1),
    pg_temp.msg('E_BOM_LEGAME_NOT_FOUND'),
    '19) legame inesistente: E_BOM_LEGAME_NOT_FOUND');

-- 20 (per ultimo: cambia il contesto)
SELECT set_config('app.current_user_id', '999999999', true);
SELECT throws_like(
    format('SELECT * FROM catalogo.fn_chiudi_legame_distinta(%L, %L)',
           pg_temp.leg('L4'), pg_temp.oggi()),
    pg_temp.msg('E_PERMESSO_NEGATO'),
    '20) senza permesso: E_PERMESSO_NEGATO');

SELECT * FROM finish();
ROLLBACK;
