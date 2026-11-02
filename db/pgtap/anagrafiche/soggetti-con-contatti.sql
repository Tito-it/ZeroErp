-- ---------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2025 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- Test: un soggetto ha i suoi contatti, e almeno uno con un recapito vero
-- ------------------------------------------------------------
-- Indice test (1..3):
--   1) il soggetto di supporto e' stato creato
--   2) il contatto REFERENTE aggiunto dal test c'e', ed e' uno
--   3) il soggetto ha almeno un contatto con un recapito valido
--
-- ============================================================================
-- rev 2026-08-18 — bonifica baseline. Il file era NON TRANSAZIONALE: apriva la
-- transazione a meta' e chiudeva in COMMIT, quindi lasciava il soggetto nel
-- database. Alla corsa dopo una «pulizia preventiva» in testa provava a
-- cancellarlo, e falliva: il soggetto residuo aveva nel frattempo acquisito
-- riferimenti, e dal 2026-01-23 le tabelle di ruolo non si cancellano
-- (dbops.automation_delete_block_ruoli). Il file moriva alla riga 46 con ZERO
-- asserzioni eseguite — copertura zero, non «parziale».
--
-- Ora: BEGIN ... ROLLBACK (il ROLLBACK e' la garanzia, la pulizia sparisce) e
-- il soggetto lo costruisce dbops.fn_pgtap_crea_soggetto_pg, che sa la saga
-- corrente — testata, dati societari, indirizzi obbligatori, contatto — e usa
-- una partita IVA valida e mai usata. Il vecchio 01677080440 resta sul
-- «Cliente Test pgTAP» del 2025, e da oggi non da' piu' fastidio a nessuno.
--
-- ⚠️ L'helper crea gia' un contatto suo (tipo PRINCIPALE), quindi il test 2
-- conta il contatto CHE AGGIUNGE LUI — identificandolo per TIPO, non per
-- nominativo: l'helper battezza il suo «Referente <ragione sociale>», che e'
-- esattamente la stringa che questo test usava, e contarli per nome ne
-- prendeva due.
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

SELECT plan(3);

-- ---------------------------------------------------------
-- Soggetto di supporto (persona giuridica completa)
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_soggetto AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Cliente Test pgTAP') AS id;

SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto WHERE id IS NOT NULL),
    1,
    'Creato esattamente 1 soggetto di test'
);

-- ---------------------------------------------------------
-- Il contatto del test.
-- ⚠️ Tipo REFERENTE e non il primo disponibile: uq_contatti_soggetto_tipo e'
--   UNIQUE su (soggetto_id, tipo_contatto_id) quando non c'e' ruolo ne'
--   istanza, e il contatto PRINCIPALE l'ha gia' messo l'helper.
-- is_default = FALSE per la stessa ragione: il predefinito e' gia' suo.
-- ---------------------------------------------------------
INSERT INTO anagrafiche.contatti (
    tipo_contatto_id,
    soggetto_id,
    nominativo,
    email,
    is_default,
    default_context
)
SELECT
    (SELECT t.id FROM config.tipi_contatti t WHERE t.codice_interno = 'REFERENTE'),
    s.id,
    'Referente Cliente Test pgTAP',
    'cliente.pgtap@example.com',
    FALSE,
    'soggetto'
FROM tmp_soggetto s;

SELECT is(
    (SELECT count(*)::int
       FROM anagrafiche.contatti c
      WHERE c.soggetto_id = (SELECT id FROM tmp_soggetto)
        AND c.tipo_contatto_id = (SELECT t.id FROM config.tipi_contatti t
                                   WHERE t.codice_interno = 'REFERENTE')),
    1,
    'Inserito esattamente 1 contatto REFERENTE per il soggetto di test'
);

SELECT ok(
    EXISTS (
        SELECT 1
        FROM anagrafiche.contatti c
        WHERE c.soggetto_id = (SELECT id FROM tmp_soggetto)
          AND (
            c.email IS NOT NULL
            OR c.telefono IS NOT NULL
            OR c.cellulare IS NOT NULL
            OR c.pec IS NOT NULL
          )
    ),
    'Il soggetto di test ha almeno un contatto con un recapito valido'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'.
-- ⚠️ finish() sta PRIMA: pgTAP tiene il suo stato in una temp table, e dopo il
-- ROLLBACK non esiste piu'.
ROLLBACK;
