-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: CREATE TRIGGER su anagrafiche.indirizzi_dettaglio — fault injection per
--   dimostrare che l'INSERT del dettaglio fallisce davvero e che la creazione
--   dell'indirizzo e' atomica. Il ruolo applicativo ha la DML completa sulla
--   tabella ma NON il privilegio TRIGGER, e non deve averlo: creare trigger
--   su una tabella di dominio non e' un'operazione dell'applicazione.
--   Stessa natura di vendite/test-annulla-commessa-attivita-v1 (brief §24.3).
-- pgTAP per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU GPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: anagrafiche.fn_create_indirizzo (piano analisi-fix-transazioni, #13)
--
-- Copre:
--   * happy "via nuova"  : upsert stradario_generale + stradario + dettaglio.
--   * idempotenza         : seconda chiamata stessa via -> stesso stradario
--                           (upsert, non duplica).
--   * ATOMICITA'          : se il dettaglio fallisce, le righe stradario appena
--                           create NON restano (nessun orfano nel registro).
--
-- Idempotente: BEGIN ... ROLLBACK. Descrizioni via dedicate (non collidono).
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- =========================================================
-- Precondizioni: toponomastica + (comune, cap) coerenti
-- =========================================================
CREATE TEMP TABLE k AS
SELECT
    (SELECT id FROM config.toponomastica ORDER BY id LIMIT 1) AS topo_id,
    cp.comune_id AS comune_id,
    cp.id        AS cap_id,
    'PGTAP-FNCREATE-VIA-HAPPY'::varchar AS via_happy,
    'PGTAP-FNCREATE-VIA-ATOM'::varchar  AS via_atom
FROM config.codici_postali cp
ORDER BY cp.id LIMIT 1;

SELECT ok((SELECT topo_id FROM k) IS NOT NULL AND (SELECT comune_id FROM k) IS NOT NULL,
          'Precondizione: toponomastica + comune/CAP disponibili');

-- =========================================================
-- HAPPY: via nuova -> stradario + dettaglio
-- =========================================================
CREATE TEMP TABLE r_happy AS
SELECT anagrafiche.fn_create_indirizzo(
    NULL,                         -- p_stradario_id (via nuova)
    (SELECT topo_id FROM k),
    (SELECT via_happy FROM k),
    (SELECT comune_id FROM k),
    (SELECT cap_id FROM k),
    10                            -- p_civico
) AS indirizzo_id;

SELECT ok((SELECT indirizzo_id FROM r_happy) IS NOT NULL,
          'Happy: indirizzo_id ritornato non nullo');

SELECT is(
    (SELECT count(*)::int FROM config.stradario_generale sg
      WHERE sg.toponomastica_id = (SELECT topo_id FROM k)
        AND sg.descrizione = (SELECT via_happy FROM k)),
    1,
    'Happy: stradario_generale creato per la via nuova');

-- =========================================================
-- IDEMPOTENZA: seconda chiamata stessa via -> stesso stradario (upsert)
-- =========================================================
SELECT anagrafiche.fn_create_indirizzo(
    NULL, (SELECT topo_id FROM k), (SELECT via_happy FROM k),
    (SELECT comune_id FROM k), (SELECT cap_id FROM k), 20);

SELECT is(
    (SELECT count(*)::int FROM config.stradario_generale sg
      WHERE sg.toponomastica_id = (SELECT topo_id FROM k)
        AND sg.descrizione = (SELECT via_happy FROM k)),
    1,
    'Idempotenza: la via non e'' duplicata (upsert, ancora 1 stradario_generale)');

-- =========================================================
-- ATOMICITA': il dettaglio fallisce (trigger iniettato) => stradario NON resta
-- =========================================================
CREATE FUNCTION pg_temp.pgtap_fail_dettaglio() RETURNS trigger
    LANGUAGE plpgsql AS $f$
BEGIN
    RAISE EXCEPTION 'pgtap: fallimento iniettato sull''INSERT del dettaglio';
END;
$f$;

CREATE TRIGGER zzz_pgtap_fail_dettaglio
    BEFORE INSERT ON anagrafiche.indirizzi_dettaglio
    FOR EACH ROW EXECUTE FUNCTION pg_temp.pgtap_fail_dettaglio();

SELECT throws_like(
    $$ SELECT anagrafiche.fn_create_indirizzo(
           NULL, (SELECT topo_id FROM k), (SELECT via_atom FROM k),
           (SELECT comune_id FROM k), (SELECT cap_id FROM k), 30) $$,
    '%fallimento iniettato sull''INSERT del dettaglio%',
    'Atomicita'': il fallimento del dettaglio fa fallire l''intera chiamata');

DROP TRIGGER zzz_pgtap_fail_dettaglio ON anagrafiche.indirizzi_dettaglio;

SELECT is(
    (SELECT count(*)::int FROM config.stradario_generale sg
      WHERE sg.toponomastica_id = (SELECT topo_id FROM k)
        AND sg.descrizione = (SELECT via_atom FROM k)),
    0,
    'Atomicita'': nessuno stradario orfano (upsert annullato col dettaglio)');

SELECT * FROM finish();

ROLLBACK;
