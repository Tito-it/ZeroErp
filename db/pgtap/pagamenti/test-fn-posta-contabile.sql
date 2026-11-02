-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la MADRE DEL POSTING — pagamenti.fn_posta_contabile
--
-- Elenco test (plan 20):
--  1) Riferimenti costruiti (azienda, operatore, cliente) e a catalogo
--  2) La distinta nasce in BOZZA con le sue tre righe
--  3) Una distinta non VALIDATA non si registra
--  4) Una dichiarazione che non corrisponde viene RIFIUTATA
--  5) ...e non ha registrato NIENTE: zero movimenti
--  6) Il posting crea un movimento per ogni riga pronta
--  7) ...e porta quelle righe a POSTATA
--  8) Le righe non pronte restano indietro, e la funzione lo dice
--  9) Il totale registrato e' quello delle righe pronte
-- 10) L'esito e' dichiarato, non dedotto
-- 11) QUADRATURA: somma movimenti = somma righe registrate
-- 12) La riga SOSPESA non ha generato nessun movimento
-- 13) ⭐ Dopo il posting il saldo della fattura CAMBIA
-- 14) La distinta e' CHIUSA: la chiusura e' una conseguenza
-- 15) La conferma e' scritta sul documento (data_conferma / user_conferma)
-- 16) Registrare una seconda volta e' rifiutato, e lo dice
-- 17) ⭐ QUARTA MOSSA: sotto una distinta chiusa una riga non diventa pronta
-- 18) «Niente da registrare» NON e' un errore: e' un esito
-- 19) Una distinta che non esiste e' rifiutata
-- 20) Assert finale cleanup
--
-- Scopo:
--  - collaudare il changeSet in cui NASCE IL PRIMO MOVIMENTO del progetto:
--    fino a qui `pagamenti.fn_get_saldo_fattura` rispondeva «residuo = totale»
--    per costruzione, perche' nessuna funzione scriveva vendite_movimenti. Il
--    test 13 e' la prova che la slice serve;
--  - presidiare le tre decisioni prese scrivendo la madre: la chiusura come
--    CONSEGUENZA del registrare (test 14), la dichiarazione di chi conferma
--    che rifiuta PRIMA di scrivere (test 4 e 5), e «niente da postare» come
--    esito e non come errore (test 18);
--  - presidiare la quarta mossa del guard sulla distinta finale (test 17), che
--    e' il prezzo della chiusura automatica.
--
-- Piano: brief-db-posting-e-abbinamento-rata.md
--        §2.1 S1-10, §2.4 casi 1, 2, 3, 5, 13 · lotto 4
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (rev 2026-09-17 sera). Fino a quel
--   giorno il file pescava «l'ultimo billing account per data_insert» e ne
--   deduceva l'emittente: su un database ricostruito dai changelog (zeroerp_ci,
--   la CI) le anagrafiche sono a ZERO, tmp_refs usciva vuota e il file moriva
--   nel fixture — ERRORE_FIXTURE in baseline-rossi-ci.tsv, e il PRIMO
--   MOVIMENTO del progetto era collaudato solo su dbdev. Ora: un'azienda col
--   suo operatore (dbops.fn_pgtap_crea_emittente_operatore) PRIMA del
--   contesto, un cliente fatturabile (dbops.fn_pgtap_crea_cliente_ba) NEL
--   contesto — guida pgtap-come-si-scrive-un-test §«Il mondo si costruisce,
--   non si cerca». Con un emittente nuovo la chiave di riuso di
--   fn_get_or_create_vendite_contabile (che dal 2026-09-15 comprende
--   l'emittente) non puo' agganciare una distinta preesistente della macchina.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore.
CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione (OPERATORE +
--   RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI: senza, non verrebbero mai esercitati (si chiude in
--   ROLLBACK) e il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(20);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_posta_contabile'::text AS test_scope;

-- Il cliente fatturabile, nel contesto dell'operatore: il legame BA -> emittente
-- lo scrive il trigger z90 verso l'emittente di chi agisce.
CREATE TEMP TABLE tmp_cli AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('posta contabile') c;

-- ⚠️ Il centro NON si fabbrica: dal 2026-08-21 i cinque centri sono seminati e
--   i due ruoli interni sono unici per vincolo. Un test che se li crea da solo
--   non verifica il seed: lo nasconde.
-- ⭐ E si prende BANCA, non FONDI_FATTURA: qui si registra denaro ARRIVATO.
CREATE TEMP TABLE tmp_refs AS
SELECT script.fn_pgtap_registro_fattura(m.soggetto_ruolo_id)                       AS registro_id,
       (SELECT billing_account_id FROM tmp_cli)                                      AS billing_account_id,
       (SELECT utility_id FROM tmp_cli)                                              AS utility_id,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1)                           AS valuta_id,
       m.soggetto_ruolo_id                                                          AS emittente_soggetto_ruolo_id,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA'
         ORDER BY c.id LIMIT 1)                                                     AS centro_banca_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'ABBINATA' ORDER BY s.id LIMIT 1)                 AS stato_abbinata_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'SOSPESA' ORDER BY s.id LIMIT 1)                  AS stato_sospesa_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'DA_ABBINARE' ORDER BY s.id LIMIT 1)              AS stato_da_abbinare_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'VALIDATA' ORDER BY s.id LIMIT 1)                 AS stato_validata_id
  FROM _mondo m;

SELECT ok(
  (SELECT registro_id IS NOT NULL
      AND billing_account_id IS NOT NULL
      AND tipo_doc_fiscale_id IS NOT NULL
      AND valuta_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL
      AND centro_banca_id IS NOT NULL
      AND stato_abbinata_id IS NOT NULL
      AND stato_sospesa_id IS NOT NULL
      AND stato_da_abbinare_id IS NOT NULL
      AND stato_validata_id IS NOT NULL
     FROM tmp_refs),
  '1) Riferimenti costruiti (azienda, operatore, cliente, registro) e a catalogo (centro BANCA, stati)'
);

-- La fattura da incassare: 300, di cui se ne registrano 150.
CREATE TEMP TABLE tmp_fattura AS
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, totale_a_pagare, meta)
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id, r.billing_account_id,
         r.tipo_doc_fiscale_id, r.valuta_id, r.utility_id, 300.00,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_refs r
  RETURNING id
)
SELECT * FROM ins;

-- La distinta: manuale, come il lotto di lavoro di un operatore.
CREATE TEMP TABLE tmp_contabile AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_banca_id FROM tmp_refs),
    p_data_contabile        => script.fn_data_operativa(),
    p_data_registrazione    => script.fn_data_operativa(),
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
    p_origine               => 'MANUALE'
  ) AS contabile_id;

-- Quattro righe: due pronte (100 + 50) e due sospese (30 + 20).
-- ⚠️ La riga D porta comunque fattura e cliente: serve al test 17, dove
--   l'unico guard che deve poter rifiutare e' quello sulla distinta finale.
--   Senza, rifiuterebbe prima il guard sull'abbinamento e il test direbbe
--   verde per la ragione sbagliata.
-- ⭐ Rev 2026-09-18 (D20-a): D era DA_ABBINARE ed e' SOSPESA. Da quel giorno
--   una distinta con righe non lavorate non entra in VALIDATA — e' la regola
--   che entra, non una regressione — e la quarta mossa (test 17) si prova
--   dalla sospesa, che e' l'unico stato che puo' davvero restare indietro.
INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, data_valuta, importo,
     fattura_id, billing_account_id, stato_id, motivo_sospeso, meta)
SELECT (SELECT contabile_id FROM tmp_contabile), v.rif, script.fn_data_operativa(), script.fn_data_operativa(), v.importo,
       (SELECT id FROM tmp_fattura), r.billing_account_id, v.stato_id,
       CASE WHEN v.stato_id = r.stato_sospesa_id THEN 'da capire' END,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r,
       (VALUES ('PGTAP_A', 100.00, 'ABBINATA'),
               ('PGTAP_B',  50.00, 'ABBINATA'),
               ('PGTAP_C',  30.00, 'SOSPESA'),
               ('PGTAP_D',  20.00, 'SOSPESA')) AS raw(rif, importo, stato)
       CROSS JOIN LATERAL (
         SELECT raw.rif, raw.importo,
                CASE raw.stato
                  WHEN 'ABBINATA'    THEN r.stato_abbinata_id
                  ELSE                    r.stato_sospesa_id
                END AS stato_id) v;

SELECT is(
  (SELECT COUNT(*)::int FROM pagamenti.vendite_contabili_righe cr
    WHERE cr.contabile_id = (SELECT contabile_id FROM tmp_contabile)),
  4,
  '2) La distinta nasce in BOZZA con le sue quattro righe'
);

-- ============================================================
-- 3) Da BOZZA non si registra
-- ============================================================
-- ⚠️ Lo SQLSTATE si dichiara: senza, throws_ok accetterebbe qualunque errore,
--   compreso il crash del guard. P0001 = errore di dominio.
SELECT throws_ok(
  format('SELECT * FROM pagamenti.fn_posta_contabile(%s)',
         (SELECT contabile_id FROM tmp_contabile)),
  'P0001',
  NULL,
  '3) Una distinta non VALIDATA non si registra'
);

-- L'operatore dichiara di aver finito di inserire.
UPDATE pagamenti.vendite_contabili c
   SET importo_dichiarato = 200.00,
       stato_id = (SELECT stato_validata_id FROM tmp_refs)
 WHERE c.id = (SELECT contabile_id FROM tmp_contabile);

-- ============================================================
-- 4) La dichiarazione di chi conferma (D13)
-- ============================================================
-- Chi conferma dice di aver visto 3 righe pronte per 200: ce ne sono 2 per 150.
SELECT throws_ok(
  format('SELECT * FROM pagamenti.fn_posta_contabile(%s, 3, 200.00)',
         (SELECT contabile_id FROM tmp_contabile)),
  'P0001',
  NULL,
  '4) Una dichiarazione che non corrisponde viene rifiutata'
);

-- ⭐ E il punto non e' che rifiuta: e' che rifiuta PRIMA di scrivere. La
--   registrazione non si torna indietro, e un avviso dopo non ripara niente.
SELECT is(
  (SELECT COUNT(*)::int FROM pagamenti.vendite_movimenti m
    WHERE m.fattura_id = (SELECT id FROM tmp_fattura)),
  0,
  '5) ...e non ha registrato niente: zero movimenti'
);

-- Il saldo PRIMA, per il test 13: si legge una volta sola e si tiene.
CREATE TEMP TABLE tmp_saldo_prima AS
SELECT sf.saldo FROM pagamenti.fn_get_saldo_fattura((SELECT id FROM tmp_fattura)) sf;

-- ============================================================
-- Il posting — il verbo in un'istruzione SEPARATA dalle asserzioni
-- ============================================================
-- ⚠️ La snapshot di statement legge PRIMA delle scritture: un'asserzione nella
--   stessa istruzione accuserebbe la funzione invece del test.
CREATE TEMP TABLE tmp_esito AS
SELECT * FROM pagamenti.fn_posta_contabile(
    (SELECT contabile_id FROM tmp_contabile), 2, 150.00);

SELECT is((SELECT movimenti_creati FROM tmp_esito), 2,
  '6) Il posting crea un movimento per ogni riga pronta');

SELECT is((SELECT righe_postate FROM tmp_esito), 2,
  '7) ...e porta quelle righe a POSTATA');

SELECT is((SELECT righe_saltate FROM tmp_esito), 2,
  '8) Le righe non pronte restano indietro, e la funzione lo dice');

SELECT is((SELECT totale_postato FROM tmp_esito), 150.00::numeric,
  '9) Il totale registrato e'' quello delle righe pronte');

SELECT is((SELECT esito FROM tmp_esito), 'POSTATA'::text,
  '10) L''esito e'' dichiarato, non dedotto');

-- ============================================================
-- 11) La quadratura: si asserisce il FATTO, non i singoli valori
-- ============================================================
SELECT is(
  (SELECT COALESCE(SUM(m.importo), 0)
     FROM pagamenti.vendite_movimenti m
    WHERE m.contabile_id = (SELECT contabile_id FROM tmp_contabile)),
  (SELECT COALESCE(SUM(cr.importo), 0)
     FROM pagamenti.vendite_contabili_righe cr
     JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
    WHERE cr.contabile_id = (SELECT contabile_id FROM tmp_contabile)
      AND st.codice_interno = 'POSTATA'),
  '11) Somma dei movimenti = somma delle righe registrate'
);

SELECT is(
  (SELECT COUNT(*)::int
     FROM pagamenti.vendite_movimenti m
     JOIN pagamenti.vendite_contabili_righe cr ON cr.id = m.contabile_riga_id
    WHERE cr.riferimento_ente = 'PGTAP_C'),
  0,
  '12) La riga SOSPESA non ha generato nessun movimento'
);

-- ============================================================
-- 13) ⭐ La prova che questa slice serve
-- ============================================================
-- Fino a qui nessuna funzione del database scriveva vendite_movimenti, quindi
-- il residuo coincideva col totale PER COSTRUZIONE. Adesso no.
SELECT is(
  (SELECT sf.saldo FROM pagamenti.fn_get_saldo_fattura((SELECT id FROM tmp_fattura)) sf),
  (SELECT saldo - 150.00 FROM tmp_saldo_prima),
  '13) Dopo il posting il saldo della fattura cambia, e cala di quanto e'' stato registrato'
);

-- ============================================================
-- 14-15) La chiusura e la conferma
-- ============================================================
SELECT is(
  (SELECT s.codice_interno
     FROM pagamenti.vendite_contabili c
     JOIN pagamenti.vendite_contabili_stati s ON s.id = c.stato_id
    WHERE c.id = (SELECT contabile_id FROM tmp_contabile)),
  'CHIUSA'::text,
  '14) La distinta e'' chiusa: la chiusura e'' una conseguenza del registrare'
);

SELECT ok(
  (SELECT c.data_conferma IS NOT NULL AND c.user_conferma IS NOT NULL
     FROM pagamenti.vendite_contabili c
    WHERE c.id = (SELECT contabile_id FROM tmp_contabile)),
  '15) La conferma e'' scritta sul documento, non solo avvenuta'
);

-- ============================================================
-- 16) Registrare due volte
-- ============================================================
-- ⭐ Non serve nessun meccanismo anti-replay: la distinta e' chiusa, e da li'
--   non si registra. Il doppio movimento resta impossibile anche per l'indice
--   unico su contabile_riga_id.
SELECT throws_ok(
  format('SELECT * FROM pagamenti.fn_posta_contabile(%s)',
         (SELECT contabile_id FROM tmp_contabile)),
  'P0001',
  NULL,
  '16) Registrare una seconda volta e'' rifiutato, e lo dice'
);

-- ============================================================
-- 17) ⭐ La quarta mossa del guard sulla distinta finale
-- ============================================================
-- E' il prezzo della chiusura automatica: sotto una distinta chiusa una riga
-- rimasta indietro non deve poter diventare PRONTA, o sarebbe denaro
-- dichiarato che non si registrera' mai.
-- ⚠️ `throws_like` e non `throws_ok`: qui il discriminante e' la frase — P0001
--   direbbe solo «errore di dominio», non QUALE.
-- ⭐ Dal 2026-09-18 la porta esiste, ma la apre solo pagamenti.fn_posta_riga_tardiva
--   (D20-b): un UPDATE a mano resta rifiutato. La tardiva e' collaudata in
--   test-posta-riga-tardiva-v1.
SELECT throws_like(
  format('UPDATE pagamenti.vendite_contabili_righe SET stato_id = %s WHERE riferimento_ente = ''PGTAP_D''',
         (SELECT stato_abbinata_id FROM tmp_refs)),
  '%non si lavorano piu%',
  '17) Sotto una distinta chiusa una riga non diventa pronta'
);

-- ============================================================
-- 18) «Niente da registrare» non e' un errore (Q-7, opzione B)
-- ============================================================
CREATE TEMP TABLE tmp_contabile_vuota AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT centro_banca_id FROM tmp_refs),
    p_data_contabile        => script.fn_data_operativa() - 1,
    p_data_registrazione    => script.fn_data_operativa(),
    p_codice_stato_interno  => 'BOZZA',
    p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
    p_origine               => 'MANUALE'
  ) AS contabile_id;

INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, importo, fattura_id,
     billing_account_id, stato_id, meta)
SELECT (SELECT contabile_id FROM tmp_contabile_vuota), 'PGTAP_E', script.fn_data_operativa(), 10.00,
       (SELECT id FROM tmp_fattura), r.billing_account_id, r.stato_sospesa_id,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r;

UPDATE pagamenti.vendite_contabili c
   SET stato_id = (SELECT stato_validata_id FROM tmp_refs)
 WHERE c.id = (SELECT contabile_id FROM tmp_contabile_vuota);

CREATE TEMP TABLE tmp_esito_vuota AS
SELECT * FROM pagamenti.fn_posta_contabile((SELECT contabile_id FROM tmp_contabile_vuota));

SELECT is(
  (SELECT esito FROM tmp_esito_vuota),
  'NULLA_DA_POSTARE'::text,
  '18) «Niente da registrare» e'' un esito, non un errore'
);

-- ============================================================
-- 19) Una distinta che non esiste
-- ============================================================
SELECT throws_ok(
  'SELECT * FROM pagamenti.fn_posta_contabile(999999999)',
  'P0001',
  NULL,
  '19) Una distinta che non esiste e'' rifiutata'
);

-- ============================================================
-- Cleanup
-- ============================================================
-- ⚠️ Ordine imposto dalle FK: movimenti -> righe -> testate -> fattura.
SELECT set_config('zeroerp.maintenance_allow_delete_logs', 'on', true);

DELETE FROM pagamenti.vendite_movimenti
 WHERE fattura_id = (SELECT id FROM tmp_fattura);

-- ⚠️ Dal 2026-09-14 (D17) il DELETE di una riga contabile passa dal guard del
--    contenuto della distinta: sotto una CHIUSA o una GENERATA e' rifiutato.
--    Questo cleanup e' un passaggio tecnico e lo dichiara con la stessa GUC
--    che usa la madre del giro dei fondi (fn_cancella_fondo_fattura); il
--    ROLLBACK farebbe comunque il lavoro.
SELECT set_config('zeroerp.allow_contabile_riga_delete_override', 'on', true);
DELETE FROM pagamenti.vendite_contabili_righe
 WHERE contabile_id IN (SELECT contabile_id FROM tmp_contabile
                        UNION ALL SELECT contabile_id FROM tmp_contabile_vuota);

DELETE FROM pagamenti.vendite_contabili
 WHERE id IN (SELECT contabile_id FROM tmp_contabile
              UNION ALL SELECT contabile_id FROM tmp_contabile_vuota);

DELETE FROM vendite.fatture_log
 WHERE fattura_id = (SELECT id FROM tmp_fattura);

UPDATE vendite.fatture
   SET storicizza = false
 WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti);

DELETE FROM vendite.fatture
 WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti);

SELECT ok(true, '20) Cleanup completato');

SELECT * FROM finish();

ROLLBACK;
