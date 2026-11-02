-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test — dbops.vw_bersagli_non_dichiarati: il cancello del vocabolario
--   Brief: brief-db-bersaglio-errore.md §6 L3, T-4
--
-- ⭐ PERCHE' QUESTO FILE ESISTE, in una riga:
--     Tid ha deciso che config.tipi_entita cresca UNA VOCE PER VOLTA, insieme
--     al messaggio che la usa. Quella decisione e' sicura solo se dimenticare
--     la voce e' IMPOSSIBILE — ed e' questo test a renderlo vero: il test 1
--     fallisce la build quando qualcuno punta a un tipo non dichiarato.
--
-- ⚠️ Il test 1 e' l'unico che conta davvero, ed e' anche l'unico che un giorno
--   diventera' rosso da solo, senza che nessuno abbia toccato questo file. E'
--   il suo mestiere: il messaggio che stampa deve bastare a capire cosa fare.
--
-- Indice test (1..4):
--   1. ⭐ IL CANCELLO — nessun bersaglio punta a un tipo non dichiarato
--   2. la vista distingue ASSENTE da OBSOLETO (le due righe chiedono cose diverse)
--   3. i tipi nominati SOLO in un commento non contano
--   4. una funzione che non costruisce bersagli non entra, anche se nomina un tipo
--
-- ⚠️ 2, 3 e 4 misurano la MECCANICA della vista su dati finti costruiti qui:
--   servono perche' un cancello che non sa distinguere e' peggio di nessun
--   cancello — direbbe «rosso» a caso e verrebbe disattivato al terzo falso
--   allarme.
--
-- Runner: `app` (il default). Le funzioni di appoggio vivono in `pg_temp` e
--   muoiono con la sessione; nessuna scrittura, nessun DDL permanente.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(4);

-- ============================================================
-- 1 — ⭐ IL CANCELLO
-- ============================================================
SELECT is(
    (SELECT coalesce(string_agg(v.tipo || ' [' || v.motivo || '] <- ' || v.funzioni,
                                E'\n' ORDER BY v.tipo), '')
       FROM dbops.vw_bersagli_non_dichiarati v),
    '',
    '1. Nessun bersaglio punta a un tipo che config.tipi_entita non dichiara'
);

-- ============================================================
-- 2..4 — la meccanica, su funzioni finte
-- ⚠️ `pg_temp` e' uno schema come gli altri per pg_proc: la vista le vede,
--   ed e' proprio cio' che permette di collaudarla senza sporcare niente.
-- ============================================================

-- Un tipo mai dichiarato + uno ritirato + uno buono, tutti in una funzione
-- che il bersaglio lo costruisce davvero.
CREATE OR REPLACE FUNCTION pg_temp.finta_con_bersaglio()
RETURNS void LANGUAGE plpgsql AS $fn$
BEGIN
    PERFORM script.fn_log_and_raise_error(
        'test', 'pg_temp.finta_con_bersaglio', 'E_PARAMETRO_INVALIDO',
        jsonb_build_object('bersaglio', jsonb_build_array(
            jsonb_build_object('tipo', 'PIPPO',   'id', '1'),
            jsonb_build_object('tipo', 'FATTURA', 'id', '2'))),
        NULL::uuid, 'x');
END
$fn$;

-- Nomina un tipo, ma NON costruisce nessun bersaglio: non deve entrare.
CREATE OR REPLACE FUNCTION pg_temp.finta_senza_bersaglio()
RETURNS text LANGUAGE plpgsql AS $fn$
BEGIN
    RETURN (jsonb_build_object('tipo', 'PLUTO') ->> 'tipo');
END
$fn$;

SELECT is(
    (SELECT string_agg(v.tipo || ':' || v.motivo, ',' ORDER BY v.tipo)
       FROM dbops.vw_bersagli_non_dichiarati v),
    'PIPPO:ASSENTE',
    '2. Il tipo mai dichiarato compare come ASSENTE; quello a catalogo no'
);

-- Il tipo c'e' ma e' ritirato: motivo diverso, perche' il rimedio e' diverso.
UPDATE config.tipi_entita SET obsoleto_dal = script.fn_data_operativa() - 1 WHERE codice = 'FATTURA';

SELECT is(
    (SELECT string_agg(v.tipo || ':' || v.motivo, ',' ORDER BY v.tipo)
       FROM dbops.vw_bersagli_non_dichiarati v),
    'FATTURA:OBSOLETO,PIPPO:ASSENTE',
    '3. Un tipo ritirato compare come OBSOLETO, non come ASSENTE'
);

-- ⚠️ Un tipo nominato in un COMMENTO non e' un tipo scritto.
CREATE OR REPLACE FUNCTION pg_temp.finta_solo_commento()
RETURNS void LANGUAGE plpgsql AS $fn$
BEGIN
    -- bersaglio: 'tipo', 'PAPERINO' — questo e' solo un commento
    RETURN;
END
$fn$;

SELECT is(
    (SELECT count(*)::integer
       FROM dbops.vw_bersagli_non_dichiarati v
      WHERE v.tipo IN ('PAPERINO', 'PLUTO')),
    0,
    '4. Non contano ne'' i tipi nei commenti ne'' quelli fuori da un bersaglio'
);

SELECT * FROM finish();

ROLLBACK;
