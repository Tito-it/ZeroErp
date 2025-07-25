## 📘 Documentazione Concettuale – View `script.vw_stradario_esteso`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:   
> - [config.stradario_generale](/dbzero/config/tabelle/stradario_generale)   
> - [config.toponomastica](/dbzero/config/tabelle/toponomastica)   
> - [config.stati](/dbzero/config/tabelle/stati)   
>
> Approfondimento view:   
> - [script.vw_indirizzo_completo](/dbzero/script/views/vw_indirizzo_completo)    


La view **`script.vw_stradario_esteso`** offre una rappresentazione denormalizzata delle vie, combinando i dati base di **`stradario_generale`** con le relative informazioni di tipologia toponomastica e stato, per semplificare le query di indirizzo.

---

### 🎯 Scopo Principale

* **Aggregazione logica**: unire in un’unica sorgente i dati di via, toponomastica e stato, evitando join ripetuti nei client e nelle applicazioni.
* **Pulizia dati**: fornire alias chiari (`id_via`, `id_toponomastica`, `tipo_toponimo`, `sigla_stato`, `nome_strada`) per facilitare l’interpretazione dei risultati.
* **Performance**: ridurre il carico di join runtime raggruppando più tabelle in un’unica view materializzata (se necessario).

---


### 💡 Vantaggi Operativi

* **Sviluppo semplificato**: i client possono accedere a tutti i dettagli di via con una singola query.
* **Flessibilità**: la view può essere indicizzata o materializzata per scenari ad alto carico di lettura.
* **Coerenza terminologica**: garantisce che la costruzione di `indirizzo_generale` sia uniforme in tutte le parti dell’applicazione.

---

### 🔖 Commento sulla View

```sql
COMMENT ON VIEW script.vw_stradario_esteso
  IS 'View che estende stradario_generale con dati di toponomastica e stato, "indirizzo_generale" = tipo_toponimo || nome_strada';
```

---

> 🧠 **“`vw_stradario_esteso` è lo strumento ideale per ottenere in un colpo solo tutte le informazioni essenziali di una via, facilitando integrazioni e reportistica.”**