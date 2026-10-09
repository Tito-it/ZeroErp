{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_normalize.md" %}
# ⚙️ Funzione `trgfn_ddt_normalize`

```sql
CREATE FUNCTION trgfn_ddt_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo: normalizzazione DDT su INSERT/UPDATE.
  --   1. anno/data se numero presente (INSERT).
  --   2. eredita billing/utility/valuta/emittente dall'ordine
  --      sorgente (ORDINE_VENDITA, lookup per codice_interno) su
  --      INSERT se non gia' valorizzati.
  --   3. fallback emittente da billing_account (standalone).
  -- =========================================================

  -- 1. anno/data
  IF TG_OP = 'INSERT' AND (NEW.numero IS NOT NULL AND btrim(NEW.numero) <> '') THEN
    IF NEW.anno IS NULL OR NEW.anno = 0 THEN
      NEW.anno := EXTRACT(YEAR FROM script.fn_data_operativa())::smallint;
    END IF;
    IF NEW.data IS NULL THEN
      NEW.data := script.fn_data_operativa();
    END IF;
  END IF;

  -- 2. eredita billing/utility/valuta/emittente da ordine sorgente
  IF TG_OP = 'INSERT'
     AND NEW.sorgente_tipo_id IS NOT NULL
     AND NEW.sorgente_uid IS NOT NULL
     AND (NEW.billing_account_id IS NULL
          OR NEW.utility_id IS NULL
          OR NEW.valuta_id IS NULL
          OR NEW.emittente_fiscale_id IS NULL)
  THEN
    IF EXISTS (
      SELECT 1 FROM config.sorgenti
      WHERE id = NEW.sorgente_tipo_id AND codice_interno = 'ORDINE_VENDITA'
    ) THEN
      SELECT
        COALESCE(NEW.billing_account_id, o.billing_account_id),
        COALESCE(NEW.utility_id, ba.utility_id),
        COALESCE(NEW.valuta_id, o.valuta_id),
        COALESCE(NEW.emittente_fiscale_id, o.emittente_fiscale_id)
      INTO
        NEW.billing_account_id,
        NEW.utility_id,
        NEW.valuta_id,
        NEW.emittente_fiscale_id
      FROM vendite.ordini o
      LEFT JOIN anagrafiche.billing_account ba
        ON ba.id = o.billing_account_id
      WHERE o.uid = NEW.sorgente_uid
      LIMIT 1;
    END IF;
  END IF;

  -- 3. fallback standalone: emittente da billing_account (convenzione PK).
  IF TG_OP = 'INSERT'
     AND NEW.emittente_fiscale_id IS NULL
     AND NEW.billing_account_id IS NOT NULL
  THEN
    NEW.emittente_fiscale_id :=
      anagrafiche.fn_get_emittente_fiscale_pk(NEW.billing_account_id);
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_normalize()
IS 'Normalize DDT: anno/data; eredita billing/utility/valuta/emittente da ordine sorgente (ORDINE_VENDITA, per codice_interno) su INSERT; fallback emittente da billing_account (fn_get_emittente_fiscale_pk). rev 2026-07-10 (§15 emittente).';
```

---
{% include-markdown "signature-core.md" %}
