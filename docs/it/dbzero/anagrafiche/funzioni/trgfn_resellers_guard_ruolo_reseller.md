# ⚙️ Funzione `trgfn_resellers_guard_ruolo_reseller`

```sql
CREATE FUNCTION trgfn_resellers_guard_ruolo_reseller()
```

**Definizione completa:**

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
    NEW.soggetto_ruolo_id := script.fn_check_soggetto_ruolo(
                            p_soggetto_id       := NULL,
                            p_soggetto_ruolo_id := NEW.soggetto_ruolo_id,
                            p_cd_int_ruolo      := 'RE'
                            );
    RETURN NEW;
END;

$function$
```

---
{% include-markdown "signature-core.md" %}
