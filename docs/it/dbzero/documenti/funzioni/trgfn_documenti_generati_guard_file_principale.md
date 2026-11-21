{% include-markdown "it/dbzero/documenti/manual/trgfn_documenti_generati_guard_file_principale.md" %}
# ⚙️ Funzione `trgfn_documenti_generati_guard_file_principale`

```sql
CREATE FUNCTION trgfn_documenti_generati_guard_file_principale()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_documenti_generati_guard_file_principale()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
-- Scopo:
--   A fine transazione una stampa nata ha il suo file principale, il
--   PDF che si scarica e si ristampa.
--
-- Regole:
--   - scatta al commit (constraint trigger differito), dopo che il
--     servizio ha scritto stampa e file;
--   - giudica la nascita: il file non si cancella e il flag
--     is_principale non cambia, quindi dopo non serve altro;
--   - legge il file da proprietario, fuori dalla row security di chi
--     chiude la transazione, e solo per la stampa che nasce.
--
-- Errore:
--   E_DOCUMENTI_GENERATO_SENZA_FILE_PRINCIPALE
BEGIN
  IF NOT EXISTS (
      SELECT 1
        FROM documenti.documenti_generati_file f
       WHERE f.documento_generato_id = NEW.id
         AND f.is_principale IS TRUE
  ) THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_documenti_generati_guard_file_principale',
      'E_DOCUMENTI_GENERATO_SENZA_FILE_PRINCIPALE',
      jsonb_build_object(
        'documento_generato_id', NEW.id,
        'uid', NEW.uid::text
      ),
      NEW.tx_id,
      NEW.nome_file
    );
  END IF;
  RETURN NULL;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_documenti_generati_guard_file_principale()
IS 'A fine transazione una stampa nata ha il suo file principale (E_DOCUMENTI_GENERATO_SENZA_FILE_PRINCIPALE, col nome del file nella frase). Giudica la nascita: il file non si cancella e is_principale non cambia. SECURITY DEFINER con search_path fisso: legge il file fuori dalla row security di chi chiude la transazione, solo per la stampa che nasce.';
```

</div>

---
{% include-markdown "signature-core.md" %}
