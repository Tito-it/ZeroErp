-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: I7 — anagrafiche.soggetti_titoli_iva, il suo ambito, il registro dei
--       movimenti di plafond e la primitiva di consumo.
--       Piano: brief-db-be-iva-risolutore-e-regime-cliente.md
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

-- ⭐ rev 2026-10-10 (brief-db-dati-fiscali-e-societari-del-soggetto, Parte D):
--   il «tipo senza plafond» della fixture e' USO_INDUSTRIALE, non piu'
--   AGEVOLATA_104. Da trgfn_soggetti_titoli_iva_guard_tipo_soggetto (20261010-92)
--   un titolo vigente deve essere ammesso dalla natura del titolare, e
--   l'agevolazione L. 104 spetta al solo privato: sul cliente della fixture (una
--   societa' di capitali) sarebbe rifiutata, e i rifiuti attesi dal guard di
--   coerenza (P0001) passerebbero per il motivo sbagliato.

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

-- ⭐ 2026-09-23: il soggetto del titolo e' il CLIENTE del mondo, non «il primo
--   soggetto attivo». Su un database ricostruito quel primo soggetto e'
--   l'azienda stessa del contesto — una lettera d'intento dell'emittente a se'
--   stesso — e la fattura dei test 13-15 era di un altro cliente ancora,
--   pescato. Ora titolo e fattura parlano dello stesso cliente.
CREATE TEMP TABLE tmp_tiva_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('titoli IVA');

CREATE TEMP TABLE tmp_tiva_refs AS
SELECT
    (SELECT uef.emittente_fiscale_id
       FROM config.user_emittenti_fiscali uef
      WHERE uef.auth_user_id = (SELECT auth_user_id FROM tmp_tiva_ctx)
      ORDER BY uef.emittente_fiscale_id
      LIMIT 1)                                              AS emittente_fiscale_id,
    (SELECT m.cliente_soggetto_id FROM tmp_tiva_mondo m)  AS soggetto_id,
    (SELECT i.id FROM config.iva i
      WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)         AS iva_id,
    (SELECT a.id FROM catalogo.articoli a
      WHERE a.attivo IS TRUE ORDER BY a.id LIMIT 1)         AS articolo_id,
    (SELECT g.id FROM vendite.articoli_gruppi g
      WHERE g.attivo IS TRUE ORDER BY g.id LIMIT 1)         AS gruppo_voce_id,
    (SELECT t.id FROM config.tipi_titolo_iva t
      WHERE t.codice_interno = 'INTENTO')                   AS tipo_intento_id,
    (SELECT t.id FROM config.tipi_titolo_iva t
      WHERE t.codice_interno = 'USO_INDUSTRIALE')             AS tipo_senza_plafond_id;

SELECT ok(
    (SELECT emittente_fiscale_id IS NOT NULL
        AND soggetto_id     IS NOT NULL
        AND iva_id          IS NOT NULL
        AND articolo_id     IS NOT NULL
        AND gruppo_voce_id  IS NOT NULL
        AND tipo_intento_id IS NOT NULL
        AND tipo_senza_plafond_id IS NOT NULL
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
        (SELECT tipo_senza_plafond_id FROM tmp_tiva_refs),
        (SELECT iva_id FROM tmp_tiva_refs)),
    'P0001',
    NULL,
    'USO_INDUSTRIALE con un plafond: il guard rifiuta anche il verso opposto'
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
  SELECT r.soggetto_id, r.emittente_fiscale_id, r.tipo_senza_plafond_id, r.iva_id,
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
  SELECT r.soggetto_id, r.emittente_fiscale_id, r.tipo_senza_plafond_id, r.iva_id,
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
  SELECT r.soggetto_id, r.emittente_fiscale_id, r.tipo_senza_plafond_id, r.iva_id,
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
-- ⛔ 2026-09-23: la fattura era scritta a mano su mattoni PESCATI — «la prima
--   coppia (emittente, utility) configurata con un BA», «il BA piu' recente» —
--   e il registro nasceva con emittente NULL su un database ricostruito, dove
--   nessuna delle due cose c'e'. Ora la costruisce dbops.fn_pgtap_crea_fattura,
--   sul BA del cliente del titolo (terzo parametro): registro coerente con
--   l'azienda di chi agisce, coppia configurata, valuta risolta.
CREATE TEMP TABLE tmp_tiva_fattura AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
           'titoli IVA', 'DRAFT',
           (SELECT m.billing_account_id FROM tmp_tiva_mondo m)) f;

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
-- 18-20) La madre di consumo: capienza, spezzatura (P2), idempotenza
-- ============================================================
-- ⚠️ Dal 2026-10-04 (20261004-05/-06, brief-db-bom-flag-quantita-e-kit-in-
--   fattura §13) la forma a una riga e' ritirata e la madre vuole righe vere
--   della fattura (l'imponibile passato deve essere quello della riga): una
--   riga per importo (300, 1000, 5000). Prima passavano un importo e una riga
--   NULL.
-- Scopo: una riga della fattura con l'imponibile dato (qta 1).
CREATE OR REPLACE FUNCTION pg_temp.fx_tiva_riga(p_nr integer, p_imp numeric)
RETURNS bigint LANGUAGE sql AS $fx$
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione, uom_id,
         qta, prezzo_unitario, iva_id, competenza_dal, competenza_al)
  SELECT (SELECT id FROM tmp_tiva_fattura), p_nr, r.articolo_id, 'Riga ' || p_nr,
         (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1),
         1, p_imp, r.iva_id, script.fn_data_operativa(), script.fn_data_operativa()
    FROM tmp_tiva_refs r
  RETURNING id;
$fx$;

CREATE TEMP TABLE tmp_tiva_righe AS
SELECT pg_temp.fx_tiva_riga(1, 300.00)  AS r300,
       pg_temp.fx_tiva_riga(2, 1000.00) AS r1000,
       pg_temp.fx_tiva_riga(3, 5000.00) AS r5000;

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
       FROM anagrafiche.fn_consuma_plafond_titolo_iva_righe(
                (SELECT id FROM tmp_tiva_consumo),
                (SELECT id FROM tmp_tiva_fattura),
                ARRAY[(SELECT r300 FROM tmp_tiva_righe)], ARRAY[300.00], DATE '2029-03-01') c),
    '(300.00,0.00)',
    'Consumo entro capienza: il titolo copre tutto e la quota ordinaria e'' zero'
  );

-- ⭐ P2: il plafond finisce a meta' riga. Residuo 700, si chiedono 1000 ->
--   700 coperti dal titolo, 300 tornano all'aliquota ordinaria. Senza questa
--   spezzatura una fattura sbagliata non darebbe nessun errore.
-- ⚠️ Un titolo suo: l'idempotenza e' per (titolo, fattura), e sul titolo del
--   test 18 la fattura ha gia' consumato.
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
       FROM anagrafiche.fn_consuma_plafond_titolo_iva_righe(
                (SELECT id FROM tmp_tiva_consumo_2),
                (SELECT id FROM tmp_tiva_fattura),
                ARRAY[(SELECT r1000 FROM tmp_tiva_righe)], ARRAY[1000.00], DATE '2030-03-01') c),
    '(700.00,300.00)',
    'P2: plafond esaurito a meta'' riga -> 700 non imponibili, 300 ad aliquota ordinaria'
  );

-- ⭐ Idempotenza: la stessa fattura, sullo stesso titolo, non consuma due volte.
--   Si guarda il NUMERO di movimenti e non solo la ripartizione: una funzione
--   che ritornasse il valore giusto scrivendo una seconda riga passerebbe un
--   test scritto sulla sola ripartizione.
SELECT is(
    (SELECT count(*)::int FROM anagrafiche.fn_consuma_plafond_titolo_iva_righe(
                (SELECT id FROM tmp_tiva_consumo_2),
                (SELECT id FROM tmp_tiva_fattura),
                ARRAY[(SELECT r1000 FROM tmp_tiva_righe)], ARRAY[1000.00], DATE '2030-03-01') c
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
  SELECT r.soggetto_id, r.emittente_fiscale_id, r.tipo_senza_plafond_id, r.iva_id,
         'TUTTO', DATE '2031-01-01', DATE '2031-12-31', 'PGTAP-SENZA-TETTO'
    FROM tmp_tiva_refs r
  RETURNING id
)
SELECT * FROM ins;

SELECT is(
    (SELECT (c.quota_coperta, c.quota_ordinaria)::text
       FROM anagrafiche.fn_consuma_plafond_titolo_iva_righe(
                (SELECT id FROM tmp_tiva_senza_tetto),
                (SELECT id FROM tmp_tiva_fattura),
                ARRAY[(SELECT r5000 FROM tmp_tiva_righe)], ARRAY[5000.00], DATE '2031-03-01') c)
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
      SELECT * FROM anagrafiche.fn_consuma_plafond_titolo_iva_righe(%s, %s, ARRAY[%s]::bigint[], ARRAY[300.00]::numeric[], DATE '2035-01-01')
    $$, (SELECT id FROM tmp_tiva_consumo), (SELECT id FROM tmp_tiva_fattura),
        (SELECT r300 FROM tmp_tiva_righe)),
    'P0001',
    NULL,
    'Consumo a una data fuori dalla validita'' del titolo: si rifiuta'
  );

SELECT * FROM finish();
ROLLBACK;
