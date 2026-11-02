-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2d): l'area della dashboard e' il codice della sorgente.
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): il contratto ATTIVO nasce da dbops.fn_pgtap_crea_contratto (madre di produzione) invece che da un INSERT a mano; date multi-mese e listino in bozza.
-- rev 2026-10-24 (brief-modello-documento-vendita R-2/R-9): l'azienda A nasce da dbops.fn_pgtap_crea_mondo_cliente (contesto aperto sul suo operatore, whitelist gia' sua: tolta la riscrittura a mano); B ha il suo operatore e il suo cliente e preventivo nascono sotto il suo contesto; il contratto nasce ATTIVO col periodo, la data e il listino dal builder; la commessa nasce da dbops.fn_pgtap_crea_commessa in BOZZA.
-- rev 2026-10-25 (brief-modello-documento-vendita §8.5): il caso (b) e' un contratto CESSATO; il preventivo EVASO con riga residua il modello non lo ammette piu'.
-- rev 2026-10-31 (brief-db-contratto-righe-periodiche-in-commessa §6.13, 20261031-04): il giudizio dei contratti e' riacceso; un contratto senza niente da mandare e' transitato ed esce dallo stock. I due contratti stanno su un listino QUOTA_FISSA con una quota mensile: dal valido_dal di due mesi fa i canoni maturano e non sono in commessa, quindi sono fermi (CANONE_NON_GENERATO). L'ATTIVO resta nello stock; il CESSATO resta il caso (b): chiuso, non transitato.
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE vendite.preventivi FORCE ROW LEVEL SECURITY: il test verifica che
--   la vista di dashboard resti coerente con la RLS armata.
-- pgTAP test per Zero ERP
--
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima il
--   contratto nasceva gia' ATTIVO, i preventivi NEGATIVO e di B gia' RIFIUTATO e
--   ACCETTATO). Il contratto si costruisce dopo il passaggio all'operatore di A
--   (setup 4): per attivarsi vuole un listino con una versione in vigore, e
--   dbops.fn_pgtap_crea_listino gli da' l'emittente di chi agisce.
--
-- Test: viste "Situazione aperta" v2 — SERBATOIO PRE-COMMESSA
--       (brief-db-situazione-aperta-v2, 20260708-03..04; design §6-ter
--       DL-14..18). Perimetro ristretto agli APERTI-NON-CONCLUSI:
--         area<>COMMESSE AND NOT is_abortito
--         AND is_transitato IS DISTINCT FROM true   (solo aperti)
--         AND fase <> 'CHIUSO'                       (solo non-conclusi)
--       e viste SNELLITE (via colonne transitato/is_aperto/n_aperti).
--
--       I due predicati sono entrambi necessari (nessuno basta da solo):
--         (a) TRANSITATO-non-chiuso  -> lo toglie SOLO is_transitato<>true
--             (es. preventivo ACCETTATO gia' completamente smistato, IN_CORSO);
--         (b) CHIUSO-non-transitato  -> lo toglie SOLO fase<>CHIUSO
--             (es. contratto CESSATO: esito POSITIVO -> NOT is_abortito NON
--             lo prende, is_transitato false (fermo: canoni maturati non in
--             commessa, rev 2026-10-31) -> is_aperto NON lo prende).  NB: l'esempio "offerta SUPERATA" del brief NON
--             vale (SUPERATA ha esito=NEGATIVO -> is_abortito, gia' escluso).
--             ⛔ rev 2026-10-25: l'esempio era il preventivo EVASO con riga
--             residua, che il modello non ammette piu': EVASO lo scrive solo
--             la proiezione dello smistamento quando nessuna riga e' RESIDUA,
--             cioe' quando il preventivo e' anche transitato (brief-modello-
--             documento-vendita §8; la fixture non lo raggiunge: passaggio di
--             processo, manuale = false).
--
--       Caso (a): coperto da INVARIANTE data-level (fallback, test 10) invece
--       che da fixture "transito completo" (costosa: is_transitato e' derivata
--       da tutte-le-righe-transitate).
--
-- Fixture: preventivo ACCETTATO con riga residua (aperto, resta), contratto
-- CESSATO (chiuso-non-transitato, ESCE — caso b), preventivo
-- ABORTITO (NEGATIVO, fuori), preventivo emittente B (scope), contratto ATTIVO
-- multi-mese fermo (aperto, resta), commessa (esclusa dallo stock).
--
-- Indice test (0..13):
--   0)  Precondizioni (refs: BA, articoli, stati incl. NEGATIVO e CESSATO)
--   1)  Le 2 viste vw_dash_aperto_* esistono
--   2)  Colonne transitato RIMOSSE dalla dettaglio
--       (is_transitato/is_aperto/valore_transitato/unita_transitate)
--   3)  Colonne RIMOSSE dal riepilogo (n_aperti/valore_transitato)
--   4)  Setup: operatore OPERATORE non-super trovato + GUC scope
--   5)  COMMESSE fuori dallo stock
--   6)  Abortito (esito NEGATIVO) fuori dallo stock
--   7)  Preventivo ACCETTATO con residuo: nello stock, valore>0, fase, motivo
--   8)  Contratto ATTIVO multi-mese fermo: 1 riga nello stock, valori NULL
--   9)  Caso (b): contratto CESSATO fermo -> in union (fase=CHIUSO,
--       NON abortito, NON transitato) ma ASSENTE dallo stock (fase<>CHIUSO)
--  10)  INVARIANTE perimetro: nessuna riga dello stock e' transitata o CHIUSA
--       sulla union (fallback caso a + b, seed-agnostico)
--  11)  Riepilogo coerente col dettaglio + DL-11 (CONTRATTI valore NULL)
--  12)  fase mai NULL nello stock
--  13)  SCOPE RLS (FORCE in-transazione): preventivo emittente B invisibile
-- ------------------------------------------------------------

BEGIN;
-- Il contesto e' quello dell'operatore di A, aperto dal mondo; i documenti di
-- B nascono sotto il contesto dell'operatore di B (il guard
-- trgfn_guard_emittente_scope rifiuterebbe, giustamente, un documento di B
-- scritto dall'operatore di A), poi si torna ad A. Cio' che il file verifica
-- e' lo scope RLS: l'asserzione 13 pretende che il preventivo di B risulti
-- invisibile all'operatore di A (ALTER TABLE ... FORCE ROW LEVEL SECURITY in
-- transazione). Brief: brief-db-pgtap-runner-rls-baseline §8.

SELECT plan(14);

-- ============================================================
-- 0) Riferimenti minimi
-- ============================================================
-- ⭐ Il mondo si FABBRICA (rev 2026-10-18): emittente A col suo operatore,
--   emittente B col suo, e un cliente per ciascuno, legato al suo emittente.
--   Prima si pescavano «il primo BA con un emittente derivabile» e «un BA di
--   un altro emittente»: su un database ricostruito da zero non ce n'e'.
-- rev 2026-10-24 (R-9): A e' il mondo del builder, che apre il contesto sul
--   suo operatore (whitelist su A, scritta dal builder). B si costruisce piu'
--   sotto, col suo operatore, insieme al suo preventivo.
CREATE TEMP TABLE tmp_ap_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('dash aperto A');

CREATE TEMP TABLE tmp_ap_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_ap_mondo) AS billing_account_id,
  (SELECT utility_id FROM tmp_ap_mondo) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_ap_mondo) AS istanza_utility_id,
  dbops.fn_pgtap_crea_articolo('PGT-DASH-AP') AS articolo_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'ACCETTATO' AND s.attivo IS TRUE LIMIT 1) AS prev_accettato_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE) AS prev_bozza_id,
  (SELECT s.id FROM config.stati_doc_contratti s
    WHERE s.codice_interno = 'CESSATO' AND s.attivo IS TRUE LIMIT 1) AS contr_cessato_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.esito = 'NEGATIVO' AND s.attivo IS TRUE
    ORDER BY s.id LIMIT 1) AS prev_negativo_id,
  -- lo stesso stato, per codice: ci si arriva per la matrice (rev 2026-10-24)
  (SELECT s.codice_interno FROM config.stati_doc_preventivi s
    WHERE s.esito = 'NEGATIVO' AND s.attivo IS TRUE
    ORDER BY s.id LIMIT 1) AS prev_negativo_cod,
  (SELECT s.id FROM config.stati_doc_contratti s
    WHERE s.codice_interno = 'ATTIVO' AND s.attivo IS TRUE LIMIT 1) AS contr_attivo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE
    ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE
    ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  -- lo stato in cui nasce la commessa del test (rev 2026-10-24: per codice)
  (SELECT sc.id FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE AND sc.codice_interno = 'BOZZA') AS stato_commessa_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  -- Emittente A = quello DERIVABILE dal BA principale (fn_get_emittente_fiscale_pk
  -- e' la funzione con cui i guard emittente<->BA confrontano).
  (SELECT anagrafiche.fn_get_emittente_fiscale_pk(billing_account_id) FROM tmp_ap_mondo) AS emittente_fiscale_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND articolo_id IS NOT NULL
      AND prev_accettato_id IS NOT NULL AND contr_cessato_id IS NOT NULL
      AND prev_negativo_id IS NOT NULL
      AND contr_attivo_id IS NOT NULL AND stato_commessa_id IS NOT NULL
      AND emittente_fiscale_id IS NOT NULL
     FROM tmp_ap_refs),
  '0. Precondizioni soddisfatte (incl. stato CESSATO per il caso b)'
);

-- ============================================================
-- 1) Le 2 viste esistono
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM pg_views
    WHERE schemaname = 'vendite'
      AND viewname IN ('vw_dash_aperto_documenti', 'vw_dash_aperto_riepilogo')),
  2,
  '1. Le 2 viste vw_dash_aperto_* esistono'
);

-- ============================================================
-- 2) Colonne transitato RIMOSSE dalla dettaglio (DL-14)
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM information_schema.columns
    WHERE table_schema = 'vendite' AND table_name = 'vw_dash_aperto_documenti'
      AND column_name IN ('is_transitato','is_aperto','valore_transitato','unita_transitate')),
  0,
  '2. Colonne transitato/is_aperto rimosse da vw_dash_aperto_documenti (DL-14)'
);

-- ============================================================
-- 3) Colonne RIMOSSE dal riepilogo (n_aperti/valore_transitato)
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM information_schema.columns
    WHERE table_schema = 'vendite' AND table_name = 'vw_dash_aperto_riepilogo'
      AND column_name IN ('n_aperti','valore_transitato')),
  0,
  '3. Colonne n_aperti/valore_transitato rimosse da vw_dash_aperto_riepilogo (DL-14)'
);

-- ============================================================
-- Fixture (con GUC ancora vuota: guard emittente in modalita' batch).
-- ============================================================

-- Preventivo ACCETTATO con 1 riga residua (emittente A) -> stock aperto.
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT, prende la riga, poi passa ad ACCETTATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le righe non si scrivono piu' (20261008-91).
CREATE TEMP TABLE tmp_ap_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-AP-PREV', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.prev_bozza_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_aperto'), r.emittente_fiscale_id
    FROM tmp_ap_refs r
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
SELECT p.id, r.articolo_id, 2.000000, 25.000000, r.iva_id, true
  FROM tmp_ap_prev p, tmp_ap_refs r;
DO $porta$ BEGIN PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_ap_prev), 'ACCETTATO'); END $porta$;

-- Caso (b): il contratto CESSATO, costruito dopo il setup 4 (vuole il listino
-- dell'operatore di A). rev 2026-10-25: era un preventivo EVASO con riga
-- residua, che il modello non ammette piu' (vedi la testata del file).

-- Preventivo ABORTITO (stato con esito NEGATIVO, emittente A) -> fuori stock.
-- rev 2026-10-24: nasce DRAFT e arriva allo stato NEGATIVO per la matrice.
CREATE TEMP TABLE tmp_ap_prev_neg AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-AP-PRNEG', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.prev_bozza_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_aperto'), r.emittente_fiscale_id
    FROM tmp_ap_refs r
  RETURNING id)
SELECT * FROM ins;

-- rev 2026-10-25 (brief-modello-documento-vendita §8.5): la riga e lo stato dal
--   builder sulla testata del test — l'emissione, sul percorso verso lo stato
--   NEGATIVO, chiede almeno una riga attiva (vendite.trgfn_preventivi_guard_transizione).
SELECT c.stato_doc_preventivo_id
  FROM tmp_ap_prev_neg p, tmp_ap_refs r,
       dbops.fn_pgtap_crea_preventivo_con_righe(
           'dash aperto neg', r.prev_negativo_cod, p.id, NULL, r.articolo_id) c;

-- Preventivo emittente B (per il test scope 13; il guard emittente<->BA del
-- 2026-07-13 vieta di appoggiare l'emittente B sul BA di A).
-- rev 2026-10-24: nasce DRAFT e arriva ad ACCETTATO per la matrice.
-- rev 2026-10-24 (R-9): l'azienda B col suo operatore; il cliente e il
--   preventivo nascono sotto il SUO contesto (il trigger z90 lega il BA a
--   chi agisce), poi si torna all'operatore di A.
CREATE TEMP TABLE tmp_ap_ef_b AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_ap_ef_b));

CREATE TEMP TABLE tmp_ap_cli_b AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgTAP dash aperto B');

CREATE TEMP TABLE tmp_ap_refs_b AS
SELECT c.billing_account_id                                       AS ba_b_id,
       c.utility_id                                               AS ba_b_utility_id,
       c.istanza_utility_id                                       AS ba_b_istanza_id,
       anagrafiche.fn_get_emittente_fiscale_pk(c.billing_account_id) AS ef_b_id
  FROM tmp_ap_cli_b c;

CREATE TEMP TABLE tmp_ap_prev_b AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-AP-PREVB', 0, b.ba_b_id, b.ba_b_istanza_id, b.ba_b_utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.prev_bozza_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_aperto'), b.ef_b_id
    FROM tmp_ap_refs r, tmp_ap_refs_b b
  RETURNING id)
SELECT * FROM ins;

-- rev 2026-10-25 (§8.5): la riga e lo stato dal builder, come sopra; l'articolo
--   lo costruisce il builder sotto il contesto di B.
SELECT c.stato_doc_preventivo_id
  FROM tmp_ap_prev_b p,
       dbops.fn_pgtap_crea_preventivo_con_righe('dash aperto B', 'ACCETTATO', p.id) c;

SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_ap_mondo));

-- Il contratto ATTIVO si costruisce dopo il setup 4 (rev 2026-10-24).

-- Commessa (emittente A) con 1 attivita': visibile in union, MAI nello stock.
-- rev 2026-10-24: nasce dalla madre via dbops.fn_pgtap_crea_commessa, in
--   BOZZA (prima: INSERT a mano nel «primo stato per id»). L'attivita' BOZZA
--   del 2080 resta del test.
CREATE TEMP TABLE tmp_ap_cmd AS
SELECT * FROM dbops.fn_pgtap_crea_commessa(
                 'dash aperto', 'BOZZA', (SELECT billing_account_id FROM tmp_ap_refs));

CREATE TEMP TABLE tmp_ap_commessa AS
SELECT commessa_id AS id FROM tmp_ap_cmd;

INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
  uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
  stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
SELECT (SELECT id FROM tmp_ap_commessa),
       'PGTAP-AP-A1-' || substr(md5(clock_timestamp()::text), 1, 8),
       r.articolo_id, r.istanza_utility_id, DATE '2080-02-01', r.uom_id, 1,
       DATE '2080-02-01', DATE '2080-02-01', DATE '2080-02-28',
       r.tipo_doc_fiscale_id, r.valuta_id, 33.000000, 'FIXED',
       'BOZZA', 'NON_EMESSA', (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
         ((SELECT id FROM tmp_ap_commessa))::text
FROM tmp_ap_refs r;

-- ============================================================
-- 4) Setup scope: operatore OPERATORE non-super whitelistato su A.
-- ============================================================
-- L'operatore e' quello fabbricato con l'emittente A (rev 2026-10-18): un
-- operatore OPERATORE non super, che prima si pescava fra quelli esistenti.
-- rev 2026-10-24 (R-9): la whitelist su A e il contesto li da' il mondo; la
--   riscrittura a mano di config.user_emittenti_fiscali e il set_config sono
--   usciti.
CREATE TEMP TABLE tmp_ap_op AS
SELECT id.auth_user_id AS user_id
  FROM anagrafiche.identita_digitali id
 WHERE id.auth_user_id = (SELECT auth_user_id FROM tmp_ap_mondo)
   AND id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND id.attivo = true
   AND NOT EXISTS (
       SELECT 1 FROM config.profili_accesso_bindings pab
       JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
       WHERE pab.identita_digitale_id = id.id
         AND pab.attivo = true
         AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso);

SELECT ok(
  (SELECT user_id IS NOT NULL FROM tmp_ap_op),
  '4. Trovato un operatore OPERATORE non-super per lo scope'
);

-- Contratto ATTIVO multi-mese (de-esploso: 1 riga nello stock).
-- ⛔ rev 2026-10-24 (brief-modello-documento-vendita N-1): nasceva gia' ATTIVO,
--   senza listino. L'attivazione vuole un listino con una versione in vigore
--   (trgfn_contratti_freeze_listino_versione): lo costruisce il builder, che
--   gli da' l'emittente di chi agisce, cioe' l'operatore di A in sessione.
-- ⛔ rev 2026-10-31 (20261031-04): il giudizio dei contratti e' riacceso, e un
--   contratto senza niente da mandare e' transitato: esce dallo stock e, CESSATO,
--   non e' piu' il caso (b). Il listino porta una quota QUOTA_FISSA mensile
--   (come in test-vw-dash-contratti-giudizio-v1, senza la quota che non puo'
--   partire): il push la legge dal listino anche senza righe di contratto, i
--   canoni dal valido_dal maturano e non sono in commessa, e i due contratti sono
--   fermi (CANONE_NON_GENERATO). La versione vale dal valido_dal dei contratti.
CREATE TEMP TABLE tmp_ap_listino AS
WITH ins AS (
  INSERT INTO vendite.listini (codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
  SELECT 'PGTAP_AP_' || substr(md5(clock_timestamp()::text || random()::text), 1, 10),
         'Fixture pgTAP: dash aperto',
         (SELECT utility_id FROM tmp_ap_refs),
         (SELECT t.id FROM config.listini_tipologie t WHERE t.codice = 'QUOTA_FISSA'),
         script.fn_pgtap_emittente_sr_operatore()
  RETURNING id)
SELECT id AS listino_id FROM ins;

CREATE TEMP TABLE tmp_ap_lst_ver AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
  SELECT listino_id, 'PGTAP_V1',
         (date_trunc('month', script.fn_data_operativa()) - interval '2 months')::date
    FROM tmp_ap_listino
  RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ap_quota AS
SELECT dbops.fn_pgtap_crea_articolo('PGTAP-AP-QUOTA',
         p_listino_tipologia_id => (SELECT t.id FROM config.listini_tipologie t WHERE t.codice = 'QUOTA_FISSA')) AS id;

DO $fx$ BEGIN
  PERFORM dbops.fn_pgtap_listino_aggiungi_articoli((SELECT id FROM tmp_ap_lst_ver),
    ARRAY[(SELECT id FROM tmp_ap_quota)], 100);
END $fx$;

UPDATE vendite.listini_righe
   SET periodicita = 'MENSILE'
 WHERE listino_versione_id = (SELECT id FROM tmp_ap_lst_ver)
   AND articolo_id = (SELECT id FROM tmp_ap_quota);

DO $fx$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni'::regclass, v.id, 'ATTIVA')
     FROM tmp_ap_lst_ver v;
END $fx$;

-- ⭐ rev 2026-10-24 (R-2): il contratto nasce dal builder, dalla madre di
--   produzione (numero, indirizzo di default), sul cliente di A, gia' ATTIVO
--   col periodo multi-mese (da due mesi fa, aperto), la data e il listino del
--   test.
CREATE TEMP TABLE tmp_ap_k AS
SELECT * FROM dbops.fn_pgtap_crea_contratto(
                 'pgTAP dash aperto', 'ATTIVO', (SELECT billing_account_id FROM tmp_ap_refs), NULL,
                 (date_trunc('month', script.fn_data_operativa()) - interval '2 months')::date,
                 NULL,
                 (date_trunc('month', script.fn_data_operativa()) - interval '2 months')::date,
                 (SELECT listino_id FROM tmp_ap_listino));

CREATE TEMP TABLE tmp_ap_contratto AS
SELECT contratto_id AS id FROM tmp_ap_k;

-- Caso (b): contratto CESSATO (fase CHIUSO, esito POSITIVO -> NON abortito;
-- fermo, canoni maturati non in commessa -> is_transitato false, rev
-- 2026-10-31). Deve essere presente in
-- union ma FUORI dallo stock, tolto SOLO da fase<>CHIUSO.
-- rev 2026-10-25: un cliente suo (il builder senza BA lo costruisce nella
-- stessa azienda, il contesto e' aperto), cosi' non si sovrappone al
-- contratto ATTIVO qui sopra; ATTIVO fino a oggi, poi la cessazione manuale
-- per la matrice (il guard la vuole con valido_al non nel passato).
CREATE TEMP TABLE tmp_ap_k_cessato AS
SELECT * FROM dbops.fn_pgtap_crea_contratto(
                 'pgTAP dash aperto cessato', 'ATTIVO', NULL, NULL,
                 (date_trunc('month', script.fn_data_operativa()) - interval '2 months')::date,
                 script.fn_data_operativa(),
                 (date_trunc('month', script.fn_data_operativa()) - interval '2 months')::date,
                 (SELECT listino_id FROM tmp_ap_listino));

CREATE TEMP TABLE tmp_ap_contratto_cessato AS
SELECT contratto_id AS id FROM tmp_ap_k_cessato;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti', c.id, 'CESSATO')
  FROM tmp_ap_contratto_cessato c;

-- ============================================================
-- 5) COMMESSE fuori dallo stock
-- ============================================================
SELECT ok(
  (SELECT EXISTS (
     SELECT 1 FROM vendite.vw_dash_fatturazione_documenti d
      WHERE d.area = 'COMMESSA'
        AND d.documento_id = (SELECT id FROM tmp_ap_commessa)))
  AND NOT EXISTS (
     SELECT 1 FROM vendite.vw_dash_aperto_documenti a
      WHERE a.area = 'COMMESSA'),
  '5. La commessa e'' nella union ma le COMMESSE non entrano nello stock (Lente 1 le copre)'
);

-- ============================================================
-- 6) Abortito fuori dallo stock (D-6 applicata dalla vista aperto)
-- ============================================================
SELECT ok(
  (SELECT EXISTS (
     SELECT 1 FROM vendite.vw_dash_fatturazione_documenti d
      WHERE d.documento_id = (SELECT id FROM tmp_ap_prev_neg)
        AND d.area = 'PREVENTIVO' AND d.is_abortito))
  AND NOT EXISTS (
     SELECT 1 FROM vendite.vw_dash_aperto_documenti a
      WHERE a.area = 'PREVENTIVO'
        AND a.documento_id = (SELECT id FROM tmp_ap_prev_neg)),
  '6. Preventivo con esito NEGATIVO: marcato abortito in union, ASSENTE dallo stock'
);

-- ============================================================
-- 7) Preventivo aperto nello stock (colonne v2: no is_aperto/valore_transitato)
-- ============================================================
SELECT ok(
  (SELECT a.fase IS NOT NULL
      AND a.valore_totale = 50
      AND a.motivo_fermo = 'RIGA_RESIDUA'
     FROM vendite.vw_dash_aperto_documenti a
    WHERE a.area = 'PREVENTIVO'
      AND a.documento_id = (SELECT id FROM tmp_ap_prev)),
  '7. Preventivo ACCETTATO con residuo: nello stock, valore 50, fase valorizzata, motivo_fermo tenuto'
);

-- ============================================================
-- 8) Contratto de-esploso -> 1 riga, valori NULL
--    rev 2026-10-31: fermo (tre canoni maturati non in commessa), resta nello
--    stock con UNA riga sola.
-- ============================================================
SELECT ok(
  (SELECT count(*) = 1
      AND bool_and(a.fase IS NOT NULL)
      AND bool_and(a.valore_totale IS NULL)
      AND bool_and(a.motivo_fermo = 'CANONE_NON_GENERATO')
     FROM vendite.vw_dash_aperto_documenti a
    WHERE a.area = 'CONTRATTO'
      AND a.documento_id = (SELECT id FROM tmp_ap_contratto)),
  '8. Contratto ATTIVO multi-mese fermo (canoni non in commessa): 1 sola riga nello stock, valori NULL'
);

-- ============================================================
-- 9) CASO (b): contratto CESSATO — in union (CHIUSO, non-abortito,
--    non-transitato) ma FUORI dallo stock (tolto SOLO da fase<>CHIUSO).
-- ============================================================
SELECT ok(
  (SELECT EXISTS (
     SELECT 1 FROM vendite.vw_dash_fatturazione_documenti d
      WHERE d.documento_id = (SELECT id FROM tmp_ap_contratto_cessato)
        AND d.area = 'CONTRATTO'
        AND d.fase = 'CHIUSO'
        AND NOT d.is_abortito
        AND d.is_transitato = false))
  AND NOT EXISTS (
     SELECT 1 FROM vendite.vw_dash_aperto_documenti a
      WHERE a.area = 'CONTRATTO'
        AND a.documento_id = (SELECT id FROM tmp_ap_contratto_cessato)),
  '9. Caso (b): contratto CESSATO fermo, non-abortito/non-transitato in union (fase CHIUSO), ASSENTE dallo stock via fase<>CHIUSO'
);

-- ============================================================
-- 10) INVARIANTE perimetro: nessuna riga dello stock e' transitata o CHIUSA
--     sulla union (fallback caso a + b, seed-agnostico — evita la fixture
--     "transito completo" costosa).
-- ============================================================
SELECT is(
  (SELECT count(*)::integer
     FROM vendite.vw_dash_aperto_documenti a
     JOIN vendite.vw_dash_fatturazione_documenti u
       ON u.area = a.area AND u.documento_id = a.documento_id
    WHERE u.is_transitato IS TRUE
       OR u.fase = 'CHIUSO'),
  0,
  '10. Invariante: nessun documento dello stock e'' transitato o in fase CHIUSO sulla union'
);

-- ============================================================
-- 11) Riepilogo coerente col dettaglio + DL-11
-- ============================================================
SELECT ok(
  -- cella PREVENTIVI della fase del fixture: conta e somma
  (SELECT r.n_documenti >= 1 AND r.valore_totale IS NOT NULL
     FROM vendite.vw_dash_aperto_riepilogo r
    WHERE r.area = 'PREVENTIVO'
      AND r.fase = (SELECT a.fase FROM vendite.vw_dash_aperto_documenti a
                     WHERE a.documento_id = (SELECT id FROM tmp_ap_prev)
                       AND a.area = 'PREVENTIVO'))
  AND
  -- cella CONTRATTI: area a conteggi -> valore_totale NULL (DL-11)
  (SELECT bool_and(r.valore_totale IS NULL)
     FROM vendite.vw_dash_aperto_riepilogo r
    WHERE r.area = 'CONTRATTO')
  AND
  -- coerenza globale: somma n_documenti del riepilogo = righe del dettaglio
  (SELECT (SELECT COALESCE(SUM(n_documenti), 0) FROM vendite.vw_dash_aperto_riepilogo)
        = (SELECT count(*) FROM vendite.vw_dash_aperto_documenti)),
  '11. Riepilogo: cella PREVENTIVI con valore, CONTRATTI a NULL (DL-11), somme = dettaglio'
);

-- ============================================================
-- 12) fase mai NULL nello stock
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_aperto_documenti a
    WHERE a.fase IS NULL),
  0,
  '12. Nessuna riga dello stock ha fase NULL'
);

-- ============================================================
-- 13) SCOPE RLS: FORCE in-transazione (pattern
--    test-rls-fatture-ef-whitelist-functional) assoggetta anche l'owner
--    titodb; GUC operatore A gia' impostata -> il preventivo di emittente B
--    deve sparire dallo stock (invoker -> RLS preventivi). Rollback finale
--    ripristina tutto. ULTIMO test: il FORCE resta attivo fino al rollback.
-- ============================================================
SET CONSTRAINTS ALL IMMEDIATE;
ALTER TABLE vendite.preventivi FORCE ROW LEVEL SECURITY;
SELECT set_config('app.ruolo_applicativo', 'OPERATORE', true);

SELECT CASE WHEN (SELECT ef_b_id FROM tmp_ap_refs_b) IS NULL
  THEN pass('13. [skip] nessun BA con secondo emittente derivabile: scope RLS non testabile')
  ELSE ok(
    (SELECT NOT EXISTS (
       SELECT 1 FROM vendite.vw_dash_aperto_documenti a
        WHERE a.documento_id = (SELECT id FROM tmp_ap_prev_b)
          AND a.area = 'PREVENTIVO')
     AND EXISTS (
       SELECT 1 FROM vendite.vw_dash_aperto_documenti a
        WHERE a.documento_id = (SELECT id FROM tmp_ap_prev)
          AND a.area = 'PREVENTIVO')),
    '13. Scope RLS (FORCE): l''operatore A vede il preventivo A, NON quello di emittente B'
  )
END;

SELECT * FROM finish();
ROLLBACK;
