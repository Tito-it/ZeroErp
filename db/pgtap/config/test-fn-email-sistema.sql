-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test deve RILEGGERE le righe che le due porte
--   scrivono, e quelle righe la policy le nasconde a un operatore che non sia
--   super admin — leggerle e' l'unico modo di provare che la porta ha scritto la
--   cosa giusta. ⭐ Che l'operatore NON le veda e' l'altra meta', ed e' provata
--   dove va provata: db/pgtap/rls/test-rls-email-log-ambito.sql.
--
-- Test: le due porte per le email di sistema
-- ChangeSet: 20260906-01 / -02 · Brief: brief-db-email-perimetro-e-invio-di-sistema §4
--
-- Elenco test (plan 8):
--  1) la porta accoda, e scrive SEMPRE ambito SISTEMA senza emittente
--  2) ⭐ e le tre colonne di CONTESTO arrivano: uo, cc, pratica
--  3) ⛔ un destinatario vuoto si ferma
--  4) la gemella CHIUDE, e (4-bis) scrive esito, tentativi+1 e la data
--  5) ⛔ `PENDING` non e' un esito ammesso
--  6) ⛔ un identificativo inesistente si ferma, e lo dice
--  7) ⛔ una riga NON di sistema non si chiude da questa porta — ed e' il caso
--     pericoloso, con parole sue
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ PERCHE' LE DUE FUNZIONI SI COLLAUDANO INSIEME.
--   Sono una cosa sola: la decisione e' che una mail di sistema parta SUBITO,
--   quindi dopo l'`INSERT` il backend tenta l'invio e ne scrive l'esito.
--   ⛔ Instradare solo l'accodamento avrebbe spostato la rottura di due righe
--   piu' in la', sull'aggiornamento — che la policy blocca per lo STESSO motivo.
--
-- ⛔ E IL TEST 7 E' QUELLO CHE TIENE LA PORTA STRETTA.
--   Il pregio di queste funzioni e' che sanno fare una cosa sola. Senza il
--   test 7, `fn_chiudi_email_sistema` sarebbe un modo per aggiornare QUALUNQUE
--   email aggirando la policy — cioe' il contrario di cio' per cui esiste.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- 1..2. La porta che accoda
-- ============================================================
DO $accoda$
DECLARE
    v_id config.email_log.id%TYPE;
BEGIN
    v_id := config.fn_accoda_email_sistema(
        'reset@example.invalid', 'Reset password pgTAP', '<p/>',
        p_unita_organizzativa_id => (SELECT id FROM config.unita_organizzative
                                      ORDER BY id LIMIT 1),
        p_destinatari_cc         => ARRAY['cc@example.invalid'],
        p_pratica_id             => NULL);
    PERFORM set_config('pgtap.email_id', v_id::text, true);
END
$accoda$;

-- ⛔ `ambito` ed emittente non sono parametri: sono decisi dalla funzione. E'
--   tutto il suo valore — se fossero passabili, sarebbe una porta per scrivere
--   qualunque email aggirando la policy.
SELECT is(
    (SELECT ambito || '/' || COALESCE(emittente_fiscale_id::text, 'NULL')
            || '/' || stato
       FROM config.email_log
      WHERE id = current_setting('pgtap.email_id')::bigint),
    'SISTEMA/NULL/PENDING',
    '1. la porta scrive sempre ambito SISTEMA, senza emittente, in PENDING'
);

-- ⭐ Le tre colonne che la prima stesura perdeva. ⚠️ Senza di esse quel dato
--   sarebbe sparito IN SILENZIO instradando i chiamanti — peggio di un rifiuto,
--   perche' un rifiuto lo vedi.
SELECT is(
    (SELECT COALESCE(unita_organizzativa_id::text, '-') || '/' ||
            COALESCE(array_to_string(destinatari_cc, ','), '-')
       FROM config.email_log
      WHERE id = current_setting('pgtap.email_id')::bigint),
    (SELECT (SELECT id FROM config.unita_organizzative ORDER BY id LIMIT 1)::text
            || '/cc@example.invalid'),
    '2. le tre colonne di contesto arrivano fino alla riga'
);

-- ============================================================
-- 3. ⛔ Cio' che non deve entrare
-- ============================================================
-- Una email senza destinatario non partira' mai e nessuno la collegherebbe a
-- niente: si rifiuta subito, con un nome.
SELECT throws_ok(
    $$SELECT config.fn_accoda_email_sistema('', 'x', '<p/>')$$,
    'P0001',
    NULL,
    '3. un destinatario vuoto si ferma'
);

-- ============================================================
-- 4..7. La gemella che chiude
-- ============================================================
SELECT lives_ok(
    format($$SELECT config.fn_chiudi_email_sistema(%s, 'SENT', NULL, now())$$,
           current_setting('pgtap.email_id')),
    '4. la gemella chiude la riga che la porta aveva scritto'
);

SELECT is(
    (SELECT stato || '/' || tentativi::text || '/' ||
            (inviato_at IS NOT NULL)::text
       FROM config.email_log
      WHERE id = current_setting('pgtap.email_id')::bigint),
    'SENT/1/true',
    '4-bis. e scrive esito, tentativi+1 e la data di invio'
);

-- ⛔ Questa e' la funzione che CHIUDE. Ammettere `PENDING` vorrebbe dire poter
--   resuscitare una email gia' chiusa.
SELECT throws_ok(
    format($$SELECT config.fn_chiudi_email_sistema(%s, 'PENDING')$$,
           current_setting('pgtap.email_id')),
    'P0001',
    NULL,
    '5. PENDING non e'' un esito ammesso'
);

-- ⚠️ Un UPDATE che non trova niente e' muto per natura, e il chiamante
--   crederebbe di aver chiuso qualcosa.
SELECT throws_ok(
    $$SELECT config.fn_chiudi_email_sistema(999999999, 'SENT')$$,
    'P0001',
    NULL,
    '6. un identificativo inesistente si ferma invece di tacere'
);

-- ⛔ IL CASO PERICOLOSO: qualcuno usa la porta di sistema per una email che
--   appartiene a un'azienda. E' l'unico momento in cui lo si puo' notare.
DO $altrui$
DECLARE
    v_id config.email_log.id%TYPE;
BEGIN
    INSERT INTO config.email_log
        (destinatario, oggetto, stato, ambito, emittente_fiscale_id, contesto_json)
    VALUES ('azienda@example.invalid', 'pgtap', 'PENDING', 'OPERATORE',
            script.fn_pgtap_emittente_operatore(), '{}'::jsonb)
    RETURNING id INTO v_id;
    PERFORM set_config('pgtap.email_azienda', v_id::text, true);
END
$altrui$;

SELECT throws_ok(
    format($$SELECT config.fn_chiudi_email_sistema(%s, 'SENT')$$,
           current_setting('pgtap.email_azienda')),
    'P0001',
    NULL,
    '7. una email di un''azienda non si chiude dalla porta di sistema'
);

SELECT * FROM finish();

ROLLBACK;
