# ⚙️ Funzione `trgfn_regioni_guard_sigla_province`

```sql
CREATE FUNCTION trgfn_regioni_guard_sigla_province()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_regioni_guard_sigla_province()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_sigla        config.province.sigla%TYPE;
  v_descrizione  config.province.descrizione%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Una regione che cambia stato porta con se' le sue
  --   province: se una di loro ha una sigla che il nuovo stato
  --   non ammette, il cambio si rifiuta e la frase nomina la
  --   prima (in ordine di sigla). Montato AFTER UPDATE WHEN
  --   stato_id cambia: vede lo stato finale, anche quello che
  --   trg_regioni_normalize_ins_upd mette al posto di un NULL.
  -- =========================================================
  IF NEW.stato_id IS NOT DISTINCT FROM OLD.stato_id THEN
    RETURN NEW;
  END IF;

  SELECT p.sigla, p.descrizione INTO v_sigla, v_descrizione
    FROM config.province p
   WHERE p.regione_id = NEW.id
     AND NOT config.fn_sigla_provincia_ammessa(p.sigla, NEW.stato_id)
   ORDER BY p.sigla, p.id
   LIMIT 1;

  IF FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'config', 'trgfn_regioni_guard_sigla_province', 'E_PROVINCIA_SIGLA_NON_VALIDA',
      jsonb_build_object('regione_id', NEW.id,
                         'stato_id',   NEW.stato_id,
                         'campo',      'stato_id'),
      NULL::uuid,
      v_sigla,
      v_descrizione);
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_regioni_guard_sigla_province()
IS 'Guard AFTER UPDATE (WHEN stato_id cambia) su config.regioni: una regione non cambia stato se una sua provincia ha una sigla che il nuovo stato non ammette (config.fn_sigla_provincia_ammessa). E_PROVINCIA_SIGLA_NON_VALIDA. Brief: brief-db-character-n-spazi-di-riempimento D-2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
