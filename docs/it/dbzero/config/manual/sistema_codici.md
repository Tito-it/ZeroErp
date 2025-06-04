## 📘 Documentazione Concettuale – Tabella `config.sistema_codici`

La tabella **`config.sistema_codici`** definisce le regole per la generazione automatica di codici alfanumerici, utilizzati in vari ambiti (ordini, clienti, fatture, ecc.).

---

### 🎯 Scopo Principale

* **Definizione del formato codice**
  Consente di specificare per ogni tipo di codice (`codice_tipo`) un **prefisso**, un **separatore** e la **lunghezza numerica** totale, rendendo parametrica la struttura dei codici generati.
* **Configurazione del meccanismo di sequenza**
  Tramite il flag `usa_sequenza` e l’attributo `nome_sequenza`, si abilita o meno l’utilizzo di una progressione automatica basata su sequenza di database, a garanzia di unicità e ordinarietà.
* **Attivazione o disattivazione**
  Il campo `attivo` permette di abilitare o disabilitare temporaneamente il sistema di generazione per un tipo di codice, senza cancellare la configurazione.

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
* **`nome_sequenza`**
  Nome della sequenza di database (es. `seq_ordine`) da cui attingere il valore numerico.

---

### 💡 Vantaggi Operativi

* **Uniformità dei codici**
  Garantisce che tutti i codici generati rispettino lo stesso pattern configurato, migliorando la leggibilità e la coerenza aziendale.
* **Flessibilità**
  La parametrizzazione di `prefisso`, `separatore` e `lunghezza_numero` consente di adattarsi a requisiti diversi (es. prefissi stagionali, codifiche diverse per aree di business) senza modifiche al codice.
* **Affidabilità della sequenza**
  L’uso di una sequenza di database (quando `usa_sequenza` è **true**) evita collisioni e garantisce incrementi atomici, utili in contesti ad alto carico.
* **Gestione dinamica**
  Il flag `attivo` permette di sospendere la generazione di un dato tipo di codice senza rimuoverne la configurazione, utile per archiviare vecchie configurazioni o per esigenze temporanee.

---

> 🧠 **"Un sistema configurabile di generazione codici, che separa prefisso, numerazione e logica di sequenza, per codifiche coerenti e facilmente modificabili."**
