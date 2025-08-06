## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_soggetti_ins_upd_genera_cdsoggetto`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> * [config.sistema_codici](/dbzero/config/tabelle/sistema_codici)
>
> Approfondimento funzioni:
>
> * [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)

---

### 🎯 Scopo Principale

Il trigger `anagrafiche.trgfn_soggetti_ins_upd_genera_cdsoggetto`, eseguito **prima di ogni INSERT o UPDATE** sulla tabella `anagrafiche.soggetti`, assicura la **generazione automatica** del campo `codice_soggetto` quando non viene fornito, utilizzando la configurazione presente in `config.sistema_codici` per il tipo `soggetto`.

---

### 🔄 Contesto di Esecuzione

* **Evento**: `BEFORE INSERT OR UPDATE` su `anagrafiche.soggetti`.
* **Record interessato**: il record `NEW` prima di essere inserito o aggiornato.
* **Trigger condition**: genera il codice solo se `NEW.codice_soggetto IS NULL`.

---


### 🔍 Logica Operativa

1. **Verifica evento**: controlla che l’operazione sia `INSERT` o `UPDATE`.
2. **Controllo valore**: se `NEW.codice_soggetto` è `NULL`, chiama `script.fn_generate_codice('soggetto')`.
3. **Assegnazione**: assegna il valore generato a `NEW.codice_soggetto`.
4. **Restituzione**: ritorna il record modificato per la prosecuzione dell’operazione DML.

---

### ⚙️ Trigger Collegato

```sql
DROP TRIGGER IF EXISTS trg_soggetti_ins_upd_genera_cdsoggetto
  ON anagrafiche.soggetti;

CREATE TRIGGER trg_soggetti_ins_upd_genera_cdsoggetto
  BEFORE INSERT OR UPDATE
  ON anagrafiche.soggetti
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ins_upd_genera_cdsoggetto();
```

---

### 💡 Vantaggi Operativi

* **Uniformità**: garantisce che ogni soggetto abbia un codice generato secondo lo stesso pattern.
* **Automazione**: evita la necessità di gestire manualmente il `codice_soggetto` dall’applicazione.
* **Configurabilità**: la logica di generazione è centralizzata in `config.sistema_codici`, modificabile senza cambiare il codice PL/pgSQL.

---

### 📌 Best Practice

* Verificare la presenza di un record **attivo** in `config.sistema_codici` con `codice_tipo = 'soggetto'`.
* Assicurarsi che `script.fn_generate_codice` supporti il contesto `soggetto` e gestisca eventuali collisioni.
* Tenere semplice la funzione trigger: eviti logica aggiuntiva oltre la generazione del codice.

---

{% include-markdown "signature-core.md" %}
