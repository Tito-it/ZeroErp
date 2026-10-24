-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce un'AZIENDA e un CLIENTE
--   (dbops.fn_pgtap_crea_emittente_operatore + fn_pgtap_crea_cliente_ba), e un
--   operatore dentro un perimetro non puo' crearli: l'INSERT su
--   anagrafiche.billing_account e' un `... RETURNING id`, e la RLS non lascia
--   RILEGGERE una riga il cui legame all'emittente non esiste ancora — lo
--   scrive il trigger z90, cioe' DOPO. E' la stessa ragione per cui girano da
--   owner tutti e sei i call-site di quel building block (rls/*-satelliti).
-- pgTAP test per Zero ERP
--
-- Test: P-8 — LO SPECCHIO. `fn_list_emittibili_lane` e
--       `fn_diagnostica_gruppi_fatturabili` devono parlare delle STESSE righe.
--
-- Elenco test (plan 4) — numerati come li stampa il TAP:
--  0) riferimenti minimi risolti
--  1) ⭐⭐ i gruppi che la LANE copre sono esattamente quelli che la
--        DIAGNOSTICA conta pronti (col fattore di testata applicato)
--  2) ⛔ e il fattore di TESTATA e' reale: un gruppo con la commessa in BOZZA
--        e' pronto per la diagnostica e NON coperto dalla lane
--  3) 🔴 un gruppo TRATTENUTO non e' coperto dalla lane E non e' fra i pronti:
--        e' in `n_trattenute`, col lotto che lo tiene
--
-- ────────────────────────────────────────────────────────────────
-- 🔴 PERCHE' QUESTO FILE ESISTE, ed e' il presidio che mancava.
--   `fn_diagnostica_gruppi_fatturabili` e' dichiarata nel proprio manuale
--   «lo specchio di fn_list_emittibili_lane: i criteri che questa fotografia
--   conta uno per uno». Esisteva uno specchio DICHIARATO e NIENTE che
--   verificasse che fosse ancora tale.
--   ⛔ Il 2026-09-09 il changeSet -25 ha aggiunto un criterio alla lane — il
--   trattenuto — e non allo specchio. Da li':
--     · la lane non offriva il gruppo   -> il giro non lo serviva
--     · il backend chiedeva alla diagnostica PERCHE'
--     · la diagnostica rispondeva «n_pronte = 1», cioe' «era pronto»
--   e l'operatore leggeva «verificare emittente e utility della commessa» —
--   due cose giuste da controllare, e non una parola sull'unica che contava.
--   ⭐ Con questo test in casa, quel giorno sarebbe stato ROSSO.
--
-- ⭐ IL TEST 2 NON E' UN DETTAGLIO: e' la differenza VOLUTA fra i due.
--   La lane pretende DUE fattori (riga PRONTA + testata emittibile); la
--   diagnostica tiene il secondo separato, per poter dire «le righe sarebbero
--   pronte, e' la commessa a essere in BOZZA» — la sola cosa che sa dire
--   meglio della lane. Senza questo test, qualcuno «allineerebbe» i due
--   oggetti fondendo il fattore nella classe, e la diagnosi perderebbe la sua
--   ragione di esistere.
--
-- ⚠️ Il perimetro si restringe con `p_gruppi`: cosi' il confronto guarda le
--   sole righe COSTRUITE qui, e non dipende da cosa c'e' nel database.
--
-- ChangeSet: 20260909-59 · -60 · -63
-- Brief: brief-db-il-trattenuto-passa-lo-stesso.md (L3, §9.2)
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in bozza e si
--   portano avanti con dbops.fn_pgtap_porta_a_stato (prima le commesse nascevano gia'
--   in stato_ok / stato_ko).
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- ⭐ L'AZIENDA, L'OPERATORE E IL CLIENTE SI COSTRUISCONO (rev 2026-09-09).
--   Prima l'emittente si CERCAVA (`fn_pgtap_emittente_sr_operatore`) e il
--   billing account pure (`ORDER BY b.id LIMIT 1`). Su un database ricostruito
--   dai changelog — cioe' in CI — `anagrafiche` e' vuoto: sono seed di
--   `dati_macchina`. ⇒ Il file sollevava «Nessun emittente fiscale attivo» e
--   non eseguiva NEMMENO UNA asserzione — cioe' il presidio che secondo la sua
--   stessa intestazione «quel giorno sarebbe stato ROSSO» era muto proprio
--   dove gira la CI.
-- ⛔ Il mondo si costruisce PRIMA di aprire il contesto: dopo, il legame
--   BA→emittente lo scriverebbe anche `trg_billing_account_z90_link_ef_ins` e
--   i due si scontrerebbero su `uq_emittenti_fiscali_ba`.
CREATE TEMP TABLE tmp_sp_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE tmp_sp_cliente AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'specchio lane', NULL, (SELECT soggetto_ruolo_id FROM tmp_sp_mondo));

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM tmp_sp_mondo));
END $ctx$;

SELECT plan(4);

-- ============================================================
-- Fixture — tre gruppi, tre situazioni
-- ============================================================
CREATE TEMP TABLE tmp_sp_rif AS
SELECT
  (SELECT m.soggetto_ruolo_id FROM tmp_sp_mondo m)         AS emittente_sr,
  (SELECT c.billing_account_id FROM tmp_sp_cliente c)      AS billing_account_id,
  (SELECT c.utility_id FROM tmp_sp_cliente c)              AS utility_id,
  (SELECT c.istanza_utility_id FROM tmp_sp_cliente c)      AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1) AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)          AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)          AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT sc.id FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE AND sc.emittibile IS TRUE ORDER BY sc.id LIMIT 1)  AS stato_ok,
  (SELECT sc.id FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE AND sc.emittibile IS FALSE
      AND sc.codice_interno <> 'ANNULLATA' ORDER BY sc.id LIMIT 1)            AS stato_ko,
  date_trunc('month', script.fn_data_operativa())::date                  AS mese;

SELECT ok(
  (SELECT r.emittente_sr IS NOT NULL AND r.billing_account_id IS NOT NULL
      AND r.articolo_id IS NOT NULL AND r.stato_ok IS NOT NULL
      AND r.stato_ko IS NOT NULL
     FROM tmp_sp_rif r),
  '0. riferimenti minimi risolti (emittente, anagrafiche, catalogo, due stati commessa)'
);

CREATE TEMP TABLE tmp_sp (caso text, commessa_id bigint, gruppo_key text);

DO $fixture$
DECLARE
    v_rif  record;
    r      record;
    v_comm vendite.commesse.id%TYPE;
    v_lot  vendite.fatturazione_lotti.id%TYPE;
BEGIN
    SELECT * INTO v_rif FROM tmp_sp_rif;

    FOR r IN
        SELECT * FROM (VALUES
            ('coperto',    true),   -- riga pronta, testata emittibile
            ('testata_ko', false),  -- riga pronta, testata NO
            ('trattenuto', true)    -- riga pronta, ma un lotto la tiene
        ) AS v(caso, testata_ok)
    LOOP
        -- rev 2026-10-24: la commessa nasce BOZZA (trigger della nascita) e passa
        --   allo stato voluto (stato_ok / stato_ko) DOPO la sua riga APPROVATA,
        --   che il passaggio a PRONTA_FATTURAZIONE pretende.
        INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                      emittente_soggetto_ruolo_id)
        VALUES ('PGTAP-SP-' || upper(r.caso) || '-'
                            || substr(md5(clock_timestamp()::text), 1, 6),
                v_rif.billing_account_id, v_rif.utility_id, v_rif.emittente_sr)
        RETURNING id INTO v_comm;

        INSERT INTO vendite.commesse_attivita (
            commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
            uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
            tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
            stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
        VALUES (v_comm,
                'PGTAP-SP-' || r.caso || '-' || substr(md5(clock_timestamp()::text), 1, 12),
                v_rif.articolo_id, v_rif.istanza_utility_id, v_rif.mese,
                v_rif.uom_id, 1, v_rif.mese, v_rif.mese,
                (v_rif.mese + INTERVAL '1 month - 1 day')::date,
                v_rif.tipo_doc_fiscale_id, v_rif.valuta_id, 10.000000, 'FIXED',
                'APPROVATA', 'NON_EMESSA', -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
                (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'), v_comm::text);

        PERFORM dbops.fn_pgtap_porta_a_stato('vendite.commesse', v_comm,
            (SELECT sc.codice_interno FROM vendite.stati_commessa sc
              WHERE sc.id = CASE WHEN r.testata_ok THEN v_rif.stato_ok ELSE v_rif.stato_ko END));

        INSERT INTO tmp_sp VALUES (r.caso, v_comm,
            vendite.fn_build_gruppo_fatturabile_key(
                (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'), v_comm::text, v_comm));
    END LOOP;

    INSERT INTO vendite.fatturazione_lotti
        (codice, competenza_mese, tipo_doc_fiscale_id,
         emittente_soggetto_ruolo_id, stato_doc_fiscale_id)
    VALUES ('PGTAP-SP-LOTTO', v_rif.mese, v_rif.tipo_doc_fiscale_id, v_rif.emittente_sr,
            (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DRAFT'))
    RETURNING id INTO v_lot;

    INSERT INTO vendite.fatturazione_lotti_esiti
        (lotto_id, gruppo_key, stato_esecuzione, errore_codice, errore_messaggio)
    SELECT v_lot, t.gruppo_key, 'ERRORE', 'E_PULL_COMMESSA', 'rotto per la prova'
      FROM tmp_sp t WHERE t.caso = 'trattenuto';
END;
$fixture$;

-- Le due letture, sullo STESSO perimetro.
CREATE TEMP TABLE tmp_sp_lane AS
  SELECT DISTINCT unnest(l.gruppi_coperti) AS gruppo_key
    FROM vendite.fn_list_emittibili_lane(
           p_competenza_mese => (SELECT mese FROM tmp_sp_rif),
           p_gruppi          => (SELECT array_agg(gruppo_key) FROM tmp_sp)) l;

CREATE TEMP TABLE tmp_sp_diag AS
  SELECT d.*
    FROM vendite.fn_diagnostica_gruppi_fatturabili(
           (SELECT array_agg(gruppo_key) FROM tmp_sp),
           (SELECT mese FROM tmp_sp_rif)) d;

-- ============================================================
-- 1) ⭐⭐ LO SPECCHIO: le due letture parlano delle stesse righe
-- ============================================================
-- ⭐ L'equivalenza e' fra: i gruppi che la lane COPRE, e i gruppi che la
--   diagnostica conta PRONTI **col fattore di testata applicato**. I due
--   fattori sono dichiarati da entrambe le parti, quindi il confronto e'
--   possibile — ed e' proprio cio' che prima non lo era.
SELECT results_eq(
    $$ SELECT (SELECT count(*)::int FROM (
                 SELECT gruppo_key FROM tmp_sp_lane
                 EXCEPT
                 SELECT gruppo_key FROM tmp_sp_diag
                  WHERE n_pronte > 0 AND commessa_emittibile) a) AS solo_lane,
              (SELECT count(*)::int FROM (
                 SELECT gruppo_key FROM tmp_sp_diag
                  WHERE n_pronte > 0 AND commessa_emittibile
                 EXCEPT
                 SELECT gruppo_key FROM tmp_sp_lane) b) AS solo_diagnostica $$,
    $$ VALUES (0, 0) $$,
    '1. lo SPECCHIO: i gruppi coperti dalla lane sono esattamente quelli contati pronti dalla diagnostica'
);

-- ============================================================
-- 2) ⛔ Il fattore di TESTATA e' reale, e solo la lane lo applica
-- ============================================================
-- ⭐ E' la differenza VOLUTA: senza, la diagnostica non potrebbe dire «le
--   righe sarebbero pronte, e' la commessa a essere in BOZZA».
-- ⚠️ Se un giorno qualcuno fondesse `commessa_emittibile` dentro la classe,
--   questo test diventa rosso — ed e' il suo mestiere.
SELECT results_eq(
    $$ SELECT (SELECT n_pronte FROM tmp_sp_diag
                WHERE gruppo_key = (SELECT gruppo_key FROM tmp_sp WHERE caso = 'testata_ko')),
              (SELECT commessa_emittibile FROM tmp_sp_diag
                WHERE gruppo_key = (SELECT gruppo_key FROM tmp_sp WHERE caso = 'testata_ko')),
              EXISTS (SELECT 1 FROM tmp_sp_lane
                       WHERE gruppo_key = (SELECT gruppo_key FROM tmp_sp WHERE caso = 'testata_ko')) $$,
    $$ VALUES (1::bigint, false, false) $$,
    '2. testata in BOZZA: la diagnostica lo conta PRONTO, la lane non lo copre — la differenza e'' voluta e dichiarata'
);

-- ============================================================
-- 3) 🔴 Il trattenuto: fuori da entrambe, e con il suo perche'
-- ============================================================
-- ⛔ E' il caso che il 2026-09-09 rispondeva «era pronto». Adesso esce da
--   n_pronte, entra in n_trattenute, e `lotti_trattenenti` NOMINA il lotto —
--   senza il quale «trattenuto» non e' azionabile.
SELECT results_eq(
    $$ SELECT d.n_pronte, d.n_trattenute,
              jsonb_array_length(d.lotti_trattenenti),
              EXISTS (SELECT 1 FROM tmp_sp_lane l WHERE l.gruppo_key = d.gruppo_key)
         FROM tmp_sp_diag d
        WHERE d.gruppo_key = (SELECT gruppo_key FROM tmp_sp WHERE caso = 'trattenuto') $$,
    $$ VALUES (0::bigint, 1::bigint, 1, false) $$,
    '3. il trattenuto: fuori dai pronti, fuori dalla lane, dentro n_trattenute e col lotto nominato'
);

SELECT * FROM finish();

ROLLBACK;
