-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2d): l'ambito dei tipi d'indirizzo ammessi e' il codice della sorgente (FATTURE -> FATTURA).
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): le fatture nascono in
--   bozza e la «definitiva» si porta avanti con dbops.fn_pgtap_porta_a_stato
--   (prima nasceva gia' DEFINITIVA). Per uscire dalla bozza le si scrivono
--   indirizzo FATT e intestazione, che in EMESSA (sotto soglia) si TOLGONO di
--   nuovo: arriva in DEFINITIVA nuda come prima, e il test 4 («non toccata»,
--   zero indirizzi) misura ancora il giro del lotto e non la fixture.
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-3/Q-4): il mondo si
--   COSTRUISCE (azienda, cliente con due BA su istanze diverse, le tre fatture
--   dal builder; la «definitiva» arriva in DEFINITIVA gia' spogliata) invece di
--   pescare «un ruolo con due istanze e lo spazio indirizzi libero». Il debito
--   del §22.4 e' curato: la fixture lascia un lotto COERENTE, il file gira tutto
--   IMMEDIATE e il guard di coerenza lotto/fatture scatta a ogni istruzione
--   (vedi dopo il BEGIN). I test 1 e 2 contano righe vere.
-- rev 2026-10-24 (brief-modello-documento-vendita R-1): esce dalla fixture la
--   fattura DEFINITIVA resa ferma dalla segnalazione 'C' di un altro task. Con
--   R-1 (Tid) quel mondo non esiste piu': una fattura in errore gia' congelata
--   non sta in un lotto non congelato (E_LOTTO_FATTURE_STATO_INCOERENTE), e nel
--   giro vero una definitiva in un lotto in bozza non si forma (dal DEFINITIVA
--   non si torna, e il ritorno del lotto in bozza cancella le fatture).
--   * Il 4 (definitiva non toccata) e l'8 (nota di lotto per le saltate)
--     diventano skip(): il ramo `congela_fiscale` di fn_snapshot_fattura_lotto
--     e' una DIFESA DICHIARATA, NON PROVATA da questo file. Resta nella
--     funzione (Regola zero), il modello non lo costruisce piu'.
--   * Attese cambiate, tutte per la stessa ragione (zero saltate): il 2 conta
--     DUE fatture nel ponte (erano tre), il 3 «2/1/0/1/0/1» (era 1 saltata),
--     il 9 «1/0/0» (era 1 saltata).
--   * Il cliente (BA 1) lo costruisce ora la fattura «ok».
-- pgTAP test per Zero ERP
-- Test: vendite.fn_snapshot_fattura_lotto (Fase 2.2 + brief intestazione)
--       comportamento D-Q: lo step si completa, la fattura difettosa resta
--       marcata, il lotto non avanza, il rilancio ripulisce
-- Piano: piano-db-satelliti-fattura.md Fase 2.2 / D-F esteso / D-Q
-- ------------------------------------------------------------
-- Indice test (1..12):
--  1) Fixture: due BA dello stesso ruolo su istanze diverse, spazio indirizzi libero
--  2) Lotto, due fatture e ponte creati, tutto in DRAFT
--  3) Primo giro: 2 lavorate, 1 indirizzo, 1 intestazione, 0 saltate, 1 fallita
--  4) [skip, R-1] La fattura DEFINITIVA non e' stata toccata
--  5) La fattura risolvibile ha il suo snapshot
--  6) La fattura difettosa e' marcata 'C' dal task
--  7) ...e il ponte la porta in stato_esecuzione = ERRORE
--  8) [skip, R-1] Nota informativa di lotto per le fatture saltate
--  9) Corretta l'anagrafica, il secondo giro non fallisce piu'
-- 10) La segnalazione del task e' ritirata e lo stato_esecuzione si sblocca
-- 11) Il ritiro tocca solo le PROPRIE segnalazioni
-- 12) Idempotenza: il terzo giro non scrive nulla, intestazione compresa
-- ------------------------------------------------------------
-- COSA STA DAVVERO PROVANDO QUESTO FILE. Non «la funzione scrive gli
-- indirizzi» -- quello lo prova gia' test-snapshot-indirizzi-fattura-v1 sulla
-- per-fattura. Qui si prova la REGOLA DI CONVIVENZA decisa da Tid (D-Q):
--   * una fattura definitiva non ha lavoro da fare e non ferma le altre
--     (rev 2026-10-24, R-1: difesa dichiarata, non provata -- vedi in testa);
--   * una fattura difettosa non fa morire il giro: resta marcata, e le altre
--     vengono lavorate lo stesso, cosi' i clienti incompleti si vedono TUTTI
--     in una volta invece di uno per esecuzione;
--   * il lotto non avanza finche' la marcatura e' li' (stato_esecuzione);
--   * e -- il pezzo che rende praticabile il «rilancia lo stesso step» -- il
--     task RITIRA la propria segnalazione quando il problema e' risolto.
--
-- Il test 11 e' quello che sorveglia l'errore piu' facile da commettere in
-- futuro: spegnere anche le segnalazioni altrui, cioe' dichiarare risolto un
-- problema che non si e' nemmeno guardato.
--
-- ⚠️ COME SI OTTIENE UNA FATTURA DIFETTOSA E UNA SANA. Non con due clienti
-- diversi: sul DB di sviluppo i BA con lo spazio indirizzi libero appartengono
-- tutti a UN solo soggetto_ruolo (un cliente con molte istanze -- e' il modello
-- utilities: una persona con luce, gas e idrico e' un ruolo con tre istanze).
-- Si usano allora due BA dello STESSO ruolo su ISTANZE diverse, e l'indirizzo
-- si crea legato all'istanza del primo: il secondo resta scoperto perche' non
-- ha ne' un indirizzo per la sua istanza ne' un generico.
-- Il giro e' cosi' anche piu' severo di quello progettato in origine: esercita
-- la precedenza per istanza (C-2) dentro il contesto del lotto, e la
-- correzione del test 9 avviene aggiungendo il generico -- cioe' provando il
-- fallback, non un secondo indirizzo per istanza.
-- ------------------------------------------------------------
BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   vendite.fatturazione_lotti, vendite.fatture e il ponte hanno tre guard
--   DEFERRABLE INITIALLY DEFERRED che pretendono la coerenza fra lo stato
--   fiscale del lotto e quello delle sue fatture
--   (E_LOTTO_FATTURE_STATO_INCOERENTE). Fino al 2026-10-24 questo file ne era
--   escluso: la fixture metteva una fattura DEFINITIVA in un lotto in DRAFT,
--   uno stato che un COMMIT vero rifiuta (brief-db-pgtap-runner-rls-baseline
--   §22). Ora (R-1) il lotto contiene solo fatture DRAFT come lui, e resta
--   coerente a ogni istruzione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- ⛔ L'AZIENDA SI COSTRUISCE (rev 2026-10-24, Q-4), e il contesto e' quello del
--   SUO operatore.
CREATE TEMP TABLE tmp_mondo_sil AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM tmp_mondo_sil)); END $ctx$;

SELECT plan(12);

-- ============================================================
-- Riferimenti e costruzione dei due BA
-- ============================================================
CREATE TEMP TABLE tmp_ti_sil AS
SELECT (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'FATT') AS fatt_id;

CREATE TEMP TABLE tmp_base_sil AS
SELECT
  (SELECT s.id FROM config.stati_doc_fiscale s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE)      AS stato_draft_id,
  -- Lo stato dal risolutore (codice_iso2 non e' univoco: mai una riga a caso).
  script.fn_stato_id_da_iso2('IT') AS stato_id;

-- La fattura «ok» per prima: costruisce il cliente (BA 1). In bozza il
-- builder non scrive ne' indirizzi ne' intestazione: li scrive il giro.
CREATE TEMP TABLE tmp_f_ok_sil AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('snapshot indirizzi lotto ok', 'DRAFT');

-- Il secondo BA: STESSO ruolo, ISTANZA nuova (vedi la nota in testa). Nessun
-- builder lo fa: lo scrive il building block di dominio
-- anagrafiche.fn_crea_billing_account, dentro la stessa finestra differita
-- che usa dbops.fn_pgtap_crea_cliente_ba (l'istanza nasce un'istruzione prima
-- del suo BA), richiusa subito: i guard differiti scattano qui, su un'unita'
-- di lavoro completa.
SET CONSTRAINTS ALL DEFERRED;

CREATE TEMP TABLE tmp_ba2_sil AS
SELECT b.billing_account_id, b.istanza_utility_id
  FROM tmp_f_ok_sil d
 CROSS JOIN LATERAL anagrafiche.fn_crea_billing_account(
         p_soggetto_ruolo_id           := d.cliente_soggetto_ruolo_id,
         p_utility_id                  := d.utility_id,
         p_campi                       := jsonb_build_object(
             'codice',               'PGTAPSIL2',
             'categoria_cliente_id', (SELECT cc.id FROM anagrafiche.categorie_clienti cc
                                       ORDER BY cc.id LIMIT 1),
             'valuta_id',            d.valuta_id),
         p_istanza                     := jsonb_build_object('codice', 'PGTAPSIL2'),
         p_emittente_soggetto_ruolo_id := d.emittente_soggetto_ruolo_id) b;

SET CONSTRAINTS ALL IMMEDIATE;

CREATE TEMP TABLE tmp_f_senza_sil AS
SELECT * FROM dbops.fn_pgtap_crea_fattura(
    'snapshot indirizzi lotto senza indirizzo', 'DRAFT',
    (SELECT billing_account_id FROM tmp_ba2_sil));

CREATE TEMP TABLE tmp_ba_sil AS
SELECT d.billing_account_id, d.cliente_soggetto_ruolo_id AS soggetto_ruolo_id,
       d.istanza_utility_id, d.utility_id, d.emittente_soggetto_ruolo_id,
       d.tipo_doc_fiscale_id, 1 AS rn
  FROM tmp_f_ok_sil d
UNION ALL
SELECT b.billing_account_id, d.cliente_soggetto_ruolo_id,
       b.istanza_utility_id, d.utility_id, d.emittente_soggetto_ruolo_id,
       d.tipo_doc_fiscale_id, 2
  FROM tmp_ba2_sil b, tmp_f_ok_sil d;

-- ⚠️ LO SPAZIO INDIRIZZI SI SVUOTA. Il ruolo CL nasce col suo FATT generico
--   (obbligatorio, lo scrive anagrafiche.fn_crea_indirizzi_ruolo), e un
--   generico coprirebbe per fallback anche la seconda istanza: proprio il caso
--   che il test vuole scoperto. Si toglie, cosi' i conteggi dipendono solo da
--   cio' che inserisce il test (lo stesso criterio di
--   test-snapshot-indirizzi-fattura-v1, che prima si otteneva SCEGLIENDO un
--   ruolo senza indirizzi). Il SEDELEG del soggetto non e' un tipo ammesso
--   in ambito FATTURA: resta.
DELETE FROM anagrafiche.indirizzi i
 USING tmp_ba_sil b
 WHERE b.rn = 1
   AND i.soggetto_ruolo_id = b.soggetto_ruolo_id
   AND i.tipo_indirizzo_id IN (SELECT a.tipo_indirizzo_id
                                 FROM config.tipi_indirizzi_allowed a
                                WHERE a.ambito = 'FATTURA'
                                  AND a.attivo IS TRUE);

-- ⚠️ Il 1 guarda le righe VERE: due BA dello stesso ruolo su istanze diverse,
--   e nessun indirizzo d'ambito FATTURA ne' sul ruolo ne' sul soggetto.
SELECT is(
  (SELECT count(DISTINCT ba.istanza_utility_id)::int
     FROM tmp_ba_sil t
     JOIN anagrafiche.billing_account ba ON ba.id = t.billing_account_id
     JOIN anagrafiche.soggetti_ruoli sr  ON sr.id = ba.soggetto_ruolo_id
    WHERE ba.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM tmp_ba_sil WHERE rn = 1)
      AND NOT EXISTS (
            SELECT 1 FROM anagrafiche.indirizzi i
             WHERE i.soggetto_ruolo_id = ba.soggetto_ruolo_id
               AND i.tipo_indirizzo_id IN (SELECT a.tipo_indirizzo_id
                                             FROM config.tipi_indirizzi_allowed a
                                            WHERE a.ambito = 'FATTURA'
                                              AND a.attivo IS TRUE))
      AND NOT EXISTS (
            SELECT 1 FROM anagrafiche.indirizzi_soggetti g
             WHERE g.soggetto_id = sr.soggetto_id
               AND g.tipo_indirizzo_id IN (SELECT a.tipo_indirizzo_id
                                             FROM config.tipi_indirizzi_allowed a
                                            WHERE a.ambito = 'FATTURA'
                                              AND a.attivo IS TRUE))),
  2,
  '1) fixture: due BA dello stesso ruolo su istanze diverse, spazio indirizzi libero'
);

CREATE TEMP TABLE tmp_gate_sil AS
SELECT (SELECT count(*) FROM tmp_ba_sil) = 2 AS ok;

-- L'indirizzo si lega all'ISTANZA del primo BA. Il secondo BA condivide il
-- ruolo ma non l'istanza, e non esiste un generico: resta quindi scoperto, ed
-- e' la fattura che dovra' fallire.
INSERT INTO anagrafiche.indirizzi (
  soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id,
  indirizzo_libero, stato_id, comune_id, codice_postale_id, locality, postal_code
)
SELECT b.soggetto_ruolo_id, ti.fatt_id, b.istanza_utility_id,
       'Via Lotto pgTAP 1', bs.stato_id, (dbops.fn_pgtap_indirizzo_libero_forma(bs.stato_id)).*  -- rev 2026-10-18: la forma dello stato
  FROM tmp_ba_sil b, tmp_ti_sil ti, tmp_base_sil bs
 WHERE b.rn = 1;

-- ============================================================
-- Lotto, fatture, ponte
-- ============================================================
CREATE TEMP TABLE tmp_lotto_sil AS
SELECT vendite.fn_create_fatturazione_lotto(
    p_competenza_mese             => date_trunc('month', script.fn_data_operativa())::date,
    p_tipo_doc_fiscale_id         => (SELECT tipo_doc_fiscale_id FROM tmp_ba_sil WHERE rn = 1),
    p_utility_id                  => (SELECT utility_id FROM tmp_ba_sil WHERE rn = 1),
    p_billing_account_id          => (SELECT billing_account_id FROM tmp_ba_sil WHERE rn = 1),
    p_lock_batch_id               => NULL,
    p_meta                        => jsonb_build_object('test', 'pgtap_snapshot_indirizzi_lotto'),
    p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_ba_sil WHERE rn = 1)
  ) AS lotto_id
 WHERE (SELECT ok FROM tmp_gate_sil);

CREATE TEMP TABLE tmp_fatture_sil AS
SELECT f.id, f.stato_doc_fiscale_id, t.caso
  FROM (SELECT fattura_id, 'ok'::text AS caso FROM tmp_f_ok_sil
        UNION ALL SELECT fattura_id, 'senza_indirizzo' FROM tmp_f_senza_sil) t
  JOIN vendite.fatture f ON f.id = t.fattura_id;

-- ⛔ Nessuna fattura definitiva nel lotto (rev 2026-10-24, R-1): niente piu'
--   segnalazione 'C' «di un altro task» per tenerla ferma. Vedi in testa.
INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, stato_doc_fiscale_id)
SELECT l.lotto_id, f.id, f.stato_doc_fiscale_id
  FROM tmp_fatture_sil f, tmp_lotto_sil l;

-- ⚠️ Il 2 conta il ponte e la forma dichiarata: lotto in DRAFT, le due
--   lavorabili in DRAFT e non critical.
--   ⚠️ Attesa cambiata (R-1): DUE righe, erano tre con la definitiva.
SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sil)
  THEN skip('fixture non disponibile: servono due BA con spazio indirizzi libero', 1)
  ELSE is(
    (SELECT count(*)::int
       FROM vendite.fatturazione_lotti_fatture lf
       JOIN tmp_lotto_sil l             ON l.lotto_id = lf.lotto_id
       JOIN vendite.fatturazione_lotti lo ON lo.id = lf.lotto_id
       JOIN vendite.fatture f           ON f.id = lf.fattura_id
       JOIN tmp_fatture_sil t           ON t.id = f.id
       JOIN tmp_base_sil bs             ON true
      WHERE lo.stato_doc_fiscale_id = bs.stato_draft_id
        AND f.stato_doc_fiscale_id = bs.stato_draft_id
        AND f.critical IS FALSE),
    2,
    '2) lotto, due fatture e ponte creati')
END;

-- ============================================================
-- 3) PRIMO GIRO. E' l'asserzione centrale di D-Q: il giro non si ferma
--    sulla difettosa.
--    ⚠️ Attesa cambiata (R-1): zero saltate (era 1, la definitiva).
-- ============================================================
CREATE TEMP TABLE tmp_run1_sil AS
SELECT s.*
  FROM tmp_lotto_sil l
 CROSS JOIN LATERAL vendite.fn_snapshot_fattura_lotto(l.lotto_id) s;

SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sil)
  THEN skip('fixture non disponibile', 1)
  ELSE is(
    (SELECT format('%s/%s/%s/%s/%s/%s', fatture_count, inserted_rows, updated_rows,
                   intestazioni_scritte, skipped_rows, failed_rows) FROM tmp_run1_sil),
    '2/1/0/1/0/1',
    '3) primo giro: 2 lavorate, 1 indirizzo, 1 intestazione, 0 saltate, 1 fallita')
END;

-- 4) La definitiva non e' stata toccata.
--    ⛔ rev 2026-10-24 (R-1): skip dichiarato, il ramo resta come difesa.
SELECT skip('R-1 (Tid, 2026-10-24): una fattura definitiva non convive con una in errore nello stesso lotto; il ramo che la salta resta come difesa e il modello non lo costruisce piu''', 1);

-- 5) La fattura risolvibile ha il suo snapshot.
SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sil)
  THEN skip('fixture non disponibile', 1)
  ELSE is(
    (SELECT fi.snapshot ->> 'via' FROM vendite.fatture_indirizzi fi, tmp_fatture_sil f
      WHERE fi.fattura_id = f.id AND f.caso = 'ok'),
    'Via Lotto pgTAP 1',
    '5) la fattura risolvibile ha il suo snapshot')
END;

-- 6) La difettosa e' marcata dal task, non da altri.
SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sil)
  THEN skip('fixture non disponibile', 1)
  ELSE is(
    (SELECT count(*)::int FROM vendite.fatture_log fl, tmp_fatture_sil f
      WHERE fl.fattura_id = f.id AND f.caso = 'senza_indirizzo'
        AND fl.status = 'C' AND fl.disabilitato IS FALSE
        AND fl.meta ->> 'task' = 'snapshot_indirizzi_lotto'),
    1,
    '6) la fattura difettosa e'' marcata critical dal task')
END;

-- 7) La marcatura arriva fino al ponte: e' cio' che tiene fermo il lotto.
SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sil)
  THEN skip('fixture non disponibile', 1)
  ELSE is(
    (SELECT lf.stato_esecuzione::text
       FROM vendite.fatturazione_lotti_fatture lf, tmp_fatture_sil f
      WHERE lf.fattura_id = f.id AND f.caso = 'senza_indirizzo'),
    'ERRORE',
    '7) il ponte porta la fattura difettosa in stato_esecuzione ERRORE')
END;

-- 8) Una nota informativa di lotto per le saltate: non critica, altrimenti
--    bloccherebbe proprio cio' che si vuole lasciar scorrere.
--    ⛔ rev 2026-10-24 (R-1): skip dichiarato, senza saltate la nota non nasce.
SELECT skip('R-1 (Tid, 2026-10-24): una fattura definitiva non convive con una in errore nello stesso lotto; il ramo che la salta resta come difesa e il modello non lo costruisce piu''', 1);

-- ============================================================
-- 9-10) Si corregge l'anagrafica e si rilancia lo STESSO step: e' la via
--       d'uscita prevista da D-Q, e deve funzionare fino in fondo.
--       La correzione e' un indirizzo GENERICO (istanza NULL) sullo stesso
--       ruolo: copre l'istanza rimasta scoperta per fallback, e non tocca la
--       prima fattura, che continua a preferire quello della sua istanza.
-- ============================================================
INSERT INTO anagrafiche.indirizzi (
  soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id,
  indirizzo_libero, stato_id, comune_id, codice_postale_id, locality, postal_code
)
SELECT b.soggetto_ruolo_id, ti.fatt_id, NULL,
       'Via Lotto pgTAP 2', bs.stato_id, (dbops.fn_pgtap_indirizzo_libero_forma(bs.stato_id)).*  -- rev 2026-10-18: la forma dello stato
  FROM tmp_ba_sil b, tmp_ti_sil ti, tmp_base_sil bs
 WHERE b.rn = 2;

CREATE TEMP TABLE tmp_run2_sil AS
SELECT s.*
  FROM tmp_lotto_sil l
 CROSS JOIN LATERAL vendite.fn_snapshot_fattura_lotto(l.lotto_id) s;

SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sil)
  THEN skip('fixture non disponibile', 1)
  ELSE is(
    (SELECT format('%s/%s/%s', inserted_rows, skipped_rows, failed_rows)
       FROM tmp_run2_sil),
    -- ⚠️ Attesa cambiata (R-1): zero saltate (era '1/1/0').
    '1/0/0',
    '9) secondo giro dopo la correzione: 1 inserita, nessun fallimento')
END;

SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sil)
  THEN skip('fixture non disponibile', 1)
  ELSE is(
    -- Non si asserisce il valore esatto dello stato: quale sia dopo lo sblocco
    -- lo decide fn_resolve_stato_esecuzione dal contesto del lotto. Cio' che
    -- deve valere e' che NON sia piu' ERRORE.
    (SELECT (fl.disabilitato)::text || '|' ||
            (lf.stato_esecuzione <> 'ERRORE')::text
       FROM vendite.fatture_log fl
       JOIN tmp_fatture_sil f ON f.id = fl.fattura_id
       JOIN vendite.fatturazione_lotti_fatture lf ON lf.fattura_id = f.id
      WHERE f.caso = 'senza_indirizzo'
        AND fl.meta ->> 'task' = 'snapshot_indirizzi_lotto'),
    'true|true',
    '10) segnalazione ritirata e stato_esecuzione sbloccato')
END;

-- ============================================================
-- 11) Il ritiro e' chirurgico: la segnalazione di un ALTRO task resta.
--     Spegnere anche quella significherebbe dichiarare risolto un problema
--     che questo task non ha nemmeno guardato.
-- ============================================================
INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta)
SELECT f.id, now(), 'Segnalazione di un altro task', 'C', FALSE,
       -- Stessa CHIAVE, valore diverso: cosi' il test prova che il filtro
       -- discrimina sul task e non si limita a guardare se la chiave c'e'.
       jsonb_build_object('task', 'un_altro_task', 'source', 'un_altro_task')
  FROM tmp_fatture_sil f WHERE f.caso = 'senza_indirizzo';

CREATE TEMP TABLE tmp_run3_sil AS
SELECT s.*
  FROM tmp_lotto_sil l
 CROSS JOIN LATERAL vendite.fn_snapshot_fattura_lotto(l.lotto_id) s;

SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sil)
  THEN skip('fixture non disponibile', 1)
  ELSE is(
    (SELECT count(*)::int FROM vendite.fatture_log fl, tmp_fatture_sil f
      WHERE fl.fattura_id = f.id AND f.caso = 'senza_indirizzo'
        AND fl.status = 'C' AND fl.disabilitato IS FALSE
        AND fl.meta ->> 'source' = 'un_altro_task'),
    1,
    '11) il ritiro tocca solo le proprie segnalazioni')
END;

-- 12) Idempotenza del giro: a dati invariati non si scrive nulla.
SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sil)
  THEN skip('fixture non disponibile', 1)
  ELSE is(
    (SELECT format('%s/%s/%s/%s', inserted_rows, updated_rows,
                   intestazioni_scritte, failed_rows)
       FROM tmp_run3_sil),
    '0/0/0/0',
    '12) idempotenza: il terzo giro non scrive nulla, intestazione compresa')
END;

SELECT * FROM finish();
ROLLBACK;
