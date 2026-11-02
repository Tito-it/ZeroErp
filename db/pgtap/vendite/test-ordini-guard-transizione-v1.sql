-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-26 (brief-modello-documento-vendita §14, giro 10):
--   la commessa del caso 7 nasce APERTA con l'attivita' del builder (p_con_attivita
--   => true, prima false): BOZZA -> APERTA e' spenta, APERTA si raggiunge solo da
--   PRONTA_FATTURAZIONE («riapri»), e PRONTA_FATTURAZIONE vuole una riga APPROVATA
--   e non emessa. La riga del builder ha la sua sorgente, non l'ordine: il guard
--   del caso 7 lo ferma ancora e solo la riga EMESSA scritta sotto. Attese invariate.
-- rev 2026-10-25 (brief-modello-documento-vendita §9): l'ordine ha la porta sulla colonna di
--   stato. Le transizioni provate passano dal verbo vendite.fn_cambia_stato_ordine (con
--   emetti_ordine concessa all'operatore costruito), che arriva al guard di transizione:
--   prima erano UPDATE diretti, ora fermati dalla porta (E_DOC_STATO_SOLO_DAL_VERBO). Stessi
--   esiti attesi; i throws_ok dei casi 3, 5, 7 passavano anche sulla porta, per questo
--   passano dal verbo e non restano UPDATE.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): gli ordini A, C, D (DRAFT) ed E, F
--   (CONFERMATO) da dbops.fn_pgtap_crea_ordine_con_righe (3 x 10, data 2026-06-15); lo slot B,
--   senza righe, da dbops.fn_pgtap_crea_ordine. Restano a mano le transizioni provate, la
--   sorgente della commessa e la riga EMESSA del caso 7.
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in bozza e si
--   portano avanti con dbops.fn_pgtap_porta_a_stato (prima nascevano gia' CONFERMATO
--   l'ordine F e APERTA la commessa).
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): la commessa del caso 7 la apre
--   dbops.fn_pgtap_crea_commessa sul cliente dell'ordine, in APERTA, senza la riga del
--   builder (p_con_attivita => false: e' la riga EMESSA del test che ferma il guard);
--   prima testata scritta a mano e passaggio di stato a parte. L'unita' di misura della
--   riga EMESSA e' quella dell'articolo costruito, non «la prima per id».
-- rev 2026-10-24 (brief-modello-documento-vendita Q-4): il mondo si costruisce intero —
--   azienda e operatore da dbops.fn_pgtap_crea_emittente_operatore (contesto aperto su di
--   lui), il cliente legato a quell'azienda (terzo argomento di fn_pgtap_crea_cliente_ba);
--   gli ordini portano l'emittente costruito. Prima emittente e soggetto_ruolo erano «i
--   primi per id» del database (non usati, ma pescati); valuta e IVA si leggono per codice.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2d/2e): chiavi del push e ambito degli indirizzi col codice della sorgente.
-- pgTAP test per Zero ERP
-- Test: vendite.trgfn_ordini_guard_transizione (+ trigger)
-- ------------------------------------------------------------
-- Brief: brief-ordini-azioni-data-driven.md
-- Enforcement DB-first del grafo transizioni stato ordine letto da
-- config.transizioni_stati_ordini.
-- Indice test (1..6):
-- 1) trg_ordini_a10_guard_transizione_upd esiste
-- 2) DRAFT->CONFERMATO con riga -> ok (lives)
-- 3) DRAFT->CONFERMATO senza righe -> throws E_ORDINE_CONFERMA_SENZA_RIGHE
-- 4) DRAFT->ANNULLATO -> ok (transizione manuale attiva)
-- 5) DRAFT->SPEDITO (fuori matrice) -> throws E_ORDINE_TRANSIZIONE_NON_AMMESSA
-- 6) CONFERMATO->ANNULLATO senza figli a valle -> ok (lives)
-- 7) CONFERMATO->ANNULLATO con righe di commessa gia' EMESSA -> throws
-- 8) ...e il CODICE di dominio esce nel campo strutturato CONSTRAINT
--
-- ⛔ rev 2026-08-26 — LA REGOLA E' CAMBIATA, e i test 7-8 con lei.
--   Fino a oggi bastava che l'ordine AVESSE SPINTO in commessa perche'
--   l'annullamento fosse rifiutato (E_ORD_ANNULLA_IN_COMMESSA). Quel divieto
--   e' stato RITIRATO (cantiere «il lavoro che non torna indietro», Q-9): il
--   motivo per cui esisteva era che non c'era modo di disfare il push, e
--   adesso c'e' — alla chiusura il documento ritira da se' le righe che
--   nessuno ha ancora emesso.
--   ⭐ Resta un freno solo, e su una condizione VERA: le righe gia' EMESSA
--   sono in volo verso una fattura (E_SORGENTE_CON_RIGHE_EMESSE), e hanno una
--   via d'uscita che il messaggio nomina («Riporta da emettere»).
--   ⚠️ Quindi la fixture non basta piu' che colleghi l'ordine a una commessa:
--   deve produrre una riga di commessa EMESSA, che e' la cosa che ferma.
--    (gruppo C: il codice arriva da `v_motivi -> 0 ->> 'codice'`, non da un
--     letterale — vedi brief-db-codice-errore-strutturato §2)
--
-- rev 2026-08-04: il caso 6 fissava la transizione come DISATTIVA
-- (attivo=false) e si aspettava E_ORDINE_TRANSIZIONE_NON_AMMESSA. Quella
-- disattivazione lasciava un ordine confermato senza NESSUNA via d'uscita
-- azionabile da una persona: decisione di Tid, si riattiva con tutti i
-- controlli che devono impedirla. Il test segue la decisione nuova e diventa
-- piu' forte: non basta che l'annullamento sia ammesso, deve essere ammesso
-- SOLO quando non c'e' gia' qualcosa a valle.
-- Brief: brief-db-vie-uscita-operatore.md
-- ------------------------------------------------------------

-- Nota emittente: gli ordini nascono dai builder sul billing account del cliente
--   costruito, legato all'azienda dell'operatore: l'emittente e' quello del BA.
-- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-1): fino a questo giorno gli
--   ordini nascevano con billing_account_id=NULL per saltare il guard di
--   coerenza emittente <-> BA. L'ordine senza BA non esiste piu': il cliente si
--   FABBRICA (tmp_gt_cli), col BA legato dal trigger z90 all'emittente
--   dell'operatore. Le transizioni di stato testate non dipendono dal BA.

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

SELECT plan(8);

-- Contesto non-API: GUC vuota.
-- ⛔ 2026-09-04 — QUI IL TEST SPEGNEVA IL GUARD, e adesso non piu'.
--   La riga rimossa era `set_config('app.current_user_id', '', true)`: senza
--   utente in sessione `script.trgfn_guard_emittente_scope` usciva subito con
--   RETURN NEW, e le fixture entravano senza che nessuno guardasse l'emittente.
--   La fase 6 di `brief-db-processi-automatici-identita-e-perimetro` chiude quel
--   ramo — una sessione applicativa senza utente non scrive piu'.
--   ⇒ Il contesto operatore del preambolo RESTA valido per tutto il file, e le
--     fixture prendono l'emittente su cui quell'operatore puo' davvero scrivere
--     (`script.fn_pgtap_emittente_operatore()`).
--   ⭐ Non e' una riparazione di comodo: prima questo file collaudava il
--     comportamento di una porta aperta, adesso attraversa il guard come lo
--     attraversa l'applicazione.

-- ============================================================
-- Riferimenti minimi
-- ============================================================
-- ⭐ rev 2026-10-24 (Q-4): l'azienda e il suo operatore si COSTRUISCONO, e il
--   contesto si riapre su di lui: gli ordini nascono sotto il guard di perimetro
--   come nell'applicazione, sull'emittente costruito.
CREATE TEMP TABLE tmp_gt_az AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_gt_az)); END $ctx$;
-- rev 2026-10-25 (§9): la conferma e l'annullo del confermato chiedono emetti_ordine.
SELECT dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM tmp_gt_az), 'emetti_ordine');

CREATE TEMP TABLE tmp_refs_gt AS
SELECT
-- 🔴 rev 2026-10-13 (brief-db-articoli-ammessi-per-documento D-1/D-2): l'articolo si
--   COSTRUISCE. Prima si pescava dal catalogo (il primo per id, o il piu' recente):
--   il primo per id e' l'onere del seed ONERE_SENZA_CONTRATTO (natura servizio), e
--   da 20261013-42 ordine e bolla portano solo merce. Un articolo costruito ha solo
--   le proprieta' che il test gli da' (merce, non gestito a magazzino).
  dbops.fn_pgtap_crea_articolo('PGT-OGT-ART', false) AS articolo_id,
  (SELECT v.id FROM config.valute v WHERE v.codice = 'EUR') AS valuta_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'CONFERMATO') AS stato_conf_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'ANNULLATO') AS stato_ann_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'SPEDITO') AS stato_sped_id;

CREATE TEMP TABLE tmp_gt_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('guard transizione ordini', NULL,
                                             (SELECT soggetto_ruolo_id FROM tmp_gt_az));
SET CONSTRAINTS ALL IMMEDIATE;

-- Gli slot: ordini del cliente costruito, 3 x 10 sull'articolo costruito. La riga
--   porta l'aliquota (la mette il builder): l'ingresso in CONFERMATO rifiuta un
--   prezzo senza aliquota (E_ORDINE_RIGA_IVA_MANCANTE).
-- Slot A: DRAFT con riga (test 2)
CREATE TEMP TABLE tmp_gt_a AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('guard transizione A', 'DRAFT',
    p_billing_account_id => (SELECT billing_account_id FROM tmp_gt_cli),
    p_quantita => 3, p_prezzo => 10, p_articolo_id => (SELECT articolo_id FROM tmp_refs_gt),
    p_data_ordine => DATE '2026-06-15');

-- Slot B: DRAFT senza righe (test 3): la testata sola.
CREATE TEMP TABLE tmp_gt_b AS
SELECT * FROM dbops.fn_pgtap_crea_ordine('guard transizione B', 'DRAFT',
    (SELECT billing_account_id FROM tmp_gt_cli), DATE '2026-06-15');

-- Slot C: DRAFT con riga (test 4 annulla)
CREATE TEMP TABLE tmp_gt_c AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('guard transizione C', 'DRAFT',
    p_billing_account_id => (SELECT billing_account_id FROM tmp_gt_cli),
    p_quantita => 3, p_prezzo => 10, p_articolo_id => (SELECT articolo_id FROM tmp_refs_gt),
    p_data_ordine => DATE '2026-06-15');

-- Slot D: DRAFT con riga (test 5 transizione fuori matrice)
CREATE TEMP TABLE tmp_gt_d AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('guard transizione D', 'DRAFT',
    p_billing_account_id => (SELECT billing_account_id FROM tmp_gt_cli),
    p_quantita => 3, p_prezzo => 10, p_articolo_id => (SELECT articolo_id FROM tmp_refs_gt),
    p_data_ordine => DATE '2026-06-15');

-- Slot E: CONFERMATO con riga (test 6 CONFERMATO->ANNULLATO senza figli a valle)
CREATE TEMP TABLE tmp_gt_e AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('guard transizione E', 'CONFERMATO',
    p_billing_account_id => (SELECT billing_account_id FROM tmp_gt_cli),
    p_quantita => 3, p_prezzo => 10, p_articolo_id => (SELECT articolo_id FROM tmp_refs_gt),
    p_data_ordine => DATE '2026-06-15');

-- ============================================================
-- 1) trigger esiste
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger
     WHERE tgname = 'trg_ordini_a10_guard_transizione_upd'
       AND NOT tgisinternal
  ),
  '1) trg_ordini_a10_guard_transizione_upd esiste'
);

-- ============================================================
-- 2) DRAFT->CONFERMATO con riga -> ok
-- ============================================================
SELECT lives_ok(
  format($q$SELECT * FROM vendite.fn_cambia_stato_ordine(%s, 'CONFERMATO')$q$,
         (SELECT ordine_id FROM tmp_gt_a)),
  '2) DRAFT->CONFERMATO con riga -> ok'
);

-- ============================================================
-- 3) DRAFT->CONFERMATO senza righe -> throws E_ORDINE_CONFERMA_SENZA_RIGHE
-- ============================================================
SELECT throws_ok(
  format($q$SELECT * FROM vendite.fn_cambia_stato_ordine(%s, 'CONFERMATO')$q$,
         (SELECT ordine_id FROM tmp_gt_b)),
  'P0001', NULL,
  '3) DRAFT->CONFERMATO senza righe -> throws E_ORDINE_CONFERMA_SENZA_RIGHE'
);

-- ============================================================
-- 4) DRAFT->ANNULLATO -> ok
-- ============================================================
SELECT lives_ok(
  format($q$SELECT * FROM vendite.fn_cambia_stato_ordine(%s, 'ANNULLATO')$q$,
         (SELECT ordine_id FROM tmp_gt_c)),
  '4) DRAFT->ANNULLATO -> ok (transizione manuale attiva)'
);

-- ============================================================
-- 5) DRAFT->SPEDITO (fuori matrice) -> throws E_ORDINE_TRANSIZIONE_NON_AMMESSA
-- ============================================================
SELECT throws_ok(
  format($q$SELECT * FROM vendite.fn_cambia_stato_ordine(%s, 'SPEDITO')$q$,
         (SELECT ordine_id FROM tmp_gt_d)),
  'P0001', NULL,
  '5) DRAFT->SPEDITO (fuori matrice) -> throws E_ORDINE_TRANSIZIONE_NON_AMMESSA'
);

-- ============================================================
-- 6) CONFERMATO->ANNULLATO senza figli a valle -> ok
--    L'ordine di fixture non ha DDT ne' commesse collegate:
--    script.fn_check_ordine_annullabile ritorna [] e il guard lascia passare.
-- ============================================================
SELECT lives_ok(
  format($q$SELECT * FROM vendite.fn_cambia_stato_ordine(%s, 'ANNULLATO')$q$,
         (SELECT ordine_id FROM tmp_gt_e)),
  '6) CONFERMATO->ANNULLATO senza figli a valle -> ammesso'
);

-- ============================================================
-- 7) CONFERMATO->ANNULLATO con righe di commessa gia' EMESSA -> throws
--    Un secondo ordine confermato, agganciato a una commessa E con una riga
--    gia' emessa: il guard legge la stessa funzione pura del bottone e rifiuta.
--    ⚠️ Il solo collegamento alla commessa NON basta piu' (Q-9): quello che
--    ferma e' il lavoro in volo, non il fatto di aver spinto.
-- ============================================================
-- Il secondo ordine confermato, come lo slot E.
CREATE TEMP TABLE tmp_gt_f AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('guard transizione F', 'CONFERMATO',
    p_billing_account_id => (SELECT billing_account_id FROM tmp_gt_cli),
    p_quantita => 3, p_prezzo => 10, p_articolo_id => (SELECT articolo_id FROM tmp_refs_gt),
    p_data_ordine => DATE '2026-06-15');

-- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-1): la commessa e' quella del
--   cliente dell'ordine, con l'emittente dell'ordine. Prima si copiava dalla
--   prima commessa del database (un altro cliente, magari un altro emittente):
--   passava solo perche' l'ordine non aveva BA, e il guard «una commessa, un
--   emittente» non aveva niente da confrontare.
-- rev 2026-10-24 (Q-2): la testata dal builder, sul billing account dell'ordine,
--   portata ad APERTA per la matrice. ⚠️ p_con_attivita => true (giro 10): APERTA
--   passa da PRONTA_FATTURAZIONE, che vuole una riga APPROVATA e non emessa;
--   la riga che conta per il guard resta quella EMESSA scritta sotto (la riga
--   del builder non nasce dall'ordine).
CREATE TEMP TABLE tmp_gt_com AS
SELECT * FROM dbops.fn_pgtap_crea_commessa(
    'guard transizione ordini', 'APERTA',
    (SELECT billing_account_id FROM tmp_gt_cli), true);

INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
SELECT (SELECT commessa_id FROM tmp_gt_com),
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA'),
       (SELECT ordine_id FROM tmp_gt_f)::text,
       'ROOT';

-- ⛔ E la riga che davvero FERMA: una commessa_attivita gia' EMESSA spinta da
--    questo ordine. Senza, dal 2026-08-26 l'annullamento passerebbe — ed e'
--    voluto, perche' il documento ritira da se' cio' che nessuno ha emesso.
-- ⚠️ La chiave e' l'`uid` dell'ordine, non il suo `id`: e' quella che
--    fn_list_ordini_da_pushare scrive in commesse_attivita.sorgente_uid.
--    ⭐ E NON e' la stessa che commesse_sorgenti usa qui sopra (li' e' l'id):
--    due chiavi polimorfe diverse per la stessa sorgente, e confonderle non
--    darebbe un errore — darebbe un guard che non ferma.
INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
  uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
  valuta_id, prezzo_snapshot, pricing_mode,
  stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
SELECT (SELECT commessa_id FROM tmp_gt_com),
       'ORDINE_VENDITA:PGTAP-GT:R:1',
       r.articolo_id,
       -- ⚠️ vendite.commesse non ha istanza_utility_id: si risolve dal
       --    billing account della commessa, che e' dove vive.
       (SELECT b.istanza_utility_id FROM vendite.commesse c
          JOIN anagrafiche.billing_account b ON b.id = c.billing_account_id
         WHERE c.id = (SELECT commessa_id FROM tmp_gt_com)),
       DATE '2026-06-15',
       (SELECT a.uom_id FROM catalogo.articoli a WHERE a.id = r.articolo_id),
       1,
       DATE '2026-06-01', DATE '2026-06-01', DATE '2026-06-30',
       r.valuta_id, 10.000000, 'FIXED',
       'BOZZA', 'EMESSA',
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA'),
       (SELECT o.uid::text FROM vendite.ordini o WHERE o.id = (SELECT ordine_id FROM tmp_gt_f))
  FROM tmp_refs_gt r;

SELECT throws_ok(
  format($q$SELECT * FROM vendite.fn_cambia_stato_ordine(%s, 'ANNULLATO')$q$,
         (SELECT ordine_id FROM tmp_gt_f)),
  'P0001', NULL,
  '7) CONFERMATO->ANNULLATO con righe di commessa gia'' EMESSA -> rifiutato dal guard'
);

-- ============================================================
-- 8) Il codice di dominio esce nel campo strutturato CONSTRAINT
--    Migration 20260805-05 · brief-db-codice-errore-strutturato §6
--
--    ⚠️ PERCHE' QUI E NON SOLO SULL'HELPER. Questo e' uno dei nove call site
--    del "gruppo C": il codice non e' un letterale nella chiamata, arriva da
--    `v_motivi -> 0 ->> 'codice'`. Ed e' esattamente il caso che il vecchio
--    meccanismo NON copriva: il backend pescava il codice con una regex dal
--    testo dell'eccezione, dove pero' il driver riporta lo statement chiamante
--    — e li' c'era scritto il NOME DELLA VARIABILE, non il suo valore. Il
--    ripiego era E_DATABASE, classificato tecnico: messaggio localizzato
--    scartato e dettaglio soppresso. Chi provava ad annullare un ordine gia'
--    in commessa non leggeva perche' non si poteva.
--
--    Un test sul solo `script.fn_log_and_raise_error` (che pure esiste, in
--    test-fn-log-and-raise-error-constraint-codice.sql) non basterebbe a
--    coprire questo: li' il codice si sa gia' quando si chiama. Qui il
--    percorso e' quello vero, UPDATE -> trigger -> guard -> funzione pura ->
--    helper, e il codice lo decide il DB.
--
--    Il test 7 usa throws_ok, che vede solo SQLSTATE e messaggio: i campi
--    diagnostici richiedono un blocco EXCEPTION con GET STACKED DIAGNOSTICS.
--    Lo stesso UPDATE si puo' rieseguire perche' il fallimento del 7 ha
--    annullato solo il proprio statement, non la transazione del test.
-- ============================================================
CREATE FUNCTION pg_temp.capture_annulla(p_ordine_id bigint)
RETURNS TABLE(v_sqlstate text, v_constraint text)
LANGUAGE plpgsql
AS $fn$
BEGIN
    BEGIN
        PERFORM vendite.fn_cambia_stato_ordine(p_ordine_id, 'ANNULLATO');
        v_sqlstate := NULL; v_constraint := NULL;
        RETURN NEXT;
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS
            v_sqlstate   = RETURNED_SQLSTATE,
            v_constraint = CONSTRAINT_NAME;
        RETURN NEXT;
    END;
END;
$fn$;

SELECT is(
  (SELECT ROW(v_sqlstate, v_constraint)::text
     FROM pg_temp.capture_annulla((SELECT ordine_id FROM tmp_gt_f))),
  ROW('P0001', 'E_SORGENTE_CON_RIGHE_EMESSE')::text,
  '8) il codice di dominio (da v_motivi, non da letterale) esce nel campo CONSTRAINT'
);

SELECT * FROM finish();
ROLLBACK;