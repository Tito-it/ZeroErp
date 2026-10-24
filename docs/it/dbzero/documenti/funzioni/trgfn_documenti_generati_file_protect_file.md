{% include-markdown "it/dbzero/documenti/manual/trgfn_documenti_generati_file_protect_file.md" %}
# ⚙️ Funzione `trgfn_documenti_generati_file_protect_file`

```sql
CREATE FUNCTION trgfn_documenti_generati_file_protect_file()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_documenti_generati_file_protect_file()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Blocca l'UPDATE di campi file su documenti_generati_file.
--
-- Regole:
--   Campi immutabili:
--     - documento_generato_id, file_tipo_id
--     - storage_key, sha256, file_size_bytes, mime_type, file_name
--     - is_principale
--   Campi modificabili (per futuro Fase B):
--     - meta, ordinamento (condizionatamente)
--
-- Errore:
--   E_DOCUMENTI_GENERATO_FILE_IMMUTABILE
BEGIN
  IF  (NEW.documento_generato_id != OLD.documento_generato_id OR
       NEW.file_tipo_id          != OLD.file_tipo_id          OR
       NEW.storage_key           != OLD.storage_key           OR
       NEW.sha256                != OLD.sha256                OR
       NEW.file_size_bytes       != OLD.file_size_bytes       OR
       NEW.mime_type             != OLD.mime_type             OR
       NEW.file_name             != OLD.file_name             OR
       NEW.is_principale         != OLD.is_principale) THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_documenti_generati_file_protect_file',
      'E_DOCUMENTI_GENERATO_FILE_IMMUTABILE',
      jsonb_build_object(
        'documento_generato_id', OLD.documento_generato_id,
        'file_tipo_id', OLD.file_tipo_id
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_documenti_generati_file_protect_file()
IS 'Guard A7-bis: blocca UPDATE su file. File generato = istantanea immutabile di salvataggio. Solo meta/ordinamento modificabili.';
```

</div>

---
{% include-markdown "signature-core.md" %}
