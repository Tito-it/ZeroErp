## 📘 Documentazione Concettuale – Tabella `acquisti.ddt`

> 👀 **Vedi anche**
>
> • [acquisti.ddt_righe](/dbzero/acquisti/tabelle/ddt_righe)
> • [acquisti.ordini_righe_fulfillment](/dbzero/acquisti/tabelle/ordini_righe_fulfillment)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Documento di trasporto in ingresso**: la ricezione della merce dal fornitore.

⚠️ A differenza del DDT di vendita, questo è tipicamente **subìto**: arriva insieme al
trasporto e va registrato così com'è. Non ha una numerazione fiscale nostra — il numero è
quello del fornitore, e non è sotto il nostro controllo.

Ne segue che i vincoli di unicità del numero, se ci sono, vanno pensati **per fornitore** e
non in assoluto: due fornitori diversi possono legittimamente emettere lo stesso numero.

---

### Il legame con l'ordine

Passa dal ponte `acquisti.ordini_righe_fulfillment`, riga per riga — non dalla testata. È la
stessa scelta del ciclo vendite: un DDT può coprire righe di ordini diversi, e un ordine può
essere evaso da più DDT.

---

{% include-markdown "it/dbzero/acquisti/_dominio-acquisti.md" %}

---

{% include-markdown "signature-core.md" %}
