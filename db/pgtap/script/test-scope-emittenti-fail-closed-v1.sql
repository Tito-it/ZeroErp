-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Passo 2 (P-2a) del cantiere «perimetro emittente»: fail-closed nella catena
-- canonica dello scope. Un operatore SENZA riga in
-- config.user_emittenti_fiscali non vede piu' TUTTI gli emittenti.
-- Brief: brief-db-perimetro-emittente-liste-e-gerarchia-ba.md §2.5
--
-- Elenco test (plan 8):
--   0) PRECONDIZIONI: un operatore con riga, diverso da quello di contesto
--   1) operatore CON riga            -> array di 1 (invariato)
--   2) * operatore SENZA riga        -> '{}' e NON NULL     ⬅ LA correzione
--   3) * stesso, fn_check_user_emittente_scope -> false
--   4) super admin                   -> NULL (invariato: non e' toccato)
--   5) super admin + emittente attivo-> array di 1 (l'intersezione regge)
--   6) * eredita': fn_get_emittenti_scope_sr_ids -> '{}'
--   7) * eredita': fn_scope_ef_whitelist_via_efba -> false
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
-- ⚠️ FIXTURE. DL-A e' stato sanato il 2026-08-18 (era 2, ora e' 0), quindi un
--   operatore senza riga NON ESISTE PIU' e va costruito: si toglie lo scope a
--   un operatore vero con la funzione di dominio
--   script.fn_change_user_emittenti_scope(x, '{}'), e il file chiude in
--   ROLLBACK. Si evita di proposito l'operatore del CONTESTO pgTAP: e' quello
--   da cui dipendono le policy RLS durante la corsa.
--
-- ⚠️ Le funzioni dello scope prendono l'auth_user_id come PARAMETRO, quindi non
--   serve cambiare contesto per interrogarle su un altro utente. Cambiarlo
--   sarebbe anzi peggio: sposterebbe anche la RLS sotto i piedi della fixture.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- Fixture
-- ============================================================
-- Un operatore con riga, NON super admin e DIVERSO da quello di contesto.
-- ⚠️ ORDER BY obbligatorio: la scelta deve essere stabile fra le corse.
CREATE TEMP TABLE _t_op ON COMMIT DROP AS
SELECT uef.auth_user_id,
       uef.emittente_fiscale_id
  FROM config.user_emittenti_fiscali uef
 WHERE script.fn_has_identita_attiva(
           uef.auth_user_id, 'OPERATORE'::config.ruolo_applicativo)
   AND NOT script.fn_is_super_admin(uef.auth_user_id)
   AND uef.auth_user_id <> NULLIF(current_setting('app.current_user_id', true), '')::integer
 ORDER BY uef.auth_user_id
 LIMIT 1;

CREATE TEMP TABLE _t_sa ON COMMIT DROP AS
SELECT (SELECT idg.auth_user_id
          FROM anagrafiche.identita_digitali idg
         WHERE idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
           AND idg.attivo
           AND script.fn_is_super_admin(idg.auth_user_id)
         ORDER BY idg.auth_user_id
         LIMIT 1) AS auth_user_id;

-- Un billing account qualunque, per l'adapter del test 7.
CREATE TEMP TABLE _t_ba ON COMMIT DROP AS
SELECT ba.id AS ba_id FROM anagrafiche.billing_account ba ORDER BY ba.id LIMIT 1;

SELECT ok(
    (SELECT auth_user_id FROM _t_op) IS NOT NULL
    AND (SELECT auth_user_id FROM _t_sa) IS NOT NULL
    AND (SELECT ba_id FROM _t_ba) IS NOT NULL,
    '0. PRECONDIZIONI: un operatore configurato (non di contesto), un super admin, un BA'
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
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
