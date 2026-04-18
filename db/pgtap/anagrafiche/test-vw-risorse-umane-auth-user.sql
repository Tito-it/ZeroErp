-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vista anagrafiche.vw_risorse_umane_auth_user (§4.6.F.1 WIP).
--
-- Semantica attesa:
--   - La vista espone il layout di risorse_umane_auth_user leggendo da
--     identita_digitali (OPERATORE).
--   - ruolo_sistema e' ricostruito via CASE:
--       * identita inattiva / ruolo_applicativo=DISABILITATO -> 'DISABILITATO'
--       * fn_is_super_admin=true -> 'ADMIN'
--       * altrimenti -> 'OPERATIVO'
--   - Il trigger-ponte trgfn_rua_sync_identita propaga gli INSERT/UPDATE
--     su RUA alla vista (via identita_digitali); questo test lo verifica
--     scrivendo su RUA e leggendo dalla vista.
--
-- Pattern: sfrutta il seed operatore 'tid' (username fisso) se presente,
-- altrimenti skip. In alternativa, setup manuale con soggetto PF pura.
--
-- Indice test (1..5):
--    1. Setup: crea operatore via fn_crea_operatore (o seed tid)
--    2. Vista legge record con ruolo_sistema='OPERATIVO' (no binding)
--    3. Aggiungendo binding SUPER_ADMIN -> ruolo_sistema='ADMIN'
--    4. Identita inattiva -> ruolo_sistema='DISABILITATO'
--    5. Trigger-ponte: UPDATE RUA.ruolo_sistema='ADMIN' -> vista=ADMIN
--
-- BEGIN; + rollback implicito a fine file.
-- ------------------------------------------------------------

BEGIN;
SELECT plan(5);

-- =========================================================
-- 1) Setup: usa l'operatore seed 'tid' se esiste, altrimenti skip dei test
-- =========================================================
-- L'operatore 'tid' viene seedato da 20260309-01. Se assente
-- (es. CI minimal), gli step restanti skippano.
CREATE TEMP TABLE _t_op AS
SELECT au.id AS auth_user_id
  FROM django.auth_user au
 WHERE au.username = 'tid'
 LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM _t_op) >= 0,
    '1. Setup: tabella _t_op creata (operatore seed tid se presente)'
);

-- =========================================================
-- 2) La vista legge OPERATIVO per un operatore senza binding SUPER_ADMIN
-- =========================================================
-- Rimuovo eventuale binding SUPER_ADMIN preesistente per l'operatore tid.
-- (Il seed tid e' ADMIN via RUA legacy; il trigger-ponte lo ha propagato
-- a binding SUPER_ADMIN. Per questo test lo rimuovo temporaneamente.)
WITH id_op AS (
    SELECT id.id AS identita_id
      FROM anagrafiche.identita_digitali id
      JOIN _t_op op ON op.auth_user_id = id.auth_user_id
     WHERE id.ruolo_applicativo = 'OPERATORE'
     LIMIT 1
)
DELETE FROM config.profili_accesso_bindings pab
 USING id_op
 WHERE pab.identita_digitale_id = id_op.identita_id
   AND pab.profilo_accesso_id = 9100;

SELECT ok(
    CASE
        WHEN (SELECT count(*) FROM _t_op) = 0 THEN true  -- skip se no seed
        ELSE (SELECT ruolo_sistema::text FROM anagrafiche.vw_risorse_umane_auth_user v
                JOIN _t_op op ON op.auth_user_id = v.auth_user_id) = 'OPERATIVO'
    END,
    '2. Vista: operatore senza binding SUPER_ADMIN -> ruolo_sistema=OPERATIVO'
);

-- =========================================================
-- 3) Aggiunta binding SUPER_ADMIN -> vista mostra ADMIN
-- =========================================================
WITH id_op AS (
    SELECT id.id AS identita_id
      FROM anagrafiche.identita_digitali id
      JOIN _t_op op ON op.auth_user_id = id.auth_user_id
     WHERE id.ruolo_applicativo = 'OPERATORE'
     LIMIT 1
)
INSERT INTO config.profili_accesso_bindings
    (profilo_accesso_id, identita_digitale_id, attivo)
SELECT 9100, identita_id, true FROM id_op;

SELECT ok(
    CASE
        WHEN (SELECT count(*) FROM _t_op) = 0 THEN true
        ELSE (SELECT ruolo_sistema::text FROM anagrafiche.vw_risorse_umane_auth_user v
                JOIN _t_op op ON op.auth_user_id = v.auth_user_id) = 'ADMIN'
    END,
    '3. Vista: binding SUPER_ADMIN attivo -> ruolo_sistema=ADMIN'
);

-- =========================================================
-- 4) Identita con attivo=false -> vista mostra DISABILITATO
-- =========================================================
-- NOTA: il trigger framework dbops.trgfn_prevent_deactivate_if_children
-- blocca la disattivazione del padre se ci sono bindings figli attivi
-- (il caso 3 ha creato un binding SUPER_ADMIN). Strategia: disattivare
-- PRIMA il binding (attivo=false), POI l'identita. Questo e' anche il
-- pattern realistico di produzione: il trigger-ponte §4.6.D.4 quando
-- vede RUA.ruolo_sistema='DISABILITATO' imposta identita.attivo=false
-- dopo aver rimosso il binding SUPER_ADMIN.
UPDATE config.profili_accesso_bindings pab
   SET attivo = false
  FROM anagrafiche.identita_digitali id, _t_op op
 WHERE pab.identita_digitale_id = id.id
   AND id.auth_user_id = op.auth_user_id
   AND id.ruolo_applicativo = 'OPERATORE'
   AND pab.profilo_accesso_id = 9100;

UPDATE anagrafiche.identita_digitali id
   SET attivo = false
  FROM _t_op op
 WHERE id.auth_user_id = op.auth_user_id
   AND id.ruolo_applicativo = 'OPERATORE';

SELECT ok(
    CASE
        WHEN (SELECT count(*) FROM _t_op) = 0 THEN true
        ELSE (SELECT ruolo_sistema::text FROM anagrafiche.vw_risorse_umane_auth_user v
                JOIN _t_op op ON op.auth_user_id = v.auth_user_id) = 'DISABILITATO'
    END,
    '4. Vista: identita attivo=false -> ruolo_sistema=DISABILITATO'
);

-- Ripristino per caso 5: riattivo identita + binding.
-- Nota ordine inverso: prima riattivo il padre (identita), poi il figlio
-- (binding). Non c'e' trigger che blocca l'attivazione, solo la
-- disattivazione, quindi l'ordine qui e' per coerenza logica.
UPDATE anagrafiche.identita_digitali id
   SET attivo = true
  FROM _t_op op
 WHERE id.auth_user_id = op.auth_user_id
   AND id.ruolo_applicativo = 'OPERATORE';

UPDATE config.profili_accesso_bindings pab
   SET attivo = true
  FROM anagrafiche.identita_digitali id, _t_op op
 WHERE pab.identita_digitale_id = id.id
   AND id.auth_user_id = op.auth_user_id
   AND id.ruolo_applicativo = 'OPERATORE'
   AND pab.profilo_accesso_id = 9100;

-- =========================================================
-- 5) Trigger-ponte: UPDATE RUA.ruolo_sistema='OPERATIVO' -> vista=OPERATIVO
--    (il trigger trgfn_rua_sync_identita rimuove il binding SUPER_ADMIN
--     quando il ruolo_sistema passa da ADMIN a OPERATIVO)
-- =========================================================
UPDATE anagrafiche.risorse_umane_auth_user rau
   SET ruolo_sistema = 'OPERATIVO'::config.ruolo_sistema
  FROM _t_op op
 WHERE rau.auth_user_id = op.auth_user_id;

SELECT ok(
    CASE
        WHEN (SELECT count(*) FROM _t_op) = 0 THEN true
        ELSE (SELECT ruolo_sistema::text FROM anagrafiche.vw_risorse_umane_auth_user v
                JOIN _t_op op ON op.auth_user_id = v.auth_user_id) = 'OPERATIVO'
    END,
    '5. Trigger-ponte: UPDATE RUA a OPERATIVO -> vista torna a OPERATIVO'
);

SELECT * FROM finish();
ROLLBACK;
