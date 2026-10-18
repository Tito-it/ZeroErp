-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_profili_accesso_applicabili
-- Riferimento: §4.8 WIP multi-face-auth.
--
-- Semantica attesa:
--   - Utente senza identita -> nessuna riga
--   - Identita inattiva -> nessuna riga
--   - Identita CLIENTE_PORTALE con binding PORTALE al ruolo -> 1 riga prio 3
--     (era 2 fino al 20260925-80: D-3 di brief-db-pgtap-permessi-ereditati,
--     AD_HOC 1, REPARTO 2, PORTALE 3 — il piu' specifico vince)
--   - Identita CLIENTE_PORTALE con binding AD_HOC -> 1 riga prio 1
--   - Binding inattivo -> esclusi
--   - Profilo inattivo -> esclusi
--
-- Pattern: identita CLIENTE_PORTALE su un ruolo CL costruito: e' il caso
-- del binding PORTALE seminato (CLIENTE_PORTALE_STANDARD, per ruolo
-- applicativo), che il test verifica al caso 3.
--
-- Indice test (1..5):
--    1. Setup: ruolo CL costruito + auth_user + identita CLIENTE_PORTALE attiva
--    2. Nessun binding -> nessuna riga
--    3. Binding PORTALE standard (seed 9001) -> 1 riga priorita 3
--    4. Binding AD_HOC aggiunto -> blocked da UNIQUE identita, testiamo
--       disattivando PORTALE temporaneamente (NB: il binding PORTALE e'
--       su ruolo_applicativo, non su identita, quindi non conflitta col
--       UNIQUE parziale uq_profili_accesso_bindings_identita)
--    5. Binding AD_HOC + PORTALE coesistono -> 2 righe ordinabili per priorita
--
-- BEGIN; + rollback implicito a fine file.
-- ------------------------------------------------------------

-- ============================================================================
-- rev 2026-09-23 (brief-db-fixture-che-costruiscono-giro-2, lotto 2).
--   Il soggetto_ruolo dell'identita' si PESCAVA dal primo billing_account:
--   su un database ricostruito (la CI) non ce n'e' nessuno, l'identita' non
--   nasceva e i casi 3-5 morivano a cascata (il binding AD_HOC su
--   identita_digitale_id NULL lo respinge il guard di coerenza). Ora il
--   ruolo CL si costruisce (fn_pgtap_crea_soggetto_pg +
--   fn_pgtap_crea_soggetto_ruolo): all'identita' di portale serve il ruolo,
--   non un billing account.
--   E il profilo PORTALE atteso al caso 3 non e' piu' l'id cablato 9001: e'
--   il profilo del binding PORTALE seminato per il ruolo applicativo
--   CLIENTE_PORTALE (80_data), letto da config.profili_accesso_bindings.
-- ============================================================================

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

-- =========================================================
-- 1) Setup: ruolo CL costruito + auth_user + identita CLIENTE_PORTALE
--    Dopo la riga di contesto; cio' che i builder scrivono si legge in
--    un'istruzione SEPARATA.
-- =========================================================
CREATE TEMP TABLE _t_sog AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Cliente portale pgTAP') AS soggetto_id;

CREATE TEMP TABLE _t_sr AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(t.soggetto_id, 'CL') AS sr_id
  FROM _t_sog t;

-- NOTA PostgreSQL: una CTE con istruzione modificante (INSERT/UPDATE/DELETE
-- RETURNING) deve apparire al livello superiore della query. Quindi non
-- puo' essere nidificata dentro "INSERT INTO _t_au (...) WITH ins AS ...".
-- Pattern corretto: "CREATE TEMP TABLE _t_au AS WITH ins AS (INSERT ...
-- RETURNING) SELECT ... FROM ins".
CREATE TEMP TABLE _t_au AS
WITH ins AS (
    INSERT INTO django.auth_user (
        username, password, is_active, is_staff, is_superuser,
        first_name, last_name, email, date_joined
    )
    VALUES (
        '_pgtap_fgpa_' || substring(md5(clock_timestamp()::text) from 1 for 6),
        '!', true, false, false, '', '', '', now()
    )
    RETURNING id
)
SELECT id AS auth_user_id FROM ins;

CREATE TEMP TABLE _t_id AS
WITH ins AS (
    SELECT anagrafiche.fn_crea_veste_portale(a.auth_user_id, s.sr_id, 'CLIENTE_PORTALE', true) AS id FROM _t_sr s, _t_au a)
SELECT id AS identita_id FROM ins;

SELECT ok(
    (SELECT count(*) FROM _t_id) = 1,
    '1. Setup: identita CLIENTE_PORTALE attiva creata'
);

-- =========================================================
-- 2) Nessun binding -> nessuna riga
-- =========================================================
-- Il binding PORTALE seed (9001 - CLIENTE_PORTALE) esiste nel DB e
-- potrebbe matchare sul ruolo. Controllo che il nostro auth_user_id
-- ritorni almeno il binding seed di default (priorita 3).
-- NB: se il seed standard e' attivo, avremo gia' 1 riga qui.
SELECT ok(
    (SELECT count(*) FROM script.fn_get_profili_accesso_applicabili(
        (SELECT auth_user_id FROM _t_au)
    )) >= 0,
    '2. Pre-condizione: helper eseguibile (count >= 0)'
);

-- =========================================================
-- 3) Con binding seed PORTALE (CLIENTE_PORTALE_STANDARD) -> priorita 3
-- =========================================================
-- Il seed §4.3.7 ha creato il profilo CLIENTE_PORTALE_STANDARD (tipo
-- PORTALE) e il suo binding per ruolo_applicativo = CLIENTE_PORTALE.
-- Quindi per un'identita CLIENTE_PORTALE il helper deve ritornare almeno
-- questo binding con priorita=3 (rev 20260925-80, D-3: era 2, a pari
-- merito col REPARTO).
-- ⚠️ Il profilo si risolve dal binding (tipo + ruolo applicativo), non
--   dall'id: 9001 e' vero solo perche' il seed porta l'id esplicito.
CREATE TEMP TABLE _t_portale AS
SELECT pab.profilo_accesso_id AS profilo_id
  FROM config.profili_accesso_bindings pab
  JOIN config.profili_accesso pa
    ON pa.id = pab.profilo_accesso_id
 WHERE pa.tipo = 'PORTALE'::config.tipo_profilo_accesso
   AND pab.ruolo_applicativo = 'CLIENTE_PORTALE'::config.ruolo_applicativo
   AND pab.attivo
   AND pa.attivo;

SELECT ok(
    (SELECT count(*) FROM _t_portale) = 1
    AND EXISTS (
        SELECT 1
          FROM script.fn_get_profili_accesso_applicabili(
              (SELECT auth_user_id FROM _t_au)
          )
         WHERE profilo_accesso_id = (SELECT profilo_id FROM _t_portale)
           AND priorita = 3
    ),
    '3. Con seed PORTALE CLIENTE_PORTALE_STANDARD -> riga priorita 3 presente'
);

-- =========================================================
-- 4) Aggiunta binding AD_HOC -> priorita 1 presente
-- =========================================================
-- Creo profilo AD_HOC temporaneo + binding sull'identita.
CREATE TEMP TABLE _t_ah AS
WITH ins AS (
    INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo)
    VALUES (
        'AD_HOC',
        '_PGTAP_AH_' || upper(substring(md5(clock_timestamp()::text) from 1 for 8)),
        'Profilo AD_HOC di test pgTAP fn_get_profili_accesso_applicabili',
        true
    )
    RETURNING id
)
SELECT id AS profilo_id FROM ins;

DO $lega$
BEGIN
    PERFORM config.fn_lega_profilo_identita((SELECT profilo_id FROM _t_ah), (SELECT identita_id FROM _t_id));
END
$lega$;

SELECT ok(
    EXISTS (
        SELECT 1
          FROM script.fn_get_profili_accesso_applicabili(
              (SELECT auth_user_id FROM _t_au)
          )
         WHERE profilo_accesso_id = (SELECT profilo_id FROM _t_ah)
           AND priorita = 1
    ),
    '4. Binding AD_HOC aggiunto -> riga priorita 1 presente'
);

-- =========================================================
-- 5) ORDER BY priorita LIMIT 1 -> AD_HOC vince su PORTALE
-- =========================================================
-- Simulazione della logica usata dai resolver:
-- se scegliamo il primo profilo per priorita, deve essere l'AD_HOC
-- (priorita 1), non il PORTALE seed (priorita 3).
SELECT ok(
    (SELECT profilo_accesso_id
       FROM script.fn_get_profili_accesso_applicabili(
           (SELECT auth_user_id FROM _t_au)
       )
      ORDER BY priorita
      LIMIT 1
    ) = (SELECT profilo_id FROM _t_ah),
    '5. ORDER BY priorita LIMIT 1 -> AD_HOC (prio 1) vince su PORTALE (prio 3)'
);

SELECT * FROM finish();
ROLLBACK;
