-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce TRE aziende e un billing account
--   legato a un emittente che NON e' quello di default: come `zeroerp_app`
--   l'INSERT del BA muore al RETURNING (la policy di lettura risolve il BA non
--   ancora mappato sull'emittente di default, che e' un'altra azienda — il
--   legame lo scrive un trigger AFTER). Il soggetto del test sono le funzioni
--   dello scope, che prendono l'utente come parametro: il ruolo di connessione
--   non cambia cio' che misurano.
-- pgTAP test per Zero ERP
--
-- Passo 2 (P-2a) del cantiere «perimetro emittente»: fail-closed nella catena
-- canonica dello scope. Un operatore SENZA riga in
-- config.user_emittenti_fiscali non vede piu' TUTTI gli emittenti.
-- Brief: brief-db-perimetro-emittente-liste-e-gerarchia-ba.md §2.5
--
-- Elenco test (plan 11):
--   0) PRECONDIZIONI: le tre aziende e il BA sono stati costruiti
--   1) operatore CON riga            -> array di 1 (invariato)
--   2) * operatore SENZA riga        -> '{}' e NON NULL     ⬅ LA correzione
--   3) * stesso, fn_check_user_emittente_scope -> false
--   4) super admin                   -> NULL (invariato: non e' toccato)
--   5) super admin + emittente attivo-> array di 1 (l'intersezione regge)
--   6) * eredita': fn_get_emittenti_scope_sr_ids -> '{}'
--   7) * eredita': fn_scope_ef_whitelist_via_efba -> false
--  Utente NULL (rev 2026-10-04, Q-1 di brief-db-esclusioni-implicite):
--   8) * fn_check_user_emittente_scope(NULL, …) -> false   (era true)
--   9) * fn_scope_ef_whitelist_via_efba(NULL, …) -> false  (era true)
--  10) * fn_get_emittenti_scope_sr_ids(NULL) -> '{}' (la canonica, non NULL = tutto)
--
-- Rev 2026-10-10 (brief-db-codici-non-trovato-email-e-permessi R-5): i test 10
--   e 11 provavano fn_get_emittenti_scope_sr_effettivo, ritirata con il
--   parametro p_emittente_ids della ricerca universale (20261010-14). Ne era
--   un involucro: la proprieta' che custodivano, «utente NULL = nessun
--   accesso», resta qui sulla canonica fn_get_emittenti_scope_sr_ids, che
--   nessun test asseriva direttamente (le viste fail-closed la davano per
--   buona nei commenti).
--
-- Scopo:
--  - 2 e 3 sono la correzione. Prima erano NULL e true, cioe' «vede tutto»:
--    lo stesso utente che sul lato SCRITTURA non poteva nemmeno creare un
--    billing account (fn_check_user_can_create_ba) sul lato LETTURA li vedeva
--    tutti. Le due letture non potevano essere entrambe intenzionali;
--  - 6 e 7 verificano l'EREDITA' invece di assumerla: il brief sostiene che gli
--    adapter si sistemano «per costruzione» perche' trattano gia' cardinality=0
--    come nessun accesso. Sostenerlo non basta, si misura.
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (2026-09-12). Fino a quel giorno il
--   file pescava un operatore, un super admin e un BA fra quelli ESISTENTI: su
--   un database ricostruito dai changelog non ce n'e' nessuno, il file moriva
--   nella fixture e la proprieta' fail-closed — la piu' importante del
--   perimetro — restava collaudata solo su dbdev. Ora:
--     - tre aziende con `dbops.fn_pgtap_crea_emittente_operatore()`: quella del
--       CONTESTO, quella dell'operatore a cui si toglie lo scope (diverso da
--       quello di contesto: e' da lui che dipendono le policy durante la corsa)
--       e quella del super admin, che lo diventa con un binding al profilo
--       SUPER_ADMIN;
--     - un BA con `dbops.fn_pgtap_crea_cliente_ba()` legato all'emittente
--       dell'operatore da spogliare, PRIMA di aprire il contesto: con un
--       operatore in sessione il trigger z90 del BA scriverebbe un secondo
--       legame e i due si scontrerebbero su uq_emittenti_fiscali_ba. Cosi' il
--       test 7 e' onesto: prima dello spoglio l'adapter dice SI' (test 0), dopo
--       dice NO — e il NO viene dallo scope, non da un BA che non c'entra.
--   Un operatore senza riga NON ESISTE (DL-A sanato il 2026-08-18): si toglie
--   lo scope con la funzione di dominio script.fn_change_user_emittenti_scope,
--   che e' la sede unica del modello 1-a-1, e il file chiude in ROLLBACK.
--
-- ⚠️ Le funzioni dello scope prendono l'auth_user_id come PARAMETRO, quindi non
--   serve cambiare contesto per interrogarle su un altro utente. Cambiarlo
--   sarebbe anzi peggio: sposterebbe anche la RLS sotto i piedi della fixture.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- Fixture: si costruisce il mondo, POI si apre il contesto
-- ============================================================
CREATE TEMP TABLE _mondi ON COMMIT DROP AS
SELECT 'CTX' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'OP'  AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'SA'  AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Il super admin: un'identita' OPERATORE attiva con binding SUPER_ADMIN attivo
-- (e' la definizione di script.fn_is_super_admin).
DO $lega$ BEGIN PERFORM config.fn_lega_profilo_identita((SELECT pa.id FROM config.profili_accesso pa WHERE pa.codice = 'SUPER_ADMIN'), (SELECT m.identita_id FROM _mondi m WHERE m.lato = 'SA')); END $lega$;

-- L'operatore a cui si togliera' lo scope, e il super admin.
CREATE TEMP TABLE _t_op ON COMMIT DROP AS
SELECT m.auth_user_id, m.emittente_fiscale_id, m.soggetto_ruolo_id
  FROM _mondi m WHERE m.lato = 'OP';

CREATE TEMP TABLE _t_sa ON COMMIT DROP AS
SELECT m.auth_user_id FROM _mondi m WHERE m.lato = 'SA';

-- Un billing account dell'azienda dell'operatore da spogliare, per l'adapter
-- del test 7. Prima del contesto (vedi intestazione).
CREATE TEMP TABLE _t_ba ON COMMIT DROP AS
SELECT c.billing_account_id AS ba_id
  FROM dbops.fn_pgtap_crea_cliente_ba(
           'scope fail-closed', NULL, (SELECT soggetto_ruolo_id FROM _t_op)) c;

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT m.auth_user_id FROM _mondi m WHERE m.lato = 'CTX'));
END $ctx$;

SELECT ok(
    (SELECT count(*) FROM _mondi) = 3
    AND script.fn_is_super_admin((SELECT auth_user_id FROM _t_sa))
    AND NOT script.fn_is_super_admin((SELECT auth_user_id FROM _t_op))
    AND script.fn_scope_ef_whitelist_via_efba(
            (SELECT auth_user_id FROM _t_op), (SELECT ba_id FROM _t_ba)),
    '0. PRECONDIZIONI: tre aziende costruite, il super admin lo e'' davvero, l''operatore no, e VEDE il suo BA'
);

-- ============================================================
-- Asserzioni
-- ============================================================

-- 1) Operatore CON riga: invariato, un solo emittente.
SELECT is(
    cardinality(script.fn_get_emittenti_scope_pk_ids((SELECT auth_user_id FROM _t_op))),
    1,
    '1. operatore CON riga: scope di cardinalita'' 1 (invariato)'
);

-- Togli lo scope: da qui l'operatore e' «configurato a meta'».
-- Si usa la funzione di dominio, non un DELETE: e' la sede unica del modello 1-a-1.
SELECT script.fn_change_user_emittenti_scope(
           (SELECT auth_user_id FROM _t_op), '{}'::bigint[]);

-- 2) * LA correzione: senza riga NON significa piu' «nessuna restrizione».
SELECT is(
    script.fn_get_emittenti_scope_pk_ids((SELECT auth_user_id FROM _t_op)),
    '{}'::bigint[],
    '2. * operatore SENZA riga -> ''{}'' e non piu'' NULL (era: vede tutti gli emittenti)'
);

-- 3) * La gemella puntuale.
SELECT ok(
    NOT script.fn_check_user_emittente_scope(
            (SELECT auth_user_id FROM _t_op),
            (SELECT emittente_fiscale_id FROM _t_op)),
    '3. * operatore SENZA riga: fn_check_user_emittente_scope -> false (era true)'
);

-- 4) Il super admin NON e' toccato: resta l'unico multi-emittente legittimo.
SELECT is(
    script.fn_get_emittenti_scope_pk_ids((SELECT auth_user_id FROM _t_sa)),
    NULL,
    '4. super admin -> NULL (universo): non toccato da P-2a'
);

-- 5) ...ma l'emittente attivo lo restringe lo stesso: «solo restringente».
SELECT set_config('app.current_emittente_id',
                  (SELECT emittente_fiscale_id FROM _t_op)::text, false);

SELECT is(
    script.fn_get_emittenti_scope_pk_ids((SELECT auth_user_id FROM _t_sa)),
    ARRAY[(SELECT emittente_fiscale_id FROM _t_op)]::bigint[],
    '5. super admin CON emittente attivo -> quel solo emittente (universo ∩ {X})'
);

SELECT set_config('app.current_emittente_id', '', false);

-- 6) * L'eredita' si misura, non si assume: il wrapper su soggetto_ruolo_id.
SELECT is(
    script.fn_get_emittenti_scope_sr_ids((SELECT auth_user_id FROM _t_op)),
    '{}'::bigint[],
    '6. * eredita'': fn_get_emittenti_scope_sr_ids -> ''{}'' senza modifiche proprie'
);

-- 7) * ...e l'adapter usato dalle policy RLS.
SELECT ok(
    NOT script.fn_scope_ef_whitelist_via_efba(
            (SELECT auth_user_id FROM _t_op),
            (SELECT ba_id FROM _t_ba)),
    '7. * eredita'': fn_scope_ef_whitelist_via_efba -> false (le policy chiudono)'
);

-- ============================================================
-- 8..10) * Utente NULL = nessun accesso (rev 2026-10-04, Q-1)
-- ============================================================
-- Fino al 2026-10-04 la famiglia diceva «utente NULL = job batch = vede
-- tutto». Le policy restavano chiuse solo per la veste OPERATORE: con la veste
-- e l'utente vuoto una sessione vedeva tutte le aziende. Il guard di scrittura
-- aveva tolto lo stesso ramo il 2026-09-04. La prova sulla policy vera, come
-- applicazione, e' in script/test-guard-emittente-senza-utente (test 9-10):
-- questo file gira da owner e misura le funzioni.
-- ⚠️ L'emittente e il BA sono quelli che l'operatore di contesto VEDE: un false
--   su un emittente altrui non direbbe niente.
SELECT ok(
    NOT script.fn_check_user_emittente_scope(
            NULL,
            (SELECT m.emittente_fiscale_id FROM _mondi m WHERE m.lato = 'CTX')),
    '8. * utente NULL: fn_check_user_emittente_scope -> false (era true, «job batch»)'
);

SELECT ok(
    NOT script.fn_scope_ef_whitelist_via_efba(NULL, (SELECT ba_id FROM _t_ba)),
    '9. * utente NULL: fn_scope_ef_whitelist_via_efba -> false (era true)'
);

SELECT is(
    script.fn_get_emittenti_scope_sr_ids(NULL),
    '{}'::bigint[],
    '10. * utente NULL: fn_get_emittenti_scope_sr_ids -> ''{}'' (nessun accesso, non NULL = tutto)'
);

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
