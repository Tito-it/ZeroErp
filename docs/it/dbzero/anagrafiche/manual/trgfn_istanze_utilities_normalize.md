## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_istanze_utilities_normalize`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — la tabella su cui è montata
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_istanze_utilities_gen_codice](/dbzero/anagrafiche/funzioni/trgfn_istanze_utilities_gen_codice) — chi assegna il codice
> * [script.trgfn_codice_maiuscolo](/dbzero/script/funzioni/trgfn_codice_maiuscolo) — chi normalizza il codice

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_istanze_utilities_normalize` è montata prima di ogni scrittura di un'istanza e non fa
niente: restituisce la riga com'è.

---

### Che cosa fanno gli altri

La normalizzazione dell'istanza sta altrove: il codice lo assegna il generatore della tabella e lo porta in
maiuscolo il trigger del codice normalizzato. Questa funzione non tocca nessuna colonna e non legge nessuna
tabella.

---

### ⚠️ Che cosa oggi non copre

* **Scatta a vuoto.** Il trigger gira a ogni nascita e a ogni modifica di un'istanza senza effetto.

---

{% include-markdown "signature-core.md" %}
