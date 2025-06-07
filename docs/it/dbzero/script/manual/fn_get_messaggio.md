## 📘 Documentazione Concettuale – Funzione `script.fn_get_messaggio`

> 👀 **Vedi anche**

> Approfondimenti tabelle:   
> * [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)  



La funzione **`script.fn_get_messaggio(p_codice text, p_valore text DEFAULT NULL, p_lingua text DEFAULT 'it') RETURNS text`** recupera il testo di un messaggio dalla tabella `config.messaggi_errore`, con supporto multilingua e sostituzione di placeholder.

---

### 🎯 Scopo Principale

* **Centralizzare i testi**
  Mantenere in tabella tutti i messaggi di errore e informativi, evitando di hard‑codarli nelle procedure, trigger o sorgenti SQL.
* **Internazionalizzazione**
  Supportare più lingue per gli stessi messaggi semplicemente tramite il parametro `p_lingua`.
* **Placeholder dinamici**
  Applicare sostituzioni dei placeholder `%s` all’interno del messaggio, consentendo di inserire uno o più valori dinamici direttamente nel template.

---

### 🔍 Parametri di Input

| Nome       | Tipo   | Descrizione                                                                                         |
| ---------- | ------ | --------------------------------------------------------------------------------------------------- |
| `p_codice` | `text` | Codice del messaggio da recuperare (campo `codice` in `config.messaggi_errore`).                    |
| `p_valore` | `text` | Valore da sostituire al placeholder `%s`; se `NULL`, il messaggio viene restituito senza modifiche. |
| `p_lingua` | `text` | Codice lingua (es. `it`, `en`); default `it`.                                                       |

---

### ⚙️ Comportamento

1. **Recupero del template**
   Seleziona il campo `messaggio` da `config.messaggi_errore` dove `codice = p_codice` e `lingua = p_lingua`.
2. **Messaggio non definito**
   Se non viene trovato un record, restituisce:

   > `[MESSAGGIO NON DEFINITO: <p_codice>]`
3. **Sostituzione placeholder**
   Se `p_valore` non è `NULL`, sostituisce ogni occorrenza di `%s` nel template con il contenuto di `p_valore`.

---

### 🔒 Valore di Ritorno

* **`text`**
  Il messaggio finale, con eventuali sostituzioni di `%s` applicate.

---

### 💡 Vantaggi Operativi

* **Manutenzione semplificata**
  Tutti i testi sono centralizzati in una tabella, modificabili senza intervenire sul codice.
* **Coerenza e uniformità**
  Unico punto di gestione dei messaggi applicativi, evitando duplicazioni e incongruenze.
* **Supporto multilingua**
  Traduzioni gestite inserendo più righe nella tabella per codici e lingue differenti.
* **Flessibilità tramite placeholder**
  Permette di generare messaggi contestualizzati con parametri dinamici sostituiti al posto di `%s`.
* **Best practice**
  Separare i contenuti testuali dal codice aumenta la qualità del progetto e facilita le future estensioni.

---

> 🧠 **“Centralizzare i messaggi in tabella e utilizzare placeholder `%s` rende l’applicazione più pulita, coerente e facilmente traducibile.”**
