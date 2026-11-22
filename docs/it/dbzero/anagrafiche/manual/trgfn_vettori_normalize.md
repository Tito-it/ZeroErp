## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_vettori_normalize`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.vettori](/dbzero/anagrafiche/tabelle/vettori) — la tabella su cui è agganciata
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_vettori_gen_codice](/dbzero/anagrafiche/funzioni/trgfn_vettori_gen_codice) — chi genera davvero il codice
> * [script.trgfn_codice_maiuscolo](/dbzero/script/funzioni/trgfn_codice_maiuscolo) — chi normalizza davvero il codice

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_vettori_normalize` non fa niente: restituisce la riga così com'è. È agganciata a
`anagrafiche.vettori` prima di ogni inserimento e modifica (`trg_vettori_norm_ins_upd`), e scatta a ogni scrittura
senza effetti.

---

### Il lavoro che il nome promette lo fanno altri

Il nome, allineato ai `normalize` che normalizzano davvero, e il COMMENT, che rinvia la generazione del codice a
`config.sistema_codici`, fanno pensare a un effetto che non c'è. Sui vettori il codice lo genera
`anagrafiche.trgfn_vettori_gen_codice`, dalla riga `vettori` di `config.sistema_codici`, e lo porta in maiuscolo
`script.trgfn_codice_maiuscolo`. Gli altri campi non hanno una normalizzazione.

---

### ⚠️ Che cosa oggi non copre

* **Scatta senza far niente.** Il trigger costa una chiamata a ogni scrittura della tabella. Toglierlo non cambia
  il comportamento.

---

### Codici errore

Nessuno.

---

### Note di migrazione

* 2026-08-21 — il rinvio del COMMENT trova un destinatario: nasce la riga `vettori` di `config.sistema_codici`, e
  il codice si genera. Fino ad allora il rinvio non portava a niente, e un vettore senza codice cadeva sul
  `NOT NULL`.

---

{% include-markdown "signature-core.md" %}
