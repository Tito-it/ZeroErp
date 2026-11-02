-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il giro completo di una sistemazione — dall'elenco al documento
--
-- Elenco test (plan 13):
--  1) Riferimenti minimi presenti, e la fattura e' sovra-incassata
--  2) La vista la vede, con l'eccedenza e con CHI e' in credito
--  3) Un atto in bozza si conta, e non fa sparire la riga dall'elenco
--  4) Un RIMBORSO confermato senza canale e' rifiutato
--  5) ...con il canale genera la sua distinta
--  6) ⭐ E la riga ha il SEGNO giusto: negativa su una fattura sovra-incassata
--  6-bis) ⭐ La distinta del rimborso e' numerata sul registro DISTINTA dell'emittente dell'ATTO, non SIS_… (rev 2026-09-15)
--  7) Riconfermare un atto gia' eseguito e' rifiutato
--  8) Modificare un atto terminale e' rifiutato
--  9) 🔴 La distinta di una sistemazione non si aggancia a un lotto
-- 10) ⭐ La COMPENSAZIONE genera DUE righe che sommano a ZERO
-- 11) Un importo maggiore dell'eccedenza e' rifiutato ALLA CONFERMA
-- 12) L'annullamento lascia l'atto a registro, e su uno inesistente rifiuta
-- 14) Assert finale cleanup
--
-- Scopo:
--  - collaudare la slice 4 per intero: la vista presenta, la persona decide,
--    l'atto diventa un fatto (D15-d) — e nessuna macchina nuova sotto;
--  - ⭐ il test 6 e' il piu' importante e il meno ovvio: il segno della riga si
--    ricava dal SALDO e non da un `IF` sul tipo di documento, e la prova che la
--    formula e' giusta e' che su una fattura sovra-incassata la riga esce
--    NEGATIVA — cioe' il denaro esce, che e' che cosa fa un rimborso;
--  - ⭐ il test 10 e' la definizione stessa di compensare: due righe che
--    sommano a zero. Se un giorno il segno della seconda cambiasse, la somma
--    smetterebbe di essere zero e questo test lo direbbe subito;
--  - ⭐ il test 11 presidia una decisione: il controllo dell'eccedenza sta alla
--    CONFERMA e non alla registrazione, perche' fra decidere e confermare puo'
--    arrivare un altro incasso — una garanzia data prima e' una garanzia che
--    scade.
--
-- Piano: brief-db-posting-e-abbinamento-rata.md
--        §2.3-bis S4-3/S4-4 · Decisioni: brief madre D15 · lotto 7
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- Fixture — due fatture di uno stesso cliente, la prima sovra-incassata
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_sistemazioni_giro'::text AS test_scope;

-- ⛔ LE DUE FATTURE E LA FILIALE SI COSTRUISCONO (2026-09-23). La fixture
--   CERCAVA «un cliente con almeno due fatture» e «una filiale bancaria»: su
--   un database ricostruito `vendite.fatture` e `anagrafiche.bank_branches`
--   sono a zero — la prima e' vuota per costruzione, la seconda perche' e'
--   dato di macchina — e il file moriva sulla RLS di `vendite_movimenti` con
--   una fattura che non esisteva.
-- ⭐ E le due fatture sono dello STESSO cliente per COSTRUZIONE (terzo
--   parametro del BB), non per una GROUP BY che spera di trovarlo.
CREATE TEMP TABLE tmp_fatt_a AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('sistemazioni giro A');

CREATE TEMP TABLE tmp_fatt_b AS
SELECT * FROM dbops.fn_pgtap_crea_fattura(
                 'sistemazioni giro B', 'DRAFT',
                 (SELECT billing_account_id FROM tmp_fatt_a));

CREATE TEMP TABLE tmp_banca AS
SELECT * FROM dbops.fn_pgtap_crea_filiale_bancaria('sistemazioni giro');

-- Il totale e' il caso del test: cento euro, e la prima sara' sovra-incassata.
UPDATE vendite.fatture SET totale_a_pagare = 100.00
 WHERE id IN ((SELECT fattura_id FROM tmp_fatt_a), (SELECT fattura_id FROM tmp_fatt_b));

CREATE TEMP TABLE tmp_ref AS
SELECT a.fattura_id                  AS fattura_a,
       b.fattura_id                  AS fattura_b,
       100.00::numeric               AS totale_a,
       a.billing_account_id          AS ba_a,
       a.cliente_soggetto_ruolo_id   AS cliente_sr,
       a.emittente_soggetto_ruolo_id AS emittente_sr,
       (SELECT bank_branch_id FROM tmp_banca) AS bank_branch,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice = 'BANCA' ORDER BY c.id LIMIT 1) AS centro_banca
  FROM tmp_fatt_a a, tmp_fatt_b b;

-- ⭐ Il sovra-incasso: cento euro piu' del totale. Da qui in poi la fattura
--   compare nell'elenco delle eccedenze.
INSERT INTO pagamenti.vendite_movimenti
    (fattura_id, billing_account_id, data_effettiva, data_registrazione, importo, meta)
SELECT r.fattura_a, r.ba_a, script.fn_data_operativa(), script.fn_data_operativa(), r.totale_a + 100,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_ref r;

SELECT ok(
  (SELECT fattura_a IS NOT NULL AND fattura_b IS NOT NULL AND fattura_a <> fattura_b
          AND cliente_sr IS NOT NULL AND centro_banca IS NOT NULL AND bank_branch IS NOT NULL
     FROM tmp_ref)
  AND (SELECT count(*) = 1 FROM pagamenti.vw_eccedenze_da_sistemare v
        WHERE v.fattura_id = (SELECT fattura_a FROM tmp_ref)),
  '1) Riferimenti minimi presenti, e la fattura di partenza risulta sovra-incassata'
);

-- ============================================================
-- 2. La vista dice quanto, e soprattutto CHI e' in credito
-- ============================================================
-- ⭐ Un saldo negativo su una fattura e uno positivo su una nota di credito sono
--   situazioni OPPOSTE, e i numeri da soli non lo dicono: sbagliare il verso
--   significa rimborsare denaro che si deve incassare.
SELECT is(
  (SELECT (v.eccedenza, v.chi_e_in_credito)
     FROM pagamenti.vw_eccedenze_da_sistemare v
    WHERE v.fattura_id = (SELECT fattura_a FROM tmp_ref)),
  (100.00::numeric, 'CLIENTE'::text),
  '2) La vista dice l''eccedenza (100) e che in credito e'' il CLIENTE'
);

-- ============================================================
-- 3. Un atto in bozza si conta, e la riga NON sparisce
-- ============================================================
CREATE TEMP TABLE tmp_atto AS
WITH ins AS (
  INSERT INTO pagamenti.sistemazioni
      (destinazione, importo, cliente_soggetto_ruolo_id, emittente_soggetto_ruolo_id,
       fattura_origine_id, motivo, meta)
  SELECT 'RIMBORSO', 60, r.cliente_sr, r.emittente_sr, r.fattura_a, 'test giro completo',
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_ref r
  RETURNING id
)
SELECT id AS atto_rimborso FROM ins;

-- ⛔ Segnala, non filtra: la decisione e' presa ma il denaro non si e' mosso,
--   quindi l'eccedenza c'e' ancora. Toglierla sarebbe nascondere.
SELECT is(
  (SELECT (v.sistemazioni_in_bozza, v.sistemazioni_confermate)
     FROM pagamenti.vw_eccedenze_da_sistemare v
    WHERE v.fattura_id = (SELECT fattura_a FROM tmp_ref)),
  (1::bigint, 0::bigint),
  '3) L''atto in bozza si conta, e la riga resta nell''elenco: segnala, non filtra'
);

-- ============================================================
-- 4/5/6. Il giro del RIMBORSO
-- ============================================================
SELECT throws_ok(
  format($sql$SELECT * FROM pagamenti.fn_conferma_sistemazione(%s)$sql$,
         (SELECT atto_rimborso FROM tmp_atto)),
  'P0001', NULL,
  '4) Un rimborso confermato senza canale e'' rifiutato: da quale conto esce?'
);

-- Un canale, col suo conto di incasso (dal lotto 6 e' obbligatorio).
-- 🔴 DUE ISTRUZIONI E NON UNA, e non e' stile: dal 2026-08-28 `enti_incasso`
--    ha una policy che chiede «esiste un conto TUO con questo id?». Se il
--    legame nasce nella STESSA istruzione, quella sottoquery non lo vede — la
--    snapshot del comando non contiene le righe che il comando stesso sta
--    scrivendo — e la `WITH CHECK` rifiuta con 42501. E' la trappola RLS+CTE
--    che il progetto ha gia' pagato altrove: padre e figlio nella stessa CTE
--    non passano mai. ⚠️ Vale identica per il backend: chi crea conto e canale
--    in un colpo solo trovera' lo stesso rifiuto.
CREATE TEMP TABLE tmp_legame_sis AS
WITH conto AS (
  INSERT INTO anagrafiche.conti_bancari (iban, bank_branch_id, attivo, storicizza, meta)
  SELECT 'IT00PGTAPSISTEMAZIONI0000001', r.bank_branch, true, false,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_ref r RETURNING id
), legame AS (
  INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
      (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, storicizza, meta)
  SELECT r.emittente_sr, conto.id, 'INCASSO', false, false,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM conto CROSS JOIN tmp_ref r RETURNING id
)
SELECT id AS legame_id FROM legame;

CREATE TEMP TABLE tmp_ente AS
WITH ente AS (
  INSERT INTO pagamenti.enti_incasso
      (codice, descrizione, tipo, attivo, soggetto_ruolo_conto_bancario_id,
       centro_riscossione_id, meta)
  SELECT 'PGTAP_SIS_BANCA', 'canale pgtap sistemazioni', 'ALTRO', true,
         (SELECT legame_id FROM tmp_legame_sis),
         r.centro_banca, jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_ref r
  RETURNING id
)
SELECT id AS ente_id FROM ente;

CREATE TEMP TABLE tmp_esito AS
SELECT * FROM pagamenti.fn_conferma_sistemazione(
    (SELECT atto_rimborso FROM tmp_atto), (SELECT ente_id FROM tmp_ente));

SELECT is(
  (SELECT (s.stato, s.contabile_id IS NOT NULL, s.data_esecuzione IS NOT NULL)
     FROM pagamenti.sistemazioni s WHERE s.id = (SELECT atto_rimborso FROM tmp_atto)),
  ('CONFERMATA'::character varying, true, true),
  '5) Il rimborso confermato genera la sua distinta e diventa un fatto'
);

-- ⭐ IL TEST CHE CONTA: il segno lo da' il SALDO, non un IF sul tipo di
--   documento. Su una fattura sovra-incassata la riga esce NEGATIVA, cioe' il
--   denaro esce — che e' che cosa fa un rimborso.
SELECT is(
  (SELECT r.importo FROM pagamenti.vendite_contabili_righe r
    WHERE r.contabile_id = (SELECT contabile_id FROM tmp_esito)),
  -60.00::numeric,
  '6) La riga ha il SEGNO giusto: negativa su una fattura sovra-incassata'
);

-- ⭐ Rev 2026-09-15 (brief distinta-numerata-sul-registro, D5/L7): la distinta
--   di una sistemazione non porta piu' un codice composto dalla madre (SIS_…):
--   la numera il trigger sul registro DISTINTA dell'emittente dell'ATTO, che
--   entra nella riga; l'aggancio all'atto resta in meta.sistemazione_id.
SELECT is(
  (SELECT concat_ws('|',
              c.codice ~ ('^DIS-' || ef.codice || '-\d{4}-\d{7}$'),
              c.emittente_soggetto_ruolo_id = a.emittente_soggetto_ruolo_id,
              c.registro_id IS NOT NULL,
              (c.meta->>'sistemazione_id')::bigint = a.id)
     FROM pagamenti.vendite_contabili c
     JOIN pagamenti.sistemazioni a ON a.id = (SELECT atto_rimborso FROM tmp_atto)
     JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = a.emittente_soggetto_ruolo_id
    WHERE c.id = (SELECT contabile_id FROM tmp_esito)),
  't|t|t|t',
  '6-bis) La distinta del rimborso e'' DIS-<sigla dell''emittente dell''atto>-…, non SIS_…, e meta.sistemazione_id resta l''aggancio'
);

-- ============================================================
-- 7/8/9. Cio' che dopo non si puo' piu' fare
-- ============================================================
SELECT throws_ok(
  format($sql$SELECT * FROM pagamenti.fn_conferma_sistemazione(%s, %s)$sql$,
         (SELECT atto_rimborso FROM tmp_atto), (SELECT ente_id FROM tmp_ente)),
  'P0001', NULL,
  '7) Riconfermare un atto gia'' eseguito e'' rifiutato: si esegue una volta sola'
);

-- ⭐ Non e' un doppione del test 7: li' si ripete l'AZIONE, qui si tocca il
--   DATO. Un atto confermato ha generato un documento, e se il registro potesse
--   cambiare sotto racconterebbe una cosa e il documento un'altra.
SELECT throws_ok(
  format($sql$UPDATE pagamenti.sistemazioni SET importo = 99 WHERE id = %s$sql$,
         (SELECT atto_rimborso FROM tmp_atto)),
  'P0001', NULL,
  '8) Modificare un atto terminale e'' rifiutato: un fatto non si riscrive'
);

SELECT throws_ok(
  format(
    $sql$INSERT INTO pagamenti.vendite_contabili_lotti (lotto_id, contabile_id)
         SELECT (SELECT id FROM vendite.fatturazione_lotti ORDER BY id DESC LIMIT 1), %s$sql$,
    (SELECT contabile_id FROM tmp_esito)),
  'P0001', NULL,
  '9) La distinta di una sistemazione non si aggancia a un lotto di fatturazione'
);

-- ============================================================
-- 10. ⭐ La COMPENSAZIONE: due righe che sommano a ZERO
-- ============================================================
CREATE TEMP TABLE tmp_atto_comp AS
WITH ins AS (
  INSERT INTO pagamenti.sistemazioni
      (destinazione, importo, cliente_soggetto_ruolo_id, emittente_soggetto_ruolo_id,
       fattura_origine_id, fattura_destinazione_id, motivo, meta)
  SELECT 'COMPENSAZIONE', 20, r.cliente_sr, r.emittente_sr, r.fattura_a, r.fattura_b,
         'test compensazione',
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_ref r
  RETURNING id
)
SELECT id AS atto FROM ins;

CREATE TEMP TABLE tmp_esito_comp AS
SELECT * FROM pagamenti.fn_conferma_sistemazione((SELECT atto FROM tmp_atto_comp));

-- ⭐ E' la definizione stessa di compensare. Se un giorno il segno della seconda
--   riga cambiasse, la somma smetterebbe di essere zero e questo test lo
--   direbbe subito.
SELECT is(
  (SELECT (count(*), sum(r.importo))
     FROM pagamenti.vendite_contabili_righe r
    WHERE r.contabile_id = (SELECT contabile_id FROM tmp_esito_comp)),
  (2::bigint, 0.00::numeric),
  '10) La compensazione genera DUE righe che sommano a ZERO'
);

-- ============================================================
-- 11. L'eccedenza si verifica ALLA CONFERMA
-- ============================================================
-- ⭐ Presidia una decisione: fra il momento in cui una persona decide e quello
--   in cui conferma puo' arrivare un altro incasso, o un'altra sistemazione
--   puo' aver consumato lo stesso credito. Una garanzia data prima e' una
--   garanzia che scade.
-- ⚠️ L'atto si crea in un'ISTRUZIONE A PARTE e non dentro l'argomento della
--    conferma: una CTE che modifica dati deve stare al livello superiore
--    (0A000), e annidarla in una chiamata di funzione non e' ammesso.
CREATE TEMP TABLE tmp_atto_troppo AS
WITH ins AS (
  INSERT INTO pagamenti.sistemazioni
      (destinazione, importo, cliente_soggetto_ruolo_id, emittente_soggetto_ruolo_id,
       fattura_origine_id, motivo, meta)
  SELECT 'RIMBORSO', 999999, r.cliente_sr, r.emittente_sr, r.fattura_a, 'troppo grande',
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_ref r
  RETURNING id
)
SELECT id AS atto FROM ins;

SELECT throws_ok(
  format($sql$SELECT * FROM pagamenti.fn_conferma_sistemazione(%s, %s)$sql$,
         (SELECT atto FROM tmp_atto_troppo), (SELECT ente_id FROM tmp_ente)),
  'P0001', NULL,
  '11) Un importo maggiore dell''eccedenza e'' rifiutato ALLA CONFERMA'
);

-- ============================================================
-- 12. L'annullamento
-- ============================================================
-- ⚠️ Annullare non e' cancellare: l'atto resta a registro con la sua ragione,
--   e l'eccedenza continua a comparire nell'elenco — e' vera, non se n'e' andata.
CREATE TEMP TABLE tmp_atto_ann AS
WITH ins AS (
  INSERT INTO pagamenti.sistemazioni
      (destinazione, importo, cliente_soggetto_ruolo_id, emittente_soggetto_ruolo_id,
       fattura_origine_id, meta)
  SELECT 'RIMBORSO', 10, r.cliente_sr, r.emittente_sr, r.fattura_a,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_ref r
  RETURNING id
)
SELECT id AS atto FROM ins;

SELECT is(
  (SELECT pagamenti.fn_annulla_sistemazione((SELECT atto FROM tmp_atto_ann), 'non serve piu')),
  'ANNULLATA'::character varying,
  '12) L''annullamento lascia l''atto a registro con la sua ragione'
);

-- ============================================================
-- 13. Cleanup
-- ============================================================
SELECT ok(true, '14) Cleanup: la transazione viene annullata, nessun residuo');

SELECT * FROM finish();
ROLLBACK;
