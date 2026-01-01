## 📘 Documentazione Concettuale – Tabella `config.toponomastica`

>  👀 **Vedi anche** 

> Approfondimento Tabelle:  
>
> * [config.stati](/dbzero/config/tabelle/stati)   
> * [config.comuni](/dbzero/config/tabelle/comuni)   
> * [config.stradario](/dbzero/config/tabelle/stradario)        
> * [config.stradario_generale](/dbzero/config/tabelle/stradario_generale)  
>
> Approfondimento Funzione:  
>
> * [config.trgfn_toponomastica_bump_normalize](/dbzero/config/funzioni/trgfn_toponomastica_bump_normalize)   
> * [config.trgfn_toponomastica_protect_update](/dbzero/config/funzioni/trgfn_toponomastica_protect_update)   




La tabella **`config.toponomastica`** raccoglie i tipi di toponimi utilizzati per la composizione degli indirizzi: è la base per lo **`stradario_generale`**, dove ogni record di toponimo si combina con un nome specifico per generare l’indirizzo completo.

---

### 🎯 Scopo Principale

(latest review 31-12-25)
* **Censimento dei toponimi**
  Elenco delle tipologie di vie, strade, piazze, viali, ecc., utilizzate come prefisso negli indirizzi.
* **Fondamentale per lo stradario**
  Fornisce i prefissi standardizzati che, uniti al nome (es. "Garibaldi", "Roma"), generano i record di **`stradario_generale`**.
* **Integrazione con lo stato geografico**
  Collegato alla tabella `config.stati` per associare ogni tipo di toponimo all’area amministrativa di riferimento.

---

### ✅ Gestione attivo/inattivo

La colonna `attivo` permette di **disattivare** i toponimi non piu' utilizzati senza eliminarli, evitando che vengano proposti in nuove configurazioni.

---

### 🧩 Regola di manutenzione (coerente con la policy indirizzi)

Se un toponimo e' **in uso** nello `stradario_generale`, la modifica della descrizione e' bloccata dal guard.  
In caso di correzioni (es. refusi), si crea un **nuovo** toponimo e si riallineano i record di `config.stradario_generale` interessati.  
Il trigger `trgfn_toponomastica_bump_normalize` riallinea `indirizzo_normalizzato` sui record collegati.

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
