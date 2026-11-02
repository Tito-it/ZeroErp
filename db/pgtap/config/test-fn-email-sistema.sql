-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
-- ChangeSet: 20260906-01 / -02 / -14 · 20260907-05 · 20260911-06 / -07 / -08
-- Brief: brief-db-email-perimetro-e-invio-di-sistema §4 ·
--        brief-db-sveglia-dei-processi §23 ·
--        brief-db-stato-email-console-non-e-inviata §7.2
--
-- Elenco test (plan 12):
--  1) la porta accoda, e scrive SEMPRE ambito SISTEMA senza emittente
--  2) ⭐ e le tre colonne di CONTESTO arrivano: uo, cc, pratica
--  3) ⛔ un destinatario vuoto si ferma
--  4) la gemella CHIUDE, e (4-bis) scrive esito, tentativi+1 e la data
--  5) ⛔ `PENDING` non e' un esito ammesso, e la frase lo dice
--  6) ⛔ un identificativo inesistente si ferma con un codice suo (TECNICO)
--  7) ⛔ una riga NON di sistema non si chiude da questa porta — ed e' il caso
--     pericoloso, con un codice suo e una frase che nomina l'ambito
--  8) ⭐ `SIMULATA` e' un esito ammesso, e (8-bis) NON porta una data di invio
--  9) ⭐ L'INVARIANTE FRA LE DUE SEDI DEL VOCABOLARIO
-- 10) `config.email_outbox` ammette lo stesso valore
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
--
-- ⭐ E IL TEST 9 E' QUELLO CHE MANCAVA, rev 2026-09-11.
--   Il vocabolario di `config.email_log.stato` ha DUE sedi: il
--   `CHECK chk_email_log_stato` e la whitelist di `p_stato` qui dentro. Fino a
--   oggi niente le confrontava, e la seconda era invisibile: il brief del
--   backend chiedeva «un valore nel CHECK, nient'altro», e con quello solo il
--   valore nuovo sarebbe rimasto IRRAGGIUNGIBILE per le righe di ambito
--   `SISTEMA` — che passano tutte da questa funzione, perche' la RLS rifiuta
--   l'`UPDATE` diretto.
--   ⛔ E l'invariante NON e' l'uguaglianza: la funzione esclude `PENDING` di
--   proposito («questa chiude, non rimette in coda»). Un test che pretendesse
--   le due liste identiche nascerebbe rosso e verrebbe spento il giorno dopo.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

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
-- ⚠️ Si chiede il MESSAGGIO e non il solo SQLSTATE, rev 2026-09-11: tutti gli
--   errori applicativi sono `P0001`, quindi con `NULL` al posto della frase
--   questo test sarebbe verde anche se a fermare la chiamata fosse una qualunque
--   delle altre due guardie. ⭐ E la frase ELENCA gli esiti ammessi: e' la
--   seconda rete sotto il test 9 — se un domani qualcuno allargasse la whitelist
--   senza toccare il messaggio, l'operatore leggerebbe un elenco incompleto.
SELECT throws_ok(
    format($$SELECT config.fn_chiudi_email_sistema(%s, 'PENDING')$$,
           current_setting('pgtap.email_id')),
    'P0001',
    'Validazione fallita: stato ammesso solo fra SENT, FAILED, RETRY e SIMULATA',
    '5. PENDING non e'' un esito ammesso, e la frase elenca quelli che lo sono'
);

-- ⚠️ Un UPDATE che non trova niente e' muto per natura, e il chiamante
--   crederebbe di aver chiuso qualcosa.
-- ⚠️ Non basta `throws_ok` col solo SQLSTATE: tutti gli errori applicativi sono
--   `P0001`, quindi sarebbe verde anche se a fermare la chiamata fosse un guard
--   qualunque. Si chiede il MESSAGGIO, che e' l'unica cosa che distingue questo
--   caso dagli altri due.
-- ⭐ E il codice e' suo, non `E_VALIDAZIONE`: quello e' DATO_ERRATO, «hai
--   sbagliato i dati». Ma questo id non arriva da una persona — e' quello che il
--   chiamante ha scritto un istante prima. ⛔ E nemmeno NON_TROVATO, che porta un
--   404: qui non c'e' nessuno che cerca una risorsa, c'e' del codice che passa un
--   valore inesistente. Segnalato dal classificatore dei codici il 2026-09-06.
SELECT throws_ok(
    $$SELECT config.fn_chiudi_email_sistema(999999999, 'SENT')$$,
    'P0001',
    'Nessuna email di sistema con identificativo 999999999.',
    '6. un identificativo inesistente si ferma con un codice SUO, non con «dati errati»'
);

-- ⛔ IL CASO PERICOLOSO: qualcuno usa la porta di sistema per una email che
--   appartiene a un'azienda. E' l'unico momento in cui lo si puo' notare.
DO $altrui$
DECLARE
    v_id config.email_log.id%TYPE;
BEGIN
    -- ⚠️ Rev 2026-09-25: una mail OPERATORE nomina il suo autore
    --   (chk_email_log_operatore_creatore, 20260925-64), e la policy la da'
    --   solo a lui (20260925-66).
    INSERT INTO config.email_log
        (destinatario, oggetto, stato, ambito, emittente_fiscale_id,
         creato_da_user_id, contesto_json)
    VALUES ('azienda@example.invalid', 'pgtap', 'PENDING', 'OPERATORE',
            script.fn_pgtap_emittente_operatore(),
            NULLIF(current_setting('app.current_user_id', true), '')::integer,
            '{}'::jsonb)
    RETURNING id INTO v_id;
    PERFORM set_config('pgtap.email_azienda', v_id::text, true);
END
$altrui$;

-- ⚠️ E si chiede il MESSAGGIO, non il solo SQLSTATE. Tutti gli errori
--   applicativi sono `P0001`: con `NULL` al posto della frase questo test
--   sarebbe verde anche se a fermare la chiamata fosse il guard di `p_stato`
--   due righe piu' su — cioe' proverebbe che qualcosa si e' rotto, non CHE COSA.
--   ⛔ E fino al 2026-09-07 era proprio cosi': la frase e' entrata insieme al
--   codice suo, e senza di essa il test non avrebbe distinto il caso nuovo.
-- ⭐ Il codice e' `E_EMAIL_LOG_NON_DI_SISTEMA`, TECNICO, e non piu'
--   `E_VALIDAZIONE` (DATO_ERRATO, «hai sbagliato i dati»): qui la riga esiste e
--   i parametri sono a posto — e' il chiamante che ha bussato alla porta
--   sbagliata. ⛔ E non si riusa `E_EMAIL_LOG_INESISTENTE` del test 6: «la riga
--   non c'e'» e «la riga c'e' e non e' tua» mandano a guardare due posti
--   diversi. Domanda lasciata aperta da 20260906-14, chiusa da 20260907-05
--   quando il classificatore ha imparato a leggere questa forma di guardia.
-- ⚠️ La frase nomina l'AMBITO della riga, ed e' il valore utile: dice a chi
--   appartiene davvero l'email che si stava per chiudere.
SELECT throws_ok(
    format($$SELECT config.fn_chiudi_email_sistema(%s, 'SENT')$$,
           current_setting('pgtap.email_azienda')),
    'P0001',
    format('L''email di sistema %s appartiene all''ambito OPERATORE: da questa '
           'porta si chiudono solo le email di ambito SISTEMA.',
           current_setting('pgtap.email_azienda')),
    '7. una email di un''azienda non si chiude dalla porta di sistema, e la frase dice di chi e'''
);

-- ============================================================
-- 8..10. ⭐ `SIMULATA` — e le DUE sedi del vocabolario
-- ============================================================
-- ⭐ «Stampata a video» e «consegnata» sono due fatti opposti, e fino al
--   2026-09-11 si scrivevano con la stessa parola: il ramo che mostra la mail
--   invece di spedirla chiudeva la riga in `SENT`.
-- ⛔ Serviva un valore SUO, e non uno dei quattro: `FAILED` affermerebbe un
--   guasto che non c'e' (in sviluppo quel comportamento e' VOLUTO, e marcarlo
--   fallito insegnerebbe a ignorare i rossi), `PENDING`/`RETRY` la
--   rimetterebbero in coda senza fine.
DO $simulata$
DECLARE
    v_id config.email_log.id%TYPE;
BEGIN
    v_id := config.fn_accoda_email_sistema(
        'simulata@example.invalid', 'pgTAP esito simulato', '<p/>');
    PERFORM set_config('pgtap.email_simulata', v_id::text, true);
END
$simulata$;

SELECT lives_ok(
    format($$SELECT config.fn_chiudi_email_sistema(%s, 'SIMULATA')$$,
           current_setting('pgtap.email_simulata')),
    '8. SIMULATA e'' un esito ammesso: la porta di sistema lo scrive'
);

-- ⛔ E NON PORTA UNA DATA DI INVIO, ed e' la meta' che si dimentica.
--   `inviato_at` e' l'unica colonna che DATA una consegna, ed e' proiettata sia
--   nella lista sia nel dettaglio del giornale: valorizzarla su una riga che
--   dichiara il non-invio sposterebbe la bugia di una casella invece di
--   toglierla. Il momento c'e' gia' in `data_insert`.
-- ⭐ Lo rende possibile il `COALESCE(p_inviato_at, l.inviato_at)` della
--   funzione: il chiamante passa NULL e la colonna resta com'era.
-- ⚠️ `tentativi` sale lo stesso, e va bene: la riga e' TERMINALE comunque —
--   `SIMULATA` non compare nella SELECT di `send_pending_emails`, che ripesca
--   `PENDING`, `FAILED` e `RETRY`. Nessuno la riprende in mano.
SELECT is(
    (SELECT stato || '/' || COALESCE(inviato_at::text, 'NULL') || '/' || tentativi::text
       FROM config.email_log
      WHERE id = current_setting('pgtap.email_simulata')::bigint),
    'SIMULATA/NULL/1',
    '8-bis. e la riga non porta la data di una consegna che non c''e'' stata'
);

-- ⭐ L'INVARIANTE FRA LE DUE SEDI DEL VOCABOLARIO — il presidio che mancava.
--
--     whitelist di fn_chiudi_email_sistema  =  valori di chk_email_log_stato
--                                              MENO  {PENDING}
--
-- ⛔ NON e' l'uguaglianza: `PENDING` e' escluso di proposito, perche' questa
--   funzione chiude e non rimette in coda. Scritto come uguaglianza, questo
--   test nascerebbe rosso e verrebbe spento.
-- ⚠️ E' un presidio SUL TESTO del corpo, quindi il suo perimetro e' la forma
--   `p_stato NOT IN (...)`: se qualcuno riscrivesse la guardia in un'altra forma
--   (un `ANY`, una tabella) il `substring` tornerebbe NULL e questo test
--   fallirebbe invece di tacere — che e' il verso giusto, perche' a quel punto
--   il presidio va riscritto, non ignorato.
-- ⭐ Il confronto e' fra TESTI apposta: su un rosso la diagnostica TAP stampa
--   entrambi gli elenchi, e si vede subito quale dei due e' rimasto indietro.
SELECT is(
    (SELECT array_agg(trim(both '''' from trim(x)) ORDER BY trim(both '''' from trim(x)))::text
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace,
            LATERAL unnest(string_to_array(
                substring(p.prosrc from 'p_stato NOT IN \(([^)]*)\)'), ',')) AS x
      WHERE n.nspname = 'config'
        AND p.proname = 'fn_chiudi_email_sistema'),
    (SELECT ARRAY(SELECT v FROM (
                SELECT m[1] AS v
                  FROM pg_constraint k,
                       LATERAL regexp_matches(pg_get_constraintdef(k.oid),
                                              '''([A-Z_]+)''::character varying', 'g') AS m
                 WHERE k.conrelid = 'config.email_log'::regclass
                   AND k.conname  = 'chk_email_log_stato'
             ) AS c WHERE v <> 'PENDING' ORDER BY v)::text),
    '9. la whitelist della funzione e'' il CHECK meno PENDING: le due sedi del vocabolario non divergono'
);

-- Il gemello una tabella piu' in la': in console mode `send_from_outbox` scrive
-- `SENT` sulla bozza. ⛔ E non si puo' dire che quella colonna parli del ciclo
-- di REDAZIONE e non della consegna: lo smentisce il ramo accanto nello stesso
-- metodo, che su fallimento SMTP riporta la bozza a `DRAFT` perche' l'operatore
-- riprovi. Una colonna che retrocede quando la consegna fallisce parla di
-- consegna.
-- ⚠️ Prova FUNZIONALE e non una lettura del catalogo: leggere il `CHECK` per
--   poi asserire cio' che il `CHECK` dice sarebbe misurare attraverso il
--   meccanismo esaminato.
SELECT lives_ok(
    $$INSERT INTO config.email_outbox (destinatario, oggetto, corpo_html, stato)
      VALUES ('simulata-outbox@example.invalid', 'pgTAP bozza simulata', '<p/>', 'SIMULATA')$$,
    '10. config.email_outbox ammette SIMULATA, come la sua gemella'
);

SELECT * FROM finish();

ROLLBACK;
