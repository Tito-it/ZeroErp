{% include-markdown "it/dbzero/vendite/manual/trgfn_resi_normalize.md" %}
# ⚙️ Funzione `trgfn_resi_normalize`

```sql
CREATE FUNCTION trgfn_resi_normalize()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo: normalizzazione reso su INSERT/UPDATE.
  --   1. anno/data se numero presente (INSERT).
  --   2. eredita billing/destinatario/utility/valuta/emittente
  --      dal DDT sorgente (DDT_VENDITA, lookup per codice_interno
  --      via uid) su INSERT se non gia' valorizzati.
  --   3. fallback emittente da billing_account (standalone,
  --      predisposizione: sorgente NOT NULL in questa slice).
  -- =========================================================

  -- 1. anno/data
  IF TG_OP = 'INSERT' AND (NEW.numero IS NOT NULL AND btrim(NEW.numero) <> '') THEN
    IF NEW.anno IS NULL OR NEW.anno = 0 THEN
      NEW.anno := EXTRACT(YEAR FROM script.fn_data_operativa())::smallint;
    END IF;
    IF NEW.data IS NULL THEN
      NEW.data := script.fn_data_operativa();
    END IF;
  END IF;

  -- 2. eredita billing/destinatario/utility/valuta/emittente dal DDT sorgente
  IF TG_OP = 'INSERT'
     AND NEW.sorgente_tipo_id IS NOT NULL
     AND NEW.sorgente_uid IS NOT NULL
     AND (NEW.billing_account_id IS NULL
          OR NEW.destinatario_soggetto_ruolo_id IS NULL
          OR NEW.utility_id IS NULL
          OR NEW.valuta_id IS NULL
          OR NEW.emittente_fiscale_id IS NULL)
  THEN
    IF EXISTS (
      SELECT 1 FROM config.sorgenti
      WHERE id = NEW.sorgente_tipo_id AND codice_interno = 'DDT_VENDITA'
    ) THEN
      SELECT
        COALESCE(NEW.billing_account_id, d.billing_account_id),
        COALESCE(NEW.destinatario_soggetto_ruolo_id, d.destinatario_soggetto_ruolo_id),
        COALESCE(NEW.utility_id, d.utility_id),
        COALESCE(NEW.valuta_id, d.valuta_id),
        COALESCE(NEW.emittente_fiscale_id, d.emittente_fiscale_id)
      INTO
        NEW.billing_account_id,
        NEW.destinatario_soggetto_ruolo_id,
        NEW.utility_id,
        NEW.valuta_id,
        NEW.emittente_fiscale_id
      FROM vendite.ddt d
      WHERE d.uid = NEW.sorgente_uid
      LIMIT 1;
    END IF;
  END IF;

  -- 3. fallback standalone: emittente da billing_account (convenzione PK).
  IF TG_OP = 'INSERT'
     AND NEW.emittente_fiscale_id IS NULL
     AND NEW.billing_account_id IS NOT NULL
  THEN
    NEW.emittente_fiscale_id :=
      anagrafiche.fn_get_emittente_fiscale_pk(NEW.billing_account_id);
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_normalize()
IS 'Normalize reso: anno/data; eredita billing/destinatario/utility/valuta/emittente dal DDT sorgente (DDT_VENDITA, per codice_interno, JOIN vendite.ddt su uid) su INSERT; fallback emittente da billing_account. Mirror trgfn_ddt_normalize (fonte = DDT). rev 2026-07-13.';
```

</div>

---
{% include-markdown "signature-core.md" %}
