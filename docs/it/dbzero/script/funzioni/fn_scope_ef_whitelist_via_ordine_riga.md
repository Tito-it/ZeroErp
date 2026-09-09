# ⚙️ Funzione `fn_scope_ef_whitelist_via_ordine_riga`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_ordine_riga(p_auth_user_id integer, p_riga_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_ordine_riga(p_auth_user_id integer, p_riga_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    SELECT script.fn_scope_ef_whitelist_via_ordine(
        p_auth_user_id,
        (SELECT r.ordine_id
           FROM vendite.ordini_righe r WHERE r.id = p_riga_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_ordine_riga(p_auth_user_id integer, p_riga_id bigint)
IS 'Come fn_scope_ef_whitelist_via_ordine ma a partire da una riga d''ordine: e'' la chiave che portano ordini_righe_componenti e ordini_righe_fulfillment. Delega alla sorella invece di ripetere la risalita.';
```

---
{% include-markdown "signature-core.md" %}
