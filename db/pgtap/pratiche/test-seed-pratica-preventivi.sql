-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: seed catalogo pratica PREVENTIVI (B4-B7)
--       tipi_prestazione + template_flussi + handler_params + prerequisiti
--       esito-aware + handler_flussi + canali. Asserzioni read-only sui dati.
--
-- Indice test:
-- 0) 2 tipi_prestazione PREVENTIVI (pre/post false, categoria COMMERCIALE)
-- 1) 4 template_flussi per ciascun tipo (8 totali)
-- 2) Catena codici + direzioni corrette
-- 3) CONFERMA: handler_params modalita_fatturazione IMMEDIATA/DIFFERITA
-- 4) CONFERMA: handler_id -> handler_key 'vendita.push_preventivo'
-- 5) Prerequisiti lineari con esito_richiesto='POSITIVO' (3 per tipo)
-- 6) Canali WEB_CLIENTI sui flussi ENTRATA
-- 7) handler_flussi 'vendita.push_preventivo' attivo
-- ------------------------------------------------------------

SELECT plan(9);

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
-- 4) CONFERMA: handler_id -> handler_key
-- =========================================================

SELECT is(
    (SELECT count(*)::integer
       FROM pratiche.template_flussi tf
       JOIN pratiche.tipi_prestazione tp ON tp.id = tf.tipo_prestazione_id
       JOIN pratiche.handler_flussi hf ON hf.id = tf.handler_id
      WHERE tp.codice_interno IN ('PREVENTIVI_IMMEDIATA','PREVENTIVI_DIFFERITA')
        AND tf.codice = 'CONFERMA'
        AND hf.handler_key = 'vendita.push_preventivo'),
    2,
    '6. Entrambi i CONFERMA puntano a handler vendita.push_preventivo'
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

SELECT * FROM finish();
