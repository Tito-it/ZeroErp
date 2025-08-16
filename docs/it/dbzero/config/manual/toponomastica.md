## 📘 Documentazione Concettuale – Tabella `config.toponomastica`

>  👀 **Vedi anche** 

> Approfondimento Tabelle:  
>
> * [config.stati](/dbzero/config/tabelle/stati)   
> * [config.comuni](/dbzero/config/tabelle/comuni)   
> * [config.stradario](/dbzero/config/tabelle/stradario)        
> * [config.stradario_generale](/dbzero/config/tabelle/stradario_generale)  


La tabella **`config.toponomastica`** raccoglie i tipi di toponimi utilizzati per la composizione degli indirizzi: è la base per lo **`stradario_generale`**, dove ogni record di toponimo si combina con un nome specifico per generare l’indirizzo completo.

---

### 🎯 Scopo Principale

* **Censimento dei toponimi**
  Elenco delle tipologie di vie, strade, piazze, viali, ecc., utilizzate come prefisso negli indirizzi.
* **Fondamentale per lo stradario**
  Fornisce i prefissi standardizzati che, uniti al nome (es. "Garibaldi", "Roma"), generano i record di **`stradario_generale`**.
* **Integrazione con lo stato geografico**
  Collegato alla tabella `config.stati` per associare ogni tipo di toponimo all’area amministrativa di riferimento.

---


### 💡 Vantaggi Operativi

* **Standardizzazione degli indirizzi**
  Assicura coerenza nella definizione dei prefissi toponomastici, evitando errori di inserimento.
* **Performance nelle ricerche**
  Indice su `stato_id` permette filtraggi rapidi per area geografica.
* **Audit e tracciabilità**
  Campi e trigger di audit garantiscono la storia delle modifiche, supportando controlli e rollback in caso di necessità.

---

> 🧠 **"Un elenco strutturato e referenziato dei prefissi toponomastici, alla base di un sistema di indirizzamento preciso e coerente."**
