-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): le commesse le costruisce
--   dbops.fn_pgtap_crea_commessa sul billing account del test, con UNA riga APPROVATA:
--   PRONTA_FATTURAZIONE per le testate emittibili, BOZZA (riga chiesta, p_con_attivita
--   => true) per testata_ko. Prima testata e riga erano scritte a mano con articolo,
--   unita' di misura, tipo documento e valuta pescati «il primo per id», e lo stato «no»
--   era «il primo non emittibile per id». Le due righe fuori mese (mese_prima /
--   mese_dopo) restano scritte dal test, su una commessa del builder, con articolo,
--   unita' di misura, tipo documento e valuta della prima riga scritta dal builder. Il
--   test 0 conta le righe costruite (11) al posto del catalogo pescato.
-- rev 2026-10-24 (brief-modello-documento-vendita R-4): i tre lotti-testimone (DRAFT,
--   EMESSA, DEFINITIVA) nascono da dbops.fn_pgtap_crea_lotto (madre
--   vendite.fn_create_fatturazione_lotto, stato per la matrice, tipo documento della
--   riga, cliente del test), e l'esito ERRORE E_PULL_COMMESSA di «trattenuta» lo scrive
--   il builder (p_gruppo_key_trattenuto). Prima i lotti erano INSERT a mano, gia' nello
--   stato. Restano del test gli altri tre ERRORE del lotto DRAFT (il builder ne
--   trattiene UNO), il PENDING e il COMPLETED: sono forme del caso. Le asserzioni non
--   leggono codice ne' utility del lotto.
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
-- ⭐ Le DUE testate, per codice_interno: una emittibile e una no. Servono al
--   test 3, che e' il punto dell'ortogonalita'.
CREATE TEMP TABLE tmp_ce_stati AS
SELECT 'PRONTA_FATTURAZIONE'::varchar AS stato_ok, 'BOZZA'::varchar AS stato_ko;

-- Un caso = una COMMESSA con UNA riga: cosi' ogni caso ha la sua gruppo_key.
CREATE TEMP TABLE tmp_ce (caso text, commessa_id bigint, ca_id bigint, gruppo_key text);

DO $fixture$
DECLARE
    r          record;
    v_st       record;
    v_mese     vendite.commesse_attivita.competenza_mese%TYPE;
    v_comm     vendite.commesse.id%TYPE;
    v_ca       vendite.commesse_attivita.id%TYPE;
    -- la riga del primo caso costruito dal builder: le righe fuori mese ne
    --   prendono articolo, unita' di misura, tipo documento e valuta.
    v_modello  vendite.commesse_attivita%ROWTYPE;
BEGIN
    SELECT * INTO v_st FROM tmp_ce_stati;
    v_mese := date_trunc('month', script.fn_data_operativa())::date;

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
        IF r.off_mese = 0 THEN
            -- Il builder: testata dalla madre, UNA riga APPROVATA/NON_EMESSA,
            --   lo stato per la matrice (in BOZZA la riga la si chiede).
            SELECT c.commessa_id, c.attivita_id INTO v_comm, v_ca
              FROM dbops.fn_pgtap_crea_commessa(
                       'emittibilita ' || r.caso,
                       CASE WHEN r.testata_ok THEN v_st.stato_ok ELSE v_st.stato_ko END,
                       (SELECT billing_account_id FROM tmp_ce_cliente),
                       true) c;

            IF v_modello.id IS NULL THEN
                SELECT * INTO v_modello FROM vendite.commesse_attivita ca WHERE ca.id = v_ca;
            END IF;
        ELSE
            -- ⚠️ La riga FUORI MESE e' una forma del test: il builder scrive la
            --   riga nel mese corrente. Commessa del builder (in BOZZA, senza
            --   riga), la riga scritta qui, poi lo stato per la matrice.
            SELECT c.commessa_id INTO v_comm
              FROM dbops.fn_pgtap_crea_commessa(
                       'emittibilita ' || r.caso, NULL,
                       (SELECT billing_account_id FROM tmp_ce_cliente)) c;

            INSERT INTO vendite.commesse_attivita (
                commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
                uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
                tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
                stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_id)
            VALUES (v_comm,
                    ((SELECT x.segment_key FROM dbops.fn_pgtap_consumo_della_commessa(v_comm) x) || ':' || 'PGTAP-CE-' || r.caso || '-' || substr(md5(clock_timestamp()::text), 1, 12)),
                    v_modello.articolo_id, v_modello.istanza_utility_id,
                    (v_mese + (r.off_mese || ' month')::interval)::date,
                    v_modello.uom_id, 1,
                    (v_mese + (r.off_mese || ' month')::interval)::date,
                    (v_mese + (r.off_mese || ' month')::interval)::date,
                    ((v_mese + (r.off_mese || ' month')::interval)
                      + INTERVAL '1 month - 1 day')::date,
                    v_modello.tipo_doc_fiscale_id, v_modello.valuta_id, 10.000000, 'FIXED',
                    r.approvazione, r.emissione,
                    (SELECT x.sorgente_tipo_id FROM dbops.fn_pgtap_consumo_della_commessa(v_comm) x), (SELECT x.consumo_id FROM dbops.fn_pgtap_consumo_della_commessa(v_comm) x))
            RETURNING id INTO v_ca;

            PERFORM dbops.fn_pgtap_porta_a_stato('vendite.commesse', v_comm,
                CASE WHEN r.testata_ok THEN v_st.stato_ok ELSE v_st.stato_ko END);
        END IF;

        -- ⚠️ Il passaggio a PRONTA_FATTURAZIONE pretende una riga APPROVATA e
        --   NON_EMESSA (fn_check_commessa_pronta_fatturazione): la riga nasce
        --   pronta e, passata la testata, si porta alla forma del caso.
        IF r.testata_ok AND (r.approvazione, r.emissione) IS DISTINCT FROM ('APPROVATA', 'NON_EMESSA') THEN
            UPDATE vendite.commesse_attivita ca
               SET stato_approvazione = r.approvazione,
                   stato_emissione    = r.emissione
             WHERE ca.id = v_ca;
        END IF;

        INSERT INTO tmp_ce VALUES (
            r.caso, v_comm, v_ca,
            -- ⭐ La chiave si CHIEDE alla sola fonte, non si scrive a mano.
            (SELECT vendite.fn_gruppo_fatturabile_key_di_attivita(ca.sorgente_tipo_id, ca.segment_key, ca.commessa_id)
                FROM vendite.commesse_attivita ca WHERE ca.id = v_ca));
    END LOOP;
END;
$fixture$;

CREATE TEMP TABLE tmp_ce_rif AS
SELECT
  (SELECT m.soggetto_ruolo_id FROM tmp_ce_mondo m)             AS emittente_sr,
  (SELECT c.billing_account_id FROM tmp_ce_cliente c)          AS billing_account_id,
  -- il tipo documento dei lotti e' quello della riga scritta, non un pescato
  (SELECT ca.tipo_doc_fiscale_id FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT t.ca_id FROM tmp_ce t WHERE t.caso = 'pronta')) AS tipo_doc_fiscale_id,
  (SELECT sc.emittibile FROM vendite.stati_commessa sc, tmp_ce_stati st
    WHERE sc.codice_interno = st.stato_ok AND sc.attivo IS TRUE)          AS stato_ok_emittibile,
  (SELECT sc.emittibile FROM vendite.stati_commessa sc, tmp_ce_stati st
    WHERE sc.codice_interno = st.stato_ko AND sc.attivo IS TRUE)          AS stato_ko_emittibile,
  -- le righe costruite: una per commessa, sul cliente del test
  (SELECT count(*) FROM tmp_ce t
     JOIN vendite.commesse_attivita ca ON ca.id = t.ca_id AND ca.commessa_id = t.commessa_id
     JOIN vendite.commesse c ON c.id = t.commessa_id
    WHERE c.billing_account_id = (SELECT billing_account_id FROM tmp_ce_cliente)) AS n_costruite,
  date_trunc('month', script.fn_data_operativa())::date                      AS mese;

SELECT ok(
  (SELECT r.emittente_sr IS NOT NULL AND r.billing_account_id IS NOT NULL
      AND r.tipo_doc_fiscale_id IS NOT NULL
      AND r.stato_ok_emittibile IS TRUE AND r.stato_ko_emittibile IS FALSE
      AND r.n_costruite = 11
     FROM tmp_ce_rif r),
  '0. riferimenti minimi risolti (emittente, anagrafiche, undici righe costruite, due stati commessa)'
);

-- I lotti-testimone, dal builder: lotto vuoto, stato per la matrice.
--   Il DRAFT trattiene «trattenuta» (l'esito ERRORE lo scrive il builder).
--   ⭐ DEFINITIVA: chiuso, non annullato. E' il caso del difetto §6.1.
CREATE TEMP TABLE tmp_ce_lotti AS
SELECT v.caso, l.*
  FROM tmp_ce_rif r,
       (VALUES ('vivo', 'DRAFT', 1), ('vivo2', 'EMESSA', 2), ('chiuso', 'DEFINITIVA', 3))
           AS v(caso, stato, ord),
       LATERAL dbops.fn_pgtap_crea_lotto(
           'emittibilita ' || v.caso, v.stato::varchar, r.billing_account_id,
           p_tipo_doc_fiscale_id   => r.tipo_doc_fiscale_id,
           p_competenza_mese       => r.mese,
           p_gruppo_key_trattenuto => CASE WHEN v.caso = 'vivo'
               THEN (SELECT t.gruppo_key FROM tmp_ce t WHERE t.caso = 'trattenuta') END) l
 ORDER BY v.ord;

-- Gli altri esiti sono forme del caso: il builder ne trattiene uno solo.
-- ⚠️ `errore_codice` e `errore_messaggio` sono OBBLIGATORI su ERRORE: lo
--   pretende il CHECK chk_fatturazione_lotti_esiti_errore_parlante, e ha
--   ragione — un errore che non sa dire cosa e' successo non e' un esito.
INSERT INTO vendite.fatturazione_lotti_esiti
    (lotto_id, gruppo_key, stato_esecuzione, errore_codice, errore_messaggio)
SELECT (SELECT l.lotto_id FROM tmp_ce_lotti l WHERE l.caso = 'vivo'),
       t.gruppo_key, 'ERRORE', 'E_PULL_COMMESSA', 'rotto per la prova'
  FROM tmp_ce t WHERE t.caso IN ('due_lotti', 'mese_prima', 'mese_dopo');

INSERT INTO vendite.fatturazione_lotti_esiti (lotto_id, gruppo_key, stato_esecuzione)
SELECT (SELECT l.lotto_id FROM tmp_ce_lotti l WHERE l.caso = 'vivo2'), t.gruppo_key, 'PENDING'
  FROM tmp_ce t WHERE t.caso = 'due_lotti';

INSERT INTO vendite.fatturazione_lotti_esiti (lotto_id, gruppo_key, stato_esecuzione)
SELECT (SELECT l.lotto_id FROM tmp_ce_lotti l WHERE l.caso = 'chiuso'), t.gruppo_key, 'COMPLETED'
  FROM tmp_ce t WHERE t.caso = 'lotto_chiuso';

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
