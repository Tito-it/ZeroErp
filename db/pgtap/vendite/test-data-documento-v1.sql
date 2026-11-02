-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la DATA DEL DOCUMENTO — cantiere numerazione-data-documento (2026-08-25)
--       script.fn_data_operativa · vendite.fn_calcola_data_documento
--       vendite.fn_imposta_data_documento_lotto
--       vendite.trgfn_fatture_guard_data_numerata
-- ------------------------------------------------------------
-- Indice test (1..15)
--  1) fixture: due registri di prova (OGGI e FINE_MESE_COMPETENZA) + una fattura
--  2) fn_data_operativa risponde nel fuso DELL'AZIENDA, non in quello di sessione
--  3) fn_data_operativa: parametro VUOTO -> solleva
--  4) fuso NON riconosciuto -> rifiutato ALLA SCRITTURA dal registro (rev 2026-10-08)
--  4b) ... anche una stringa POSIX che AT TIME ZONE accetterebbe ('UTC+1')
--  4c) rete di sicurezza: valore passato col registro spento -> la funzione
--      solleva, e la frase nomina il valore
--  5) fn_data_operativa: parametro ASSENTE -> solleva
--  6) fn_calcola_data_documento, politica OGGI
--  7) fn_calcola_data_documento, FINE_MESE_COMPETENZA -> ultimo del mese di competenza
--  8) la data DICHIARATA sul lotto vince su ENTRAMBE le politiche
--  9) FINE_MESE_COMPETENZA senza competenza -> solleva (nessun ripiego su oggi)
-- 10) fn_imposta_data_documento_lotto: scrive la data e RIGENERA il piano rate
-- 11) ... e la prima rata si e' davvero spostata
-- 12) DB-14: su una fattura NON numerata la data si cambia (controprova, prima della numerazione)
-- 13) fn_imposta_data_documento_lotto: le fatture gia' numerate si SALTANO
-- 14) DB-14: cambiare la data di una fattura NUMERATA -> rifiutato (P0001)
-- 15) DB-14: ... e la frase nomina il NUMERO del documento
-- ------------------------------------------------------------
-- Scopo:
--  - la data di un documento non e' piu' `current_date` catturato alla
--    generazione della bozza nel fuso di chi chiama, ma una REGOLA: la politica
--    del registro, che la data dichiarata sul lotto puo' scavalcare;
--  - dichiararla su un lotto rigenera i piani rate, perche' le scadenze si
--    calcolano da `fatture.data` e il guard D-K non se ne accorgerebbe (verifica
--    la SOMMA delle rate, che non cambia);
--  - da quando un documento ha un numero, la sua data non si tocca piu'.
--
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): attivita', lotto ed
--   emittente dei registri si COSTRUISCONO. Prima si pescavano «la prima
--   attivita'», «l'ultimo lotto DRAFT» e «il primo emittente attivo»: su un
--   database ricostruito da zero non ci sono, e il file moriva nella fixture. Ora
--   la commessa emittibile la fa dbops.fn_pgtap_crea_commessa (mondo e contesto
--   compresi), il lotto DRAFT la sua madre, l'attivita' il PULL vero; l'emittente
--   dei due registri di prova e' quello del mondo.
-- rev 2026-10-24 (brief-modello-documento-vendita R-3/R-4): la sorgente ROOT la
--   scrive il builder della commessa (p_con_sorgente_root), non piu' un INSERT
--   del test; il lotto DRAFT nasce da dbops.fn_pgtap_crea_lotto, del cliente
--   (p_del_cliente) e col tipo documento della riga di commessa, come prima lo
--   faceva la madre chiamata col billing account. Asserzioni invariate.
-- ⚠️ QUESTO FILE NON PROVA IL CANCELLO DI MONOTONIA: quello vive in
--   fn_get_next_progressivo ed e' collaudato in test-registri-progressivi.sql.
--   Qui si prova solo la sua ANTICAMERA dentro fn_imposta_data_documento_lotto.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Scattano al COMMIT, che qui non arriva mai (si chiude in ROLLBACK): senza,
--   il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS
-- attiva), non come owner.
-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_commessa (rev
--   2026-10-24), sull'operatore dell'azienda
--   che costruisce (fn_pgtap_crea_mondo_cliente, ramo «nessun contesto»).
CREATE TEMP TABLE tmp_ddoc_comm AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('data documento', 'PRONTA_FATTURAZIONE',
                                           p_con_sorgente_root => true);

-- ⚠️ La sessione si forza in UTC APPOSTA: e' il fuso in cui si connette Django
--   (USE_TZ senza TIME_ZONE in DATABASES), cioe' quello che produceva il
--   difetto. Se fn_data_operativa leggesse il fuso della sessione invece di
--   quello dell'azienda, il test 2 lo vedrebbe.
SET LOCAL TimeZone = 'UTC';

SELECT plan(17);

-- ============================================================
-- 1) Fixture
-- ============================================================
-- ⚠️ Il pull PRETENDE una sorgente ROOT: la scrive il builder
--   (p_con_sorgente_root, sorgente COMMESSA, chiave = id della commessa).

-- ⚠️ Solo un lotto in DRAFT: la fattura nasce in DRAFT e il guard di coerenza
--   pretende che il lotto sia nello stesso stato. Lo da' dbops.fn_pgtap_crea_lotto
--   (madre sotto), nello stato iniziale, del cliente e col tipo documento della
--   riga di commessa; ed e' SOLO del test, quindi il 13 conta la fattura del test.
CREATE TEMP TABLE tmp_ddoc_lotto AS
SELECT l.lotto_id
  FROM (SELECT c.billing_account_id, ca.tipo_doc_fiscale_id
          FROM tmp_ddoc_comm c
          JOIN vendite.commesse_attivita ca ON ca.id = c.attivita_id) r,
       dbops.fn_pgtap_crea_lotto('data documento', 'DRAFT', r.billing_account_id,
                                 r.tipo_doc_fiscale_id, p_del_cliente => true) l;

-- L'attivita' fatturabile nasce dal PULL vero, col marchio del lotto.
CREATE TEMP TABLE tmp_ddoc_pull AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
         p_commessa_id   => (SELECT commessa_id FROM tmp_ddoc_comm),
         p_emit_batch_id => (SELECT fl.lock_batch_id FROM vendite.fatturazione_lotti fl
                              WHERE fl.id = (SELECT lotto_id FROM tmp_ddoc_lotto)));

CREATE TEMP TABLE tmp_ddoc_refs AS
SELECT af.id AS attivita_id, l.lotto_id
  FROM vendite.attivita_fatturabili af, tmp_ddoc_lotto l
 WHERE af.commessa_attivita_id = (SELECT attivita_id FROM tmp_ddoc_comm);

-- Due registri di prova, uno per politica. ⭐ Si creano invece di usare quelli
-- di catalogo: cosi' il test non dipende dal seed, che e' una DECISIONE di
-- configurazione e puo' cambiare senza che questo file debba accorgersene.
-- ⛔ L'emittente del registro e' NOT NULL dal 2026-08-30 (C1-2, 20260830-11):
--   un registro di numerazione appartiene a UN emittente. Questo file prova la
--   politica della data e i pavimenti, non il perimetro: ne serve uno, ed e'
--   quello del mondo costruito (rev 2026-10-24: prima «il primo attivo per id»).
CREATE TEMP TABLE tmp_ddoc_ef AS
SELECT c.emittente_soggetto_ruolo_id AS emittente_id
  FROM tmp_ddoc_comm c;

CREATE TEMP TABLE tmp_ddoc_reg AS
WITH ins AS (
  INSERT INTO vendite.registri_fatturazione
      (codice, descrizione, reset_policy, attivo, politica_data_documento,
       emittente_soggetto_ruolo_id, meta)
  VALUES ('RDD_OGGI',    'Registro prova OGGI',     'ANNUALE', true, 'OGGI',
          (SELECT emittente_id FROM tmp_ddoc_ef), jsonb_build_object('test_scope', 'pgtap_data_documento')),
         ('RDD_FINEMESE','Registro prova fine mese','ANNUALE', true, 'FINE_MESE_COMPETENZA',
          (SELECT emittente_id FROM tmp_ddoc_ef), jsonb_build_object('test_scope', 'pgtap_data_documento'))
  RETURNING id, codice)
SELECT max(id) FILTER (WHERE codice = 'RDD_OGGI')     AS reg_oggi,
       max(id) FILTER (WHERE codice = 'RDD_FINEMESE') AS reg_finemese
  FROM ins;

-- La fattura si crea con il creatore applicativo, che la mette in DRAFT: cosi'
-- la fixture attraversa la stessa porta del giro reale.
CREATE TEMP TABLE tmp_ddoc_f AS
SELECT vendite.fn_get_or_create_fattura_header(
         (SELECT lotto_id    FROM tmp_ddoc_refs),
         (SELECT attivita_id FROM tmp_ddoc_refs)) AS id;

SELECT ok(
  (SELECT reg_oggi FROM tmp_ddoc_reg) IS NOT NULL
  AND (SELECT reg_finemese FROM tmp_ddoc_reg) IS NOT NULL
  AND (SELECT id FROM tmp_ddoc_f) IS NOT NULL
  AND (SELECT count(*) FROM tmp_ddoc_refs) = 1
  AND (SELECT inserted_rows FROM tmp_ddoc_pull) = 1,
  '1) Fixture: due registri di prova e una fattura in DRAFT');

-- ============================================================
-- 2..5) script.fn_data_operativa
-- ============================================================
-- ⭐ La sessione e' in UTC (vedi il preambolo). La funzione deve rispondere la
--   data nel fuso dell'AZIENDA: se rispondesse quella di sessione, questo
--   confronto fallirebbe ogni volta che le due date divergono — cioe' fra la
--   mezzanotte e le 02:00 di Roma, che e' esattamente la finestra in cui il
--   difetto si manifestava.
SELECT is(
  script.fn_data_operativa(),
  (now() AT TIME ZONE (SELECT default_value FROM config.parameters
                        WHERE code = 'SYSTEM_FUSO_ORARIO'))::date,
  '2) fn_data_operativa risponde nel fuso dell''azienda, non in quello di sessione');

-- ⚠️ I tre rami di guasto si provano uno alla volta e si RIPRISTINA subito: il
--   DEFAULT di vendite.fatture.data chiama questa funzione, quindi lasciare il
--   parametro rotto farebbe fallire qualunque INSERT successiva della fixture.
UPDATE config.parameters SET default_value = '' WHERE code = 'SYSTEM_FUSO_ORARIO';
SELECT throws_ok(
  $$ SELECT script.fn_data_operativa() $$,
  'P0001', NULL,
  '3) fn_data_operativa: parametro VUOTO -> solleva (nessun ripiego a UTC)');

-- ⭐ rev 2026-10-08 (20261008-20): il fuso si VALIDA QUANDO SI SCRIVE, dal
--   registro config.parameter_fk_surrogate (riga 7 -> pg_timezone_names), non
--   piu' a ogni chiamata della funzione (~8 ms, per riga nelle viste).
UPDATE config.parameters SET default_value = 'Europe/Rome' WHERE code = 'SYSTEM_FUSO_ORARIO';
SELECT throws_like(
  $$ UPDATE config.parameters SET default_value = 'Europe/Roma'
      WHERE code = 'SYSTEM_FUSO_ORARIO' $$,
  '%Europe/Roma%',
  '4) fuso non riconosciuto -> rifiutato alla scrittura, e la frase nomina il valore');

-- ⛔ E' il caso per cui la validazione NON puo' stare in un EXCEPTION attorno ad
--   AT TIME ZONE: 'UTC+1' e' una stringa POSIX che AT TIME ZONE accetta (col
--   segno rovesciato: vuol dire UTC-1), cioe' una data plausibile e sbagliata.
SELECT throws_like(
  $$ UPDATE config.parameters SET default_value = 'UTC+1'
      WHERE code = 'SYSTEM_FUSO_ORARIO' $$,
  '%UTC+1%',
  '4b) una stringa POSIX (UTC+1) e'' rifiutata alla scrittura, anche se AT TIME ZONE la accetterebbe');

-- La rete di sicurezza della funzione: un valore che il sistema non riconosce
-- (qui passato spegnendo la riga del registro) solleva l'errore di DOMINIO,
-- non un 22023 grezzo. Si riaccende subito.
UPDATE config.parameter_fk_surrogate SET enabled = false WHERE code_pattern = 'SYSTEM_FUSO_ORARIO';
UPDATE config.parameters SET default_value = 'Europe/Roma' WHERE code = 'SYSTEM_FUSO_ORARIO';
SELECT throws_like(
  $$ SELECT script.fn_data_operativa() $$,
  '%Europe/Roma%',
  '4c) rete di sicurezza: fuso non riconosciuto dal sistema -> errore di dominio che nomina il valore');
UPDATE config.parameters SET default_value = 'Europe/Rome' WHERE code = 'SYSTEM_FUSO_ORARIO';
UPDATE config.parameter_fk_surrogate SET enabled = true WHERE code_pattern = 'SYSTEM_FUSO_ORARIO';

DELETE FROM config.parameters WHERE code = 'SYSTEM_FUSO_ORARIO';
SELECT throws_ok(
  $$ SELECT script.fn_data_operativa() $$,
  'P0001', NULL,
  '5) fn_data_operativa: parametro ASSENTE -> solleva');

-- Ripristino: da qui in poi la funzione deve tornare a rispondere.
-- 2026-10-25 (brief-db-parametri-senza-override): ammette_override e' NOT NULL senza
-- DEFAULT, e il NOT NULL si giudica sulla riga proposta anche con ON CONFLICT. Il fuso
-- vale per tutti: false, come nel CSV.
INSERT INTO config.parameters (id, code, default_value, description, ammette_override, tipo_valore)
VALUES (54, 'SYSTEM_FUSO_ORARIO', 'Europe/Rome', 'ripristino fixture pgTAP', false, 'TESTO')
ON CONFLICT (id) DO UPDATE SET default_value = 'Europe/Rome';

-- ============================================================
-- 6..9) vendite.fn_calcola_data_documento
-- ============================================================
SELECT is(
  vendite.fn_calcola_data_documento(
      (SELECT reg_oggi FROM tmp_ddoc_reg), date '2026-07-01', NULL),
  script.fn_data_operativa(),
  '6) politica OGGI -> la data operativa (la competenza non c''entra)');

-- ⚠️ rev 2026-08-26: p_serie e' il TERZO argomento ed e' OBBLIGATORIO — senza
--   di essa il clamp leggerebbe il contatore di un'altra sequenza. NULL
--   significa «la serie di default del registro».
-- ⭐ Su politica OGGI il clamp del limite di emissione e' un NO-OP per
--   costruzione: la politica da' data_operativa() e il pavimento e'
--   data_operativa() - giorni. Questo test resta quindi identico a prima.

-- ⛔ LA COMPETENZA E' RELATIVA A OGGI, E NON E' PIGRIZIA. Con una competenza
--   LETTERALE (era `2026-07-01` -> atteso `2026-07-31`) questo test diventava
--   rosso da solo il 16/08/2026: da quel giorno il permesso della differita per
--   luglio e' scaduto, e il clamp del limite di emissione risponde OGGI invece
--   della fine competenza. La proprieta' da provare qui e' «la politica torna
--   l'ultimo giorno del mese di competenza», e si prova sul mese CORRENTE —
--   dove il permesso e' aperto per costruzione (oggi e' sempre prima del 15 del
--   mese successivo) e il clamp non entra in gioco.
--   ⚠️ Il caso opposto — permesso SCADUTO, quindi clamp a oggi — vive in
--   test-limite-emissione-v1.sql, che e' il file di quel presidio.
SELECT is(
  vendite.fn_calcola_data_documento(
      (SELECT reg_finemese FROM tmp_ddoc_reg),
      date_trunc('month', script.fn_data_operativa())::date,
      NULL),
  (date_trunc('month', script.fn_data_operativa()) + interval '1 month - 1 day')::date,
  '7) politica FINE_MESE_COMPETENZA: competenza del mese corrente -> ultimo giorno di quel mese');

-- ⭐ La dichiarazione vince su ENTRAMBE, ed e' il senso della decisione «una
--   data sola per l'intero atto»: un lotto puo' contenere documenti di registri
--   con politiche diverse, e la data dichiarata deve valere per tutti.
SELECT is(
  ARRAY[
    vendite.fn_calcola_data_documento(
        (SELECT reg_oggi FROM tmp_ddoc_reg),     date '2026-07-01', NULL, date '2026-08-10'),
    vendite.fn_calcola_data_documento(
        (SELECT reg_finemese FROM tmp_ddoc_reg), date '2026-07-01', NULL, date '2026-08-10')
  ],
  ARRAY[date '2026-08-10', date '2026-08-10'],
  '8) la data DICHIARATA vince su entrambe le politiche');

-- ⛔ E rev 2026-08-26: la dichiarata vince ANCHE SUI DUE PAVIMENTI, e non e' una
--   svista. Il clamp vale per il DEFAULT, il cancello vale per la
--   DICHIARAZIONE: spostare in silenzio una scelta esplicita e' la classe di
--   difetto che il cantiere della numerazione ha passato tre giorni a togliere.
--   Il 10/08/2026 e' sotto il limite di emissione di oggi, e questo test lo
--   pretende INVARIATO.

-- ⛔ Nessun ripiego su oggi: una data plausibile e sbagliata su un documento
--   fiscale non la nota nessuno, e quando la si nota il numero e' gia' stato
--   consumato.
SELECT throws_ok(
  format($$ SELECT vendite.fn_calcola_data_documento(%s, NULL, NULL) $$,
         (SELECT reg_finemese FROM tmp_ddoc_reg)),
  'P0001', NULL,
  '9) FINE_MESE_COMPETENZA senza competenza -> solleva, non ripiega su oggi');

-- ============================================================
-- 10..12) vendite.fn_imposta_data_documento_lotto
-- ============================================================
-- La fattura ha bisogno di un piano rate perche' il punto 4 della madre abbia
-- qualcosa da rigenerare: termine + totale, poi il generatore.
UPDATE vendite.fatture
   SET termine_pagamento_id = (SELECT tp.id FROM config.termini_pagamento tp
                                WHERE tp.attivo IS TRUE ORDER BY tp.id LIMIT 1),
       totale_a_pagare = 120.00,
       data = date '2026-08-25'
 WHERE id = (SELECT id FROM tmp_ddoc_f);

SELECT vendite.fn_genera_scadenze_fattura((SELECT id FROM tmp_ddoc_f));

CREATE TEMP TABLE tmp_ddoc_prima AS
SELECT min(s.data_scadenza) AS prima_rata
  FROM vendite.fatture_scadenze s WHERE s.fattura_id = (SELECT id FROM tmp_ddoc_f);

-- ⚠️ La data dichiarata e' nel FUTURO rispetto al pavimento del sezionale: la
--   madre ha un guard sul minimo, e una data bassa verrebbe rifiutata per una
--   ragione che non e' quella che questo test vuole misurare.
CREATE TEMP TABLE tmp_ddoc_esito AS
SELECT * FROM vendite.fn_imposta_data_documento_lotto(
                (SELECT lotto_id FROM tmp_ddoc_refs), date '2027-06-15');

SELECT is(
  (SELECT f.data FROM vendite.fatture f WHERE f.id = (SELECT id FROM tmp_ddoc_f)),
  date '2027-06-15',
  '10) fn_imposta_data_documento_lotto scrive la data sulla fattura non numerata');

-- ⭐ IL PUNTO 4: le scadenze si calcolano da f.data, e il guard D-K verifica la
--   SOMMA delle rate — che non cambia. Se la rigenerazione saltasse, il
--   documento passerebbe con scadenze calcolate su una data che non porta piu':
--   un difetto che non solleva niente. Questo e' l'unico posto in cui si vede.
SELECT isnt(
  (SELECT min(s.data_scadenza) FROM vendite.fatture_scadenze s
    WHERE s.fattura_id = (SELECT id FROM tmp_ddoc_f)),
  (SELECT prima_rata FROM tmp_ddoc_prima),
  '11) ... e il piano rate e'' stato RIGENERATO: la prima rata si e'' spostata');

-- Controprova, PRIMA della numerazione: senza numero la data si cambia. ⭐ Serve
--   a distinguere «il guard funziona» da «il guard blocca tutto», che sarebbe
--   verde uguale sul test 14.
-- ⚠️ Rev 2026-10-05: stava in coda e TOGLIEVA il numero alla fattura appena
--   numerata (numero, anno, serie a NULL) per poi cambiarle la data. Dal
--   20261004-80 (vendite.trgfn_fatture_guard_numero_fiscale, Q-4 di
--   brief-db-esclusioni-implicite) la regola lo vieta — una fattura numerata non
--   cambia identita' fiscale — e il file moriva li'. La domanda e' la stessa;
--   la si fa sulla fattura quando non e' ancora numerata.
-- ⚠️ Una data diversa da quella dei test 14-15 (2027-01-01): li' deve essere un
--   CAMBIO, e un UPDATE allo stesso valore non lo e'.
UPDATE vendite.fatture SET data = date '2027-02-01'
 WHERE id = (SELECT id FROM tmp_ddoc_f);

SELECT is(
  (SELECT f.data FROM vendite.fatture f WHERE f.id = (SELECT id FROM tmp_ddoc_f)),
  date '2027-02-01',
  '12) su una fattura NON numerata la data si cambia (il guard non blocca tutto)');

-- Adesso la fattura diventa numerata: la madre deve saltarla e contarla, non
-- fallire. ⚠️ Il caso «lotto numerato a meta'» esiste nei dati veri.
UPDATE vendite.fatture
   SET numero = 999001, anno = 2027, serie = 'PGT'
 WHERE id = (SELECT id FROM tmp_ddoc_f);

SELECT is(
  (SELECT saltate_numerate FROM vendite.fn_imposta_data_documento_lotto(
             (SELECT lotto_id FROM tmp_ddoc_refs), date '2027-07-20')),
  1,
  '13) le fatture gia'' numerate si SALTANO e si contano (il lotto non fallisce)');

-- ============================================================
-- 14..15) DB-14: la data di una fattura numerata e' immutabile
-- ============================================================
SELECT throws_ok(
  format($$ UPDATE vendite.fatture SET data = date '2027-01-01' WHERE id = %s $$,
         (SELECT id FROM tmp_ddoc_f)),
  'P0001', NULL,
  '14) cambiare la data di una fattura NUMERATA -> rifiutato');

-- ⚠️ `throws_like` perche' la frase e' la posta in gioco: deve dire CHE COSA
--   blocca (il numero), non «colonna non modificabile».
SELECT throws_like(
  format($$ UPDATE vendite.fatture SET data = date '2027-01-01' WHERE id = %s $$,
         (SELECT id FROM tmp_ddoc_f)),
  '%999001%',
  '15) ... e la frase nomina il NUMERO del documento');

SELECT * FROM finish();

ROLLBACK;
