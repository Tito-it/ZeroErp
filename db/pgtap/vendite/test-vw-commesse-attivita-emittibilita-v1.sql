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
-- Test: vendite.vw_commesse_attivita_emittibilita — la SEDE UNICA del criterio
--       «questa riga di commessa puo' entrare in un giro di fatturazione,
--       e se no perche'?».
--
-- Elenco test (plan 9) — numerati come li stampa il TAP:
--  0) riferimenti minimi risolti
--  1) il contratto: la vista espone esattamente le colonne dichiarate
--  2) ⭐ le SEI classi, una riga costruita per forma
--  3) ⛔ la TESTATA non entra nella classe: riga PRONTA su commessa in BOZZA
--        resta PRONTA, e `commessa_emittibile` lo dice a parte
--  4) ⭐ TRATTENUTA: un lotto IN GIOCO sullo stesso mese trattiene
--  5) ⭐ e il verso opposto: un lotto CHIUSO non trattiene
--  6) ⚠️ competenza CUMULATIVA: lotto di settembre, riga di AGOSTO -> trattenuta
--  7) ⚠️ e il contrario: lotto di settembre, riga di OTTOBRE -> PRONTA
--  8) ⚠️ `trattenuta_da_lotti`: NULL se libera, ORDINATO se tenuta da due lotti
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ PERCHE' QUESTA VISTA ESISTE, in una riga: il criterio era scritto DUE
--   volte — `fn_list_emittibili_lane` lo filtrava, `fn_diagnostica_gruppi_-
--   fatturabili` lo contava — e il 2026-09-09 le due sono divergute in
--   silenzio. Ora il criterio non e' scritto in nessuna delle due.
--
-- ⛔ I TEST 3 E' IL PIU' IMPORTANTE, e non sembra. `commessa_emittibile` NON
--   entra nella classe: e' un fattore ORTOGONALE. Fonderlo toglierebbe alla
--   diagnostica la sola cosa che sa dire meglio della lane — «le righe
--   sarebbero pronte, e' la commessa a essere in BOZZA». Prima quella
--   differenza c'era ma era IMPLICITA, cioe' indistinguibile da una svista.
--
-- ⚠️ I TEST 6 E 7 SONO UNA COPPIA, e provano il legame di competenza:
--   `lotto_competenza_mese >= competenza della riga`. Con l'UGUAGLIANZA il
--   test 6 sarebbe rosso; senza legame alcuno lo sarebbe il 7. Servono
--   entrambi, e il verso giusto e' il cumulativo perche' un lotto di
--   settembre lavora anche agosto — non ottobre.
--
-- ⛔ I CASI SI COSTRUISCONO: una commessa per forma, cosi' ogni riga ha la sua
--   `gruppo_key` senza dipendere da nessun documento sorgente. In sviluppo le
--   classi RIFIUTATA e NON_APPROVATA non esistono, e cercarle fra i dati di
--   oggi darebbe due test verdi a vuoto.
--
-- ⭐ E la chiave non si scrive mai a mano: si chiede a
--   vendite.fn_build_gruppo_fatturabile_key, che e' la sola fonte.
--
-- ChangeSet: 20260909-59-create-vw-commesse-attivita-emittibilita
-- Brief: brief-db-il-trattenuto-passa-lo-stesso.md (L3)
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
--   `dati_macchina`, e non esistono ne' emittenti ne' clienti. ⇒ Il file
--   sollevava «Nessun emittente fiscale attivo» e non eseguiva NEMMENO UNA
--   asserzione.
-- ⛔ E contraddiceva la propria intestazione, che dichiara casi costruiti: le
--   undici righe di commessa si', il mondo sotto no.
-- ⚠️ Il terzo argomento LEGA il cliente a questa azienda: senza,
--   `fn_get_emittente_fiscale_pk` ricadrebbe sull'emittente di DEFAULT e i
--   guard di coerenza confronterebbero due aziende diverse.
-- ⛔ IL MONDO SI COSTRUISCE PRIMA DI APRIRE IL CONTESTO. Con il contesto gia'
--   aperto il legame BA→emittente verrebbe scritto DUE volte — una
--   dall'automatismo `trg_billing_account_z90_link_ef_ins`, che guarda
--   l'operatore, e una dal terzo argomento — contro `uq_emittenti_fiscali_ba`,
--   che dice che un BA ha ESATTAMENTE un emittente.
CREATE TEMP TABLE tmp_ce_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE tmp_ce_cliente AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'emittibilita', NULL, (SELECT soggetto_ruolo_id FROM tmp_ce_mondo));

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM tmp_ce_mondo));
END $ctx$;

SELECT plan(9);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_ce_rif AS
SELECT
  (SELECT m.soggetto_ruolo_id FROM tmp_ce_mondo m)             AS emittente_sr,
  (SELECT c.billing_account_id FROM tmp_ce_cliente c)          AS billing_account_id,
  (SELECT c.utility_id FROM tmp_ce_cliente c)                  AS utility_id,
  (SELECT c.istanza_utility_id FROM tmp_ce_cliente c)          AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE
    ORDER BY a.id LIMIT 1)                                     AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)              AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)              AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)     AS valuta_id,
  -- ⭐ Le DUE testate: una emittibile e una no. Servono al test 3, che e' il
  --   punto dell'ortogonalita'.
  (SELECT sc.id FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE AND sc.emittibile IS TRUE
    ORDER BY sc.id LIMIT 1)                                    AS stato_ok,
  (SELECT sc.id FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE AND sc.emittibile IS FALSE
      AND sc.codice_interno <> 'ANNULLATA'
    ORDER BY sc.id LIMIT 1)                                    AS stato_ko,
  date_trunc('month', script.fn_data_operativa())::date                      AS mese;

SELECT ok(
  (SELECT r.emittente_sr IS NOT NULL AND r.billing_account_id IS NOT NULL
      AND r.articolo_id IS NOT NULL AND r.uom_id IS NOT NULL
      AND r.tipo_doc_fiscale_id IS NOT NULL AND r.valuta_id IS NOT NULL
      AND r.stato_ok IS NOT NULL AND r.stato_ko IS NOT NULL
     FROM tmp_ce_rif r),
  '0. riferimenti minimi risolti (emittente, anagrafiche, catalogo, due stati commessa)'
);

-- Un caso = una COMMESSA con UNA riga: cosi' ogni caso ha la sua gruppo_key.
CREATE TEMP TABLE tmp_ce (caso text, commessa_id bigint, ca_id bigint, gruppo_key text);

DO $fixture$
DECLARE
    r          record;
    v_rif      record;
    v_comm     vendite.commesse.id%TYPE;
    v_ca       vendite.commesse_attivita.id%TYPE;
BEGIN
    SELECT * INTO v_rif FROM tmp_ce_rif;

    FOR r IN
        SELECT * FROM (VALUES
            -- caso            emissione     approvazione  testata  offset mese
            ('emessa',        'EMESSA',     'APPROVATA',  true,   0),
            ('annullata',     'ANNULLATA',  'APPROVATA',  true,   0),
            ('rifiutata',     'NON_EMESSA', 'RIFIUTATA',  true,   0),
            ('bozza',         'NON_EMESSA', 'BOZZA',      true,   0),
            ('pronta',        'NON_EMESSA', 'APPROVATA',  true,   0),
            -- ⛔ Il caso del test 3: la RIGA e' pronta, la TESTATA no.
            ('testata_ko',    'NON_EMESSA', 'APPROVATA',  false,  0),
            -- I casi del trattenuto: la riga nasce pronta, poi si attacca un esito.
            ('trattenuta',    'NON_EMESSA', 'APPROVATA',  true,   0),
            ('lotto_chiuso',  'NON_EMESSA', 'APPROVATA',  true,   0),
            ('due_lotti',     'NON_EMESSA', 'APPROVATA',  true,   0),
            -- ⚠️ Competenza: una riga PRIMA del mese del lotto e una DOPO.
            ('mese_prima',    'NON_EMESSA', 'APPROVATA',  true,  -1),
            ('mese_dopo',     'NON_EMESSA', 'APPROVATA',  true,   1)
        ) AS v(caso, emissione, approvazione, testata_ok, off_mese)
    LOOP
        -- rev 2026-10-24: la commessa nasce BOZZA (trigger della nascita) e passa
        --   allo stato voluto con dbops.fn_pgtap_porta_a_stato DOPO la sua riga.
        -- ⚠️ Il passaggio a PRONTA_FATTURAZIONE pretende una riga APPROVATA e
        --   NON_EMESSA (fn_check_commessa_pronta_fatturazione): sulle testate
        --   emittibili la riga nasce pronta e, passata la testata, si porta alla
        --   forma del caso. La forma finale di ogni riga e' quella di prima.
        INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                      emittente_soggetto_ruolo_id)
        VALUES ('PGTAP-CE-' || upper(r.caso) || '-'
                            || substr(md5(clock_timestamp()::text), 1, 6),
                v_rif.billing_account_id, v_rif.utility_id, v_rif.emittente_sr)
        RETURNING id INTO v_comm;

        INSERT INTO vendite.commesse_attivita (
            commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
            uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
            tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
            stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
        VALUES (v_comm,
                'PGTAP-CE-' || r.caso || '-' || substr(md5(clock_timestamp()::text), 1, 12),
                v_rif.articolo_id, v_rif.istanza_utility_id,
                (v_rif.mese + (r.off_mese || ' month')::interval)::date,
                v_rif.uom_id, 1,
                (v_rif.mese + (r.off_mese || ' month')::interval)::date,
                (v_rif.mese + (r.off_mese || ' month')::interval)::date,
                ((v_rif.mese + (r.off_mese || ' month')::interval)
                  + INTERVAL '1 month - 1 day')::date,
                v_rif.tipo_doc_fiscale_id, v_rif.valuta_id, 10.000000, 'FIXED',
                CASE WHEN r.testata_ok THEN 'APPROVATA'  ELSE r.approvazione END,
                CASE WHEN r.testata_ok THEN 'NON_EMESSA' ELSE r.emissione END,
                -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
                (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'), v_comm::text)
        RETURNING id INTO v_ca;

        PERFORM dbops.fn_pgtap_porta_a_stato('vendite.commesse', v_comm,
            (SELECT sc.codice_interno FROM vendite.stati_commessa sc
              WHERE sc.id = CASE WHEN r.testata_ok THEN v_rif.stato_ok ELSE v_rif.stato_ko END));

        IF r.testata_ok AND (r.approvazione, r.emissione) IS DISTINCT FROM ('APPROVATA', 'NON_EMESSA') THEN
            UPDATE vendite.commesse_attivita ca
               SET stato_approvazione = r.approvazione,
                   stato_emissione    = r.emissione
             WHERE ca.id = v_ca;
        END IF;

        INSERT INTO tmp_ce VALUES (
            r.caso, v_comm, v_ca,
            -- ⭐ La chiave si CHIEDE alla sola fonte, non si scrive a mano.
            vendite.fn_build_gruppo_fatturabile_key(
                (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'), v_comm::text, v_comm));
    END LOOP;
END;
$fixture$;

-- I lotti-testimone, e i loro esiti.
DO $lotti$
DECLARE
    v_rif      record;
    v_vivo     vendite.fatturazione_lotti.id%TYPE;
    v_vivo2    vendite.fatturazione_lotti.id%TYPE;
    v_chiuso   vendite.fatturazione_lotti.id%TYPE;
BEGIN
    SELECT * INTO v_rif FROM tmp_ce_rif;

    INSERT INTO vendite.fatturazione_lotti
        (codice, competenza_mese, tipo_doc_fiscale_id,
         emittente_soggetto_ruolo_id, stato_doc_fiscale_id)
    VALUES ('PGTAP-CE-LOTTO-VIVO', v_rif.mese, v_rif.tipo_doc_fiscale_id,
            v_rif.emittente_sr,
            (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DRAFT'))
    RETURNING id INTO v_vivo;

    INSERT INTO vendite.fatturazione_lotti
        (codice, competenza_mese, tipo_doc_fiscale_id,
         emittente_soggetto_ruolo_id, stato_doc_fiscale_id)
    VALUES ('PGTAP-CE-LOTTO-VIVO2', v_rif.mese, v_rif.tipo_doc_fiscale_id,
            v_rif.emittente_sr,
            (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'EMESSA'))
    RETURNING id INTO v_vivo2;

    -- ⭐ DEFINITIVA: chiuso, non annullato. E' il caso del difetto §6.1.
    INSERT INTO vendite.fatturazione_lotti
        (codice, competenza_mese, tipo_doc_fiscale_id,
         emittente_soggetto_ruolo_id, stato_doc_fiscale_id)
    VALUES ('PGTAP-CE-LOTTO-CHIUSO', v_rif.mese, v_rif.tipo_doc_fiscale_id,
            v_rif.emittente_sr,
            (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DEFINITIVA'))
    RETURNING id INTO v_chiuso;

    -- ⚠️ `errore_codice` e `errore_messaggio` sono OBBLIGATORI su ERRORE: lo
    --   pretende il CHECK chk_fatturazione_lotti_esiti_errore_parlante, e ha
    --   ragione — un errore che non sa dire cosa e' successo non e' un esito.
    INSERT INTO vendite.fatturazione_lotti_esiti
        (lotto_id, gruppo_key, stato_esecuzione, errore_codice, errore_messaggio)
    SELECT v_vivo, t.gruppo_key, 'ERRORE', 'E_PULL_COMMESSA', 'rotto per la prova'
      FROM tmp_ce t WHERE t.caso IN ('trattenuta', 'due_lotti', 'mese_prima', 'mese_dopo');

    INSERT INTO vendite.fatturazione_lotti_esiti (lotto_id, gruppo_key, stato_esecuzione)
    SELECT v_vivo2, t.gruppo_key, 'PENDING'
      FROM tmp_ce t WHERE t.caso = 'due_lotti';

    INSERT INTO vendite.fatturazione_lotti_esiti (lotto_id, gruppo_key, stato_esecuzione)
    SELECT v_chiuso, t.gruppo_key, 'COMPLETED'
      FROM tmp_ce t WHERE t.caso = 'lotto_chiuso';
END;
$lotti$;

-- ============================================================
-- 1) Il contratto
-- ============================================================
-- ⚠️ `columns_are`: diventa rosso anche su una colonna AGGIUNTA di straforo.
--   Il contratto sta nel brief (§8.2.2) e i quattro consumatori ci si
--   appoggiano.
SELECT columns_are(
    'vendite', 'vw_commesse_attivita_emittibilita',
    ARRAY['commessa_attivita_id', 'commessa_id', 'commessa_codice',
          'commessa_stato_codice_interno', 'commessa_stato_descrizione',
          'commessa_emittibile', 'gruppo_key', 'competenza_mese',
          'tipo_doc_fiscale_id', 'emittente_soggetto_ruolo_id', 'utility_id',
          'billing_account_id', 'fatturazione_immediata',
          'stato_emissione', 'stato_approvazione',
          'classe_emittibilita', 'trattenuta_da_lotti'],
    '1. il contratto: la vista espone esattamente le colonne dichiarate'
);

-- ============================================================
-- 2) ⭐ Le sei classi, una riga costruita per forma
-- ============================================================
SELECT results_eq(
    $$ SELECT t.caso, e.classe_emittibilita::text
         FROM tmp_ce t
         JOIN vendite.vw_commesse_attivita_emittibilita e
           ON e.commessa_attivita_id = t.ca_id
        WHERE t.caso IN ('emessa','annullata','rifiutata','bozza','pronta','trattenuta')
        ORDER BY t.caso $$,
    $$ VALUES ('annullata','ANNULLATA'), ('bozza','NON_APPROVATA'),
              ('emessa','EMESSA'), ('pronta','PRONTA'),
              ('rifiutata','RIFIUTATA'), ('trattenuta','TRATTENUTA') $$,
    '2. le sei classi: una riga costruita per forma, e ciascuna prende la sua'
);

-- ============================================================
-- 3) ⛔ La TESTATA non entra nella classe
-- ============================================================
-- ⭐ E' il test che tiene in piedi l'ortogonalita'. Se qualcuno «semplificasse»
--   fondendo `commessa_emittibile` dentro la classe, questa riga smetterebbe di
--   essere PRONTA — e la diagnostica perderebbe la sola cosa che sa dire meglio
--   della lane: «le righe sarebbero pronte, e' la commessa a essere in BOZZA».
-- ⚠️ La lane pretende ENTRAMBI i fattori, e resta corretta: li dichiara.
SELECT results_eq(
    $$ SELECT e.classe_emittibilita::text, e.commessa_emittibile
         FROM tmp_ce t
         JOIN vendite.vw_commesse_attivita_emittibilita e
           ON e.commessa_attivita_id = t.ca_id
        WHERE t.caso = 'testata_ko' $$,
    $$ VALUES ('PRONTA', false) $$,
    '3. la testata NON entra nella classe: riga PRONTA su commessa non emittibile, e il flag lo dice a parte'
);

-- ============================================================
-- 4) ⭐ Un lotto IN GIOCO trattiene
-- ============================================================
SELECT is(
    (SELECT e.classe_emittibilita::text
       FROM tmp_ce t
       JOIN vendite.vw_commesse_attivita_emittibilita e
         ON e.commessa_attivita_id = t.ca_id
      WHERE t.caso = 'trattenuta'),
    'TRATTENUTA',
    '4. un lotto in gioco sullo stesso mese TRATTIENE la riga'
);

-- ============================================================
-- 5) ⭐ E il verso opposto: un lotto CHIUSO non trattiene
-- ============================================================
-- ⛔ E' il difetto §6.1 visto da qui: DEFINITIVA non e' ANNULLATA, e con il
--   predicato vecchio (`NOT is_abortito`) questa riga sarebbe rimasta
--   trattenuta PER SEMPRE.
SELECT is(
    (SELECT e.classe_emittibilita::text
       FROM tmp_ce t
       JOIN vendite.vw_commesse_attivita_emittibilita e
         ON e.commessa_attivita_id = t.ca_id
      WHERE t.caso = 'lotto_chiuso'),
    'PRONTA',
    '5. un lotto CHIUSO (DEFINITIVA) non trattiene: la riga resta PRONTA'
);

-- ============================================================
-- 6) ⚠️ Competenza CUMULATIVA: il lotto di settembre tiene anche agosto
-- ============================================================
-- ⭐ Con l'UGUAGLIANZA questo test sarebbe rosso, ed e' il motivo per cui il
--   legame e' `>=`: la selezione del giro e' cumulativa, un lotto lavora la
--   propria competenza E quelle precedenti.
SELECT is(
    (SELECT e.classe_emittibilita::text
       FROM tmp_ce t
       JOIN vendite.vw_commesse_attivita_emittibilita e
         ON e.commessa_attivita_id = t.ca_id
      WHERE t.caso = 'mese_prima'),
    'TRATTENUTA',
    '6. competenza cumulativa: una riga del mese PRECEDENTE e'' trattenuta dal lotto di questo mese'
);

-- ============================================================
-- 7) ⚠️ E il contrario: il mese DOPO non lo tiene
-- ============================================================
-- ⛔ Senza nessun legame di competenza questo test sarebbe rosso: il documento
--   di ottobre erediterebbe il blocco del lotto di settembre, che non lo
--   lavorera' mai.
SELECT is(
    (SELECT e.classe_emittibilita::text
       FROM tmp_ce t
       JOIN vendite.vw_commesse_attivita_emittibilita e
         ON e.commessa_attivita_id = t.ca_id
      WHERE t.caso = 'mese_dopo'),
    'PRONTA',
    '7. e il contrario: una riga del mese SUCCESSIVO non e'' trattenuta'
);

-- ============================================================
-- 8) ⚠️ `trattenuta_da_lotti`: NULL se libera, ORDINATO se tenuta da due
-- ============================================================
-- ⭐ NULL e non array vuoto: «non trattenuta» e «trattenuta da nessuno» sono
--   due frasi diverse, e la seconda non significa niente.
-- ⚠️ Ordinato: chi ne vuole UNO prende il primo, e due chiamate identiche
--   devono dare lo stesso array.
SELECT results_eq(
    $$ SELECT t.caso,
              e.trattenuta_da_lotti IS NULL             AS libera,
              COALESCE(cardinality(e.trattenuta_da_lotti), 0) AS quanti,
              COALESCE(e.trattenuta_da_lotti
                       = (SELECT array_agg(x ORDER BY x)
                            FROM unnest(e.trattenuta_da_lotti) x), true) AS ordinato
         FROM tmp_ce t
         JOIN vendite.vw_commesse_attivita_emittibilita e
           ON e.commessa_attivita_id = t.ca_id
        WHERE t.caso IN ('pronta', 'due_lotti')
        ORDER BY t.caso $$,
    $$ VALUES ('due_lotti', false, 2, true), ('pronta', true, 0, true) $$,
    '8. trattenuta_da_lotti: NULL se libera, due lotti se tenuta da due, sempre ordinato'
);

SELECT * FROM finish();

ROLLBACK;
