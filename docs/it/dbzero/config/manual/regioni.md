## 📘 Documentazione Concettuale – Tabella `config.regioni`

>  👀 **Vedi anche** 

> Approfondimento Tabelle:  
> - [config.stati](../stati) 


La tabella **`config.regioni`** censisce le regioni (italiane e di altri stati), fornendo informazioni amministrative e metadati utili per la gerarchia territoriale e la gestione delle accise.

---

### 🎯 Scopo Principale

* **Elenco delle regioni**
  Comprende tutte le regioni appartenenti a uno stato (es. in Italia: `Lazio`, `Campania`, `Sicilia`), con collegamento al rispettivo `stato_id` in **`config.stati`**.

* **Campo `extra_country` (JSONB)**
  Contiene metadati aggiuntivi, adattabili a diverse nazionalità:

  * **Italia**: include `codice_istat` (codice ISTAT della regione) e il flag `is_mezzogiorno` (booleano) che indica se la regione è considerata parte del Mezzogiorno ai fini del calcolo delle accise.
  * **Altri stati**: può ospitare attributi analoghi (es. codici statistici regionali, dati fiscali locali, zone economiche speciali, ecc.).

* **Gerarchia territoriale**
  Collegata a **`config.stati`** attraverso `stato_id`, la tabella definisce la struttura geografica top-down (Stato → Regione → Provincia → Comune → Stradario).

---

### 💡 Vantaggi Operativi

* **Coerenza geografica**
  Utilizzando `config.regioni` assieme a `config.province` e `config.comuni`, si ottiene una gerarchia completa dei territori, necessaria per reportistica, logistica e compliance fiscale.

* **Flessibilità di configurazione**
  Grazie al campo `extra_country`, è possibile personalizzare le informazioni di ogni regione senza alterare lo schema:

  * In Italia, il flag `is_mezzogiorno` permette di includere agevolazioni o calcoli specifici per le regioni meridionali (ad esempio riduzioni sulle accise).
  * Per altri stati si possono definire campi come `regional_tax_zone`, `climate_zone`, `economic_area`, ecc.

* **Supporto per accise**
  Il valore `is_mezzogiorno` (true/false) nel JSONB aiuta il modulo accise a determinare se una regione riconosce agevolazioni o differenti aliquote fiscali legate alle aree del Mezzogiorno.

* **Audit e tracciabilità**
  I trigger associati aggiornano automaticamente i campi `data_update` e `user_update`, mantenendo uno storico dettagliato di tutte le modifiche dei record di regione.

---

> 🧠 **"Un elenco configurabile di regioni, arricchito da metadati specifici per il calcolo delle accise e la gerarchia geografica, alla base di un sistema territoriale completo in Zero ERP."**
