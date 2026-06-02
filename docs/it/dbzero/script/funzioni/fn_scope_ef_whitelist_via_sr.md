{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_sr.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_sr`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_sr(p_auth_user_id integer, p_emittente_sr_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_sr(p_auth_user_id integer, p_emittente_sr_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Risolve SR -> emittente_fiscale_id (1:1 via soggetto_ruolo_id)
    -- e delega alla canonica. SR non mappato / emittente NULL ->
    -- la canonica con emittente_fiscale_id NULL ritorna false se la
    -- whitelist e' valorizzata (fail-closed), true se vuota/super_admin.
    SELECT script.fn_check_user_emittente_scope(
        p_auth_user_id,
        (SELECT ef.id
           FROM anagrafiche.emittenti_fiscali ef
          WHERE ef.soggetto_ruolo_id = p_emittente_sr_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_sr(p_auth_user_id integer, p_emittente_sr_id bigint)
IS 'Adapter SR dello scope EF_WHITELIST: risolve emittente_soggetto_ruolo_id -> emittente_fiscale_id e delega a script.fn_check_user_emittente_scope (canonica auth_user_id/PK). Per tabelle convenzione SR (fatture, fatturazione_lotti). STABLE, inlineable. Nessuna logica whitelist duplicata.';
```

---
{% include-markdown "signature-core.md" %}
