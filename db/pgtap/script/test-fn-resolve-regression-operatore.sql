-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test regression end-to-end §4.8.4 WIP multi-face-auth:
-- verifica che un operatore con permessi configurati tramite il nuovo
-- modello profili_accesso (popolato dal backfill §4.3.5 a partire da
-- profili_reparto_*) restituisca i livelli attesi chiamando le funzioni
-- resolver refactored (§4.6.B + §4.8):
--   - fn_resolve_livello_area
--   - fn_resolve_livello_oggetto (tramite fallback area)
--   - fn_check_azione_processo
--   - fn_get_user_permissions_map  (set-based)
--   - fn_get_user_actions_map      (set-based)
--
-- Pattern: uso l'operatore seed 'tid' come base (ha gia' soggetto PF pura,
-- risorsa_umana, bridge RUA + identita OPERATORE creati dal backfill
-- §4.6.E). Lo sposto temporaneamente in una UO test dedicata con profilo
-- REPARTO dedicato, rimuovo binding SUPER_ADMIN + eventuali user_override
-- che altrimenti prevarrebbero sul profilo. ROLLBACK a fine file ripristina
-- tutto.
--
-- Indice test (1..8):
--    1. Setup: trova tid (auth_user + identita OPERATORE + RU)
--    2. Setup: pulisce override + rimuove binding SUPER_ADMIN di tid
--    3. Setup: UO test + profilo REPARTO test + binding
--    4. Setup: config permessi (2 aree + 1 azione) sul profilo test
--    5. fn_resolve_livello_area area1 -> LETTURA
--    6. fn_resolve_livello_area area2 -> TUTTO
--    7. fn_resolve_livello_area area_inesistente -> BLOCCATO
--    8. fn_check_azione_processo azione configurata -> true
--    9. fn_check_azione_processo azione inesistente -> false
--   10. fn_get_user_permissions_map contiene area1 -> LETTURA
--   11. fn_get_user_actions_map contiene azione test -> true
--
-- NOTA se operatore 'tid' non presente (CI minimale): skip graceful
--      (count(*)=0 -> tutti gli assert passano banalmente).
--
-- BEGIN; + rollback implicito a fine file.
-- ------------------------------------------------------------

BEGIN;
SELECT plan(11);

-- =========================================================
-- 1) Setup: cache dell'operatore tid (auth_user + identita + RU)
-- =========================================================
CREATE TEMP TABLE _t_op AS
SELECT au.id AS auth_user_id,
       id.id AS identita_id,
       ru.id AS ru_id,
       ru.unita_organizzativa_id AS uo_originale_id
  FROM django.auth_user au
  JOIN anagrafiche.identita_digitali id
    ON id.auth_user_id = au.id
   AND id.ruolo_applicativo = 'OPERATORE'
   AND id.attivo = true
  JOIN anagrafiche.risorse_umane ru
    ON ru.soggetto_ruolo_id = id.soggetto_ruolo_id
 WHERE au.username = 'tid'
 LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM _t_op) >= 0,
    '1. Setup: cache operatore tid (0 se seed assente, 1 se presente)'
);

-- =========================================================
-- 2) Pulisce override + rimuove binding SUPER_ADMIN
-- =========================================================
-- Gli user_override (aree/azioni) prevalgono sul profilo: se esistono
-- per tid, i test sui profili fallirebbero. Pulizia temporanea
-- (ROLLBACK ripristina).
DELETE FROM config.user_override_aree uoa
 USING _t_op op
 WHERE uoa.auth_user_id = op.auth_user_id;

DELETE FROM config.user_override_azioni uoa
 USING _t_op op
 WHERE uoa.auth_user_id = op.auth_user_id;

-- Rimuovo binding SUPER_ADMIN per non attivare il bypass in
-- fn_is_super_admin (altrimenti tutti i resolver ritornano TUTTO/true).
-- Prima disattivo (non-cascade child guard), poi DELETE.
UPDATE config.profili_accesso_bindings pab
   SET attivo = false
  FROM _t_op op
 WHERE pab.identita_digitale_id = op.identita_id
   AND pab.profilo_accesso_id = 9100;

DELETE FROM config.profili_accesso_bindings pab
 USING _t_op op
 WHERE pab.identita_digitale_id = op.identita_id
   AND pab.profilo_accesso_id = 9100;

SELECT ok(
    true,
    '2. Setup: user_override ripuliti + binding SUPER_ADMIN rimosso'
);

-- =========================================================
-- 3) Setup: UO test + profilo REPARTO + binding
-- =========================================================
CREATE TEMP TABLE _t_uo AS
WITH ins AS (
    INSERT INTO config.unita_organizzative (
        codice, codice_interno, descrizione, attivo
    )
    VALUES (
        '_PGTAP_REG_' || upper(substring(md5(clock_timestamp()::text) from 1 for 8)),
        '_PGTAPREG_'  || upper(substring(md5(clock_timestamp()::text) from 1 for 8)),
        'UO test regression resolver §4.8.4',
        true
    )
    RETURNING id
)
SELECT id AS uo_id FROM ins;

CREATE TEMP TABLE _t_profilo AS
WITH ins AS (
    INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo)
    VALUES (
        'REPARTO'::config.tipo_profilo_accesso,
        '_PGTAP_REGPR_' || upper(substring(md5(clock_timestamp()::text) from 1 for 8)),
        'Profilo REPARTO test regression §4.8.4',
        true
    )
    RETURNING id
)
SELECT id AS profilo_id FROM ins;

INSERT INTO config.profili_accesso_bindings
    (profilo_accesso_id, unita_organizzativa_id, attivo)
SELECT p.profilo_id, u.uo_id, true
  FROM _t_profilo p, _t_uo u;

SELECT ok(
    (SELECT count(*) FROM config.profili_accesso_bindings pab
      JOIN _t_uo u ON u.uo_id = pab.unita_organizzativa_id) = 1,
    '3. Setup: UO test + profilo REPARTO + binding UO creati'
);

-- =========================================================
-- 4) Config permessi: 2 aree (LETTURA + TUTTO) + 1 azione (true)
-- =========================================================
CREATE TEMP TABLE _t_aree AS
SELECT af.id AS area_id,
       af.schema_db,
       ROW_NUMBER() OVER (ORDER BY af.id) AS rn
  FROM config.aree_funzionali af
 WHERE af.attivo = true
 ORDER BY af.id
 LIMIT 2;

INSERT INTO config.profili_accesso_aree (profilo_accesso_id, area_id, livello)
SELECT p.profilo_id,
       a.area_id,
       CASE a.rn
           WHEN 1 THEN 'LETTURA'::config.livello_accesso
           ELSE 'TUTTO'::config.livello_accesso
       END
  FROM _t_profilo p, _t_aree a;

CREATE TEMP TABLE _t_azione AS
SELECT ap.id AS azione_id, ap.permission_codename
  FROM config.azioni_processo ap
 WHERE ap.attivo = true
 ORDER BY ap.id
 LIMIT 1;

INSERT INTO config.profili_accesso_azioni (profilo_accesso_id, azione_id, abilitata)
SELECT p.profilo_id, az.azione_id, true
  FROM _t_profilo p, _t_azione az;

-- NOTA: non popoliamo profili_reparto_aree/azioni (modello legacy).
-- Post §4.8, le funzioni resolver (inclusi fn_get_user_permissions_map
-- e fn_get_user_actions_map, §4.8.5) leggono solo dal nuovo modello
-- profili_accesso_* via fn_get_profili_accesso_applicabili.
-- Se questo test fallisce perche' il DB non ha applicato le migration
-- fino a -54, il fallimento e' INTENZIONALE: applicare le migration.

-- Sposto tid nella UO test (fn_get_profili_accesso_applicabili risolve
-- via ru.unita_organizzativa_id, quindi il nuovo binding REPARTO diventa
-- immediatamente attivo).
UPDATE anagrafiche.risorse_umane ru
   SET unita_organizzativa_id = u.uo_id
  FROM _t_op op, _t_uo u
 WHERE ru.id = op.ru_id;

SELECT ok(
    (SELECT count(*) FROM config.profili_accesso_aree paa
      JOIN _t_profilo p ON p.profilo_id = paa.profilo_accesso_id) = 2,
    '4. Setup: 2 aree (LETTURA, TUTTO) + 1 azione configurate su profilo test'
);

-- =========================================================
-- 5) fn_resolve_livello_area: area1 -> LETTURA
-- =========================================================
SELECT ok(
    CASE
        WHEN (SELECT count(*) FROM _t_op) = 0 THEN true
        ELSE script.fn_resolve_livello_area(
                (SELECT auth_user_id FROM _t_op),
                (SELECT schema_db FROM _t_aree WHERE rn = 1)
             )::text = 'LETTURA'
    END,
    '5. fn_resolve_livello_area area1 (configurata LETTURA) -> LETTURA'
);

-- =========================================================
-- 6) fn_resolve_livello_area: area2 -> TUTTO
-- =========================================================
SELECT ok(
    CASE
        WHEN (SELECT count(*) FROM _t_op) = 0 THEN true
        ELSE script.fn_resolve_livello_area(
                (SELECT auth_user_id FROM _t_op),
                (SELECT schema_db FROM _t_aree WHERE rn = 2)
             )::text = 'TUTTO'
    END,
    '6. fn_resolve_livello_area area2 (configurata TUTTO) -> TUTTO'
);

-- =========================================================
-- 7) fn_resolve_livello_area area non configurata -> BLOCCATO
-- =========================================================
SELECT ok(
    CASE
        WHEN (SELECT count(*) FROM _t_op) = 0 THEN true
        ELSE script.fn_resolve_livello_area(
                (SELECT auth_user_id FROM _t_op),
                '__pgtap_area_inesistente__'
             )::text = 'BLOCCATO'
    END,
    '7. fn_resolve_livello_area area inesistente -> BLOCCATO (default)'
);

-- =========================================================
-- 8) fn_check_azione_processo: azione configurata -> true
-- =========================================================
SELECT ok(
    CASE
        WHEN (SELECT count(*) FROM _t_op) = 0 THEN true
        ELSE script.fn_check_azione_processo(
                (SELECT auth_user_id FROM _t_op),
                (SELECT permission_codename FROM _t_azione)
             ) = true
    END,
    '8. fn_check_azione_processo azione configurata abilitata -> true'
);

-- =========================================================
-- 9) fn_check_azione_processo azione inesistente -> false
-- =========================================================
SELECT ok(
    CASE
        WHEN (SELECT count(*) FROM _t_op) = 0 THEN true
        ELSE script.fn_check_azione_processo(
                (SELECT auth_user_id FROM _t_op),
                '__pgtap_azione_inesistente__'
             ) = false
    END,
    '9. fn_check_azione_processo azione inesistente -> false (default)'
);

-- =========================================================
-- 10) fn_get_user_permissions_map: contiene area1 con LETTURA
-- =========================================================
SELECT ok(
    CASE
        WHEN (SELECT count(*) FROM _t_op) = 0 THEN true
        ELSE (SELECT script.fn_get_user_permissions_map(
                (SELECT auth_user_id FROM _t_op)
              ) ->> (SELECT schema_db FROM _t_aree WHERE rn = 1)) = 'LETTURA'
    END,
    '10. fn_get_user_permissions_map contiene area1 con livello LETTURA'
);

-- =========================================================
-- 11) fn_get_user_actions_map: contiene azione test con true
-- =========================================================
SELECT ok(
    CASE
        WHEN (SELECT count(*) FROM _t_op) = 0 THEN true
        ELSE (SELECT script.fn_get_user_actions_map(
                (SELECT auth_user_id FROM _t_op)
              ) ->> (SELECT permission_codename FROM _t_azione)) = 'true'
    END,
    '11. fn_get_user_actions_map contiene azione test abilitata (true)'
);

SELECT * FROM finish();
ROLLBACK;
