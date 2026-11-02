-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-differiti: escluso — la fixture non soddisfa un vincolo DIFFERITO e la
--   ragione e' scritta per esteso piu' sotto. Debito noto (§22.4): quando la
--   fixture viene completata, si toglie questa riga e si rimette il
--   SET CONSTRAINTS ALL IMMEDIATE nel punto in cui l'unita' di lavoro e' completa.
-- pgTAP test per Zero ERP
--
-- Test anagrafiche.fn_crea_risorsa_umana_v2 (building block):
--   1. Precondizione: esiste qualifica attiva e UO attiva
--   2. Setup: soggetto PF 1 (senza utente)
--   3. Setup: soggetto PF 2 (con utente)
--   4. Creazione risorsa umana SENZA utente (nessuna identita' nasce)
--   5. Verifica risorse_umane creato con ruolo RIS_UMANA
--   6. Creazione risorsa umana CON utente (p_auth_user_id)
--   7. Verifica: e' nata l'identita' digitale OPERATORE attiva, legata alla RU
--   8. Errore: soggetto_id NULL   (E_ADMIN_VALIDAZIONE)
--   9. Errore: UO inesistente     (E_ADMIN_UO_NON_TROVATA)
--
-- ⭐ Riscritto sulla v2 il 12-09-2026 (decisione Tid, analisi
--   analisi-software-per-dati-morti §6.7). Fino a quel giorno chiamava
--   fn_crea_risorsa_umana (v1) con `p_ruolo_sistema config.ruolo_sistema`:
--   funzione ed enum RIMOSSI nella Fase 7 del multi-face (29-04-2026). Da allora
--   il file si rompeva nella fixture — in baseline ERRORE_FIXTURE — cioe'
--   eseguiva ZERO asserzioni. Col modello nuovo la v2 prende `p_is_super_admin`
--   e `p_attivo`, e il «bridge» e' una riga di `identita_digitali` con
--   `ruolo_applicativo = 'OPERATORE'` sullo stesso `soggetto_ruolo_id` della RU
--   (il nome vecchio risorse_umane_auth_user e' stato ritirato il 12-09-2026).
-- ------------------------------------------------------------
BEGIN;

-- ⚠️ QUESTO FILE NON USA `SET CONSTRAINTS ALL IMMEDIATE`, a differenza degli
--   altri, e non e' una dimenticanza.
--   `anagrafiche.soggetti` ha TRE guard DEFERRABLE INITIALLY DEFERRED —
--   indirizzi, contatti, dati societari — e li' la deferralita' e' il CONTRATTO
--   DEL DOMINIO: si crea il soggetto, poi il suo indirizzo, e la completezza si
--   verifica al COMMIT. E' per questo che anagrafiche.fn_crea_soggetto_pf puo'
--   restituire un soggetto ancora incompleto, ed e' cosi' che la usa il backend.
--   Forzare IMMEDIATE pretenderebbe l'indirizzo nell'istante stesso dell'INSERT
--   del soggetto: vieterebbe il pattern che il dominio ha scelto.
--   ⚠️ Resta un buco reale: senza la riga quei guard non vengono esercitati da
--   questo test, e la fixture lascia un soggetto che l'applicazione non
--   potrebbe committare. La correzione vera e' COMPLETARE LA FIXTURE
--   (indirizzo + contatti): allora la riga si rimette e il test verifica sul
--   serio. Brief: brief-db-pgtap-runner-rls-baseline §21.

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ VINCOLI DIFFERITI — ⭐ LA FINESTRA SI RIAPRE, NON SI PRESUME.
--   La persona fisica nasce, POI riceve indirizzo e contatti (esenzione
--   dichiarata sopra): vuole i guard di `soggetti` DIFFERITI.
--   ⛔ Ma la riga di contesto qui sopra, quando COSTRUISCE il mondo (database
--   senza operatori: lo scratch `zeroerp_ci`, la CI), ESCE CON I VINCOLI
--   IMMEDIATE (rev 20260921-18, come ogni helper pgTAP). Fino al 2026-09-23 lo
--   mascherava un residuo: `create-gestore-conto-*` committavano l'operatore
--   `PGTR0001` e da li' la riga non costruiva piu'. Tolto quel COMMIT (brief
--   fixture-che-costruiscono giro 2), lo scratch appena ricostruito ha dato
--   rossi di ASSERZIONE: il soggetto rifiutato all'INSERT.
--   La finestra la riapre il file, e dice da se' cosa vuole.
SET CONSTRAINTS ALL DEFERRED;

SELECT plan(9);

-- =========================================================
-- Setup
-- =========================================================
CREATE TEMP TABLE tmp_ru_ctx (
  qualifica_id    integer,
  uo_id           integer,
  soggetto_id_1   uuid,
  soggetto_id_2   uuid,
  auth_user_id    integer,
  ru_id_1         bigint,
  ru_id_2         bigint
);

-- =========================================================
-- 1) Precondizione: qualifica e UO attive
-- =========================================================
INSERT INTO tmp_ru_ctx (qualifica_id, uo_id)
SELECT q.id, uo.id
FROM config.qualifiche q
  CROSS JOIN config.unita_organizzative uo
WHERE q.attivo = true
  AND uo.attivo = true
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_ru_ctx WHERE qualifica_id IS NOT NULL AND uo_id IS NOT NULL) = 1,
    '1. Esiste almeno una qualifica attiva e una UO attiva'
  );

-- =========================================================
-- 2) Setup: crea 2 soggetti PF di supporto + 1 auth_user
-- =========================================================

-- Soggetto 1 (senza auth_user)
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_soggetto_pf(
        p_cognome := 'TestRU',
        p_nome := 'SenzaBridge',
        p_codice_fiscale := %L,
        p_email := %L,
        p_sesso := 'M',
        p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR')
      ) $$,
      'PNZFDN78A01L219Y',
      'test_ru_senza_' || floor(random() * 1000000)::text || '@test.local'
    ),
    '2. Soggetto PF 1 creato per test senza bridge'
  );

UPDATE tmp_ru_ctx
SET soggetto_id_1 = (
    SELECT id FROM anagrafiche.soggetti
    WHERE cognome = 'TestRU' AND nome = 'SenzaBridge'
    ORDER BY data_insert DESC LIMIT 1
  );

-- Soggetto 2 (con auth_user)
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_soggetto_pf(
        p_cognome := 'TestRU',
        p_nome := 'ConBridge',
        p_codice_fiscale := %L,
        p_email := %L,
        p_sesso := 'M',
        p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR')
      ) $$,
      'PRAFNC80A01F205N',
      'test_ru_con_' || floor(random() * 1000000)::text || '@test.local'
    ),
    '3. Soggetto PF 2 creato per test con bridge'
  );

UPDATE tmp_ru_ctx
SET soggetto_id_2 = (
    SELECT id FROM anagrafiche.soggetti
    WHERE cognome = 'TestRU' AND nome = 'ConBridge'
    ORDER BY data_insert DESC LIMIT 1
  );

-- Auth user per bridge
UPDATE tmp_ru_ctx
SET auth_user_id = (
    SELECT anagrafiche.fn_crea_auth_user(
      p_username := 'test_ru_bridge_' || floor(random() * 1000000)::text,
      p_email := 'test_ru_bridge_' || floor(random() * 1000000)::text || '@test.local',
      p_password_hash := 'pbkdf2_sha256$600000$test$hash=='
    )
  );

-- =========================================================
-- 4) Creazione risorsa umana SENZA bridge
-- =========================================================
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_risorsa_umana_v2(
        p_soggetto_id := %L::uuid,
        p_qualifica_id := %s,
        p_unita_organizzativa_id := %s
      ) $$,
      (SELECT soggetto_id_1 FROM tmp_ru_ctx),
      (SELECT qualifica_id FROM tmp_ru_ctx),
      (SELECT uo_id FROM tmp_ru_ctx)
    ),
    '4. fn_crea_risorsa_umana_v2 senza utente eseguita'
  );

-- =========================================================
-- 5) Verifica risorse_umane con ruolo RIS_UMANA
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1
      FROM anagrafiche.risorse_umane ru
        JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ru.soggetto_ruolo_id
        JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
      WHERE ru.soggetto_id = (SELECT soggetto_id_1 FROM tmp_ru_ctx)
        AND tr.codice_interno = 'RIS_UMANA'
        AND ru.attivo = true
    ),
    '5. Risorsa umana creata con ruolo RIS_UMANA'
  );

-- =========================================================
-- 6) Creazione risorsa umana CON bridge auth_user
-- =========================================================
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_risorsa_umana_v2(
        p_soggetto_id := %L::uuid,
        p_qualifica_id := %s,
        p_unita_organizzativa_id := %s,
        p_auth_user_id := %s,
        p_is_super_admin := false,
        p_attivo := true
      ) $$,
      (SELECT soggetto_id_2 FROM tmp_ru_ctx),
      (SELECT qualifica_id FROM tmp_ru_ctx),
      (SELECT uo_id FROM tmp_ru_ctx),
      (SELECT auth_user_id FROM tmp_ru_ctx)
    ),
    '6. fn_crea_risorsa_umana_v2 con utente eseguita'
  );

-- =========================================================
-- 7) Verifica: identita' digitale OPERATORE attiva, sullo stesso
--    soggetto_ruolo della RU (era «bridge risorse_umane_auth_user» con
--    ruolo_sistema = OPERATIVO: oggi e' OPERATORE + attivo + non super admin)
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1
      FROM anagrafiche.identita_digitali i
        JOIN anagrafiche.risorse_umane ru ON ru.soggetto_ruolo_id = i.soggetto_ruolo_id
      WHERE i.auth_user_id = (SELECT auth_user_id FROM tmp_ru_ctx)
        AND ru.soggetto_id = (SELECT soggetto_id_2 FROM tmp_ru_ctx)
        AND i.ruolo_applicativo = 'OPERATORE'
        AND i.attivo = true
        AND NOT script.fn_is_super_admin((SELECT auth_user_id FROM tmp_ru_ctx))
    ),
    '7. Identita'' digitale OPERATORE attiva creata e legata alla risorsa umana'
  );

-- =========================================================
-- 8) Errore: soggetto_id NULL
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_risorsa_umana_v2(
        p_soggetto_id := NULL,
        p_qualifica_id := %s
      ) $$,
      (SELECT qualifica_id FROM tmp_ru_ctx)
    ),
    'Soggetto obbligatorio',
    '8. Errore soggetto_id NULL (E_ADMIN_VALIDAZIONE)'
  );

-- =========================================================
-- 9) Errore: UO inesistente
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_risorsa_umana_v2(
        p_soggetto_id := %L::uuid,
        p_qualifica_id := %s,
        p_unita_organizzativa_id := -999
      ) $$,
      (SELECT soggetto_id_1 FROM tmp_ru_ctx),
      (SELECT qualifica_id FROM tmp_ru_ctx)
    ),
    'non trovata o non attiva',
    '9. Errore UO inesistente (E_ADMIN_UO_NON_TROVATA)'
  );

SELECT * FROM finish();
ROLLBACK;
