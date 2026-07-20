{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_commessa.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_commessa`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_commessa(p_auth_user_id integer, p_commessa_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_commessa(p_auth_user_id integer, p_commessa_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Risolve commessa -> emittente_soggetto_ruolo_id e delega
    -- all'adapter SR. Commessa inesistente / emittente NULL -> SR
    -- NULL -> false (fail-closed se whitelist valorizzata).
    SELECT script.fn_scope_ef_whitelist_via_sr(
        p_auth_user_id,
        (SELECT c.emittente_soggetto_ruolo_id
           FROM vendite.commesse c
          WHERE c.id = p_commessa_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_commessa(p_auth_user_id integer, p_commessa_id bigint)
IS 'Adapter via-commessa dello scope EF_WHITELIST: risolve l''emittente attraverso vendite.commesse e delega a fn_scope_ef_whitelist_via_sr (-> canonica). Per tabelle figlie senza colonna emittente propria (es. vendite.commesse_attivita). STABLE, inlineable. Mirror di fn_scope_ef_whitelist_via_fattura. Brief: brief-db-rls-commesse.';
```

---
{% include-markdown "signature-core.md" %}
