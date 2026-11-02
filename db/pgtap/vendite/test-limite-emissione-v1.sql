-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: IL LIMITE DI EMISSIONE — cantiere limite-emissione-e-data-verificata
--       vendite.fn_get_limite_emissione_default
--       vendite.fn_get_pavimento_emissione
--       vendite.fn_get_pavimento_data_documento
--       vendite.fn_calcola_data_documento (il CLAMP alla nascita)
--       vendite.fn_get_next_progressivo   (il CANCELLO, ramo EMISSIONE)
--       i CHECK di vendite.registri_fatturazione
-- ------------------------------------------------------------
-- Indice test (1..19)
--  1) fixture: cinque registri di prova
--  2) OGGI: il pavimento e' data_operativa - giorni (default globale)
--  3) ... e l'override sul registro vince sul default globale
--  4) DIFFERITA con permesso APERTO -> LEAST(oggi - giorni, fine competenza)
--  5) DIFFERITA con permesso SCADUTO -> oggi - giorni   (⛔ non «oggi»)
--  6) BOUNDARY: scadenza = OGGI -> il permesso e' ancora aperto (<=)
--  7) BOUNDARY: scadenza = IERI -> il permesso e' chiuso
--  8) la composta: sequenza vergine -> origine EMISSIONE
--  9) ... e con una sequenza piu' alta -> origine SEQUENZA
-- 10) CLAMP: differita IN RITARDO nasce con la data di OGGI
-- 11) CLAMP: differita IN TERMINE nasce a fine competenza (nessun clamp)
-- 12) ⛔ la data DICHIARATA non si clampa mai
-- 13) CANCELLO: data oltre il limite -> rifiutata (P0001)
-- 14) ... e la FRASE nomina la data da cui ripartire
-- 15) CANCELLO: la data UGUALE al pavimento e' ammessa
-- 16) CHECK: giorno del mese su un registro OGGI -> rifiutato (23514)
-- 17) presidio: il CHECK di coerenza e' ancora quello scritto
-- 18) fn_get_limite_emissione_default: valore non numerico -> solleva
-- 19) cleanup completato
-- ------------------------------------------------------------
-- Scopo:
--  - un documento non deve nascere con una data che non e' piu' trasmissibile:
--    il limite di emissione e' UNA REGOLA GENERALE (non piu' di N giorni fa) con
--    un PERMESSO della sola differita (fino al giorno G del mese successivo alla
--    competenza) che SCADE;
--  - alla nascita la data calcolata si CLAMPA — e atterra su OGGI, non sul
--    pavimento, o il documento nascerebbe con margine di trasmissione zero;
--  - la data DICHIARATA da una persona non si sposta mai in silenzio: si
--    rifiuta;
--  - il cancello rifiuta con un codice SUO, distinto da quello della sequenza.
--
-- ⚠️ COSA QUESTO FILE **NON** PUO' PROVARE, ed e' scritto qui invece di essere
--   scoperto da chi verra' dopo:
--
--   a) che il cancello stia SOTTO l'advisory lock. pgTAP e' mono-sessione, il
--      lock non si contende, e spostando il controllo PRIMA del lock questo file
--      resterebbe interamente VERDE. La posizione si presidia in review.
--
--   b) ⛔ IL CLAMP AL MESE del giorno di scadenza (decisione D-6,
--      `LEAST(primo + giorno - 1, ultimo del mese)`) NON E' OSSERVABILE dal
--      comportamento pubblico, e non e' una svista del test. Il clamp puo' solo
--      ANTICIPARE una scadenza, e la scadenza conta solo quando cade nel mese
--      SUCCESSIVO alla competenza: se quel mese e' il mese corrente, sia la data
--      clampata sia quella non clampata sono >= oggi, quindi il verdetto
--      «permesso aperto» non cambia; se e' un mese passato, sono entrambe <
--      oggi. L'unica finestra in cui i due valori danno verdetti diversi e' 1-3
--      marzo con un giorno configurato > 28, cioe' tre giorni all'anno.
--      ⭐ Cio' che questo file prova e' l'ARITMETICA DELLA SCADENZA AL SUO
--      BORDO (test 6 e 7): che il confronto sia `<=` e non `<`, che e' la
--      proprieta' che si sbaglia davvero.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Scattano al COMMIT, che qui non arriva mai (si chiude in ROLLBACK): senza,
--   il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS
-- attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(19);

-- ============================================================
-- 0) Le date di riferimento, scelte UNA volta
-- ============================================================
-- ⚠️ Tutto e' RELATIVO a script.fn_data_operativa(), mai a date letterali: una
--   data letterale in un test sul limite di emissione e' una bomba a orologeria
--   — passa oggi e diventa rossa fra un mese. E' esattamente il difetto che il
--   test 7 di test-data-documento-v1.sql ha avuto per un giorno.
CREATE TEMP TABLE tmp_le_date AS
SELECT script.fn_data_operativa()                                                   AS oggi,
       -- il mese di competenza CORRENTE: il permesso e' aperto per costruzione
       -- (oggi e' sempre prima del giorno G del mese successivo)
       date_trunc('month', script.fn_data_operativa())::date                         AS comp_corrente,
       (date_trunc('month', script.fn_data_operativa())
        + interval '1 month - 1 day')::date                                          AS fine_comp_corrente,
       -- il mese scorso: serve ai due test di bordo
       (date_trunc('month', script.fn_data_operativa()) - interval '1 month')::date   AS comp_scorsa,
       -- sei mesi fa: il permesso e' scaduto per costruzione, ogni giorno
       -- dell'anno
       (date_trunc('month', script.fn_data_operativa()) - interval '6 months')::date  AS comp_vecchia,
       -- il giorno del mese di oggi: i test 6 e 7 ci costruiscono sopra una
       -- scadenza che cade ESATTAMENTE oggi e una che cade ieri
       extract(day FROM script.fn_data_operativa())::smallint                         AS giorno_oggi;

-- ============================================================
-- 1) Fixture: cinque registri di prova
-- ============================================================
-- ⭐ Si creano invece di usare quelli di catalogo: cosi' il test non dipende dal
--   seed, che e' una DECISIONE di configurazione e puo' cambiare senza che
--   questo file debba accorgersene.
-- ⚠️ Cinque e non due: il registro del CANCELLO deve avere il contatore
--   VERGINE, o il pavimento di sequenza coprirebbe quello di emissione e i test
--   13-15 proverebbero l'altro presidio senza dirlo.
-- ⛔ L'emittente del registro e' NOT NULL dal 2026-08-30 (C1-2, 20260830-11):
--   un registro di numerazione appartiene a UN emittente. Questo file prova la
--   politica della data e i pavimenti, non il perimetro: ne serve uno qualsiasi,
--   e si PRENDE dal catalogo invece di cablarne l'id.
CREATE TEMP TABLE tmp_le_ef AS
SELECT ef.soggetto_ruolo_id AS emittente_id
  FROM anagrafiche.emittenti_fiscali ef
 WHERE ef.attivo IS TRUE
 ORDER BY ef.id
 LIMIT 1;

CREATE TEMP TABLE tmp_le_reg AS
WITH ins AS (
  INSERT INTO vendite.registri_fatturazione
      (codice, descrizione, reset_policy, attivo, politica_data_documento,
       limite_emissione_giorni, limite_emissione_giorno_mese,
       emittente_soggetto_ruolo_id, meta)
  VALUES
      ('RLE_OGGI',  'Registro prova limite OGGI',      'ANNUALE', true, 'OGGI',
       12,   NULL, (SELECT emittente_id FROM tmp_le_ef), jsonb_build_object('test_scope', 'pgtap_limite_emissione')),
      ('RLE_OVER',  'Registro prova override giorni',  'ANNUALE', true, 'OGGI',
       3,    NULL, (SELECT emittente_id FROM tmp_le_ef), jsonb_build_object('test_scope', 'pgtap_limite_emissione')),
      ('RLE_DIFF',  'Registro prova differita',        'ANNUALE', true, 'FINE_MESE_COMPETENZA',
       12,   15,   (SELECT emittente_id FROM tmp_le_ef), jsonb_build_object('test_scope', 'pgtap_limite_emissione')),
      ('RLE_GATE',  'Registro prova cancello',         'ANNUALE', true, 'OGGI',
       12,   NULL, (SELECT emittente_id FROM tmp_le_ef), jsonb_build_object('test_scope', 'pgtap_limite_emissione')),
      -- ⭐ giorni = 0 NON e' un capriccio: e' cio' che rende DISCRIMINANTI i due
      --   test di bordo. Con 12 giorni, nella prima meta' del mese la fine della
      --   competenza scorsa e' PIU' RECENTE di `oggi - 12`, quindi il LEAST
      --   risponde `oggi - 12` sia a permesso aperto sia a permesso chiuso e i
      --   due test direbbero la stessa cosa. Con 0, il permesso aperto risponde
      --   la fine competenza e quello chiuso risponde oggi: sempre diversi.
      ('RLE_BORDO', 'Registro prova bordo scadenza',   'ANNUALE', true, 'FINE_MESE_COMPETENZA',
       0,    15,   (SELECT emittente_id FROM tmp_le_ef), jsonb_build_object('test_scope', 'pgtap_limite_emissione'))
  RETURNING id, codice)
SELECT max(id) FILTER (WHERE codice = 'RLE_OGGI')  AS reg_oggi,
       max(id) FILTER (WHERE codice = 'RLE_OVER')  AS reg_over,
       max(id) FILTER (WHERE codice = 'RLE_DIFF')  AS reg_diff,
       max(id) FILTER (WHERE codice = 'RLE_GATE')  AS reg_gate,
       max(id) FILTER (WHERE codice = 'RLE_BORDO') AS reg_bordo
  FROM ins;

SELECT ok(
  (SELECT reg_oggi FROM tmp_le_reg) IS NOT NULL
  AND (SELECT reg_over FROM tmp_le_reg) IS NOT NULL
  AND (SELECT reg_diff FROM tmp_le_reg) IS NOT NULL
  AND (SELECT reg_gate FROM tmp_le_reg) IS NOT NULL
  AND (SELECT reg_bordo FROM tmp_le_reg) IS NOT NULL,
  '1) Fixture: cinque registri di prova');

-- ============================================================
-- 2..3) vendite.fn_get_pavimento_emissione — politica OGGI
-- ============================================================
SELECT is(
  vendite.fn_get_pavimento_emissione((SELECT reg_oggi FROM tmp_le_reg), NULL),
  (SELECT oggi - 12 FROM tmp_le_date),
  '2) OGGI: il pavimento e'' data_operativa - giorni');

-- ⭐ L'override sul registro e' l'UNICO asse di override ammesso: il parametro
--   globale non si sovrascrive per utente o sessione, o lo stesso documento
--   avrebbe limiti diversi a seconda di chi lo genera.
SELECT is(
  vendite.fn_get_pavimento_emissione((SELECT reg_over FROM tmp_le_reg), NULL),
  (SELECT oggi - 3 FROM tmp_le_date),
  '3) l''override sul registro vince sul default globale');

-- ============================================================
-- 4..5) ... e politica FINE_MESE_COMPETENZA
-- ============================================================
-- ⭐ Permesso APERTO: la data di fine competenza resta ammessa ANCHE se e' piu'
--   vecchia del pavimento mobile. LEAST e non GREATEST: la regola generale e il
--   permesso sono due ragioni INDIPENDENTI per cui una data e' ammessa, e basta
--   che ne valga una.
SELECT is(
  vendite.fn_get_pavimento_emissione(
      (SELECT reg_diff FROM tmp_le_reg),
      (SELECT comp_corrente FROM tmp_le_date)),
  (SELECT LEAST(oggi - 12, fine_comp_corrente) FROM tmp_le_date),
  '4) DIFFERITA con permesso aperto: LEAST(oggi - giorni, fine competenza)');

-- ⛔ QUESTO E' IL RAMO B DELLA DECISIONE D-2, ed e' la scelta che si sbaglia
--   piu' facilmente: a permesso scaduto NON si torna a «solo oggi». I giorni
--   sono la regola di TUTTI i documenti, e quando un permesso IN PIU' scade non
--   ne compare uno piu' SEVERO. Se questo test diventasse `= oggi`, qualcuno
--   avrebbe riportato indietro la decisione.
SELECT is(
  vendite.fn_get_pavimento_emissione(
      (SELECT reg_diff FROM tmp_le_reg),
      (SELECT comp_vecchia FROM tmp_le_date)),
  (SELECT oggi - 12 FROM tmp_le_date),
  '5) DIFFERITA con permesso scaduto: oggi - giorni, NON «solo oggi»');

-- ============================================================
-- 6..7) Il BORDO della scadenza: `<=` e non `<`
-- ============================================================
-- ⭐ Si costruisce una scadenza che cade ESATTAMENTE oggi (competenza del mese
--   scorso + giorno del mese di oggi) e una che cade IERI. E' l'unica proprieta'
--   dell'aritmetica della scadenza che si puo' osservare in modo deterministico,
--   ed e' quella che si sbaglia: un `<` al posto di un `<=` chiuderebbe il
--   permesso un giorno prima, e nessun altro test se ne accorgerebbe.
-- ⚠️ Il primo del mese si SALTA: «ieri» sarebbe il giorno 0, che il CHECK di
--   colonna non ammette (1..31). Un test che non si puo' costruire si dichiara,
--   non si annacqua.
-- ⚠️ Sul registro RLE_BORDO, che ha `giorni = 0`: vedi la nota nella fixture.
UPDATE vendite.registri_fatturazione
   SET limite_emissione_giorno_mese = (SELECT giorno_oggi FROM tmp_le_date)
 WHERE id = (SELECT reg_bordo FROM tmp_le_reg);

SELECT CASE WHEN (SELECT giorno_oggi FROM tmp_le_date) = 1
  THEN skip('oggi e'' il primo del mese: «ieri» sarebbe il giorno 0, fuori dal CHECK', 1)
  ELSE is(
    vendite.fn_get_pavimento_emissione(
        (SELECT reg_bordo FROM tmp_le_reg),
        (SELECT comp_scorsa FROM tmp_le_date)),
    (SELECT (date_trunc('month', comp_scorsa) + interval '1 month - 1 day')::date
       FROM tmp_le_date),
    '6) scadenza = OGGI: il permesso e'' ancora APERTO (il confronto e'' <=)')
END;

UPDATE vendite.registri_fatturazione
   SET limite_emissione_giorno_mese = (SELECT giorno_oggi - 1 FROM tmp_le_date)
 WHERE id = (SELECT reg_bordo FROM tmp_le_reg)
   AND (SELECT giorno_oggi FROM tmp_le_date) > 1;

SELECT CASE WHEN (SELECT giorno_oggi FROM tmp_le_date) = 1
  THEN skip('oggi e'' il primo del mese: vedi il test 6', 1)
  ELSE is(
    vendite.fn_get_pavimento_emissione(
        (SELECT reg_bordo FROM tmp_le_reg),
        (SELECT comp_scorsa FROM tmp_le_date)),
    (SELECT oggi FROM tmp_le_date),
    '7) scadenza = IERI: il permesso e'' CHIUSO, e si ricade sulla regola generale')
END;

-- ============================================================
-- 8..9) vendite.fn_get_pavimento_data_documento: la composizione
-- ============================================================
-- Sequenza VERGINE: il pavimento di sequenza e' NULL, quindi vince l'emissione.
SELECT is(
  ARRAY[
    (SELECT pavimento::text FROM vendite.fn_get_pavimento_data_documento(
        (SELECT reg_oggi FROM tmp_le_reg), NULL, NULL)),
    (SELECT origine        FROM vendite.fn_get_pavimento_data_documento(
        (SELECT reg_oggi FROM tmp_le_reg), NULL, NULL))
  ],
  ARRAY[(SELECT (oggi - 12)::text FROM tmp_le_date), 'EMISSIONE'],
  '8) sequenza vergine: il pavimento e'' quello di emissione, origine EMISSIONE');

-- Ora si consuma un numero con la data di OGGI: il pavimento di sequenza sale a
-- oggi e supera quello di emissione (oggi - 12).
-- ⚠️ Fixture, non asserzione: alza il pavimento di sequenza a oggi. In un
--   `lives_ok` conterebbe nel plan senza verificare nessuna proprieta' di
--   questo file — e un plan che non torna e' un rosso che non insegna niente.
DO $svc$
DECLARE v_n bigint;
BEGIN
  SELECT vendite.fn_get_next_progressivo(
             (SELECT reg_oggi FROM tmp_le_reg),
             (SELECT oggi FROM tmp_le_date),
             NULL, NULL, NULL)
    INTO v_n;
END
$svc$;

SELECT is(
  ARRAY[
    (SELECT pavimento::text FROM vendite.fn_get_pavimento_data_documento(
        (SELECT reg_oggi FROM tmp_le_reg), NULL, NULL)),
    (SELECT origine        FROM vendite.fn_get_pavimento_data_documento(
        (SELECT reg_oggi FROM tmp_le_reg), NULL, NULL))
  ],
  ARRAY[(SELECT oggi::text FROM tmp_le_date), 'SEQUENZA'],
  '9) con una sequenza piu'' alta: vince lei, e origine diventa SEQUENZA');

-- ============================================================
-- 10..12) IL CLAMP alla nascita — vendite.fn_calcola_data_documento
-- ============================================================
-- ⭐ IL CUORE DEL CANTIERE. Un lotto di competenza vecchia lavorato oggi
--   nascerebbe con la data di fine di quel mese — una data che non e' piu'
--   trasmissibile. Deve nascere con la data di OGGI.
-- ⛔ E su OGGI, non sul pavimento: nascere sul pavimento e' nascere con margine
--   di trasmissione ZERO, cioe' intrasmissibile il giorno dopo.
SELECT is(
  vendite.fn_calcola_data_documento(
      (SELECT reg_diff FROM tmp_le_reg),
      (SELECT comp_vecchia FROM tmp_le_date),
      NULL),
  (SELECT oggi FROM tmp_le_date),
  '10) CLAMP: la differita in ritardo nasce con la data di OGGI');

-- ⭐ E il flusso NORMALE non si tocca: 46 lotti su 52 nascono in termine, e per
--   loro non deve cambiare niente.
SELECT is(
  vendite.fn_calcola_data_documento(
      (SELECT reg_diff FROM tmp_le_reg),
      (SELECT comp_corrente FROM tmp_le_date),
      NULL),
  (SELECT fine_comp_corrente FROM tmp_le_date),
  '11) nessun clamp sul flusso normale: la differita in termine nasce a fine competenza');

-- ⛔ LA DICHIARAZIONE NON SI SPOSTA MAI IN SILENZIO. Il clamp vale per il
--   DEFAULT, il cancello vale per la DICHIARAZIONE: se un operatore scrive una
--   data sotto il pavimento, quella data si RIFIUTA a valle — non si corregge
--   qui senza dirlo. Spostare senza dirlo una scelta esplicita e' la classe di
--   difetto che il cantiere della numerazione ha passato tre giorni a togliere.
SELECT is(
  vendite.fn_calcola_data_documento(
      (SELECT reg_diff FROM tmp_le_reg),
      (SELECT comp_vecchia FROM tmp_le_date),
      NULL,
      (SELECT oggi - 300 FROM tmp_le_date)),
  (SELECT oggi - 300 FROM tmp_le_date),
  '12) ⛔ la data DICHIARATA non si clampa, nemmeno sotto il pavimento');

-- ============================================================
-- 13..15) IL CANCELLO — ramo LIMITE DI EMISSIONE
-- ============================================================
-- ⚠️ Sul registro RLE_GATE, che ha il contatore VERGINE: senza, a rifiutare
--   sarebbe il pavimento di SEQUENZA e questo test proverebbe l'altro presidio
--   credendo di provare questo.
SELECT throws_ok(
  format($$ SELECT vendite.fn_get_next_progressivo(%s, %L::date, NULL, NULL, NULL) $$,
         (SELECT reg_gate FROM tmp_le_reg), (SELECT oggi - 60 FROM tmp_le_date)),
  'P0001', NULL,
  '13) CANCELLO: una data oltre il limite di emissione viene rifiutata (P0001)');

-- ⚠️ `throws_like` e non solo `throws_ok`: qui LA FRASE E' LA POSTA IN GIOCO.
--   E' l'unica cosa che dice all'operatore da quale data ripartire, e un test
--   che si accontenta dello SQLSTATE resterebbe verde anche se il messaggio
--   smettesse di nominare la data.
-- ⭐ E la data nominata e' il pavimento EFFETTIVO: se il messaggio nominasse un
--   altro pavimento, manderebbe l'operatore a scegliere una data che verrebbe
--   rifiutata di nuovo.
SELECT throws_like(
  format($$ SELECT vendite.fn_get_next_progressivo(%s, %L::date, NULL, NULL, NULL) $$,
         (SELECT reg_gate FROM tmp_le_reg), (SELECT oggi - 60 FROM tmp_le_date)),
  format('%%%s%%', (SELECT to_char(oggi - 12, 'DD/MM/YYYY') FROM tmp_le_date)),
  '14) ... e la FRASE nomina la data da cui ripartire');

-- ⚠️ `<` e non `<=` nel cancello: la data UGUALE al pavimento e' ammessa, ed e'
--   il caso di bordo che rende vivibile il limite — chi lavora al dodicesimo
--   giorno non deve essere respinto.
SELECT is(
  vendite.fn_get_next_progressivo(
      (SELECT reg_gate FROM tmp_le_reg),
      (SELECT oggi - 12 FROM tmp_le_date),
      NULL, NULL, NULL),
  1::bigint,
  '15) CANCELLO: la data UGUALE al pavimento e'' ammessa');

-- ============================================================
-- 16..17) I vincoli di colonna
-- ============================================================
-- ⭐ Il CHECK di coerenza e' A UN LATO SOLO: su un registro a data odierna il
--   giorno del mese non ha nessun significato, e un valore inerte che sembra
--   configurazione e' peggio di un valore assente. Il verso opposto NON si
--   vieta — i giorni valgono anche sulla differita.
SELECT throws_ok(
  format($$ UPDATE vendite.registri_fatturazione
               SET limite_emissione_giorno_mese = 15
             WHERE id = %s $$,
         (SELECT reg_oggi FROM tmp_le_reg)),
  '23514', NULL,
  '16) CHECK: il giorno del mese su un registro OGGI viene rifiutato');

-- ⛔ Un CHECK non sa chi ci scrive: il presidio di un vincolo e' un test che ne
--   rilegge la DEFINIZIONE. Senza, qualcuno puo' allargarlo in un changeSet
--   successivo e nessun rosso lo direbbe.
SELECT ok(
  (SELECT pg_get_constraintdef(c.oid) LIKE '%limite_emissione_giorno_mese IS NULL%'
     FROM pg_constraint c
     JOIN pg_class t     ON t.oid = c.conrelid
     JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = 'vendite'
      AND t.relname = 'registri_fatturazione'
      AND c.conname = 'chk_registri_fatturazione_limite_coerenza'),
  '17) presidio: il CHECK di coerenza nomina ancora giorno_mese IS NULL');

-- ============================================================
-- 18) Il lettore del parametro e' FAIL-LOUD
-- ============================================================
-- ⛔ Senza il controllo sul formato, il cast alzerebbe un 22P02 grezzo: il
--   contratto «P0001 + CONSTRAINT = errore di dominio» salterebbe e il guasto
--   arriverebbe al backend come 500 non tradotto.
-- ⚠️ Si usa un parametro ESISTENTE e non numerico invece di rompere il proprio:
--   una UPDATE su config.parameters lascerebbe il catalogo in uno stato strano
--   per tutte le asserzioni successive.
SELECT throws_ok(
  $$ SELECT vendite.fn_get_limite_emissione_default('SYSTEM_FUSO_ORARIO') $$,
  'P0001', NULL,
  '18) fn_get_limite_emissione_default: un valore non numerico solleva (non un 22P02)');

-- ============================================================
-- Cleanup
-- ============================================================
UPDATE vendite.registri_fatturazione
   SET storicizza = false
 WHERE id IN (SELECT reg_oggi FROM tmp_le_reg
              UNION ALL SELECT reg_over FROM tmp_le_reg
              UNION ALL SELECT reg_diff FROM tmp_le_reg
              UNION ALL SELECT reg_gate FROM tmp_le_reg
              UNION ALL SELECT reg_bordo FROM tmp_le_reg);

DELETE FROM vendite.registri_fatturazione_progressivi
 WHERE registro_id IN (SELECT reg_oggi FROM tmp_le_reg
                       UNION ALL SELECT reg_over FROM tmp_le_reg
                       UNION ALL SELECT reg_diff FROM tmp_le_reg
                       UNION ALL SELECT reg_gate FROM tmp_le_reg
              UNION ALL SELECT reg_bordo FROM tmp_le_reg);

DELETE FROM vendite.registri_fatturazione
 WHERE id IN (SELECT reg_oggi FROM tmp_le_reg
              UNION ALL SELECT reg_over FROM tmp_le_reg
              UNION ALL SELECT reg_diff FROM tmp_le_reg
              UNION ALL SELECT reg_gate FROM tmp_le_reg
              UNION ALL SELECT reg_bordo FROM tmp_le_reg);

SELECT ok(true, '19) Cleanup completato');

SELECT * FROM finish();

ROLLBACK;
