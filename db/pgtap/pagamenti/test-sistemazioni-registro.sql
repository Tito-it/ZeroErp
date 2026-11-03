-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il REGISTRO delle sistemazioni — la tabella e i suoi guard
--
-- Elenco test (plan 14):
--  1) Riferimenti minimi presenti
--  2) La tabella si chiama `sistemazioni`, e `compensazioni` non esiste piu'
--  3) ⭐ E nessun oggetto suo nomina ancora il vecchio nome
--  4) 🔴 Su `vendite_contabili` non restano ne' colonna, ne' unico, ne' FK
--  5) Un RIMBORSO che indica una fattura di destinazione e' rifiutato
--  6) Una COMPENSAZIONE senza destinazione e' rifiutata
--  7) Una destinazione uguale all'origine e' rifiutata
--  8) Un RIPORTO senza motivo e' rifiutato
--  9) ⭐ Due documenti di clienti diversi sono rifiutati, e la frase lo dice
-- 10) Un emittente dichiarato diverso da quello della fattura e' rifiutato
-- 11) Un atto non nasce gia' CONFERMATO
-- 12) 🔴 Una COMPENSAZIONE che registra su una distinta fuori dal centro delle compensazioni e' rifiutata
-- 13) ...e l'atto e' rimasto in BOZZA
-- 14) Assert finale cleanup
--
-- Scopo:
--  - collaudare S4-1 e S4-2: il guscio `compensazioni` e' diventato il registro
--    `sistemazioni`, e il legame con la contabile ha cambiato verso (D15-e);
--  - ⭐ il test 3 e' quello che si dimentica: rinominare una tabella e lasciarle
--    addosso la chiave primaria, la sequenza e i trigger col nome vecchio non
--    da' nessun errore — ma le automazioni di `pagamenti` lavorano per pattern
--    (`*all`), quindi alla prima passata di `ci_apply` ne genererebbero altri
--    col nome nuovo ACCANTO a quelli vecchi. Due trigger di audit sulla stessa
--    tabella scrivono due volte, in silenzio;
--  - ⭐ il test 9 presidia la regola che rende sensata la compensazione (D15-b):
--    mettere insieme due documenti DI UN SOLO CLIENTE. E si asserisce con
--    `throws_like` sulla FRASE, non solo sullo SQLSTATE: la domanda «di chi
--    sono?» si fa fuori dalla row security, e un guard che la facesse sotto
--    direbbe «di un altro cliente» anche quando il cliente e' lo stesso.
--  - 🔴 il test 12 presidia E_CENTRO_NON_ABILITATO_COMPENSAZIONE: la distinta
--    di una compensazione sta sul centro dedicato (is_compensazione), perche'
--    quel denaro non entra da nessuna banca. La madre la crea li', ma il guard
--    tiene la regola per ogni scrittore: si prova con un UPDATE scritto a
--    mano, nell'istruzione unica con cui un atto diventa CONFERMATO.
--
-- Piano: brief-db-posting-e-abbinamento-rata.md
--        §2.3-bis S4-1/S4-2 · Decisioni: brief madre D15-b, D15-c, D15-e · lotto 7
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- Fixture — due fatture dello stesso cliente e una di un altro
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_sistemazioni_registro'::text AS test_scope;

-- ⛔ LE TRE FATTURE SI COSTRUISCONO (2026-09-23). La fixture CERCAVA nella
--   popolazione «un cliente che abbia almeno due fatture, e un altro cliente
--   con almeno una»: su un database ricostruito `vendite.fatture` e' a zero e
--   tutte le colonne uscivano NULL — otto asserzioni rosse che parlavano
--   dell'assenza di dati, non del registro delle sistemazioni.
-- ⭐ Costruirle dice anche una cosa in piu': la coppia e' la stessa PER
--   COSTRUZIONE (terzo parametro del BB), non per una GROUP BY che spera di
--   trovarla.
CREATE TEMP TABLE tmp_fatt_a AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('sistemazioni registro A');

CREATE TEMP TABLE tmp_fatt_b AS
SELECT * FROM dbops.fn_pgtap_crea_fattura(
                 'sistemazioni registro B', 'DRAFT',
                 (SELECT billing_account_id FROM tmp_fatt_a));

-- La terza e' di un ALTRO cliente: senza terzo parametro il BB ne costruisce
-- uno nuovo, nella stessa azienda.
CREATE TEMP TABLE tmp_fatt_altro AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('sistemazioni registro altro cliente');

-- Gli importi: il registro delle sistemazioni lavora su fatture con un totale.
UPDATE vendite.fatture SET totale_a_pagare = 100.00
 WHERE id IN ((SELECT fattura_id FROM tmp_fatt_a),
              (SELECT fattura_id FROM tmp_fatt_b),
              (SELECT fattura_id FROM tmp_fatt_altro));

CREATE TEMP TABLE tmp_ref AS
SELECT a.fattura_id                    AS fattura_a,
       b.fattura_id                    AS fattura_b,
       a.cliente_soggetto_ruolo_id     AS cliente_sr,
       a.emittente_soggetto_ruolo_id   AS emittente_sr,
       x.fattura_id                    AS fattura_altro_cliente
  FROM tmp_fatt_a a, tmp_fatt_b b, tmp_fatt_altro x;

SELECT ok(
  (SELECT fattura_a IS NOT NULL AND fattura_b IS NOT NULL
          AND fattura_a <> fattura_b
          AND cliente_sr IS NOT NULL AND emittente_sr IS NOT NULL
          AND fattura_altro_cliente IS NOT NULL
     FROM tmp_ref),
  '1) Riferimenti minimi presenti: due fatture di uno stesso cliente e una di un altro'
);

-- ============================================================
-- 2/3/4. La rinomina, e che non abbia lasciato niente indietro
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'pagamenti' AND c.relname IN ('sistemazioni', 'compensazioni')),
  1,
  '2) La tabella si chiama `sistemazioni`, e `compensazioni` non esiste piu'''
);

-- ⭐ Il test che si dimentica: la tabella rinominata puo' portarsi dietro la
--   chiave primaria, la sequenza e i trigger col nome vecchio. Nessun errore —
--   ma le automazioni di `pagamenti` lavorano per pattern e ne genererebbero
--   altri col nome nuovo ACCANTO, e la tabella avrebbe due audit e due tx_id.
SELECT is(
  (SELECT count(*)::int FROM (
      SELECT con.conname AS nome FROM pg_constraint con
       WHERE con.conrelid = 'pagamenti.sistemazioni'::regclass
      UNION ALL
      SELECT t.tgname FROM pg_trigger t
       WHERE t.tgrelid = 'pagamenti.sistemazioni'::regclass AND NOT t.tgisinternal
      UNION ALL
      SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE n.nspname = 'pagamenti' AND c.relkind = 'S'
         AND c.oid = pg_get_serial_sequence('pagamenti.sistemazioni', 'id')::regclass
   ) x WHERE x.nome LIKE '%compensazioni%'),
  0,
  '3) Nessun vincolo, trigger o sequenza della tabella nomina ancora `compensazioni`'
);

SELECT is(
  (SELECT count(*)::int FROM (
      SELECT 1 FROM information_schema.columns
       WHERE table_schema = 'pagamenti' AND table_name = 'vendite_contabili'
         AND column_name = 'compensazione_id'
      UNION ALL
      SELECT 1 FROM pg_constraint
       WHERE conrelid = 'pagamenti.vendite_contabili'::regclass
         AND conname IN ('uq_vendite_contabili_compensazione',
                         'fk_vendite_contabili_compensazione')
   ) x),
  0,
  '4) Su vendite_contabili non restano ne'' la colonna, ne'' il suo unico, ne'' la sua FK'
);

-- ============================================================
-- 5/6/7/8. Il guard sui dati: destinazione e bagaglio
-- ============================================================
-- ⚠️ SQLSTATE esplicito ovunque: P0001 e' l'errore di dominio. Senza, il test
--    accetterebbe anche il crash del guard — o un 23514 del CHECK, che e' la
--    rete e non il presidio.
SELECT throws_ok(
  format(
    $sql$INSERT INTO pagamenti.sistemazioni
            (destinazione, importo, cliente_soggetto_ruolo_id,
             emittente_soggetto_ruolo_id, fattura_origine_id, fattura_destinazione_id)
         VALUES ('RIMBORSO', 50, %s, %s, %s, %s)$sql$,
    r.cliente_sr, r.emittente_sr, r.fattura_a, r.fattura_b),
  'P0001', NULL,
  '5) Un RIMBORSO che indica una fattura di destinazione e'' rifiutato: il denaro esce, un secondo documento non c''e'''
) FROM tmp_ref r;

SELECT throws_ok(
  format(
    $sql$INSERT INTO pagamenti.sistemazioni
            (destinazione, importo, cliente_soggetto_ruolo_id,
             emittente_soggetto_ruolo_id, fattura_origine_id)
         VALUES ('COMPENSAZIONE', 50, %s, %s, %s)$sql$,
    r.cliente_sr, r.emittente_sr, r.fattura_a),
  'P0001', NULL,
  '6) Una COMPENSAZIONE senza fattura di destinazione e'' rifiutata'
) FROM tmp_ref r;

SELECT throws_ok(
  format(
    $sql$INSERT INTO pagamenti.sistemazioni
            (destinazione, importo, cliente_soggetto_ruolo_id,
             emittente_soggetto_ruolo_id, fattura_origine_id, fattura_destinazione_id,
             motivo)
         VALUES ('RIPORTO', 50, %s, %s, %s, %s, 'motivo')$sql$,
    r.cliente_sr, r.emittente_sr, r.fattura_a, r.fattura_a),
  'P0001', NULL,
  '7) Spostare denaro da un documento a se stesso non e'' una sistemazione'
) FROM tmp_ref r;

-- ⚠️ Il motivo su un RIPORTO non e' una scelta di stile: il riporto genera un
--    fondo con origine MANUALE, e chk_fondi_source_motivo_obbligatorio lo
--    pretende. Chiederlo qui evita di rifiutare alla CONFERMA una cosa che si
--    poteva sistemare mentre l'operatore era ancora nel flusso.
SELECT throws_ok(
  format(
    $sql$INSERT INTO pagamenti.sistemazioni
            (destinazione, importo, cliente_soggetto_ruolo_id,
             emittente_soggetto_ruolo_id, fattura_origine_id, fattura_destinazione_id)
         VALUES ('RIPORTO', 50, %s, %s, %s, %s)$sql$,
    r.cliente_sr, r.emittente_sr, r.fattura_a, r.fattura_b),
  'P0001', NULL,
  '8) Un RIPORTO senza motivo e'' rifiutato: il fondo che genera lo pretende'
) FROM tmp_ref r;

-- ============================================================
-- 9. ⭐ Due documenti di clienti diversi, e la frase lo dice
-- ============================================================
-- ⭐ E' la regola che rende sensata la compensazione (D15-b). Si asserisce con
--   `throws_like` sulla FRASE e non solo sullo SQLSTATE: la domanda «di chi
--   sono questi documenti?» si fa FUORI dalla row security, e un guard che la
--   facesse sotto direbbe «di un altro cliente» anche quando il cliente e' lo
--   stesso — una frase falsa con lo SQLSTATE giusto.
SELECT throws_like(
  format(
    $sql$INSERT INTO pagamenti.sistemazioni
            (destinazione, importo, cliente_soggetto_ruolo_id,
             emittente_soggetto_ruolo_id, fattura_origine_id, fattura_destinazione_id,
             motivo)
         VALUES ('COMPENSAZIONE', 50, %s, %s, %s, %s, 'motivo')$sql$,
    r.cliente_sr, r.emittente_sr, r.fattura_a, r.fattura_altro_cliente),
  '%non si puo%abbinare%',
  '9) Due documenti di clienti diversi sono rifiutati, e il messaggio lo dice'
) FROM tmp_ref r;

-- ============================================================
-- 10/11. Quello che nessuna interfaccia dovrebbe produrre
-- ============================================================
-- ⭐ Codice TECNICO: l'emittente non lo sceglie una persona in un modulo, lo
--   deriva chi costruisce l'atto. Il lettore del messaggio e' dbops.error_log.
SELECT throws_ok(
  format(
    $sql$INSERT INTO pagamenti.sistemazioni
            (destinazione, importo, cliente_soggetto_ruolo_id,
             emittente_soggetto_ruolo_id, fattura_origine_id)
         VALUES ('RIMBORSO', 50, %s, %s, %s)$sql$,
    r.cliente_sr,
    (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr
      WHERE sr.id <> r.emittente_sr ORDER BY sr.id LIMIT 1),
    r.fattura_a),
  'P0001', NULL,
  '10) Un emittente dichiarato diverso da quello della fattura e'' rifiutato'
) FROM tmp_ref r;

SELECT throws_ok(
  format(
    $sql$INSERT INTO pagamenti.sistemazioni
            (destinazione, stato, importo, cliente_soggetto_ruolo_id,
             emittente_soggetto_ruolo_id, fattura_origine_id)
         VALUES ('RIMBORSO', 'CONFERMATA', 50, %s, %s, %s)$sql$,
    r.cliente_sr, r.emittente_sr, r.fattura_a),
  'P0001', NULL,
  '11) Un atto non nasce gia'' CONFERMATO: nasce come decisione'
) FROM tmp_ref r;

-- ============================================================
-- 12/13. La distinta di una compensazione sta sul centro delle compensazioni
-- ============================================================
CREATE FUNCTION pg_temp.codice_rifiuto(p_sql text)
RETURNS text
LANGUAGE plpgsql
AS $fn$
DECLARE
    v_codice text;
BEGIN
    BEGIN
        EXECUTE p_sql;
        RETURN 'NESSUN_RIFIUTO';
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME;
        RETURN COALESCE(NULLIF(v_codice, ''), 'SQLSTATE ' || SQLSTATE);
    END;
END;
$fn$;

CREATE TEMP TABLE tmp_atto_comp AS
WITH ins AS (
  INSERT INTO pagamenti.sistemazioni
      (destinazione, importo, cliente_soggetto_ruolo_id, emittente_soggetto_ruolo_id,
       fattura_origine_id, fattura_destinazione_id, motivo, meta)
  SELECT 'COMPENSAZIONE', 20, r.cliente_sr, r.emittente_sr, r.fattura_a, r.fattura_b,
         'test centro compensazione',
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_ref r
  RETURNING id
)
SELECT id AS atto FROM ins;

-- Una distinta sul centro BANCA: quello di un incasso, non di una compensazione.
CREATE TEMP TABLE tmp_distinta_banca AS
WITH ins AS (
  INSERT INTO pagamenti.vendite_contabili
      (centro_riscossione_id, data_contabile, data_registrazione, stato_id, origine, meta)
  SELECT (SELECT c.id FROM pagamenti.centri_riscossione c
           WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA' ORDER BY c.id LIMIT 1),
         script.fn_data_operativa(), script.fn_data_operativa(),
         (SELECT s.id FROM pagamenti.vendite_contabili_stati s
           WHERE s.codice_interno = 'BOZZA' ORDER BY s.id LIMIT 1),
         'GENERATA',
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  RETURNING id
)
SELECT id FROM ins;

SELECT is(
  pg_temp.codice_rifiuto(format(
    $sql$UPDATE pagamenti.sistemazioni
            SET stato = 'CONFERMATA', contabile_id = %s,
                data_esecuzione = now(), user_esecuzione = current_user
          WHERE id = %s$sql$,
    (SELECT id FROM tmp_distinta_banca), (SELECT atto FROM tmp_atto_comp))),
  'E_CENTRO_NON_ABILITATO_COMPENSAZIONE',
  '12) Una COMPENSAZIONE che registra su una distinta del centro BANCA e'' rifiutata dal guard'
);

SELECT is(
  (SELECT s.stato::text FROM pagamenti.sistemazioni s WHERE s.id = (SELECT atto FROM tmp_atto_comp)),
  'BOZZA',
  '13) ...e l''atto e'' rimasto in BOZZA, senza distinta'
);

-- ============================================================
-- 14. Cleanup
-- ============================================================
SELECT ok(true, '14) Cleanup: la transazione viene annullata, nessun residuo');

SELECT * FROM finish();
ROLLBACK;
