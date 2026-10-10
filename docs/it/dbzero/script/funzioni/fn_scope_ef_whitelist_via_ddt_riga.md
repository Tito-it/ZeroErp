# ⚙️ Funzione `fn_scope_ef_whitelist_via_ddt_riga`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_ddt_riga(p_auth_user_id integer, p_riga_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_ddt_riga(p_auth_user_id integer, p_riga_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: come sopra, ma partendo da una RIGA di DDT — e' la
    --   chiave che porta vendite.ddt_righe_componenti.
    -- ⭐ Delega alla sorella invece di ripetere la risalita: se un
    --   giorno cambia il modo in cui un DDT nomina il proprio
    --   emittente, si corregge in un posto solo.
    SELECT script.fn_scope_ef_whitelist_via_ddt(
        p_auth_user_id,
        (SELECT r.ddt_id
           FROM vendite.ddt_righe r
          WHERE r.id = p_riga_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_ddt_riga(p_auth_user_id integer, p_riga_id bigint)
IS 'Come fn_scope_ef_whitelist_via_ddt ma a partire da una riga di DDT: e'' la chiave che porta vendite.ddt_righe_componenti. Delega alla sorella invece di ripetere la risalita alla testata.';
```

---
{% include-markdown "signature-core.md" %}
