-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: LA REGISTRAZIONE TARDIVA PER RIGA — pagamenti.fn_posta_riga_tardiva
--       e la porta della quarta mossa (D20-b)
--
-- Elenco test (plan 20):
--  1) Riferimenti costruiti (azienda, operatore, cliente, fatture, rate) e a catalogo
--  2) La distinta e' REGISTRATA: CHIUSA, con data_conferma, quattro righe indietro
--  3) ⭐ Caso 1: una SOSPESA sotto la chiusa si registra — movimento nato, esito POSTATA
--  4) ...la riga e' POSTATA e il movimento porta rata, fattura, origine POSTING_TARDIVO, data di oggi
--  5) ...la testata e' ancora CHIUSA e data_conferma e' INVARIATA
--  6) ...e la somma delle righe della distinta non e' cambiata: la quadratura del giorno regge
--  7) Caso 10: sulla rata `incassato` e' cresciuto dell'importo e `in_lavorazione` e' zero
--  8) Caso 2: rata senza spazio, senza forzatura — E_RIGA_CONTABILE_CAPIENZA_SUPERATA, coi numeri
--  9) ...e non ha scritto NIENTE: la riga e' ancora SOSPESA, nessun movimento
-- 10) Caso 3: con la forzatura entra, e sulla riga resta scritto il perche'
-- 11) Caso 4: una SCARTATA non si registra da qui — E_RIGA_CONTABILE_TARDIVA_STATO
-- 12) Una riga gia' registrata nemmeno: nessun NULLA_DA_POSTARE, un rifiuto
-- 13) Caso 5: SOSPESA sotto una ANNULLATA — E_RIGA_CONTABILE_TARDIVA_DISTINTA_NON_REGISTRATA
-- 14) Caso 6: SOSPESA sotto una VALIDATA — idem, «usa il giro normale»
-- 15) Caso 7: la rata di un'ALTRA fattura — il guard della coerenza gira
-- 16) Caso 8: fuori dalla madre, SOSPESA -> ABBINATA sotto la chiusa e' ancora rifiutato (4ª mossa)
-- 17) Caso 9: la GUC settata su un ALTRO id non apre la porta
-- 18) Dopo la madre la porta e' richiusa: la GUC e' vuota
-- 19) Una riga che non esiste: E_RIGA_CONTABILE_NON_TROVATA
-- 20) Cleanup
--
-- Scopo:
--  - collaudare D20-b: il «resto» di D3-a ha un futuro. Sotto una distinta
--    registrata una sospesa si abbina e si registra nello stesso gesto (test
--    3-7), senza toccare la conferma della distinta ne' la sua quadratura;
--  - presidiare che la madre PASSI DA ABBINATA e che quindi girino i guard
--    dell'abbinamento normale: la capienza col doppio tempo (8-10) e la
--    coerenza della rata (15);
--  - presidiare la PORTA della quarta mossa (16-18): si apre solo per la riga
--    nominata dalla GUC, solo dentro la madre; un UPDATE a mano resta
--    rifiutato e la GUC su un altro id non apre;
--  - presidiare i rifiuti (11-14, 19): nessun esito NULLA_DA_POSTARE.
--
-- Brief: brief-db-validata-e-registrazione-tardiva §2.2, §4.1, §4.2
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca: un'azienda col suo operatore
--   (dbops.fn_pgtap_crea_emittente_operatore) PRIMA del contesto, un cliente
--   fatturabile (dbops.fn_pgtap_crea_cliente_ba) NEL contesto — guida
--   pgtap-come-si-scrive-un-test §«Il mondo si costruisce, non si cerca».
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore.
CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- ⚠️ 2. CONTESTO APPLICATIVO.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(20);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_posta_riga_tardiva'::text AS test_scope;

CREATE TEMP TABLE tmp_cli AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('posta riga tardiva') c;

CREATE TEMP TABLE tmp_refs AS
SELECT script.fn_pgtap_registro_fattura(m.soggetto_ruolo_id)                       AS registro_id,
       (SELECT billing_account_id FROM tmp_cli)                                      AS billing_account_id,
       (SELECT utility_id FROM tmp_cli)                                              AS utility_id,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1)                           AS valuta_id,
       m.soggetto_ruolo_id                                                          AS emittente_soggetto_ruolo_id,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA' ORDER BY c.id LIMIT 1) AS centro_banca_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'ABBINATA' ORDER BY s.id LIMIT 1)                  AS st_abbinata,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'SOSPESA'  ORDER BY s.id LIMIT 1)                  AS st_sospesa,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'SCARTATA' ORDER BY s.id LIMIT 1)                  AS st_scartata,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'VALIDATA'  ORDER BY s.id LIMIT 1)                 AS d_validata,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'ANNULLATA' ORDER BY s.id LIMIT 1)                 AS d_annullata
  FROM _mondo m;

-- Due fatture: la nostra (F, 350 in tre rate) e un'altra (G), per la coerenza.
CREATE TEMP TABLE tmp_fatture AS
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, totale_a_pagare, meta)
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id, r.billing_account_id,
         r.tipo_doc_fiscale_id, r.valuta_id, r.utility_id, v.totale,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti), 'ruolo', v.ruolo)
    FROM tmp_refs r, (VALUES ('F', 350.00), ('G', 100.00)) AS v(ruolo, totale)
  RETURNING id, meta ->> 'ruolo' AS ruolo
)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_rate AS
WITH ins AS (
  INSERT INTO vendite.fatture_scadenze (fattura_id, numero_rata, data_scadenza, importo, meta)
  SELECT f.id, v.n, script.fn_data_operativa() + v.n, v.importo,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti), 'rata', v.et)
    FROM (VALUES ('F', 1, 100.00, 'R1'),
                 ('F', 2, 200.00, 'R2'),
                 ('F', 3,  50.00, 'R3'),
                 ('G', 1, 100.00, 'RG')) AS v(ruolo, n, importo, et)
    JOIN tmp_fatture f ON f.ruolo = v.ruolo
  RETURNING id, meta ->> 'rata' AS etichetta, fattura_id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT registro_id IS NOT NULL AND billing_account_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL AND centro_banca_id IS NOT NULL
      AND st_abbinata IS NOT NULL AND st_sospesa IS NOT NULL AND st_scartata IS NOT NULL
      AND d_validata IS NOT NULL AND d_annullata IS NOT NULL
     FROM tmp_refs)
  AND (SELECT count(*) FROM tmp_rate) = 4,
  '1) Riferimenti costruiti (azienda, operatore, cliente, due fatture, quattro rate) e a catalogo'
);

-- ============================================================
-- La distinta del giorno: A ABBINATA 100 su R1, tre SOSPESE (S1 60, S2 40,
-- S3 10) e una SCARTATA (K 5). Si registra: A diventa POSTATA, la distinta
-- CHIUSA con la conferma, le altre quattro restano indietro. Σ = 215.
-- ============================================================
CREATE TEMP TABLE tmp_contabile AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_banca_id FROM tmp_refs),
    p_data_contabile        => script.fn_data_operativa(),
    p_data_registrazione    => script.fn_data_operativa(),
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
    p_origine               => 'MANUALE'
  ) AS contabile_id;

CREATE TEMP TABLE tmp_righe AS
WITH ins AS (
  INSERT INTO pagamenti.vendite_contabili_righe
      (contabile_id, riferimento_ente, data_pagamento, importo,
       fattura_id, billing_account_id, scadenza_id, stato_id, motivo_sospeso, meta)
  SELECT (SELECT contabile_id FROM tmp_contabile), 'PGTAP_TARD_' || v.et, script.fn_data_operativa(), v.importo,
         CASE WHEN v.et = 'A' THEN (SELECT id FROM tmp_fatture WHERE ruolo = 'F') END,
         CASE WHEN v.et = 'A' THEN r.billing_account_id END,
         CASE WHEN v.et = 'A' THEN (SELECT id FROM tmp_rate WHERE etichetta = 'R1') END,
         CASE v.et WHEN 'A' THEN r.st_abbinata
                   WHEN 'K' THEN r.st_scartata
                   ELSE          r.st_sospesa END,
         CASE WHEN v.et IN ('S1', 'S2', 'S3') THEN 'da capire di chi e''' END,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti), 'et', v.et)
    FROM tmp_refs r
    CROSS JOIN (VALUES ('A', 100.00::numeric), ('S1', 60.00::numeric), ('S2', 40.00::numeric),
                       ('S3', 10.00::numeric), ('K',   5.00::numeric)) AS v(et, importo)
  RETURNING id, meta ->> 'et' AS et
)
SELECT * FROM ins;

UPDATE pagamenti.vendite_contabili c
   SET stato_id = (SELECT d_validata FROM tmp_refs)
 WHERE c.id = (SELECT contabile_id FROM tmp_contabile);

CREATE TEMP TABLE tmp_posting AS
SELECT * FROM pagamenti.fn_posta_contabile((SELECT contabile_id FROM tmp_contabile));

-- Lo stato della testata DOPO la registrazione, tenuto da parte per il test 5.
CREATE TEMP TABLE tmp_testata_prima AS
SELECT c.stato_id, c.data_conferma, c.user_conferma,
       (SELECT COALESCE(SUM(cr.importo), 0) FROM pagamenti.vendite_contabili_righe cr
         WHERE cr.contabile_id = c.id AND cr.attivo IS TRUE) AS somma_righe
  FROM pagamenti.vendite_contabili c
 WHERE c.id = (SELECT contabile_id FROM tmp_contabile);

SELECT ok(
  (SELECT s.codice_interno = 'CHIUSA' AND c.data_conferma IS NOT NULL
     FROM pagamenti.vendite_contabili c
     JOIN pagamenti.vendite_contabili_stati s ON s.id = c.stato_id
    WHERE c.id = (SELECT contabile_id FROM tmp_contabile))
  AND (SELECT righe_postate = 1 AND righe_saltate = 4 FROM tmp_posting)
  AND (SELECT somma_righe = 215.00 FROM tmp_testata_prima),
  '2) La distinta e'' REGISTRATA (CHIUSA, con data_conferma): una postata, quattro indietro, Σ 215'
);

-- Il saldo della rata R2 PRIMA della tardiva, per il test 7.
CREATE TEMP TABLE tmp_r2_prima AS
SELECT * FROM pagamenti.fn_get_saldo_rata((SELECT id FROM tmp_rate WHERE etichetta = 'R2'));

-- ============================================================
-- 3-7) ⭐ Caso 1: S1 (60) su R2 (200, spazio) — si registra
-- ============================================================
-- ⚠️ Il verbo in un'istruzione SEPARATA dalle asserzioni.
CREATE TEMP TABLE tmp_esito AS
SELECT * FROM pagamenti.fn_posta_riga_tardiva(
    (SELECT id FROM tmp_righe WHERE et = 'S1'),
    (SELECT id FROM tmp_fatture WHERE ruolo = 'F'),
    (SELECT billing_account_id FROM tmp_refs),
    (SELECT id FROM tmp_rate WHERE etichetta = 'R2'));

SELECT ok(
  (SELECT movimento_id IS NOT NULL AND riga_id = (SELECT id FROM tmp_righe WHERE et = 'S1')
      AND importo = 60.00 AND esito = 'POSTATA'
     FROM tmp_esito),
  '3) Caso 1: una SOSPESA sotto la distinta chiusa si registra — movimento nato, esito POSTATA'
);

SELECT ok(
  (SELECT st.codice_interno = 'POSTATA'
     FROM pagamenti.vendite_contabili_righe cr
     JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
    WHERE cr.id = (SELECT id FROM tmp_righe WHERE et = 'S1'))
  AND (SELECT m.scadenza_id = (SELECT id FROM tmp_rate WHERE etichetta = 'R2')
           AND m.fattura_id = (SELECT id FROM tmp_fatture WHERE ruolo = 'F')
           AND m.contabile_id = (SELECT contabile_id FROM tmp_contabile)
           AND m.importo = 60.00
           AND m.meta ->> 'origine' = 'POSTING_TARDIVO'
           AND m.data_registrazione = script.fn_data_operativa()
           AND m.data_contabilizzazione = script.fn_data_operativa()
         FROM pagamenti.vendite_movimenti m
        WHERE m.id = (SELECT movimento_id FROM tmp_esito)),
  '4) La riga e'' POSTATA; il movimento porta rata, fattura, distinta, origine POSTING_TARDIVO e la data di oggi'
);

SELECT ok(
  (SELECT c.stato_id = p.stato_id
      AND c.data_conferma = p.data_conferma
      AND c.user_conferma = p.user_conferma
     FROM pagamenti.vendite_contabili c, tmp_testata_prima p
    WHERE c.id = (SELECT contabile_id FROM tmp_contabile)),
  '5) La testata e'' ancora CHIUSA e data_conferma / user_conferma sono INVARIATE: la conferma e'' della prima registrazione'
);

SELECT is(
  (SELECT COALESCE(SUM(cr.importo), 0) FROM pagamenti.vendite_contabili_righe cr
    WHERE cr.contabile_id = (SELECT contabile_id FROM tmp_contabile) AND cr.attivo IS TRUE),
  (SELECT somma_righe FROM tmp_testata_prima),
  '6) La somma delle righe della distinta non e'' cambiata: la riga era gia'' contata, la quadratura del giorno regge'
);

SELECT ok(
  (SELECT r.incassato = p.incassato + 60.00
      AND r.saldo = p.saldo - 60.00
      AND r.in_lavorazione = 0
     FROM pagamenti.fn_get_saldo_rata((SELECT id FROM tmp_rate WHERE etichetta = 'R2')) r,
          tmp_r2_prima p),
  '7) Caso 10: sulla rata `incassato` e'' cresciuto di 60 e `in_lavorazione` e'' zero'
);

-- ============================================================
-- 8-10) Caso 2 e 3: la capienza col doppio tempo
-- ============================================================
-- R1 (100) e' gia' saldata per intero da A: S2 (40) non ci rientra.
SELECT throws_like(
  format($q$SELECT * FROM pagamenti.fn_posta_riga_tardiva(%s, %s, %s, %s)$q$,
         (SELECT id FROM tmp_righe WHERE et = 'S2'),
         (SELECT id FROM tmp_fatture WHERE ruolo = 'F'),
         (SELECT billing_account_id FROM tmp_refs),
         (SELECT id FROM tmp_rate WHERE etichetta = 'R1')),
  '%restano 0.00 da regolare: un importo di 40.00 non ci rientra%',
  '8) Caso 2: rata senza spazio, senza forzatura — rifiutato coi numeri (il guard della rata gira)'
);

SELECT ok(
  (SELECT st.codice_interno = 'SOSPESA'
     FROM pagamenti.vendite_contabili_righe cr
     JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
    WHERE cr.id = (SELECT id FROM tmp_righe WHERE et = 'S2'))
  AND NOT EXISTS (SELECT 1 FROM pagamenti.vendite_movimenti m
                   WHERE m.contabile_riga_id = (SELECT id FROM tmp_righe WHERE et = 'S2')),
  '9) ...e non ha scritto niente: la riga e'' ancora SOSPESA, nessun movimento'
);

CREATE TEMP TABLE tmp_esito_forzata AS
SELECT * FROM pagamenti.fn_posta_riga_tardiva(
    (SELECT id FROM tmp_righe WHERE et = 'S2'),
    (SELECT id FROM tmp_fatture WHERE ruolo = 'F'),
    (SELECT billing_account_id FROM tmp_refs),
    (SELECT id FROM tmp_rate WHERE etichetta = 'R1'),
    true,
    'Il cliente ha pagato due volte lo stesso avviso');

SELECT ok(
  (SELECT esito = 'POSTATA' FROM tmp_esito_forzata)
  AND (SELECT cr.forzata IS TRUE AND cr.motivo_forzatura LIKE '%due volte%'
           AND st.codice_interno = 'POSTATA'
         FROM pagamenti.vendite_contabili_righe cr
         JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
        WHERE cr.id = (SELECT id FROM tmp_righe WHERE et = 'S2')),
  '10) Caso 3: con la forzatura entra, e sulla riga resta scritto che e'' stata forzata e perche'''
);

-- ============================================================
-- 11-12) I rifiuti sulla RIGA — nessun esito, un errore
-- ============================================================
SELECT throws_like(
  format($q$SELECT * FROM pagamenti.fn_posta_riga_tardiva(%s, %s, %s)$q$,
         (SELECT id FROM tmp_righe WHERE et = 'K'),
         (SELECT id FROM tmp_fatture WHERE ruolo = 'F'),
         (SELECT billing_account_id FROM tmp_refs)),
  '%non e'' sospesa (Riga scartata definitivamente)%',
  '11) Caso 4: una SCARTATA non si registra da qui — prima «Riprendi», poi la tardiva'
);

SELECT throws_like(
  format($q$SELECT * FROM pagamenti.fn_posta_riga_tardiva(%s, %s, %s)$q$,
         (SELECT id FROM tmp_righe WHERE et = 'S1'),
         (SELECT id FROM tmp_fatture WHERE ruolo = 'F'),
         (SELECT billing_account_id FROM tmp_refs)),
  '%non e'' sospesa%',
  '12) Una riga gia'' registrata e'' un RIFIUTO, non un esito NULLA_DA_POSTARE'
);

-- ============================================================
-- 13-14) I rifiuti sulla TESTATA: annullata, e ancora aperta
-- ============================================================
CREATE TEMP TABLE tmp_contabile_ann AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_banca_id FROM tmp_refs),
    p_data_contabile        => script.fn_data_operativa() - 1,
    p_data_registrazione    => script.fn_data_operativa(),
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
    p_origine               => 'MANUALE'
  ) AS contabile_id;

INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, importo, stato_id, motivo_sospeso, meta)
SELECT (SELECT contabile_id FROM tmp_contabile_ann), 'PGTAP_TARD_S4', script.fn_data_operativa(), 7.00,
       r.st_sospesa, 'sospesa poi annullata',
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti), 'et', 'S4')
  FROM tmp_refs r;

UPDATE pagamenti.vendite_contabili
   SET stato_id = (SELECT d_annullata FROM tmp_refs)
 WHERE id = (SELECT contabile_id FROM tmp_contabile_ann);

SELECT throws_like(
  format($q$SELECT * FROM pagamenti.fn_posta_riga_tardiva(%s, %s, %s)$q$,
         (SELECT cr.id FROM pagamenti.vendite_contabili_righe cr WHERE cr.riferimento_ente = 'PGTAP_TARD_S4'
            AND cr.meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti)),
         (SELECT id FROM tmp_fatture WHERE ruolo = 'F'),
         (SELECT billing_account_id FROM tmp_refs)),
  -- ⚠️ Non '%annullata%': dal 2026-09-30 la contiene anche la frase di
  --    E_RIGA_CONTABILE_DISTINTA_ANNULLATA (quinta mossa del guard sulle
  --    righe), e il test resterebbe verde per coincidenza se la tardiva
  --    smettesse di rifiutare per prima. Si lega alla frase propria.
  '%si registra in ritardo solo%',
  '13) Caso 5: una SOSPESA sotto una distinta ANNULLATA non si registra — quel denaro non e'' mai successo'
);

CREATE TEMP TABLE tmp_contabile_val AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_banca_id FROM tmp_refs),
    p_data_contabile        => script.fn_data_operativa() - 2,
    p_data_registrazione    => script.fn_data_operativa(),
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
    p_origine               => 'MANUALE'
  ) AS contabile_id;

INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, importo, stato_id, motivo_sospeso, meta)
SELECT (SELECT contabile_id FROM tmp_contabile_val), 'PGTAP_TARD_S5', script.fn_data_operativa(), 8.00,
       r.st_sospesa, 'sospesa sotto una validata',
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti), 'et', 'S5')
  FROM tmp_refs r;

UPDATE pagamenti.vendite_contabili
   SET stato_id = (SELECT d_validata FROM tmp_refs)
 WHERE id = (SELECT contabile_id FROM tmp_contabile_val);

SELECT throws_like(
  format($q$SELECT * FROM pagamenti.fn_posta_riga_tardiva(%s, %s, %s)$q$,
         (SELECT cr.id FROM pagamenti.vendite_contabili_righe cr WHERE cr.riferimento_ente = 'PGTAP_TARD_S5'
            AND cr.meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti)),
         (SELECT id FROM tmp_fatture WHERE ruolo = 'F'),
         (SELECT billing_account_id FROM tmp_refs)),
  '%usa il giro normale%',
  '14) Caso 6: sotto una VALIDATA la tardiva non serve — «usa il giro normale»'
);

-- ============================================================
-- 15) Caso 7: la rata di un'ALTRA fattura — la coerenza gira
-- ============================================================
SELECT throws_like(
  format($q$SELECT * FROM pagamenti.fn_posta_riga_tardiva(%s, %s, %s, %s)$q$,
         (SELECT id FROM tmp_righe WHERE et = 'S3'),
         (SELECT id FROM tmp_fatture WHERE ruolo = 'F'),
         (SELECT billing_account_id FROM tmp_refs),
         (SELECT id FROM tmp_rate WHERE etichetta = 'RG')),
  '%non appartiene alla fattura%',
  '15) Caso 7: la rata di un''altra fattura e'' rifiutata — il guard della coerenza gira anche qui'
);

-- ============================================================
-- 16-18) La porta della quarta mossa
-- ============================================================
-- Fuori dalla madre nessuna GUC e' impostata: l'UPDATE a mano resta rifiutato.
SELECT throws_like(
  format($q$UPDATE pagamenti.vendite_contabili_righe
             SET stato_id = %s, fattura_id = %s, billing_account_id = %s WHERE id = %s$q$,
         (SELECT st_abbinata FROM tmp_refs),
         (SELECT id FROM tmp_fatture WHERE ruolo = 'F'),
         (SELECT billing_account_id FROM tmp_refs),
         (SELECT id FROM tmp_righe WHERE et = 'S3')),
  '%non si lavorano piu%',
  '16) Caso 8: fuori dalla madre SOSPESA -> ABBINATA sotto la chiusa e'' ancora rifiutato: la quarta mossa regge'
);

-- La GUC nomina la riga A, non S3.
SELECT set_config('app.registrazione_tardiva_riga_id',
                  (SELECT id FROM tmp_righe WHERE et = 'A')::text, true);

SELECT throws_like(
  format($q$UPDATE pagamenti.vendite_contabili_righe
             SET stato_id = %s, fattura_id = %s, billing_account_id = %s WHERE id = %s$q$,
         (SELECT st_abbinata FROM tmp_refs),
         (SELECT id FROM tmp_fatture WHERE ruolo = 'F'),
         (SELECT billing_account_id FROM tmp_refs),
         (SELECT id FROM tmp_righe WHERE et = 'S3')),
  '%non si lavorano piu%',
  '17) Caso 9: la GUC settata su un ALTRO id non apre la porta'
);

SELECT set_config('app.registrazione_tardiva_riga_id', '', true);

-- Dopo il caso 1 (test 3) la madre ha richiuso la porta da sola.
SELECT is(
  COALESCE(NULLIF(current_setting('app.registrazione_tardiva_riga_id', true), ''), ''),
  ''::text,
  '18) Dopo la madre la porta e'' richiusa: la GUC e'' vuota'
);

-- ============================================================
-- 19) Una riga che non esiste
-- ============================================================
SELECT throws_like(
  format($q$SELECT * FROM pagamenti.fn_posta_riga_tardiva(999999999, %s, %s)$q$,
         (SELECT id FROM tmp_fatture WHERE ruolo = 'F'),
         (SELECT billing_account_id FROM tmp_refs)),
  '%non trovata%',
  '19) Una riga che non esiste: E_RIGA_CONTABILE_NON_TROVATA'
);

-- ============================================================
-- Cleanup
-- ============================================================
SELECT set_config('zeroerp.maintenance_allow_delete_logs', 'on', true);

DELETE FROM pagamenti.vendite_movimenti m
 WHERE m.fattura_id IN (SELECT id FROM tmp_fatture);

SELECT set_config('zeroerp.allow_contabile_riga_delete_override', 'on', true);
DELETE FROM pagamenti.vendite_contabili_righe cr
 WHERE cr.contabile_id IN (SELECT contabile_id FROM tmp_contabile
                           UNION ALL SELECT contabile_id FROM tmp_contabile_ann
                           UNION ALL SELECT contabile_id FROM tmp_contabile_val);

DELETE FROM pagamenti.vendite_contabili
 WHERE id IN (SELECT contabile_id FROM tmp_contabile
              UNION ALL SELECT contabile_id FROM tmp_contabile_ann
              UNION ALL SELECT contabile_id FROM tmp_contabile_val);

DELETE FROM vendite.fatture_scadenze
 WHERE id IN (SELECT id FROM tmp_rate);

DELETE FROM vendite.fatture_log
 WHERE fattura_id IN (SELECT id FROM tmp_fatture);

UPDATE vendite.fatture
   SET storicizza = false
 WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti);

DELETE FROM vendite.fatture
 WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti);

SELECT ok(true, '20) Cleanup completato');

SELECT * FROM finish();

ROLLBACK;
