{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_emittenti_fiscali_regime_conferma.md" %}
# ⚙️ Funzione `trgfn_emittenti_fiscali_regime_conferma`

```sql
CREATE FUNCTION trgfn_emittenti_fiscali_regime_conferma()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_emittenti_fiscali_regime_conferma()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: una conferma del regime fiscale vale per il regime a cui
--   e' stata data. Se il regime cambia e la conferma no, la
--   conferma si azzera.
-- Uso:   BEFORE UPDATE OF regime_fiscale_rf FOR EACH ROW
BEGIN
    -- UPDATE OF scatta anche quando la colonna e' riscritta con lo
    -- stesso valore: li' la conferma resta com'e'.
    IF NEW.regime_fiscale_rf IS NOT DISTINCT FROM OLD.regime_fiscale_rf THEN
        RETURN NEW;
    END IF;

    -- Una conferma scritta insieme al regime nuovo e' la conferma
    -- del regime nuovo: resta.
    IF NEW.regime_fiscale_confermato_il IS DISTINCT FROM OLD.regime_fiscale_confermato_il THEN
        RETURN NEW;
    END IF;

    NEW.regime_fiscale_confermato_il := NULL;
    NEW.regime_fiscale_confermato_da := NULL;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_emittenti_fiscali_regime_conferma()
IS 'Una conferma del regime fiscale vale per il regime a cui e'' stata data: quando regime_fiscale_rf cambia e regime_fiscale_confermato_il no, la conferma (data e autore) si azzera, e l''emittente torna nel presidio dbops.vw_emittenti_regime_non_confermato. Chi dichiara il regime nuovo scrive la conferma nella stessa scrittura, e quella resta. Non solleva. Brief: brief-db-esigibilita-iva-per-cassa-emittente (D-11).';
```

---
{% include-markdown "signature-core.md" %}
