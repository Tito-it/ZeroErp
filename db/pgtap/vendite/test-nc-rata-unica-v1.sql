-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la NOTA DI CREDITO ha UNA rata — P-5 / D19-e per intero
--       (changeSet 20260917-11 · -12 · -13 · -14)
--
-- Elenco test (plan 13):
--  1) Riferimenti costruiti (azienda, operatore, cliente, coppia emittente/utility) e a catalogo
--  2) ⭐ La NC genera UNA rata col segno: importo = totale a pagare (negativo), numero 1
--  3) ...alla PRIMA data del termine (fine mese di data + 30: Q-C, nessuna seconda regola)
--  4) ...e meta della rata e snapshot in testata dichiarano rata_unica_credito
--  5) La nota NON critica resta, riformulata (Q-D)
--  6) ⭐ La NC con la sua rata SI NUMERA (il terzo contro-pezzo, condizione 4 di D-K)
--  7) ⛔ Una rata di segno sbagliato NON si numera: la somma col segno e' il presidio (il CHECK non c'e' piu')
--  8) Un rimborso parziale sulla rata della NC entra senza dire niente (verso giusto)
--  9) ⭐ «Il cliente paga la NC» (+15 su un credito): il guard di capienza lo SEGNALA
-- 10) ...e con la forzatura entra, e dopo il posting l'elenco dice MOVIMENTO_CONTRARIO
-- 11) Un rimborso oltre il credito (forzato): l'elenco dice SOVRA_INCASSATA — sovra-rimborsata
-- 12) L'elenco porta numero_documento dalla sede unica (P-1-bis): «numero - serie» sulla NC numerata
-- 13) ⭐ L'elenco porta la NATURA del documento (P-7): codice_interno NOTA_CREDITO e la descrizione a catalogo
--
-- Scopo:
--  - costruire la nota di credito per intero — righe negative (D-NC-2),
--    riepiloghi, totali, piano rate, numerazione — e provare che i TRE
--    contro-pezzi sono caduti insieme: il generatore (una rata col segno),
--    il CHECK sull'importo (una rata negativa si scrive), la numerazione
--    (condizioni 3-4 col segno);
--  - provare l'argomento di P-5 sul modello: senza rata, una riga sulla NC
--    non incontrava nessuna capienza; con la rata, «il cliente paga la NC»
--    passa dal guard di D14-c come tutto il resto (9-10);
--  - provare la forma di D14-c su vw_rate_fuori_capienza (10-11): su una rata
--    negativa i due motivi escono giusti — prima uscivano invertiti.
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (rev 2026-09-17 sera). La prima
--   stesura ricopiava la «terna scelta insieme» di
--   test-numerazione-guard-coerenza-v1 — una riga di
--   anagrafiche.emittenti_fiscali_utilities con un billing account della
--   stessa utility — che in baseline-rossi-ci.tsv e' gia' ERRORE_FIXTURE per
--   lo stesso motivo: su un database ricostruito dai changelog (zeroerp_ci, la
--   CI) le anagrafiche sono a ZERO, tmp_refs_nc usciva vuota e il registro
--   nasceva con emittente NULL — nessuna delle 12 asserzioni eseguita.
--   Ora: un'azienda col suo operatore (dbops.fn_pgtap_crea_emittente_operatore)
--   PRIMA del contesto; NEL contesto un cliente fatturabile
--   (dbops.fn_pgtap_crea_cliente_ba) e la riga emittente/utility che
--   fn_ricalcola_totali_fattura pretende (arrotondamento a 2 decimali,
--   HALF_UP: la configurazione che il ricalcolo legge, scritta dal test e non
--   pescata dalla macchina) — guida pgtap-come-si-scrive-un-test §«Il mondo si
--   costruisce, non si cerca».
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore.
CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- Fixture
-- ============================================================
-- Il cliente fatturabile, nel contesto dell'operatore: il legame BA -> emittente
-- lo scrive il trigger z90 verso l'emittente di chi agisce.
CREATE TEMP TABLE tmp_cli_nc AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('NC rata unica') c;

-- La coppia (emittente, utility) che fn_ricalcola_totali_fattura pretende
-- (E_CONFIG_MANCANTE senza): la terna emittente/utility/BA e' COSTRUITA
-- coerente, non scelta insieme fra i dati della macchina.
INSERT INTO anagrafiche.emittenti_fiscali_utilities
    (emittente_soggetto_ruolo_id, utility_id, arrotondamento_importi_dec,
     metodo_arrotondamento_importi, meta)
SELECT m.soggetto_ruolo_id, c.utility_id, 2, 'HALF_UP',
       jsonb_build_object('test_scope', 'pgtap_nc_rata_unica')
  FROM _mondo m, tmp_cli_nc c;

CREATE TEMP TABLE tmp_refs_nc AS
SELECT m.soggetto_ruolo_id                                                                AS emittente_soggetto_ruolo_id,
       (SELECT utility_id FROM tmp_cli_nc)                                                AS utility_id,
       (SELECT billing_account_id FROM tmp_cli_nc)                                        AS billing_account_id,
       (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DRAFT')            AS stato_draft_id,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1)   AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY (iso_code <> 'EUR'), id LIMIT 1)             AS valuta_id,
       (SELECT id FROM config.iva WHERE attivo IS TRUE ORDER BY id LIMIT 1)                AS iva_id,
       -- ⭐ Un termine a DUE rate, fine mese: la NC deve fare UNA rata lo stesso,
       --    alla prima data del termine (fine mese di data + 30).
       (SELECT id FROM config.termini_pagamento
         WHERE codice_interno = 'TP_30_60_EOM_2R' AND attivo IS TRUE)                      AS termine_2r_id,
       config.fn_get_natura_doc_fiscale_id('NOTA_CREDITO')                                 AS natura_nc_id,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA' ORDER BY c.id LIMIT 1)      AS centro_banca_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'ABBINATA' ORDER BY s.id LIMIT 1)                        AS stato_abbinata_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'VALIDATA' ORDER BY s.id LIMIT 1)                        AS stato_validata_id
  FROM _mondo m;

-- Registro dedicato e vergine, dello STESSO emittente delle note.
CREATE TEMP TABLE tmp_reg_nc AS
WITH ins AS (
  INSERT INTO vendite.registri_fatturazione (codice, descrizione, reset_policy, attivo,
          emittente_soggetto_ruolo_id, meta)
  VALUES ('REGNC_pgtap', 'Registro test NC rata unica', 'ANNUALE', true,
          (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_nc),
          jsonb_build_object('test_scope', 'pgtap_nc_rata_unica'))
  RETURNING id)
SELECT * FROM ins;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND termine_2r_id IS NOT NULL AND natura_nc_id IS NOT NULL
      AND centro_banca_id IS NOT NULL AND stato_abbinata_id IS NOT NULL AND stato_validata_id IS NOT NULL
     FROM tmp_refs_nc)
  AND (SELECT id IS NOT NULL FROM tmp_reg_nc),
  '1) Riferimenti costruiti (terna emittente/utility/BA, registro) e a catalogo (termine a 2 rate, natura NC, centro, stati)'
);

-- Una nota di credito con UNA riga a quantita' NEGATIVA (D-NC-2: il segno sta
-- nel numero), portata a stato completo con le funzioni vere e nell'ordine
-- della pipeline: IVA -> totali -> rate. Due statement, non una CTE (RLS).
CREATE FUNCTION pg_temp.fx_nc(p_prezzo numeric) RETURNS bigint LANGUAGE plpgsql AS $fx$
DECLARE
  v_id bigint;
BEGIN
  -- ⛔ La data e' script.fn_data_operativa(), MAI un letterale (rev 2026-09-23): il test 6
  --   NUMERA la nota, e la numerazione applica la finestra di emissione del
  --   registro («non piu' di N giorni fa»). Con DATE '2026-09-10' il test e'
  --   diventato rosso da solo il 23-09, a codice invariato. Il registro e'
  --   vergine, quindi oggi e' sempre una data ammessa.
  INSERT INTO vendite.fatture (registro_id, data, emittente_soggetto_ruolo_id,
                               billing_account_id, utility_id, stato_doc_fiscale_id,
                               tipo_doc_fiscale_id, valuta_id, termine_pagamento_id,
                               natura_doc_id, meta)
  SELECT (SELECT id FROM tmp_reg_nc), script.fn_data_operativa(),
         r.emittente_soggetto_ruolo_id, r.billing_account_id, r.utility_id,
         r.stato_draft_id, r.tipo_doc_fiscale_id, r.valuta_id, r.termine_2r_id,
         r.natura_nc_id, jsonb_build_object('test_scope', 'pgtap_nc_rata_unica')
    FROM tmp_refs_nc r
  RETURNING id INTO v_id;

  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta,
                                     prezzo_unitario, iva_id, meta, competenza_dal, competenza_al)
  VALUES (v_id, 1, 'Riga test NC rata unica', -1::numeric, p_prezzo,
          (SELECT iva_id FROM tmp_refs_nc),
          jsonb_build_object('test_scope', 'pgtap_nc_rata_unica'), script.fn_data_operativa(), script.fn_data_operativa());

  PERFORM vendite.fn_ricalcola_riepilogo_iva_fattura(v_id);
  PERFORM vendite.fn_ricalcola_totali_fattura(v_id);
  PERFORM vendite.fn_genera_scadenze_fattura(v_id);
  RETURN v_id;
END;
$fx$;

CREATE TEMP TABLE tmp_nc AS
SELECT pg_temp.fx_nc(100) AS id, 'A' AS ruolo
UNION ALL SELECT pg_temp.fx_nc(100), 'B'
UNION ALL SELECT pg_temp.fx_nc(100), 'C';

-- ============================================================
-- 2-5) Il generatore: una rata col segno, alla prima data del termine
-- ============================================================
SELECT ok(
  (SELECT count(*) = 1
      AND bool_and(s.numero_rata = 1)
      AND bool_and(s.importo = f.totale_a_pagare)
      AND bool_and(s.importo < 0)
     FROM vendite.fatture_scadenze s
     JOIN vendite.fatture f ON f.id = s.fattura_id
    WHERE s.fattura_id = (SELECT id FROM tmp_nc WHERE ruolo = 'A')),
  '2) La NC genera UNA rata col segno: importo = totale a pagare (negativo), numero 1 — su un termine a 2 rate'
);

SELECT is(
  (SELECT s.data_scadenza FROM vendite.fatture_scadenze s
    WHERE s.fattura_id = (SELECT id FROM tmp_nc WHERE ruolo = 'A')),
  (date_trunc('month', (script.fn_data_operativa() + 30)::timestamp) + interval '1 month - 1 day')::date,
  '3) ...alla PRIMA data del termine: fine mese di data + 30 (Q-C: la rata resta figlia del termine)'
);

SELECT ok(
  (SELECT (s.meta->>'rata_unica_credito')::boolean IS TRUE
     FROM vendite.fatture_scadenze s
    WHERE s.fattura_id = (SELECT id FROM tmp_nc WHERE ruolo = 'A'))
  -- ⭐ Lo snapshot descrive il piano APPLICATO, non il catalogo: numero_rate = 1
  --   (v_num_rate := 1 precede la sua costruzione) e rata_unica_credito spiega
  --   il perche'; il termine d'origine resta leggibile da termine_pagamento_id e
  --   codice_interno (TP_30_60_EOM_2R, che di rate ne dice 2).
  AND (SELECT (f.termine_pagamento_snapshot->>'rata_unica_credito')::boolean IS TRUE
          AND (f.termine_pagamento_snapshot->>'numero_rate')::int = 1
          AND f.termine_pagamento_snapshot->>'codice_interno' = 'TP_30_60_EOM_2R'
         FROM vendite.fatture f WHERE f.id = (SELECT id FROM tmp_nc WHERE ruolo = 'A')),
  '4) ...e meta della rata e snapshot in testata dichiarano rata_unica_credito (snapshot: numero_rate 1, termine a 2)'
);

SELECT ok(
  (SELECT count(*) = 1
     FROM vendite.fatture_log fl
    WHERE fl.fattura_id = (SELECT id FROM tmp_nc WHERE ruolo = 'A')
      AND fl.status = 'W'
      AND fl.meta->>'error_code' = 'W_SCADENZE_TOTALE_NEGATIVO'
      AND (fl.meta->>'rata_unica_credito')::boolean IS TRUE
      AND fl.messaggio LIKE '%rata unica di credito%'),
  '5) La nota NON critica resta, riformulata: «generata una rata unica di credito» (Q-D)'
);

-- ============================================================
-- 6-7) La numerazione: il terzo contro-pezzo
-- ============================================================
SELECT lives_ok(
  $$ SELECT * FROM vendite.fn_assign_numero_fattura((SELECT id FROM tmp_nc WHERE ruolo = 'A')) $$,
  '6) La NC con la sua rata SI NUMERA: la condizione 4 di D-K non respinge piu'' il negativo'
);

-- ⛔ Una rata di segno sbagliato: il CHECK non c'e' piu' (l'UPDATE passa), ma la
--   numerazione la ferma — somma delle rate col segno diversa dal totale.
UPDATE vendite.fatture_scadenze s
   SET importo = abs(s.importo)
 WHERE s.fattura_id = (SELECT id FROM tmp_nc WHERE ruolo = 'B');

SELECT throws_like(
  $$ SELECT * FROM vendite.fn_assign_numero_fattura((SELECT id FROM tmp_nc WHERE ruolo = 'B')) $$,
  '%somma delle rate%diversa dal totale a pagare%',
  '7) Una rata di segno sbagliato NON si numera: la somma col segno e'' il presidio, il CHECK non serve'
);

-- ============================================================
-- 8-11) La capienza sulla rata della NC, e l'elenco
-- ============================================================
CREATE TEMP TABLE tmp_rata_nc AS
SELECT s.id AS scadenza_id, s.fattura_id, s.importo, f.billing_account_id
  FROM vendite.fatture_scadenze s
  JOIN vendite.fatture f ON f.id = s.fattura_id
 WHERE s.fattura_id = (SELECT id FROM tmp_nc WHERE ruolo = 'A');

CREATE TEMP TABLE tmp_contabile AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_banca_id FROM tmp_refs_nc),
    p_data_contabile        => script.fn_data_operativa(),
    p_data_registrazione    => script.fn_data_operativa(),
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', 'pgtap_nc_rata_unica'),
    p_origine               => 'MANUALE'
  ) AS contabile_id;

-- 8) Un rimborso PARZIALE: verso giusto, non supera → entra senza dire niente.
SELECT lives_ok(
  format($q$INSERT INTO pagamenti.vendite_contabili_righe
             (contabile_id, riferimento_ente, data_pagamento, importo, fattura_id, billing_account_id, scadenza_id, stato_id)
           VALUES (%s, 'PGTAP_NC_RIMBORSO', script.fn_data_operativa(), -10.00, %s, %s, %s, %s)$q$,
         (SELECT contabile_id FROM tmp_contabile),
         (SELECT fattura_id FROM tmp_rata_nc),
         (SELECT billing_account_id FROM tmp_rata_nc),
         (SELECT scadenza_id FROM tmp_rata_nc),
         (SELECT stato_abbinata_id FROM tmp_refs_nc)),
  '8) Un rimborso parziale sulla rata della NC entra senza dire niente (verso giusto, non supera)'
);

-- 9) ⭐ «Il cliente paga la nota di credito»: verso SBAGLIATO → il guard segnala.
--    Prima di P-5 questa riga entrava senza rata, e nessuna capienza la vedeva.
SELECT throws_like(
  format($q$INSERT INTO pagamenti.vendite_contabili_righe
             (contabile_id, importo, fattura_id, billing_account_id, scadenza_id, stato_id)
           VALUES (%s, 15.00, %s, %s, %s, %s)$q$,
         (SELECT contabile_id FROM tmp_contabile),
         (SELECT fattura_id FROM tmp_rata_nc),
         (SELECT billing_account_id FROM tmp_rata_nc),
         (SELECT scadenza_id FROM tmp_rata_nc),
         (SELECT stato_abbinata_id FROM tmp_refs_nc)),
  -- ⭐ Dal 2026-09-18 (20260918-04) il residuo esce col SEGNO e a DUE decimali:
  --   «restano -N.NN da regolare: un importo di 15.00 non ci rientra». Il `_`
  --   di LIKE conta i caratteri: con sei decimali il pattern non chiude.
  '%restano -%.__ da regolare: un importo di 15.00 non ci rientra%',
  '9) «Il cliente paga la NC» (+15 su un credito): il guard di capienza lo SEGNALA — col segno, a due decimali'
);

-- 10) ...e con la forzatura entra; registrato, l'elenco lo chiama col nome giusto.
INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, importo, fattura_id, billing_account_id,
     scadenza_id, stato_id, forzata, motivo_forzatura)
SELECT (SELECT contabile_id FROM tmp_contabile), 'PGTAP_NC_PAGATA', script.fn_data_operativa(), 15.00,
       r.fattura_id, r.billing_account_id, r.scadenza_id,
       (SELECT stato_abbinata_id FROM tmp_refs_nc),
       true, 'Il cliente ha pagato la nota di credito'
  FROM tmp_rata_nc r;

UPDATE pagamenti.vendite_contabili c
   SET stato_id = (SELECT stato_validata_id FROM tmp_refs_nc)
 WHERE c.id = (SELECT contabile_id FROM tmp_contabile);

CREATE TEMP TABLE tmp_esito AS
SELECT * FROM pagamenti.fn_posta_contabile((SELECT contabile_id FROM tmp_contabile));

-- Residuo atteso: importo (negativo) - (-10 + 15) = importo - 5 → piu' negativo
-- dell'importo: |saldo| > |importo|, stesso segno → MOVIMENTO_CONTRARIO.
SELECT ok(
  (SELECT v.motivo = 'MOVIMENTO_CONTRARIO'
      AND v.residuo = (SELECT importo FROM tmp_rata_nc) - 5.00
      AND v.righe_forzate = 1
     FROM pagamenti.vw_rate_fuori_capienza v
    WHERE v.scadenza_id = (SELECT scadenza_id FROM tmp_rata_nc)),
  '10) ...con la forzatura entra, e dopo il posting l''elenco dice MOVIMENTO_CONTRARIO (prima diceva SOVRA)'
);

-- 11) Sulla terza NC: un rimborso OLTRE il credito (forzato) attraversa lo zero.
CREATE TEMP TABLE tmp_rata_nc_c AS
SELECT s.id AS scadenza_id, s.fattura_id, s.importo, f.billing_account_id
  FROM vendite.fatture_scadenze s
  JOIN vendite.fatture f ON f.id = s.fattura_id
 WHERE s.fattura_id = (SELECT id FROM tmp_nc WHERE ruolo = 'C');

CREATE TEMP TABLE tmp_contabile_c AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_banca_id FROM tmp_refs_nc),
    p_data_contabile        => script.fn_data_operativa() - 1,
    p_data_registrazione    => script.fn_data_operativa(),
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', 'pgtap_nc_rata_unica'),
    p_origine               => 'MANUALE'
  ) AS contabile_id;

INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, importo, fattura_id, billing_account_id,
     scadenza_id, stato_id, forzata, motivo_forzatura)
SELECT (SELECT contabile_id FROM tmp_contabile_c), 'PGTAP_NC_SOVRA', script.fn_data_operativa(),
       r.importo - 20.00,                           -- oltre il credito, nel verso giusto
       r.fattura_id, r.billing_account_id, r.scadenza_id,
       (SELECT stato_abbinata_id FROM tmp_refs_nc),
       true, 'Rimborso calcolato su un dato vecchio'
  FROM tmp_rata_nc_c r;

UPDATE pagamenti.vendite_contabili c
   SET stato_id = (SELECT stato_validata_id FROM tmp_refs_nc)
 WHERE c.id = (SELECT contabile_id FROM tmp_contabile_c);

SELECT pagamenti.fn_posta_contabile((SELECT contabile_id FROM tmp_contabile_c));

-- Residuo atteso: importo - (importo - 20) = +20 → segno diverso → SOVRA_INCASSATA.
SELECT ok(
  (SELECT v.motivo = 'SOVRA_INCASSATA' AND v.residuo = 20.00
     FROM pagamenti.vw_rate_fuori_capienza v
    WHERE v.scadenza_id = (SELECT scadenza_id FROM tmp_rata_nc_c)),
  '11) Un rimborso oltre il credito: l''elenco dice SOVRA_INCASSATA — sovra-rimborsata, ha attraversato lo zero'
);

-- 12) numero_documento dalla sede unica, sulla NC numerata (A) e NULL sulla non numerata (C).
SELECT ok(
  (SELECT v.numero_documento = vendite.fn_numero_documento_fattura(f.numero, f.serie)
      AND v.numero_documento IS NOT NULL
     FROM pagamenti.vw_rate_fuori_capienza v
     JOIN vendite.fatture f ON f.id = v.fattura_id
    WHERE v.scadenza_id = (SELECT scadenza_id FROM tmp_rata_nc))
  AND (SELECT v.numero_documento IS NULL
         FROM pagamenti.vw_rate_fuori_capienza v
        WHERE v.scadenza_id = (SELECT scadenza_id FROM tmp_rata_nc_c)),
  '12) L''elenco porta numero_documento dalla sede unica: valorizzato sulla NC numerata, NULL sulla bozza'
);

-- 13) ⭐ P-7 (20260918-03): la natura viaggia con la riga. Il vocabolario dei
--    motivi resta a due valori e la sfumatura («sovra-rimborsata») la dice
--    l'etichetta del frontend — che ramifica su codice_interno (§6c) e
--    mostra la descrizione. Su TUTTE le righe delle NC costruite.
SELECT ok(
  (SELECT count(*) = 2
      AND bool_and(v.natura_doc_codice_interno = 'NOTA_CREDITO')
      AND bool_and(v.natura_doc_descrizione = nd.descrizione)
     FROM pagamenti.vw_rate_fuori_capienza v
     JOIN config.nature_doc_fiscale nd ON nd.id = (SELECT natura_nc_id FROM tmp_refs_nc)
    WHERE v.scadenza_id IN ((SELECT scadenza_id FROM tmp_rata_nc),
                            (SELECT scadenza_id FROM tmp_rata_nc_c))),
  '13) L''elenco porta la natura del documento: NOTA_CREDITO (codice_interno) e la descrizione a catalogo, sulle due NC'
);

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
