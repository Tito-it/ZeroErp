# ⚙️ Funzione `trgfn_emittenti_fiscali_guard_utilities_required`

```sql
CREATE FUNCTION trgfn_emittenti_fiscali_guard_utilities_required()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_utilities_required()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  IF TG_TABLE_NAME = 'emittenti_fiscali' THEN
    IF TG_OP <> 'DELETE' THEN
      PERFORM anagrafiche.fn_guard_emittente_fiscale_utilities_required(
        NEW.soggetto_ruolo_id,
        concat(TG_TABLE_NAME, ':', TG_OP)
      );
    END IF;
  ELSIF TG_TABLE_NAME = 'emittenti_fiscali_utilities' THEN
    PERFORM anagrafiche.fn_guard_emittente_fiscale_utilities_required(
      COALESCE(NEW.emittente_soggetto_ruolo_id, OLD.emittente_soggetto_ruolo_id),
      concat(TG_TABLE_NAME, ':', TG_OP, ':current')
    );

    IF TG_OP = 'UPDATE'
       AND OLD.emittente_soggetto_ruolo_id IS DISTINCT FROM NEW.emittente_soggetto_ruolo_id THEN
      PERFORM anagrafiche.fn_guard_emittente_fiscale_utilities_required(
        OLD.emittente_soggetto_ruolo_id,
        concat(TG_TABLE_NAME, ':', TG_OP, ':old')
      );
    END IF;
  END IF;

  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_utilities_required()
IS 'Constraint trigger wrapper: garantisce che un emittente fiscale attivo abbia almeno una utility attiva configurata.';
```

---
{% include-markdown "signature-core.md" %}
