## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_soggetti_upd_protect_codice_soggetto`

> 👀 **Vedi anche**
>
> Approdondmenti tabelle: 
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
>
> Approdondmenti funzioni: 
>
> * Funzione errori: [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---

### 🎯 Scopo Principale

Il trigger `anagrafiche.trgfn_soggetti_upd_protect_codice_soggetto`, esploso **prima di ogni UPDATE** sulla tabella `anagrafiche.soggetti`, garantisce che il campo **`codice_soggetto`** non possa essere modificato una volta assegnato.

---

### 🔄 Contesto di Esecuzione

* **Evento**: `BEFORE UPDATE` su `anagrafiche.soggetti`.
* **Condizione**: attivazione solo se:

  1. `TG_OP = 'UPDATE'`
  2. `OLD.codice_soggetto` **non** è `NULL`
  3. `NEW.codice_soggetto` **diverso** da `OLD.codice_soggetto`
* **Risultato**: blocco dell’UPDATE con eccezione loggata.

---


### 🔍 Logica Operativa

1. **Verifica evento**: conferma che l’operazione sia un `UPDATE`.
2. **Protezione campo**:

   * Blocca l’update solo se `OLD.codice_soggetto` era già valorizzato.
   * Confronta i valori `OLD` e `NEW` per identificare eventuali modifiche.
3. **Eccezione**: in caso di modifica non consentita, invoca `script.fn_log_and_raise_error` con il codice `E_COLONNA_NON_MODIFICABILE` e termina l’operazione.

---

### ⚙️ Trigger Collegato

```sql
DROP TRIGGER IF EXISTS trg_soggetti_upd_protect_codice_soggetto
  ON anagrafiche.soggetti;

CREATE TRIGGER trg_soggetti_upd_protect_codice_soggetto
  BEFORE UPDATE ON anagrafiche.soggetti
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_soggetti_upd_protect_codice_soggetto();
```

---

### 💡 Vantaggi Operativi

* **Integrità della chiave**: `codice_soggetto` rimane immutabile dopo la prima assegnazione.
* **Logging standardizzato**: tutte le eccezioni passano per il catalogo `config.messaggi_errore` e `dbops.error_log`.
* **Indipendenza**: il controllo è a livello database, non richiede logica in applicazione.

---

### 📌 Best Practice

* Inserire il messaggio di errore `E_COLONNA_NON_MODIFICABILE` in `config.messaggi_errore` con dettagli appropriati.
* Testare gli update sul campo `codice_soggetto` per garantire il blocco corretto.
* Mantenere la funzione focalizzata solo sulla protezione della colonna.

---

{% include-markdown "signature-core.md" %}
