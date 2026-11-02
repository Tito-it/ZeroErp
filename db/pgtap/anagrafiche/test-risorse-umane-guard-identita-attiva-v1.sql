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
-- Test: anagrafiche.trgfn_risorse_umane_guard_identita_attiva — una risorsa
--       umana con un'identita' OPERATORE attiva non si disattiva
-- ------------------------------------------------------------
-- Elenco test (plan 8):
-- 1) riferimenti minimi: la funzione, il trigger montato su risorse_umane
--    (BEFORE UPDATE OF attivo), il codice a catalogo con la sua classe
-- 2) fixture: la madre fn_crea_operatore_v2 ha creato utente + identita'
--    OPERATORE + risorsa umana, e l'invito accettato ha acceso la veste
--    (e l'helper li lega)
-- 3) ⭐ RU con identita' attiva -> attivo=false RIFIUTATO (P0001)
-- 4) ... e il codice viaggia nel canale CONSTRAINT: E_RISORSA_UMANA_IDENTITA_ATTIVA
-- 5) ... e la frase nomina l'utente (lo username nel VARIADIC)
-- 6) identita' spenta PRIMA -> la stessa RU si disattiva (passa)
-- 7) ... e il sync z90 (dalla madre) ha spento l'utente: is_active = false
-- 8) il guard sul nome vecchio (vista) non e' piu' montato su risorse_umane
--
-- Scopo:
--  - Fino al 12-09-2026 questa regola viveva PER CASO: il guard di automazione
--    `..._risorse_umane_auth_user_block_deact_upd` leggeva la VISTA col nome
--    vecchio del ponte. Con la vista ritirata (90_end/20260912-26) la regola e'
--    scritta a mano sulla madre (20_code/20260912-18), perche' il legame
--    risorsa umana -> identita' passa da soggetto_ruolo_id e non da una FK: la
--    automazione ATTIVO non lo vede. Decisione Tid 12-09 (analisi
--    analisi-software-per-dati-morti §6.2).
--  - Il test COSTRUISCE il suo operatore con la madre viva (fn_crea_operatore_v2)
--    invece di cercarne uno: un test che itera su cio' che c'e' passa a vuoto in
--    CI, dove anagrafiche e' vuoto (AGENTS, regola zero — corollario sui test).
--  - ⚠️ throws_ok porta SEMPRE lo SQLSTATE; il codice si legge dal canale
--    CONSTRAINT (contratto P0001 + CONSTRAINT = codice di dominio, api.md).
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE. Senza, un fallimento a meta' lascia i dati di prova nel
--   database e rompe la corsa successiva.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: il test gira come `zeroerp_app` con la RLS attiva;
--   la madre fn_crea_operatore_v2 scrive dove scrive l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ VINCOLI DIFFERITI — ⭐ LA FINESTRA SI RIAPRE, NON SI PRESUME.
--   La madre fn_crea_operatore_v2 non nasce completa in un'istruzione (punto 3
--   qui sotto): vuole i guard di `soggetti` DIFFERITI.
--   ⛔ Ma la riga di contesto qui sopra, quando COSTRUISCE il mondo (database
--   senza operatori: lo scratch `zeroerp_ci`, la CI), ESCE CON I VINCOLI
--   IMMEDIATE (rev 20260921-18, come ogni helper pgTAP). Fino al 2026-09-23 lo
--   mascherava un residuo: `create-gestore-conto-*` committavano l'operatore
--   `PGTR0001` e da li' la riga non costruiva piu'. Tolto quel COMMIT (brief
--   fixture-che-costruiscono giro 2), lo scratch appena ricostruito ha dato
--   ERRORE_FIXTURE: «Indirizzo obbligatorio mancante per soggetto …»
--   all'INSERT del soggetto.
--   La finestra la riapre il file, e dice da se' cosa vuole.
SET CONSTRAINTS ALL DEFERRED;

-- ⚠️ 3. VINCOLI DIFFERITI: QUESTO FILE NON USA `SET CONSTRAINTS ALL IMMEDIATE`,
--   esenzione dichiarata in testa (`pgtap-differiti: escluso`) con la ragione:
--   la madre fn_crea_operatore_v2 non puo' nascere completa in una istruzione.

SELECT plan(8);

-- ============================================================
-- 1) Riferimenti minimi
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM (
        SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'anagrafiche' AND p.proname = 'trgfn_risorse_umane_guard_identita_attiva'
        UNION ALL
        SELECT 1 FROM pg_trigger t
         WHERE t.tgrelid = 'anagrafiche.risorse_umane'::regclass
           AND t.tgname = 'trg_risorse_umane_a10_guard_identita_attiva_upd'
           AND NOT t.tgisinternal
        UNION ALL
        SELECT 1 FROM config.codici_errore c
         WHERE c.codice = 'E_RISORSA_UMANA_IDENTITA_ATTIVA'
           AND c.classe = 'CONFLITTO_STATO'
           AND c.obsoleto_dal IS NULL
    ) x),
    3,
    '1) funzione, trigger su risorse_umane e codice a catalogo (CONFLITTO_STATO) esistono'
);

-- ============================================================
-- Fixture: un operatore VERO, costruito dalla madre. CF valido gia' in uso
-- nei test di anagrafiche (LCCRLD80A01L736X); username univoco per corsa.
-- ⭐ Rev 2026-09-25 (brief-db-blocco-login-per-credenziale §12, 20260925-42):
--   la madre ritorna una TABLE (si legge con FROM) e crea la veste OPERATORE
--   SPENTA; in esercizio la accende l'attivazione dell'invito (il backend).
--   Qui si fa lo stesso passo, subito dopo: la regola sotto prova e' quella
--   dell'identita' ATTIVA.
-- ============================================================
CREATE TEMP TABLE tmp_guard_ctx AS
SELECT m.auth_user_id
  FROM anagrafiche.fn_crea_operatore_v2(
        p_cognome                := 'Guard',
        p_nome                   := 'Prova',
        p_codice_fiscale         := 'LCCRLD80A01L736X',
        p_username               := 'pgtap_guard_ru_' || floor(random() * 1000000)::text,
        p_email                  := 'pgtap_guard_ru_' || floor(random() * 1000000)::text || '@test.local',
        p_password_hash          := 'pbkdf2_sha256$600000$test$hash_placeholder==',
        p_qualifica_id           := (SELECT id FROM config.qualifiche           WHERE attivo ORDER BY id LIMIT 1),
        p_unita_organizzativa_id := (SELECT id FROM config.unita_organizzative WHERE attivo ORDER BY id LIMIT 1),
        p_data_nascita           := DATE '1980-01-01',
        p_sesso                  := 'M'
    ) m;

-- L'invito accettato: la veste OPERATORE si accende.
UPDATE anagrafiche.identita_digitali i
   SET attivo = true
  FROM tmp_guard_ctx c
 WHERE i.auth_user_id = c.auth_user_id
   AND i.ruolo_applicativo = 'OPERATORE';

ALTER TABLE tmp_guard_ctx ADD COLUMN risorsa_umana_id bigint;
UPDATE tmp_guard_ctx c
   SET risorsa_umana_id = ru.id
  FROM anagrafiche.identita_digitali i
  JOIN anagrafiche.risorse_umane ru ON ru.soggetto_ruolo_id = i.soggetto_ruolo_id
 WHERE i.auth_user_id = c.auth_user_id
   AND i.ruolo_applicativo = 'OPERATORE';

-- ============================================================
-- 2) La fixture e' in piedi, e l'helper della madre la lega nel verso RU -> utente
-- ============================================================
SELECT is(
    (SELECT script.fn_get_auth_user_id_for_risorsa_umana(risorsa_umana_id) FROM tmp_guard_ctx),
    (SELECT auth_user_id FROM tmp_guard_ctx),
    '2) fixture: identita'' OPERATORE attiva + risorsa umana, legate da fn_get_auth_user_id_for_risorsa_umana'
);

-- ============================================================
-- 3) Con l'identita' attiva la RU NON si disattiva: P0001
-- ============================================================
SELECT throws_ok(
    $$UPDATE anagrafiche.risorse_umane SET attivo = false
       WHERE id = (SELECT risorsa_umana_id FROM tmp_guard_ctx)$$,
    'P0001',
    NULL,
    '3) RU con identita'' OPERATORE attiva: attivo=false rifiutato (P0001)'
);

-- ============================================================
-- 4) Il codice viaggia strutturato nel canale CONSTRAINT (contratto BE)
-- 5) La frase nomina l'utente: e' il valore del VARIADIC, non un parametro
-- ============================================================
CREATE TEMP TABLE tmp_guard_err (constraint_name text, message_text text);
DO $$
DECLARE v_c text; v_m text;
BEGIN
    BEGIN
        UPDATE anagrafiche.risorse_umane SET attivo = false
         WHERE id = (SELECT risorsa_umana_id FROM tmp_guard_ctx);
    EXCEPTION WHEN SQLSTATE 'P0001' THEN
        GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME, v_m = MESSAGE_TEXT;
        INSERT INTO tmp_guard_err VALUES (v_c, v_m);
    END;
END $$;

SELECT is(
    (SELECT constraint_name FROM tmp_guard_err),
    'E_RISORSA_UMANA_IDENTITA_ATTIVA',
    '4) il codice arriva nel canale CONSTRAINT: E_RISORSA_UMANA_IDENTITA_ATTIVA'
);

SELECT ok(
    (SELECT message_text FROM tmp_guard_err)
        LIKE '%' || (SELECT au.username FROM django.auth_user au JOIN tmp_guard_ctx c ON c.auth_user_id = au.id) || '%',
    '5) la frase nomina l''utente ancora attivo (lo username, dal VARIADIC)'
);

-- ============================================================
-- 6) Identita' spenta PRIMA: la stessa RU si disattiva («figli prima, padre poi»)
-- ============================================================
UPDATE anagrafiche.identita_digitali
   SET attivo = false
 WHERE auth_user_id = (SELECT auth_user_id FROM tmp_guard_ctx)
   AND ruolo_applicativo = 'OPERATORE';

SELECT lives_ok(
    $$UPDATE anagrafiche.risorse_umane SET attivo = false
       WHERE id = (SELECT risorsa_umana_id FROM tmp_guard_ctx)$$,
    '6) con l''identita'' gia'' spenta la RU si disattiva'
);

-- ============================================================
-- 7) Il sync z90 e' passato dalla madre: l'utente e' spento
-- ============================================================
SELECT is(
    (SELECT au.is_active FROM django.auth_user au JOIN tmp_guard_ctx c ON c.auth_user_id = au.id),
    false,
    '7) trgfn_risorse_umane_sync_auth_user_active (dalla madre) ha messo is_active = false'
);

-- ============================================================
-- 8) Il guard sul nome vecchio non c'e' piu' (00_schema/20260912-19)
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_trigger t
      WHERE t.tgrelid = 'anagrafiche.risorse_umane'::regclass
        AND NOT t.tgisinternal
        AND pg_get_triggerdef(t.oid) ~ 'risorse_umane_auth_user'),
    0,
    '8) nessun trigger su risorse_umane nomina piu'' il ponte vecchio (00_schema/20260912-19)'
);

-- ⚠️ NIENTE cleanup in coda: ci pensa il ROLLBACK.
SELECT * FROM finish();
ROLLBACK;
