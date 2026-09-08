-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'esito di un documento dentro un lotto — dal posto dove si scrive
--       (vendite.fatturazione_lotti_esiti) a quello dove si vede
--       (vendite.vw_dash_competenza_gruppi), piu' il presidio
-- ChangeSet: 20260907-12 (la casa), -13 (chi scrive), -14 e -15 (chi legge),
--            -16 (il perimetro torna a fare solo il perimetro)
--
-- Elenco test (plan 12):
--   1) la casa dell'esito ha le sue colonne
--   2) ⭐ il vocabolario e' lo STESSO del gemello, e si legge dai vincoli
--   3) ⛔ un errore senza causa ne' frase non si scrive
--   4) ✅ marcare un documento: una riga, e i campi parlano
--   5) ✅ COMPLETED non lascia residui dell'errore precedente
--   6) ⛔ una commessa che non alimenta niente in quel lotto non scrive
--   7) ⭐ un lotto SENZA perimetro viene marcato lo stesso — il caso per cui
--      questa casa e' nata
--   8) ⭐ un secondo tentativo sovrascrive, non duplica
--   9) la competenza espone le cinque colonne dell'ultimo tentativo
--  10) ⛔ e NON ha smesso di dire se il documento e' ancora da emettere
--  11) ⛔ un lotto chiuso coi documenti a posto NON viene nominato (COSTRUITO)
--  12) ⭐ ...e si accende davvero, su un caso COSTRUITO
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ IL CASO DA CUI NASCE. Il lotto LTF-0009578 ha preso in carico tre ordini
--   e ne ha fatturati due. Il terzo e' caduto al primo passo, e non essendo mai
--   diventato fattura non aveva nessuna riga dove comparire: fuori dal lotto, e
--   dentro i documenti da emettere senza un segno. Sembrava fatturabile.
--
-- ⭐ E LA SECONDA META', del 2026-09-07. L'esito viveva sulle righe del
--   PERIMETRO, che i giri di massa non scrivono: li' un documento fallito
--   restava muto come prima. Adesso l'esito ha una casa sua, e la riga si crea
--   invece di dover essere trovata — il test 7 e' quello che lo verifica.
--
-- ⚠️ TUTTI I CASI SONO COSTRUITI. Lotti e documenti li fabbrica la fixture:
--   nessuna asserzione si appoggia a un lotto vero, che domani puo' essere
--   archiviato o corretto. L'unica cosa presa dai dati sono i due riferimenti
--   obbligatori del lotto (tipo documento ed emittente), letti da un lotto
--   esistente perche' devono stare nel perimetro dell'operatore.
--
-- ⛔ QUELLO CHE QUESTO FILE NON PROVA, E VA DETTO: il ritrovamento del
--   documento PARTENDO DALLA COMMESSA quando la commessa lo alimenta davvero.
--   Costruirlo richiederebbe una commessa con le sue attivita' — una fixture
--   piu' grande della cosa da provare. Il test 6 copre il verso che si puo'
--   costruire (una commessa che non c'entra non scrive niente); il verso
--   positivo si collauda sul giro vero, ed e' un debito dichiarato.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- ============================================================
-- Fixture: due lotti — uno CON perimetro e uno SENZA
-- ============================================================
CREATE TEMP TABLE tmp_esito AS
SELECT l.tipo_doc_fiscale_id, l.emittente_soggetto_ruolo_id
  FROM vendite.fatturazione_lotti l
 ORDER BY l.id DESC
 LIMIT 1;

DO $fixture$
DECLARE
    v_mirato vendite.fatturazione_lotti.id%TYPE;
    v_massa  vendite.fatturazione_lotti.id%TYPE;
BEGIN
    INSERT INTO vendite.fatturazione_lotti
        (codice, competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP-ESITO-MIRATO', date_trunc('month', CURRENT_DATE)::date,
           t.tipo_doc_fiscale_id, t.emittente_soggetto_ruolo_id
      FROM tmp_esito t
    RETURNING id INTO v_mirato;

    -- Padre e figlio in DUE istruzioni: una CTE unica condividerebbe la stessa
    -- snapshot e la FK non troverebbe il padre.
    INSERT INTO vendite.fatturazione_lotti_gruppi (lotto_id, gruppo_key)
    VALUES (v_mirato, 'PGTAP:documento-che-fallisce'),
           (v_mirato, 'PGTAP:documento-che-riesce');

    -- ⭐ Il secondo lotto NON ha righe di perimetro: e' un giro di massa, e
    --   fino al 2026-09-07 non aveva nessun posto dove essere marcato.
    INSERT INTO vendite.fatturazione_lotti
        (codice, competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP-ESITO-MASSA', date_trunc('month', CURRENT_DATE)::date,
           t.tipo_doc_fiscale_id, t.emittente_soggetto_ruolo_id
      FROM tmp_esito t
    RETURNING id INTO v_massa;

    PERFORM set_config('pgtap.lotto', v_mirato::text, true);
    PERFORM set_config('pgtap.lotto_massa', v_massa::text, true);
END
$fixture$;

-- ============================================================
-- 1. La casa dell'esito ha le sue colonne
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM information_schema.columns
      WHERE table_schema = 'vendite'
        AND table_name   = 'fatturazione_lotti_esiti'
        AND column_name IN ('lotto_id', 'gruppo_key', 'stato_esecuzione',
                            'errore_codice', 'errore_messaggio', 'errore_quando')),
    6,
    '1. vendite.fatturazione_lotti_esiti ha le colonne dell''esito'
);

-- ============================================================
-- 2. ⭐ Stesso vocabolario del gemello, A MENO DEL SURPLUS DICHIARATO
-- ============================================================
-- ⛔ Non si scrive a mano l'elenco dei valori: sarebbe una fotografia, e il
--   giorno in cui uno dei due ne ammette uno in piu' questo test resterebbe
--   verde mentre le due colonne hanno smesso di parlare la stessa lingua.
--
-- 🔴 REV 2026-09-08 — l'invariante NON e' piu' «identici», ed e' una decisione.
--   `ESCLUSO` e' entrato sul solo lato ESITO (20260908-01), e li' deve restare:
--   dice «l'operatore ha tolto questo DOCUMENTO dal giro», e una FATTURA quello
--   stato non lo puo' avere — quando un documento esce, la sua bozza viene
--   CANCELLATA e la riga di ponte sparisce. Non esiste una fattura «esclusa ma
--   ancora li'».
--   ⛔ E il test NON e' stato indebolito a un confronto vago: si sottrae il
--   surplus DICHIARATO. Cosi' resta rosso in tutti e tre i casi che contano —
--   il lato fattura acquista uno stato, il lato esito ne acquista uno che non
--   e' fra quelli dichiarati, oppure `ESCLUSO` sparisce dal lato esito.
--   E' la forma «l'invariante non e' vuoto, e' nessun NON_DICHIARATO».
SELECT is(
    (SELECT array_agg(v ORDER BY v)
       FROM (SELECT unnest(regexp_matches(pg_get_constraintdef(oid), '''([A-Z_]+)''', 'g')) AS v
               FROM pg_constraint
              WHERE conname = 'chk_fatturazione_lotti_esiti_stato') s
      WHERE s.v <> ALL (ARRAY['ESCLUSO'])),
    (SELECT array_agg(v ORDER BY v)
       FROM (SELECT unnest(regexp_matches(pg_get_constraintdef(oid), '''([A-Z_]+)''', 'g')) AS v
               FROM pg_constraint
              WHERE conname = 'chk_fatturazione_lf_stato_esecuzione') s),
    '2. l''esito e la fattura ammettono gli stessi stati, meno il surplus dichiarato (ESCLUSO)'
);

-- ============================================================
-- 3. ⛔ Un errore muto non si scrive
-- ============================================================
-- Se passasse, la riga direbbe «è andata male» e nient'altro: chi la legge non
-- saprebbe né che cosa sistemare né dove andare.
SELECT is(
    vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id   => current_setting('pgtap.lotto')::bigint,
        p_stato      => 'ERRORE',
        p_gruppo_key => 'PGTAP:documento-che-fallisce'),
    0,
    '3. un ERRORE senza causa ne'' frase non viene scritto'
);

-- ============================================================
-- 4. ✅ Marcare un documento
-- ============================================================
SELECT is(
    vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id         => current_setting('pgtap.lotto')::bigint,
        p_stato            => 'ERRORE',
        p_gruppo_key       => 'PGTAP:documento-che-fallisce',
        p_errore_codice    => 'E_PULL_COMMESSA',
        p_errore_messaggio => 'ROOT source mancante'),
    1,
    '4. l''esito viene appeso al documento indicato, e a quello solo'
);

-- ============================================================
-- 5. ✅ COMPLETED non lascia residui
-- ============================================================
-- ⭐ Un documento che ci riprova e stavolta riesce non deve restare con addosso
--   il messaggio del tentativo di prima: sarebbe un rosso che non scade mai.
DO $riuscito$
BEGIN
    PERFORM vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id   => current_setting('pgtap.lotto')::bigint,
        p_stato      => 'COMPLETED',
        p_gruppo_key => 'PGTAP:documento-che-fallisce');
END
$riuscito$;

SELECT ok(
    (SELECT stato_esecuzione = 'COMPLETED'
        AND errore_codice IS NULL
        AND errore_messaggio IS NULL
        AND errore_quando IS NULL
       FROM vendite.fatturazione_lotti_esiti
      WHERE lotto_id = current_setting('pgtap.lotto')::bigint
        AND gruppo_key = 'PGTAP:documento-che-fallisce'),
    '5. un documento riuscito non conserva l''errore del tentativo precedente'
);

-- ============================================================
-- 6. ⛔ Il perimetro del lotto tiene
-- ============================================================
-- Una commessa che in questo lotto non alimenta niente non deve scrivere
-- niente: ⚠️ marcare «il primo documento che capita» sarebbe peggio del non
-- marcare, perché attribuirebbe un errore a un documento che non c'entra.
SELECT is(
    vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id         => current_setting('pgtap.lotto')::bigint,
        p_stato            => 'ERRORE',
        p_commessa_id      => -1,
        p_errore_codice    => 'E_PULL_COMMESSA',
        p_errore_messaggio => 'commessa che non c''entra'),
    0,
    '6. una commessa che non alimenta niente in quel lotto non scrive'
);

-- ============================================================
-- 7. ⭐ Il caso per cui questa casa e' nata: il giro SENZA perimetro
-- ============================================================
-- ⛔ Fino al 2026-09-07 l'esito viveva sulle righe del perimetro, e un giro di
--   massa non ne scrive nessuna: la marcatura non trovava niente da aggiornare
--   e tornava 0. Il documento fallito restava muto, e nessuno lo sapeva.
-- ⭐ Adesso la riga si CREA. E il backend non e' cambiato: e' la stessa
--   chiamata di prima, che prima non trovava casa.
SELECT is(
    vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id         => current_setting('pgtap.lotto_massa')::bigint,
        p_stato            => 'ERRORE',
        p_gruppo_key       => 'PGTAP:documento-di-un-giro-di-massa',
        p_errore_codice    => 'E_PULL_COMMESSA',
        p_errore_messaggio => 'fallito in un giro senza perimetro'),
    1,
    '7. un lotto senza perimetro riceve comunque l''esito del suo documento'
);

-- ============================================================
-- 8. ⭐ Un secondo tentativo sovrascrive, non duplica
-- ============================================================
-- ⚠️ La chiave e' (lotto, documento): la domanda a cui questa casa risponde e'
--   «com'e' finita», non «quante volte ci abbiamo provato». Lo storico dei
--   tentativi vive nel giornale del lotto, che e' fatto per quello.
DO $ancora$
BEGIN
    PERFORM vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id         => current_setting('pgtap.lotto_massa')::bigint,
        p_stato            => 'ERRORE',
        p_gruppo_key       => 'PGTAP:documento-di-un-giro-di-massa',
        p_errore_codice    => 'E_PULL_COMMESSA',
        p_errore_messaggio => 'secondo tentativo, stesso documento');
END
$ancora$;

SELECT is(
    (SELECT count(*)::int
       FROM vendite.fatturazione_lotti_esiti
      WHERE lotto_id = current_setting('pgtap.lotto_massa')::bigint
        AND gruppo_key = 'PGTAP:documento-di-un-giro-di-massa'),
    1,
    '8. due tentativi sullo stesso documento lasciano UNA riga, non due'
);

-- ============================================================
-- 9. La competenza porta l'esito dell'ultimo tentativo
-- ============================================================
-- ⭐ E' il pezzo che rende visibile tutto il resto: senza queste colonne
--   l'esito starebbe scritto e non lo leggerebbe nessuno.
SELECT is(
    (SELECT count(*)::int
       FROM information_schema.columns
      WHERE table_schema = 'vendite'
        AND table_name   = 'vw_dash_competenza_gruppi'
        AND column_name IN ('ultimo_esito', 'ultimo_errore_codice',
                            'ultimo_errore_messaggio', 'ultimo_errore_quando',
                            'ultimo_lotto_codice')),
    5,
    '9. i documenti da emettere portano l''esito dell''ultimo tentativo'
);

-- ============================================================
-- 10. ⛔ Il segno non ha spento l'emittibilita'
-- ============================================================
-- ⛔ E' il presidio della decisione di Tid del 2026-09-06, e sta qui perche' e'
--   la cosa che qualcuno, fra sei mesi, sara' tentato di «sistemare»: togliere
--   dall'elenco i documenti che hanno un errore. Sarebbe tornare al problema di
--   partenza dall'altra parte — il documento sparirebbe di nuovo.
SELECT is(
    (SELECT count(*)::int
       FROM information_schema.columns
      WHERE table_schema = 'vendite'
        AND table_name   = 'vw_dash_competenza_gruppi'
        AND column_name IN ('stadio', 'commessa_emittibile')),
    2,
    '10. un documento con un errore resta comunque uno che dice se e'' da emettere'
);

-- ============================================================
-- 11..12. Il presidio della decisione «3 su 3 come 2 su 3»
-- ============================================================
-- ⭐ CHE COSA SORVEGLIA. Dal 2026-09-06 il passo non solleva piu' quando
--   falliscono TUTTE le commesse: cosi' i segni non vengono annullati dal
--   rollback. Ma senza l'eccezione lo stato finale del lotto lo decide chi
--   guarda fatture in errore e segnalazioni critiche — e con tutte le commesse
--   fallite le fatture NON NASCONO.
--   ⇒ La salvezza dipende da segnalazioni scritte da un altro pezzo. Se
--     cambiassero forma, un fallimento totale si presenterebbe come «Pipeline
--     completata», in silenzio. Questa vista e' li' per quel giorno.
--
-- ⛔ IL TEST 11 CHIEDEVA CHE LA VISTA FOSSE VUOTA SULL'INTERA POPOLAZIONE, e
--   quella forma e' stata tolta il 2026-09-07. Non era «legata a un lotto»: era
--   legata a TUTTI. E aveva i due difetti che l'intestazione di questo file
--   dichiara di non avere:
--     * su un database ricostruito da zero — cioe' in CI — la vista e' vuota
--       perche' non c'e' niente, quindi il test passava **a vuoto**: verde
--       senza provare nulla. E' il «verde per sottrazione» di AGENTS.md;
--     * su dbdev diventava rosso al primo uso reale che produce quello stato,
--       e un rosso che non e' una regressione insegna a ignorare i rossi.
--   ⚠️ E contraddiceva la riga «TUTTI I CASI SONO COSTRUITI... nessuna
--   asserzione si appoggia a un lotto vero» scritta in testa a questo file.
--
-- ⭐ Sostituito dal CONTROLLO NEGATIVO sullo stesso lotto costruito: prima la
--   contraddizione non c'e' e la vista tace, poi la si crea e la vista parla. La
--   coppia prova le due direzioni senza dipendere da nessun dato reale.
--
-- ⚠️ La domanda «e il database VERO e' pulito?» non e' sparita: si risponde
--   GUARDANDO la vista, che e' cio' per cui un presidio esiste. Un pgTAP che
--   interroga la popolazione non e' un test, e' monitoraggio travestito — e il
--   2026-09-07 quella domanda ha avuto la sua prima risposta vera: il lotto
--   LTF-0009900, COMPLETATO con una segnalazione critica e un documento in
--   E_PULL_COMMESSA. Registrata nel brief, non qui.
DO $lotto_sano$
DECLARE
    v_lotto_id vendite.fatturazione_lotti.id%TYPE;
BEGIN
    INSERT INTO vendite.fatturazione_lotti
        (codice, competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id,
         stato_lotto)
    SELECT 'PGTAP-CONTRADDIZIONE', date_trunc('month', CURRENT_DATE)::date,
           t.tipo_doc_fiscale_id, t.emittente_soggetto_ruolo_id, 'COMPLETATO'
      FROM tmp_esito t
    RETURNING id INTO v_lotto_id;

    -- Un lotto chiuso con un documento andato BENE: nessuna contraddizione.
    PERFORM vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id   => v_lotto_id,
        p_stato      => 'COMPLETED',
        p_gruppo_key => 'PGTAP:documento-riuscito-in-lotto-chiuso');

    PERFORM set_config('pgtap.lotto_chiuso', v_lotto_id::text, true);
END
$lotto_sano$;

-- ⛔ Il controllo negativo: senza, il test 12 passerebbe anche su una vista che
--   nomina QUALUNQUE lotto chiuso — cioe' su un presidio che grida sempre.
SELECT is_empty(
    format($$SELECT lotto_codice FROM vendite.vw_lotti_chiusi_con_gruppi_in_errore
              WHERE lotto_id = %s$$, current_setting('pgtap.lotto_chiuso')),
    '11. un lotto COMPLETATO con i suoi documenti a posto NON viene nominato'
);

-- ============================================================
-- 12. ⭐ ...e il presidio si accende davvero
-- ============================================================
-- ⛔ Senza questo, il test 11 proverebbe solo che la vista tace — non che sappia
--   accorgersi di qualcosa.
DO $contraddizione$
BEGIN
    PERFORM vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id         => current_setting('pgtap.lotto_chiuso')::bigint,
        p_stato            => 'ERRORE',
        p_gruppo_key       => 'PGTAP:documento-fallito-in-lotto-chiuso',
        p_errore_codice    => 'E_PULL_COMMESSA',
        p_errore_messaggio => 'costruito dal test');
END
$contraddizione$;

SELECT is(
    (SELECT gruppi_in_errore::int
       FROM vendite.vw_lotti_chiusi_con_gruppi_in_errore
      WHERE lotto_id = current_setting('pgtap.lotto_chiuso')::bigint),
    1,
    '12. un lotto COMPLETATO con un documento in ERRORE viene nominato'
);

SELECT * FROM finish();
ROLLBACK;
