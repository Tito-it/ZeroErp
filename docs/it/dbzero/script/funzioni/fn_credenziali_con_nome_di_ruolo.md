{% include-markdown "it/dbzero/script/manual/fn_credenziali_con_nome_di_ruolo.md" %}
# ⚙️ Funzione `fn_credenziali_con_nome_di_ruolo`

```sql
CREATE FUNCTION fn_credenziali_con_nome_di_ruolo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_credenziali_con_nome_di_ruolo()
 RETURNS TABLE(auth_user_id integer, username text)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- Scopo: le credenziali il cui username e' SEED o il nome di un
    --   ruolo del database (pg_roles), senza distinguere maiuscole e
    --   minuscole.
    RETURN QUERY
    SELECT au.id, au.username::text
      FROM django.auth_user au
     WHERE upper(au.username) = 'SEED'
        OR EXISTS (SELECT 1
                     FROM pg_catalog.pg_roles r
                    WHERE lower(r.rolname) = lower(au.username))
     ORDER BY au.id;
END;
$function$

COMMENT ON FUNCTION script.fn_credenziali_con_nome_di_ruolo()
IS 'Le credenziali dell''applicazione (django.auth_user) il cui username e'' SEED o il nome di un ruolo del database (pg_roles), senza distinguere maiuscole e minuscole. Accessore del motivo NOME_DI_RUOLO_DB di dbops.vw_credenziali_da_sanare: una credenziale cosi'', quando il runner del seed di primo impianto iscrive una tabella, fa sembrare nata dal seed una riga scritta da lei. plpgsql, cosi'' la vista non dipende dallo schema django alla creazione. INVOKER, STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
