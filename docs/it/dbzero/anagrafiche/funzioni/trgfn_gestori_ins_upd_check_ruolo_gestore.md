{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_gestori_ins_upd_check_ruolo_gestore.md" %}
# ⚙️ Funzione `trgfn_gestori_ins_upd_check_ruolo_gestore`

### 🎯 Scopo Principale
- **Centralizzare l’assegnazione del ruolo “Gestore”**  
  Delegare a `script.fn_check_ins_soggetto_ruolo` la logica di inserimento o verifica del linking table, evitando duplicazioni di codice.

- **Mantenere coerenza referenziale**  
  Associare sempre correttamente il soggetto al ruolo di gestore, aggiornando `NEW.soggetto_ruolo_id` con l’ID valido, che sia preesistente o appena creato.

- **Semplificare i trigger client**  
  Qualunque operazione di INSERT o UPDATE su `anagrafiche.gestori` non deve preoccuparsi di controllare manualmente `soggetto_ruolo_id`; la trigger function ne gestisce la delega.

---

```sql
CREATE FUNCTION trgfn_gestori_ins_upd_check_ruolo_gestore()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_gestori_ins_upd_check_ruolo_gestore()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
 BEGIN
       -- FUNCTION: 
       --   Ogni volta che inserisco/aggiorno in gestori, gestisco la
       --   creazione/verifica della riga corrispondente in soggetti_ruoli
       --   alimentando poi in NEW.soggetto_ruolo_id il record finale.

     -- Sostituisco NEW.soggetto_ruolo_id con l'ID vero (nuovo o esistente),
     -- delegando completamente alla funzione generica:
     NEW.soggetto_ruolo_id := script.fn_check_ins_soggetto_ruolo(
                               p_soggetto_id       := NEW.soggetto_id,
                               p_soggetto_ruolo_id := NEW.soggetto_ruolo_id,
                               p_cd_int_ruolo      := 'GE'
                             );
     RETURN NEW;
 END;
 $function$
```