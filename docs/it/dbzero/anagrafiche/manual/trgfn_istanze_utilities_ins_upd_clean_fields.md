## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_istanze_utilities_ins_upd_clean_fields`

> 👀 **Vedi anche**
>
>  Approfondimento tabelle:
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
>
>  Approfondimento funzioni:
>
> * [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)

---

### 🎯 Scopo Principale

Il trigger `anagrafiche.trgfn_istanze_utilities_ins_upd_clean_fields` è invocato **prima di ogni INSERT o UPDATE** su `anagrafiche.istanze_utilities` e ha i seguenti obiettivi:

1. **Generazione automatica** di `codice_istanza` quando non è specificato dall’utente.
2. **Pulizia** e predisposizione di ulteriori campi, se in futuro fosse necessario estendere la logica di default o normalizzazione.

---

### 🔄 Contesto di Esecuzione

* **Evento**: `BEFORE INSERT OR UPDATE` sulla tabella `anagrafiche.istanze_utilities`.
* **Record interessato**: oggetto `NEW`, che rappresenta la riga prima del commit.
* **Dipendenze**: utilizza `script.fn_generate_codice('istanze_utilties')` per calcolare il codice.

---


### 🔍 Logica Operativa

1. **Verifica `codice_istanza`**

   * Se `NEW.codice_istanza` è `NULL` o vuoto, chiama `script.fn_generate_codice('istanze_utilties')`.
   * Il valore restituito è assegnato a `NEW.codice_istanza`.

2. **Restituzione**

   * Ritorna il record `NEW`, arricchito del codice, pronto per la persistenza.

---

### ⚙️ Trigger Collegato

```sql
DROP TRIGGER IF EXISTS trg_istanze_utilities_ins_upd_clean_fields
  ON anagrafiche.istanze_utilities;

CREATE TRIGGER trg_istanze_utilities_ins_upd_clean_fields
  BEFORE INSERT OR UPDATE ON anagrafiche.istanze_utilities
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_istanze_utilities_ins_upd_clean_fields();
```

---

### 💡 Vantaggi Operativi

* **Uniformità**: tutti i record di istanze hanno un `codice_istanza` generato secondo lo stesso schema, eliminando errori manuali.
* **Estendibilità**: la funzione può essere arricchita con ulteriori pulizie (e.g. normalizzazione di testo, assegnazione di default) senza modifiche all’applicazione.

---

### 📌 Best Practice

* Verificare che esista in `config.sistema_codici` la configurazione per `codice_tipo = 'istanze_utilties'`.
* Assicurarsi che `script.fn_generate_codice` gestisca correttamente collisioni e sia performante.
* Evitare di inserire logica complessa o chiamate a tabelle esterne in questo trigger: mantenerlo rapido e focalizzato.

---

{% include-markdown "signature-core.md" %}