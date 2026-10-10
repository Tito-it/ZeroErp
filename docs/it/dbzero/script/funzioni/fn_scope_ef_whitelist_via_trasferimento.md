{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_trasferimento.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_trasferimento`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_trasferimento(p_auth_user_id integer, p_trasferimento_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_trasferimento(p_auth_user_id integer, p_trasferimento_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: perimetro di un trasferimento via il magazzino di ORIGINE.
    -- ⭐ Una sola risalita basta: il guard
    --   magazzino.trgfn_trasferimenti_guard_stesso_emittente garantisce
    --   che la destinazione sia dello stesso emittente (M-6).
    SELECT script.fn_scope_ef_whitelist_via_magazzino(
        p_auth_user_id,
        (SELECT t.magazzino_id_from
           FROM magazzino.trasferimenti t
          WHERE t.id = p_trasferimento_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_trasferimento(p_auth_user_id integer, p_trasferimento_id bigint)
IS 'Adattatore di scope per un trasferimento via il magazzino di ORIGINE (magazzino_id_from): una risalita basta perche'' trgfn_trasferimenti_guard_stesso_emittente garantisce che la destinazione sia dello stesso emittente (M-6). Chiave di trasferimenti_righe e delle note note_trasferimento e note_trasferimento_riga.';
```

---
{% include-markdown "signature-core.md" %}
