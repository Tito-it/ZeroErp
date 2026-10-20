{% include-markdown "it/dbzero/vendite/manual/fn_preventivo_ha_residuo_ordine.md" %}
# ⚙️ Funzione `fn_preventivo_ha_residuo_ordine`

```sql
CREATE FUNCTION fn_preventivo_ha_residuo_ordine(p_preventivo_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_preventivo_ha_residuo_ordine(p_preventivo_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Residuo MERCE: delega alla vista-predicato unica
    -- (DB-first). Nessun predicato duplicato qui.
    SELECT EXISTS (
        SELECT 1
          FROM vendite.vw_preventivi_righe_smistabili_ordine v
         WHERE v.preventivo_id = p_preventivo_id
    );
$function$

COMMENT ON FUNCTION vendite.fn_preventivo_ha_residuo_ordine(p_preventivo_id bigint)
IS 'TRUE se il preventivo ha righe natura ORDINE (merce) non ancora allocate a un ordine. Predicato condiviso (vista vw_preventivi_righe_smistabili_ordine): capability can_genera_ordine + gate stato EVASO (D6, brief-preventivi-ordini.md). Non considera COMMESSA (gestita da push_a_commessa) ne CONTRATTO (non ammesso sul preventivo).';
```

</div>

---
{% include-markdown "signature-core.md" %}
