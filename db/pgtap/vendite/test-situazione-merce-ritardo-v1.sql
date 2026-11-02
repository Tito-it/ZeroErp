-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): gli ordini da dbops.fn_pgtap_crea_ordine_con_righe (p_righe con la richiesta del cliente, p_data_ordine a -40, trigger SPEDITO); restano a mano le date scritte dopo (la promessa a ordine CONFERMATO, la richiesta in bozza del test 8): sono il caso.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla del test 9 dal builder dbops.fn_pgtap_crea_ddt_da_ordine (p_ordine_id); l'ordine resta scritto dal test: data a -40 (una data di consegna non precede l'ordine) e la promessa a -3 scritta a ordine CONFERMATO prima della spedizione.
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce un'AZIENDA — emittente fiscale,
--   utente tecnico e identita' digitale (dbops.fn_pgtap_crea_emittente_operatore)
--   — e un operatore dentro un perimetro non crea l'azienda in cui lavora.
--   E' il criterio 2 di scripts/testpgtap.sh. Dal contesto in poi si lavora
--   nei panni dell'operatore costruito.
-- pgTAP test — vw_situazione_merce_ordine: il RITARDO e le due date della riga
--   giorni_ritardo, data_consegna_richiesta_cliente, data_consegna_confermata
--   ChangeSet: 20260913-18. Brief: brief-db-modifiche-certe-ciclo-vendita-e-articolo,
--   sezioni 5.2 e 7 (P-8). Gemello di test-vw-situazione-merce-ordine-v1, che
--   resta la sede del residuo e degli stati: qui solo cio' che e' nato il 13-09.
--
-- Elenco test (plan 11):
--   STRUTTURA
--    1) le tre nuove sono IN CODA (posizioni 19, 20, 21) e con il loro tipo
--       (l'insieme delle 21 colonne lo pinna il gemello, test 3: non due volte)
--    2) da_spedire e' ancora numeric: la formula e' passata in una LATERAL, la colonna no
--   IL RITARDO — riga IMPEGNATA con residuo (ordine CONFERMATO, mai spedito)
--    3) senza date: NULL — c'e' da spedire, ma non c'e' un riferimento
--    4) solo la richiesta del cliente, 5 giorni fa: 5
--    5) ⭐ arriva la promessa, 3 giorni fa: 3 — la promessa VINCE sulla richiesta
--    6) promessa fra 2 giorni: 0 — c'e' da spedire e NON e' tardi (non NULL)
--    7) le due date escono dalla vista tali e quali
--   IL RITARDO — dove NON si applica
--    8) riga NON impegnata (ordine in bozza) con una data a -30: NULL, e da_spedire NULL
--    9) ⭐ riga SPEDITA PER INTERO con la promessa a -3: da_spedire 0 e giorni_ritardo NULL
--       — «non c'e' niente da spedire» non e' «in ritardo»
--   L'INVARIANTE, su tutta la vista
--   10) nessuna riga con giorni_ritardo valorizzato e da_spedire NULL o zero
--   11) nessuna riga con giorni_ritardo valorizzato e nessuna data dichiarata
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ CONTRO QUALE DATA SI MISURA — decisione di Tid del 2026-09-14 (brief 5.2):
--   la PROMESSA (data_consegna_confermata) se c'e', altrimenti la richiesta
--   del cliente. Si e' in ritardo rispetto a cio' a cui ci si e' impegnati; se
--   a una richiesta per il 1° abbiamo risposto «il 15», il 10 non siamo in
--   ritardo. Il test 5 inchioda la precedenza, il 6 lo zero.
--
-- ⚠️ TRE VALORI, E IL VUOTO NON E' ZERO — la disciplina di questa vista:
--   NULL = non si applica (niente da spedire, riga non impegnata, nessuna
--   data); 0 = c'e' da spedire e siamo in tempo; N = giorni di ritardo. Il
--   test 9 e' quello che distingue «pareggiata» da «in ritardo»: senza, un
--   ritardo contato su una riga gia' evasa passerebbe inosservato.
--
-- ⚠️ IL MONDO SI COSTRUISCE: azienda, cliente, articolo. Gli ordini (con la
--   riga, nello stato chiesto) dal builder dbops.fn_pgtap_crea_ordine_con_righe
--   e la spedizione del test 9 e' una bolla VERA, dal builder dbops.fn_pgtap_crea_ddt_da_ordine su
--   quell'ordine (p_ordine_id), fino a CONSEGNATO.
--
-- ⚠️ script.fn_data_operativa() anche qui: la vista conta i giorni dal giorno
--   dell'azienda (e' un indicatore, non una data documento), e il test calcola
--   l'attesa con lo stesso giorno, nella stessa transazione.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- STRUTTURA
-- ============================================================
-- ⚠️ L'INSIEME delle 21 colonne lo pinna test-vw-situazione-merce-ordine-v1
--    (test 3), sede del contratto: qui non se ne tiene una copia. Cio' che e'
--    nato il 13-09 e che `columns_are` NON sa provare — confronta insiemi, non
--    l'ordine — e' che le tre stanno IN CODA, 19-20-21, con il loro tipo.
SELECT results_eq(
    $q$SELECT a.attname::text COLLATE "default", format_type(a.atttypid, a.atttypmod), a.attnum::int
         FROM pg_attribute a
        WHERE a.attrelid = 'vendite.vw_situazione_merce_ordine'::regclass
          AND a.attnum > 0 AND NOT a.attisdropped
          AND a.attname IN ('data_consegna_richiesta_cliente','data_consegna_confermata','giorni_ritardo')
        ORDER BY a.attnum$q$,
    $q$VALUES ('data_consegna_richiesta_cliente', 'date',    19),
              ('data_consegna_confermata',       'date',    20),
              ('giorni_ritardo',                 'integer', 21)$q$,
    '1) le tre nuove sono IN CODA (19, 20, 21) e con il loro tipo: CREATE OR REPLACE puo'' solo appendere');

SELECT is(
    (SELECT format_type(a.atttypid, a.atttypmod) || '/' || a.attnum::text
       FROM pg_attribute a
      WHERE a.attrelid = 'vendite.vw_situazione_merce_ordine'::regclass AND a.attname = 'da_spedire'),
    'numeric/14',
    '2) da_spedire e'' ancora numeric, in quattordicesima posizione: la formula e'' passata in una LATERAL, la colonna no');

-- ============================================================
-- Fixture: il mondo, da owner
-- ============================================================
CREATE TEMP TABLE _mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE _cliente AS
SELECT c.*
  FROM _mondo m
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba(
      'Situazione merce ritardo', NULL, m.soggetto_ruolo_id) c;

CREATE TEMP TABLE _articolo AS
WITH a AS (
    INSERT INTO catalogo.articoli (codice, descrizione, uom_id)
    SELECT 'PGTAP-RITARDO-' || substr(md5(random()::text), 1, 10),
           'Articolo pgTAP ritardo consegna',
           (SELECT um.id FROM catalogo.unita_misura um WHERE um.attivo IS TRUE ORDER BY um.id LIMIT 1)
    RETURNING id
)
SELECT id AS articolo_id FROM a;

-- ⭐ Da qui nei panni dell'operatore costruito.
DO $ctx$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo));
END $ctx$;

-- Helper: un ordine nello stato dato, con una riga da p_qta a 25 (e, se data,
-- la richiesta del cliente scritta sulla riga in bozza), dal builder.
-- ⚠️ rev 2026-10-13 (collaudo date di consegna, 20261013-66): una data di
--   consegna non viene prima della data dell'ordine. L'ordine nasce a -40
--   (era -10), prima di ogni data di consegna del file (la piu' bassa e' la
--   richiesta a -30 del test 8): il ritardo si misura su oggi, non sulla
--   data dell'ordine, e nessuna asserzione cambia.
CREATE OR REPLACE FUNCTION pg_temp.mk_ordine(p_stato text, p_qta numeric,
                                             p_richiesta date DEFAULT NULL)
RETURNS TABLE(ordine_id bigint, ordine_riga_id bigint) AS $$
  SELECT o.ordine_id, o.ordine_riga_id
    FROM dbops.fn_pgtap_crea_ordine_con_righe('situazione_merce_ritardo', p_stato,
           (SELECT c.billing_account_id FROM _cliente c),
           p_fatturazione_trigger => 'SPEDITO',
           p_data_ordine          => script.fn_data_operativa() - 40,
           p_righe                => jsonb_build_array(jsonb_strip_nulls(jsonb_build_object(
               'articolo_id', (SELECT a.articolo_id FROM _articolo a), 'quantita', p_qta, 'prezzo', 25,
               'data_consegna_richiesta_cliente', p_richiesta)))) o
$$ LANGUAGE sql;

-- La riga IMPEGNATA (ordine confermato, 10 pezzi, mai spedita): residuo 10.
CREATE TEMP TABLE _a AS
SELECT * FROM pg_temp.mk_ordine('CONFERMATO', 10);

-- ============================================================
-- IL RITARDO sulla riga impegnata
-- ============================================================
SELECT is(
    (SELECT (s.da_spedire = 10)::text || '|' || COALESCE(s.giorni_ritardo::text, 'NULL')
       FROM vendite.vw_situazione_merce_ordine s WHERE s.ordine_riga_id = (SELECT ordine_riga_id FROM _a)),
    'true|NULL',
    '3) riga impegnata con residuo 10 (da_spedire = 10) e nessuna data: giorni_ritardo NULL (nessun riferimento)');

-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la richiesta del
--   cliente fuori bozza non si scrive piu' (20261008-90: l'eccezione e' la sola
--   data_consegna_confermata). Dal test 4 in poi la riga e' una seconda, _a2, che
--   nasce con la richiesta a -5 scritta IN BOZZA e poi e' confermata; la promessa
--   (5-7) resta un UPDATE su CONFERMATO, l'eccezione ammessa.
CREATE TEMP TABLE _a2 AS
SELECT * FROM pg_temp.mk_ordine('CONFERMATO', 10, script.fn_data_operativa() - 5);

SELECT is(
    (SELECT s.giorni_ritardo FROM vendite.vw_situazione_merce_ordine s WHERE s.ordine_riga_id = (SELECT ordine_riga_id FROM _a2)),
    5,
    '4) solo la richiesta del cliente, 5 giorni fa: 5 giorni di ritardo');

UPDATE vendite.ordini_righe SET data_consegna_confermata = script.fn_data_operativa() - 3
 WHERE id = (SELECT ordine_riga_id FROM _a2);

SELECT is(
    (SELECT s.giorni_ritardo FROM vendite.vw_situazione_merce_ordine s WHERE s.ordine_riga_id = (SELECT ordine_riga_id FROM _a2)),
    3,
    '5) con la promessa a -3 accanto alla richiesta a -5: 3 — la promessa vince (decisione 2026-09-14)');

UPDATE vendite.ordini_righe SET data_consegna_confermata = script.fn_data_operativa() + 2
 WHERE id = (SELECT ordine_riga_id FROM _a2);

SELECT is(
    (SELECT s.giorni_ritardo FROM vendite.vw_situazione_merce_ordine s WHERE s.ordine_riga_id = (SELECT ordine_riga_id FROM _a2)),
    0,
    '6) promessa fra 2 giorni: 0 — c''e'' da spedire e NON e'' tardi (non NULL)');

SELECT is(
    (SELECT (s.data_consegna_richiesta_cliente = script.fn_data_operativa() - 5)::text || '/' || (s.data_consegna_confermata = script.fn_data_operativa() + 2)::text
       FROM vendite.vw_situazione_merce_ordine s WHERE s.ordine_riga_id = (SELECT ordine_riga_id FROM _a2)),
    'true/true',
    '7) le due date della riga escono dalla vista tali e quali');

-- ============================================================
-- DOVE NON SI APPLICA
-- ============================================================
CREATE TEMP TABLE _b AS
SELECT * FROM pg_temp.mk_ordine('DRAFT', 10);

UPDATE vendite.ordini_righe SET data_consegna_richiesta_cliente = script.fn_data_operativa() - 30
 WHERE id = (SELECT ordine_riga_id FROM _b);

SELECT is(
    (SELECT COALESCE(s.da_spedire::text, 'NULL') || '|' || COALESCE(s.giorni_ritardo::text, 'NULL') || '|' || s.stato
       FROM vendite.vw_situazione_merce_ordine s WHERE s.ordine_riga_id = (SELECT ordine_riga_id FROM _b)),
    'NULL|NULL|NON_IMPEGNATA',
    '8) riga in bozza con la richiesta a -30: da_spedire NULL e giorni_ritardo NULL — sotto la soglia dell''impegno non c''e'' ritardo');

-- ⭐ Spedita per intero: DDT vero da 10, consegnato. Promessa scaduta a -3.
CREATE TEMP TABLE _c AS
SELECT * FROM pg_temp.mk_ordine('CONFERMATO', 10);
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la promessa si
--   scrive PRIMA della spedizione, a ordine CONFERMATO (l'eccezione di 20261008-90):
--   spedito per intero l'ordine e' EVASO e la riga non si tocca piu'.
UPDATE vendite.ordini_righe SET data_consegna_confermata = script.fn_data_operativa() - 3
 WHERE id = (SELECT ordine_riga_id FROM _c);
CREATE TEMP TABLE _c_ddt AS
SELECT b.ddt_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('ritardo', p_ordine_id => (SELECT ordine_id FROM _c),
                                         p_qta_da_evadere => 10) b;

SELECT is(
    (SELECT (s.da_spedire = 0)::text || '|' || COALESCE(s.giorni_ritardo::text, 'NULL')
       FROM vendite.vw_situazione_merce_ordine s WHERE s.ordine_riga_id = (SELECT ordine_riga_id FROM _c)),
    'true|NULL',
    '9) riga spedita per intero con la promessa a -3: da_spedire 0 e giorni_ritardo NULL — «niente da spedire» non e'' «in ritardo»');

-- ============================================================
-- L'INVARIANTE, su tutta la vista (owner: security_invoker legge tutto)
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_situazione_merce_ordine s
      WHERE s.giorni_ritardo IS NOT NULL AND (s.da_spedire IS NULL OR s.da_spedire <= 0)),
    0,
    '10) invariante: nessuna riga con un ritardo e niente da spedire');

SELECT is(
    (SELECT count(*)::int FROM vendite.vw_situazione_merce_ordine s
      WHERE s.giorni_ritardo IS NOT NULL
        AND s.data_consegna_confermata IS NULL AND s.data_consegna_richiesta_cliente IS NULL),
    0,
    '11) invariante: nessuna riga con un ritardo e nessuna data dichiarata');

SELECT * FROM finish();
ROLLBACK;
