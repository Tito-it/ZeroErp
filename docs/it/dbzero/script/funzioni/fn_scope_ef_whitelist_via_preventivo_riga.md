# ⚙️ Funzione `fn_scope_ef_whitelist_via_preventivo_riga`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_preventivo_riga(p_auth_user_id integer, p_riga_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_preventivo_riga(p_auth_user_id integer, p_riga_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: come sopra, ma partendo da una RIGA di preventivo —
    --   e' la chiave che portano i componenti.
    -- ⭐ Delega alla sorella invece di ripetere la risalita: la
    --   regola «come un preventivo nomina il suo emittente» resta
    --   scritta in un posto solo.
    SELECT script.fn_scope_ef_whitelist_via_preventivo(
        p_auth_user_id,
        (SELECT r.preventivo_id
           FROM vendite.preventivi_righe r
          WHERE r.id = p_riga_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_preventivo_riga(p_auth_user_id integer, p_riga_id bigint)
IS 'Come fn_scope_ef_whitelist_via_preventivo ma a partire da una riga di preventivo: e'' la chiave che porta vendite.preventivi_righe_componenti. Delega alla sorella invece di ripetere la risalita alla testata.';
```

---
{% include-markdown "signature-core.md" %}
