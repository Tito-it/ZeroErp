-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: seed catalogo pratica PREVENTIVI (B4-B7) — post ritiro handler
--       monolitico push_preventivo (2026-07-02, brief disinnesco binding).
--       tipi_prestazione + template_flussi + handler_params + prerequisiti
--       esito-aware + handler_flussi + canali. Asserzioni read-only sui dati.
--
-- Indice test (0..10):
-- 0) 2 tipi_prestazione PREVENTIVI (pre/post false, categoria COMMERCIALE)
-- 1) 8 template_flussi (4 per tipo IMMEDIATA/DIFFERITA)
-- 2) Catena 4 codici (RICHIESTA_CLIENTE->PREVENTIVAZIONE->APPROVAZIONE_CLIENTE->CONFERMA)
-- 3) RICHIESTA_CLIENTE/APPROVAZIONE_CLIENTE sono ENTRATA (4)
-- 4) CONFERMA IMMEDIATA: handler_params.modalita_fatturazione = IMMEDIATA
-- 5) CONFERMA DIFFERITA: handler_params.modalita_fatturazione = DIFFERITA
-- 6) CONFERMA di 9002/9003 SBINDATI (handler_id IS NULL) — push_preventivo ritirato
-- 7) 6 prerequisiti lineari esito_richiesto='POSITIVO' (3 per tipo)
-- 8) 4 canali WEB_CLIENTI sui flussi ENTRATA
-- 9) handler_flussi 'vendita.push_preventivo' deprecato (attivo=false)
-- 10) tipi IMMEDIATA/DIFFERITA con obsoleto_dal valorizzato
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. Messa in testa e non in coda
--   apposta: in coda scatterebbero tutti insieme DOPO il cleanup, su righe
--   ormai cancellate, e fallirebbero per un motivo che non riguarda il test.
--   Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(11);

-- =========================================================
-- 0) tipi_prestazione PREVENTIVI
-- =========================================================

SELECT is(
    (SELECT count(*)::integer FROM pratiche.tipi_prestazione
      WHERE codice_interno IN ('PREVENTIVI_IMMEDIATA', 'PREVENTIVI_DIFFERITA')
        AND categoria = 'COMMERCIALE'
        AND pre_attivazione = false AND post_attivazione = false),
    2,
    '0. 2 tipi_prestazione PREVENTIVI (COMMERCIALE, pre/post false)'
);

-- =========================================================
-- 1) 4 template_flussi per tipo (8 totali)
-- =========================================================

SELECT is(
    (SELECT count(*)::integer FROM pratiche.template_flussi tf
      JOIN pratiche.tipi_prestazione tp ON tp.id = tf.tipo_prestazione_id
     WHERE tp.codice_interno IN ('PREVENTIVI_IMMEDIATA', 'PREVENTIVI_DIFFERITA')),
    8,
    '1. 8 template_flussi totali (4 per tipo)'
);

-- =========================================================
-- 2) Catena codici (4 distinti) + direzioni
-- =========================================================

SELECT is(
    (SELECT count(DISTINCT tf.codice)::integer FROM pratiche.template_flussi tf
      JOIN pratiche.tipi_prestazione tp ON tp.id = tf.tipo_prestazione_id
     WHERE tp.codice_interno = 'PREVENTIVI_IMMEDIATA'
       AND tf.codice IN ('RICHIESTA_CLIENTE','PREVENTIVAZIONE','APPROVAZIONE_CLIENTE','CONFERMA')),
    4,
    '2. Catena 4 flussi RICHIESTA_CLIENTE->PREVENTIVAZIONE->APPROVAZIONE_CLIENTE->CONFERMA'
);

SELECT is(
    (SELECT count(*)::integer FROM pratiche.template_flussi tf
      JOIN pratiche.tipi_prestazione tp ON tp.id = tf.tipo_prestazione_id
     WHERE tp.codice_interno IN ('PREVENTIVI_IMMEDIATA','PREVENTIVI_DIFFERITA')
       AND tf.codice IN ('RICHIESTA_CLIENTE','APPROVAZIONE_CLIENTE')
       AND tf.direzione = 'ENTRATA'),
    4,
    '3. I 4 flussi RICHIESTA_CLIENTE/APPROVAZIONE_CLIENTE sono ENTRATA'
);

-- =========================================================
-- 3) CONFERMA: handler_params modalita_fatturazione
-- =========================================================

SELECT is(
    (SELECT tf.handler_params ->> 'modalita_fatturazione'
       FROM pratiche.template_flussi tf
       JOIN pratiche.tipi_prestazione tp ON tp.id = tf.tipo_prestazione_id
      WHERE tp.codice_interno = 'PREVENTIVI_IMMEDIATA' AND tf.codice = 'CONFERMA'),
    'IMMEDIATA',
    '4. CONFERMA tipo IMMEDIATA: handler_params.modalita_fatturazione = IMMEDIATA'
);

SELECT is(
    (SELECT tf.handler_params ->> 'modalita_fatturazione'
       FROM pratiche.template_flussi tf
       JOIN pratiche.tipi_prestazione tp ON tp.id = tf.tipo_prestazione_id
      WHERE tp.codice_interno = 'PREVENTIVI_DIFFERITA' AND tf.codice = 'CONFERMA'),
    'DIFFERITA',
    '5. CONFERMA tipo DIFFERITA: handler_params.modalita_fatturazione = DIFFERITA'
);

-- =========================================================
-- 4) CONFERMA sbindati: handler push_preventivo ritirato (unbind seed 08)
-- =========================================================

SELECT is(
    (SELECT count(*)::integer
       FROM pratiche.template_flussi tf
       JOIN pratiche.tipi_prestazione tp ON tp.id = tf.tipo_prestazione_id
      WHERE tp.codice_interno IN ('PREVENTIVI_IMMEDIATA','PREVENTIVI_DIFFERITA')
        AND tf.codice = 'CONFERMA'
        AND tf.handler_id IS NULL),
    2,
    '6. I CONFERMA di 9002/9003 sono sbindati (handler_id IS NULL): push_preventivo ritirato'
);

-- =========================================================
-- 5) Prerequisiti lineari esito-aware (3 per tipo, esito POSITIVO)
-- =========================================================

SELECT is(
    (SELECT count(*)::integer
       FROM pratiche.template_flussi_prerequisiti tfp
       JOIN pratiche.template_flussi tf ON tf.id = tfp.template_flusso_id
       JOIN pratiche.tipi_prestazione tp ON tp.id = tf.tipo_prestazione_id
      WHERE tp.codice_interno IN ('PREVENTIVI_IMMEDIATA','PREVENTIVI_DIFFERITA')
        AND tfp.esito_richiesto = 'POSITIVO'),
    6,
    '7. 6 prerequisiti lineari (3 per tipo) con esito_richiesto = POSITIVO'
);

-- =========================================================
-- 6) Canali WEB_CLIENTI sui flussi ENTRATA
-- =========================================================

SELECT is(
    (SELECT count(*)::integer
       FROM pratiche.template_flussi_canali tfc
       JOIN pratiche.template_flussi tf ON tf.id = tfc.template_flusso_id
       JOIN pratiche.tipi_prestazione tp ON tp.id = tf.tipo_prestazione_id
       JOIN config.canali_pratiche cp ON cp.id = tfc.canale_id
      WHERE tp.codice_interno IN ('PREVENTIVI_IMMEDIATA','PREVENTIVI_DIFFERITA')
        AND tf.direzione = 'ENTRATA'
        AND cp.codice_interno = 'WEB_CLIENTI'),
    4,
    '8. 4 canali WEB_CLIENTI sui flussi ENTRATA'
);

-- =========================================================
-- 7) Ritiro handler push_preventivo + obsolescenza tipi (2026-07-02)
-- =========================================================

SELECT is(
    (SELECT hf.attivo
       FROM pratiche.handler_flussi hf
      WHERE hf.handler_key = 'vendita.push_preventivo'),
    false,
    '9. handler_flussi vendita.push_preventivo e'' deprecato (attivo=false)'
);

SELECT is(
    (SELECT count(*)::integer
       FROM pratiche.tipi_prestazione
      WHERE codice_interno IN ('PREVENTIVI_IMMEDIATA','PREVENTIVI_DIFFERITA')
        AND obsoleto_dal IS NOT NULL),
    2,
    '10. tipi IMMEDIATA/DIFFERITA hanno obsoleto_dal valorizzato (tipo unico PREVENTIVI subentra)'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
