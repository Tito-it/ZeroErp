{% include-markdown "it/dbzero/config/manual/trgfn_regioni_ins_upd_clean_fields.md" %}
# ⚙️ Funzione `trgfn_regioni_ins_upd_clean_fields`

```sql
CREATE FUNCTION trgfn_regioni_ins_upd_clean_fields()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.trgfn_regioni_ins_upd_clean_fields()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
 BEGIN
   ------------------------------------------------------------------
   -- 1) Imposta stato_id di default da config.stati se è NULL
   IF NEW.stato_id IS NULL THEN
     NEW.stato_id := script.fn_get_default_by_param(
       'config',           -- schema della tabella lookup
       'stati',            -- tabella di lookup
       'codice_iso3',        -- colonna di filtro in config.stati
       'state_code_iso3',  -- codice parametro in config.parameters
       TG_NAME             -- nome del trigger chiamante
     )::integer;           -- cast al tipo integer di stato_id
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
```

---
{% include-markdown "signature-core.md" %}
