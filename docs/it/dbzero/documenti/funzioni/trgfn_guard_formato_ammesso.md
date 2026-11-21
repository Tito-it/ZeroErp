{% include-markdown "it/dbzero/documenti/manual/trgfn_guard_formato_ammesso.md" %}
# ⚙️ Funzione `trgfn_guard_formato_ammesso`

```sql
CREATE FUNCTION trgfn_guard_formato_ammesso()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_guard_formato_ammesso()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Una risorsa dei modelli (template_asset) e un file della stampa
--   (documenti_generati_file) hanno un tipo MIME abbinato al loro tipo.
--
-- Regole:
--   - l'abbinamento si legge da documenti.tipi_asset_documento_formati
--     o da documenti.tipi_file_documento_formati, secondo la tabella;
--   - il tipo MIME si confronta minuscolo: il vocabolario lo tiene
--     minuscolo, e un tipo MIME non distingue le maiuscole;
--   - scatta alla nascita e quando cambiano tipo o formato.
--
-- Errore:
--   E_DOCUMENTI_FORMATO_NON_AMMESSO (nome del file, formato, tipo)
DECLARE
  -- Il codice di due vocabolari diversi, secondo la tabella: testo.
  v_tipo     text;
  v_ammesso  boolean;
BEGIN
  IF TG_TABLE_NAME = 'template_asset' THEN
    SELECT t.codice,
           EXISTS (SELECT 1
                     FROM documenti.tipi_asset_documento_formati af
                     JOIN config.formati_file ff ON ff.id = af.formato_file_id
                    WHERE af.asset_tipo_id = t.id
                      AND ff.mime_type = lower(NEW.mime_type))
      INTO v_tipo, v_ammesso
      FROM documenti.tipi_asset_documento t
     WHERE t.id = NEW.asset_tipo_id;
  ELSIF TG_TABLE_NAME = 'documenti_generati_file' THEN
    SELECT t.codice,
           EXISTS (SELECT 1
                     FROM documenti.tipi_file_documento_formati ff_t
                     JOIN config.formati_file ff ON ff.id = ff_t.formato_file_id
                    WHERE ff_t.file_tipo_id = t.id
                      AND ff.mime_type = lower(NEW.mime_type))
      INTO v_tipo, v_ammesso
      FROM documenti.tipi_file_documento t
     WHERE t.id = NEW.file_tipo_id;
  ELSE
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_guard_formato_ammesso',
      'E_TRIGGER_ARGOMENTI_INVALIDI',
      jsonb_build_object('tabella', TG_TABLE_NAME, 'trigger', TG_NAME),
      NULL,
      format('%s montato su %s, che non ha un abbinamento di formati', TG_NAME, TG_TABLE_NAME)
    );
  END IF;

  -- Un tipo che non esiste lo rifiuta la FK, dopo questo trigger.
  IF v_tipo IS NOT NULL AND NOT v_ammesso THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_guard_formato_ammesso',
      'E_DOCUMENTI_FORMATO_NON_AMMESSO',
      jsonb_build_object(
        'tabella', TG_TABLE_NAME,
        'id', NEW.id,
        'mime_type', NEW.mime_type,
        'tipo', v_tipo
      ),
      NEW.tx_id,
      NEW.file_name, NEW.mime_type, v_tipo
    );
  END IF;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_guard_formato_ammesso()
IS 'Una risorsa dei modelli e un file della stampa hanno un tipo MIME abbinato al loro tipo, in documenti.tipi_asset_documento_formati o documenti.tipi_file_documento_formati secondo la tabella (E_DOCUMENTI_FORMATO_NON_AMMESSO). Il tipo MIME si confronta minuscolo. Scatta alla nascita e quando cambiano tipo o formato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
