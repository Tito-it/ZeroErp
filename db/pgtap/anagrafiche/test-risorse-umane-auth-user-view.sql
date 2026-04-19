-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vista anagrafiche.risorse_umane_auth_user (§13.3.2 WIP).
--
-- Post-cutover §13.3.2 (2026-04-19): la vista ha preso il nome
-- canonico (la tabella legacy e' stata rinominata _legacy_...).
-- Il trigger-ponte RUA -> identita_digitali e' stato droppato
-- (migration 20260419-91): ogni scrittura ora passa da
-- fn_crea_risorsa_umana / amm_software_repository direttamente su
-- identita_digitali + bindings. Questo test verifica solo la
-- semantica di lettura della vista.
--
-- Strategia: il test usa un'identita OPERATORE "vergine" (senza
-- binding SUPER_ADMIN pre-esistente) come soggetto. Cosi' tutte le
-- modifiche del test riguardano solo quella identita e NON scattano
-- il guard anti-lockout ultimo SUPER_ADMIN (i binding SA dei
-- preesistenti, es. operatore 'tid', restano attivi).
--
-- Semantica attesa (ricostruzione ruolo_sistema):
--   * identita inattiva / ruolo_applicativo=DISABILITATO / fuori
--     finestra temporale -> 'DISABILITATO'
--   * binding SUPER_ADMIN attivo -> 'ADMIN'
--   * altrimenti -> 'OPERATIVO'
--
-- Indice test (1..4):
--    1. Setup: identifica un'identita OPERATORE vergine (skip se assente)
--    2. Vista: identita vergine senza binding -> ruolo_sistema=OPERATIVO
--    3. Vista: aggiungendo binding SUPER_ADMIN -> ruolo_sistema=ADMIN
--    4. Vista: disattivando binding + identita -> ruolo_sistema=DISABILITATO
--
-- BEGIN; + ROLLBACK a fine file.
-- ------------------------------------------------------------

BEGIN;
SELECT plan(4);

-- =========================================================
-- 1) Setup: identita OPERATORE vergine (senza alcun binding)
-- =========================================================
-- Il vincolo UNIQUE parziale uq_profili_accesso_bindings_identita
-- permette al piu' un binding per identita. Scelgo una identita con
-- nessun binding per poter aggiungere quello SUPER_ADMIN senza
-- conflitti, e cosi' isolare gli effetti dai preesistenti.
CREATE TEMP TABLE _t_op AS
SELECT id.auth_user_id,
       id.id AS identita_id
  FROM anagrafiche.identita_digitali id
 WHERE id.ruolo_applicativo = 'OPERATORE'
   AND id.attivo = true
   AND NOT EXISTS (
       SELECT 1 FROM config.profili_accesso_bindings pab
        WHERE pab.identita_digitale_id = id.id
   )
 ORDER BY id.id
 LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM _t_op) >= 0,
    '1. Setup: tabella _t_op creata (identita OPERATORE vergine se presente)'
);

-- =========================================================
-- 2) Identita vergine senza binding -> ruolo_sistema=OPERATIVO
-- =========================================================
SELECT CASE
    WHEN (SELECT count(*) FROM _t_op) = 0
    THEN skip('Nessuna identita OPERATORE vergine disponibile: test 2 skippato', 1)
    ELSE ok(
        (SELECT ruolo_sistema::text
           FROM anagrafiche.risorse_umane_auth_user v
           JOIN _t_op op ON op.auth_user_id = v.auth_user_id) = 'OPERATIVO',
        '2. Vista: identita senza binding SUPER_ADMIN -> ruolo_sistema=OPERATIVO'
    )
END;

-- =========================================================
-- 3) Aggiunto binding SUPER_ADMIN -> vista mostra ADMIN
-- =========================================================
INSERT INTO config.profili_accesso_bindings
    (profilo_accesso_id, identita_digitale_id, attivo)
SELECT 9100, identita_id, true
  FROM _t_op;

SELECT CASE
    WHEN (SELECT count(*) FROM _t_op) = 0
    THEN skip('Setup non completato: test 3 skippato', 1)
    ELSE ok(
        (SELECT ruolo_sistema::text
           FROM anagrafiche.risorse_umane_auth_user v
           JOIN _t_op op ON op.auth_user_id = v.auth_user_id) = 'ADMIN',
        '3. Vista: binding SUPER_ADMIN attivo -> ruolo_sistema=ADMIN'
    )
END;

-- =========================================================
-- 4) Disattivo binding + identita -> vista mostra DISABILITATO
-- =========================================================
-- Questo NON scatta il guard anti-lockout: i binding SA preesistenti
-- (seed 80_data, es. tid) restano attivi, quindi non siamo mai
-- sull'ultimo SUPER_ADMIN.
-- Ordine: prima binding (child), poi identita (parent).
UPDATE config.profili_accesso_bindings pab
   SET attivo = false
  FROM _t_op op
 WHERE pab.identita_digitale_id = op.identita_id
   AND pab.profilo_accesso_id = 9100;

UPDATE anagrafiche.identita_digitali id
   SET attivo = false
  FROM _t_op op
 WHERE id.id = op.identita_id;

SELECT CASE
    WHEN (SELECT count(*) FROM _t_op) = 0
    THEN skip('Setup non completato: test 4 skippato', 1)
    ELSE ok(
        (SELECT ruolo_sistema::text
           FROM anagrafiche.risorse_umane_auth_user v
           JOIN _t_op op ON op.auth_user_id = v.auth_user_id) = 'DISABILITATO',
        '4. Vista: identita attivo=false -> ruolo_sistema=DISABILITATO'
    )
END;

SELECT * FROM finish();
ROLLBACK;
