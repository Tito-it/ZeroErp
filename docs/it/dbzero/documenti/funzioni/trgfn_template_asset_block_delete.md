{% include-markdown "it/dbzero/documenti/manual/trgfn_template_asset_block_delete.md" %}
# ⚙️ Funzione `trgfn_template_asset_block_delete`

```sql
CREATE FUNCTION trgfn_template_asset_block_delete()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_template_asset_block_delete()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Blocca la cancellazione fisica di asset.
--
-- Regola:
--   Non si cancellano mai asset fisicamente. Se un asset non
--   serve piu', si chiude impostando valido_al. Questo preserva
--   l'integrità storica dei documenti generati (che referenziano
--   via template_asset_id).
--
-- Errore:
--   E_DOCUMENTI_ASSET_DELETE_BLOCKED
BEGIN
  PERFORM script.fn_log_and_raise_error(
    'documenti', 'trgfn_template_asset_block_delete',
    'E_DOCUMENTI_ASSET_DELETE_BLOCKED',
    jsonb_build_object(
      'template_asset_id', OLD.id,
      'emittente_fiscale_id', OLD.emittente_fiscale_id,
      'codice_interno', OLD.codice_interno
    ),
    NULL::uuid,
    VARIADIC ARRAY[]::text[]
  );
  RETURN OLD;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_template_asset_block_delete()
IS 'Guard A3: blocca DELETE fisico su asset. Asset sono immutabili; disattivarli via valido_al invece di cancellarli.';
```

</div>

---
{% include-markdown "signature-core.md" %}
