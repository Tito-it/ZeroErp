# ⚙️ Funzione `trgfn_tipi_ruoli_guard_entita_ref`

```sql
CREATE FUNCTION trgfn_tipi_ruoli_guard_entita_ref()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.trgfn_tipi_ruoli_guard_entita_ref()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_colonna_codice  text;
  v_rel_oid         oid;
BEGIN
  -- Regola 1: coerenza NULL — se nessuna tabella, niente colonna
  IF NEW.entita_tabella IS NULL THEN
    IF NEW.entita_colonna_codice IS NOT NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        'config.trgfn_tipi_ruoli_guard_entita_ref',
        'E_PARAMETRO_INVALIDO',
        jsonb_build_object(
          'detail', 'entita_colonna_codice deve essere NULL se entita_tabella e'' NULL',
          'codice_interno', NEW.codice_interno,
          'entita_colonna_codice', NEW.entita_colonna_codice
        ),
        NULL::uuid,
        'entita_colonna_codice non NULL senza entita_tabella'
      );
    END IF;
    -- Niente da validare, passa
    RETURN NEW;
  END IF;

  -- Regola 2: entita_tabella deve essere un regclass valido
  v_rel_oid := to_regclass(NEW.entita_tabella);

  IF v_rel_oid IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'config.trgfn_tipi_ruoli_guard_entita_ref',
      'E_GENERICO',
      jsonb_build_object(
        'detail', 'entita_tabella non e'' una tabella/vista valida',
        'codice_interno', NEW.codice_interno,
        'entita_tabella', NEW.entita_tabella
      ),
      NULL::uuid,
      concat('entita_tabella=', NEW.entita_tabella, ' non trovata')
    );
  END IF;

  -- Regola 3: la tabella/vista deve avere soggetto_ruolo_id
  -- Usa pg_attribute (non dipende da search_path)
  IF NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_attribute a
    WHERE a.attrelid = v_rel_oid
      AND a.attname  = 'soggetto_ruolo_id'
      AND a.attnum   > 0
      AND NOT a.attisdropped
  ) THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'config.trgfn_tipi_ruoli_guard_entita_ref',
      'E_GENERICO',
      jsonb_build_object(
        'detail', 'entita_tabella non ha colonna soggetto_ruolo_id',
        'codice_interno', NEW.codice_interno,
        'entita_tabella', NEW.entita_tabella
      ),
      NULL::uuid,
      concat(NEW.entita_tabella, ' manca soggetto_ruolo_id')
    );
  END IF;

  -- Regola 4: colonna codice deve esistere
  v_colonna_codice := COALESCE(NEW.entita_colonna_codice, 'codice');

  IF NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_attribute a
    WHERE a.attrelid = v_rel_oid
      AND a.attname  = v_colonna_codice
      AND a.attnum   > 0
      AND NOT a.attisdropped
  ) THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'config.trgfn_tipi_ruoli_guard_entita_ref',
      'E_GENERICO',
      jsonb_build_object(
        'detail', 'colonna codice non trovata nella tabella entita''',
        'codice_interno', NEW.codice_interno,
        'entita_tabella', NEW.entita_tabella,
        'colonna_cercata', v_colonna_codice
      ),
      NULL::uuid,
      concat(NEW.entita_tabella, '.', v_colonna_codice, ' non trovata')
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_tipi_ruoli_guard_entita_ref()
IS 'Guard INSERT/UPDATE: valida entita_tabella (regclass + soggetto_ruolo_id) e entita_colonna_codice (colonna esistente). Coerenza NULL: se entita_tabella NULL, entita_colonna_codice deve essere NULL.';
```

---
{% include-markdown "signature-core.md" %}
