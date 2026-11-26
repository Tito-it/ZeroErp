{% include-markdown "it/dbzero/vendite/manual/trgfn_attivita_fatturabili_guard_fatturato.md" %}
# ⚙️ Funzione `trgfn_attivita_fatturabili_guard_fatturato`

```sql
CREATE FUNCTION trgfn_attivita_fatturabili_guard_fatturato()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_attivita_fatturabili_guard_fatturato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Blocca UPDATE/DELETE se la riga e' gia' fatturata
  --   (fattura_riga_id valorizzato).
  --   Passa solo dalla porta del reset del lotto: GUC e proprietario
  --   (vendite.fn_porta_reset_lotto_aperta).
  -- =========================================================
  IF vendite.fn_porta_reset_lotto_aperta(TG_RELID) THEN
    IF TG_OP = 'DELETE' THEN
      RETURN OLD;
    END IF;
    RETURN NEW;
  END IF;

  IF TG_OP = 'UPDATE' THEN
    IF OLD.fattura_riga_id IS NOT NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_RIGA_GIA_FATTURATA',
        jsonb_build_object('id', OLD.id, 'fattura_riga_id', OLD.fattura_riga_id),
        NULL::uuid, OLD.id::text
      );
    END IF;
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    IF OLD.fattura_riga_id IS NOT NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_RIGA_GIA_FATTURATA',
        jsonb_build_object('id', OLD.id, 'fattura_riga_id', OLD.fattura_riga_id),
        NULL::uuid, OLD.id::text
      );
    END IF;
    RETURN OLD;
  END IF;

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_attivita_fatturabili_guard_fatturato()
IS 'Blocca update/delete se fattura_riga_id e'' valorizzato; la scrittura la lascia passare solo la porta del reset del lotto (vendite.fn_porta_reset_lotto_aperta: GUC zeroerp.maintenance_reset_lotto_draft e proprietario della tabella, dentro la pulizia di vendite.fn_cleanup_fatture_by_ids).';
```

</div>

---
{% include-markdown "signature-core.md" %}
