# ⚙️ Funzione `trgfn_emittenti_fiscali_check_ruolo_emi_fis`

```sql
CREATE FUNCTION trgfn_emittenti_fiscali_check_ruolo_emi_fis()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_emittenti_fiscali_check_ruolo_emi_fis()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
 BEGIN
       -- FUNCTION: 
       --   Ogni volta che inserisco/aggiorno in emittenti_fiscali, gestisco la
       --   creazione/verifica della riga corrispondente in soggetti_ruoli
       --   alimentando poi in NEW.soggetto_ruolo_id il record finale.

     -- Sostituisco NEW.soggetto_ruolo_id con l'ID vero (nuovo o esistente),
     -- delegando completamente alla funzione generica:
     NEW.soggetto_ruolo_id := script.fn_check_ins_soggetto_ruolo(
                               p_soggetto_id       := NEW.soggetto_id,
                               p_soggetto_ruolo_id := NEW.soggetto_ruolo_id,
                               p_cd_int_ruolo      := 'EMIT-IS'
                             );
     RETURN NEW;
 END;
 $function$
```

---
{% include-markdown "signature-core.md" %}
