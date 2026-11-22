{% include-markdown "it/dbzero/ui/manual/trgfn_ui_lista_colonna_a10_valida_campo_sorgente.md" %}
# ⚙️ Funzione `trgfn_ui_lista_colonna_a10_valida_campo_sorgente`

```sql
CREATE FUNCTION trgfn_ui_lista_colonna_a10_valida_campo_sorgente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: il campo sorgente di una colonna esiste dove la colonna dice di
-- leggerlo (origine_campo).
--   LINEAGE -> la lista dichiara legge_lineage, su ogni lista;
--              il nome lo verifica il presidio
--              dbops.vw_liste_colonne_campo_orfano;
--   VISTA   -> il campo e' un attributo della relazione della lista
--              (ui.fn_lista_relazione_ha_attributo), se la lista e'
--              accesa e ha una relazione. Su una lista spenta giudica
--              il guard della definizione, all'accensione.
-- Senza campo (azione, colonna composta): niente da verificare.
-- Un campo vuoto lo rifiuta chk_lista_colonna_campo_sorgente_non_vuoto:
-- il salto lascia parlare il vincolo, che dice la cosa giusta.
DECLARE
  v_lista ui.lista_definizione%ROWTYPE;
BEGIN
  IF NEW.campo_sorgente IS NULL OR btrim(NEW.campo_sorgente) = '' THEN
    RETURN NEW;
  END IF;

  SELECT ld.*
    INTO v_lista
    FROM ui.lista_definizione ld
   WHERE ld.id = NEW.lista_id;

  IF NEW.origine_campo = 'LINEAGE' THEN
    IF v_lista.legge_lineage IS NOT TRUE THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        'ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente',
        'E_UI_LINEAGE_NON_DICHIARATA',
        jsonb_build_object(
          'campo', 'origine_campo',
          'lista_id', NEW.lista_id,
          'codice', NEW.codice
        ),
        NULL,
        NEW.codice::text,
        v_lista.codice::text
      );
    END IF;
    RETURN NEW;
  END IF;

  IF v_lista.attivo IS NOT TRUE OR v_lista.vista_sql IS NULL THEN
    RETURN NEW;
  END IF;

  IF NOT ui.fn_lista_relazione_ha_attributo(v_lista.schema_dati, v_lista.vista_sql,
                                            NEW.campo_sorgente) THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente',
      'E_UI_CAMPO_SORGENTE_NON_TROVATO',
      jsonb_build_object(
        'campo', 'campo_sorgente',
        'lista_id', NEW.lista_id,
        'codice', NEW.codice
      ),
      NULL,
      NEW.campo_sorgente::text,
      v_lista.schema_dati || '.' || v_lista.vista_sql
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente()
IS 'Guard BEFORE INSERT OR UPDATE OF campo_sorgente, origine_campo, lista_id su ui.lista_colonna: il campo sorgente esiste dove la colonna dice di leggerlo. Una colonna LINEAGE sta solo su una lista che dichiara legge_lineage (E_UI_LINEAGE_NON_DICHIARATA); il nome lo verifica il presidio dbops.vw_liste_colonne_campo_orfano. Una colonna VISTA ha il campo nella relazione della lista (ui.fn_lista_relazione_ha_attributo, E_UI_CAMPO_SORGENTE_NON_TROVATO), se la lista è accesa e ha una relazione; su una lista spenta giudica ui.trgfn_ui_lista_definizione_a10_valida_vista_sql all''accensione. Una colonna senza campo (azione, composta) passa; un campo vuoto lo rifiuta il vincolo chk_lista_colonna_campo_sorgente_non_vuoto, che il guard lascia parlare.';
```

</div>

---
{% include-markdown "signature-core.md" %}
