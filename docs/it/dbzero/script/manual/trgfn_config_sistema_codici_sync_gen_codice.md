## 📘 Documentazione Concettuale – Funzione `script.trgfn_config_sistema_codici_sync_gen_codice()`

> 👀 **Vedi anche**
>
**Guide generali:**    
>
• [Automazione DB](/guide/automazione-db)    
>
**Approfondimento tabelle:**    
>
• [config.sistema_codici](/dbzero/config/manual/sistema_codici)    
>
**Approfondimento funzioni:**    
>
• [script.fn_generate_codice](/dbzero/script/manual/fn_generate_codice)    
> • [script.fn_log_and_raise_error](/dbzero/script/manual/fn_log_and_raise_error)    

---
### 🎯 Scopo Principale
La funzione `script.trgfn_config_sistema_codici_sync_gen_codice()` mantiene **sincronizzati**
trigger e trigger function per la **generazione automatica dei codici/numero** in base a
`config.sistema_codici`.

Viene eseguita **AFTER INSERT/UPDATE/DELETE** su `config.sistema_codici` e:

* crea o aggiorna la trigger function `trgfn_<tabella>_gen_codice`;
* crea o aggiorna il trigger `trg_<tabella>_a10_gen_codice_ins_upd`;
* rimuove entrambi se `usa_sequenza = false` o se la configurazione viene eliminata.

---

### Logica principale

1. **DELETE** su `config.sistema_codici`  
   Rimuove trigger e trigger function associate alla tabella target.

2. **UPDATE** con cambio target (schema/tabella/colonna)  
   Rimuove trigger/function precedenti e rigenera quelle nuove.

3. **INSERT/UPDATE con `usa_sequenza = true`**  
   Genera la trigger function e il trigger, con condizione coerente al tipo colonna:

   * **numerica**: `NEW.<colonna> IS NULL OR NEW.<colonna> = 0`
   * **testuale**: `NEW.<colonna> IS NULL OR btrim(NEW.<colonna>::text) = ''`

4. **INSERT/UPDATE con `usa_sequenza = false`**  
   Rimuove trigger/function e non applica automazioni.

---

### Effetto sul runtime

Quando la colonna target e` NULL/vuota, il trigger invoca:

```sql
NEW.<colonna> := script.fn_generate_codice('<codice_interno>');
```

Questo genera il valore secondo la configurazione e crea la sequenza automatica
`<schema>.<tabella>_<colonna>_seq` se assente.

---

### Naming generato

* **Trigger function**: `trgfn_<tabella>_gen_codice`
* **Trigger**: `trg_<tabella>_a10_gen_codice_ins_upd`

---

### ⚠️ Errori gestiti

La funzione usa `script.fn_log_and_raise_error` se:

* mancano `schema_tabella`, `nome_tabella` o `nome_colonna`;
* la tabella/colonna target non esiste;
* la configurazione non e` coerente.

---

{% include-markdown "signature-core.md" %}

---
