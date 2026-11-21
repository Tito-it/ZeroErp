{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_fornitori_guard_normalize.md" %}
# ⚙️ Funzione `trgfn_fornitori_guard_normalize`

```sql
CREATE FUNCTION trgfn_fornitori_guard_normalize()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_fornitori_guard_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- ============================================================
  -- Scopo: valida i campi del fornitore prima di INS/UPD.
  -- Regole:
  --   1) ritenuta: se acconto = true, aliquota obbligatoria > 0
  --   2) ritenuta: se acconto <> true, aliquota azzerata
  -- ============================================================

  -- 1) Guard: coerenza ritenuta d'acconto
  IF NEW.ritenuta_acconto = true
     AND (NEW.ritenuta_aliquota IS NULL OR NEW.ritenuta_aliquota <= 0)
  THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'anagrafiche.trgfn_fornitori_guard_normalize',
      'E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA',
      jsonb_build_object(
          'campo', 'ritenuta_aliquota',
        'detail', 'Se ritenuta_acconto = true, ritenuta_aliquota deve essere > 0',
        'ritenuta_acconto', NEW.ritenuta_acconto,
        'ritenuta_aliquota', NEW.ritenuta_aliquota
      ),
      NULL::uuid,
      'ritenuta_aliquota obbligatoria quando ritenuta_acconto = true'
    );
  END IF;

  -- 2) Pulizia: se ritenuta non attiva, azzera aliquota
  IF NEW.ritenuta_acconto IS DISTINCT FROM true THEN
    NEW.ritenuta_aliquota := NULL;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_fornitori_guard_normalize()
IS 'Guard su anagrafiche.fornitori, BEFORE INSERT OR UPDATE: coerenza della ritenuta d''acconto (con ritenuta_acconto = true serve ritenuta_aliquota > 0, E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA; senza ritenuta l''aliquota si azzera).';
```

</div>

---
{% include-markdown "signature-core.md" %}
