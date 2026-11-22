## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_resellers_normalize`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.resellers](/dbzero/anagrafiche/tabelle/resellers) — la tabella su cui scatta
> * [config.sistema_codici](/dbzero/config/tabelle/sistema_codici) — i generatori di codice, dove il reseller non c'è
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_vettori_gen_codice](/dbzero/anagrafiche/funzioni/trgfn_vettori_gen_codice) — come si genera il codice di una specializzazione che ce l'ha
> * [anagrafiche.trgfn_emittenti_fiscali_normalize](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_normalize) — la sorella degli emittenti, vuota anche lei
> * [anagrafiche.trgfn_vettori_normalize](/dbzero/anagrafiche/funzioni/trgfn_vettori_normalize) — la sorella dei vettori, vuota anche lei

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_resellers_normalize` è un trigger di normalizzazione dei reseller che non fa niente: restituisce
la riga così come la riceve, a ogni nascita e modifica.

---

### ⚠️ Che cosa oggi non copre

* **Il trigger scatta e non fa niente.** Non tocca nessuna colonna e non solleva errori.
* **Il commento della funzione promette un generatore che non c'è.** Dice che la generazione del codice è demandata
  a `config.sistema_codici`, dove non c'è una riga per i reseller, e nessun altro trigger lo genera: il codice, che
  è obbligatorio, lo scrive chi crea il reseller. La forma maiuscola del codice la dà
  `script.trgfn_codice_maiuscolo`, non questo trigger.

---

{% include-markdown "signature-core.md" %}
