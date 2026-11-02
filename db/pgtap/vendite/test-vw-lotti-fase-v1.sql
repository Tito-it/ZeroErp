-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce un'AZIENDA — emittente fiscale,
--   utente tecnico e identita' digitale (dbops.fn_pgtap_crea_emittente_operatore)
--   — e un operatore dentro un perimetro non crea l'azienda in cui lavora.
--   E' il criterio 2 di scripts/testpgtap.sh, lo stesso dei tre file gemelli di
--   questo cantiere e dei sei db/pgtap/rls/*-satelliti.sql.
--   🔴 Ed e' una CORREZIONE del 2026-09-09 sera: era rimasto `app` perche' come
--   `app` passava sullo scratch locale — cioe' per una MISURA, non per il
--   modello. Su GitHub, dove la CI ricostruisce tutto da zero, era rosso.
-- pgTAP test per Zero ERP
--
-- Test: P-9 — vendite.vw_lotti_fase, la SEDE UNICA della domanda
--       «in che fase e' questo lotto?».
--
-- Elenco test (plan 8) — numerati come li stampa il TAP:
--  1) il contratto: la vista espone esattamente le colonne dichiarate
--  2) ⭐ DRAFT ed EMESSA        -> pre_fiscale TRUE
--  3) ⭐ DEFINITIVA, INVIATA, REGISTRATA, ANNULLATA -> pre_fiscale FALSE
--  4) ⚠️ stato IGNOTO           -> la riga C'E' e pre_fiscale e' FALSE
--  5) ⚠️ stato IGNOTO           -> i tre assi grezzi restano NULL
--  6) ⭐ il catalogo ammette DEFINITIVA -> INVIATA per il LOTTO: il caso del
--        test 3 e' RAGGIUNGIBILE, non ipotetico
--  7) ⭐ `in_gioco` sui sei stati: coincide con `pre_fiscale`
--  8) ⭐⭐ sullo stato IGNOTO i due DIVERGONO — ed e' tutta la ragione per cui
--        sono due flag e non uno
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ I TEST 2 E 3 VANNO LETTI INSIEME, ed e' la stessa disciplina del test
--   gemello sul trattenuto: col solo verso «aperto» passerebbe anche un
--   predicato che dice aperto SEMPRE; col solo verso «chiuso», uno che dice
--   chiuso sempre. Servono entrambi.
--
-- ⛔ E IL TEST 3 CONTIENE IL CASO CHE HA FATTO SBAGLIARE LA PRIMA STESURA.
--   `vw_lotti_fase` nasceva con un flag `in_gioco` definito come
--   `NOT is_abortito AND NOT chiude_lotto`. Su INVIATA e REGISTRATA quel
--   predicato dice APERTO, perche' `chiude_lotto` e' TRUE solo su DEFINITIVA:
--   marca la TRANSIZIONE che chiude, non la PROPRIETA' di essere chiuso.
--   ⇒ Un lotto chiuso e poi inviato sarebbe tornato «in gioco», e i suoi
--   documenti sarebbero risultati trattenuti di nuovo.
--   Il flag giusto e' UNO: `pre_fiscale`, cioe' `NOT congela_fiscale`.
--
-- ⭐ E COINCIDE CON LA PORTA D'USCITA, che e' la ragione per cui e' quello
--   giusto e non una coincidenza fortunata:
--   script.fn_check_documento_escludibile_da_giro ammette di togliere un
--   documento dal giro SOLO se il lotto e' pre-fiscale.
--     ⇒ trattenuto ⇔ si puo' ancora uscire.
--   Se i due predicati divergessero esisterebbe un documento trattenuto senza
--   via d'uscita: un cancello senza chiave.
--
-- ⛔ I CASI SI COSTRUISCONO. La fixture crea SETTE lotti, uno per stato piu'
--   quello senza stato, e non ne cerca nessuno fra i lotti di oggi: su un
--   database ricostruito da zero un testimone «trovato» non esiste, e il file
--   sarebbe verde per sottrazione.
--
-- ⚠️ Il test 6 non prova la vista: prova che il CASO del test 3 e' ammesso dal
--   catalogo. Se un giorno quella transizione venisse tolta, questo test
--   diventa rosso — ed e' voluto: obbliga a rileggere perche' il flag non e'
--   `chiude_lotto` prima di cambiarlo.
--
-- ChangeSet: 20260909-51-create-vw-lotti-fase · 20260909-56-update-vw-lotti-fase-in-gioco
-- Brief: brief-db-il-trattenuto-passa-lo-stesso.md (L1)
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- ⭐ L'AZIENDA E IL SUO OPERATORE SI COSTRUISCONO (rev 2026-09-09).
--   Prima si prendeva l'emittente dell'operatore con
--   `script.fn_pgtap_emittente_sr_operatore()`, che lo CERCA. Su un database
--   ricostruito dai changelog — cioe' in CI — `anagrafiche` e' vuoto: zero
--   emittenti, zero utenti, zero assegnazioni, perche' quei seed sono
--   `dati_macchina`. ⇒ La funzione sollevava «Nessun emittente fiscale attivo»
--   e il file non eseguiva NEMMENO UNA asserzione.
-- ⛔ Ed era in contraddizione con l'intestazione di questo file, che dichiara
--   «I CASI SI COSTRUISCONO»: i sette lotti si', ma il mondo sotto no.
-- ⚠️ `dbops.fn_pgtap_crea_emittente_operatore` apre e richiude da sola la
--   finestra dei vincoli differiti di cui ha bisogno: va chiamata DOPO la riga
--   `SET CONSTRAINTS ALL IMMEDIATE`, non prima.
CREATE TEMP TABLE tmp_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Contesto applicativo: questo test gira come gira l'applicazione, e
-- l'operatore e' quello che ha nel perimetro l'azienda appena creata.
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM tmp_mondo));
END $ctx$;

SELECT plan(8);

-- ============================================================
-- Fixture — sette lotti-testimone, uno per forma
-- ============================================================
-- ⚠️ Emittente e tipo documento si COSTRUISCONO: l'emittente e' quello
--   dell'operatore del contesto (senza, la RLS su vendite.fatturazione_lotti
--   nasconderebbe le righe appena scritte e il file passerebbe a vuoto), e il
--   tipo documento si prende dal catalogo per `codice_interno`, che e' la
--   chiave stabile.
CREATE TEMP TABLE tmp_fase (stato text, lotto_id bigint);

DO $fixture$
DECLARE
    v_id       vendite.fatturazione_lotti.id%TYPE;
    v_emit_sr  vendite.fatturazione_lotti.emittente_soggetto_ruolo_id%TYPE;
    v_tipo     vendite.fatturazione_lotti.tipo_doc_fiscale_id%TYPE;
    r          record;
BEGIN
    SELECT m.soggetto_ruolo_id INTO v_emit_sr FROM tmp_mondo m;

    SELECT t.id INTO v_tipo
      FROM config.tipi_doc_fiscale t
     WHERE t.codice_interno = 'BACKOFFICE';

    FOR r IN
        SELECT * FROM (VALUES
            ('DRAFT'), ('EMESSA'), ('DEFINITIVA'),
            ('INVIATA'), ('REGISTRATA'), ('ANNULLATA'),
            -- ⭐ Lo stato IGNOTO e' COSTRUIBILE: la colonna e' nullable,
            --   quindi il ramo fail-closed non e' un ramo dichiarato
            --   irraggiungibile — e' un caso che il modello ammette.
            (NULL)
        ) AS v(stato)
    LOOP
        INSERT INTO vendite.fatturazione_lotti
            (codice, competenza_mese, tipo_doc_fiscale_id,
             emittente_soggetto_ruolo_id, stato_doc_fiscale_id)
        VALUES ('PGTAP-FASE-' || COALESCE(r.stato, 'IGNOTO'),
                date_trunc('month', script.fn_data_operativa())::date,
                v_tipo, v_emit_sr,
                -- ⭐ `codice_interno`, mai un id: e' la chiave stabile.
                (SELECT s.id FROM config.stati_doc_fiscale s
                  WHERE s.codice_interno = r.stato))
        RETURNING id INTO v_id;

        INSERT INTO tmp_fase VALUES (COALESCE(r.stato, '(ignoto)'), v_id);
    END LOOP;
END;
$fixture$;

-- ============================================================
-- 1) Il contratto della vista
-- ============================================================
-- ⚠️ `columns_are` e non N volte `has_column`: cosi' diventa rosso anche una
--   colonna AGGIUNTA di straforo, non solo una tolta. Il contratto di questa
--   vista e' scritto nel brief (§8.2.1) e i suoi lettori ci si appoggiano.
SELECT columns_are(
    'vendite', 'vw_lotti_fase',
    ARRAY['lotto_id', 'lotto_codice', 'lotto_competenza_mese',
          'stato_codice_interno', 'is_abortito', 'congela_fiscale',
          'chiude_lotto', 'pre_fiscale', 'in_gioco'],
    '1. il contratto: la vista espone esattamente le colonne dichiarate'
);

-- ============================================================
-- 2) ⭐ DRAFT ed EMESSA: il giro puo' ancora agire
-- ============================================================
SELECT results_eq(
    $$ SELECT t.stato, f.pre_fiscale
         FROM tmp_fase t JOIN vendite.vw_lotti_fase f ON f.lotto_id = t.lotto_id
        WHERE t.stato IN ('DRAFT', 'EMESSA')
        ORDER BY t.stato $$,
    $$ VALUES ('DRAFT', true), ('EMESSA', true) $$,
    '2. DRAFT ed EMESSA: pre_fiscale TRUE — il giro puo'' ancora agire'
);

-- ============================================================
-- 3) ⭐ E il verso opposto: chiuso, inviato, registrato, annullato
-- ============================================================
-- ⛔ INVIATA e REGISTRATA sono il caso che un predicato costruito su
--   `chiude_lotto` sbaglierebbe: quel flag e' TRUE solo su DEFINITIVA, quindi
--   direbbe «aperto» su due stati che vengono DOPO la chiusura.
SELECT results_eq(
    $$ SELECT t.stato, f.pre_fiscale
         FROM tmp_fase t JOIN vendite.vw_lotti_fase f ON f.lotto_id = t.lotto_id
        WHERE t.stato IN ('DEFINITIVA', 'INVIATA', 'REGISTRATA', 'ANNULLATA')
        ORDER BY t.stato $$,
    $$ VALUES ('ANNULLATA', false), ('DEFINITIVA', false),
              ('INVIATA', false), ('REGISTRATA', false) $$,
    '3. DEFINITIVA, INVIATA, REGISTRATA e ANNULLATA: pre_fiscale FALSE — e chiuso resta chiuso'
);

-- ============================================================
-- 4) ⚠️ Stato non risolvibile: la riga C'E', e la risposta e' chiusa
-- ============================================================
-- ⭐ Le due meta' contano tutte e due. Se la riga sparisse, chi fa un JOIN non
--   troverebbe niente e leggerebbe «nessun problema»: il fail-closed si
--   perderebbe proprio dove serve.
SELECT results_eq(
    $$ SELECT count(*)::int, bool_and(f.pre_fiscale IS FALSE)
         FROM tmp_fase t JOIN vendite.vw_lotti_fase f ON f.lotto_id = t.lotto_id
        WHERE t.stato = '(ignoto)' $$,
    $$ VALUES (1, true) $$,
    '4. stato non risolvibile: la riga c''e'' E pre_fiscale e'' FALSE (fail-closed)'
);

-- ============================================================
-- 5) ⚠️ E i tre assi GREZZI restano NULL: il fatto non si maschera
-- ============================================================
-- ⛔ Se anche i grezzi fossero COALESCE-ati, la stessa colonna direbbe «fatto»
--   e «difesa» insieme — per giunta con default in direzioni opposte
--   (is_abortito -> false, congela_fiscale -> true). Il grezzo e' il fatto, e
--   un fatto ignoto si dice ignoto.
SELECT results_eq(
    $$ SELECT f.is_abortito IS NULL, f.congela_fiscale IS NULL,
              f.chiude_lotto IS NULL, f.stato_codice_interno IS NULL
         FROM tmp_fase t JOIN vendite.vw_lotti_fase f ON f.lotto_id = t.lotto_id
        WHERE t.stato = '(ignoto)' $$,
    $$ VALUES (true, true, true, true) $$,
    '5. stato non risolvibile: i tre assi grezzi restano NULL, il fatto non si maschera'
);

-- ============================================================
-- 6) ⭐ Il caso del test 3 e' RAGGIUNGIBILE, non ipotetico
-- ============================================================
-- ⚠️ Questo test non guarda la vista: guarda il CATALOGO. Serve a tenere in
--   vita la ragione per cui il flag non e' `chiude_lotto` — se un giorno la
--   transizione venisse tolta, questo diventa rosso e obbliga a rileggere la
--   decisione prima di cambiarla.
-- ⛔ Si guarda l'ASSE DEL LOTTO (`solo_lotto`), e si chiede se la transizione
--   ESISTE: contare le righe sarebbe la forma sbagliata, perche' la stessa
--   coppia di stati vive due volte — una per il lotto e una per la fattura —
--   e un conteggio diventerebbe rosso il giorno che si aggiunge un asse.
SELECT ok(
    EXISTS (SELECT 1
              FROM config.stati_doc_fiscale_transizioni t
              JOIN config.stati_doc_fiscale sda ON sda.id = t.stato_from_id
              JOIN config.stati_doc_fiscale sdb ON sdb.id = t.stato_to_id
             WHERE t.ammesso
               AND t.solo_lotto
               AND sda.codice_interno = 'DEFINITIVA'
               AND sdb.codice_interno = 'INVIATA'),
    '6. il catalogo ammette DEFINITIVA -> INVIATA per il LOTTO: un lotto chiuso PUO'' cambiare ancora stato'
);

-- ============================================================
-- 7) ⭐ `in_gioco` sui sei stati: dice le stesse cose di `pre_fiscale`
-- ============================================================
-- ⚠️ Sui casi VERI i due flag coincidono, ed e' giusto: sono lo stesso asse.
--   Se qui divergessero, uno dei due avrebbe una formula sbagliata.
SELECT results_eq(
    $$ SELECT t.stato, f.in_gioco
         FROM tmp_fase t JOIN vendite.vw_lotti_fase f ON f.lotto_id = t.lotto_id
        WHERE t.stato <> '(ignoto)'
        ORDER BY t.stato $$,
    $$ VALUES ('ANNULLATA', false), ('DEFINITIVA', false), ('DRAFT', true),
              ('EMESSA', true), ('INVIATA', false), ('REGISTRATA', false) $$,
    '7. in_gioco sui sei stati a catalogo: coincide con pre_fiscale'
);

-- ============================================================
-- 8) ⭐⭐ E sull'IGNOTO divergono: e' tutta la ragione per cui sono due
-- ============================================================
-- ⭐ Le due domande vogliono la risposta PRUDENTE opposta:
--     · «si puo' ancora USCIRE dal giro?»  -> ignoto = NO  -> pre_fiscale f
--     · «il lotto TRATTIENE ancora?»       -> ignoto = SI' -> in_gioco    t
--   ⛔ Con un flag solo, un lotto senza stato risolvibile sarebbe LIBERO per un
--   secondo giro E non estraibile dal primo: il peggio dei due, in silenzio.
-- ⚠️ Questo test e' l'unico posto in cui la differenza fra i due flag e'
--   VISIBILE. Se un giorno qualcuno li fondesse «perche' dicono la stessa
--   cosa», e' questo che diventa rosso.
SELECT results_eq(
    $$ SELECT f.pre_fiscale, f.in_gioco
         FROM tmp_fase t JOIN vendite.vw_lotti_fase f ON f.lotto_id = t.lotto_id
        WHERE t.stato = '(ignoto)' $$,
    $$ VALUES (false, true) $$,
    '8. stato non risolvibile: pre_fiscale FALSE e in_gioco TRUE — le due prudenze sono opposte'
);

SELECT * FROM finish();

ROLLBACK;
