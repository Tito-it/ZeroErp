-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: I7 — anagrafiche.soggetti_titoli_iva, il suo ambito, il registro dei
--       movimenti di plafond e la primitiva di consumo.
--       Piano: docs/it/dev/work-in-progress/brief-db-be-iva-risolutore-e-regime-cliente.md
--       D5 / D10 / D12 / D13 / D15-bis · changeSet 20260829-23 … -34
-- ------------------------------------------------------------
-- Elenco test (plan 23):
--  0) riferimenti minimi presenti                    (la fixture non mente)
--  1) il vocabolario porta i quattro tipi di D10
--  2) ha_plafond e' true SOLO su INTENTO
--  3) titolo con tetto e senza plafond              -> E_TITOLO_IVA_PLAFOND_MANCANTE
--  4) titolo SENZA tetto con plafond valorizzato    -> E_TITOLO_IVA_PLAFOND_NON_AMMESSO
--  5) titolo INTENTO ben formato: si registra        (il controllo dei due sopra)
--  6) secondo titolo TUTTO, stesso tipo, periodo sovrapposto -> EXCLUDE (23P01)
--  7) ⭐ stesso, periodo NON sovrapposto -> PASSA     (il vincolo non blocca di piu')
--  8) titolo RISTRETTO + riga di ambito ARTICOLO: si registra
--  9) riga di ambito su un titolo TUTTO             -> E_TITOLO_IVA_AMBITO_NON_AMMESSO
-- 10) due titoli RISTRETTI, stesso ARTICOLO         -> E_TITOLO_IVA_AMBITO_SOVRAPPOSTO
-- 11) ⭐ due titoli RISTRETTI, livelli DIVERSI -> PASSA (D13 li risolve, non e' pareggio)
-- 12) ⭐ il lato che si dimentica: allargare il PERIODO del padre fa scattare il guard
-- 13) il registro alimenta l'accumulatore
-- 14) la nota di credito RESTITUISCE plafond        (P4)
-- 15) somma sotto zero                              -> E_TITOLO_IVA_UTILIZZATO_NEGATIVO
-- 16) forzatura senza motivo                        -> il CHECK morde
-- 17) forzatura che nomina una fattura              -> il CHECK morde
-- 18) consumo entro capienza: coperta = tutto, ordinaria = 0
-- 19) ⭐ P2: consumo oltre capienza -> si SPEZZA
-- 20) ⭐ idempotenza: la stessa fattura non consuma due volte
-- 21) titolo SENZA tetto: copre tutto e NON scrive movimenti
-- 22) consumo fuori validita'                       -> E_TITOLO_IVA_CONSUMO_FUORI_VALIDITA
--
-- Scopo:
--   I7 costruisce la SEDE dei titoli che sostituiscono l'aliquota ordinaria.
--   Il risolutore che li legge (I2) non esiste ancora: qui si prova che la sede
--   regge da sola — i vincoli, i guard, l'accumulatore e la primitiva di
--   consumo con il suo lock.
--
--   ⭐ I TRE TEST CHE CONTANO, e vale la pena sapere perche':
--     * il 7 e l'11 provano che i vincoli NON bloccano piu' del dovuto. Un
--       anti-sovrapposizione scritto largo passerebbe tutti gli altri test e
--       rifiuterebbe configurazioni legittime — due titoli su livelli diversi
--       sono il caso normale di D13, non un errore;
--     * il 12 prova il lato che un guard scritto solo sulla tabella figlia non
--       vedrebbe mai: due titoli diventano sovrapposti anche quando a cambiare
--       e' il PADRE (si allarga una data, si riattiva un titolo spento);
--     * il 19 e' P2: se la spezzatura non funziona, un plafond esaurito a meta'
--       riga produce una fattura sbagliata senza nessun errore.
--
--   ⚠️ COSA QUESTO FILE NON PROVA, e va detto:
--     * la separazione dei plafond fra DUE EMITTENTI (D10-bis) sta in
--       db/pgtap/anagrafiche/test-soggetti-titoli-iva-due-emittenti.sql: la
--       fixture deve creare un secondo emittente, e quello e' un atto di
--       configurazione che un operatore non compie;
--     * l'APPLICAZIONE del titolo su una riga di documento e' del risolutore
--       (I2) e non esiste ancora. Qui si prova che l'ambito e' registrabile e
--       coerente, non che qualcuno lo legga.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE: un fallimento a meta' lascerebbe la fixture nel database.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: il test gira come gira l'applicazione (ruolo
--   OPERATORE + RLS attiva). Serve davvero: le tre tabelle nuove hanno una
--   policy di perimetro emittente (20260829-27), e senza contesto le SELECT
--   della fixture leggerebbero zero righe.
CREATE TEMP TABLE tmp_tiva_ctx AS
SELECT script.fn_pgtap_set_contesto_operatore() AS auth_user_id;

-- ⚠️ 3. VINCOLI DIFFERITI: qui il COMMIT non arriva mai (si chiude in
--   ROLLBACK), quindi senza questa riga i DEFERRABLE non verrebbero mai
--   esercitati. Sta in testa perche' la fixture non crea soggetti ne' ruoli:
--   usa riferimenti che esistono gia', quindi non c'e' nessuna unita' di lavoro
--   a meta' strada.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(23);

-- ============================================================
-- 0) Riferimenti
-- ============================================================
-- ⚠️ L'emittente si prende DALLA WHITELIST dell'operatore che il contesto ha
--   scelto, non «il piu' recente»: le policy di 20260829-27 chiedono
--   fn_scope_ef_whitelist, e un emittente fuori scope farebbe fallire ogni
--   INSERT della fixture con un errore che sembra un difetto del guard.
-- ⚠️ Ogni LIMIT 1 ha il suo ORDER BY: senza, quale riga esca dipende dal piano
--   del planner e il test passerebbe a giorni alterni.
CREATE TEMP TABLE tmp_tiva_costanti AS
SELECT 'pgtap_titoli_iva'::text AS test_scope;

CREATE TEMP TABLE tmp_tiva_refs AS
SELECT
    (SELECT uef.emittente_fiscale_id
       FROM config.user_emittenti_fiscali uef
      WHERE uef.auth_user_id = (SELECT auth_user_id FROM tmp_tiva_ctx)
      ORDER BY uef.emittente_fiscale_id
      LIMIT 1)                                              AS emittente_fiscale_id,
    (SELECT s.id FROM anagrafiche.soggetti s
      WHERE s.attivo IS TRUE ORDER BY s.id LIMIT 1)         AS soggetto_id,
    (SELECT i.id FROM config.iva i
      WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)         AS iva_id,
    (SELECT a.id FROM catalogo.articoli a
      WHERE a.attivo IS TRUE ORDER BY a.id LIMIT 1)         AS articolo_id,
    (SELECT g.id FROM vendite.articoli_gruppi g
      WHERE g.attivo IS TRUE ORDER BY g.id LIMIT 1)         AS gruppo_voce_id,
    (SELECT t.id FROM config.tipi_titolo_iva t
      WHERE t.codice_interno = 'INTENTO')                   AS tipo_intento_id,
    (SELECT t.id FROM config.tipi_titolo_iva t
      WHERE t.codice_interno = 'AGEVOLATA_104')             AS tipo_agevolata_id;

SELECT ok(
    (SELECT emittente_fiscale_id IS NOT NULL
        AND soggetto_id     IS NOT NULL
        AND iva_id          IS NOT NULL
        AND articolo_id     IS NOT NULL
        AND gruppo_voce_id  IS NOT NULL
        AND tipo_intento_id IS NOT NULL
        AND tipo_agevolata_id IS NOT NULL
       FROM tmp_tiva_refs),
    'Riferimenti minimi presenti (emittente in whitelist, soggetto, IVA, articolo, gruppo, tipi)'
  );

-- ============================================================
-- 1-2) Il vocabolario di D10
-- ============================================================
-- ⚠️ set_eq e non «esiste INTENTO»: cosi' un quinto tipo seminato domani senza
--   pensarci fa rosso qui, invece di entrare in silenzio nel dominio.
SELECT set_eq(
    $$SELECT codice_interno FROM config.tipi_titolo_iva$$,
    $$VALUES ('INTENTO'), ('USO_INDUSTRIALE'), ('AGEVOLATA_104'), ('COOPERATIVA')$$,
    'Il vocabolario porta i quattro tipi di titolo nominati in D10'
  );

-- ⭐ E' la riga che porta l'informazione del vocabolario: solo la dichiarazione
--   d'intento ha un contatore che si consuma. Se un giorno un secondo tipo
--   nascesse con ha_plafond = true, il registro e la primitiva di consumo
--   varrebbero anche per lui — e chi lo semina deve accorgersene qui.
SELECT set_eq(
    $$SELECT codice_interno FROM config.tipi_titolo_iva WHERE ha_plafond IS TRUE$$,
    $$VALUES ('INTENTO')$$,
    'Ha un tetto che si consuma SOLO la dichiarazione d''intento'
  );

-- ============================================================
-- 3-4) Il guard di coerenza del plafond, sui DUE versi
-- ============================================================
-- ⚠️ SQLSTATE esplicito: throws_ok(sql, NULL, NULL, ...) accetterebbe QUALUNQUE
--   errore, compreso un permesso negato che non c'entra niente. P0001 e'
--   l'errore di dominio di script.fn_log_and_raise_error.
SELECT throws_ok(
    format($$
      INSERT INTO anagrafiche.soggetti_titoli_iva
          (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
           ambito, valido_dal, valido_al, protocollo)
      VALUES (%L::uuid, %s, %s, %s, 'TUTTO', DATE '2026-01-01', DATE '2026-12-31', 'PGTAP-3')
    $$, (SELECT soggetto_id FROM tmp_tiva_refs),
        (SELECT emittente_fiscale_id FROM tmp_tiva_refs),
        (SELECT tipo_intento_id FROM tmp_tiva_refs),
        (SELECT iva_id FROM tmp_tiva_refs)),
    'P0001',
    NULL,
    'INTENTO senza plafond: il guard rifiuta (il tetto e'' la ragione per cui quel tipo esiste)'
  );

-- ⭐ Il verso che si dimentica: un tetto su un titolo che non ne ha e' un numero
--   che nessuno consuma, e chi lo legge crede che quel titolo abbia un limite.
SELECT throws_ok(
    format($$
      INSERT INTO anagrafiche.soggetti_titoli_iva
          (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
           ambito, valido_dal, valido_al, plafond)
      VALUES (%L::uuid, %s, %s, %s, 'TUTTO', DATE '2026-01-01', DATE '2026-12-31', 5000.00)
    $$, (SELECT soggetto_id FROM tmp_tiva_refs),
        (SELECT emittente_fiscale_id FROM tmp_tiva_refs),
        (SELECT tipo_agevolata_id FROM tmp_tiva_refs),
        (SELECT iva_id FROM tmp_tiva_refs)),
    'P0001',
    NULL,
    'AGEVOLATA_104 con un plafond: il guard rifiuta anche il verso opposto'
  );

-- ============================================================
-- 5) Il titolo ben formato si registra — ed e' il CONTROLLO dei due sopra
-- ============================================================
-- ⚠️ Senza questo, un rosso dei test 3-4 potrebbe venire da una fixture storta
--   (un permesso, un riferimento sbagliato) invece che dal guard.
CREATE TEMP TABLE tmp_tiva_intento AS
WITH ins AS (
  INSERT INTO anagrafiche.soggetti_titoli_iva
      (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
       ambito, valido_dal, valido_al, protocollo, data_ricezione, plafond, meta)
  SELECT r.soggetto_id, r.emittente_fiscale_id, r.tipo_intento_id, r.iva_id,
         'TUTTO', DATE '2026-01-01', DATE '2026-12-31',
         'PGTAP-PROT-1', DATE '2025-12-20', 1000.00,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_tiva_costanti))
    FROM tmp_tiva_refs r
  RETURNING id, plafond, imponibile_utilizzato
)
SELECT * FROM ins;

SELECT is(
    (SELECT imponibile_utilizzato FROM tmp_tiva_intento),
    0::numeric,
    'Il titolo INTENTO ben formato si registra, e nasce con zero plafond consumato'
  );

-- ============================================================
-- 6-7) L'EXCLUDE sui titoli che valgono per TUTTO
-- ============================================================
-- 23P01 = exclusion_violation. E' un vincolo vero, non un guard: si vede dallo
-- SQLSTATE, che non e' P0001.
SELECT throws_ok(
    format($$
      INSERT INTO anagrafiche.soggetti_titoli_iva
          (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
           ambito, valido_dal, valido_al, plafond)
      VALUES (%L::uuid, %s, %s, %s, 'TUTTO', DATE '2026-06-01', DATE '2027-05-31', 2000.00)
    $$, (SELECT soggetto_id FROM tmp_tiva_refs),
        (SELECT emittente_fiscale_id FROM tmp_tiva_refs),
        (SELECT tipo_intento_id FROM tmp_tiva_refs),
        (SELECT iva_id FROM tmp_tiva_refs)),
    '23P01',
    NULL,
    'Due titoli TUTTO dello stesso tipo con periodi che si toccano: EXCLUDE'
  );

-- ⭐ Il lato che nessuno prova: che il vincolo non blocchi PIU' del dovuto. Lo
--   stesso titolo, su un periodo che NON si sovrappone, e' il rinnovo annuale —
--   il caso piu' normale che esista.
SELECT lives_ok(
    format($$
      INSERT INTO anagrafiche.soggetti_titoli_iva
          (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
           ambito, valido_dal, valido_al, plafond)
      VALUES (%L::uuid, %s, %s, %s, 'TUTTO', DATE '2027-01-01', DATE '2027-12-31', 2000.00)
    $$, (SELECT soggetto_id FROM tmp_tiva_refs),
        (SELECT emittente_fiscale_id FROM tmp_tiva_refs),
        (SELECT tipo_intento_id FROM tmp_tiva_refs),
        (SELECT iva_id FROM tmp_tiva_refs)),
    'Lo stesso titolo su un periodo che NON si sovrappone passa: e'' il rinnovo annuale'
  );

-- ============================================================
-- 8-9) L'ambito: si registra, e non convive con «vale per tutto»
-- ============================================================
CREATE TEMP TABLE tmp_tiva_ristretto AS
WITH ins AS (
  INSERT INTO anagrafiche.soggetti_titoli_iva
      (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
       ambito, valido_dal, valido_al, riferimento)
  SELECT r.soggetto_id, r.emittente_fiscale_id, r.tipo_agevolata_id, r.iva_id,
         'RISTRETTO', DATE '2026-01-01', DATE '2026-12-31', 'PGTAP-CERT-104'
    FROM tmp_tiva_refs r
  RETURNING id
)
SELECT * FROM ins;

INSERT INTO anagrafiche.soggetti_titoli_iva_ambiti (titolo_iva_id, livello, articolo_id)
SELECT (SELECT id FROM tmp_tiva_ristretto), 'ARTICOLO', r.articolo_id FROM tmp_tiva_refs r;

SELECT is(
    (SELECT count(*)::int FROM anagrafiche.soggetti_titoli_iva_ambiti
      WHERE titolo_iva_id = (SELECT id FROM tmp_tiva_ristretto)),
    1,
    'Un titolo RISTRETTO accetta la sua riga di ambito su un ARTICOLO'
  );

-- Il titolo del test 5 vale per TUTTO: un ambito li' sopra direbbe due cose
-- opposte, e il risolutore ne leggerebbe una sola.
SELECT throws_ok(
    format($$
      INSERT INTO anagrafiche.soggetti_titoli_iva_ambiti (titolo_iva_id, livello, articolo_id)
      VALUES (%s, 'ARTICOLO', %L::uuid)
    $$, (SELECT id FROM tmp_tiva_intento),
        (SELECT articolo_id FROM tmp_tiva_refs)),
    'P0001',
    NULL,
    'Una riga di ambito su un titolo che vale per TUTTO: il guard rifiuta'
  );

-- ============================================================
-- 10-11) Il PAREGGIO, e cio' che pareggio non e'
-- ============================================================
CREATE TEMP TABLE tmp_tiva_ristretto_2 AS
WITH ins AS (
  INSERT INTO anagrafiche.soggetti_titoli_iva
      (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
       ambito, valido_dal, valido_al, riferimento)
  SELECT r.soggetto_id, r.emittente_fiscale_id, r.tipo_agevolata_id, r.iva_id,
         'RISTRETTO', DATE '2026-03-01', DATE '2026-09-30', 'PGTAP-CERT-104-BIS'
    FROM tmp_tiva_refs r
  RETURNING id
)
SELECT * FROM ins;

-- Stesso soggetto, stesso emittente, stesso tipo, periodo sovrapposto e
-- STESSO articolo: nessuno dei due e' piu' specifico. D13 dice che si solleva.
SELECT throws_ok(
    format($$
      INSERT INTO anagrafiche.soggetti_titoli_iva_ambiti (titolo_iva_id, livello, articolo_id)
      VALUES (%s, 'ARTICOLO', %L::uuid)
    $$, (SELECT id FROM tmp_tiva_ristretto_2),
        (SELECT articolo_id FROM tmp_tiva_refs)),
    'P0001',
    NULL,
    'Due titoli ristretti sullo STESSO articolo e periodo: pareggio, si solleva'
  );

-- ⭐ E qui il lato opposto, che e' il caso NORMALE di D13: livelli diversi non
--   sono un pareggio — articolo > categoria di merce > tutto. Un guard scritto
--   largo passerebbe il test 10 e rifiuterebbe questa, che e' legittima.
SELECT lives_ok(
    format($$
      INSERT INTO anagrafiche.soggetti_titoli_iva_ambiti (titolo_iva_id, livello, gruppo_voce_id)
      VALUES (%s, 'GRUPPO_VOCE', %s)
    $$, (SELECT id FROM tmp_tiva_ristretto_2),
        (SELECT gruppo_voce_id FROM tmp_tiva_refs)),
    'Due titoli ristretti su LIVELLI diversi convivono: li risolve D13, non e'' un pareggio'
  );

-- ============================================================
-- 12) ⭐ Il lato che si dimentica: a cambiare e' il PADRE
-- ============================================================
-- Il titolo 2 copre oggi un GRUPPO, il titolo 1 un ARTICOLO: convivono. Ma se
-- si desse al titolo 2 anche quell'articolo... lo ferma il test 10. Qui invece
-- si sposta il PERIODO di un terzo titolo fino a sovrapporsi, senza toccare
-- nessuna riga di ambito: e' il caso che un guard scritto solo sulla tabella
-- figlia non vedrebbe MAI.
CREATE TEMP TABLE tmp_tiva_ristretto_3 AS
WITH ins AS (
  INSERT INTO anagrafiche.soggetti_titoli_iva
      (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
       ambito, valido_dal, valido_al, riferimento)
  SELECT r.soggetto_id, r.emittente_fiscale_id, r.tipo_agevolata_id, r.iva_id,
         'RISTRETTO', DATE '2028-01-01', DATE '2028-12-31', 'PGTAP-CERT-104-TER'
    FROM tmp_tiva_refs r
  RETURNING id
)
SELECT * FROM ins;

-- Stesso articolo del titolo 1, ma in un periodo lontano: legittimo.
INSERT INTO anagrafiche.soggetti_titoli_iva_ambiti (titolo_iva_id, livello, articolo_id)
SELECT (SELECT id FROM tmp_tiva_ristretto_3), 'ARTICOLO', r.articolo_id FROM tmp_tiva_refs r;

SELECT throws_ok(
    format($$
      UPDATE anagrafiche.soggetti_titoli_iva
         SET valido_dal = DATE '2026-01-01'
       WHERE id = %s
    $$, (SELECT id FROM tmp_tiva_ristretto_3)),
    'P0001',
    NULL,
    'Allargare il PERIODO del padre fino a sovrapporsi: il guard scatta anche cosi'''
  );

-- ============================================================
-- 13-15) Il registro e l'accumulatore (D5)
-- ============================================================
-- Fixture: un registro di fatturazione e una fattura, che servono perche' un
-- movimento di tipo FATTURA la nomina per forza (CHECK chk_stiva_movimenti_documento).
CREATE TEMP TABLE tmp_tiva_ba AS
WITH cfg AS (
  SELECT efu.emittente_soggetto_ruolo_id, efu.utility_id
    FROM anagrafiche.emittenti_fiscali_utilities efu
   WHERE efu.attivo IS TRUE
     AND EXISTS (SELECT 1 FROM anagrafiche.billing_account ba WHERE ba.utility_id = efu.utility_id)
   ORDER BY efu.emittente_soggetto_ruolo_id, efu.utility_id
   LIMIT 1
)
SELECT (SELECT emittente_soggetto_ruolo_id FROM cfg) AS emittente_soggetto_ruolo_id,
       (SELECT utility_id FROM cfg)                  AS utility_id,
       (SELECT ba.id FROM anagrafiche.billing_account ba
         WHERE ba.utility_id = (SELECT utility_id FROM cfg)
         ORDER BY ba.data_insert DESC NULLS LAST, ba.id DESC LIMIT 1) AS billing_account_id,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DRAFT' ORDER BY id LIMIT 1) AS stato_draft_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id;

CREATE TEMP TABLE tmp_tiva_fattura AS
WITH reg AS (
  -- ⛔ emittente_soggetto_ruolo_id e' NOT NULL dal 2026-08-30 (C1-2,
  --   20260830-11), e dev'essere lo STESSO delle fatture di questo file:
  --   vendite.trgfn_fatture_guard_registro_emittente rifiuta un documento
  --   sul registro di un altro emittente (C1-3, 20260830-10).
  INSERT INTO vendite.registri_fatturazione (codice, descrizione, reset_policy, attivo,
         emittente_soggetto_ruolo_id, meta)
  SELECT left('REGTIVA_' || (SELECT test_scope FROM tmp_tiva_costanti), 16),
         'Registro test titoli IVA', 'ANNUALE', true,
         (SELECT emittente_soggetto_ruolo_id FROM tmp_tiva_ba),
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_tiva_costanti))
  RETURNING id
), ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, stato_doc_fiscale_id, valuta_id, utility_id, meta)
  SELECT (SELECT id FROM reg), DATE '2026-06-15',
         b.emittente_soggetto_ruolo_id, b.billing_account_id,
         b.tipo_doc_fiscale_id, b.stato_draft_id, b.valuta_id, b.utility_id,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_tiva_costanti))
    FROM tmp_tiva_ba b
  RETURNING id
)
SELECT id FROM ins;

INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti
    (titolo_iva_id, tipo_movimento, imponibile, data_movimento, fattura_id)
SELECT (SELECT id FROM tmp_tiva_intento), 'FATTURA', 400.00, DATE '2026-06-15',
       (SELECT id FROM tmp_tiva_fattura);

SELECT is(
    (SELECT imponibile_utilizzato FROM anagrafiche.soggetti_titoli_iva
      WHERE id = (SELECT id FROM tmp_tiva_intento)),
    400.00::numeric,
    'Un movimento di FATTURA alimenta imponibile_utilizzato: la colonna e'' la somma del registro'
  );

-- P4: la nota di credito restituisce plafond, e lo fa in ARITMETICA — nessun
-- caso speciale, e' un movimento con il segno opposto.
INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti
    (titolo_iva_id, tipo_movimento, imponibile, data_movimento, fattura_id)
SELECT (SELECT id FROM tmp_tiva_intento), 'NOTA_CREDITO', -150.00, DATE '2026-07-01',
       (SELECT id FROM tmp_tiva_fattura);

SELECT is(
    (SELECT imponibile_utilizzato FROM anagrafiche.soggetti_titoli_iva
      WHERE id = (SELECT id FROM tmp_tiva_intento)),
    250.00::numeric,
    'La nota di credito RESTITUISCE plafond (P4), per somma algebrica'
  );

SELECT throws_ok(
    format($$
      INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti
          (titolo_iva_id, tipo_movimento, imponibile, data_movimento, motivo)
      VALUES (%s, 'FORZATURA', -1000.00, DATE '2026-07-02', 'prova di sfondamento al contrario')
    $$, (SELECT id FROM tmp_tiva_intento)),
    'P0001',
    NULL,
    'La somma del registro non puo'' andare sotto zero: l''accumulatore rifiuta'
  );

-- ============================================================
-- 16-17) I due CHECK che tengono onesta la forzatura
-- ============================================================
-- 23514 = check_violation: qui il presidio e' un vincolo, non un guard.
SELECT throws_ok(
    format($$
      INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti
          (titolo_iva_id, tipo_movimento, imponibile, data_movimento)
      VALUES (%s, 'FORZATURA', 10.00, DATE '2026-07-03')
    $$, (SELECT id FROM tmp_tiva_intento)),
    '23514',
    NULL,
    'Una forzatura senza motivo non si scrive: senza il perche'' e'' un numero sovrascritto'
  );

SELECT throws_ok(
    format($$
      INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti
          (titolo_iva_id, tipo_movimento, imponibile, data_movimento, fattura_id, motivo)
      VALUES (%s, 'FORZATURA', 10.00, DATE '2026-07-03', %s, 'con una fattura, che non deve passare')
    $$, (SELECT id FROM tmp_tiva_intento), (SELECT id FROM tmp_tiva_fattura)),
    '23514',
    NULL,
    'Una forzatura non nomina una fattura: altrimenti sarebbe la scorciatoia per saltare la primitiva'
  );

-- ============================================================
-- 18-20) La primitiva di consumo: capienza, spezzatura (P2), idempotenza
-- ============================================================
-- Titolo pulito per i test di consumo: plafond 1000, niente movimenti.
CREATE TEMP TABLE tmp_tiva_consumo AS
WITH ins AS (
  INSERT INTO anagrafiche.soggetti_titoli_iva
      (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
       ambito, valido_dal, valido_al, protocollo, plafond)
  SELECT r.soggetto_id, r.emittente_fiscale_id, r.tipo_intento_id, r.iva_id,
         'TUTTO', DATE '2029-01-01', DATE '2029-12-31', 'PGTAP-PROT-CONSUMO', 1000.00
    FROM tmp_tiva_refs r
  RETURNING id
)
SELECT * FROM ins;

SELECT is(
    (SELECT (c.quota_coperta, c.quota_ordinaria)::text
       FROM anagrafiche.fn_consuma_plafond_titolo_iva(
                (SELECT id FROM tmp_tiva_consumo),
                (SELECT id FROM tmp_tiva_fattura),
                300.00, DATE '2029-03-01') c),
    '(300.00,0.00)',
    'Consumo entro capienza: il titolo copre tutto e la quota ordinaria e'' zero'
  );

-- ⭐ P2: il plafond finisce a meta' riga. Residuo 700, si chiedono 1000 ->
--   700 coperti dal titolo, 300 tornano all'aliquota ordinaria. Senza questa
--   spezzatura una fattura sbagliata non darebbe nessun errore.
-- ⚠️ Fattura diversa dalla precedente? No: e' la RIGA a cambiare, e la UNIQUE
--   parziale distingue (titolo, tipo, fattura, riga). Qui si passa una riga
--   nulla su un secondo consumo, quindi si usa il ramo idempotente — percio'
--   il secondo consumo si fa su un titolo suo.
CREATE TEMP TABLE tmp_tiva_consumo_2 AS
WITH ins AS (
  INSERT INTO anagrafiche.soggetti_titoli_iva
      (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
       ambito, valido_dal, valido_al, protocollo, plafond)
  SELECT r.soggetto_id, r.emittente_fiscale_id, r.tipo_intento_id, r.iva_id,
         'TUTTO', DATE '2030-01-01', DATE '2030-12-31', 'PGTAP-PROT-SPEZZA', 700.00
    FROM tmp_tiva_refs r
  RETURNING id
)
SELECT * FROM ins;

SELECT is(
    (SELECT (c.quota_coperta, c.quota_ordinaria)::text
       FROM anagrafiche.fn_consuma_plafond_titolo_iva(
                (SELECT id FROM tmp_tiva_consumo_2),
                (SELECT id FROM tmp_tiva_fattura),
                1000.00, DATE '2030-03-01') c),
    '(700.00,300.00)',
    'P2: plafond esaurito a meta'' riga -> 700 non imponibili, 300 ad aliquota ordinaria'
  );

-- ⭐ Idempotenza: la stessa fattura, sullo stesso titolo, non consuma due volte.
--   Si guarda il NUMERO di movimenti e non solo la ripartizione: una funzione
--   che ritornasse il valore giusto scrivendo una seconda riga passerebbe un
--   test scritto sulla sola ripartizione.
SELECT is(
    (SELECT count(*)::int FROM anagrafiche.fn_consuma_plafond_titolo_iva(
                (SELECT id FROM tmp_tiva_consumo_2),
                (SELECT id FROM tmp_tiva_fattura),
                1000.00, DATE '2030-03-01') c
      WHERE c.quota_coperta = 700.00)
    + (SELECT count(*)::int FROM anagrafiche.soggetti_titoli_iva_movimenti m
        WHERE m.titolo_iva_id = (SELECT id FROM tmp_tiva_consumo_2)),
    2,
    'Idempotenza: il secondo consumo ritorna la stessa quota e NON scrive un secondo movimento'
  );

-- ============================================================
-- 21-22) I due rami che restano
-- ============================================================
CREATE TEMP TABLE tmp_tiva_senza_tetto AS
WITH ins AS (
  INSERT INTO anagrafiche.soggetti_titoli_iva
      (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
       ambito, valido_dal, valido_al, riferimento)
  SELECT r.soggetto_id, r.emittente_fiscale_id, r.tipo_agevolata_id, r.iva_id,
         'TUTTO', DATE '2031-01-01', DATE '2031-12-31', 'PGTAP-SENZA-TETTO'
    FROM tmp_tiva_refs r
  RETURNING id
)
SELECT * FROM ins;

SELECT is(
    (SELECT (c.quota_coperta, c.quota_ordinaria)::text
       FROM anagrafiche.fn_consuma_plafond_titolo_iva(
                (SELECT id FROM tmp_tiva_senza_tetto),
                (SELECT id FROM tmp_tiva_fattura),
                5000.00, DATE '2031-03-01') c)
    || ' mov=' ||
    (SELECT count(*)::text FROM anagrafiche.soggetti_titoli_iva_movimenti m
      WHERE m.titolo_iva_id = (SELECT id FROM tmp_tiva_senza_tetto)),
    '(5000.00,0.00) mov=0',
    'Un titolo SENZA tetto copre tutto e non scrive nessun movimento: il registro non si allunga a vuoto'
  );

-- ⭐ Consumare su un titolo scaduto e' un difetto di chi ha risolto, non un dato
--   da correggere: e' TECNICO. Ma senza cancello sarebbe un plafond consumato da
--   una fattura che quel titolo non copre piu' — invisibile.
SELECT throws_ok(
    format($$
      SELECT * FROM anagrafiche.fn_consuma_plafond_titolo_iva(%s, %s, 100.00, DATE '2035-01-01')
    $$, (SELECT id FROM tmp_tiva_consumo), (SELECT id FROM tmp_tiva_fattura)),
    'P0001',
    NULL,
    'Consumo a una data fuori dalla validita'' del titolo: si rifiuta'
  );

SELECT * FROM finish();
ROLLBACK;
