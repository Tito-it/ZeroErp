{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_rettifica.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_rettifica`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_rettifica(p_auth_user_id integer, p_rettifica_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_rettifica(p_auth_user_id integer, p_rettifica_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: perimetro di una rettifica via il suo magazzino. Chiave di
    --   rettifiche_righe e delle note note_rettifica / note_rettifica_riga.
    SELECT script.fn_scope_ef_whitelist_via_magazzino(
        p_auth_user_id,
        (SELECT r.magazzino_id
           FROM magazzino.rettifiche r
          WHERE r.id = p_rettifica_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_rettifica(p_auth_user_id integer, p_rettifica_id bigint)
IS 'Adattatore di scope per una rettifica via il suo magazzino (delega a via_magazzino). Chiave di rettifiche_righe e delle note note_rettifica e note_rettifica_riga.';
```

---
{% include-markdown "signature-core.md" %}
