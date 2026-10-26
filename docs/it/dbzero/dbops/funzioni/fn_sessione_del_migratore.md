{% include-markdown "it/dbzero/dbops/manual/fn_sessione_del_migratore.md" %}
# ⚙️ Funzione `fn_sessione_del_migratore`

```sql
CREATE FUNCTION fn_sessione_del_migratore()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_sessione_del_migratore()
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: dire se la sessione e' di chi amministra il database
    --   (il migratore o un superuser), letto dal ruolo di LOGIN.
    -- ⛔ session_user: dentro una DEFINER current_user e' il
    --    proprietario. Fail-closed: NULL vale false.
    SELECT COALESCE(
               pg_catalog.pg_has_role(
                   session_user,
                   (SELECT n.nspowner FROM pg_catalog.pg_namespace n WHERE n.nspname = 'dbops'),
                   'MEMBER')
            OR (SELECT a.rolsuper FROM pg_catalog.pg_roles a WHERE a.rolname = session_user),
               false);
$function$

COMMENT ON FUNCTION dbops.fn_sessione_del_migratore()
IS 'La sessione e'' di chi amministra il database? true se il ruolo di LOGIN (session_user) e'' membro del proprietario dello schema dbops — il migratore, in ogni ambiente — o un superuser. session_user e non current_user perche'' dentro una SECURITY DEFINER current_user e'' il proprietario; limite dichiarato: un SET ROLE non cambia session_user. Fail-closed (NULL = false), non solleva: rifiuta il chiamante. La chiamano dbops.fn_sync_functions_owner (RAISE nudo, canale di log protetto) e script.fn_totp_disabilita_device (lo sblocco del secondo fattore dal server). Estratta il 2026-09-29 (regola del 2). INVOKER, STABLE. Brief: brief-db-secondo-fattore-totp §3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
