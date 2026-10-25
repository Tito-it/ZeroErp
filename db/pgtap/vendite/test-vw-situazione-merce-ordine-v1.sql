-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-modello-documento-vendita §9, giro 7): l'annullo dell'ordine H (test 13) non e' piu' un UPDATE diretto dello stato, che la porta ferma (E_DOC_STATO_SOLO_DAL_VERBO): passa dal verbo d'annullo vendite.fn_annulla_ordine, con emetti_ordine concessa all'utente del contesto (l'annullo di un confermato la chiede). Attese invariate.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): gli ordini senza bolla (A, G, H) da dbops.fn_pgtap_crea_ordine_con_righe in pg_temp.mk_ordine (lo stato per parametro: ritirata la copia pg_temp.mk_ordine_stato); restano a mano l'annullo di H (il percorso del 13) e l'attivita' del kit di F (il caso del 10).
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): il reso dal builder dbops.fn_pgtap_crea_reso, la ri-consegna da dbops.fn_pgtap_crea_ddt_riconsegna (tutto il reso, consegnata); l'azione conferma_reso la concede il builder.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine (le spedizioni parziali con p_qta_da_evadere e p_ordine_id); restano a mano gli ordini SENZA bolla (A, G, H: il caso del 4/5/12/13), la bolla di ri-consegna (indirizzo e causale; gli stati per dbops.fn_pgtap_porta_a_stato) e il reso (giro 2).
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: vendite.vw_situazione_merce_ordine — l'aggregato PARLANTE per riga
--       d'ordine, per il pannello situazione merce.
--       (brief-db-situazione-merce-ordine-aggregato.md, changeSet 20260817-15)
--       ⚠️ Il contratto e' a 21 colonne dal 20260913-18 (P-6 di
--       brief-db-modifiche-certe-ciclo-vendita-e-articolo, sezione 5.2): le tre
--       in coda — le due date di consegna e giorni_ritardo — hanno il loro
--       gemello, test-situazione-merce-ritardo-v1. Qui restano il residuo e
--       gli stati. Fino al 2026-09-14 il test 3 inchiodava le 18 e il changeSet
--       aveva censito solo il gemello nuovo, non questo file: un contratto che
--       cambia si censisce anche nei pgTAP che GIA' lo pinnano.
--
-- Elenco test (plan 17):
--   1) la vista esiste
--   2) e' security_invoker=on
--   3) espone le 21 colonne del contratto (insieme, non ordine)
--   4) riga d'ordine MAI SPEDITA: c'e', partite_merce 0, differenza NULL,
--      stato NON_SPEDITA
--   5) riga mai spedita: da_spedire = ordinato
--   6) ⭐ tutte le partite NON fatturabili -> differenza NULL, NON `tenuti`
--   7) partite MISTE -> somma dei soli conti che si applicano
--   8) ⭐ `da_spedire` viene dal residuo ESISTENTE: evaso = ordinato ma un reso
--      per ri-consegna e' pendente -> 3, non 0
--   9) la RI-CONSEGNA emessa non conta due volte, e da_spedire torna a 0
--  10) kit senza `coeff_qta` sulla corsia ORD -> misurabile false, differenza NULL
--  11) scope ristretto: la riga SPARISCE, non esce a zero
--  --- soglia dell'impegno (20260818-06) ---
--  12) riga di ordine in BOZZA: c'e', ma stato NON_IMPEGNATA e da_spedire NULL
--  13) riga di ordine ANNULLATO mai spedito: idem — e non «N da spedire» per sempre
--  14) la PORTA che rende irraggiungibile «abortito con partite»: un ordine con
--      un DDT vivo non e' annullabile
--  15) coerenza del SEED: DRAFT e' l'unico stato attivo sotto la soglia
--  16) invariante globale: nessuna riga con da_spedire valorizzato sotto soglia
--  17) la CARDINALITA' non cambia: una riga per riga d'ordine attiva
--
-- Scopo:
--  - il 6) e' il ramo che **nessun dato attraversa oggi** e che il perimetro
--    BE ha chiesto esplicitamente di costruire: su una riga d'ordine le cui
--    partite sono tutte NON_FATTURABILE, il vecchio contatore grezzo
--    (`vw_contatore_merce`, ritirata il 22-09-2026) diceva «N da fatturare»
--    (faceva `tenuti − 0`). Qui deve dire «non si applica».
--  - l' 8) presidia la correzione piu' importante rispetto alla richiesta
--    originale. `GREATEST(0, ordinato − consegnato)` avrebbe dato 0 su questa
--    fixture, mentre l'ordine deve ancora spedire: il `consegnato` delle
--    partite include le ri-consegne e non e' comparabile con l'ordinato.
--    Il caso e' quello reale della riga d'ordine 18946 (ORD0018586).
--  - l' 11) presidia la regola «zero non e' un dato»: se lo scope nasconde
--    l'ordine, la riga non deve uscire con dei conti a zero.
--    ⭐ E ha gia' fatto il suo mestiere: la prima versione della vista partiva
--    da `vendite.ordini_righe`, che NON ha policy — la RLS sta su
--    `vendite.ordini`. Un utente fuori scope avrebbe visto TUTTE le 107 righe
--    con i conti a zero, perche' le partite erano nascoste e i COALESCE le
--    trasformavano in zeri. Il `JOIN vendite.ordini` della vista esiste per
--    questo.
--    ⚠️ Questo test ha senso SOLO col runner applicativo (il default dal
--    2026-08-07): l'owner salta la RLS e lo vedrebbe passare per finta.
--  - il 12) e il 13) sono la SOGLIA DELL'IMPEGNO (changeSet 20260818-06),
--    gemella della decisione D1 sul DDT. Prima, 60 righe su 107 — tutte su
--    ordini in bozza — dichiaravano «N da spedire»: un'intenzione presentata
--    come un arretrato. ⚠️ Si verifica che la riga CI SIA ancora: farla
--    sparire renderebbe VUOTO il pannello di ogni bozza (il pannello e' per
--    ordine), cioe' «non ho il permesso di saperlo» presentato come «non c'e'
--    nulla da fare» — lo stesso difetto dell' 11), da un'altra porta.
--  - il 14) non misura la vista: misura la PORTA che rende il ramo «ordine
--    abortito CON partite» irraggiungibile. Senza, la precedenza data alle
--    partite nel CASE sarebbe una regola non verificata — e una fixture
--    costruita a mano l'avrebbe confermata scavalcando il dominio.
--  - il 15) inchioda un'assunzione sul SEED e non sul modello: su
--    `config.stati_doc_ordini` la colonna `ordine` e' un ordinamento di
--    PRESENTAZIONE (EVASO 25 sta prima di ALLOCATO 30), non un ciclo di vita.
--    La soglia `>= CONFERMATO` e' corretta solo finche' DRAFT resta l'unico
--    stato sotto. Se un seed futuro lo cambia, deve fallire QUI e non far
--    ricomparire le bozze in silenzio.
--  - il 16) e il 17) sono la rete chiesta dal perimetro BE, nella forma che
--    non decade: non «le 47 righe di oggi» (un numero che i dati di sviluppo
--    spostano), ma i due INVARIANTI — nessun arretrato sotto soglia, e la
--    cardinalita' del contratto invariata. Il 17) e' cio' che rende vero
--    «il BE non deve muovere niente».
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE. Senza, un fallimento a meta' lascia i dati di prova nel
--   database e rompe la corsa successiva, che vede un rosso non suo.
BEGIN;

-- ⚠️ 2. VINCOLI DIFFERITI. Scattano al COMMIT, e qui il COMMIT non arriva mai:
--   senza questa riga il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- ⚠️ 3. CONTESTO APPLICATIVO. La vista legge ordini e ddt, che hanno RLS.
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (in CI l'utente 1 non esiste;
--   anagrafiche e articoli sono vuoti). fn_pgtap_crea_mondo_cliente fa azienda,
--   operatore, cliente BA legato a quell'azienda e APRE il contesto da se'.
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP situazione merce');
-- Il mondo ha gia' aperto il contesto sul suo operatore: la riga lo
--   dichiara (e il guardrail del preambolo la cerca).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;

SELECT plan(17);

-- ============================================================
-- 1-3) Struttura
-- ============================================================
SELECT has_view('vendite', 'vw_situazione_merce_ordine', '1) la vista esiste');

SELECT ok(
  (SELECT 'security_invoker=on' = ANY(c.reloptions)
     FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite' AND c.relname = 'vw_situazione_merce_ordine'),
  '2) vw_situazione_merce_ordine e'' security_invoker=on');

-- ⚠️ `columns_are` confronta INSIEMI, non l'ordine: questa e' la sede del
--    contratto (quali colonne), la posizione delle tre in coda la pinna il
--    gemello test-situazione-merce-ritardo-v1 (test 1 e 2), non due volte qui.
SELECT columns_are('vendite', 'vw_situazione_merce_ordine',
  ARRAY['ordine_riga_id','ordine_id','riga_nr','articolo_id','ordinato',
        'consegnato','reso','in_riconsegna','tenuti','fatturato_merce',
        'fatturato_da_ordine','fatturato','fatturato_anticipato','da_spedire',
        'partite_merce','misurabile','differenza','stato',
        'data_consegna_richiesta_cliente','data_consegna_confermata','giorni_ritardo'],
  '3) espone le 21 colonne del contratto (18 del 2026-08 + le tre del 20260913-18)');

-- ============================================================
-- Riferimenti
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  -- ⛔ rev 2026-10-13: BA, utility e istanza del cliente dal
  --   mondo costruito; l'articolo si costruisce (merce, non gestito: il test non
  --   misura il magazzino). La sua UoM base e' la prima attiva del seed, la
  --   stessa che uom_id legge qui sotto.
  (SELECT billing_account_id FROM _m)                                    AS billing_account_id,
  (SELECT utility_id FROM _m)                                            AS utility_id,
  (SELECT istanza_utility_id FROM _m)                                    AS istanza_utility_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-SITUAZ-MERCE', false)              AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA' AND s.attivo LIMIT 1)        AS sorgente_root_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id;

-- Helper: l'ordine (una riga da p_qta a 25, trigger SPEDITO, del 2026-08-15)
-- SENZA bolla, nello stato chiesto (default CONFERMATO), dal builder: serve
-- alle righe mai spedite (A, G, H). Le bolle vengono dal builder della bolla.
CREATE OR REPLACE FUNCTION pg_temp.mk_ordine(p_qta numeric, p_stato text DEFAULT 'CONFERMATO')
RETURNS TABLE(ordine_id bigint, ordine_uid uuid, ordine_riga_id bigint) AS $$
  SELECT o.ordine_id, o.ordine_uid, o.ordine_riga_id
    FROM dbops.fn_pgtap_crea_ordine_con_righe('situazione_ordine', p_stato,
           (SELECT r.billing_account_id FROM tmp_refs r),
           p_quantita => p_qta, p_prezzo => 25, p_articolo_id => (SELECT r.articolo_id FROM tmp_refs r),
           p_fatturazione_trigger => 'SPEDITO', p_data_ordine => DATE '2026-08-15') o
$$ LANGUAGE sql;

-- Le spedizioni: dbops.fn_pgtap_crea_ddt_da_ordine, col cliente del mondo,
-- l'articolo del file, trigger SPEDITO e la causale per codice (VENDITA o
-- CONTO_VISIONE, la non fatturabile), fino a CONSEGNATO.

-- ============================================================
-- A) Riga MAI SPEDITA — test 4 e 5
-- ============================================================
CREATE TEMP TABLE tmp_a AS SELECT * FROM pg_temp.mk_ordine(10);

SELECT results_eq(
  $q$SELECT partite_merce, differenza, stato::text FROM vendite.vw_situazione_merce_ordine
      WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_a)$q$,
  $q$VALUES (0, NULL::numeric, 'NON_SPEDITA')$q$,
  '4) riga mai spedita: c''e'', 0 partite, differenza NULL, stato NON_SPEDITA');

SELECT is(
  (SELECT da_spedire FROM vendite.vw_situazione_merce_ordine
    WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_a)),
  10::numeric, '5) riga mai spedita: da_spedire = tutto l''ordinato');

-- ============================================================
-- B) Tutte le partite NON fatturabili — test 6
--    ⭐ Il ramo che nessun dato attraversa: il contatore grezzo ritirato
--    (`vw_contatore_merce`) qui diceva «10 da fatturare» (tenuti − 0) su un
--    conto visione.
-- ============================================================
CREATE TEMP TABLE tmp_b AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('situazione B',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs), p_quantita => 10,
         p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'SPEDITO',
         p_causale_codice => 'CONTO_VISIONE');

SELECT results_eq(
  $q$SELECT tenuti, differenza, stato::text FROM vendite.vw_situazione_merce_ordine
      WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_b)$q$,
  $q$VALUES (10::numeric, NULL::numeric, 'NON_FATTURABILE')$q$,
  '6) tutte le partite non fatturabili: tenuti 10 ma differenza NULL, non 10');

-- ============================================================
-- C) Partite MISTE — test 7
--    4 su causale fatturabile + 6 su conto visione: il conto e' 4, non 10.
-- ============================================================
CREATE TEMP TABLE tmp_c AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('situazione C',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs), p_quantita => 10,
         p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'SPEDITO',
         p_qta_da_evadere => 4);
SELECT ddt_id FROM dbops.fn_pgtap_crea_ddt_da_ordine('situazione C',
         p_ordine_id => (SELECT ordine_id FROM tmp_c), p_qta_da_evadere => 6,
         p_causale_codice => 'CONTO_VISIONE');

SELECT results_eq(
  $q$SELECT partite_merce, tenuti, differenza FROM vendite.vw_situazione_merce_ordine
      WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_c)$q$,
  $q$VALUES (2, 10::numeric, 4::numeric)$q$,
  '7) partite miste: 2 partite, tenuti 10, ma il conto e'' 4 — solo cio'' che si applica');

-- ============================================================
-- D) ⭐ `da_spedire` dal residuo ESISTENTE — test 8
--    Ordine 10, spediti tutti e 10, poi 3 tornati indietro PER RI-CONSEGNA e
--    non ancora rispediti. L'ordine deve ancora 3.
--    ⚠️ `GREATEST(0, ordinato − consegnato)` darebbe 10 − 10 = 0: e' la
--    divergenza misurata sulla riga d'ordine reale 18946.
-- ============================================================
CREATE TEMP TABLE tmp_d AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('situazione D',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs), p_quantita => 10,
         p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'SPEDITO');
-- Il reso per ri-consegna di 3, confermato, sulla bolla di tmp_d: dal builder.
CREATE TEMP TABLE tmp_d_reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('situazione D', (SELECT ddt_id FROM tmp_d), 3, 'RESO_PER_RICONSEGNA',
         p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_d),
         p_ordine_riga_id => (SELECT ordine_riga_id FROM tmp_d));

SELECT results_eq(
  $q$SELECT ordinato, consegnato, da_spedire FROM vendite.vw_situazione_merce_ordine
      WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_d)$q$,
  $q$VALUES (10::numeric, 10::numeric, 3::numeric)$q$,
  '8) evaso = ordinato ma 3 tornati per ri-consegna: da_spedire 3, non 0 (residuo esistente)');

-- ============================================================
-- E) La RI-CONSEGNA emessa — test 9
--    I 3 pezzi rispediti tornano nel consegnato dell'ORIGINE, non aprono una
--    partita nuova, e il residuo si chiude.
-- ============================================================
CREATE TEMP TABLE tmp_e AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_riconsegna((SELECT reso_id FROM tmp_d_reso));

SELECT results_eq(
  $q$SELECT partite_merce, consegnato, da_spedire FROM vendite.vw_situazione_merce_ordine
      WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_d)$q$,
  $q$VALUES (1, 13::numeric, 0::numeric)$q$,
  '9) ri-consegna emessa: UNA partita (non due), consegnato 13, da_spedire 0');

-- ============================================================
-- F) Kit senza coefficiente sulla corsia ORD — test 10
--    Il conto non si sa fare: si dichiara, non si mette a zero.
-- ============================================================
CREATE TEMP TABLE tmp_f AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('situazione F',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs), p_quantita => 5,
         p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'SPEDITO');
CREATE TEMP TABLE tmp_com AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa => 'AUTO', p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false, p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-08-01', p_competenza_al => DATE '2026-08-31',
  p_meta => jsonb_build_object('test_scope','pgtap_situazione_ordine'), p_force_new => true
) AS commessa_id;
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_com),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs),
  p_sorgente_uid => (SELECT commessa_id FROM tmp_com)::text,
  p_sorgente_riga => 1, p_meta => '{}'::jsonb);
-- Componente di kit SENZA `coeff_qta`: la quantita' del padre non e' ricostruibile.
DO $mk$
DECLARE r RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_com),
    -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
    p_sorgente_uid => ((SELECT commessa_id FROM tmp_com))::text,
    p_segment_key => 'ORDINE_VENDITA:' || (SELECT ordine_uid FROM tmp_f)::text || ':R:'
                     || (SELECT ordine_riga_id FROM tmp_f)::text || '#CMP:senza-coeff',
    p_articolo_id => r.articolo_id, p_istanza_utility_id => r.istanza_utility_id,
    p_data_attivita => DATE '2026-08-15', p_uom_id => r.uom_id, p_quantita => 5,
    p_competenza_mese => DATE '2026-08-01',
    p_competenza_dal => DATE '2026-08-01', p_competenza_al => DATE '2026-08-31',
    p_prezzo_snapshot => 10.0, p_prezzo_base_snapshot => NULL, p_origine_prezzo => NULL,
    p_tipo_variazione_applicata => NULL, p_valore_variazione_applicata => NULL,
    p_promo_id => NULL, p_contratto_id => NULL,
    p_categoria_cliente_id_snapshot => NULL, p_classe_utenza_id_snapshot => NULL,
    p_tipo_doc_fiscale_id => r.tipo_doc_fiscale_id,
    p_stato_approvazione => 'APPROVATA', p_stato_emissione => 'NON_EMESSA',
    p_tipo_movimento => 'NORMALE', 
    p_meta => '{}'::jsonb, p_causale_onere_id => NULL);
END $mk$;
SELECT vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM tmp_com), 'PRONTA_FATTURAZIONE');
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com));

SELECT results_eq(
  $q$SELECT misurabile, differenza, stato::text FROM vendite.vw_situazione_merce_ordine
      WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_f)$q$,
  $q$VALUES (false, NULL::numeric, 'NON_MISURABILE')$q$,
  '10) kit senza coeff_qta: misurabile false e differenza NULL, non un numero');

-- ============================================================
-- 11) Scope ristretto: la riga SPARISCE, non esce a zero.
--     ⚠️ Il cancello e' `app.ruolo_applicativo`: con la veste OPERATORE e un
--     utente senza whitelist, la RLS su `ordini` non fa vedere il documento.
--     Se un giorno la vista uscisse con dei conti a zero invece che con
--     l'assenza, questo test lo direbbe — ed e' la differenza fra «non c'e'
--     nulla da fare» e «non ho il permesso di saperlo».
-- ============================================================
SELECT set_config('app.current_user_id', '999999999', true);

SELECT is(
  (SELECT COUNT(*)::int FROM vendite.vw_situazione_merce_ordine
    WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_d)),
  0,
  '11) scope che non vede l''ordine: la riga sparisce, non esce con dei conti a zero (rosso da owner, che salta la RLS; verde come app)');


-- ============================================================
-- ⭐ LA SOGLIA DELL'IMPEGNO — test 12..17 (changeSet 20260818-06)
--
--    ⚠️ Il test 11 ha ristretto lo scope apposta. Da qui in poi serve di
--    nuovo l'utente che vede i documenti, altrimenti i test sotto sarebbero
--    verdi per sottrazione — che e' esattamente il difetto che il file
--    combatte in tre punti.
-- ============================================================
-- ⛔ rev 2026-10-13: si torna all'operatore del mondo costruito, non all'utente 1.
SELECT set_config('app.current_user_id', (SELECT auth_user_id FROM _m)::text, true);

-- ============================================================
-- G) Ordine in BOZZA — test 12
--    Prima della soglia questa riga diceva «10 da spedire»: nessuno aspetta
--    quei 10, l'ordine non e' ancora stato confermato.
--    ⚠️ La riga deve ESSERCI: il pannello e' per ordine.
-- ============================================================
CREATE TEMP TABLE tmp_g AS SELECT * FROM pg_temp.mk_ordine(10, 'DRAFT');

SELECT results_eq(
  $q$SELECT ordinato, partite_merce, da_spedire, differenza, stato::text
       FROM vendite.vw_situazione_merce_ordine
      WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_g)$q$,
  $q$VALUES (10::numeric, 0, NULL::numeric, NULL::numeric, 'NON_IMPEGNATA')$q$,
  '12) ordine in bozza: la riga c''e'' con il suo ordinato, ma da_spedire NULL e NON_IMPEGNATA');

-- ============================================================
-- H) Ordine ANNULLATO mai spedito — test 13
--    Confermato -> mai spedito -> annullato: il percorso REALE, e l'unico che
--    porta un ordine abortito ad avere righe attive (l'annullamento non
--    disattiva le righe).
--    🔴 Prima della soglia questa riga avrebbe detto «7 da spedire» PER
--    SEMPRE: nessuna azione avrebbe potuto azzerarla.
-- ============================================================
CREATE TEMP TABLE tmp_h AS SELECT * FROM pg_temp.mk_ordine(7);
-- rev 2026-10-25 (giro 7): l'annullo dal verbo d'annullo (la porta ferma
--   l'UPDATE diretto); l'annullo di un confermato chiede emetti_ordine.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'emetti_ordine');
SELECT vendite.fn_annulla_ordine((SELECT ordine_id FROM tmp_h));

SELECT results_eq(
  $q$SELECT ordinato, partite_merce, da_spedire, stato::text
       FROM vendite.vw_situazione_merce_ordine
      WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_h)$q$,
  $q$VALUES (7::numeric, 0, NULL::numeric, 'NON_IMPEGNATA')$q$,
  '13) ordine annullato mai spedito: da_spedire NULL, non «7 da spedire» per sempre');

-- ============================================================
-- I) La PORTA — test 14
--    ⭐ Questo test NON guarda la vista. Guarda il motivo per cui il ramo
--    «ordine abortito CON partite» non e' raggiungibile: finche' esiste un
--    DDT figlio VIVO l'ordine non si annulla, e la D1 esclude i DDT abortiti
--    dalle partite. Quindi abortito => zero partite.
--    La precedenza data alle partite nel CASE della vista resta comunque (e
--    se un domani questa porta si apre, il pannello MOSTRA la merce invece di
--    nasconderla) — ma senza questo test sarebbe una regola non verificata,
--    e una fixture costruita a mano l'avrebbe confermata scavalcando il
--    dominio.
--    tmp_d e' l'ordine del test 8/9: ha due DDT vivi (spedizione + ri-consegna).
-- ============================================================
SELECT ok(
  script.fn_check_ordine_annullabile((SELECT ordine_id FROM tmp_d))
    @> '[{"codice":"E_ORD_ANNULLA_CON_DDT"}]'::jsonb,
  '14) ordine con merce uscita: NON annullabile — e'' la porta che rende irraggiungibile «abortito con partite»');

-- ============================================================
-- L) Coerenza del SEED — test 15
--    ⚠️ Su config.stati_doc_ordini la colonna `ordine` NON e' un ciclo di
--    vita: EVASO 25 sta prima di ALLOCATO 30 e SPEDITO 40. E' un ordinamento
--    di presentazione. La soglia `>= CONFERMATO` regge solo finche' DRAFT
--    resta l'unico stato attivo sotto: se un seed futuro lo cambia, le bozze
--    tornerebbero nel pannello IN SILENZIO. Qui invece fallisce.
-- ============================================================
--    ⚠️ E `ordine` e' NULLABLE: uno stato attivo senza ordinamento finirebbe
--    sotto soglia per COALESCE, cioe' i suoi ordini diventerebbero tutti
--    NON_IMPEGNATA. Si conta anche quello, qui e non a valle.
SELECT is(
  (SELECT COUNT(*)::int
     FROM config.stati_doc_ordini s
    WHERE s.attivo IS TRUE
      AND (s.ordine IS NULL
           OR (s.codice_interno <> 'DRAFT'
               AND s.ordine < (SELECT c.ordine FROM config.stati_doc_ordini c
                                WHERE c.codice_interno = 'CONFERMATO')))),
  0,
  '15) seed: `ordine` sempre valorizzato e DRAFT unico stato attivo sotto la soglia CONFERMATO');

-- ============================================================
-- M) Gli INVARIANTI — test 16 e 17
--    La rete chiesta dal perimetro BE, nella forma che non decade. Non «le 47
--    righe di oggi» — un numero che i dati di sviluppo spostano da soli — ma
--    le due proprieta' che devono valere sempre.
-- ============================================================
SELECT is(
  (SELECT COUNT(*)::int
     FROM vendite.vw_situazione_merce_ordine s
     JOIN vendite.ordini o             ON o.id   = s.ordine_id
     JOIN config.stati_doc_ordini sdo  ON sdo.id = o.stato_doc_ordine_id
    WHERE s.da_spedire IS NOT NULL
      AND (sdo.is_abortito
           OR sdo.ordine < (SELECT c.ordine FROM config.stati_doc_ordini c
                             WHERE c.codice_interno = 'CONFERMATO'))),
  0,
  '16) invariante: nessun arretrato di spedizione dichiarato su ordini in bozza o abortiti');

-- ⭐ E' questo che rende vero «il BE non deve muovere niente»: la soglia
--    cambia i NUMERI di alcune righe, non QUANTE righe tornano.
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.vw_situazione_merce_ordine),
  (SELECT COUNT(*)::int
     FROM vendite.ordini_righe orr
     JOIN vendite.ordini o ON o.id = orr.ordine_id
    WHERE orr.attivo IS TRUE),
  '17) cardinalita'' invariata: una riga per riga d''ordine attiva, anche sotto soglia');

SELECT * FROM finish();
ROLLBACK;
