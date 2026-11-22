{% include-markdown "it/dbzero/ui/manual/trgfn_ui_lista_definizione_a10_valida_vista_sql.md" %}
# ⚙️ Funzione `trgfn_ui_lista_definizione_a10_valida_vista_sql`

```sql
CREATE FUNCTION trgfn_ui_lista_definizione_a10_valida_vista_sql()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_ui_lista_definizione_a10_valida_vista_sql()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: la relazione di una lista accesa esiste nel suo schema e,
-- quando l'applicazione cambia la vista o riaccende la lista, ha
-- ancora i campi delle sue colonne VISTA.
-- Lista spenta o senza vista: niente da verificare (la verifica
-- arriva con la riaccensione).
DECLARE
  v_orfane text;
BEGIN
  IF NEW.vista_sql IS NULL OR NEW.attivo IS NOT TRUE THEN
    RETURN NEW;
  END IF;

  IF NOT ui.fn_lista_relazione_ha_attributo(NEW.schema_dati, NEW.vista_sql, NULL) THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'ui.trgfn_ui_lista_definizione_a10_valida_vista_sql',
      'E_UI_VISTA_SQL_NON_TROVATA',
      jsonb_build_object(
        'campo', 'vista_sql',
        'codice', NEW.codice
      ),
      NULL,
      NEW.schema_dati || '.' || NEW.vista_sql
    );
  END IF;

  -- Le colonne si riverificano solo quando cambia cio' contro cui sono
  -- state giudicate (la relazione) o quando la lista torna accesa, e
  -- solo per l'applicazione: il seed lo giudicano pgTAP e presidio.
  IF TG_OP <> 'UPDATE'
     OR NOT (NEW.vista_sql   IS DISTINCT FROM OLD.vista_sql
             OR NEW.schema_dati IS DISTINCT FROM OLD.schema_dati
             OR OLD.attivo IS NOT TRUE)
     OR script.fn_is_proprietario_tabella(TG_RELID) THEN
    RETURN NEW;
  END IF;

  SELECT string_agg(lc.codice, ', ' ORDER BY lc.codice)
    INTO v_orfane
    FROM ui.lista_colonna lc
   WHERE lc.lista_id = NEW.id
     AND lc.origine_campo = 'VISTA'
     AND lc.campo_sorgente IS NOT NULL
     AND NOT ui.fn_lista_relazione_ha_attributo(NEW.schema_dati, NEW.vista_sql,
                                                lc.campo_sorgente);

  IF v_orfane IS NOT NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'ui.trgfn_ui_lista_definizione_a10_valida_vista_sql',
      'E_UI_LISTA_COLONNE_ORFANE',
      jsonb_build_object(
        'campo', 'vista_sql',
        'lista_id', NEW.id,
        'codice', NEW.codice
      ),
      NULL,
      NEW.codice::text,
      NEW.schema_dati || '.' || NEW.vista_sql,
      v_orfane
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_ui_lista_definizione_a10_valida_vista_sql()
IS 'Guard BEFORE INSERT OR UPDATE OF vista_sql, schema_dati, attivo su ui.lista_definizione. Su una lista accesa con una vista, la relazione esiste nel suo schema (ui.fn_lista_relazione_ha_attributo: vista, vista materializzata, tabella, tabella partizionata), altrimenti E_UI_VISTA_SQL_NON_TROVATA. Per chi non è il proprietario della tabella, un cambio di vista o di schema e la riaccensione della lista si rifiutano se una colonna VISTA, accesa o spenta, ha un campo che la relazione non ha: E_UI_LISTA_COLONNE_ORFANE, con le colonne nella frase. Il seed lo giudicano il pgTAP del catalogo e il presidio dbops.vw_liste_colonne_campo_orfano. Lista spenta o senza vista: niente da verificare.';
```

</div>

---
{% include-markdown "signature-core.md" %}
