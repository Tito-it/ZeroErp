{% include-markdown "it/dbzero/vendite/manual/trgfn_ordini_normalize.md" %}
# ⚙️ Funzione `trgfn_ordini_normalize`

```sql
CREATE FUNCTION trgfn_ordini_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ordini_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_fatturazione_ordini anagrafiche.billing_account.fatturazione_ordini%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Normalizzazione campi ordine su INSERT e UPDATE.
  --
  -- Regole:
  --   1. Imposta anno/data se numero presente e valori mancanti (INSERT).
  --   2. Eredita fatturazione_trigger da billing_account.fatturazione_ordini
  --      su INSERT, o su UPDATE se billing_account_id cambia.
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
  -- 2. Eredita fatturazione_trigger da billing_account
  --    - INSERT: sempre se billing_account_id e` valorizzato
  --    - UPDATE: solo se billing_account_id cambia
  IF NEW.billing_account_id IS NOT NULL THEN
    IF TG_OP = 'INSERT'
       OR (TG_OP = 'UPDATE'
           AND OLD.billing_account_id IS DISTINCT FROM NEW.billing_account_id)
    THEN
      SELECT ba.fatturazione_ordini
      INTO v_fatturazione_ordini
      FROM anagrafiche.billing_account ba
      WHERE ba.id = NEW.billing_account_id;

      IF v_fatturazione_ordini IS NOT NULL THEN
        NEW.fatturazione_trigger := v_fatturazione_ordini;
      END IF;
    END IF;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ordini_normalize()
IS 'Normalize: imposta anno/data se numero presente. Eredita fatturazione_trigger da billing_account.fatturazione_ordini su INSERT e su cambio billing_account_id.';
```

---
{% include-markdown "signature-core.md" %}
