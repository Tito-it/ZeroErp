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
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): le tre commesse le costruisce
--   dbops.fn_pgtap_crea_commessa sul billing account del test, ognuna con UNA riga
--   APPROVATA: PRONTA_FATTURAZIONE per quelle emittibili, BOZZA (con la riga chiesta,
--   p_con_attivita => true) per la testata no. Prima testata e riga erano scritte a mano
--   con articolo, unita' di misura e tipo documento pescati «il primo per id», e lo stato
--   «no» era «il primo non emittibile per id». Il tipo documento del lotto si legge dalla
--   riga scritta; il test 0 conta le righe costruite al posto dell'articolo pescato.
-- rev 2026-10-24 (brief-modello-documento-vendita R-4): il lotto DRAFT e l'esito ERRORE
--   E_PULL_COMMESSA che trattiene il gruppo «trattenuto» nascono da dbops.fn_pgtap_crea_lotto
--   (madre vendite.fn_create_fatturazione_lotto, tipo documento della riga, cliente del
--   test, p_gruppo_key_trattenuto); prima lotto ed esito erano INSERT a mano. Le
--   asserzioni non leggono codice ne' utility del lotto.
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
-- Gli stati per codice_interno: la testata emittibile e quella in BOZZA.
CREATE TEMP TABLE tmp_sp_stati AS
SELECT 'PRONTA_FATTURAZIONE'::varchar AS stato_ok, 'BOZZA'::varchar AS stato_ko;

CREATE TEMP TABLE tmp_sp (caso text, commessa_id bigint, gruppo_key text, attivita_id bigint);

DO $fixture$
DECLARE
    r      record;
    v_comm vendite.commesse.id%TYPE;
    v_ca   vendite.commesse_attivita.id%TYPE;
BEGIN
    FOR r IN
        SELECT * FROM (VALUES
            ('coperto',    true),   -- riga pronta, testata emittibile
            ('testata_ko', false),  -- riga pronta, testata NO
            ('trattenuto', true)    -- riga pronta, ma un lotto la tiene
        ) AS v(caso, testata_ok)
    LOOP
        -- Il builder: testata dalla madre, UNA riga APPROVATA, lo stato per la
        --   matrice. In BOZZA la riga la si chiede (p_con_attivita => true).
        SELECT c.commessa_id, c.attivita_id INTO v_comm, v_ca
          FROM dbops.fn_pgtap_crea_commessa(
                   'specchio lane ' || r.caso,
                   (SELECT CASE WHEN r.testata_ok THEN st.stato_ok ELSE st.stato_ko END
                      FROM tmp_sp_stati st),
                   (SELECT billing_account_id FROM tmp_sp_cliente),
                   true) c;

        INSERT INTO tmp_sp VALUES (r.caso, v_comm,
            vendite.fn_build_gruppo_fatturabile_key(
                (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'), v_comm::text, v_comm),
            v_ca);
    END LOOP;
END;
$fixture$;

CREATE TEMP TABLE tmp_sp_rif AS
SELECT
  (SELECT m.soggetto_ruolo_id FROM tmp_sp_mondo m)         AS emittente_sr,
  (SELECT c.billing_account_id FROM tmp_sp_cliente c)      AS billing_account_id,
  -- il tipo documento del lotto e' quello della riga scritta, non un pescato
  (SELECT ca.tipo_doc_fiscale_id FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT t.attivita_id FROM tmp_sp t WHERE t.caso = 'trattenuto')) AS tipo_doc_fiscale_id,
  (SELECT sc.emittibile FROM vendite.stati_commessa sc, tmp_sp_stati st
    WHERE sc.codice_interno = st.stato_ok AND sc.attivo IS TRUE)          AS stato_ok_emittibile,
  (SELECT sc.emittibile FROM vendite.stati_commessa sc, tmp_sp_stati st
    WHERE sc.codice_interno = st.stato_ko AND sc.attivo IS TRUE)          AS stato_ko_emittibile,
  -- le righe costruite: una APPROVATA/NON_EMESSA per commessa, nello stato chiesto
  (SELECT count(*) FROM tmp_sp t
     JOIN vendite.commesse_attivita ca ON ca.id = t.attivita_id AND ca.commessa_id = t.commessa_id
     JOIN vendite.commesse c ON c.id = t.commessa_id
     JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id
     CROSS JOIN tmp_sp_stati st
    WHERE ca.stato_approvazione = 'APPROVATA' AND ca.stato_emissione = 'NON_EMESSA'
      AND sc.codice_interno = CASE WHEN t.caso = 'testata_ko' THEN st.stato_ko ELSE st.stato_ok END)
                                                           AS n_costruite,
  date_trunc('month', script.fn_data_operativa())::date                  AS mese;

SELECT ok(
  (SELECT r.emittente_sr IS NOT NULL AND r.billing_account_id IS NOT NULL
      AND r.tipo_doc_fiscale_id IS NOT NULL
      AND r.stato_ok_emittibile IS TRUE AND r.stato_ko_emittibile IS FALSE
      AND r.n_costruite = 3
     FROM tmp_sp_rif r),
  '0. riferimenti minimi risolti (emittente, anagrafiche, tre commesse costruite, due stati commessa)'
);

-- Il lotto DRAFT che trattiene il gruppo «trattenuto»: il builder scrive anche
--   l'esito ERRORE E_PULL_COMMESSA.
CREATE TEMP TABLE tmp_sp_lotto AS
SELECT l.*
  FROM tmp_sp_rif r,
       LATERAL dbops.fn_pgtap_crea_lotto(
           'specchio lane', 'DRAFT', r.billing_account_id,
           p_tipo_doc_fiscale_id   => r.tipo_doc_fiscale_id,
           p_competenza_mese       => r.mese,
           p_gruppo_key_trattenuto => (SELECT t.gruppo_key FROM tmp_sp t WHERE t.caso = 'trattenuto')) l;

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
