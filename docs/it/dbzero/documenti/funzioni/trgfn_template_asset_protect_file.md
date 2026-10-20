{% include-markdown "it/dbzero/documenti/manual/trgfn_template_asset_protect_file.md" %}
# ⚙️ Funzione `trgfn_template_asset_protect_file`

```sql
CREATE FUNCTION trgfn_template_asset_protect_file()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_template_asset_protect_file()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Blocca la modifica di colonne file su asset.
--
-- Regole:
--   Campi immutabili (file specifics):
--     - storage_key, sha256, file_size_bytes, mime_type, file_name
--   Campi modificabili:
--     - meta, validita (via valido_al)
--
--   Il file (e il suo hash) non si modificano mai.
--   Se serve un file diverso si crea un nuovo asset.
--
-- Errore:
--   E_DOCUMENTI_ASSET_FILE_IMMUTABILE
BEGIN
  IF  (NEW.storage_key    != OLD.storage_key    OR
       NEW.sha256         != OLD.sha256         OR
       NEW.file_size_bytes != OLD.file_size_bytes OR
       NEW.mime_type      != OLD.mime_type      OR
       NEW.file_name      != OLD.file_name) THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_template_asset_protect_file',
      'E_DOCUMENTI_ASSET_FILE_IMMUTABILE',
      jsonb_build_object(
        'template_asset_id', OLD.id,
        'emittente_fiscale_id', OLD.emittente_fiscale_id,
        'codice_interno', OLD.codice_interno
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_template_asset_protect_file()
IS 'Guard A4: blocca UPDATE su file asset. Una volta salvato il file, storage_key/hash/nome diventano immutabili.';
```

</div>

---
{% include-markdown "signature-core.md" %}
