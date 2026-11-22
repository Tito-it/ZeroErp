## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_titoli_iva_ambiti_guard`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_titoli_iva_ambiti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_ambiti) — le righe su cui è montata
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_titolo_iva_ambito](/dbzero/anagrafiche/funzioni/fn_check_titolo_iva_ambito) — la regola, che chiama
> * [anagrafiche.trgfn_soggetti_titoli_iva_guard_ambito](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_guard_ambito) — il gemello sul titolo
> * [script.fn_raise_primo_motivo_se_presente](/dbzero/script/funzioni/fn_raise_primo_motivo_se_presente) — chi solleva il primo motivo

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_titoli_iva_ambiti_guard` rifiuta una riga di ambito che rende incoerente il suo titolo:
una voce su un titolo che vale per tutto, o un pareggio con un altro titolo. Non contiene la regola: chiama
`anagrafiche.fn_check_titolo_iva_ambito` e solleva il primo motivo, sul campo `ambito`.

---

### ⚠️ Dopo la scrittura, contro la convenzione dei guard

Scatta dopo ogni inserimento e modifica di una riga di ambito. Un guard di solito gira prima della scrittura, ma
qui la funzione conta le righe di ambito e confronta gli oggetti coperti: la riga nuova deve essere già scritta.
Prima della scrittura il titolo si vedrebbe senza di lei, e passerebbe proprio la riga che crea il conflitto.

La cancellazione di una riga non lo sveglia: togliere una voce non crea né una voce su un titolo totale né un
pareggio.

---

### Codici errore

* `E_TITOLO_IVA_AMBITO_NON_AMMESSO` — una voce su un titolo che vale per tutto.
* `E_TITOLO_IVA_AMBITO_SOVRAPPOSTO` — un altro titolo dello stesso tipo copre lo stesso oggetto allo stesso
  livello.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-titoli-iva.sql` — la riga su un titolo ristretto che si registra, quella su un
  titolo totale e il pareggio rifiutati, i livelli diversi che passano.

---

{% include-markdown "signature-core.md" %}
