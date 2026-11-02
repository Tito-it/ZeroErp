-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
    -- Caso 2: primo auth_user CLIENTE_PORTALE e NON operatore.
    -- 🔴 `NOT EXISTS` aggiunto il 2026-08-18. Prendeva «il primo auth_user con
    --   identita CLIENTE_PORTALE attiva» — ma la funzione ha per chiave
    --   l'AUTH_USER, non l'identita', e in un modello MULTI-VESTE lo stesso
    --   auth_user puo' essere insieme CLIENTE_PORTALE e OPERATORE. In sviluppo
    --   l'utente 1 lo e' (lo dimostra test-fn-get-user-profile-guc-aware, che
    --   su quella coppia trovava gia' la riga).
    --   Quindi la funzione rispondeva con la UO della veste OPERATORE — cioe'
    --   CORRETTAMENTE — e il test la leggeva come una fuga di perimetro.
    --   ⚠️ Il difetto era nella scelta del soggetto, non nella funzione:
    --   l'intestazione del file dice «utente NON operatore -> NULL», e la
    --   query non lo imponeva. Ora si sceglie chi ha SOLO la veste portale;
    --   se non esiste, il CASE sotto fa skip dichiarato.
    (SELECT id.auth_user_id
       FROM anagrafiche.identita_digitali id
      WHERE id.ruolo_applicativo = 'CLIENTE_PORTALE'
        AND id.attivo = true
        AND NOT EXISTS (
            SELECT 1 FROM anagrafiche.identita_digitali o
             WHERE o.auth_user_id = id.auth_user_id
               AND o.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
               AND o.attivo = true
        )
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
    -- 🔴 SKIP ONESTO — 2026-08-18. Il messaggio diceva «nessuna identita
    --   CLIENTE_PORTALE attiva»: falso, ce ne sono. A mancare e' un auth_user
    --   con la SOLA veste portale, e sono ZERO (misurato).
    --   ⚠️ Quindi questo caso NON e' coperto, e va detto: uno skip che racconta
    --   la ragione sbagliata e' peggio di un rosso, perche' sembra una scelta.
    --   ⭐ Costruire la precondizione e' stato tentato e NON si puo' a buon
    --   mercato: spegnere la veste OPERATORE di un utente multi-veste urta
    --   `prevent_deactivate_if_children` (ha figli attivi), e creare un
    --   auth_user nuovo vuole un soggetto_ruolo CL libero piu' i guard di
    --   identita'. Resta un DEBITO DI COPERTURA dichiarato, non una svista.
    ELSE skip('Nessun auth_user con la SOLA veste CLIENTE_PORTALE (misurato: 0): il filtro ruolo NON e'' verificato — debito di copertura dichiarato', 1)
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
