-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_genera_scadenze_fattura — il generatore del piano rate
--       (piano-db-satelliti-fattura.md Fase 4.1, rilievi C-4/C-5, decisioni D-D/D-E/D-F)
-- ------------------------------------------------------------
-- Perche' questo file esiste, e perche' arriva INSIEME alla funzione
--   Nella Fase 3b i test sono arrivati per ultimi e tre difetti sono stati
--   trovati a mano, uno alla volta, riparando altro. Qui si inverte l'ordine:
--   il generatore e la sua copertura nascono nello stesso giro.
--
--   Quello che va presidiato non e' «genera delle rate», e' che generi
--   ESATTAMENTE quelle: la somma deve fare la base al centesimo (una fattura
--   le cui rate non quadrano e' un documento che non si puo' incassare), le
--   date devono seguire la formula a ramo unico di C-5, e i tre casi della
--   base di D-D devono restare tre casi diversi invece di ricollassare in un
--   errore solo — che e' il difetto che C-4 ha tolto dal brief originale.
-- ------------------------------------------------------------
-- Indice test
-- 1) Fixture costruita: azienda, cliente, fattura in DRAFT, fattura oltre la soglia, termine a 3 rate
-- 2) Termine mancante in testata -> E_SCADENZE_TERMINE_MANCANTE
-- 3) Base non calcolata -> E_SCADENZE_BASE_NON_PRONTA
-- 4) Fattura oltre la soglia DRAFT/EMESSA -> E_SCADENZE_FATTURA_BLOCCATA
-- 5) Rata unica: la data e' data_fattura + primo_offset_giorni
-- 6) fine_mese: la data si sposta a fine mese
-- 7) fine_mese a cavallo d anno: il clamp non ha codice dedicato
-- 8) Quadratura 100/3: la somma delle rate e ESATTAMENTE la base
-- 9) La differenza di quadratura sta sull ULTIMA rata
-- 10) numero_rata progressivo da 1 a numero_rate
-- 11) Idempotenza: rieseguire ricostruisce lo stesso piano
-- 12) Base = 0: zero rate, nessun log, e le rate precedenti spariscono
-- 13) Base < 0: UNA rata col segno alla prima data del termine, e log NON critico (P-5, 2026-09-17)
-- 14) Lo snapshot del termine finisce in testata con i VALORI
-- 15) Il rifiuto del piano rate porta il BERSAGLIO sulla fattura
-- 16) ...anche quello per termine mancante
-- ------------------------------------------------------------
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (rev 2026-09-17 sera). Fino a quel
--   giorno la fattura nasceva da fn_get_or_create_fattura_header su «la prima
--   attivita' fatturabile» e «l'ultimo lotto in DRAFT» della macchina, e il
--   caso oltre la soglia era «una fattura congelata qualunque», con uno skip
--   se mancava: su un database ricostruito dai changelog (zeroerp_ci, la CI)
--   non c'e' nessuna delle tre, e il file moriva nel fixture — ERRORE_FIXTURE
--   in baseline-rossi-ci.tsv, il generatore del piano rate collaudato solo su
--   dbdev. Ora: un'azienda col suo operatore
--   (dbops.fn_pgtap_crea_emittente_operatore) PRIMA del contesto, un cliente
--   fatturabile (dbops.fn_pgtap_crea_cliente_ba) NEL contesto, e DUE fatture
--   scritte dal test — una in DRAFT, una nata gia' in uno stato che congela
--   (nessuna transizione: la matrice degli stati resta al suo guard). Il
--   generatore legge la sola testata (data, base, termine, stato): la porta
--   del creatore applicativo non gli aggiungeva niente, e lo skip del test 4
--   sparisce — guida pgtap-come-si-scrive-un-test §«Il mondo si costruisce,
--   non si cerca».
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima la
--   fattura oltre la soglia nasceva gia' nel primo stato che congela). La
--   matrice ora si attraversa: per uscire dalla bozza la fattura vuole
--   indirizzi e intestazione, e li scrivono i building block della pipeline
--   (vendite.fn_snapshot_indirizzi_fattura, fn_snapshot_intestazione_fattura).
--   Il caso non cambia: il generatore legge lo stato, e la fattura ha ancora
--   termine e base.
-- ------------------------------------------------------------

BEGIN;

-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore.
CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

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
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

SELECT plan(16);

-- ============================================================
-- 0) Fixture
-- ============================================================
-- Il cliente fatturabile, nel contesto dell'operatore: il legame BA -> emittente
-- lo scrive il trigger z90 verso l'emittente di chi agisce.
CREATE TEMP TABLE tmp_cli_gsf AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('genera scadenze') c;

CREATE TEMP TABLE tmp_refs_gsf AS
SELECT m.soggetto_ruolo_id                                                          AS emittente_sr_id,
       script.fn_pgtap_registro_fattura(m.soggetto_ruolo_id)                        AS registro_id,
       (SELECT billing_account_id FROM tmp_cli_gsf)                                  AS billing_account_id,
       (SELECT utility_id FROM tmp_cli_gsf)                                          AS utility_id,
       (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DRAFT')      AS stato_draft_id,
       -- Lo stato oltre la soglia si sceglie dal CONTRATTO (congela_fiscale),
       -- non da un nome: e' la stessa colonna che il generatore legge.
       (SELECT id FROM config.stati_doc_fiscale WHERE congela_fiscale IS TRUE
         ORDER BY ordine, id LIMIT 1)                                                AS stato_congelato_id,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY (iso_code <> 'EUR'), id LIMIT 1)       AS valuta_id
  FROM _mondo m;

-- La fattura di prova, in DRAFT: la testata e' tutto cio' che il generatore
-- legge (data, base, termine, stato).
CREATE TEMP TABLE tmp_f_gsf AS
WITH ins AS (
  INSERT INTO vendite.fatture (registro_id, data, emittente_soggetto_ruolo_id,
                               billing_account_id, utility_id, stato_doc_fiscale_id,
                               tipo_doc_fiscale_id, valuta_id, meta)
  SELECT r.registro_id, DATE '2026-01-15', r.emittente_sr_id, r.billing_account_id,
         r.utility_id, r.stato_draft_id, r.tipo_doc_fiscale_id, r.valuta_id,
         jsonb_build_object('test_scope', 'pgtap_genera_scadenze_fattura')
    FROM tmp_refs_gsf r
  RETURNING id)
SELECT id FROM ins;

-- La fattura OLTRE la soglia. ⛔ Dal 2026-10-24 nasce in bozza come ogni
-- documento (script.trgfn_doc_stato_iniziale): si scrivono indirizzi e
-- intestazione come la pipeline prima di emettere, e la si porta nel primo
-- stato che congela per la matrice, sotto i guard veri.
CREATE TEMP TABLE tmp_f_congelata_gsf AS
WITH ins AS (
  INSERT INTO vendite.fatture (registro_id, data, emittente_soggetto_ruolo_id,
                               billing_account_id, utility_id,
                               tipo_doc_fiscale_id, valuta_id, totale_a_pagare,
                               termine_pagamento_id, meta)
  SELECT r.registro_id, DATE '2026-01-15', r.emittente_sr_id, r.billing_account_id,
         r.utility_id, r.tipo_doc_fiscale_id, r.valuta_id, 100.00,
         (SELECT id FROM config.termini_pagamento WHERE codice_interno = 'TP_30G_1R'),
         jsonb_build_object('test_scope', 'pgtap_genera_scadenze_fattura')
    FROM tmp_refs_gsf r
  RETURNING id)
SELECT id FROM ins;

SELECT vendite.fn_snapshot_indirizzi_fattura(f.id),
       vendite.fn_snapshot_intestazione_fattura(f.id)
  FROM tmp_f_congelata_gsf f;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.fatture', f.id, s.codice_interno)
  FROM tmp_f_congelata_gsf f, tmp_refs_gsf r
  JOIN config.stati_doc_fiscale s ON s.id = r.stato_congelato_id;

-- Termine di prova a 3 rate: serve alla quadratura di 100/3, che e' il caso in
-- cui la divisione non torna. I 9 termini di catalogo hanno 1 o 2 rate.
CREATE TEMP TABLE tmp_tp3_gsf AS
WITH ins AS (
  INSERT INTO config.termini_pagamento (
      codice, codice_interno, descrizione, numero_rate, intervallo,
      primo_offset_giorni, fine_mese, ripartizione,
      arrotondamento_metodo, arrotondamento_decimali)
  VALUES ('T3PGTAP', 'TP_PGTAP_3R', 'tre rate (fixture pgTAP)', 3, 30, 30, false,
          'UGUALI', 'HALF_UP', 2)
  RETURNING id)
SELECT id FROM ins;

SELECT ok(
  (SELECT id FROM tmp_f_gsf) IS NOT NULL AND (SELECT id FROM tmp_tp3_gsf) IS NOT NULL
  AND (SELECT id FROM tmp_f_congelata_gsf) IS NOT NULL,
  '1) Fixture costruita: azienda, cliente, fattura in DRAFT, fattura oltre la soglia, termine a 3 rate');

-- ============================================================
-- 1) I codici di errore, uno per caso
-- ============================================================
UPDATE vendite.fatture
   SET termine_pagamento_id = NULL, totale_a_pagare = 100.00, data = DATE '2026-01-15'
 WHERE id = (SELECT id FROM tmp_f_gsf);

SELECT throws_ok(
  format($$ SELECT * FROM vendite.fn_genera_scadenze_fattura(%s) $$, (SELECT id FROM tmp_f_gsf)),
  'P0001', NULL,
  '2) Termine mancante in testata -> errore (non un fallback silenzioso)');

-- ⚠️ La base si azzera DOPO aver rimesso il termine: se restassero entrambi
-- mancanti, il test misurerebbe il guard precedente e passerebbe per la
-- ragione sbagliata.
UPDATE vendite.fatture
   SET termine_pagamento_id = (SELECT id FROM tmp_tp3_gsf), totale_a_pagare = NULL
 WHERE id = (SELECT id FROM tmp_f_gsf);

SELECT throws_ok(
  format($$ SELECT * FROM vendite.fn_genera_scadenze_fattura(%s) $$, (SELECT id FROM tmp_f_gsf)),
  'P0001', NULL,
  '3) Base non calcolata -> errore (passo eseguito fuori ordine)');

-- La soglia si prova su una fattura portata oltre DRAFT/EMESSA per la matrice
-- (rev 2026-10-24: prima vi nasceva; ora un documento nasce solo in bozza). ⚠️ throws_like sulla frase, non
-- throws_ok P0001: la fattura ha termine e base, quindi l'unico rifiuto
-- possibile e' la soglia — e la frase lo dice.
SELECT throws_like(
  format($$ SELECT * FROM vendite.fn_genera_scadenze_fattura(%s) $$,
         (SELECT id FROM tmp_f_congelata_gsf)),
  '%piano rate non%rigenerabile%',
  '4) Fattura oltre la soglia DRAFT/EMESSA -> errore, non una DELETE che fallisce sul trigger');

-- ============================================================
-- 2) La formula delle date
-- ============================================================
UPDATE vendite.fatture
   SET totale_a_pagare = 100.00, data = DATE '2026-01-15',
       termine_pagamento_id = (SELECT id FROM config.termini_pagamento WHERE codice_interno = 'TP_30G_1R')
 WHERE id = (SELECT id FROM tmp_f_gsf);
SELECT vendite.fn_genera_scadenze_fattura((SELECT id FROM tmp_f_gsf));

SELECT is(
  (SELECT data_scadenza FROM vendite.fatture_scadenze WHERE fattura_id = (SELECT id FROM tmp_f_gsf)),
  DATE '2026-02-14',
  '5) Rata unica: 15/01 + 30 giorni = 14/02');

UPDATE vendite.fatture
   SET termine_pagamento_id = (SELECT id FROM config.termini_pagamento WHERE codice_interno = 'TP_30G_EOM_1R')
 WHERE id = (SELECT id FROM tmp_f_gsf);
SELECT vendite.fn_genera_scadenze_fattura((SELECT id FROM tmp_f_gsf));

SELECT is(
  (SELECT data_scadenza FROM vendite.fatture_scadenze WHERE fattura_id = (SELECT id FROM tmp_f_gsf)),
  DATE '2026-02-28',
  '6) fine_mese: 14/02 si sposta al 28/02');

-- Cavallo d'anno: dicembre + 30 giorni cade a gennaio, e il fine mese deve
-- essere quello di GENNAIO dell'anno dopo. Il clamp lo fa PostgreSQL: il test
-- serve a garantire che nessuno lo sostituisca con aritmetica fatta a mano.
UPDATE vendite.fatture SET data = DATE '2026-12-20' WHERE id = (SELECT id FROM tmp_f_gsf);
SELECT vendite.fn_genera_scadenze_fattura((SELECT id FROM tmp_f_gsf));

SELECT is(
  (SELECT data_scadenza FROM vendite.fatture_scadenze WHERE fattura_id = (SELECT id FROM tmp_f_gsf)),
  DATE '2027-01-31',
  '7) fine_mese a cavallo d anno: 20/12/2026 + 30 -> 31/01/2027');

-- ============================================================
-- 3) La quadratura
-- ============================================================
UPDATE vendite.fatture
   SET data = DATE '2026-01-15', totale_a_pagare = 100.00,
       termine_pagamento_id = (SELECT id FROM tmp_tp3_gsf)
 WHERE id = (SELECT id FROM tmp_f_gsf);
SELECT vendite.fn_genera_scadenze_fattura((SELECT id FROM tmp_f_gsf));

SELECT is(
  (SELECT sum(importo) FROM vendite.fatture_scadenze WHERE fattura_id = (SELECT id FROM tmp_f_gsf)),
  100.00::numeric,
  '8) Quadratura: la somma delle rate e ESATTAMENTE la base');

SELECT ok(
  (SELECT importo FROM vendite.fatture_scadenze
    WHERE fattura_id = (SELECT id FROM tmp_f_gsf) AND numero_rata = 3)
  > (SELECT importo FROM vendite.fatture_scadenze
      WHERE fattura_id = (SELECT id FROM tmp_f_gsf) AND numero_rata = 1),
  '9) La differenza di quadratura sta sull ultima rata');

SELECT is(
  (SELECT array_agg(numero_rata ORDER BY numero_rata)::int[]
     FROM vendite.fatture_scadenze WHERE fattura_id = (SELECT id FROM tmp_f_gsf)),
  ARRAY[1,2,3]::int[],
  '10) numero_rata progressivo da 1 a numero_rate');

-- ============================================================
-- 4) Idempotenza
-- ============================================================
-- Non basta contare le righe: un generatore che sbaglia le date le
-- riscriverebbe diverse mantenendo lo stesso conteggio. Si confronta il piano
-- intero, importi e date.
CREATE TEMP TABLE tmp_piano1_gsf AS
SELECT numero_rata, data_scadenza, importo
  FROM vendite.fatture_scadenze WHERE fattura_id = (SELECT id FROM tmp_f_gsf);

SELECT vendite.fn_genera_scadenze_fattura((SELECT id FROM tmp_f_gsf));

SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM tmp_piano1_gsf p
    FULL JOIN (SELECT numero_rata, data_scadenza, importo
                 FROM vendite.fatture_scadenze
                WHERE fattura_id = (SELECT id FROM tmp_f_gsf)) d
      ON d.numero_rata = p.numero_rata
   WHERE d.data_scadenza IS DISTINCT FROM p.data_scadenza
      OR d.importo       IS DISTINCT FROM p.importo
      OR d.numero_rata   IS NULL OR p.numero_rata IS NULL),
  '11) Idempotenza: il rerun ricostruisce lo stesso piano, date e importi');

-- ============================================================
-- 5) I tre casi della base (D-D)
-- ============================================================
CREATE TEMP TABLE tmp_log_pre_gsf AS
SELECT count(*)::int AS n FROM vendite.fatture_log WHERE fattura_id = (SELECT id FROM tmp_f_gsf);

UPDATE vendite.fatture SET totale_a_pagare = 0 WHERE id = (SELECT id FROM tmp_f_gsf);
SELECT vendite.fn_genera_scadenze_fattura((SELECT id FROM tmp_f_gsf));

SELECT ok(
  (SELECT count(*) FROM vendite.fatture_scadenze WHERE fattura_id = (SELECT id FROM tmp_f_gsf)) = 0
  AND (SELECT count(*)::int FROM vendite.fatture_log WHERE fattura_id = (SELECT id FROM tmp_f_gsf))
      = (SELECT n FROM tmp_log_pre_gsf),
  '12) Base = 0: zero rate, nessun log, e le rate precedenti spariscono');

UPDATE vendite.fatture SET totale_a_pagare = -5.00 WHERE id = (SELECT id FROM tmp_f_gsf);
SELECT vendite.fn_genera_scadenze_fattura((SELECT id FROM tmp_f_gsf));

-- ⭐ P-5 (2026-09-17, D19-e): la base negativa ha UNA rata, importo = la base
--   col suo segno, data = la PRIMA del termine (primo_offset del termine a tre
--   rate della fixture: +30), meta che lo dichiara. Il log NON critico resta
--   (Q-D). Fino al 2026-09-17 qui si asseriva «zero rate».
SELECT ok(
  (SELECT count(*) = 1
      AND bool_and(s.numero_rata = 1)
      AND bool_and(s.importo = -5.00)
      AND bool_and(s.data_scadenza = f.data + 30)
      AND bool_and((s.meta->>'rata_unica_credito')::boolean IS TRUE)
     FROM vendite.fatture_scadenze s
     JOIN vendite.fatture f ON f.id = s.fattura_id
    WHERE s.fattura_id = (SELECT id FROM tmp_f_gsf))
  AND (SELECT count(*) FROM vendite.fatture_log
        WHERE fattura_id = (SELECT id FROM tmp_f_gsf) AND status = 'W'
          AND meta->>'source' = 'fn_genera_scadenze_fattura'
          AND meta->>'error_code' = 'W_SCADENZE_TOTALE_NEGATIVO') = 1,
  '13) Base < 0: UNA rata col segno (-5) alla prima data del termine, e log NON critico');

-- ============================================================
-- 6) Lo snapshot del termine
-- ============================================================
-- Un id non e' uno snapshot: se il catalogo cambia, la fattura deve continuare
-- a spiegare le rate che ha. Si verifica che ci siano i VALORI.
UPDATE vendite.fatture
   SET totale_a_pagare = 100.00, termine_pagamento_id = (SELECT id FROM tmp_tp3_gsf)
 WHERE id = (SELECT id FROM tmp_f_gsf);
SELECT vendite.fn_genera_scadenze_fattura((SELECT id FROM tmp_f_gsf));

SELECT ok(
  (SELECT termine_pagamento_snapshot->>'codice_interno' = 'TP_PGTAP_3R'
      AND (termine_pagamento_snapshot->>'numero_rate')::int = 3
      AND (termine_pagamento_snapshot->>'primo_offset_giorni')::int = 30
      AND termine_pagamento_snapshot ? 'arrotondamento_metodo'
     FROM vendite.fatture WHERE id = (SELECT id FROM tmp_f_gsf)),
  '14) Lo snapshot in testata porta i VALORI del termine, non il solo id');

-- ============================================================
-- 15-16) ⭐ IL BERSAGLIO — e chi non lo prende, nella stessa funzione.
--   Questi due rifiuti nascono DENTRO il giro di lotto: la fattura da
--   sistemare non e' quella che l'operatore ha davanti, e senza bersaglio
--   dovrebbe cercarsela. ⛔ Il 16 presidia l'esclusione: E_VALORE_MANCANTE ha
--   un context IDENTICO ai due, ma parla di un CAMPO — il suo canale e'
--   COLUMN, non DATATYPE — e un'ancora piu' larga in fase di scrittura gli
--   avrebbe messo il bersaglio addosso.
--   ⚠️ Il verbo in un'istruzione separata dall'asserzione.
--   Brief: brief-db-bersaglio-errore §6 L6.
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.gsf_canali(p_fattura_id bigint)
RETURNS TABLE(bersaglio text, codice text) AS $fn$
-- ⚠️ `text` espliciti: sono canali dell'eccezione, non valori di colonna.
DECLARE v_b text; v_c text;
BEGIN
  PERFORM * FROM vendite.fn_genera_scadenze_fattura(p_fattura_id);
  RETURN QUERY SELECT 'NESSUN ERRORE'::text, ''::text;
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_b = PG_DATATYPE_NAME, v_c = CONSTRAINT_NAME;
  RETURN QUERY SELECT COALESCE(v_b, ''), COALESCE(v_c, '');
END $fn$ LANGUAGE plpgsql;

-- Stato di partenza: termine presente, base NULL -> E_SCADENZE_BASE_NON_PRONTA
UPDATE vendite.fatture
   SET termine_pagamento_id = (SELECT id FROM tmp_tp3_gsf), totale_a_pagare = NULL
 WHERE id = (SELECT id FROM tmp_f_gsf);

CREATE TEMP TABLE tmp_gsf_canali AS
SELECT * FROM pg_temp.gsf_canali((SELECT id FROM tmp_f_gsf));

SELECT is(
  (SELECT bersaglio || '|' || codice FROM tmp_gsf_canali),
  'FATTURA:' || (SELECT id FROM tmp_f_gsf)::text || '|E_SCADENZE_BASE_NON_PRONTA',
  '15) il rifiuto del piano rate porta il bersaglio sulla fattura'
);

-- ⛔ E ora il codice che NON lo prende, sollevato dalla stessa funzione.
UPDATE vendite.fatture
   SET termine_pagamento_id = NULL, totale_a_pagare = NULL
 WHERE id = (SELECT id FROM tmp_f_gsf);

CREATE TEMP TABLE tmp_gsf_canali_2 AS
SELECT * FROM pg_temp.gsf_canali((SELECT id FROM tmp_f_gsf));

SELECT is(
  (SELECT bersaglio FROM tmp_gsf_canali_2),
  'FATTURA:' || (SELECT id FROM tmp_f_gsf)::text,
  '16) anche il rifiuto per termine mancante porta il bersaglio'
);

SELECT * FROM finish();

ROLLBACK;
