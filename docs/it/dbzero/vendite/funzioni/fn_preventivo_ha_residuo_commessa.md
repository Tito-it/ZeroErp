{% include-markdown "it/dbzero/vendite/manual/fn_preventivo_ha_residuo_commessa.md" %}
# ⚙️ Funzione `fn_preventivo_ha_residuo_commessa`

```sql
CREATE FUNCTION fn_preventivo_ha_residuo_commessa(p_preventivo_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

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
  --   pregresso) non ancora instradate in commessa: il push
  --   commessa avrebbe effetto.
  --   Funzione fn_*: puro boolean, no raise oltre il guard id.
  --
  --   rev 2026-10-10: via il requisito di «testata completa»
  --   (billing_account_id, utility_id): sono NOT NULL dal
  --   2026-10-08. Brief: brief-db-istanza-nasce-col-ba-residui.
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
     WHERE v.preventivo_id = p_preventivo_id
  );
END;
$function$

COMMENT ON FUNCTION vendite.fn_preventivo_ha_residuo_commessa(p_preventivo_id bigint)
IS 'TRUE se il preventivo ha righe natura COMMESSA (servizi; natura NULL = pregresso) non ancora mandate in commessa. Predicato condiviso (vista vw_preventivi_righe_smistabili_commessa, che dal 2026-10-12 lo legge da script.fn_get_stato_push_segment: una riga di commessa ANNULLATA non occupa). Lo leggono la capability can_push_commessa e la proiezione dello stato del preventivo (vendite.fn_preventivo_proietta_stato_smistamento: ACCETTATO <-> EVASO). Gemella di fn_preventivo_ha_residuo_ordine; non considera ORDINE (gestita da fn_push_preventivo_a_ordine). rev 2026-10-10 (20261010-51): via il requisito di testata completa (billing_account_id, utility_id NOT NULL), tautologico dal 2026-10-08. Brief: brief-db-istanza-nasce-col-ba-residui (R-2). rev 2026-10-12 (20261012-09): commento allineato al predicato del classificatore unico, brief-db-annullo-a-valle-riapre-a-monte (D-5).';
```

</div>

---
{% include-markdown "signature-core.md" %}
