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
--  5) ⭐ DB-2: la riga del livello 2 DICE di essere attesa
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
SELECT throws_ok(
    $$INSERT INTO config.email_outbox
          (ambito, destinatario, oggetto, corpo_html, stato)
      VALUES ('OPERATORE', 'pgtap@example.invalid', 'pgtap', '<p/>', 'DRAFT')$$,
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
-- `config.email_outbox` ha il percorso (changeSet -18) ma non ancora la policy:
-- e' un debito con un nome, e la vista deve dirlo invece di sembrare un allarme.
SELECT is(
    (SELECT stato FROM dbops.vw_processi_dominio_senza_difesa
      WHERE nome_tabella = 'email_outbox'),
    'DEBITO_DICHIARATO',
    '5. la riga attesa nel livello 2 si DICHIARA'
);

-- ⛔ E il verso che rende il presidio ancora un presidio: un bersaglio NUOVO,
--   rotto, non dichiarato da nessuno, deve gridare.
DO $allarme$
DECLARE
    v_id dbops.processi.id%TYPE := 9401;
BEGIN
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale)
    VALUES (v_id, 'PGTAP-DB2-ALLARME',
            'processo di prova col percorso su una colonna inesistente',
            'DOMINIO', 'COMMAND');

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
