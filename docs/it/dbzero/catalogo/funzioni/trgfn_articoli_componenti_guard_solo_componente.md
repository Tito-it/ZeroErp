{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_componenti_guard_solo_componente.md" %}
# ⚙️ Funzione `trgfn_articoli_componenti_guard_solo_componente`

```sql
CREATE FUNCTION trgfn_articoli_componenti_guard_solo_componente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_componenti_guard_solo_componente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_prodotto_id catalogo.articoli.id%TYPE;
  v_is_solo_componente catalogo.articoli.is_solo_componente%TYPE;
BEGIN
  IF NOT (TG_OP = 'INSERT' OR TG_OP = 'UPDATE') THEN
    RETURN NEW;
  END IF;

  v_prodotto_id := NEW.prodotto_id;

  IF v_prodotto_id IS NULL THEN
    RETURN NEW;
  END IF;

  SELECT a.is_solo_componente
    INTO v_is_solo_componente
  FROM catalogo.articoli a
  WHERE a.id = v_prodotto_id;

  IF COALESCE(v_is_solo_componente, false) IS TRUE THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_ARTICOLO_SOLO_COMPONENTE',
      jsonb_build_object(
        'prodotto_id', v_prodotto_id,
        'table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_componenti_guard_solo_componente()
IS 'Blocca articoli marcati is_solo_componente come prodotto in distinta base.';
```

</div>

---
{% include-markdown "signature-core.md" %}
