{% include-markdown "it/dbzero/ui/manual/trgfn_ui_lista_colonna_a10_valida_campo_sorgente.md" %}
# ⚙️ Funzione `trgfn_ui_lista_colonna_a10_valida_campo_sorgente`

```sql
CREATE FUNCTION trgfn_ui_lista_colonna_a10_valida_campo_sorgente()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: verifica che campo_sorgente esista come attributo della view
-- referenziata da lista_definizione.vista_sql, prima di permettere
-- INSERT/UPDATE su lista_colonna.
-- Skip per:
--   - tipo_colonna='azione'           (nessun campo sorgente per disegno)
--   - campo_sorgente IS NULL o ''     (colonna calcolata FE, es. sosp_riatt)
--   - lista senza vista_sql definita
DECLARE
  v_vista_sql        VARCHAR(120);
  v_colonna_esiste   BOOLEAN;
BEGIN
  -- Le colonne di tipo 'azione' non hanno campo_sorgente
  IF NEW.tipo_colonna = 'azione' THEN
    RETURN NEW;
  END IF;

  -- Nessuna validazione se campo_sorgente non valorizzato
  -- (NULL = colonna calcolata; '' = equivalente nel seed CSV via loadUpdateData)
  IF NEW.campo_sorgente IS NULL OR NEW.campo_sorgente = '' THEN
    RETURN NEW;
  END IF;

  -- Recupera vista_sql dalla lista padre
  SELECT ld.vista_sql
    INTO v_vista_sql
    FROM ui.lista_definizione ld
   WHERE ld.id = NEW.lista_id;

  -- Se la lista non ha una view definita, skip
  IF v_vista_sql IS NULL THEN
    RETURN NEW;
  END IF;

  -- Verifica esistenza della colonna nella relazione
  SELECT EXISTS (
    SELECT 1
      FROM pg_catalog.pg_class c
      JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
      JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid
     WHERE c.relname = v_vista_sql
       AND c.relkind IN ('v', 'm', 'r')
       AND a.attname = NEW.campo_sorgente
       AND a.attnum > 0
       AND NOT a.attisdropped
  ) INTO v_colonna_esiste;

  IF NOT v_colonna_esiste THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente',
      'E_UI_CAMPO_SORGENTE_NON_TROVATO',
      jsonb_build_object(
        'detail', format('campo_sorgente = ''%s'' non trovato nella view ''%s''', NEW.campo_sorgente, v_vista_sql),
        'lista_id', NEW.lista_id,
        'codice', NEW.codice
      ),
      NULL,
      NEW.campo_sorgente,
      v_vista_sql
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente()
IS 'Guard INSERT/UPDATE: verifica esistenza di campo_sorgente in pg_catalog.pg_attribute sulla view della lista. Skip per tipo_colonna=azione o campo_sorgente NULL/vuoto (colonne calcolate FE).';
```

---
{% include-markdown "signature-core.md" %}
