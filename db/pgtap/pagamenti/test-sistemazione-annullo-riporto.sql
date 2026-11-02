-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: annullare un RIPORTO confermato fa cadere il fondo che aveva creato
--
-- Elenco test (plan 13):
--  1) Riferimenti minimi presenti, e la fattura di partenza e' sovra-incassata
--  2) Il RIPORTO confermato ha creato il suo fondo, e nasce ASSEGNATO
--  3) Il predicato dice SISTEMAZIONE_ATTIVA: la FK detta PRIMA che scatti
--  4) ...e la cancellazione diretta del fondo rifiuta NOMINANDO l'alternativa
--  5) ⚠️ Il varco non e' un'apertura: da solo, l'importo resta immutabile
--  6) ⭐ ...e nemmeno INSIEME all'annullamento — e' l'asse delle COLONNE
--  7) ⚠️ ...e da CONFERMATA non si torna in BOZZA
--  8) ⭐ L'annullamento porta l'atto ad ANNULLATA
--  9) ⭐ ...e il fondo cade con lui
-- 10) ⭐ Il composito dell'esito cade INTERO
-- 11) ⭐ ...ma la memoria di quando era stato eseguito resta nel meta
-- 12) Una COMPENSAZIONE confermata non si annulla, e il rifiuto e' UN ALTRO
-- 13) Assert finale cleanup
--
-- Scopo:
--  - ⭐ i test 5, 6 e 7 presidiano la parola «chirurgico»: il varco di G-4 apre
--    UNA transizione, su UNA destinazione e su UN gruppo di colonne, e il guard
--    deve continuare a rifiutare tutto il resto. Senza, un varco allargato per
--    sbaglio passerebbe inosservato — i test 8 e 9 resterebbero verdi lo stesso;
--  - ⛔ e il 6 non e' un doppione del 5: LA PROVA DI MUTAZIONE lo ha dimostrato.
--    Togliendo dal guard il confronto sulle colonne, il 5 restava VERDE — perche'
--    un UPDATE del solo importo non chiede l'annullamento, e a rifiutarlo bastava
--    l'asse dello STATO. L'asse delle COLONNE si esercita solo cambiando lo stato
--    e un'altra colonna NELLA STESSA istruzione: e' quello che fa il 6, ed e'
--    l'unico dei tre che cade se quel confronto sparisce;
--  - ⭐ il test 12 verifica la FRASE e non solo il rifiuto (throws_like): §9.8 del
--    brief chiede che il rifiuto NOMINI l'alternativa invece di dire
--    «immutabile», ed e' un requisito che uno SQLSTATE non sa esprimere. E' la
--    stessa autocritica scritta nel COMMENT del guard;
--  - ⭐ il test 11 e' la contropartita del 10: il composito dell'esito si azzera
--    perche' il CHECK lo pretende, ma la memoria di cio' che e' successo non si
--    butta. Se un giorno qualcuno togliesse la scrittura nel meta «perche' tanto
--    c'e' il motivo», il registro smetterebbe di sapere che quell'atto era stato
--    eseguito davvero.
--
-- Piano: brief-db-fondo-fattura-ricalcolo-e-governo.md
--        §9.6 (G-4) · §9.8 (G-5) · §9.3 D-25 · changeSet 20260831-66/-67
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- Fixture — due fatture dello stesso cliente, la prima sovra-incassata
-- ============================================================
-- ⚠️ Le fatture si COSTRUISCONO invece di pescarle dalla popolazione: il ramo
--   RIPORTO di fn_conferma_sistemazione pretende utility, tipo documento e
--   valuta sulla fattura di partenza (sono NULLABILI su vendite.fatture), e un
--   test che iterasse su cio' che c'e' salterebbe il caso a giorni alterni — e
--   passerebbe a vuoto su un database ricostruito da zero.
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_sistemazione_annullo'::text AS test_scope;

-- ⛔ E IL MONDO SOTTO DI LORO SI COSTRUISCE (2026-09-23). Le due fatture le
--   scriveva gia' questo file — il commento qui sopra lo dice — ma i mattoni
--   li pescava: il billing account «piu' recente», e l'emittente per ripiego
--   con un `OR is_default IS TRUE` che su un BA senza legame risponde
--   un'ALTRA azienda (il difetto di D13). Su un database ricostruito non c'e'
--   nessun BA, e il file moriva su «p_fattura_id obbligatorio».
-- ⭐ Le due fatture stanno sullo STESSO cliente, ed e' il motivo per cui il
--   BB ha un terzo parametro: la seconda si chiede sul billing account della
--   prima invece di costruirne un altro.
CREATE TEMP TABLE tmp_origine_bb AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('sistemazione annullo', 'DEFINITIVA');

CREATE TEMP TABLE tmp_dest_bb AS
SELECT * FROM dbops.fn_pgtap_crea_fattura(
                 'sistemazione annullo destinazione', 'DRAFT',
                 (SELECT billing_account_id FROM tmp_origine_bb));

CREATE TEMP TABLE tmp_refs AS
SELECT o.registro_id,
       o.billing_account_id,
       o.utility_id,
       o.cliente_soggetto_ruolo_id   AS cliente_sr,
       o.tipo_doc_fiscale_id,
       o.valuta_id,
       o.emittente_soggetto_ruolo_id AS emittente_sr,
       o.stato_doc_fiscale_id        AS stato_definitiva_id,
       d.stato_doc_fiscale_id        AS stato_draft_id,
       -- ⚠️ Il centro della compensazione NON si fabbrica: e' seminato ed e'
       --   garantito unico da un indice parziale. Un test che se lo crea non
       --   verifica il seed, lo nasconde.
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.is_compensazione IS TRUE ORDER BY c.id LIMIT 1) AS centro_compensazione_id
  FROM tmp_origine_bb o, tmp_dest_bb d;

-- Gli importi sono il caso del test, non del builder: la fattura di PARTENZA
-- e' definitiva con totale 100 (poi sovra-incassata), quella di DESTINAZIONE
-- e' DRAFT — cioe' ancora lavorabile: se fosse congelata il fondo non sarebbe
-- cancellabile e i test 7/8 direbbero un'altra cosa.
UPDATE vendite.fatture
   SET minimo = false, totale_a_pagare = 100.00,
       meta = meta || jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
 WHERE id = (SELECT fattura_id FROM tmp_origine_bb);

UPDATE vendite.fatture
   SET minimo = false, totale_a_pagare = 500.00,
       meta = meta || jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
 WHERE id = (SELECT fattura_id FROM tmp_dest_bb);

CREATE TEMP TABLE tmp_origine AS
SELECT fattura_id AS id FROM tmp_origine_bb;

CREATE TEMP TABLE tmp_destinazione AS
SELECT fattura_id AS id FROM tmp_dest_bb;

-- ⭐ Il sovra-incasso: duecento su una fattura da cento. Da qui l'eccedenza e'
--   di cento, e le sistemazioni hanno di che confermarsi.
INSERT INTO pagamenti.vendite_movimenti
    (fattura_id, billing_account_id, data_effettiva, data_registrazione, importo, meta)
SELECT (SELECT id FROM tmp_origine), r.billing_account_id, script.fn_data_operativa(), script.fn_data_operativa(), 200.00,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_refs r;

SELECT ok(
  (SELECT registro_id IS NOT NULL AND cliente_sr IS NOT NULL AND emittente_sr IS NOT NULL
      AND utility_id IS NOT NULL AND tipo_doc_fiscale_id IS NOT NULL AND valuta_id IS NOT NULL
      AND centro_compensazione_id IS NOT NULL
     FROM tmp_refs)
  AND (SELECT s.saldo < 0 FROM pagamenti.fn_get_saldo_fattura((SELECT id FROM tmp_origine)) s),
  '1) Riferimenti minimi presenti, e la fattura di partenza risulta sovra-incassata'
);

-- ============================================================
-- Il RIPORTO: si decide, si conferma, e nasce il fondo
-- ============================================================
CREATE TEMP TABLE tmp_riporto AS
WITH ins AS (
  INSERT INTO pagamenti.sistemazioni
      (destinazione, importo, cliente_soggetto_ruolo_id, emittente_soggetto_ruolo_id,
       fattura_origine_id, fattura_destinazione_id, motivo, meta)
  SELECT 'RIPORTO', 30, r.cliente_sr, r.emittente_sr,
         (SELECT id FROM tmp_origine), (SELECT id FROM tmp_destinazione),
         'riporto di prova',
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_refs r
  RETURNING id
)
SELECT id AS atto_id FROM ins;

-- ⚠️ Il VERBO in un'istruzione SEPARATA dall'asserzione.
SELECT * FROM pagamenti.fn_conferma_sistemazione((SELECT atto_id FROM tmp_riporto));

CREATE TEMP TABLE tmp_fondo AS
SELECT s.fondo_source_id AS source_id
  FROM pagamenti.sistemazioni s
 WHERE s.id = (SELECT atto_id FROM tmp_riporto);

SELECT is(
  (SELECT (f.stato, f.fattura_figlia_id, f.origine)
     FROM vendite.fatture_fondi_fattura_source f
    WHERE f.id = (SELECT source_id FROM tmp_fondo)),
  ('ASSEGNATO'::varchar, (SELECT id FROM tmp_destinazione), 'MANUALE'::varchar),
  '2) Il RIPORTO confermato ha creato il fondo, ASSEGNATO alla fattura di destinazione'
);

-- ============================================================
-- LA FK DETTA PRIMA CHE SCATTI
-- ============================================================
SELECT is(
  vendite.fn_check_fondo_cancellabile((SELECT source_id FROM tmp_fondo)),
  'SISTEMAZIONE_ATTIVA',
  '3) Il predicato dice SISTEMAZIONE_ATTIVA: la FK detta prima che scatti'
);

-- ⭐ throws_like e non throws_ok: qui la posta in gioco e' la FRASE — il rifiuto
--   deve NOMINARE l'alternativa, non limitarsi a negare.
SELECT throws_like(
  format($sql$SELECT * FROM vendite.fn_cancella_fondo_fattura(%s)$sql$,
         (SELECT source_id FROM tmp_fondo)),
  '%annullando%',
  '4) ...e la cancellazione diretta del fondo rifiuta NOMINANDO l''alternativa'
);

-- ============================================================
-- ⚠️ IL VARCO E' CHIRURGICO — le due prove che lo tengono stretto
-- ============================================================
-- L'asse dello STATO: senza annullamento non c'e' varco, e ogni modifica cade.
SELECT throws_ok(
  format($sql$UPDATE pagamenti.sistemazioni SET importo = 40 WHERE id = %s$sql$,
         (SELECT atto_id FROM tmp_riporto)),
  'P0001', NULL,
  '5) ⚠️ Il varco non e'' un''apertura: da solo, l''importo resta immutabile'
);

-- ⭐ L'asse delle COLONNE, ed e' l'unico dei tre che lo esercita davvero.
--   L'istruzione chiede tutto cio' che il varco ammette — stato, e le tre
--   colonne dell'esito azzerate — PIU' una colonna che non ammette. Se il guard
--   smettesse di confrontare le colonne, questo passerebbe: l'atto risulterebbe
--   annullato con un importo che non e' quello deliberato.
-- ⛔ Non e' un doppione del 5: con il confronto tolto, il 5 resta VERDE (a
--   rifiutarlo basta l'asse dello stato). Lo ha detto la prova di mutazione, non
--   il ragionamento.
SELECT throws_ok(
  format($sql$UPDATE pagamenti.sistemazioni
                 SET stato = 'ANNULLATA', importo = 40,
                     data_esecuzione = NULL, user_esecuzione = NULL,
                     fondo_source_id = NULL
               WHERE id = %s$sql$,
         (SELECT atto_id FROM tmp_riporto)),
  'P0001', NULL,
  '6) ⭐ ...e nemmeno INSIEME all''annullamento: e'' l''asse delle COLONNE'
);

SELECT throws_ok(
  format($sql$UPDATE pagamenti.sistemazioni SET stato = 'BOZZA' WHERE id = %s$sql$,
         (SELECT atto_id FROM tmp_riporto)),
  'P0001', NULL,
  '7) ⚠️ ...e da CONFERMATA non si torna in BOZZA'
);

-- ============================================================
-- ⭐ L'ANNULLAMENTO: l'atto e il suo effetto cadono insieme
-- ============================================================
SELECT pagamenti.fn_annulla_sistemazione(
    (SELECT atto_id FROM tmp_riporto), 'riporto sbagliato, si disfa');

SELECT is(
  (SELECT s.stato FROM pagamenti.sistemazioni s
    WHERE s.id = (SELECT atto_id FROM tmp_riporto))::text,
  'ANNULLATA',
  '8) ⭐ L''annullamento porta l''atto ad ANNULLATA'
);

SELECT ok(
  NOT EXISTS (SELECT 1 FROM vendite.fatture_fondi_fattura_source f
               WHERE f.id = (SELECT source_id FROM tmp_fondo)),
  '9) ⭐ ...e il fondo cade con lui'
);

-- ⚠️ Tutte e tre insieme: chk_sistemazioni_eseguita ne pretende due, la terza
--   (user_esecuzione) appartiene allo stesso fatto e lasciarla sarebbe un dato
--   composito spostato a meta'.
SELECT ok(
  (SELECT s.data_esecuzione IS NULL
      AND s.user_esecuzione IS NULL
      AND s.fondo_source_id IS NULL
     FROM pagamenti.sistemazioni s
    WHERE s.id = (SELECT atto_id FROM tmp_riporto)),
  '10) ⭐ Il composito dell''esito cade INTERO'
);

SELECT ok(
  (SELECT s.meta -> 'annullata_dopo_esecuzione' ->> 'fondo_source_id'
        = (SELECT source_id FROM tmp_fondo)::text
     FROM pagamenti.sistemazioni s
    WHERE s.id = (SELECT atto_id FROM tmp_riporto)),
  '11) ⭐ ...ma la memoria di quando era stato eseguito resta nel meta'
);

-- ============================================================
-- G-5 — GLI ALTRI DUE RESTANO TERMINALI, E LO DICONO BENE
-- ============================================================
-- ⚠️ Si usa la COMPENSAZIONE e non il RIMBORSO perche' il suo centro e'
--   seminato e unico, mentre il rimborso pretenderebbe un canale di uscita con
--   il suo conto: la regola in prova e' la stessa (G-5 li tratta insieme) e la
--   fixture piu' leggera e' quella che ha meno modi di rompersi per altro.
CREATE TEMP TABLE tmp_compensazione AS
WITH ins AS (
  INSERT INTO pagamenti.sistemazioni
      (destinazione, importo, cliente_soggetto_ruolo_id, emittente_soggetto_ruolo_id,
       fattura_origine_id, fattura_destinazione_id, motivo, meta)
  SELECT 'COMPENSAZIONE', 20, r.cliente_sr, r.emittente_sr,
         (SELECT id FROM tmp_origine), (SELECT id FROM tmp_destinazione),
         'compensazione di prova',
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_refs r
  RETURNING id
)
SELECT id AS atto_id FROM ins;

SELECT * FROM pagamenti.fn_conferma_sistemazione((SELECT atto_id FROM tmp_compensazione));

-- ⭐ La FRASE e' il requisito: §9.8 chiede che il rifiuto nomini la correzione
--   guidata invece di dire «immutabile». Uno SQLSTATE non sa esprimerlo.
SELECT throws_like(
  format($sql$SELECT pagamenti.fn_annulla_sistemazione(%s, 'ci ho ripensato')$sql$,
         (SELECT atto_id FROM tmp_compensazione)),
  '%distinta contabile%',
  '12) Una COMPENSAZIONE confermata non si annulla, e il rifiuto nomina la distinta'
);

-- ============================================================
-- Cleanup
-- ============================================================
DELETE FROM pagamenti.vendite_movimenti m
 WHERE m.fattura_id = (SELECT id FROM tmp_origine);

SELECT ok(
  NOT EXISTS (SELECT 1 FROM pagamenti.vendite_movimenti m
               WHERE m.fattura_id = (SELECT id FROM tmp_origine)),
  '13) Cleanup completato'
);

SELECT * FROM finish();
ROLLBACK;
