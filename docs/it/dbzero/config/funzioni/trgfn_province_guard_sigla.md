# ⚙️ Funzione `trgfn_province_guard_sigla`

```sql
CREATE FUNCTION trgfn_province_guard_sigla()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_province_guard_sigla()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_stato_id  config.regioni.stato_id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Rifiuta una sigla che config.fn_sigla_provincia_ammessa
  --   non ammette per lo stato della regione della provincia.
  --   Montato BEFORE INSERT OR UPDATE OF sigla, regione_id.
  -- =========================================================
  IF TG_OP = 'UPDATE'
     AND NEW.sigla IS NOT DISTINCT FROM OLD.sigla
     AND NEW.regione_id IS NOT DISTINCT FROM OLD.regione_id THEN
    RETURN NEW;
  END IF;

  SELECT r.stato_id INTO v_stato_id
    FROM config.regioni r
   WHERE r.id = NEW.regione_id;

  IF NOT config.fn_sigla_provincia_ammessa(NEW.sigla, v_stato_id) THEN
    PERFORM script.fn_log_and_raise_error(
      'config', 'trgfn_province_guard_sigla', 'E_PROVINCIA_SIGLA_NON_VALIDA',
      jsonb_build_object('provincia_id', NEW.id,
                         'regione_id',   NEW.regione_id,
                         'stato_id',     v_stato_id,
                         'campo',        'sigla'),
      NULL::uuid,
      COALESCE(NEW.sigla, ''),
      NEW.descrizione);
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_province_guard_sigla()
IS 'Guard BEFORE INSERT OR UPDATE OF sigla, regione_id su config.province: la sigla deve essere ammessa da config.fn_sigla_provincia_ammessa per lo stato della regione (Italia: due lettere). E_PROVINCIA_SIGLA_NON_VALIDA. Brief: brief-db-character-n-spazi-di-riempimento D-2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
