-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   `titodb` non e' superuser e non puo' fare SET ROLE. E la fixture costruisce
--   DUE aziende con la loro commessa: un operatore dentro un perimetro non
--   potrebbe crearle.
-- pgTAP test FUNZIONALE RLS — i QUATTRO satelliti della famiglia COMMESSE
--   Slice 20260910-27..30, brief brief-db-perimetro-emittente-righe-documento.md §11.15
--   Quinta famiglia consegnata dal presidio dbops.vw_rls_perimetro_scoperto.
--
-- Elenco test (plan 16):
--   1) struttura: tutte e quattro le TABELLE sono coperte da una policy
--   2) struttura: e la RLS e' ACCESA su tutte e quattro
--   3) ⛔ tutte e quattro le policy di veste operatore usano l'adattatore
--      della PROPRIA chiave — contate, non «nessuna sbagliata»
--   4) ⭐ LA DECISIONE: `attivita_consumi` ha UNA veste sola, mentre la sua
--      testata `anagrafiche.billing_account` ne ha quattro
--   5) l'operatore A vede la PROPRIA attivita' fatturabile
--   6) ⛔ e non quella di B — la riparazione
--   7) A vede la PROPRIA sorgente di commessa
--   8) ⛔ e non quella di B
--   9) A vede il PROPRIO diario di riga di commessa
--  10) ⛔ e non quello di B
--  11) A vede il PROPRIO consumo
--  12) ⛔ e non quello di B
--  13) ⛔ SCRITTURA: A non puo' appendere un diario alla riga di commessa di B
--  14) ⛔ SCRITTURA: ne' un consumo al billing account di B
--  15) ⛔ senza veste applicativa: fail-closed su tutte e quattro
--  16) ⭐ l'adattatore `_via_commessa_attivita` dice il vero nei due versi
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ IL DIFETTO CHE QUESTO FILE CHIUDE, e qui il contenuto e' IL LAVORO.
--   `vendite.commesse` e `vendite.commesse_attivita` sono protette; i quattro
--   satelliti no, e `zeroerp_app` ha su tutti SELECT, INSERT, UPDATE e DELETE.
--   Il perimetro si fermava alla riga di commessa — mentre articolo, quantita',
--   prezzo, competenza e il diario di chi ha toccato cosa passavano di li'.
--
-- ⭐ UN SOLO ADATTATORE NUOVO, e il registro ne prometteva due.
--     attivita_fatturabili  ──(_via_commessa)──────────>  [c'era]
--     commesse_sorgenti     ──(_via_commessa)──────────>  [c'era]
--     commesse_attivita_log ──(_via_commessa_attivita)─>  [20260910-27]
--     attivita_consumi      ──(_via_efba)──────────────>  [c'era]
--   ⛔ La riga di registro di `attivita_consumi` sosteneva che l'adattatore da
--   un billing account all'emittente non esistesse. Esiste — ed e' proprio
--   quello che protegge `anagrafiche.billing_account`, cioe' il suo padre.
--
-- ⛔ IL TEST 3 PRENDE IL REFUSO CHE NON FA RUMORE. `_via_commessa` e
--   `_via_commessa_attivita` hanno la STESSA firma `(integer, bigint)` e le due
--   chiavi sono entrambe `bigint`: scambiarle **non da' nessun errore**.
--   ⚠️ E nel verso NEGATIVO lo scambio *sembra funzionare* — un id di riga di
--   commessa letto come id di commessa non trova quasi mai una commessa,
--   quindi fail-closed. A smascherarlo e' il verso POSITIVO, il test 9.
--
-- ⭐ IL TEST 4 E' LA DECISIONE MESSA PER ISCRITTO.
--   `vendite.attivita_consumi` e' l'unica delle quattro la cui testata ha PIU'
--   vesti: `anagrafiche.billing_account` porta `OPERATORE FOR ALL`, una
--   `FOR INSERT`, `CLIENTE_PORTALE FOR SELECT` e `SHOP_CUSTOMER FOR SELECT`.
--   ⇒ Decisione di Tid, 2026-09-10: **solo OPERATORE**, perche' sul modello
--   `attivita_consumi` non e' una faccia dell'anagrafica ma un documento
--   SORGENTE della pipeline di fatturazione (`config.sorgenti` codice interno
--   ATTIVITA_CONSUMI) che nomina un cliente — e il cliente i consumi li vede
--   resi sulla fattura, non come righe grezze.
--   ⚠️ Non e' neutra: chiude a portale e shop una porta oggi APERTA, perche'
--   oggi quella tabella non filtra affatto. Il test la pinna sulla definizione
--   della policy, cosi' il giorno in cui qualcuno aggiunge una veste deve
--   cambiare anche questa riga — e leggere perche'.
--
-- ⚠️ IL FORCE VA SU SEI TABELLE, non su quattro. Le due testate — `commesse` e
--   `commesse_attivita` — ci stanno perche' gli adattatori le LEGGONO: sotto
--   `zeroerp_app` quella lettura e' filtrata, e un test che la lasciasse
--   esente misurerebbe un adattatore piu' generoso di quello vero.
--   ⛔ E il FORCE va su tutte e quattro le tabelle armate anche se la fixture
--   le popola tutte: e' la stessa disciplina di `pratiche` e `listini`, dove
--   una tabella lasciata esente faceva contare all'owner le righe vere del
--   database di sviluppo — verde qui, e verde per sottrazione su un database
--   ricostruito.
--
-- ⚠️ COSA QUESTO FILE NON PROVA. Che i quattro siano TUTTI i satelliti: quello
--   lo dice il criterio, in `db/pgtap/rls/test-rls-perimetro-scoperto.sql`.
--   ⭐ Questa slice ne aveva fatta entrare una che NON arma —
--   `vendite.attivita_fatturabili_log`, che pendeva da `attivita_consumi` con
--   l'unica FK nullable. ⚠️ Il 2026-09-11 il censimento ha detto che non aveva
--   nessuno scrittore ne' lettore: era un residuo del dominio pipeline
--   «attivita fatturabili», ed e' stata **ritirata** (`20260911-04`).
--
-- ⭐ PROVATO FACENDOLO FALLIRE, non solo passare (2026-09-10):
--
--   | Mutazione                                            | Chi se ne accorge |
--   | ---------------------------------------------------- | ----------------- |
--   | `_via_commessa` al posto di `_via_commessa_attivita`  | test 3 **e 9**    |
--   | una veste `CLIENTE_PORTALE` su `attivita_consumi`     | test 4, e SOLO lui|
--   | `commesse_attivita_log` senza `ENABLE`                | test 2, 10, 13, 15|
--   | la policy del diario RINOMINATA                       | test 3            |
--
--   ⛔ La prima e' il refuso muto: nel verso NEGATIVO lo scambio sembra
--   funzionare (test 10 resta VERDE), perche' un id di riga letto come id di
--   commessa non trova nessuna commessa e la riga altrui resta invisibile lo
--   stesso. Senza il gemello positivo sarebbe passato.
--   ⛔ La quarta e' il buco che la prima stesura aveva: il test 3 era un
--   `is_empty` («nessuna policy sbagliata») e sarebbe stato VERDE con la
--   policy sparita, perche' il join non trovava piu' niente da giudicare.
--   Riscritto sul denominatore noto — quattro — la rinomina lo fa cadere.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ============================================================
-- I due mondi, una commessa a testa e i quattro satelliti attorno
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- ⛔ Il BA va LEGATO al proprio emittente (terzo parametro): senza,
--   `anagrafiche.fn_get_emittente_fiscale_id` non fallisce — ricade
--   sull'emittente di DEFAULT dell'installazione, cioe' risponde un'altra
--   azienda. E qui quella funzione decide l'emittente della commessa, perche'
--   `trgfn_commesse_default_emittente` lo deriva dal billing account.
CREATE TEMP TABLE _clienti AS
SELECT m.lato, m.soggetto_ruolo_id AS emittente_sr_id, m.auth_user_id, c.*
  FROM _mondi m
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba(
      'RLS commesse ' || m.lato, NULL, m.soggetto_ruolo_id) c;

-- ⚠️ L'articolo se lo costruisce: `catalogo/articoli.csv` e' VUOTO (sola
--   intestazione), quindi i 257 articoli di sviluppo sono dati di macchina e
--   su un database ricostruito da zero non ce n'e' nessuno. Un test che ne
--   cercasse uno sarebbe verde qui e senza materia in CI.
CREATE TEMP TABLE _articolo AS
WITH a AS (
    INSERT INTO catalogo.articoli (codice, descrizione, uom_id)
    SELECT 'PGTAP-RLS-CM', 'Articolo pgTAP RLS commesse',
           (SELECT um.id FROM catalogo.unita_misura um ORDER BY um.id LIMIT 1)
    RETURNING id, uom_id
)
SELECT id AS articolo_id, uom_id FROM a;

-- ⭐ `emittente_soggetto_ruolo_id` NON si passa: lo deriva dal BA il trigger
--   `trgfn_commesse_default_emittente`. Passarlo a mano proverebbe la fixture,
--   non il modello.
CREATE TEMP TABLE _commesse AS
WITH c AS (
    INSERT INTO vendite.commesse
        (codice, billing_account_id, utility_id,
         competenza_dal, competenza_al)
    SELECT 'PGTAP-CM-' || cl.lato || '-' || cl.billing_account_id,
           cl.billing_account_id, cl.utility_id,
           date_trunc('month', script.fn_data_operativa())::date,
           (date_trunc('month', script.fn_data_operativa()) + interval '1 month - 1 day')::date
      FROM _clienti cl
    RETURNING id, billing_account_id
)
SELECT cl.lato, c.id AS commessa_id, cl.billing_account_id,
       cl.istanza_utility_id, cl.auth_user_id
  FROM c JOIN _clienti cl ON cl.billing_account_id = c.billing_account_id;

-- La riga di commessa: e' la madre del diario, ed e' gia' protetta per conto suo.
-- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
CREATE TEMP TABLE _attivita AS
WITH a AS (
    INSERT INTO vendite.commesse_attivita
        (commessa_id, segment_key, articolo_id, istanza_utility_id,
         data_attivita, uom_id, quantita,
         competenza_mese, competenza_dal, competenza_al, prezzo_snapshot,
         sorgente_tipo_id, sorgente_uid)
    SELECT cm.commessa_id,
           ('SEG-RLSCM-' || cm.lato || '-' || cm.commessa_id)::varchar,
           ar.articolo_id, cm.istanza_utility_id,
           script.fn_data_operativa(), ar.uom_id, 1.000000,
           date_trunc('month', script.fn_data_operativa())::date,
           date_trunc('month', script.fn_data_operativa())::date,
           (date_trunc('month', script.fn_data_operativa()) + interval '1 month - 1 day')::date,
           50.0000000000,
           (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'), cm.commessa_id::text
      FROM _commesse cm CROSS JOIN _articolo ar
    RETURNING id, commessa_id
)
SELECT cm.lato, a.id AS commessa_attivita_id, a.commessa_id
  FROM a JOIN _commesse cm ON cm.commessa_id = a.commessa_id;

-- ---------- I quattro satelliti, uno per lato ----------

-- 1. il diario della riga di commessa
INSERT INTO vendite.commesse_attivita_log (commessa_attivita_id, evento, dettaglio)
SELECT a.commessa_attivita_id, 'PGTAP_RLS_COMMESSE',
       jsonb_build_object('lato', a.lato)
  FROM _attivita a;

-- 2. la sorgente della commessa: la commessa e' la ROOT di se stessa, che e'
--    la forma che `fn_link_commessa_sorgente` scrive.
--    ⚠️ La chiave va in `sorgente_id` perche' config.sorgenti.key_selector di
--    COMMESSA e' `id`: il guard unico valida chiave ed esistenza (giro C.2).
INSERT INTO vendite.commesse_sorgenti
    (commessa_id, sorgente_tipo_id, sorgente_id, ruolo_link)
SELECT cm.commessa_id,
       (SELECT s.id FROM config.sorgenti s
         WHERE s.codice_interno = 'COMMESSA' AND s.attivo),
       cm.commessa_id, 'ROOT'
  FROM _commesse cm;

-- 3. il lavoro fatturabile
--    ⚠️ `istanza_utility_id` DEVE essere quella del billing account: lo
--    pretende `trgfn_attivita_fatturabili_guard_ba_coerenza`, che dal
--    2026-09-10 valida davvero (prima usciva su ogni riga: slice 20260910-26).
INSERT INTO vendite.attivita_fatturabili
    (commessa_id, commessa_attivita_id, articolo_id, billing_account_id,
     istanza_utility_id, data_attivita, uom_id, quantita,
     competenza_mese, competenza_dal, competenza_al)
SELECT a.commessa_id, a.commessa_attivita_id, ar.articolo_id,
       cm.billing_account_id, cm.istanza_utility_id,
       script.fn_data_operativa(), ar.uom_id, 1.000000,
       date_trunc('month', script.fn_data_operativa())::date,
       date_trunc('month', script.fn_data_operativa())::date,
       (date_trunc('month', script.fn_data_operativa()) + interval '1 month - 1 day')::date
  FROM _attivita a
  JOIN _commesse cm ON cm.commessa_id = a.commessa_id
  CROSS JOIN _articolo ar;

-- 4. la testata consumi: l'unica che NON pende dalla commessa
INSERT INTO vendite.attivita_consumi (billing_account_id, competenza_mese)
SELECT cm.billing_account_id, date_trunc('month', script.fn_data_operativa())::date
  FROM _commesse cm;

-- ============================================================
-- 1..4. La struttura, e la decisione
-- ============================================================
-- ⚠️ Si contano le TABELLE coperte, non le policy: il giorno in cui una veste
--   in piu' fosse decisa, questo test non deve diventare rosso per il motivo
--   sbagliato — a pretendere che la veste resti una sola e' il test 4, che
--   quella decisione la nomina.
SELECT is(
    (SELECT count(DISTINCT p.tablename)::int FROM pg_policies p
      WHERE p.schemaname = 'vendite'
        AND p.tablename IN ('attivita_fatturabili', 'commesse_sorgenti',
                            'commesse_attivita_log', 'attivita_consumi')),
    4,
    '1. tutti e quattro i satelliti della famiglia commesse hanno la loro policy'
);

-- ⛔ Si asserisce `relrowsecurity`, non l'esistenza della policy: una policy
--   con la RLS spenta non e' una difesa — e' il secondo criterio del presidio.
SELECT is(
    (SELECT count(*)::int FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE c.relrowsecurity
        AND n.nspname = 'vendite'
        AND c.relname IN ('attivita_fatturabili', 'commesse_sorgenti',
                          'commesse_attivita_log', 'attivita_consumi')),
    4,
    '2. e la ROW LEVEL SECURITY e'' accesa su tutti e quattro'
);

-- ⛔ Tre adattatori, tre chiavi, tutte bigint: scambiarne due compila, gira e
--   filtra sulla cosa sbagliata.
-- ⚠️ Il perimetro e' la sola veste OPERATORE (`%_ef_whitelist`), e non e'
--   pigrizia: una veste diversa avrebbe per forza un adattatore diverso —
--   `fn_scope_ba_ownership` per il portale — e pretendere `_via_efba` anche da
--   lei renderebbe questo test rosso su una decisione legittima, cioe' nel
--   posto sbagliato. A pretendere che la veste resti una sola e' il test 4.
-- ⛔ E si conta quante sono CORRETTE, non quante sono sbagliate: un
--   `is_empty` sarebbe verde anche il giorno in cui una di queste policy
--   sparisse o cambiasse nome — il join non troverebbe niente, e «nessuna
--   riga cattiva» e' esattamente cio' che dice un presidio che non guarda piu'
--   niente. Il denominatore e' scritto: quattro.
-- ⭐ Rev 2026-10-18 (D-3b-2 giro 1b, 20261018-33): la rotta si legge nel modo di
--   script.fn_resolve_emittente_fiscale_id, non piu' nel nome dell'adattatore.
--   attivita_consumi (ondata 2, 20261018-50): il billing account, letto da
--   script.fn_get_ba_emittente_sr_id col perimetro in convenzione SR.
SELECT is(
    (SELECT count(*)::int
       FROM (VALUES
              ('attivita_fatturabili',  'fn_resolve_emittente_fiscale_id(''commessa''::text'),
              ('commesse_sorgenti',     'fn_resolve_emittente_fiscale_id(''commessa''::text'),
              ('commesse_attivita_log', 'fn_resolve_emittente_fiscale_id(''commessa_attivita''::text'),
              ('attivita_consumi',      'fn_get_ba_emittente_sr_id(')
            ) AS a(tab, adattatore)
       JOIN pg_policies p
         ON p.schemaname = 'vendite'
        AND p.tablename  = a.tab
        AND p.policyname LIKE '%\_ef\_whitelist'
      WHERE position(a.adattatore IN p.qual)       > 0
        AND position(a.adattatore IN p.with_check) > 0),
    4,
    '3. tutte e quattro le policy di veste operatore usano l''adattatore della propria chiave (commessa / riga di commessa / billing account)'
);

-- ⭐ LA DECISIONE, pinnata dove vive. `anagrafiche.billing_account` ha quattro
--   policy; il suo satellite ne ha UNA, ed e' OPERATORE. Aggiungere una veste
--   al portale o allo shop deve far cadere questa riga.
SELECT is(
    (SELECT count(*)::int || '/' || count(*) FILTER (
                WHERE p.qual LIKE '%OPERATORE%'
                  AND p.qual NOT LIKE '%CLIENTE_PORTALE%'
                  AND p.qual NOT LIKE '%SHOP_CUSTOMER%')::int
       FROM pg_policies p
      WHERE p.schemaname = 'vendite' AND p.tablename = 'attivita_consumi'),
    '1/1',
    '4. attivita_consumi porta UNA sola veste, OPERATORE: la testata ne ha quattro, ed e'' una decisione (Tid, 2026-09-10)'
);

-- ============================================================
-- Il perimetro, esercitato da dentro
-- ============================================================
-- ⛔ Anche le due TESTATE: gli adattatori le leggono, e sotto `zeroerp_app`
--   quella lettura e' filtrata. Lasciarle esenti misurerebbe un adattatore
--   piu' generoso di quello vero.
ALTER TABLE vendite.commesse              FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.commesse_attivita     FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.attivita_fatturabili  FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.commesse_sorgenti     FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.commesse_attivita_log FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.attivita_consumi      FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a record;
    v_b record;
    v_n integer;
BEGIN
    SELECT cm.*, a.commessa_attivita_id INTO v_a
      FROM _commesse cm JOIN _attivita a ON a.commessa_id = cm.commessa_id
     WHERE cm.lato = 'A';
    SELECT cm.*, a.commessa_attivita_id INTO v_b
      FROM _commesse cm JOIN _attivita a ON a.commessa_id = cm.commessa_id
     WHERE cm.lato = 'B';

    PERFORM script.fn_pgtap_set_contesto_operatore(v_a.auth_user_id);

    -- ⭐ I versi POSITIVI sono quelli che smascherano un adattatore scambiato:
    --   nel verso negativo uno scambio sembra funzionare lo stesso.
    SELECT count(*) INTO v_n FROM vendite.attivita_fatturabili af
     WHERE af.commessa_id = v_a.commessa_id;
    PERFORM set_config('pgtap.af_a', v_n::text, true);

    SELECT count(*) INTO v_n FROM vendite.attivita_fatturabili af
     WHERE af.commessa_id = v_b.commessa_id;
    PERFORM set_config('pgtap.af_b', v_n::text, true);

    SELECT count(*) INTO v_n FROM vendite.commesse_sorgenti cs
     WHERE cs.commessa_id = v_a.commessa_id;
    PERFORM set_config('pgtap.sorg_a', v_n::text, true);

    SELECT count(*) INTO v_n FROM vendite.commesse_sorgenti cs
     WHERE cs.commessa_id = v_b.commessa_id;
    PERFORM set_config('pgtap.sorg_b', v_n::text, true);

    SELECT count(*) INTO v_n FROM vendite.commesse_attivita_log l
     WHERE l.commessa_attivita_id = v_a.commessa_attivita_id;
    PERFORM set_config('pgtap.log_a', v_n::text, true);

    SELECT count(*) INTO v_n FROM vendite.commesse_attivita_log l
     WHERE l.commessa_attivita_id = v_b.commessa_attivita_id;
    PERFORM set_config('pgtap.log_b', v_n::text, true);

    SELECT count(*) INTO v_n FROM vendite.attivita_consumi ac
     WHERE ac.billing_account_id = v_a.billing_account_id;
    PERFORM set_config('pgtap.cons_a', v_n::text, true);

    SELECT count(*) INTO v_n FROM vendite.attivita_consumi ac
     WHERE ac.billing_account_id = v_b.billing_account_id;
    PERFORM set_config('pgtap.cons_b', v_n::text, true);

    -- ⛔ SCRITTURA: un diario sulla riga di commessa altrui.
    -- ⚠️ Si cattura anche `raise_exception` (P0001): a rifiutare potrebbe
    --   essere un guard che legge sotto RLS PRIMA che la WITH CHECK sia
    --   valutata, con un messaggio che parla d'altro. La proprieta' misurata e'
    --   «la scrittura non passa», non «chi la rifiuta».
    BEGIN
        INSERT INTO vendite.commesse_attivita_log (commessa_attivita_id, evento)
        VALUES (v_b.commessa_attivita_id, 'PGTAP_RLS_INTRUSIONE');
        PERFORM set_config('pgtap.scr_log', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation OR raise_exception THEN
        PERFORM set_config('pgtap.scr_log', 'RIFIUTATA', true);
    END;

    -- ⛔ SCRITTURA: un consumo sul billing account altrui.
    BEGIN
        INSERT INTO vendite.attivita_consumi (billing_account_id, competenza_mese)
        VALUES (v_b.billing_account_id, date_trunc('month', script.fn_data_operativa())::date);
        PERFORM set_config('pgtap.scr_cons', 'PASSATA', true);
    EXCEPTION WHEN insufficient_privilege OR check_violation OR raise_exception THEN
        PERFORM set_config('pgtap.scr_cons', 'RIFIUTATA', true);
    END;

    -- ⭐ L'adattatore nuovo nei due versi: e' l'unica prova che distingue
    --   `_via_commessa_attivita` da `_via_commessa`, che ha la stessa firma.
    PERFORM set_config('pgtap.adattatore',
        CASE WHEN     script.fn_scope_ef_whitelist_via_commessa_attivita(
                          v_a.auth_user_id, v_a.commessa_attivita_id)
              AND NOT script.fn_scope_ef_whitelist_via_commessa_attivita(
                          v_a.auth_user_id, v_b.commessa_attivita_id)
             THEN 'CORRETTO' ELSE 'SBAGLIATO' END, true);

    -- ⛔ Nessuna veste: fail-closed su tutte e quattro.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    SELECT (SELECT count(*) FROM vendite.attivita_fatturabili)
         + (SELECT count(*) FROM vendite.commesse_sorgenti)
         + (SELECT count(*) FROM vendite.commesse_attivita_log)
         + (SELECT count(*) FROM vendite.attivita_consumi)
      INTO v_n;
    PERFORM set_config('pgtap.senza_veste', v_n::text, true);
END
$perimetro$;

ALTER TABLE vendite.attivita_consumi      NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.commesse_attivita_log NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.commesse_sorgenti     NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.attivita_fatturabili  NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.commesse_attivita     NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.commesse              NO FORCE ROW LEVEL SECURITY;

SELECT isnt(current_setting('pgtap.af_a', true), '0',
            '5. l''operatore A vede la PROPRIA attivita'' fatturabile');

SELECT is(current_setting('pgtap.af_b', true), '0',
          '6. e non quella di B: il lavoro fatturabile altrui non si legge piu''');

SELECT isnt(current_setting('pgtap.sorg_a', true), '0',
            '7. A vede la PROPRIA sorgente di commessa');

SELECT is(current_setting('pgtap.sorg_b', true), '0',
          '8. e non quella di B: da dove nasce la commessa di un''altra azienda non si legge');

SELECT isnt(current_setting('pgtap.log_a', true), '0',
            '9. A vede il PROPRIO diario di riga di commessa: senza questo verso un adattatore scambiato passerebbe');

SELECT is(current_setting('pgtap.log_b', true), '0',
          '10. e non quello di B');

SELECT isnt(current_setting('pgtap.cons_a', true), '0',
            '11. A vede il PROPRIO consumo — la rotta passa dal billing account, non dalla commessa');

SELECT is(current_setting('pgtap.cons_b', true), '0',
          '12. e non quello di B');

SELECT is(current_setting('pgtap.scr_log', true), 'RIFIUTATA',
          '13. e non puo'' appendere un diario alla riga di commessa di B: la WITH CHECK, non la sola lettura');

SELECT is(current_setting('pgtap.scr_cons', true), 'RIFIUTATA',
          '14. ne'' un consumo al billing account di B');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '15. senza veste applicativa nessuna delle quattro risponde: fail-closed');

SELECT is(current_setting('pgtap.adattatore', true), 'CORRETTO',
          '16. l''adattatore _via_commessa_attivita dice il vero: la propria riga si'', quella di B no');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia dietro di se' nessuna commessa e nessuna azienda di prova.
ROLLBACK;
