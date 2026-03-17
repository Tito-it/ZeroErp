## 📘 Documentazione Concettuale – Funzione `script.fn_get_messaggio`

> 👀 **Vedi anche**

> Approfondimenti tabelle:   
>
[config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)  


La funzione **`script.fn_get_messaggio(p_codice text, p_valore text DEFAULT NULL, p_lingua text DEFAULT NULL) RETURNS text`** recupera e formatta un messaggio dall’archivio centralizzato, con supporto per placeholder e internazionalizzazione.

---

### 🎯 Scopo Principale

* **Centralizzare i testi**
  Conservare tutti i messaggi (errori, avvisi, info) in tabella, evitando hard‑coding in trigger, procedure o sorgenti SQL.
* **Internazionalizzazione avanzata**
  Selezionare dinamicamente la lingua di output in base a:

  1. parametro `p_lingua`
  2. impostazione configurazione `myapp.user_language`
  3. default `'it'`
* **Placeholder dinamici**
  Utilizzare `format()` per sostituire i placeholder `%s` nel template con i valori runtime, abilitando messaggi parametrizzati.

---

### Parametri di Input

| Nome       | Tipo   | Default |Descrizione                                           |
| ---------- | ------ | ------- |----------------------------------------------------- |
| `p_codice` | `text` | —       | Codice del messaggio (`codice` in `config.messaggi_errore`). |
| `p_valore` | `text` | `NULL`  | Valore da sostituire al placeholder `%s`; se `NULL`, nessuna         sostituzione viene applicata.|
| `p_lingua` | `text` | `NULL`  | Lingua desiderata (es. `it`, `en`); se `NULL`, usa `myapp.user_language` o fallback a `it`. |

---

### Comportamento Interno

1. **Determinazione lingua effettiva**

   ```plpgsql
   lingua_eff := coalesce(
     p_lingua,
     current_setting('myapp.user_language', true),
     'it'
   );
   ```
2. **Recupero del template**

   ```plpgsql
   SELECT messaggio
     INTO tmpl
     FROM config.messaggi_errore
    WHERE codice = p_codice
      AND lingua = lingua_eff;
   ```
3. **Messaggio non definito**

   * Se `tmpl IS NULL`, restituisce:

     ```text
     [MESSAGGIO NON DEFINITO: <p_codice>]
     ```
4. **Sostituzione placeholder**

   * Se `p_valore IS NOT NULL`, restituisce:

     ```plpgsql
     format(tmpl, p_valore)
     ```
   * Altrimenti restituisce `tmpl` originale.

---

### Valore di Ritorno

* **`text`**
  Messaggio finale, con eventuale sostituzione di `%s` applicata.

---

### Vantaggi Operativi

* **Manutenzione semplificata**
  Modifiche ai messaggi avvengono unicamente in tabella, senza interventi su sorgenti PL/pgSQL.
* **Coerenza e uniformità**
  Un solo punto di definizione e recupero per tutti i testi applicativi.
* **Internazionalizzazione flessibile**
  Supporto per lingua utente tramite GUC e fallback gerarchico.
* **Messaggi parametrizzati**
  Placeholder `%s` sostituiti dinamicamente, per contesti runtime variabili.
* **Best practice**
  Separazione tra codici di business e contenuti testuali, migliorando qualità e riusabilità.

---

> **“Centralizzare e parametrizzare i messaggi in tabella con supporto multilingua e placeholder `%s` è una best practice per mantenere il codice pulito, manutenibile e traducibile.”**