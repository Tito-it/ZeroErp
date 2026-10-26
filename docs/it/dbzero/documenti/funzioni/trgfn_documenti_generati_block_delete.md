{% include-markdown "it/dbzero/documenti/manual/trgfn_documenti_generati_block_delete.md" %}
# ⚙️ Funzione `trgfn_documenti_generati_block_delete`

```sql
CREATE FUNCTION trgfn_documenti_generati_block_delete()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_documenti_generati_block_delete()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Blocca la cancellazione fisica di documenti generati.
--
-- Regola:
--   La tabella è append-only sulla generazione storica.
--   Il ciclo vita si gestisce tramite stato (GENERATO → ARCHIVIATO/ANNULLATO).
--   Non si cancella mai fisicamente: la cancellazione invaliderebbe
--   il tracciamento della generazione e l'audit tramite context_json.
--
-- Errore:
--   E_DOCUMENTI_GENERATO_DELETE_BLOCKED
BEGIN
  PERFORM script.fn_log_and_raise_error(
    'documenti', 'trgfn_documenti_generati_block_delete',
    'E_DOCUMENTI_GENERATO_DELETE_BLOCKED',
    jsonb_build_object(
      'documento_generato_id', OLD.id,
      'uid', OLD.uid::text,
      'stato', OLD.stato
    ),
    NULL::uuid,
    VARIADIC ARRAY[]::text[]
  );
  RETURN OLD;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_documenti_generati_block_delete()
IS 'Guard A5: blocca DELETE fisico su documenti_generati. Tabella append-only: usa stato per ciclo vita, mai DELETE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
