{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_listino.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_listino`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_listino(p_auth_user_id integer, p_listino_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_listino(p_auth_user_id integer, p_listino_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Risolve listino -> emittente_soggetto_ruolo_id e delega
    -- all'adapter SR. Listino inesistente -> SR NULL -> false
    -- (fail-closed se whitelist valorizzata).
    SELECT script.fn_scope_ef_whitelist_via_sr(
        p_auth_user_id,
        (SELECT l.emittente_soggetto_ruolo_id
           FROM vendite.listini l
          WHERE l.id = p_listino_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_listino(p_auth_user_id integer, p_listino_id bigint)
IS 'Adapter via-listino dello scope EF_WHITELIST: risolve l''emittente attraverso vendite.listini e delega a fn_scope_ef_whitelist_via_sr (-> canonica). Per le tabelle figlie del listino senza colonna emittente propria (vendite.listini_versioni). Gemello di fn_scope_ef_whitelist_via_fattura. STABLE, inlineable. Brief: brief-db-processi-automatici-residui-be §DB-4.';
```

---
{% include-markdown "signature-core.md" %}
