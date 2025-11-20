# ⚙️ Funzione `trgfn_fornitori_check_ruolo_fornitore`

```sql
CREATE FUNCTION trgfn_fornitori_check_ruolo_fornitore()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_fornitori_check_ruolo_fornitore()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
 BEGIN
       
       --   Ogni volta che inserisco/aggiorno in fornitori, gestisco la
       --   creazione/verifica della riga corrispondente in soggetti_ruoli
       --   alimentando poi in NEW.soggetto_ruolo_id il record finale.

     -- Sostituisco NEW.soggetto_ruolo_id con l'ID vero (nuovo o esistente),
     -- delegando completamente alla funzione generica:
     NEW.soggetto_ruolo_id := script.fn_check_ins_soggetto_ruolo(
                               p_soggetto_id       := NEW.soggetto_id,
                               p_soggetto_ruolo_id := NEW.soggetto_ruolo_id,
                               p_cd_int_ruolo      := 'FO'
                             );
     RETURN NEW;
 END;
 $function$
```

---
{% include-markdown "signature-core.md" %}
