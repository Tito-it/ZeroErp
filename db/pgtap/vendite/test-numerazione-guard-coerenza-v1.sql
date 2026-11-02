-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: Fase 4b / D-K — guard di coerenza alla numerazione
--       (vendite.fn_assign_numero_fattura, changeSet 20260802-24).
--
--       Una fattura per ciascuna delle SEI condizioni deve essere
--       respinta con E_FATTURA_NON_NUMERABILE_INCOERENTE.
--
--       ⚠️ COSA QUESTO FILE **NON** PUO' PROVARE, e perche' e' scritto
--       qui invece di essere scoperto da chi verra' dopo: la POSIZIONE
--       del guard rispetto a fn_get_next_progressivo non e' verificabile
--       con un pgTAP in questo modello. Il progressivo non e' una
--       sequence — e' `pg_advisory_xact_lock` + `UPDATE last_numero` su
--       registri_fatturazione_progressivi — quindi e' transazionale; e
--       throws_like cattura l'eccezione dentro un blocco con savepoint
--       implicito, che annulla comunque l'eventuale incremento.
--       MISURATO il 2026-08-02: spostando il guard DOPO il consumo del
--       progressivo, questo file resta interamente VERDE. Una versione
--       precedente del test 9 affermava di presidiare quella posizione:
--       non la presidiava, dava solo fiducia. Il test 9 e' stato quindi
--       riformulato su cio' che prova davvero.
--       Le ragioni per cui il guard sta comunque prima (non scrivere
--       prima di validare, non contendere l'advisory lock del registro,
--       non dipendere da chi ripulisce) stanno nel changeSet 20260802-24
--       e si presidiano in review, non con un'asserzione.
--
--       ⚠️ Ogni caso e' costruito perche' faccia scattare LA SUA
--       condizione: si parte da un documento completo e coerente e si
--       rompe una cosa sola. Un caso che ne violasse tre passerebbe
--       comunque, ma non direbbe quale ramo del guard funziona.
-- ------------------------------------------------------------
-- Indice test (1..9):
--   1)  fixture costruita: terna emittente/utility/BA coerente, con la configurazione scritta
--   2)  C1 totali non calcolati        -> respinta
--   3)  C2 riepilogo IVA assente       -> respinta
--   4)  C3a piano rate assente         -> respinta
--   5)  C3b somma rate != totale       -> respinta
--   6)  C4 rate su totale ZERO -> respinta (dal 2026-09-17: il negativo ha la sua rata, P-5)
--   7)  C5 riepiloghi IVA non coerenti con i totali di testata -> respinta
--   8)  C6 totale_a_pagare != somma degli addendi (fondi/arrotondamenti) -> respinta
--   9)  controprova: un documento COERENTE si numera e parte da 1
--       (il guard non rifiuta troppo, e i sei rifiuti non lasciano residui)
-- ------------------------------------------------------------
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (rev 2026-09-17 sera). Fino a quel
--   giorno la «terna scelta insieme» era pescata fra i dati della macchina —
--   una riga di anagrafiche.emittenti_fiscali_utilities con un billing account
--   della stessa utility: su un database ricostruito dai changelog (zeroerp_ci,
--   la CI) le anagrafiche sono a ZERO, tmp_refs_dk usciva vuota e il registro
--   nasceva con emittente NULL — ERRORE_FIXTURE in baseline-rossi-ci.tsv, il
--   guard D-K collaudato solo su dbdev. E la stessa fixture, ricopiata, ha fatto
--   nascere rosso test-nc-rata-unica-v1. Ora: un'azienda col suo operatore
--   (dbops.fn_pgtap_crea_emittente_operatore) PRIMA del contesto; NEL contesto
--   un cliente fatturabile (dbops.fn_pgtap_crea_cliente_ba) e la riga
--   emittente/utility che fn_ricalcola_totali_fattura pretende (2 decimali,
--   HALF_UP) — la terna resta «scelta insieme», ma perche' e' COSTRUITA
--   coerente, non perche' un LIMIT 1 l'ha trovata — guida
--   pgtap-come-si-scrive-un-test §«Il mondo si costruisce, non si cerca».
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

SELECT plan(9);

-- ============================================================
-- Fixture
-- ============================================================
-- Il cliente fatturabile, nel contesto dell'operatore: il legame BA -> emittente
-- lo scrive il trigger z90 verso l'emittente di chi agisce.
CREATE TEMP TABLE tmp_cli_dk AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('guard coerenza numerazione') c;

-- La terna si sceglie INSIEME: il ricalcolo totali pretende una riga in
-- anagrafiche.emittenti_fiscali_utilities per la coppia (emittente, utility).
-- Qui la coppia la SCRIVE il test, coerente col cliente appena costruito.
INSERT INTO anagrafiche.emittenti_fiscali_utilities
    (emittente_soggetto_ruolo_id, utility_id, arrotondamento_importi_dec,
     metodo_arrotondamento_importi, meta)
SELECT m.soggetto_ruolo_id, c.utility_id, 2, 'HALF_UP',
       jsonb_build_object('test_scope', 'pgtap_guard_dk')
  FROM _mondo m, tmp_cli_dk c;

CREATE TEMP TABLE tmp_refs_dk AS
SELECT m.soggetto_ruolo_id                        AS emittente_soggetto_ruolo_id,
       (SELECT utility_id FROM tmp_cli_dk)        AS utility_id,
       (SELECT billing_account_id FROM tmp_cli_dk) AS billing_account_id
  FROM _mondo m;

SELECT ok(
  (SELECT count(*) = 1 FROM tmp_refs_dk WHERE billing_account_id IS NOT NULL)
  AND EXISTS (SELECT 1 FROM anagrafiche.emittenti_fiscali_utilities efu
               JOIN tmp_refs_dk r ON r.emittente_soggetto_ruolo_id = efu.emittente_soggetto_ruolo_id
                                 AND r.utility_id = efu.utility_id
              WHERE efu.attivo IS TRUE),
  '1) fixture costruita: terna emittente/utility/BA coerente, con la configurazione scritta');

-- Registro dedicato e VERGINE: e' cio' che rende leggibile il test 9.
CREATE TEMP TABLE tmp_reg_dk AS
WITH ins AS (
  -- ⛔ emittente_soggetto_ruolo_id e' NOT NULL dal 2026-08-30 (C1-2,
  --   20260830-11), e dev'essere lo STESSO delle fatture di questo file:
  --   vendite.trgfn_fatture_guard_registro_emittente rifiuta un documento
  --   sul registro di un altro emittente (C1-3, 20260830-10).
  INSERT INTO vendite.registri_fatturazione (codice, descrizione, reset_policy, attivo,
          emittente_soggetto_ruolo_id, meta)
  VALUES ('REGDK_pgtap_dk', 'Registro test guard coerenza numerazione', 'ANNUALE', true,
          (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_dk),
          jsonb_build_object('test_scope', 'pgtap_guard_dk'))
  RETURNING id)
SELECT * FROM ins;

-- Crea una fattura con UNA riga al prezzo richiesto. Nient'altro: i satelliti
-- li aggiunge ogni caso, quel tanto che gli serve.
-- ⚠️ 2026-08-07: `plpgsql` e due statement, non `sql` con una CTE sola.
--   La policy rls_fatture_righe_ef_whitelist risolve l'emittente passando da
--   vendite.fatture (script.fn_scope_ef_whitelist_via_fattura, STABLE). Dentro
--   una CTE che scrive, tutti i rami condividono la stessa snapshot: la fattura
--   appena inserita NON e' ancora visibile, l'SR risolve a NULL e il WITH CHECK
--   nega fail-closed. Misurato: stessi dati, stesso operatore — in due statement
--   passa, in una CTE no. E' anche la forma piu' fedele: il BE crea la fattura
--   in uno step della pipeline e le righe in quello dopo, mai insieme.
CREATE FUNCTION pg_temp.fx_fattura_dk(p_prezzo numeric) RETURNS bigint LANGUAGE plpgsql AS $fx$
DECLARE
  v_fattura_id bigint;
BEGIN
  INSERT INTO vendite.fatture (registro_id, data, emittente_soggetto_ruolo_id,
                               billing_account_id, utility_id, stato_doc_fiscale_id,
                               tipo_doc_fiscale_id, valuta_id, termine_pagamento_id, meta)
  SELECT (SELECT id FROM tmp_reg_dk), script.fn_data_operativa(),
         r.emittente_soggetto_ruolo_id, r.billing_account_id, r.utility_id,
         (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DRAFT'),
         (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1),
         (SELECT id FROM config.valute ORDER BY (iso_code <> 'EUR'), id LIMIT 1),
         (SELECT id FROM config.termini_pagamento
           WHERE codice_interno = 'TP_1RATA' AND attivo IS TRUE),
         jsonb_build_object('test_scope', 'pgtap_guard_dk')
    FROM tmp_refs_dk r
  RETURNING id INTO v_fattura_id;

  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta,
                                     prezzo_unitario, iva_id, meta, competenza_dal, competenza_al)
  VALUES (v_fattura_id, 1, 'Riga test guard D-K', 1::numeric, p_prezzo,
          (SELECT id FROM config.iva WHERE attivo IS TRUE ORDER BY id LIMIT 1),
          jsonb_build_object('test_scope', 'pgtap_guard_dk'), script.fn_data_operativa(), script.fn_data_operativa());

  RETURN v_fattura_id;
END;
$fx$;

-- Porta la fattura allo stato COMPLETO E COERENTE, con le funzioni vere e
-- nell'ordine della pipeline: IVA -> totali -> rate.
CREATE FUNCTION pg_temp.fx_completa_dk(p_id bigint) RETURNS void LANGUAGE plpgsql AS $fx$
BEGIN
  PERFORM vendite.fn_ricalcola_riepilogo_iva_fattura(p_id);
  PERFORM vendite.fn_ricalcola_totali_fattura(p_id);
  PERFORM vendite.fn_genera_scadenze_fattura(p_id);
END;
$fx$;

-- ============================================================
-- 2) C1 — nessun ricalcolo: i totali non esistono
-- ============================================================
CREATE TEMP TABLE tmp_c1 AS SELECT pg_temp.fx_fattura_dk(100) AS id;
SELECT throws_like(
  $$ SELECT * FROM vendite.fn_assign_numero_fattura((SELECT id FROM tmp_c1)) $$,
  '%totali non calcolati%',
  '2) C1: totali non calcolati -> numerazione respinta');

-- ============================================================
-- 3) C2 — riepilogo IVA cancellato dopo il ricalcolo
-- ============================================================
CREATE TEMP TABLE tmp_c2 AS SELECT pg_temp.fx_fattura_dk(100) AS id;
SELECT pg_temp.fx_completa_dk((SELECT id FROM tmp_c2));
DELETE FROM vendite.fatture_riepiloghi_iva WHERE fattura_id = (SELECT id FROM tmp_c2);
SELECT throws_like(
  $$ SELECT * FROM vendite.fn_assign_numero_fattura((SELECT id FROM tmp_c2)) $$,
  '%riepilogo IVA assente%',
  '3) C2: riepilogo IVA assente -> numerazione respinta');

-- ============================================================
-- 4) C3a — documento da incassare senza piano rate.
--    E' il caso della fattura 362: DEFINITIVA, numero 6, totale 200, zero rate.
-- ============================================================
CREATE TEMP TABLE tmp_c3a AS SELECT pg_temp.fx_fattura_dk(100) AS id;
SELECT vendite.fn_ricalcola_riepilogo_iva_fattura((SELECT id FROM tmp_c3a));
SELECT vendite.fn_ricalcola_totali_fattura((SELECT id FROM tmp_c3a));
SELECT throws_like(
  $$ SELECT * FROM vendite.fn_assign_numero_fattura((SELECT id FROM tmp_c3a)) $$,
  '%piano rate assente%',
  '4) C3a: piano rate assente su totale positivo -> numerazione respinta');

-- ============================================================
-- 5) C3b — le rate ci sono ma non quadrano
-- ============================================================
CREATE TEMP TABLE tmp_c3b AS SELECT pg_temp.fx_fattura_dk(100) AS id;
SELECT pg_temp.fx_completa_dk((SELECT id FROM tmp_c3b));
UPDATE vendite.fatture_scadenze SET importo = importo - 1
 WHERE fattura_id = (SELECT id FROM tmp_c3b);
SELECT throws_like(
  $$ SELECT * FROM vendite.fn_assign_numero_fattura((SELECT id FROM tmp_c3b)) $$,
  '%somma delle rate%diversa dal totale a pagare%',
  '5) C3b: somma delle rate diversa dal totale -> numerazione respinta');

-- ============================================================
-- 6) C4 — D-D allo specchio: rate su un documento a totale ZERO.
--    Prezzo zero -> totale zero -> il generatore NON crea rate; una rata
--    inserita a mano e' quindi esattamente l'incoerenza da intercettare.
--    ⭐ Dal 2026-09-17 (P-5) la condizione e' «= 0» e non piu' «<= 0»: il
--    documento NEGATIVO ha la sua rata unica e si numera (lo prova
--    test-nc-rata-unica-v1.sql); qui resta il caso dello zero.
-- ============================================================
CREATE TEMP TABLE tmp_c4 AS SELECT pg_temp.fx_fattura_dk(0) AS id;
SELECT pg_temp.fx_completa_dk((SELECT id FROM tmp_c4));
INSERT INTO vendite.fatture_scadenze (fattura_id, numero_rata, data_scadenza, importo)
VALUES ((SELECT id FROM tmp_c4), 1, script.fn_data_operativa(), 0);
SELECT throws_like(
  $$ SELECT * FROM vendite.fn_assign_numero_fattura((SELECT id FROM tmp_c4)) $$,
  '%rate su un totale a pagare zero%',
  '6) C4: rate presenti su totale zero -> numerazione respinta');

-- ============================================================
-- 7) C5 — i riepiloghi IVA si spostano, la testata resta ferma.
--    Non e' un caso di scuola: fatture_riepiloghi_iva e' fuori dal guard di
--    congelamento dei satelliti, quindi la strada esiste davvero.
-- ============================================================
CREATE TEMP TABLE tmp_c5 AS SELECT pg_temp.fx_fattura_dk(100) AS id;
SELECT pg_temp.fx_completa_dk((SELECT id FROM tmp_c5));
UPDATE vendite.fatture_riepiloghi_iva SET imponibile = imponibile + 10
 WHERE fattura_id = (SELECT id FROM tmp_c5);
SELECT throws_like(
  $$ SELECT * FROM vendite.fn_assign_numero_fattura((SELECT id FROM tmp_c5)) $$,
  '%riepilogo IVA non coerente con i totali di testata%',
  '7) C5: riepiloghi non coerenti con i totali di testata -> numerazione respinta');

-- ============================================================
-- 8) C6 — l'anello di mezzo: un arrotondamento comparso DOPO il ricalcolo.
--    Le rate continuano a quadrare con totale_a_pagare (la C3 tace), i
--    riepiloghi continuano a quadrare con totale_doc (la C5 tace): senza
--    questa condizione il documento passerebbe con un totale che non tiene
--    conto dell'addendo nuovo. E' il caso dell'acconto registrato in ritardo.
-- ============================================================
CREATE TEMP TABLE tmp_c6 AS SELECT pg_temp.fx_fattura_dk(100) AS id;
SELECT pg_temp.fx_completa_dk((SELECT id FROM tmp_c6));
UPDATE vendite.fatture SET arrotondamento_attuale = COALESCE(arrotondamento_attuale, 0) + 5
 WHERE id = (SELECT id FROM tmp_c6);
SELECT throws_like(
  $$ SELECT * FROM vendite.fn_assign_numero_fattura((SELECT id FROM tmp_c6)) $$,
  '%non corrisponde alla somma dei suoi addendi%',
  '8) C6: totale a pagare diverso dalla somma degli addendi -> numerazione respinta');

-- ============================================================
-- 9) Controprova — la meta' che manca a un test di guard.
--    Sei casi provano che il guard RIFIUTA; questo prova che non rifiuta
--    TROPPO: un documento costruito con le funzioni vere e coerente su tutte e
--    sei le condizioni passa, e prende il primo numero del registro.
--    ⚠️ Non e' un'asserzione sulla posizione del guard: come spiegato in testa
--    al file, il progressivo e' transazionale e il numero sarebbe 1 anche con
--    il guard a valle. Qui l'1 dice due cose piu' modeste ma vere — il registro
--    creato dalla fixture e' vergine, e i sei rifiuti non hanno lasciato
--    residui che alterino il conteggio.
-- ============================================================
CREATE TEMP TABLE tmp_ok AS SELECT pg_temp.fx_fattura_dk(100) AS id;
SELECT pg_temp.fx_completa_dk((SELECT id FROM tmp_ok));
SELECT is(
  (SELECT numero FROM vendite.fn_assign_numero_fattura((SELECT id FROM tmp_ok))),
  1::bigint,
  '9) controprova: un documento coerente si numera e prende il numero 1');

SELECT * FROM finish();
ROLLBACK;
