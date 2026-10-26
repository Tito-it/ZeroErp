{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_fornitori_guard_ruolo_fornitore.md" %}
# ⚙️ Funzione `trgfn_fornitori_guard_ruolo_fornitore`

```sql
CREATE FUNCTION trgfn_fornitori_guard_ruolo_fornitore()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_fornitori_guard_ruolo_fornitore()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- FUNCTION: 
    --   Ogni volta che inserisco/aggiorno in fornitori, gestisco la
    --   verifica della riga corrispondente in soggetti_ruoli.
    --   alimentando poi in NEW.soggetto_ruolo_id il record finale.

    -- Sostituisco NEW.soggetto_ruolo_id con l'ID vero (esistente),
    -- delegando completamente alla funzione generica:
    NEW.soggetto_ruolo_id := script.fn_guard_soggetto_ruolo(
                            p_soggetto_id       := NULL,
                            p_soggetto_ruolo_id := NEW.soggetto_ruolo_id,
                            p_cd_int_ruolo      := 'FO'
                            );
    RETURN NEW;
END;

$function$

COMMENT ON FUNCTION anagrafiche.trgfn_fornitori_guard_ruolo_fornitore()
IS 'Trigger che, prima di inserire/aggiornare in anagrafiche.fornitori,
chiama fn_guard_soggetto_ruolo per validare il legame
soggetto→ruolo (cd_int_ruolo = ''FO'').';
```

</div>

---
{% include-markdown "signature-core.md" %}
