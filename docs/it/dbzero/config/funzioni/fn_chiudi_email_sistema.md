# ⚙️ Funzione `fn_chiudi_email_sistema`

```sql
CREATE FUNCTION fn_chiudi_email_sistema(p_email_log_id bigint, p_stato character varying, p_errore text, p_inviato_at timestamp with time zone)
```

**Definizione completa:**

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
    -- =========================================================

    -- ⛔ `PENDING` non e' un esito: questa e' la funzione che
    --   CHIUDE, non quella che rimette in coda. Ammetterlo
    --   vorrebbe dire poter resuscitare una email gia' chiusa.
    -- ⚠️ Qui `E_VALIDAZIONE` e' il codice GIUSTO: e' la
    --   validazione di un parametro, la famiglia che quel codice
    --   copre da sempre.
    IF p_stato IS NULL OR p_stato NOT IN ('SENT', 'FAILED', 'RETRY') THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'fn_chiudi_email_sistema', 'E_VALIDAZIONE',
            jsonb_build_object('stato', p_stato,
                               'email_log_id', p_email_log_id),
            NULL::uuid,
            'stato ammesso solo fra SENT, FAILED e RETRY');
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

    -- ⛔ IL CASO PERICOLOSO, e per questo ha parole sue: qualcuno
    --   sta usando la porta di sistema per una email che
    --   appartiene a un'azienda. Dirlo con la stessa frase del
    --   caso sopra avrebbe sprecato l'unico momento in cui si
    --   puo' notare.
    IF v_ambito <> 'SISTEMA' THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'fn_chiudi_email_sistema', 'E_VALIDAZIONE',
            jsonb_build_object('email_log_id', p_email_log_id,
                               'ambito', v_ambito),
            NULL::uuid,
            'questa porta chiude solo le email di ambito SISTEMA: '
            'una email di un''azienda si chiude dalla sessione di '
            'chi ne ha il perimetro');
    END IF;

    -- ⚠️ `tentativi + 1` come faceva update_log_stato: instradare
    --   dev'essere un cambio di indirizzo, non di comportamento.
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
IS 'Scrive l''ESITO dell''invio (SENT / FAILED / RETRY, errore, inviato_at, tentativi+1) su una riga di ambito SISTEMA, dal percorso che NON ha un utente in sessione. ⭐ E'' la meta'' mancante di config.fn_accoda_email_sistema: la decisione e'' che una mail di sistema parta SUBITO, quindi dopo l''INSERT il backend tenta l''invio e deve scriverne l''esito — e quell''UPDATE e'' bloccato dalla stessa policy, per lo stesso motivo. ⛔ Non e'' una porta di servizio: tocca SOLO righe di ambito SISTEMA (sta nella WHERE, non in un controllo dimenticabile) e SOLO i campi dell''esito. ⛔ PENDING non e'' un esito ammesso: questa chiude, non rimette in coda. ⚠️ Se la riga non esiste solleva E_EMAIL_LOG_INESISTENTE, classe TECNICO — rev 2026-09-06, su segnalazione del classificatore dei codici: prima era E_VALIDAZIONE, che e'' DATO_ERRATO e a video diventa «hai sbagliato i dati», mentre quell''id non arriva da una persona ma dal chiamante che l''ha scritto un istante prima. ⭐ E non NON_TROVATO, che porta un 404: qui nessuno cerca una risorsa, e'' del codice che passa un valore inesistente. Se invece la riga esiste e NON e'' di sistema, il messaggio e'' un altro: e'' qualcuno che usa la porta di sistema per una email di un''azienda, ed e'' l''unico momento in cui lo si puo'' notare. ⚠️ tentativi+1 lo fa la funzione perche'' lo faceva update_log_stato: instradare dev''essere un cambio di indirizzo, non di comportamento.';
```

---
{% include-markdown "signature-core.md" %}
