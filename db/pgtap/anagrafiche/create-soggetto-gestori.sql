-- ---------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2025 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- Test: soggetto GESTORE — creazione, ruolo, singleton e unicita' fiscale
-- ------------------------------------------------------------
-- Indice test (1..5):
--   1) soggetto di test creato
--   2) assegnato esattamente 1 ruolo GESTORE
--   3) nel sistema esiste esattamente 1 gestore (singleton globale)
--   4) crearne un altro sul ruolo appena creato e' respinto
--   5) un SECONDO soggetto con la stessa P.IVA e' respinto (unicita' fiscale)
--
-- ============================================================================
-- rev 2026-08-18 — bonifica baseline. Il file era NON TRANSAZIONALE: chiudeva
-- in COMMIT e lasciava soggetto, ruolo e gestore nel database. Alla corsa dopo,
-- quattro DELETE di «pulizia preventiva» in testa provavano a toglierli e
-- fallivano: anagrafiche.gestori e' fra le tabelle di
-- dbops.automation_delete_block_ruoli dal 2026-01-23, quindi «Cancellazione non
-- permessa». Il file moriva alla riga 40 con ZERO asserzioni eseguite.
--
-- Ora: BEGIN ... ROLLBACK (il ROLLBACK e' la garanzia, le quattro pulizie
-- spariscono) e il soggetto lo costruisce dbops.fn_pgtap_crea_soggetto_pg, che
-- sa la saga corrente. La partita IVA se la fa dare da dbops.fn_pgtap_piva_libera
-- PRIMA, perche' al test 5 serve riusarla per provare il duplicato.
--
-- ⚠️ Il test 5 era `throws_ok(..., NULL, NULL, ...)`: senza SQLSTATE accetta
-- QUALUNQUE errore, compreso il crash del guard che dovrebbe verificare. Ora
-- pretende 23505, che e' la violazione di unicita' che la sua etichetta
-- promette. E per arrivarci deve valorizzare anche il codice fiscale: il guard
-- cf/piva e' un BEFORE e scatterebbe prima, dando P0001 — cioe' un verde preso
-- dal controllo sbagliato.
--
-- L'INSERT del contatto e' sparito: lo fa l'helper, ed era li' solo per
-- soddisfare il guard differito dei contatti (nessuna asserzione lo guardava).
-- ============================================================================

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

-- =========================================================
-- Costanti. La P.IVA si prende PRIMA e si tiene: il test 5 la riusa per
-- provare il duplicato, quindi deve essere la stessa del soggetto buono.
-- =========================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT
    dbops.fn_pgtap_piva_libera() AS piva_test,
    'GE'::varchar                AS codice_ruolo_gestore,
    'EUR'::varchar               AS codice_valuta,
    'ZEROERP'::varchar           AS codice_prod_software;

-- ---------------------------------------------------------
-- 1) Soggetto di test (persona giuridica completa)
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_soggetto AS
SELECT dbops.fn_pgtap_crea_soggetto_pg(
           p_ragione_sociale := 'Gestore Test pgTAP',
           p_piva            := k.piva_test
       ) AS id
  FROM tmp_costanti k;

SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto WHERE id IS NOT NULL),
    1,
    'Inserito esattamente 1 soggetto di test'
);

-- ---------------------------------------------------------
-- 2) Ruolo GESTORE
-- ---------------------------------------------------------
-- ⚠️ Non basta fn_get_or_create_soggetto_ruolo: il ruolo GESTORE ha i suoi
--   indirizzi OBBLIGATORI (SEDELEG, FATT) su un layer diverso da quelli del
--   soggetto, con matrice e guard propri. L'helper li mette.
CREATE TEMP TABLE tmp_soggetto_ruolo AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(
           p_soggetto_id  := s.id,
           p_cd_int_ruolo := k.codice_ruolo_gestore
       ) AS id
  FROM tmp_soggetto s, tmp_costanti k;

SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto_ruolo),
    1,
    'Assegnato esattamente 1 ruolo GESTORE al soggetto di test'
);

-- ---------------------------------------------------------
-- 3) Il singleton: nel sistema c'e' UN gestore, e uno solo
--
-- ⚠️ rev 2026-08-18 — QUESTA ASSERZIONE E' STATA RIVOLTATA, non riparata.
--   Diceva «inserito esattamente 1 gestore», e per poterlo fare il file
--   cancellava prima quello esistente. Ma il gestore e' un singleton GLOBALE
--   (uno per installazione, non uno per ruolo) e dal 2026-01-23
--   anagrafiche.gestori e' fra le tabelle a cancellazione vietata: «creo il
--   gestore» e' un caso possibile solo su un database vuoto, cioe' mai.
--   Cio' che resta vero, ed e' quello che il test dice ora, e' che il
--   singleton REGGE: uno, e crearne un altro non si puo' (test 4).
-- ---------------------------------------------------------
SELECT is(
    (SELECT count(*)::int FROM anagrafiche.gestori),
    1,
    'Nel sistema esiste esattamente 1 gestore (singleton globale)'
);

-- ---------------------------------------------------------
-- 4) Singleton in azione: creare un gestore sul ruolo NUOVO e' respinto,
--    perche' uno nel sistema c'e' gia'
-- ---------------------------------------------------------
SELECT throws_ok(
    $$
    INSERT INTO anagrafiche.gestori (
        soggetto_ruolo_id, descrizione, cd_prod_software, valuta_id
    )
    SELECT sr.id,
           'Gestore Illegale - Test pgTAP',
           k.codice_prod_software,
           v.id
      FROM tmp_soggetto_ruolo sr,
           tmp_costanti k,
           LATERAL (SELECT vv.id FROM config.valute vv
                     WHERE vv.iso_code = k.codice_valuta
                     ORDER BY vv.id LIMIT 1) v;
    $$,
    'P0001',
    NULL,
    'Il tentativo di creare un secondo gestore genera un errore (regola singleton)'
);

-- ---------------------------------------------------------
-- 5) Unicita' fiscale: stessa P.IVA, secondo soggetto, respinto
-- ---------------------------------------------------------
SELECT throws_ok(
    $$
    INSERT INTO anagrafiche.soggetti (
        ragione_sociale, cognome, nome, sesso, stato_id,
        partita_iva, codice_fiscale, tipo_soggetto_dettaglio_id,
        storicizza, attivo
    )
    -- sesso NULL: una societa' non ne ha (sesso_policy NONE); era 'S',
    --   fuori vocabolario dal 2026-10-09 (brief-db-sesso-senza-default)
    SELECT 'Gestore Test Doppio pgTAP', NULL, NULL, NULL, 1,
           k.piva_test, k.piva_test, 3, TRUE, TRUE
      FROM tmp_costanti k;
    $$,
    '23505',
    NULL,
    'Il tentativo di creare un secondo soggetto con stessa P.IVA genera un errore (unique constraint)'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'.
-- ⚠️ finish() sta PRIMA: pgTAP tiene il suo stato in una temp table, e dopo il
-- ROLLBACK non esiste piu'.
ROLLBACK;
