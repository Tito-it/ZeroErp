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
  -- Scopo:
  --   Normalizzazione campi DDT su INSERT e UPDATE.
  --
  -- Regole:
  --   1. Imposta anno/data se numero presente e valori mancanti (INSERT).
  --   2. Eredita billing_account_id, utility_id, valuta_id dall'ordine
  --      sorgente (via sorgente_uid) se non gia` valorizzati (INSERT).
  -- =========================================================

  ----------------------------------------------------------------
  -- 1. Imposta anno/data se numero e' presente e anno/data mancanti
  IF TG_OP = 'INSERT' AND (NEW.numero IS NOT NULL AND btrim(NEW.numero) <> '') THEN
    IF NEW.anno IS NULL OR NEW.anno = 0 THEN
      NEW.anno := EXTRACT(YEAR FROM CURRENT_DATE)::smallint;
    END IF;
    IF NEW.data IS NULL THEN
      NEW.data := CURRENT_DATE;
    END IF;
  END IF;

  ----------------------------------------------------------------
  -- 2. Eredita billing fields da ordine sorgente (se DDT creato da ordine)
  --    sorgente_tipo_id punta a config.sorgenti; sorgente_uid = ordini.uid
  IF TG_OP = 'INSERT'
     AND NEW.sorgente_tipo_id IS NOT NULL
     AND NEW.sorgente_uid IS NOT NULL
     AND (NEW.billing_account_id IS NULL
          OR NEW.utility_id IS NULL
          OR NEW.valuta_id IS NULL)
  THEN
    -- Verifica che la sorgente sia ORDINE_VENDITA e eredita i campi mancanti.
    IF EXISTS (
      SELECT 1 FROM config.sorgenti
      WHERE id = NEW.sorgente_tipo_id AND codice = 'ORDINE_VENDITA'
    ) THEN
      SELECT
        COALESCE(NEW.billing_account_id, o.billing_account_id),
        COALESCE(NEW.utility_id, ba.utility_id),
        COALESCE(NEW.valuta_id, o.valuta_id)
      INTO
        NEW.billing_account_id,
        NEW.utility_id,
        NEW.valuta_id
      FROM vendite.ordini o
      LEFT JOIN anagrafiche.billing_account ba
        ON ba.id = o.billing_account_id
      WHERE o.uid = NEW.sorgente_uid
      LIMIT 1;
    END IF;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_normalize()
IS 'Normalize: imposta anno/data se numero presente. Eredita billing_account_id, utility_id, valuta_id da ordine sorgente (ORDINE_VENDITA) su INSERT se non gia` valorizzati.';
```

---
{% include-markdown "signature-core.md" %}
