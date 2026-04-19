-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_uo_id_for_user
-- Riferimento: 13.3.7 WIP multi-face-auth (helper risoluzione UO da
-- auth_user_id, catena identita_digitali -> soggetti_ruoli ->
-- risorse_umane -> unita_organizzativa_id).
--
-- Semantica attesa:
--   - auth_user_id inesistente -> NULL
--   - utente non operatore (es. CLIENTE_PORTALE) -> NULL
--   - utente operatore senza RU attiva / senza UO -> NULL
--   - utente operatore con RU attiva e UO -> integer UO id
--
-- Strategia: riuso identita esistenti quando possibile per evitare di
-- urtare fn_guard_soggetto_pf_pura (che richiede PF senza P.IVA per
-- OPERATORE) e il unique parziale su (soggetto_ruolo_id, attivo).
-- Quando non c'e' un caso esistente che matcha, usiamo skip() pgTAP.
--
-- Indice test (1..4):
--    1. Utente auth_user_id inesistente -> NULL
--    2. Utente CLIENTE_PORTALE esistente -> NULL (filtro ruolo OPERATORE)
--    3. Utente OPERATORE senza UO -> NULL (SR con RU ma UO NULL oppure
--       identita OPERATORE senza RU attiva)
--    4. Utente OPERATORE con RU attiva + UO -> ritorna UO id atteso
--
-- BEGIN; + rollback implicito a fine file.
-- ------------------------------------------------------------

BEGIN;
SELECT plan(4);

-- =========================================================
-- 1) auth_user_id inesistente -> NULL
-- =========================================================
SELECT is(
    script.fn_get_uo_id_for_user(
        (SELECT COALESCE(MAX(id), 0) + 999999 FROM django.auth_user)
    ),
    NULL::integer,
    '1. auth_user_id inesistente -> NULL'
);

-- =========================================================
-- Setup casi 2..4: estrae candidati esistenti (no INSERT nuovi).
-- =========================================================
CREATE TEMP TABLE _t_setup (
    case_2_au          int,      -- CLIENTE_PORTALE esistente
    case_3_au          int,      -- OPERATORE senza UO (RU NULL o RU.uo NULL)
    case_4_au          int,      -- OPERATORE con RU attiva + UO
    case_4_expected_uo integer
);

INSERT INTO _t_setup (case_2_au, case_3_au, case_4_au, case_4_expected_uo)
VALUES (
    -- Caso 2: primo auth_user con identita CLIENTE_PORTALE attiva
    (SELECT id.auth_user_id
       FROM anagrafiche.identita_digitali id
      WHERE id.ruolo_applicativo = 'CLIENTE_PORTALE'
        AND id.attivo = true
      ORDER BY id.auth_user_id
      LIMIT 1),
    -- Caso 3: auth_user con identita OPERATORE attiva ma UO non
    -- risolvibile (nessuna RU attiva oppure RU.unita_organizzativa_id NULL).
    (SELECT id.auth_user_id
       FROM anagrafiche.identita_digitali id
      WHERE id.ruolo_applicativo = 'OPERATORE'
        AND id.attivo = true
        AND NOT EXISTS (
            SELECT 1
              FROM anagrafiche.risorse_umane ru
             WHERE ru.soggetto_ruolo_id = id.soggetto_ruolo_id
               AND ru.attivo = true
               AND ru.unita_organizzativa_id IS NOT NULL
        )
      ORDER BY id.auth_user_id
      LIMIT 1),
    -- Caso 4: auth_user con identita OPERATORE + RU attiva + UO valorizzata
    (SELECT id.auth_user_id
       FROM anagrafiche.identita_digitali id
       JOIN anagrafiche.risorse_umane     ru
         ON ru.soggetto_ruolo_id = id.soggetto_ruolo_id
      WHERE id.ruolo_applicativo = 'OPERATORE'
        AND id.attivo = true
        AND ru.attivo = true
        AND ru.unita_organizzativa_id IS NOT NULL
      ORDER BY id.auth_user_id
      LIMIT 1),
    (SELECT ru.unita_organizzativa_id
       FROM anagrafiche.identita_digitali id
       JOIN anagrafiche.risorse_umane     ru
         ON ru.soggetto_ruolo_id = id.soggetto_ruolo_id
      WHERE id.ruolo_applicativo = 'OPERATORE'
        AND id.attivo = true
        AND ru.attivo = true
        AND ru.unita_organizzativa_id IS NOT NULL
      ORDER BY id.auth_user_id
      LIMIT 1)
);

-- =========================================================
-- 2) Utente CLIENTE_PORTALE -> NULL
-- =========================================================
SELECT CASE
    WHEN (SELECT case_2_au IS NOT NULL FROM _t_setup)
    THEN is(
        script.fn_get_uo_id_for_user((SELECT case_2_au FROM _t_setup)),
        NULL::integer,
        '2. Utente CLIENTE_PORTALE -> NULL (filtro ruolo OPERATORE)'
    )
    ELSE skip('Nessuna identita CLIENTE_PORTALE attiva nel DB: test 2 skippato', 1)
END;

-- =========================================================
-- 3) Utente OPERATORE senza UO risolvibile -> NULL
-- =========================================================
SELECT CASE
    WHEN (SELECT case_3_au IS NOT NULL FROM _t_setup)
    THEN is(
        script.fn_get_uo_id_for_user((SELECT case_3_au FROM _t_setup)),
        NULL::integer,
        '3. Utente OPERATORE senza RU attiva / UO valorizzata -> NULL'
    )
    ELSE skip('Nessun OPERATORE senza UO risolvibile: test 3 skippato', 1)
END;

-- =========================================================
-- 4) Utente OPERATORE con RU + UO -> ritorna UO id atteso
-- =========================================================
SELECT CASE
    WHEN (SELECT case_4_au IS NOT NULL FROM _t_setup)
    THEN is(
        script.fn_get_uo_id_for_user((SELECT case_4_au FROM _t_setup)),
        (SELECT case_4_expected_uo FROM _t_setup),
        '4. Utente OPERATORE con RU attiva + UO -> ritorna unita_organizzativa_id atteso'
    )
    ELSE skip('Nessun OPERATORE con RU+UO: test 4 skippato', 1)
END;

SELECT * FROM finish();
