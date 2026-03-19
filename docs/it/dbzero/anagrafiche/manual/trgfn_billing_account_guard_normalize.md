## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_billing_account_guard_normalize`

> 👀 **Vedi anche**
>
Approfondimenti tabelle: 
>
[anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
>
Approfondimenti funzioni:
>
[config.sistema_codici](/dbzero/config/manual/sistema_codici)

---
### 🎯 Scopo Principale
(latest review 28-12-25)
Il trigger `anagrafiche.trgfn_billing_account_guard_normalize` applica le **validazioni di business** e normalizza i campi, mentre la generazione del `codice` e' demandata al sistema automatico basato su `config.sistema_codici`.

---

### Contesto di Esecuzione

* **Tipo**: `BEFORE INSERT OR UPDATE` trigger sulla tabella `anagrafiche.billing_account`
* **Oggetto**: opera sul record `NEW`

---


### Logica Operativa

1. **Normalizzazione `codice (account)`**

   * Se `NEW.codice` è valorizzato, viene normalizzato (trim).

2. **Restituzione record**

   * Il record `NEW`, opportunamente modificato, viene ritornato al motore di PostgreSQL, che prosegue l’operazione di INSERT o UPDATE.

---

### Impatto e Vantaggi

* **Consistenza**: garantisce che nessun record venga creato senza un codice di fatturazione.
* **Automazione**: la generazione del codice e' gestita dal trigger automatico su `config.sistema_codici`.
* **Estendibilita**: la configurazione e' centralizzata in `config.sistema_codici` per tutte le tabelle.

---

### ⚠️ Note Operative

* Assicurarsi che in `config.sistema_codici` sia presente la riga per `codice_interno = 'billing_account'` con `usa_sequenza = TRUE`.
* La generazione del codice avviene nel trigger automatico sulla tabella target.

---

{% include-markdown "signature-core.md" %}
