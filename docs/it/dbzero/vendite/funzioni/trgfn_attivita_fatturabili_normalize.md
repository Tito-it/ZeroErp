{% include-markdown "it/dbzero/vendite/manual/trgfn_attivita_fatturabili_normalize.md" %}
# ⚙️ Funzione `trgfn_attivita_fatturabili_normalize`

```sql
CREATE FUNCTION trgfn_attivita_fatturabili_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_attivita_fatturabili_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_utility_id config.utilities.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Normalizza campi base e risolve tipo_doc_fiscale/valuta.
  --
  -- Regole:
  --   - competenza_mese sempre valorizzata e al primo del mese
  --   - se NULL -> mese di posticipa_al (se presente)
  --   - competenza_dal/al: se NULL, default su data_attivita
  --   - sorgente_riga default 0 se sorgente valorizzata
  --   - tipo_doc_fiscale_id: da sorgente
  --   - valuta_id: BA -> utility -> gestore
  -- =========================================================

  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;

  IF NEW.competenza_mese IS NULL AND NEW.posticipa_al IS NOT NULL THEN
    NEW.competenza_mese := date_trunc('month', NEW.posticipa_al)::date;
  ELSIF NEW.competenza_mese IS NOT NULL THEN
    NEW.competenza_mese := date_trunc('month', NEW.competenza_mese)::date;
  END IF;

  IF NEW.competenza_dal IS NULL THEN
    NEW.competenza_dal := NEW.data_attivita;
  END IF;

  IF NEW.competenza_al IS NULL THEN
    NEW.competenza_al := NEW.competenza_dal;
  END IF;

  IF NEW.sorgente_tipo_id IS NOT NULL THEN
    IF NEW.sorgente_riga IS NULL THEN
      NEW.sorgente_riga := 0;
    END IF;
  END IF;

  IF NEW.billing_account_id IS NOT NULL THEN
    SELECT ba.utility_id
      INTO v_utility_id
      FROM anagrafiche.billing_account ba
     WHERE ba.id = NEW.billing_account_id;
  END IF;

  IF NEW.tipo_doc_fiscale_id IS NULL THEN
    NEW.tipo_doc_fiscale_id := vendite.fn_get_tipo_doc_fiscale_id(
      NEW.sorgente_tipo_id
    );
  END IF;

  IF NEW.valuta_id IS NULL THEN
    NEW.valuta_id := vendite.fn_get_valuta_id(
      NEW.billing_account_id,
      v_utility_id
    );
  END IF;

  RETURN NEW;
END
$function$
```

---
{% include-markdown "signature-core.md" %}
