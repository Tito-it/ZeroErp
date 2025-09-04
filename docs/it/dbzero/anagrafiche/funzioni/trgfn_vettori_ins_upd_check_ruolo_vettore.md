# ⚙️ Funzione `trgfn_vettori_ins_upd_check_ruolo_vettore`

```sql
CREATE FUNCTION trgfn_vettori_ins_upd_check_ruolo_vettore()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_vettori_ins_upd_check_ruolo_vettore()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
 BEGIN
       -- FUNCTION: 
       --   Ogni volta che inserisco/aggiorno in vettori, gestisco la
       --   creazione/verifica della riga corrispondente in soggetti_ruoli
       --   alimentando poi in NEW.soggetto_ruolo_id il record finale.

     -- Sostituisco NEW.soggetto_ruolo_id con l'ID vero (nuovo o esistente),
     -- delegando completamente alla funzione generica:
     NEW.soggetto_ruolo_id := script.fn_check_ins_soggetto_ruolo(
                               p_soggetto_id       := NEW.soggetto_id,
                               p_soggetto_ruolo_id := NEW.soggetto_ruolo_id,
                               p_cd_int_ruolo      := 'VET'
                             );
     RETURN NEW;
 END;
 $function$
```

---
{% include-markdown "signature-core.md" %}
