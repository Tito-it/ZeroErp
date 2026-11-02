-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
--    2. Setup: 2 operatori dalla madre (veste accesa / veste spenta)
--    3. PK: auth_user inesistente -> false (fail-closed)
--    4. PK: identita OPERATORE non attiva -> false
--    5. PK: identita attiva, whitelist vuota -> true (accesso globale)
--    6. Setup: popola user_emittenti_fiscali con 1 EF per l'auth_user attivo
--    7. PK: target EF in whitelist -> true
--    8. PK: target EF non in whitelist -> false
--    9. SR: adapter via_sr risolve SR->PK, target in whitelist -> true
--   10. SR: adapter via_sr, SR non-emittente (PK NULL) -> false
--
-- BEGIN; + rollback a fine file.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
-- ⭐ Rev 2026-10-07 (brief-db-veste-utilizzabile): fino a oggi questo file non
--   la aveva, perche' costruiva l'operatore a mano con fn_crea_soggetto_pf e
--   lasciava il soggetto senza indirizzo, contando sul ROLLBACK (§22.4). Ora
--   l'operatore viene dalla madre (dbops.fn_pgtap_crea_operatore_umano), che
--   lo consegna COMPLETO: la riga torna, e i guard del soggetto si esercitano.
SET CONSTRAINTS ALL IMMEDIATE;

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
-- 2) Setup: due operatori dalla madre, uno con la veste accesa e uno spenta
-- =========================================================
-- ⭐ Rev 2026-10-07 (brief-db-veste-utilizzabile): l'operatore viene dalla
--   MADRE (dbops.fn_pgtap_crea_operatore_umano: persona fisica completa,
--   risorsa umana, veste OPERATORE accesa come all'invito accettato) e
--   l'emittente gli si da' con la funzione di dominio
--   script.fn_change_user_emittenti_scope. Prima la fixture costruiva
--   soggetto, soggetto_ruolo e veste a mano, senza risorsa umana: uno stato
--   che la madre non produce, e che da D-2 (l'operatore umano vale finche'
--   vale il suo rapporto, script.fn_veste_utilizzabile) non e' piu' un
--   operatore valido. Il builder esce con i vincoli IMMEDIATE: niente piu'
--   finestra differita da riaprire per lui.
CREATE TEMP TABLE _t_op_acceso AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('scope ef acceso');

CREATE TEMP TABLE _t_op_spento AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('scope ef spento');

-- Lo spegnimento e' un UPDATE dopo l'accensione: il percorso con cui una veste
-- viene dismessa davvero.
UPDATE anagrafiche.identita_digitali
   SET attivo = false
 WHERE id = (SELECT identita_id FROM _t_op_spento);

-- Le tabelle che le asserzioni leggono: idx 1 = acceso, idx 2 = spento.
CREATE TEMP TABLE _t_au (idx int, auth_user_id int);
INSERT INTO _t_au
SELECT 1, auth_user_id FROM _t_op_acceso
UNION ALL
SELECT 2, auth_user_id FROM _t_op_spento;

CREATE TEMP TABLE _t_id (idx int, identita_id bigint);
INSERT INTO _t_id
SELECT 1, identita_id FROM _t_op_acceso
UNION ALL
SELECT 2, identita_id FROM _t_op_spento;

-- Il soggetto_ruolo RIS_UMANA dell'operatore acceso: non e' un emittente (caso 10).
CREATE TEMP TABLE _t_sr_ru AS
SELECT soggetto_ruolo_id AS sr_id FROM _t_op_acceso;

SELECT ok(
    (SELECT count(*) FROM _t_id) = 2,
    '2. Setup: 2 operatori dalla madre (1 veste accesa, 1 spenta)'
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
SELECT script.fn_change_user_emittenti_scope(
    (SELECT auth_user_id FROM _t_au WHERE idx = 1),
    ARRAY[(SELECT ef_id FROM _t_ef)]);

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
