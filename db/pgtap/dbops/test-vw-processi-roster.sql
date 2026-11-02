-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test SPEGNE, uno alla volta, i quattro livelli che
--   tengono in piedi un'identita' tecnica (legame, identita', utente Django,
--   ruolo). Sono scritture su cataloghi e su django.auth_user che il ruolo
--   applicativo non fa e non deve fare. Verificato cercando gli scrittori, non
--   dedotto.
--
-- Test: dbops.vw_processi_roster — con quale identita' un processo lavora
--       ciascuna azienda
-- Brief: brief-db-processi-automatici-identita-e-perimetro §12.12 (DB-1)
--
-- Elenco test (plan 7):
--  1) la vista porta le colonne che il produttore legge
--  2) il roster nomina la coppia (processo, azienda) appena COSTRUITA
--  3) ⚠️ e la nomina UNA volta sola: nessun fan-out dalle cinque join
--  4) ⛔ spento il LEGAME processo-utente, la coppia sparisce
--  5) ⛔ spenta l'IDENTITA' applicativa, la coppia sparisce
--  6) ⛔ disattivato l'UTENTE Django, la coppia sparisce
--  7) ⛔ cambiato il RUOLO applicativo, la coppia sparisce
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ CHE COSA PROVANO DAVVERO I TEST 4..7.
--   Il produttore `dbops.fn_accoda_chiusura_scadenze` accoda **per ogni riga
--   che legge qui**: se il roster nominasse un'identita' spenta a un livello
--   solo, il lavoro partirebbe per fermarsi dopo — o, peggio, girerebbe a
--   vuoto senza che nessuno lo sappia. Ognuno dei quattro spegnimenti deve
--   bastare da solo. E' la stessa terna che `script.fn_riattiva_utente_tecnico`
--   riaccende tutta insieme: spegnerne uno basta a fermare, quindi guardarne
--   uno solo basta a sbagliare.
--
-- ⚠️ LA QUINTA CONDIZIONE — `ef.attivo` — NON E' COLLAUDATA QUI, e va detto.
--   ⭐ Rev 2026-09-09: la ragione scritta prima non regge piu', e quella nuova
--   e' migliore perche' sta sul MODELLO invece che sui dati di oggi.
--   Diceva: «spegnere EMITEST o PGTAPEF202 e' vietato perche' hanno figlie
--   (contratti, documenti), e un emittente usa-e-getta sarebbe una fixture piu'
--   grande della cosa da provare». La seconda meta' non e' piu' vera —
--   `dbops.fn_pgtap_crea_roster_processo` un emittente usa-e-getta lo fabbrica
--   in una riga — ma provandolo si scopre che la prima non era la causa.
--   ⛔ Misurato il 2026-09-09 su un emittente appena creato, senza contratti e
--   senza documenti: lo spegnimento e' vietato lo stesso, e il guard nomina
--   `config.user_emittenti_fiscali`. Cioe' e' la riga di PERIMETRO dell'utente
--   tecnico a trattenerlo — proprio quella che serve al roster per esistere.
--   ⇒ `ef.attivo` non e' isolabile: per vederlo cadere bisognerebbe togliere
--   la riga di perimetro, ma il roster la JOINA, quindi la coppia sparirebbe
--   per l'altra ragione. Le due condizioni non si possono separare su un
--   emittente che ha un utente tecnico, ed e' l'unico che il roster nomina.
--   ⛔ Si dichiara invece di fingere: un `CASE WHEN … skip()` avrebbe detto la
--   stessa cosa occupando un numero di test, e un test che non prova niente e'
--   peggio di un test che manca — sembra copertura.
--
-- ⚠️ COME SI SPEGNE E SI RIACCENDE, e perche' non con un SAVEPOINT.
--   pgTAP tiene i risultati in tabelle temporanee dentro la STESSA
--   transazione: un `ROLLBACK TO` porterebbe via anche i test gia' passati.
--   Quindi ogni caso spegne, misura in una GUC, e riaccende — nello stesso
--   blocco, cosi' il ripristino non dipende da cio' che viene dopo.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- 1. Le colonne che il produttore legge
-- ============================================================
-- ⛔ Non e' pignoleria: `fn_accoda_chiusura_scadenze` legge esattamente questi
--   nomi. Perderne uno rinominando la vista romperebbe il produttore a
--   esecuzione, cioe' di notte e in silenzio.
SELECT is(
    (SELECT count(*)::int FROM information_schema.columns
      WHERE table_schema = 'dbops' AND table_name = 'vw_processi_roster'
        AND column_name IN ('processo_codice', 'auth_user_id', 'username',
                            'identita_id', 'emittente_fiscale_id',
                            'emittente_codice')),
    6,
    '1. la vista porta le sei colonne che il produttore legge'
);

-- ============================================================
-- La coppia su cui si lavora — si COSTRUISCE, non si cerca
-- ============================================================
-- ⛔ Fino al 2026-09-09 questo blocco pescava la prima coppia del roster
--   ESISTENTE. Su dbdev funzionava — due emittenti veri, otto coppie — e su un
--   database ricostruito dai changelog no: emittenti e soggetti sono
--   `dati_macchina`, quindi il roster e' vuoto e non deve contenere niente.
--   Misurato quel giorno sul database scratch di `scripts/ci-local.sh`: 0
--   righe, e i test 2 e 4..7 rossi tutti insieme. E' il corollario sui test
--   della Regola zero: un test che si appoggia alla popolazione prova i soli
--   casi che quella popolazione per caso contiene.
--
-- ⭐ E IL SECONDO GUADAGNO E' PIU' GRANDE DEL PRIMO. I test 4..7 spengono e
--   riaccendono quattro livelli di un'identita' tecnica. Prima lo facevano su
--   un'identita' VERA — quella con cui `chiusura_scadenze_daily` lavora
--   davvero i documenti di un'azienda di esercizio. Dentro una transazione
--   annullata, quindi senza danno, ma il collaudo si appoggiava a un mondo che
--   non era suo: bastava che quell'utente cambiasse stato per un'altra ragione
--   e il test avrebbe misurato altro. Adesso il mondo lo fabbrica il test.
DO $scelta$
DECLARE
    v_r record;
BEGIN
    SELECT * INTO v_r
      FROM dbops.fn_pgtap_crea_roster_processo('chiusura_scadenze_daily');

    PERFORM set_config('pgtap.user', v_r.auth_user_id::text, true);
    PERFORM set_config('pgtap.identita', v_r.identita_id::text, true);
    PERFORM set_config('pgtap.emittente', v_r.emittente_codice, true);
END
$scelta$;

-- ⚠️ Non piu' «almeno una coppia» ma «LA coppia»: l'asserzione nomina cio' che
--   la fixture ha appena costruito, quindi non puo' passare per merito di una
--   riga di esercizio che c'era gia'.
SELECT isnt_empty(
    format($$SELECT 1 FROM dbops.vw_processi_roster
              WHERE processo_codice = 'chiusura_scadenze_daily'
                AND emittente_codice = %L$$,
           current_setting('pgtap.emittente', true)),
    '2. il roster nomina la coppia (processo, azienda) appena costruita'
);

-- ⚠️ Cinque join in fila sono cinque occasioni di moltiplicare le righe. Una
--   coppia duplicata farebbe accodare DUE lavori alla stessa azienda, e
--   l'idempotenza li salverebbe — nascondendo il difetto invece di dirlo.
SELECT is_empty(
    $$SELECT processo_codice, emittente_codice
        FROM dbops.vw_processi_roster
       GROUP BY processo_codice, emittente_codice
      HAVING count(*) > 1$$,
    '3. nessuna coppia (processo, azienda) compare due volte'
);

-- ============================================================
-- 4..7. ⛔ Ognuno dei quattro livelli basta da solo
-- ============================================================
-- Ogni blocco: spegne, misura, riaccende. Il ripristino sta nello stesso
-- blocco perche' non dipenda da cio' che viene dopo.
DO $spegni$
DECLARE
    v_user integer := NULLIF(current_setting('pgtap.user', true), '')::integer;
    v_idg  bigint  := NULLIF(current_setting('pgtap.identita', true), '')::bigint;
    v_resta integer;
BEGIN
    IF v_user IS NULL THEN
        RETURN;   -- il test 2 ha gia' fallito: non si finge un risultato
    END IF;

    -- a) il legame processo-utente
    UPDATE dbops.processi_identita SET attivo = false WHERE auth_user_id = v_user;
    SELECT count(*) INTO v_resta FROM dbops.vw_processi_roster WHERE auth_user_id = v_user;
    PERFORM set_config('pgtap.senza_legame', v_resta::text, true);
    UPDATE dbops.processi_identita SET attivo = true WHERE auth_user_id = v_user;

    -- b) l'identita' applicativa
    UPDATE anagrafiche.identita_digitali SET attivo = false WHERE id = v_idg;
    SELECT count(*) INTO v_resta FROM dbops.vw_processi_roster WHERE auth_user_id = v_user;
    PERFORM set_config('pgtap.senza_identita', v_resta::text, true);
    UPDATE anagrafiche.identita_digitali SET attivo = true WHERE id = v_idg;

    -- c) l'utente Django
    -- ⭐ Questo caso ISOLA davvero `au.is_active`: misurato il 2026-09-05,
    --   disattivare l'utente NON spegne l'identita' collegata, quindi la
    --   sparizione dal roster viene dalla condizione che si sta provando e non
    --   da un effetto collaterale.
    UPDATE django.auth_user SET is_active = false WHERE id = v_user;
    SELECT count(*) INTO v_resta FROM dbops.vw_processi_roster WHERE auth_user_id = v_user;
    PERFORM set_config('pgtap.senza_django', v_resta::text, true);
    PERFORM set_config('pgtap.identita_dopo_django',
                       (SELECT attivo::text FROM anagrafiche.identita_digitali
                         WHERE id = v_idg), true);
    UPDATE django.auth_user SET is_active = true WHERE id = v_user;

    -- d) il ruolo applicativo
    -- ⚠️ Non un ruolo qualunque: le policy RLS riconoscono OPERATORE. Un
    --   utente tecnico con un'altra veste non e' «meno abilitato», e' un
    --   utente che le policy non vedono — e il lavoro girerebbe senza
    --   perimetro.
    -- ⚠️ Rev 2026-10-02 (brief-db-be-fe-area-accessi R-DB-1): era DISABILITATO,
    --   che la tabella viva ora rifiuta (una veste si spegne con attivo = false).
    --   API_CLIENT e' un altro tipo di MACCHINA: passa il guard di coerenza
    --   (early-exit) e quello sulla natura della credenziale (tecnica resta).
    UPDATE anagrafiche.identita_digitali
       SET ruolo_applicativo = 'API_CLIENT'::config.ruolo_applicativo
     WHERE id = v_idg;
    SELECT count(*) INTO v_resta FROM dbops.vw_processi_roster WHERE auth_user_id = v_user;
    PERFORM set_config('pgtap.senza_ruolo', v_resta::text, true);
    UPDATE anagrafiche.identita_digitali
       SET ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
     WHERE id = v_idg;
END
$spegni$;

SELECT is(current_setting('pgtap.senza_legame', true), '0',
          '4. spento il legame processo-utente, la coppia sparisce dal roster');

SELECT is(current_setting('pgtap.senza_identita', true), '0',
          '5. spenta l''identita'' applicativa, la coppia sparisce dal roster');

SELECT is(current_setting('pgtap.senza_django', true) || '/' ||
          current_setting('pgtap.identita_dopo_django', true),
          '0/true',
          '6. disattivato l''utente Django la coppia sparisce, e l''identita'' resta accesa');

SELECT is(current_setting('pgtap.senza_ruolo', true), '0',
          '7. cambiato il ruolo applicativo, la coppia sparisce dal roster');

SELECT * FROM finish();

ROLLBACK;
