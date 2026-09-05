-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: config.email_log — la policy `rls_email_log_ambito` e il write-guard
-- ChangeSet: 20260905-43 / -44 · Brief: brief-db-email-perimetro-e-invio-di-sistema
--
-- Elenco test (plan 6):
--  1) ⭐ IL PRESUPPOSTO: questa sessione SUBISCE la row level security
--  2) ⛔ un operatore NON vede le email di ambito SISTEMA
--  3) ✅ vede — e scrive — quelle della propria azienda
--  4) ⛔ una email di un'ALTRA azienda si ferma, e SPIEGA
--  5) ⭐ la regola nomina l'identita' tecnica di chi spedisce
--  6) ⚠️ e quel processo e' a catalogo, con un'identita' viva
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ IL TEST 2 E' LA DECISIONE, NON UN DETTAGLIO.
--   Le email di ambito SISTEMA — reset password, alert — hanno un contenuto che
--   vale quanto una credenziale. Fra le persone le legge **solo il super
--   admin**; fra le macchine, l'identita' tecnica di chi le spedisce.
--   ⇒ Un operatore qualunque, anche in buona fede, non deve poterle aprire.
--
-- ⚠️ IL TEST 5 GUARDA IL TESTO DELLA REGOLA, e ha per perimetro quella regola.
--   Non prova che l'identita' tecnica veda davvero le righe — per farlo
--   servirebbe girare NEI SUOI PANNI, e quella e' una sessione che il test non
--   ha. Prova che il ramo ci sia: se sparisse, la posta di sistema smetterebbe
--   di partire **in silenzio**, perche' una coda vuota e' identica a «niente da
--   fare».
--   ⭐ Che il ramo funzioni davvero, livello per livello, lo prova
--   db/pgtap/script/test-fn-scope-identita-processo.sql.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- ============================================================
-- 1. Il presupposto
-- ============================================================
-- ⚠️ Senza, i test 2..4 sarebbero verdi «perche' non succede niente».
SELECT ok(
    row_security_active('config.email_log'::regclass),
    '1. questa sessione SUBISCE la RLS: i test che seguono hanno senso'
);

-- ============================================================
-- 2. ⛔ Le email di sistema non si vedono
-- ============================================================
-- ⭐ La riga la scrive la PORTA (`config.fn_accoda_email_sistema`), che e'
--   SECURITY DEFINER del proprietario e quindi non subisce la policy: e'
--   esattamente il percorso del reset password, che non ha una sessione.
--   ⇒ Poi si guarda dalla sessione dell'operatore, e non deve esserci.
DO $sistema$
DECLARE
    v_id config.email_log.id%TYPE;
BEGIN
    v_id := config.fn_accoda_email_sistema(
        'reset@example.invalid', 'Reset password pgTAP', '<p/>');
    PERFORM set_config('pgtap.email_sistema', v_id::text, true);
END
$sistema$;

SELECT is_empty(
    format($$SELECT id FROM config.email_log WHERE id = %s$$,
           current_setting('pgtap.email_sistema')),
    '2. un operatore non vede l''email di sistema appena scritta'
);

-- ============================================================
-- 3. ✅ Cio' che deve passare
-- ============================================================
-- Prima del rifiuto va provato il consenso: una policy che nega tutto
-- passerebbe i test 2 e 4 senza essere corretta.
SELECT lives_ok(
    $$INSERT INTO config.email_log
          (destinatario, oggetto, stato, ambito, emittente_fiscale_id, contesto_json)
      VALUES ('mia@example.invalid', 'pgtap mia', 'PENDING', 'OPERATORE',
              script.fn_pgtap_emittente_operatore(), '{}'::jsonb)$$,
    '3. una email della PROPRIA azienda si scrive'
);

-- ============================================================
-- 4. ⛔ Cio' che deve fermarsi, e come lo dice
-- ============================================================
-- ⚠️ Non si usa `throws_ok` col solo SQLSTATE: tutti gli errori applicativi sono
--   `P0001`, quindi sarebbe verde anche se a fermare la riga fosse un guard
--   qualunque — o la policy con il suo messaggio inservibile. Si chiede che a
--   parlare sia il write-guard dello SCOPE.
DO $altrui$
DECLARE
    v_esito   text := 'non-sollevato';
    v_altro   anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
    SELECT ef.id INTO v_altro
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.attivo AND ef.id <> script.fn_pgtap_emittente_operatore()
     ORDER BY ef.id
     LIMIT 1;

    IF v_altro IS NULL THEN
        PERFORM set_config('pgtap.esito4', 'skip', true);
        RETURN;
    END IF;

    BEGIN
        INSERT INTO config.email_log
            (destinatario, oggetto, stato, ambito, emittente_fiscale_id, contesto_json)
        VALUES ('altrui@example.invalid', 'pgtap altrui', 'PENDING', 'OPERATORE',
                v_altro, '{}'::jsonb);
    EXCEPTION WHEN OTHERS THEN
        v_esito := SQLSTATE || '|' ||
                   CASE WHEN SQLERRM ILIKE '%scope emittente fiscale%'
                        THEN 'scope' ELSE 'altro:' || left(SQLERRM, 60) END;
    END;

    PERFORM set_config('pgtap.esito4', v_esito, true);
END
$altrui$;

SELECT CASE
    WHEN current_setting('pgtap.esito4', true) = 'skip'
        THEN skip('4. un solo emittente attivo: il caso non e'' costruibile', 1)
    ELSE is(
        current_setting('pgtap.esito4', true),
        'P0001|scope',
        '4. una email di un''ALTRA azienda si ferma, e SPIEGA'
    )
END;

-- ============================================================
-- 5..6. ⭐ Il ramo della macchina
-- ============================================================
-- ⭐ Nel database PORTARE E' LEGGERE: non esiste un modo di spedire una riga
--   senza vederla. Se questo ramo sparisse, la posta di sistema smetterebbe di
--   partire senza che nessuno se ne accorga.
SELECT ok(
    (SELECT pg_get_expr(polqual, polrelid) LIKE '%send_pending_emails%'
       FROM pg_policy
      WHERE polrelid = 'config.email_log'::regclass
        AND polname  = 'rls_email_log_ambito'),
    '5. la regola nomina send_pending_emails: chi spedisce puo'' leggere'
);

-- ⚠️ Un nome dentro una regola di sicurezza non ha nessuna FK che lo tenga
--   ancorato: se il processo venisse rinominato, il ramo nominerebbe nessuno e
--   l'invio si fermerebbe in silenzio.
SELECT ok(
    EXISTS (SELECT 1 FROM dbops.processi
             WHERE codice = 'send_pending_emails'
               AND classe = 'DOMINIO'
               AND attivo),
    '6. e quel processo e'' a catalogo, vivo, di dominio'
);

SELECT * FROM finish();

ROLLBACK;
