{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_clienti_guard_ruolo_cliente.md" %}
# ⚙️ Funzione `trgfn_clienti_guard_ruolo_cliente`

```sql
CREATE FUNCTION trgfn_clienti_guard_ruolo_cliente()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_clienti_guard_ruolo_cliente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- FUNCTION: 
    --   Ogni volta che inserisco/aggiorno in clienti, gestisco la
    --   creazione/verifica della riga corrispondente in soggetti_ruoli
    --   alimentando poi in NEW.soggetto_ruolo_id il record finale.

    -- Sostituisco NEW.soggetto_ruolo_id con l'ID vero (nuovo o esistente),
    -- delegando completamente alla funzione generica:
    NEW.soggetto_ruolo_id := script.fn_guard_soggetto_ruolo(
                            p_soggetto_id       := NULL,
                            p_soggetto_ruolo_id := NEW.soggetto_ruolo_id,
                            p_cd_int_ruolo      := 'CL'
                            );
    RETURN NEW;
END;

$function$

COMMENT ON FUNCTION anagrafiche.trgfn_clienti_guard_ruolo_cliente()
IS 'Trigger che, prima di inserire/aggiornare in anagrafiche.clienti,
chiama fn_guard_soggetto_ruolo per validare il legame
soggetto→ruolo (cd_int_ruolo = ''CL'').';
```

</div>

---
{% include-markdown "signature-core.md" %}
