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
  --   Normalizza campi base e risolve registro/valuta per
  --   attivita_fatturabili.
  --
  -- Regole:
  --   - competenza_mese -> primo del mese
  --   - sorgente_riga default 0 se sorgente valorizzata
  --   - registro_id: sorgente -> utility -> errore
  --   - valuta_id: BA -> utility -> gestore
  -- =========================================================

  IF NEW.competenza_mese IS NOT NULL THEN
    NEW.competenza_mese := date_trunc('month', NEW.competenza_mese)::date;
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

  IF NEW.registro_id IS NULL THEN
    NEW.registro_id := vendite.fn_get_registro_id(
      NEW.sorgente_tipo_id,
      v_utility_id
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
