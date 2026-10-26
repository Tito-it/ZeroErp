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
  -- Scopo: normalizza e valida campi fornitori prima di INS/UPD.
  -- Regole:
  --   1) canale_fe → uppercase senza spazi (se valorizzato)
  --   2) pec_email → lowercase trimmed (se valorizzata)
  --   3) ritenuta: se acconto = true, aliquota obbligatoria > 0
  --   4) ritenuta: se acconto <> true, aliquota azzerata
  -- ============================================================

  -- 1) Normalizza canale_fe (uppercase, rimozione spazi)
  IF NEW.canale_fe IS NOT NULL THEN
    NEW.canale_fe := upper(regexp_replace(NEW.canale_fe, '\s+', '', 'g'));
  END IF;

  -- 2) Normalizza pec_email (lowercase, trim)
  IF NEW.pec_email IS NOT NULL THEN
    NEW.pec_email := lower(btrim(NEW.pec_email));
  END IF;

  -- 3) Guard: coerenza ritenuta d'acconto
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

  -- 4) Pulizia: se ritenuta non attiva, azzera aliquota
  IF NEW.ritenuta_acconto IS DISTINCT FROM true THEN
    NEW.ritenuta_aliquota := NULL;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_fornitori_guard_normalize()
IS 'Guard/normalize su fornitori: canale_fe (uppercase no spazi), pec_email (lowercase trim), coerenza ritenuta acconto/aliquota.';
```

</div>

---
{% include-markdown "signature-core.md" %}
