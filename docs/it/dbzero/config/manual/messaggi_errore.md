## 📘 Documentazione Concettuale – Tabella `config.messaggi_errore`

> 👀 **Vedi anche**

> Approfondimenti funzioni:   
> - [script.fn_get_messaggio](/dbzero/script/funzioni/fn_get_messaggio)  

La tabella **`config.messaggi_errore`** è il catalogo centralizzato dei testi utilizzati dall’applicazione (errori, avvisi, messaggi informativi) con supporto per l’internazionalizzazione (i18n). Ogni record definisce un messaggio univoco, differenziato per codice e lingua.

---

### 🎯 Scopo Principale

* **Centralizzare i messaggi**
  Raggruppare in un’unica tabella tutti i testi di errore e di notifica, evitando hard‑coding nei sorgenti SQL, trigger o procedure.

* **Supporto multilingua**
  Gestire versioni localizzate degli stessi messaggi tramite il campo `lingua`, semplificando traduzioni e manutenzione.

* **Placeholder dinamici**
  Consentire l’uso di placeholder `%s` nel campo `messaggio`, che verranno sostituiti a runtime dalla funzione `script.fn_get_messaggio` con valori specifici.

---

### 🔍 Struttura dei Campi

| Nome        | Tipo | PK | Descrizione                                                                                    |
| ----------- | ---- | -- | ---------------------------------------------------------------------------------------------- |
| `codice`    | text | ✓  | Codice univoco del messaggio (chiave primaria insieme a `lingua`).                             |
| `lingua`    | text | ✓  | Codice lingua (es. `it`, `en`); default `it`. Identifica la localizzazione del messaggio.      |
| `messaggio` | text |    | Testo del messaggio, che può contenere uno o più placeholder `%s` da sostituire dinamicamente. |

---

### 🔒 Vincoli di Integrità

* **Primary Key**
  `pk_messaggi_errore(codice, lingua)` garantisce l’unicità di ogni coppia codice‑lingua.

---

### 💡 Vantaggi Operativi

* **Manutenzione semplificata**
  Tutti i testi applicativi sono gestiti in un’unica tabella, modificabili senza interventi sul codice.

* **Consistenza**
  Unico punto di verità per i messaggi, riduce duplicazioni e incoerenze fra diversi componenti.

* **Internazionalizzazione**
  Aggiunta di nuove lingue semplicemente inserendo record per lo stesso `codice` con `lingua` diversa.

* **Flessibilità dei testi**
  Placeholder `%s` supportati in fase di recupero garantiscono messaggi contestualizzati e parametrizzati.

* **Best practice**
  Separare i contenuti testuali dal codice SQL migliora leggibilità, manutenzione e qualità del progetto.

---

> 🧠 **“Un catalogo centralizzato e multilingua dei messaggi applicativi, con placeholder `%s` per parametri dinamici, garantisce coerenza, manutenibilità e facilità di traduzione.”**
