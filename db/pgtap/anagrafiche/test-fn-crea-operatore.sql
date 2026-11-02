-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-differiti: escluso — la fixture costruisce un OPERATORE con la madre
--   fn_crea_operatore_v2, che passa da fn_crea_soggetto_pf: per contratto del
--   dominio quel soggetto nasce SENZA indirizzo, e il guard sugli indirizzi e'
--   DEFERRABLE INITIALLY DEFERRED — la completezza si verifica al COMMIT, che
--   qui non arriva mai. Con IMMEDIATE la madre fallirebbe all'INSERT del
--   soggetto (E_INDIRIZZO_OBBLIGATORIO_MANCANTE): provato il 12-09-2026.
--   Stessa esenzione, stessa ragione, di test-fn-crea-risorsa-umana. Debito
--   noto (§22.4): quando la madre potra' nascere completa (indirizzo nella
--   stessa unita' di lavoro), si toglie questa riga e si rimette IMMEDIATE.
-- pgTAP test per Zero ERP
--
-- Test anagrafiche.fn_crea_operatore_v2 (orchestratore) e i suoi building block
-- (fn_crea_auth_user, fn_crea_soggetto_pf, fn_crea_risorsa_umana_v2).
--
-- Elenco test (plan 12):
--   1. Precondizione: esiste UO attiva e qualifica attiva
--   2. Creazione operatore con successo (la v2 torna l'auth_user_id, in una TABLE)
--   3. auth_user creato con username corretto
--   4. auth_user.email corretta
--   5. Catena soggetto -> ruolo -> risorsa_umana -> identita' OPERATORE SPENTA
--   6. Soggetto ha tipo_soggetto_dettaglio_id = PR (Privato PF)
--   7. Contatto default creato con email corretta
--   8. Errore: username duplicato       (E_ADMIN_USERNAME_DUPLICATO)
--   9. Errore: email gia' di un operatore, anche in MAIUSCOLO (E_CREDENZIALE_GIA_OPERATORE)
--  10. Errore: codice fiscale duplicato (E_ADMIN_CF_DUPLICATO)
--  11. Errore: UO inesistente           (E_ADMIN_UO_NON_TROVATA)
--  12. Errore: cognome vuoto            (E_ADMIN_VALIDAZIONE)
--
-- ⭐ Riscritto sulla v2 il 12-09-2026 (decisione Tid, analisi
--   analisi-software-per-dati-morti §6.7). Fino a quel giorno chiamava
--   fn_crea_operatore (v1) con `p_ruolo_sistema config.ruolo_sistema`: funzione
--   ed enum RIMOSSI nella Fase 7 del multi-face (29-04-2026). Da allora il file
--   si rompeva nella fixture — in baseline ERRORE_FIXTURE — cioe' eseguiva ZERO
--   asserzioni: la funzione con cui si crea ogni operatore non aveva un test.
--   Cosa cambia col modello nuovo:
--     · `p_ruolo_sistema` non esiste: la v2 prende `p_is_super_admin` e `p_attivo`;
--     · il «bridge» risorse_umane_auth_user non esiste (tabella e vista ritirate
--       il 12-09-2026): la catena arriva a `identita_digitali` con
--       `ruolo_applicativo = 'OPERATORE'`, legata a `risorse_umane` per
--       `soggetto_ruolo_id`;
--     · i messaggi NON portano piu' il codice (dal 2026-08-05 il codice viaggia
--       nel canale CONSTRAINT): i throws_matching cercano la FRASE a catalogo,
--       e il codice si legge dal canale, nel test 8.
--
-- ⭐ Rev 2026-09-25 (brief-db-blocco-login-per-credenziale §12, changeSet
--   20260925-42). La madre:
--     · ritorna TABLE(auth_user_id, username, credenziale_riusata): si legge
--       con SELECT … FROM (test 2); `p_attivo` e' uscito dalla firma;
--     · crea la veste OPERATORE SPENTA — la accende l'attivazione dell'invito
--       (regola unica, R-2): il test 5 lo pretende;
--     · RIUSA la credenziale di un'email esistente (D-6) e rifiuta quella che
--       ha gia' una veste OPERATORE: il test 9, che era «email duplicata», e'
--       ora quel rifiuto — con l'email in MAIUSCOLO, che prova anche il
--       confronto senza maiuscole (D-9). Il riuso vero e proprio sta in
--       test-crea-operatore-riusa-credenziale-v1.sql.
-- ------------------------------------------------------------
BEGIN;

-- ⚠️ QUESTO FILE NON USA `SET CONSTRAINTS ALL IMMEDIATE`: esenzione dichiarata
--   in testa (`pgtap-differiti: escluso`), con la ragione. ⚠️ Resta un buco reale:
--   i guard differiti di anagrafiche.soggetti non vengono esercitati qui, e la
--   fixture lascia un soggetto che l'applicazione non potrebbe committare.
--   Brief: brief-db-pgtap-runner-rls-baseline §21.

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ VINCOLI DIFFERITI — ⭐ LA FINESTRA SI RIAPRE, NON SI PRESUME.
--   La madre dell'operatore non nasce completa in un'istruzione (esenzione
--   dichiarata sopra): vuole i guard di `soggetti` DIFFERITI.
--   ⛔ Ma la riga di contesto qui sopra, quando COSTRUISCE il mondo (database
--   senza operatori: lo scratch `zeroerp_ci`, la CI), ESCE CON I VINCOLI
--   IMMEDIATE (rev 20260921-18, come ogni helper pgTAP). Fino al 2026-09-23 lo
--   mascherava un residuo: `create-gestore-conto-*` committavano l'operatore
--   `PGTR0001` e da li' la riga non costruiva piu'. Tolto quel COMMIT (brief
--   fixture-che-costruiscono giro 2), lo scratch appena ricostruito ha dato
--   rossi di ASSERZIONE: la madre rifiutata a meta' saga.
--   La finestra la riapre il file, e dice da se' cosa vuole.
SET CONSTRAINTS ALL DEFERRED;

SELECT plan(12);

-- =========================================================
-- Setup: variabili temporanee
-- =========================================================
CREATE TEMP TABLE tmp_crea_op_ctx (
  uo_id          integer,
  qualifica_id   integer,
  auth_user_id   integer,
  test_username  text,
  test_email     text,
  test_cf        text
);

INSERT INTO tmp_crea_op_ctx (uo_id, qualifica_id, test_username, test_email, test_cf)
SELECT
  uo.id,
  q.id,
  'test_op_' || floor(random() * 1000000)::text,
  'test_op_' || floor(random() * 1000000)::text || '@test.local',
  'LCCRLD80A01L736X'
FROM config.unita_organizzative uo
  CROSS JOIN config.qualifiche q
WHERE uo.attivo = true
  AND q.attivo = true
LIMIT 1;

-- =========================================================
-- 1) Precondizione
-- =========================================================
SELECT ok(
    (SELECT count(*) FROM tmp_crea_op_ctx WHERE uo_id IS NOT NULL AND qualifica_id IS NOT NULL) = 1,
    '1. Esiste almeno una UO attiva e una qualifica attiva per il test'
  );

-- =========================================================
-- 2) Creazione operatore con successo — la v2 TORNA l'auth_user_id
-- =========================================================
SELECT lives_ok(
    format(
      $$UPDATE tmp_crea_op_ctx SET auth_user_id = (SELECT m.auth_user_id FROM anagrafiche.fn_crea_operatore_v2(
        p_cognome := 'Rossi',
        p_nome := 'Mario',
        p_codice_fiscale := %L,
        p_data_nascita := '1990-01-15',
        p_sesso := 'M',
        p_username := %L,
        p_email := %L,
        p_password_hash := 'pbkdf2_sha256$600000$test$hash_placeholder==',
        p_qualifica_id := %s,
        p_unita_organizzativa_id := %s,
        p_is_super_admin := false
      ) m) $$,
      (SELECT test_cf FROM tmp_crea_op_ctx),
      (SELECT test_username FROM tmp_crea_op_ctx),
      (SELECT test_email FROM tmp_crea_op_ctx),
      (SELECT qualifica_id FROM tmp_crea_op_ctx),
      (SELECT uo_id FROM tmp_crea_op_ctx)
    ),
    '2. fn_crea_operatore_v2 eseguita senza errori'
  );

-- =========================================================
-- 3) auth_user creato: il valore di ritorno e' l'id dell'utente con quello username
-- =========================================================
SELECT is(
    (SELECT auth_user_id FROM tmp_crea_op_ctx),
    (SELECT id FROM django.auth_user WHERE username = (SELECT test_username FROM tmp_crea_op_ctx)),
    '3. auth_user creato con username corretto (e la v2 ne torna l''id)'
  );

SELECT is(
    (SELECT email::text FROM django.auth_user
     WHERE id = (SELECT auth_user_id FROM tmp_crea_op_ctx)),
    (SELECT test_email FROM tmp_crea_op_ctx),
    '4. auth_user.email corretta'
  );

-- =========================================================
-- 5) Catena: soggetto + ruolo + risorsa umana + identita' OPERATORE SPENTA
--    (era «bridge risorse_umane_auth_user» con ruolo_sistema = OPERATIVO;
--     nel modello nuovo: identita_digitali OPERATORE, non super admin).
--    ⭐ Rev 2026-09-25: SPENTA — la accende l'attivazione dell'invito (R-2).
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1
      FROM anagrafiche.identita_digitali i
        JOIN anagrafiche.risorse_umane ru ON ru.soggetto_ruolo_id = i.soggetto_ruolo_id
        JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ru.soggetto_ruolo_id
        JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
      WHERE i.auth_user_id = (SELECT auth_user_id FROM tmp_crea_op_ctx)
        AND i.ruolo_applicativo = 'OPERATORE'
        AND i.attivo = false
        AND s.cognome = 'Rossi'
        AND s.nome = 'Mario'
        AND NOT script.fn_is_super_admin((SELECT auth_user_id FROM tmp_crea_op_ctx))
    ),
    '5. Catena soggetto -> ruolo -> risorsa_umana -> identita'' OPERATORE SPENTA (la accende l''invito), non super admin'
  );

-- =========================================================
-- 6) Soggetto ha tipo_soggetto_dettaglio = PR (Privato PF)
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1
      FROM anagrafiche.soggetti s
        JOIN anagrafiche.soggetti_ruoli sr ON sr.soggetto_id = s.id
        JOIN anagrafiche.identita_digitali i ON i.soggetto_ruolo_id = sr.id
        JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id
      WHERE i.auth_user_id = (SELECT auth_user_id FROM tmp_crea_op_ctx)
        AND tsd.codice_interno = 'PR'
    ),
    '6. Soggetto ha tipo_soggetto_dettaglio_id = PR (Privato PF)'
  );

-- =========================================================
-- 7) Contatto default creato
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1
      FROM anagrafiche.contatti c
        JOIN anagrafiche.soggetti s ON s.id = c.soggetto_id
        JOIN anagrafiche.soggetti_ruoli sr ON sr.soggetto_id = s.id
        JOIN anagrafiche.identita_digitali i ON i.soggetto_ruolo_id = sr.id
      WHERE i.auth_user_id = (SELECT auth_user_id FROM tmp_crea_op_ctx)
        AND c.is_default = true
        AND c.email = (SELECT test_email FROM tmp_crea_op_ctx)
    ),
    '7. Contatto default creato con email corretta'
  );

-- =========================================================
-- 8) Errore: username duplicato — il codice si legge dal canale CONSTRAINT
--    (dal 2026-08-05 il messaggio NON porta il codice: matcharlo nel testo
--     sarebbe verde per sottrazione).
-- =========================================================
CREATE TEMP TABLE tmp_crea_op_err (constraint_name text);
DO $$
DECLARE v_c text;
BEGIN
    BEGIN
        PERFORM anagrafiche.fn_crea_operatore_v2(
            p_cognome := 'Bianchi',
            p_nome := 'Luca',
            p_codice_fiscale := 'TSTDUP' || lpad(floor(random() * 10000000)::text, 10, '0'),
            p_username := (SELECT test_username FROM tmp_crea_op_ctx),
            p_email := 'altro_' || (SELECT test_email FROM tmp_crea_op_ctx),
            p_password_hash := 'pbkdf2_sha256$600000$test$hash==',
            p_qualifica_id := (SELECT qualifica_id FROM tmp_crea_op_ctx),
            p_unita_organizzativa_id := (SELECT uo_id FROM tmp_crea_op_ctx),
            p_sesso := 'M'
        );
    EXCEPTION WHEN SQLSTATE 'P0001' THEN
        GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
        INSERT INTO tmp_crea_op_err VALUES (v_c);
    END;
END $$;

SELECT is(
    (SELECT constraint_name FROM tmp_crea_op_err),
    'E_ADMIN_USERNAME_DUPLICATO',
    '8. Errore username duplicato (E_ADMIN_USERNAME_DUPLICATO nel canale CONSTRAINT)'
  );

-- =========================================================
-- 9) Errore: l'email e' gia' di un operatore — scritta in MAIUSCOLO.
--    Rev 2026-09-25: la madre riusa la credenziale dell'email (D-6), e questa
--    ha gia' la veste OPERATORE del test 2 (spenta): E_CREDENZIALE_GIA_OPERATORE.
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_operatore_v2(
        p_cognome := 'Verdi',
        p_nome := 'Anna',
        p_codice_fiscale := 'TSTDUP' || lpad(floor(random() * 10000000)::text, 10, '0'),
        p_username := 'altro_user_unico_' || floor(random() * 1000000)::text,
        p_email := %L,
        p_password_hash := 'pbkdf2_sha256$600000$test$hash==',
        p_qualifica_id := %s,
        p_unita_organizzativa_id := %s,
        p_sesso := 'M'
      ) $$,
      (SELECT upper(test_email) FROM tmp_crea_op_ctx),
      (SELECT qualifica_id FROM tmp_crea_op_ctx),
      (SELECT uo_id FROM tmp_crea_op_ctx)
    ),
    'appartiene gia',
    '9. Email (in maiuscolo) gia'' di un operatore -> E_CREDENZIALE_GIA_OPERATORE'
  );

-- =========================================================
-- 10) Errore: codice fiscale duplicato
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_operatore_v2(
        p_cognome := 'Neri',
        p_nome := 'Paolo',
        p_codice_fiscale := %L,
        p_username := 'user_cf_dup_' || floor(random() * 1000000)::text,
        p_email := 'cf_dup_' || floor(random() * 1000000)::text || '@test.local',
        p_password_hash := 'pbkdf2_sha256$600000$test$hash==',
        p_qualifica_id := %s,
        p_unita_organizzativa_id := %s,
        p_sesso := 'M'
      ) $$,
      (SELECT test_cf FROM tmp_crea_op_ctx),
      (SELECT qualifica_id FROM tmp_crea_op_ctx),
      (SELECT uo_id FROM tmp_crea_op_ctx)
    ),
    'Codice fiscale gia',
    '10. Errore codice fiscale duplicato (E_ADMIN_CF_DUPLICATO)'
  );

-- =========================================================
-- 11) Errore: UO inesistente
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_operatore_v2(
        p_cognome := 'Test',
        p_nome := 'UO',
        p_codice_fiscale := 'PNZFDN78A01L219Y',
        p_username := 'user_uo_ines_' || floor(random() * 1000000)::text,
        p_email := 'uo_ines_' || floor(random() * 1000000)::text || '@test.local',
        p_password_hash := 'pbkdf2_sha256$600000$test$hash==',
        p_qualifica_id := %s,
        p_unita_organizzativa_id := -999,
        p_sesso := 'M'
      ) $$,
      (SELECT qualifica_id FROM tmp_crea_op_ctx)
    ),
    'non trovata o non attiva',
    '11. Errore UO inesistente (E_ADMIN_UO_NON_TROVATA)'
  );

-- =========================================================
-- 12) Errore: cognome vuoto (soggetto nuovo senza cognome)
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_operatore_v2(
        p_cognome := '',
        p_nome := 'Test',
        p_codice_fiscale := 'PNZFDN78A01L219Y',
        p_username := 'user_cognome_vuoto_' || floor(random() * 1000000)::text,
        p_email := 'cognome_vuoto_' || floor(random() * 1000000)::text || '@test.local',
        p_password_hash := 'pbkdf2_sha256$600000$test$hash==',
        p_qualifica_id := %s,
        p_unita_organizzativa_id := %s,
        p_sesso := 'M'
      ) $$,
      (SELECT qualifica_id FROM tmp_crea_op_ctx),
      (SELECT uo_id FROM tmp_crea_op_ctx)
    ),
    'Cognome obbligatorio',
    '12. Errore cognome vuoto (E_ADMIN_VALIDAZIONE)'
  );

SELECT * FROM finish();
ROLLBACK;
