# ⚙️ Funzione `fn_scope_ef_whitelist_via_contratto_riga`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_contratto_riga(p_auth_user_id integer, p_riga_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_contratto_riga(p_auth_user_id integer, p_riga_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: come sopra, ma partendo da una RIGA di contratto —
    --   e' la chiave che porta vendite.contratti_righe_componenti.
    -- ⭐ Delega alla sorella invece di ripetere la risalita: la
    --   regola «come un contratto nomina il proprio emittente»
    --   resta scritta in un posto solo.
    SELECT script.fn_scope_ef_whitelist_via_contratto(
        p_auth_user_id,
        (SELECT r.contratto_id
           FROM vendite.contratti_righe r
          WHERE r.id = p_riga_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_contratto_riga(p_auth_user_id integer, p_riga_id bigint)
IS 'Come fn_scope_ef_whitelist_via_contratto ma a partire da una riga di contratto: e'' la chiave che porta vendite.contratti_righe_componenti. Delega alla sorella invece di ripetere la risalita alla testata.';
```

---
{% include-markdown "signature-core.md" %}
