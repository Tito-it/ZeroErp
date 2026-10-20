{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_bank_guard_ruolo_bank_branches.md" %}
# ⚙️ Funzione `trgfn_bank_guard_ruolo_bank_branches`

```sql
CREATE FUNCTION trgfn_bank_guard_ruolo_bank_branches()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_bank_guard_ruolo_bank_branches()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- FUNCTION: 
    --   Ogni volta che inserisco/aggiorno in bank_branches, gestisco la
    --   verifica della riga corrispondente in soggetti_ruoli.
    --   alimentando poi in NEW.soggetto_ruolo_id il record finale.

    -- Sostituisco NEW.soggetto_ruolo_id con l'ID vero (nuovo o esistente),
    -- delegando completamente alla funzione generica:
    NEW.soggetto_ruolo_id := script.fn_guard_soggetto_ruolo(
                            p_soggetto_id       := NULL,
                            p_soggetto_ruolo_id := NEW.soggetto_ruolo_id,
                            p_cd_int_ruolo      := 'BANK_B'
                            );
    RETURN NEW;
END;

$function$

COMMENT ON FUNCTION anagrafiche.trgfn_bank_guard_ruolo_bank_branches()
IS 'Trigger che, prima di inserire/aggiornare in anagrafiche.bank,
chiama fn_guard_soggetto_ruolo per validare il legame
soggetto→ruolo (cd_int_ruolo = ''BANK_B'').';
```

</div>

---
{% include-markdown "signature-core.md" %}
