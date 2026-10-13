-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce un'AZIENDA — emittente fiscale,
--   utente tecnico e identita' digitale (dbops.fn_pgtap_crea_emittente_operatore)
--   — e un operatore dentro un perimetro non crea l'azienda in cui lavora.
--   E' il criterio 2 di scripts/testpgtap.sh. Dal contesto in poi si lavora
--   nei panni dell'operatore costruito.
-- pgTAP test — le DATE DI CONSEGNA sulla riga, e la data che SOPRAVVIVE ai passaggi
--   (il push preventivo→ordine e la revisione N→N+1)
--   vendite.ordini_righe.data_consegna_richiesta_cliente / data_consegna_confermata
--   vendite.preventivi_righe.data_consegna_richiesta_cliente
--   acquisti.ordini_righe.data_consegna_richiesta / data_consegna_confermata_fornitore
--   ChangeSet: 20260913-06/-07/-08 (colonne), -16 (vista smistabili), -17
--   (vw_ordini_lista), -20 (fn_push_preventivo_a_ordine), 20260914-13
--   (fn_crea_revisione_preventivo). Brief:
--   brief-db-modifiche-certe-ciclo-vendita-e-articolo, sezioni 2, 6-quinquies e 7 (P-8, P-10).
--
-- Elenco test (plan 13):
--   STRUTTURA
--    1) le cinque colonne data esistono, con i nomi di D-16 (attore non marcato = nostro)
--    2) ⛔ nessun CHECK sulle date di consegna: fra le due e' una SCELTA (brief 2.3); contro la
--       data del documento la regola c'e' dal 2026-10-13, ma e' un GUARD con un codice
--       (test-data-consegna-vs-data-documento-v1), non un CHECK muto
--   PRIMA DEL PUSH
--    3) la vista-predicato dei smistabili espone la data della riga di preventivo, dalla sorgente
--   IL PUSH — percorso reale, vendite.fn_push_preventivo_a_ordine
--    4) ⭐ la data richiesta dal cliente sopravvive al push sulla riga d'ordine
--    5) la riga di preventivo SENZA data resta senza data: non si inventa
--    6) data_consegna_confermata resta NULL su tutte le righe: e' la promessa nostra, si decide dopo
--   LA TESTATA
--    7) vw_ordini_lista.data_consegna_richiesta_cliente_min = la piu' bassa fra le righe attive
--    8) e ignora una riga spenta: il min sale quando la riga con la data piu' bassa viene disattivata
--   LE DATE SI SCRIVONO E SI RILEGGONO
--    9) si puo' confermare PRIMA di quanto chiesto — nessun vincolo, e' una buona notizia
--   10) le due date si rileggono tali e quali dalla riga
--   LA REVISIONE — percorso reale, vendite.fn_crea_revisione_preventivo (20260914-13)
--   11) ⭐ la data richiesta dal cliente sopravvive alla revisione: sulla riga della rev N+1 c'e' la stessa
--   12) la riga di preventivo SENZA data resta senza data sulla rev N+1: non si inventa
--   13) la rev N conserva le sue date: la revisione COPIA, non sposta
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ I TEST 4 E 11 SONO PROVATI SUL PERCORSO REALE: chiamano
--   fn_push_preventivo_a_ordine e fn_crea_revisione_preventivo e leggono la
--   riga che ne esce. Confrontare due colonne di due tabelle proverebbe che
--   oggi coincidono; cosi' si prova che il passaggio NON perde la data — che
--   e' il punto in cui gli utenti smetterebbero di fidarsene (brief 2.4).
--   ⚠️ Sono DUE passaggi, e il secondo era scoperto: P-5 ha coperto il push,
--   la revisione ricopia le righe con un ALTRO elenco esplicito di colonne
--   (segnalazione del BE, 2026-09-14). Un presidio che guarda un passaggio
--   solo non dice niente sull'altro.
--
-- ⚠️ IL MONDO SI COSTRUISCE, NON SI CERCA: azienda (con i suoi registri, che il
--   provisioning dell'emittente crea da solo — serve il registro ORDINE per
--   numerare l'ordine che il push crea), cliente con billing account legato
--   a QUELLA azienda, articolo (catalogo/articoli.csv e' vuoto). Cosi' il file
--   misura la stessa cosa su dbdev e in CI.
--
-- ⚠️ acquisti.ordini_righe entra SOLO nella struttura (test 1): costruire un
--   ordine d'acquisto e' del cantiere acquisti, che non ha ancora un
--   comportamento applicativo. Le due date su acquisti si scrivono con
--   l'attore ribaltato (richiesta nostra, conferma del fornitore): il nome
--   lo dice, e il test 1 lo pinna.
--
-- ⚠️ I vincoli restano IMMEDIATE dalla riga di preambolo: gli helper della
--   fixture aprono e richiudono da soli la loro finestra differita.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ⚠️ rev 2026-10-13 (collaudo date di consegna, 20261013-66): le date sono
--   RELATIVE A OGGI. Il preventivo e l'ordine del push nascono con la data di
--   oggi, e una consegna anteriore al documento ora si rifiuta (righe) o non si
--   copia (push e revisione): con le date fisse di prima (2026-11-11, …) il file
--   sarebbe diventato rosso da solo, passata quella data. «bassa» e' la data
--   piu' bassa del test 8, comunque non anteriore a oggi.
CREATE TEMP TABLE _d AS
SELECT script.fn_data_operativa() + 29 AS richiesta,
       script.fn_data_operativa() + 23 AS confermata,
       script.fn_data_operativa() + 5  AS bassa,
       script.fn_data_operativa() + 51 AS rev;

-- ============================================================
-- STRUTTURA (prima della fixture: non dipende da nessun dato)
-- ============================================================
SELECT is(
    (SELECT string_agg(c.table_schema || '.' || c.table_name || '.' || c.column_name, ', '
                       ORDER BY c.table_schema, c.table_name, c.column_name)
       FROM information_schema.columns c
      WHERE c.data_type = 'date'
        AND (   (c.table_schema, c.table_name, c.column_name) = ('vendite',  'ordini_righe',     'data_consegna_richiesta_cliente')
             OR (c.table_schema, c.table_name, c.column_name) = ('vendite',  'ordini_righe',     'data_consegna_confermata')
             OR (c.table_schema, c.table_name, c.column_name) = ('vendite',  'preventivi_righe', 'data_consegna_richiesta_cliente')
             OR (c.table_schema, c.table_name, c.column_name) = ('acquisti', 'ordini_righe',     'data_consegna_richiesta')
             OR (c.table_schema, c.table_name, c.column_name) = ('acquisti', 'ordini_righe',     'data_consegna_confermata_fornitore'))),
    'acquisti.ordini_righe.data_consegna_confermata_fornitore, acquisti.ordini_righe.data_consegna_richiesta, '
    'vendite.ordini_righe.data_consegna_confermata, vendite.ordini_righe.data_consegna_richiesta_cliente, '
    'vendite.preventivi_righe.data_consegna_richiesta_cliente',
    '1) le cinque colonne data esistono, tipo date, con i nomi di D-16 (non marcato = nostro, marcato = della controparte)'
);

-- ⛔ Un CHECK «confermata >= richiesta» sarebbe FALSO (si puo' confermare
--   prima). Il test pinna la scelta: un vincolo aggiunto domani fa rosso qui, e
--   chi lo aggiunge legge perche' non c'era.
-- ⚠️ rev 2026-10-13 (collaudo date di consegna, 20261013-62…-68): contro la data
--   del documento la regola ora c'e' — una consegna non viene prima del
--   documento — ma e' un GUARD (script.trgfn_doc_righe_guard_data_consegna, col
--   lato testata), con un codice e una frase: un CHECK risponderebbe 23514 muto.
--   La retrodatazione resta possibile: si retrodata il documento, e le
--   consegne seguono. Il comportamento si prova in
--   test-data-consegna-vs-data-documento-v1.
SELECT is(
    (SELECT count(*)::int
       FROM pg_constraint k
      WHERE k.contype = 'c'
        AND k.conrelid IN ('vendite.ordini_righe'::regclass, 'vendite.preventivi_righe'::regclass,
                           'acquisti.ordini_righe'::regclass)
        AND pg_get_constraintdef(k.oid) ILIKE '%data_consegna%'),
    0,
    '2) nessun CHECK sulle date di consegna (brief 2.3): fra le due non c''e'' regola, contro la data documento la regola e'' un guard'
);

-- ============================================================
-- Fixture: il mondo, da owner
-- ============================================================
CREATE TEMP TABLE _mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Il billing account si lega a QUESTA azienda (terzo parametro): da owner il
-- trigger z90 non ha un operatore in sessione da cui derivarlo.
CREATE TEMP TABLE _cliente AS
SELECT c.*
  FROM _mondo m
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba(
      'Date consegna', NULL, m.soggetto_ruolo_id) c;

-- Articolo MERCE (natura di default = destinazione ORDINE): e' cio' che la
-- vista-predicato dei smistabili lascia passare verso l'ordine.
CREATE TEMP TABLE _articolo AS
WITH a AS (
    INSERT INTO catalogo.articoli (codice, descrizione, uom_id)
    SELECT 'PGTAP-DATECONS-' || substr(md5(random()::text), 1, 10),
           'Articolo pgTAP date di consegna',
           (SELECT um.id FROM catalogo.unita_misura um WHERE um.attivo IS TRUE ORDER BY um.id LIMIT 1)
    RETURNING id
)
SELECT id AS articolo_id FROM a;

-- ⭐ Da qui nei panni dell'operatore costruito: preventivo, righe e push sono
--   la strada dell'applicazione, e i guard di emittente leggono il contesto.
DO $ctx$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo));
END $ctx$;

-- Preventivo ACCETTATO (lo stato d'ingresso del push), con i riferimenti
-- della fixture: emittente derivato dal mondo, non pescato.
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): i due
--   preventivi del file (ACCETTATO per il push, EMESSO per la revisione)
--   nascono DRAFT, prendono le righe, poi passano di stato con
--   dbops.fn_pgtap_porta_a_stato — fuori bozza le righe non si scrivono piu'
--   (20261008-91).
CREATE TEMP TABLE _preventivo AS
WITH p AS (
    INSERT INTO vendite.preventivi
        (numero, billing_account_id, istanza_utility_id, utility_id, valuta_id,
         stato_doc_preventivo_id, emittente_fiscale_id, meta)
    SELECT 'PGTAP-DATECONS-' || substr(md5(random()::text), 1, 8),
           c.billing_account_id, c.istanza_utility_id, c.utility_id,
           (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1),
           (SELECT s.id FROM config.stati_doc_preventivi s
             WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE),
           m.emittente_fiscale_id,
           jsonb_build_object('test_scope', 'pgtap_date_consegna')
      FROM _cliente c, _mondo m
    RETURNING id
)
SELECT id AS preventivo_id FROM p;

-- Due righe: una CON la data richiesta dal cliente, una SENZA. La seconda e'
-- il gemello che prova che il push non inventa niente.
-- ⚠️ iva_id esplicito: un trigger di riga chiede l'aliquota.
CREATE TEMP TABLE _righe_prev AS
WITH r AS (
    INSERT INTO vendite.preventivi_righe
        (preventivo_id, articolo_id, prezzo_unitario, qta_operativa, iva_id, ordine,
         data_consegna_richiesta_cliente)
    SELECT p.preventivo_id, a.articolo_id, 10.00, 2, i.iva_id, x.ordine, x.data_richiesta
      FROM _preventivo p, _articolo a,
           (SELECT i.id AS iva_id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) i,
           (VALUES (1, (SELECT richiesta FROM _d)), (2, NULL::date)) AS x(ordine, data_richiesta)
    RETURNING id, ordine, data_consegna_richiesta_cliente
)
SELECT id AS riga_prev_id, ordine, data_consegna_richiesta_cliente FROM r;

DO $x$ BEGIN
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi',
                                         (SELECT preventivo_id FROM _preventivo), 'ACCETTATO');
END $x$;

-- ============================================================
-- 3) PRIMA DEL PUSH: la vista-predicato porta la data, dalla sorgente
-- ============================================================
SELECT is(
    (SELECT string_agg(COALESCE(v.data_consegna_richiesta_cliente::text, 'NULL'), ',' ORDER BY v.ordine)
       FROM vendite.vw_preventivi_righe_smistabili_ordine v
      WHERE v.preventivo_id = (SELECT preventivo_id FROM _preventivo)),
    (SELECT richiesta::text || ',NULL' FROM _d),
    '3) vw_preventivi_righe_smistabili_ordine espone la data della riga di preventivo tale e quale'
);

-- ============================================================
-- IL PUSH, sul percorso reale
-- ============================================================
CREATE TEMP TABLE _ordine AS
SELECT vendite.fn_push_preventivo_a_ordine((SELECT preventivo_id FROM _preventivo)) AS ordine_id;

CREATE TEMP TABLE _righe_ord AS
SELECT orr.id AS riga_ord_id, orr.riga_nr, orr.preventivo_riga_id,
       orr.data_consegna_richiesta_cliente, orr.data_consegna_confermata
  FROM vendite.ordini_righe orr
 WHERE orr.ordine_id = (SELECT ordine_id FROM _ordine);

SELECT is(
    (SELECT o.data_consegna_richiesta_cliente
       FROM _righe_ord o
       JOIN _righe_prev p ON p.riga_prev_id = o.preventivo_riga_id
      WHERE p.ordine = 1),
    (SELECT richiesta FROM _d),
    '4) la data richiesta dal cliente SOPRAVVIVE al push: sulla riga d''ordine c''e'' la stessa del preventivo'
);

SELECT is(
    (SELECT o.data_consegna_richiesta_cliente
       FROM _righe_ord o
       JOIN _righe_prev p ON p.riga_prev_id = o.preventivo_riga_id
      WHERE p.ordine = 2),
    NULL::date,
    '5) la riga di preventivo senza data resta senza data sull''ordine: il push non inventa'
);

SELECT is(
    (SELECT count(*)::int || ' righe, ' || count(*) FILTER (WHERE data_consegna_confermata IS NOT NULL)::int || ' confermate'
       FROM _righe_ord),
    '2 righe, 0 confermate',
    '6) data_consegna_confermata resta NULL su tutte le righe: e'' la promessa nostra, si decide alla conferma'
);

-- ============================================================
-- LA TESTATA: min() delle righe attive
-- ============================================================
SELECT is(
    (SELECT v.data_consegna_richiesta_cliente_min
       FROM vendite.vw_ordini_lista v
      WHERE v.id = (SELECT ordine_id FROM _ordine)),
    (SELECT richiesta FROM _d),
    '7) vw_ordini_lista.data_consegna_richiesta_cliente_min = la sola data presente (la riga NULL non conta)'
);

-- La riga 2 prende una data PIU' BASSA e poi viene spenta: il min deve
-- scendere e poi risalire. Cosi' si prova sia il min sia il filtro «attive».
UPDATE vendite.ordini_righe
   SET data_consegna_richiesta_cliente = (SELECT bassa FROM _d)
 WHERE id = (SELECT o.riga_ord_id FROM _righe_ord o JOIN _righe_prev p ON p.riga_prev_id = o.preventivo_riga_id WHERE p.ordine = 2);

UPDATE vendite.ordini_righe
   SET attivo = false
 WHERE id = (SELECT o.riga_ord_id FROM _righe_ord o JOIN _righe_prev p ON p.riga_prev_id = o.preventivo_riga_id WHERE p.ordine = 2);

SELECT is(
    (SELECT v.data_consegna_richiesta_cliente_min
       FROM vendite.vw_ordini_lista v
      WHERE v.id = (SELECT ordine_id FROM _ordine)),
    (SELECT richiesta FROM _d),
    '8) una riga spenta con una data piu'' bassa NON abbassa il min della testata: contano solo le righe attive'
);

-- ============================================================
-- LE DATE SI SCRIVONO E SI RILEGGONO
-- ============================================================
-- Conferma PRIMA di quanto chiesto (+29 -> +23): nessun vincolo fra le due la ferma.
SELECT lives_ok(
    $$UPDATE vendite.ordini_righe
         SET data_consegna_confermata = (SELECT confermata FROM _d)
       WHERE id = (SELECT o.riga_ord_id FROM _righe_ord o
                    JOIN _righe_prev p ON p.riga_prev_id = o.preventivo_riga_id
                   WHERE p.ordine = 1)$$,
    '9) si puo'' confermare una consegna PRIMA di quanto chiesto: nessun CHECK fra le due date'
);

SELECT is(
    (SELECT orr.data_consegna_richiesta_cliente::text || ' -> ' || orr.data_consegna_confermata::text
       FROM vendite.ordini_righe orr
      WHERE orr.id = (SELECT o.riga_ord_id FROM _righe_ord o
                       JOIN _righe_prev p ON p.riga_prev_id = o.preventivo_riga_id
                      WHERE p.ordine = 1)),
    (SELECT richiesta::text || ' -> ' || confermata::text FROM _d),
    '10) le due date si rileggono dalla riga tali e quali: richiesta dal cliente e confermata da noi'
);

-- ============================================================
-- LA REVISIONE, sul percorso reale — vendite.fn_crea_revisione_preventivo
--   Il secondo passaggio in cui le righe si RICOPIANO colonna per colonna
--   (20260914-13). Serve un preventivo EMESSO: la revisione nasce solo da
--   li', e quello sopra e' ACCETTATO ed e' gia' passato all'ordine.
--   Stesso cliente, stessa azienda, stesso articolo: cambia solo lo stato.
-- ============================================================
CREATE TEMP TABLE _preventivo_rev AS
WITH p AS (
    INSERT INTO vendite.preventivi
        (numero, billing_account_id, istanza_utility_id, utility_id, valuta_id,
         stato_doc_preventivo_id, emittente_fiscale_id, meta)
    SELECT 'PGTAP-DATECONS-REV-' || substr(md5(random()::text), 1, 8),
           c.billing_account_id, c.istanza_utility_id, c.utility_id,
           (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1),
           (SELECT s.id FROM config.stati_doc_preventivi s
             WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE),
           m.emittente_fiscale_id,
           jsonb_build_object('test_scope', 'pgtap_date_consegna')
      FROM _cliente c, _mondo m
    RETURNING id
)
SELECT id AS preventivo_id FROM p;

-- Le stesse due righe del push: una CON la data, una SENZA. Una data diversa
-- da quella del test 4, cosi' un'asserzione che leggesse per sbaglio l'altro
-- preventivo non passerebbe per caso.
INSERT INTO vendite.preventivi_righe
    (preventivo_id, articolo_id, prezzo_unitario, qta_operativa, iva_id, ordine,
     data_consegna_richiesta_cliente)
SELECT p.preventivo_id, a.articolo_id, 10.00, 2, i.iva_id, x.ordine, x.data_richiesta
  FROM _preventivo_rev p, _articolo a,
       (SELECT i.id AS iva_id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) i,
       (VALUES (1, (SELECT rev FROM _d)), (2, NULL::date)) AS x(ordine, data_richiesta);

DO $x$ BEGIN
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi',
                                         (SELECT preventivo_id FROM _preventivo_rev), 'EMESSO');
END $x$;

-- La revisione, nei panni dell'operatore: la testata nuova prende l'emittente
-- dal contesto (trigger BEFORE INSERT su preventivi), che e' quello del mondo.
CREATE TEMP TABLE _rev AS
SELECT r.nuovo_preventivo_id, r.nuova_rev
  FROM vendite.fn_crea_revisione_preventivo((SELECT preventivo_id FROM _preventivo_rev), 'pgtap') r;

-- La riga della rev N+1 si riconosce per `ordine`, che la revisione copia:
-- e' la stessa chiave con cui la funzione rimappa i componenti.
SELECT is(
    (SELECT pr.data_consegna_richiesta_cliente
       FROM vendite.preventivi_righe pr
      WHERE pr.preventivo_id = (SELECT nuovo_preventivo_id FROM _rev)
        AND pr.ordine = 1),
    (SELECT rev FROM _d),
    '11) la data richiesta dal cliente SOPRAVVIVE alla revisione: sulla riga della rev N+1 c''e'' la stessa del preventivo'
);

SELECT is(
    (SELECT pr.data_consegna_richiesta_cliente
       FROM vendite.preventivi_righe pr
      WHERE pr.preventivo_id = (SELECT nuovo_preventivo_id FROM _rev)
        AND pr.ordine = 2),
    NULL::date,
    '12) la riga di preventivo senza data resta senza data sulla rev N+1: la revisione non inventa'
);

-- La rev N e' storia: le sue righe restano come erano. Se una revisione un
-- giorno SPOSTASSE la data invece di copiarla, questo fa rosso.
SELECT is(
    (SELECT (SELECT nuova_rev FROM _rev)::text || ' | ' ||
            string_agg(pr.ordine || ':' || COALESCE(pr.data_consegna_richiesta_cliente::text, 'NULL'), ',' ORDER BY pr.ordine)
       FROM vendite.preventivi_righe pr
      WHERE pr.preventivo_id = (SELECT preventivo_id FROM _preventivo_rev)),
    (SELECT '1 | 1:' || rev::text || ',2:NULL' FROM _d),
    '13) la rev N+1 e'' nata (rev 1) e la rev N conserva le sue date tali e quali: la revisione COPIA, non sposta'
);

SELECT * FROM finish();
ROLLBACK;
