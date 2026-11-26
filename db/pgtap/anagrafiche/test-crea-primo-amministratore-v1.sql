-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce «nessun legame SUPER_ADMIN», uno stato che i
--   guard dell'ultimo SUPER_ADMIN vietano a chiunque: li spegne nella transazione con
--   ALTER TABLE … DISABLE TRIGGER, che solo il proprietario puo' fare. Il verbo e'
--   SECURITY DEFINER, quindi il suo corpo gira da proprietario chiunque lo chiami: dal
--   runner owner si prova la stessa cosa. Cio' che dell'app conta, l'EXECUTE, lo
--   asserisce il test 2 (brief-db-porte-aperte-dalla-sola-guc §4.9, 2026-11-25).
-- pgTAP test per Zero ERP
-- Test: anagrafiche.fn_crea_primo_amministratore — il primo SUPER_ADMIN di
--       un'installazione nuova (R-DB-K1, D-K7 b)
-- ------------------------------------------------------------
-- Perche' questo file esiste
--   Il verbo e' eseguibile dall'app e non ha un guard di permesso: lo chiude
--   soltanto la condizione «nessuna veste ha un legame SUPER_ADMIN, acceso o
--   spento». Il file prova che la condizione apre sull'installazione vuota, che
--   chiude in tutti gli altri casi (un amministratore presente, solo legami
--   spenti, la seconda chiamata), e che sul vuoto nasce un amministratore che
--   entra davvero: veste accesa, SUPER_ADMIN senza scadenza, perimetro su tutto.
--
--   Il vuoto si COSTRUISCE: su dbdev i legami SUPER_ADMIN ci sono, su un database
--   ricostruito da zero no. pg_temp.svuota_legami_sa() li cancella tutti, coi guard
--   spenti solo per quell'istruzione, e il test 3 verifica che il vuoto ci sia.
--
--   ⚠️ I controlli differiti di anagrafiche.soggetti (gli indirizzi obbligatori,
--   i contatti) scattano al COMMIT, dopo che il verbo ha scritto gli indirizzi.
--   Il file li tiene IMMEDIATE, li rimanda solo intorno a ogni chiamata del verbo
--   (pg_temp.chiama) e li fa scattare subito dopo con SET CONSTRAINTS ALL
--   IMMEDIATE: un indirizzo che manca rompe il test, come romperebbe il COMMIT.
--
--   Fuori, dichiarato: la concorrenza. Due chiamate in parallelo non si provano
--   in una sessione sola; le serializza il LOCK TABLE sui legami.
-- ------------------------------------------------------------
-- Indice test
--  1) Il verbo e' SECURITY DEFINER
--  2) L'app ha EXECUTE sul verbo
--  3) Fixture: nessun legame SUPER_ADMIN su una veste
--  4) Sul vuoto il verbo passa
--  5) La credenziale e' nuova (non riusata)
--  6) L'amministratore e' SUPER_ADMIN (script.fn_is_super_admin)
--  7) La sua veste OPERATORE e' accesa
--  8) Esiste ora un SUPER_ADMIN senza scadenza
--  9) Il perimetro emittenti e' NULL: tutto, senza nessun emittente legato
-- 10) Il soggetto e' privato (PR), con la qualifica AMMINISTRATORE
-- 11) Residenza e domicilio fiscale: il domicilio che manca e' la residenza
-- 12) La seconda chiamata: E_PRIMO_AMMINISTRATORE_GIA_PRESENTE
-- 13) …e non nasce niente: nessuna credenziale con quell'email
-- 14) Solo legami SUPER_ADMIN spenti (D-K7 b): rifiutato
-- 15) Sul vuoto, un'email con credenziale senza consenso: E_CREDENZIALE_DA_CONFERMARE
-- 16) …e non nasce nessun legame SUPER_ADMIN
-- 17) Col consenso il verbo passa e riusa la credenziale
-- 18) fn_crea_indirizzi_operatore: un indirizzo che porta il tipo si rifiuta
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. Li rimanda solo pg_temp.chiama, intorno al verbo.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il verbo e' DEFINER e non legge il contesto
--   dell'operatore: sul primo impianto nessuna persona e' autenticata.

SELECT plan(18);

-- =========================================================
-- Helper
-- =========================================================

-- Il vuoto: nessun legame SUPER_ADMIN su una veste. I guard dell'ultimo
-- SUPER_ADMIN si spengono solo per la cancellazione.
CREATE OR REPLACE FUNCTION pg_temp.svuota_legami_sa()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    ALTER TABLE config.profili_accesso_bindings
        DISABLE TRIGGER trg_profili_accesso_bindings_a10_guard_ultimo_super_admin_upd_d;
    DELETE FROM config.profili_accesso_bindings pab
     USING config.profili_accesso pa
     WHERE pa.id = pab.profilo_accesso_id
       AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
       AND pab.identita_digitale_id IS NOT NULL;
    ALTER TABLE config.profili_accesso_bindings
        ENABLE TRIGGER trg_profili_accesso_bindings_a10_guard_ultimo_super_admin_upd_d;
END;
$$;

-- Solo legami spenti: ogni legame SUPER_ADMIN su una veste resta, spento.
CREATE OR REPLACE FUNCTION pg_temp.spegni_legami_sa()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    ALTER TABLE config.profili_accesso_bindings
        DISABLE TRIGGER trg_profili_accesso_bindings_a10_guard_ultimo_super_admin_upd_d;
    UPDATE config.profili_accesso_bindings pab
       SET attivo = false
      FROM config.profili_accesso pa
     WHERE pa.id = pab.profilo_accesso_id
       AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
       AND pab.identita_digitale_id IS NOT NULL;
    ALTER TABLE config.profili_accesso_bindings
        ENABLE TRIGGER trg_profili_accesso_bindings_a10_guard_ultimo_super_admin_upd_d;
END;
$$;

-- Quanti legami SUPER_ADMIN su una veste, accesi o spenti.
CREATE OR REPLACE FUNCTION pg_temp.legami_sa()
RETURNS bigint
LANGUAGE sql
AS $$
    SELECT count(*)
      FROM config.profili_accesso_bindings pab
      JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
     WHERE pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
       AND pab.identita_digitale_id IS NOT NULL;
$$;

-- La residenza nella forma che il guard pretende per lo stato.
CREATE OR REPLACE FUNCTION pg_temp.residenza()
RETURNS jsonb
LANGUAGE sql
AS $$
    SELECT jsonb_build_object('indirizzo_libero', 'Via del Primo Impianto 1', 'stato_id', 1)
           || (SELECT jsonb_strip_nulls(to_jsonb(frm)) FROM dbops.fn_pgtap_indirizzo_libero_forma(1) frm);
$$;

-- Il verbo, coi controlli differiti rimandati solo per lui e fatti scattare
-- subito dopo: come al COMMIT di una chiamata vera. Ritorna il codice che l'ha
-- rifiutato, o NULL. ⚠️ Un controllo differito che rifiuta scatta FUORI da
-- fn_pgtap_codice_errore, al SET CONSTRAINTS ALL IMMEDIATE: interrompe il
-- file, come interromperebbe il COMMIT. E' voluto: non e' un rifiuto del verbo
-- da asserire, e' un amministratore che non potrebbe nascere.
CREATE OR REPLACE FUNCTION pg_temp.chiama(p_etichetta text, p_riusa integer DEFAULT NULL)
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
    v_codice text;
BEGIN
    SET CONSTRAINTS ALL DEFERRED;
    v_codice := dbops.fn_pgtap_codice_errore(format(
        $f$SELECT * FROM anagrafiche.fn_crea_primo_amministratore(
               p_cognome             := 'Primo',
               p_nome                := 'Amministratore',
               p_codice_fiscale      := %L,
               p_sesso               := 'F',
               p_email               := %L,
               p_username            := %L,
               p_password_hash       := 'pbkdf2_sha256$1$pgtap$pgtap',
               p_indirizzo_residenza := %L::jsonb,
               p_riusa_auth_user_id  := %s)$f$,
        dbops.fn_pgtap_cf_libero(),
        p_etichetta || '@primo-impianto.pgtap.invalid',
        p_etichetta,
        pg_temp.residenza()::text,
        COALESCE(p_riusa::text, 'NULL')));
    SET CONSTRAINTS ALL IMMEDIATE;
    RETURN v_codice;
END;
$$;

-- La credenziale nata dalla chiamata con quell'etichetta.
CREATE OR REPLACE FUNCTION pg_temp.credenziale(p_etichetta text)
RETURNS integer
LANGUAGE sql
AS $$
    SELECT au.id FROM django.auth_user au
     WHERE lower(au.email) = lower(p_etichetta || '@primo-impianto.pgtap.invalid');
$$;

-- =========================================================
-- 1-2) Postura
-- =========================================================
SELECT ok(
    (SELECT p.prosecdef FROM pg_proc p
      WHERE p.oid = 'anagrafiche.fn_crea_primo_amministratore'::regproc),
    '1) Il verbo e'' SECURITY DEFINER');

SELECT ok(
    has_function_privilege('zeroerp_app', 'anagrafiche.fn_crea_primo_amministratore'::regproc, 'EXECUTE'),
    '2) L''app ha EXECUTE sul verbo (lo chiama il comando del backend)');

-- =========================================================
-- 3-11) Sul vuoto nasce il primo amministratore
-- =========================================================
SELECT pg_temp.svuota_legami_sa();

SELECT is(pg_temp.legami_sa(), 0::bigint,
    '3) Fixture: nessun legame SUPER_ADMIN su una veste');

SELECT is(pg_temp.chiama('pgtap_primo'), NULL,
    '4) Sul vuoto il verbo passa');

SELECT is(
    (SELECT au.username || '/' || au.password FROM django.auth_user au
      WHERE au.id = pg_temp.credenziale('pgtap_primo')),
    'pgtap_primo/pbkdf2_sha256$1$pgtap$pgtap',
    '5) La credenziale e'' nuova: username e hash quelli passati al verbo');

SELECT ok(script.fn_is_super_admin(pg_temp.credenziale('pgtap_primo')),
    '6) L''amministratore e'' SUPER_ADMIN');

SELECT ok(
    (SELECT idg.attivo FROM anagrafiche.identita_digitali idg
      WHERE idg.auth_user_id = pg_temp.credenziale('pgtap_primo')
        AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo),
    '7) La sua veste OPERATORE e'' accesa, senza invito');

SELECT ok(script.fn_check_almeno_un_super_admin_attivo(),
    '8) Esiste un SUPER_ADMIN senza scadenza');

SELECT ok(script.fn_get_emittenti_scope_pk_ids(pg_temp.credenziale('pgtap_primo')) IS NULL
          AND NOT EXISTS (SELECT 1 FROM config.user_emittenti_fiscali uef
                           WHERE uef.auth_user_id = pg_temp.credenziale('pgtap_primo')),
    '9) Il perimetro e'' NULL (tutto), senza nessun emittente legato');

SELECT is(
    (SELECT tsd.codice_interno || '/' || q.codice_interno
       FROM anagrafiche.identita_digitali idg
       JOIN anagrafiche.soggetti_ruoli sr       ON sr.id = idg.soggetto_ruolo_id
       JOIN anagrafiche.soggetti s              ON s.id = sr.soggetto_id
       JOIN config.tipi_soggetto_dettaglio tsd  ON tsd.id = s.tipo_soggetto_dettaglio_id
       JOIN anagrafiche.risorse_umane ru        ON ru.soggetto_ruolo_id = sr.id
       JOIN config.qualifiche q                 ON q.id = ru.qualifica_id
      WHERE idg.auth_user_id = pg_temp.credenziale('pgtap_primo')
        AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo)::text,
    'PR/AMMINISTRATORE',
    '10) Il soggetto e'' privato (PR), con la qualifica AMMINISTRATORE');

SELECT is(
    (SELECT string_agg(ti.codice_interno || '=' || isg.indirizzo_libero, ',' ORDER BY ti.codice_interno)
       FROM anagrafiche.identita_digitali idg
       JOIN anagrafiche.soggetti_ruoli sr      ON sr.id = idg.soggetto_ruolo_id
       JOIN anagrafiche.indirizzi_soggetti isg ON isg.soggetto_id = sr.soggetto_id
       JOIN config.tipi_indirizzi ti           ON ti.id = isg.tipo_indirizzo_id
      WHERE idg.auth_user_id = pg_temp.credenziale('pgtap_primo')
        AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo),
    'DOMFISC=Via del Primo Impianto 1,RES=Via del Primo Impianto 1',
    '11) Residenza e domicilio fiscale: il domicilio che manca e'' la residenza');

-- =========================================================
-- 12-14) Chiuso in tutti gli altri casi
-- =========================================================
SELECT is(pg_temp.chiama('pgtap_secondo'), 'E_PRIMO_AMMINISTRATORE_GIA_PRESENTE',
    '12) La seconda chiamata: E_PRIMO_AMMINISTRATORE_GIA_PRESENTE');

SELECT is(pg_temp.credenziale('pgtap_secondo'), NULL,
    '13) …e non nasce niente: nessuna credenziale con quell''email');

SELECT pg_temp.spegni_legami_sa();

SELECT is(pg_temp.chiama('pgtap_spenti'), 'E_PRIMO_AMMINISTRATORE_GIA_PRESENTE',
    '14) Solo legami SUPER_ADMIN spenti: un amministratore c''e'' stato, rifiutato');

-- =========================================================
-- 15-17) Il riuso di una credenziale vuole il consenso
-- =========================================================
SELECT pg_temp.svuota_legami_sa();

SELECT anagrafiche.fn_crea_auth_user(
    p_username      := 'pgtap_riuso',
    p_email         := 'pgtap_riuso@primo-impianto.pgtap.invalid',
    p_password_hash := 'pbkdf2_sha256$1$pgtap$pgtap',
    p_first_name    := 'Riuso',
    p_last_name     := 'Pgtap');

SELECT is(pg_temp.chiama('pgtap_riuso'), 'E_CREDENZIALE_DA_CONFERMARE',
    '15) Un''email con credenziale, senza consenso: E_CREDENZIALE_DA_CONFERMARE');

SELECT is(pg_temp.legami_sa(), 0::bigint,
    '16) …e non nasce nessun legame SUPER_ADMIN');

SELECT is(pg_temp.chiama('pgtap_riuso', pg_temp.credenziale('pgtap_riuso')), NULL,
    '17) Col consenso il verbo passa, sulla credenziale che c''era');

-- =========================================================
-- 18) Il building block degli indirizzi: il tipo lo dice il parametro
-- =========================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $f$SELECT anagrafiche.fn_crea_indirizzi_operatore(gen_random_uuid(), %L::jsonb)$f$,
        (pg_temp.residenza() || '{"tipo_indirizzo_codice_interno": "FATT"}')::text)),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '18) fn_crea_indirizzi_operatore: un indirizzo che porta il tipo e'' una chiamata non valida');

SELECT * FROM finish();
ROLLBACK;
