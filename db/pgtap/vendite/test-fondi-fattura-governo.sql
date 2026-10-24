-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: governo del fondo fattura — banda, atto unico, corrispondenza, chiave
--       Fase A di brief-db-fondo-fattura-ricalcolo-e-governo.md §8.2
--       (changeSet 20260815-03 .. 20260815-09)
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): le sorgenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima
--   nascevano gia' DEFINITIVA o ANNULLATA). La sorgente ANNULLATA dei test 8 e
--   20 diventa una sorgente EMESSA: una fattura singola non ha nessun passaggio
--   verso ANNULLATA (DRAFT -> ANNULLATA c'e' solo per il lotto, e l'annullo del
--   lotto cancella le fatture), e la regola provata e' «genera e propone SOLO
--   una fattura DEFINITIVA». EMESSA e' il caso piu' stretto: uscita dalla bozza,
--   completa, lo stato subito prima di DEFINITIVA (decisione di Tid, 2026-10-24,
--   Q-1 opzione B).
-- rev 2026-10-24 (brief-modello-documento-vendita Q-4): il cliente, l'azienda
--   e il registro li costruisce dbops.fn_pgtap_crea_mondo_cliente (+
--   script.fn_pgtap_registro_fattura) invece di pescare il primo billing
--   account, che su un database ricostruito non c'e'. Il contesto si apre
--   DOPO, sull'operatore del mondo.
-- rev 2026-10-24 (brief-modello-documento-vendita R-5): sorgenti e figlia le
--   scrive dbops.fn_pgtap_crea_fattura, con minimo, totale e termine alla
--   nascita — la regola del file («le differenze stanno nella fixture, non in
--   una mutazione successiva») ora vale anche per lo stato. Resta a mano la
--   sola SRC_C_NOUTIL, la sorgente SENZA utility: il builder la scrive sempre.
-- rev 2026-10-24 (brief-modello-documento-vendita §4-octies): anche
--   SRC_C_NOUTIL la scrive dbops.fn_pgtap_crea_fattura(..., p_senza_utility =>
--   true) (changeSet 20261024-42), sul cliente del mondo: spariscono l'INSERT a
--   mano, i suoi snapshot e il suo porta_a_stato. Nessuna fattura resta a mano.
-- ------------------------------------------------------------
-- Indice test
--  1) Riferimenti minimi presenti
--  2) D-0: una sola soglia del minimo non si salva
--  3) D-2: importo zero rifiutato dal CHECK (sorgente a totale zero)
--  4) D-2/D-22: stato fuori vocabolario rifiutato dal GUARD (non piu' dal CHECK)
--  4-bis) D-2: ...e il CHECK resta la rete strutturale, con quattro valori
--  5) D-3a: fondo di segno opposto al totale della sorgente rifiutato
--  6) D-3a: fondo piu' grande della sorgente rifiutato
--  7) ⭐ Banda: fondo NEGATIVO su sorgente a credito AMMESSO
--  8) D-1: sorgente EMESSA (non ancora DEFINITIVA) non genera alcun fondo
--  9) D-1: sorgente DEFINITIVA genera il fondo
-- 10) D-1: il secondo giro NON riscrive un fondo esistente (atto unico)
-- 11) D-4: il fondo non passa a una figlia con termine di pagamento diverso
-- 12) D-5: atto MANUALE senza motivo rifiutato
-- 13) D-5: atto MANUALE di segno opposto AMMESSO (il guard non lo tocca)
-- 14) D-6: l'importo di un atto non si modifica piu'
-- 15) D-5: annullamento senza motivo rifiutato
-- 16) D-7: ANNULLATO e' terminale, non si riapre
-- 17) D-8: due atti automatici vivi sulla stessa sorgente rifiutati
-- 18) D-9: la proposta vale l'importo che l'automatismo scriverebbe
-- 19) D-9: nessuna proposta dove un atto esiste gia'
-- 20) D-9: nessuna proposta su sorgente EMESSA (non ancora DEFINITIVA)
-- 21) D-9: nessuna proposta su sorgente senza utility
-- 22) D-9: parametro invalido rifiutato
-- 23) D-10: PROPOSTA_SENZA_ATTO, con l'importo proposto
-- 24) D-10: IMPORTO_NON_CORRISPONDENTE — l'automatismo tace, l'elenco no
-- 25) D-10: UTILITY_NON_ATTRIBUIBILE
-- 26) D-10: NON_PIU_CAPIENTE — la sorgente non regge piu' il suo atto
-- 27) D-3b: il fondo non piu' capiente NON viene applicato (e il capiente si')
-- 28) D-10: il vocabolario dei motivi e' chiuso
-- 29) Cleanup completato
-- ------------------------------------------------------------
BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Il mondo PRIMA del contesto: azienda, operatore e cliente. Poi il test
-- gira come gira l'applicazione (ruolo OPERATORE + RLS attiva), sull'operatore
-- del mondo.
CREATE TEMP TABLE tmp_mondo_ffg AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('fondi_governo');

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_mondo_ffg)); END $ctx$;

SELECT plan(30);

-- ============================================================
-- 0) Riferimenti
-- ============================================================
CREATE TEMP TABLE tmp_cost_ffg AS
SELECT 'pgtap_fondi_governo'::text AS test_scope;

-- I riferimenti del documento sono quelli del mondo: il registro e' quello
-- della sua azienda (lo crea se non c'e').
CREATE TEMP TABLE tmp_refs_ffg AS
SELECT script.fn_pgtap_registro_fattura(m.emittente_soggetto_ruolo_id) AS registro_id,
  m.billing_account_id,
  m.utility_id,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id,
  (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DEFINITIVA' AND attivo IS TRUE ORDER BY id LIMIT 1) AS stato_definitiva_id,
  (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'EMESSA'     AND attivo IS TRUE ORDER BY id LIMIT 1) AS stato_emessa_id,
  (SELECT id FROM vendite.tipi_fondi_fattura WHERE attivo IS TRUE AND codice_interno = 'F_F_ADD_ACC' ORDER BY id LIMIT 1) AS tipo_fondo_id,
  (SELECT id FROM config.termini_pagamento WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS termine_pagamento_id,
  m.emittente_soggetto_ruolo_id
FROM tmp_mondo_ffg m;

SELECT ok(
    (SELECT registro_id IS NOT NULL
        AND billing_account_id IS NOT NULL
        AND utility_id IS NOT NULL
        AND tipo_doc_fiscale_id IS NOT NULL
        AND valuta_id IS NOT NULL
        AND stato_definitiva_id IS NOT NULL
        AND stato_emessa_id IS NOT NULL
        AND tipo_fondo_id IS NOT NULL
        AND termine_pagamento_id IS NOT NULL
        AND emittente_soggetto_ruolo_id IS NOT NULL
     FROM tmp_refs_ffg),
    'Riferimenti minimi presenti'
  );

-- ============================================================
-- 1) D-0 — le due soglie del minimo: entrambe o nessuna
-- ============================================================
-- ⚠️ Le righe esistenti hanno entrambe le soglie vuote (misurato con Tid il
--    2026-08-15): valorizzarne UNA sola dev'essere rifiutato. 23514 =
--    check_violation, e non P0001: e' un vincolo di tabella, non un errore
--    di dominio sollevato da una funzione.
-- ⛔ rev 2026-10-24 (Q-4): la riga NON si pesca («la prima per id»): dal
--    20261021-17 il mondo non la scrive piu', e su un database ricostruito non
--    ce n'e' nessuna — l'UPDATE toccava zero righe e il test era rosso per
--    «no exception». La coppia (emittente, utility) del mondo nasce valida,
--    con le soglie vuote come le righe vere, DENTRO l'istruzione provata: la
--    sottotransazione di throws_ok la porta via, e il resto del file resta sui
--    parametri di sistema dell'utility.
SELECT throws_ok(
    $$
      DO $d0$
      DECLARE
          v_id anagrafiche.emittenti_fiscali_utilities.id%TYPE;
      BEGIN
          INSERT INTO anagrafiche.emittenti_fiscali_utilities (
              emittente_soggetto_ruolo_id, utility_id,
              arrotondamento_importi_dec, metodo_arrotondamento_importi)
          SELECT m.emittente_soggetto_ruolo_id, m.utility_id, 2, 'HALF_UP'
            FROM tmp_mondo_ffg m
          RETURNING id INTO v_id;

          UPDATE anagrafiche.emittenti_fiscali_utilities
             SET minimo_soglia_min = -500.00, minimo_soglia_max = NULL
           WHERE id = v_id;
      END
      $d0$;
    $$,
    '23514',
    NULL,
    'D-0: una sola soglia del minimo non si salva'
  );

-- ============================================================
-- Fixture: quattro sorgenti + una figlia
-- ============================================================
-- ⚠️ Tutte create GIA' con i valori definitivi: nessun test aggiorna una
--    fattura DEFINITIVA, che i guard di intestazione congelata rifiuterebbero.
--    Le differenze fra i casi stanno nella fixture, non in una mutazione
--    successiva. ⭐ Dal 2026-10-24 (R-5) la regola regge anche per lo STATO:
--    le scrive dbops.fn_pgtap_crea_fattura sul cliente del mondo (terzo
--    parametro), con minimo, totale e termine alla NASCITA, e le porta nello
--    stato del loro caso (DEFINITIVA, o EMESSA) per la matrice, con gli
--    snapshot dei building block. Un builder per istruzione.

-- SRC_POS: definitiva, a minimo, totale +100 -> fondo a debito
CREATE TEMP TABLE tmp_src_pos AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_governo', 'DEFINITIVA', (SELECT billing_account_id FROM tmp_refs_ffg),
         false, false, p_minimo => true, p_totale_a_pagare => 100.00) f;

-- SRC_NEG: definitiva, a minimo, totale -80 -> fondo a CREDITO. E' il capo
--          inferiore della banda: il caso che il tampone «genera solo
--          importi positivi» avrebbe spento, ed e' la ragione per cui il
--          test 7 esiste.
CREATE TEMP TABLE tmp_src_neg AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_governo', 'DEFINITIVA', (SELECT billing_account_id FROM tmp_refs_ffg),
         false, false, p_minimo => true, p_totale_a_pagare => -80.00) f;

-- SRC_EME: EMESSA, con minimo = true e un totale positivo: tutto come una
--          sorgente che genera, tranne lo stato. Prima del filtro di stato
--          avrebbe generato un fondo, perche' fn_get_saldo_fattura non guarda
--          lo stato e restituisce il totale intero. (Fino al 2026-10-24 era una
--          sorgente ANNULLATA, che nasceva gia' annullata: il modello non ha un
--          passaggio che porti una fattura singola in ANNULLATA.)
CREATE TEMP TABLE tmp_src_eme AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_governo', 'EMESSA', (SELECT billing_account_id FROM tmp_refs_ffg),
         false, false, p_minimo => true, p_totale_a_pagare => 50.00) f;

-- SRC_TERM: definitiva, a minimo, +40, ma con un TERMINE DI PAGAMENTO che
--           la figlia non ha. Nona colonna della chiave di generazione:
--           prima dei nove elementi il suo fondo sarebbe passato lo stesso.
CREATE TEMP TABLE tmp_src_term AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_governo', 'DEFINITIVA', (SELECT billing_account_id FROM tmp_refs_ffg),
         false, false, p_minimo => true, p_totale_a_pagare => 40.00,
         p_termine_pagamento_id => (SELECT termine_pagamento_id FROM tmp_refs_ffg)) f;

-- SRC_ZERO: totale ZERO, non a minimo. Serve SOLO al test 3, ed e' l'unico
--           terreno da cui il CHECK `importo <> 0` e' RAGGIUNGIBILE: su ogni
--           altra sorgente il guard di corrispondenza arriva prima (i trigger
--           BEFORE ROW girano prima dei CHECK) e intercetta lo zero perche'
--           sign(0) non e' il segno di nessun totale diverso da zero.
CREATE TEMP TABLE tmp_src_zero AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_governo', 'DEFINITIVA', (SELECT billing_account_id FROM tmp_refs_ffg),
         false, false, p_minimo => false, p_totale_a_pagare => 0.00) f;

-- FIGLIA: nessun termine di pagamento, non a minimo.
CREATE TEMP TABLE tmp_figlia AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_governo', 'DRAFT', (SELECT billing_account_id FROM tmp_refs_ffg),
         false, false, p_minimo => false, p_totale_a_pagare => 200.00) f;

-- ============================================================
-- 2) e 3) D-2 — i due CHECK di tabella
-- ============================================================
-- ⚠️ La sorgente e' SRC_ZERO, e la scelta e' obbligata: i trigger BEFORE ROW
--    girano PRIMA dei CHECK, quindi su una sorgente con totale diverso da zero
--    l'importo 0 viene intercettato dal guard di corrispondenza (sign(0) non e'
--    il segno di nessun totale non nullo) e il CHECK non entra mai in gioco.
--    Su un totale zero il guard passa (0 e 0 hanno lo stesso segno e lo stesso
--    valore assoluto) e il CHECK diventa raggiungibile — che e' poi l'unico
--    caso in cui serve davvero come rete.
--    🔴 Prima stesura di questo test: puntava a SRC_POS e asseriva 23514,
--    ottenendo P0001. Collaudava il guard credendo di collaudare il CHECK.
SELECT throws_ok(
    format($$
      INSERT INTO vendite.fatture_fondi_fattura_source (
          fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
          billing_account_id, utility_id, tipo_doc_fiscale_id,
          emittente_soggetto_ruolo_id, valuta_id)
      SELECT %s, r.tipo_fondo_id, 0, 'DISPONIBILE',
             r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
             r.emittente_soggetto_ruolo_id, r.valuta_id
        FROM tmp_refs_ffg r;
    $$, (SELECT id FROM tmp_src_zero)),
    '23514',
    NULL,
    'D-2: importo zero rifiutato dal CHECK (su sorgente a totale zero, dove il guard non arriva prima)'
  );

-- 🔴 RISCRITTO IL 2026-08-31 (D-22): a rifiutare non e' piu' il CHECK.
--   Dal changeSet 20260831-61 il guard di transizione e' montato anche in
--   BEFORE INSERT, e un BEFORE ROW scatta PRIMA che i CHECK di tabella siano
--   valutati: adesso parla lui, con P0001 e con una frase che nomina i due
--   stati di nascita ammessi. ⚠️ Il presidio non e' sparito ne' si e' spostato
--   di significato — si e' spostato di SEDE, ed e' esattamente la specie di
--   cambio che un `throws_ok` senza SQLSTATE non avrebbe fatto vedere: sarebbe
--   restato verde raccontando una cosa falsa.
-- ⛔ Il CHECK resta, e non e' ridondante: presidia le strade che il trigger non
--   percorre (un COPY con i trigger spenti, un DISABLE TRIGGER). Che ci sia
--   ancora, e con tutti e quattro i valori, lo dice l'asserzione subito dopo —
--   senza, spegnere il vincolo passerebbe inosservato perche' a fermare
--   l'INSERT basterebbe il guard.
SELECT throws_ok(
    format($$
      INSERT INTO vendite.fatture_fondi_fattura_source (
          fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
          billing_account_id, utility_id, tipo_doc_fiscale_id,
          emittente_soggetto_ruolo_id, valuta_id)
      SELECT %s, r.tipo_fondo_id, 10.00, 'RIAPERTO',
             r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
             r.emittente_soggetto_ruolo_id, r.valuta_id
        FROM tmp_refs_ffg r;
    $$, (SELECT id FROM tmp_src_pos)),
    'P0001',
    NULL,
    'D-2/D-22: stato fuori vocabolario rifiutato — dal 2026-08-31 dal GUARD, non piu'' dal CHECK'
  );

SELECT ok(
    (SELECT pg_get_constraintdef(c.oid) LIKE '%DISPONIBILE%'
        AND pg_get_constraintdef(c.oid) LIKE '%ASSEGNATO%'
        AND pg_get_constraintdef(c.oid) LIKE '%ANNULLATO%'
        AND pg_get_constraintdef(c.oid) LIKE '%ESEGUITO%'
       FROM pg_constraint c
      WHERE c.conname = 'chk_fondi_source_stato'
        AND c.conrelid = 'vendite.fatture_fondi_fattura_source'::regclass),
    'D-2: ...e il CHECK resta la rete strutturale, con tutti e quattro i valori'
  );

-- ============================================================
-- 4) e 5) D-3a — il guard di corrispondenza
-- ============================================================
-- ⚠️ P0001 e non 23514: e' un errore di DOMINIO sollevato da
--    script.fn_log_and_raise_error, non un vincolo di tabella. La
--    distinzione conta: un'asserzione generica passerebbe anche se a
--    fermare l'INSERT fosse un CHECK, cioe' un altro presidio.
SELECT throws_ok(
    format($$
      INSERT INTO vendite.fatture_fondi_fattura_source (
          fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
          billing_account_id, utility_id, tipo_doc_fiscale_id,
          emittente_soggetto_ruolo_id, valuta_id)
      SELECT %s, r.tipo_fondo_id, -30.00, 'DISPONIBILE',
             r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
             r.emittente_soggetto_ruolo_id, r.valuta_id
        FROM tmp_refs_ffg r;
    $$, (SELECT id FROM tmp_src_pos)),
    'P0001',
    NULL,
    'D-3a: fondo di segno opposto al totale della sorgente rifiutato'
  );

SELECT throws_ok(
    format($$
      INSERT INTO vendite.fatture_fondi_fattura_source (
          fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
          billing_account_id, utility_id, tipo_doc_fiscale_id,
          emittente_soggetto_ruolo_id, valuta_id)
      SELECT %s, r.tipo_fondo_id, 100.01, 'DISPONIBILE',
             r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
             r.emittente_soggetto_ruolo_id, r.valuta_id
        FROM tmp_refs_ffg r;
    $$, (SELECT id FROM tmp_src_pos)),
    'P0001',
    NULL,
    'D-3a: fondo piu'' grande della sorgente rifiutato'
  );

-- ============================================================
-- 6) ⭐ Il fondo NEGATIVO legittimo: capo inferiore della banda
-- ============================================================
-- ⚠️ E' il contrario del test 4: li' un importo negativo e' un difetto, qui
--    e' il meccanismo che funziona. A distinguerli non e' il SEGNO ma la
--    CORRISPONDENZA con la sorgente — ed e' esattamente l'errore che il
--    tampone «genera solo importi positivi» avrebbe commesso, spegnendo
--    meta' del meccanismo senza che nessuno se ne accorgesse.
SELECT lives_ok(
    format($$
      INSERT INTO vendite.fatture_fondi_fattura_source (
          fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
          billing_account_id, utility_id, tipo_doc_fiscale_id,
          emittente_soggetto_ruolo_id, valuta_id, meta)
      SELECT %s, r.tipo_fondo_id, -80.00, 'DISPONIBILE',
             r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
             r.emittente_soggetto_ruolo_id, r.valuta_id,
             jsonb_build_object('test_scope', '%s')
        FROM tmp_refs_ffg r;
    $$, (SELECT id FROM tmp_src_neg), (SELECT test_scope FROM tmp_cost_ffg)),
    'Banda: fondo NEGATIVO su sorgente a credito AMMESSO'
  );

-- ------------------------------------------------------------
-- Preparazione del test «atto unico»: si mette a mano un fondo di 60 su una
-- sorgente da 100. E' dentro l'inviluppo (stesso segno, minore in valore
-- assoluto) quindi il guard lo accetta, ma NON e' il valore che la
-- generazione calcolerebbe. Il vecchio ramo UPDATE lo avrebbe riallineato a
-- 100; il nuovo non deve toccarlo.
-- ------------------------------------------------------------
INSERT INTO vendite.fatture_fondi_fattura_source (
    fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
    billing_account_id, utility_id, tipo_doc_fiscale_id,
    emittente_soggetto_ruolo_id, valuta_id, meta)
SELECT (SELECT id FROM tmp_src_pos), r.tipo_fondo_id, 60.00, 'DISPONIBILE',
       r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
       r.emittente_soggetto_ruolo_id, r.valuta_id,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_ffg))
  FROM tmp_refs_ffg r;

-- ------------------------------------------------------------
-- La generazione gira UNA volta. Da qui in poi si osserva il risultato.
-- ------------------------------------------------------------
SELECT vendite.fn_genera_fondi_fattura_source(
      p_billing_account_id          => (SELECT billing_account_id FROM tmp_refs_ffg),
      p_utility_id                  => (SELECT utility_id FROM tmp_refs_ffg),
      p_tipo_doc_fiscale_id         => (SELECT tipo_doc_fiscale_id FROM tmp_refs_ffg),
      p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_ffg),
      p_valuta_id                   => (SELECT valuta_id FROM tmp_refs_ffg),
      p_tipo_fondo_fattura_id       => (SELECT tipo_fondo_id FROM tmp_refs_ffg)
    );

-- ============================================================
-- 7) D-1 — la sorgente EMESSA (non ancora DEFINITIVA) non genera niente
-- ============================================================
SELECT is(
    (SELECT count(*)::INTEGER
       FROM vendite.fatture_fondi_fattura_source s
      WHERE s.fattura_sorgente_id = (SELECT id FROM tmp_src_eme)),
    0,
    'D-1: sorgente EMESSA (non ancora DEFINITIVA) non genera alcun fondo'
  );

-- ============================================================
-- 8) D-1 — la sorgente DEFINITIVA genera il suo fondo
-- ============================================================
-- ⚠️ Si osserva SRC_TERM e non il valore di ritorno della funzione: il
--    conteggio globale dipende da quante fatture a minimo esistono nel
--    database, e un'asserzione su quello sarebbe data-dependent.
SELECT is(
    (SELECT s.importo
       FROM vendite.fatture_fondi_fattura_source s
      WHERE s.fattura_sorgente_id = (SELECT id FROM tmp_src_term)
      ORDER BY s.id),
    40.00::NUMERIC,
    'D-1: la sorgente DEFINITIVA genera il fondo, con il suo importo'
  );

-- ============================================================
-- 9) D-1 — ATTO UNICO: la generazione non riscrive un fondo esistente
-- ============================================================
SELECT is(
    (SELECT s.importo
       FROM vendite.fatture_fondi_fattura_source s
      WHERE s.fattura_sorgente_id = (SELECT id FROM tmp_src_pos)
      ORDER BY s.id),
    60.00::NUMERIC,
    'D-1: il fondo esistente NON viene riallineato dalla generazione'
  );

-- ============================================================
-- 10) D-4 — la chiave a nove elementi: il termine di pagamento separa
-- ============================================================
SELECT vendite.fn_applica_fondi_fattura(
      p_billing_account_id          => (SELECT billing_account_id FROM tmp_refs_ffg),
      p_utility_id                  => (SELECT utility_id FROM tmp_refs_ffg),
      p_tipo_doc_fiscale_id         => (SELECT tipo_doc_fiscale_id FROM tmp_refs_ffg),
      p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_ffg),
      p_valuta_id                   => (SELECT valuta_id FROM tmp_refs_ffg),
      p_fattura_figlia_id           => (SELECT id FROM tmp_figlia),
      p_tipo_fondo_fattura_id       => (SELECT tipo_fondo_id FROM tmp_refs_ffg)
    );

-- ⚠️ L'asserzione e' RELATIVA e non assoluta: si confronta il fondo con il
--    termine (che non deve passare) con quello senza (che deve passare).
--    Un test sul solo primo passerebbe anche se l'applicazione non avesse
--    fatto nulla — verde per sottrazione.
SELECT is(
    (SELECT string_agg(x.stato, '|' ORDER BY x.ord)
       FROM (
         SELECT 1 AS ord, s.stato
           FROM vendite.fatture_fondi_fattura_source s
          WHERE s.fattura_sorgente_id = (SELECT id FROM tmp_src_term)
         UNION ALL
         SELECT 2 AS ord, s.stato
           FROM vendite.fatture_fondi_fattura_source s
          WHERE s.fattura_sorgente_id = (SELECT id FROM tmp_src_pos)
       ) x),
    'DISPONIBILE|ASSEGNATO',
    'D-4: il fondo con termine diverso resta DISPONIBILE, quello con la stessa chiave viene ASSEGNATO'
  );


-- ============================================================
-- FASE B — il registro degli atti (changeSet 20260815-12 .. -18)
-- ============================================================

-- 11) e 12) origine MANUALE: governata, non vincolata
-- ------------------------------------------------------------
-- ⚠️ Senza motivo non si salva (CHECK), ma il guard di corrispondenza NON la
--    tocca: l'eccedenza di un sovra-incasso e' un credito su una fattura
--    POSITIVA — segno opposto per costruzione — ed e' l'atto per cui la
--    strada manuale esiste. I due test vanno letti insieme: da soli
--    direbbero mezza verita'.
SELECT throws_ok(
    format($$
      INSERT INTO vendite.fatture_fondi_fattura_source (
          fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato, origine,
          billing_account_id, utility_id, tipo_doc_fiscale_id,
          emittente_soggetto_ruolo_id, valuta_id)
      SELECT %s, r.tipo_fondo_id, -30.00, 'DISPONIBILE', 'MANUALE',
             r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
             r.emittente_soggetto_ruolo_id, r.valuta_id
        FROM tmp_refs_ffg r;
    $$, (SELECT id FROM tmp_src_pos)),
    '23514',
    NULL,
    'D-5: atto MANUALE senza motivo rifiutato dal CHECK'
  );

SELECT lives_ok(
    format($$
      INSERT INTO vendite.fatture_fondi_fattura_source (
          fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato, origine, motivo,
          billing_account_id, utility_id, tipo_doc_fiscale_id,
          emittente_soggetto_ruolo_id, valuta_id, meta)
      SELECT %s, r.tipo_fondo_id, -30.00, 'DISPONIBILE', 'MANUALE',
             'Eccedenza da sovra-incasso riportata sulla prossima fattura',
             r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
             r.emittente_soggetto_ruolo_id, r.valuta_id,
             jsonb_build_object('test_scope', '%s')
        FROM tmp_refs_ffg r;
    $$, (SELECT id FROM tmp_src_pos), (SELECT test_scope FROM tmp_cost_ffg)),
    'D-5: atto MANUALE di segno opposto al totale AMMESSO (governato, non vincolato)'
  );

-- 13) D-6 — l'atto e' immutabile
-- ------------------------------------------------------------
-- ⚠️ P0001: e' script.trgfn_lock_columns a sollevare, non un vincolo.
-- ⛔ 2026-09-05 — L'ASSERZIONE ORA NOMINA LA FRASE, e il motivo e' successo.
--   Il lock era stato montato con un CREATE TRIGGER A MANO (20260815-15) e non
--   registrato in dbops.automation_lock_columns: un oggetto che sembrava
--   governato dall'automazione e non lo era. Quando e' sparito, nessuno l'ha
--   rimesso — e questo test e' stato l'unico ad accorgersene.
--   ⚠️ Ma con `throws_ok(..., 'P0001', NULL, ...)` sarebbe bastato un QUALUNQUE
--   errore di dominio per tornare verde: su questa tabella ci sono altri due
--   guard BEFORE ROW che parlano prima in ordine alfabetico
--   (`_a10_guard_importo_`, `_a10_guard_transizione_`), e uno di loro avrebbe
--   coperto il lock ancora mancante.
--   ⇒ Si asserisce la FRASE del codice E_FONDO_ATTO_IMMUTABILE: cosi' il verde
--     dice che ha parlato QUEL presidio, non che qualcuno si e' lamentato.
SELECT throws_like(
    format($$
      UPDATE vendite.fatture_fondi_fattura_source
         SET importo = 70.00
       WHERE fattura_sorgente_id = %s AND origine = 'AUTOMATICA';
    $$, (SELECT id FROM tmp_src_pos)),
    '%atto gia%compiuto: la colonna%',
    'D-6: l''importo di un atto gia'' compiuto non si modifica (E_FONDO_ATTO_IMMUTABILE)'
  );

-- 14) e 15) D-5 e D-7 — annullamento e terminalita'
-- ------------------------------------------------------------
SELECT throws_ok(
    format($$
      UPDATE vendite.fatture_fondi_fattura_source
         SET stato = 'ANNULLATO'
       WHERE fattura_sorgente_id = %s AND origine = 'AUTOMATICA';
    $$, (SELECT id FROM tmp_src_term)),
    '23514',
    NULL,
    'D-5: annullamento senza motivo rifiutato dal CHECK'
  );

-- Annullamento fatto come si deve, per poter provare la terminalita'.
UPDATE vendite.fatture_fondi_fattura_source
   SET stato = 'ANNULLATO', motivo = 'Annullato dal pgTAP per collaudare la terminalita'
 WHERE fattura_sorgente_id = (SELECT id FROM tmp_src_term) AND origine = 'AUTOMATICA';

SELECT throws_ok(
    format($$
      UPDATE vendite.fatture_fondi_fattura_source
         SET stato = 'DISPONIBILE'
       WHERE fattura_sorgente_id = %s AND origine = 'AUTOMATICA';
    $$, (SELECT id FROM tmp_src_term)),
    'P0001',
    NULL,
    'D-7: ANNULLATO e'' terminale — un fondo annullato non si riapre'
  );

-- 16) D-8 — un solo atto automatico vivo per sorgente
-- ------------------------------------------------------------
-- ⚠️ 23505 = unique_violation. L'importo (-10 su una sorgente da -80) e'
--    dentro l'inviluppo, quindi il guard di corrispondenza passa: a fermare
--    l'INSERT dev'essere l'indice, non un altro presidio.
SELECT throws_ok(
    format($$
      INSERT INTO vendite.fatture_fondi_fattura_source (
          fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
          billing_account_id, utility_id, tipo_doc_fiscale_id,
          emittente_soggetto_ruolo_id, valuta_id)
      SELECT %s, r.tipo_fondo_id, -10.00, 'DISPONIBILE',
             r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
             r.emittente_soggetto_ruolo_id, r.valuta_id
        FROM tmp_refs_ffg r;
    $$, (SELECT id FROM tmp_src_neg)),
    '23505',
    NULL,
    'D-8: due atti automatici vivi sulla stessa sorgente rifiutati dall''indice'
  );

-- ============================================================
-- FASE C — la proposta e l'elenco (changeSet 20260815-19 .. -23)
-- ============================================================
-- ⚠️ Le fixture di questa fase nascono ADESSO, dopo che la generazione ha
--    gia' girato: se esistessero prima, l'automatismo le avrebbe dotate di
--    un atto e il caso «proposta senza atto» non esisterebbe piu'.

-- SRC_C_PROP: pulita, +120. E' il caso normale: merita un fondo e non ce l'ha.
CREATE TEMP TABLE tmp_src_c_prop AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_governo', 'DEFINITIVA', (SELECT billing_account_id FROM tmp_refs_ffg),
         false, false, p_minimo => true, p_totale_a_pagare => 120.00) f;

-- SRC_C_NC: +50, ma con una riga contabile da +200 che qualcun altro sta
--           lavorando. Il residuo diventa -150: un fondo A CREDITO su un
--           documento A DEBITO. Non e' «negativo», e' di un'altra fattura —
--           ed e' esattamente il caso che l'automatismo salta in silenzio.
CREATE TEMP TABLE tmp_src_c_nc AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_governo', 'DEFINITIVA', (SELECT billing_account_id FROM tmp_refs_ffg),
         false, false, p_minimo => true, p_totale_a_pagare => 50.00) f;

-- SRC_C_NOUTIL: +90, in banda e definitiva, ma senza utility. Nessun giro la
--               vedra' mai: il filtro e' `=`, e NULL non e' uguale a niente.
-- ⭐ Dal builder (rev 2026-10-24, §4-octies): p_senza_utility, sul cliente del
--    mondo, minimo e totale alla nascita, fino a DEFINITIVA per la matrice coi
--    suoi snapshot, come le altre.
CREATE TEMP TABLE tmp_src_c_noutil AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_governo', 'DEFINITIVA', (SELECT billing_account_id FROM tmp_refs_ffg),
         p_minimo => true, p_totale_a_pagare => 90.00,
         p_senza_utility => true) f;

-- SRC_C_CAP: +100 con il suo atto da 100, poi arriva un incasso in
--            lavorazione da 60. L'atto resta valido ma la sorgente non lo
--            regge piu': 40 di capienza contro 100 di fondo.
CREATE TEMP TABLE tmp_src_c_cap AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_governo', 'DEFINITIVA', (SELECT billing_account_id FROM tmp_refs_ffg),
         false, false, p_minimo => true, p_totale_a_pagare => 100.00) f;

-- SRC_C_CTRL: il CONTROLLO del test 27. Stessa chiave, atto capiente, nessun
--             incasso: deve essere applicato. Senza di lui l'asserzione «il
--             non capiente resta DISPONIBILE» passerebbe anche se
--             l'applicazione non avesse fatto NIENTE — verde per sottrazione.
CREATE TEMP TABLE tmp_src_c_ctrl AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_governo', 'DEFINITIVA', (SELECT billing_account_id FROM tmp_refs_ffg),
         false, false, p_minimo => true, p_totale_a_pagare => 70.00) f;

-- Gli atti delle due sorgenti con fondo: entrambi dentro l'inviluppo (stesso
-- segno, pari al totale), quindi il guard di corrispondenza li accetta.
INSERT INTO vendite.fatture_fondi_fattura_source (
    fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
    billing_account_id, utility_id, tipo_doc_fiscale_id,
    emittente_soggetto_ruolo_id, valuta_id, meta)
SELECT (SELECT id FROM tmp_src_c_cap), r.tipo_fondo_id, 100.00, 'DISPONIBILE',
       r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
       r.emittente_soggetto_ruolo_id, r.valuta_id,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_ffg))
  FROM tmp_refs_ffg r;

INSERT INTO vendite.fatture_fondi_fattura_source (
    fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
    billing_account_id, utility_id, tipo_doc_fiscale_id,
    emittente_soggetto_ruolo_id, valuta_id, meta)
SELECT (SELECT id FROM tmp_src_c_ctrl), r.tipo_fondo_id, 70.00, 'DISPONIBILE',
       r.billing_account_id, r.utility_id, r.tipo_doc_fiscale_id,
       r.emittente_soggetto_ruolo_id, r.valuta_id,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_ffg))
  FROM tmp_refs_ffg r;

-- ------------------------------------------------------------
-- ⭐ LE RIGHE CONTABILI: la fixture che mancava da Fase A.
--    Finora «sorgente non piu' capiente» era un ramo scritto e mai
--    percorso, perche' serviva una riga contabile POSTABILE sulla
--    sorgente. Eccola: stato ABBINATA (is_postabile = true) su una
--    testata non finale.
-- ------------------------------------------------------------
CREATE TEMP TABLE tmp_contabile_ffg AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
         p_centro_riscossione_id => (
           SELECT c.id FROM pagamenti.centri_riscossione c
            WHERE c.attivo IS TRUE ORDER BY c.id LIMIT 1),
         p_data_contabile => script.fn_data_operativa()
       ) AS contabile_id;

CREATE TEMP TABLE tmp_righe_ffg AS WITH ins AS (
  INSERT INTO pagamenti.vendite_contabili_righe (
      contabile_id, fattura_id, billing_account_id, importo, stato_id, meta)
  SELECT (SELECT contabile_id FROM tmp_contabile_ffg),
         v.fattura_id,
         (SELECT billing_account_id FROM tmp_refs_ffg),
         v.importo,
         (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
           WHERE s.codice_interno = 'ABBINATA' ORDER BY s.id LIMIT 1),
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_cost_ffg))
    FROM (VALUES
            ((SELECT id FROM tmp_src_c_nc),  200.00::NUMERIC),
            ((SELECT id FROM tmp_src_c_cap),  60.00::NUMERIC)
         ) AS v(fattura_id, importo)
  RETURNING id
) SELECT * FROM ins;

-- ============================================================
-- 18) .. 21) D-9 — la proposta, e i tre silenzi
-- ============================================================
SELECT is(
    vendite.fn_fondo_fattura_proponibile(
      (SELECT id FROM tmp_src_c_prop), (SELECT tipo_fondo_id FROM tmp_refs_ffg)),
    120.00::NUMERIC,
    'D-9: la proposta vale l''importo che l''automatismo scriverebbe'
  );

-- ⚠️ SRC_POS ha gia' un atto: la proposta tace. E' la stessa regola dell'atto
--    unico — se qualcuno lo ha annullato, riproporlo sarebbe l'elenco che
--    chiede ogni giorno di rifare cio' che una persona ha deciso di non fare.
SELECT is(
    vendite.fn_fondo_fattura_proponibile(
      (SELECT id FROM tmp_src_pos), (SELECT tipo_fondo_id FROM tmp_refs_ffg)),
    NULL::NUMERIC,
    'D-9: nessuna proposta dove un atto esiste gia'''
  );

SELECT is(
    vendite.fn_fondo_fattura_proponibile(
      (SELECT id FROM tmp_src_eme), (SELECT tipo_fondo_id FROM tmp_refs_ffg)),
    NULL::NUMERIC,
    'D-9: nessuna proposta su sorgente EMESSA (non ancora DEFINITIVA)'
  );

SELECT is(
    vendite.fn_fondo_fattura_proponibile(
      (SELECT id FROM tmp_src_c_noutil), (SELECT tipo_fondo_id FROM tmp_refs_ffg)),
    NULL::NUMERIC,
    'D-9: nessuna proposta su sorgente senza utility'
  );

-- ============================================================
-- 22) D-9 — un id non valido e' un errore del chiamante, non un silenzio
-- ============================================================
SELECT throws_ok(
    $$ SELECT vendite.fn_fondo_fattura_proponibile(0, 1); $$,
    'P0001',
    NULL,
    'D-9: parametro invalido rifiutato (non confuso con «niente da proporre»)'
  );

-- ============================================================
-- 23) .. 26) D-10 — i quattro motivi dell'elenco
-- ============================================================
SELECT is(
    (SELECT v.motivo || '|' || v.importo_proposto::TEXT
       FROM vendite.vw_fondi_fattura_da_decidere v
      WHERE v.fattura_sorgente_id = (SELECT id FROM tmp_src_c_prop)),
    'PROPOSTA_SENZA_ATTO|120.00',
    'D-10: la fattura senza atto compare come PROPOSTA_SENZA_ATTO, con l''importo'
  );

-- ⚠️ Qui l'automatismo NON fa niente ed e' giusto (un lotto non si ferma per
--    un caso ordinario). Ma «non fare niente in silenzio» e' cio' che questa
--    vista esiste per rendere visibile.
SELECT is(
    (SELECT v.motivo || '|' || v.capienza_attuale::TEXT
       FROM vendite.vw_fondi_fattura_da_decidere v
      WHERE v.fattura_sorgente_id = (SELECT id FROM tmp_src_c_nc)),
    'IMPORTO_NON_CORRISPONDENTE|-150.00',
    'D-10: il residuo che non assomiglia al documento compare come IMPORTO_NON_CORRISPONDENTE'
  );

SELECT is(
    (SELECT v.motivo
       FROM vendite.vw_fondi_fattura_da_decidere v
      WHERE v.fattura_sorgente_id = (SELECT id FROM tmp_src_c_noutil)),
    'UTILITY_NON_ATTRIBUIBILE',
    'D-10: la fattura senza utility compare come UTILITY_NON_ATTRIBUIBILE'
  );

SELECT is(
    (SELECT v.motivo || '|' || v.capienza_attuale::TEXT || '|' || v.importo_atto::TEXT
       FROM vendite.vw_fondi_fattura_da_decidere v
      WHERE v.fattura_sorgente_id = (SELECT id FROM tmp_src_c_cap)),
    'NON_PIU_CAPIENTE|40.00|100.00',
    'D-10: l''atto che la sorgente non regge piu'' compare come NON_PIU_CAPIENTE'
  );

-- ============================================================
-- 27) D-3b — il guard di capienza, finalmente PERCORSO
-- ============================================================
-- ⚠️ Asserzione RELATIVA: il fondo non capiente (100 su 40 di residuo) contro
--    quello capiente (70 su 70). Sul solo primo, un'applicazione che non
--    facesse NULLA passerebbe il test.
SELECT vendite.fn_applica_fondi_fattura(
      p_billing_account_id          => (SELECT billing_account_id FROM tmp_refs_ffg),
      p_utility_id                  => (SELECT utility_id FROM tmp_refs_ffg),
      p_tipo_doc_fiscale_id         => (SELECT tipo_doc_fiscale_id FROM tmp_refs_ffg),
      p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_ffg),
      p_valuta_id                   => (SELECT valuta_id FROM tmp_refs_ffg),
      p_fattura_figlia_id           => (SELECT id FROM tmp_figlia),
      p_tipo_fondo_fattura_id       => (SELECT tipo_fondo_id FROM tmp_refs_ffg)
    );

SELECT is(
    (SELECT string_agg(x.stato, '|' ORDER BY x.ord)
       FROM (
         SELECT 1 AS ord, s.stato
           FROM vendite.fatture_fondi_fattura_source s
          WHERE s.fattura_sorgente_id = (SELECT id FROM tmp_src_c_cap)
         UNION ALL
         SELECT 2 AS ord, s.stato
           FROM vendite.fatture_fondi_fattura_source s
          WHERE s.fattura_sorgente_id = (SELECT id FROM tmp_src_c_ctrl)
       ) x),
    'DISPONIBILE|ASSEGNATO',
    'D-3b: il fondo non piu'' capiente NON viene applicato, quello capiente si'''
  );

-- ============================================================
-- 28) D-10 — il vocabolario dei motivi e' chiuso
-- ============================================================
-- ⚠️ Su una VISTA non esiste il CHECK di colonna che il piano prevedeva
--    (PostgreSQL non ne ha): il vocabolario e' chiuso per costruzione, e il
--    presidio contro un quinto valore aggiunto di nascosto e' questo test.
--    Si asserisce l'INSIEME dei motivi, non la presenza dei quattro: un
--    valore in piu' deve far diventare rosso il file.
SELECT is(
    (SELECT string_agg(DISTINCT v.motivo, ',' ORDER BY v.motivo)
       FROM vendite.vw_fondi_fattura_da_decidere v
      WHERE v.fattura_sorgente_id IN (
        SELECT id FROM tmp_src_c_prop
        UNION ALL SELECT id FROM tmp_src_c_nc
        UNION ALL SELECT id FROM tmp_src_c_noutil
        UNION ALL SELECT id FROM tmp_src_c_cap
        UNION ALL SELECT id FROM tmp_src_c_ctrl)),
    'IMPORTO_NON_CORRISPONDENTE,NON_PIU_CAPIENTE,PROPOSTA_SENZA_ATTO,UTILITY_NON_ATTRIBUIBILE',
    'D-10: i motivi dell''elenco sono esattamente i quattro previsti'
  );

-- ============================================================
-- Cleanup
-- ============================================================
-- ⚠️ Dal 2026-09-14 (D17) il DELETE di una riga contabile passa dal guard del
--    contenuto della distinta: sotto una CHIUSA o una GENERATA e' rifiutato.
--    Questo cleanup e' un passaggio tecnico e lo dichiara con la stessa GUC
--    che usa la madre del giro dei fondi (fn_cancella_fondo_fattura); il
--    ROLLBACK farebbe comunque il lavoro.
SELECT set_config('zeroerp.allow_contabile_riga_delete_override', 'on', true);
DELETE FROM pagamenti.vendite_contabili_righe
 WHERE id IN (SELECT id FROM tmp_righe_ffg);

DELETE FROM vendite.fatture_fondi_fattura
 WHERE fattura_id IN (SELECT id FROM tmp_figlia);

DELETE FROM vendite.fatture_fondi_fattura_source
 WHERE fattura_sorgente_id IN (
   SELECT id FROM tmp_src_pos
   UNION ALL SELECT id FROM tmp_src_neg
   UNION ALL SELECT id FROM tmp_src_eme
   UNION ALL SELECT id FROM tmp_src_term
   UNION ALL SELECT id FROM tmp_src_zero
   UNION ALL SELECT id FROM tmp_src_c_prop
   UNION ALL SELECT id FROM tmp_src_c_nc
   UNION ALL SELECT id FROM tmp_src_c_noutil
   UNION ALL SELECT id FROM tmp_src_c_cap
   UNION ALL SELECT id FROM tmp_src_c_ctrl);

DELETE FROM vendite.fatture
 WHERE id IN (
   SELECT id FROM tmp_src_pos
   UNION ALL SELECT id FROM tmp_src_neg
   UNION ALL SELECT id FROM tmp_src_eme
   UNION ALL SELECT id FROM tmp_src_term
   UNION ALL SELECT id FROM tmp_src_zero
   UNION ALL SELECT id FROM tmp_src_c_prop
   UNION ALL SELECT id FROM tmp_src_c_nc
   UNION ALL SELECT id FROM tmp_src_c_noutil
   UNION ALL SELECT id FROM tmp_src_c_cap
   UNION ALL SELECT id FROM tmp_src_c_ctrl
   UNION ALL SELECT id FROM tmp_figlia);

-- ⚠️ Il conteggio guarda anche la VISTA: se una riga sopravvivesse al
--    cleanup, l'elenco continuerebbe a mostrarla — ed e' il modo in cui una
--    fixture dimenticata contamina la corsa successiva.
SELECT is(
    (SELECT count(*)::INTEGER
       FROM vendite.fatture_fondi_fattura_source s
      WHERE s.fattura_sorgente_id IN (
        SELECT id FROM tmp_src_pos
        UNION ALL SELECT id FROM tmp_src_neg
        UNION ALL SELECT id FROM tmp_src_eme
        UNION ALL SELECT id FROM tmp_src_term
        UNION ALL SELECT id FROM tmp_src_zero
        UNION ALL SELECT id FROM tmp_src_c_prop
        UNION ALL SELECT id FROM tmp_src_c_nc
        UNION ALL SELECT id FROM tmp_src_c_noutil
        UNION ALL SELECT id FROM tmp_src_c_cap
        UNION ALL SELECT id FROM tmp_src_c_ctrl))
    + (SELECT count(*)::INTEGER FROM vendite.vw_fondi_fattura_da_decidere v
        WHERE v.fattura_sorgente_id IN (
          SELECT id FROM tmp_src_c_prop
          UNION ALL SELECT id FROM tmp_src_c_nc
          UNION ALL SELECT id FROM tmp_src_c_noutil
          UNION ALL SELECT id FROM tmp_src_c_cap)),
    0,
    'Cleanup completato'
  );

SELECT * FROM finish();
ROLLBACK;
