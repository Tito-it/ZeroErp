{% include-markdown "it/dbzero/config/manual/trgfn_regioni_normalize.md" %}
# ⚙️ Funzione `trgfn_regioni_normalize`

```sql
CREATE FUNCTION trgfn_regioni_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.trgfn_regioni_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
 BEGIN
   ------------------------------------------------------------------
   -- 1) Imposta stato_id di default da config.stati se è NULL
   IF NEW.stato_id IS NULL THEN
     NEW.stato_id := script.fn_stato_proposto_id(TG_NAME);           -- cast al tipo integer di stato_id
   END IF;
   ------------------------------------------------------------------
   -- 2) Altri cleanup (esempi)
   --IF NEW.nome IS NOT NULL THEN
   --  NEW.nome := UPPER(TRIM(NEW.nome));
   --END IF;
   --IF NEW.cognome IS NOT NULL THEN
     --NEW.cognome := UPPER(TRIM(NEW.cognome));
  -- END IF;
   ------------------------------------------------------------------
   RETURN NEW;
 END;
 $function$

COMMENT ON FUNCTION config.trgfn_regioni_normalize()
IS 'Function che pulisce i campi di config.regioni e imposta i valori di default per le colonne che non hanno un valore specificato: stato_id dal BB script.fn_stato_proposto_id (rev 2026-10-18: prima state_code_iso3 con fn_get_default_by_param, ritirati; D-1 di Tid).';
```

---
{% include-markdown "signature-core.md" %}
