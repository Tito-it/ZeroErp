{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_normalize.md" %}
# ⚙️ Funzione `trgfn_soggetti_normalize`

```sql
CREATE FUNCTION trgfn_soggetti_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  ------------------------------------------------------------------
  -- 1) Imposta stato_id di default da config.stati se e' NULL
  IF NEW.stato_id IS NULL THEN
    NEW.stato_id := script.fn_get_default_by_param(
      'config',           -- schema della tabella lookup
      'stati',            -- tabella di lookup
      'codice_iso3',      -- colonna di filtro in config.stati
      'state_code_iso3',  -- codice parametro in config.parameters
      TG_NAME             -- nome del trigger chiamante
    )::integer;           -- cast al tipo integer di stato_id
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_normalize()
IS 'Normalize: imposta stato_id default; generazione codice demandata al sistema_codici.';
```

---
{% include-markdown "signature-core.md" %}
