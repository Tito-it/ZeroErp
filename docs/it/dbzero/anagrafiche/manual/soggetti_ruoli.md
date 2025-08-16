## 📘 Documentazione Concettuale – Tabella `anagrafiche.soggetti_ruoli`

>  👀 **Vedi anche** 

> Approfondimento Tabelle:  
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)  
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)    

> Approfondimento trigger e funzioni:   
>
> * [script.tipi_ruoli](/dbzero/script/funzioni/fn_check_ins_soggetto_ruolo)

La tabella **`anagrafiche.soggetti_ruoli`** funge da collegamento (linking table) tra i soggetti registrati nel sistema e i ruoli definiti in `config.tipi_ruoli`, permettendo di assegnare a ciascun soggetto - individuo o azienda - uno o più ruoli specifici all’interno del software Zero ERP.

---

### 🎯 Scopo Principale

* **Associazione molti-a-molti**: stabilisce una relazione N\:N tra la tabella `anagrafiche.soggetti` e `config.tipi_ruoli`, consentendo a ogni soggetto di rivestire più ruoli (es. cliente, fornitore, gestore) e a ogni ruolo di essere assegnato a molti soggetti.
* **Estensione semantica**: il campo `extra` (JSONB) offre la possibilità di collegare metadati aggiuntivi per la singola associazione soggetto-ruolo (ad esempio, parametri contrattuali specifici se il ruolo è “fornitore” o date di attivazione per il ruolo “cliente”).
* **Tracciatura delle modifiche**: grazie ai campi di audit (`user_insert`, `data_insert`, `user_update`, `data_update`) aggiornati automaticamente, la tabella conserva la cronologia di creazione e aggiornamento di ciascuna associazione.

---

### 🔗 Collegamenti con Altre Tabelle

* **`anagrafiche.soggetti`**

  * Il campo `soggetto_id` (UUID) fa riferimento alla chiave primaria di `anagrafiche.soggetti`.
  * Vincolo `fk_soggetti_anagrafiche`: se un soggetto viene eliminato, tutte le righe corrispondenti in `soggetti_ruoli` vengono automaticamente cancellate (ON DELETE CASCADE).

* **`config.tipi_ruoli`**

  * Il campo `ruolo_id` (integer) fa riferimento alla chiave primaria di `config.tipi_ruoli`.
  * Vincolo `fk_tipi_ruoli_config`: impedisce la cancellazione di un ruolo se esistono associazioni attive (ON DELETE RESTRICT), garantendo la coerenza referenziale.

* **Unicità dell’associazione**

  * Il vincolo `uq_soggetto_ruolo` su `(soggetto_id, ruolo_id)` garantisce che non esistano duplicati: uno stesso soggetto non può avere due volte lo stesso ruolo.

---

### 💡 Vantaggi Operativi

* **Modularità e pulizia dei dati**
  Separando i dati anagrafici base (in `anagrafiche.soggetti`) dall’assegnazione dei ruoli, si evita di dover ripetere attributi del soggetto ogni qualvolta cambia un ruolo. Questo design semplifica le query e migliora le performance.

* **Flessibilità nella configurazione dei ruoli**
  Grazie al campo `extra` in JSONB, è possibile aggiungere informazioni contestuali per ogni associazione (es. contratti specifici, date di validità, note), senza dover modificare lo schema SQL.

* **Garanzia di coerenza referenziale**
  I vincoli di chiave esterna e di unicità assicurano che ogni associazione sia valida (il soggetto e il ruolo devono esistere) e che non vi siano duplicazioni.

* **Tracciabilità delle modifiche**
  I trigger di audit mantengono un log implicito delle modifiche, rendendo più semplice identificare chi ha modificato cosa e quando, utile per scopi di compliance e diagnostica.

---

> 🧠 **"Una tabella ponte che unisce flessibilità e integrità referenziale, consentendo di assegnare e tracciare ruoli multipli a ciascun soggetto senza duplicare dati anagrafici."**