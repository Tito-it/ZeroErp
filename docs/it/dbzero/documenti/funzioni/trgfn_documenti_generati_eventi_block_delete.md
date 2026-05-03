{% include-markdown "it/dbzero/documenti/manual/trgfn_documenti_generati_eventi_block_delete.md" %}
# ⚙️ Funzione `trgfn_documenti_generati_eventi_block_delete`

```sql
CREATE FUNCTION trgfn_documenti_generati_eventi_block_delete()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_documenti_generati_eventi_block_delete()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Blocca la cancellazione fisica di eventi della timeline documento.
--
-- Regola:
--   La tabella documenti_generati_eventi e' append-only per audit.
--   Una correzione/segnalazione si registra come nuovo evento
--   (esito KO/WARN), non cancellando lo storico.
--
-- Errore:
--   E_EVENTO_DOCUMENTO_DELETE_VIETATA
BEGIN
  PERFORM script.fn_log_and_raise_error(
    'documenti', 'trgfn_documenti_generati_eventi_block_delete',
    'E_EVENTO_DOCUMENTO_DELETE_VIETATA',
    jsonb_build_object(
      'evento_id', OLD.id,
      'documento_generato_id', OLD.documento_generato_id,
      'evento_tipo', OLD.evento_tipo,
      'evento_at', OLD.evento_at::text
    ),
    NULL::uuid
  );
  RETURN OLD;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_documenti_generati_eventi_block_delete()
IS 'Guard append-only: blocca DELETE su documenti_generati_eventi. La timeline e'' immutabile, correzioni vanno registrate come nuovo evento.';
```

---
{% include-markdown "signature-core.md" %}
