# ⚙️ Funzione `fn_accoda_email_sistema`

```sql
CREATE FUNCTION fn_accoda_email_sistema(p_destinatario character varying, p_oggetto text, p_corpo_html text, p_corpo_testo text, p_email_account_id integer, p_email_template_id integer, p_auth_user_id integer, p_contesto_json jsonb, p_unita_organizzativa_id integer, p_destinatari_cc text[], p_pratica_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_accoda_email_sistema(p_destinatario character varying, p_oggetto text, p_corpo_html text, p_corpo_testo text DEFAULT NULL::text, p_email_account_id integer DEFAULT NULL::integer, p_email_template_id integer DEFAULT NULL::integer, p_auth_user_id integer DEFAULT NULL::integer, p_contesto_json jsonb DEFAULT '{}'::jsonb, p_unita_organizzativa_id integer DEFAULT NULL::integer, p_destinatari_cc text[] DEFAULT NULL::text[], p_pratica_id bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_id config.email_log.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Accodare una email di SISTEMA — reset password, alert,
    --   inviti — da un percorso che NON ha un utente in sessione.
    --
    -- ⛔ `ambito` NON e' un parametro, e nemmeno l'emittente: se
    --   lo fossero questa sarebbe una porta per scrivere
    --   qualunque email aggirando la policy. Sa scrivere una cosa
    --   sola, ed e' tutto il suo valore.
    -- =========================================================

    -- ⚠️ Un destinatario vuoto non e' un caso di frontiera: e' una
    --   email che non partira' mai e che nessuno colleghera' a
    --   niente. Si rifiuta subito, con un nome.
    IF p_destinatario IS NULL OR btrim(p_destinatario) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'fn_accoda_email_sistema', 'E_VALIDAZIONE',
            jsonb_build_object('oggetto', p_oggetto),
            NULL::uuid,
            'destinatario obbligatorio per una email di sistema');
    END IF;

    INSERT INTO config.email_log
        (email_account_id, email_template_id, destinatario,
         destinatari_cc, oggetto, corpo_inviato_html,
         corpo_inviato_testo, stato, ambito, emittente_fiscale_id,
         unita_organizzativa_id, pratica_id,
         auth_user_id, contesto_json)
    VALUES (p_email_account_id, p_email_template_id, p_destinatario,
            p_destinatari_cc, p_oggetto, p_corpo_html,
            p_corpo_testo, 'PENDING', 'SISTEMA', NULL,
            p_unita_organizzativa_id, p_pratica_id,
            p_auth_user_id, COALESCE(p_contesto_json, '{}'::jsonb))
    RETURNING id INTO v_id;

    RETURN v_id;
END
$function$

COMMENT ON FUNCTION config.fn_accoda_email_sistema(p_destinatario character varying, p_oggetto text, p_corpo_html text, p_corpo_testo text, p_email_account_id integer, p_email_template_id integer, p_auth_user_id integer, p_contesto_json jsonb, p_unita_organizzativa_id integer, p_destinatari_cc text[], p_pratica_id bigint)
IS 'Accoda una email di ambito SISTEMA (reset password, alert, inviti) da un percorso NON autenticato. ⭐ Esiste perche'' i percorsi di reset e invito girano con AllowAny e authentication_classes = []: senza utente in sessione, con la row level security accesa su config.email_log l''INSERT verrebbe respinto — cioe'' il reset password si romperebbe, che e'' proprio la ragione per cui le email di SISTEMA esistono. ⛔ `ambito` NON e'' un parametro, e nemmeno l''emittente: se lo fossero questa sarebbe una porta per scrivere QUALUNQUE email aggirando la policy. Sa scrivere una cosa sola. ⭐ Rev 2026-09-06: accetta anche unita_organizzativa_id, destinatari_cc e pratica_id — i chiamanti li passavano e senza di essi quel dato sarebbe sparito IN SILENZIO, che e'' peggio di un rifiuto. Non sono perimetro ma CONTESTO: servono a chi legge il giornale, non a chi decide i permessi. ⚠️ SECURITY DEFINER del proprietario della tabella e non di un superuser: la RLS e'' ENABLE senza FORCE, quindi l''owner non la subisce. ⚠️ La gemella che CHIUDE la riga (esito dell''invio) e'' config.fn_chiudi_email_sistema: instradare solo l''INSERT sposterebbe la rottura sull''UPDATE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
