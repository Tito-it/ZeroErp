## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_istanze_utilities_ins_set_istanza_codice`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
> * [config.sistema_codici](/dbzero/config/tabelle/sistema_codici)
>
> Approfondimenti funzioni:
>
> * [script.fn_get_messaggio](/dbzero/script/funzioni/fn_get_messaggio)

---

### 🎯 Scopo Principale

Il trigger `anagrafiche.trgfn_istanze_utilities_ins_set_istanza_codice`, eseguito **prima di ogni INSERT** su `istanze_utilities`, genera automaticamente un **codice univoco** per la colonna `codice_istanza` se non è stato già fornito, basandosi sulle regole definite in `config.sistema_codici`.

---

### 🔄 Contesto di Esecuzione

* **Tipo**: `BEFORE INSERT` trigger sulla tabella `anagrafiche.istanze_utilities`
* **Dipendenze**: configurazione di prefisso, separatore e sequenza in `config.sistema_codici`
* **Eccezione**: se non trova sequenza configurata solleva errore tramite `script.fn_get_messaggio`

---


### 🔍 Logica Operativa

1. Verifica se `NEW.codice_istanza` è `NULL`.
2. Preleva da `config.sistema_codici`:

   * `prefisso` e `separatore` (stringhe)
   * `lunghezza_numero` (numero di cifre)
   * `nome_sequenza` (nome della sequence SQL)
3. Se `nome_sequenza` esiste:

   * Usa `nextval` per ottenere il valore successivo.
   * Concatena `prefix`, `sep` e il numero formattato con `lpad` a sinistra.
4. Se non trova configurazione, solleva eccezione con messaggio localizzato `SEQUENZA_NON_CONFIGURATA`.

---

### 🚩 Vantaggi Operativi

* **Coerenza dei codici**: tutti i codici istanza seguono uno schema centralizzato e configurabile.
* **Flessibilità**: modifica dinamica di prefisso, separatore e lunghezza tramite tabella di configurazione.
* **Internazionalizzazione**: messaggi d’errore multilingue tramite `fn_get_messaggio`.

---

### ⚠️ Note e Raccomandazioni

* Assicurarsi che esista almeno un record **attivo** in `config.sistema_codici` per `codice_tipo = 'istanze_utilities'`.
* Verificare i permessi sull’esecuzione di `nextval` sulla sequence configurata.
* Gestire possibili collisioni di prefissi/sequenze in ambienti replicati o sharding.

---

{% include-markdown "signature-core.md" %}
