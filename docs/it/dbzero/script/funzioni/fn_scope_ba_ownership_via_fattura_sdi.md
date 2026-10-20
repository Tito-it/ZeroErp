# ⚙️ Funzione `fn_scope_ba_ownership_via_fattura_sdi`

```sql
CREATE FUNCTION fn_scope_ba_ownership_via_fattura_sdi(p_identita_id bigint, p_sdi_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ba_ownership_via_fattura_sdi(p_identita_id bigint, p_sdi_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: veste CLIENTE_PORTALE per gli eventi SDI.
    -- ⚠️ Esiste perche' i satelliti devono rispecchiare TUTTE le
    --   vesti della testata: `vendite.fatture` ne ha due.
    SELECT script.fn_scope_ba_ownership_via_fattura(
        p_identita_id,
        (SELECT s.fattura_id
           FROM vendite.fatture_sdi s
          WHERE s.id = p_sdi_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ba_ownership_via_fattura_sdi(p_identita_id bigint, p_sdi_id bigint)
IS 'Come fn_scope_ef_whitelist_via_fattura_sdi ma per la veste CLIENTE_PORTALE. ⚠️ Esiste perche'' vendite.fatture ha DUE vesti e ogni satellite le rispecchia entrambe: con la sola veste operatore un cliente del portale smetterebbe di vedere gli eventi SDI delle proprie fatture.';
```

</div>

---
{% include-markdown "signature-core.md" %}
