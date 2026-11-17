{% include-markdown "it/dbzero/documenti/manual/trgfn_template_asset_protect_file.md" %}
# ⚙️ Funzione `trgfn_template_asset_protect_file`

```sql
CREATE FUNCTION trgfn_template_asset_protect_file()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_template_asset_protect_file()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Il file di una risorsa dei modelli non cambia: e' cosi' che lo stesso
--   codice interno indica sempre gli stessi byte, e la ristampa fedele
--   ritrova il file di allora.
--
-- Regole:
--   Fermi: storage_key, sha256, file_size_bytes, mime_type, file_name.
--   Liberi: codice, descrizione, il tipo (se ammette il formato:
--   documenti.trgfn_guard_formato_ammesso), attivo, valido_dal,
--   valido_al, meta. codice_interno lo blocca script.trgfn_lock_columns.
--   Le cinque colonne ferme sono NOT NULL: il confronto con != basta.
--   Un file diverso e' una risorsa nuova, con un codice interno nuovo.
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
IS 'Il file di una risorsa dei modelli non cambia: chiave nello storage, impronta, peso, tipo MIME e nome sono quelli del caricamento (E_DOCUMENTI_ASSET_FILE_IMMUTABILE). Restano liberi codice, descrizione, il tipo (se ammette il formato), attivo, le date e meta; codice_interno lo blocca script.trgfn_lock_columns. Un file diverso e'' una risorsa nuova, con un codice interno nuovo: lo stesso codice indica sempre gli stessi byte, ed e'' cosi'' che la ristampa fedele ritrova il file di allora.';
```

</div>

---
{% include-markdown "signature-core.md" %}
