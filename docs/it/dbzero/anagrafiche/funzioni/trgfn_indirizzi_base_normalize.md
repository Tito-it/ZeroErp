{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_base_normalize.md" %}
# ⚙️ Funzione `trgfn_indirizzi_base_normalize`

```sql
CREATE FUNCTION trgfn_indirizzi_base_normalize()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_base_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  IF NEW.indirizzo_dettaglio_id IS NOT NULL THEN
    -- pulisco i fallback/liberi (evita mix normalizzato+libero)
    NEW.stato_id             := NULL;
    NEW.indirizzo_libero     := NULL;
    NEW.comune_id            := NULL;
    NEW.codice_postale_id    := NULL;
    NEW.administrative_area  := NULL;
    NEW.locality             := NULL;
    NEW.sublocality          := NULL;
    NEW.postal_code          := NULL;

    -- geoloc: coerente con sync_geoloc (si ricalcola da indirizzi_dettaglio)
    NEW.geoloc := NULL;

  ELSE
    -- Indirizzo libero. Un testo vuoto non e' un valore: a NULL,
    -- cosi' il CHECK e il guard della forma (z10, dopo) lo vedono
    -- per quello che e' (rev 2026-10-18).
    NEW.indirizzo_libero    := NULLIF(btrim(NEW.indirizzo_libero), '');
    NEW.locality            := NULLIF(btrim(NEW.locality), '');
    NEW.postal_code         := NULLIF(btrim(NEW.postal_code), '');
    NEW.administrative_area := NULLIF(btrim(NEW.administrative_area), '');
    NEW.sublocality         := NULLIF(btrim(NEW.sublocality), '');

    -- Lo stato non detto: quello proposto (rev 2026-10-18, D-1 di
    -- Tid). Il BB valida e non ripiega.
    IF NEW.stato_id IS NULL THEN
      NEW.stato_id := script.fn_stato_proposto_id(TG_NAME);
    END IF;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_indirizzi_base_normalize()
IS 'Trigger function generica: normalizza indirizzi (ruolo/soggetto). Se indirizzo_dettaglio_id presente pulisce fallback/liberi; altrimenti, nell''indirizzo libero, porta a NULL i testi vuoti (indirizzo_libero, locality, postal_code, administrative_area, sublocality) e scrive lo stato non detto con script.fn_stato_proposto_id. Rev 2026-10-18 (D-1 e D-3 di Tid): prima leggeva state_code_iso3 con fn_get_default_by_param, e la colonna si chiamava postal_box. Il guard della forma, anagrafiche.trgfn_indirizzi_guard_forma_libera, gira dopo (z10).';
```

</div>

---
{% include-markdown "signature-core.md" %}
