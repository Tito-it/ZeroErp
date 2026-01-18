## 📘 Documentazione Concettuale – Tabella `config.sistema_codici`

La tabella **`config.sistema_codici`** definisce le regole per la generazione automatica di codici alfanumerici, utilizzati in vari ambiti (ordini, clienti, fatture, ecc.).

---

### 🎯 Scopo Principale

(latest review 18-01-26)
* **Definizione del formato codice**
  Consente di specificare per ogni tipo di codice (`codice_interno`) un **prefisso**, un **separatore** e la **lunghezza numerica** totale, rendendo parametrica la struttura dei codici generati.
* **Configurazione del meccanismo di sequenza**
  Tramite il flag `usa_sequenza` si abilita o meno l’utilizzo di una progressione automatica basata su sequenza di database, a garanzia di unicità e ordinarietà.
* **Aggancio alla tabella target**
  Le colonne `schema_tabella`, `nome_tabella` e `nome_colonna` definiscono la destinazione del codice e permettono di derivare automaticamente il nome sequenza standard.
* **Automazione trigger**
  Le righe con `usa_sequenza = TRUE` attivano automaticamente la creazione di un trigger sulla tabella target che genera il codice quando il campo risulta nullo (o vuoto/0 secondo il tipo).

---

### 🔄 Parametri di Configurazione

* **`prefisso`**
  Prefisso testuale anteposto alla parte numerica (es. `ORD-`, `CL-`).
* **`separatore`**
  Carattere o stringa utilizzata per separare il prefisso dalla parte numerica (es. `-`, `/`, `_`).
* **`lunghezza_numero`**
  Numero totale di cifre della parte numerica (es. `6` → da `000001` a `999999`). Se la sequenza supera lo spazio, si deve aggiornare il parametro.
* **`usa_sequenza`**
  Booleano che, se **true**, indica che il codice numerico è generato tramite una sequenza di database; se **false**, occorre gestire manualmente l’incremento.
* **`schema_tabella`**, **`nome_tabella`**, **`nome_colonna`**
  Identificano la tabella e la colonna a cui si applica la numerazione e servono per calcolare il nome sequenza automatico `<schema>.<tabella>_<colonna>_seq`.

---

### 💡 Vantaggi Operativi

* **Uniformità dei codici**
  Garantisce che tutti i codici generati rispettino lo stesso pattern configurato, migliorando la leggibilità e la coerenza aziendale.
* **Flessibilità**
  La parametrizzazione di `prefisso`, `separatore` e `lunghezza_numero` consente di adattarsi a requisiti diversi (es. prefissi stagionali, codifiche diverse per aree di business) senza modifiche al codice.
* **Affidabilità della sequenza**
  L’uso di una sequenza di database (quando `usa_sequenza` è **true**) evita collisioni e garantisce incrementi atomici, utili in contesti ad alto carico.
* **Gestione dinamica**
  Il flag `usa_sequenza` permette di sospendere la generazione di un dato tipo di codice senza rimuoverne la configurazione, utile per archiviare vecchie configurazioni o per esigenze temporanee.

---

> 🧠 **"Un sistema configurabile di generazione codici, che separa prefisso, numerazione e logica di sequenza, per codifiche coerenti e facilmente modificabili."**
