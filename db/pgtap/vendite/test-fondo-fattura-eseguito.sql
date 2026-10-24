-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il fondo fattura REGISTRATO — quarto stato ESEGUITO e sue conseguenze
--
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): la sorgente nasce in
--   bozza e si porta avanti con dbops.fn_pgtap_porta_a_stato (prima nasceva
--   gia' DEFINITIVA).
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): le due fatture le
--   costruisce dbops.fn_pgtap_crea_fattura (mondo, registro dell'azienda,
--   snapshot coi building block) invece di pescare il primo billing account:
--   su un database ricostruito non c'e'. Il contesto si apre DOPO, sul suo
--   operatore.
-- rev 2026-10-24 (brief-modello-documento-vendita R-5): minimo e totale li
--   scrive il builder alla nascita; la sorgente non si ferma piu' in EMESSA
--   per un UPDATE, nasce e arriva in DEFINITIVA in una chiamata.
--
-- Elenco test (plan 13):
--  1) Riferimenti minimi presenti
--  2) Il sync crea la riga contabile del fondo
--  3) Il legame riga -> atto sta nella COLONNA fondo_source_id (S1-14)
--  4) ...e non piu' nel meta: due sorgenti di verita' sono il difetto
--  5) REGISTRAZIONE: la riga passa a POSTATA e l'atto diventa ESEGUITO (S1-16)
--  6) ESEGUITO e' TERMINALE: uscirne e' rifiutato (P0001)
--  7) Invariante S1-9: nessun fondo ASSEGNATO ha una riga registrata
--  8) C-2: il sync non riscrive piu' quella riga (zero aggiornate)
--  9) C-3: e non annulla piu' quel fondo (zero annullati)
-- 10) Il sync non ne inserisce una seconda (zero inserite)
-- 11) Il reset NON tocca un atto eseguito (zero cancellati)
-- 12) ...e l'atto resta ESEGUITO con la figlia ancora agganciata
-- 13) Il reset lo DICHIARA nel diario col suo codice
--
-- Scopo:
--  - collaudare la meta' «denaro REGISTRATO» del vecchio caso 14, che
--    test-fondi-fattura.sql non poteva provare: li' si chiude una distinta
--    senza che nessuna riga sia mai stata registrata, ed e' un altro fatto.
--    Sdoppiamento chiesto da Tid il 2026-08-22.
--  - presidiare l'invariante su cui regge fn_saldo_sorgente_fondo: lo
--    scorporo del contributo proprio somma le sole righe POSTABILI, quindi
--    vale finche' la riga e' in lavorazione. Se un fondo ASSEGNATO avesse una
--    riga registrata, lo scorporo verrebbe a zero e il residuo risulterebbe
--    piu' basso del vero.
--
-- Piano: brief-db-posting-e-abbinamento-rata.md
--        §2.4 casi 9, 9-bis, 9-ter, 9-quater · lotto 3
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 2. IL MONDO, poi il CONTESTO APPLICATIVO: la sorgente la costruisce il
--   builder (azienda, operatore, cliente, registro) con minimo e totale alla
--   NASCITA, e la porta in DEFINITIVA per la matrice. Il test gira come gira
--   l'applicazione (OPERATORE + RLS attiva), sull'operatore del mondo.
CREATE TEMP TABLE tmp_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_fattura(
         'fondo_eseguito', 'DEFINITIVA', NULL, false, false,
         p_minimo => true, p_totale_a_pagare => 100.00);

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_mondo)); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI: senza, non verrebbero mai esercitati (si chiude in
--   ROLLBACK) e il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_fondo_eseguito'::text AS test_scope;

-- ⚠️ Il centro dei fondi NON si fabbrica: dal 2026-08-21 e' seminato
--   (changeSet 20260821-20) ed e' garantito unico da un indice parziale.
--   Un test che se lo crea da solo non verifica il seed: lo nasconde.
-- I riferimenti del documento sono quelli della fattura costruita.
CREATE TEMP TABLE tmp_refs AS
SELECT m.registro_id,
       m.billing_account_id,
       m.utility_id,
       m.tipo_doc_fiscale_id,
       m.valuta_id,
       m.emittente_soggetto_ruolo_id,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.is_fondo_fattura IS TRUE
         ORDER BY c.id LIMIT 1)                                                     AS centro_fondo_id,
       (SELECT t.id FROM vendite.tipi_fondi_fattura t
         WHERE t.attivo IS TRUE AND t.codice_interno = 'F_F_ADD_ACC'
         ORDER BY t.id LIMIT 1)                                                     AS tipo_fondo_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'POSTATA' ORDER BY s.id LIMIT 1)                  AS stato_postata_id
  FROM tmp_mondo m;

SELECT ok(
  (SELECT registro_id IS NOT NULL
      AND billing_account_id IS NOT NULL
      AND utility_id IS NOT NULL
      AND tipo_doc_fiscale_id IS NOT NULL
      AND valuta_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL
      AND centro_fondo_id IS NOT NULL
      AND tipo_fondo_id IS NOT NULL
      AND stato_postata_id IS NOT NULL
     FROM tmp_refs),
  '1) Riferimenti minimi presenti (centro fondi e stato POSTATA compresi)'
);

-- La fattura SORGENTE: definitiva, di minimo, col totale che diventa il fondo
--   (scritti dal builder alla nascita, prima della DEFINITIVA che li congela).
CREATE TEMP TABLE tmp_src AS
SELECT fattura_id AS id FROM tmp_mondo;

-- La fattura FIGLIA: quella su cui il fondo viene applicato. Stesso cliente
--   (terzo parametro), in bozza, col suo totale alla nascita.
CREATE TEMP TABLE tmp_dst AS
SELECT fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura('fondo_eseguito', 'DRAFT',
                                   (SELECT billing_account_id FROM tmp_refs),
                                   false, false,
                                   p_minimo => false, p_totale_a_pagare => 200.00);

-- Genera l'atto, lo applica alla figlia, e ne scrive la riga contabile.
-- ⚠️ Tre VERBI, tre istruzioni separate dalle asserzioni: la snapshot di
--   statement legge PRIMA delle scritture, e un'asserzione nella stessa
--   istruzione accuserebbe la funzione invece del test.
SELECT vendite.fn_genera_fondi_fattura_source(
    p_billing_account_id          => (SELECT billing_account_id FROM tmp_refs),
    p_utility_id                  => (SELECT utility_id FROM tmp_refs),
    p_tipo_doc_fiscale_id         => (SELECT tipo_doc_fiscale_id FROM tmp_refs),
    p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs),
    p_valuta_id                   => (SELECT valuta_id FROM tmp_refs),
    p_tipo_fondo_fattura_id       => (SELECT tipo_fondo_id FROM tmp_refs));

SELECT vendite.fn_applica_fondi_fattura(
    p_billing_account_id          => (SELECT billing_account_id FROM tmp_refs),
    p_utility_id                  => (SELECT utility_id FROM tmp_refs),
    p_tipo_doc_fiscale_id         => (SELECT tipo_doc_fiscale_id FROM tmp_refs),
    p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs),
    p_valuta_id                   => (SELECT valuta_id FROM tmp_refs),
    p_fattura_figlia_id           => (SELECT id FROM tmp_dst),
    p_tipo_fondo_fattura_id       => (SELECT tipo_fondo_id FROM tmp_refs));

SELECT vendite.fn_sync_contabili_fondo_fattura(
    p_fattura_figlia_id => (SELECT id FROM tmp_dst));

-- L'atto e la sua riga contabile si scelgono UNA volta: due sotto-select
-- indipendenti potrebbero pescare righe diverse.
CREATE TEMP TABLE tmp_atto AS
SELECT s.id AS source_id
  FROM vendite.fatture_fondi_fattura_source s
 WHERE s.fattura_sorgente_id = (SELECT id FROM tmp_src)
 ORDER BY s.id DESC
 LIMIT 1;

CREATE TEMP TABLE tmp_riga AS
SELECT cr.id AS riga_id, cr.contabile_id
  FROM pagamenti.vendite_contabili_righe cr
 WHERE cr.fondo_source_id = (SELECT source_id FROM tmp_atto)
 ORDER BY cr.id DESC
 LIMIT 1;

SELECT ok(
  (SELECT riga_id IS NOT NULL FROM tmp_riga),
  '2) Il sync ha creato la riga contabile del fondo'
);

-- ============================================================
-- S1-14 — il legame sta nella COLONNA, e solo li'
-- ============================================================
SELECT is(
  (SELECT cr.fondo_source_id FROM pagamenti.vendite_contabili_righe cr
    WHERE cr.id = (SELECT riga_id FROM tmp_riga)),
  (SELECT source_id FROM tmp_atto),
  '3) Il legame riga -> atto e'' nella colonna fondo_source_id'
);

-- ⚠️ La chiave nel meta non si scrive piu': due sorgenti di verita' sullo
--   stesso legame sono il difetto che S1-14 chiude, non una ridondanza utile.
-- ℹ️ Si guarda `meta -> 'chiave' IS NULL` e non l'operatore di esistenza: in un
--   file eseguito da psql `?` funziona, ma resta un carattere che altrove nel
--   progetto va raddoppiato (Liquibase) — meglio non insegnarne l'uso qui.
SELECT ok(
  (SELECT cr.meta -> 'fondo_source_id' IS NULL
     FROM pagamenti.vendite_contabili_righe cr
    WHERE cr.id = (SELECT riga_id FROM tmp_riga)),
  '4) La chiave fondo_source_id non e'' piu'' nel meta'
);

-- ============================================================
-- S1-16 — LA REGISTRAZIONE: il denaro si muove, l'atto diventa ESEGUITO
-- ============================================================
-- Prima il movimento (la registrazione vera), poi lo stato della riga: il
-- trigger scatta sul cambio di stato, e l'ordine fra i due non conta per lui —
-- conta che siano nella STESSA transazione, che e' cio' che si sta provando.
-- ⚠️ fattura_id e billing_account_id NON si passano: li deriva dalla riga il
--   trigger di mirror, e passarli diversi sarebbe un errore di dominio.
INSERT INTO pagamenti.vendite_movimenti (
    contabile_riga_id, data_effettiva, data_registrazione, importo, meta)
SELECT tr.riga_id, script.fn_data_operativa(), script.fn_data_operativa(), cr.importo,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_riga tr
  JOIN pagamenti.vendite_contabili_righe cr ON cr.id = tr.riga_id;

UPDATE pagamenti.vendite_contabili_righe cr
   SET stato_id = (SELECT stato_postata_id FROM tmp_refs)
 WHERE cr.id = (SELECT riga_id FROM tmp_riga);

SELECT is(
  (SELECT s.stato::text FROM vendite.fatture_fondi_fattura_source s
    WHERE s.id = (SELECT source_id FROM tmp_atto)),
  'ESEGUITO'::text,
  '5) Registrata la riga, l''atto e'' ESEGUITO nella stessa transazione'
);

-- ============================================================
-- ESEGUITO e' terminale
-- ============================================================
-- ⚠️ Lo SQLSTATE si dichiara: senza, throws_ok accetterebbe qualunque errore,
--   compreso il crash del guard. P0001 = errore di dominio.
SELECT throws_ok(
  format('UPDATE vendite.fatture_fondi_fattura_source SET stato = ''ANNULLATO'', motivo = ''prova'' WHERE id = %s',
         (SELECT source_id FROM tmp_atto)),
  'P0001',
  NULL,
  '6) Da ESEGUITO non si esce: la transizione e'' rifiutata'
);

-- ============================================================
-- L'invariante su cui regge fn_saldo_sorgente_fondo (S1-9)
-- ============================================================
-- ⚠️ La domanda e' GLOBALE e non ristretta alla fixture, ed e' voluto: e'
--   l'invariante del database, non una proprieta' di questo test.
SELECT is(
  (SELECT count(*)::int
     FROM vendite.fatture_fondi_fattura_source s
    WHERE s.stato = 'ASSEGNATO'
      AND EXISTS (
          SELECT 1
            FROM pagamenti.vendite_contabili_righe cr
            JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
           WHERE cr.fondo_source_id = s.id
             AND st.codice_interno = 'POSTATA')),
  0,
  '7) Invariante: nessun fondo ASSEGNATO ha una riga gia'' registrata'
);

-- ============================================================
-- C-2 e C-3: il sync non arriva piu' a quella riga
-- ============================================================
-- ⚠️ Il verbo in un'istruzione separata, e l'esito in una temp table: la
--   funzione va chiamata UNA volta sola, non una per asserzione.
CREATE TEMP TABLE tmp_sync2 AS
SELECT * FROM vendite.fn_sync_contabili_fondo_fattura(
    p_fattura_figlia_id => (SELECT id FROM tmp_dst));

SELECT is(
  (SELECT updated_righe FROM tmp_sync2), 0,
  '8) C-2: il sync non riscrive la riga gia'' registrata'
);

SELECT is(
  (SELECT annullati_source FROM tmp_sync2), 0,
  '9) C-3: e non annulla il fondo interamente registrato'
);

SELECT is(
  (SELECT inserted_righe FROM tmp_sync2), 0,
  '10) E non ne inserisce una seconda dalla porta accanto'
);

-- ============================================================
-- S1-17 — il reset non tocca un atto eseguito
-- ============================================================
CREATE TEMP TABLE tmp_reset AS
SELECT * FROM vendite.fn_reset_fondi_fattura(
    p_fattura_id => (SELECT id FROM tmp_dst));

SELECT is(
  (SELECT deleted_source FROM tmp_reset), 0,
  '11) Il reset non cancella un atto ESEGUITO'
);

-- ⭐ E non lo annulla nemmeno: il record resta coerente — eseguito, con la
--   figlia a cui e' stato applicato. E' la meta' di D11 che toglie il vecchio
--   record autocontraddittorio (ANNULLATO con fattura_figlia_id valorizzato).
SELECT ok(
  (SELECT s.stato::text = 'ESEGUITO' AND s.fattura_figlia_id = (SELECT id FROM tmp_dst)
     FROM vendite.fatture_fondi_fattura_source s
    WHERE s.id = (SELECT source_id FROM tmp_atto)),
  '12) L''atto resta ESEGUITO, con la figlia ancora agganciata'
);

-- Il codice DICHIARATO nel diario: e' cio' che la lista delle segnalazioni
-- mostra nella colonna «codice». `cause` accanto e' il vocabolario locale.
SELECT is(
  (SELECT fl.meta ->> 'error_code'
     FROM vendite.fatture_log fl
    WHERE fl.fattura_id = (SELECT id FROM tmp_dst)
      AND fl.meta ->> 'cause' = 'ATTO_ESEGUITO'
    ORDER BY fl.id DESC
    LIMIT 1),
  'W_FONDO_ESEGUITO_NON_RESETTABILE',
  '13) Il reset dichiara nel diario il codice dell''atto non resettabile'
);

-- ============================================================
-- Cleanup
-- ============================================================
-- ⚠️ Ordine imposto dalle FK: movimenti -> righe contabili -> fondi -> atti.
SELECT set_config('zeroerp.maintenance_allow_delete_logs', 'on', true);

UPDATE vendite.fatture
   SET storicizza = false
 WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti);

DELETE FROM vendite.fatture_log
 WHERE fattura_id IN (SELECT id FROM tmp_dst UNION ALL SELECT id FROM tmp_src);

DELETE FROM pagamenti.vendite_movimenti
 WHERE contabile_riga_id IN (SELECT riga_id FROM tmp_riga);

-- ⚠️ Dal 2026-09-14 (D17) il DELETE di una riga contabile passa dal guard del
--    contenuto della distinta: sotto una CHIUSA o una GENERATA e' rifiutato.
--    Questo cleanup e' un passaggio tecnico e lo dichiara con la stessa GUC
--    che usa la madre del giro dei fondi (fn_cancella_fondo_fattura); il
--    ROLLBACK farebbe comunque il lavoro.
SELECT set_config('zeroerp.allow_contabile_riga_delete_override', 'on', true);
DELETE FROM pagamenti.vendite_contabili_righe
 WHERE fondo_source_id IN (SELECT source_id FROM tmp_atto);

DELETE FROM vendite.fatture_fondi_fattura
 WHERE fattura_id IN (SELECT id FROM tmp_dst);

DELETE FROM vendite.fatture_fondi_fattura_source
 WHERE fattura_sorgente_id IN (SELECT id FROM tmp_src);

DELETE FROM vendite.fatture
 WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti);

SELECT * FROM finish();

ROLLBACK;
