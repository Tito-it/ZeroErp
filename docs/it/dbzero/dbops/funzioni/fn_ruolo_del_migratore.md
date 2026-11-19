# ⚙️ Funzione `fn_ruolo_del_migratore`

```sql
CREATE FUNCTION fn_ruolo_del_migratore(p_ruolo text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_ruolo_del_migratore(p_ruolo text)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: dire se un nome e' un ruolo di chi amministra il
    --   database: membro del proprietario dello schema dbops (il
    --   migratore, in ogni ambiente) o superuser.
    -- ⛔ Il nome si cerca in pg_roles, non si passa a pg_has_role:
    --    su un nome che non e' un ruolo pg_has_role solleva.
    -- Fail-closed: NULL, o un nome che non e' un ruolo, vale false.
    SELECT COALESCE(
               (SELECT pg_catalog.pg_has_role(r.oid, n.nspowner, 'MEMBER') OR r.rolsuper
                  FROM pg_catalog.pg_roles r
                 CROSS JOIN pg_catalog.pg_namespace n
                 WHERE r.rolname = p_ruolo
                   AND n.nspname = 'dbops'),
               false);
$function$

COMMENT ON FUNCTION dbops.fn_ruolo_del_migratore(p_ruolo text)
IS 'Un nome e'' un ruolo di chi amministra il database? true se e'' un ruolo membro del proprietario dello schema dbops (il migratore, in ogni ambiente) o un superuser. Il nome si cerca in pg_roles: uno username dell''applicazione, NULL o un ruolo che non esiste valgono false, senza errore. La chiamano dbops.fn_sessione_del_migratore (su session_user) e il runner del seed di primo impianto (su user_insert, quando iscrive una tabella). INVOKER, STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
