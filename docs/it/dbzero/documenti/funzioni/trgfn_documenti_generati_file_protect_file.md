{% include-markdown "it/dbzero/documenti/manual/trgfn_documenti_generati_file_protect_file.md" %}
# ⚙️ Funzione `trgfn_documenti_generati_file_protect_file`

```sql
CREATE FUNCTION trgfn_documenti_generati_file_protect_file()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

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
IS 'Tiene fermi i dati di salvataggio di un file della stampa: la stampa, il tipo, il tipo MIME, il nome, il peso, la chiave nello storage, l''impronta e is_principale (E_DOCUMENTI_GENERATO_FILE_IMMUTABILE). Restano liberi meta e ordinamento. Le colonne confrontate sono tutte NOT NULL.';
```

</div>

---
{% include-markdown "signature-core.md" %}
