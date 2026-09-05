# ⚙️ Funzione `fn_accoda_email_sistema`

```sql
CREATE FUNCTION fn_accoda_email_sistema(p_destinatario character varying, p_oggetto text, p_corpo_html text, p_corpo_testo text, p_email_account_id integer, p_email_template_id integer, p_auth_user_id integer, p_contesto_json jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.fn_accoda_email_sistema(p_destinatario character varying, p_oggetto text, p_corpo_html text, p_corpo_testo text DEFAULT NULL::text, p_email_account_id integer DEFAULT NULL::integer, p_email_template_id integer DEFAULT NULL::integer, p_auth_user_id integer DEFAULT NULL::integer, p_contesto_json jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_id config.email_log.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Accodare una email di SISTEMA — reset password, alert —
    --   da un percorso che NON ha un utente in sessione.
    --
    -- ⛔ `ambito` NON e' un parametro, ed e' il punto: se lo
    --   fosse, questa sarebbe una porta per scrivere qualunque
    --   email aggirando la policy. Sa scrivere una cosa sola.
    -- ⛔ Nemmeno `emittente_fiscale_id`: un'email di sistema non
    --   appartiene a nessuna azienda, per definizione.
    -- =========================================================

    -- ⚠️ Un destinatario vuoto qui non e' un caso di frontiera: e'
    --   una email che non partira' mai e che nessuno colleghera' a
    --   niente. Si rifiuta subito, con un nome.
    IF p_destinatario IS NULL OR btrim(p_destinatario) = '' THEN
        -- ⚠️ Cinque argomenti fissi PIU' almeno un valore
        --   variadico: il messaggio a catalogo e' «Validazione
        --   fallita: %s» e senza il valore format() non avrebbe
        --   niente da mettere. Fermarsi a quattro non risolve
        --   nemmeno la funzione.
        PERFORM script.fn_log_and_raise_error(
            'config', 'fn_accoda_email_sistema', 'E_VALIDAZIONE',
            jsonb_build_object('oggetto', p_oggetto),
            NULL::uuid,
            'destinatario obbligatorio per una email di sistema');
    END IF;

    INSERT INTO config.email_log
        (email_account_id, email_template_id, destinatario,
         oggetto, corpo_inviato_html, corpo_inviato_testo,
         stato, ambito, emittente_fiscale_id,
         auth_user_id, contesto_json)
    VALUES (p_email_account_id, p_email_template_id, p_destinatario,
            p_oggetto, p_corpo_html, p_corpo_testo,
            'PENDING', 'SISTEMA', NULL,
            p_auth_user_id, COALESCE(p_contesto_json, '{}'::jsonb))
    RETURNING id INTO v_id;

    RETURN v_id;
END
$function$

COMMENT ON FUNCTION config.fn_accoda_email_sistema(p_destinatario character varying, p_oggetto text, p_corpo_html text, p_corpo_testo text, p_email_account_id integer, p_email_template_id integer, p_auth_user_id integer, p_contesto_json jsonb)
IS 'Accoda una email di ambito SISTEMA (reset password, alert) da un percorso NON autenticato. ⭐ Esiste perche'' PasswordResetRequestView e PasswordResetConfirmView girano con AllowAny e authentication_classes = []: in quelle richieste le GUC app.current_user_id e app.ruolo_applicativo NON esistono, e con la row level security accesa su config.email_log l''INSERT verrebbe respinto dal gate OPERATORE della policy — cioe'' il reset password si romperebbe, che e'' proprio la ragione per cui le email di SISTEMA esistono. ⛔ La strada scartata era far passare nella policy anche «nessun utente in sessione»: sarebbe riaprire la porta chiusa dalla fase 6, dove bastava NON impostare una GUC per scrivere senza dire chi si e''. ⛔ `ambito` NON e'' un parametro, e nemmeno l''emittente: se lo fossero questa sarebbe una porta per scrivere QUALUNQUE email aggirando la policy. Sa scrivere una cosa sola. ⚠️ SECURITY DEFINER del proprietario della tabella e non di un superuser: la RLS e'' ENABLE senza FORCE, quindi l''owner non la subisce — nessun privilegio speciale, nessun canale separato. ⚠️ Al backend: nei due password_reset_views l''INSERT diretto diventa una chiamata a questa funzione.';
```

---
{% include-markdown "signature-core.md" %}
