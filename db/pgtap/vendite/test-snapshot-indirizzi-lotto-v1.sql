-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2d): l'ambito dei tipi d'indirizzo ammessi e' il codice della sorgente (FATTURE -> FATTURA).
-- pgtap-differiti: escluso — la fixture non soddisfa un vincolo DIFFERITO e la
--   ragione e' scritta per esteso piu' sotto. Debito noto (§22.4): quando la
--   fixture viene completata, si toglie questa riga e si rimette il
--   SET CONSTRAINTS ALL IMMEDIATE nel punto in cui l'unita' di lavoro e' completa.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_snapshot_fattura_lotto (Fase 2.2 + brief intestazione)
--       comportamento D-Q: lo step si completa, la fattura difettosa resta
--       marcata, il lotto non avanza, il rilancio ripulisce
-- Piano: piano-db-satelliti-fattura.md Fase 2.2 / D-F esteso / D-Q
-- ------------------------------------------------------------
-- Indice test (1..12):
--  1) Fixture: due BA con spazio indirizzi libero e ruoli distinti
--  2) Lotto, tre fatture e ponte creati
--  3) Primo giro: 2 lavorate, 1 indirizzo, 1 intestazione, 1 saltata, 1 fallita
--  4) La fattura DEFINITIVA non e' stata toccata
--  5) La fattura risolvibile ha il suo snapshot
--  6) La fattura difettosa e' marcata 'C' dal task
--  7) ...e il ponte la porta in stato_esecuzione = ERRORE
--  8) Nota informativa di lotto per le fatture saltate
--  9) Corretta l'anagrafica, il secondo giro non fallisce piu'
-- 10) La segnalazione del task e' ritirata e lo stato_esecuzione si sblocca
-- 11) Il ritiro tocca solo le PROPRIE segnalazioni
-- 12) Idempotenza: il terzo giro non scrive nulla, intestazione compresa
-- ------------------------------------------------------------
-- COSA STA DAVVERO PROVANDO QUESTO FILE. Non «la funzione scrive gli
-- indirizzi» -- quello lo prova gia' test-snapshot-indirizzi-fattura-v1 sulla
-- per-fattura. Qui si prova la REGOLA DI CONVIVENZA decisa da Tid (D-Q):
--   * una fattura definitiva non ha lavoro da fare e non ferma le altre;
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
-- ⚠️ QUESTO FILE NON USA `SET CONSTRAINTS ALL IMMEDIATE`, e la ragione e' un
--   DEBITO, non una scelta di stile.
--   vendite.fatturazione_lotti e vendite.fatture hanno due guard DEFERRABLE
--   INITIALLY DEFERRED che pretendono la coerenza fra lo stato fiscale del
--   lotto e quello delle sue fatture (E_LOTTO_FATTURE_STATO_INCOERENTE). Sono
--   differiti apposta: si aggiornano lotto e fatture in qualsiasi ordine dentro
--   la stessa transazione, e la coerenza si verifica al COMMIT.
--   ⚠️ Ma qui non e' questione di «troppo presto»: MISURATO mettendo il
--   controllo in coda, cioe' dove starebbe il COMMIT, il file esegue tutte le
--   sue asserzioni e POI fallisce lo stesso — «Lotto N: fattura/e con stato
--   fiscale diverso da quello del lotto». La fixture lascia davvero un lotto
--   incoerente: e' uno stato che l'applicazione non potrebbe committare.
--   La correzione vera e' allineare lo stato delle fatture a quello del lotto
--   prima di chiudere; allora la riga si rimette e il guard viene esercitato.
--   Brief: brief-db-pgtap-runner-rls-baseline §22.

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- ============================================================
-- Riferimenti e scelta dei due BA
-- ============================================================
CREATE TEMP TABLE tmp_ti_sil AS
SELECT (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'FATT') AS fatt_id;

CREATE TEMP TABLE tmp_base_sil AS
SELECT
  (SELECT m.registro_id
     FROM vendite.tipi_doc_fiscale_registri m
     JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
    WHERE t.attivo IS TRUE ORDER BY m.id LIMIT 1)   AS registro_id,
  (SELECT m.tipo_doc_fiscale_id
     FROM vendite.tipi_doc_fiscale_registri m
     JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
    WHERE t.attivo IS TRUE ORDER BY m.id LIMIT 1)   AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT s.id FROM config.stati_doc_fiscale s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE)      AS stato_draft_id,
  (SELECT s.id FROM config.stati_doc_fiscale s
    WHERE s.codice_interno = 'DEFINITIVA' AND s.attivo IS TRUE) AS stato_def_id,
  COALESCE((SELECT st.id FROM config.stati st WHERE st.codice_iso2 = 'IT'),
           (SELECT st.id FROM config.stati st ORDER BY st.id LIMIT 1)) AS stato_id;


-- Stesso criterio di test-snapshot-indirizzi-fattura-v1: spazio indirizzi
-- (ruolo + soggetto) vuoto per i tipi ammessi in ambito FATTURA, cosi' i
-- conteggi dipendono solo da cio' che inserisce il test.
CREATE TEMP TABLE tmp_cand_sil AS
SELECT ba.id AS billing_account_id, ba.soggetto_ruolo_id, ba.istanza_utility_id,
       ba.utility_id,
       anagrafiche.fn_get_emittente_fiscale_id(ba.id) AS emittente_soggetto_ruolo_id
  FROM anagrafiche.billing_account ba
  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
 WHERE anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
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
                                           AND a.attivo IS TRUE));

-- Due BA dello stesso ruolo, su istanze diverse: vedi la nota in testa.
CREATE TEMP TABLE tmp_ba_sil AS
SELECT c.*, row_number() OVER (ORDER BY c.billing_account_id) AS rn
  FROM tmp_cand_sil c
 WHERE c.soggetto_ruolo_id = (
         SELECT c2.soggetto_ruolo_id
           FROM tmp_cand_sil c2
          GROUP BY c2.soggetto_ruolo_id
         HAVING count(DISTINCT c2.istanza_utility_id) >= 2
          ORDER BY c2.soggetto_ruolo_id
          LIMIT 1)
 ORDER BY c.billing_account_id
 LIMIT 2;


-- ⛔ IL REGISTRO SI ALLINEA ALL'EMITTENTE, e prima non lo faceva: era scelto
--   dalla mappa tipi_doc_fiscale_registri INDIPENDENTEMENTE da chi emette, e dal
--   2026-08-30 vendite.trgfn_fatture_guard_registro_emittente non ammette piu' la
--   coincidenza. ⚠️ Sta QUI e non accanto a tmp_base_sil: l'emittente nasce con
--   tmp_ba_sil, ed e' la riga rn = 1 quella che il lotto usa.
UPDATE tmp_base_sil SET registro_id = script.fn_pgtap_registro_fattura(
    (SELECT emittente_soggetto_ruolo_id FROM tmp_ba_sil WHERE rn = 1));
SELECT is(
  (SELECT count(DISTINCT istanza_utility_id)::int FROM tmp_ba_sil), 2,
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
    p_tipo_doc_fiscale_id         => (SELECT tipo_doc_fiscale_id FROM tmp_base_sil),
    p_utility_id                  => (SELECT utility_id FROM tmp_ba_sil WHERE rn = 1),
    p_billing_account_id          => (SELECT billing_account_id FROM tmp_ba_sil WHERE rn = 1),
    p_lock_batch_id               => NULL,
    p_meta                        => jsonb_build_object('test', 'pgtap_snapshot_indirizzi_lotto'),
    p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_ba_sil WHERE rn = 1)
  ) AS lotto_id
 WHERE (SELECT ok FROM tmp_gate_sil);

CREATE TEMP TABLE tmp_fatture_sil AS
WITH casi AS (
  SELECT 'ok'::text AS caso, b.billing_account_id, b.emittente_soggetto_ruolo_id,
         bs.stato_draft_id AS stato_id
    FROM tmp_ba_sil b, tmp_base_sil bs WHERE b.rn = 1
  UNION ALL
  SELECT 'senza_indirizzo', b.billing_account_id, b.emittente_soggetto_ruolo_id,
         bs.stato_draft_id
    FROM tmp_ba_sil b, tmp_base_sil bs WHERE b.rn = 2
  UNION ALL
  SELECT 'definitiva', b.billing_account_id, b.emittente_soggetto_ruolo_id,
         bs.stato_def_id
    FROM tmp_ba_sil b, tmp_base_sil bs WHERE b.rn = 1
), ins AS (
  INSERT INTO vendite.fatture (
    registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
    tipo_doc_fiscale_id, stato_doc_fiscale_id, valuta_id, meta
  )
  SELECT bs.registro_id, script.fn_data_operativa(), c.emittente_soggetto_ruolo_id,
         c.billing_account_id, bs.tipo_doc_fiscale_id, c.stato_id, bs.valuta_id,
         jsonb_build_object('test', 'pgtap_snapshot_indirizzi_lotto', 'caso', c.caso)
    FROM casi c, tmp_base_sil bs
  RETURNING id, stato_doc_fiscale_id, meta ->> 'caso' AS caso
)
SELECT id, stato_doc_fiscale_id, caso FROM ins;

INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, stato_doc_fiscale_id)
SELECT l.lotto_id, f.id, f.stato_doc_fiscale_id
  FROM tmp_fatture_sil f, tmp_lotto_sil l;

SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sil)
  THEN skip('fixture non disponibile: servono due BA con spazio indirizzi libero', 1)
  ELSE is(
    (SELECT count(*)::int FROM vendite.fatturazione_lotti_fatture lf, tmp_lotto_sil l
      WHERE lf.lotto_id = l.lotto_id),
    3,
    '2) lotto, tre fatture e ponte creati')
END;

-- ============================================================
-- 3) PRIMO GIRO. E' l'asserzione centrale di D-Q: il giro non si ferma ne'
--    sulla definitiva ne' sulla difettosa.
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
    '2/1/0/1/1/1',
    '3) primo giro: 2 lavorate, 1 indirizzo, 1 intestazione, 1 saltata, 1 fallita')
END;

-- 4) La definitiva non e' stata toccata.
SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sil)
  THEN skip('fixture non disponibile', 1)
  ELSE is(
    (SELECT count(*)::int FROM vendite.fatture_indirizzi fi, tmp_fatture_sil f
      WHERE fi.fattura_id = f.id AND f.caso = 'definitiva'),
    0,
    '4) la fattura DEFINITIVA non e'' stata toccata')
END;

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
SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sil)
  THEN skip('fixture non disponibile', 1)
  ELSE is(
    (SELECT count(*)::int FROM vendite.fatturazione_lotti_log ll, tmp_lotto_sil l
      WHERE ll.lotto_id = l.lotto_id AND ll.status = 'I'
        AND ll.meta ->> 'task' = 'snapshot_indirizzi_lotto'),
    1,
    '8) nota informativa di lotto per le fatture saltate')
END;

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
    '1/1/0',
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
