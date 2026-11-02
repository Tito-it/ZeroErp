-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'esito di un documento dentro un lotto — dal posto dove si scrive
--       (vendite.fatturazione_lotti_esiti) a quello dove si vede
--       (vendite.vw_dash_competenza_gruppi), piu' il presidio
-- ChangeSet: 20260907-12 (la casa), -13 (chi scrive), -14 e -15 (chi legge),
--            -16 (il perimetro torna a fare solo il perimetro),
--            20260909-20 (il marcatore torna TRE conteggi invece di uno)
--
-- Elenco test (plan 13):
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
--  13) ⭐ il TERZO zero: un documento fuori dal perimetro si distingue
--
-- ⭐ REV 2026-09-09 — IL MARCATORE TORNA TRE NUMERI, NON UNO. Dal changeSet
--   20260909-20 `fn_segna_esito_gruppo_lotto` e' `RETURNS TABLE(marcati,
--   usciti, fuori_perimetro)`: «zero marcati» ha TRE cause e una sola e' un
--   difetto. I test 3-4-6-7 leggono tutti e tre i conteggi — asserire il solo
--   `marcati` rimetterebbe le tre cause dentro lo stesso zero — e il 13 e'
--   nuovo: e' il terzo, che nessun pgTAP provava e su cui il backend ha un
--   allarme suo.
-- ⚠️ E si legge `SELECT ... FROM fn(...)`: su una `RETURNS TABLE` la forma
--   `fn(...)` in lista di select consegna la tupla intera in un campo solo — un
--   valore plausibile e falso.
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
--   archiviato o corretto. rev 2026-10-27 (lotto 4 di D7): anche i lotti
--   nascono dal builder (dbops.fn_pgtap_crea_lotto); prima tipo documento ed
--   emittente si leggevano dall'ultimo lotto del DB.
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

SELECT plan(13);

-- ============================================================
-- Fixture: due lotti — uno CON perimetro e uno SENZA
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): i lotti si COSTRUISCONO con
--   dbops.fn_pgtap_crea_lotto (madre vera, azienda di chi agisce), il secondo
--   e il terzo sullo stesso cliente del primo. Prima si scrivevano a mano coi
--   riferimenti dell'ultimo lotto del DB: da zero non c'era, e la RLS
--   rifiutava le righe di perimetro su un lotto fuori dall'operatore.
CREATE TEMP TABLE tmp_esito AS
SELECT * FROM dbops.fn_pgtap_crea_lotto('lotti gruppi esito mirato');

DO $fixture$
DECLARE
    v_mirato vendite.fatturazione_lotti.id%TYPE;
    v_massa  vendite.fatturazione_lotti.id%TYPE;
BEGIN
    SELECT t.lotto_id INTO v_mirato FROM tmp_esito t;

    -- Padre e figlio in DUE istruzioni: una CTE unica condividerebbe la stessa
    -- snapshot e la FK non troverebbe il padre.
    INSERT INTO vendite.fatturazione_lotti_gruppi (lotto_id, gruppo_key)
    VALUES (v_mirato, 'PGTAP:documento-che-fallisce'),
           (v_mirato, 'PGTAP:documento-che-riesce');

    -- ⭐ Il secondo lotto NON ha righe di perimetro: e' un giro di massa, e
    --   fino al 2026-09-07 non aveva nessun posto dove essere marcato.
    SELECT l.lotto_id INTO v_massa
      FROM dbops.fn_pgtap_crea_lotto('lotti gruppi esito massa', 'DRAFT',
                                     (SELECT t.billing_account_id FROM tmp_esito t)) l;

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
--
-- ⭐ REV 2026-09-09 — SI LEGGONO TUTTI E TRE I CONTEGGI, e non e' cosmesi.
--   Dal changeSet 20260909-20 la funzione torna `(marcati, usciti,
--   fuori_perimetro)` invece di un intero: «zero marcati» ha TRE cause e una
--   sola e' un difetto — nessun documento appeso (difetto), gli unici documenti
--   sono usciti dal giro (normale), i documenti ci sono ma nessuno e' nel
--   perimetro (sospetto). ⛔ Asserire il solo `marcati` rimetterebbe le tre
--   cause dentro lo stesso zero, cioe' proprio l'ambiguita' che quel changeSet
--   ha tolto: qui il rifiuto arriva dal GUARD, e `0|0|0` lo dice.
-- ⚠️ `SELECT ... FROM fn(...)`, non `fn(...)`: su una `RETURNS TABLE` la
--   seconda forma consegna la tupla intera in un campo solo — un valore
--   plausibile e falso, ed e' come la firma vecchia era sopravvissuta al
--   cambio.
SELECT is(
    (SELECT format('%s|%s|%s', marcati, usciti, fuori_perimetro)
       FROM vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id   => current_setting('pgtap.lotto')::bigint,
        p_stato      => 'ERRORE',
        p_gruppo_key => 'PGTAP:documento-che-fallisce')),
    '0|0|0',
    '3. un ERRORE senza causa ne'' frase non viene scritto'
);

-- ============================================================
-- 4. ✅ Marcare un documento
-- ============================================================
SELECT is(
    (SELECT format('%s|%s|%s', marcati, usciti, fuori_perimetro)
       FROM vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id         => current_setting('pgtap.lotto')::bigint,
        p_stato            => 'ERRORE',
        p_gruppo_key       => 'PGTAP:documento-che-fallisce',
        p_errore_codice    => 'E_PULL_COMMESSA',
        p_errore_messaggio => 'ROOT source mancante')),
    '1|0|0',
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
--
-- ⚠️ L'id e' POSITIVO e non `-1`, ed e' una correzione del 2026-09-08. Con un
--   id negativo lo zero arriva dal GUARD di parametro (20260908-19), non dalla
--   risoluzione: il test sarebbe passato anche a risoluzione rotta — verde per
--   sottrazione. Un id positivo e inesistente percorre la strada vera e trova
--   zero documenti, che e' la condizione che questo test dichiara di provare.
--
-- ⭐ E I TRE ZERI DICONO QUALE dei tre casi e' questo: la commessa non alimenta
--   NESSUN documento, quindi non c'e' niente da marcare, niente di uscito e
--   niente fuori perimetro. `0|0|0` distingue questo caso da «i documenti
--   c'erano ma sono tutti usciti» (`0|N|0`) e da «c'erano ma nessuno e' nel
--   perimetro» (`0|0|N`), che il ritorno a un numero solo confondeva.
SELECT is(
    (SELECT format('%s|%s|%s', marcati, usciti, fuori_perimetro)
       FROM vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id         => current_setting('pgtap.lotto')::bigint,
        p_stato            => 'ERRORE',
        p_commessa_id      => 2147483647,
        p_errore_codice    => 'E_PULL_COMMESSA',
        p_errore_messaggio => 'commessa che non c''entra')),
    '0|0|0',
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
-- ⚠️ `fuori_perimetro` DEVE essere 0, e la coppia col test 13 e' il punto: qui
--   il lotto non dichiara nessun perimetro, quindi «fuori» non e' una domanda
--   che si possa fare — se contasse 1 il backend avviserebbe su un giro di
--   massa perfettamente normale.
SELECT is(
    (SELECT format('%s|%s|%s', marcati, usciti, fuori_perimetro)
       FROM vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id         => current_setting('pgtap.lotto_massa')::bigint,
        p_stato            => 'ERRORE',
        p_gruppo_key       => 'PGTAP:documento-di-un-giro-di-massa',
        p_errore_codice    => 'E_PULL_COMMESSA',
        p_errore_messaggio => 'fallito in un giro senza perimetro')),
    '1|0|0',
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
    -- rev 2026-10-27 (lotto 4 di D7): il lotto dal builder, poi COMPLETATO
    --   per la strada del runner (IN_ESECUZIONE -> COMPLETATO, giudicata dal
    --   guard della matrice config.transizioni_stati_lotto_job). Prima: INSERT
    --   a mano gia' COMPLETATO, coi riferimenti pescati.
    SELECT l.lotto_id INTO v_lotto_id
      FROM dbops.fn_pgtap_crea_lotto('lotti gruppi esito chiuso', 'DRAFT',
                                     (SELECT t.billing_account_id FROM tmp_esito t)) l;

    UPDATE vendite.fatturazione_lotti SET stato_lotto = 'IN_ESECUZIONE' WHERE id = v_lotto_id;
    UPDATE vendite.fatturazione_lotti SET stato_lotto = 'COMPLETATO'    WHERE id = v_lotto_id;

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

-- ============================================================
-- 13. ⭐ IL TERZO ZERO: «fuori dal perimetro» si distingue
-- ============================================================
-- ⭐ E' il caso su cui il backend ha un allarme SUO (`fuori_perimetro > 0` in
--   `_marca_esito_gruppi`), ed e' l'unico dei tre che il database non provava
--   da nessuna parte: i test del backend lo verificano su un ritorno FINTO, e
--   un mock non si accorge se la funzione smettesse di contarlo.
-- ⚠️ Un documento che il lotto NON ha dichiarato non si marca — marcarlo
--   attribuirebbe un errore a un documento che questo giro non ha mai preso in
--   carico — ma il rifiuto va DETTO, e detto in modo diverso da «non c'era
--   niente da fare»: e' l'unico dei tre zeri che chiede a qualcuno di andare a
--   guardare.
-- ⛔ Il lotto e' quello MIRATO, che un perimetro ce l'ha: sul lotto di massa la
--   stessa chiamata scrive (test 7), perche' senza perimetro non c'e' nessun
--   fuori.
SELECT is(
    (SELECT format('%s|%s|%s', marcati, usciti, fuori_perimetro)
       FROM vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id         => current_setting('pgtap.lotto')::bigint,
        p_stato            => 'ERRORE',
        p_gruppo_key       => 'PGTAP:documento-mai-dichiarato',
        p_errore_codice    => 'E_PULL_COMMESSA',
        p_errore_messaggio => 'documento che questo lotto non ha preso in carico')),
    '0|0|1',
    '13. un documento fuori dal perimetro non si marca, e il conteggio lo dice'
);

SELECT * FROM finish();
ROLLBACK;
