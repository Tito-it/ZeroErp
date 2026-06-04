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
  --   Normalizzazione campi ordine su INSERT.
  --
  -- Regole:
  --   1. Imposta anno/data se numero presente e valori mancanti.
  --   2. Eredita fatturazione_trigger da billing_account.fatturazione_ordini
  --      SOLO su INSERT.
  --
  -- Nota (DB-ORD-LOCK 2026-06-04): billing_account_id e'
  --   immutabile su UPDATE (automation_lock_columns ->
  --   script.trgfn_lock_columns, codice E_ORD_CLIENTE_IMMUTABILE).
  --   Non esiste piu' un "cambio BA su UPDATE" da propagare, quindi
  --   il vecchio ramo UPDATE e' stato rimosso (era irraggiungibile:
  --   il lock in fase a10 scatta prima di questo trigger).
  -- =========================================================

  IF TG_OP = 'INSERT' THEN
    ----------------------------------------------------------------
    -- 1. Imposta anno/data se numero e' presente e anno/data mancanti
    IF NEW.numero IS NOT NULL AND btrim(NEW.numero) <> '' THEN
      IF NEW.anno IS NULL OR NEW.anno = 0 THEN
        NEW.anno := EXTRACT(YEAR FROM CURRENT_DATE)::smallint;
      END IF;
      IF NEW.data IS NULL THEN
        NEW.data := CURRENT_DATE;
      END IF;
    END IF;

    ----------------------------------------------------------------
    -- 2. Eredita fatturazione_trigger da billing_account (solo INSERT)
    IF NEW.billing_account_id IS NOT NULL THEN
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
IS 'Normalize: imposta anno/data se numero presente ed eredita fatturazione_trigger da billing_account.fatturazione_ordini, entrambe SOLO su INSERT. Il cambio BA su UPDATE non e'' piu'' supportato (billing_account_id immutabile - DB-ORD-LOCK).';
```

---
{% include-markdown "signature-core.md" %}
