-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: tutte le funzioni di risoluzione permessi e trigger
-- rev 2026-10-27 (brief-modello-documento-vendita §15, giro 11): reset_lotto_draft e'
--   ritirata (Q-F1: «riporta in bozza» chiede numera_fatture_lotti). Test 30: i codename
--   della sezione I ancora vivi sono due, e reset_lotto_draft e' spenta.
-- ⚠️ Attesa cambiata: test 30 (3 attivi -> 2 attivi + reset_lotto_draft spenta).
--       defense-in-depth guard emittente scope.
--
-- Migrazione Fase 7 Chunk A (2026-04-29):
--   Pre-cutover il test forzava lo stato dell'utente via UPDATE su
--   rau.ruolo_sistema (OPERATIVO/ADMIN/DISABILITATO). Post-cutover
--   §13.3 RAU e' vista non updatable + ruolo_sistema CASE calcolato.
--   Sostituzioni:
--     UPDATE rau SET ruolo_sistema='OPERATIVO' (forzatura iniziale)
--       -> setup COSTRUISCE un operatore non-SA (rev 2026-09-23,
--          sotto): stato gia' "OPERATIVO".
--     UPDATE rau SET ruolo_sistema='ADMIN' (cicli temporanei)
--       -> INSERT binding SUPER_ADMIN (helper pg_temp.set_admin).
--     UPDATE rau SET ruolo_sistema='OPERATIVO' (ripristino post-ADMIN)
--       -> DELETE del binding (helper pg_temp.unset_admin). Un SA
--          di presidio COSTRUITO al setup garantisce che il SA del
--          test non sia mai l'unico -> guard anti-lockout non scatta.
--     UPDATE rau SET ruolo_sistema='DISABILITATO' (test 29)
--       -> UPDATE id.attivo = false (helper pg_temp.set_disabilitato).
--     Ripristino -> UPDATE id.attivo = true (pg_temp.unset_disabilitato).
--     ⚠️ Rev 2026-10-02 (brief-db-be-fe-area-accessi R-DB-1): fino a quel
--     giorno i due helper scrivevano ruolo_applicativo = DISABILITATO /
--     OPERATORE. Una veste si spegne con attivo = false e tiene il tipo, e
--     la tabella viva rifiuta DISABILITATO.
--
-- Funzioni testate:
--   script.fn_is_super_admin (sostituisce fn_get_ruolo_sistema
--     droppata in Fase 7 cleanup 2026-04-29),
--   script.fn_resolve_livello_area,
--   script.fn_resolve_livello_oggetto,
--   script.fn_get_user_object_permissions_map,
--   script.fn_check_azione_processo,
--   script.fn_get_emittenti_scope  [DISMESSA 2026-08-18: il test 13 ora
--     verifica che NON esista piu'],
--   script.fn_check_user_emittente_scope,
--   script.fn_get_override_scaduti,
--   script.fn_get_emittenti_scope_sr_ids,
--   script.trgfn_guard_emittente_scope (+ 2 trigger).
--
-- Elenco test:
--  1) fn_is_super_admin: utente OPERATORE non-SA → false
--  2) fn_is_super_admin: utente inesistente → false (fail-closed)
--  3) fn_resolve_livello_area: OPERATIVO default → BLOCCATO
--  4) fn_resolve_livello_area: ADMIN → TUTTO
--  5) fn_resolve_livello_area: override area LETTURA → LETTURA
--  6) fn_resolve_livello_area: override scaduto → BLOCCATO
--  7) fn_resolve_livello_oggetto: OPERATIVO default → BLOCCATO
--  8) fn_resolve_livello_oggetto: override oggetto LETTURA sotto l'area TUTTO → LETTURA
--  9) fn_resolve_livello_oggetto: fallback ad area TUTTO → TUTTO
-- 10) fn_check_azione_processo: OPERATIVO default → false
-- 11) fn_check_azione_processo: ADMIN → true
-- 12) fn_check_azione_processo: override abilitata, area dell'azione TUTTO → true
-- 13) legacy fn_get_emittenti_scope: DISMESSA (asserzione girata di segno)
-- 14) fn_check_user_emittente_scope: NULL user → false (rev 2026-10-04, Q-1)
-- 15) fn_check_user_emittente_scope: ADMIN → true
-- 16) fn_check_user_emittente_scope: OPERATIVO senza whitelist → false (P-2a)
-- 17) fn_check_user_emittente_scope: emittente in whitelist → true
-- 18) fn_check_user_emittente_scope: emittente fuori whitelist → false
-- 19) fn_get_emittenti_scope_pk_ids (erede guarded): con whitelist → array contiene emittente
-- 20) fn_get_override_scaduti(0): override scaduto trovato
-- 21) fn_get_override_scaduti(30): override recente escluso da tolleranza
-- 22) Trigger function trgfn_guard_emittente_scope esiste
-- 23) Trigger su vendite.fatture esiste (BEFORE INSERT OR UPDATE)
-- 24) Trigger su pagamenti.vendite_movimenti esiste
-- 25) Integrazione: fn_check blocca emittente fuori scope
-- 26) fn_get_emittenti_scope_sr_ids: OPERATIVO con whitelist → array con sr_id
-- 27) fn_get_emittenti_scope_sr_ids: ADMIN → NULL
-- 28) fn_get_emittenti_scope_sr_ids: OPERATIVO senza whitelist → NULL
-- 29) fn_get_emittenti_scope_sr_ids: veste operatore spenta → array vuoto
-- 30) Seed: 3 nuovi codename azioni_processo esistono
-- 31) fn_get_user_object_permissions_map: nessun override → il livello d'area
-- 32) fn_get_user_object_permissions_map: override attivo → il livello dell'override
-- 33) fn_get_user_object_permissions_map: override scaduto → torna l'area
-- 34) fn_get_user_object_permissions_map: override futuro → l'area
--
-- ⚠️ Rev 2026-10-04 (brief-db-permessi-tetto-area, 20261004-55 → -58): l'area e' un
--   TETTO. I test 8, 12 e 31-34 provavano «il piu' specifico vince» sotto un'area
--   BLOCCATO (il default dell'operatore costruito): riscritti sulla regola nuova,
--   con l'area aperta dal test. La regola stessa (area chiusa + override che
--   allarga) la prova test-permessi-tetto-area-v1. La mappa degli oggetti non da'
--   piu' i soli override: da' il livello EFFETTIVO di ogni oggetto del catalogo.
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

SELECT plan(34);

-- ============================================================================
-- rev 2026-09-23 (brief-db-fixture-che-costruiscono-giro-2, lotto 2).
--   Il setup PESCAVA «la prima identita' OPERATORE attiva non-SA» e il primo
--   emittente attivo, e contava su un super admin preesistente. Su un database
--   ricostruito (la CI) tre difetti in fila:
--   1. l'unica identita' OPERATORE e' quella del CONTESTO (costruita dalla
--      riga di contesto): il test ne cancellava whitelist e override e ne
--      cambiava i binding — il soggetto del test era chi agisce;
--   2. nessun altro super admin: tolto il binding SA del test,
--      unset_admin moriva sul guard anti-lockout («rimarrebbe zero
--      SUPER_ADMIN attivi»), al test 4;
--   3. il profilo SA per id cablato: vero solo perche' il seed porta l'id
--      esplicito (lo stesso difetto corretto nella madre da 20260923-10).
--   Ora: l'operatore del test si COSTRUISCE (fn_pgtap_crea_operatore_umano,
--   nasce senza azienda: niente whitelist, niente override), un super admin
--   di PRESIDIO si costruisce accanto, il profilo SA si risolve dal TIPO, e
--   l'emittente e' quello di chi agisce (script.fn_pgtap_emittente_operatore:
--   l'emittente non si pesca, si deriva).
--   ⛔ Cio' che il builder scrive si legge in un'istruzione SEPARATA.
-- ============================================================================

-- ============================================================
-- Helper pg_temp per il refactor multi-face:
--   set_admin / unset_admin    -> INSERT/DELETE binding SUPER_ADMIN
--   set_disabilitato / unset_disabilitato -> UPDATE id.ruolo_applicativo
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.set_admin(p_identita_id bigint)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    -- Il profilo SA si risolve dal TIPO (chiave stabile, come in
    -- fn_is_super_admin), non dall'id del seed.
    INSERT INTO config.profili_accesso_bindings
        (profilo_accesso_id, identita_digitale_id, attivo)
    SELECT pa.id, p_identita_id, true
      FROM config.profili_accesso pa
     WHERE pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
       AND pa.attivo
    ON CONFLICT DO NOTHING;
END
$$;

CREATE OR REPLACE FUNCTION pg_temp.unset_admin(p_identita_id bigint)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM config.profili_accesso_bindings pab
     USING config.profili_accesso pa
     WHERE pa.id = pab.profilo_accesso_id
       AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
       AND pab.identita_digitale_id = p_identita_id;
END
$$;

-- Rev 2026-10-02 (R-DB-1): l'operatore si spegne con attivo = false, il tipo resta.
CREATE OR REPLACE FUNCTION pg_temp.set_disabilitato(p_identita_id bigint)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    UPDATE anagrafiche.identita_digitali
       SET attivo = false
     WHERE id = p_identita_id;
END
$$;

CREATE OR REPLACE FUNCTION pg_temp.unset_disabilitato(p_identita_id bigint)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    UPDATE anagrafiche.identita_digitali
       SET attivo = true
     WHERE id = p_identita_id;
END
$$;

-- ============================================================
-- 0. Setup: operatore non-SA COSTRUITO + SA di presidio costruito
--    + area_funzionali + azioni_processo + emittente di chi agisce.
-- ============================================================

-- L'operatore del test: nasce senza azienda, senza binding SA, senza
-- override ne' whitelist — lo stato «OPERATIVO» di default.
CREATE TEMP TABLE tmp_op AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('permessi risoluzione');

-- Il SA di presidio: c'e' solo perche' unset_admin non tolga l'ULTIMO
-- super admin (guard anti-lockout). Non entra in nessuna asserzione.
CREATE TEMP TABLE tmp_sa_presidio AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('permessi presidio SA', p_super_admin := true);

CREATE TEMP TABLE tmp_ctx AS
SELECT
    id.auth_user_id        AS user_id,
    id.id                  AS identita_id,
    af.id                  AS area_id,
    af.schema_db           AS area_schema_db,
    ap.id                  AS azione_id,
    ap.permission_codename,
    ef.id                  AS emittente_id,
    ef.soggetto_ruolo_id   AS emittente_sr_id,
    -1::bigint             AS emittente_ko_id
FROM anagrafiche.identita_digitali id
CROSS JOIN (
    SELECT id, schema_db FROM config.aree_funzionali
    WHERE attivo = true AND schema_db = 'vendite'
) af
CROSS JOIN (
    SELECT id, permission_codename FROM config.azioni_processo
    WHERE attivo = true ORDER BY id LIMIT 1
) ap
CROSS JOIN (
    -- L'emittente di chi agisce: visibile sotto RLS per costruzione.
    SELECT ef0.id, ef0.soggetto_ruolo_id
      FROM anagrafiche.emittenti_fiscali ef0
     WHERE ef0.id = script.fn_pgtap_emittente_operatore()
) ef
JOIN tmp_op op
  ON op.identita_id = id.id;

-- Pre-condizione dei test 3/6/7 (default BLOCCATO): l'operatore costruito
-- non ha profili che concedono 'vendite' (fn_resolve_livello_area step 4
-- lo promuoverebbe). Era un filtro della pesca; ora e' un controllo di
-- setup che, se cade, dice perche' cadono i test dopo.
DO $pre$
BEGIN
    IF (SELECT count(*) FROM tmp_ctx) <> 1 THEN
        RAISE EXCEPTION 'Setup: tmp_ctx ha % righe, attesa 1', (SELECT count(*) FROM tmp_ctx);
    END IF;
    IF EXISTS (
        SELECT 1
          FROM script.fn_get_profili_accesso_applicabili((SELECT user_id FROM tmp_ctx)) h
          JOIN config.profili_accesso_aree paa ON paa.profilo_accesso_id = h.profilo_accesso_id
          JOIN config.aree_funzionali af2 ON af2.id = paa.area_id
         WHERE af2.schema_db = 'vendite'
    ) THEN
        RAISE EXCEPTION 'Setup: l''operatore costruito ha un profilo che concede vendite';
    END IF;
END
$pre$;

-- ============================================================
-- A. fn_is_super_admin (sostituisce fn_get_ruolo_sistema droppata
--    in Fase 7 cleanup 2026-04-29)
-- ============================================================

-- 1) Utente OPERATORE non-SA (costruito al setup) → false
SELECT is(
    script.fn_is_super_admin(
        (SELECT user_id FROM tmp_ctx)
    ),
    false,
    '1) fn_is_super_admin: utente OPERATORE non-SA → false'
);

-- 2) Utente inesistente → false (fail-closed)
SELECT is(
    script.fn_is_super_admin(99999999),
    false,
    '2) fn_is_super_admin: utente inesistente → false (fail-closed)'
);

-- ============================================================
-- B. fn_resolve_livello_area
-- ============================================================

-- 3) OPERATIVO senza override/profilo → BLOCCATO (default)
SELECT is(
    script.fn_resolve_livello_area(
        (SELECT user_id FROM tmp_ctx),
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'BLOCCATO'::config.livello_accesso,
    '3) fn_resolve_livello_area: OPERATIVO default → BLOCCATO'
);

-- 4) ADMIN → TUTTO
SELECT pg_temp.set_admin((SELECT identita_id FROM tmp_ctx));

SELECT is(
    script.fn_resolve_livello_area(
        (SELECT user_id FROM tmp_ctx),
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'TUTTO'::config.livello_accesso,
    '4) fn_resolve_livello_area: ADMIN → TUTTO'
);

SELECT pg_temp.unset_admin((SELECT identita_id FROM tmp_ctx));

-- 5) Override area LETTURA → LETTURA
INSERT INTO config.user_override_aree
    (auth_user_id, area_id, livello, meta)
SELECT user_id, area_id, 'LETTURA'::config.livello_accesso,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

SELECT is(
    script.fn_resolve_livello_area(
        (SELECT user_id FROM tmp_ctx),
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'LETTURA'::config.livello_accesso,
    '5) fn_resolve_livello_area: override area LETTURA → LETTURA'
);

-- 6) Override scaduto (valido_al = ieri) → ignorato → BLOCCATO
UPDATE config.user_override_aree
   SET valido_dal = script.fn_data_operativa() - 30,
       valido_al  = script.fn_data_operativa() - 1
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx)
   AND area_id = (SELECT area_id FROM tmp_ctx);

SELECT is(
    script.fn_resolve_livello_area(
        (SELECT user_id FROM tmp_ctx),
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'BLOCCATO'::config.livello_accesso,
    '6) fn_resolve_livello_area: override scaduto → BLOCCATO'
);

-- Pulizia override area per test successivi
DELETE FROM config.user_override_aree
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- ============================================================
-- C. fn_resolve_livello_oggetto
-- ============================================================

-- 7) OPERATIVO senza override → BLOCCATO (fallback area = BLOCCATO)
--    Oggetto ('vendite', 'fattura'): a catalogo. Fino al 2026-09-28 era 'fatture',
--    che il catalogo non ha: la FK composita della D-4 (brief-db-be-fe-catalogo-
--    oggetti-permessi) rifiuta un override per oggetto fuori catalogo.
SELECT is(
    script.fn_resolve_livello_oggetto(
        (SELECT user_id FROM tmp_ctx),
        'vendite', 'fattura',
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'BLOCCATO'::config.livello_accesso,
    '7) fn_resolve_livello_oggetto: OPERATIVO default → BLOCCATO'
);

-- 8) Override oggetto LETTURA sotto l'area TUTTO → LETTURA (lo specifico restringe).
--    ⚠️ Fino al 2026-10-04 l'area restava BLOCCATO: provava «lo specifico vince»,
--    che col tetto d'area e' il contrario della regola.
INSERT INTO config.user_override_aree
    (auth_user_id, area_id, livello, meta)
SELECT user_id, area_id, 'TUTTO'::config.livello_accesso,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

INSERT INTO config.user_override_oggetti
    (auth_user_id, app_label, model_name, livello, meta)
SELECT user_id, 'vendite', 'fattura', 'LETTURA'::config.livello_accesso,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

SELECT is(
    script.fn_resolve_livello_oggetto(
        (SELECT user_id FROM tmp_ctx),
        'vendite', 'fattura',
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'LETTURA'::config.livello_accesso,
    '8) fn_resolve_livello_oggetto: override oggetto LETTURA sotto l''area TUTTO → LETTURA'
);

DELETE FROM config.user_override_oggetti
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

DELETE FROM config.user_override_aree
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- 9) Fallback ad area: override area TUTTO, nessun override oggetto → TUTTO
INSERT INTO config.user_override_aree
    (auth_user_id, area_id, livello, meta)
SELECT user_id, area_id, 'TUTTO'::config.livello_accesso,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

SELECT is(
    script.fn_resolve_livello_oggetto(
        (SELECT user_id FROM tmp_ctx),
        'vendite', 'fattura',
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'TUTTO'::config.livello_accesso,
    '9) fn_resolve_livello_oggetto: fallback ad area TUTTO → TUTTO'
);

DELETE FROM config.user_override_aree
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- ============================================================
-- D. fn_check_azione_processo
-- ============================================================

-- 10) OPERATIVO senza override/profilo → false (default)
SELECT is(
    script.fn_check_azione_processo(
        (SELECT user_id FROM tmp_ctx),
        (SELECT permission_codename FROM tmp_ctx)
    ),
    false,
    '10) fn_check_azione_processo: OPERATIVO default → false'
);

-- 11) ADMIN → true
SELECT pg_temp.set_admin((SELECT identita_id FROM tmp_ctx));

SELECT is(
    script.fn_check_azione_processo(
        (SELECT user_id FROM tmp_ctx),
        (SELECT permission_codename FROM tmp_ctx)
    ),
    true,
    '11) fn_check_azione_processo: ADMIN → true'
);

SELECT pg_temp.unset_admin((SELECT identita_id FROM tmp_ctx));

-- 12) Override azione abilitata, area dell'azione TUTTO → true.
--     ⚠️ Rev 2026-10-04: col tetto d'area l'override vale solo se l'area dell'azione
--     arriva al suo livello_minimo_area; l'area si apre qui, sull'area DELL'AZIONE
--     (non e' detto che sia vendite).
INSERT INTO config.user_override_aree
    (auth_user_id, area_id, livello, meta)
SELECT t.user_id, ap.area_id, 'TUTTO'::config.livello_accesso,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx t
JOIN config.azioni_processo ap ON ap.id = t.azione_id;

INSERT INTO config.user_override_azioni
    (auth_user_id, azione_id, abilitata, meta)
SELECT user_id, azione_id, true,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

SELECT is(
    script.fn_check_azione_processo(
        (SELECT user_id FROM tmp_ctx),
        (SELECT permission_codename FROM tmp_ctx)
    ),
    true,
    '12) fn_check_azione_processo: override abilitata, area dell''azione TUTTO → true'
);

DELETE FROM config.user_override_azioni
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

DELETE FROM config.user_override_aree
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- ============================================================
-- E. dismissione della legacy + fn_check_user_emittente_scope
-- ============================================================

-- 13) ⛔ L'asserzione non e' stata CANCELLATA: e' stata GIRATA DI SEGNO.
--     Diceva «senza whitelist → NULL», cioe' «un utente senza abilitazioni vede
--     tutti gli emittenti»: il fail-open che P-2a ha chiuso ovunque il
--     2026-08-18. La legacy non e' mai stata allineata perche' non la
--     chiamava piu' nessuno, ed e' stata dismessa (changeSet 20260818-66).
--     Ora il test dice che la funzione NON C'E' PIU': chi la ricreasse
--     troverebbe questa riga rossa. Cancellarlo avrebbe tolto il presidio
--     insieme al difetto.
SELECT hasnt_function(
    'script', 'fn_get_emittenti_scope', ARRAY['integer'],
    '13) legacy fn_get_emittenti_scope: DISMESSA (era il fail-open «senza whitelist → tutti»)'
);

-- 14) fn_check NULL user → false. Rev 2026-10-04 (Q-1,
--     brief-db-esclusioni-implicite): era true («batch job»).
SELECT is(
    script.fn_check_user_emittente_scope(
        NULL,
        (SELECT emittente_id FROM tmp_ctx)
    ),
    false,
    '14) fn_check_user_emittente_scope: NULL user → false (era true, «batch»)'
);

-- 15) fn_check ADMIN → true
SELECT pg_temp.set_admin((SELECT identita_id FROM tmp_ctx));

SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_ctx),
        (SELECT emittente_id FROM tmp_ctx)
    ),
    true,
    '15) fn_check_user_emittente_scope: ADMIN → true'
);

SELECT pg_temp.unset_admin((SELECT identita_id FROM tmp_ctx));

-- 16) OPERATIVO senza whitelist → FALSE (fail-closed, P-2a 2026-08-18)
--     ⚠️ Diceva `true`. Vedi la nota al test 28: non e' una fixture da
--     riallineare, e' il contratto che e' cambiato.
SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_ctx),
        (SELECT emittente_id FROM tmp_ctx)
    ),
    false,
    '16) fn_check_user_emittente_scope: OPERATIVO senza whitelist → false (P-2a)'
);

-- Inserisce whitelist per emittente_id (reale)
INSERT INTO config.user_emittenti_fiscali
    (auth_user_id, emittente_fiscale_id, meta)
SELECT user_id, emittente_id,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

-- 17) Emittente in whitelist → true
SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_ctx),
        (SELECT emittente_id FROM tmp_ctx)
    ),
    true,
    '17) fn_check_user_emittente_scope: emittente in whitelist → true'
);

-- 18) Emittente fuori whitelist → false
SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_ctx),
        (SELECT emittente_ko_id FROM tmp_ctx)
    ),
    false,
    '18) fn_check_user_emittente_scope: emittente fuori whitelist → false'
);

-- 19) La COPERTURA non se ne va con la funzione: la stessa domanda — «la
--     whitelist finisce nello scope?» — si fa all'erede guarded
--     fn_get_emittenti_scope_pk_ids, che risponde in PK emittente come la
--     legacy. Il test 13 presidia che la vecchia non torni; questo continua a
--     verificare il comportamento.
SELECT ok(
    (SELECT emittente_id FROM tmp_ctx) = ANY(
        script.fn_get_emittenti_scope_pk_ids(
            (SELECT user_id FROM tmp_ctx)
        )
    ),
    '19) fn_get_emittenti_scope_pk_ids (erede guarded): con whitelist → array contiene emittente'
);

-- ============================================================
-- F. fn_get_override_scaduti
-- ============================================================

-- Inserisce override scaduto (valido_dal = 30 gg fa, valido_al = 10 gg fa)
INSERT INTO config.user_override_aree
    (auth_user_id, area_id, livello, valido_dal, valido_al, meta)
SELECT user_id, area_id, 'LETTURA'::config.livello_accesso,
       script.fn_data_operativa() - 30, script.fn_data_operativa() - 10,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

-- 20) Tolleranza 0 → trova override scaduto
SELECT ok(
    EXISTS (
        SELECT 1 FROM script.fn_get_override_scaduti(0)
        WHERE auth_user_id = (SELECT user_id FROM tmp_ctx)
          AND tipo_override = 'user_override_aree'
    ),
    '20) fn_get_override_scaduti(0): override scaduto trovato'
);

-- 21) Tolleranza 30 → non trova (scaduto solo da 10 giorni)
SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM script.fn_get_override_scaduti(30)
        WHERE auth_user_id = (SELECT user_id FROM tmp_ctx)
          AND tipo_override = 'user_override_aree'
    ),
    '21) fn_get_override_scaduti(30): override recente escluso da tolleranza'
);

-- ============================================================
-- G. trgfn_guard_emittente_scope + trigger
-- ============================================================

-- 22) Trigger function esiste
SELECT ok(
    EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'script'
          AND p.proname = 'trgfn_guard_emittente_scope'
    ),
    '22) Trigger function script.trgfn_guard_emittente_scope esiste'
);

-- 23) Trigger su vendite.fatture esiste (BEFORE INSERT OR UPDATE)
SELECT ok(
    EXISTS (
        SELECT 1
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'vendite'
          AND c.relname = 'fatture'
          AND t.tgname  = 'trg_fatture_a10_guard_emittente_scope_ins_upd'
          AND NOT t.tgisinternal
          AND (t.tgtype::int & 2)  > 0  -- BEFORE
          AND (t.tgtype::int & 4)  > 0  -- INSERT
          AND (t.tgtype::int & 16) > 0  -- UPDATE
    ),
    '23) Trigger vendite.fatture: BEFORE INSERT OR UPDATE esiste'
);

-- 24) Trigger su pagamenti.vendite_movimenti esiste
SELECT ok(
    EXISTS (
        SELECT 1
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'pagamenti'
          AND c.relname = 'vendite_movimenti'
          AND t.tgname  = 'trg_vendite_movimenti_a10_guard_emittente_scope_ins_upd'
          AND NOT t.tgisinternal
    ),
    '24) Trigger pagamenti.vendite_movimenti esiste'
);

-- 25) Integrazione: fn_check blocca emittente fuori scope
--     La whitelist e' gia inserita (emittente_id in scope).
SELECT set_config('app.current_user_id',
    (SELECT user_id::text FROM tmp_ctx), true);

SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_ctx),
        (SELECT emittente_ko_id FROM tmp_ctx)
    ),
    false,
    '25) Integrazione: fn_check blocca emittente fuori scope (catena trigger)'
);

-- ============================================================
-- H. fn_get_emittenti_scope_sr_ids
--    (whitelist presente da sezione E, utente OPERATIVO)
-- ============================================================

-- 26) OPERATIVO con whitelist → array contiene soggetto_ruolo_id
SELECT ok(
    (SELECT emittente_sr_id FROM tmp_ctx) = ANY(
        script.fn_get_emittenti_scope_sr_ids(
            (SELECT user_id FROM tmp_ctx)
        )
    ),
    '26) fn_get_emittenti_scope_sr_ids: OPERATIVO con whitelist → array con sr_id'
);

-- 27) ADMIN → NULL (nessuna restrizione)
SELECT pg_temp.set_admin((SELECT identita_id FROM tmp_ctx));

SELECT is(
    script.fn_get_emittenti_scope_sr_ids(
        (SELECT user_id FROM tmp_ctx)
    ),
    NULL::bigint[],
    '27) fn_get_emittenti_scope_sr_ids: ADMIN → NULL'
);

SELECT pg_temp.unset_admin((SELECT identita_id FROM tmp_ctx));

-- Rimuovi whitelist per test "senza whitelist"
SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

-- 28) OPERATIVO senza whitelist → '{}' (fail-closed, P-2a 2026-08-18)
--     ⚠️ Diceva `NULL`, cioe' «nessuna restrizione». Nella convenzione a tre
--     stati NULL = TUTTO e '{}' = NIENTE: un operatore senza riga finiva
--     dalla parte che apre, ed era indistinguibile da un super admin.
--     Questa asserzione verifica anche l'EREDITA': _sr_ids non e' stata
--     modificata da P-2a, cambia perche' e' un wrapper sulla canonica _pk_ids.
--     Brief perimetro-emittente §2.5.
SELECT is(
    script.fn_get_emittenti_scope_sr_ids(
        (SELECT user_id FROM tmp_ctx)
    ),
    '{}'::bigint[],
    '28) fn_get_emittenti_scope_sr_ids: OPERATIVO senza whitelist → ''{}'' (P-2a)'
);

-- 29) veste OPERATORE spenta → array vuoto (nessun accesso)
SELECT pg_temp.set_disabilitato((SELECT identita_id FROM tmp_ctx));

SELECT is(
    script.fn_get_emittenti_scope_sr_ids(
        (SELECT user_id FROM tmp_ctx)
    ),
    '{}'::bigint[],
    '29) fn_get_emittenti_scope_sr_ids: veste operatore spenta → array vuoto'
);

SELECT pg_temp.unset_disabilitato((SELECT identita_id FROM tmp_ctx));

-- ============================================================
-- I. Seed azioni_processo — nuovi codename
-- ============================================================

-- 30) Verifica che i 3 nuovi codename esistano
SELECT is(
    (SELECT string_agg(permission_codename || ':' || attivo::text, ' ' ORDER BY permission_codename)
       FROM config.azioni_processo
      WHERE permission_codename IN (
              'reset_lotto_draft',
              'reset_lotto_fattura_draft',
              'run_commesse_push'
            )
    ),
    'reset_lotto_draft:false reset_lotto_fattura_draft:true run_commesse_push:true',
    '30) Seed: i codename della sezione I presenti; reset_lotto_draft ritirata (giro 11, Q-F1)'
);

-- ============================================================
-- J. fn_get_user_object_permissions_map
-- ============================================================

-- Dal 2026-10-04 (R5) la mappa da' il livello EFFETTIVO di ogni oggetto del
-- catalogo, col tetto d'area: si apre l'area di vendite.fattura a TUTTO, cosi'
-- l'override LETTURA si legge (restringe) e la sua assenza da' l'area.
-- (La sezione F ha lasciato un override d'area SCADUTO: l'upsert lo riapre.)
INSERT INTO config.user_override_aree
    (auth_user_id, area_id, livello, valido_dal, valido_al, meta)
SELECT user_id, area_id, 'TUTTO'::config.livello_accesso, script.fn_data_operativa(), NULL,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx
ON CONFLICT ON CONSTRAINT uq_user_override_aree_user_area
DO UPDATE SET livello = EXCLUDED.livello, valido_dal = script.fn_data_operativa(), valido_al = NULL;

-- 31) Nessun override attivo → il livello d'area (non piu' {})
DELETE FROM config.user_override_oggetti
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

SELECT is(
    script.fn_get_user_object_permissions_map(
        (SELECT user_id FROM tmp_ctx)
    ) ->> 'vendite.fattura',
    'TUTTO',
    '31) fn_get_user_object_permissions_map: nessun override → il livello d''area'
);

-- 32) Override attivo → chiave presente
INSERT INTO config.user_override_oggetti
    (auth_user_id, app_label, model_name, livello, meta)
SELECT user_id, 'vendite', 'fattura', 'LETTURA'::config.livello_accesso,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

SELECT is(
    script.fn_get_user_object_permissions_map(
        (SELECT user_id FROM tmp_ctx)
    ) ->> 'vendite.fattura',
    'LETTURA',
    '32) fn_get_user_object_permissions_map: override attivo → il livello dell''override'
);

-- 33) Override scaduto → escluso
UPDATE config.user_override_oggetti
   SET valido_dal = script.fn_data_operativa() - 30,
       valido_al  = script.fn_data_operativa() - 1
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx)
   AND app_label = 'vendite'
   AND model_name = 'fattura';

SELECT is(
    script.fn_get_user_object_permissions_map(
        (SELECT user_id FROM tmp_ctx)
    ) ->> 'vendite.fattura',
    'TUTTO',
    '33) fn_get_user_object_permissions_map: override scaduto → torna l''area'
);

-- 34) Override futuro → escluso
UPDATE config.user_override_oggetti
   SET valido_dal = script.fn_data_operativa() + 1,
       valido_al  = script.fn_data_operativa() + 30
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx)
   AND app_label = 'vendite'
   AND model_name = 'fattura';

SELECT is(
    script.fn_get_user_object_permissions_map(
        (SELECT user_id FROM tmp_ctx)
    ) ->> 'vendite.fattura',
    'TUTTO',
    '34) fn_get_user_object_permissions_map: override futuro → l''area'
);

SELECT * FROM finish();

ROLLBACK;
