{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_inventario.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_inventario`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_inventario(p_auth_user_id integer, p_inventario_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_inventario(p_auth_user_id integer, p_inventario_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: perimetro di un inventario via il suo magazzino. E' la chiave
    --   che portano inventari_righe (inventario_id) e le note
    --   note_inventario / note_inventario_riga (target_id = la testata).
    SELECT script.fn_scope_ef_whitelist_via_magazzino(
        p_auth_user_id,
        (SELECT i.magazzino_id
           FROM magazzino.inventari i
          WHERE i.id = p_inventario_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_inventario(p_auth_user_id integer, p_inventario_id bigint)
IS 'Adattatore di scope per un inventario via il suo magazzino (delega a via_magazzino). Chiave di inventari_righe e delle note note_inventario e note_inventario_riga (dove target_id e'' la testata).';
```

---
{% include-markdown "signature-core.md" %}
