-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: annullamento di un lotto DRAFT **senza fatture**
--       (segnalazione BE del 2026-08-01, decisione «strada C»)
-- ------------------------------------------------------------
-- Il difetto che questo file presidia
--   Un lotto che non ha prodotto nessuna fattura — un giro a vuoto, che
--   capita — non si riusciva ad annullare. La catena, misurata:
--
--     · per annullare, il lotto deve passare da DRAFT ad ANNULLATA;
--     · quel passaggio NON era nella matrice `config.stati_doc_fiscale_transizioni`;
--     · a salvarlo c'era la GUC di manutenzione `zeroerp.maintenance_reset_lotto_draft`,
--       che pero' `fn_annulla_lotto_da_draft` non accende: la accende
--       `fn_cleanup_fatture_by_ids`, che chiama;
--     · e quel cleanup esce SUBITO, prima di accenderla, quando l'array di
--       fatture e' vuoto.
--
--   Quindi: lotto con fatture, la GUC si accendeva per strada e l'annullamento
--   passava; lotto vuoto, niente GUC e tutto bloccato — con un errore di
--   transizione che all'operatore non dice niente.
--
--   Rimedio scelto: la transizione entra in **matrice**, perche' annullare un
--   lotto in bozza e' un'operazione legittima del dominio e non una
--   manutenzione straordinaria. Con la riga in matrice l'annullamento non ha
--   piu' bisogno di nessuna chiave di servizio — ed e' quello che il test 3
--   verifica: gira **senza** GUC.
-- ------------------------------------------------------------
-- Indice test
-- 1) Fixture: un lotto MASSIVO in DRAFT e senza fatture
-- 2) Seed: la transizione DRAFT -> ANNULLATA esiste, per il LOTTO
-- 3) Il lotto vuoto si annulla SENZA la GUC di manutenzione
-- 4) Dopo l annullamento: stato ANNULLATA e stato_operativo CHIUSO
-- 5) Il lotto era vuoto: nessuna fattura e nessuna attivita toccata
-- 6) La transizione NON e stata aperta anche alle fatture
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

-- ============================================================
-- 0) Fixture
-- ============================================================
-- Il lotto si crea con la funzione applicativa, cosi' nasce con lo stato e i
-- riferimenti che avrebbe nel giro reale. Non gli si attacca nessuna fattura:
-- e' esattamente il caso del difetto.
-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba) e l'emittente e' quello di chi agisce
--   (script.fn_pgtap_emittente_sr_operatore). Prima utility ed emittente si
--   pescavano dal primo BA e dalla prima fattura: da zero non c'erano.
CREATE TEMP TABLE tmp_cli_alv AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('annulla lotto vuoto');

CREATE TEMP TABLE tmp_lotto_alv AS
SELECT vendite.fn_get_or_create_lotto(
         p_competenza_mese             => (date_trunc('month', script.fn_data_operativa()) + interval '2 month')::date,
         p_tipo_doc_fiscale_id         => (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1),
         p_utility_id                  => (SELECT utility_id FROM tmp_cli_alv),
         p_emittente_soggetto_ruolo_id => script.fn_pgtap_emittente_sr_operatore(),
         p_tipo_lotto                  => 'MASSIVO') AS id;

SELECT ok(
  (SELECT count(*) FROM vendite.fatturazione_lotti_fatture WHERE lotto_id = (SELECT id FROM tmp_lotto_alv)) = 0
  AND (SELECT s.codice_interno FROM vendite.fatturazione_lotti fl
         JOIN config.stati_doc_fiscale s ON s.id = fl.stato_doc_fiscale_id
        WHERE fl.id = (SELECT id FROM tmp_lotto_alv)) = 'DRAFT',
  '1) Fixture: lotto MASSIVO in DRAFT e senza nessuna fattura');

-- ============================================================
-- 1) Il seed
-- ============================================================
-- La riga non e' vincolata al tipo di lotto (`meta` vuoto): la decisione e'
-- che anche un giornaliero interrotto deve poter tornare indietro da bozza.
-- ⚠️ Oggi una funzione di annullamento esiste solo per il MASSIVO: la matrice
-- apre la porta, l'implementazione per il giornaliero e' un lavoro a parte.
SELECT ok(
  EXISTS (
    SELECT 1 FROM config.stati_doc_fiscale_transizioni t
      JOIN config.stati_doc_fiscale sf ON sf.id = t.stato_from_id
      JOIN config.stati_doc_fiscale st ON st.id = t.stato_to_id
     WHERE sf.codice_interno = 'DRAFT' AND st.codice_interno = 'ANNULLATA'
       AND t.ammesso IS TRUE AND t.solo_lotto IS TRUE
       AND (t.meta->>'tipo_lotto') IS NULL),
  '2) Seed: la transizione DRAFT -> ANNULLATA esiste per il lotto, senza vincolo di tipo');

-- ============================================================
-- 2) Il caso del difetto
-- ============================================================
-- ⚠️ Nessun `set_config` qui, ed e' il punto: se l'annullamento avesse ancora
-- bisogno della chiave di servizio, questo test fallirebbe — che e' come si
-- accorgerebbe chi un domani togliesse la riga dalla matrice.
-- Si usa `lives_ok` e non una chiamata diretta perche' senza la riga in matrice
-- la funzione SOLLEVA: una chiamata nuda abortirebbe la transazione e il file
-- morirebbe qui, senza eseguire le asserzioni sotto — cioe' riporterebbe un
-- rosso solo, e proprio quelle che spiegano cosa non ha funzionato andrebbero
-- perse.
SELECT lives_ok(
  format($$ SELECT * FROM vendite.fn_annulla_lotto_da_draft(%s) $$, (SELECT id FROM tmp_lotto_alv)),
  '3) Il lotto vuoto si annulla senza GUC di manutenzione');

SELECT ok(
  (SELECT s.codice_interno FROM vendite.fatturazione_lotti fl
     JOIN config.stati_doc_fiscale s ON s.id = fl.stato_doc_fiscale_id
    WHERE fl.id = (SELECT id FROM tmp_lotto_alv)) = 'ANNULLATA'
  AND (SELECT stato_operativo FROM vendite.fatturazione_lotti
        WHERE id = (SELECT id FROM tmp_lotto_alv)) = 'CHIUSO',
  '4) Dopo l annullamento: stato ANNULLATA e stato_operativo CHIUSO');

SELECT ok(
  (SELECT count(*) FROM vendite.fatturazione_lotti_fatture
    WHERE lotto_id = (SELECT id FROM tmp_lotto_alv)) = 0
  AND (SELECT count(*) FROM vendite.attivita_fatturabili a
        WHERE a.lock_batch_id = (SELECT fl.lock_batch_id FROM vendite.fatturazione_lotti fl
                                  WHERE fl.id = (SELECT id FROM tmp_lotto_alv))
          AND (SELECT fl.lock_batch_id FROM vendite.fatturazione_lotti fl
                WHERE fl.id = (SELECT id FROM tmp_lotto_alv)) IS NOT NULL) = 0,
  '5) Il lotto era vuoto: nessuna fattura collegata e nessuna attivita agganciata al suo batch');

-- ============================================================
-- 3) Quello che NON abbiamo aperto
-- ============================================================
-- La stessa transizione per le FATTURE (EMESSA -> ANNULLATA) e' una decisione
-- separata — D-N-bis, il modello «reperto» — e non deve entrare di straforo
-- insieme a questa. La matrice distingue le due entita' con solo_lotto /
-- solo_fattura: il test presidia che la riga aggiunta valga solo per il lotto.
SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM config.stati_doc_fiscale_transizioni t
      JOIN config.stati_doc_fiscale st ON st.id = t.stato_to_id
     WHERE st.codice_interno = 'ANNULLATA'
       AND t.solo_fattura IS TRUE AND t.ammesso IS TRUE),
  '6) La transizione verso ANNULLATA non e stata aperta anche alle fatture (resta D-N-bis)');

SELECT * FROM finish();

ROLLBACK;
