## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_istanze_utilities_normalize`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
>
Approfondimento funzioni:
>
[config.sistema_codici](/dbzero/config/manual/sistema_codici)

---

### 🎯 Scopo Principale

(latest review 28-12-25)
Il trigger `anagrafiche.trgfn_istanze_utilities_normalize` è invocato **prima di ogni INSERT o UPDATE** su `anagrafiche.istanze_utilities` e ha i seguenti obiettivi:

1. **Pulizia** e predisposizione di ulteriori campi, se in futuro fosse necessario estendere la logica di default o normalizzazione.

---

### Contesto di Esecuzione

* **Evento**: `BEFORE INSERT OR UPDATE` sulla tabella `anagrafiche.istanze_utilities`.
* **Record interessato**: oggetto `NEW`, che rappresenta la riga prima del commit.
* **Dipendenze**: la generazione del codice e' demandata al trigger automatico basato su `config.sistema_codici`.

---


### Logica Operativa

1. **Restituzione**

   * Ritorna il record `NEW` senza alterare il codice; la generazione avviene nel trigger automatico della tabella target.

---

### Trigger Collegato

```sql
DROP TRIGGER IF EXISTS trg_istanze_utilities_normalize_ins_upd
  ON anagrafiche.istanze_utilities;

CREATE TRIGGER trg_istanze_utilities_normalize_ins_upd
  BEFORE INSERT OR UPDATE ON anagrafiche.istanze_utilities
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_istanze_utilities_normalize();
```

---

### Vantaggi Operativi

* **Uniformita**: tutti i record di istanze hanno un `codice (istanza)` generato secondo lo stesso schema, eliminando errori manuali.
* **Estendibilita**: la funzione può essere arricchita con ulteriori pulizie (e.g. normalizzazione di testo, assegnazione di default) senza modifiche all’applicazione.

---

### Best Practice

* Verificare che esista in `config.sistema_codici` la configurazione per `codice_interno = 'istanze_utilties'` e `usa_sequenza = TRUE`.
* Evitare di inserire logica complessa o chiamate a tabelle esterne in questo trigger: mantenerlo rapido e focalizzato.

---

{% include-markdown "signature-core.md" %}
