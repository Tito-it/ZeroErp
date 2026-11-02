-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: l'abbinamento alla RATA — coerenza, capienza, forzatura, saldo
--
-- Elenco test (plan 18):
--  1) Riferimenti costruiti (azienda, operatore, cliente) e a catalogo
--  2) COERENZA: una rata di un'altra fattura e' rifiutata
--  3) Una rata SENZA fattura non parla qui: risponde il guard sui dati
--  4) Una riga che ci sta entra senza dire niente
--  5) CAPIENZA: quello che non ci sta e' rifiutato, coi numeri
--  6) ...ma con la conferma entra (D14-d)
--  7) ...e sulla riga resta scritto che e' stata forzata
--  8) fn_get_saldo_rata separa il registrato dal dichiarato
--  9) Il posting registra, e il mirror copia la rata sul movimento
-- 10) Il mirror rifiuta un movimento che nomina un'altra rata
-- 11) Dopo il posting il saldo della rata e' negativo: e' sovra-incassata
-- 12) `incassato` conta solo la CASSA, non i centri interni
-- 13) La vista mostra la rata sovra-incassata, e dice perche'
-- 14) ...e mostra anche il verso contrario, che il nome del piano ometteva
-- 15) Una riga SOSPESA non occupa spazio sulla rata
-- 16) ⭐ Portare a SCARTATA una riga sospesa NON e' rifiutato
-- 17) La rata resta invisibile a chi non deve vederla (fail-closed)
-- 18) Assert finale cleanup
--
-- Scopo:
--  - collaudare la slice 2 per intero: l'incasso arriva alla RATA, e il
--    database distingue le due domande che sembrano una sola — la COERENZA
--    («questa rata e' di questa fattura?»), che rifiuta, e la CAPIENZA («c'e'
--    ancora spazio?»), che segnala e accetta se qualcuno conferma;
--  - presidiare il caso che si sbaglia facile (test 16): se la capienza si
--    verificasse a ogni cambio di stato, TOGLIERE di mezzo una riga sospesa
--    verrebbe rifiutato perche' un'altra riga ha nel frattempo occupato lo
--    spazio — si rifiuterebbe un gesto che libera;
--  - presidiare che «incassato» non sia «registrato» (test 12): i centri
--    interni saldano il documento ma in banca non entra niente;
--  - ⭐ i test 5-6 sono ANCHE il contratto di D16 (2026-09-14, brief
--    riga-manuale-nasce-abbinata §4 P-0): la riga manuale nasce con
--    INSERT diretto in ABBINATA, e il doppio tempo della capienza — rifiuto
--    coi numeri, poi `forzata = true` — vale sull'INSERT come sull'UPDATE.
--    E' il contratto su cui il backend fa nascere la riga gia' abbinata.
--
-- Piano: brief-db-posting-e-abbinamento-rata.md
--        §2.2 S2-1…S2-8 · Decisioni: brief madre D14-b/c/d/e · lotto 5
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (rev 2026-09-17 sera). Fino a quel
--   giorno il file pescava «l'ultimo billing account per data_insert» e ne
--   deduceva l'emittente: su un database ricostruito dai changelog (zeroerp_ci,
--   la CI) le anagrafiche sono a ZERO, tmp_refs usciva vuota e il file moriva
--   nel fixture — ERRORE_FIXTURE in baseline-rossi-ci.tsv, 18 asserzioni
--   collaudate solo su dbdev. E la stessa fixture, ricopiata, ha fatto nascere
--   rossi tre test nuovi (brief-db-distinta-ricerca-rate §4-bis.9). Ora:
--   un'azienda col suo operatore (dbops.fn_pgtap_crea_emittente_operatore)
--   PRIMA del contesto, un cliente fatturabile (dbops.fn_pgtap_crea_cliente_ba)
--   NEL contesto — guida pgtap-come-si-scrive-un-test §«Il mondo si
--   costruisce, non si cerca». Con un emittente nuovo la chiave di riuso di
--   fn_get_or_create_vendite_contabile (che dal 2026-09-15 comprende
--   l'emittente) non puo' agganciare una distinta preesistente della macchina.
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

SELECT plan(18);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_abbinamento_rata'::text AS test_scope;

-- Il cliente fatturabile, nel contesto dell'operatore: il legame BA -> emittente
-- lo scrive il trigger z90 verso l'emittente di chi agisce.
CREATE TEMP TABLE tmp_cli AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('abbinamento rata') c;

CREATE TEMP TABLE tmp_refs AS
SELECT script.fn_pgtap_registro_fattura(m.soggetto_ruolo_id)                       AS registro_id,
       (SELECT billing_account_id FROM tmp_cli)                                      AS billing_account_id,
       (SELECT utility_id FROM tmp_cli)                                              AS utility_id,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1)                           AS valuta_id,
       m.soggetto_ruolo_id                                                          AS emittente_soggetto_ruolo_id,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA' ORDER BY c.id LIMIT 1) AS centro_banca_id,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.is_fondo_fattura IS TRUE ORDER BY c.id LIMIT 1) AS centro_fondo_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'ABBINATA' ORDER BY s.id LIMIT 1)                  AS stato_abbinata_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'SOSPESA' ORDER BY s.id LIMIT 1)                   AS stato_sospesa_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'SCARTATA' ORDER BY s.id LIMIT 1)                  AS stato_scartata_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'VALIDATA' ORDER BY s.id LIMIT 1)                  AS stato_validata_id
  FROM _mondo m;

SELECT ok(
  (SELECT registro_id IS NOT NULL AND billing_account_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL AND centro_banca_id IS NOT NULL
      AND centro_fondo_id IS NOT NULL AND stato_abbinata_id IS NOT NULL
      AND stato_sospesa_id IS NOT NULL AND stato_scartata_id IS NOT NULL
      AND stato_validata_id IS NOT NULL
     FROM tmp_refs),
  '1) Riferimenti costruiti (azienda, operatore, cliente, registro) e a catalogo (centri, stati)'
);

-- Due fatture: la nostra (F) e un'altra (G), che serve a provare la coerenza.
CREATE TEMP TABLE tmp_fatture AS
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, totale_a_pagare, meta)
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id, r.billing_account_id,
         r.tipo_doc_fiscale_id, r.valuta_id, r.utility_id, v.totale,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti),
                            'ruolo', v.ruolo)
    FROM tmp_refs r, (VALUES ('F', 350.00), ('G', 100.00)) AS v(ruolo, totale)
  RETURNING id, meta ->> 'ruolo' AS ruolo
)
SELECT * FROM ins;

-- Tre rate sulla nostra fattura, una sull'altra.
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

-- La distinta di lavoro, manuale come il lotto di un operatore.
CREATE TEMP TABLE tmp_contabile AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_banca_id FROM tmp_refs),
    p_data_contabile        => script.fn_data_operativa(),
    p_data_registrazione    => script.fn_data_operativa(),
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
    p_origine               => 'MANUALE'
  ) AS contabile_id;

-- ============================================================
-- 2) COERENZA — si rifiuta, ed e' un'incoerenza logica
-- ============================================================
-- ⚠️ `throws_like` e non `throws_ok`: P0001 direbbe solo «errore di dominio».
--   Qui il discriminante e' la frase, perche' il punto e' PROPRIO quale delle
--   due domande ha risposto.
SELECT throws_like(
  format($q$INSERT INTO pagamenti.vendite_contabili_righe
             (contabile_id, importo, fattura_id, billing_account_id, scadenza_id, stato_id)
           VALUES (%s, 10.00, %s, %s, %s, %s)$q$,
         (SELECT contabile_id FROM tmp_contabile),
         (SELECT id FROM tmp_fatture WHERE ruolo = 'F'),
         (SELECT billing_account_id FROM tmp_refs),
         (SELECT id FROM tmp_rate WHERE etichetta = 'RG'),
         (SELECT stato_abbinata_id FROM tmp_refs)),
  '%non appartiene alla fattura%',
  '2) Una rata di un''altra fattura e'' rifiutata'
);

-- ============================================================
-- 3) Una rata senza fattura: a parlare e' il guard sui DATI
-- ============================================================
-- ⭐ Il guard della rata tace apposta. Girando PRIMA (i BEFORE ROW vanno in
--   ordine alfabetico) coprirebbe il messaggio utile — «serve la fattura» —
--   con uno vero e inutile: «la rata non e' di quella fattura».
SELECT throws_like(
  format($q$INSERT INTO pagamenti.vendite_contabili_righe
             (contabile_id, importo, scadenza_id, stato_id)
           VALUES (%s, 10.00, %s, %s)$q$,
         (SELECT contabile_id FROM tmp_contabile),
         (SELECT id FROM tmp_rate WHERE etichetta = 'R1'),
         (SELECT stato_abbinata_id FROM tmp_refs)),
  '%serv%',
  '3) Una rata senza fattura non parla qui: risponde il guard sui dati'
);

-- ============================================================
-- 4-7) Capienza e forzatura
-- ============================================================
INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, importo, fattura_id,
     billing_account_id, scadenza_id, stato_id, meta)
SELECT (SELECT contabile_id FROM tmp_contabile), 'PGTAP_R1_PIENA', script.fn_data_operativa(), 100.00,
       (SELECT id FROM tmp_fatture WHERE ruolo = 'F'), r.billing_account_id,
       (SELECT id FROM tmp_rate WHERE etichetta = 'R1'), r.stato_abbinata_id,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r;

SELECT is(
  (SELECT COUNT(*)::int FROM pagamenti.vendite_contabili_righe
    WHERE riferimento_ente = 'PGTAP_R1_PIENA'),
  1,
  '4) Una riga che ci sta entra senza dire niente'
);

-- La rata da 100 e' gia' impegnata per intero: questi 50 non ci rientrano.
SELECT throws_like(
  format($q$INSERT INTO pagamenti.vendite_contabili_righe
             (contabile_id, importo, fattura_id, billing_account_id, scadenza_id, stato_id)
           VALUES (%s, 50.00, %s, %s, %s, %s)$q$,
         (SELECT contabile_id FROM tmp_contabile),
         (SELECT id FROM tmp_fatture WHERE ruolo = 'F'),
         (SELECT billing_account_id FROM tmp_refs),
         (SELECT id FROM tmp_rate WHERE etichetta = 'R1'),
         (SELECT stato_abbinata_id FROM tmp_refs)),
  -- ⭐ Dal 2026-09-18 il pattern guarda i NUMERI, a due decimali: v_residuo e'
  --   fatture_scadenze.importo%TYPE = numeric(18,6), e con ::text la frase
  --   diceva «restano 0.000000» accanto a «50.00» (20260918-04). Un pattern
  --   che non guarda i numeri e' verde con qualunque scala.
  '%restano 0.00 da regolare: un importo di 50.00 non ci rientra%',
  '5) Quello che non ci sta e'' rifiutato, coi numeri — a due decimali'
);

-- ⭐ Ma il cliente ha pagato due volte, e questo e' un fatto del mondo.
INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, importo, fattura_id,
     billing_account_id, scadenza_id, stato_id, forzata, motivo_forzatura, meta)
SELECT (SELECT contabile_id FROM tmp_contabile), 'PGTAP_R1_FORZATA', script.fn_data_operativa(), 50.00,
       (SELECT id FROM tmp_fatture WHERE ruolo = 'F'), r.billing_account_id,
       (SELECT id FROM tmp_rate WHERE etichetta = 'R1'), r.stato_abbinata_id,
       true, 'Il cliente ha pagato due volte lo stesso avviso',
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r;

SELECT is(
  (SELECT COUNT(*)::int FROM pagamenti.vendite_contabili_righe
    WHERE riferimento_ente = 'PGTAP_R1_FORZATA'),
  1,
  '6) ...ma con la conferma entra'
);

SELECT ok(
  (SELECT cr.forzata IS TRUE AND btrim(COALESCE(cr.motivo_forzatura, '')) <> ''
     FROM pagamenti.vendite_contabili_righe cr
    WHERE cr.riferimento_ente = 'PGTAP_R1_FORZATA'),
  '7) ...e sulla riga resta scritto che e'' stata forzata, col suo perche'''
);

-- ============================================================
-- 8) Il saldo separa il REGISTRATO dal DICHIARATO
-- ============================================================
CREATE TEMP TABLE tmp_saldo_prima AS
SELECT * FROM pagamenti.fn_get_saldo_rata((SELECT id FROM tmp_rate WHERE etichetta = 'R1'));

SELECT ok(
  (SELECT saldo = 100.00 AND in_lavorazione = 150.00 AND has_movimenti IS FALSE
     FROM tmp_saldo_prima),
  '8) Niente registrato (saldo 100) e 150 dichiarati: sono due numeri diversi'
);

-- ============================================================
-- 9-10) Il posting, e il mirror che copia la rata
-- ============================================================
UPDATE pagamenti.vendite_contabili c
   SET stato_id = (SELECT stato_validata_id FROM tmp_refs)
 WHERE c.id = (SELECT contabile_id FROM tmp_contabile);

CREATE TEMP TABLE tmp_esito AS
SELECT * FROM pagamenti.fn_posta_contabile((SELECT contabile_id FROM tmp_contabile));

SELECT is(
  (SELECT COUNT(*)::int
     FROM pagamenti.vendite_movimenti m
    WHERE m.scadenza_id = (SELECT id FROM tmp_rate WHERE etichetta = 'R1')),
  2,
  '9) Il posting registra, e il mirror copia la rata sul movimento'
);

-- ⚠️ Un movimento che nomina una rata diversa da quella della sua riga
--   racconterebbe un'altra storia.
SELECT throws_ok(
  format($q$INSERT INTO pagamenti.vendite_movimenti
             (contabile_riga_id, data_effettiva, data_registrazione, importo, scadenza_id)
           SELECT cr.id, script.fn_data_operativa(), script.fn_data_operativa(), 1.00, %s
             FROM pagamenti.vendite_contabili_righe cr
            WHERE cr.riferimento_ente = 'PGTAP_R1_PIENA'$q$,
         (SELECT id FROM tmp_rate WHERE etichetta = 'R2')),
  'P0001',
  NULL,
  '10) Il mirror rifiuta un movimento che nomina un''altra rata'
);

SELECT ok(
  (SELECT saldo = -50.00 FROM pagamenti.fn_get_saldo_rata(
      (SELECT id FROM tmp_rate WHERE etichetta = 'R1'))),
  '11) Dopo il posting il saldo della rata e'' negativo: e'' sovra-incassata'
);

-- ============================================================
-- 12) `incassato` non e' «registrato»
-- ============================================================
-- Una distinta sul centro interno dei fondi: salda il documento, ma in banca
-- non e' entrato niente.
CREATE TEMP TABLE tmp_contabile_fondo AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_fondo_id FROM tmp_refs),
    p_data_contabile        => script.fn_data_operativa() - 1,
    p_data_registrazione    => script.fn_data_operativa(),
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
    p_origine               => 'MANUALE'
  ) AS contabile_id;

INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, importo, fattura_id,
     billing_account_id, scadenza_id, stato_id, meta)
SELECT (SELECT contabile_id FROM tmp_contabile_fondo), 'PGTAP_R3_FONDO', script.fn_data_operativa(), 50.00,
       (SELECT id FROM tmp_fatture WHERE ruolo = 'F'), r.billing_account_id,
       (SELECT id FROM tmp_rate WHERE etichetta = 'R3'), r.stato_abbinata_id,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r;

UPDATE pagamenti.vendite_contabili c
   SET stato_id = (SELECT stato_validata_id FROM tmp_refs)
 WHERE c.id = (SELECT contabile_id FROM tmp_contabile_fondo);

SELECT pagamenti.fn_posta_contabile((SELECT contabile_id FROM tmp_contabile_fondo));

SELECT ok(
  (SELECT saldo = 0.00 AND incassato = 0.00 AND has_movimenti IS TRUE
     FROM pagamenti.fn_get_saldo_rata((SELECT id FROM tmp_rate WHERE etichetta = 'R3'))),
  '12) La rata e'' saldata ma NON incassata: il centro dei fondi non e'' cassa'
);

-- ============================================================
-- 13-14) L'elenco, e i suoi due motivi
-- ============================================================
SELECT is(
  (SELECT v.motivo FROM pagamenti.vw_rate_fuori_capienza v
    WHERE v.scadenza_id = (SELECT id FROM tmp_rate WHERE etichetta = 'R1')),
  'SOVRA_INCASSATA'::text,
  '13) La vista mostra la rata sovra-incassata, e dice perche'''
);

-- Un rimborso dove non era entrato niente: il residuo SUPERA l'importo.
CREATE TEMP TABLE tmp_contabile_contraria AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_banca_id FROM tmp_refs),
    p_data_contabile        => script.fn_data_operativa() - 2,
    p_data_registrazione    => script.fn_data_operativa(),
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
    p_origine               => 'MANUALE'
  ) AS contabile_id;

INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, importo, fattura_id,
     billing_account_id, scadenza_id, stato_id, forzata, motivo_forzatura, meta)
SELECT (SELECT contabile_id FROM tmp_contabile_contraria), 'PGTAP_R2_CONTRARIA', script.fn_data_operativa(), -30.00,
       (SELECT id FROM tmp_fatture WHERE ruolo = 'F'), r.billing_account_id,
       (SELECT id FROM tmp_rate WHERE etichetta = 'R2'), r.stato_abbinata_id,
       true, 'Rimborso calcolato su un dato vecchio',
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r;

UPDATE pagamenti.vendite_contabili c
   SET stato_id = (SELECT stato_validata_id FROM tmp_refs)
 WHERE c.id = (SELECT contabile_id FROM tmp_contabile_contraria);

SELECT pagamenti.fn_posta_contabile((SELECT contabile_id FROM tmp_contabile_contraria));

SELECT is(
  (SELECT v.motivo FROM pagamenti.vw_rate_fuori_capienza v
    WHERE v.scadenza_id = (SELECT id FROM tmp_rate WHERE etichetta = 'R2')),
  'MOVIMENTO_CONTRARIO'::text,
  '14) ...e mostra il verso contrario, che il nome del piano ometteva'
);

-- ============================================================
-- 15-16) Le righe sospese: non occupano, e si possono togliere
-- ============================================================
CREATE TEMP TABLE tmp_contabile_sospesa AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_banca_id FROM tmp_refs),
    p_data_contabile        => script.fn_data_operativa() - 3,
    p_data_registrazione    => script.fn_data_operativa(),
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
    p_origine               => 'MANUALE'
  ) AS contabile_id;

INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, importo, fattura_id,
     billing_account_id, scadenza_id, stato_id, motivo_sospeso, meta)
SELECT (SELECT contabile_id FROM tmp_contabile_sospesa), 'PGTAP_R3_SOSPESA', script.fn_data_operativa(), 999.00,
       (SELECT id FROM tmp_fatture WHERE ruolo = 'F'), r.billing_account_id,
       (SELECT id FROM tmp_rate WHERE etichetta = 'R3'), r.stato_sospesa_id,
       'in attesa di capire di chi e''',
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r;

SELECT is(
  (SELECT in_lavorazione FROM pagamenti.fn_get_saldo_rata(
      (SELECT id FROM tmp_rate WHERE etichetta = 'R3'))),
  0.00::numeric,
  '15) Una riga sospesa non occupa spazio sulla rata, per quanto grande sia'
);

-- ⭐ Il caso che si sbaglia facile: togliere di mezzo una riga sospesa e' un
--   gesto che LIBERA, e non deve incontrare il guard della capienza.
SELECT lives_ok(
  format($q$UPDATE pagamenti.vendite_contabili_righe SET stato_id = %s
             WHERE riferimento_ente = 'PGTAP_R3_SOSPESA'$q$,
         (SELECT stato_scartata_id FROM tmp_refs)),
  '16) Portare a SCARTATA una riga sospesa non e'' rifiutato'
);

-- ============================================================
-- 17) La coerenza si chiede fuori dalla RLS, ma non regala niente
-- ============================================================
-- ⚠️ La funzione risponde su una coppia gia' nominata dal chiamante: su una
--   coppia che non esiste risponde FALSO, non «non lo so».
SELECT ok(
  (SELECT script.fn_check_scadenza_di_fattura(
            (SELECT id FROM tmp_rate WHERE etichetta = 'RG'),
            (SELECT id FROM tmp_fatture WHERE ruolo = 'F')) IS FALSE
      AND script.fn_check_scadenza_di_fattura(
            (SELECT id FROM tmp_rate WHERE etichetta = 'R1'),
            (SELECT id FROM tmp_fatture WHERE ruolo = 'F')) IS TRUE),
  '17) La domanda di coerenza risponde sul fatto, in entrambi i versi'
);

-- ============================================================
-- Cleanup
-- ============================================================
SELECT set_config('zeroerp.maintenance_allow_delete_logs', 'on', true);

DELETE FROM pagamenti.vendite_movimenti m
 WHERE m.fattura_id IN (SELECT id FROM tmp_fatture);

-- ⚠️ Dal 2026-09-14 (D17) il DELETE di una riga contabile passa dal guard del
--    contenuto della distinta: sotto una CHIUSA o una GENERATA e' rifiutato.
--    Questo cleanup e' un passaggio tecnico e lo dichiara con la stessa GUC
--    che usa la madre del giro dei fondi (fn_cancella_fondo_fattura); il
--    ROLLBACK farebbe comunque il lavoro.
SELECT set_config('zeroerp.allow_contabile_riga_delete_override', 'on', true);
DELETE FROM pagamenti.vendite_contabili_righe cr
 WHERE cr.contabile_id IN (SELECT contabile_id FROM tmp_contabile
                           UNION ALL SELECT contabile_id FROM tmp_contabile_fondo
                           UNION ALL SELECT contabile_id FROM tmp_contabile_contraria
                           UNION ALL SELECT contabile_id FROM tmp_contabile_sospesa);

DELETE FROM pagamenti.vendite_contabili c
 WHERE c.id IN (SELECT contabile_id FROM tmp_contabile
                UNION ALL SELECT contabile_id FROM tmp_contabile_fondo
                UNION ALL SELECT contabile_id FROM tmp_contabile_contraria
                UNION ALL SELECT contabile_id FROM tmp_contabile_sospesa);

DELETE FROM vendite.fatture_log fl
 WHERE fl.fattura_id IN (SELECT id FROM tmp_fatture);

DELETE FROM vendite.fatture_scadenze s
 WHERE s.fattura_id IN (SELECT id FROM tmp_fatture);

UPDATE vendite.fatture
   SET storicizza = false
 WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti);

DELETE FROM vendite.fatture
 WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti);

SELECT ok(true, '18) Cleanup completato');

SELECT * FROM finish();

ROLLBACK;
