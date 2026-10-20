{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_emittenti_fiscali_guard_ruolo_emi_fis.md" %}
# ⚙️ Funzione `trgfn_emittenti_fiscali_guard_ruolo_emi_fis`

```sql
CREATE FUNCTION trgfn_emittenti_fiscali_guard_ruolo_emi_fis()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_ruolo_emi_fis()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- FUNCTION: 
    --   Ogni volta che inserisco/aggiorno in emittenti_fiscali, gestisco la
    --   verifica della riga corrispondente in soggetti_ruoli.
    --   alimentando poi in NEW.soggetto_ruolo_id il record finale.

    -- Sostituisco NEW.soggetto_ruolo_id con l'ID vero (esistente),
    -- delegando completamente alla funzione generica:
    NEW.soggetto_ruolo_id := script.fn_guard_soggetto_ruolo(
                            p_soggetto_id       := NULL,
                            p_soggetto_ruolo_id := NEW.soggetto_ruolo_id,
                            p_cd_int_ruolo      := 'EF'
                            );
    RETURN NEW;
END;

$function$

COMMENT ON FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_ruolo_emi_fis()
IS 'Trigger che, prima di inserire/aggiornare in anagrafiche.emittenti_fiscali,
chiama fn_guard_soggetto_ruolo per validare il legame
soggetto→ruolo (cd_int_ruolo = ''EF'').';
```

</div>

---
{% include-markdown "signature-core.md" %}
