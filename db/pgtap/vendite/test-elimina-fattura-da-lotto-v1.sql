-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: eliminazione di UNA fattura da un lotto pre-fiscale
--       (piano-db-ritorno-lotto-a-draft.md, Slice 6-B — RD-7)
-- ------------------------------------------------------------
-- Cosa presidia questo file
--   RD-7 (2026-08-04): togliere una fattura dal lotto vuol dire
--   CANCELLARLA. Il modello «reperto» — staccarla e portarla ad
--   ANNULLATA — e' caduto perche' era incoerente: riportare in bozza un
--   lotto INTERO cancella gia' le sue fatture EMESSA, e non aveva senso
--   che la stessa operazione su UNA riga lasciasse un documento vuoto.
--
--   Con quella decisione l'unico lavoro rimasto e' allargare il
--   perimetro del LOTTO da «DRAFT» a «pre-fiscale» e portare le quattro
--   precondizioni in una sede sola.
--
-- 🔴 I TEST CHE VALGONO DI PIU' SONO IL 10 E L'11.
--   Il 10 verifica l'unica cosa che conta davvero: dove la fn_check dice
--   no, la funzione di mutazione SOLLEVA. Senza, le due meta' della
--   stessa regola possono separarsi in silenzio.
--   L'11 verifica che l'allargamento sia reale, cioe' che su un lotto
--   EMESSA la fattura si possa togliere. E' il bug che questo lavoro
--   chiude: il drawer proponeva gia' la voce su quei lotti (gate sul
--   solo stato della fattura) e la chiamata falliva.
--
-- ⚠️ FIXTURE SCELTE, NON COSTRUITE, e detto invece che nascosto.
--   Un lotto con fatture agganciate e' il prodotto di due step di
--   pipeline: non si fabbrica in un pgTAP senza riscrivere la pipeline.
--   Il file SCEGLIE lotti reali e lavora dentro BEGIN/ROLLBACK. Dove il
--   DB non ha il caso, il test si SALTA invece di fallire. I test 1-5
--   sono strutturali e girano sempre.
-- ------------------------------------------------------------
-- Indice test
-- 1) La funzione nuova esiste, col nome nuovo e i quattro contatori
-- 2) Il vecchio nome NON esiste piu (la rinomina e reale, niente doppione)
-- 3) La fn_check esiste
-- 4) I quattro codici errore sono a catalogo
-- 5) La fn_check rifiuta parametri invalidi
-- 6) Caso lecito: su lotto e fattura pre-fiscali il check non ha motivi
-- 7) Motivo: il lotto e oltre il pre-fiscale
-- 8) Motivo: la fattura non e collegata a quel lotto
-- 9) Motivo: la fattura ha gia un numero
-- 10) Equivalenza check <-> mutazione            <-- il test che vale
-- 11) Il perimetro allargato: da lotto EMESSA si puo togliere  <-- il bug chiuso
-- 12) ...ma NON se su una riga e gia stato registrato un accredito
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

SELECT plan(12);

-- ============================================================
-- Strutturali (girano sempre)
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'vendite'
       AND p.proname = 'fn_elimina_fattura_da_lotto'
       AND pg_get_function_result(p.oid) ILIKE '%riemesse_attivita%'
       AND pg_get_function_result(p.oid) ILIKE '%deleted_fatture%'),
  '1) La funzione esiste col nome nuovo e restituisce i quattro contatori');

-- Niente alias di transizione: due nomi vivi per la stessa cosa sono
-- esattamente il modo in cui i chiamanti si sfilano senza accorgersene.
SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'vendite' AND p.proname = 'fn_elimina_fattura_da_lotto_draft'),
  '2) Il vecchio nome non esiste piu: la rinomina e reale');

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'script' AND p.proname = 'fn_check_fattura_eliminabile_da_lotto'),
  '3) La funzione pura di check esiste');

-- Un codice sollevato ma non a catalogo produce «MESSAGGIO NON DEFINITO»
-- all'operatore: il presidio sta qui perche' e' un silenzio, non un errore.
SELECT is(
  (SELECT count(*)::integer FROM config.messaggi_errore m
    WHERE m.codice IN ('E_LOTTO_NON_PRE_FISCALE', 'E_FATTURA_NON_COLLEGATA_AL_LOTTO',
                       'E_FATTURA_GIA_FISCALE', 'E_FATTURA_GIA_NUMERATA')
      AND m.lingua = 'it'),
  4,
  '4) I quattro codici errore sono a catalogo in lingua it');

SELECT throws_ok(
  $$ SELECT script.fn_check_fattura_eliminabile_da_lotto(0, 0) $$,
  'P0001',
  NULL,
  '5) La fn_check rifiuta un lotto_id invalido');

-- ============================================================
-- Fixture
-- ============================================================
-- Criterio: una coppia (lotto, fattura) collegata, con entrambi
-- pre-fiscali e la fattura NON numerata — cioe' il caso lecito. Il
-- filtro sul numero e' lo stesso che il test 9 esercita: la fixture non
-- muore su una condizione che il file verifica altrove.
CREATE TEMP TABLE tmp_efl AS
SELECT lf.lotto_id, lf.fattura_id
  FROM vendite.fatturazione_lotti_fatture lf
  JOIN vendite.fatturazione_lotti fl ON fl.id = lf.lotto_id
  JOIN config.stati_doc_fiscale sl ON sl.id = fl.stato_doc_fiscale_id
  JOIN vendite.fatture f ON f.id = lf.fattura_id
  JOIN config.stati_doc_fiscale sf ON sf.id = f.stato_doc_fiscale_id
 WHERE sl.codice_interno IN ('DRAFT', 'EMESSA')
   AND sf.codice_interno IN ('DRAFT', 'EMESSA')
   AND f.numero IS NULL
 ORDER BY lf.lotto_id DESC, lf.fattura_id DESC
 LIMIT 1;

-- Un lotto oltre il pre-fiscale, per i motivi 1 e 2. ⚠️ Si pretende che
-- NON contenga la fattura della fixture: il test 8 deve poter asserire
-- lo scollegamento, e una fattura presente in due lotti — la chiave
-- unica del ponte e' (lotto, fattura), quindi e' possibile — renderebbe
-- quell'asserzione falsa per un motivo che non c'entra.
CREATE TEMP TABLE tmp_efl_oltre AS
SELECT fl.id AS lotto_id
  FROM vendite.fatturazione_lotti fl
  JOIN config.stati_doc_fiscale s ON s.id = fl.stato_doc_fiscale_id
 WHERE s.codice_interno NOT IN ('DRAFT', 'EMESSA')
   AND NOT EXISTS (
         SELECT 1 FROM vendite.fatturazione_lotti_fatture x
          WHERE x.lotto_id = fl.id
            AND x.fattura_id = (SELECT fattura_id FROM tmp_efl))
 ORDER BY fl.id DESC
 LIMIT 1;

-- ============================================================
-- 6-9) I quattro verdetti della fn_check
-- ============================================================

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_efl)
    THEN skip('nessuna coppia lotto/fattura pre-fiscale su questo DB', 1)
  ELSE is(
    script.fn_check_fattura_eliminabile_da_lotto(
      (SELECT lotto_id FROM tmp_efl), (SELECT fattura_id FROM tmp_efl)),
    '[]'::jsonb,
    '6) Caso lecito: lotto e fattura pre-fiscali, nessun motivo ostativo')
END;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_efl_oltre) OR NOT EXISTS (SELECT 1 FROM tmp_efl)
    THEN skip('nessun lotto oltre il pre-fiscale su questo DB', 1)
  ELSE ok(
    EXISTS (
      SELECT 1 FROM jsonb_array_elements(
        script.fn_check_fattura_eliminabile_da_lotto(
          (SELECT lotto_id FROM tmp_efl_oltre), (SELECT fattura_id FROM tmp_efl))) m
       WHERE m->>'reason' = 'STATO_LOTTO_NON_PRE_FISCALE'),
    '7) Motivo: il lotto oltre il pre-fiscale e rifiutato')
END;

-- La fattura della fixture esiste, ma non e' collegata al lotto scelto
-- qui: il motivo deve nominare il legame, non lo stato.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_efl_oltre) OR NOT EXISTS (SELECT 1 FROM tmp_efl)
    THEN skip('serve un secondo lotto per provare lo scollegamento', 1)
  ELSE ok(
    EXISTS (
      SELECT 1 FROM jsonb_array_elements(
        script.fn_check_fattura_eliminabile_da_lotto(
          (SELECT lotto_id FROM tmp_efl_oltre), (SELECT fattura_id FROM tmp_efl))) m
       WHERE m->>'reason' = 'FATTURA_NON_COLLEGATA'),
    '8) Motivo: la fattura non collegata a quel lotto e rifiutata')
END;

-- ⚠️ Il numero si mette DENTRO UNA SOTTOTRANSAZIONE che si annulla da sola:
--   check e mutazione si interrogano sulla fattura numerata, gli esiti si
--   salvano in variabili, poi il blocco esce con un errore proprio (PGT01) e
--   tutto cio' che ha scritto — il numero, e una cancellazione se la mutazione
--   per errore riuscisse — torna indietro. La fixture torna com'era e i test
--   successivi lavorano sulla coppia intatta.
-- ⚠️ Rev 2026-10-05: prima il numero si TOGLIEVA con un UPDATE (numero =
--   NULL). Dal 20261004-80 (vendite.trgfn_fatture_guard_numero_fiscale, Q-4 di
--   brief-db-esclusioni-implicite) una fattura numerata non cambia identita'
--   fiscale, e il file moriva li'. Il rollback di una sottotransazione non e'
--   una modifica della fattura: e' una numerazione che non e' mai avvenuta.
CREATE TEMP TABLE tmp_efl_numerata (motivi jsonb, esito_mutazione text);
DO $num$
DECLARE
  v_motivi jsonb;
  v_esito  text;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM tmp_efl) THEN
    RETURN;
  END IF;
  BEGIN
    UPDATE vendite.fatture SET numero = 999999
     WHERE id = (SELECT fattura_id FROM tmp_efl);
    v_motivi := script.fn_check_fattura_eliminabile_da_lotto(
                  (SELECT lotto_id FROM tmp_efl), (SELECT fattura_id FROM tmp_efl));
    BEGIN
      PERFORM * FROM vendite.fn_elimina_fattura_da_lotto(
                (SELECT lotto_id FROM tmp_efl), (SELECT fattura_id FROM tmp_efl));
      v_esito := 'NESSUN ERRORE';
    EXCEPTION WHEN OTHERS THEN
      v_esito := SQLSTATE;
    END;
    RAISE EXCEPTION USING ERRCODE = 'PGT01';   -- annulla il numero
  EXCEPTION WHEN SQLSTATE 'PGT01' THEN
    NULL;
  END;
  INSERT INTO tmp_efl_numerata VALUES (v_motivi, v_esito);
END $num$;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_efl)
    THEN skip('nessuna coppia lotto/fattura pre-fiscale su questo DB', 1)
  ELSE ok(
    EXISTS (
      SELECT 1 FROM tmp_efl_numerata n, jsonb_array_elements(n.motivi) m
       WHERE m->>'reason' = 'FATTURA_NUMERATA'),
    '9) Motivo: la fattura gia numerata e rifiutata (si guarda il numero)')
END;

-- ============================================================
-- 10) 🔴 Equivalenza check <-> mutazione
-- ============================================================
-- Il cuore del file. Sulla fattura numerata (nella sottotransazione qui
-- sopra) il check elenca almeno un motivo, e la mutazione deve sollevare.
-- Se domani qualcuno rimettesse una precondizione a mano dentro la
-- mutazione — o ne togliesse una — le due meta' si separerebbero e qui si
-- vedrebbe.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_efl)
    THEN skip('nessuna coppia lotto/fattura pre-fiscale su questo DB', 1)
  WHEN (SELECT coalesce(jsonb_array_length(n.motivi), 0) FROM tmp_efl_numerata n) = 0
    THEN ok(false,
            '10) INCOERENZA: la fn_check non vede il numero che il test ha appena scritto')
  ELSE is(
    (SELECT n.esito_mutazione FROM tmp_efl_numerata n),
    'P0001',
    '10) Equivalenza: il check elenca motivi e la mutazione solleva')
END;

-- La fattura non e' numerata: la sottotransazione e' stata annullata.

-- ============================================================
-- 11) 🔴 Il perimetro allargato
-- ============================================================
-- Il bug che questo lavoro chiude: prima la funzione pretendeva il LOTTO
-- in DRAFT, mentre il drawer proponeva la voce su qualunque lotto con
-- fattura pre-fiscale. Su un lotto EMESSA la voce c'era e falliva.
-- Qui si asserisce il caso specifico — lotto EMESSA — e non il generico
-- «pre-fiscale»: con DRAFT il test sarebbe passato anche prima
-- dell'allargamento, cioe' non avrebbe misurato niente.
CREATE TEMP TABLE tmp_efl_emessa AS
SELECT lf.lotto_id, lf.fattura_id
  FROM vendite.fatturazione_lotti_fatture lf
  JOIN vendite.fatturazione_lotti fl ON fl.id = lf.lotto_id
  JOIN config.stati_doc_fiscale sl ON sl.id = fl.stato_doc_fiscale_id
  JOIN vendite.fatture f ON f.id = lf.fattura_id
  JOIN config.stati_doc_fiscale sf ON sf.id = f.stato_doc_fiscale_id
 WHERE sl.codice_interno = 'EMESSA'
   AND sf.codice_interno IN ('DRAFT', 'EMESSA')
   AND f.numero IS NULL
   -- ⭐ rev 2026-08-22: la fixture deve scegliere una fattura DAVVERO
   --   togliibile, e dal motivo 5 «non numerata» non basta piu': su una riga
   --   puo' essere gia' stato registrato un accredito, e allora la funzione
   --   rifiuta — a ragione. Senza questa riga il test sceglieva quel caso e
   --   diventava rosso accusando il codice invece della propria selezione.
   -- ⚠️ NON e' circolare: il soggetto del test e'
   --   fn_check_fattura_eliminabile_da_lotto, che compone CINQUE motivi; qui
   --   se ne neutralizza uno solo, con la stessa funzione che il motivo 5
   --   delega. E il caso del RIFIUTO ha il suo presidio nel test 12 qui
   --   sotto, quindi non e' questa fixture a doverlo garantire.
   AND script.fn_check_fatture_con_rettifiche(ARRAY[f.id]) = '[]'::jsonb
 ORDER BY lf.lotto_id DESC
 LIMIT 1;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_efl_emessa)
    THEN skip('nessun lotto EMESSA con fattura non numerata su questo DB', 1)
  ELSE is(
    script.fn_check_fattura_eliminabile_da_lotto(
      (SELECT lotto_id FROM tmp_efl_emessa), (SELECT fattura_id FROM tmp_efl_emessa)),
    '[]'::jsonb,
    '11) Perimetro allargato: da un lotto EMESSA la fattura si puo togliere')
END;


-- ============================================================
-- 12) ⭐ Il confine del perimetro allargato
-- ============================================================
-- Il motivo 5, nato il 2026-08-22 (changeSet 20260822-51). ⚠️ Questa e' la
-- porta piu' ESPOSTA delle tre: lavora su UNA fattura e la ammette anche a
-- lotto EMESSA — cioe' proprio lo stato in cui vive un accredito registrato
-- prima della numerazione. Il motivo 4 non lo copre: l'accredito e' ancorato
-- alla coda dei resi, non al numero.
-- ⚠️ Si asserisce il CODICE e non «l'array non e' vuoto»: qualunque altro
-- motivo renderebbe l'array non vuoto e il test passerebbe misurando altro.
CREATE TEMP TABLE tmp_efl_rett AS
SELECT lf.lotto_id, lf.fattura_id
  FROM vendite.fatturazione_lotti_fatture lf
 WHERE script.fn_check_fatture_con_rettifiche(ARRAY[lf.fattura_id]) <> '[]'::jsonb
 ORDER BY lf.lotto_id DESC
 LIMIT 1;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_efl_rett)
    THEN skip('nessuna fattura con righe gia accreditate su questo DB', 1)
  ELSE ok(
    EXISTS (
      SELECT 1
        FROM jsonb_array_elements(
               script.fn_check_fattura_eliminabile_da_lotto(
                 (SELECT lotto_id FROM tmp_efl_rett),
                 (SELECT fattura_id FROM tmp_efl_rett))) m
       WHERE m ->> 'codice' = 'E_FATTURE_RIGHE_RETTIFICATE'),
    '12) ...ma una fattura con righe gia accreditate NON si toglie, e il motivo lo dice')
END;

SELECT * FROM finish();

ROLLBACK;
