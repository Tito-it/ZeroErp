-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture semina su dbops.processi / processi_bersagli,
--   cataloghi che a runtime non scrive nessuno (li popola il mirror CSV di
--   80_data) e su cui il ruolo applicativo ha SELECT-only. Verificato cercando
--   gli scrittori, non dedotto.
--
-- Test: un debito si DICHIARA (DB-2), e l'email sa di chi e' (DB-3)
-- Brief: brief-db-processi-automatici-residui-be.md, DB-2 e DB-3
--
-- Elenco test (plan 8):
--  1) il flag esiste, e il default e' false
--  2) ⛔ DB-3: un'email non di SISTEMA senza emittente si ferma
--  3) ✅ DB-3: un'email di SISTEMA entra SENZA emittente, come deve
--  4) ⭐ il livello 1 non ha ALLARMI (nessuna riga NON_DICHIARATO)
--  5) ⭐ DB-2: un bersaglio scoperto ma DICHIARATO si presenta come tale (COSTRUITO)
--  6) ⛔ DB-2: un bersaglio nuovo e rotto e' un ALLARME, non un debito
--  7) le due viste parlano la stessa lingua
--  8) ⛔ una policy SCRITTA ma con la RLS spenta non conta come difesa
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ LA CONTRADDIZIONE CHE SI CHIUDE, e il backend l'ha vista giusta.
--   La descrizione delle viste diceva «DEVE restare VUOTA»; il seed diceva,
--   sulla riga di config.email_outbox, «riga ATTESA in quella vista». Le due
--   frasi non possono essere vere insieme — e la conseguenza non e' formale:
--   ⭐ un presidio sempre acceso viene ignorato, e il giorno in cui compare una
--     riga VERA nessuno la distingue dal rumore di fondo.
--
-- ⭐ I test 5 e 6 vanno letti INSIEME: sono lo stesso presidio che risponde in
--   due modi opposti a due situazioni diverse. Provare solo il 5 lascerebbe
--   passare un flag che dice sempre «dichiarato» — cioe' un presidio spento.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- 1. Il flag, e il suo default
-- ============================================================
-- ⭐ Il default e' la parte che protegge: un bersaglio nuovo nasce NON
--   dichiarato, quindi se finisce in un presidio e' un allarme. Il default
--   opposto avrebbe reso il silenzio l'impostazione di fabbrica.
SELECT col_default_is('dbops', 'processi_bersagli', 'debito_dichiarato', 'false',
                      '1. debito_dichiarato ha default false: dichiarare e'' un gesto');

-- ============================================================
-- 2..3. DB-3: il CHECK legato ad `ambito`
-- ============================================================
-- ⛔ Non un NOT NULL, e la ragione sta nella tabella stessa: un'email di
--   SISTEMA — reset password, alert — non ha un emittente e non puo' averlo.
-- ⚠️ Rev 2026-09-25: con il proprietario della bozza. Dal 20260925-64 una bozza
--   OPERATORE senza proprietario viola anche chk_email_outbox_operatore_creatore:
--   senza questa colonna il 23514 arriverebbe da due vincoli, e il test sarebbe
--   verde anche con il CHECK dell'emittente sparito.
SELECT throws_ok(
    $$INSERT INTO config.email_outbox
          (ambito, destinatario, oggetto, corpo_html, stato, creato_da_user_id)
      VALUES ('OPERATORE', 'pgtap@example.invalid', 'pgtap', '<p/>', 'DRAFT',
              NULLIF(current_setting('app.current_user_id', true), '')::integer)$$,
    '23514',
    NULL,
    '2. un''email non di SISTEMA senza emittente si ferma'
);

-- ⚠️ Il verso opposto, che da solo il test 2 non copre: un CHECK scritto male —
--   per esempio `emittente_fiscale_id IS NOT NULL` senza la clausola su
--   `ambito` — passerebbe il test 2 e romperebbe TUTTE le email di sistema.
SELECT lives_ok(
    $$INSERT INTO config.email_outbox
          (ambito, destinatario, oggetto, corpo_html, stato)
      VALUES ('SISTEMA', 'pgtap@example.invalid', 'pgtap reset', '<p/>', 'DRAFT')$$,
    '3. un''email di SISTEMA entra SENZA emittente, come deve'
);

-- ============================================================
-- 4. ⭐ Il livello 1 non ha ALLARMI
-- ============================================================
-- ⚠️ ASSERZIONE CAMBIATA il 2026-09-05, ed era «il livello 1 e' VUOTO».
--   Era vera, e ha smesso di esserlo per un motivo che e' un miglioramento:
--   `config.email_log` — la tabella che `send_pending_emails` LEGGE davvero, e
--   che non ha nessuna colonna emittente — e' stata dichiarata come bersaglio.
--   ⛔ Prima il censimento nominava `config.email_outbox`, che quel processo non
--   apre mai: il presidio sorvegliava con sicurezza la tabella sbagliata, e
--   quella vera non compariva da nessuna parte.
--   ⇒ Dichiararla la fa comparire qui, ed e' giusto che compaia: il percorso
--     verso l'emittente non esiste ancora.
--
-- ⭐ L'invariante che resta vera — e che vale per entrambi i livelli — e'
--   **«nessuna riga NON_DICHIARATO»**: un debito con un nome e' un lavoro, una
--   riga che nessuno ha dichiarato e' un allarme.
-- ⚠️ E il rischio si dichiara: dichiarare un debito ZITTISCE questo test. Lo
--   tiene onesto il test 6 qui sotto, che costruisce un bersaglio NUOVO e rotto
--   e pretende che esca NON_DICHIARATO — cioe' che il flag sia un gesto e non
--   l'impostazione di fabbrica.
SELECT is_empty(
    $$SELECT processo_codice, nome_tabella
        FROM dbops.vw_processi_dominio_senza_emittente
       WHERE stato = 'NON_DICHIARATO'$$,
    '4. nessun bersaglio di dominio senza percorso che non sia DICHIARATO'
);

-- ============================================================
-- 5..6. ⭐ DB-2: il presidio distingue l'atteso dal nuovo
-- ============================================================
-- ⚠️ ASSERZIONE RIVOLTATA il 2026-09-05, ed e' la QUARTA volta che questa
--   lezione si paga. Chiedeva che `config.email_outbox` comparisse nel livello 2
--   come `DEBITO_DICHIARATO`: si appoggiava a un **debito reale**, e quel debito
--   e' stato ritirato — la riga di censimento affermava il falso
--   (`send_pending_emails` non apre mai quella tabella, changeSet `20260905-34`).
--   ⛔ Un test che si appoggia a un debito si rompe quando il debito se ne va,
--     cioe' **quando il lavoro riesce**.
--   ⇒ Il caso si COSTRUISCE, esattamente come lo costruisce il test 6 per il
--     verso opposto. I due sono lo stesso presidio che risponde in due modi a
--     due situazioni diverse, e adesso sono simmetrici anche nella forma.
DO $dichiarato$
DECLARE
    v_id dbops.processi.id%TYPE := 9402;
BEGIN
    -- 20261016-20: chi ha una sveglia dichiara l'accensione; un CODA no.
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento)
    VALUES (v_id, 'PGTAP-DB2-DICHIARATO',
            'processo di prova con un bersaglio scoperto ma DICHIARATO',
            'DOMINIO', 'COMMAND', true, true, true, 'PROGRAMMA');

    -- Padre e figlio in DUE istruzioni: una CTE unica condividerebbe la stessa
    -- snapshot e la FK non troverebbe il padre.
    -- ⭐ ANCHE LA TABELLA SCOPERTA SI COSTRUISCE, e questa e' la QUINTA volta.
    --   La stesura precedente puntava a `config.email_outbox` perche' «oggi e'
    --   davvero scoperta». Lo era la mattina; il changeSet `20260905-37` le ha
    --   dato RLS e write-guard nel pomeriggio, e il test e' andato rosso
    --   **perche' il lavoro era riuscito** — di nuovo.
    --   ⛔ Costruire il processo e il bersaglio NON BASTA se la condizione che
    --     li rende «scoperti» resta una proprieta' di una tabella VERA che
    --     qualcun altro sta riparando: il caso e' costruito a meta', e la meta'
    --     presa in prestito e' proprio quella che deve cambiare.
    --   ⇒ Il caso possiede tutto cio' che afferma: la tabella nasce qui, senza
    --     policy, senza row level security e senza write-guard, e muore col
    --     `ROLLBACK`. E' scoperta per costruzione, non per congiuntura.
    --   ⚠️ Serve una tabella VERA (`relkind = 'r'`) con una colonna vera: il
    --     livello 1 respinge «tabella inesistente» e «colonna del percorso
    --     inesistente», e la riga arriverebbe li' invece che al livello 2.
    --     ⛔ E non puo' essere temporanea: il presidio cerca lo schema per NOME,
    --     e `pg_temp_<n>` cambia a ogni sessione.
    CREATE TABLE dbops.pgtap_bersaglio_scoperto (
        id                   bigint PRIMARY KEY,
        emittente_fiscale_id bigint
    );

    INSERT INTO dbops.processi_bersagli
        (id, processo_id, schema_tabella, nome_tabella,
         emittente_via, emittente_colonna, note, debito_dichiarato)
    VALUES (9402, v_id, 'dbops', 'pgtap_bersaglio_scoperto',
            'fiscale', 'emittente_fiscale_id',
            'debito dichiarato costruito dal test', true);
END
$dichiarato$;

SELECT is(
    (SELECT stato FROM dbops.vw_processi_dominio_senza_difesa
      WHERE processo_codice = 'PGTAP-DB2-DICHIARATO'),
    'DEBITO_DICHIARATO',
    '5. un bersaglio scoperto ma DICHIARATO si presenta come tale'
);

-- ⛔ E il verso che rende il presidio ancora un presidio: un bersaglio NUOVO,
--   rotto, non dichiarato da nessuno, deve gridare.
DO $allarme$
DECLARE
    v_id dbops.processi.id%TYPE := 9401;
BEGIN
    -- 20261016-20: chi ha una sveglia dichiara l'accensione; un CODA no.
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento)
    VALUES (v_id, 'PGTAP-DB2-ALLARME',
            'processo di prova col percorso su una colonna inesistente',
            'DOMINIO', 'COMMAND', true, true, true, 'PROGRAMMA');

    -- Padre e figlio in DUE istruzioni: una CTE unica condividerebbe la stessa
    -- snapshot e la FK non troverebbe il padre.
    INSERT INTO dbops.processi_bersagli
        (id, processo_id, schema_tabella, nome_tabella,
         emittente_via, emittente_colonna)
    VALUES (9401, v_id, 'vendite', 'fatture', 'fiscale', 'colonna_che_non_esiste');
END
$allarme$;

SELECT is(
    (SELECT stato FROM dbops.vw_processi_dominio_senza_emittente
      WHERE processo_codice = 'PGTAP-DB2-ALLARME'),
    'NON_DICHIARATO',
    '6. un bersaglio nuovo e rotto e'' un ALLARME, non un debito'
);

-- ============================================================
-- 7. Le due viste parlano la stessa lingua
-- ============================================================
-- ⭐ Il frontend le mostra in un pannello solo: se una portasse `stato` e
--   l'altra no, dovrebbe tenere una tabella di eccezioni scritta a mano nel
--   codice — che e' esattamente cio' che questo lavoro toglie.
SELECT is(
    (SELECT count(*)::int
       FROM information_schema.columns
      WHERE table_schema = 'dbops'
        AND table_name IN ('vw_processi_dominio_senza_emittente',
                           'vw_processi_dominio_senza_difesa')
        AND column_name IN ('stato', 'nota')),
    4,
    '7. entrambe le viste portano `stato` e `nota`'
);

-- ============================================================
-- 8. ⛔ Una policy non in vigore non e' una difesa
-- ============================================================
-- Rev 2026-09-05 (changeSet `20260905-26`). `ha_policy` chiedeva soltanto che
-- una policy ESISTESSE. Ma PostgreSQL conserva le policy di una tabella con
-- `ROW LEVEL SECURITY` disabilitata e **non le applica**: bastava scriverne una
-- e non abilitare la RLS per far sparire la riga da questo presidio lasciando
-- la tabella aperta a tutti.
--
-- ⭐ Non e' nato da una misura — nessun bersaglio era in quello stato — ma
--   dalla scorciatoia che si stava per prendere sulla policy di
--   `config.email_outbox`, dove abilitare la RLS avrebbe fermato l'invio delle
--   email. ⛔ Un presidio che si spegne con una decorazione fa credere che il
--   lavoro sia fatto.
--
-- ⚠️ Il caso si COSTRUISCE su un bersaglio che oggi e' difeso davvero: si
--   spegne la RLS, si guarda, e la si riaccende. Cercare una tabella gia' in
--   quello stato avrebbe fatto saltare il test proprio quando la difesa
--   funziona.
DO $rls_spenta$
DECLARE
    v_manca text;
BEGIN
    ALTER TABLE vendite.listini_versioni DISABLE ROW LEVEL SECURITY;

    SELECT manca INTO v_manca
      FROM dbops.vw_processi_dominio_senza_difesa
     WHERE nome_tabella = 'listini_versioni';

    ALTER TABLE vendite.listini_versioni ENABLE ROW LEVEL SECURITY;

    PERFORM set_config('pgtap.manca_rls_spenta', COALESCE(v_manca, ''), true);
END
$rls_spenta$;

SELECT matches(
    current_setting('pgtap.manca_rls_spenta', true),
    'ROW LEVEL SECURITY non e'' attiva',
    '8. una policy con la RLS spenta compare nel presidio, e il motivo lo dice'
);

SELECT * FROM finish();

ROLLBACK;
