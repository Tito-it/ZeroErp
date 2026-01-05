## 📘 Documentazione Concettuale – Tabella `config.comuni`

>  👀 **Vedi anche**   
>
> Approfondimento tabelle:   
>
>  * [config.province](/dbzero/config/tabelle/province)        
>  * [config.stradario](/dbzero/config/tabelle/stradario)        
>  * [config.stradario_generale](/dbzero/config/tabelle/stradario_generale)        
>  * [storico.comuni](/dbzero/storico/tabelle/comuni)  
>
> Approfondimento funzione:   
> * [config.trgfn_comuni_protect_update](/dbzero/config/funzioni/trgfn_comuni_protect_update)   
> * [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic)   

La tabella **`config.comuni`** censisce i comuni (italiani ed esteri) all’interno di uno stato, fornendo la base per la geolocalizzazione degli indirizzi e per l’associazione con lo stradario.

---

### 🎯 Scopo Principale

(last review 30-12-25)
* **Censimento dei comuni**
  Elenco dei comuni presenti in ciascuno stato, identificati da nome e collegamento gerarchico a provincia e stato.
* **Attributi specifici per stato**
  La colonna `extra_country` (JSONB) permette di memorizzare dati aggiuntivi specifici per ogni paese (per l’Italia: codice catastale, codice ISTAT, fascia climatica, ecc.).
* **Integrazione con lo stradario**
  L’associazione tra `config.stradario_generale` (prefissi e nomi delle vie) e `config.comuni` genera la tabella `config.stradario`, che contiene l’indirizzo completo con la localizzazione geografica sul comune di appartenenza.
  Utilizzata per associare i record di **`config.stradario`** al comune di appartenenza, completa il percorso di indirizzamento.
* **Storicizzazione**
  Il campo `storicizza` se true attiva il trigger per la storicizzazione delle informazioni sulla tabella `storico.comuni`. Il front-end dovrà sempre impostare a true il valore, solo per funzioni administrator si potrà non gestire a true.

* **Protezione aggiornamenti quando in uso**
  Se il comune e' gia' utilizzato in `config.stradario`, la modifica dei campi chiave e' bloccata dal guard `config.trgfn_comuni_protect_update()`.

---

### 🔗 Collegamenti con Altre Tabelle

* **`config.province`**
  Il campo `provincia_id` identifica al provincia di appartenenza..
* **`storico.comuni`**
  `storico` True attiva il trigger per il salvataggio delle informazioni.
---

### 💡 Vantaggi Operativi

* **Flessibilità**
  L’uso di un campo JSONB per attributi extra consente di adattare la struttura dei dati alle diverse normative nazionali senza modifiche allo schema.
* **Coerenza geografica**
  Collegamento a tabelle di stato e provincia garantisce una gerarchia amministrativa corretta e uniforme.
* **Facilità di manutenzione**
  Inserimenti e aggiornamenti automatici tramite trigger di auditing e storicizzazione (se abilitata) assicurano la tracciabilità delle modifiche.

---

> 🧠 **"Un catalogo flessibile e gerarchico dei comuni, arricchito da attributi nazionali personalizzabili per supportare indirizzamento e reporting geografico."**
