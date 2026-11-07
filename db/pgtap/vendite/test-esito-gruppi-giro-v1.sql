-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): CURATO — pescava il billing account «il primo per id» e moriva sulla commessa (billing_account_id nullo), un'asserzione su dodici. Ora il mondo si costruisce: la commessa da dbops.fn_pgtap_crea_commessa (sorgente ROOT), le tre righe sui tre gruppi da dbops.fn_pgtap_crea_commessa_attivita con la sorgente ORDINE_VENDITA di tre ordini veri (dbops.fn_pgtap_crea_ordine_con_righe; prima tre uid PREVENTIVO inventati, che la madre della riga rifiuta), i due lotti da dbops.fn_pgtap_crea_lotto, emissione, fatture, righe e aggancio da dbops.fn_pgtap_fattura_attivita (p_lotto_id: G1 su L1, G3 su L2). Resta a mano il PERIMETRO del giro su L1 (fatturazione_lotti_gruppi, lo scrive il backend): con la distribuzione dei gruppi nei lotti e' il caso.
-- pgTAP test per Zero ERP
--
-- Test: vendite.vw_lotti_gruppi_serviti (20260815-26)
--       vendite.fn_esito_gruppi_giro   (20260815-27)
--       Il CONSUNTIVO di un giro di fatturazione, gruppo per gruppo.
--       Brief: brief-db-emittibilita-visibile-e-sbloccabile §8.2 / §9.
--
-- Perche' esiste: `fn_list_emittibili_lane.gruppi_coperti` e' una PREVISIONE.
-- Fra la discovery e l'esecuzione le righe di un gruppo possono essere prese
-- da un altro giro: la pipeline esce senza errore e senza lotto per quel
-- gruppo, e l'esito legge pieno successo. Queste asserzioni presidiano la
-- misura fatta DOPO, che e' l'unica che sa distinguere i tre casi.
--
-- Fixture costruita dentro il test (non pescata dai dati) dai builder di dbops:
-- una commessa con tre gruppi sorgente distinti, due lotti, due fatture.
--   G1 -> attivita' EMESSA fatturata dal lotto L1   -> atteso SERVITO
--   G2 -> attivita' NON_EMESSA, mai fatturata       -> atteso NON_SERVITO
--   G3 -> attivita' EMESSA fatturata dal lotto L2   -> atteso FATTURATO_ALTROVE
-- Il perimetro richiesto {G1,G2,G3} e' persistito su L1 come fa
-- pipeline_repository.set_lotto_gruppi. L2 non ha perimetro: e' il giro di massa.
--
-- Indice test (0..11):
--   0)  Precondizioni (riferimenti minimi risolti)
--   1)  La vista e la funzione esistono
--   2)  vw_lotti_gruppi_serviti: L1 ha servito G1 con 1 attivita'
--   3)  G1 -> SERVITO, lotti_serventi = {L1}
--   4)  G2 -> NON_SERVITO con residuo 1 (e' il caso su cui si agisce)
--   5)  G3 -> FATTURATO_ALTROVE, lotti_altrui = {L2}, residuo 0
--   6)  Invarianza: richiesti = serviti + non serviti, tutti misurati
--   7)  Tutti e tre risultano richiesto = true (perimetro letto dal DB)
--   8)  Guard: array vuoto -> errore di dominio, non risposta vuota
--   9)  Guard: lotto inesistente -> errore di dominio
--   10) Giro di MASSA (L2, nessun perimetro): i serviti escono con richiesto=false
--   11) ⚠️ FAIL-CLOSED: lotto fuori scope -> SOLLEVA, non «non servito»
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Scattano al COMMIT, e qui il COMMIT non arriva mai (si chiude in ROLLBACK):
--   sarebbero saltati in silenzio, e il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (ruolo OPERATORE
-- + RLS attiva). Qui non e' un dettaglio: meta' della catena ha la RLS e meta'
-- no, ed e' proprio l'asimmetria che il test 11 verifica.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- ============================================================
-- 0) Riferimenti minimi
-- ============================================================
-- ⚠️ Niente LIMIT 1 senza ORDER BY: senza ordine, quale riga esca dipende dal
--   piano del planner e il test passerebbe a giorni alterni.
-- ⚠️ L'emittente non si pesca, si DERIVA dall'operatore corrente: le policy
--   ef_whitelist lo pretendono, e una fixture scritta su un emittente altrui
--   non passerebbe la RLS in scrittura.
-- ⚠️ Il mondo si COSTRUISCE: la commessa (con la sorgente ROOT, che il pull
--   pretende) di un cliente dell'azienda di chi agisce, e UN articolo per le
--   tre righe. La riga G1 nasce subito: il tipo documento dei lotti e' il suo.
CREATE TEMP TABLE tmp_eg_commessa AS
SELECT c.commessa_id AS id, c.billing_account_id, c.utility_id,
       c.emittente_soggetto_ruolo_id AS ef_sr, c.stato_commessa_id
  FROM dbops.fn_pgtap_crea_commessa('esito gruppi giro', NULL, NULL, p_con_sorgente_root => true) c;

CREATE TEMP TABLE tmp_eg_articolo AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-EG-ART', false) AS articolo_id;

-- I tre DOCUMENTI sorgente, uno per gruppo: tre ordini confermati dello
-- stesso cliente, ciascuno con la sua riga. ⚠️ Fino al 2026-10-25 erano tre
-- uid inventati con sorgente PREVENTIVO scritti a mano nella riga di
-- commessa; la madre della riga (fn_upsert_commessa_attivita) pretende che la
-- sorgente esista, e il builder dei preventivi costruisce un cliente suo. La
-- forma della chiave di gruppo ('<sorgente>:<uid>') e' la stessa.
CREATE TEMP TABLE tmp_eg_uid AS
SELECT 'G1'::text AS slot, o.ordine_uid::text AS uid, o.ordine_riga_id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('esito gruppi G1', 'CONFERMATO',
         (SELECT billing_account_id FROM tmp_eg_commessa),
         p_articolo_id => (SELECT articolo_id FROM tmp_eg_articolo)) o;
INSERT INTO tmp_eg_uid
SELECT 'G2', o.ordine_uid::text, o.ordine_riga_id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('esito gruppi G2', 'CONFERMATO',
         (SELECT billing_account_id FROM tmp_eg_commessa),
         p_articolo_id => (SELECT articolo_id FROM tmp_eg_articolo)) o;
INSERT INTO tmp_eg_uid
SELECT 'G3', o.ordine_uid::text, o.ordine_riga_id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('esito gruppi G3', 'CONFERMATO',
         (SELECT billing_account_id FROM tmp_eg_commessa),
         p_articolo_id => (SELECT articolo_id FROM tmp_eg_articolo)) o;

-- Le righe di commessa, una per gruppo (sorgente ORDINE_VENDITA, tre ordini),
-- APPROVATE e NON_EMESSE: l'emissione la fa la madre dentro il builder della
-- fattura. ⚠️ Nascono UNA per volta, appena prima del loro giro: la madre
-- emette TUTTE le righe approvate della commessa, e G3 emessa col marchio di
-- L1, o G2 emessa del tutto, non sarebbero piu' i casi del test.
CREATE TEMP TABLE tmp_eg_att (slot text, attivita_id bigint);

INSERT INTO tmp_eg_att
SELECT 'G1', a.attivita_id
  FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT id FROM tmp_eg_commessa), 10,
         (SELECT articolo_id FROM tmp_eg_articolo),
         p_sorgente_codice  => 'ORDINE_VENDITA',
         p_sorgente_uid     => (SELECT uid FROM tmp_eg_uid WHERE slot = 'G1'),
         p_sorgente_riga_id => (SELECT ordine_riga_id FROM tmp_eg_uid WHERE slot = 'G1')) a;

CREATE TEMP TABLE tmp_eg_refs AS
SELECT
  c.billing_account_id,
  c.utility_id,
  ca.istanza_utility_id,
  ca.articolo_id,
  ca.uom_id,
  ca.tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  c.stato_commessa_id,
  c.ef_sr,
  ca.sorgente_tipo_id,
  script.fn_pgtap_registro_fattura() AS registro_id,
  (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.attivo IS TRUE
    ORDER BY COALESCE(s.ordine, 32767), s.id LIMIT 1) AS stato_fiscale_id
  FROM tmp_eg_commessa c
  JOIN vendite.commesse_attivita ca ON ca.id = (SELECT attivita_id FROM tmp_eg_att WHERE slot = 'G1');

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND articolo_id IS NOT NULL
      AND uom_id IS NOT NULL AND tipo_doc_fiscale_id IS NOT NULL
      AND stato_commessa_id IS NOT NULL AND ef_sr IS NOT NULL
      AND sorgente_tipo_id IS NOT NULL AND registro_id IS NOT NULL
      AND stato_fiscale_id IS NOT NULL AND valuta_id IS NOT NULL
     FROM tmp_eg_refs),
  '0. Precondizioni soddisfatte (riferimenti minimi risolti)'
);

-- ============================================================
-- 1) Gli oggetti del cantiere esistono
-- ============================================================
SELECT ok(
  (SELECT count(*) FROM pg_views
     WHERE schemaname = 'vendite' AND viewname = 'vw_lotti_gruppi_serviti') = 1
  AND (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'vendite' AND p.proname = 'fn_esito_gruppi_giro') = 1,
  '1. vw_lotti_gruppi_serviti e fn_esito_gruppi_giro esistono'
);

-- ============================================================
-- Fixture: due lotti, e i tre gruppi distribuiti
--   G1 -> fatturato dal lotto L1 (il giro che stiamo consuntivando)
--   G3 -> fatturato da un ALTRO lotto, L2 («lavoro rubato da un altro giro»)
--   G2 -> resta NON_EMESSA: il lavoro fermo che il consuntivo deve vedere
-- ============================================================
-- I lotti dalla loro madre, DRAFT, massivi, col tipo documento delle righe.
CREATE TEMP TABLE tmp_eg_lotto AS
SELECT 'L1'::text AS slot, l.lotto_id
  FROM tmp_eg_refs r,
       dbops.fn_pgtap_crea_lotto('esito gruppi L1', 'DRAFT', r.billing_account_id, r.tipo_doc_fiscale_id) l;

INSERT INTO tmp_eg_lotto
SELECT 'L2', l.lotto_id
  FROM tmp_eg_refs r,
       dbops.fn_pgtap_crea_lotto('esito gruppi L2', 'DRAFT', r.billing_account_id, r.tipo_doc_fiscale_id) l;

-- G1 nel giro L1: emissione col marchio del lotto, testata della madre, riga,
-- lucchetto e aggancio (fattura_riga_id valorizzato: «questa riga E' stata
-- fatturata»).
CREATE TEMP TABLE tmp_eg_fatt AS
SELECT 'G1'::text AS slot, f.*
  FROM dbops.fn_pgtap_fattura_attivita('esito gruppi G1',
         ARRAY[(SELECT attivita_id FROM tmp_eg_att WHERE slot = 'G1')],
         (SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L1')) f;

-- G3 nel giro L2.
INSERT INTO tmp_eg_att
SELECT 'G3', a.attivita_id
  FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT id FROM tmp_eg_commessa), 30,
         (SELECT articolo_id FROM tmp_eg_articolo),
         p_sorgente_codice  => 'ORDINE_VENDITA',
         p_sorgente_uid     => (SELECT uid FROM tmp_eg_uid WHERE slot = 'G3'),
         p_sorgente_riga_id => (SELECT ordine_riga_id FROM tmp_eg_uid WHERE slot = 'G3')) a;

INSERT INTO tmp_eg_fatt
SELECT 'G3', f.*
  FROM dbops.fn_pgtap_fattura_attivita('esito gruppi G3',
         ARRAY[(SELECT attivita_id FROM tmp_eg_att WHERE slot = 'G3')],
         (SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L2')) f;

-- G2 per ultima: nessun giro la emette.
INSERT INTO tmp_eg_att
SELECT 'G2', a.attivita_id
  FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT id FROM tmp_eg_commessa), 20,
         (SELECT articolo_id FROM tmp_eg_articolo),
         p_sorgente_codice  => 'ORDINE_VENDITA',
         p_sorgente_uid     => (SELECT uid FROM tmp_eg_uid WHERE slot = 'G2'),
         p_sorgente_riga_id => (SELECT ordine_riga_id FROM tmp_eg_uid WHERE slot = 'G2')) a;

-- Le chiavi di gruppo si prendono dalla SOLA fonte di verita': ricostruirle a
-- mano nel test significherebbe verificare la copia, non l'originale.
CREATE TEMP TABLE tmp_eg_key AS
SELECT a.slot,
       vendite.fn_gruppo_fatturabile_key_di_attivita(ca.sorgente_tipo_id, ca.segment_key, ca.commessa_id) AS gruppo_key
  FROM tmp_eg_att a
  JOIN vendite.commesse_attivita ca ON ca.id = a.attivita_id;

-- Il PERIMETRO del giro, scritto come lo scrive pipeline_repository:
-- l'intera tupla richiesta su OGNI lotto del giro. Qui il giro e' un lotto solo.
INSERT INTO vendite.fatturazione_lotti_gruppi (lotto_id, gruppo_key)
SELECT (SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L1'), k.gruppo_key
  FROM tmp_eg_key k;

-- L'esito del giro L1 si calcola UNA volta e si interroga: cosi' le sei
-- asserzioni parlano della stessa fotografia, non di sei chiamate diverse.
CREATE TEMP TABLE tmp_eg_esito AS
SELECT * FROM vendite.fn_esito_gruppi_giro(
  ARRAY(SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L1'));

-- ============================================================
-- 2) La vista misura il fatto
-- ============================================================
SELECT ok(
  (SELECT s.n_attivita_fatturate = 1 AND s.n_fatture = 1
     FROM vendite.vw_lotti_gruppi_serviti s
    WHERE s.lotto_id = (SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L1')
      AND s.gruppo_key = (SELECT gruppo_key FROM tmp_eg_key WHERE slot = 'G1')),
  '2. vw_lotti_gruppi_serviti: L1 ha servito G1 con 1 attivita'' su 1 fattura'
);

-- ============================================================
-- 3-5) I tre esiti
-- ============================================================
SELECT ok(
  (SELECT e.esito = 'SERVITO'
      AND e.n_attivita_fatturate = 1
      AND e.lotti_serventi = ARRAY[(SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L1')]
      AND e.lotti_altrui IS NULL
     FROM tmp_eg_esito e
    WHERE e.gruppo_key = (SELECT gruppo_key FROM tmp_eg_key WHERE slot = 'G1')),
  '3. G1 fatturato dal lotto del giro -> SERVITO, lotti_serventi = {L1}'
);

SELECT ok(
  (SELECT e.esito = 'NON_SERVITO'
      AND e.n_attivita_fatturate = 0
      AND e.n_attivita_residue = 1
      AND e.lotti_serventi IS NULL
      AND e.lotti_altrui IS NULL
     FROM tmp_eg_esito e
    WHERE e.gruppo_key = (SELECT gruppo_key FROM tmp_eg_key WHERE slot = 'G2')),
  '4. G2 richiesto e mai fatturato, con righe ancora NON_EMESSA -> NON_SERVITO, residuo 1'
);

-- ⚠️ Il ramo che vale il test: senza il residuo a zero, G3 sarebbe
--   indistinguibile da G2, e il lavoro fermo verrebbe archiviato come gia'
--   sistemato. L'ordine dei rami del CASE E' la regola.
SELECT ok(
  (SELECT e.esito = 'FATTURATO_ALTROVE'
      AND e.n_attivita_fatturate = 0
      AND e.n_attivita_residue = 0
      AND e.lotti_serventi IS NULL
      AND e.lotti_altrui = ARRAY[(SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L2')]
     FROM tmp_eg_esito e
    WHERE e.gruppo_key = (SELECT gruppo_key FROM tmp_eg_key WHERE slot = 'G3')),
  '5. G3 fatturato da un ALTRO lotto, niente residuo -> FATTURATO_ALTROVE, lotti_altrui = {L2}'
);

-- ============================================================
-- 6-7) Invarianza e provenienza del perimetro
-- ============================================================
SELECT ok(
  (SELECT count(*) FILTER (WHERE e.richiesto)                                       = 3
      AND count(*) FILTER (WHERE e.richiesto AND e.esito = 'SERVITO')               = 1
      AND count(*) FILTER (WHERE e.richiesto AND e.esito <> 'SERVITO')              = 2
      AND count(*) FILTER (WHERE e.richiesto)
          = count(*) FILTER (WHERE e.richiesto AND e.esito = 'SERVITO')
          + count(*) FILTER (WHERE e.richiesto AND e.esito <> 'SERVITO')
     FROM tmp_eg_esito e),
  '6. Invarianza: richiesti (3) = serviti (1) + non serviti (2), entrambi misurati'
);

SELECT ok(
  (SELECT bool_and(e.richiesto) AND count(*) = 3 FROM tmp_eg_esito e),
  '7. Tutti e tre risultano richiesto=true: il perimetro e'' letto dal DB, non passato dal chiamante'
);

-- ============================================================
-- 8-9) Guard sui parametri
-- ============================================================
-- ⚠️ SQLSTATE esplicito: senza, throws_ok accetterebbe qualunque errore,
--   compreso il crash del guard che si vuole verificare.
SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_esito_gruppi_giro(ARRAY[]::bigint[]) $$,
  'P0001', NULL,
  '8. Array di lotti vuoto: errore di dominio, non una risposta vuota che sembra «nessun gruppo»'
);

SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_esito_gruppi_giro(ARRAY[-1]::bigint[]) $$,
  'P0001', NULL,
  '9. Id lotto non valido: errore di dominio (guard parametri, mai normalizzazione silenziosa)'
);

-- ============================================================
-- 10) Giro di MASSA: nessun perimetro persistito
-- ============================================================
SELECT ok(
  (SELECT e.esito = 'SERVITO' AND e.richiesto = false AND e.n_attivita_fatturate = 1
     FROM vendite.fn_esito_gruppi_giro(
            ARRAY(SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L2')) e
    WHERE e.gruppo_key = (SELECT gruppo_key FROM tmp_eg_key WHERE slot = 'G3')),
  '10. Lotto senza perimetro (giro di massa): i serviti escono con richiesto=false'
);

-- ============================================================
-- 11) ⚠️ FAIL-CLOSED. E'' il presidio del difetto piu' insidioso: la RLS su
--     questa catena e' asimmetrica (fatturazione_lotti_gruppi non ne ha,
--     fatturazione_lotti si'). Se la funzione rispondesse su un perimetro
--     dimezzato, un lotto invisibile produrrebbe «gruppi non serviti» — un
--     falso allarme con l'aria di un dato. Deve SOLLEVARE.
-- ============================================================
-- ⚠️ NON basta svuotare `app.current_user_id`: misurato, con utente NULL
--   `script.fn_scope_ef_whitelist_via_sr` risponde TRUE — «nessuna
--   restrizione», non «nessun accesso» — e i lotti resterebbero tutti
--   visibili. Il cancello vero e' il primo congiunto della policy: si cambia
--   veste, e la sessione smette di essere un operatore.
SELECT set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);

SELECT throws_ok(
  format(
    $$ SELECT * FROM vendite.fn_esito_gruppi_giro(ARRAY[%s]::bigint[]) $$,
    (SELECT lotto_id FROM tmp_eg_lotto WHERE slot = 'L1')),
  'P0001', NULL,
  '11. Lotto fuori scope: SOLLEVA (fail-closed), non risponde «non servito»'
);

SELECT * FROM finish();
ROLLBACK;
