-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): CURATO — sceglieva dal DB un lotto pre-fiscale con fatture e uno con righe accreditate, e saltava 10 asserzioni su 14. Ora i due lotti si costruiscono: commessa (dbops.fn_pgtap_crea_commessa), lotto DRAFT (dbops.fn_pgtap_crea_lotto), fattura agganciata nel lotto (dbops.fn_pgtap_fattura_attivita con p_lotto_id), una corsa COMPLETATA dalle primitive della pipeline; per il 13 bolla, reso a credito e accredito (dbops.fn_pgtap_crea_ddt_da_ordine, fn_pgtap_crea_reso, vendite.fn_accredita_riga_reso). Gli skip del 4, 8 e 13 ritirati: a fixture costruita un'assenza e' un rosso. Il lotto resta DRAFT: a EMESSA la fattura della madre del lotto non arriva (indirizzi FATT, intestazione).
-- pgTAP test per Zero ERP
-- Test: ritorno di un lotto a DRAFT (piano-db-ritorno-lotto-a-draft.md, A4)
-- ------------------------------------------------------------
-- Cosa presidia questo file
--   Il disegno «EMESSA = documento non modificabile; per correggere si
--   riporta a DRAFT e si ricalcola», che fino al 2026-08-03 era dichiarato
--   a meta': la matrice ammetteva la transizione per il lotto, ma nessuna
--   funzione la eseguiva (rilievo C-18). Caso reale che l'ha aperto: la
--   fattura 2263 del lotto 1200, EMESSA e non numerata, con un piano rate
--   sbagliato e nessun modo di disfarla.
--
-- 🔴 IL TEST CHE VALE DI PIU' E' L'8.
--   Gli altri verificano che il ritorno abbia la FORMA giusta. L'8 verifica
--   che serva a QUALCOSA: `fn_cleanup_fatture_by_ids` ripristina
--   attivita_fatturabili ma non tocca MAI commesse_attivita, e
--   `fn_emit_attivita_fatturabili_da_commessa` filtra su
--   stato_emissione = 'EMESSA'. Un'attivita' lasciata li' non verrebbe
--   ripresa dal giro successivo: il lotto ripartirebbe senza niente da
--   riemettere. Lo stesso campo decide lo stadio nel cruscotto competenza,
--   che non guarda mai lo stato fiscale della fattura.
--
-- ⭐ FIXTURE COSTRUITA (rev 2026-10-25). Fino a oggi il file SCEGLIEVA un
--   lotto pre-fiscale reale e, se non c'era, saltava i test di comportamento:
--   su un database da zero (CI) e sullo scratch passava muto. Ora il lotto
--   pre-fiscale con la fattura, la riga e l'attivita' agganciate lo danno i
--   builder di dbops e le madri che chiamano. ⚠️ Il lotto e' DRAFT, non
--   EMESSA: la fattura in bozza della madre del lotto non e' emettibile senza
--   indirizzi e intestazione, che nessun builder scrive; il criterio del file
--   (DRAFT o EMESSA) lo ha sempre ammesso. I test 1-3 sono strutturali.
-- ------------------------------------------------------------
-- Indice test
-- 1) Seed: la transizione EMESSA -> DRAFT del LOTTO non ha vincolo di tipo
-- 2) La colonna riaperto_il esiste, e' timestamptz e nullable
-- 3) La funzione esiste e restituisce i SEI contatori
-- 4) Fixture: un lotto pre-fiscale con almeno una fattura
-- 5) Guard: con una fattura NUMERATA il ritorno e rifiutato
-- 6) Il ritorno gira e non solleva
-- 7) Dopo: lotto DRAFT, stato_operativo APERTO, riaperto_il valorizzato
-- 8) Le commesse_attivita sono tornate NON_EMESSA  <-- il test che vale
-- 9) Le fatture del lotto sono state cancellate
-- 10) I task_run sono chiusi ad ANNULLATO (il rilancio torna RUN, non SKIP)
-- 11) RD-7: l'atto e' scritto nel GIORNALE, e il payload DICE IL VERO
-- 12) RD-7: la riga si vede da vw_giornale_entita, e non SOTTO il suo effetto
-- 13) La porta rifiuta un lotto le cui righe sono gia' accreditate
-- 14) RD-7: il codice evento e' DICHIARATO a catalogo (strutturale)
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

SELECT plan(14);

-- ============================================================
-- Strutturali (girano sempre)
-- ============================================================

-- Il `meta` vuoto e' sostanza, non forma: trgfn_fatturazione_lotti_guard_stato
-- LEGGE quel meta e ne applica `tipo_lotto`. Finche' conteneva "MASSIVO" un
-- lotto GIORNALIERO non poteva tornare indietro, mentre il perimetro deciso
-- (D-L.2 / D-T) e' entrambi i tipi.
SELECT ok(
  EXISTS (
    SELECT 1 FROM config.stati_doc_fiscale_transizioni t
      JOIN config.stati_doc_fiscale sf ON sf.id = t.stato_from_id
      JOIN config.stati_doc_fiscale st ON st.id = t.stato_to_id
     WHERE sf.codice_interno = 'EMESSA' AND st.codice_interno = 'DRAFT'
       AND t.ammesso IS TRUE AND t.solo_lotto IS TRUE
       AND (t.meta->>'tipo_lotto') IS NULL),
  '1) Seed: EMESSA -> DRAFT esiste per il lotto, senza vincolo di tipo');

SELECT ok(
  EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'vendite' AND table_name = 'fatturazione_lotti'
       AND column_name = 'riaperto_il'
       AND data_type = 'timestamp with time zone'
       AND is_nullable = 'YES'),
  '2) La colonna riaperto_il esiste, e timestamptz e nullable');

-- Sei contatori e non quattro: `riemesse_attivita` e' separato perche' un
-- numero unico direbbe «10 cose fatte» senza distinguere fatture cancellate
-- da attivita' rimesse in coda, che per il cockpit sono fatti diversi; e
-- `annullati_task_run` perche' e' il passo RD-6, che senza un numero proprio
-- non si distingue da «non c'era niente da annullare».
-- ⚠️ rev 2026-08-31: l'etichetta diceva «cinque» ed era ferma alla firma
-- pre-20260803-12 — lo stesso refuso che la scheda manuale portava fino a
-- oggi (voce DB-R1). L'asserzione invece era gia' giusta: guarda due nomi
-- che ci sono, non il conteggio. Ora ne guarda tre, incluso il sesto.
SELECT ok(
  (SELECT count(*) FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite' AND p.proname = 'fn_riporta_lotto_a_draft'
      AND pg_get_function_result(p.oid) ILIKE '%riemesse_attivita%'
      AND pg_get_function_result(p.oid) ILIKE '%annullati_task_run%'
      AND pg_get_function_result(p.oid) ILIKE '%deleted_fatture%') = 1,
  '3) La funzione esiste e restituisce i sei contatori');

-- ============================================================
-- Fixture
-- ============================================================
-- Criterio di scelta: un lotto in DRAFT o EMESSA, con almeno una fattura e
-- NESSUNA fattura numerata. Il filtro sul numero e' lo stesso guard che il
-- test 5 esercita: cosi' la fixture non muore su una condizione che il file
-- verifica altrove.
-- ⭐ rev 2026-08-31: si fotografa anche lo STATO FISCALE di partenza. Serve al
--   test 11: e' il solo dato del payload che dopo l'UPDATE non sarebbe piu'
--   ricostruibile, quindi e' anche il solo che un'asserzione «dice il vero»
--   deve catturare prima.
-- ⭐ rev 2026-10-25 (giro D-4): il lotto si COSTRUISCE. Una commessa emittibile
--   con la sorgente ROOT (dbops.fn_pgtap_crea_commessa), il lotto DRAFT del suo
--   cliente (dbops.fn_pgtap_crea_lotto), la fattura in bozza nel lotto con la
--   riga, il lucchetto e l'aggancio (dbops.fn_pgtap_fattura_attivita), poi il
--   lotto a EMESSA per la matrice (dbops.fn_pgtap_porta_a_stato): il caso reale
--   che ha aperto il disegno. Una corsa COMPLETATA dalle primitive della
--   pipeline (fn_start_lotto_task_run / fn_complete_lotto_task_run): senza, il
--   10 sarebbe verde per sottrazione.
CREATE TEMP TABLE tmp_comm_rld AS
SELECT c.* FROM dbops.fn_pgtap_crea_commessa('riporta lotto', 'PRONTA_FATTURAZIONE',
                                             p_con_sorgente_root => true) c;

CREATE TEMP TABLE tmp_lotto_mk_rld AS
SELECT l.lotto_id, l.lock_batch_id
  FROM tmp_comm_rld c
  JOIN vendite.commesse_attivita ca ON ca.id = c.attivita_id,
       dbops.fn_pgtap_crea_lotto('riporta lotto', 'DRAFT', c.billing_account_id,
                                 ca.tipo_doc_fiscale_id, p_del_cliente => true) l;

CREATE TEMP TABLE tmp_fatt_rld AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('riporta lotto',
         ARRAY[(SELECT attivita_id FROM tmp_comm_rld)], (SELECT lotto_id FROM tmp_lotto_mk_rld));


CREATE TEMP TABLE tmp_run_mk_rld AS
SELECT r.task_run_id AS id
  FROM vendite.fn_start_lotto_task_run(
         p_lotto_id             => (SELECT lotto_id FROM tmp_lotto_mk_rld),
         p_pipeline_id          => (SELECT p.id FROM vendite.fatturazione_pipeline p ORDER BY p.id LIMIT 1),
         p_stato_doc_fiscale_id => (SELECT fl.stato_doc_fiscale_id FROM vendite.fatturazione_lotti fl
                                     WHERE fl.id = (SELECT lotto_id FROM tmp_lotto_mk_rld)),
         p_task_code            => 'pull_attivita_da_commessa') AS r;
SELECT vendite.fn_complete_lotto_task_run((SELECT id FROM tmp_run_mk_rld));

-- Il soggetto, con lo stesso criterio di prima: pre-fiscale, con fatture, e
-- riportabile per la funzione che il test collauda.
CREATE TEMP TABLE tmp_lotto_rld AS
SELECT fl.id,
       fl.lock_batch_id,
       s.codice_interno AS stato_prima,
       (SELECT count(*) FROM vendite.fatturazione_lotti_fatture lf WHERE lf.lotto_id = fl.id) AS n_fatture
  FROM vendite.fatturazione_lotti fl
  JOIN config.stati_doc_fiscale s ON s.id = fl.stato_doc_fiscale_id
 WHERE fl.id = (SELECT lotto_id FROM tmp_lotto_mk_rld)
   AND s.codice_interno IN ('DRAFT', 'EMESSA')
   AND EXISTS (SELECT 1 FROM vendite.fatturazione_lotti_fatture lf WHERE lf.lotto_id = fl.id)
   -- ⭐ rev 2026-08-22: la fixture NON ri-elenca i motivi ostativi, li CHIEDE
   --   alla stessa funzione che il test collauda.
   AND script.fn_check_lotto_riportabile_a_draft(fl.id) = '[]'::jsonb;

-- Le commesse_attivita che il ritorno dovra' rimettere in coda: si fotografano
-- ADESSO, perche' dopo la pulizia il legame (fattura_riga_id) non esiste piu'.
CREATE TEMP TABLE tmp_ca_rld AS
SELECT DISTINCT af.commessa_attivita_id AS id
  FROM vendite.attivita_fatturabili af
 WHERE af.commessa_attivita_id IS NOT NULL
   AND (
         af.lock_batch_id = (SELECT lock_batch_id FROM tmp_lotto_rld)
      OR af.fattura_riga_id IN (
             SELECT fr.id FROM vendite.fatture_righe fr
              WHERE fr.fattura_id IN (SELECT lf.fattura_id FROM vendite.fatturazione_lotti_fatture lf
                                       WHERE lf.lotto_id = (SELECT id FROM tmp_lotto_rld))
         )
       );

CREATE TEMP TABLE tmp_runs_rld AS
SELECT count(*) AS n
  FROM vendite.fatturazione_lotti_task_runs
 WHERE lotto_id = (SELECT id FROM tmp_lotto_rld);

-- ⛔ Niente skip: il lotto e' costruito, e un'assenza qui e' un rosso.
SELECT ok((SELECT n_fatture FROM tmp_lotto_rld) > 0,
          '4) Fixture: lotto pre-fiscale con almeno una fattura');

-- ============================================================
-- 5) Il guard sul numero
-- ============================================================
-- ⚠️ Il guard guarda il NUMERO, non lo stato. A EMESSA la fattura non e'
-- numerata (C-19), quindi il controllo di stato basterebbe: ma cancellare una
-- fattura gia' numerata aprirebbe un buco IRREVERSIBILE nella numerazione
-- fiscale, e un presidio che si fida di un'implicazione e' un presidio che
-- cade il giorno che l'implicazione cambia.
-- Il numero si mette DENTRO UNA SOTTOTRANSAZIONE che si annulla da sola: il
-- ritorno si tenta sul lotto con la fattura numerata, l'esito si salva in una
-- variabile, poi il blocco esce con un errore proprio (PGT01) e il numero — e
-- il ritorno, se per errore riuscisse — torna indietro. La fixture torna
-- com'era e i test successivi lavorano sul lotto intatto.
-- ⚠️ Rev 2026-10-05: prima il numero si TOGLIEVA con un UPDATE (numero =
--   NULL). Dal 20261004-80 (vendite.trgfn_fatture_guard_numero_fiscale, Q-4 di
--   brief-db-esclusioni-implicite) una fattura numerata non cambia identita'
--   fiscale, e il file moriva li'. Il rollback di una sottotransazione non e'
--   una modifica della fattura: e' una numerazione che non e' mai avvenuta.
CREATE TEMP TABLE tmp_rld_numerata (esito text);
DO $num$
DECLARE
  v_esito text;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM tmp_lotto_rld) THEN
    RETURN;
  END IF;
  BEGIN
    UPDATE vendite.fatture SET numero = 999999
     WHERE id = (SELECT lf.fattura_id FROM vendite.fatturazione_lotti_fatture lf
                  WHERE lf.lotto_id = (SELECT id FROM tmp_lotto_rld) ORDER BY lf.fattura_id LIMIT 1);
    BEGIN
      PERFORM * FROM vendite.fn_riporta_lotto_a_draft((SELECT id FROM tmp_lotto_rld));
      v_esito := 'NESSUN ERRORE';
    EXCEPTION WHEN OTHERS THEN
      v_esito := SQLSTATE;
    END;
    RAISE EXCEPTION USING ERRCODE = 'PGT01';   -- annulla il numero
  EXCEPTION WHEN SQLSTATE 'PGT01' THEN
    NULL;
  END;
  INSERT INTO tmp_rld_numerata VALUES (v_esito);
END $num$;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_lotto_rld) THEN NULL
  ELSE is(
         (SELECT esito FROM tmp_rld_numerata),
         'P0001',
         '5) Guard: con una fattura numerata il ritorno e rifiutato')
END;

-- ============================================================
-- 6-10) Il giro buono
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_lotto_rld) THEN NULL
  ELSE lives_ok(
         format($$ SELECT * FROM vendite.fn_riporta_lotto_a_draft(%s) $$, (SELECT id FROM tmp_lotto_rld)),
         '6) Il ritorno gira e non solleva')
END;

-- stato_operativo torna APERTO perche' il lotto ha di nuovo lavoro da fare, e
-- riaperto_il e' il marcatore che distingue «riaperto» da «rotto»: senza,
-- l'unico modo di far ripartire il lotto sarebbe marcarlo in ERRORE, cioe'
-- dire una bugia che il cruscotto mostrerebbe in rosso.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_lotto_rld) THEN NULL
  ELSE ok(
    (SELECT s.codice_interno FROM vendite.fatturazione_lotti fl
       JOIN config.stati_doc_fiscale s ON s.id = fl.stato_doc_fiscale_id
      WHERE fl.id = (SELECT id FROM tmp_lotto_rld)) = 'DRAFT'
    AND (SELECT stato_operativo FROM vendite.fatturazione_lotti
          WHERE id = (SELECT id FROM tmp_lotto_rld)) = 'APERTO'
    AND (SELECT riaperto_il FROM vendite.fatturazione_lotti
          WHERE id = (SELECT id FROM tmp_lotto_rld)) IS NOT NULL,
    '7) Dopo il ritorno: lotto DRAFT, stato_operativo APERTO, riaperto_il valorizzato')
END;

-- 🔴 Il test che vale. Si asserisce la COPERTURA — quante delle attivita'
-- coinvolte NON sono piu' EMESSA sul totale di quelle coinvolte — e non la
-- semplice esistenza di qualcuna a NON_EMESSA: un conteggio parziale
-- passerebbe anche se il ritorno ne dimenticasse meta'.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_lotto_rld) THEN NULL
  ELSE ok(
    (SELECT count(*) FROM vendite.commesse_attivita ca
      WHERE ca.id IN (SELECT id FROM tmp_ca_rld) AND ca.stato_emissione = 'EMESSA') = 0,
    '8) Le commesse_attivita coinvolte sono tutte uscite da EMESSA (tornano emittibili)')
END;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_lotto_rld) THEN NULL
  ELSE ok(
    (SELECT count(*) FROM vendite.fatturazione_lotti_fatture lf
      WHERE lf.lotto_id = (SELECT id FROM tmp_lotto_rld)) = 0,
    '9) Le fatture del lotto sono state cancellate (rollback, non riapertura)')
END;

-- 🔴 QUESTO TEST ERA SCRITTO AL CONTRARIO, e cristallizzava un bug.
-- Diceva «i task_runs non si toccano», sulla base di un'analisi sbagliata:
-- avevo verificato che `resume_mode` fosse letto da un metodo Python senza
-- chiamanti e ne avevo concluso che nessuno consultasse i task_run. Il
-- consumatore vero e' un altro — fn_resolve_lotto_task_execution_mode, che il
-- runner chiama a OGNI task: legge l'ultimo task_run e su COMPLETATO risponde
-- SKIP. Col test scritto cosi', il lotto riaperto rilanciava A VUOTO (tutti e
-- quattro i task saltati, nessun errore, nessun task_run nuovo) e il file
-- restava verde.
--
-- Ora si asserisce il fatto giusto, in DUE meta':
--   * nessuna corsa attiva resta COMPLETATO -> il resolver torna a dire RUN;
--   * il NUMERO di righe non cala -> la storia non si cancella, si chiude con
--     esito, e il giro nuovo aprira' tentativo = MAX+1.
-- ⚠️ Non si verifica `attivo`: quella colonna il resolver non la guarda
-- nemmeno, ed e' proprio il motivo per cui disattivare le righe non avrebbe
-- risolto niente.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_lotto_rld) THEN NULL
  ELSE ok(
    NOT EXISTS (SELECT 1 FROM vendite.fatturazione_lotti_task_runs
                 WHERE lotto_id = (SELECT id FROM tmp_lotto_rld)
                   AND attivo IS TRUE
                   AND task_stato = 'COMPLETATO')
    AND (SELECT count(*) FROM vendite.fatturazione_lotti_task_runs
          WHERE lotto_id = (SELECT id FROM tmp_lotto_rld)) >= (SELECT n FROM tmp_runs_rld),
    '10) I task_run del lotto sono chiusi ad ANNULLATO (il rilancio torna RUN, non SKIP) e la storia resta')
END;

-- ============================================================
-- 11-12) RD-7 — l'atto entra nel GIORNALE
-- ============================================================
-- ⚠️ Fino al 2026-08-31 la riapertura non scriveva in NESSUNO dei quattro
--   registri di script.vw_giornale_entita: nella scheda «Storia» si leggeva
--   solo DI RIMBALZO, dai task_run passati ad ANNULLATO (il test 10). Cioe'
--   l'unico atto della funzione che CANCELLA documenti era anche l'unico
--   senza una riga propria.
--
-- ⭐ E SI ASSERISCE CHE LA RIGA DICA IL VERO, non che esista.
--   Una riga di giornale presente ma con contatori sbagliati e' peggio della
--   sua assenza: chi indaga si fida di un numero inventato. Quindi il payload
--   si confronta con i fatti fotografati PRIMA (n_fatture, stato_prima), non
--   con se stesso.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_lotto_rld) THEN NULL
  ELSE ok(
    EXISTS (
      SELECT 1 FROM vendite.event_log e
       WHERE e.entity_type = 'LOTTO'
         AND e.entity_id   = (SELECT id FROM tmp_lotto_rld)
         AND e.event_code  = 'LOTTO_RIAPERTO'
         AND e.severity    = 'WARN'
         AND (e.payload ->> 'stato_precedente')    = (SELECT stato_prima FROM tmp_lotto_rld)
         AND (e.payload ->> 'deleted_fatture')::int = (SELECT n_fatture  FROM tmp_lotto_rld)
         AND (e.payload ? 'annullati_task_run')
         AND (e.payload ? 'riemesse_attivita')
         AND e.emittente_soggetto_ruolo_id IS NOT NULL),
    '11) RD-7: la riapertura e scritta nel giornale, WARN, e il payload dice il vero')
END;

-- ⭐ IL PUNTO DELLA VOCE NON E' LA TABELLA, E' LA SCHEDA «STORIA»:
--   la riga deve arrivare fino a script.vw_giornale_entita, che e' cio' che
--   una persona guarda. Una riga scritta in event_log ma invisibile li'
--   avrebbe risolto la voce solo sulla carta.
--
-- ⚠️ E si verifica anche la GRAVITA' RELATIVA, che e' l'argomento del WARN:
--   la vista mappa gia' TASK_RUN 'ANNULLATO' -> 'WARN'. Se la causa fosse
--   INFO, chi filtra per gravita' vedrebbe l'effetto (otto corse annullate)
--   senza il motivo — la riapertura sparirebbe proprio dal filtro che serve a
--   capire perche' quelle corse sono state annullate.
--   Si asserisce quindi che la riapertura NON stia sotto il suo stesso
--   effetto, non che sia «WARN» in astratto: se un domani la vista rimappasse
--   gli ANNULLATO, questa asserzione resta quella giusta.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_lotto_rld) THEN NULL
  ELSE ok(
    EXISTS (
      SELECT 1 FROM script.vw_giornale_entita g
       WHERE g.registro    = 'EVENT_LOG'
         AND g.entity_type = 'LOTTO'
         AND g.entity_id   = (SELECT id FROM tmp_lotto_rld)
         AND g.cosa        = 'LOTTO_RIAPERTO')
    AND NOT EXISTS (
      -- nessun task_run ANNULLATO dello stesso lotto risulta piu' grave
      -- della riapertura che li ha prodotti
      SELECT 1
        FROM script.vw_giornale_entita eff
        JOIN script.vw_giornale_entita causa
          ON causa.entity_id = eff.entity_id
         AND causa.registro  = 'EVENT_LOG'
         AND causa.cosa      = 'LOTTO_RIAPERTO'
       WHERE eff.entity_type = 'LOTTO'
         AND eff.entity_id   = (SELECT id FROM tmp_lotto_rld)
         AND eff.registro    = 'TASK_RUN'
         AND eff.cosa LIKE '%ANNULLATO%'
         AND eff.gravita = 'WARN' AND causa.gravita = 'INFO'),
    '12) RD-7: la riapertura si vede nel giornale, e non sotto il suo stesso effetto')
END;


-- ============================================================
-- 13) La porta rifiuta un lotto le cui righe sono gia' accreditate
-- ============================================================
-- ⚠️ E' il motivo 4, nato il 2026-08-22 dopo un 23503 grezzo dentro
--   fn_cleanup_fatture_by_ids. Il gemello sulle fatture NUMERATE non lo
--   copriva: l'accredito si registra PRIMA della numerazione, perche' e'
--   ancorato alla coda dei resi e non al numero.
-- ⭐ rev 2026-08-24 — QUESTA FIXTURE AVEVA LO STESSO DIFETTO CHE IL 22/08 ERA
--   GIA' STATO CORRETTO SUL SOGGETTO PRINCIPALE, e in due modi.
--
--   🔴 PRIMO, ed e' quello che l'ha resa rossa. `fn_riporta_lotto_a_draft`
--   solleva il codice del PRIMO motivo (`v_motivi -> 0 ->> 'codice'`), e i
--   motivi sono ordinati: lo STATO viene prima delle rettifiche. La fixture
--   prendeva «l'ultimo lotto con righe accreditate» senza guardare in che
--   stato fosse: il 2026-08-24 il piu' recente e' diventato uno in DEFINITIVA,
--   la funzione ha risposto — correttamente — «il ritorno in bozza e' ammesso
--   solo su un lotto in bozza o emesso», e il test e' diventato rosso
--   accusando il codice invece della propria selezione.
--   ⚠️ Non era un errore di ORDER BY mancante: l'ORDER BY c'era. Mancava la
--   condizione che rende il caso SIGNIFICATIVO — cioe' che il motivo sotto
--   esame sia quello che la funzione solleva davvero.
--
--   ⛔ SECONDO, e non si era ancora manifestato: la fixture ri-elencava a mano
--   UNA delle quattro sorgenti che `script.fn_check_fatture_con_rettifiche`
--   guarda (`commesse_attivita`), ignorando `attivita_fatturabili`,
--   `resi_righe_accrediti` e l'auto-riferimento fra righe di fattura. Cercava
--   quindi meno soggetti di quanti ne esistano, e su un database dove
--   l'accredito fosse arrivato per una delle altre tre strade avrebbe
--   saltato il test dichiarando «caso non riproducibile».
--
--   ➡️ Si CHIEDE alla stessa funzione, come gia' fa la fixture principale:
--   «qual e' il primo motivo?». Cosi' un motivo nuovo che passasse davanti
--   non rompe piu' il test — al massimo lo fa saltare, dichiarandolo.
--
-- ⚠️ E si asserisce il CODICE DI DOMINIO, non la frase. Prima qui c'era un
--   `throws_like` sul testo del messaggio: e' il canale sbagliato su cui
--   legarsi, e il 2026-08-24 se n'e' avuta la prova nello stesso giorno — il
--   messaggio 937 e' stato riscritto per togliere gli id dalla prosa (passo
--   T-3b). Un messaggio si riscrive quando serve; un codice registrato a
--   catalogo no. Il codice si legge dal canale CONSTRAINT dell'eccezione, che
--   e' il contratto di `script.fn_log_and_raise_error`.
--   ⭐ E risponde alla stessa domanda per cui il `throws_like` era stato
--   scelto contro `throws_ok('P0001')`: non «e' un errore di dominio» ma
--   QUALE — `E_LOTTO_NON_RIPORTABILE_A_DRAFT` e `E_FATTURE_RIGHE_RETTIFICATE`
--   sono due codici diversi, mentre erano lo stesso SQLSTATE.
-- ⭐ rev 2026-10-25 (giro D-4): il soggetto si COSTRUISCE. Una bolla consegnata
--   (dbops.fn_pgtap_crea_ddt_da_ordine), l'attivita' sulla sua riga (sorgente
--   DDT_VENDITA) fatturata nel lotto DRAFT del cliente
--   (dbops.fn_pgtap_fattura_attivita con p_lotto_id), un reso a credito
--   confermato (dbops.fn_pgtap_crea_reso) e l'accredito col verbo vero
--   (vendite.fn_accredita_riga_reso): la riga di fattura e' RETTIFICATA.
CREATE TEMP TABLE tmp_ddt_rett_rld AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('riporta lotto rettificato', 'CONSEGNATO');

CREATE TEMP TABLE tmp_comm_rett_rld AS
SELECT c.* FROM dbops.fn_pgtap_crea_commessa('riporta lotto rettificato', NULL,
                  (SELECT billing_account_id FROM tmp_ddt_rett_rld), p_con_sorgente_root => true) c;

CREATE TEMP TABLE tmp_att_rett_rld AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM tmp_comm_rett_rld), 25,
         (SELECT articolo_id FROM tmp_ddt_rett_rld),
         p_sorgente_codice  => 'DDT_VENDITA',
         p_sorgente_chiave  => (SELECT ddt_uid FROM tmp_ddt_rett_rld)::text,
         p_sorgente_riga_id => (SELECT ddt_riga_id FROM tmp_ddt_rett_rld),
         p_quantita         => 10);

CREATE TEMP TABLE tmp_lotto_mk_rett_rld AS
SELECT l.lotto_id
  FROM tmp_comm_rett_rld c, tmp_att_rett_rld a
  JOIN vendite.commesse_attivita ca ON ca.id = a.attivita_id,
       dbops.fn_pgtap_crea_lotto('riporta lotto rettificato', 'DRAFT', c.billing_account_id,
                                 ca.tipo_doc_fiscale_id, p_del_cliente => true) l;

CREATE TEMP TABLE tmp_fatt_rett_rld AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('riporta lotto rettificato',
         ARRAY[(SELECT attivita_id FROM tmp_att_rett_rld)], (SELECT lotto_id FROM tmp_lotto_mk_rett_rld));

CREATE TEMP TABLE tmp_reso_rett_rld AS
SELECT * FROM dbops.fn_pgtap_crea_reso('riporta lotto rettificato', (SELECT ddt_id FROM tmp_ddt_rett_rld), 4,
         'RESO_A_CREDITO', p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_ddt_rett_rld));

CREATE TEMP TABLE tmp_acc_rett_rld AS
SELECT * FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_reso_rett_rld));

-- Il soggetto, col criterio di prima: il PRIMO motivo ostativo e' l'accredito.
CREATE TEMP TABLE tmp_lotto_rett_rld AS
SELECT fl.id
  FROM vendite.fatturazione_lotti fl
 WHERE fl.id = (SELECT lotto_id FROM tmp_lotto_mk_rett_rld)
   AND script.fn_check_lotto_riportabile_a_draft(fl.id) -> 0 ->> 'reason'
       = 'RIGHE_RETTIFICATE';

-- Il verbo in una funzione a parte, che restituisce il CODICE: cosi'
-- l'asserzione confronta due stringhe e non dipende da come e' scritta la
-- frase per l'operatore.
CREATE OR REPLACE FUNCTION pg_temp.rld_codice(p_lotto_id bigint)
RETURNS text AS $$
DECLARE v_cod text;
BEGIN
  PERFORM vendite.fn_riporta_lotto_a_draft(p_lotto_id);
  RETURN 'NESSUN ERRORE';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_cod = CONSTRAINT_NAME;
  RETURN COALESCE(NULLIF(v_cod, ''), 'SQLSTATE:' || SQLSTATE);
END $$ LANGUAGE plpgsql;

-- ⛔ Niente skip: il lotto e' costruito, e un'assenza qui e' un rosso.
SELECT is(
         pg_temp.rld_codice((SELECT id FROM tmp_lotto_rett_rld)),
         'E_FATTURE_RIGHE_RETTIFICATE',
         '13) un lotto con righe gia accreditate viene rifiutato, e col codice giusto');


-- ============================================================
-- 14) Il codice evento e' DICHIARATO a catalogo (strutturale, gira sempre)
-- ============================================================
-- ⛔ QUESTO TEST ESISTE PERCHE' IL RUBINETTO CI NON COPRE QUESTO CODICE, ed
--   e' l'unico punto del file che parla di un presidio invece che di dominio.
--
--   `backend/apps/core/tests/test_event_codes_declared_guardrail.py` e' il
--   rubinetto dei codici evento: fa fallire la build se un `event_code` viene
--   scritto senza essere dichiarato in config.eventi_dominio. Ma cerca i punti
--   di scrittura nel **Python**, e la sua stessa intestazione spiega perche':
--   «il codice evento lo scrive il BACKEND», e una vista su `pg_proc`
--   tornerebbe «vuota per sempre».
--
--   ⚠️ Quella premessa e' scaduta il 2026-08-31: `LOTTO_RIAPERTO` e' il PRIMO
--   codice evento scritto dal DATABASE. Sul rubinetto Python e' invisibile —
--   non e' un difetto del rubinetto, e' che guarda un'altra sorgente — quindi
--   il verso «dichiarato obsoleto, ma ancora scritto» qui non lo presidia
--   nessuno. La spia dei dati (dbops.vw_eventi_non_dichiarati) se ne
--   accorgerebbe solo DOPO che una riga sbagliata e' finita nel registro.
--
--   ⭐ Si copre qui, dove il codice e' scritto: e si asserisce anche il verso
--   dell'obsolescenza, non la sola presenza. Un codice deprecato a catalogo e
--   ancora emesso da questa funzione e' esattamente il caso che nessun altro
--   cancello vedrebbe.
SELECT ok(
  EXISTS (
    SELECT 1 FROM config.eventi_dominio ed
     WHERE ed.codice = 'LOTTO_RIAPERTO'
       AND (ed.obsoleto_dal IS NULL OR ed.obsoleto_dal > script.fn_data_operativa()))
  AND EXISTS (
    -- e il tipo di entita' su cui la funzione lo scrive dev'essere
    -- GIORNALABILE: un modo di risoluzione a NULL fa rifiutare la riga dal
    -- trigger di scope, cioe' la riapertura fallirebbe invece di registrarsi.
    SELECT 1 FROM config.tipi_entita te
     WHERE te.codice = 'LOTTO'
       AND te.modo_risoluzione_emittente IS NOT NULL
       AND (te.obsoleto_dal IS NULL OR te.obsoleto_dal > script.fn_data_operativa())),
  '14) RD-7: LOTTO_RIAPERTO e dichiarato e non obsoleto, e LOTTO e giornalabile');

SELECT * FROM finish();

ROLLBACK;
