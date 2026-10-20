{% include-markdown "it/dbzero/vendite/manual/trgfn_offerte_commerciali_default_valuta.md" %}
# ⚙️ Funzione `trgfn_offerte_commerciali_default_valuta`

```sql
CREATE FUNCTION trgfn_offerte_commerciali_default_valuta()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_offerte_commerciali_default_valuta()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_emittente_sr_id anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
BEGIN
  -- 1) Skip se gia' valorizzato esplicitamente nel payload.
  IF NEW.valuta_id IS NOT NULL THEN
    RETURN NEW;
  END IF;

  -- 2) Mappa emittente PK -> soggetto_ruolo_id (gia' su NEW).
  IF NEW.emittente_fiscale_id IS NOT NULL THEN
    SELECT ef.soggetto_ruolo_id
      INTO v_emittente_sr_id
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.id = NEW.emittente_fiscale_id;
  END IF;

  -- 3) Resolver canonico: BA -> emittente -> gestore -> RAISE.
  NEW.valuta_id := vendite.fn_get_valuta_id(
    NEW.billing_account_id,
    v_emittente_sr_id
  );

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_offerte_commerciali_default_valuta()
IS 'BEFORE INSERT trigger fn: setta offerte_commerciali.valuta_id via vendite.fn_get_valuta_id (catena BA -> emittente -> gestore). Skip se valorizzato esplicitamente. Solleva E_CONFIG_MANCANTE (dalla fn) se nulla risolve. Pattern simmetrico a trgfn_preventivi_default_valuta / trgfn_contratti_default_valuta.';
```

</div>

---
{% include-markdown "signature-core.md" %}
