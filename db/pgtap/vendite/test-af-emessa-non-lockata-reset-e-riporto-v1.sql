-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce un'AZIENDA e un CLIENTE
--   (dbops.fn_pgtap_crea_emittente_operatore + fn_pgtap_crea_cliente_ba), e un
--   operatore dentro un perimetro non puo' crearli: l'INSERT su
--   anagrafiche.billing_account e' un `... RETURNING id`, e la RLS non lascia
--   RILEGGERE una riga il cui legame all'emittente non esiste ancora — lo
--   scrive il trigger z90, cioe' DOPO. Stessa ragione dei sei call-site di
--   quel building block (rls/*-satelliti) e di test-pull-non-prende-trattenuti.
-- pgTAP test per Zero ERP
--
-- Test: l'attivita' EMESSA E NON LOCKATA — la finestra fra il pull (che
--       scrive `emit_batch_id`) e la select (che scrive `lock_batch_id`) —
--       e le due porte che dovevano vederla e non la vedevano:
--       fn_cleanup_fatture_by_ids (dietro «Annulla» e «Riporta a DRAFT») e
--       fn_check_attivita_riportabile_da_emettere (dietro «Riporta da emettere»).
--
-- Elenco test (plan 9) — numerati come li stampa il TAP:
--  0) riferimenti minimi risolti
--  1) dopo il PULL (percorso vero): attivita' col marchio del lotto, senza
--        lucchetto, riga di commessa EMESSA — e' la finestra
--  2) 🔴 in quella finestra, con il lotto IN GIOCO, «Riporta da emettere» la
--        rifiuta come IN LAVORAZIONE (reason ATTIVITA_EMESSA_IN_GIRO_VIVO): non
--        si libera da sotto un giro vivo
--  3) 🔴 «Annulla» il lotto riporta la riga di commessa a NON_EMESSA: l'attivita'
--        emessa-non-lockata e' nel perimetro del reset (terzo ramo del cleanup)
--  4) e l'attivita' e' libera e di nuovo PRONTA per un altro giro
--  5) la DIVERGENZA costruita (riga EMESSA, attivita' libera, marchio di un
--        lotto MORTO) e' RIPORTABILE: nessun motivo
--  6) e «Riporta da emettere» la riallinea: riga NON_EMESSA, 1 riportata
--  7) ⚠️ controprova: attivita' libera E riga NON_EMESSA -> E_ATTIVITA_GIA_DA_EMETTERE
--        (il motivo 3 resta quello che era, dove era vero)
--  8) ⚠️ controprova del reset PER-FATTURA: con p_lock_batch_id NULL il terzo
--        ramo non scatta — l'attivita' emessa resta emessa
--
-- ────────────────────────────────────────────────────────────────
-- 🔴 PERCHE' QUESTO TEST ESISTE — il 13338, 12-09-2026 alle 15:31.
--   Un lotto annullato da Tid aveva lasciato due attivita' col marchio del
--   lotto morto, nessun lucchetto, righe di commessa EMESSE. Il reset libera
--   per `lock_batch_id` — e quelle due un lucchetto non l'avevano mai avuto.
--   «Riporta da emettere» le rifiutava: il check guardava il solo livello AF,
--   che risultava libero (E_ATTIVITA_GIA_DA_EMETTERE). Nessun giro le avrebbe
--   mai riprese: il pull le vede EMESSE, la select di un lotto nuovo non trova
--   il suo marchio. Riparate a mano con fn_libera_attivita_fatturabili.
--   ⛔ I casi si COSTRUISCONO, e la finestra si costruisce col PULL VERO
--   (fn_emit_attivita_fatturabili_da_commessa), non scrivendo le colonne a
--   mano: e' il percorso che il difetto attraversa.
--
-- ChangeSet: 20260912-34 (cleanup), 20260912-35 (check).
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in bozza e si
--   portano avanti con dbops.fn_pgtap_porta_a_stato (prima la commessa nasceva gia' nello
--   stato emittibile, PRONTA_FATTURAZIONE).
-- Brief: brief-db-rilancio-step-non-rivede-le-proprie-commesse.md §10.4
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- Il mondo si costruisce PRIMA di aprire il contesto (vedi P-5).
CREATE TEMP TABLE tmp_ar_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE tmp_ar_cliente AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'af emessa non lockata', NULL, (SELECT soggetto_ruolo_id FROM tmp_ar_mondo));

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM tmp_ar_mondo));
END $ctx$;

SELECT plan(9);

-- ============================================================
-- Fixture: una commessa con una riga, due lotti DRAFT
-- ============================================================
CREATE TEMP TABLE tmp_ar_rif AS
SELECT
  (SELECT m.soggetto_ruolo_id FROM tmp_ar_mondo m)         AS emittente_sr,
  (SELECT c.billing_account_id FROM tmp_ar_cliente c)      AS billing_account_id,
  (SELECT c.utility_id FROM tmp_ar_cliente c)              AS utility_id,
  (SELECT c.istanza_utility_id FROM tmp_ar_cliente c)      AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1) AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)          AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)          AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT sc.id FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE AND sc.emittibile IS TRUE ORDER BY sc.id LIMIT 1) AS stato_ok,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'COMMESSA' AND s.attivo IS TRUE) AS sorgente_id,
  (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DRAFT') AS stato_draft,
  date_trunc('month', script.fn_data_operativa())::date                  AS mese;

SELECT ok(
  (SELECT r.emittente_sr IS NOT NULL AND r.billing_account_id IS NOT NULL
      AND r.articolo_id IS NOT NULL AND r.tipo_doc_fiscale_id IS NOT NULL
      AND r.stato_ok IS NOT NULL AND r.sorgente_id IS NOT NULL AND r.stato_draft IS NOT NULL
     FROM tmp_ar_rif r),
  '0. riferimenti minimi risolti'
);

CREATE TEMP TABLE tmp_ar (commessa_id bigint, ca_id bigint, af_id bigint);
CREATE TEMP TABLE tmp_ar_lotti (caso text, lotto_id bigint, lock_batch_id uuid);

DO $fixture$
DECLARE
    v_rif  record;
    r      record;
    v_comm vendite.commesse.id%TYPE;
    v_ca   vendite.commesse_attivita.id%TYPE;
    v_lot  vendite.fatturazione_lotti.id%TYPE;
    v_lock vendite.fatturazione_lotti.lock_batch_id%TYPE;
BEGIN
    SELECT * INTO v_rif FROM tmp_ar_rif;

    -- rev 2026-10-24: la commessa nasce BOZZA (trigger della nascita); passa allo
    --   stato emittibile DOPO aver preso la riga APPROVATA (il passaggio a
    --   PRONTA_FATTURAZIONE la pretende: fn_check_commessa_pronta_fatturazione).
    INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                  emittente_soggetto_ruolo_id)
    VALUES ('PGTAP-AR-' || substr(md5(clock_timestamp()::text), 1, 6),
            v_rif.billing_account_id, v_rif.utility_id, v_rif.emittente_sr)
    RETURNING id INTO v_comm;

    -- Il pull PRETENDE una sorgente ROOT (vedi P-5 per il perche' della chiave).
    INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
    VALUES (v_comm, v_rif.sorgente_id, v_comm::text, 'ROOT');

    INSERT INTO vendite.commesse_attivita (
        commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
        uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
        tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
        stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
    VALUES (v_comm, 'PGTAP-AR-' || substr(md5(clock_timestamp()::text), 1, 12),
            v_rif.articolo_id, v_rif.istanza_utility_id, v_rif.mese,
            v_rif.uom_id, 1, v_rif.mese, v_rif.mese,
            (v_rif.mese + INTERVAL '1 month - 1 day')::date,
            v_rif.tipo_doc_fiscale_id, v_rif.valuta_id, 10.000000, 'FIXED',
            'APPROVATA', 'NON_EMESSA', -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
            (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'), v_comm::text)
    RETURNING id INTO v_ca;

    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.commesse', v_comm,
        (SELECT sc.codice_interno FROM vendite.stati_commessa sc WHERE sc.id = v_rif.stato_ok));

    INSERT INTO tmp_ar VALUES (v_comm, v_ca, NULL);

    -- Due lotti DRAFT, in gioco: «primo» fara' il pull e verra' annullato;
    -- «secondo» fara' il pull e poi MORIRA' senza reset (la divergenza).
    FOR r IN SELECT * FROM (VALUES ('primo'), ('secondo')) AS v(caso)
    LOOP
        INSERT INTO vendite.fatturazione_lotti
            (codice, competenza_mese, tipo_doc_fiscale_id,
             emittente_soggetto_ruolo_id, stato_doc_fiscale_id)
        VALUES ('PGTAP-AR-LOTTO-' || upper(r.caso), v_rif.mese,
                v_rif.tipo_doc_fiscale_id, v_rif.emittente_sr, v_rif.stato_draft)
        RETURNING id, lock_batch_id INTO v_lot, v_lock;
        INSERT INTO tmp_ar_lotti VALUES (r.caso, v_lot, v_lock);
    END LOOP;
END;
$fixture$;

-- ============================================================
-- 1) Il PULL vero, col marchio del primo lotto: la finestra
-- ============================================================
-- ⛔ Non si scrivono le colonne a mano: e' fn_emit_attivita_fatturabili_da_commessa
--   a marcare `emit_batch_id` e a portare la riga a EMESSA. La select — che
--   scriverebbe `lock_batch_id` — qui NON gira: e' esattamente la finestra.
SELECT (vendite.fn_emit_attivita_fatturabili_da_commessa(
            p_commessa_id   => (SELECT commessa_id FROM tmp_ar),
            p_emit_batch_id => (SELECT lock_batch_id FROM tmp_ar_lotti WHERE caso = 'primo'))).inserted_rows;

UPDATE tmp_ar t
   SET af_id = (SELECT af.id FROM vendite.attivita_fatturabili af
                 WHERE af.commessa_attivita_id = t.ca_id);

SELECT is(
    (SELECT (af.emit_batch_id = (SELECT lock_batch_id FROM tmp_ar_lotti WHERE caso = 'primo'))::text
            || '/' || (af.lock_batch_id IS NULL)::text
            || '/' || ca.stato_emissione::text
       FROM vendite.attivita_fatturabili af
       JOIN vendite.commesse_attivita ca ON ca.id = af.commessa_attivita_id
      WHERE af.id = (SELECT af_id FROM tmp_ar)),
    'true/true/EMESSA',
    '1. dopo il pull: marchio del lotto, nessun lucchetto, riga EMESSA — la finestra fra pull e select'
);

-- ============================================================
-- 2) 🔴 In transito dentro un giro VIVO: non si riporta
-- ============================================================
SELECT is(
    (SELECT m ->> 'codice' || '/' || (m ->> 'reason')
       FROM script.fn_check_attivita_riportabile_da_emettere(ARRAY[(SELECT af_id FROM tmp_ar)]) AS v,
            LATERAL jsonb_array_elements(v) AS m
      ORDER BY 1 LIMIT 1),
    'E_ATTIVITA_IN_LAVORAZIONE/ATTIVITA_EMESSA_IN_GIRO_VIVO',
    '2. emessa e non lockata dentro un lotto IN GIOCO: «Riporta da emettere» la rifiuta come in lavorazione'
);

-- ============================================================
-- 3-4) 🔴 «Annulla» il lotto riprende anche l'attivita' emessa-non-lockata
-- ============================================================
SELECT vendite.fn_annulla_lotto_da_draft((SELECT lotto_id FROM tmp_ar_lotti WHERE caso = 'primo'));

SELECT is(
    (SELECT ca.stato_emissione::text FROM vendite.commesse_attivita ca
      WHERE ca.id = (SELECT ca_id FROM tmp_ar)),
    'NON_EMESSA',
    '3. annullato il lotto, la riga di commessa torna NON_EMESSA: il terzo ramo del cleanup la vede'
);

SELECT is(
    (SELECT (af.lock_batch_id IS NULL AND COALESCE(af.lock_in_fatturazione, false) IS FALSE)::text
            || '/' || e.classe_emittibilita::text
       FROM vendite.attivita_fatturabili af
       JOIN vendite.vw_commesse_attivita_emittibilita e ON e.commessa_attivita_id = af.commessa_attivita_id
      WHERE af.id = (SELECT af_id FROM tmp_ar)),
    'true/PRONTA',
    '4. e l''attivita'' e'' libera e di nuovo PRONTA per un altro giro'
);

-- ============================================================
-- 5-6) La DIVERGENZA: riga EMESSA, attivita' libera, lotto MORTO
-- ============================================================
-- Il secondo lotto fa il pull (la riga torna EMESSA, il marchio e' il suo),
-- poi il lotto MUORE senza passare dal reset: e' lo stato del 13338 delle
-- 15:31, quello che il cleanup di prima lasciava e che ora costruiamo apposta
-- perche' il check lo riconosca.
SELECT (vendite.fn_emit_attivita_fatturabili_da_commessa(
            p_commessa_id   => (SELECT commessa_id FROM tmp_ar),
            p_emit_batch_id => (SELECT lock_batch_id FROM tmp_ar_lotti WHERE caso = 'secondo'))).updated_rows;

UPDATE vendite.fatturazione_lotti
   SET stato_doc_fiscale_id = (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'ANNULLATA')
 WHERE id = (SELECT lotto_id FROM tmp_ar_lotti WHERE caso = 'secondo');

SELECT is(
    (SELECT jsonb_array_length(script.fn_check_attivita_riportabile_da_emettere(ARRAY[(SELECT af_id FROM tmp_ar)]))),
    0,
    '5. riga EMESSA + attivita'' libera + marchio di un lotto MORTO: nessun motivo, e'' riportabile'
);

-- ⚠️ Il verbo in un'istruzione SEPARATA dalla rilettura: nella stessa SELECT
--   la sotto-query leggerebbe la snapshot di PRIMA dell'UPDATE e direbbe
--   EMESSA anche a verbo riuscito (trovato alla prima corsa di questo file).
CREATE TEMP TABLE tmp_ar_riporto AS
SELECT * FROM vendite.fn_riporta_attivita_da_emettere(ARRAY[(SELECT af_id FROM tmp_ar)]);

SELECT is(
    (SELECT r.riportate::text || '/' || r.riemesse_attivita::text FROM tmp_ar_riporto r)
      || '/' ||
    (SELECT ca.stato_emissione::text FROM vendite.commesse_attivita ca WHERE ca.id = (SELECT ca_id FROM tmp_ar)),
    '1/1/NON_EMESSA',
    '6. «Riporta da emettere» riallinea i due livelli: 1 riportata, 1 riemessa, riga NON_EMESSA'
);

-- ============================================================
-- 7) ⚠️ Controprova: libera E gia' NON_EMESSA -> «gia' da emettere»
-- ============================================================
SELECT is(
    (SELECT m ->> 'codice'
       FROM script.fn_check_attivita_riportabile_da_emettere(ARRAY[(SELECT af_id FROM tmp_ar)]) AS v,
            LATERAL jsonb_array_elements(v) AS m
      ORDER BY 1 LIMIT 1),
    'E_ATTIVITA_GIA_DA_EMETTERE',
    '7. controprova: attivita'' libera e riga gia'' NON_EMESSA -> E_ATTIVITA_GIA_DA_EMETTERE (il motivo 3 resta dove era vero)'
);

-- ============================================================
-- 8) ⚠️ Controprova del reset PER-FATTURA: p_lock_batch_id NULL non tocca il terzo ramo
-- ============================================================
-- Pull di nuovo col marchio del secondo lotto (morto, ma il marchio e' un
-- uuid come un altro), poi il cleanup nella forma per-fattura (C-22): senza
-- marchio del giro il terzo ramo non scatta e l'attivita' resta emessa.
SELECT (vendite.fn_emit_attivita_fatturabili_da_commessa(
            p_commessa_id   => (SELECT commessa_id FROM tmp_ar),
            p_emit_batch_id => (SELECT lock_batch_id FROM tmp_ar_lotti WHERE caso = 'secondo'))).updated_rows;

SELECT vendite.fn_cleanup_fatture_by_ids(ARRAY[]::bigint[], NULL::uuid);

SELECT is(
    (SELECT ca.stato_emissione::text FROM vendite.commesse_attivita ca
      WHERE ca.id = (SELECT ca_id FROM tmp_ar)),
    'EMESSA',
    '8. controprova: il reset per-fattura (p_lock_batch_id NULL) non libera un''attivita'' emessa — il terzo ramo vale solo col marchio del giro'
);

SELECT * FROM finish();

ROLLBACK;
