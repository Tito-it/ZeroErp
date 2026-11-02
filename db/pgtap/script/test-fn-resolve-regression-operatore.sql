-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test regression end-to-end §4.8.4 WIP multi-face-auth:
-- verifica che un operatore con permessi configurati sul modello
-- profili_accesso_* restituisca i livelli attesi chiamando le funzioni
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
-- ⚠️ Rev 2026-10-04 (brief-db-permessi-tetto-area, 20261004-55/-56): l'area e' un
--   TETTO anche per le azioni abilitate dal profilo (D-2). I test 8 e 11 passavano
--   perche' la prima azione del catalogo stava, per caso, nella seconda area per id
--   (configurata TUTTO). Ora si COSTRUISCE: la seconda area del profilo e' l'area
--   DELL'AZIONE (TUTTO), la prima e' un'altra area (LETTURA).
--
-- BEGIN; + rollback implicito a fine file.
-- ------------------------------------------------------------

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
-- 2) Pulisce override + rimuove binding SUPER_ADMIN di tid
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

-- Tid puo' avere piu' identita attive (multi-face auth: OPERATORE +
-- CLIENTE_PORTALE + ...). I profili PORTALE_STANDARD ereditati dalle
-- identita non-OPERATORE definirebbero livelli su 'vendite'/'pagamenti'
-- con stessa priorita 2 del profilo REPARTO test, rendendo l'ORDER BY
-- non deterministico. Disattivo temporaneamente le altre identita
-- (ROLLBACK ripristina). Sicuro: non sono SUPER_ADMIN, il guard non
-- scatta.
UPDATE anagrafiche.identita_digitali id
   SET attivo = false
  FROM _t_op op
 WHERE id.auth_user_id = op.auth_user_id
   AND id.id <> op.identita_id
   AND id.attivo = true;

-- Per togliere il binding SUPER_ADMIN di tid senza far scattare
-- trgfn_profili_accesso_bindings_guard_ultimo_super_admin (anti-lockout)
-- creo un binding SUPER_ADMIN "di ammortizzo" su un'altra identita
-- attiva. Se nessuna spare identita esiste (CI minimale con solo tid),
-- svuoto _t_op cosi' i test successivi passano graceful via la guard
-- "WHEN count(*) = 0 THEN true".
CREATE TEMP TABLE _t_spare_id AS
SELECT id.id AS identita_id
  FROM anagrafiche.identita_digitali id
  JOIN _t_op op ON true
 WHERE id.id <> op.identita_id
   AND id.attivo = true
   AND id.ruolo_applicativo <> 'DISABILITATO'
   AND (id.valido_dal IS NULL OR id.valido_dal <= script.fn_data_operativa())
   AND (id.valido_al  IS NULL OR id.valido_al  >= script.fn_data_operativa())
   -- Esclude identita gia' SUPER_ADMIN: il binding sarebbe duplicato.
   AND NOT EXISTS (
        SELECT 1 FROM config.profili_accesso_bindings pab
         WHERE pab.identita_digitale_id = id.id
           AND pab.profilo_accesso_id = 9100
   )
 LIMIT 1;

DO $lega$
BEGIN
    PERFORM config.fn_lega_profilo_identita(9100, sp.identita_id) FROM _t_spare_id sp;
END
$lega$;

-- Se nessuna spare identita: svuoto _t_op cosi' i test 5..11 passano
-- banalmente (graceful skip). Non possiamo rimuovere il binding di tid
-- senza violare l'invariante "almeno un SUPER_ADMIN attivo".
DELETE FROM _t_op
 WHERE NOT EXISTS (SELECT 1 FROM _t_spare_id);

-- A questo punto rimuovere il binding di tid e' sicuro:
-- - se _t_op e' popolata, l'ammortizzo soddisfa il guard.
-- - se _t_op e' vuota, le UPDATE/DELETE che seguono sono no-op.
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
    '2. Setup: user_override ripuliti + binding SUPER_ADMIN di tid rimosso (ammortizzato su spare identita)'
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
-- L'azione prima delle aree: la sua area e' la seconda del profilo (TUTTO).
CREATE TEMP TABLE _t_azione AS
SELECT ap.id AS azione_id, ap.permission_codename, ap.area_id
  FROM config.azioni_processo ap
 WHERE ap.attivo = true
 ORDER BY ap.id
 LIMIT 1;

CREATE TEMP TABLE _t_aree AS
SELECT x.area_id, x.schema_db, x.rn
  FROM (
        -- rn 1: un'area diversa da quella dell'azione (LETTURA)
        (SELECT af.id AS area_id, af.schema_db, 1 AS rn
           FROM config.aree_funzionali af
          WHERE af.attivo = true
            AND af.id <> (SELECT area_id FROM _t_azione)
          ORDER BY af.id
          LIMIT 1)
        UNION ALL
        -- rn 2: l'area dell'azione (TUTTO): il tetto la lascia passare
        (SELECT af.id, af.schema_db, 2
           FROM config.aree_funzionali af
          WHERE af.id = (SELECT area_id FROM _t_azione))
       ) x;

INSERT INTO config.profili_accesso_aree (profilo_accesso_id, area_id, livello)
SELECT p.profilo_id,
       a.area_id,
       CASE a.rn
           WHEN 1 THEN 'LETTURA'::config.livello_accesso
           ELSE 'TUTTO'::config.livello_accesso
       END
  FROM _t_profilo p, _t_aree a;

INSERT INTO config.profili_accesso_azioni (profilo_accesso_id, azione_id, abilitata)
SELECT p.profilo_id, az.azione_id, true
  FROM _t_profilo p, _t_azione az;

-- I resolver (incluso fn_get_user_permissions_map e fn_get_user_actions_map,
-- §4.8.5) leggono dal modello profili_accesso_* via
-- fn_get_profili_accesso_applicabili. Il modello legacy profili_reparto_*
-- e' stato dismesso il 2026-05-04 (changeSet 20260505-02-drop-profili-reparto).

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

-- Per diagnosi in caso di regressione, scommentare il diag() seguente:
-- mostra aree scelte, profili applicabili e identita attive di tid.
--
-- SELECT diag(format(
--     'Setup areas: rn1=%s rn2=%s | profili applicabili=%s | identita_attive=%s',
--     (SELECT schema_db FROM _t_aree WHERE rn = 1),
--     (SELECT schema_db FROM _t_aree WHERE rn = 2),
--     (SELECT string_agg(format('%s(p=%s)', pa.codice, h.priorita), ', ' ORDER BY h.priorita)
--        FROM script.fn_get_profili_accesso_applicabili((SELECT auth_user_id FROM _t_op)) h
--        JOIN config.profili_accesso pa ON pa.id = h.profilo_accesso_id),
--     (SELECT string_agg(ruolo_applicativo::text, ',') FROM anagrafiche.identita_digitali id
--        JOIN _t_op op ON op.auth_user_id = id.auth_user_id
--       WHERE id.attivo = true)
-- ));

-- =========================================================
-- 5) fn_resolve_livello_area: area1 -> LETTURA
-- =========================================================
SELECT is(
    CASE
        WHEN (SELECT count(*) FROM _t_op) = 0 THEN 'LETTURA'::text
        ELSE script.fn_resolve_livello_area(
                (SELECT auth_user_id FROM _t_op),
                (SELECT schema_db FROM _t_aree WHERE rn = 1)
             )::text
    END,
    'LETTURA',
    '5. fn_resolve_livello_area area1 (configurata LETTURA) -> LETTURA'
);

-- =========================================================
-- 6) fn_resolve_livello_area: area2 -> TUTTO
-- =========================================================
SELECT is(
    CASE
        WHEN (SELECT count(*) FROM _t_op) = 0 THEN 'TUTTO'::text
        ELSE script.fn_resolve_livello_area(
                (SELECT auth_user_id FROM _t_op),
                (SELECT schema_db FROM _t_aree WHERE rn = 2)
             )::text
    END,
    'TUTTO',
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
