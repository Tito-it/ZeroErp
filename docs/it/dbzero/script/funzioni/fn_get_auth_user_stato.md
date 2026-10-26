{% include-markdown "it/dbzero/script/manual/fn_get_auth_user_stato.md" %}
# ⚙️ Funzione `fn_get_auth_user_stato`

```sql
CREATE FUNCTION fn_get_auth_user_stato(p_auth_user_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_auth_user_stato(p_auth_user_id integer)
 RETURNS TABLE(username text, is_active boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- ⚠️ Nessun guard sul parametro, ed e' una scelta motivata:
    --   questa non e' una funzione applicativa chiamata da un
    --   form, e' la CHIAVE DI UN JOIN. Un id assente (utente
    --   cancellato) deve dare ZERO RIGHE — che in un INNER JOIN
    --   LATERAL fa sparire la riga, cioe' fail-closed. Sollevare
    --   fermerebbe la lettura del roster INTERO per una riga sola.
    RETURN QUERY
    SELECT au.username::text, au.is_active
      FROM django.auth_user au
     WHERE au.id = p_auth_user_id;
END;
$function$

COMMENT ON FUNCTION script.fn_get_auth_user_stato(p_auth_user_id integer)
IS 'Lo stato di un utente Django (username, is_active) per auth_user_id. ⭐ Esiste per una ragione sola e va detta: una VISTA si risolve alla CREATE, e le tabelle dello schema django le crea manage.py migrate — non Liquibase — quindi durante il migrate non esistono. Una funzione plpgsql invece e'' late-bound. ⇒ Il DB puo'' CHIAMARE dentro django.*, non puo'' DIPENDERNE strutturalmente (vista, FK, colonna generata): chi ha bisogno di auth_user dentro una vista passa da qui. ⚠️ Zero righe su id assente e'' la risposta giusta, non un errore: e'' la chiave di un join, e in un INNER JOIN LATERAL fa sparire la riga (fail-closed).';
```

</div>

---
{% include-markdown "signature-core.md" %}
