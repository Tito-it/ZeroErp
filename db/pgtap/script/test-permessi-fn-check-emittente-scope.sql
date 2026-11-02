-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: funzioni scope emittente e flag SUPER_ADMIN
--       script.fn_is_super_admin (sostituisce fn_get_ruolo_sistema
--         droppata in Fase 7 cleanup 2026-04-29),
--       script.fn_get_emittenti_scope  [DISMESSA 2026-08-18: il test 9 ora
--         verifica che NON esista piu'],
--       script.fn_check_user_emittente_scope
--
-- Migrazione Fase 7 Chunk A (2026-04-29):
--   Pre-cutover il test scriveva su rau.ruolo_sistema (UPDATE diretti).
--   Post-cutover §13.3 rau e' vista non updatable + ruolo_sistema CASE
--   calcolato. Sostituzioni:
--     UPDATE rau SET ruolo_sistema='OPERATIVO' (forzatura iniziale)
--       -> il setup pesca identita OPERATORE attiva senza binding SA
--          (filtro NOT EXISTS, pattern §4.bis): stato gia' "OPERATIVO".
--     UPDATE rau SET ruolo_sistema='ADMIN' (test 7 promotion temporanea)
--       -> INSERT binding SUPER_ADMIN su identita_digitali esistente.
--          Il filtro vergine garantisce che il nuovo SA non sia l'unico:
--          esistono altri SA preesistenti (es. seed tid), il guard 384
--          anti-lockout non scatta su DELETE successiva.
--     UPDATE rau SET ruolo_sistema='OPERATIVO' (ripristino post-7)
--       -> DELETE del binding SA appena creato.
--
-- Elenco test:
--  1) Riferimento utente OPERATORE non-SA presente
--  2) Riferimento emittenti_fiscali (1) presente
--  3) Emittente fittizio (2) diverso da emittente reale (1)
--  4) fn_is_super_admin: utente OPERATORE non-SA → false
--  5) fn_is_super_admin: utente inesistente → false (fail-closed)
--  6) fn_check_user_emittente_scope: NULL user → false (rev 2026-10-04, Q-1)
--  7) fn_check_user_emittente_scope: ADMIN → true qualunque emittente
--  8) fn_check_user_emittente_scope: OPERATIVO senza whitelist → false (P-2a)
--  9) legacy fn_get_emittenti_scope: DISMESSA (asserzione girata di segno)
-- 10) Aggiunta whitelist per emittente_1
-- 11) fn_check_user_emittente_scope: emittente_1 in whitelist → true
-- 12) fn_check_user_emittente_scope: emittente_2 non in whitelist → false
-- 13) fn_get_emittenti_scope_pk_ids (erede guarded): con whitelist → array contenente emittente_1
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
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (2026-09-12). Fino a quel giorno il
--   file pescava un'identita' OPERATORE e un emittente fra quelli ESISTENTI, e
--   contava su «altri SA preesistenti (seed tid)» perche' il DELETE del binding
--   al test 7 non facesse scattare l'anti-lockout: su un database ricostruito
--   dai changelog non c'e' nessuna delle tre cose. Tre aziende con
--   `dbops.fn_pgtap_crea_emittente_operatore()`, PRIMA di aprire il contesto:
--   CTX (il contesto), OP (l'identita' sotto test) e SA2, che diventa super
--   admin con un binding — cosi' quando il test 7 toglie il proprio binding
--   non e' l'ultimo, e il guard anti-lockout ha ragione a tacere.
CREATE TEMP TABLE _mondi AS
SELECT 'CTX' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'OP'  AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'SA2' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

DO $lega$ BEGIN PERFORM config.fn_lega_profilo_identita(9100, (SELECT identita_id FROM _mondi WHERE lato = 'SA2')); END $lega$;

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'CTX'));
END $ctx$;

SELECT plan(13);

-- ============================================================
-- 0. Setup: l'identita' OPERATORE costruita, senza binding SUPER_ADMIN
-- ============================================================

CREATE TEMP TABLE tmp_refs_scope AS
SELECT m.auth_user_id AS user_id,
       m.identita_id  AS identita_id
  FROM _mondi m WHERE m.lato = 'OP';

-- Pulisce eventuali whitelist pre-esistenti per l'utente di test.
-- Override del guard_delete (trgfn_user_emittenti_fiscali_guard_delete)
-- necessario: l'utente Django associato e' ancora attivo. Reset
-- difensivo subito dopo per non lasciar leakare la GUC nel resto del
-- test.
SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_refs_scope);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

CREATE TEMP TABLE tmp_emittenti AS
SELECT m.emittente_fiscale_id AS emittente_id_1,   -- l'azienda di OP, riassegnata al test 10
       -1::bigint             AS emittente_id_2    -- fittizio: fn_check verifica solo whitelist
  FROM _mondi m WHERE m.lato = 'OP';

-- 1) Setup: utente OPERATORE non-SA trovato
SELECT ok(
    (SELECT user_id FROM tmp_refs_scope) IS NOT NULL,
    '1) Setup: identita OPERATORE attiva non-SA costruita'
);

SELECT ok(
    (SELECT emittente_id_1 FROM tmp_emittenti) IS NOT NULL,
    '2) Riferimento emittenti_fiscali (1) presente'
);

SELECT ok(
    (SELECT emittente_id_2 FROM tmp_emittenti) IS NOT NULL
    AND (SELECT emittente_id_2 FROM tmp_emittenti) <>
        (SELECT emittente_id_1 FROM tmp_emittenti),
    '3) Emittente fittizio (2) diverso da emittente reale (1)'
);

-- ============================================================
-- 1. fn_is_super_admin (sostituisce fn_get_ruolo_sistema droppata
--    in Fase 7 cleanup 2026-04-29)
-- ============================================================

-- 4) Utente OPERATORE non-SA → fn_is_super_admin = false
--    (filtro vergine al setup: nessun binding SA per definizione).
SELECT is(
    script.fn_is_super_admin(
        (SELECT user_id FROM tmp_refs_scope)
    ),
    false,
    '4) fn_is_super_admin: utente OPERATORE non-SA → false'
);

-- 5) Utente inesistente → fn_is_super_admin = false (fail-closed)
SELECT is(
    script.fn_is_super_admin(99999999),
    false,
    '5) fn_is_super_admin: utente inesistente → false (fail-closed)'
);

-- ============================================================
-- 2. fn_check_user_emittente_scope — casi base
-- ============================================================

-- 6) NULL user_id → false. Rev 2026-10-04 (Q-1, brief-db-esclusioni-implicite):
--    era true («batch job»), e con la veste OPERATORE e l'utente vuoto una
--    sessione vedeva tutte le aziende.
SELECT is(
    script.fn_check_user_emittente_scope(
        NULL,
        (SELECT emittente_id_1 FROM tmp_emittenti)
    ),
    false,
    '6) fn_check_user_emittente_scope: NULL user → false (era true, «batch job»)'
);

-- 7) ADMIN → true per qualunque emittente.
-- Pre-Fase 7: UPDATE rau SET ruolo_sistema='ADMIN'.
-- Post-Fase 7: INSERT binding SUPER_ADMIN su identita esistente.
DO $lega$
BEGIN
    PERFORM config.fn_lega_profilo_identita(9100, ctx.identita_id) FROM tmp_refs_scope ctx;
END
$lega$;

SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_refs_scope),
        (SELECT emittente_id_1 FROM tmp_emittenti)
    ),
    true,
    '7) fn_check_user_emittente_scope: ADMIN (binding SA) → true qualunque emittente'
);

-- Ripristina stato non-SA: DELETE del binding appena creato.
-- Il guard 384 anti-lockout non scatta perche' esiste l'altro SA costruito
-- dalla fixture (SA2).
DELETE FROM config.profili_accesso_bindings
 WHERE identita_digitale_id = (SELECT identita_id FROM tmp_refs_scope)
   AND profilo_accesso_id = 9100;

-- 8) OPERATIVO senza whitelist → FALSE (fail-closed, P-2a 2026-08-18)
--    ⚠️ Diceva `true`, «nessuna restrizione»: era il vecchio contratto, non
--    una fixture rimasta indietro. La riga mancante e' una configurazione
--    incompleta, non un permesso — e lo stesso utente in SCRITTURA era gia'
--    rifiutato. Brief perimetro-emittente §2.5.
SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_refs_scope),
        (SELECT emittente_id_1 FROM tmp_emittenti)
    ),
    false,
    '8) fn_check_user_emittente_scope: OPERATIVO senza whitelist → false (P-2a)'
);

-- ============================================================
-- 3. fn_get_emittenti_scope — DISMESSA
-- ============================================================

-- 9) ⛔ L'asserzione non e' stata CANCELLATA: e' stata GIRATA DI SEGNO, ed e'
--    il modo giusto di ritirare una funzione.
--    Diceva «senza whitelist → NULL», cioe' «un utente senza abilitazioni
--    vede tutti gli emittenti»: era il fail-open che P-2a ha chiuso ovunque il
--    2026-08-18. La legacy non e' mai stata allineata perche' non la chiamava
--    piu' nessuno — e per questo e' stata dismessa (changeSet 20260818-66).
--    Da qui in avanti il test dice che la funzione NON C'E' PIU': chi la
--    ricreasse troverebbe questa riga rossa. Cancellarlo avrebbe tolto il
--    presidio insieme al difetto.
SELECT hasnt_function(
    'script', 'fn_get_emittenti_scope', ARRAY['integer'],
    '9) legacy fn_get_emittenti_scope: DISMESSA (era il fail-open «senza whitelist → tutti»)'
);

-- ============================================================
-- 4. Aggiunta whitelist e verifica scope
-- ============================================================

-- 10) Aggiunta whitelist per emittente_1
SELECT lives_ok(
    format(
        $$INSERT INTO config.user_emittenti_fiscali
              (auth_user_id, emittente_fiscale_id, meta)
          VALUES (%s, %s,
                  '{"test_scope":"pgtap_fn_check_emittente_scope"}'::jsonb)$$,
        (SELECT user_id FROM tmp_refs_scope),
        (SELECT emittente_id_1 FROM tmp_emittenti)
    ),
    '10) Whitelist: aggiunta emittente_1 per utente test'
);

-- 11) Emittente_1 in whitelist → true
SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_refs_scope),
        (SELECT emittente_id_1 FROM tmp_emittenti)
    ),
    true,
    '11) fn_check_user_emittente_scope: emittente in whitelist → true'
);

-- 12) Emittente_2 NON in whitelist → false
SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_refs_scope),
        (SELECT emittente_id_2 FROM tmp_emittenti)
    ),
    false,
    '12) fn_check_user_emittente_scope: emittente NON in whitelist → false'
);

-- 13) La COPERTURA non si perde con la funzione: la stessa domanda — «la
--     whitelist finisce nello scope?» — si fa all'erede guarded
--     fn_get_emittenti_scope_pk_ids, che risponde in PK emittente come la
--     legacy. Il test 9 presidia che la vecchia non torni; questo continua a
--     verificare il comportamento.
SELECT ok(
    (SELECT emittente_id_1 FROM tmp_emittenti) = ANY(
        script.fn_get_emittenti_scope_pk_ids(
            (SELECT user_id FROM tmp_refs_scope)
        )
    ),
    '13) fn_get_emittenti_scope_pk_ids (erede guarded): con whitelist → array contiene emittente_1'
);

SELECT * FROM finish();

ROLLBACK;
