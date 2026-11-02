-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_numera_fattura_opz_emessa — non si numera un documento che
--       rettifica una fattura ancora senza numero
--       (E_FATTURA_RETTIFICATA_SENZA_NUMERO, changeSet 20260821-05)
-- ------------------------------------------------------------
-- ⛔ Prima di 20260821-05 questo file e' ROSSO su UN test solo — il 2 — e vale
--    la pena sapere perche', misurato il 2026-08-21:
--      2  have E_FATTURA_NON_NUMERABILE_INCOERENTE, want
--         E_FATTURA_RETTIFICATA_SENZA_NUMERO   <- ⭐ l'unico che misura il difetto
--      3  VERDE anche senza la guardia, e NON perche' la guardia funzioni: la
--         numerazione si ferma comunque prima, su un'altra precondizione
--         (piano rate). Il numero resta NULL per un motivo che non c'entra.
--      1,4,5 verdi anche senza: sono invarianti, non misure.
--    ⚠️ Il 3 e' quindi VERDE PER SOTTRAZIONE in questa fixture, ed e' scritto
--    qui perche' chi legge «cinque test» sappia che il difetto lo misura UNO.
--    Resta utile: il giorno in cui la fixture soddisfacesse anche il piano rate,
--    il 3 diventerebbe l'unica prova che il numero non e' stato consumato.
--
-- 📌 E c'e' una conseguenza per chi valuta il rischio: oggi, sui dati veri, una
--    nota di credito non si numera comunque prima del tempo — la fermerebbe
--    quell'altra precondizione. Il difetto segnalato dal BE e' reale ma
--    MASCHERATO da un controllo che parla d'altro, e un controllo che protegge
--    per caso non e' un presidio: il giorno in cui il piano rate c'e', la nota
--    passerebbe. E' il motivo per cui la guardia si scrive lo stesso.
--    Con il changeSet applicato: 5/5.
--
-- Indice test (1..5):
--   1) fixture: due documenti, la NC rettifica riga per riga il padre, e
--      nessuno dei due e' numerato
--   2) ⭐ numerare la NC RIFIUTA, con E_FATTURA_RETTIFICATA_SENZA_NUMERO nel
--      canale CONSTRAINT
--   3) e la NC e' rimasta senza numero: il rifiuto arriva PRIMA che il numero
--      venga consumato — che e' l'unica cosa che non si torna indietro
--   4) nessuna regressione: su una fattura ORDINARIA la guardia non vede nulla
--   5) ⭐ dato un numero al padre, la guardia si spegne
--   6) ⭐ il rifiuto porta il BERSAGLIO, e il primo elemento e' il documento
--      da numerare (T-3b)
--   7) ⭐ due padri senza numero: tre bersagli, nell'ordine dichiarato
--   8) ⭐ la FRASE non porta nessun id e porta il conteggio dei bloccanti
--
-- ⚠️ PERCHE' IL TEST 5 NON DICE «la NC si numera». Numerare ha ALTRE
--    precondizioni che non c'entrano con questa guardia: la prima che si
--    incontra e' «piano rate assente», sollevata da vendite.fn_assign_numero_fattura
--    DOPO di noi. Soddisfarle qui vorrebbe dire costruire mezza fatturazione in
--    una fixture e collaudare quella invece di questa guardia. Si asserisce
--    quindi che il codice sollevato NON sia piu' il nostro: e' esattamente la
--    proprieta' che serve — la guardia si e' spenta — e non una di meno.
--
-- ⚠️ COSA QUESTO FILE NON MISURA, e va detto invece di sembrare coperto: il
--    ramo FAIL-CLOSED sulla visibilita'. La guardia usa dei LEFT JOIN e conta
--    come bloccante anche la riga il cui documento padre non e' VISIBILE
--    (RLS, perimetro emittente diverso). Per esercitarlo servirebbe una
--    seconda fattura intestata a un altro emittente e un operatore che non la
--    veda: una fixture a due perimetri, che e' un file a se'. E un puntatore
--    penzolante non si puo' fabbricare — fatture_righe.riga_rettificata_id ha
--    una chiave esterna (fk_fatture_righe_riga_rettificata).
--
-- ⚠️ Il codice di dominio si legge dal canale CONSTRAINT dell'eccezione, non
--    dal testo: e' il contratto di script.fn_log_and_raise_error, e cosi' il
--    file e' verde anche prima che il mirror CSV di 80_data carichi la riga
--    del codice nuovo.
--
-- ⭐ AGGIUNTO IL 2026-08-23 — i test 6 e 7: il rifiuto porta un BERSAGLIO.
--   Brief: brief-db-bersaglio-errore.md §6 L2.
--
-- ⭐ AGGIORNATO IL 2026-08-24 — il passo T-3b (changeSet 20260824-13 + la riga
--   937 di messaggi_errore.csv). Due cose cambiano, e vanno lette insieme:
--
--   · IL BERSAGLIO HA DUE RUOLI. Il primo elemento e' il DOCUMENTO DA NUMERARE
--     (la nota), poi vengono i padri bloccanti visibili in ordine di id. I test
--     6 e 7 asseriscono percio' la stringa ESATTA e non piu' l'insieme:
--     l'ordine e' diventato una proprieta' che conta, perche' il canale
--     compatto tiene i PRIMI CINQUE elementi e in testa deve stare la cosa che
--     dice «quale documento».
--
--   · LA FRASE NON PORTA PIU' NESSUN ID: porta il CONTEGGIO dei bloccanti. E'
--     il test 8, ed e' lo scopo dell'intero cantiere — il messaggio smette di
--     mettere una chiave interna davanti a una persona.
--
--   ⛔ IL TEST 8 E' ROSSO FINCHE' IL CSV NON E' CARICATO, ed e' voluto: misura
--     la coppia. Con la funzione applicata e il catalogo indietro, format()
--     riceve un valore e ne chiede due, ripiega sul template non composto e
--     scrive W_MESSAGGIO_ARITA — il conteggio non compare e il test lo vede.
--     E' la trappola del §5.3 del brief, presa dal lato del collaudo.
--
-- ⛔ COSA QUESTO FILE **NON** MISURA, e va detto invece di lasciarlo credere:
--   il ramo FAIL-CLOSED. Quando la fattura rettificata sta fuori dal perimetro
--   emittente di chi opera, la guardia blocca lo stesso (LEFT JOIN, «non posso
--   dimostrare che sia numerata») ma il bersaglio dev'essere VUOTO — a un
--   documento che non si puo' aprire non si manda nessuno. Qui non e' coperto:
--   servirebbe una seconda anagrafica emittente e una sessione fuori scope, e
--   il perimetro non si puo' spostare con un UPDATE perche' la policy lo
--   rifiuterebbe in scrittura. Il ramo e' presidiato dalla forma del codice
--   (JOIN interni contro LEFT JOIN, changeSet 20260823-03) e da questa riga.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- rev 2026-10-27 (lotto 4 di D7): via il vecchio «SET LOCAL app.current_user_id
--   = '1'» (con ruolo OPERATORE): l'utente 1 da zero non esiste, e su dev e' un
--   super admin senza azienda (la fattura moriva sulla RLS). Chi agisce e'
--   l'operatore del contesto qui sopra. Il cliente e l'articolo si COSTRUISCONO:
--   prima si pescavano il primo BA con emittente e l'ultimo articolo non
--   composito, e da zero non c'erano. Ora il BA viene da
--   dbops.fn_pgtap_crea_cliente_ba (legato all'azienda di chi agisce) e
--   l'articolo da dbops.fn_pgtap_crea_articolo (servizio, non composito).
--   Emittente e registro sono quelli dell'operatore. Restano letture di
--   catalogo di SEED: unita_misura, valute, iva, tipi_doc_fiscale,
--   stati_doc_fiscale, nature.
--   ⚠️ Le testate restano scritte da nnc_mk_doc e non da
--   dbops.fn_pgtap_crea_fattura: il builder non sceglie la natura del
--   documento (FATTURA / NOTA_CREDITO), che qui si scrive alla nascita.
CREATE TEMP TABLE tmp_cli_nnc AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('numera nota credito riferimento');

CREATE TEMP TABLE tmp_refs_nnc AS
SELECT
  c.billing_account_id                     AS billing_account_id,
  c.utility_id                             AS utility_id,
  script.fn_pgtap_emittente_sr_operatore() AS emittente_sr_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-NNC-ART', false)                                    AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)            AS iva_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)                               AS tipo_doc_fiscale_id,
  (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno='DRAFT' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1) AS stato_draft_id,
  script.fn_pgtap_registro_fattura()                         AS registro_id,
  config.fn_get_natura_doc_fiscale_id('FATTURA')      AS natura_fattura_id,
  config.fn_get_natura_doc_fiscale_id('NOTA_CREDITO') AS natura_nc_id
FROM tmp_cli_nnc c;

-- Un documento con una riga. `p_natura_id` distingue il padre dalla nota, ma
-- la guardia NON lo legge: guarda le righe. Sta qui per realismo, non perche'
-- serva — ed e' il punto del §44.
CREATE OR REPLACE FUNCTION pg_temp.nnc_mk_doc(p_natura_id bigint, p_qta numeric, p_prezzo numeric)
RETURNS TABLE(fattura_id bigint, riga_id bigint) AS $$
DECLARE r RECORD; v_f bigint; v_r bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_nnc;
  INSERT INTO vendite.fatture (registro_id, data, tipo_doc_fiscale_id, stato_doc_fiscale_id,
      emittente_soggetto_ruolo_id, billing_account_id, utility_id, valuta_id, tasso_cambio,
      natura_doc_id, meta)
  VALUES (r.registro_id, DATE '2026-08-21', r.tipo_doc_fiscale_id, r.stato_draft_id,
      r.emittente_sr_id, r.billing_account_id, r.utility_id, r.valuta_id, 1,
      p_natura_id, jsonb_build_object('test_scope','pgtap_numera_nc'))
  RETURNING id INTO v_f;

  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione,
      uom_id, qta, prezzo_unitario, iva_id, imponibile_riga, competenza_dal, competenza_al)
  VALUES (v_f, 1, r.articolo_id, 'Riga pgTAP numerazione NC', r.uom_id, p_qta, p_prezzo,
      r.iva_id, p_qta * p_prezzo, script.fn_data_operativa(), script.fn_data_operativa())
  RETURNING id INTO v_r;

  RETURN QUERY SELECT v_f, v_r;
END $$ LANGUAGE plpgsql;

-- ⭐ Il gemello del verbo, e restituisce l'altro canale: il BERSAGLIO.
--   Due funzioni e non una con due colonne, perche' i test esistenti chiamano
--   gia' nnc_esito e cambiarle firma vorrebbe dire riscriverli tutti.
--   ⚠️ `text` esplicito: e' un canale dell'eccezione, non il valore di una
--   colonna.
CREATE OR REPLACE FUNCTION pg_temp.nnc_bersaglio(p_fattura_id bigint)
RETURNS text AS $$
DECLARE v_bers text;
BEGIN
  PERFORM vendite.fn_numera_fattura_opz_emessa(p_fattura_id, false);
  RETURN 'NESSUN ERRORE';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_bers = PG_DATATYPE_NAME;
  RETURN COALESCE(v_bers, '');
END $$ LANGUAGE plpgsql;

-- ⭐ IL TERZO GEMELLO (24-08-2026): la FRASE che legge l'operatore. Serve al
--   test 8, che e' lo scopo del passo T-3b — dopo di esso il messaggio non deve
--   piu' contenere nessuna chiave interna.
--   ⚠️ `MESSAGE_TEXT` e non `SQLERRM`: sono la stessa cosa qui, ma la forma con
--   GET STACKED DIAGNOSTICS e' quella dei due gemelli sopra e si legge uguale.
CREATE OR REPLACE FUNCTION pg_temp.nnc_messaggio(p_fattura_id bigint)
RETURNS text AS $$
DECLARE v_msg text;
BEGIN
  PERFORM vendite.fn_numera_fattura_opz_emessa(p_fattura_id, false);
  RETURN 'NESSUN ERRORE';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
  RETURN COALESCE(v_msg, '');
END $$ LANGUAGE plpgsql;

-- ⭐ L'esito della numerazione come CODICE di dominio (canale CONSTRAINT), o
--    'OK' se e' passata. E' il contratto di script.fn_log_and_raise_error e non
--    lega il test alla formulazione del catalogo.
CREATE OR REPLACE FUNCTION pg_temp.nnc_esito(p_fattura_id bigint)
RETURNS text AS $$
DECLARE v_cod text;
BEGIN
  PERFORM vendite.fn_numera_fattura_opz_emessa(p_fattura_id, false);
  RETURN 'OK';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_cod = CONSTRAINT_NAME;
  RETURN COALESCE(NULLIF(v_cod, ''), 'SQLSTATE:' || SQLSTATE);
END $$ LANGUAGE plpgsql;

-- ============================================================
-- FIXTURE: un padre e una nota che ne rettifica la riga.
-- ⚠️ Padre e figlio in DUE istruzioni: le CTE che scrivono condividono la
--    stessa snapshot, e una policy che risolve il perimetro dal padre non lo
--    troverebbe.
-- ============================================================
CREATE TEMP TABLE tmp_padre AS
SELECT * FROM pg_temp.nnc_mk_doc((SELECT natura_fattura_id FROM tmp_refs_nnc), 10, 25);

CREATE TEMP TABLE tmp_nc AS
SELECT * FROM pg_temp.nnc_mk_doc((SELECT natura_nc_id FROM tmp_refs_nnc), -4, 25);

UPDATE vendite.fatture_righe
   SET riga_rettificata_id = (SELECT riga_id FROM tmp_padre)
 WHERE id = (SELECT riga_id FROM tmp_nc);

SELECT is(
  (SELECT count(*)::int FROM vendite.fatture
    WHERE id IN ((SELECT fattura_id FROM tmp_padre), (SELECT fattura_id FROM tmp_nc))
      AND numero IS NULL)::text
  || '|' ||
  (SELECT (riga_rettificata_id = (SELECT riga_id FROM tmp_padre))::text
     FROM vendite.fatture_righe WHERE id = (SELECT riga_id FROM tmp_nc)),
  '2|true',
  '1) fixture: due documenti senza numero, e la nota rettifica la riga del padre'
);

-- ============================================================
-- IL RIFIUTO
-- ⚠️ Il verbo in un'istruzione SEPARATA dall'asserzione: la snapshot di
--    statement leggerebbe PRIMA delle scritture.
-- ============================================================
CREATE TEMP TABLE tmp_esito_1 AS
SELECT pg_temp.nnc_esito((SELECT fattura_id FROM tmp_nc)) AS esito;

SELECT is(
  (SELECT esito FROM tmp_esito_1),
  'E_FATTURA_RETTIFICATA_SENZA_NUMERO',
  '2) numerare la nota di credito e'' RIFIUTATO, col codice giusto'
);

-- ⭐ Il numero non e' stato consumato: il rifiuto arriva PRIMA
--    dell'assegnazione, che e' l'unico passo irreversibile del giro.
SELECT is(
  (SELECT numero FROM vendite.fatture WHERE id = (SELECT fattura_id FROM tmp_nc)),
  NULL::bigint,
  '3) e il numero non e'' stato consumato: la nota e'' ancora senza numero'
);

-- ============================================================
-- 4) NESSUNA REGRESSIONE su un documento che non rettifica niente.
--    Il padre non ha righe con riga_rettificata_id, quindi la guardia non deve
--    nemmeno vederlo. ⚠️ Non si asserisce 'OK': numerare ha altre
--    precondizioni (la prima e' «piano rate assente», da fn_assign_numero_fattura)
--    che non c'entrano con questo file. Si asserisce che il codice NON sia il
--    nostro — che e' la proprieta' che serve.
-- ============================================================
CREATE TEMP TABLE tmp_esito_2 AS
SELECT pg_temp.nnc_esito((SELECT fattura_id FROM tmp_padre)) AS esito;

SELECT isnt(
  (SELECT esito FROM tmp_esito_2),
  'E_FATTURA_RETTIFICATA_SENZA_NUMERO',
  '4) una fattura che non rettifica nulla non e'' toccata dalla guardia'
);

-- ============================================================
-- 5) ⭐ DATO UN NUMERO AL PADRE, LA GUARDIA SI SPEGNE.
--    Il numero si mette a mano: qui interessa che il padre RISULTI numerato,
--    non come ci sia arrivato — e passare dalla sua funzione vorrebbe dire
--    soddisfare precondizioni che non sono il soggetto di questo file.
--    ⚠️ Rev 2026-10-05: il numero si mette DENTRO UNA SOTTOTRANSAZIONE che si
--    annulla da sola (errore proprio PGT01), dopo aver salvato l'esito in una
--    variabile. Prima il test 6 lo TOGLIEVA con un UPDATE (numero = NULL) per
--    tornare al padre bloccante; dal 20261004-80
--    (vendite.trgfn_fatture_guard_numero_fiscale, Q-4 di
--    brief-db-esclusioni-implicite) una fattura numerata non cambia identita'
--    fiscale, e il file moriva li'. Il rollback non e' una modifica della
--    fattura: e' una numerazione che non e' mai avvenuta. E se la NC venisse
--    numerata qui dentro, torna indietro anche lei.
-- ============================================================
CREATE TEMP TABLE tmp_esito_3 (esito text);
DO $num$
DECLARE
  v_esito text;
BEGIN
  BEGIN
    UPDATE vendite.fatture
       SET numero = 999999, anno = 2026
     WHERE id = (SELECT fattura_id FROM tmp_padre);
    v_esito := pg_temp.nnc_esito((SELECT fattura_id FROM tmp_nc));
    RAISE EXCEPTION USING ERRCODE = 'PGT01';   -- annulla il numero del padre
  EXCEPTION WHEN SQLSTATE 'PGT01' THEN
    NULL;
  END;
  INSERT INTO tmp_esito_3 VALUES (v_esito);
END $num$;

SELECT isnt(
  (SELECT esito FROM tmp_esito_3),
  'E_FATTURA_RETTIFICATA_SENZA_NUMERO',
  '5) numerato il padre, la guardia non morde piu'''
);

-- ============================================================
-- 6) ⭐ IL BERSAGLIO — il rifiuto dice su quale documento, e su quale prima.
--    E' la ragione per cui il 20260823-03 esiste: fin qui il messaggio
--    nominava un id dentro la frase e l'operatore doveva ricopiarselo; adesso
--    accanto alla frase viaggia l'indicazione del documento, e il frontend ci
--    disegna un pulsante.
--
--    ⭐ DAL 2026-08-24 (T-3b) GLI ELEMENTI SONO DUE, e il primo e' la NOTA —
--    cioe' il documento che si sta cercando di numerare. Senza di lui il passo
--    T-3b non si sarebbe potuto fare: dentro un giro di lotto l'errore arriva
--    su una fattura fra molte, e tolti gli id dalla frase QUALE ha rifiutato
--    non lo direbbe piu' nessuno.
--
--    ⚠️ SI ASSERISCE LA STRINGA ESATTA, ordine compreso, e fino a ieri questo
--    file diceva il contrario («l'ordine non e' una proprieta' su cui valga la
--    pena legare un test»). E' cambiato il motivo: il canale compatto tiene i
--    PRIMI CINQUE elementi per ordinalita', quindi la testa dell'array e' cio'
--    che sopravvive al tetto. Che li' ci sia il documento da numerare non e'
--    piu' un dettaglio di resa, e' la garanzia che regge il messaggio.
--
--    ⚠️ Il padre e' di nuovo senza numero: il test 5 l'ha numerato dentro una
--    sottotransazione annullata. Il verbo, di nuovo, in un'istruzione
--    separata dall'asserzione.
-- ============================================================

CREATE TEMP TABLE tmp_bers_1 AS
SELECT pg_temp.nnc_bersaglio((SELECT fattura_id FROM tmp_nc)) AS bersaglio;

SELECT is(
  (SELECT bersaglio FROM tmp_bers_1),
  'FATTURA:' || (SELECT fattura_id FROM tmp_nc)::text
    || ',FATTURA:' || (SELECT fattura_id FROM tmp_padre)::text,
  '6) il bersaglio porta PRIMA il documento da numerare, POI il padre bloccante'
);

-- ============================================================
-- 7) ⭐ DUE BLOCCANTI, DUE BERSAGLI — ed e' il caso per cui la forma e'
--    un ARRAY e non un oggetto solo. Una nota puo' rettificare righe di
--    fatture DIVERSE, e ne basta una senza numero perche' il blocco fiscale
--    resti incompleto: l'operatore deve poterle raggiungere tutte.
--    ⚠️ La seconda riga della nota si scrive a mano perche' `nnc_mk_doc` ne
--    crea una sola: senza, l'asserzione passerebbe senza aver misurato niente.
-- ============================================================
CREATE TEMP TABLE tmp_padre2 AS
SELECT * FROM pg_temp.nnc_mk_doc((SELECT natura_fattura_id FROM tmp_refs_nnc), 7, 25);

INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione,
    uom_id, qta, prezzo_unitario, iva_id, imponibile_riga, riga_rettificata_id, competenza_dal, competenza_al)
SELECT (SELECT fattura_id FROM tmp_nc), 2, r.articolo_id, 'Seconda riga pgTAP NC',
       r.uom_id, -3, 25, r.iva_id, -75, (SELECT riga_id FROM tmp_padre2), script.fn_data_operativa(), script.fn_data_operativa()
  FROM tmp_refs_nnc r;

CREATE TEMP TABLE tmp_bers_2 AS
SELECT pg_temp.nnc_bersaglio((SELECT fattura_id FROM tmp_nc)) AS bersaglio;

-- ⚠️ Stringa esatta, per la ragione scritta al test 6: dal T-3b l'ordine e'
--    portante. La nota resta in TESTA anche se il suo id non e' il piu' basso
--    (tmp_padre e' stata creata prima di lei, tmp_padre2 dopo), quindi questa
--    asserzione distingue davvero «primo perche' e' il soggetto» da «primo
--    perche' e' il piu' piccolo» — che sarebbe stata una coincidenza.
SELECT is(
  (SELECT bersaglio FROM tmp_bers_2),
  'FATTURA:' || (SELECT fattura_id FROM tmp_nc)::text
    || ',FATTURA:' || (SELECT fattura_id FROM tmp_padre)::text
    || ',FATTURA:' || (SELECT fattura_id FROM tmp_padre2)::text,
  '7) due padri senza numero: tre bersagli, col documento da numerare in testa'
);

-- ============================================================
-- 8) ⭐ LA FRASE NON PORTA PIU' NESSUN ID — ed e' lo scopo del cantiere.
--    Fino al 2026-08-23 il messaggio 937 diceva «Non si puo' numerare il
--    documento 19563: la fattura che rettifica non e' ancora numerata
--    (documento 835)»: due chiavi interne dentro una frase scritta per una
--    persona, che per rimediare doveva ricopiarsele in un campo di ricerca.
--    Adesso la frase dice QUANTI documenti mancano, e DOVE andare lo dicono i
--    pulsanti costruiti sul bersaglio del test 7.
--
--    ⚠️ SI ASSERISCONO LE PROPRIETA', NON IL TESTO. Ripetere qui la frase del
--    catalogo vorrebbe dire scriverla due volte e rendere rosso il test a ogni
--    limatura della formulazione — che e' esattamente il debito descritto in
--    «i consumatori di un messaggio si cercano dal nome di chi lo solleva».
--    Le due proprieta' che contano sono: nessuno dei tre id compare nella
--    frase, e il conteggio dei bloccanti (qui 2) compare come numero a se'.
--
--    ⛔ E QUESTO TEST MISURA LA COPPIA changeSet+CSV. Se il catalogo e' ancora
--    quello vecchio (due segnaposto) e la funzione passa un valore solo,
--    format() fallisce, fn_log_and_raise_error ripiega sul template non
--    composto e scrive W_MESSAGGIO_ARITA: gli id non ci sono lo stesso — sono
--    dei `%s` — ma il conteggio non compare, e il test lo vede.
-- ============================================================
CREATE TEMP TABLE tmp_msg_1 AS
SELECT pg_temp.nnc_messaggio((SELECT fattura_id FROM tmp_nc)) AS messaggio;

SELECT is(
  (SELECT (position((SELECT fattura_id FROM tmp_nc)::text     IN m.messaggio) = 0
       AND position((SELECT fattura_id FROM tmp_padre)::text  IN m.messaggio) = 0
       AND position((SELECT fattura_id FROM tmp_padre2)::text IN m.messaggio) = 0
       AND m.messaggio ~ '(^|[^0-9])2([^0-9]|$)')::text
     FROM tmp_msg_1 m),
  'true',
  '8) la frase non nomina nessun id e dice quanti sono i documenti da numerare'
);

SELECT * FROM finish();
ROLLBACK;
