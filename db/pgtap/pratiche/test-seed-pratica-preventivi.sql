-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
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

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- ⚠️ Questo file non apre una transazione propria: la riga va prima di plan().
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
