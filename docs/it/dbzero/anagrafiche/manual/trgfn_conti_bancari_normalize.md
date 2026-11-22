## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_conti_bancari_normalize`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.conti_bancari](/dbzero/anagrafiche/tabelle/conti_bancari) — il registro degli IBAN, di cui normalizza la riga
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_sepa_mandati_guard](/dbzero/anagrafiche/funzioni/trgfn_sepa_mandati_guard) — la stessa normalizzazione sull'IBAN copiato nel mandato
>
> Guide:
>
> * [Gestione dei conti bancari](/guide/gestione-conti-bancari) — il registro e i suoi legami

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_conti_bancari_normalize` porta IBAN e BIC di un conto nella forma canonica, senza spazi e in
maiuscolo, e ricava il paese dall'IBAN quando chi scrive non lo passa.

---

### ⭐ L'unicità e i formati giudicano il valore normalizzato

Il trigger scatta prima di ogni nascita e di ogni modifica del conto, quindi prima dei vincoli: l'IBAN scritto come
lo si legge da un documento, a gruppi di quattro e in minuscolo, diventa quello canonico, ed è quello che
`uq_conti_bancari_iban` confronta. Due grafie dello stesso conto non fanno due righe.

* **IBAN e BIC**: tolti tutti gli spazi, portati in maiuscolo.
* **Il paese**: le prime due lettere dell'IBAN, solo se il paese manca.

Il trigger non giudica niente e non solleva errori: che l'IBAN, il BIC e il paese abbiano il formato giusto lo dicono
i vincoli della tabella, sul valore che il trigger ha prodotto. Né la cifra di controllo dell'IBAN né l'esistenza del
paese sono verificate.

---

### ⚠️ Che cosa oggi non copre

* **Il paese non segue l'IBAN.** Si ricava solo quando manca: a ogni modifica la riga ha già il paese di prima, e
  cambiato l'IBAN il paese resta quello vecchio. Un paese passato da chi scrive non è confrontato con l'IBAN.
* **Gli altri caratteri restano.** Si tolgono gli spazi, non trattini o punti: un IBAN scritto con un separatore
  diverso dallo spazio è rifiutato dal vincolo di formato.

---

### Test

* Nessun test prova la normalizzazione.

---

{% include-markdown "signature-core.md" %}
