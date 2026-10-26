{% include-markdown "it/dbzero/script/manual/fn_credenziali.md" %}
# ⚙️ Funzione `fn_credenziali`

```sql
CREATE FUNCTION fn_credenziali()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_credenziali()
 RETURNS TABLE(auth_user_id integer, username text, email text, nome text, cognome text, is_active boolean, last_login timestamp with time zone)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- Tutte, senza filtro: anche le spente e quelle senza veste. Chi
    -- legge decide cosa mostrare (le viste dell'area Accessi le
    -- ripartiscono con script.fn_categoria_accesso).
    RETURN QUERY
    SELECT au.id,
           au.username::text,
           NULLIF(btrim(au.email), '')::text,
           NULLIF(btrim(au.first_name), '')::text,
           NULLIF(btrim(au.last_name), '')::text,
           au.is_active,
           au.last_login
      FROM django.auth_user au;
END;
$function$

COMMENT ON FUNCTION script.fn_credenziali()
IS 'L''elenco delle CREDENZIALI (django.auth_user), tutte: anche spente e senza alcuna veste. Colonne: auth_user_id, username, email, nome, cognome (stringhe vuote di Django rese NULL), is_active, last_login. Esiste perche'' una VISTA non puo'' nominare django.* (si risolve alla CREATE, e le tabelle di Django le crea manage.py migrate dopo Liquibase), mentre una funzione plpgsql e'' late-bound: le viste anagrafiche.vw_accessi_altri e vw_accessi_sistema passano da qui. Gemella per elenco di script.fn_get_auth_user_stato (una credenziale per id). Niente password ne'' flag di Django che il DB non governa. Brief: brief-db-be-fe-area-accessi (R-DB-A2).';
```

</div>

---
{% include-markdown "signature-core.md" %}
