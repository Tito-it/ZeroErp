-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-differiti: escluso — la fixture non soddisfa un vincolo DIFFERITO e la
--   ragione e' scritta per esteso piu' sotto. Debito noto (§22.4): quando la
--   fixture viene completata, si toglie questa riga e si rimette il
--   SET CONSTRAINTS ALL IMMEDIATE nel punto in cui l'unita' di lavoro e' completa.
-- pgTAP test per Zero ERP
--
-- Test: script.fn_scope_ef_whitelist (PK) + fn_scope_ef_whitelist_via_sr (SR)
-- Riferimento: brief RLS §1/§2. Dopo il refactor 20260601-06..09 le fn
-- delegano alla canonica script.fn_check_user_emittente_scope
-- (chiave auth_user_id, convenzione PK emittente_fiscale_id), con adapter
-- SR che risolve emittente_soggetto_ruolo_id -> emittente_fiscale_id.
--
-- Semantica attesa (canonica):
--   - auth_user inesistente / identita OPERATORE non attiva -> false (fail-closed)
--   - identita OPERATORE attiva, whitelist vuota            -> true (accesso globale)
--   - identita attiva, target EF in whitelist               -> true
--   - identita attiva, target EF non in whitelist           -> false
--   - super_admin -> true (non coperto qui: nessun binding SUPER_ADMIN nei fixture)
--
-- Indice test (1..10):
--    1. Precondizione: emittente_fiscale costruito dalla fixture
--    2. Setup: soggetto PF + SR RIS_UMANA + 2 auth_user + 2 identita (attiva/inattiva)
--    3. PK: auth_user inesistente -> false (fail-closed)
--    4. PK: identita OPERATORE non attiva -> false
--    5. PK: identita attiva, whitelist vuota -> true (accesso globale)
--    6. Setup: popola user_emittenti_fiscali con 1 EF per l'auth_user attivo
--    7. PK: target EF in whitelist -> true
--    8. PK: target EF non in whitelist -> false
--    9. SR: adapter via_sr risolve SR->PK, target in whitelist -> true
--   10. SR: adapter via_sr, SR non-emittente (PK NULL) -> false
--
-- BEGIN; + rollback implicito a fine file (guard DEFERRABLE soggetti
-- non scattano senza COMMIT).
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ QUESTO FILE NON USA `SET CONSTRAINTS ALL IMMEDIATE`, a differenza degli
--   altri, e non e' una dimenticanza.
--   La fixture costruisce un soggetto con le funzioni del dominio
--   (fn_crea_soggetto_pf e sorelle). Ma `anagrafiche.soggetti` ha TRE guard
--   DEFERRABLE INITIALLY DEFERRED — indirizzi, contatti, dati societari — e la
--   deferralita' li' e' VOLUTA: si crea il soggetto, poi il suo indirizzo, e la
--   completezza si verifica al COMMIT. Forzare IMMEDIATE pretenderebbe
--   l'indirizzo nell'istante stesso dell'INSERT del soggetto, cioe' vieterebbe
--   il pattern che il dominio ha scelto — misurato: da 7 asserzioni verdi a 1,
--   con «Indirizzo obbligatorio mancante per soggetto ...».
--   ⚠️ Resta pero' un buco reale: senza la riga, quei tre guard non vengono
--   esercitati da questo test, e la fixture lascia un soggetto che
--   l'applicazione non potrebbe committare. La correzione vera e' completare la
--   fixture (indirizzo + contatti) e allora la riga si puo' rimettere.
--   Brief: brief-db-pgtap-runner-rls-baseline §20.

-- ⛔ L'EMITTENTE SI COSTRUISCE, non si cerca (2026-09-12): fino a quel giorno il
--   file pescava il primo emittente attivo, e su un database ricostruito dai
--   changelog non ce n'e' nessuno — moriva nella fixture al test 6 (NULL in
--   user_emittenti_fiscali), e le dieci asserzioni sul perimetro restavano
--   collaudate solo su dbdev. `dbops.fn_pgtap_crea_emittente_operatore()` da'
--   l'azienda E l'operatore su cui aprire il contesto applicativo: il test
--   gira come gira l'applicazione (ruolo OPERATORE + RLS attiva), non come
--   owner. Brief: brief-db-pgtap-runner-rls-baseline §8.
CREATE TEMP TABLE _t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- ⚠️ L'helper esce con i vincoli IMMEDIATE (li richiude sul proprio mondo
--   finito). Questo file li vuole DIFFERITI — vedi la nota qui sopra — quindi
--   li riapre: senza, fn_crea_soggetto_pf muore su «Indirizzo obbligatorio
--   mancante» al primo INSERT.
SET CONSTRAINTS ALL DEFERRED;

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _t_mondo));
END $ctx$;

SELECT plan(10);

-- =========================================================
-- 1) Precondizione: l'emittente_fiscale costruito
-- =========================================================
CREATE TEMP TABLE _t_ef AS
SELECT m.emittente_fiscale_id AS ef_id,
       m.soggetto_ruolo_id    AS ef_sr_id
  FROM _t_mondo m;

SELECT ok(
    (SELECT count(*) FROM _t_ef) = 1
    AND EXISTS (SELECT 1 FROM anagrafiche.emittenti_fiscali ef
                 WHERE ef.id = (SELECT ef_id FROM _t_ef) AND ef.attivo),
    '1. Precondizione: un emittente_fiscale attivo, costruito dalla fixture'
);

-- =========================================================
-- 2) Setup: soggetto PF pura + SR RIS_UMANA + 2 auth_user + 2 identita
-- =========================================================
CREATE TEMP TABLE _t_comune AS
SELECT id AS comune_id FROM config.comuni ORDER BY id LIMIT 1;

-- CF fisso valido. pgTAP rollbacca a fine file; il CF puo' essere riusato
-- in altri file test senza conflitti (transazioni indipendenti).
CREATE TEMP TABLE _t_sogg_pf AS
SELECT anagrafiche.fn_crea_soggetto_pf(
    p_cognome           := 'PnzTestScopeEf',
    p_nome              := 'Fdn',
    p_codice_fiscale    := 'PNZFDN78A01L219Y',
    p_email             := 'pgtap_scope_ef_' || substring(md5(clock_timestamp()::text) from 1 for 6) || '@test.local',
    p_data_nascita      := DATE '1978-01-01',
    p_sesso             := 'M',
    p_stato_iso2        := 'IT',
    p_comune_nascita_id := (SELECT comune_id FROM _t_comune),
    p_tipo_contatto_id  := NULL
) AS soggetto_id;

CREATE TEMP TABLE _t_sr_ru AS
SELECT script.fn_get_or_create_soggetto_ruolo(
    p_soggetto_id  := (SELECT soggetto_id FROM _t_sogg_pf),
    p_cd_int_ruolo := 'RIS_UMANA'
) AS sr_id;

-- 2 auth_user distinti (uno per identita attiva, uno per inattiva)
CREATE TEMP TABLE _t_au (idx int, auth_user_id int);
DO $$
DECLARE v_i int; v_id int;
BEGIN
    FOR v_i IN 1..2 LOOP
        INSERT INTO django.auth_user (
            username, password, is_active, is_staff, is_superuser,
            first_name, last_name, email, date_joined
        )
        VALUES (
            '_pgtap_scope_ef_' || v_i || '_' || substring(md5(clock_timestamp()::text) from 1 for 6),
            '!', true, false, false, '', '', '', now()
        )
        RETURNING id INTO v_id;
        INSERT INTO _t_au (idx, auth_user_id) VALUES (v_i, v_id);
    END LOOP;
END
$$;

-- Identita attiva (idx=1) e inattiva (idx=2) su SR RIS_UMANA.
CREATE TEMP TABLE _t_id (idx int, identita_id bigint);
WITH ins_attiva AS (
    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    SELECT (SELECT sr_id FROM _t_sr_ru),
           (SELECT auth_user_id FROM _t_au WHERE idx = 1),
           'OPERATORE',
           true
    RETURNING id
)
INSERT INTO _t_id (idx, identita_id)
SELECT 1, id FROM ins_attiva;

WITH ins_inattiva AS (
    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    SELECT (SELECT sr_id FROM _t_sr_ru),
           (SELECT auth_user_id FROM _t_au WHERE idx = 2),
           'OPERATORE',
           false
    RETURNING id
)
INSERT INTO _t_id (idx, identita_id)
SELECT 2, id FROM ins_inattiva;

SELECT ok(
    (SELECT count(*) FROM _t_id) = 2,
    '2. Setup: 2 identita create (1 attiva, 1 inattiva) su SR RIS_UMANA'
);

-- =========================================================
-- 3) PK: auth_user inesistente -> false (fail-closed)
-- =========================================================
SELECT ok(
    script.fn_scope_ef_whitelist(
        (SELECT COALESCE(MAX(id), 0) + 999999 FROM django.auth_user),
        (SELECT ef_id FROM _t_ef)
    ) = false,
    '3. PK: auth_user inesistente -> false (no identita OPERATORE attiva)'
);

-- =========================================================
-- 4) PK: identita OPERATORE non attiva -> false
-- =========================================================
SELECT ok(
    script.fn_scope_ef_whitelist(
        (SELECT auth_user_id FROM _t_au WHERE idx = 2),
        (SELECT ef_id FROM _t_ef)
    ) = false,
    '4. PK: auth_user con identita OPERATORE non attiva -> false (fail-closed)'
);

-- =========================================================
-- 5) PK: identita attiva, whitelist vuota -> FALSE (fail-closed)
--
-- ⚠️ Fino al 2026-08-18 questa asserzione diceva `true`, con la nota
--   «accesso globale». Non era una fixture stantia: era il VECCHIO
--   contratto, scritto. P-2a lo ha rovesciato, e la ragione sta
--   nell'asimmetria che nessuno aveva mai messo a confronto — lo stesso
--   utente, sul lato SCRITTURA, non poteva nemmeno creare un billing
--   account (fn_check_user_can_create_ba -> false) mentre in LETTURA
--   vedeva tutti gli emittenti. Le due letture non potevano essere
--   entrambe intenzionali.
--   Una riga mancante e' un errore di configurazione, non un permesso.
--   Brief: brief-db-perimetro-emittente-liste-e-gerarchia-ba §2.5 (P-2a).
-- =========================================================
SELECT ok(
    script.fn_scope_ef_whitelist(
        (SELECT auth_user_id FROM _t_au WHERE idx = 1),
        (SELECT ef_id FROM _t_ef)
    ) = false,
    '5. PK: identita attiva, whitelist vuota -> false (fail-closed, P-2a)'
);

-- =========================================================
-- 6) Setup: popola user_emittenti_fiscali per l'auth_user attivo
-- =========================================================
INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
VALUES (
    (SELECT auth_user_id FROM _t_au WHERE idx = 1),
    (SELECT ef_id FROM _t_ef)
)
ON CONFLICT DO NOTHING;

SELECT ok(
    EXISTS (
        SELECT 1 FROM config.user_emittenti_fiscali
         WHERE auth_user_id = (SELECT auth_user_id FROM _t_au WHERE idx = 1)
    ),
    '6. Setup: whitelist popolata per auth_user attivo (1 EF autorizzato)'
);

-- =========================================================
-- 7) PK: target EF in whitelist -> true
-- =========================================================
SELECT ok(
    script.fn_scope_ef_whitelist(
        (SELECT auth_user_id FROM _t_au WHERE idx = 1),
        (SELECT ef_id FROM _t_ef)
    ) = true,
    '7. PK: whitelist valorizzata, target EF in lista -> true'
);

-- =========================================================
-- 8) PK: target EF non in whitelist -> false
-- =========================================================
SELECT ok(
    script.fn_scope_ef_whitelist(
        (SELECT auth_user_id FROM _t_au WHERE idx = 1),
        (SELECT COALESCE(MAX(id), 0) + 999999 FROM anagrafiche.emittenti_fiscali)
    ) = false,
    '8. PK: whitelist valorizzata, target EF fuori lista -> false'
);

-- =========================================================
-- 9) SR adapter: risolve SR->PK, target in whitelist -> true
-- =========================================================
SELECT ok(
    script.fn_scope_ef_whitelist_via_sr(
        (SELECT auth_user_id FROM _t_au WHERE idx = 1),
        (SELECT ef_sr_id FROM _t_ef)
    ) = true,
    '9. SR: adapter via_sr risolve emittente_sr -> EF, target in whitelist -> true'
);

-- =========================================================
-- 10) SR adapter: SR non-emittente (PK risolto NULL) -> false
-- =========================================================
-- Uso il soggetto_ruolo della risorsa umana: non e' un emittente fiscale,
-- quindi la risoluzione SR->emittente_fiscale_id da NULL e la canonica con
-- whitelist valorizzata ritorna false (fail-closed).
SELECT ok(
    script.fn_scope_ef_whitelist_via_sr(
        (SELECT auth_user_id FROM _t_au WHERE idx = 1),
        (SELECT sr_id FROM _t_sr_ru)
    ) = false,
    '10. SR: adapter via_sr, SR non-emittente -> PK NULL -> false'
);

SELECT * FROM finish();
ROLLBACK;
