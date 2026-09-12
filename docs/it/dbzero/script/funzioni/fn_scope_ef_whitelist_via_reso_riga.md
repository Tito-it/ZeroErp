# ⚙️ Funzione `fn_scope_ef_whitelist_via_reso_riga`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_reso_riga(p_auth_user_id integer, p_riga_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_reso_riga(p_auth_user_id integer, p_riga_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: come sopra, ma partendo da una RIGA di reso — e' la
    --   chiave che portano accrediti, riconsegne e rinunce.
    -- ⛔ Si risale dal RESO, non dal DDT: la riga appartiene al
    --   documento di reso. `resi_righe` ha due genitori
    --   `NOT NULL` e questa e' la scelta, non una svista.
    SELECT script.fn_scope_ef_whitelist_via_reso(
        p_auth_user_id,
        (SELECT rr.reso_id
           FROM vendite.resi_righe rr
          WHERE rr.id = p_riga_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_reso_riga(p_auth_user_id integer, p_riga_id bigint)
IS 'Come fn_scope_ef_whitelist_via_reso ma a partire da una riga di reso: e'' la chiave che portano resi_righe_accrediti, resi_righe_riconsegne e resi_righe_rinunce. ⚠️ Risale dal RESO e non dal DDT: vendite.resi_righe ha due genitori NOT NULL (reso_id e ddt_riga_id) e la riga appartiene al documento di reso.';
```

---
{% include-markdown "signature-core.md" %}
