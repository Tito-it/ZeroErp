## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_billing_account_ins_upd_guard_normalize`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle: 
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
>
> Approfondimenti fuzioni: 
>
> * [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)

---

### 🎯 Scopo Principale

Il trigger `anagrafiche.trgfn_billing_account_ins_upd_guard_normalize` assicura che ogni record di **`billing_account`** abbia un **`codice (account)`** valido, generandolo automaticamente quando non viene specificato in fase di INSERT o UPDATE.

---

### 🔄 Contesto di Esecuzione

* **Tipo**: `BEFORE INSERT OR UPDATE` trigger sulla tabella `anagrafiche.billing_account`
* **Oggetto**: opera sul record `NEW`

---


### 📋 Logica Operativa

1. **Verifica `codice (account)`**

   * Se `NEW.codice` è `NULL`, si invoca la funzione `script.fn_generate_codice('billing_account')` per ottenere un nuovo codice.

2. **Restituzione record**

   * Il record `NEW`, opportunamente modificato, viene ritornato al motore di PostgreSQL, che prosegue l’operazione di INSERT o UPDATE.

---

### 🔍 Impatto e Vantaggi

* **Consistenza**: garantisce che nessun record venga creato senza un codice di fatturazione.
* **Automazione**: solleva l’applicazione dal dover calcolare manualmente i codici, riducendo errori.
* **Estendibilità**: cambiando il parametro passato a `fn_generate_codice`, è possibile utilizzare lo stesso pattern di generazione su tabelle diverse.

---

### ⚠️ Note Operative

* La funzione `script.fn_generate_codice` deve supportare il contesto `'billing_account'` e restituire un valore univoco.
* In caso di collisione di codici (rare), il trigger non gestisce retry; è consigliabile che `fn_generate_codice` includa un meccanismo di controllo collisione.

---

{% include-markdown "signature-core.md" %}
