-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: resta sempre almeno un SUPER_ADMIN SENZA SCADENZA; il batch notturno
--       spegne E accende
-- ChangeSet: 20261007-16 (script.fn_identita_super_admin_senza_scadenza),
--            -17 (fn_check_ultimo_super_admin_attivo), -18
--            (fn_check_almeno_un_super_admin_attivo), -19 (guard sulla veste,
--            anche le date), -20 (guard sul rapporto), -21
--            (fn_sync_auth_user_expired nei due versi)
-- Brief: brief-db-veste-utilizzabile §7.5 (decisioni di Tid del 2026-10-07)
--
-- Elenco test (plan 16):
--   Il building block
--    1) esiste script.fn_identita_super_admin_senza_scadenza(bigint) -> boolean
--    2) un SUPER_ADMIN acceso, senza date di fine: senza scadenza
--   La garanzia passa da A a B
--    3) A riceve una data di fine sulla veste: permesso (B non scade)
--    4) ...e A non e' piu' «senza scadenza»
--    5) fn_check_ultimo_super_admin_attivo: B si', A no (A scade gia')
--   B e' l'ultimo che non scade: ogni scrittura che riduce si ferma
--    6) data di fine sulla veste di B: E_PROFILO_ULTIMO_SUPER_ADMIN
--    7) inizio della veste di B domani: E_PROFILO_ULTIMO_SUPER_ADMIN
--    8) data di fine sul RAPPORTO di B (guard -20): E_PROFILO_ULTIMO_SUPER_ADMIN
--    9) inizio del rapporto di B domani: E_PROFILO_ULTIMO_SUPER_ADMIN
--   10) veste di B spenta: E_PROFILO_ULTIMO_SUPER_ADMIN (lo spegnimento di
--       prima, ora sulla stessa regola)
--   Le scritture che migliorano passano sempre
--   11) a A si toglie la data di fine: permesso, e A torna senza scadenza
--   12) ora la data di fine a B passa
--   13) a un operatore NON amministratore la data di fine si da' sempre
--   Il batch notturno nei due versi
--   14) una credenziale con la veste valida oggi ma ancora spenta (il giorno
--       della data di inizio, nessuno ha scritto) viene ACCESA
--   15) ...e una con la veste scaduta e ancora accesa viene SPENTA
--   16) il ritorno conta tutte e due
--
-- ⚠️ Il caso «il sistema e' gia' scoperto e una scrittura migliora» non si
--   costruisce da app: per arrivarci servirebbe una scrittura che il guard
--   ferma. Le scritture che migliorano non passano dal controllo (short-circuit
--   del guard), e il caso 11 lo prova su un sistema coperto.
-- ⚠️ Gli altri SUPER_ADMIN gia' presenti (su dbdev ce ne sono) ricevono in testa
--   una data di fine lontana: cosi' «senza scadenza» sono solo A e B, costruiti
--   qui, su qualunque database. Tutto si annulla col ROLLBACK.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ============================================================
-- Fixture
-- ============================================================

-- Due amministratori dal percorso di produzione (madre: persona, rapporto,
-- credenziale, veste accesa, binding SUPER_ADMIN).
CREATE TEMP TABLE _a AS
SELECT o.* FROM dbops.fn_pgtap_crea_operatore_umano('SA senza scadenza A', true) o;
CREATE TEMP TABLE _b AS
SELECT o.* FROM dbops.fn_pgtap_crea_operatore_umano('SA senza scadenza B', true) o;
-- Un operatore qualunque, non amministratore.
CREATE TEMP TABLE _c AS
SELECT o.* FROM dbops.fn_pgtap_crea_operatore_umano('Operatore non SA', false) o;

-- Gli altri SUPER_ADMIN del database: una data di fine lontana sulla veste.
-- Permesso: A e B non scadono.
UPDATE anagrafiche.identita_digitali idg
   SET valido_al = script.fn_data_operativa() + 3650
 WHERE idg.valido_al IS NULL
   AND idg.id NOT IN ((SELECT identita_id FROM _a), (SELECT identita_id FROM _b))
   AND EXISTS (SELECT 1
                 FROM config.profili_accesso_bindings pab
                 JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
                WHERE pab.identita_digitale_id = idg.id
                  AND pab.attivo AND pa.attivo
                  AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso);

-- Le finestre partono indietro di dieci giorni, cosi' «domani» e le date di
-- fine sono ammesse dai CHECK (valido_al >= valido_dal).
UPDATE anagrafiche.identita_digitali SET valido_dal = script.fn_data_operativa() - 10
 WHERE id IN ((SELECT identita_id FROM _a), (SELECT identita_id FROM _b), (SELECT identita_id FROM _c));
UPDATE anagrafiche.risorse_umane SET valido_dal = script.fn_data_operativa() - 10
 WHERE id IN ((SELECT risorsa_umana_id FROM _a), (SELECT risorsa_umana_id FROM _b), (SELECT risorsa_umana_id FROM _c));

-- ============================================================
-- 1-2. Il building block
-- ============================================================
SELECT function_returns('script', 'fn_identita_super_admin_senza_scadenza', ARRAY['bigint'], 'boolean',
    '1) script.fn_identita_super_admin_senza_scadenza(bigint) -> boolean');

SELECT is(script.fn_identita_super_admin_senza_scadenza((SELECT identita_id FROM _a)), true,
    '2) SUPER_ADMIN acceso e senza date di fine: senza scadenza');

-- ============================================================
-- 3-5. La garanzia passa da A a B
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE anagrafiche.identita_digitali SET valido_al = script.fn_data_operativa() + 30 WHERE id = %s',
        (SELECT identita_id FROM _a))),
    NULL,
    '3) data di fine sulla veste di A: permesso, B non scade');

SELECT is(script.fn_identita_super_admin_senza_scadenza((SELECT identita_id FROM _a)), false,
    '4) ...e A non e'' piu'' senza scadenza');

SELECT is(
    script.fn_check_ultimo_super_admin_attivo((SELECT auth_user_id FROM _b))::text || '|' ||
    script.fn_check_ultimo_super_admin_attivo((SELECT auth_user_id FROM _a))::text,
    'true|false',
    '5) ultimo SUPER_ADMIN senza scadenza: B si'', A no');

-- ============================================================
-- 6-10. B e' l'ultimo: le scritture che riducono si fermano
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE anagrafiche.identita_digitali SET valido_al = script.fn_data_operativa() + 30 WHERE id = %s',
        (SELECT identita_id FROM _b))),
    'E_PROFILO_ULTIMO_SUPER_ADMIN',
    '6) data di fine sulla veste dell''ultimo: rifiutata');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE anagrafiche.identita_digitali SET valido_dal = script.fn_data_operativa() + 1 WHERE id = %s',
        (SELECT identita_id FROM _b))),
    'E_PROFILO_ULTIMO_SUPER_ADMIN',
    '7) inizio della veste dell''ultimo spostato a domani: rifiutato');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE anagrafiche.risorse_umane SET valido_al = script.fn_data_operativa() + 30 WHERE id = %s',
        (SELECT risorsa_umana_id FROM _b))),
    'E_PROFILO_ULTIMO_SUPER_ADMIN',
    '8) data di fine sul RAPPORTO dell''ultimo: rifiutata (guard -20)');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE anagrafiche.risorse_umane SET valido_dal = script.fn_data_operativa() + 1 WHERE id = %s',
        (SELECT risorsa_umana_id FROM _b))),
    'E_PROFILO_ULTIMO_SUPER_ADMIN',
    '9) inizio del rapporto dell''ultimo spostato a domani: rifiutato');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE anagrafiche.identita_digitali SET attivo = false WHERE id = %s',
        (SELECT identita_id FROM _b))),
    'E_PROFILO_ULTIMO_SUPER_ADMIN',
    '10) veste dell''ultimo spenta: rifiutata');

-- ============================================================
-- 11-13. Le scritture che migliorano passano
-- ============================================================
-- ⚠️ Scrittura e lettura in due istruzioni: una funzione STABLE nella stessa
--   istruzione vede la fotografia di PRIMA dell'UPDATE.
CREATE TEMP TABLE _esito11 AS
SELECT COALESCE(dbops.fn_pgtap_codice_errore(format(
           'UPDATE anagrafiche.identita_digitali SET valido_al = NULL WHERE id = %s',
           (SELECT identita_id FROM _a))), 'nessun errore') AS esito;

SELECT is(
    (SELECT esito FROM _esito11)
    || '|' || script.fn_identita_super_admin_senza_scadenza((SELECT identita_id FROM _a))::text,
    'nessun errore|true',
    '11) ad A si toglie la data di fine: permesso, e A torna senza scadenza');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE anagrafiche.identita_digitali SET valido_al = script.fn_data_operativa() + 30 WHERE id = %s',
        (SELECT identita_id FROM _b))),
    NULL,
    '12) ora la data di fine a B passa: A non scade');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE anagrafiche.risorse_umane SET valido_al = script.fn_data_operativa() + 30 WHERE id = %s',
        (SELECT risorsa_umana_id FROM _c))),
    NULL,
    '13) a un operatore non amministratore la data di fine si da'' sempre');

-- ============================================================
-- 14-16. Il batch notturno nei due versi
-- ============================================================
-- 14. Il giorno della data di inizio: la veste di C e' valida oggi, ma la
-- credenziale e' rimasta spenta (ieri la veste non valeva ancora, e oggi
-- nessuno ha scritto). Lo stato si simula spegnendo is_active a mano.
UPDATE django.auth_user SET is_active = false WHERE id = (SELECT auth_user_id FROM _c);

-- 15. E l'opposto: B, scaduto ieri sul rapporto, con la credenziale ancora
-- accesa. La data di fine a B si mette a ieri ora che A copre la garanzia.
UPDATE anagrafiche.risorse_umane SET valido_al = script.fn_data_operativa() - 1
 WHERE id = (SELECT risorsa_umana_id FROM _b);
UPDATE django.auth_user SET is_active = true WHERE id = (SELECT auth_user_id FROM _b);

CREATE TEMP TABLE _batch AS SELECT anagrafiche.fn_sync_auth_user_expired() AS n;

SELECT is((SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _c)),
    true,
    '14) batch: la credenziale con la veste diventata valida oggi viene ACCESA');

SELECT is((SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _b)),
    false,
    '15) batch: la credenziale col rapporto scaduto viene SPENTA');

SELECT cmp_ok((SELECT n FROM _batch), '>=', 2,
    '16) il ritorno conta le credenziali riallineate nei due versi');

SELECT * FROM finish();
ROLLBACK;
