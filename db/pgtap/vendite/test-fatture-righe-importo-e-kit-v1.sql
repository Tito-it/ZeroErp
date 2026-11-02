-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- Test: importo di riga fattura, congelamento, e snapshot kit
-- Brief: brief-fix-importi-riga-fattura-zero.md
-- Changeset coperti: 20260728-01..16
--
-- PERCHE' ESISTE. Fino al 2026-07-28 NESSUNO valorizzava
-- vendite.fatture_righe.imponibile_riga: 7 righe su 7 a NULL, che
-- fn_ricalcola_riepilogo_iva_fattura trasformava in zero con un COALESCE, fino a
-- produrre fatture con totale 0,00 EUR — il 100% di quelle emesse dal sistema.
-- Il difetto e' sopravvissuto a una suite verde perche' le fixture dei test
-- FORNIVANO l'importo a mano, cioe' esattamente il dato che il percorso di
-- produzione non generava mai.
--
-- ⚠️ QUESTO FILE NON DEVE MAI FORNIRE `imponibile_riga`. Se un giorno servisse
-- passarlo per far tornare un atteso, vuol dire che il calcolo si e' rotto.
-- Il caso 7 presidia proprio questo: un valore passato dall'esterno viene
-- IGNORATO.
--
-- Idempotente: BEGIN ... ROLLBACK.
-- ------------------------------------------------------------
-- Indice test (1..19):
--   1) precondizione: riferimenti minimi presenti
--  -- importo di riga (D1)
--   2) qta 100 x prezzo 5, senza sconto            -> 500.00
--   3) sconto 10%                                  -> 450.00
--   4) sconto NULL esplicito, trattato come 0      -> 500.00
--   5) qta 0                                       -> 0, NON NULL
--   6) arrotondamento SOLO alla fine: 3 x 0.333    -> 1.00
--   7) valore esterno di imponibile_riga           -> IGNORATO
--  -- pulizia del modello (D1-ter)
--   8) imposta_riga non esiste piu'
--   9) totale_riga non esiste piu'
--  10) imponibile_riga e' NOT NULL
--  -- congelamento (D1-bis)
--  11) UPDATE qta entro soglia: l'importo si riallinea
--  12) UPDATE qta oltre soglia: respinto
--  13) DELETE riga oltre soglia: respinto
--  14) INSERT riga oltre soglia: respinto
--  -- numerazione (D3)
--  15) numerazione di una fattura SENZA righe: respinta
--  -- kit ed esposizione (D5)
--  16) riga di kit con metadati a meta': respinta dal CHECK
--  17) la vista produce UNA riga padre col totale del kit
--  18) compaiono solo i componenti esposti, senza importo
--  -- vocabolario arrotondamento (20260728-07/08)
--  19) metodo di arrotondamento sconosciuto: solleva
-- ------------------------------------------------------------

BEGIN;

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
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(19);

-- ============================================================
-- FIXTURE
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): cliente e articolo si COSTRUISCONO
--   (dbops.fn_pgtap_crea_cliente_ba, BA dell'azienda di chi agisce;
--   dbops.fn_pgtap_crea_articolo, il padre del kit), l'emittente e' quello
--   dell'operatore di contesto e il registro e' il suo
--   (script.fn_pgtap_registro_fattura). Prima la coppia (emittente, utility)
--   si pescava da emittenti_fiscali_utilities, il BA col primo id e
--   l'articolo era l'ultimo inserito: da zero non c'era niente. Senza la
--   riga (emittente, utility) i decimali li danno i parametri di sistema
--   dell'utility. Le fatture restano scritte a mano: sono il caso del test.
CREATE TEMP TABLE tmp_cli_fri AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('fatture righe importo');

CREATE TEMP TABLE tmp_refs_fri AS
SELECT script.fn_pgtap_emittente_sr_operatore()                             AS emittente_soggetto_ruolo_id,
       (SELECT billing_account_id FROM tmp_cli_fri)                         AS billing_account_id,
       (SELECT id FROM config.iva WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS iva_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1)                   AS valuta_id,
       (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DRAFT')      AS stato_draft,
       (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'EMESSA')     AS stato_emessa,
       (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DEFINITIVA') AS stato_definitiva,
       dbops.fn_pgtap_crea_articolo('PGTAP-FRI-PADRE')                      AS articolo_id,
       -- 3b.3: l'utility va scritta IN TESTATA. Il ricalcolo la legge da
       -- vendite.fatture.utility_id invece di dedurla da lotto/BA, quindi la
       -- fixture la porta dal cliente costruito.
       (SELECT utility_id FROM tmp_cli_fri)                                 AS utility_id;

SELECT ok(
  (SELECT emittente_soggetto_ruolo_id IS NOT NULL
      AND billing_account_id IS NOT NULL
      AND articolo_id IS NOT NULL
     FROM tmp_refs_fri),
  '1) Riferimenti minimi presenti');

CREATE TEMP TABLE tmp_reg_fri AS
SELECT script.fn_pgtap_registro_fattura(
         (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_fri)) AS id;

-- Scopo: crea una fattura di test nello stato richiesto.
CREATE OR REPLACE FUNCTION pg_temp.fx_fattura_fri(p_stato bigint)
RETURNS bigint LANGUAGE sql AS $fx$
  INSERT INTO vendite.fatture (registro_id, data, emittente_soggetto_ruolo_id,
                               billing_account_id, stato_doc_fiscale_id, valuta_id,
                               utility_id, meta)
  SELECT (SELECT id FROM tmp_reg_fri), script.fn_data_operativa(),
         r.emittente_soggetto_ruolo_id, r.billing_account_id, p_stato, r.valuta_id,
         r.utility_id,
         jsonb_build_object('test_scope', 'pgtap_fatture_righe_importo')
    FROM tmp_refs_fri r
  RETURNING id;
$fx$;

CREATE TEMP TABLE tmp_fattura_fri AS
SELECT pg_temp.fx_fattura_fri((SELECT stato_draft FROM tmp_refs_fri)) AS id;

-- ============================================================
-- 2-7 — L'IMPORTO DI RIGA
-- Nessuna di queste INSERT fornisce `imponibile_riga`: lo calcola il trigger
-- trg_fatture_righe_a20_importo_ins_upd.
-- ============================================================

-- Scopo: inserisce una riga e ne restituisce l'imponibile calcolato dal DB.
CREATE OR REPLACE FUNCTION pg_temp.fx_riga_fri(
  p_nr integer, p_qta numeric, p_prezzo numeric, p_sconto numeric)
RETURNS numeric LANGUAGE sql AS $fx$
  WITH ins AS (
    INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta,
                                       prezzo_unitario, sconto_percentuale, iva_id, competenza_dal, competenza_al)
    SELECT (SELECT id FROM tmp_fattura_fri), p_nr, 'Riga test ' || p_nr,
           p_qta, p_prezzo, p_sconto, (SELECT iva_id FROM tmp_refs_fri), script.fn_data_operativa(), script.fn_data_operativa()
    RETURNING imponibile_riga
  )
  SELECT imponibile_riga FROM ins;
$fx$;

SELECT is(pg_temp.fx_riga_fri(1, 100, 5, 0), 500.00::numeric,
          '2) qta 100 x prezzo 5 senza sconto -> 500.00');

SELECT is(pg_temp.fx_riga_fri(2, 100, 5, 10), 450.00::numeric,
          '3) sconto 10% -> 450.00');

-- `sconto_percentuale` ha DEFAULT 0 e non e' mai NULL sui dati reali: il NULL va
-- forzato. E' un caso di DIFESA (il COALESCE nella formula), non uno scenario che
-- il percorso normale produca.
SELECT is(pg_temp.fx_riga_fri(3, 100, 5, NULL), 500.00::numeric,
          '4) sconto NULL esplicito trattato come 0 -> 500.00');

SELECT is(pg_temp.fx_riga_fri(4, 0, 5, 0), 0.00::numeric,
          '5) qta 0 -> zero ESPLICITO, non NULL');

-- ⭐ La prova che l'arrotondamento avviene UNA SOLA VOLTA, sul risultato:
--    3 x 0.333 = 0.999 -> 1.00. Arrotondando gli addendi si otterrebbe 0.99.
SELECT is(pg_temp.fx_riga_fri(5, 3, 0.333, 0), 1.00::numeric,
          '6) arrotondamento solo alla fine: 3 x 0.333 -> 1.00');

-- ⭐ Con la colonna generata un valore esterno faceva FALLIRE la scrittura; con
--    il trigger viene SOVRASCRITTO. Il risultato e' lo stesso — il valore
--    esterno non sopravvive mai — ma la segnalazione sparisce: questo caso e'
--    cio' che la sostituisce.
INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta,
                                   prezzo_unitario, iva_id, imponibile_riga, competenza_dal, competenza_al)
SELECT (SELECT id FROM tmp_fattura_fri), 6, 'Riga con importo imposto',
       1, 1, (SELECT iva_id FROM tmp_refs_fri), 999999, script.fn_data_operativa(), script.fn_data_operativa();

SELECT is(
  (SELECT imponibile_riga FROM vendite.fatture_righe
    WHERE fattura_id = (SELECT id FROM tmp_fattura_fri) AND riga_nr = 6),
  1.00::numeric,
  '7) valore di imponibile_riga passato dall''esterno: IGNORATO');

-- ============================================================
-- 8-10 — PULIZIA DEL MODELLO
-- L'imposta di riga non esiste nel regime italiano: l'IVA si liquida per
-- aliquota nei riepiloghi. Le due colonne erano persistite e mai scritte.
-- ============================================================
SELECT hasnt_column('vendite', 'fatture_righe', 'imposta_riga',
                    '8) imposta_riga rimossa dal modello');

SELECT hasnt_column('vendite', 'fatture_righe', 'totale_riga',
                    '9) totale_riga rimossa dal modello');

SELECT col_not_null('vendite', 'fatture_righe', 'imponibile_riga',
                    '10) imponibile_riga e'' NOT NULL: l''invariante e'' scritto nello schema');

-- ============================================================
-- 11-14 — CONGELAMENTO
-- La fattura e' un documento fiscale: oltre la soglia DRAFT/EMESSA le righe
-- sono uno snapshot. Il presidio agisce sugli INPUT, non sull'importo: bloccare
-- il solo importo lascerebbe passare una riga con qta=999 e imponibile=500,
-- incoerente e indistinguibile da un dato buono.
-- ============================================================
UPDATE vendite.fatture_righe SET qta = 200
 WHERE fattura_id = (SELECT id FROM tmp_fattura_fri) AND riga_nr = 1;

SELECT is(
  (SELECT imponibile_riga FROM vendite.fatture_righe
    WHERE fattura_id = (SELECT id FROM tmp_fattura_fri) AND riga_nr = 1),
  1000.00::numeric,
  '11) entro soglia l''UPDATE passa e l''importo si riallinea (200 x 5)');

-- DRAFT -> EMESSA -> DEFINITIVA: la soglia si supera solo cosi'.
--
-- ⚠️ PREPARAZIONE OBBLIGATORIA DAL 2026-07-31 (piano satelliti I.4). Il primo
--    passo e' un'uscita dalla bozza, e vendite.trgfn_fatture_guard_uscita_draft
--    pretende che chi la lascia sia completo: indirizzo obbligatorio
--    dell'ambito FATTURE piu' intestazione fiscale congelata delle due parti.
--    Qui non si sta collaudando quel guard — si sta solo portando la fattura
--    oltre la soglia di congelamento per il test 12 — quindi si soddisfa il
--    requisito con lo stretto necessario, come farebbe lo step DRAFT del lotto.
INSERT INTO vendite.fatture_indirizzi (fattura_id, tipo_indirizzo_id, snapshot)
SELECT (SELECT id FROM tmp_fattura_fri),
       (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'FATT'),
       '{"intestazione":"Cliente pgTAP","via":"Via Importo Riga"}'::jsonb;

UPDATE vendite.fatture
   -- ⚠️ con la sede del cedente: senza, la fattura non lascia DRAFT
   --   (20261021-13, brief-db-modelli-documento-standard §10.7 R-5).
   SET emittente_snapshot = '{"denominazione":"Emittente pgTAP","sede":{"via":"Via Cedente 1","cap":"83100"}}'::jsonb,
       cliente_snapshot   = '{"denominazione":"Cliente pgTAP"}'::jsonb
 WHERE id = (SELECT id FROM tmp_fattura_fri);

-- rev 2026-10-27 (brief-modello-documento-vendita §15): con la porta sulla fattura
-- lo stato si scrive dal verbo della fattura, come lo scrive la pipeline.
SELECT vendite.fn_fattura_proietta_stato((SELECT id FROM tmp_fattura_fri), (SELECT stato_emessa FROM tmp_refs_fri));
SELECT vendite.fn_fattura_proietta_stato((SELECT id FROM tmp_fattura_fri), (SELECT stato_definitiva FROM tmp_refs_fri));

SELECT throws_like(
  $$ UPDATE vendite.fatture_righe SET qta = 5
      WHERE fattura_id = (SELECT id FROM tmp_fattura_fri) AND riga_nr = 1 $$,
  '%righe non sono piu'' modificabili%',
  '12) oltre soglia l''UPDATE della quantita'' e'' respinto');

SELECT throws_like(
  $$ DELETE FROM vendite.fatture_righe
      WHERE fattura_id = (SELECT id FROM tmp_fattura_fri) AND riga_nr = 1 $$,
  '%righe non sono piu'' modificabili%',
  '13) oltre soglia il DELETE della riga e'' respinto');

SELECT throws_like(
  $$ INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, competenza_dal, competenza_al)
     SELECT (SELECT id FROM tmp_fattura_fri), 99, 'Riga tardiva', 1, 1, script.fn_data_operativa(), script.fn_data_operativa() $$,
  '%righe non sono piu'' modificabili%',
  '14) oltre soglia anche l''INSERT di una riga nuova e'' respinto');

-- ============================================================
-- 15 — NUMERAZIONE DI UN DOCUMENTO VUOTO
-- Origine: le fatture 207 e 208, DEFINITIVE e senza alcuna riga. Il guard sta
-- PRIMA che il progressivo venga consumato: nextval non fa rollback, quindi
-- fallire dopo lascerebbe comunque un buco nella numerazione fiscale.
-- ============================================================
CREATE TEMP TABLE tmp_fattura_vuota_fri AS
SELECT pg_temp.fx_fattura_fri((SELECT stato_draft FROM tmp_refs_fri)) AS id;

SELECT throws_like(
  $$ SELECT * FROM vendite.fn_assign_numero_fattura(
       (SELECT id FROM tmp_fattura_vuota_fri)) $$,
  '%il documento non ha righe%',
  '15) numerazione di una fattura SENZA righe: respinta');

-- ============================================================
-- 16-18 — KIT ED ESPOSIZIONE
-- vendite.fatture_righe conserva sempre TUTTE le componenti; la vista produce
-- la sintesi. Il totale non cambia al variare dell'esposizione.
-- ============================================================
CREATE TEMP TABLE tmp_fattura_kit_fri AS
SELECT pg_temp.fx_fattura_fri((SELECT stato_draft FROM tmp_refs_fri)) AS id;

-- rev 2026-10-27 (lotto 4 di D7): la riga ha il suo articolo. Senza, scattava
--   chk_fatture_righe_kit_articolo (kit_key senza articolo) e il test era verde
--   per il vincolo sbagliato: quello di coerenza non veniva mai raggiunto.
--   Trovato con la sonda (discriminante impossibile, «caught:» letto).
SELECT throws_like(
  $$ INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione, qta,
                                        prezzo_unitario, kit_key, competenza_dal, competenza_al)
     SELECT (SELECT id FROM tmp_fattura_kit_fri), 1, (SELECT articolo_id FROM tmp_refs_fri),
            'kit a meta', 1, 1, 'K-INCOMPLETO', script.fn_data_operativa(), script.fn_data_operativa() $$,
  '%chk_fatture_righe_kit_coerente%',
  '16) riga di kit con metadati a meta'': respinta dal CHECK di coerenza');

-- Kit completo: 3 componenti (2+6+9 = 17), due esposti e uno no. Ogni componente
-- e' un articolo suo (chk_fatture_righe_kit_articolo, 20261002-43).
INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione, qta,
       prezzo_unitario, iva_id, kit_key, kit_esposizione,
       kit_articolo_padre_id, kit_descrizione_padre, competenza_dal, competenza_al, kit_qta)
SELECT (SELECT id FROM tmp_fattura_kit_fri), v.nr,
       dbops.fn_pgtap_crea_articolo('PGTAP-FRI-C' || v.nr), v.descr, 1, v.prezzo,
       (SELECT iva_id FROM tmp_refs_fri), 'K-TEST', v.esposto,
       (SELECT articolo_id FROM tmp_refs_fri), 'Padre del kit di test', script.fn_data_operativa(), script.fn_data_operativa(), 1
  FROM (VALUES (1, 'comp A', 2::numeric, 'DESCRITTIVO'),
               (2, 'comp B', 6::numeric, 'DESCRITTIVO'),
               (3, 'comp C', 9::numeric, 'NASCOSTO')) AS v(nr, descr, prezzo, esposto);

SELECT is(
  (SELECT imponibile FROM vendite.vw_fattura_righe_esposte
    WHERE fattura_id = (SELECT id FROM tmp_fattura_kit_fri) AND tipo_riga = 'KIT_PADRE'),
  17.00::numeric,
  '17) la vista produce UNA riga padre col totale del kit (2+6+9)');

SELECT is(
  (SELECT count(*)::int FROM vendite.vw_fattura_righe_esposte
    WHERE fattura_id = (SELECT id FROM tmp_fattura_kit_fri)
      AND tipo_riga = 'KIT_COMPONENTE' AND imponibile IS NULL),
  2,
  '18) compaiono solo i 2 componenti esposti, senza importo');

-- ============================================================
-- 19 — VOCABOLARIO DELL'ARROTONDAMENTO
-- Il CASE inline che questa funzione sostituisce aveva un ELSE che assorbiva
-- qualunque valore ignoto in HALF_UP: un importo sbagliato che sembra giusto.
-- ============================================================
SELECT throws_like(
  $$ SELECT script.fn_arrotonda_importo(1.005, 2, 'PIPPO') $$,
  '%non riconosciuto%',
  '19) metodo di arrotondamento non riconosciuto: solleva invece di indovinare');

SELECT * FROM finish();

ROLLBACK;
