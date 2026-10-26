{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_resellers_guard_ruolo_reseller.md" %}
# ⚙️ Funzione `trgfn_resellers_guard_ruolo_reseller`

```sql
CREATE FUNCTION trgfn_resellers_guard_ruolo_reseller()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_resellers_guard_ruolo_reseller()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- FUNCTION: 
    --   Ogni volta che inserisco/aggiorno in resellers, gestisco la
    --   verifica della riga corrispondente in soggetti_ruoli.
    --   alimentando poi in NEW.soggetto_ruolo_id il record finale.

    -- Sostituisco NEW.soggetto_ruolo_id con l'ID vero (esistente),
    -- delegando completamente alla funzione generica:
    NEW.soggetto_ruolo_id := script.fn_guard_soggetto_ruolo(
                            p_soggetto_id       := NULL,
                            p_soggetto_ruolo_id := NEW.soggetto_ruolo_id,
                            p_cd_int_ruolo      := 'RE'
                            );
    RETURN NEW;
END;

$function$

COMMENT ON FUNCTION anagrafiche.trgfn_resellers_guard_ruolo_reseller()
IS 'Trigger che, prima di inserire/aggiornare in anagrafiche.resellers,
chiama fn_guard_soggetto_ruolo per validare il legame
soggetto→ruolo (cd_int_ruolo = ''RE'').';
```

</div>

---
{% include-markdown "signature-core.md" %}
