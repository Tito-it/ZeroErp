{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_fattura.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_fattura`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_fattura(p_auth_user_id integer, p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_fattura(p_auth_user_id integer, p_fattura_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Risolve fattura -> emittente_soggetto_ruolo_id e delega
    -- all'adapter SR. Fattura inesistente -> SR NULL -> false
    -- (fail-closed se whitelist valorizzata).
    SELECT script.fn_scope_ef_whitelist_via_sr(
        p_auth_user_id,
        (SELECT f.emittente_soggetto_ruolo_id
           FROM vendite.fatture f
          WHERE f.id = p_fattura_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_fattura(p_auth_user_id integer, p_fattura_id bigint)
IS 'Adapter via-fattura dello scope EF_WHITELIST: risolve l''emittente attraverso vendite.fatture e delega a fn_scope_ef_whitelist_via_sr (-> canonica). Per tabelle figlie senza colonna emittente propria (es. vendite.fatture_scadenze). STABLE, inlineable.';
```

---
{% include-markdown "signature-core.md" %}
