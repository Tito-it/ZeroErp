-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: anagrafiche.soggetti.split_payment / .cliente_pa   (I0 / D8)
-- ------------------------------------------------------------
-- Elenco test (plan 5):
-- 1) split_payment e' NOT NULL
-- 2) cliente_pa e' NOT NULL
-- 3) ⭐ il CHECK morde: un valore fuori da ('S','N') e' respinto  (23514)
-- 4) 'S' e 'N' passano entrambi
-- 5) ⭐ un soggetto nuovo nasce a 'N' su entrambe                 (default)
--
-- Scopo:
--   Le due colonne dicono CHI VERSA l'imposta all'erario, non quale aliquota si
--   applica (D4): finiscono in vendite.fatture_righe.split_payment e nel
--   raggruppamento di vendite.fatture_riepiloghi_iva, che esistono gia'.
--
--   ⭐ IL TEST 3 E' QUELLO CHE VALE, e sembra burocrazia sullo schema finche'
--   non si guarda cosa protegge. Il dominio e' `character(1)` con 'S'/'N', non
--   un boolean: senza il CHECK la colonna accetterebbe 'Y', 't', '1' o uno
--   spazio, e ognuno di quei valori si comporterebbe come «non applicare lo
--   split» al primo confronto `= 'S'` — cioe' come un errore FISCALE silenzioso,
--   nella direzione peggiore. La forma char('S','N') e' quella dell'origine
--   (anagrafiche.clienti) ed e' stata tenuta apposta: cambiare tipo nello stesso
--   passo in cui si cambia sede avrebbe reso il travaso qualcosa di diverso da
--   una copia.
--
--   ⚠️ Il default 'N' (test 5) e' la direzione giusta qui, ed e' l'opposto di
--   quella scelta per congela_fiscale: li' un dato mancante deve BLOCCARE, qui
--   un soggetto di cui nessuno ha detto nulla NON e' in scissione dei pagamenti
--   — dichiararlo tale d'ufficio produrrebbe fatture sbagliate su tutta
--   l'anagrafica. La domanda «qual e' la direzione sicura?» si rifa' ogni volta,
--   non si eredita.
--
--   Piano: brief-db-be-iva-risolutore-e-regime-cliente.md
--     D8 / I0 · changeSet 20260829-14
--   Rev 2026-10-10: la fixture e' un ente (ENC). Chi puo' accendere i flag
--   (per natura) lo misura test-soggetti-regime-pa-v1.sql.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: il test gira come l'applicazione, con la RLS attiva.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI — ⭐ E QUI NON VANNO IN TESTA.
--   La regola e' «dove l'UNITA' DI LAVORO e' completa», non «sempre all'inizio».
--   anagrafiche.soggetti ha un vincolo differito che pretende almeno un recapito
--   valido, e la fixture crea il soggetto in un'istruzione e il suo contatto in
--   quella dopo: con SET CONSTRAINTS in testa il vincolo scatta A META' STRADA e
--   il test muore nella fixture — cioe' non verifica niente, che e' il modo
--   peggiore di fallire. Sta quindi subito dopo la coppia, e comunque PRIMA
--   delle asserzioni che scrivono.
--   ⛔ E LA FINESTRA SI DICHIARA: la riga di contesto qui sopra esce con i
--   vincoli IMMEDIATE (rev 20260921-18, come ogni helper pgTAP). Fino al
--   21-09 lo faceva solo sul database da zero, dove costruisce il mondo —
--   e li' questo file sarebbe morto all'INSERT del soggetto su «Il soggetto
--   non ha contatti validi» (provato sullo scratch forzando quel ramo; in CI
--   lo mascherava un altro file che committa un operatore prima di questo).
--   Contare sulla finestra di DEFAULT e' contare su cio' che nessuno ha
--   promesso: la si riapre, e il file dice da se' cosa vuole.
SET CONSTRAINTS ALL DEFERRED;

SELECT plan(5);

SELECT col_not_null('anagrafiche', 'soggetti', 'split_payment',
    'split_payment e'' NOT NULL');
SELECT col_not_null('anagrafiche', 'soggetti', 'cliente_pa',
    'cliente_pa e'' NOT NULL');

-- ============================================================
-- Fixture: un ENTE, cioe' una natura che ammette entrambi i flag
-- ============================================================
-- ⭐ Rev 2026-10-10 (brief-db-dati-fiscali-e-societari-del-soggetto, A-3/A-5):
--   fino a ieri il soggetto nasceva SENZA natura, con un CF di persona fisica.
--   Da trgfn_soggetti_guard_regime_pa (20261010-86) un flag a 'S' senza natura e'
--   rifiutato, e su una persona fisica e' rifiutato sempre: il test 4 sarebbe
--   morto sul guard e non sul CHECK. Un ente (ENC) ammette cliente_pa e
--   split_payment (CSV, A-2), quindi qui si misura solo il vocabolario S/N.
--   Il builder chiude da se' la finestra differita (indirizzi, contatti, dati
--   societari) e non nomina le due colonne: e' il caso del test 5.
CREATE TEMP TABLE tmp_sp_sogg AS
SELECT dbops.fn_pgtap_crea_soggetto_pg(
           'PGTAP Split Payment ente',
           p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio
                                             WHERE codice_interno = 'ENC')::integer) AS id;

-- Il builder esce IMMEDIATE: la saga del soggetto e' gia' verificata.
SET CONSTRAINTS ALL IMMEDIATE;

-- ============================================================
-- 3) ⭐ Il CHECK morde
-- ============================================================
-- ⚠️ SQLSTATE esplicito: 23514 e' il CHECK. Senza, l'asserzione accetterebbe
--   qualunque errore — compreso un permesso negato che non c'entra niente.
SELECT throws_ok(
    format('UPDATE anagrafiche.soggetti SET split_payment = ''Y'' WHERE id = %L',
           (SELECT id FROM tmp_sp_sogg)),
    '23514',
    NULL,
    'Un valore fuori da (''S'',''N'') e'' respinto dal CHECK'
  );

-- ============================================================
-- 4) I due valori legittimi passano entrambi
-- ============================================================
SELECT lives_ok(
    format('UPDATE anagrafiche.soggetti SET split_payment = ''S'', cliente_pa = ''S'' WHERE id = %L;'
           'UPDATE anagrafiche.soggetti SET split_payment = ''N'', cliente_pa = ''N'' WHERE id = %L',
           (SELECT id FROM tmp_sp_sogg), (SELECT id FROM tmp_sp_sogg)),
    '''S'' e ''N'' passano entrambi'
  );

-- ============================================================
-- 5) ⭐ Il default: un soggetto nuovo NON e' in scissione
-- ============================================================
-- Si guarda cosa SUCCEDE a una riga scritta da chi non sa che le colonne
-- esistono — non il catalogo. E' il caso che il default protegge.
SELECT is(
    (SELECT split_payment || cliente_pa
       FROM anagrafiche.soggetti
      WHERE id = (SELECT id FROM tmp_sp_sogg)),
    'NN',
    'Un soggetto scritto senza nominare le colonne nasce NON in scissione e NON PA'
  );

SELECT * FROM finish();
ROLLBACK;
