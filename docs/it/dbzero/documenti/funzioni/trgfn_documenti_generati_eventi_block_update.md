{% include-markdown "it/dbzero/documenti/manual/trgfn_documenti_generati_eventi_block_update.md" %}
# ⚙️ Funzione `trgfn_documenti_generati_eventi_block_update`

```sql
CREATE FUNCTION trgfn_documenti_generati_eventi_block_update()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_documenti_generati_eventi_block_update()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Blocca qualsiasi UPDATE sulla timeline degli eventi documento.
--
-- Regola:
--   La tabella documenti_generati_eventi e' append-only.
--   Nessun campo (incluso messaggio, detail, esito, meta) puo'
--   essere modificato dopo l'INSERT. Per registrare correzioni
--   o eventi successivi inserire una nuova riga.
--
-- Errore:
--   E_EVENTO_DOCUMENTO_UPDATE_VIETATA
BEGIN
  PERFORM script.fn_log_and_raise_error(
    'documenti', 'trgfn_documenti_generati_eventi_block_update',
    'E_EVENTO_DOCUMENTO_UPDATE_VIETATA',
    jsonb_build_object(
      'evento_id', OLD.id,
      'documento_generato_id', OLD.documento_generato_id,
      'evento_tipo', OLD.evento_tipo,
      'evento_at', OLD.evento_at::text
    ),
    NULL::uuid,
    VARIADIC ARRAY[]::text[]
  );
  RETURN OLD;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_documenti_generati_eventi_block_update()
IS 'Guard append-only: blocca UPDATE su documenti_generati_eventi. Nessun campo modificabile post INSERT, correzioni come nuovo evento.';
```

</div>

---
{% include-markdown "signature-core.md" %}
