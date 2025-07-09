## 📘 Documentazione Concettuale – Procedura `dbops.apply_fk_index_policy()`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:   
> - [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy)      
>
> Approfondimento funzioni :    
> - [dbops.fn_populate_fk_index_policy](/dbzero/dbops/funzioni/fn_populate_fk_index_policy)    
> - [dbops.vw_fk_senza_indice](/dbzero/dbops/funzioni/vw_fk_senza_indice)    

---

### 🎯 Scopo Principale

Applicare in modo automatico le regole di indicizzazione definite nella tabella `dbops.fk_index_policy`:   

*  **Creare** gli indici sulle foreign key contrassegnate come `consentito = true`.
*  **Rimuovere** gli indici non più approvati (`consentito = false`).

---

### 🔍 Descrizione del Flusso

1. **Scansione**
   Itera su ogni riga di `dbops.fk_index_policy` (schema, tabella, constraint, comando).
2. **Creazione**
   Se `rec.consentito = true`, esegue direttamente il SQL in `rec.dll_command` (tipicamente un `CREATE INDEX …`).
3. **Rimozione**
   Se `rec.consentito = false`, estrae il nome dell’indice dal sesto token di `dll_command` e invoca:

   ```sql
   DROP INDEX IF EXISTS <schema>.<index_name>;
   ```
4. **Fine**
   Continua fino all’ultima riga, garantendo che la policy definita in tabella sia sempre rispettata.

---

### ⚙️ Invocazione

```sql
CALL dbops.apply_fk_index_policy();
```

---

### 💡 Vantaggi Operativi

* **Centralizzazione**: tutte le regole di indicizzazione FK risiedono in un’unica tabella.
* **Automazione**: evita script manuali di `CREATE/DROP INDEX`, riducendo errori e incongruenze.
* **Flessibilità**: modificando la colonna `consentito` si abilita o disabilita subito l’indice, senza alterare codice.
* **Integrazione CI/CD**: è chiamata in un changeSet `90-end` per assicurarsi che, a ogni deploy, la policy sia applicata.
