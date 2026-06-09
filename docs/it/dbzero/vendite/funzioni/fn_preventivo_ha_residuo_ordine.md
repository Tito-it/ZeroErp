# ⚙️ Funzione `fn_preventivo_ha_residuo_ordine`

```sql
CREATE FUNCTION fn_preventivo_ha_residuo_ordine(p_preventivo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_preventivo_ha_residuo_ordine(p_preventivo_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Residuo MERCE: riga attiva con natura destinazione ORDINE
    -- non ancora collegata a una riga d'ordine (idempotenza di riga).
    SELECT EXISTS (
        SELECT 1
          FROM vendite.preventivi_righe pr
          JOIN config.nature_vendita nv ON nv.id = pr.natura_vendita_id
         WHERE pr.preventivo_id = p_preventivo_id
           AND COALESCE(pr.attivo, TRUE) IS TRUE
           AND nv.destinazione_tipo = 'ORDINE'
           AND NOT EXISTS (
               SELECT 1 FROM vendite.ordini_righe orr
                WHERE orr.preventivo_riga_id = pr.id)
    );
$function$

COMMENT ON FUNCTION vendite.fn_preventivo_ha_residuo_ordine(p_preventivo_id bigint)
IS 'TRUE se il preventivo ha righe natura ORDINE (merce) non ancora allocate a un ordine. Predicato condiviso: capability can_genera_ordine + gate stato EVASO (D6, brief-preventivi-ordini.md). Non considera COMMESSA (gestita da push_a_commessa) ne CONTRATTO (non ammesso sul preventivo).';
```

---
{% include-markdown "signature-core.md" %}
