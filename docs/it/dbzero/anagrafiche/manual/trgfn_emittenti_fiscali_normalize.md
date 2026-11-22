## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_emittenti_fiscali_normalize`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — la tabella su cui scatta
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_guard_codice_forma) — chi normalizza davvero la sigla

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_emittenti_fiscali_normalize` restituisce la riga così com'è: non normalizza niente e non
solleva niente.

---

### La normalizzazione sta altrove

La sola normalizzazione di un emittente è quella della sigla, e la fa
`anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma`, che la porta al maiuscolo prima di giudicarne la forma.
La sigla non si genera: la sceglie chi crea l'emittente, e `config.sistema_codici` non ha una riga per gli
emittenti.

---

### ⚠️ Che cosa oggi non copre

* **Il trigger scatta a ogni scrittura e non fa niente**: prima di ogni `INSERT` e `UPDATE` di
  `anagrafiche.emittenti_fiscali`, e il suo nome non ha una fascia.

---

{% include-markdown "signature-core.md" %}
