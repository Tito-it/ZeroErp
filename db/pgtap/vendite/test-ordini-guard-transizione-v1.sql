-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
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

-- Nota emittente: gli ordini passano emittente_fiscale_id esplicito, quello del
--   loro billing account.
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
CREATE TEMP TABLE tmp_refs_gt AS
SELECT
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1
  ) AS emittente_fiscale_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id LIMIT 1
  ) AS soggetto_ruolo_id,
-- 🔴 rev 2026-10-13 (brief-db-articoli-ammessi-per-documento D-1/D-2): l'articolo si
--   COSTRUISCE. Prima si pescava dal catalogo (il primo per id, o il piu' recente):
--   il primo per id e' l'onere del seed ONERE_SENZA_CONTRATTO (natura servizio), e
--   da 20261013-42 ordine e bolla portano solo merce. Un articolo costruito ha solo
--   le proprieta' che il test gli da' (merce, non gestito a magazzino).
  dbops.fn_pgtap_crea_articolo('PGT-OGT-ART', false) AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  -- ⚠️ Aggiunta 2026-08-29: dal changeSet 20260829-07 il guard rifiuta
  --   l'ingresso in CONFERMATO se una riga attiva porta un prezzo senza
  --   aliquota (Regola 4, E_ORDINE_RIGA_IVA_MANCANTE). Le righe di questa
  --   fixture il prezzo ce l'hanno — prezzo_unitario e' NOT NULL — quindi
  --   senza iva_id descrivono un documento che il dominio non ammette piu'.
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'DRAFT'      LIMIT 1) AS stato_draft_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'CONFERMATO' LIMIT 1) AS stato_conf_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'ANNULLATO'  LIMIT 1) AS stato_ann_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'SPEDITO'    LIMIT 1) AS stato_sped_id;

CREATE TEMP TABLE tmp_gt_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('guard transizione ordini');
SET CONSTRAINTS ALL IMMEDIATE;

-- Helper: crea ordine DRAFT e ritorna id. Slot via meta.
-- Slot A: DRAFT con riga (test 2)
CREATE TEMP TABLE tmp_gt_a AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT c.soggetto_ruolo_id, c.billing_account_id, anagrafiche.fn_get_emittente_fiscale_pk(c.billing_account_id),r.stato_draft_id, r.valuta_id,
         DATE '2026-06-15', false, '{"test_scope":"pgtap_guard_transizione","slot":"A"}'::jsonb
  FROM tmp_refs_gt r, tmp_gt_cli c RETURNING id
) SELECT id FROM ins;
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'riga A', 3.0, 3.0, 10.0, r.iva_id, true, false, '{}'::jsonb
FROM tmp_gt_a o, tmp_refs_gt r;

-- Slot B: DRAFT senza righe (test 3)
CREATE TEMP TABLE tmp_gt_b AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT c.soggetto_ruolo_id, c.billing_account_id, anagrafiche.fn_get_emittente_fiscale_pk(c.billing_account_id),r.stato_draft_id, r.valuta_id,
         DATE '2026-06-15', false, '{"test_scope":"pgtap_guard_transizione","slot":"B"}'::jsonb
  FROM tmp_refs_gt r, tmp_gt_cli c RETURNING id
) SELECT id FROM ins;

-- Slot C: DRAFT con riga (test 4 annulla)
CREATE TEMP TABLE tmp_gt_c AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT c.soggetto_ruolo_id, c.billing_account_id, anagrafiche.fn_get_emittente_fiscale_pk(c.billing_account_id),r.stato_draft_id, r.valuta_id,
         DATE '2026-06-15', false, '{"test_scope":"pgtap_guard_transizione","slot":"C"}'::jsonb
  FROM tmp_refs_gt r, tmp_gt_cli c RETURNING id
) SELECT id FROM ins;
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'riga C', 3.0, 3.0, 10.0, r.iva_id, true, false, '{}'::jsonb
FROM tmp_gt_c o, tmp_refs_gt r;

-- Slot D: DRAFT con riga (test 5 transizione fuori matrice)
CREATE TEMP TABLE tmp_gt_d AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT c.soggetto_ruolo_id, c.billing_account_id, anagrafiche.fn_get_emittente_fiscale_pk(c.billing_account_id),r.stato_draft_id, r.valuta_id,
         DATE '2026-06-15', false, '{"test_scope":"pgtap_guard_transizione","slot":"D"}'::jsonb
  FROM tmp_refs_gt r, tmp_gt_cli c RETURNING id
) SELECT id FROM ins;
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'riga D', 3.0, 3.0, 10.0, r.iva_id, true, false, '{}'::jsonb
FROM tmp_gt_d o, tmp_refs_gt r;

-- Slot E: CONFERMATO con riga (test 6 CONFERMATO->ANNULLATO disabilitata)
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT, prende la riga, poi passa a CONFERMATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le righe non si scrivono piu' (20261008-90).
CREATE TEMP TABLE tmp_gt_e AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT c.soggetto_ruolo_id, c.billing_account_id, anagrafiche.fn_get_emittente_fiscale_pk(c.billing_account_id),r.stato_draft_id, r.valuta_id,
         DATE '2026-06-15', false, '{"test_scope":"pgtap_guard_transizione","slot":"E"}'::jsonb
  FROM tmp_refs_gt r, tmp_gt_cli c RETURNING id
) SELECT id FROM ins;
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'riga E', 3.0, 3.0, 10.0, r.iva_id, true, false, '{}'::jsonb
FROM tmp_gt_e o, tmp_refs_gt r;
DO $x$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', (SELECT id FROM tmp_gt_e), 'CONFERMATO');
END $x$;

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
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_conf_id FROM tmp_refs_gt) WHERE id = %s$q$,
         (SELECT id FROM tmp_gt_a)),
  '2) DRAFT->CONFERMATO con riga -> ok'
);

-- ============================================================
-- 3) DRAFT->CONFERMATO senza righe -> throws E_ORDINE_CONFERMA_SENZA_RIGHE
-- ============================================================
SELECT throws_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_conf_id FROM tmp_refs_gt) WHERE id = %s$q$,
         (SELECT id FROM tmp_gt_b)),
  'P0001', NULL,
  '3) DRAFT->CONFERMATO senza righe -> throws E_ORDINE_CONFERMA_SENZA_RIGHE'
);

-- ============================================================
-- 4) DRAFT->ANNULLATO -> ok
-- ============================================================
SELECT lives_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_ann_id FROM tmp_refs_gt) WHERE id = %s$q$,
         (SELECT id FROM tmp_gt_c)),
  '4) DRAFT->ANNULLATO -> ok (transizione manuale attiva)'
);

-- ============================================================
-- 5) DRAFT->SPEDITO (fuori matrice) -> throws E_ORDINE_TRANSIZIONE_NON_AMMESSA
-- ============================================================
SELECT throws_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_sped_id FROM tmp_refs_gt) WHERE id = %s$q$,
         (SELECT id FROM tmp_gt_d)),
  'P0001', NULL,
  '5) DRAFT->SPEDITO (fuori matrice) -> throws E_ORDINE_TRANSIZIONE_NON_AMMESSA'
);

-- ============================================================
-- 6) CONFERMATO->ANNULLATO senza figli a valle -> ok
--    L'ordine di fixture non ha DDT ne' commesse collegate:
--    script.fn_check_ordine_annullabile ritorna [] e il guard lascia passare.
-- ============================================================
SELECT lives_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_ann_id FROM tmp_refs_gt) WHERE id = %s$q$,
         (SELECT id FROM tmp_gt_e)),
  '6) CONFERMATO->ANNULLATO senza figli a valle -> ammesso'
);

-- ============================================================
-- 7) CONFERMATO->ANNULLATO con righe di commessa gia' EMESSA -> throws
--    Un secondo ordine confermato, agganciato a una commessa E con una riga
--    gia' emessa: il guard legge la stessa funzione pura del bottone e rifiuta.
--    ⚠️ Il solo collegamento alla commessa NON basta piu' (Q-9): quello che
--    ferma e' il lavoro in volo, non il fatto di aver spinto.
-- ============================================================
CREATE TEMP TABLE tmp_gt_f AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT c.soggetto_ruolo_id, c.billing_account_id, anagrafiche.fn_get_emittente_fiscale_pk(c.billing_account_id), r.stato_conf_id, r.valuta_id,
         DATE '2026-06-15', false, '{"test_scope":"pgtap_guard_transizione","slot":"F"}'::jsonb
  FROM tmp_refs_gt r, tmp_gt_cli c RETURNING id
) SELECT id FROM ins;

-- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-1): la commessa e' quella del
--   cliente dell'ordine, con l'emittente dell'ordine. Prima si copiava dalla
--   prima commessa del database (un altro cliente, magari un altro emittente):
--   passava solo perche' l'ordine non aveva BA, e il guard «una commessa, un
--   emittente» non aveva niente da confrontare.
INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                              emittente_soggetto_ruolo_id, stato_commessa_id)
SELECT 'PGTAP-GT-COM', c.billing_account_id, c.utility_id,
       (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
         WHERE ef.id = anagrafiche.fn_get_emittente_fiscale_pk(c.billing_account_id)),
       (SELECT sc.id FROM vendite.stati_commessa sc WHERE sc.codice_interno = 'APERTA')
  FROM tmp_gt_cli c;

INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
SELECT (SELECT id FROM vendite.commesse WHERE codice = 'PGTAP-GT-COM'),
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA'),
       (SELECT id FROM tmp_gt_f)::text,
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
SELECT (SELECT id FROM vendite.commesse WHERE codice = 'PGTAP-GT-COM'),
       'ORDINE_VENDITA:PGTAP-GT:R:1',
       r.articolo_id,
       -- ⚠️ vendite.commesse non ha istanza_utility_id: si risolve dal
       --    billing account della commessa, che e' dove vive.
       (SELECT b.istanza_utility_id FROM vendite.commesse c
          JOIN anagrafiche.billing_account b ON b.id = c.billing_account_id
         WHERE c.codice = 'PGTAP-GT-COM'),
       DATE '2026-06-15',
       (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1),
       1,
       DATE '2026-06-01', DATE '2026-06-01', DATE '2026-06-30',
       r.valuta_id, 10.000000, 'FIXED',
       'BOZZA', 'EMESSA',
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA'),
       (SELECT o.uid::text FROM vendite.ordini o WHERE o.id = (SELECT id FROM tmp_gt_f))
  FROM tmp_refs_gt r;

SELECT throws_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_ann_id FROM tmp_refs_gt) WHERE id = %s$q$,
         (SELECT id FROM tmp_gt_f)),
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
        UPDATE vendite.ordini
           SET stato_doc_ordine_id = (SELECT stato_ann_id FROM tmp_refs_gt)
         WHERE id = p_ordine_id;
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
     FROM pg_temp.capture_annulla((SELECT id FROM tmp_gt_f))),
  ROW('P0001', 'E_SORGENTE_CON_RIGHE_EMESSE')::text,
  '8) il codice di dominio (da v_motivi, non da letterale) esce nel campo CONSTRAINT'
);

SELECT * FROM finish();
ROLLBACK;
