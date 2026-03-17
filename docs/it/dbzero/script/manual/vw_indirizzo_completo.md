## 📘 Documentazione Concettuale – View `script.vw_indirizzo_completo`

> 👀 **Vedi anche**   
>
Approfondimento tabelle:     
>
[config.stradario](/dbzero/config/tabelle/stradario)   
> [config.comuni](/dbzero/config/tabelle/comuni)   
>
Approfondimento view:     
>
[script.vw_stradario_esteso](/dbzero/script/views/vw_stradario_esteso)   

La view **`script.vw_indirizzo_completo`** estende la tabella `config.stradario` con dati anagrafici del comune, provincia, codice postale e dettaglio della via, fornendo un record unico per ogni via con tutte le informazioni utili.

---

### 🎯 Scopo Principale

* **Denormalizzazione per letture rapide**: aggregare in un’unica view i dati di stradario, comune, provincia, codice postale e via, semplificando le query di selezione degli indirizzi.
* **Pulizia e consistenza**: fornire campi già formattati e pronti per essere utilizzati nelle normalizzazioni e nelle funzionalità GIS.
* **Riutilizzabilità**: rendere disponibile un’unica sorgente per join di indirizzi completi, evitando duplicazione di codice SQL.

---


### Vantaggi Operativi

* **Performance**: riduce il numero di join necessari nelle query di indirizzo, migliorando i tempi di risposta.
* **Manutenibilità**: ogni modifica strutturale (es. nuovi campi) può essere gestita centralmente nella view.
* **Coesione**: fornisce un modello concettuale “indirizzo completo” facilmente comprensibile e utilizzabile.

---

### 🔖 Commento sulla View

```sql
COMMENT ON VIEW script.vw_indirizzo_completo
  IS 'View che estende config.stradario con dati di comune, provincia,
     codice postale e dettaglio via dalla view script.vw_stradario_esteso';
```

---

> **“`vw_indirizzo_completo` è il punto di riferimento per tutte le operazioni che richiedono i dati anagrafici e di localizzazione di una via, con un singolo accesso SQL.”**
