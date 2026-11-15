-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce un'AZIENDA — emittente fiscale,
--   utente tecnico e identita' digitale (dbops.fn_pgtap_crea_emittente_operatore)
--   — e un operatore dentro un perimetro non crea l'azienda in cui lavora.
--   Stesso criterio del gemello test-vw-lotti-fase-v1.
-- pgTAP test per Zero ERP
--
-- Test: T-1 — vendite.vw_documenti_trattenuti_da_lotto, la SEDE UNICA della
--       domanda «questo documento e' trattenuto da un lotto ancora in gioco?».
--
-- Elenco test (plan 6) — numerati come li stampa il TAP:
--  1) ⭐ lotto DRAFT + esito COMPLETED  -> TRATTENUTO
--  2) ⭐ lotto ANNULLATA + esito ERRORE -> LIBERO
--  3) ⛔ esito ESCLUSO su lotto vivo    -> LIBERO (uscito dal giro)
--  4) ⚠️ lo stesso documento in DUE lotti vivi -> DUE righe
--  5) 🔴 lotto DEFINITIVA (CHIUSO) + COMPLETED -> LIBERO
--  6) 🔴 lotto INVIATA (dopo la chiusura) + COMPLETED -> LIBERO
--
-- ⛔ RITIRATO il 2026-11-12 il test del lotto SENZA stato (era il 4): il caso
--   non e' piu' costruibile (stato_doc_fiscale_id NOT NULL, 20261112-46; il
--   trigger della nascita mette lo stato iniziale, -45). La LEFT JOIN della
--   vista resta. Brief: brief-db-stati-documento-dal-vocabolario §4.1, S-6.
-- ⭐ E dallo stesso giorno il mondo si COSTRUISCE: emittente e tipo documento
--   si prendevano «da un lotto che c'e' gia'», e su un database senza lotti
--   (lo scratch, la CI) il file non scriveva niente e girava a vuoto.
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ I TEST 1 E 2 VANNO LETTI INSIEME, ed e' tutto il senso del cantiere.
--   La dashboard espone gia' `ultimo_esito`, e da solo sbaglia in ENTRAMBE le
--   direzioni:
--     · COMPLETED su un lotto DRAFT    -> l'esito direbbe «libero», ed e'
--       trattenuto (test 1);
--     · ERRORE su un lotto ANNULLATA   -> l'esito direbbe «bloccato», ed e'
--       libero (test 2).
--   ⛔ Un presidio col solo test 1 passerebbe anche su una regola che blocca
--   TUTTO cio' che ha un esito; col solo test 2, su una che non blocca mai.
--
-- ⭐ E IL VERDETTO SI LEGGE DA UN FLAG. `config.stati_doc_fiscale` ha tre assi
--   distinti — `is_abortito`, `congela_fiscale`, `chiude_lotto` — e su ANNULLATA
--   il congelamento vale TRUE: chi cercasse li' «il lotto e' ancora in gioco»
--   prenderebbe la risposta sbagliata proprio sulla riga che conta. Il test 2 e'
--   quello che se ne accorgerebbe.
--
-- ⛔ I CASI SI COSTRUISCONO, non si cercano fra i lotti di oggi: una
--   popolazione che per caso non contiene un lotto annullato con esiti
--   renderebbe il test 2 verde a vuoto, e su un database ricostruito da zero
--   girerebbe identico solo per coincidenza.
--
-- ⭐ I TEST 5 E 6 SONO ARRIVATI DOPO, E DICONO PERCHE'.
--   La prima stesura definiva «in gioco» come `NOT is_abortito`, cioe' «non
--   annullato». Ma `is_abortito` e' TRUE solo su ANNULLATA: un lotto
--   DEFINITIVA non e' annullato, e' CHIUSO — e risultava ancora «vivo».
--   ⇒ Un documento fatturato in un lotto chiuso restava trattenuto PER SEMPRE,
--   e «Riporta da emettere» smetteva di avere effetto. Cancello senza chiave:
--   dal giro non lo si poteva nemmeno togliere, perche' l'uscita vuole un
--   lotto PRE-FISCALE.
--   ⛔ E il test 6 e' il seguito: la correzione ovvia — `NOT chiude_lotto` —
--   sbaglia anch'essa, perche' quel flag e' TRUE solo su DEFINITIVA e il
--   catalogo ammette DEFINITIVA -> INVIATA. Il flag giusto e' `pre_fiscale` di
--   vendite.vw_lotti_fase (fino al 2026-11-14 la sua copia `in_gioco`, R-2).
--   ⚠️ Nessuno dei due casi esisteva nei dati di sviluppo, dove i lotti
--   finiscono quasi tutti ANNULLATA: erano verdi per sottrazione, e vanno
--   COSTRUITI.
--
-- Brief: brief-db-documento-trattenuto-da-un-lotto-vivo.md (T-1)
--        brief-db-il-trattenuto-passa-lo-stesso.md (L2, §6.1)
-- ChangeSet: 20260909-23-create-vw-documenti-trattenuti-da-lotto
--            20260909-57-update-vw-documenti-trattenuti-sede-e-predicato
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- ⭐ L'AZIENDA E IL SUO OPERATORE SI COSTRUISCONO. ⚠️ Il builder apre e
--   richiude da solo la finestra dei vincoli differiti: va chiamato DOPO
--   `SET CONSTRAINTS ALL IMMEDIATE`.
CREATE TEMP TABLE tmp_trat_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Contesto applicativo: l'operatore che ha nel perimetro l'azienda appena creata
-- (senza, la RLS sui lotti nasconderebbe le righe scritte qui).
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM tmp_trat_mondo));
END $ctx$;

SELECT plan(6);

-- ============================================================
-- Fixture — sette lotti-testimone, uno per forma
-- ============================================================
-- ⚠️ L'emittente e' quello dell'azienda costruita; il tipo documento si prende
--   dal catalogo per `codice_interno`, la chiave stabile.
CREATE TEMP TABLE tmp_trat_rif AS
SELECT (SELECT t.id FROM config.tipi_doc_fiscale t
         WHERE t.codice_interno = 'BACKOFFICE') AS tipo_doc_fiscale_id,
       m.soggetto_ruolo_id                     AS emittente_soggetto_ruolo_id
  FROM tmp_trat_mondo m;

CREATE TEMP TABLE tmp_trat (caso text, lotto_id bigint, gruppo_key text);

DO $fixture$
DECLARE
    v_id  vendite.fatturazione_lotti.id%TYPE;
    r     record;
BEGIN
    -- (caso, stato del lotto, esito del documento)
    FOR r IN
        SELECT * FROM (VALUES
            ('vivo_completed',  'DRAFT',      'COMPLETED'),
            ('morto_errore',    'ANNULLATA',  'ERRORE'),
            ('vivo_escluso',    'DRAFT',      'ESCLUSO'),
            ('doppio_a',        'DRAFT',      'ERRORE'),
            ('doppio_b',        'EMESSA',     'PENDING'),
            -- ⭐ I due casi del difetto: CHIUSO non e' ANNULLATO, e
            --   INVIATA viene DOPO la chiusura.
            ('chiuso_completed',  'DEFINITIVA', 'COMPLETED'),
            ('inviato_completed', 'INVIATA',    'COMPLETED')
        ) AS v(caso, stato, esito)
    LOOP
        -- ⭐ Il lotto nasce nello stato iniziale (trigger della nascita) e si
        --   porta allo stato voluto dai verbi del lotto, lungo la matrice,
        --   PRIMA di gruppi ed esiti: e' vuoto, nessuna fattura da allineare.
        INSERT INTO vendite.fatturazione_lotti
            (codice, competenza_mese, tipo_doc_fiscale_id,
             emittente_soggetto_ruolo_id)
        SELECT 'PGTAP-TRAT-' || upper(r.caso),
               date_trunc('month', script.fn_data_operativa())::date,
               t.tipo_doc_fiscale_id, t.emittente_soggetto_ruolo_id
          FROM tmp_trat_rif t
        RETURNING id INTO v_id;

        IF r.stato <> 'DRAFT' THEN
            -- `codice_interno`, mai un id: e' la chiave stabile.
            PERFORM dbops.fn_pgtap_porta_a_stato('vendite.fatturazione_lotti', v_id, r.stato);
        END IF;

        -- I due «doppio_*» tengono lo STESSO documento: e' il caso del test 4.
        INSERT INTO tmp_trat VALUES (
            r.caso, v_id,
            CASE WHEN r.caso LIKE 'doppio%' THEN 'PGTAP:TRAT:doppio'
                 ELSE 'PGTAP:TRAT:' || r.caso END);

        INSERT INTO vendite.fatturazione_lotti_gruppi (lotto_id, gruppo_key)
        SELECT v_id, gruppo_key FROM tmp_trat WHERE lotto_id = v_id;

        -- ⚠️ `uscita_motivo` obbligatorio su ESCLUSO: lo pretende il CHECK
        --   chk_fatturazione_lotti_esiti_uscita_parlante. Un'uscita senza
        --   motivo non e' spiegabile, quindi non si scrive.
        INSERT INTO vendite.fatturazione_lotti_esiti
            (lotto_id, gruppo_key, stato_esecuzione,
             errore_codice, errore_messaggio, uscita_motivo)
        SELECT v_id, t.gruppo_key, r.esito,
               CASE WHEN r.esito = 'ERRORE' THEN 'E_PULL_COMMESSA' END,
               CASE WHEN r.esito = 'ERRORE' THEN 'rotto per la prova' END,
               CASE WHEN r.esito = 'ESCLUSO' THEN 'uscito per la prova' END
          FROM tmp_trat t WHERE t.lotto_id = v_id;
    END LOOP;
END;
$fixture$;

-- ============================================================
-- 1) ⭐ Lotto VIVO, esito COMPLETED: trattenuto
-- ============================================================
-- ⛔ E' il caso che `ultimo_esito` sbaglia in un verso: direbbe «e' andato bene,
--   quindi libero». Ma la fattura non e' definitiva e il giro tiene ancora il
--   documento: metterlo in un secondo lotto lo fatturerebbe due volte.
SELECT is(
    (SELECT lotto_codice FROM vendite.vw_documenti_trattenuti_da_lotto
      WHERE gruppo_key = 'PGTAP:TRAT:vivo_completed'),
    'PGTAP-TRAT-VIVO_COMPLETED',
    '1. un documento su un lotto VIVO e'' trattenuto, anche con esito COMPLETED'
);

-- ============================================================
-- 2) ⭐ Lotto ANNULLATO, esito ERRORE: libero
-- ============================================================
-- ⛔ Il verso opposto, ed e' quello che tiene onesto il test 1: senza, la vista
--   passerebbe anche su una regola che blocca qualunque documento abbia un
--   esito. ⚠️ E' anche il test che si accorgerebbe se qualcuno leggesse
--   `congela_fiscale` al posto di `is_abortito`: su ANNULLATA vale TRUE.
SELECT ok(
    NOT EXISTS (SELECT 1 FROM vendite.vw_documenti_trattenuti_da_lotto
                 WHERE gruppo_key = 'PGTAP:TRAT:morto_errore'),
    '2. un lotto ANNULLATO non trattiene niente, nemmeno con un esito in ERRORE'
);

-- ============================================================
-- 3) ⛔ Uscito dal giro: non trattiene
-- ============================================================
-- «Un documento fuori dal giro non si marca, non si conta, non blocca» — e non
-- trattiene. E' la stessa regola del cantiere del marcatore, vista dal terzo
-- lato.
SELECT ok(
    NOT EXISTS (SELECT 1 FROM vendite.vw_documenti_trattenuti_da_lotto
                 WHERE gruppo_key = 'PGTAP:TRAT:vivo_escluso'),
    '3. un documento ESCLUSO non e'' trattenuto, anche se il lotto e'' vivo'
);

-- ============================================================
-- 4) ⚠️ Lo stesso documento in due lotti vivi: due righe
-- ============================================================
-- ⛔ Non e' un difetto della vista: e' il difetto che la vista serve a rendere
--   visibile. Un `DISTINCT ON (gruppo_key)` qui dentro nasconderebbe proprio la
--   cosa da vedere, e chi ne vuole UNO deve ordinare — un LIMIT 1 senza ORDER BY
--   scommette.
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documenti_trattenuti_da_lotto
      WHERE gruppo_key = 'PGTAP:TRAT:doppio'),
    2,
    '4. un documento tenuto da DUE lotti vivi rende due righe: la vista non lo nasconde'
);

-- ============================================================
-- 5) 🔴 Lotto CHIUSO (DEFINITIVA): non trattiene piu' niente
-- ============================================================
-- ⛔ E' IL DIFETTO CHE HA APERTO IL CANTIERE SEGUENTE. Con `NOT is_abortito`
--   questo caso risultava TRATTENUTO: DEFINITIVA non e' abortita, e'
--   regolarmente chiusa. Un documento fatturato in un lotto chiuso restava
--   bloccato per sempre, e «Riporta da emettere» non aveva piu' effetto.
-- ⭐ E non c'era via d'uscita: togliere un documento dal giro vuole un lotto
--   PRE-FISCALE, e DEFINITIVA non lo e'. Un cancello senza chiave.
SELECT ok(
    NOT EXISTS (SELECT 1 FROM vendite.vw_documenti_trattenuti_da_lotto
                 WHERE gruppo_key = 'PGTAP:TRAT:chiuso_completed'),
    '5. un lotto DEFINITIVA (chiuso) non trattiene piu'': chiuso non e'' annullato'
);

-- ============================================================
-- 6) 🔴 E dopo la chiusura: INVIATA non riapre niente
-- ============================================================
-- ⛔ E' IL CASO CHE LA CORREZIONE OVVIA SBAGLIA. `NOT chiude_lotto` sembra dire
--   «non ha finito», ma quel flag e' TRUE solo su DEFINITIVA: marca la
--   TRANSIZIONE che chiude, non la proprieta' di essere chiuso. Il catalogo
--   ammette DEFINITIVA -> INVIATA (asse lotto), e INVIATA non lo porta.
--   ⇒ Un lotto chiuso e poi inviato sarebbe tornato «in gioco», e i suoi
--   documenti trattenuti di nuovo — dopo essere stati liberati.
SELECT ok(
    NOT EXISTS (SELECT 1 FROM vendite.vw_documenti_trattenuti_da_lotto
                 WHERE gruppo_key = 'PGTAP:TRAT:inviato_completed'),
    '6. un lotto INVIATA (dopo la chiusura) non trattiene: chiuso RESTA chiuso'
);

SELECT * FROM finish();
ROLLBACK;
