{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_movimento.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_movimento`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_movimento(p_auth_user_id integer, p_movimento_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_movimento(p_auth_user_id integer, p_movimento_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: perimetro di un movimento del registro, via il suo magazzino.
    --   E' la chiave che porta magazzino.note_movimento.
    SELECT script.fn_scope_ef_whitelist_via_magazzino(
        p_auth_user_id,
        (SELECT mv.magazzino_id
           FROM magazzino.movimenti mv
          WHERE mv.id = p_movimento_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_movimento(p_auth_user_id integer, p_movimento_id bigint)
IS 'Adattatore di scope per una riga del registro (magazzino.movimenti) via il suo magazzino: delega a fn_scope_ef_whitelist_via_magazzino. E'' la chiave di note_movimento.';
```

---
{% include-markdown "signature-core.md" %}
