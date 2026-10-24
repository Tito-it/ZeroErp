{% include-markdown "it/dbzero/dbops/manual/fn_set_gucs_conn.md" %}
# ⚙️ Funzione `fn_set_gucs_conn`

```sql
CREATE FUNCTION fn_set_gucs_conn(p_user_id integer, p_session_key text, p_group_ids integer[])
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_set_gucs_conn(p_user_id integer DEFAULT NULL::integer, p_session_key text DEFAULT NULL::text, p_group_ids integer[] DEFAULT NULL::integer[])
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
    PERFORM set_config('app.user_id', p_user_id::text, false);
    PERFORM set_config('app.session_key', p_session_key, false);
    PERFORM set_config('app.group_ids', array_to_string(p_group_ids, ','), false);
END;
$function$

COMMENT ON FUNCTION dbops.fn_set_gucs_conn(p_user_id integer, p_session_key text, p_group_ids integer[])
IS 'Imposta le GUC app.* per audit, RLS e override parametri (user_id, session_key, group_ids).';
```

</div>

---
{% include-markdown "signature-core.md" %}
