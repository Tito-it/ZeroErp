{% include-markdown "it/dbzero/config/manual/fn_resolve_email_account.md" %}
# ⚙️ Funzione `fn_resolve_email_account`

```sql
CREATE FUNCTION fn_resolve_email_account(p_unita_organizzativa_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.fn_resolve_email_account(p_unita_organizzativa_id integer DEFAULT NULL::integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_result jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Risolve l'account SMTP da usare per l'invio email.
    --   Catena di fallback:
    --     1. Account specifico del reparto (unita_organizzativa_id)
    --     2. Account di sistema (codice = 'SISTEMA')
    --
    -- Parametri:
    --   p_unita_organizzativa_id: ID reparto (NULL = usa diretto SISTEMA)
    --
    -- Restituisce:
    --   JSONB con: id, codice, smtp_host, smtp_port, smtp_use_tls,
    --   smtp_use_ssl, smtp_username, smtp_password_encrypted,
    --   email_from, email_reply_to.
    --   NULL se nessun account attivo trovato.
    -- =========================================================

    -- 1. Tentativo: account specifico del reparto
    IF p_unita_organizzativa_id IS NOT NULL THEN
        SELECT jsonb_build_object(
            'id',                      ea.id,
            'codice',                  ea.codice,
            'smtp_host',               ea.smtp_host,
            'smtp_port',               ea.smtp_port,
            'smtp_use_tls',            ea.smtp_use_tls,
            'smtp_use_ssl',            ea.smtp_use_ssl,
            'smtp_username',           ea.smtp_username,
            'smtp_password_encrypted', ea.smtp_password_encrypted,
            'email_from',              ea.email_from,
            'email_reply_to',          ea.email_reply_to
        )
        INTO v_result
        FROM config.email_account ea
        WHERE ea.unita_organizzativa_id = p_unita_organizzativa_id
          AND ea.attivo = true
        ORDER BY ea.id
        LIMIT 1;

        IF v_result IS NOT NULL THEN
            RETURN v_result;
        END IF;
    END IF;

    -- 2. Fallback: account di sistema
    SELECT jsonb_build_object(
        'id',                      ea.id,
        'codice',                  ea.codice,
        'smtp_host',               ea.smtp_host,
        'smtp_port',               ea.smtp_port,
        'smtp_use_tls',            ea.smtp_use_tls,
        'smtp_use_ssl',            ea.smtp_use_ssl,
        'smtp_username',           ea.smtp_username,
        'smtp_password_encrypted', ea.smtp_password_encrypted,
        'email_from',              ea.email_from,
        'email_reply_to',          ea.email_reply_to
    )
    INTO v_result
    FROM config.email_account ea
    WHERE ea.codice = 'SISTEMA'
      AND ea.attivo = true;

    RETURN v_result;
END;
$function$

COMMENT ON FUNCTION config.fn_resolve_email_account(p_unita_organizzativa_id integer)
IS 'Risolve account SMTP per invio email. Fallback: reparto -> SISTEMA. Ritorna JSONB con dati account (inclusa password crittografata).';
```

---
{% include-markdown "signature-core.md" %}
