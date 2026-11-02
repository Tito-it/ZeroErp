-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la veste operatore si spegne come le altre — attivo = false, il tipo
--       resta (R-DB-1)
-- ChangeSet: 20261002-22 (guard di coerenza), -25 (conversione + CHECK),
--            -26 (fn_sync_auth_user_is_active), -27 (profili applicabili),
--            -28 (fn_veste_di_riferimento), -29 (fn_get_user_profile),
--            -30 (fn_get_operatore_detail)
-- Brief: brief-db-be-fe-area-accessi, R-DB-1 (sezione 7.2)
--
-- Elenco test (plan 12):
--   Il tipo ritirato
--    1) il CHECK chk_identita_digitali_ruolo_non_ritirato c'e' ed e' validato
--    2) una veste DISABILITATO nuova -> E_RUOLO_APPLICATIVO_RITIRATO (il guard
--       parla prima del CHECK)
--    3) ...e cambiare il tipo di una veste in DISABILITATO -> stesso codice
--   L'operatore spento
--    4) spento con attivo = false resta OPERATORE, e la credenziale si spegne
--       (fn_sync_auth_user_is_active legge solo attivo)
--    5) il profilo lo rifiuta: E_UTENTE_DISABILITATO
--    6) ...e la frase nomina lo username (il segnaposto, non una frase intera)
--    7) riacceso: la credenziale si riaccende e il profilo si legge
--    8) ⭐ il guard di coerenza CONTROLLA la veste spenta: spostata su un ruolo
--       che non e' una risorsa umana -> E_SOGGETTI_RUOLI (prima di R-DB-1, su
--       DISABILITATO, usciva in anticipo e non controllava niente)
--   La veste di riferimento (credenziale con piu' vesti OPERATORE)
--    9) con una accesa e una spenta PIU' RECENTE, la veste di riferimento e'
--       l'accesa, e il profilo si legge (un JOIN nudo poteva prendere la spenta)
--   10) con tutte spente e' la piu' recente, e il profilo rifiuta
--   L'invito
--   11) ⚠️ un operatore spento con UNA veste e' invitabile: l'invito riapre una
--       veste spenta (D-3), e da R-DB-1 lo spegnimento dell'amministratore e'
--       una veste spenta come le altre (dichiarato nel brief, sezione 7.2)
--   Il presidio sul testo
--   12) nessuna funzione confronta piu' con il letterale 'DISABILITATO', tranne
--       il guard che lo rifiuta
--
-- Scopo:
--  - il nuovo modello «spenta si legge solo da attivo» e' quello che le
--    funzioni applicano;
--  - le due regressioni che R-DB-1 poteva aprire sono chiuse (il guard che non
--    controllava, il profilo che prendeva la veste sbagliata).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- Fixture
-- ============================================================
-- Il codice dell'errore viaggia nel canale CONSTRAINT_NAME dell'eccezione
-- P0001 (fn_log_and_raise_error): P0001 da solo non dice QUALE.
CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

CREATE OR REPLACE FUNCTION pg_temp.messaggio_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_m text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_m = MESSAGE_TEXT;
    RETURN v_m;
END $$;

-- L'operatore si COSTRUISCE dal percorso di produzione (crea + attivazione):
-- persona fisica, risorsa umana, credenziale, veste OPERATORE accesa.
CREATE TEMP TABLE _op AS
SELECT o.auth_user_id, o.identita_id, o.soggetto_ruolo_id, o.soggetto_id
  FROM dbops.fn_pgtap_crea_operatore_umano('veste spenta', false) o;

ALTER TABLE _op ADD COLUMN username text;
UPDATE _op SET username = au.username FROM django.auth_user au WHERE au.id = _op.auth_user_id;

-- ============================================================
-- 1-3. Il tipo ritirato
-- ============================================================
SELECT is(
    (SELECT c.convalidated
       FROM pg_catalog.pg_constraint c
      WHERE c.conrelid = 'anagrafiche.identita_digitali'::regclass
        AND c.conname  = 'chk_identita_digitali_ruolo_non_ritirato'),
    true,
    '1) CHECK chk_identita_digitali_ruolo_non_ritirato presente e validato');

SELECT is(
    pg_temp.codice_errore(format(
        $$INSERT INTO anagrafiche.identita_digitali
              (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
          VALUES (%s, %s, 'DISABILITATO'::config.ruolo_applicativo, false)$$,
        (SELECT soggetto_ruolo_id FROM _op), (SELECT auth_user_id FROM _op))),
    'E_RUOLO_APPLICATIVO_RITIRATO',
    '2) una veste DISABILITATO nuova: E_RUOLO_APPLICATIVO_RITIRATO, prima del CHECK');

SELECT is(
    pg_temp.codice_errore(format(
        $$UPDATE anagrafiche.identita_digitali
             SET ruolo_applicativo = 'DISABILITATO'::config.ruolo_applicativo,
                 attivo = false
           WHERE id = %s$$,
        (SELECT identita_id FROM _op))),
    'E_RUOLO_APPLICATIVO_RITIRATO',
    '3) spegnere cambiando il tipo in DISABILITATO: E_RUOLO_APPLICATIVO_RITIRATO');

-- ============================================================
-- 4-7. L'operatore spento
-- ============================================================
UPDATE anagrafiche.identita_digitali SET attivo = false
 WHERE id = (SELECT identita_id FROM _op);

SELECT is(
    (SELECT idg.ruolo_applicativo::text || '|' || idg.attivo::text || '|' || au.is_active::text
       FROM anagrafiche.identita_digitali idg
       JOIN django.auth_user au ON au.id = idg.auth_user_id
      WHERE idg.id = (SELECT identita_id FROM _op)),
    'OPERATORE|false|false',
    '4) spento con attivo = false resta OPERATORE, e la credenziale si spegne');

SELECT is(
    pg_temp.codice_errore(format('SELECT script.fn_get_user_profile(%s)',
                                 (SELECT auth_user_id FROM _op))),
    'E_UTENTE_DISABILITATO',
    '5) il profilo di un operatore spento: E_UTENTE_DISABILITATO');

SELECT ok(
    pg_temp.messaggio_errore(format('SELECT script.fn_get_user_profile(%s)',
                                    (SELECT auth_user_id FROM _op)))
        LIKE '%' || (SELECT username FROM _op) || '%',
    '6) ...e la frase nomina lo username');

UPDATE anagrafiche.identita_digitali SET attivo = true
 WHERE id = (SELECT identita_id FROM _op);

SELECT is(
    (SELECT au.is_active::text || '|'
            || (script.fn_get_user_profile(au.id) ->> 'ruolo_applicativo')
       FROM django.auth_user au
      WHERE au.id = (SELECT auth_user_id FROM _op)),
    'true|OPERATORE',
    '7) riacceso: la credenziale si riaccende e il profilo si legge');

-- ============================================================
-- 8. Il guard di coerenza controlla la veste spenta
-- ============================================================
-- Un ruolo cliente (CL) dello stesso soggetto: esiste, ma non e' una risorsa
-- umana. Su una veste OPERATORE persona il guard pretende RIS_UMANA.
CREATE TEMP TABLE _sr_cl AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo((SELECT soggetto_id FROM _op), 'CL') AS sr_id;
SET CONSTRAINTS ALL IMMEDIATE;

UPDATE anagrafiche.identita_digitali SET attivo = false
 WHERE id = (SELECT identita_id FROM _op);

SELECT is(
    pg_temp.codice_errore(format(
        $$UPDATE anagrafiche.identita_digitali
             SET soggetto_ruolo_id = %s
           WHERE id = %s$$,
        (SELECT sr_id FROM _sr_cl), (SELECT identita_id FROM _op))),
    'E_SOGGETTI_RUOLI',
    '8) la veste OPERATORE spenta e'' controllata: su un ruolo che non e'' RIS_UMANA, E_SOGGETTI_RUOLI');

-- ============================================================
-- 9-10. La veste di riferimento
-- ============================================================
-- La veste A torna accesa; B e' una seconda veste OPERATORE della stessa
-- credenziale, spenta e piu' recente (id maggiore: nella stessa transazione
-- data_insert e' lo stesso now(), e lo spareggio e' l'id).
UPDATE anagrafiche.identita_digitali SET attivo = true
 WHERE id = (SELECT identita_id FROM _op);

CREATE TEMP TABLE _b AS
WITH ins AS (
    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    SELECT soggetto_ruolo_id, auth_user_id, 'OPERATORE'::config.ruolo_applicativo, false
      FROM _op
    RETURNING id
)
SELECT id FROM ins;

SELECT is(
    (SELECT (script.fn_veste_di_riferimento(o.auth_user_id, 'OPERATORE'::config.ruolo_applicativo)
             = o.identita_id)::text
            || '|' || (script.fn_get_user_profile(o.auth_user_id) ->> 'ruolo_applicativo')
       FROM _op o),
    'true|OPERATORE',
    '9) accesa + spenta piu'' recente: la veste di riferimento e'' l''accesa, e il profilo si legge');

UPDATE anagrafiche.identita_digitali SET attivo = false
 WHERE id = (SELECT identita_id FROM _op);

SELECT is(
    (SELECT (script.fn_veste_di_riferimento(o.auth_user_id, 'OPERATORE'::config.ruolo_applicativo)
             = (SELECT id FROM _b))::text
            || '|' || pg_temp.codice_errore(format('SELECT script.fn_get_user_profile(%s)', o.auth_user_id))
       FROM _op o),
    'true|E_UTENTE_DISABILITATO',
    '10) tutte spente: la veste di riferimento e'' la piu'' recente, e il profilo rifiuta');

-- ============================================================
-- 11. L'invito di un operatore spento con una veste sola
-- ============================================================
-- Si toglie la seconda veste per avere UNA veste spenta: con due l'invito
-- non sa quale riaccendere (PIU_VESTI_SPENTE, rev 20260925-53).
DELETE FROM anagrafiche.identita_digitali WHERE id = (SELECT id FROM _b);

SELECT is(
    (SELECT (script.fn_check_operatore_invitabile(o.auth_user_id) ->> 'invitabile')
       FROM _op o),
    'true',
    '11) operatore spento con una veste: invitabile (l''invito riapre una veste spenta)');

-- ============================================================
-- 12. Il presidio sul testo
-- ============================================================
-- ⚠️ Il letterale CITATO ('DISABILITATO', con gli apici): «TOTP_DISABILITATO»
--   ed «E_UTENTE_DISABILITATO» sono altre parole, e i commenti che spiegano la
--   storia senza apici non sono confronti. Le funzioni BEGIN ATOMIC hanno
--   prosrc vuoto e il corpo in prosqlbody: si leggono tutti e due.
SELECT is(
    (SELECT COALESCE(string_agg(n.nspname || '.' || p.proname, ', ' ORDER BY 1), '')
       FROM pg_catalog.pg_proc p
       JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
        AND n.nspname NOT LIKE 'pg_temp%'
        AND (p.prosrc LIKE '%''DISABILITATO''%'
             OR COALESCE(pg_get_function_sqlbody(p.oid), '') LIKE '%''DISABILITATO''%')
        AND NOT (n.nspname = 'anagrafiche'
                 AND p.proname = 'trgfn_identita_digitali_guard_coerenza')),
    '',
    '12) nessuna funzione confronta piu'' con ''DISABILITATO'', tranne il guard che lo rifiuta');

SELECT * FROM finish();
ROLLBACK;
