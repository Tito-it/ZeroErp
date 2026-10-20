# ⚙️ Funzione `fn_chiudi_email_sistema`

```sql
CREATE FUNCTION fn_chiudi_email_sistema(p_email_log_id bigint, p_stato character varying, p_errore text, p_inviato_at timestamp with time zone)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_chiudi_email_sistema(p_email_log_id bigint, p_stato character varying, p_errore text DEFAULT NULL::text, p_inviato_at timestamp with time zone DEFAULT NULL::timestamp with time zone)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_ambito config.email_log.ambito%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Scrivere l'ESITO dell'invio di una email di SISTEMA, dal
    --   percorso che non ha un utente in sessione.
    --
    -- ⛔ Tocca SOLO righe di ambito SISTEMA e SOLO i campi
    --   dell'esito. Non e' una porta di servizio per aggiornare
    --   una email qualunque.
    --
    -- ⭐ LE TRE GUARDIE HANNO TRE CODICI, e non e' pignoleria:
    --   ognuna manda a guardare un posto diverso.
    --     p_stato fuori dai valori ammessi -> il PARAMETRO;
    --     la riga non esiste               -> l'ID passato;
    --     la riga non e' di sistema        -> la PORTA scelta.
    -- =========================================================

    -- ⛔ `PENDING` non e' un esito: questa e' la funzione che
    --   CHIUDE, non quella che rimette in coda. Ammetterlo
    --   vorrebbe dire poter resuscitare una email gia' chiusa.
    -- ⚠️ Qui `E_VALIDAZIONE` e' il codice GIUSTO, ed e' l'unica
    --   delle tre guardie che lo resta: e' la validazione di un
    --   parametro, la famiglia che quel codice copre da sempre.
    --
    -- ⭐ QUESTA LISTA E' LA SECONDA SEDE DEL VOCABOLARIO, rev
    --   2026-09-11, e l'invariante che la lega alla prima NON e'
    --   l'uguaglianza:
    --       questa lista = valori di chk_email_log_stato \ {PENDING}
    --   Chi aggiunge un valore al CHECK deve aggiungerlo anche
    --   qui, o quel valore resta irraggiungibile per le righe di
    --   ambito SISTEMA — che passano tutte da questa funzione,
    --   perche' la RLS rifiuta l'UPDATE diretto.
    -- ⚠️ E' esattamente il modo in cui `SIMULATA` sarebbe nato
    --   monco: il brief del backend chiedeva «un valore nel CHECK,
    --   nient'altro», e con quello solo il digest dei presidi in
    --   sviluppo avrebbe sollevato invece di scrivere.
    --   Lo presidia db/pgtap/config/test-fn-email-sistema.sql, test 9.
    --
    -- ⭐ `SIMULATA` e' un esito ammesso, ed e' terminale: dice che
    --   l'invio non e' stato tentato di proposito (ambiente senza
    --   SMTP, mail mostrata invece che spedita). ⚠️ Il chiamante
    --   passa `p_inviato_at => NULL`: una riga che dichiara il
    --   non-invio non deve portare la data di una consegna, o la
    --   bugia si sposta di una colonna invece di sparire.
    IF p_stato IS NULL OR p_stato NOT IN ('SENT', 'FAILED', 'RETRY', 'SIMULATA') THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'fn_chiudi_email_sistema', 'E_VALIDAZIONE',
            jsonb_build_object('stato', p_stato,
                               'email_log_id', p_email_log_id),
            NULL::uuid,
            'stato ammesso solo fra SENT, FAILED, RETRY e SIMULATA');
    END IF;

    -- ⚠️ Si legge PRIMA di scrivere, per poter distinguere i due
    --   modi in cui la riga puo' non essere quella giusta. Un
    --   UPDATE che non trova niente e' muto, e il chiamante
    --   crederebbe di aver chiuso qualcosa.
    SELECT l.ambito INTO v_ambito
      FROM config.email_log l
     WHERE l.id = p_email_log_id;

    IF NOT FOUND THEN
        -- ⭐ CODICE PROPRIO, di classe TECNICO. Non e'
        --   E_VALIDAZIONE (DATO_ERRATO, «hai sbagliato i dati»):
        --   questo id non arriva da una persona, e' quello che il
        --   chiamante ha scritto un istante prima.
        -- ⛔ E non e' NON_TROVATO, che porta un 404: qui non c'e'
        --   nessuno che cerca una risorsa, c'e' del codice che
        --   passa un valore inesistente.
        PERFORM script.fn_log_and_raise_error(
            'config', 'fn_chiudi_email_sistema', 'E_EMAIL_LOG_INESISTENTE',
            jsonb_build_object('email_log_id', p_email_log_id),
            NULL::uuid,
            p_email_log_id::text);
    END IF;

    -- ⛔ IL CASO PERICOLOSO, e per questo ha un codice suo:
    --   qualcuno sta usando la porta di sistema per una email che
    --   appartiene a un'azienda. Dirlo con lo stesso codice del
    --   caso sopra avrebbe sprecato l'unico momento in cui si puo'
    --   notare — «la riga non c'e'» e «la riga c'e' e non e' tua»
    --   mandano a guardare due posti diversi.
    -- ⭐ TECNICO, non DATO_ERRATO: i parametri sono a posto e la
    --   riga esiste. Non c'e' nessun dato da correggere, c'e' un
    --   chiamante che ha bussato alla porta sbagliata.
    -- ⚠️ Fino al 2026-09-07 era `E_VALIDAZIONE`: 20260906-14 lo
    --   aveva dichiarato domanda aperta, e il classificatore non
    --   sapeva ancora leggere questa forma di guardia.
    IF v_ambito <> 'SISTEMA' THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'fn_chiudi_email_sistema', 'E_EMAIL_LOG_NON_DI_SISTEMA',
            jsonb_build_object('email_log_id', p_email_log_id,
                               'ambito', v_ambito),
            NULL::uuid,
            p_email_log_id::text, v_ambito::text);
    END IF;

    -- ⚠️ `tentativi + 1` come faceva update_log_stato: instradare
    --   dev'essere un cambio di indirizzo, non di comportamento.
    -- ⭐ E il COALESCE su `inviato_at` e' cio' che rende `SIMULATA`
    --   scrivibile senza toccare niente: passando NULL la colonna
    --   resta com'era, cioe' vuota su una riga appena accodata.
    UPDATE config.email_log l
       SET stato      = p_stato,
           errore     = p_errore,
           inviato_at = COALESCE(p_inviato_at, l.inviato_at),
           tentativi  = l.tentativi + 1
     WHERE l.id     = p_email_log_id
       AND l.ambito = 'SISTEMA';

    RETURN true;
END
$function$

COMMENT ON FUNCTION config.fn_chiudi_email_sistema(p_email_log_id bigint, p_stato character varying, p_errore text, p_inviato_at timestamp with time zone)
IS 'Scrive l''ESITO dell''invio (SENT / FAILED / RETRY / SIMULATA, errore, inviato_at, tentativi+1) su una riga di ambito SISTEMA, dal percorso che NON ha un utente in sessione. ⭐ E'' la meta'' mancante di config.fn_accoda_email_sistema: la decisione e'' che una mail di sistema parta SUBITO, quindi dopo l''INSERT il backend tenta l''invio e deve scriverne l''esito — e quell''UPDATE e'' bloccato dalla stessa policy, per lo stesso motivo. ⛔ Non e'' una porta di servizio: tocca SOLO righe di ambito SISTEMA (sta nella WHERE, non in un controllo dimenticabile) e SOLO i campi dell''esito. 🔵 LA WHITELIST DI p_stato E'' LA SECONDA SEDE DEL VOCABOLARIO DI email_log.stato, rev 2026-09-11, e l''invariante NON e'' l''uguaglianza col CHECK: e'' chk_email_log_stato MENO PENDING, perche'' questa funzione chiude e non rimette in coda. Chi aggiunge un valore al CHECK deve aggiungerlo anche qui, o quel valore resta irraggiungibile per le righe SISTEMA — che passano tutte da questa porta. Lo presidia db/pgtap/config/test-fn-email-sistema.sql test 9. ⭐ SIMULATA dice «l''invio non e'' stato tentato, di proposito» (ambiente senza SMTP, mail mostrata invece che spedita) ed e'' TERMINALE: il chiamante passa p_inviato_at => NULL, perche'' una riga che dichiara il non-invio non deve portare la data di una consegna. ⭐ LE TRE GUARDIE HANNO TRE CODICI, rev 2026-09-07, e ognuna manda a guardare un posto diverso. (1) p_stato fuori dai valori ammessi: E_VALIDAZIONE, ed e'' il codice giusto perche'' li'' c''e'' davvero un parametro fuori dai valori. (2) La riga non esiste: E_EMAIL_LOG_INESISTENTE, classe TECNICO — quell''id non arriva da una persona ma dal chiamante che l''ha scritto un istante prima, e NON_TROVATO porterebbe un 404 mandando a cercare una risorsa invece di un difetto di codice. (3) La riga esiste ma NON e'' di sistema: E_EMAIL_LOG_NON_DI_SISTEMA, anch''esso TECNICO — e'' qualcuno che usa la porta di sistema per l''email di un''azienda, ed e'' l''unico momento in cui lo si puo'' notare. ⚠️ tentativi+1 lo fa la funzione perche'' lo faceva update_log_stato: instradare dev''essere un cambio di indirizzo, non di comportamento — ed e'' anche cio'' che fa funzionare il recupero, perche'' send_pending_emails ripesca i FAILED finche'' tentativi < max_tentativi.';
```

</div>

---
{% include-markdown "signature-core.md" %}
