-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test SPEGNE, uno alla volta, i livelli che tengono in
--   piedi un'identita' tecnica (il legame in dbops.processi_identita, l'identita'
--   in anagrafiche.identita_digitali). Sono scritture che il ruolo applicativo
--   non fa e non deve fare. Verificato cercando gli scrittori, non dedotto.
--
-- Test: script.fn_scope_identita_processo — «questa sessione e' l'identita'
--       tecnica VIVA di quel processo?»
-- ChangeSet: 20260905-31 · usata dalla policy `rls_email_outbox_ambito` (-32)
--
-- Elenco test (plan 6):
--  1) la funzione c'e', ed e' `sql` STABLE (una policy si valuta per riga)
--  2) riconosce l'identita' tecnica viva — il presupposto dei test dopo
--  3) ⛔ e dice NO a un utente che non e' quella identita'
--  4) ⛔ fail-closed: parametro NULL e processo inesistente
--  5) ⛔ spento il LEGAME processo-utente, la risposta e' NO
--  6) ⭐ REVOCATA l'identita' applicativa, la risposta e' NO
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ IL TEST 6 E' LA RAGIONE PER CUI QUESTA FUNZIONE ESISTE.
--   La policy portava un `EXISTS` scritto a mano, in due copie, che guardava un
--   livello solo: `dbops.processi_identita.attivo`. ⛔ Un'identita' **revocata**
--   — spenta in `anagrafiche.identita_digitali` — avrebbe continuato a leggere
--   i reset password finche' qualcuno non toccava anche il legame.
--   ⇒ Il test 5 passava anche con la forma vecchia; il test 6 no. Sono la stessa
--     domanda posta a due livelli diversi, e vanno letti insieme.
--
-- ⚠️ COME SI SPEGNE E SI RIACCENDE, e perche' non con un SAVEPOINT.
--   pgTAP tiene i risultati in tabelle temporanee dentro la STESSA transazione:
--   un `ROLLBACK TO` porterebbe via anche i test gia' passati. Ogni caso spegne,
--   misura in una GUC e riaccende, nello stesso blocco.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- ⛔ LE DUE IDENTITA' TECNICHE SI COSTRUISCONO, non si cercano (2026-09-12).
--   Fino a quel giorno il file leggeva dal roster l'identita' viva di
--   `send_pending_emails` e quella di `chiusura_scadenze_daily`: sono dati di
--   MACCHINA, e su un database ricostruito dai changelog il roster e' vuoto —
--   i test 2, 5 e 6 (cioe' la ragione del file) restavano collaudati solo su
--   dbdev. `dbops.fn_pgtap_crea_roster_processo(processo)` crea l'azienda e le
--   aggancia l'utente tecnico del processo, cosi' la coppia compare davvero in
--   dbops.vw_processi_roster: una per ciascuno dei due processi, PRIMA di
--   aprire il contesto.
CREATE TEMP TABLE _roster AS
SELECT 'send_pending_emails'::text AS processo, *
  FROM dbops.fn_pgtap_crea_roster_processo('send_pending_emails')
UNION ALL
SELECT 'chiusura_scadenze_daily'::text AS processo, *
  FROM dbops.fn_pgtap_crea_roster_processo('chiusura_scadenze_daily');

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _roster WHERE processo = 'chiusura_scadenze_daily'));
END $ctx$;

SELECT plan(6);

-- ============================================================
-- 1. La forma: `sql` STABLE
-- ============================================================
-- ⚠️ Non e' pignoleria: una policy si valuta PER RIGA, e una funzione `sql`
--   `STABLE` il pianificatore la puo' incorporare. Una plpgsql no.
SELECT is(
    (SELECT l.lanname || '/' || p.provolatile::text
       FROM pg_proc p
       JOIN pg_language l ON l.oid = p.prolang
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script'
        AND p.proname = 'fn_scope_identita_processo'),
    'sql/s',
    '1. script.fn_scope_identita_processo e'' una funzione sql STABLE'
);

-- ============================================================
-- L'identita' su cui si lavora
-- ============================================================
-- ⚠️ Si rilegge dal ROSTER, non dalla temp table: e' il roster che la policy
--   guarda, e se la fixture non ci comparisse il test 2 deve dirlo.
DO $scelta$
DECLARE
    v_r record;
BEGIN
    SELECT r.auth_user_id, r.identita_id INTO v_r
      FROM dbops.vw_processi_roster r
     WHERE r.processo_codice = 'send_pending_emails'
       AND r.auth_user_id = (SELECT x.auth_user_id FROM _roster x
                              WHERE x.processo = 'send_pending_emails');

    PERFORM set_config('pgtap.user', COALESCE(v_r.auth_user_id::text, ''), true);
    PERFORM set_config('pgtap.identita', COALESCE(v_r.identita_id::text, ''), true);
END
$scelta$;

-- ============================================================
-- 2..3. Chi si', chi no
-- ============================================================
-- ⛔ Il test 3 e' quello che rende il 2 una misura: una funzione che dicesse
--   sempre `true` passerebbe il 2 a pieni voti.
SELECT is(
    script.fn_scope_identita_processo(
        NULLIF(current_setting('pgtap.user', true), '')::integer,
        'send_pending_emails'),
    true,
    '2. l''identita'' tecnica viva di send_pending_emails viene riconosciuta'
);

SELECT is(
    script.fn_scope_identita_processo(
        (SELECT x.auth_user_id FROM _roster x
          WHERE x.processo = 'chiusura_scadenze_daily'),
        'send_pending_emails'),
    false,
    '3. l''identita'' di un ALTRO processo non viene riconosciuta'
);

-- ============================================================
-- 4. ⛔ Fail-closed per costruzione
-- ============================================================
-- ⚠️ Niente `STRICT`: con un parametro NULL l'EXISTS non trova niente e la
--   funzione torna **false**. `STRICT` tornerebbe NULL, che in una `USING` si
--   comporta come false ma per un'altra ragione — sarebbe una coincidenza, non
--   una difesa.
SELECT is(
    COALESCE(script.fn_scope_identita_processo(NULL, 'send_pending_emails'), true)
    OR COALESCE(script.fn_scope_identita_processo(
        NULLIF(current_setting('pgtap.user', true), '')::integer,
        'PGTAP-PROCESSO-CHE-NON-ESISTE'), true),
    false,
    '4. parametro NULL e processo inesistente danno false, non NULL'
);

-- ============================================================
-- 5..6. ⛔ Due livelli, e il secondo e' il motivo di tutto
-- ============================================================
DO $spegni$
DECLARE
    v_user integer := NULLIF(current_setting('pgtap.user', true), '')::integer;
    v_idg  bigint  := NULLIF(current_setting('pgtap.identita', true), '')::bigint;
BEGIN
    IF v_user IS NULL THEN
        RETURN;   -- il test 2 ha gia' fallito: non si finge un risultato
    END IF;

    -- a) il legame processo-utente — lo guardava anche la forma vecchia
    UPDATE dbops.processi_identita SET attivo = false WHERE auth_user_id = v_user;
    PERFORM set_config('pgtap.senza_legame',
        script.fn_scope_identita_processo(v_user, 'send_pending_emails')::text, true);
    UPDATE dbops.processi_identita SET attivo = true WHERE auth_user_id = v_user;

    -- b) ⭐ l'identita' applicativa — questo la forma vecchia NON lo guardava
    UPDATE anagrafiche.identita_digitali SET attivo = false WHERE id = v_idg;
    PERFORM set_config('pgtap.senza_identita',
        script.fn_scope_identita_processo(v_user, 'send_pending_emails')::text, true);
    UPDATE anagrafiche.identita_digitali SET attivo = true WHERE id = v_idg;
END
$spegni$;

SELECT is(current_setting('pgtap.senza_legame', true), 'false',
          '5. spento il legame processo-utente, la risposta e'' NO');

-- ⭐ Il livello che l'EXISTS scritto a mano non guardava: un'identita' revocata
--   avrebbe continuato a leggere i reset password.
SELECT is(current_setting('pgtap.senza_identita', true), 'false',
          '6. REVOCATA l''identita'' applicativa, la risposta e'' NO');

SELECT * FROM finish();

ROLLBACK;
