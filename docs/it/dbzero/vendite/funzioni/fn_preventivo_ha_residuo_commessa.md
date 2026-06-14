{% include-markdown "it/dbzero/vendite/manual/fn_preventivo_ha_residuo_commessa.md" %}
# ⚙️ Funzione `fn_preventivo_ha_residuo_commessa`

```sql
CREATE FUNCTION fn_preventivo_ha_residuo_commessa(p_preventivo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_preventivo_ha_residuo_commessa(p_preventivo_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   TRUE se il preventivo ha righe natura COMMESSA (o NULL,
  --   pregresso) non ancora EMESSE in commessa E testata
  --   completa (billing_account_id, utility_id): il push
  --   commessa avrebbe effetto.
  --   Funzione fn_*: puro boolean, no raise oltre il guard id.
  -- =========================================================

  -- Guard standard parametro id.
  IF p_preventivo_id IS NULL OR p_preventivo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_preventivo_ha_residuo_commessa',
      'E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro', 'p_preventivo_id',
                         'valore', p_preventivo_id),
      NULL::uuid,
      'p_preventivo_id obbligatorio e > 0'
    );
  END IF;

  RETURN EXISTS (
    SELECT 1
      FROM vendite.vw_preventivi_righe_smistabili_commessa v
      JOIN vendite.preventivi p ON p.id = v.preventivo_id
     WHERE v.preventivo_id = p_preventivo_id
       -- Requisiti di testata del push commessa (fn_list):
       -- senza, il push non listerebbe nulla.
       AND p.billing_account_id IS NOT NULL
       AND p.utility_id IS NOT NULL
  );
END;
$function$

COMMENT ON FUNCTION vendite.fn_preventivo_ha_residuo_commessa(p_preventivo_id bigint)
IS 'TRUE se il preventivo ha righe natura COMMESSA (servizi; natura NULL = pregresso) non ancora EMESSE in commessa E testata completa (billing_account_id, utility_id NOT NULL). Predicato condiviso (vista vw_preventivi_righe_smistabili_commessa): capability can_push_commessa + gate EVASO lato BE. Gemella di fn_preventivo_ha_residuo_ordine; non considera ORDINE (gestita da fn_push_preventivo_a_ordine).';
```

---
{% include-markdown "signature-core.md" %}
